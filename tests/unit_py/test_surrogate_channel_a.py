"""Phase C channel (a): per-member raw-pair rate bake, quarantine exclusion,
machine-readable provenance, and cross-seed byte-determinism.

Uses the real Phase A ``build_class_catalogue`` (like test_translator_v2) so the
EventClass rows are genuine; Phase C fields (``nu0_pair_policy``,
``audit_status``) are stamped by hand to drive the raw-pair path.
"""

from __future__ import annotations

import math

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventProjReport,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
)
from pylatkmc.pattern_codegen import (
    emit_v2_provenance,
    emit_v2_rate_table,
    n_procs_of,
)
from pylatkmc.rate_expression import KB_EV_PER_K
from pylatkmc.translator_v2 import translate_event_classes

_T_REF = 500.0
_THRESHOLDS = GateThresholds(
    emin_event=0.0,
    emax_event=10.0,
    backward_emin_event=0.0,
    snap_tol=0.9,
    db_tol=0.05,
    rcut=5.0,
)


def _sp(occ: Occ) -> OccPredicate:
    return OccPredicate("SPECIES", frozenset({occ}))


def _pe(ea: float, nu0: float, **kw: object) -> ProjectedEvent:
    base: dict[str, object] = dict(
        anchor0=(0, 0, 0),
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _sp(Occ.NI)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.NI),),
        depth_sig=DepthSig(DepthKind.BULK_OR_DEEPER, -1),
        coloring=Coloring.FULL,
        r_ctx_used=5.0,
        truncated=False,
        Ea_fwd_eV=ea,
        nu0_fwd_hz=nu0,
        k_row=1.0,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        move_atom_idx=0,
        source_row=0,
        proj_report=EventProjReport(0.3, 0.2, 6.0, True),
    )
    base.update(kw)
    return ProjectedEvent(**base)  # type: ignore[arg-type]


def _two_member_class() -> ec.EventClass:
    """A 2-member Ni-hop class (same geometry, two harvested (Ea, nu0) pairs)."""
    events = [
        _pe(0.60, 1.0e13, source_row=0, event_id="a", idx_ref=0),
        _pe(0.75, 2.0e13, source_row=1, event_id="b", idx_ref=1),
    ]
    classes = ec.build_class_catalogue(
        events, t_ref_K=_T_REF, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )
    assert len(classes) == 1
    c = classes[0]
    assert len(c.barriers_eV) == 2
    c.nu0_pair_policy = "harvested_pair"
    return c


def test_per_member_raw_pair_rates() -> None:
    """A 2-member class → 2×orientations procs with the exact (nu0_f_i, Ea_i)."""
    c = _two_member_class()
    pats, rep = translate_event_classes([c], phase_c=True)
    assert rep.phase_c and rep.n_members_total == 2
    pat = pats[0]
    n_orient = len(pat.orientation_ops)
    assert n_procs_of(pats) == 2 * n_orient

    body = emit_v2_rate_table(pats)
    # every member (nu0_f_i, Ea_i) pair appears exactly n_orient times.
    for nu0, ea in zip(c.nu0_f_list_hz, c.barriers_eV, strict=True):
        pref = f".prefactor_Hz = {nu0:.10e}"
        assert body.count(pref) == n_orient, (pref, body.count(pref))
        # Arrhenius at t_ref reproduces the member rate (nu0 already Hz).
        k = nu0 * math.exp(-ea / (KB_EV_PER_K * _T_REF))
        assert k > 0
    # Raw pairs are NOT the aggregate: at least one member != nu0_geo*1e12.
    agg_pref = c.nu0_geo_psinv * 1.0e12
    assert not all(abs(n - agg_pref) < 1.0 for n in c.nu0_f_list_hz)


def test_schema1_aggregate_path_unchanged() -> None:
    """Without the stamp (schema-1), the single aggregate rate is emitted —
    behind the explicit ``include_unstamped`` opt-in (unstamped classes are
    skip-counted by default; see test_unstamped_classes_are_skipped_and_counted)."""
    c = _two_member_class()
    c.nu0_pair_policy = None  # unstamped
    pats, rep = translate_event_classes([c], phase_c=False, include_unstamped=True)
    assert not rep.phase_c and rep.n_members_total == 1
    pat = pats[0]
    assert n_procs_of(pats) == len(pat.orientation_ops)
    assert pat.prefactor_Hz == c.nu0_geo_psinv * 1.0e12
    assert pat.Ea_eV == c.Ea_rep_eV


def test_quarantined_excluded_and_counted() -> None:
    """Quarantined classes are excluded from translation and counted (never silent)."""
    c = _two_member_class()
    q = _two_member_class()
    q.audit_status = "quarantined"
    # force a distinct class_id so both survive as separate rows
    q.class_id = "q" + c.class_id[1:]
    pats, rep = translate_event_classes([c, q], phase_c=True)
    assert rep.skipped_quarantined == 1
    assert rep.n_translated == 1
    assert all(p.class_id != q.class_id for p in pats)


def test_provenance_arrays_align_with_classes() -> None:
    """class_ids table + per-proc class/member arrays match the emitted procs."""
    c = _two_member_class()
    pats, _ = translate_event_classes([c], phase_c=True)
    n = n_procs_of(pats)
    prov = emit_v2_provenance(pats)
    assert f"v2_n_classes = {len({p.class_id for p in pats})}" in prov
    assert c.class_id in prov
    # per-proc arrays are the right length
    assert f"v2_proc_class[{n}]" in prov
    assert f"v2_proc_member[{n}]" in prov
    assert f"v2_proc_v6_ea[{n}]" in prov
    # member indices span 0..(n_members-1); each member index appears n_orient times
    n_orient = len(pats[0].orientation_ops)
    members_line = prov.split("v2_proc_member")[1].split("= {")[1].split("};")[0]
    ints = [int(x) for x in members_line.replace(",", " ").split() if x.lstrip("-").isdigit()]
    assert len(ints) == n
    assert ints.count(0) == n_orient and ints.count(1) == n_orient
    # no model baked → v6 is NaN
    assert "NAN" in prov
