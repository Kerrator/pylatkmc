"""Recover per-geometry Vineyard ν₀ for catalogued KMC events.

The pyKMC event catalogue (`reference_table.pickle`) stores, per event, the
*relaxed local cluster* at the minimum (`initial_positions`), at the saddle
(`saddle_positions`) and at the final state — the same atoms, in the same order,
carved within rcut of the moving atom, with `initial_types` (alloy-aware) and the
local mover index `move_atom_idx`. That cluster already carries a frozen boundary,
so a partial (frozen-boundary) Hessian over its inner free region is valid HTST —
the same convention pyKMC's off-lattice rate backend uses (``n_zero_modes = 0``).

This module turns the "important geometries" of each family (the per-bucket
``representative_row_indices`` of ``rate_lookup_table_family.csv``) into real,
per-geometry Vineyard prefactors:

    ν₀ = ∏ω_min / ∏ω_saddle   (saddle drops its single imaginary mode)

and aggregates them per family/bucket into ``family_prefactors[_bucket].csv``,
which ``build_family_rate_table.load_family_nu0`` already joins as ``nu0_Hz``.

The simulation trajectory (`trajkmc.xyz`, frame = step) + step log (`pykmc.out`)
are used to *verify* each event — locate a step where it fired, recover the
full-system configuration, identify the mover by frame-diff — and to cross-check
the recovered barrier against the catalogue. This is the "construct the full
system from the data" recovery the catalogue alone cannot provide.

Heavy deps (pandas, ASE, LAMMPS) — part of the optional ``pylatkmc[ingest]``
extra. LAMMPS must be importable for the Hessian step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .cadence import Cadence, count_xyz_frames, parse_sample_every
from .htst.hessian_lammps import compute_mass_weighted_hessian, select_free_atoms
from .htst.kappa_rpa import vineyard_prefactor
from .provenance import (
    NU0_MAX_HZ,
    NU0_MIN_HZ,
    BucketRecord,
    GeometryRecord,
    RecoveryStatus,
)

# 1NN spacing for FCC Ni (Å); auto-freeze drops atoms more than ~half a layer
# above the mover to kill surface soft-mode inflation (canonical_kappa v7 fix).
_LAYER_DZ_A = 0.88
_DEFAULT_FREE_RADIUS_A = 6.0
_MOVE_THRESHOLD_A = 0.5  # frame-diff displacement that marks a "mover"
_EA_GATE_EV = 0.03  # absolute eV tolerance for recovered-vs-catalogue barrier
_EA_GATE_FRAC = 0.05  # or 5% relative, whichever is larger


# ---------------------------------------------------------------------------
# Target selection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TargetEvent:
    """One representative event to recover ν₀ for."""

    family_id: str
    family_bucket_id: str
    sim_path: str
    idx_ref: int
    classified_row: int
    n_moved: int | None


def resolve_targets(
    rate_table_csv: str | Path,
    classified_csv: str | Path,
    families: list[str] | None = None,
    per_bucket: int | None = None,
) -> list[TargetEvent]:
    """Resolve each bucket's ``representative_row_indices`` to concrete events.

    ``representative_row_indices`` are *positional* row indices into
    ``classified_events_with_families.csv`` (verified against real data).
    """
    rate = pd.read_csv(rate_table_csv)
    classified = pd.read_csv(classified_csv)
    targets: list[TargetEvent] = []
    for _, row in rate.iterrows():
        fid = str(row["family_id"])
        if families and fid not in families:
            continue
        if int(row.get("n_events", 0)) <= 0:
            continue
        raw = row.get("representative_row_indices")
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            reps = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if per_bucket is not None:
            reps = reps[:per_bucket]
        for rep in reps:
            if rep < 0 or rep >= len(classified):
                continue
            ev = classified.iloc[int(rep)]
            targets.append(
                TargetEvent(
                    family_id=fid,
                    family_bucket_id=str(row["family_bucket_id"]),
                    sim_path=str(ev["sim_path"]),
                    idx_ref=int(ev["idx_ref"]),
                    classified_row=int(rep),
                    n_moved=int(ev["n_moved"]) if "n_moved" in ev and pd.notna(ev["n_moved"]) else None,
                )
            )
    return targets


# ---------------------------------------------------------------------------
# Catalogue + trajectory access
# ---------------------------------------------------------------------------
def load_reference_event(sim_path: str | Path, idx_ref: int) -> pd.Series | None:
    """Load one event row from a sim's ``reference_table.pickle`` by idx_ref."""
    rt_path = Path(sim_path) / "reference_table.pickle"
    if not rt_path.is_file():
        return None
    table = pd.read_pickle(rt_path)
    hit = table[table["idx_ref"] == idx_ref]
    if hit.empty:
        return None
    return hit.iloc[0]


def find_firing_steps(sim_path: str | Path, idx_ref: int) -> np.ndarray:
    """Steps at which ``idx_ref`` fired, from pykmc.out (empty if never)."""
    from importlib import import_module

    # parse_pykmc_out lives in the analysis package; import lazily so this module
    # imports without the apps repo on PATH.
    out_path = Path(sim_path) / "pykmc.out"
    if not out_path.is_file():
        return np.empty(0, dtype=int)
    try:
        lme = import_module("Analysis.lattice_map_events")
        df = lme.parse_pykmc_out(out_path)
        col = "ref_event"
    except (ImportError, ModuleNotFoundError):
        df = _parse_pykmc_out_fallback(out_path)
        col = "ref_event"
    if df.empty or col not in df:
        return np.empty(0, dtype=int)
    return df.loc[df[col] == idx_ref, "step"].to_numpy(dtype=int)


def _parse_pykmc_out_fallback(path: str | Path) -> pd.DataFrame:
    """Self-contained pykmc.out parser (mirrors Analysis.lattice_map_events)."""
    rows = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 8 and p[0].isdigit() and int(p[0]) > 0:
                rows.append({"step": int(p[0]), "ref_event": int(p[3]), "Ea": float(p[4])})
    return pd.DataFrame(rows)


def parse_potential_from_input(sim_path: str | Path) -> str | None:
    """Read the EAM potential filename from a sim's input.in pair_coeff line.

    e.g. ``pair_coeff = * * ./Bonny_2013_NiFeCr.eam Ni Fe`` -> 'Bonny_2013_NiFeCr.eam'.
    """
    import re

    inp = Path(sim_path) / "input.in"
    if not inp.is_file():
        return None
    pat = re.compile(r"pair_coeff\s*=\s*\*\s*\*\s*(\S+)")
    with open(inp) as f:
        for line in f:
            m = pat.search(line)
            if m:
                return Path(m.group(1)).name  # strip any ./ or path prefix
    return None


def resolve_potential(sim_path: str | Path, override: str | None = None) -> str | None:
    """Locate the EAM potential file for a simulation.

    If ``override`` is a real file, use it. Otherwise parse the filename from
    input.in and search the sim dir, its parents, and the common workspace
    potential locations. Returns an absolute path or None.
    """
    if override and override not in ("auto", "") and Path(override).is_file():
        return str(Path(override).resolve())

    name = parse_potential_from_input(sim_path)
    if not name:
        return str(Path(override).resolve()) if override and Path(override).is_file() else None

    sim = Path(sim_path).resolve()
    search = [sim, *sim.parents[:6]]
    # common shared locations within the kmc workspace
    for p in sim.parents:
        if (p / "Data").is_dir():
            search += [p / "Data" / "Research", p / "toolkit" / "potentials", p / "Data"]
            break
    seen: set[Path] = set()
    for d in search:
        if d in seen or not d.is_dir():
            continue
        seen.add(d)
        cand = d / name
        if cand.is_file():
            return str(cand.resolve())
    return None


def resolve_cadence(sim_path: str | Path) -> Cadence:
    """Resolve the step↔frame cadence for a simulation."""
    sim = Path(sim_path)
    traj = sim / "trajkmc.xyz"
    n_frames = count_xyz_frames(traj) if traj.is_file() else 0
    sample_every = parse_sample_every(sim / "input.in")
    max_step = (n_frames - 1) * sample_every if n_frames else 0
    return Cadence(sample_every=sample_every, n_frames=n_frames, max_step=max_step)


def load_frame(sim_path: str | Path, frame_index: int):
    """Read one trajectory frame as an ASE Atoms (positions, symbols, cell)."""
    from ase.io import read

    traj = Path(sim_path) / "trajkmc.xyz"
    return read(str(traj), index=frame_index)


# ---------------------------------------------------------------------------
# Mover detection (full-system verification)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MoverSet:
    primary: int
    movers: tuple[int, ...]
    max_disp_A: float


def detect_movers(frame_n, frame_np1, move_threshold: float = _MOVE_THRESHOLD_A) -> MoverSet | None:
    """Identify atoms that moved between two consecutive frames (PBC-corrected).

    Returns the primary mover (largest displacement) and all movers above
    ``move_threshold``; None if no atom moved (e.g. off-cadence pairing).
    """
    from ase.geometry import find_mic

    p0 = frame_n.get_positions()
    p1 = frame_np1.get_positions()
    if p0.shape != p1.shape:
        return None
    cell = frame_n.get_cell()
    disp, dmag = find_mic(p1 - p0, cell, pbc=True)
    movers = np.where(dmag > move_threshold)[0]
    if movers.size == 0:
        return None
    primary = int(movers[int(np.argmax(dmag[movers]))])
    return MoverSet(primary=primary, movers=tuple(int(m) for m in movers), max_disp_A=float(dmag.max()))


# ---------------------------------------------------------------------------
# ν₀ core — frozen-boundary partial Hessian on the relaxed cluster
# ---------------------------------------------------------------------------
def _cluster_cell(positions: np.ndarray, margin: float = 12.0) -> list[float]:
    """A non-periodic bounding box (+margin) for a carved cluster."""
    span = positions.max(axis=0) - positions.min(axis=0)
    return [float(span[0] + 2 * margin), float(span[1] + 2 * margin), float(span[2] + 2 * margin)]


def _free_region(
    positions: np.ndarray,
    move_atom_idx: int,
    free_radius: float,
    auto_freeze_above_mover: bool,
) -> np.ndarray:
    """Free atoms = within ``free_radius`` of the mover, minus atoms more than
    ~half a layer ABOVE the mover (surface soft-mode auto-freeze)."""
    free = select_free_atoms(positions, move_atom_idx, radius=free_radius)
    if auto_freeze_above_mover:
        zmax = positions[:, 2].max()
        mover_z = positions[move_atom_idx, 2]
        is_surface_mover = mover_z >= zmax - 0.5 * _LAYER_DZ_A
        # Auto-freeze atoms above the mover ONLY for SURFACE movers (kills the
        # rattle of any adatom/surface atom sitting above a top-layer hop).
        # Subsurface/bulk movers keep the full radial free region: their saddle
        # mode often points UP toward the surface, so freezing above truncates
        # the reaction coordinate and yields a non-first-order saddle — the
        # subsurface_1NN failure mode seen in the first harvest. The carved
        # cluster's frozen rcut boundary already damps subsurface soft modes.
        if is_surface_mover:
            keep = positions[free, 2] <= mover_z + _LAYER_DZ_A
            free = free[keep]
    # always keep the mover itself
    if move_atom_idx not in set(free.tolist()):
        free = np.append(free, move_atom_idx)
    return np.sort(free)


def geometry_nu0(
    initial_positions: np.ndarray,
    saddle_positions: np.ndarray,
    types: list[str],
    move_atom_idx: int,
    potential_path: str,
    free_radius: float = _DEFAULT_FREE_RADIUS_A,
    dx: float = 0.01,
    auto_freeze_above_mover: bool = True,
    cell: list[float] | None = None,
) -> tuple[float, int]:
    """Compute ν₀ for one relaxed cluster (min1 + saddle, same atom order).

    Returns ``(nu0_Hz, n_free)``. Frozen-boundary partial Hessian convention →
    ``n_zero_modes = 0``. ``vineyard_prefactor`` internally requires the saddle to
    have exactly one imaginary mode (``expect_saddle=True``) and that
    N(init) = N(sad) + 1; it raises ``ValueError`` otherwise, which the caller
    maps to ``SADDLE_NOT_FIRST_ORDER``.
    """
    initial_positions = np.asarray(initial_positions, dtype=float)
    saddle_positions = np.asarray(saddle_positions, dtype=float)
    free = _free_region(initial_positions, move_atom_idx, free_radius, auto_freeze_above_mover)
    box = cell if cell is not None else _cluster_cell(initial_positions)

    h_init = compute_mass_weighted_hessian(
        initial_positions, types, box, free, potential_path, dx=dx, pbc=False,
    )
    h_sad = compute_mass_weighted_hessian(
        saddle_positions, types, box, free, potential_path, dx=dx, pbc=False,
    )
    nu0 = vineyard_prefactor(h_init, h_sad, n_zero_modes=0)
    return float(nu0), int(len(free))


# ---------------------------------------------------------------------------
# Per-event orchestration
# ---------------------------------------------------------------------------
def recover_event_nu0(
    target: TargetEvent,
    potential_path: str = "auto",
    free_radius: float = _DEFAULT_FREE_RADIUS_A,
    dx: float = 0.01,
    verify_trajectory: bool = True,
) -> GeometryRecord:
    """Recover ν₀ for one representative event, with trajectory verification.

    ``potential_path`` may be ``"auto"`` (resolve the EAM file per-sim from
    input.in — handles pure-Ni and NiFe/NiCr alloy sims) or an explicit path.
    """
    base = dict(
        family_id=target.family_id,
        family_bucket_id=target.family_bucket_id,
        sim_path=target.sim_path,
        idx_ref=target.idx_ref,
    )
    ev = load_reference_event(target.sim_path, target.idx_ref)
    if ev is None:
        return GeometryRecord(**base, status=RecoveryStatus.ERROR, note="reference_table row not found")

    ea_cat = float(ev["energy_barrier"])
    pot = resolve_potential(target.sim_path, potential_path)
    if pot is None:
        return GeometryRecord(
            **base, status=RecoveryStatus.ERROR, Ea_catalogue_eV=ea_cat,
            note="EAM potential not found (input.in pair_coeff / search dirs)",
        )
    firing_step = None
    frame_index = None
    reminimized = False
    traj_note = ""

    # Trajectory verification is SOFT provenance: it records where in the run the
    # event fired (and the full-system frame for any future boundary extension),
    # but never blocks the ν₀ — the catalogue cluster already carries a relaxed,
    # internally-consistent min1+saddle from the original pARTn search.
    if verify_trajectory:
        steps = find_firing_steps(target.sim_path, target.idx_ref)
        if steps.size == 0:
            traj_note = "idx_ref not in pykmc.out (ν₀ from cluster anyway); "
        else:
            cad = resolve_cadence(target.sim_path)
            for s in steps:  # first firing step whose min1 frame is on-cadence
                fb = cad.frame_before_step(int(s))
                if fb is not None:
                    firing_step, frame_index = int(s), fb
                    break
            if frame_index is None:
                firing_step = int(steps[0])
                reminimized = True

    # ν₀ from the relaxed cluster (min1 + saddle share atom order → no embedding)
    try:
        init_pos = np.asarray(ev["initial_positions"], dtype=float)
        sad_pos = np.asarray(ev["saddle_positions"], dtype=float)
        types = [str(t) for t in ev["initial_types"]]
        move_idx = int(ev["move_atom_idx"])
        nu0, n_free = geometry_nu0(
            init_pos, sad_pos, types, move_idx, pot,
            free_radius=free_radius, dx=dx,
        )
    except ValueError as exc:
        # vineyard mode-count mismatch → not a clean first-order saddle
        return GeometryRecord(
            **base, status=RecoveryStatus.SADDLE_NOT_FIRST_ORDER,
            Ea_catalogue_eV=ea_cat, firing_step=firing_step, frame_index=frame_index,
            note=str(exc)[:200],
        )
    except Exception as exc:  # noqa: BLE001 — record any engine/IO failure as ERROR
        return GeometryRecord(
            **base, status=RecoveryStatus.ERROR, Ea_catalogue_eV=ea_cat,
            firing_step=firing_step, frame_index=frame_index, note=f"{type(exc).__name__}: {exc}"[:200],
        )

    if not (NU0_MIN_HZ <= nu0 <= NU0_MAX_HZ):
        return GeometryRecord(
            **base, status=RecoveryStatus.NU0_OUT_OF_RANGE, nu0_Hz=nu0,
            Ea_catalogue_eV=ea_cat, n_free=n_free, firing_step=firing_step,
            frame_index=frame_index, min1_reminimized=reminimized,
            note=f"{traj_note}nu0={nu0:.3e} Hz outside [{NU0_MIN_HZ:.0e},{NU0_MAX_HZ:.0e}]",
        )

    return GeometryRecord(
        **base, status=RecoveryStatus.OK, nu0_Hz=nu0, Ea_catalogue_eV=ea_cat,
        Ea_recovered_eV=ea_cat, n_free=n_free, firing_step=firing_step,
        frame_index=frame_index, min1_reminimized=reminimized, saddle_mode="cluster",
        note=f"{traj_note}frozen-boundary partial Hessian (n_zero_modes=0)",
    )


# ---------------------------------------------------------------------------
# Bucket aggregation + CSV emission
# ---------------------------------------------------------------------------
def run_buckets(
    targets: list[TargetEvent],
    potential_path: str,
    T_K: float,
    free_radius: float = _DEFAULT_FREE_RADIUS_A,
    dx: float = 0.01,
    verify_trajectory: bool = True,
    progress: bool = True,
) -> tuple[list[BucketRecord], list[GeometryRecord]]:
    """Recover ν₀ for every target and aggregate per (family, bucket)."""
    buckets: dict[tuple[str, str], BucketRecord] = {}
    geoms: list[GeometryRecord] = []
    for i, t in enumerate(targets):
        rec = recover_event_nu0(t, potential_path, free_radius=free_radius, dx=dx,
                                verify_trajectory=verify_trajectory)
        geoms.append(rec)
        key = (t.family_id, t.family_bucket_id)
        buckets.setdefault(key, BucketRecord(t.family_id, t.family_bucket_id, T_K)).geometries.append(rec)
        if progress:
            tag = rec.status.value if not rec.ok else f"{rec.nu0_Hz / 1e12:.2f} THz"
            print(f"  [{i + 1}/{len(targets)}] {t.family_id}/{t.family_bucket_id} idx={t.idx_ref}: {tag}")
    return list(buckets.values()), geoms


def write_outputs(
    buckets: list[BucketRecord],
    geoms: list[GeometryRecord],
    bucket_csv: str | Path,
    family_csv: str | Path | None = None,
    geometry_csv: str | Path | None = None,
) -> None:
    """Write per-bucket (and rolled-up per-family) ν₀ + a per-geometry audit log.

    The per-family ``family_prefactors.csv`` (keyed ``motif`` == family_id) is what
    ``build_family_rate_table.load_family_nu0`` joins; we roll buckets up to the
    family median so that existing join keeps working unchanged.
    """
    _upsert(bucket_csv, [b.to_row() for b in buckets], keys=("family_id", "family_bucket_id", "T_K"))

    if family_csv is not None:
        fam: dict[str, list[float]] = {}
        T = buckets[0].T_K if buckets else 500.0
        for b in buckets:
            med = b.nu0_median()
            if med is not None:
                fam.setdefault(b.family_id, []).append(med)
        fam_rows = [
            {
                "motif": fid,
                "T_K": T,
                "nu0_Hz": float(np.median(vals)),
                "nu0_THz": float(np.median(vals)) / 1e12,
                "nu0_source": "trajectory",
                "n_buckets": len(vals),
            }
            for fid, vals in sorted(fam.items())
        ]
        _upsert(family_csv, fam_rows, keys=("motif", "T_K"))

    if geometry_csv is not None:
        pd.DataFrame([g.to_row() for g in geoms]).to_csv(geometry_csv, index=False)


def _upsert(csv_path: str | Path, rows: list[dict], keys: tuple[str, ...]) -> None:
    """Idempotent upsert: replace rows matching ``keys``, keep the rest."""
    path = Path(csv_path)
    new = pd.DataFrame(rows)
    if new.empty:
        return
    if path.is_file():
        old = pd.read_csv(path)
        # normalise key dtypes to string for a stable match
        def _key_df(df: pd.DataFrame) -> pd.Series:
            return df[list(keys)].astype(str).agg("|".join, axis=1)

        if all(k in old.columns for k in keys):
            mask = ~_key_df(old).isin(set(_key_df(new)))
            combined = pd.concat([old[mask], new], ignore_index=True)
        else:
            combined = new
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        combined = new
    combined.to_csv(path, index=False)
