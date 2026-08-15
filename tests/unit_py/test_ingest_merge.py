"""Cross-run class-level merge of per-run ``EventClass`` catalogues.

Pure-logic tests — the merge operates on ``EventClass`` lists and needs no extras.
Covers the three merge invariants the probe flagged: idx_ref collision across runs
(provenance stays disambiguated, no cross-linking), status conflicts (a
previously-quarantined class surviving merged QC), and the class_id-keyed measured
stamp migration — plus the B4 element-set guard (2026-08-14 readiness review): a
NiCr + NiFe merge must not succeed silently. The CLI-level guard tests need
``pyarrow`` (Parquet round-trip) and ``importorskip`` out without it.
"""

from __future__ import annotations

import pytest

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    Occ,
    OccPredicate,
    StencilSite,
    catalogue_elements,
)
from pylatkmc.ingest.merge import (
    element_census,
    measured_class_ids_from_catalogue,
    merge_qcd_catalogues,
    parse_elements,
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
    context: tuple[StencilSite, ...] = (),
    arrows: tuple[Arrow, ...] = (),
    anchor_pred: OccPredicate | None = None,
    coloring: Coloring = Coloring.FULL,
    canon_version: int = 1,
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
    cf = (canon_version, 0, 0, 0, 0, (), (), ())
    return EventClass(
        class_id=class_id,
        canonical_form=cf,
        canonical_blob=ec._tlv_encode(cf),
        depth_sig=DepthSig(DepthKind.SURFACE, 0),
        coloring=coloring,
        move_shape=0,
        delta=delta,
        delta_atoms=delta_atoms,
        context=context,
        saddle_token=(),
        orientation_count=1,
        r_ctx_used=5.0,
        r_id_used=5.0,
        anchor_pred=anchor_pred if anchor_pred is not None else OccPredicate("WILDCARD"),
        arrows=arrows,
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


# --------------------------------------------------------------------------- #
# B4: element-set guard (2026-08-14 ingest-readiness review)                   #
# --------------------------------------------------------------------------- #
def _sp(o: Occ) -> OccPredicate:
    return OccPredicate("SPECIES", frozenset({o}))


def _alloy_class(class_id: str, solute: Occ | None, **kw) -> EventClass:
    """A class carrying Ni + one solute across delta / context / arrows / anchor."""
    delta = (DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI))
    context = (StencilSite((2, 0, 0), _sp(Occ.NI)), StencilSite((0, 2, 0), OccPredicate("EMPTY")))
    if solute is not None:
        context = (*context, StencilSite((0, 0, 2), _sp(solute)))
    return _mk(class_id, delta=delta, context=context, **kw)


def _legacy_class(class_id: str, solute: Occ | None) -> EventClass:
    """A pre-guard (schema<=3 shaped) class: species only in delta/context, no arrows."""
    delta = (DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),)
    context = ()
    if solute is not None:
        delta = (*delta, DeltaSite((1, 1, 0), solute, Occ.EMPTY))
    return _mk(class_id, delta=delta, context=context, arrows=())


def test_catalogue_elements_reads_every_identity_field() -> None:
    """The element set is recovered from delta, context, anchor_pred AND arrows."""
    c = _mk(
        "X",
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),),
        context=(StencilSite((2, 0, 0), _sp(Occ.CR)),),
        anchor_pred=_sp(Occ.NI),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.FE),),
    )
    assert catalogue_elements([c]) == ("Cr", "Fe", "Ni")


def test_catalogue_elements_skips_non_species_codes() -> None:
    """EMPTY / WILDCARD / OUTSIDE / OCC_ANY carry no element (GREY reports nothing)."""
    grey = _mk(
        "G",
        delta=(DeltaSite((0, 0, 0), Occ.OCC_ANY, Occ.EMPTY),),
        context=(
            StencilSite((2, 0, 0), OccPredicate("WILDCARD")),
            StencilSite((0, 2, 0), OccPredicate("OUTSIDE")),
            StencilSite((0, 0, 2), OccPredicate("OCC_ANY")),
        ),
        coloring=Coloring.GREY,
    )
    assert catalogue_elements([grey]) == ()


def test_element_census_matched_runs_pass() -> None:
    """Same-alloy runs agree: no conflict, one group, union = the alloy."""
    runs = [
        ("NiCr_T300_1vac", [_alloy_class("a", Occ.CR), _alloy_class("b", Occ.CR)]),
        ("NiCr_T500_4vac", [_alloy_class("a", Occ.CR)]),
    ]
    census = element_census(runs)
    assert census.ok
    assert census.conflicts == ()
    assert census.union == ("Cr", "Ni")
    assert census.tags_by_elements == ((("Cr", "Ni"), ("NiCr_T300_1vac", "NiCr_T500_4vac")),)
    assert "Cr,Ni" in census.summary()


def test_element_census_refuses_nicr_plus_nife() -> None:
    """The B4 hole: {Ni,Cr} + {Ni,Fe} is incomparable — flagged, never silent."""
    census = element_census(
        [
            ("NiCr_T300_1vac", [_alloy_class("a", Occ.CR)]),
            ("NiFe_T300_1vac", [_alloy_class("b", Occ.FE)]),
        ]
    )
    assert not census.ok
    assert census.conflicts == ((("Cr", "Ni"), ("Fe", "Ni")),)
    assert census.union == ("Cr", "Fe", "Ni")
    assert "CONFLICT" in census.summary()


def test_element_census_subset_run_is_not_a_conflict() -> None:
    """A same-alloy run that catalogued no solute event is a SUBSET, not a mismatch."""
    census = element_census(
        [
            ("NiCr_T300_1vac", [_alloy_class("a", Occ.CR)]),
            ("NiCr_T300_2vac", [_alloy_class("b", None)]),  # no Cr sampled
        ]
    )
    assert census.ok
    assert census.union == ("Cr", "Ni")
    assert census.tags_by_elements == (
        (("Cr", "Ni"), ("NiCr_T300_1vac",)),
        (("Ni",), ("NiCr_T300_2vac",)),
    )


def test_element_census_legacy_catalogues_are_measured_not_assumed() -> None:
    """Legacy (pre-guard, no stamp, no arrows) inputs: matched pass, mismatched refuse.

    Nothing on disk carries an element stamp, so the guard must infer from content —
    two legacy catalogues of different alloys must not be treated as compatible.
    """
    matched = element_census(
        [("r1", [_legacy_class("a", Occ.CR)]), ("r2", [_legacy_class("b", Occ.CR)])]
    )
    assert matched.ok and matched.union == ("Cr", "Ni")

    mismatched = element_census(
        [("r1", [_legacy_class("a", Occ.CR)]), ("r2", [_legacy_class("b", Occ.FE)])]
    )
    assert not mismatched.ok
    assert mismatched.conflicts == ((("Cr", "Ni"), ("Fe", "Ni")),)


def test_element_census_speciesless_inputs_are_surfaced_not_refused() -> None:
    """A GREY (species-blind) input cannot conflict — but it is counted and reported."""
    grey = _mk("g", delta=(), context=(), coloring=Coloring.GREY)
    census = element_census([("grey_run", [grey]), ("NiCr", [_alloy_class("a", Occ.CR)])])
    assert census.ok
    assert census.speciesless_tags == ("grey_run",)
    assert "species-blind" in census.summary()


def test_element_census_is_order_independent() -> None:
    """Census output does not depend on input order (determinism invariant)."""
    a = ("NiCr_A", [_alloy_class("a", Occ.CR)])
    b = ("NiFe_B", [_alloy_class("b", Occ.FE)])
    c1, c2 = element_census([a, b]), element_census([b, a])
    assert c1 == c2


def test_parse_elements_normalises_and_rejects_unknown() -> None:
    """--require-elements parses order-insensitively and rejects a typo loudly."""
    assert parse_elements("Ni,Cr") == ("Cr", "Ni")
    assert parse_elements(" Cr , Ni ") == ("Cr", "Ni")
    with pytest.raises(ValueError, match="unknown element symbol"):
        parse_elements("Ni,Al")


# --------------------------------------------------------------------------- #
# B4 at the CLI: refuse / override / record (needs pyarrow for the round-trip) #
# --------------------------------------------------------------------------- #
def _write_run(path, classes) -> None:
    """Write a per-run catalogue Parquet (classes must be on the CURRENT canon)."""
    from pylatkmc.ingest.event_class import write_catalogue_parquet

    write_catalogue_parquet(classes, path)


def _cli_run(cid: str, solute: Occ | None) -> EventClass:
    """An alloy class stamped with the current CANON version (``assert_canon_version``)."""
    from pylatkmc.ingest.canonical import CANON_SCHEMA_VERSION

    return _alloy_class(cid, solute, canon_version=CANON_SCHEMA_VERSION)


def _elements_metadata(path) -> str:
    import pyarrow.parquet as pq

    from pylatkmc.ingest.event_class import ELEMENTS_METADATA_KEY

    md = pq.read_schema(path).metadata or {}
    return md[ELEMENTS_METADATA_KEY].decode("utf-8")


def test_cli_merge_matched_elements_pass_and_record_the_set(tmp_path, capsys) -> None:
    """Matched inputs merge, and the artifact records the element set it is over."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a, b = tmp_path / "a.parquet", tmp_path / "b.parquet"
    _write_run(a, [_cli_run("a", Occ.CR)])
    _write_run(b, [_cli_run("b", Occ.CR)])
    out = tmp_path / "merged.parquet"
    rc = main(["merge", "--in", f"NiCr_A={a}", "--in", f"NiCr_B={b}", "--out", str(out)])
    assert rc == 0
    assert _elements_metadata(out) == "Cr,Ni"
    assert "elements=Cr,Ni element_conflicts=0" in capsys.readouterr().out


def test_cli_merge_refuses_mismatched_elements(tmp_path, capsys) -> None:
    """NiCr + NiFe: refused, nothing written, and the reason is on stderr."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a, b = tmp_path / "nicr.parquet", tmp_path / "nife.parquet"
    _write_run(a, [_cli_run("a", Occ.CR)])
    _write_run(b, [_cli_run("b", Occ.FE)])
    out = tmp_path / "merged.parquet"
    rc = main(["merge", "--in", f"NiCr={a}", "--in", f"NiFe={b}", "--out", str(out)])
    assert rc == 2
    assert not out.exists()
    assert "refuses incomparable element sets" in capsys.readouterr().err


def test_cli_merge_element_mismatch_override_is_explicit_and_loud(tmp_path, capsys) -> None:
    """--allow-element-mismatch proceeds, warns, and records the ternary set."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a, b = tmp_path / "nicr.parquet", tmp_path / "nife.parquet"
    _write_run(a, [_cli_run("a", Occ.CR)])
    _write_run(b, [_cli_run("b", Occ.FE)])
    out = tmp_path / "merged.parquet"
    rc = main(
        [
            "merge",
            "--in",
            f"NiCr={a}",
            "--in",
            f"NiFe={b}",
            "--out",
            str(out),
            "--allow-element-mismatch",
        ]
    )
    assert rc == 0
    assert _elements_metadata(out) == "Cr,Fe,Ni"
    cap = capsys.readouterr()
    assert "--allow-element-mismatch was given" in cap.err
    assert "elements=Cr,Fe,Ni element_conflicts=1" in cap.out


def test_cli_merge_require_elements_refuses_wrong_artifact(tmp_path, capsys) -> None:
    """--require-elements asserts what the artifact comes out as (typo-proof)."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a = tmp_path / "nicr.parquet"
    _write_run(a, [_cli_run("a", Occ.CR)])
    out = tmp_path / "merged.parquet"
    argv = ["merge", "--in", f"NiCr={a}", "--out", str(out)]
    assert main([*argv, "--require-elements", "Ni,Fe"]) == 2
    assert not out.exists()
    assert "--require-elements" in capsys.readouterr().err
    assert main([*argv, "--require-elements", "Cr,Ni"]) == 0
    assert out.exists()
