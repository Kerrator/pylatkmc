"""Cross-run class-level merge of per-run ``EventClass`` catalogues.

Pure-logic tests — the merge operates on ``EventClass`` lists and needs no extras.
Covers the three merge invariants the probe flagged: idx_ref collision across runs
(provenance stays disambiguated, no cross-linking), status conflicts (a
previously-quarantined class surviving merged QC), and the class_id-keyed measured
stamp migration.
"""

from __future__ import annotations

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    Occ,
    OccPredicate,
)
from pylatkmc.ingest.merge import (
    measured_class_ids_from_catalogue,
    merge_qcd_catalogues,
    union_classes,
)
from pylatkmc.ingest.qc import (
    NU0_POLICY_HARVESTED_PAIR,
    NU0_POLICY_PENDING_RESEARCH,
    stamp_rate_policy,
)

_G3_PASS = (ec.GateResult("G3", ec.GateOutcome.PASS, "max_residual=0.1 < 0.9", 0.1),)
_G3_FAIL = (ec.GateResult("G3", ec.GateOutcome.FAIL, "UNMAPPABLE", 1.4),)
_ONE_DELTA = (DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),)


def _mk(
    class_id: str,
    *,
    barriers: tuple[float, ...] = (0.5,),
    nu0_f: tuple[float, ...] | None = None,
    nu0_b: tuple[float, ...] | None = None,
    dE_pair_list: tuple[float, ...] = (),
    delta: tuple[DeltaSite, ...] = _ONE_DELTA,
    delta_atoms: int = 0,
    backward_class: str | None = None,
    dEnergy: float | None = None,
    self_reverse: bool = False,
    source_rows: tuple[int, ...] = (0,),
    source_idx_refs: tuple[int, ...] = (0,),
    audit_status: str = "pending",
    audit_reason: str = "",
    nu0_pair_policy: str | None = None,
    gate_log: tuple[ec.GateResult, ...] = _G3_PASS,
    t_ref_K: float = 500.0,
) -> EventClass:
    """A minimal but valid EventClass for merge tests."""
    n = len(barriers)
    cf = (1, 0, 0, 0, 0, (), (), ())
    return EventClass(
        class_id=class_id,
        canonical_form=cf,
        canonical_blob=ec._tlv_encode(cf),
        depth_sig=DepthSig(DepthKind.SURFACE, 0),
        coloring=Coloring.FULL,
        move_shape=0,
        family_id=0,
        delta=delta,
        delta_atoms=delta_atoms,
        context=(),
        saddle_token=(),
        orientation_count=1,
        r_ctx_used=5.0,
        r_id_used=5.0,
        anchor_pred=OccPredicate("WILDCARD"),
        t_ref_K=t_ref_K,
        barriers_eV=barriers,
        nu0_f_list_hz=nu0_f if nu0_f is not None else tuple(1e13 for _ in barriers),
        nu0_b_list_hz=nu0_b if nu0_b is not None else tuple(1e13 for _ in barriers),
        dE_pair_list_eV=dE_pair_list,
        k_rate_mean_psinv=1.0,
        Ea_rep_eV=barriers[0],
        nu0_geo_psinv=10.0,
        Ea_std_eV=None,
        n_eff=float(n),
        Ea_mean_eV=barriers[0],
        Ea_median_eV=barriers[0],
        backward_class=backward_class,
        self_reverse=self_reverse,
        dEnergy_eV=dEnergy,
        source_rows=source_rows,
        source_idx_refs=source_idx_refs,
        audit_status=audit_status,  # type: ignore[arg-type]
        audit_reason=audit_reason,
        nu0_pair_policy=nu0_pair_policy,
        gate_log=gate_log,
    )


def _by_id(classes) -> dict[str, EventClass]:
    return {c.class_id: c for c in classes}


# --------------------------------------------------------------------------- #
# idx_ref collision across runs (provenance disambiguated, no cross-linking)   #
# --------------------------------------------------------------------------- #
def test_idx_ref_collision_disambiguated_no_cross_link() -> None:
    """Two runs' colliding idx_ref==0 stay distinct in provenance; unrelated classes
    never merge or contaminate each other."""
    run_a = [
        _mk("X", barriers=(0.50,), source_idx_refs=(0,)),  # collides with run_b X
        _mk("Y", barriers=(0.70,), source_idx_refs=(1,)),  # run-a-only
    ]
    run_b = [
        _mk("X", barriers=(0.51,), source_idx_refs=(0,)),  # collides with run_a X
        _mk("Z", barriers=(0.90,), source_idx_refs=(1,)),  # run-b-only
    ]
    merged = union_classes([("runB", run_b), ("runA", run_a)])
    by = _by_id(merged)

    # shared class X: members concatenated, provenance run-qualified + disambiguated
    x = by["X"]
    assert x.barriers_eV == (0.50, 0.51)
    assert x.source_idx_refs == (0, 0)  # run-local values genuinely collide
    assert x.source_sim_paths == ("runA#0", "runB#0")  # ...but provenance stays distinct

    # unrelated classes never merged and never picked up the other's members
    assert by["Y"].barriers_eV == (0.70,)
    assert by["Y"].source_sim_paths == ("runA#1",)
    assert by["Z"].barriers_eV == (0.90,)
    assert by["Z"].source_sim_paths == ("runB#1",)
    assert set(by) == {"X", "Y", "Z"}


def test_merge_is_order_independent() -> None:
    """Merged class_id order and provenance are independent of run/argument order."""
    a = [_mk("X", barriers=(0.5,), source_idx_refs=(0,)), _mk("A", source_idx_refs=(2,))]
    b = [_mk("X", barriers=(0.6,), source_idx_refs=(0,)), _mk("B", source_idx_refs=(3,))]
    m1 = union_classes([("r1", a), ("r2", b)])
    m2 = union_classes([("r2", b), ("r1", a)])
    assert [c.class_id for c in m1] == [c.class_id for c in m2]
    assert _by_id(m1)["X"].source_sim_paths == _by_id(m2)["X"].source_sim_paths == ("r1#0", "r2#0")
    assert _by_id(m1)["X"].barriers_eV == (0.5, 0.6)  # sorted, deterministic


# --------------------------------------------------------------------------- #
# status conflict: quarantine is run-composition-dependent, never unioned      #
# --------------------------------------------------------------------------- #
def test_previously_quarantined_class_survives_merged_qc() -> None:
    """A class quarantined in one run's QC is re-decided on merged members, not
    carried; when the merged data is clean it survives (status conflict)."""
    # run A quarantined "P" (its member composition tripped reciprocity there); the
    # geometry itself is clean (non-empty delta, no broken pair, no spread).
    run_a = [_mk("P", audit_status="quarantined", audit_reason="QC: reciprocity (run A)")]
    run_b = [_mk("P", audit_status="pending")]  # clean in run B
    rep = merge_qcd_catalogues([("runA", run_a), ("runB", run_b)])
    out = _by_id(rep.classes)["P"]
    assert out.audit_status != "quarantined"  # NOT unioned — re-decided on merged data
    assert rep.status_conflict_count == 1
    assert rep.quarantined_in_any_run == 1


def test_merged_members_can_trip_qc_that_no_single_run_saw() -> None:
    """Merging two clean singletons whose dE_pair disagree > spread_tol quarantines
    the merged class (run-composition-dependent QC on merged members)."""
    run_a = [_mk("S", barriers=(0.50,), dE_pair_list=(0.10,))]
    run_b = [_mk("S", barriers=(0.60,), dE_pair_list=(0.55,))]  # spread 0.45 > 0.1
    rep = merge_qcd_catalogues([("runA", run_a), ("runB", run_b)], spread_tol=0.1)
    out = _by_id(rep.classes)["S"]
    assert out.audit_status == "quarantined"
    assert "CONTEXT_UNDERRESOLVED" in out.audit_reason
    assert rep.status_conflict_count == 0  # neither run had it quarantined


# --------------------------------------------------------------------------- #
# class_id-keyed measured stamp migration                                      #
# --------------------------------------------------------------------------- #
def test_stamp_rate_policy_by_class_id_measured() -> None:
    """stamp_rate_policy stamps harvested_pair by class_id membership (carry-forward)."""
    m = _mk("M", gate_log=_G3_PASS, source_idx_refs=(9,))  # idx not in any idx set
    r = _mk("R", gate_log=_G3_PASS, source_idx_refs=(9,))
    srep = stamp_rate_policy([m, r], measured_class_ids={"M"})
    by = _by_id(srep.classes)
    assert by["M"].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert by["R"].nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH
    assert srep.n_measured == 1 and srep.n_pending_research == 1


def test_stamp_by_class_id_trusts_curated_set_over_g3_fail() -> None:
    """A class in the measured class_id set is stamped measured even if its aggregated
    G3 FAILs (sweep-run snap noise must not overturn the curated representability)."""
    m = _mk("M", gate_log=_G3_FAIL, source_idx_refs=(1,))
    n = _mk("N", gate_log=_G3_FAIL, source_idx_refs=(1,))  # not measured -> non-rep
    srep = stamp_rate_policy([m, n], measured_class_ids={"M"})
    by = _by_id(srep.classes)
    assert by["M"].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert by["N"].nu0_pair_policy is None
    assert srep.n_measured == 1 and srep.n_unstamped_nonrepresentable == 1


def test_stamp_idx_ref_path_still_works() -> None:
    """The historical idx_ref-keyed measured path is unchanged (backward compat)."""
    c = _mk("m", gate_log=_G3_PASS, source_idx_refs=(7,))
    srep = stamp_rate_policy([c], measured_idx_refs={7})
    assert _by_id(srep.classes)["m"].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR


def test_measured_class_ids_from_catalogue() -> None:
    """The measured set helper extracts exactly the harvested_pair class_ids."""
    classes = [
        _mk("a", nu0_pair_policy=NU0_POLICY_HARVESTED_PAIR),
        _mk("b", nu0_pair_policy=NU0_POLICY_PENDING_RESEARCH),
        _mk("c", nu0_pair_policy=None),
    ]
    assert measured_class_ids_from_catalogue(classes) == frozenset({"a"})


def test_merge_stamps_class_id_measured_set() -> None:
    """End-to-end: the merged catalogue stamps the class_id measured set carried from
    a reference catalogue; recovered representable classes go pending_research."""
    run_a = [_mk("M", source_idx_refs=(0,)), _mk("R", source_idx_refs=(1,))]
    run_b = [_mk("M", source_idx_refs=(0,)), _mk("R", source_idx_refs=(1,))]
    rep = merge_qcd_catalogues([("runA", run_a), ("runB", run_b)], measured_class_ids={"M"})
    by = _by_id(rep.classes)
    assert by["M"].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert by["R"].nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH
    assert rep.stamp is not None and rep.stamp.n_measured == 1


def test_merge_without_measured_set_leaves_stamp_none() -> None:
    """An empty measured set skips the stamp step entirely (nothing measured)."""
    rep = merge_qcd_catalogues([("r", [_mk("X")])])
    assert rep.stamp is None
    assert all(c.nu0_pair_policy is None for c in rep.classes)


# --------------------------------------------------------------------------- #
# delta_atoms != 0 stance + purity                                            #
# --------------------------------------------------------------------------- #
def test_nonconserving_counted_not_quarantined() -> None:
    """delta_atoms != 0 classes survive merged QC and are counted (decision 2026-07-24)."""
    rep = merge_qcd_catalogues([("r", [_mk("nc", delta_atoms=1), _mk("ok", delta_atoms=0)])])
    by = _by_id(rep.classes)
    assert by["nc"].audit_status != "quarantined"
    assert rep.nonconserving_surviving == 1


def test_merge_does_not_mutate_inputs() -> None:
    """merge is pure: input EventClass objects are untouched."""
    c = _mk("X", audit_status="quarantined", audit_reason="orig", nu0_pair_policy="x")
    merge_qcd_catalogues([("r", [c])])
    assert c.audit_status == "quarantined"
    assert c.audit_reason == "orig"
    assert c.nu0_pair_policy == "x"
