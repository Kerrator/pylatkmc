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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from .processes import Action, Bystander, Condition, CoordOffset, Process
from .rate_expression import arrhenius_scalar, bucket_warns_on_scatter

# ---------------------------------------------------------------------------
# Catalogue row type — keeps translator independent of pandas
# ---------------------------------------------------------------------------


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

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "FamilyBucketRow":
        return cls(
            family_id=row["family_id"].strip(),
            family_bucket_id=row["family_bucket_id"].strip(),
            n_events=int(row["n_events"]),
            Ea_mean_eV=float(row["Ea_mean_eV"]),
            Ea_std_eV=float(row["Ea_std_eV"]),
            Ea_min_eV=float(row["Ea_min_eV"]),
            Ea_max_eV=float(row["Ea_max_eV"]),
        )


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
# Direction sets per family
# ---------------------------------------------------------------------------

# FCC(100) surface 1NN in-plane: 4 directions (±x, ±y) in the cubic
# integer basis. The runtime's CSR neighbour list resolves these to
# concrete site indices via `nn1_offsets`/`nn1_indices`.
SURFACE_1NN_INPLANE_DIRS: tuple[CoordOffset, ...] = (
    CoordOffset(di=+1, dj=0, dk=0, sublattice="a"),
    CoordOffset(di=-1, dj=0, dk=0, sublattice="a"),
    CoordOffset(di=0, dj=+1, dk=0, sublattice="a"),
    CoordOffset(di=0, dj=-1, dk=0, sublattice="a"),
)

# FCC bulk 1NN: 12 directions in the cubic basis (face-centered).
BULK_1NN_DIRS: tuple[CoordOffset, ...] = tuple(
    CoordOffset(di=di, dj=dj, dk=dk, sublattice="a")
    for di, dj, dk in [
        # In-plane (4)
        (+1, 0, 0), (-1, 0, 0), (0, +1, 0), (0, -1, 0),
        # Up-cross-layer (4)
        (+1, 0, +1), (-1, 0, +1), (0, +1, +1), (0, -1, +1),
        # Down-cross-layer (4)
        (+1, 0, -1), (-1, 0, -1), (0, +1, -1), (0, -1, -1),
    ]
)

# FCC(100) surface 2NN: 4 in-plane diagonal directions.
SURFACE_2NN_DIRS: tuple[CoordOffset, ...] = tuple(
    CoordOffset(di=di, dj=dj, dk=0, sublattice="a")
    for di, dj in [(+1, +1), (+1, -1), (-1, +1), (-1, -1)]
)

# FCC bulk 2NN: 6 cubic axial directions.
BULK_2NN_DIRS: tuple[CoordOffset, ...] = tuple(
    CoordOffset(di=di, dj=dj, dk=dk, sublattice="a")
    for di, dj, dk in [
        (+2, 0, 0), (-2, 0, 0),
        (0, +2, 0), (0, -2, 0),
        (0, 0, +2), (0, 0, -2),
    ]
)

# Cross-layer 1NN directions (used by interlayer-hop families).
INTERLAYER_1NN_DIRS_UP: tuple[CoordOffset, ...] = tuple(
    CoordOffset(di=di, dj=dj, dk=+1, sublattice="a")
    for di, dj in [(+1, 0), (-1, 0), (0, +1), (0, -1)]
)
INTERLAYER_1NN_DIRS_DOWN: tuple[CoordOffset, ...] = tuple(
    CoordOffset(di=di, dj=dj, dk=-1, sublattice="a")
    for di, dj in [(+1, 0), (-1, 0), (0, +1), (0, -1)]
)


# ---------------------------------------------------------------------------
# Process emission helpers
# ---------------------------------------------------------------------------

ANCHOR = CoordOffset(di=0, dj=0, dk=0, sublattice="a")


def _safe_name(*parts: str) -> str:
    """Build a valid C identifier from string parts. Lower-cases everything,
    replaces non-alphanumerics with `_`."""
    raw = "__".join(str(p) for p in parts)
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw).lower()
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


def _direction_label(d: CoordOffset) -> str:
    """Stable label for a CoordOffset, used in Process names."""
    sign = lambda v: "p" if v >= 0 else "m"  # noqa: E731
    return f"{sign(d.di)}{abs(d.di)}{sign(d.dj)}{abs(d.dj)}{sign(d.dk)}{abs(d.dk)}{d.sublattice}"


def _emit_simple_2action_hop(
    family_id: str,
    bucket_id: str,
    direction: CoordOffset,
    mover_species: str,
    Ea_eV: float,
    rate_Hz: float,
) -> Process:
    """A single-atom 1NN/2NN hop: vacancy at anchor + mover at direction →
    swap. Two Conditions, two Actions, no Bystanders."""
    return Process(
        name=_safe_name(family_id, bucket_id, _direction_label(direction), mover_species),
        family_id=family_id,
        Ea_eV=Ea_eV,
        rate_constant=float(rate_Hz),
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=direction, species=mover_species),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after=mover_species),
            Action(coord=direction, before=mover_species, after="Vacant"),
        ),
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
    on_scatter_warn: Optional[Callable[[str], None]] = None,
) -> list[Process]:
    """Translate any "single-atom hop" family (surface/subsurface/bulk
    1NN/2NN inplane, interlayer hops, etc.) into Processes.

    Emits one Process per (bucket × direction). The bucket's Ea_mean
    becomes the Arrhenius rate at the spec's T.
    """
    family_rows = [r for r in rows if r.family_id == family_id]
    out: list[Process] = []
    for r in family_rows:
        if msg := bucket_warns_on_scatter(r.Ea_std_eV, r.n_events):
            if on_scatter_warn is not None:
                on_scatter_warn(
                    f"{family_id}/{r.family_bucket_id} ({r.n_events} events): {msg}"
                )
        rate = arrhenius_scalar(Ea_eV=r.Ea_mean_eV, k0_Hz=k0_Hz, T_K=T_K)
        for d in directions:
            out.append(
                _emit_simple_2action_hop(
                    family_id=family_id,
                    bucket_id=r.family_bucket_id,
                    direction=d,
                    mover_species=mover_species,
                    Ea_eV=r.Ea_mean_eV,
                    rate_Hz=rate,
                )
            )
    return out


def translate_surface_1NN_inplane(
    rows: list[FamilyBucketRow],
    k0_Hz: float = 1.0e13,
    T_K: float = 500.0,
    mover_species: str = "Ni",
    on_scatter_warn: Optional[Callable[[str], None]] = None,
) -> list[Process]:
    """FCC(100) surface 1NN in-plane: 4 dirs/bucket. ~35k catalogue events."""
    return translate_simple_hop_family(
        rows, "surface_1NN_inplane", SURFACE_1NN_INPLANE_DIRS,
        mover_species, k0_Hz, T_K, on_scatter_warn,
    )


# ---------------------------------------------------------------------------
# Per-family translators — table-driven dispatch
# ---------------------------------------------------------------------------

# Maps `family_id` → directions to emit Processes for. All families in this
# table use the simple 2-action swap (anchor ↔ direction), differing only
# in which neighbour-shell directions apply.
_FAMILY_DIRECTIONS: dict[str, tuple[CoordOffset, ...]] = {
    "surface_1NN_inplane":             SURFACE_1NN_INPLANE_DIRS,        # 4
    "subsurface_1NN_inplane":          BULK_1NN_DIRS,                   # 12
    "bulk_1NN_inplane":                BULK_1NN_DIRS,                   # 12
    "surface_2NN_diagonal":            SURFACE_2NN_DIRS,                # 4
    "subsurface_2NN_diagonal":         BULK_2NN_DIRS,                   # 6
    "surface_interlayer_hop":          INTERLAYER_1NN_DIRS_DOWN,        # 4 (surface→subsurface)
    "subsurface_interlayer_hop":       INTERLAYER_1NN_DIRS_UP + INTERLAYER_1NN_DIRS_DOWN,  # 8
    "surface_subsurface_exchange_up":  INTERLAYER_1NN_DIRS_UP,          # 4
    "surface_subsurface_exchange_down": INTERLAYER_1NN_DIRS_DOWN,       # 4
    "surface_subsurface_exchange_lateral": INTERLAYER_1NN_DIRS_UP + INTERLAYER_1NN_DIRS_DOWN,
    "subsurface_migration_axial":      BULK_1NN_DIRS,                   # 12
    "subsurface_migration_interlayer": INTERLAYER_1NN_DIRS_UP + INTERLAYER_1NN_DIRS_DOWN,  # 8
}

# Multi-site families with fit_barrier=False — visibility only, skip in v2.
# These come into the catalogue with NaN Ea so load_family_rate_table()
# already filters them out, but we list them here to be explicit.
_FAMILIES_SKIPPED: frozenset[str] = frozenset({
    "concerted_multisite",
    "unresolved_multisite",
})


def translate_all(
    rows: list[FamilyBucketRow],
    k0_Hz: float = 1.0e13,
    T_K: float = 500.0,
    mover_species: str = "Ni",
    on_scatter_warn: Optional[Callable[[str], None]] = None,
    on_unknown_family: Optional[Callable[[str], None]] = None,
) -> list[Process]:
    """Translate every supported family in the catalogue into Processes.

    Iterates `_FAMILY_DIRECTIONS` and dispatches each to
    translate_simple_hop_family. Unknown family_ids in the catalogue
    (i.e. families not in `_FAMILY_DIRECTIONS` and not in
    `_FAMILIES_SKIPPED`) are reported via `on_unknown_family` and
    skipped.

    Returns a deduplicated, name-unique list[Process].
    """
    out: list[Process] = []

    families_in_catalogue = {r.family_id for r in rows}
    known = set(_FAMILY_DIRECTIONS.keys()) | _FAMILIES_SKIPPED
    unknown = families_in_catalogue - known
    for fid in sorted(unknown):
        if on_unknown_family is not None:
            on_unknown_family(fid)

    for fid in sorted(_FAMILY_DIRECTIONS.keys()):
        out.extend(translate_simple_hop_family(
            rows=rows,
            family_id=fid,
            directions=_FAMILY_DIRECTIONS[fid],
            mover_species=mover_species,
            k0_Hz=k0_Hz,
            T_K=T_K,
            on_scatter_warn=on_scatter_warn,
        ))

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
    "translate_all",
)
