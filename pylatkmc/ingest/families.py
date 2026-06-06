"""Curated FCC event-family registry for the on-lattice KMC rate table.

Phase 1 of the curated-catalogue pivot: every row of classified_events.csv is
mapped to exactly one named FCC movement family plus a family-specific
environment bucket. The registry is declarative so a human can audit and
iterate on it without editing the base classifier.

Upstream: `lattice_map_events.py` + `lattice_3d.py` already assign
`move_type`, `motif_family_3d`, `direction_family_3d`, `site_class_3d`, and
`surface_layer_initial/final` per event. Families seed from those columns —
we do NOT redesign the base geometry classifier here.

Downstream: `build_family_rate_table.py` aggregates barriers over accepted
audit rows per (family_id, family_bucket_id).

To iterate on the registry:
  1. Run `build_family_rate_table.py`.
  2. Inspect `family_assignment_report.json` → `unresolved_signatures`.
  3. Either add a new family for the dominant unresolved pattern, or extend
     an existing seed_rule. Re-run.

See the curated family catalogue design notes for the full rationale.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import pandas as pd

Predicate = Callable[[pd.Series], bool]
BucketFn  = Callable[[pd.Series], str]


@dataclass(frozen=True)
class FCCFamily:
    family_id: str                          # stable machine-readable id
    family_name: str                        # human label for plots/tables
    movement_template: str                  # short description (<110>_inplane 1NN, etc.)
    seed_rule: Predicate
    environment_rule: BucketFn
    priority: int                           # lower = checked first
    fit_barrier: bool                       # False for multisite/unresolved
    review_notes: str                       # rationale + known coverage gaps


# ── Seed predicate helpers ──────────────────────────────────────────────────

def _s(col: str, eq) -> Predicate:
    """eq: single value or iterable of allowed values."""
    if isinstance(eq, (list, tuple, set, frozenset)):
        allowed = frozenset(eq)
        return lambda r, c=col, a=allowed: r.get(c) in a
    return lambda r, c=col, v=eq: r.get(c) == v


def _all(*preds: Predicate) -> Predicate:
    return lambda r: all(p(r) for p in preds)


# ── Environment-rule helpers ────────────────────────────────────────────────

def _bucket_by_n_vac_nn1(r: pd.Series) -> str:
    try:
        n = int(r.get("n_vac_nn1_initial"))
    except (TypeError, ValueError):
        return "nv1=?"
    return f"nv1={n}"


def _bucket_by_n_vac_1nn_and_2nn(r: pd.Series) -> str:
    """Richer env for bulk-like hops — both 1NN and 2NN vacancy counts."""
    try:
        n1 = int(r.get("n_vac_nn1_initial"))
    except (TypeError, ValueError):
        n1 = -1
    # 2NN count isn't a Stage-1f descriptor today; fall back to -1 when missing.
    n2_raw = r.get("n_vac_nn2_initial", None)
    try:
        n2 = int(n2_raw) if n2_raw is not None and str(n2_raw) != "nan" else -1
    except (TypeError, ValueError):
        n2 = -1
    return f"nv1={n1}_nv2={n2}" if n2 >= 0 else f"nv1={n1}"


def _bucket_by_layer_initial(r: pd.Series) -> str:
    """For interlayer hops: the starting layer governs barrier more than
    whether surface_layer_final is top."""
    try:
        n = int(r.get("n_vac_nn1_initial"))
    except (TypeError, ValueError):
        n = -1
    try:
        li = int(r.get("surface_layer_initial"))
    except (TypeError, ValueError):
        li = -1
    return f"li={li}_nv1={n}"


def _bucket_by_n_moved(r: pd.Series) -> str:
    try:
        n = int(r.get("n_moved"))
    except (TypeError, ValueError):
        return "n_moved=?"
    # Collapse the long tail — most concerted events have n_moved in {2, 3, 4, 5+}.
    if n >= 5:
        return "n_moved=5+"
    return f"n_moved={n}"


def _bucket_all(r: pd.Series) -> str:
    return "any"


# ── The registry ────────────────────────────────────────────────────────────

FAMILY_REGISTRY: list[FCCFamily] = [
    FCCFamily(
        family_id="surface_1NN_inplane",
        family_name="Surface 1NN in-plane hop",
        movement_template="<110>_inplane, single-atom, vacancy at surface layer",
        seed_rule=_all(
            _s("motif_family_3d", "surface_1nn_translation"),
            _s("direction_family_3d", "<110>_inplane"),
            _s("site_class_3d", "surface"),
        ),
        environment_rule=_bucket_by_n_vac_1nn_and_2nn,
        priority=0,
        fit_barrier=True,
        review_notes="Dominant mechanism in surface-originated training data. "
                     "39k events in current catalogue. Two-axis (nv1, nv2) "
                     "bucketing separates isolated vacancies (nv2=0) from "
                     "clustered (nv2>=1) — fixes the pylatkmc MSD overshoot "
                     "documented in docs/pylatkmc_msd_diagnosis.md.",
    ),
    FCCFamily(
        family_id="subsurface_1NN_inplane",
        family_name="Subsurface 1NN in-plane hop",
        movement_template="<110>_inplane, single-atom, vacancy at subsurface (top-1) layer",
        seed_rule=_all(
            _s("motif_family_3d", "subsurface_1nn_translation"),
            _s("direction_family_3d", "<110>_inplane"),
            _s("site_class_3d", "subsurface"),
        ),
        environment_rule=_bucket_by_n_vac_1nn_and_2nn,
        priority=0,
        fit_barrier=True,
        review_notes="Produced by Stage 1g z-layer reclassification of "
                     "subsurface-initiated 1NN hops. Two-axis (nv1, nv2) "
                     "bucketing for isolated/clustered separation.",
    ),
    FCCFamily(
        family_id="bulk_1NN_inplane",
        family_name="Bulk 1NN in-plane hop",
        movement_template="<110>_inplane, single-atom, vacancy at bulk-like layer",
        seed_rule=_all(
            _s("motif_family_3d", "subsurface_1nn_translation"),
            _s("direction_family_3d", "<110>_inplane"),
            _s("site_class_3d", "bulk_like"),
        ),
        environment_rule=_bucket_by_n_vac_1nn_and_2nn,
        priority=0,
        fit_barrier=True,
        review_notes="Zero events in current training data — vacancies never "
                     "reach bulk-like layers via 1NN hops in surface-originated "
                     "pyKMC runs. Placeholder for future bulk-start training.",
    ),
    FCCFamily(
        family_id="surface_2NN_diagonal",
        family_name="Surface 2NN face-diagonal hop",
        movement_template="<100>_inplane, single-atom, vacancy at surface",
        seed_rule=_all(
            _s("motif_family_3d", "surface_2nn_translation"),
            _s("direction_family_3d", "<100>_inplane"),
            _s("site_class_3d", "surface"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="In-plane face-diagonal hops. Stage 1a move_type=2NN_hop.",
    ),
    FCCFamily(
        family_id="subsurface_2NN_diagonal",
        family_name="Subsurface 2NN face-diagonal hop",
        movement_template="<100>_inplane, single-atom, vacancy at subsurface",
        seed_rule=_all(
            _s("motif_family_3d", "subsurface_1nn_translation"),
            _s("direction_family_3d", "<100>_inplane"),
            _s("site_class_3d", "subsurface"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="2NN diagonals that landed in subsurface via z-layer pass.",
    ),
    FCCFamily(
        family_id="surface_interlayer_hop",
        family_name="Surface-to-subsurface interlayer hop",
        movement_template="<111>_interlayer, single-atom, mover starts at surface",
        seed_rule=_all(
            _s("motif_family_3d", "interlayer_translation"),
            _s("direction_family_3d", "<111>_interlayer"),
            _s("site_class_3d", "surface"),
        ),
        environment_rule=_bucket_by_layer_initial,
        priority=0,
        fit_barrier=True,
        review_notes="move_type interlayer_hop_up/down where surface_layer_initial=0. "
                     "424 events.",
    ),
    FCCFamily(
        family_id="subsurface_interlayer_hop",
        family_name="Subsurface interlayer hop",
        movement_template="<111>_interlayer, single-atom, mover starts at subsurface",
        seed_rule=_all(
            _s("motif_family_3d", "interlayer_translation"),
            _s("direction_family_3d", "<111>_interlayer"),
            _s("site_class_3d", "subsurface"),
        ),
        environment_rule=_bucket_by_layer_initial,
        priority=0,
        fit_barrier=True,
        review_notes="423 events.",
    ),
    FCCFamily(
        family_id="surface_subsurface_exchange_up",
        family_name="Exchange-up (subsurface→surface)",
        movement_template="2-atom concerted exchange, +z component",
        seed_rule=_all(
            _s("motif_family_3d", "surface_subsurface_exchange"),
            _s("move_type_pre_zlayer", "exchange_up"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="Stage 1a exchange_up events; includes both surface and "
                     "subsurface-initiated variants.",
    ),
    FCCFamily(
        family_id="surface_subsurface_exchange_down",
        family_name="Exchange-down (surface→subsurface)",
        movement_template="2-atom concerted exchange, -z component",
        seed_rule=_all(
            _s("motif_family_3d", "surface_subsurface_exchange"),
            _s("move_type_pre_zlayer", "exchange_down"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="Stage 1a exchange_down events.",
    ),
    FCCFamily(
        family_id="surface_subsurface_exchange_lateral",
        family_name="Lateral exchange",
        movement_template="2-atom concerted exchange, large in-plane component",
        seed_rule=_all(
            _s("motif_family_3d", "surface_subsurface_exchange"),
            _s("move_type_pre_zlayer", "exchange_lateral"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="Stage 1a exchange_lateral — mover traverses ≥3.5 Å with "
                     "layer change. 9k events.",
    ),
    FCCFamily(
        family_id="subsurface_migration_axial",
        family_name="Subsurface migration (axial)",
        movement_template="Subsurface vacancy migration with pure-z displacement",
        seed_rule=_all(
            _s("motif_family_3d", "subsurface_exchange"),
            _s("direction_family_3d", "<001>_exchange"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="Rare (6 catalogue events with <001>_exchange direction). "
                     "Populated mostly when bulk-start training runs.",
    ),
    FCCFamily(
        family_id="subsurface_migration_interlayer",
        family_name="Subsurface migration (interlayer)",
        movement_template="Subsurface vacancy migration with <111> displacement",
        seed_rule=_all(
            _s("motif_family_3d", "subsurface_exchange"),
            _s("direction_family_3d", "<111>_interlayer"),
        ),
        environment_rule=_bucket_by_n_vac_nn1,
        priority=0,
        fit_barrier=True,
        review_notes="6.1k events. z-layer-demoted exchange_* / subsurface_migration.",
    ),
    FCCFamily(
        family_id="concerted_multisite",
        family_name="Concerted multi-atom motion",
        movement_template="n_moved >= 3, no clear single-mover mechanism",
        seed_rule=_s("motif_family_3d", "concerted_3d"),
        environment_rule=_bucket_by_n_moved,
        priority=0,
        fit_barrier=False,
        review_notes="Visible in the export but excluded from barrier fitting "
                     "until a single-mover attribution is available.",
    ),
    FCCFamily(
        family_id="unresolved_multisite",
        family_name="Unresolved multi-site event",
        movement_template="complex / inplane_complex / unresolved geometry",
        seed_rule=_s("motif_family_3d", "unresolved_multisite"),
        environment_rule=_bucket_all,
        priority=0,
        fit_barrier=False,
        review_notes="Catch-all; barrier fitting skipped. Drives registry "
                     "iteration via unresolved_signatures in the report.",
    ),
]


# ── Validator ───────────────────────────────────────────────────────────────

def validate_registry(df: pd.DataFrame,
                      registry: Iterable[FCCFamily] | None = None,
                      ) -> dict:
    """Run every family's seed_rule against every row in df at priority 0.

    Returns a summary dict and raises on overlapping predicates at the same
    priority tier.
    """
    registry = list(registry if registry is not None else FAMILY_REGISTRY)
    by_priority: dict[int, list[FCCFamily]] = {}
    for f in registry:
        by_priority.setdefault(f.priority, []).append(f)

    # Unique family_ids
    ids = [f.family_id for f in registry]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate family_id: {dup}")

    # No overlap at the same priority tier
    for prio, fams in by_priority.items():
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                mask_a = df.apply(a.seed_rule, axis=1)
                mask_b = df.apply(b.seed_rule, axis=1)
                both = int((mask_a & mask_b).sum())
                if both > 0:
                    raise ValueError(
                        f"seed predicates overlap at priority {prio}: "
                        f"{a.family_id} and {b.family_id} both match {both} rows"
                    )

    # Report per-family hit counts
    hits = {}
    for f in registry:
        hits[f.family_id] = int(df.apply(f.seed_rule, axis=1).sum())
    return {"n_rows": len(df), "family_hits": hits}


def family_by_id(family_id: str,
                 registry: Iterable[FCCFamily] | None = None,
                 ) -> FCCFamily | None:
    for f in (registry if registry is not None else FAMILY_REGISTRY):
        if f.family_id == family_id:
            return f
    return None
