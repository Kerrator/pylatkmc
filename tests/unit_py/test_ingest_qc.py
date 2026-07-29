"""Ingest QC screens + schema-v2 persistence (Phase C ingest-QC leg).

Pure-logic screen tests need no extras; the Parquet round-trip / back-compat tests
``importorskip`` pyarrow so a bare CI run stays green.
"""

from __future__ import annotations

import pytest

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
from pylatkmc.ingest.qc import (
    NU0_POLICY_HARVESTED_PAIR,
    NU0_POLICY_PENDING_RESEARCH,
    apply_qc,
    graduate_classes,
    load_overlay,
    stamp_rate_policy,
)

_G3_PASS = (ec.GateResult("G3", ec.GateOutcome.PASS, "max_residual=0.1 < 0.9", 0.1),)
_G3_FAIL = (ec.GateResult("G3", ec.GateOutcome.FAIL, "UNMAPPABLE", 1.4),)

# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #
_ONE_DELTA = (DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),)


def _mk(
    class_id: str,
    *,
    backward_class: str | None = None,
    dEnergy: float | None = None,
    delta: tuple[DeltaSite, ...] = _ONE_DELTA,
    barriers: tuple[float, ...] = (0.5,),
    dE_pair_list: tuple[float, ...] = (),
    source_rows: tuple[int, ...] = (0,),
    source_idx_refs: tuple[int, ...] = (0,),
    audit_status: str = "pending",
    audit_reason: str = "",
    phi: tuple[float, ...] = (),
    fallback_stats: tuple[object, ...] = (),
    model_version: str | None = None,
    dE_model_version: str | None = None,
    nu0_pair_policy: str | None = None,
    gate_log: tuple[ec.GateResult, ...] = (),
) -> EventClass:
    """A minimal but valid EventClass for QC/round-trip tests (class_id is arbitrary)."""
    cf = (1, 0, 0, 0, 0, (), (), ())
    blob = ec._tlv_encode(cf)
    return EventClass(
        class_id=class_id,
        canonical_form=cf,
        canonical_blob=blob,
        depth_sig=DepthSig(DepthKind.SURFACE, 0),
        coloring=Coloring.FULL,
        move_shape=0,
        family_id=0,
        delta=delta,
        delta_atoms=0,
        context=(),
        saddle_token=(),
        orientation_count=1,
        r_ctx_used=5.0,
        r_id_used=5.0,
        anchor_pred=OccPredicate("WILDCARD"),
        t_ref_K=500.0,
        barriers_eV=barriers,
        nu0_f_list_hz=tuple(1e13 for _ in barriers),
        nu0_b_list_hz=tuple(1e13 for _ in barriers),
        dE_pair_list_eV=dE_pair_list,
        k_rate_mean_psinv=1.0,
        Ea_rep_eV=barriers[0],
        nu0_geo_psinv=10.0,
        Ea_std_eV=None,
        n_eff=float(len(barriers)),
        Ea_mean_eV=barriers[0],
        Ea_median_eV=barriers[0],
        phi=phi,
        model_version=model_version,
        dE_model_version=dE_model_version,
        nu0_pair_policy=nu0_pair_policy,
        backward_class=backward_class,
        dEnergy_eV=dEnergy,
        source_rows=source_rows,
        source_idx_refs=source_idx_refs,
        audit_status=audit_status,  # type: ignore[arg-type]
        audit_reason=audit_reason,
        fallback_stats=fallback_stats,
        gate_log=gate_log,
    )


def _by_id(report) -> dict[str, EventClass]:
    return {c.class_id: c for c in report.classes}


# --------------------------------------------------------------------------- #
# reciprocity screen                                                          #
# --------------------------------------------------------------------------- #
def test_reciprocity_broken_pair_quarantines_both() -> None:
    """|dE_f + dE_b| > tol quarantines BOTH linked directions with the pair reason."""
    fwd = _mk("f", backward_class="b", dEnergy=+0.20)
    bwd = _mk("b", backward_class="f", dEnergy=+0.55)  # 0.75 != 0 -> broken
    rep = apply_qc([fwd, bwd])
    out = _by_id(rep)
    assert out["f"].audit_status == "quarantined"
    assert out["b"].audit_status == "quarantined"
    assert "pair reciprocity broken" in out["f"].audit_reason
    assert rep.reciprocity_quarantined == 2


def test_reciprocity_consistent_pair_kept() -> None:
    """A consistent pair (dE_f + dE_b ~= 0) is not quarantined."""
    fwd = _mk("f", backward_class="b", dEnergy=+0.30)
    bwd = _mk("b", backward_class="f", dEnergy=-0.30)
    rep = apply_qc([fwd, bwd])
    out = _by_id(rep)
    assert out["f"].audit_status == "pending"
    assert out["b"].audit_status == "pending"
    assert rep.reciprocity_quarantined == 0


def test_reciprocity_backward_not_in_catalogue_is_skipped() -> None:
    """A backward_class absent from the catalogue is not screened (no partner dE)."""
    fwd = _mk("f", backward_class="missing", dEnergy=+0.9)
    rep = apply_qc([fwd])
    assert _by_id(rep)["f"].audit_status == "pending"
    assert rep.reciprocity_quarantined == 0


def test_self_reverse_nonzero_dE_quarantined() -> None:
    """A self-linked class (backward == self) with dE != 0 is quarantined."""
    c = _mk("s", backward_class="s", dEnergy=-0.38)
    rep = apply_qc([c])
    out = _by_id(rep)["s"]
    assert out.audit_status == "quarantined"
    assert "self-reverse with dE != 0" in out.audit_reason
    assert rep.reciprocity_quarantined == 1


def test_self_reverse_zero_dE_kept() -> None:
    """A true self-reverse (dE == 0) is not a defect."""
    c = _mk("s", backward_class="s", dEnergy=0.0)
    rep = apply_qc([c])
    assert _by_id(rep)["s"].audit_status == "pending"
    assert rep.reciprocity_quarantined == 0


# --------------------------------------------------------------------------- #
# delta-less screen                                                           #
# --------------------------------------------------------------------------- #
def test_deltaless_quarantined() -> None:
    """An empty delta is not executable -> quarantined."""
    c = _mk("d", delta=())
    rep = apply_qc([c])
    out = _by_id(rep)["d"]
    assert out.audit_status == "quarantined"
    assert "empty delta" in out.audit_reason
    assert rep.deltaless_quarantined == 1


def test_nonempty_delta_kept() -> None:
    """A non-empty delta passes the delta-less screen."""
    rep = apply_qc([_mk("d", delta=_ONE_DELTA)])
    assert _by_id(rep)["d"].audit_status == "pending"
    assert rep.deltaless_quarantined == 0


# --------------------------------------------------------------------------- #
# within-class dE-spread screen (quarantine; memo 2026-07-22 §3.5)            #
# --------------------------------------------------------------------------- #
def test_spread_quarantines() -> None:
    """>=2 members with dE_pair spread > tol is CONTEXT_UNDERRESOLVED: quarantined."""
    c = _mk("g", barriers=(0.5, 0.6), dE_pair_list=(0.10, 0.45))  # spread 0.35
    rep = apply_qc([c])
    out = _by_id(rep)["g"]
    assert out.audit_status == "quarantined"
    assert "CONTEXT_UNDERRESOLVED" in out.audit_reason
    assert rep.spread_quarantined == 1
    assert rep.spread_events == 1


def test_spread_below_tol_not_flagged() -> None:
    """A tight within-class dE spread is untouched."""
    c = _mk("g", barriers=(0.5, 0.6), dE_pair_list=(0.10, 0.12))  # spread 0.02
    rep = apply_qc([c])
    assert _by_id(rep)["g"].audit_status == "pending"
    assert _by_id(rep)["g"].audit_reason == ""
    assert rep.spread_quarantined == 0


def test_earlier_screen_wins_attribution_over_spread() -> None:
    """A self-linked defect that also has wide spread attributes to reciprocity."""
    # self-linked (dE != 0) AND wide dE_pair spread
    c = _mk("s", backward_class="s", dEnergy=-0.4, barriers=(0.5, 0.6), dE_pair_list=(0.1, 0.9))
    rep = apply_qc([c])
    out = _by_id(rep)["s"]
    assert out.audit_status == "quarantined"
    assert "self-reverse" in out.audit_reason  # first-screen-wins reason
    assert rep.reciprocity_quarantined == 1
    assert rep.spread_quarantined == 0  # attribution is disjoint
    assert rep.total_quarantined == 1


# --------------------------------------------------------------------------- #
# human-veto overlay + stickiness                                             #
# --------------------------------------------------------------------------- #
def test_overlay_quarantines_new_class() -> None:
    """An overlay entry quarantines an otherwise-clean class with the veto reason."""
    rep = apply_qc([_mk("x")], overlay={"x": "curator: unreachable-state reverse"})
    out = _by_id(rep)["x"]
    assert out.audit_status == "quarantined"
    assert "human veto" in out.audit_reason
    assert "unreachable-state reverse" in out.audit_reason
    assert rep.overlay_quarantined == 1


def test_overlay_for_missing_class_is_surfaced_not_applied() -> None:
    """An overlay entry for a class not in the catalogue is reported, never silent."""
    rep = apply_qc([_mk("x")], overlay={"not-here": "veto"})
    assert _by_id(rep)["x"].audit_status == "pending"
    assert rep.overlay_quarantined == 0
    assert rep.overlay_unmatched == ("not-here",)
    assert "orphaned vetoes" in rep.summary()


def test_preexisting_quarantine_is_never_downgraded() -> None:
    """A class quarantined on input stays quarantined on output (re-emission is sticky)."""
    c = _mk("q", audit_status="quarantined", audit_reason="curator: excluded")
    rep = apply_qc([c])
    out = _by_id(rep)["q"]
    assert out.audit_status == "quarantined"
    assert out.audit_reason == "curator: excluded"
    assert rep.preexisting_quarantined == 1
    assert rep.total_quarantined == 1


def test_schema_version_bumped_on_all_output() -> None:
    """Every re-emitted class carries the current schema_version, quarantined or not."""
    rep = apply_qc([_mk("a"), _mk("d", delta=())])
    assert {c.schema_version for c in rep.classes} == {ec.CATALOGUE_SCHEMA_VERSION}
    # v3 = per-member snap residual columns (over-snapping memo 2026-07-29 §11).
    assert ec.CATALOGUE_SCHEMA_VERSION == 3


def test_apply_qc_does_not_mutate_inputs() -> None:
    """apply_qc is pure: the input EventClass objects are untouched."""
    c = _mk("d", delta=())
    apply_qc([c])
    assert c.audit_status == "pending"
    assert c.audit_reason == ""


def test_report_totals_are_disjoint_sum() -> None:
    """total_quarantined is the disjoint sum of the per-screen attributions."""
    classes = [
        _mk("f", backward_class="b", dEnergy=+0.2),
        _mk("b", backward_class="f", dEnergy=+0.6),  # broken pair -> 2
        _mk("d", delta=()),  # delta-less -> 1
        _mk("g", barriers=(0.5, 0.6), dE_pair_list=(0.10, 0.45)),  # spread -> 1
        _mk("clean"),
    ]
    rep = apply_qc(classes, overlay={"clean": "veto it"})  # overlay -> 1
    assert rep.reciprocity_quarantined == 2
    assert rep.deltaless_quarantined == 1
    assert rep.spread_quarantined == 1
    assert rep.overlay_quarantined == 1
    assert rep.total_quarantined == 5
    assert (
        rep.total_quarantined
        == rep.reciprocity_quarantined
        + rep.deltaless_quarantined
        + rep.spread_quarantined
        + rep.overlay_quarantined
        + rep.preexisting_quarantined
    )


# --------------------------------------------------------------------------- #
# overlay loading (TOML + JSON)                                               #
# --------------------------------------------------------------------------- #
def test_load_overlay_json(tmp_path) -> None:
    """A JSON overlay round-trips into a class_id -> reason mapping."""
    p = tmp_path / "veto.json"
    p.write_text('{"abc": "mislink", "def": "artifact"}', encoding="utf-8")
    assert load_overlay(p) == {"abc": "mislink", "def": "artifact"}


def test_load_overlay_toml_wrapped(tmp_path) -> None:
    """A TOML overlay under an [overlay] table is unwrapped."""
    p = tmp_path / "veto.toml"
    p.write_text('[overlay]\nabc = "mislink"\n', encoding="utf-8")
    assert load_overlay(p) == {"abc": "mislink"}


# --------------------------------------------------------------------------- #
# schema-v2 Parquet persistence + schema-1 back-compat                        #
# --------------------------------------------------------------------------- #
def test_schema_v2_round_trip_new_fields(tmp_path) -> None:
    """phi / fallback_stats / audit_reason / [C] model fields survive write->read."""
    pytest.importorskip("pyarrow")
    src = _mk(
        "z",
        audit_reason="QC: within-class dE spread 0.30 eV — CONTEXT_UNDERRESOLVED (dE channel)",
        phi=(1.0, 2.5, -0.25),
        fallback_stats=(0.42, True, "E_sym_v1", 1),
        model_version="E_sym_v1_ridge",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        nu0_pair_policy="harvested_pair",
    )
    path = tmp_path / "qc.parquet"
    ec.write_catalogue_parquet([src], path)
    (back,) = ec.read_catalogue_parquet(path)
    assert back.audit_reason == src.audit_reason
    assert back.phi == src.phi
    assert back.fallback_stats == src.fallback_stats
    assert back.model_version == src.model_version
    assert back.dE_model_version == src.dE_model_version
    assert back.nu0_pair_policy == src.nu0_pair_policy
    assert back.schema_version == ec.CATALOGUE_SCHEMA_VERSION


def test_write_with_metadata(tmp_path) -> None:
    """File-level metadata (the QC conditions stamp) is attached to the schema."""
    pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    path = tmp_path / "qc.parquet"
    ec.write_catalogue_parquet([_mk("z")], path, metadata={b"pylatkmc.qc.conditions": b"stamp-xyz"})
    md = pq.read_schema(path).metadata or {}
    assert md.get(b"pylatkmc.qc.conditions") == b"stamp-xyz"


def test_schema_v1_read_back_compat(tmp_path) -> None:
    """A schema-1 parquet (no v2 columns) reads back with the new fields defaulted."""
    pytest.importorskip("pyarrow")
    import pyarrow as pa
    import pyarrow.parquet as pq

    src = _mk("z", phi=(9.0,), fallback_stats=(1.0,), audit_reason="ignored-in-v1")
    src.schema_version = 1  # emulate a genuine schema-1 record
    row = ec._event_to_row(src)
    v2_schema = ec.catalogue_arrow_schema()
    v2_only = {
        "audit_reason",
        "phi",
        "model_version",
        "dE_model_version",
        "nu0_pair_policy",
        "fallback_stats",
    }
    v1_fields = [f for f in v2_schema if f.name not in v2_only]
    v1_schema = pa.schema(v1_fields)
    columns = {f.name: pa.array([row[f.name]], type=f.type) for f in v1_fields}
    table = pa.Table.from_pydict(columns, schema=v1_schema)
    path = tmp_path / "v1.parquet"
    pq.write_table(table, path)

    # the written file genuinely lacks the v2 columns
    assert "phi" not in pq.read_schema(path).names
    (back,) = ec.read_catalogue_parquet(path)
    assert back.audit_reason == ""
    assert back.phi == ()
    assert back.model_version is None
    assert back.dE_model_version is None
    assert back.nu0_pair_policy is None
    assert back.fallback_stats == ()
    assert back.schema_version == 1  # the stored value is preserved verbatim


# --------------------------------------------------------------------------- #
# rate-policy stamping (memo 2026-07-22 §3.2–3.3)                             #
# --------------------------------------------------------------------------- #
def test_stamp_measured_class_fires_harvested_pairs() -> None:
    """A representable class carrying a previously-measured idx_ref -> harvested_pair."""
    c = _mk("m", gate_log=_G3_PASS, source_idx_refs=(7,))
    srep = stamp_rate_policy([c], measured_idx_refs={7})
    (out,) = srep.classes
    assert out.nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert srep.n_measured == 1 and srep.n_pending_research == 0


def test_stamp_recovered_class_is_pending_research() -> None:
    """A representable class with NO measured member is stamped pending_research."""
    c = _mk("r", gate_log=_G3_PASS, source_idx_refs=(9,))
    srep = stamp_rate_policy([c], measured_idx_refs={7})
    (out,) = srep.classes
    assert out.nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH
    assert "PENDING_RE_SEARCH" in out.audit_reason
    assert srep.n_pending_research == 1


def test_stamp_leaves_nonrepresentable_and_quarantined_unstamped() -> None:
    """G3-FAIL classes and quarantined classes get no policy stamp."""
    u = _mk("u", gate_log=_G3_FAIL, source_idx_refs=(7,))
    q = _mk(
        "q",
        gate_log=_G3_PASS,
        source_idx_refs=(7,),
        audit_status="quarantined",
        audit_reason="QC: defect",
    )
    srep = stamp_rate_policy([q, u], measured_idx_refs={7})
    by = {c.class_id: c for c in srep.classes}
    assert by["u"].nu0_pair_policy is None
    assert by["q"].nu0_pair_policy is None
    assert by["q"].audit_status == "quarantined"
    assert srep.n_unstamped_nonrepresentable == 1
    assert srep.n_quarantined_untouched == 1


def test_stamp_is_pure_and_sorted() -> None:
    """stamp_rate_policy re-emits new instances in class_id order; inputs untouched."""
    a = _mk("b", gate_log=_G3_PASS, source_idx_refs=(1,))
    b = _mk("a", gate_log=_G3_PASS, source_idx_refs=(2,))
    srep = stamp_rate_policy([a, b], measured_idx_refs={1})
    assert [c.class_id for c in srep.classes] == ["a", "b"]
    assert a.nu0_pair_policy is None and b.nu0_pair_policy is None


# --------------------------------------------------------------------------- #
# re-search graduation gate (memo 2026-07-22 §3.4)                            #
# --------------------------------------------------------------------------- #
def _pending(cid: str, ea: float) -> EventClass:
    return _mk(cid, barriers=(ea,), gate_log=_G3_PASS, nu0_pair_policy=NU0_POLICY_PENDING_RESEARCH)


def test_graduate_within_band_fires_harvested_pairs() -> None:
    """|Ea_research - Ea_harvested| <= band graduates the class to harvested_pair."""
    c = _pending("p", 0.50)
    rep = graduate_classes([c], research_ea_by_class={"p": 0.53}, band_eV=0.05)
    (out,) = rep.classes
    assert out.nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert "graduated" in out.audit_reason
    assert rep.n_graduated == 1 and rep.n_context_suspect == 0
    assert rep.review_rows == []


def test_graduate_outside_band_is_context_suspect() -> None:
    """Above the band the class stays pending and lands on the review list."""
    c = _pending("p", 0.50)
    rep = graduate_classes([c], research_ea_by_class={"p": 0.70}, band_eV=0.05)
    (out,) = rep.classes
    assert out.nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH  # stays out of measured
    assert "CONTEXT_SUSPECT" in out.audit_reason
    assert rep.n_context_suspect == 1
    assert len(rep.review_rows) == 1
    assert rep.review_rows[0]["class_id"] == "p"


def test_graduate_without_result_stays_pending() -> None:
    """A pending class with no re-search row is untouched (still pending)."""
    c = _pending("p", 0.50)
    rep = graduate_classes([c], research_ea_by_class={}, band_eV=0.05)
    (out,) = rep.classes
    assert out.nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH
    assert rep.n_unresolved == 1


def test_graduate_never_touches_measured_or_quarantined() -> None:
    """Research rows naming non-pending classes are counted and ignored."""
    m = _mk("m", gate_log=_G3_PASS, nu0_pair_policy=NU0_POLICY_HARVESTED_PAIR)
    q = _mk("q", audit_status="quarantined", audit_reason="QC: defect")
    rep = graduate_classes([m, q], research_ea_by_class={"m": 0.5, "q": 0.5})
    by = {c.class_id: c for c in rep.classes}
    assert by["m"].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert by["q"].audit_status == "quarantined"
    assert rep.n_ignored_nonpending == 2
    assert rep.n_pending_in == 0
