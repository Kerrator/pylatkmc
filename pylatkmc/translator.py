"""Translate the curated FCC family catalogue into pattern-DB Processes.

The upstream pyKMC analysis pipeline produces:

- `classified_events_with_families.csv` — one row per pyKMC event,
  tagged with `family_id`, `family_bucket_id`, `assignment_status`.
- `rate_lookup_table_family.csv` — per-(family_id, family_bucket_id)
  aggregated statistics: n_events, Ea_mean_eV, Ea_std_eV, etc.

This module reads the family rate table and emits a list[Process] that
the decision-tree codegen (M-B) can compile into runtime C.

Translation strategy per family:

| Family | Mode | Per-(bucket, direction) Process count |
|---|---|---|
| `surface_1NN_inplane` | one Process per (bucket × in-plane direction) | nv1×nv2×4 = up to 100 |
| `subsurface_1NN_inplane` | same | nv1×nv2×12 ≈ 300 (12 1NN in bulk-like FCC) |
| `bulk_1NN_inplane` | same | nv1×nv2×12 |
| `surface_2NN_diagonal` | one Process per (bucket × 2NN direction) | nv1×4 ≈ 20 (5 surface 2NN; in-plane is 4) |
| `subsurface_2NN_diagonal` | same | nv1×6 (6 bulk 2NN) |
| `surface_interlayer_hop` | one per (bucket × interlayer direction) | nv1×4 (4 cross-layer 1NN) |
| `subsurface_interlayer_hop` | same | nv1×8 |
| `surface_subsurface_exchange_*` | 2-action Process per direction | small |
| `subsurface_migration_*` | 2-action Process per direction | small |
| `concerted_multisite` | per-row positional events (deferred) | 0 in v2 (fit_barrier=False) |
| `unresolved_multisite` | skip (visibility-only) | 0 |

Each emitted Process has:

- `conditions`: anchor = Vacant, mover-direction = mover_species (Ni for now)
- `actions`: anchor → mover_species, mover-direction → Vacant (2 actions; 3 for triple hops)
- `rate_constant`: bucket Ea_mean → arrhenius_scalar at the spec's
  configured T (no Bystanders in v2; deferred to a later phase)
- `Ea_eV`: bucket's mean

For the v2 first cut (M-A), Bystanders are not used. Each bucket
becomes N Processes (one per direction); spatial asymmetry within a
bucket is averaged out (matches the curated catalogue's existing
treatment). The rate-cube approach lost this AND collapsed multiple
buckets; the pattern-DB at minimum keeps per-bucket fidelity.

A future M-A++ phase can split into per-arrangement Processes when
intra-bucket Ea scatter is wide.

References:
- The family registry:
  `apps/PyKMC_Analysis/Analysis/families.py:118+`
- The family rate table format:
  `apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table_family.csv`
"""

from __future__ import annotations

import csv
import itertools
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .dissolution_rate import DissolutionParams, dissolution_rate, e_bare
from .processes import (
    ANCHOR_COORD,
    Action,
    Condition,
    CoordOffset,
    Process,
    ShellCondition,
)
from .rate_expression import arrhenius_scalar, bucket_warns_on_scatter

# ---------------------------------------------------------------------------
# Catalogue row type — keeps translator independent of pandas
# ---------------------------------------------------------------------------


def _parse_nu0(raw: str | None) -> float | None:
    """Parse the optional ``nu0_Hz`` column: None if absent, blank, NaN, or non-positive."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if (math.isfinite(v) and v > 0.0) else None


@dataclass(frozen=True)
class FamilyBucketRow:
    """One row of `rate_lookup_table_family.csv`."""

    family_id: str
    family_bucket_id: str
    n_events: int
    Ea_mean_eV: float
    Ea_std_eV: float
    Ea_min_eV: float
    Ea_max_eV: float
    nu0_Hz: float | None = None  # per-family HTST Vineyard prefactor (Hz); None -> k0 fallback

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> FamilyBucketRow:
        return cls(
            family_id=row["family_id"].strip(),
            family_bucket_id=row["family_bucket_id"].strip(),
            n_events=int(row["n_events"]),
            Ea_mean_eV=float(row["Ea_mean_eV"]),
            Ea_std_eV=float(row["Ea_std_eV"]),
            Ea_min_eV=float(row["Ea_min_eV"]),
            Ea_max_eV=float(row["Ea_max_eV"]),
            nu0_Hz=_parse_nu0(row.get("nu0_Hz")),
        )


def load_bucket_exclusions(csv_path: Path | str) -> set[tuple[str, str]]:
    """Load a per-bucket exclusion list from a flagged CSV.

    Expected schema (columns can be in any order; only `flag`,
    `family_id`, `bucket` are read):

        flag, family_id, bucket, [decision_notes, ...]

    Rows where `flag` is "S" (skip) are returned as a set of
    (family_id, bucket_id) tuples that the translator should drop.
    Rows with flag "K" (keep) or anything else (including "?" for
    "still inspecting") are kept.

    Returns an empty set if csv_path is None or the file doesn't
    exist (i.e. translation runs unfiltered).
    """
    if csv_path is None:
        return set()
    p = Path(csv_path)
    if not p.is_file():
        return set()
    skip: set[tuple[str, str]] = set()
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            flag = (row.get("flag") or "").strip().upper()
            if flag == "S":
                fid = row["family_id"].strip()
                bkt = row["bucket"].strip()
                skip.add((fid, bkt))
    return skip


def load_family_rate_table(path: Path | str) -> list[FamilyBucketRow]:
    """Load `rate_lookup_table_family.csv` into a list of FamilyBucketRow.

    Skips rows where `Ea_mean_eV` is NaN (placeholder buckets emitted by
    family registry for visibility but not fit) or where `n_events == 0`.

    Skips families with `fit_barrier=False` semantics — we identify them
    by `Ea_mean_eV` being NaN, since those rows carry no fittable data.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"family rate table not found: {path}")

    rows: list[FamilyBucketRow] = []
    with open(path, newline="") as f:
        for raw in csv.DictReader(f):
            try:
                ea = float(raw["Ea_mean_eV"])
                n = int(raw["n_events"])
            except (ValueError, KeyError):
                continue
            if n == 0:
                continue
            if ea != ea:  # NaN check (fit_barrier=False rows)
                continue
            rows.append(FamilyBucketRow.from_csv_row(raw))
    return rows


# ---------------------------------------------------------------------------
# Bucket-key parsing (`nv1=2_nv2=0`, `nv1=4`, `li=1_nv1=3`)
# ---------------------------------------------------------------------------

_BUCKET_PART = re.compile(r"^([a-zA-Z][a-zA-Z0-9_]*)=(-?\d+)$")


def parse_bucket_key(bucket_id: str) -> dict[str, int]:
    """Parse a bucket id like `nv1=2_nv2=0` into `{"nv1": 2, "nv2": 0}`.

    Accepts arbitrary axis names (so `li=1_nv1=3` parses to
    `{"li": 1, "nv1": 3}`). Raises ValueError on malformed input.

    Examples
    --------
    >>> parse_bucket_key("nv1=2_nv2=0")
    {'nv1': 2, 'nv2': 0}
    >>> parse_bucket_key("nv1=4")
    {'nv1': 4}
    >>> parse_bucket_key("*")
    Traceback (most recent call last):
        ...
    ValueError: malformed bucket key '*'
    """
    if not bucket_id or "=" not in bucket_id:
        raise ValueError(f"malformed bucket key {bucket_id!r}")
    parts = bucket_id.split("_")
    out: dict[str, int] = {}
    for p in parts:
        m = _BUCKET_PART.match(p)
        if not m:
            raise ValueError(f"malformed bucket key {bucket_id!r}")
        out[m.group(1)] = int(m.group(2))
    return out


# ---------------------------------------------------------------------------
# Direction sets per family — using NeighbourCode IR
# ---------------------------------------------------------------------------
#
# Each direction is a CoordOffset(code="NC_<NAME>"). The runtime resolves
# each code via lattice->coord_table at touchup time. See
# runtime/src/core/coord_codes.h for the canonical Cartesian deltas of
# each code.


def _co(code: str) -> CoordOffset:
    """Shorthand: build a CoordOffset from a NeighbourCode name."""
    return CoordOffset(code=code)


# FCC(100) surface 1NN in-plane: 4 axial directions.
SURFACE_1NN_INPLANE_DIRS: tuple[CoordOffset, ...] = (
    _co("NC_NN1_PX"),
    _co("NC_NN1_MX"),
    _co("NC_NN1_PY"),
    _co("NC_NN1_MY"),
)

# FCC bulk 1NN: 12 directions = 4 in-plane + 4 cross-layer-up + 4 cross-layer-down.
BULK_1NN_DIRS: tuple[CoordOffset, ...] = (
    # In-plane (4)
    _co("NC_NN1_PX"),
    _co("NC_NN1_MX"),
    _co("NC_NN1_PY"),
    _co("NC_NN1_MY"),
    # Cross-layer up (4)
    _co("NC_NN1_UP_PP"),
    _co("NC_NN1_UP_PM"),
    _co("NC_NN1_UP_MP"),
    _co("NC_NN1_UP_MM"),
    # Cross-layer down (4)
    _co("NC_NN1_DOWN_PP"),
    _co("NC_NN1_DOWN_PM"),
    _co("NC_NN1_DOWN_MP"),
    _co("NC_NN1_DOWN_MM"),
)

# FCC(100) surface 2NN: 4 in-plane diagonals.
SURFACE_2NN_DIRS: tuple[CoordOffset, ...] = (
    _co("NC_NN2_DIAG_PP"),
    _co("NC_NN2_DIAG_PM"),
    _co("NC_NN2_DIAG_MP"),
    _co("NC_NN2_DIAG_MM"),
)

# FCC bulk 2NN: 6 axial directions (±x, ±y, ±z).
BULK_2NN_DIRS: tuple[CoordOffset, ...] = (
    _co("NC_NN2_PX"),
    _co("NC_NN2_MX"),
    _co("NC_NN2_PY"),
    _co("NC_NN2_MY"),
    _co("NC_NN2_PZ"),
    _co("NC_NN2_MZ"),
)

# Cross-layer 1NN directions (used by interlayer-hop families).
INTERLAYER_1NN_DIRS_UP: tuple[CoordOffset, ...] = (
    _co("NC_NN1_UP_PP"),
    _co("NC_NN1_UP_PM"),
    _co("NC_NN1_UP_MP"),
    _co("NC_NN1_UP_MM"),
)
INTERLAYER_1NN_DIRS_DOWN: tuple[CoordOffset, ...] = (
    _co("NC_NN1_DOWN_PP"),
    _co("NC_NN1_DOWN_PM"),
    _co("NC_NN1_DOWN_MP"),
    _co("NC_NN1_DOWN_MM"),
)


# ---------------------------------------------------------------------------
# Process emission helpers
# ---------------------------------------------------------------------------

ANCHOR = ANCHOR_COORD  # re-exported for backwards compatibility


def _safe_name(*parts: str) -> str:
    """Build a valid C identifier from string parts. Lower-cases everything,
    replaces non-alphanumerics with `_`."""
    raw = "__".join(str(p) for p in parts)
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw).lower()
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


def _direction_label(d: CoordOffset) -> str:
    """Stable label for a CoordOffset, used in Process names.
    With the NeighbourCode IR this is just the code name lower-cased and
    stripped of the `nc_` prefix (so `NC_NN1_PX` → `nn1_px`)."""
    code = d.code
    if code.startswith("NC_"):
        code = code[3:]
    return code.lower()


def _shell_conditions_from_bucket_key(
    bucket_id: str,
    mover_coord: CoordOffset,
) -> tuple:
    """Decode `nv1=k_nv2=m` → (ShellCondition(1nn,Vacant,k),
    ShellCondition(2nn,Vacant,m)).

    Returns the appropriate tuple of ShellConditions to gate this
    Process, anchored at the **mover** (`mover_coord` = the direction
    coord of the hop). The catalogue's `n_vac_nn1_initial` /
    `n_vac_nn2_initial` are computed at the mover's position upstream
    (see `apps/PyKMC_Analysis/Analysis/tools/fix_catalogue_nvac.py:
    corrected_nvac_nn1`).

    Bucket-key axes recognised:
    - `nv1` → ShellCondition at mover_coord, shell="1nn", species="Vacant"
    - `nv2` → ShellCondition at mover_coord, shell="2nn", species="Vacant"
    - `li`  → ignored in v0.3 (layer-index bucket; needs site_class
              gating, scheduled for v0.4)
    - other → silently dropped (reported via translator warnings if you
              want to plumb a callback later)

    Returns an empty tuple for unparseable bucket keys (e.g. "*",
    "(empty)"), in which case the Process is emitted *without* shell
    gating — the runtime fires it whenever the minimal Conditions
    match, exactly v0.2 behaviour.
    """
    from .processes import ShellCondition  # local import: avoid cycle warnings

    try:
        parsed = parse_bucket_key(bucket_id)
    except ValueError:
        return ()

    out: list = []
    for axis, count in parsed.items():
        if axis == "nv1":
            out.append(
                ShellCondition(
                    coord=mover_coord,
                    shell="1nn",
                    species="Vacant",
                    count=int(count),
                )
            )
        elif axis == "nv2":
            out.append(
                ShellCondition(
                    coord=mover_coord,
                    shell="2nn",
                    species="Vacant",
                    count=int(count),
                )
            )
        elif axis == "li":
            # Layer index — not a shell count. Skip in v0.3.
            continue
        else:
            # Unknown axis (e.g. n_Fe_1nn — could be supported via
            # Bystander in v0.4). Skip silently for forward-compat.
            continue
    return tuple(out)


def _emit_simple_2action_hop(
    family_id: str,
    bucket_id: str,
    direction: CoordOffset,
    mover_species: str,
    Ea_eV: float,
    rate_Hz: float,
    prefactor_Hz: float | None = None,
    emit_shell_gates: bool = True,
) -> Process:
    """A single-atom 1NN/2NN hop: vacancy at anchor + mover at direction →
    swap. Two Conditions, two Actions, plus optional ShellConditions
    decoded from bucket_id.

    `emit_shell_gates`: when True (default), the Process gets a
    ShellCondition per nv1/nv2 axis in the bucket key, gating its
    firing to configurations that match the bucket's discovery
    context. Pass False to recover v0.2 behaviour (no gating)."""
    shell_conds: tuple = (
        _shell_conditions_from_bucket_key(bucket_id, mover_coord=direction)
        if emit_shell_gates
        else ()
    )
    return Process(
        name=_safe_name(family_id, bucket_id, _direction_label(direction), mover_species),
        family_id=family_id,
        Ea_eV=Ea_eV,
        rate_constant=float(rate_Hz),
        prefactor_Hz=(float(prefactor_Hz) if prefactor_Hz is not None else None),
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=direction, species=mover_species),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after=mover_species),
            Action(coord=direction, before=mover_species, after="Vacant"),
        ),
        shell_conditions=shell_conds,
    )


# ---------------------------------------------------------------------------
# Per-family translators
# ---------------------------------------------------------------------------


def translate_simple_hop_family(
    rows: list[FamilyBucketRow],
    family_id: str,
    directions: tuple[CoordOffset, ...],
    mover_species: str,
    k0_Hz: float,
    T_K: float,
    on_scatter_warn: Callable[[str], None] | None = None,
    style: str = "constant",
) -> list[Process]:
    """Translate any "single-atom hop" family (surface/subsurface/bulk
    1NN/2NN inplane, interlayer hops, etc.) into Processes.

    Emits one Process per (bucket × direction). The bucket's Ea_mean becomes the
    Arrhenius rate at the spec's T. When ``style == "htst"`` and the family
    carries a per-family Vineyard ``nu0_Hz``, that prefactor replaces the global
    ``k0_Hz``; otherwise the global ``k0_Hz`` is used (the fallback).
    """
    family_rows = [r for r in rows if r.family_id == family_id]
    out: list[Process] = []
    for r in family_rows:
        if (msg := bucket_warns_on_scatter(r.Ea_std_eV, r.n_events)) and (
            on_scatter_warn is not None
        ):
            on_scatter_warn(f"{family_id}/{r.family_bucket_id} ({r.n_events} events): {msg}")
        k0_eff = r.nu0_Hz if (style == "htst" and r.nu0_Hz is not None) else k0_Hz
        rate = arrhenius_scalar(Ea_eV=r.Ea_mean_eV, k0_Hz=k0_eff, T_K=T_K)
        for d in directions:
            out.append(
                _emit_simple_2action_hop(
                    family_id=family_id,
                    bucket_id=r.family_bucket_id,
                    direction=d,
                    mover_species=mover_species,
                    Ea_eV=r.Ea_mean_eV,
                    rate_Hz=rate,
                    prefactor_Hz=k0_eff,
                )
            )
    return out


# ---------------------------------------------------------------------------
# Dissolution family (analytical; Erlebacher/MESOSIM electrochemical law)
# ---------------------------------------------------------------------------
#
# Unlike the hop families above, dissolution is NOT derived from the trajectory
# catalogue. It is an analytical, coordination- and composition-dependent
# electrochemical event: a surface atom (the anchor) leaves the lattice, its
# site becoming Vacant. The bare barrier
#
#     E_bare = sum over occupied 1NN neighbours of eps(mover, neighbour)
#
# is baked here as the Process Ea_eV; the overpotential term Phi is subtracted
# at runtime (see rateconst_eval in the generated proclist.h) so one compiled
# binary runs at any applied potential.
#
# Each (mover_species, neighbour-composition) bucket becomes one 1-action
# Process gated by exact occupied-species ShellConditions at the anchor's 1NN
# shell. Buckets are mutually exclusive (every occupied species, INCLUDING the
# count-0 ones, is gated), so exactly one dissolution Process fires per surface
# atom. Only coordinations in [min, max] are emitted, so high-coordination
# bulk/terrace atoms (N > max occupied neighbours) match no Process and cannot
# dissolve -- this is the MESOSIM "<= N_max occupied neighbours" gate.
#
# NOTE on coordination: a surface atom's 1NN CSR list omits the absent
# above-surface lattice neighbours, so the gated count is the number of
# OCCUPIED present-neighbours = the physical coordination N. Counting occupied
# species (not vacant) is therefore correct for both outer surfaces and the
# internal void surfaces that form during dealloying.


def compositions_of(n: int, species: tuple[str, ...]) -> list[dict[str, int]]:
    """All neighbour-composition histograms of total occupied count ``n`` over
    ``species``.

    Each result is a dict ``{species: count}`` with ``sum(counts) == n`` that
    lists EVERY species (including count 0), so the emitted ShellConditions
    fully specify the bucket and buckets are mutually exclusive.
    """
    out: list[dict[str, int]] = []
    for combo in itertools.combinations_with_replacement(species, n):
        hist = dict.fromkeys(species, 0)
        for sp in combo:
            hist[sp] += 1
        out.append(hist)
    return out


def _dissolution_bucket_label(hist: dict[str, int], species: tuple[str, ...]) -> str:
    """Deterministic label from the nonzero part of a histogram, e.g.
    ``{"Ni": 6, "Cr": 3}`` -> ``'ni6_cr3'``. Unique per mover because the
    nonzero histogram (and hence N) is fully determined by these parts."""
    parts = [f"{sp.lower()}{hist[sp]}" for sp in species if hist.get(sp, 0) > 0]
    return "_".join(parts) if parts else "n0"


def _emit_dissolution_process(
    params: DissolutionParams,
    mover_species: str,
    hist: dict[str, int],
    occupied_species: tuple[str, ...],
    T_K: float,
    shell: str = "1nn",
) -> Process:
    """One 1-action dissolution Process: ``mover`` at the anchor -> Vacant,
    gated by the exact occupied-neighbour histogram at the anchor's ``shell``.

    ``Ea_eV`` is the bare barrier E_bare; ``prefactor_Hz`` is the dissolution
    attempt frequency nu_E; ``is_electrochemical`` flags the runtime to apply
    the overpotential term. ``rate_constant`` is the phi=0 rate (diagnostic
    only; the runtime recomputes from prefactor + Ea + phi at startup)."""
    Ea = e_bare(params, mover_species, hist)
    rate = dissolution_rate(params, mover_species, hist, T_K, phi_eV=0.0)
    label = _dissolution_bucket_label(hist, occupied_species)
    shell_conds = tuple(
        ShellCondition(coord=ANCHOR, shell=shell, species=sp, count=hist.get(sp, 0))
        for sp in occupied_species
    )
    return Process(
        name=_safe_name("dissolution", mover_species, label),
        family_id="dissolution",
        Ea_eV=Ea,
        rate_constant=float(rate),
        prefactor_Hz=float(params.nu_E_Hz),
        is_electrochemical=True,
        conditions=(Condition(coord=ANCHOR, species=mover_species),),
        actions=(Action(coord=ANCHOR, before=mover_species, after="Vacant"),),
        shell_conditions=shell_conds,
    )


def translate_dissolution_family(
    params: DissolutionParams,
    species: list[str],
    T_K: float,
    shell: str = "1nn",
) -> list[Process]:
    """Emit the analytical electrochemical dissolution family.

    Parameters
    ----------
    params : DissolutionParams
        ε table, nu_E, and the [min, max] coordination gate.
    species : list[str]
        The full spec species list (``"Vacant"`` first). Movers and neighbour
        species are the non-Vacant entries.
    T_K : float
        Temperature (used only for the diagnostic ``rate_constant``).
    shell : str
        Which shell the occupied-neighbour count is taken over ("1nn").

    Returns one 1-action Process per (mover, occupied-neighbour histogram) for
    every coordination N in ``[params.min_coordination, params.max_coordination]``.
    """
    occupied = tuple(s for s in species if s != "Vacant")
    if not occupied:
        return []
    out: list[Process] = []
    for mover in occupied:
        for n in range(params.min_coordination, params.max_coordination + 1):
            for hist in compositions_of(n, occupied):
                out.append(
                    _emit_dissolution_process(
                        params, mover, hist, occupied, T_K, shell=shell
                    )
                )
    return out


def translate_surface_1NN_inplane(
    rows: list[FamilyBucketRow],
    k0_Hz: float = 1.0e13,
    T_K: float = 500.0,
    mover_species: str = "Ni",
    on_scatter_warn: Callable[[str], None] | None = None,
) -> list[Process]:
    """FCC(100) surface 1NN in-plane: 4 dirs/bucket. ~35k catalogue events."""
    return translate_simple_hop_family(
        rows,
        "surface_1NN_inplane",
        SURFACE_1NN_INPLANE_DIRS,
        mover_species,
        k0_Hz,
        T_K,
        on_scatter_warn,
    )


# ---------------------------------------------------------------------------
# Per-family translators — table-driven dispatch
# ---------------------------------------------------------------------------

# Maps `family_id` → directions to emit Processes for. All families in this
# table use the simple 2-action swap (anchor ↔ direction), differing only
# in which neighbour-shell directions apply.
_FAMILY_DIRECTIONS: dict[str, tuple[CoordOffset, ...]] = {
    "surface_1NN_inplane": SURFACE_1NN_INPLANE_DIRS,  # 4
    "subsurface_1NN_inplane": BULK_1NN_DIRS,  # 12
    "bulk_1NN_inplane": BULK_1NN_DIRS,  # 12
    "surface_2NN_diagonal": SURFACE_2NN_DIRS,  # 4
    "subsurface_2NN_diagonal": BULK_2NN_DIRS,  # 6
    "surface_interlayer_hop": INTERLAYER_1NN_DIRS_DOWN,  # 4 (surface→subsurface)
    "subsurface_interlayer_hop": INTERLAYER_1NN_DIRS_UP + INTERLAYER_1NN_DIRS_DOWN,  # 8
    "surface_subsurface_exchange_up": INTERLAYER_1NN_DIRS_UP,  # 4
    "surface_subsurface_exchange_down": INTERLAYER_1NN_DIRS_DOWN,  # 4
    "subsurface_migration_axial": BULK_1NN_DIRS,  # 12
    "subsurface_migration_interlayer": INTERLAYER_1NN_DIRS_UP + INTERLAYER_1NN_DIRS_DOWN,  # 8
}

# Multi-site families with fit_barrier=False — visibility only, skip in v2.
# These come into the catalogue with NaN Ea so load_family_rate_table()
# already filters them out, but we list them here to be explicit.
_FAMILIES_SKIPPED: frozenset[str] = frozenset(
    {
        "concerted_multisite",
        "unresolved_multisite",
    }
)

# Adatom-gated families — deliberately NOT translated until the lattice has
# above-surface adatom positions + adatom-presence conditions.
#
# The P2+P3 NiFe audit (2026-08-14) proved every curated row of the family
# formerly named surface_subsurface_exchange_lateral (now adatom_attachment)
# is a single-atom adatom re-insertion: an *above-surface* adatom drops into
# a surface vacancy (n_moved==1, coord 4→7, dz ≈ −1.5 Å). The v0.3 lattice
# has no adatom sites, so the old _FAMILY_DIRECTIONS mapping (2-action swap
# over all 8 interlayer directions at any surface vacancy, no adatom
# required) fired these as the same class of kinetic artefact described for
# _ADATOM_REVERSE_FAMILIES below — and with Ea_mean ≈ 1.0 eV the low-Ea
# floor filter could never catch it. adatom_detachment is the reverse leg
# (0 catalogue rows today; excluded upstream by the 1.2 eV barrier cap).
# The legacy id stays here so pre-rename catalogue CSVs skip cleanly
# instead of warning as unknown.
_ADATOM_GATED_FAMILIES: frozenset[str] = frozenset(
    {
        "adatom_attachment",
        "adatom_detachment",
        "surface_subsurface_exchange_lateral",  # legacy id (pre-rename CSVs)
    }
)

# Families where the very-low-Ea catalog buckets correspond to adatom-reverse
# events (an above-surface atom hops back down). These shouldn't fire in a
# v0.2 lattice that has no above-surface positions: their forward arms
# (high-Ea exchange-up events) can't fire either, so the reverse arms firing
# at every surface vacancy is a kinetic artefact. Until we add adatom
# positions + adatom-presence conditions, drop buckets where Ea < the floor.
# (Families whose *entire* population is adatom motion are handled
# structurally instead — see _ADATOM_GATED_FAMILIES above.)
#
# Set ADATOM_REVERSE_EA_FLOOR_EV = None (or pass it via translate_all) to
# include these buckets again — useful once the catalog encodes the
# adatom-presence condition explicitly.
_ADATOM_REVERSE_FAMILIES: frozenset[str] = frozenset(
    {
        "surface_interlayer_hop",
        "surface_subsurface_exchange_down",
    }
)
ADATOM_REVERSE_EA_FLOOR_EV: float | None = None
# Default: filter OFF. Use the per-bucket exclusion CSV instead (see
# `load_bucket_exclusions` below) — coarse Ea-floor filtering proved
# too blunt; per-bucket curation is the correct approach.
# Pass `adatom_reverse_ea_floor_eV=0.20` to translate_all to enable the
# experimental filter. Empirically the filter slightly perturbs MSD/D but
# does NOT cleanly fix the catalogue's bucket-mean aggregation issue: the
# remaining surface_1NN_inplane low-Ea buckets (Ea ≈ 0.17 eV) still
# dominate r_tot at high T. Real fix is upstream catalogue
# re-classification with adatom-presence conditions or per-arrangement
# Processes.


def prefactor_coverage(
    rows: list[FamilyBucketRow], style: str = "htst"
) -> dict[str, str]:
    """Per-family prefactor provenance: ``family_id -> "htst" | "fallback_k0"``.

    A family is ``"htst"`` when ``style == "htst"`` and at least one of its
    buckets carries a finite per-family ``nu0_Hz``; otherwise it falls back to
    the global ``k0`` (the Debye assumption).
    """
    cov: dict[str, str] = {}
    for r in rows:
        cur = cov.get(r.family_id, "fallback_k0")
        if style == "htst" and r.nu0_Hz is not None:
            cur = "htst"
        cov[r.family_id] = cur
    return cov


def translate_all(
    rows: list[FamilyBucketRow],
    k0_Hz: float = 1.0e13,
    T_K: float = 500.0,
    mover_species: str = "Ni",
    style: str = "constant",
    on_scatter_warn: Callable[[str], None] | None = None,
    on_unknown_family: Callable[[str], None] | None = None,
    adatom_reverse_ea_floor_eV: float | None = ADATOM_REVERSE_EA_FLOOR_EV,
    bucket_exclusions: set[tuple[str, str]] | None = None,
) -> list[Process]:
    """Translate every supported family in the catalogue into Processes.

    Iterates `_FAMILY_DIRECTIONS` and dispatches each to
    translate_simple_hop_family. Unknown family_ids in the catalogue
    (i.e. families not in `_FAMILY_DIRECTIONS`, `_FAMILIES_SKIPPED`, or
    `_ADATOM_GATED_FAMILIES`) are reported via `on_unknown_family` and
    skipped. Adatom-gated families (adatom_attachment / adatom_detachment
    and the legacy surface_subsurface_exchange_lateral id) are skipped
    silently: they need above-surface adatom sites the lattice does not
    have yet.

    `adatom_reverse_ea_floor_eV`: drop buckets in
    _ADATOM_REVERSE_FAMILIES whose Ea_mean is below this floor. These
    represent kinetic-artefact reverse arms of forward exchange-up
    events that can't fire in a lattice with no above-surface
    positions. Pass None to include all buckets.

    Returns a deduplicated, name-unique list[Process].
    """
    out: list[Process] = []

    families_in_catalogue = {r.family_id for r in rows}
    known = (
        set(_FAMILY_DIRECTIONS.keys())
        | _FAMILIES_SKIPPED
        | _ADATOM_GATED_FAMILIES
    )
    unknown = families_in_catalogue - known
    for fid in sorted(unknown):
        if on_unknown_family is not None:
            on_unknown_family(fid)

    # Filter rows by the adatom-reverse Ea floor before dispatching.
    if adatom_reverse_ea_floor_eV is not None:
        filtered_rows: list[FamilyBucketRow] = []
        for r in rows:
            if (
                r.family_id in _ADATOM_REVERSE_FAMILIES
                and r.Ea_mean_eV < adatom_reverse_ea_floor_eV
            ):
                continue
            filtered_rows.append(r)
        rows = filtered_rows

    # Per-bucket exclusions (from a user-flagged CSV via load_bucket_exclusions).
    if bucket_exclusions:
        rows = [r for r in rows if (r.family_id, r.family_bucket_id) not in bucket_exclusions]

    for fid in sorted(_FAMILY_DIRECTIONS.keys()):
        out.extend(
            translate_simple_hop_family(
                rows=rows,
                family_id=fid,
                directions=_FAMILY_DIRECTIONS[fid],
                mover_species=mover_species,
                k0_Hz=k0_Hz,
                T_K=T_K,
                on_scatter_warn=on_scatter_warn,
                style=style,
            )
        )

    # Sanity: process names should be globally unique (decision-tree
    # codegen requires it).
    seen: set[str] = set()
    for p in out:
        if p.name in seen:
            raise ValueError(
                f"duplicate Process name in translator output: {p.name!r}. "
                f"This is a translator bug — names should be globally unique."
            )
        seen.add(p.name)
    return out


__all__ = (
    "FamilyBucketRow",
    "load_family_rate_table",
    "parse_bucket_key",
    "SURFACE_1NN_INPLANE_DIRS",
    "BULK_1NN_DIRS",
    "SURFACE_2NN_DIRS",
    "BULK_2NN_DIRS",
    "INTERLAYER_1NN_DIRS_UP",
    "INTERLAYER_1NN_DIRS_DOWN",
    "ANCHOR",
    "translate_simple_hop_family",
    "translate_surface_1NN_inplane",
    "translate_dissolution_family",
    "compositions_of",
    "translate_all",
)
