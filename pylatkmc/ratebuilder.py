"""Rate-data builder: curated CSV + ModelSpec → .kmcrt binary cube.

M3a scope (MVP):
  - **Tier 1** direct aggregation by the spec's axis tuple (event-count-weighted
    mean barrier → pre-exponentiated rate via Arrhenius).
  - **Tier 2** deterministic element-drop fallback for cells that tier 1 left empty.
    Drop order chosen to preserve physical meaning:
        n_Cr_nn2 → n_Fe_nn2 → n_vac_nn2 → n_Cr_nn1 → n_Fe_nn1
  - **Tier 7** scalar legacy fallback (`rate_lookup_table.csv`, keyed by
    `n_vacant_inplane_nn`) applied only to `<110>_inplane` cells still empty.

Tiers 3 / 4 / 5 / 6 (cross-class, family-bucket, mover collapse, etc.) ship in M3b.

Input columns (from `classified_events_with_families.csv`):
  - site_class_3d, direction_family_3d, mover_species_ml
  - nn1_count_Ni/Fe/Cr, nn2_count_Ni/Fe/Cr
  - n_vac_nn1_initial  (no n_vac_nn2 column; derived from shell size 6)
  - energy_barrier     (Ea in eV)
  - assignment_status  (keep 'accepted' only)

Output: a `.kmcrt` file whose JSON header matches the shape the generated
`ratetable.c` expects. The runtime ratetable.c validates n_axes / axis_maxes
at load time, so a mismatched spec/table combo fails loudly.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from pylatkmc.kmcfmt import RATETABLE_MAGIC, write_header

if TYPE_CHECKING:
    from pylatkmc.spec import ModelSpec

K_B_EV_PER_K = 8.617333e-5

# These maps MUST stay in lock-step with events_base.h and the generator's
# CLASS_NAMES/DIR_NAMES lists. If events_base.h changes, these change too.
CLASS_MAP = {"surface": 0, "subsurface": 1, "bulk_like": 2}
DIR_MAP = {
    "<110>_inplane":    0,
    "<100>_inplane":    1,
    "<111>_interlayer": 2,
    "<001>_exchange":   3,
    "unresolved":       4,
}

# Motif enum (must match events_base.h)
MF_SURFACE_1NN, MF_SURFACE_2NN, MF_SUBSURFACE_1NN = 0, 1, 2
MF_SURF_SUBSURF_EXCHANGE, MF_INTERLAYER = 3, 4
MF_SUBSURFACE_EXCHANGE, MF_CONCERTED_3D, MF_UNRESOLVED = 5, 6, 7

# Tier 2 element-drop order. Absent axes are skipped gracefully.
_TIER2_DROP_ORDER: list[str] = [
    "n_Cr_nn2",
    "n_Fe_nn2",
    "n_vac_nn2",
    "n_Cr_nn1",
    "n_Fe_nn1",
]


# Shell size used to derive n_vac_nn2 (CSV doesn't carry it directly). This is
# a bulk-interior assumption; surface atoms whose physical NN2 shell has < 6
# entries will over-estimate vacancy count by 1-2 at most. Fallback tiers pick
# up the slack.
_NN2_SHELL_SIZE = 6


@dataclass
class BuildStats:
    n_rows_total: int
    n_rows_accepted: int
    n_rows_keyable: int
    n_cells_total: int
    n_cells_tier1: int
    n_cells_tier2: int
    n_cells_tier5: int
    n_cells_tier6: int
    n_cells_tier7: int
    n_cells_filled: int
    # Per-slab provenance: {(sc, dir): "tier-6: family_id"} filled by tier 6.
    tier6_family_used: dict[tuple[int, int], str] = field(default_factory=dict)
    # Per-slab coverage counts (fraction of cells non-zero).
    slab_coverage: dict[tuple[int, int], float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, int | float]:
        n = self.n_cells_total
        # Drop helper dicts for a simple summary view.
        summary = {
            k: v for k, v in self.__dict__.items()
            if k not in ("tier6_family_used", "slab_coverage")
        }
        return {
            **summary,
            "pct_tier1": round(100.0 * self.n_cells_tier1 / n, 2),
            "pct_filled": round(100.0 * self.n_cells_filled / n, 2),
        }


# ------------------------------------------------------------------
# Deterministic motif-of-(class, direction) — mirrors legacy motif_of in
# latkmc/tools/build_binary_rate_table.py. Hard-coded here because the
# mapping is a physics fact, not a spec choice.
# ------------------------------------------------------------------
_SC_SURFACE, _SC_SUBSURFACE, _SC_BULK_LIKE = 0, 1, 2
_DF_110, _DF_100, _DF_111, _DF_001 = 0, 1, 2, 3

# Tier 5 cross-class borrow order. For each recipient site_class, donor classes
# are tried in order; the first class with data wins. Borrowed verbatim from
# latkmc/tools/build_binary_rate_table.py:193-197 because the 100Ni MSD parity
# gate requires it — surface-subsurface exchange events live in the subsurface
# training data but also need to populate the symmetric surface cell (and vice
# versa). Pulled forward from M3b because without it the vacancy can't leave
# the surface.
_CROSS_CLASS_DONORS: dict[int, list[int]] = {
    _SC_SURFACE:    [_SC_SUBSURFACE, _SC_BULK_LIKE],
    _SC_SUBSURFACE: [_SC_BULK_LIKE, _SC_SURFACE],
    _SC_BULK_LIKE:  [_SC_SUBSURFACE, _SC_SURFACE],
}

# Tier 6 family mapping. For each (site_class, direction) pair, the primary
# family_id in Analysis/families.py and a fallback family_id (used if the
# primary has no data). Bucket is ignored — we use the family's event-weighted
# mean barrier across all its populated buckets as the fallback value.
# Pairs not listed fall through to tier 7.
_SC_DIR_TO_FAMILIES: dict[tuple[int, int], list[str]] = {
    (_SC_SURFACE,    _DF_110): ["surface_1NN_inplane"],
    (_SC_SUBSURFACE, _DF_110): ["subsurface_1NN_inplane"],
    (_SC_BULK_LIKE,  _DF_110): ["subsurface_1NN_inplane"],
    (_SC_SURFACE,    _DF_100): ["surface_1NN_inplane"],            # no exact surface_2NN family yet
    (_SC_SUBSURFACE, _DF_100): ["subsurface_2NN_diagonal"],
    (_SC_BULK_LIKE,  _DF_100): ["subsurface_2NN_diagonal"],
    (_SC_SURFACE,    _DF_111): ["surface_subsurface_exchange_up",
                                "surface_interlayer_hop"],
    (_SC_SUBSURFACE, _DF_111): ["subsurface_interlayer_hop",
                                "subsurface_migration_interlayer"],
    (_SC_BULK_LIKE,  _DF_111): ["subsurface_interlayer_hop",
                                "subsurface_migration_interlayer"],
    (_SC_SURFACE,    _DF_001): ["surface_subsurface_exchange_down",
                                "surface_subsurface_exchange_up"],
    (_SC_SUBSURFACE, _DF_001): ["subsurface_migration_interlayer"],
    (_SC_BULK_LIKE,  _DF_001): ["subsurface_migration_interlayer"],
}


def _motif_of(class_idx: int, dir_idx: int) -> int:
    if class_idx == _SC_SURFACE:
        if dir_idx == _DF_110:  return MF_SURFACE_1NN
        if dir_idx == _DF_100:  return MF_SURFACE_2NN
        if dir_idx == _DF_111:  return MF_SURF_SUBSURF_EXCHANGE
        if dir_idx == _DF_001:  return MF_SUBSURFACE_EXCHANGE
        return MF_UNRESOLVED
    if class_idx == _SC_SUBSURFACE:
        if dir_idx == _DF_110:  return MF_SUBSURFACE_1NN
        if dir_idx == _DF_111:  return MF_INTERLAYER
        if dir_idx == _DF_001:  return MF_SUBSURFACE_EXCHANGE
        return MF_UNRESOLVED
    if class_idx == _SC_BULK_LIKE:
        if dir_idx == _DF_110:  return MF_SUBSURFACE_1NN
        if dir_idx == _DF_111:  return MF_INTERLAYER
        if dir_idx == _DF_001:  return MF_SUBSURFACE_EXCHANGE
        return MF_UNRESOLVED
    return MF_UNRESOLVED


def _motif_lookup_table() -> list[int]:
    """Flat [SC_COUNT * DF_COUNT] motif-per-(class, dir) table for the header."""
    n_classes, n_dirs = len(CLASS_MAP), len(DIR_MAP)
    out = [MF_UNRESOLVED] * (n_classes * n_dirs)
    for ci in range(n_classes):
        for di in range(n_dirs):
            out[ci * n_dirs + di] = _motif_of(ci, di)
    return out


# ------------------------------------------------------------------
# Dataframe preparation
# ------------------------------------------------------------------
def _prepare_dataframe(df: pd.DataFrame, spec: ModelSpec) -> pd.DataFrame:
    """Select accepted events and add integer key columns per axis."""
    df = df[df["assignment_status"] == "accepted"].copy()

    df["_sc"] = df["site_class_3d"].map(CLASS_MAP)
    df["_dir"] = df["direction_family_3d"].map(DIR_MAP)
    df = df.dropna(subset=["_sc", "_dir"])

    species_noVacant = spec.species[1:]
    mover_map = {name: i for i, name in enumerate(species_noVacant)}
    if spec.has_mover_species_axis():
        df["_mover"] = df["mover_species_ml"].map(mover_map)
        df = df.dropna(subset=["_mover"])

    # Derive missing vacancy counts that the CSV doesn't carry directly.
    # n_vac_nn1 is in the CSV; n_vac_nn2 we derive from shell-size arithmetic.
    if any(a.kind == "count" and a.shell == "nn1" and a.match == "vac"
           for a in spec.key.axes):
        df["_n_vac_nn1"] = df["n_vac_nn1_initial"].clip(lower=0)
    if any(a.kind == "count" and a.shell == "nn2" and a.match == "vac"
           for a in spec.key.axes):
        occupied_nn2 = (
            df["nn2_count_Ni"].fillna(0)
            + df["nn2_count_Fe"].fillna(0)
            + df["nn2_count_Cr"].fillna(0)
        )
        df["_n_vac_nn2"] = (_NN2_SHELL_SIZE - occupied_nn2).clip(lower=0)

    # Build the per-axis integer key column, clipped to the axis max.
    for axis in spec.key.axes:
        if axis.kind == "count":
            src = (
                f"_n_vac_{axis.shell}"
                if axis.match == "vac"
                else f"{axis.shell}_count_{axis.match}"
            )
            df[f"_{axis.name}"] = df[src].fillna(0).clip(upper=axis.max - 1)

    # Coerce all key cols to int once.
    col_names = ["_sc", "_dir"]
    for a in spec.key.axes:
        col_names.append("_mover" if a.name == "mover_species" else f"_{a.name}")
    for c in col_names:
        df[c] = df[c].astype(int)
    return df


def _key_cols(spec: ModelSpec) -> list[str]:
    cols = ["_sc", "_dir"]
    for a in spec.key.axes:
        cols.append("_mover" if a.name == "mover_species" else f"_{a.name}")
    return cols


# ------------------------------------------------------------------
# Tier 2: element-drop fallback
# ------------------------------------------------------------------
def _apply_tier2_fallback(
    cube_rate: np.ndarray, cube_Ea: np.ndarray, spec: ModelSpec,
    drop_order: list[str] = _TIER2_DROP_ORDER,
) -> int:
    """For each axis in drop_order, copy the axis=0 slice across the axis
    into any cells that are still NaN. Returns the number of cells filled."""
    axis_names_all = [n for n, _ in spec.all_axes()]
    n_filled_here = 0
    for drop_name in drop_order:
        if drop_name not in axis_names_all:
            continue
        di = axis_names_all.index(drop_name)
        donor_rate = cube_rate.take(0, axis=di)
        donor_Ea = cube_Ea.take(0, axis=di)
        donor_rate_bcast = np.broadcast_to(
            np.expand_dims(donor_rate, di), cube_rate.shape
        )
        donor_Ea_bcast = np.broadcast_to(
            np.expand_dims(donor_Ea, di), cube_Ea.shape
        )
        mask = np.isnan(cube_rate) & ~np.isnan(donor_rate_bcast)
        n_filled_here += int(mask.sum())
        cube_rate[mask] = donor_rate_bcast[mask]
        cube_Ea[mask] = donor_Ea_bcast[mask]
    return n_filled_here


# ------------------------------------------------------------------
# Tier 5: cross-class fallback (surface ↔ subsurface ↔ bulk_like)
# ------------------------------------------------------------------
def _apply_cross_class_fallback(
    cube_rate: np.ndarray, cube_Ea: np.ndarray, spec: ModelSpec,
) -> int:
    """For each recipient site_class that has NaN cells, borrow values from
    its donor classes at the same (direction, ...rest) key. Donor order is
    _CROSS_CLASS_DONORS[recipient]; first donor with data wins, per cell.

    Works on cube views (reshaped rate/Ea arrays) — modifies in place.
    Returns number of cells newly filled.
    """
    axis_names = [n for n, _ in spec.all_axes()]
    sc_ax = axis_names.index("site_class")
    assert sc_ax == 0, "site_class must be axis 0 (first permanent axis)"

    n_filled_total = 0
    for recipient, donors in _CROSS_CLASS_DONORS.items():
        recipient_rate = cube_rate[recipient]
        recipient_Ea = cube_Ea[recipient]
        for donor in donors:
            donor_rate = cube_rate[donor]
            donor_Ea = cube_Ea[donor]
            # Fill cells that are NaN in recipient AND not-NaN in donor.
            mask = np.isnan(recipient_rate) & ~np.isnan(donor_rate)
            n_here = int(mask.sum())
            if n_here == 0:
                continue
            recipient_rate[mask] = donor_rate[mask]
            recipient_Ea[mask] = donor_Ea[mask]
            n_filled_total += n_here
    return n_filled_total


# ------------------------------------------------------------------
# Tier 6: family-BUCKET barrier fallback
# ------------------------------------------------------------------
#
# The family catalogue buckets events by the MOVING atom's nv1 count (i.e.
# number of vacant 1NN of the atom about to hop). Our cube's `n_vac_nn1`
# axis is the VACANCY's nv1 count (number of vacant 1NN of the empty site).
#
# For single-vacancy 1NN hops on FCC, the mover is a 1NN of the vacancy, so:
#     mover_nv1 = vacancy_n_vac_nn1 + 1     (the mover sees the vacancy it
#                                             moves into, plus whatever other
#                                             vacancies surround the vacancy.)
#
# This means a cube cell with n_vac_nn1=0 (isolated vacancy) must be filled
# only if the family has a bucket at nv1=1 — NOT at nv1=4..8 which represent
# multi-vacancy clusters. Filling indiscriminately across buckets would inject
# kinetics the training data doesn't actually support at low vacancy density.
_MOVER_NV1_OFFSET = 1


def _load_family_bucket_barriers(
    family_csv: Path,
) -> dict[str, dict[tuple[int, int], float]]:
    """Load `rate_lookup_table_family.csv` and return
    {family_id: {(mover_nv1, mover_nv2): Ea_mean_eV}}.

    Bucket id formats supported:
      - 'nv1=<N>'              -> key (N, -1) — nv2 unspecified ("any")
      - 'nv1=<N>_nv2=<M>'      -> key (N, M)  — both axes specified
      - 'li=<L>_nv1=<N>'       -> key (N, -1) — li prefix is ignored
      - '*'                     -> key (-1, -1) — universal bucket

    Two-axis buckets enable separation of isolated (nv2=0) from clustered
    (nv2>=1) environments, fixing the pylatkmc MSD overshoot.
    """
    if not family_csv.is_file():
        return {}
    ft = pd.read_csv(family_csv)
    if "n_events" not in ft.columns or "Ea_mean_eV" not in ft.columns:
        return {}
    ft = ft.copy()
    ft["n_events"] = pd.to_numeric(ft["n_events"], errors="coerce").fillna(0)
    ft["Ea_mean_eV"] = pd.to_numeric(ft["Ea_mean_eV"], errors="coerce")
    ft = ft[(ft["n_events"] > 0) & ft["Ea_mean_eV"].notna()]
    if "source_filter" in ft.columns:
        ft = ft[~ft["source_filter"].astype(str).str.startswith("excluded:")]
    if ft.empty:
        return {}

    def _parse_bucket(b: str) -> tuple[int, int] | None:
        """Return (nv1, nv2) for a bucket id, with -1 meaning unspecified.
        '*' -> (-1, -1)."""
        if b == "*":
            return (-1, -1)
        s = pd.Series([b])
        m1 = s.str.extract(r"nv1=(\d+)").iloc[0, 0]
        m2 = s.str.extract(r"nv2=(\d+)").iloc[0, 0]
        if pd.isna(m1):
            return None
        try:
            nv1 = int(m1)
            nv2 = int(m2) if not pd.isna(m2) else -1
            return (nv1, nv2)
        except (TypeError, ValueError):
            return None

    out: dict[str, dict[tuple[int, int], float]] = {}
    for fid, sub in ft.groupby("family_id"):
        per_bucket: dict[tuple[int, int], list[tuple[float, float]]] = {}
        for _, row in sub.iterrows():
            key = _parse_bucket(str(row["family_bucket_id"]))
            if key is None:
                continue
            per_bucket.setdefault(key, []).append(
                (float(row["Ea_mean_eV"]), float(row["n_events"]))
            )
        buckets: dict[tuple[int, int], float] = {}
        for key, rows in per_bucket.items():
            Eas = np.array([r[0] for r in rows])
            ws = np.array([r[1] for r in rows])
            buckets[key] = float(np.average(Eas, weights=ws))

        # If the family is exclusively 2-axis bucketed, derive a 1-axis
        # "any nv2" fallback per nv1 by event-weighted averaging across nv2
        # values. Lets tier 6 still cover (nv1, nv2) cube cells where a
        # specific 2-axis bucket doesn't exist in the catalogue.
        per_nv1: dict[int, list[tuple[float, float]]] = {}
        for (nv1, nv2), rows in per_bucket.items():
            if nv1 < 0:   # skip universal '*'
                continue
            for Ea, n in rows:
                per_nv1.setdefault(nv1, []).append((Ea, n))
        for nv1, rows in per_nv1.items():
            if (nv1, -1) in buckets:
                continue
            Eas = np.array([r[0] for r in rows])
            ws = np.array([r[1] for r in rows])
            buckets[(nv1, -1)] = float(np.average(Eas, weights=ws))

        if buckets:
            out[str(fid)] = buckets
    return out


def _apply_tier6_family(
    cube_rate: np.ndarray, cube_Ea: np.ndarray, spec: ModelSpec,
    family_barriers: dict[str, dict[int, float]],
    kT_eV: float, k0_Hz: float,
) -> tuple[int, dict[tuple[int, int], str]]:
    """For each (site_class, direction) slab, fill NaN cells at cube n_vac_nn1=V
    from the family's bucket at nv1=V+_MOVER_NV1_OFFSET (the mover's perspective).

    Cells where the family has no matching bucket stay NaN — on purpose, to
    avoid injecting kinetics the training data doesn't support. The '*'
    universal bucket (only in `unresolved_multisite`) is NOT auto-applied here
    because it would over-fill legitimate cells.

    Returns (n_cells_filled, {(sc, dir): family_id_used}).
    """
    axis_names = [n for n, _ in spec.all_axes()]
    assert axis_names[0] == "site_class" and axis_names[1] == "direction"

    # Axis indices for the vacancy-perspective vacancy counts.
    try:
        nvac1_ax = axis_names.index("n_vac_nn1")
    except ValueError:
        return 0, {}   # no such axis → tier 6 has nothing to do
    nvac2_ax = axis_names.index("n_vac_nn2") if "n_vac_nn2" in axis_names else None

    nvac1_max = cube_rate.shape[nvac1_ax]
    nvac2_max = cube_rate.shape[nvac2_ax] if nvac2_ax is not None else 1
    n_filled_total = 0
    used_per_slab: dict[tuple[int, int], str] = {}
    for (sc_i, dir_i), candidates in _SC_DIR_TO_FAMILIES.items():
        for fid in candidates:
            buckets = family_barriers.get(fid)
            if not buckets:
                continue
            any_filled_here = False
            # Per cube cell at (n_vac_nn1=v1, n_vac_nn2=v2), prefer a 2-axis
            # bucket at (mover_nv1=v1+1, mover_nv2=v2). Fall back to the 1-axis
            # bucket (nv1=v1+1, nv2=-1) if no 2-axis match exists.
            for v1 in range(nvac1_max):
                mover_nv1 = v1 + _MOVER_NV1_OFFSET
                # Pre-extract any 1-axis fallback Ea for this nv1
                fallback_Ea = buckets.get((mover_nv1, -1))
                for v2 in range(nvac2_max):
                    Ea_val = buckets.get((mover_nv1, v2), fallback_Ea)
                    if Ea_val is None:
                        continue
                    slicer: list[slice | int] = [slice(None)] * cube_rate.ndim
                    slicer[0] = sc_i
                    slicer[1] = dir_i
                    slicer[nvac1_ax] = v1
                    if nvac2_ax is not None:
                        slicer[nvac2_ax] = v2
                    sub_rate = cube_rate[tuple(slicer)]
                    sub_Ea = cube_Ea[tuple(slicer)]
                    mask = np.isnan(sub_rate)
                    n_here = int(mask.sum())
                    if n_here == 0:
                        continue
                    fill_rate = np.float32(k0_Hz * math.exp(-Ea_val / kT_eV))
                    sub_rate[mask] = fill_rate
                    sub_Ea[mask] = np.float32(Ea_val)
                    n_filled_total += n_here
                    any_filled_here = True
            if any_filled_here:
                used_per_slab[(sc_i, dir_i)] = fid
                break   # primary candidate worked; don't fall through
    return n_filled_total, used_per_slab


# ------------------------------------------------------------------
# Tier 7: scalar legacy fallback (<110>_inplane only)
# ------------------------------------------------------------------
def _apply_tier7_scalar(
    cube_rate: np.ndarray, cube_Ea: np.ndarray, spec: ModelSpec,
    scalar_csv: Path, kT_eV: float, k0_Hz: float,
) -> int:
    """Load the legacy scalar table and fill any still-empty <110>_inplane
    cells with its barrier, keyed only on n_vacant_inplane_nn (our
    n_vac_nn1). Returns cells newly filled."""
    if not scalar_csv.is_file():
        return 0
    legacy = pd.read_csv(scalar_csv)
    # Legacy columns are historically named n_vacant_inplane_nn and Ea_mean_eV.
    if "n_vacant_inplane_nn" not in legacy.columns or "Ea_mean_eV" not in legacy.columns:
        return 0
    # Build a small lookup {n_vac: Ea}.
    n_vac_to_Ea: dict[int, float] = {}
    for _, row in legacy.iterrows():
        try:
            n_vac_to_Ea[int(row["n_vacant_inplane_nn"])] = float(row["Ea_mean_eV"])
        except (ValueError, KeyError):
            continue
    if not n_vac_to_Ea:
        return 0

    # Index into the cube. Only touch cells with direction=<110>_inplane.
    axis_names_all = [n for n, _ in spec.all_axes()]
    dir_ax = axis_names_all.index("direction")
    nvac1_ax = (
        axis_names_all.index("n_vac_nn1") if "n_vac_nn1" in axis_names_all else None
    )
    if nvac1_ax is None:
        return 0

    n_filled = 0
    # Build an axis-slicer; take dir=DF_110 and then iterate n_vac values.
    # Use np.take to slice; the result is a view.
    cube_shape = cube_rate.shape
    for n_vac_val, Ea_val in n_vac_to_Ea.items():
        if n_vac_val < 0 or n_vac_val >= cube_shape[nvac1_ax]:
            continue
        # Build a full-cube mask: direction == DF_110 AND n_vac_nn1 == n_vac_val AND rate is nan
        idx_arrays: list[np.ndarray] = []
        # We do this by iterating positions along other axes with np.ndindex.
        # Efficient: index the cube via multidim mask.
        # Create a boolean mask that is True along dir=DF_110 and n_vac=n_vac_val.
        dir_selector = [slice(None)] * cube_rate.ndim
        dir_selector[dir_ax] = _DF_110
        dir_selector[nvac1_ax] = n_vac_val
        sub_rate = cube_rate[tuple(dir_selector)]
        sub_Ea = cube_Ea[tuple(dir_selector)]
        local_mask = np.isnan(sub_rate)
        n_filled += int(local_mask.sum())
        fill_rate = np.float32(k0_Hz * np.exp(-Ea_val / kT_eV))
        sub_rate[local_mask] = fill_rate
        sub_Ea[local_mask] = np.float32(Ea_val)
    return n_filled


# ------------------------------------------------------------------
# Binary writer
# ------------------------------------------------------------------
def _build_header(spec: ModelSpec) -> dict[str, object]:
    axes = spec.all_axes()
    return {
        "model_name":    spec.name,
        "n_axes":        len(axes),
        "n_entries":     int(spec.n_cube_entries()),
        "temperature_K": float(spec.rate_data.temperature_K),
        "k0_Hz":         float(spec.rate_data.k0_Hz),
        "strides":       [int(s) for s in spec.strides()],
        "axis_maxes":    [int(m) for _, m in axes],
        "axis_names":    [n for n, _ in axes],
        "motif_of_class_dir": _motif_lookup_table(),
        "version":       3,
    }


def _write_kmcrt(
    spec: ModelSpec, rate: np.ndarray, Ea: np.ndarray,
    count: np.ndarray, out_path: Path,
) -> None:
    header = _build_header(spec)
    n = rate.size
    assert Ea.size == n and count.size == n, "rate/Ea/count size mismatch"
    with open(out_path, "wb") as fp:
        write_header(fp, RATETABLE_MAGIC, header)
        fp.write(struct.pack("<I", n))
        fp.write(rate.astype("<f4").tobytes(order="C"))
        fp.write(Ea.astype("<f4").tobytes(order="C"))
        fp.write(count.astype("<u4").tobytes(order="C"))


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def build(
    spec: ModelSpec,
    classified_csv: str | Path,
    out_path: str | Path,
    scalar_csv: str | Path | None = None,
    family_csv: str | Path | None = None,
    verbose: bool = True,
) -> BuildStats:
    """Build the .kmcrt binary for `spec`, drawing barrier data from
    `classified_csv` (the curated catalogue) with optional scalar and
    family-table fallbacks."""
    classified_csv = Path(classified_csv)
    out_path = Path(out_path)
    scalar_path = Path(scalar_csv) if scalar_csv else None
    family_path = Path(family_csv) if family_csv else None

    # --- Ingest + prepare ---
    df = pd.read_csv(classified_csv)
    n_total = len(df)
    df = _prepare_dataframe(df, spec)
    n_keyable = len(df)

    # --- Tier 1: direct aggregation ---
    key_cols = _key_cols(spec)
    agg = (
        df.groupby(key_cols, as_index=False)
        .agg(
            Ea_mean=("energy_barrier", "mean"),
            n_events=("energy_barrier", "size"),
        )
    )

    axes = spec.all_axes()
    axis_maxes = [m for _, m in axes]
    n_entries = int(spec.n_cube_entries())
    kT = K_B_EV_PER_K * spec.rate_data.temperature_K
    k0 = spec.rate_data.k0_Hz

    rate = np.full(n_entries, np.nan, dtype=np.float32)
    Ea = np.full(n_entries, np.nan, dtype=np.float32)
    count = np.zeros(n_entries, dtype=np.uint32)

    strides = np.array(spec.strides(), dtype=np.int64)
    key_arr = agg[key_cols].values.astype(np.int64)
    idx = (key_arr * strides).sum(axis=1)

    rate[idx] = (k0 * np.exp(-agg["Ea_mean"].values / kT)).astype(np.float32)
    Ea[idx] = agg["Ea_mean"].values.astype(np.float32)
    count[idx] = agg["n_events"].values.astype(np.uint32)
    n_tier1 = int(np.isfinite(rate).sum())

    # --- Tier 2: element-drop fallback (operates on reshaped cube view) ---
    cube_rate = rate.reshape(axis_maxes)
    cube_Ea = Ea.reshape(axis_maxes)
    n_tier2 = _apply_tier2_fallback(cube_rate, cube_Ea, spec)

    # --- Tier 5: cross-class borrow (surface ↔ subsurface ↔ bulk_like) ---
    n_tier5 = _apply_cross_class_fallback(cube_rate, cube_Ea, spec)

    # --- Tier 6: family-BUCKET-matched barrier ---
    n_tier6 = 0
    family_used: dict[tuple[int, int], str] = {}
    if family_path is not None:
        family_buckets = _load_family_bucket_barriers(family_path)
        if family_buckets:
            n_tier6, family_used = _apply_tier6_family(
                cube_rate, cube_Ea, spec, family_buckets, kT, k0,
            )

    # --- Tier 7: scalar legacy (last resort) ---
    n_tier7 = 0
    if scalar_path is not None:
        n_tier7 = _apply_tier7_scalar(cube_rate, cube_Ea, spec, scalar_path, kT, k0)

    n_filled = int(np.isfinite(cube_rate).sum())

    # NaN cells are forced to zero rate (events skipped at runtime).
    cube_rate[np.isnan(cube_rate)] = np.float32(0.0)
    cube_Ea[np.isnan(cube_Ea)] = np.float32(0.0)

    # Per-slab coverage (useful for the `pylatkmc-gen provenance` report).
    slab_coverage: dict[tuple[int, int], float] = {}
    for sc_i in range(cube_rate.shape[0]):
        for dir_i in range(cube_rate.shape[1]):
            slab = cube_rate[sc_i, dir_i]
            slab_coverage[(sc_i, dir_i)] = float((slab > 0).mean())

    stats = BuildStats(
        n_rows_total=n_total,
        n_rows_accepted=len(df),
        n_rows_keyable=n_keyable,
        n_cells_total=n_entries,
        n_cells_tier1=n_tier1,
        n_cells_tier2=n_tier2,
        n_cells_tier5=n_tier5,
        n_cells_tier6=n_tier6,
        n_cells_tier7=n_tier7,
        n_cells_filled=n_filled,
        tier6_family_used=family_used,
        slab_coverage=slab_coverage,
    )

    _write_kmcrt(spec, rate, Ea, count, out_path)
    if verbose:
        print(f"ratebuilder: wrote {out_path} ({n_entries:,} entries)")
        print(f"  rows:   {n_total:,} total  →  {n_keyable:,} keyable")
        print(f"  tier 1: {n_tier1:,} cells filled ({stats.as_dict()['pct_tier1']}%)")
        print(f"  tier 2: {n_tier2:,} additional cells (element drops)")
        print(f"  tier 5: {n_tier5:,} additional cells (cross-class borrow)")
        if family_path is not None:
            print(f"  tier 6: {n_tier6:,} additional cells (family-averaged)")
        if scalar_path is not None:
            print(f"  tier 7: {n_tier7:,} additional cells (scalar <110> fallback)")
        print(f"  total:  {n_filled:,} filled / {n_entries:,} = "
              f"{stats.as_dict()['pct_filled']}%")
    return stats
