"""Rate-space aggregation + ingest gates G1-G7 (Agent A2, contract 11.5).

Pure numpy/stdlib: ``event_class`` imports cleanly without the ``[ingest]``
extras, so no importorskip guard is needed here (the pandas/pyarrow-dependent
Parquet tests live in ``test_ingest_parquet.py``).
"""

from __future__ import annotations

import math

import numpy as np

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    Arrow,
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
from pylatkmc.rate_expression import KB_EV_PER_K


# --------------------------------------------------------------------------- #
# Rate-space aggregation (contract 6.1)                                       #
# --------------------------------------------------------------------------- #
def test_rate_space_matches_brute_force() -> None:
    """k_rate_mean equals the brute-force mean(nu0*exp(-Ea/kT))/1e12 (C1)."""
    t = 300.0
    kt = KB_EV_PER_K * t
    barriers = [0.55, 0.60, 0.65]
    nu0 = [1.0e13, 1.2e13, 0.9e13]
    agg = ec.aggregate_rate_space(barriers, nu0, t, nu0_fallback_hz=1.0e12)
    brute = float(np.mean([n * math.exp(-e / kt) for e, n in zip(barriers, nu0)]))
    brute /= ec.HZ_PER_PSINV
    assert math.isclose(agg.k_rate_mean_psinv, brute, rel_tol=1e-12)


def test_jensen_gap_direction_and_magnitude() -> None:
    """Rate-space > mean-then-exp by the Jensen factor; ~6x on sigma=0.05 eV @ 300 K."""
    t = 300.0
    kt = KB_EV_PER_K * t
    # 3-point 0.05 eV spread: rate-space strictly exceeds mean-then-exp.
    barriers = [0.55, 0.60, 0.65]
    nu0 = [1.0e13, 1.0e13, 1.0e13]
    agg = ec.aggregate_rate_space(barriers, nu0, t, nu0_fallback_hz=1.0e12)
    mean_then_exp = agg.nu0_geo_psinv * math.exp(-float(np.mean(barriers)) / kt)
    assert agg.k_rate_mean_psinv > mean_then_exp  # exp(-<Ea>) <= <exp(-Ea)>
    assert agg.k_rate_mean_psinv / mean_then_exp > 2.0

    # A dense Gaussian sample (sigma = 0.05 eV) reproduces the ~6.5x analytic
    # Jensen factor exp(sigma^2 / (2 (kT)^2)).
    rng = np.random.default_rng(0)
    sample = rng.normal(0.60, 0.05, 20000)
    aggg = ec.aggregate_rate_space(sample.tolist(), [1.0e13] * sample.size, t, nu0_fallback_hz=1.0e12)
    mte = aggg.nu0_geo_psinv * math.exp(-float(np.mean(sample)) / kt)
    ratio = aggg.k_rate_mean_psinv / mte
    analytic = math.exp((0.05 / kt) ** 2 / 2.0)
    assert abs(ratio - analytic) / analytic < 0.1
    assert 5.5 < ratio < 7.5  # "~6x"


def test_reproduction_at_t_ref() -> None:
    """nu0_geo * exp(-Ea_rep/kT_ref) reproduces k_rate_mean exactly at T_ref."""
    t = 500.0
    kt = KB_EV_PER_K * t
    agg = ec.aggregate_rate_space([0.4, 0.5, 0.7, 0.9], [1e13, 2e13, 3e13, 4e13], t,
                                  nu0_fallback_hz=1e12)
    repro = agg.nu0_geo_psinv * math.exp(-agg.Ea_rep_eV / kt)
    assert math.isclose(repro, agg.k_rate_mean_psinv, rel_tol=1e-12)


def test_ea_std_and_n_eff() -> None:
    """Ea_std is None for n<3; floored for n>=3; n_eff == n."""
    a2 = ec.aggregate_rate_space([0.5, 0.6], [1e13, 1e13], 500.0, nu0_fallback_hz=1e12)
    assert a2.Ea_std_eV is None
    assert a2.n_eff == 2.0 and a2.n_members == 2

    # tiny spread -> the prior floor (0.02 eV) dominates, never 0.
    a_tight = ec.aggregate_rate_space([0.6, 0.6, 0.6], [1e13, 1e13, 1e13], 500.0,
                                      nu0_fallback_hz=1e12)
    assert a_tight.Ea_std_eV is not None
    assert math.isclose(a_tight.Ea_std_eV, ec.PRIOR_EA_STD_FLOOR_EV, rel_tol=1e-9)

    a5 = ec.aggregate_rate_space([0.3, 0.5, 0.6, 0.7, 0.9], [1e13] * 5, 500.0,
                                 nu0_fallback_hz=1e12)
    assert a5.Ea_std_eV is not None and a5.Ea_std_eV >= ec.PRIOR_EA_STD_FLOOR_EV
    assert a5.n_eff == 5.0


def test_sorted_determinism() -> None:
    """Shuffling the member input order yields bit-identical outputs (M4)."""
    a = ec.aggregate_rate_space([0.65, 0.55, 0.60], [2e13, 1e13, 3e13], 500.0, nu0_fallback_hz=1e12)
    b = ec.aggregate_rate_space([0.55, 0.60, 0.65], [1e13, 3e13, 2e13], 500.0, nu0_fallback_hz=1e12)
    assert a == b


def test_nu0_fallback_used_for_missing() -> None:
    """A NaN / non-positive member nu0 falls back to nu0_fallback_hz."""
    t = 500.0
    kt = KB_EV_PER_K * t
    agg = ec.aggregate_rate_space([0.5], [float("nan")], t, nu0_fallback_hz=7.0e12)
    assert math.isclose(agg.nu0_geo_psinv, 7.0, rel_tol=1e-12)
    expected = 7.0e12 * math.exp(-0.5 / kt) / ec.HZ_PER_PSINV
    assert math.isclose(agg.k_rate_mean_psinv, expected, rel_tol=1e-12)


def test_ea_rep_at_least_ea_min() -> None:
    """The rate-equivalent barrier is never below the fastest member (uniform nu0)."""
    agg = ec.aggregate_rate_space([0.45, 0.60, 0.75], [1e13, 1e13, 1e13], 500.0,
                                  nu0_fallback_hz=1e12)
    assert agg.Ea_rep_eV >= min(0.45, 0.60, 0.75)
    assert agg.Ea_rep_eV <= agg.Ea_mean_eV


def test_empty_member_list() -> None:
    """Zero members -> NaN rate columns, None Ea_std (defensive)."""
    agg = ec.aggregate_rate_space([], [], 500.0, nu0_fallback_hz=1e12)
    assert math.isnan(agg.k_rate_mean_psinv)
    assert agg.Ea_std_eV is None and agg.n_members == 0


# --------------------------------------------------------------------------- #
# Gates G1-G7 (contract 8)                                                     #
# --------------------------------------------------------------------------- #
def _mk_pe(**kw: object) -> ProjectedEvent:
    """A minimal, gate-passing ProjectedEvent; override any field via kwargs."""
    base: dict[str, object] = dict(
        anchor0=(0, 0, 0),
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), OccPredicate("SPECIES", frozenset({Occ.NI}))),
            StencilSite((2, 0, 0), OccPredicate("EMPTY")),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.NI),),
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
        proj_report=EventProjReport(0.3, 0.2, 4.0, True),
    )
    base.update(kw)
    return ProjectedEvent(**base)  # type: ignore[arg-type]


_THRESH = GateThresholds(
    emin_event=0.1, emax_event=2.0, backward_emin_event=0.1, snap_tol=0.9, db_tol=0.05, rcut=5.0
)


def test_run_gates_all_pass() -> None:
    """A clean event passes G1/G3/G5-G7; NA on G2 (no pair) and G4 (deferred round-trip)."""
    res = ec.run_gates(_mk_pe(), thresholds=_THRESH, t_ref_K=500.0)
    assert tuple(r.gate for r in res) == ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    outcomes = {r.gate: r.outcome for r in res}
    assert outcomes["G2"] == GateOutcome.NA  # no linked backward pair
    # G4's mover-agreement half holds; its ideal-site re-projection round-trip is
    # deferred (contract 13) and reported NA rather than a vacuous PASS.
    assert outcomes["G4"] == GateOutcome.NA
    assert all(outcomes[g] == GateOutcome.PASS for g in ("G1", "G3", "G5", "G6", "G7"))


def test_g1_barrier_bounds_fires() -> None:
    """G1 FAILs outside [emin_event, emax_event]."""
    assert ec.gate_g1_barrier_bounds(_mk_pe(Ea_fwd_eV=5.0), 0.1, 2.0, 0.1).outcome == GateOutcome.FAIL
    assert ec.gate_g1_barrier_bounds(_mk_pe(Ea_fwd_eV=0.05), 0.1, 2.0, 0.1).outcome == GateOutcome.FAIL
    assert ec.gate_g1_barrier_bounds(_mk_pe(Ea_fwd_eV=0.6), 0.1, 2.0, 0.1).outcome == GateOutcome.PASS


def test_g2_detailed_balance_real_not_tautology() -> None:
    """G2 PASSes a consistent linked pair, FAILs an inconsistent one, NA without a pair."""
    t = 500.0
    kt = KB_EV_PER_K * t
    ea_f, ea_b, nu_f, nu_b = 0.6, 0.5, 1.0e13, 2.0e13
    k_f = nu_f * math.exp(-ea_f / kt)
    k_b = nu_b * math.exp(-ea_b / kt)
    fwd = _mk_pe(Ea_fwd_eV=ea_f, nu0_fwd_hz=nu_f, k_row=k_f)
    bwd = _mk_pe(Ea_fwd_eV=ea_b, nu0_fwd_hz=nu_b, k_row=k_b)
    assert ec.gate_g2_detailed_balance(fwd, None, t).outcome == GateOutcome.NA
    assert ec.gate_g2_detailed_balance(fwd, bwd, t).outcome == GateOutcome.PASS
    # fold-in an unpaired backward whose stored k violates detailed balance
    bwd_bad = _mk_pe(Ea_fwd_eV=ea_b, nu0_fwd_hz=nu_b, k_row=k_f)
    assert ec.gate_g2_detailed_balance(fwd, bwd_bad, t).outcome == GateOutcome.FAIL


def _k(nu0: float, ea: float, t: float) -> float:
    """pyKMC-consistent stored rate k = nu0 * exp(-Ea / kT)."""
    return nu0 * math.exp(-ea / (KB_EV_PER_K * t))


def test_g2_pair_spread_foldin_fails_on_consistent_k() -> None:
    """Class-level G2 catches a fold-in the per-pair ratio cannot (contract 8, C2).

    Two members merged into one class whose per-member dE_pair diverge (0.20 vs 0.50)
    are a fold-in even though each row's stored k is perfectly pyKMC-consistent -- the
    per-pair ratio is 0 for both, but the spread (0.30 eV) is 6x db_tol -> FAIL.
    """
    t = 500.0
    # member 1: Ea_f=0.60, Ea_b=0.40 -> dE_pair=0.20 ; member 2: 0.60/0.10 -> 0.50
    terms = [
        (_k(1e13, 0.60, t), _k(2e13, 0.40, t), 1e13, 2e13),
        (_k(5e12, 0.60, t), _k(8e12, 0.10, t), 5e12, 8e12),
    ]
    res = ec.gate_g2_pair_spread([0.20, 0.50], terms, t, db_tol=0.05)
    assert res.outcome == GateOutcome.FAIL
    assert "spread" in res.detail


def test_g2_pair_spread_consistent_class_passes() -> None:
    """A genuine class (tight dE_pair + pyKMC-consistent stored k) PASSes G2."""
    t = 500.0
    terms = [
        (_k(1e13, 0.60, t), _k(2e13, 0.50, t), 1e13, 2e13),  # dE_pair = 0.10
        (_k(3e13, 0.61, t), _k(4e13, 0.51, t), 3e13, 4e13),  # dE_pair = 0.10
    ]
    res = ec.gate_g2_pair_spread([0.10, 0.10], terms, t, db_tol=0.05)
    assert res.outcome == GateOutcome.PASS


def test_g2_pair_spread_single_pair_is_na() -> None:
    """With fewer than two linked pairs there is no spread / mean -> NA."""
    t = 500.0
    terms = [(_k(1e13, 0.6, t), _k(2e13, 0.5, t), 1e13, 2e13)]
    assert ec.gate_g2_pair_spread([0.10], terms, t).outcome == GateOutcome.NA
    assert ec.gate_g2_pair_spread([], [], t).outcome == GateOutcome.NA


def test_g2_pair_spread_independent_mean_ratio_fires() -> None:
    """Tight dE_pair spread but a stored k off the class-mean fails the mean ratio.

    The barrier channel (dE_pair) is tight [0.10, 0.12], but member 2's stored k
    implies a reaction energy of 0.50 eV -- far off the class mean -- so the
    independent-mean detailed-balance residual FAILs even though the spread passes.
    """
    t = 500.0
    kt = KB_EV_PER_K * t
    good = (_k(1e13, 0.60, t), _k(2e13, 0.50, t), 1e13, 2e13)  # implies dE = 0.10
    # member 2: nu0_f/nu0_b = 1e13/1e13; stored k ratio implies dE_stored = 0.50 eV.
    kf2, nu0f2, nu0b2 = 1.0, 1e13, 1e13
    kb2 = kf2 / math.exp(-0.50 / kt)  # ln(kf/kb) = -0.50/kt
    bad = (kf2, kb2, nu0f2, nu0b2)
    res = ec.gate_g2_pair_spread([0.10, 0.12], [good, bad], t, db_tol=0.05)
    assert res.outcome == GateOutcome.FAIL
    assert "residual" in res.detail


def test_g3_snap_residual_fires() -> None:
    """G3 is mover-keyed (memo 2026-07-29 §4): only mover residuals FAIL.

    Regression for the pre-2026-07-29 dead mover branch (§11-i): an event failing
    *only* on mover residual must FAIL with a MOVER_OFFLATTICE detail — the old
    gate tested max_residual first, so its mover branch was unreachable (movers
    are a subset of atoms). A bystander-only high residual now PASSes (the §6
    mask, not the gate, handles it).
    """
    # mover off-lattice -> FAIL, and the detail names the mover criterion.
    res = ec.gate_g3_snap_residual(_mk_pe(proj_report=EventProjReport(0.95, 0.95, 4.0, True)))
    assert res.outcome == GateOutcome.FAIL
    assert "MOVER_OFFLATTICE" in res.detail
    # bystander-only high residual (movers tight) -> PASS under the mover-keyed gate.
    res = ec.gate_g3_snap_residual(_mk_pe(proj_report=EventProjReport(1.0, 0.2, 4.0, True)))
    assert res.outcome == GateOutcome.PASS
    assert "max_residual=1.000" in res.detail  # both residuals recorded for audit
    assert ec.gate_g3_snap_residual(_mk_pe()).outcome == GateOutcome.PASS


def test_g4_mover_agreement() -> None:
    """G4 FAILs on the concerted mislabel (move_atom_idx not in movers)."""
    assert ec.gate_g4_round_trip(_mk_pe(proj_report=EventProjReport(0.3, 0.2, 4.0, False))).outcome == GateOutcome.FAIL
    # Mover agreement holds; the ideal-site re-projection round-trip is not verifiable
    # in Phase A (no re-projection entry point), so the gate is NA -- never a vacuous
    # same-object PASS that could never catch a mis-projection (contract 8 / 13).
    assert ec.gate_g4_round_trip(_mk_pe()).outcome == GateOutcome.NA


def test_g5_conservation_fires() -> None:
    """G5 FAILs on a non-conservative (dissolution) event, PASSes a hop."""
    dissolution = _mk_pe(delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),), delta_atoms=-1)
    assert ec.gate_g5_conservation(dissolution).outcome == GateOutcome.FAIL
    assert ec.gate_g5_conservation(_mk_pe()).outcome == GateOutcome.PASS


def test_g6_context_completeness_warns() -> None:
    """G6 WARNs (not FAILs) on a truncated cluster."""
    assert ec.gate_g6_context_completeness(_mk_pe(truncated=True)).outcome == GateOutcome.WARN
    assert ec.gate_g6_context_completeness(_mk_pe()).outcome == GateOutcome.PASS


def test_g7_cluster_integrity_fires() -> None:
    """G7 FAILs when the unwrapped diameter reaches 2*rcut."""
    straddle = _mk_pe(proj_report=EventProjReport(0.3, 0.2, 20.0, True))
    assert ec.gate_g7_cluster_integrity(straddle, 5.0).outcome == GateOutcome.FAIL
    assert ec.gate_g7_cluster_integrity(_mk_pe(), 5.0).outcome == GateOutcome.PASS


def test_jensen_direction_inequality() -> None:
    """Explicit Jensen direction check: exp(-<Ea>) <= <exp(-Ea)> for any spread."""
    t = 400.0
    kt = KB_EV_PER_K * t
    barriers = [0.3, 0.55, 0.62, 0.8, 1.1]
    agg = ec.aggregate_rate_space(barriers, [1e13] * len(barriers), t, nu0_fallback_hz=1e12)
    mean_then_exp = agg.nu0_geo_psinv * math.exp(-float(np.mean(barriers)) / kt)
    assert mean_then_exp <= agg.k_rate_mean_psinv
