"""Reference-table driver: pyKMC ``reference_table.pickle`` -> EventClass catalogue.

The installed counterpart of the per-leg scratch drivers that built every catalogue
before the 2026-07-22 frame fix: read a pyKMC reference table, ``project_event`` every
row (robust frame fit, pinned identity scale), run the gates, and assemble the
``EventClass`` catalogue -- one function, deterministic, with per-row failures
recorded (never silently dropped). ``python -m pylatkmc.ingest.cli build`` is the CLI
wrapper.

Frame-unfit rows do NOT appear in ``failures``: :func:`~pylatkmc.ingest.
event_projection.project_event` returns them as degenerate events whose gate log
records ``G3 FRAME_UNFIT`` (memo 2026-07-22 s3.6), so they stay auditable inside the
catalogue. ``failures`` holds only rows that raised -- malformed/incomplete data.

Load cost: pandas is imported lazily inside :func:`read_reference_table` (matching
the Parquet I/O pattern in ``event_class``); importing this module stays cheap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pylatkmc.ingest.event_class import (
    CatalogueReport,
    Coloring,
    EventClass,
    GateThresholds,
    ProjectedEvent,
    build_class_catalogue,
)
from pylatkmc.ingest.event_projection import DEFAULT_NOMINAL_A, project_event


@dataclass
class ReftableBuildReport:
    """Everything :func:`build_catalogue_from_reference_table` measured.

    ``failures`` is ``(row_position, "ExcType: message")`` per raising row;
    ``n_frame_unfit`` counts degenerate (G3 ``FRAME_UNFIT``) events -- part of
    ``n_projected``, since they enter the catalogue as auditable rows.
    """

    n_rows: int = 0
    n_projected: int = 0
    n_frame_unfit: int = 0
    failures: list[tuple[int, str]] = field(default_factory=list)
    catalogue: CatalogueReport = field(default_factory=CatalogueReport)


def read_reference_table(path: str | Path) -> Any:
    """Load a pyKMC ``reference_table.pickle`` as a pandas DataFrame."""
    import pandas as pd

    return pd.read_pickle(Path(path))


def project_reference_table(
    df: Any,
    *,
    coloring: Coloring,
    rcut: float,
    d_max: int,
    r_ctx_min: float,
    nominal_a: float = DEFAULT_NOMINAL_A,
    report: ReftableBuildReport | None = None,
) -> list[ProjectedEvent]:
    """Project every reference row, in row order, recording per-row failures.

    Rows are identified by their positional index (the prototype/triage ``row``
    convention). A raising row is recorded in ``report.failures`` and skipped --
    the survivors keep their original positions via ``source_row``/``idx_ref``.
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
            )
        except Exception as exc:  # noqa: BLE001 -- recorded, never silent
            rep.failures.append((i, f"{type(exc).__name__}: {exc}"))
            continue
        if pe.proj_report.frame_unfit_reason is not None:
            rep.n_frame_unfit += 1
        out.append(pe)
    rep.n_projected = len(out)
    return out


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
    the G7 straddling gate trips wholesale otherwise). Events are sorted by
    ``source_row`` before assembly, matching the validated prototype driver, so
    the produced ``class_id`` set and member order are reproducible.
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
        report=rep,
    )
    return build_class_catalogue(
        sorted(events, key=lambda pe: pe.source_row),
        t_ref_K=t_ref_K,
        thresholds=thresholds,
        nu0_fallback_hz=nu0_fallback_hz,
        first_seen_cycle=first_seen_cycle,
        report=rep.catalogue,
    )
