"""Reference-table driver: pyKMC ``reference_table.pickle`` -> EventClass catalogue.

The installed counterpart of the per-leg scratch drivers that built every catalogue
before the 2026-07-22 frame fix: read a pyKMC reference table, ``project_event`` every
row (robust frame fit, pinned identity scale), enforce the mover-keyed G3 as a
build-time drop, and assemble the ``EventClass`` catalogue -- one function,
deterministic, with per-row failures recorded (never silently dropped).
``python -m pylatkmc.ingest.cli build`` is the CLI wrapper.

Discard ledger (memo 2026-07-29 §5)
-----------------------------------
A G3-failing row is dropped **before joining a class**: frame-unfit rows (no FCC
frame exists -- reason ``FRAME_UNFIT``; convention change vs memo 2026-07-22 §3.6,
which kept them in-catalogue as degenerate rows) and mover-off-lattice rows
(``mover_max_residual >= mover_snap_tol`` -- reason ``MOVER_OFFLATTICE``). Both land
in the sidecar ledger ``<out>_discarded.parquet`` (row position, ``idx_ref``,
reason, residuals, lineage), sorted by row position -- one place to look for every
event the catalogue refused, counted, never silent. The conservation invariant is
exact: ``n_rows = n_projected + n_raised + n_discarded``.

``failures`` still holds only rows that raised -- malformed/incomplete data.

Load cost: pandas is imported lazily inside :func:`read_reference_table` and
pyarrow inside :func:`write_discard_ledger_parquet` (matching the Parquet I/O
pattern in ``event_class``); importing this module stays cheap.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pylatkmc.ingest.event_class import (
    CatalogueReport,
    Coloring,
    EventClass,
    GateOutcome,
    GateThresholds,
    ProjectedEvent,
    RawArrow,
    build_class_catalogue,
)
from pylatkmc.ingest.event_projection import DEFAULT_NOMINAL_A, project_event

DiscardReason = Literal["MOVER_OFFLATTICE", "FRAME_UNFIT"]


@dataclass(frozen=True)
class DiscardedRow:
    """One ledger entry: a reference row the catalogue refused (memo 2026-07-29 §5).

    ``row`` is the positional index in the reference table; ``detail`` carries the
    frame fitter's reason (``FRAME_UNFIT``) or the residual-vs-threshold message
    (``MOVER_OFFLATTICE``). The remaining fields are the lineage needed to
    re-audit / re-harvest the event without re-projection.

    Action axis (action-fingerprint memo §5.1, Phase 1): ``arrows`` holds the
    **unsnapped** :class:`~pylatkmc.ingest.event_class.RawArrow` provenance -- real-
    valued lattice coordinates, so triage can see *what almost happened* -- and the
    ledger's ``action_id`` / ``archetype`` / ``one_way`` are always ``None``: an
    off-lattice event has **no faithful site permutation by definition**, so no
    action is defined for it, and a ledger row is a single event with no class-level
    forward/backward pairing from which liveness could be resolved. For a
    ``FRAME_UNFIT`` row even ``arrows`` is empty -- with no frame there is no
    coordinate system to express an arrow in.
    """

    row: int
    idx_ref: int
    source_row: int
    event_id: str
    reason: DiscardReason
    detail: str
    mover_max_residual: float
    max_residual: float
    Ea_fwd_eV: float
    move_atom_idx: int
    arrows: tuple[RawArrow, ...] = ()
    action_id: int | None = None
    archetype: int | None = None
    one_way: bool | None = None


@dataclass
class ReftableBuildReport:
    """Everything :func:`build_catalogue_from_reference_table` measured.

    ``failures`` is ``(row_position, "ExcType: message")`` per raising row;
    ``discarded`` is the §5 ledger (row-position order); ``n_frame_unfit`` /
    ``n_mover_offlattice`` split ``n_discarded`` by reason. Conservation is exact:
    ``n_rows = n_projected + len(failures) + n_discarded``.
    """

    n_rows: int = 0
    n_projected: int = 0
    n_discarded: int = 0
    n_frame_unfit: int = 0
    n_mover_offlattice: int = 0
    failures: list[tuple[int, str]] = field(default_factory=list)
    discarded: list[DiscardedRow] = field(default_factory=list)
    catalogue: CatalogueReport = field(default_factory=CatalogueReport)


def read_reference_table(path: str | Path) -> Any:
    """Load a pyKMC ``reference_table.pickle`` as a pandas DataFrame."""
    import pandas as pd

    return pd.read_pickle(Path(path))


def discard_ledger_path(out_path: str | Path) -> Path:
    """The sidecar ledger path for a catalogue output: ``<out>_discarded.parquet``.

    Same directory as the catalogue parquet (memo §11), so per-run and merged
    variants stay adjacent to their catalogues.
    """
    out = Path(out_path)
    return out.with_name(f"{out.stem}_discarded.parquet")


def _discard_reason(pe: ProjectedEvent, mover_snap_tol: float) -> tuple[DiscardReason, str] | None:
    """The §5 drop decision for one projected row (None = keep).

    Mirrors :func:`~pylatkmc.ingest.event_class.gate_g3_snap_residual` exactly:
    the same event-level criterion decides both the recorded gate outcome and the
    build-time drop, so the retained class-level G3 can never FAIL post-drop.
    """
    rep = pe.proj_report
    if rep.frame_unfit_reason is not None:
        return "FRAME_UNFIT", rep.frame_unfit_reason
    if rep.mover_max_residual >= mover_snap_tol:
        return (
            "MOVER_OFFLATTICE",
            f"mover_max_residual={rep.mover_max_residual:.3f} >= "
            f"mover_snap_tol={mover_snap_tol} (max_residual={rep.max_residual:.3f})",
        )
    return None


def project_reference_table(
    df: Any,
    *,
    coloring: Coloring,
    rcut: float,
    d_max: int,
    r_ctx_min: float,
    nominal_a: float = DEFAULT_NOMINAL_A,
    mover_snap_tol: float = 0.5,
    bystander_mask_tol: float = 0.5,
    report: ReftableBuildReport | None = None,
) -> list[ProjectedEvent]:
    """Project every reference row, in row order, enforcing the §5 drop.

    Rows are identified by their positional index (the prototype/triage ``row``
    convention). A raising row is recorded in ``report.failures``; a G3-failing
    row (``FRAME_UNFIT`` / ``MOVER_OFFLATTICE``) is recorded in
    ``report.discarded`` and never returned -- it must not join a class. The
    survivors keep their original positions via ``source_row``/``idx_ref``.
    """
    rep = report if report is not None else ReftableBuildReport()
    rep.n_rows = int(len(df))
    out: list[ProjectedEvent] = []
    for i in range(len(df)):
        try:
            pe = project_event(
                df.iloc[i],
                coloring=coloring,
                rcut=rcut,
                d_max=d_max,
                r_ctx_min=r_ctx_min,
                nominal_a=nominal_a,
                bystander_mask_tol=bystander_mask_tol,
            )
        except Exception as exc:  # noqa: BLE001 -- recorded, never silent
            rep.failures.append((i, f"{type(exc).__name__}: {exc}"))
            continue
        dropped = _discard_reason(pe, mover_snap_tol)
        if dropped is not None:
            reason, detail = dropped
            rep.discarded.append(
                DiscardedRow(
                    row=i,
                    idx_ref=pe.idx_ref,
                    source_row=pe.source_row,
                    event_id=pe.event_id,
                    reason=reason,
                    detail=detail,
                    mover_max_residual=pe.proj_report.mover_max_residual,
                    max_residual=pe.proj_report.max_residual,
                    Ea_fwd_eV=pe.Ea_fwd_eV,
                    move_atom_idx=pe.move_atom_idx,
                    arrows=pe.arrows_raw,
                )
            )
            rep.n_discarded += 1
            if reason == "FRAME_UNFIT":
                rep.n_frame_unfit += 1
            else:
                rep.n_mover_offlattice += 1
            continue
        out.append(pe)
    rep.n_projected = len(out)
    return out


def write_discard_ledger_parquet(
    discarded: list[DiscardedRow],
    path: str | Path,
    *,
    metadata: dict[bytes, bytes] | None = None,
) -> None:
    """Write the §5 discard ledger sidecar (row-position order, deterministic).

    Always writes the file, even when empty, so downstream tooling can rely on
    the sidecar existing next to every catalogue built under the 2026-07-29
    policy.

    The four action-axis columns (action-fingerprint memo §7 Phase 1) are present
    here too, with the ledger's documented encoding: ``arrows`` is the **unsnapped**
    (``float64`` lattice-coordinate) counterpart of the catalogue's integer arrow
    struct, and ``action_id`` / ``archetype`` / ``one_way`` are **always null** —
    see :class:`DiscardedRow`.
    """
    import pyarrow as pa  # type: ignore[import-untyped]
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    raw_arrow_type = pa.list_(
        pa.struct(
            [
                ("sx", pa.float64()),
                ("sy", pa.float64()),
                ("sz", pa.float64()),
                ("ex", pa.float64()),
                ("ey", pa.float64()),
                ("ez", pa.float64()),
                # uint8: OCC_ANY is 254 in a grey build (see the catalogue schema).
                ("species", pa.uint8()),
            ]
        )
    )
    schema = pa.schema(
        [
            ("row", pa.int64()),
            ("idx_ref", pa.int64()),
            ("source_row", pa.int64()),
            ("event_id", pa.string()),
            ("reason", pa.string()),
            ("detail", pa.string()),
            ("mover_max_residual", pa.float64()),
            ("max_residual", pa.float64()),
            ("Ea_fwd_eV", pa.float64()),
            ("move_atom_idx", pa.int64()),
            # --- action axis (memo §5.1): unsnapped arrows; the rest always null ---
            ("arrows", raw_arrow_type),
            ("action_id", pa.uint64()),
            ("archetype", pa.uint64()),
            ("one_way", pa.bool_()),
        ]
    )
    ordered = sorted(discarded, key=lambda d: d.row)
    columns: dict[str, list[Any]] = {
        "row": [d.row for d in ordered],
        "idx_ref": [d.idx_ref for d in ordered],
        "source_row": [d.source_row for d in ordered],
        "event_id": [d.event_id for d in ordered],
        "reason": [d.reason for d in ordered],
        "detail": [d.detail for d in ordered],
        "mover_max_residual": [_finite_or_none(d.mover_max_residual) for d in ordered],
        "max_residual": [_finite_or_none(d.max_residual) for d in ordered],
        "Ea_fwd_eV": [_finite_or_none(d.Ea_fwd_eV) for d in ordered],
        "move_atom_idx": [d.move_atom_idx for d in ordered],
        "arrows": [_raw_arrow_rows(d.arrows) for d in ordered],
        "action_id": [d.action_id for d in ordered],
        "archetype": [d.archetype for d in ordered],
        "one_way": [d.one_way for d in ordered],
    }
    if metadata is not None:
        schema = schema.with_metadata(metadata)
    table = pa.Table.from_pydict(columns, schema=schema)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


def _finite_or_none(x: float) -> float | None:
    """Parquet-friendly float: ``inf`` (frame-unfit residuals) / NaN -> null."""
    return float(x) if math.isfinite(x) else None


def _raw_arrow_rows(arrows: tuple[RawArrow, ...]) -> list[dict[str, Any]]:
    """One ledger ``arrows`` cell: unsnapped lattice coordinates + species code."""
    return [
        {
            "sx": float(a.start[0]),
            "sy": float(a.start[1]),
            "sz": float(a.start[2]),
            "ex": float(a.end[0]),
            "ey": float(a.end[1]),
            "ez": float(a.end[2]),
            "species": int(a.species),
        }
        for a in arrows
    ]


def build_catalogue_from_reference_table(
    reftable: str | Path | Any,
    *,
    coloring: Coloring,
    rcut: float,
    thresholds: GateThresholds,
    t_ref_K: float,
    d_max: int,
    r_ctx_min: float,
    nominal_a: float = DEFAULT_NOMINAL_A,
    nu0_fallback_hz: float = 1.0e12,
    first_seen_cycle: int = 0,
    report: ReftableBuildReport | None = None,
) -> list[EventClass]:
    """The full installed pipeline: reference table -> ``EventClass`` catalogue.

    ``reftable`` is a path (pickled DataFrame) or an already-loaded DataFrame.
    ``rcut`` must be the pyKMC run's rcut (``thresholds.rcut`` should match it --
    the G7 straddling gate trips wholesale otherwise). ``thresholds`` also
    supplies ``mover_snap_tol`` (the §5 build-time drop) and
    ``bystander_mask_tol`` (the §6 context mask). Events are sorted by
    ``source_row`` before assembly, matching the validated prototype driver, so
    the produced ``class_id`` set and member order are reproducible.

    Post-assembly, the retained class-level G3 must PASS on every class (the
    §5 drop removed every FAILing member); a FAIL is a pipeline bug and is
    surfaced as a warning, never silently.
    """
    df = read_reference_table(reftable) if isinstance(reftable, (str, Path)) else reftable
    rep = report if report is not None else ReftableBuildReport()
    events = project_reference_table(
        df,
        coloring=coloring,
        rcut=rcut,
        d_max=d_max,
        r_ctx_min=r_ctx_min,
        nominal_a=nominal_a,
        mover_snap_tol=thresholds.mover_snap_tol,
        bystander_mask_tol=thresholds.bystander_mask_tol,
        report=rep,
    )
    classes = build_class_catalogue(
        sorted(events, key=lambda pe: pe.source_row),
        t_ref_K=t_ref_K,
        thresholds=thresholds,
        nu0_fallback_hz=nu0_fallback_hz,
        first_seen_cycle=first_seen_cycle,
        report=rep.catalogue,
    )
    g3_fail = [
        ec.class_id
        for ec in classes
        if any(g.gate == "G3" and g.outcome == GateOutcome.FAIL for g in ec.gate_log)
    ]
    if g3_fail:
        warnings.warn(
            f"pipeline bug: {len(g3_fail)} classes FAIL class-level G3 after the "
            f"build-time discard (must always PASS post-drop, memo 2026-07-29 §5): "
            f"{g3_fail[:5]}",
            stacklevel=2,
        )
    return classes
