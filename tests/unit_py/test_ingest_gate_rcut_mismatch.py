"""IF THIS TEST IS RED — READ THIS.

What G7 / STRADDLING_CLUSTER protects against
---------------------------------------------
Gate **G7** (contract §8; FINAL_DESIGN.md Geom-1 / G7) is the boundary-straddle /
projection-collision guard. pyKMC stores *raw, wrapped* subset coordinates, so a
reference event whose mover sat within ~rcut of an in-plane periodic face has its
-x/-y neighbours wrapped to the far side of the cell. After the ingest projection
min-image-unwraps the cluster about ``move_atom_idx`` (Geom-1), a genuinely local
event has diameter well under ``2*rcut``; a cluster that is still torn across the
boundary (or has two atoms collapsed onto one site) exceeds it. G7 FAILs those with
``STRADDLING_CLUSTER`` (or ``COLLISION``) and routes them to audit instead of poisoning
the catalogue.

The 2026-07-17 production_NiCrFe incident (why this test exists)
---------------------------------------------------------------
The first real-data ingest of
``production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle`` (445 events) FAILed
G7 on **445/445 rows**. The clusters were fine; the *configuration* was wrong.
``GateThresholds.rcut`` defaulted to **5.0 Å**, but the pyKMC run that produced the
pickle used rcut ≈ **8 Å**. A reference cluster spans roughly ``2*run_rcut`` in
diameter (14.95–16.75 Å observed), so *every* cluster tripped
``diameter >= 2*rcut = 10 Å``. The user saw their entire catalogue rejected with no
hint as to why.

Diagnostic rule of thumb
------------------------
The median reference-cluster diameter ≈ ``2 * the pyKMC run's rcut``. So if (nearly)
every event fails G7, read the implied run rcut straight off the failures:
``implied_run_rcut ≈ median_cluster_diameter / 2``. If that number is far above your
configured ``GateThresholds.rcut``, you have a config mismatch, not bad data.

The fix (and the anti-fix)
--------------------------
Pass the pyKMC run's actual rcut (from its input ``[pARTn]`` / eventsearch config)
into ``GateThresholds.rcut`` and re-ingest. **Never** "fix" a wholesale G7 failure by
loosening the gate (raising the ``2*rcut`` limit or disabling G7) — that would silently
admit genuinely boundary-straddled / collided clusters, exactly what G7 exists to keep
out.

This module pins both halves of that contract: the per-event G7 FAIL message must
*carry* the actionable hint, and ``build_class_catalogue`` must *surface* the
systematic mismatch when it sees near-total G7 failure. The green/red contrast between
``test_g7_flags_rcut_mismatch`` and ``test_g7_passes_with_matching_rcut`` on the *same*
cluster IS the executable documentation of the fix: change only ``rcut``.
"""

from __future__ import annotations

import warnings

import pytest

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    CatalogueReport,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventProjReport,
    GateOutcome,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
)

# A realistic rcut≈8 Å reference cluster: diameter ≈ 15.8 Å (the incident saw
# 14.95–16.75 Å). At the mismatched rcut=5.0 the limit is 2*rcut=10.0 → FAIL; at the
# run's true rcut=8.0 the limit is 16.0 → PASS. Same cluster, one config knob.
_STRADDLE_DIAMETER = 15.8
_MISMATCHED_RCUT = 5.0
_RUN_RCUT = 8.0


def _mk_pe(**kw: object) -> ProjectedEvent:
    """A minimal, otherwise gate-passing ProjectedEvent (the established test pattern).

    Mirrors the ``_mk_pe`` helper in ``test_ingest_rate_agg.py`` /
    ``test_ingest_canonical.py`` so no new fixture framework is introduced; override any
    field (here: ``proj_report.diameter``, ``idx_ref``, ``source_row``, ``event_id``).
    """
    base: dict[str, object] = dict(
        anchor0=(0, 0, 0),
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), OccPredicate("SPECIES", frozenset({Occ.NI}))),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), OccPredicate("EMPTY")),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        depth_sig=DepthSig(DepthKind.BULK_OR_DEEPER, -1),
        coloring=Coloring.FULL,
        r_ctx_used=5.0,
        truncated=False,
        Ea_fwd_eV=0.6,
        nu0_fwd_hz=1.0e13,
        k_row=1.0,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        move_atom_idx=0,
        source_row=0,
        # diameter is the only field that matters for G7; keep snap residuals clean so
        # ONLY G7 fails on the straddler (isolates the gate under test).
        proj_report=EventProjReport(0.3, 0.2, _STRADDLE_DIAMETER, True),
    )
    base.update(kw)
    return ProjectedEvent(**base)  # type: ignore[arg-type]


def _straddling_events(n: int) -> list[ProjectedEvent]:
    """``n`` distinct straddling events (all diameter ≈ 15.8 Å) for the catalogue path."""
    return [_mk_pe(idx_ref=i, source_row=i, event_id=f"e{i}") for i in range(n)]


def test_g7_flags_rcut_mismatch() -> None:
    """A rcut≈8 cluster judged at the mismatched rcut=5.0 FAILs G7 with the actionable hint."""
    pe = _mk_pe()  # diameter ≈ 15.8 Å
    res = ec.gate_g7_cluster_integrity(pe, _MISMATCHED_RCUT)

    assert res.outcome == GateOutcome.FAIL
    assert res.gate == "G7"
    detail = res.detail
    # names the audit reason ...
    assert "STRADDLING_CLUSTER" in detail
    # ... carries BOTH numbers (the cluster diameter and the 2*rcut limit it tripped) ...
    assert "15.800" in detail  # diameter
    assert "10.000" in detail  # 2*rcut at the mismatched rcut=5.0
    # ... names the mismatched rcut and the implied run rcut (diameter/2 ≈ 7.9) ...
    assert "5.0 A" in detail
    assert "7.9 A" in detail
    # ... and points at the one-knob fix (never "loosen the gate").
    assert "set GateThresholds.rcut" in detail


def test_g7_passes_with_matching_rcut() -> None:
    """The SAME cluster PASSes G7 once rcut matches the run — the fix is one knob.

    This is the green half of the red/green contrast documented in the module
    docstring: nothing about the event changes between this test and
    ``test_g7_flags_rcut_mismatch`` except ``rcut`` (5.0 → 8.0). That contrast IS the
    documentation that the fix is to set ``GateThresholds.rcut`` to the run's rcut, not
    to weaken G7.
    """
    pe = _mk_pe()  # identical event, diameter ≈ 15.8 Å
    res = ec.gate_g7_cluster_integrity(pe, _RUN_RCUT)  # limit = 16.0 > 15.8

    assert res.outcome == GateOutcome.PASS
    assert "diameter=15.800 < 2*rcut=16.000" in res.detail


def test_catalogue_flags_systematic_mismatch() -> None:
    """>= 10 events all straddling at rcut=5.0 → build_class_catalogue flags the mismatch."""
    events = _straddling_events(12)
    bad_thresholds = GateThresholds(
        emin_event=0.1,
        emax_event=2.0,
        backward_emin_event=0.1,
        snap_tol=0.9,
        db_tol=0.05,
        rcut=_MISMATCHED_RCUT,
    )
    report = CatalogueReport()
    with pytest.warns(UserWarning, match="rcut_mismatch_suspected"):
        classes = ec.build_class_catalogue(
            events,
            t_ref_K=500.0,
            thresholds=bad_thresholds,
            nu0_fallback_hz=1.0e13,
            report=report,
        )

    # Classes are still assembled (the heuristic is additive — it never rejects data
    # or changes a gate outcome), but the systematic flag is raised.
    assert classes, "catalogue should still assemble even under a total-G7-fail mismatch"
    assert report.rcut_mismatch_suspected is True
    assert report.n_events == 12
    assert report.n_g7_fail == 12
    assert report.g7_fail_fraction == 1.0
    assert report.rcut_configured_A == _MISMATCHED_RCUT
    # median cluster diameter ≈ 15.8 → implied run rcut ≈ 7.9 (≈ the true 8.0).
    assert abs(report.median_cluster_diameter_A - _STRADDLE_DIAMETER) < 1e-9
    assert abs(report.implied_run_rcut_A - _STRADDLE_DIAMETER / 2.0) < 1e-9

    msg = report.rcut_mismatch_message
    assert msg is not None
    assert "rcut_mismatch_suspected" in msg
    assert "median cluster diameter" in msg
    # the exact, greppable fix string a user in the wild will land on.
    assert "set GateThresholds.rcut to the pyKMC run's rcut and re-ingest" in msg


def test_catalogue_no_flag_with_matching_rcut() -> None:
    """Control: the same 12 events at the run's true rcut=8.0 raise no flag or warning."""
    events = _straddling_events(12)
    good_thresholds = GateThresholds(
        emin_event=0.1,
        emax_event=2.0,
        backward_emin_event=0.1,
        snap_tol=0.9,
        db_tol=0.05,
        rcut=_RUN_RCUT,
    )
    report = CatalogueReport()
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any spurious rcut warning would fail here
        classes = ec.build_class_catalogue(
            events,
            t_ref_K=500.0,
            thresholds=good_thresholds,
            nu0_fallback_hz=1.0e13,
            report=report,
        )

    assert classes
    assert report.rcut_mismatch_suspected is False
    assert report.rcut_mismatch_message is None
    assert report.n_g7_fail == 0
    assert report.g7_fail_fraction == 0.0
