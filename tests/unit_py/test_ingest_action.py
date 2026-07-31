"""Action x context fingerprint tests (Phase 1; memo ACTION_FINGERPRINT_DESIGN_2026-07-29).

Phase 1 (memo §7) under the 2026-07-30 interview rulings (§11) is purely additive:
arrows are captured at projection time and four columns (``arrows`` / ``action_id`` /
``archetype`` / ``one_way``) join the catalogue + discard ledger. Nothing here may
touch ``class_id`` — the last test in this file is that guard.

The four invariants the design turns on:

* **(a)** a projected event and its reverse produce the same ``action_id``
  (the canon is ``min`` over ``{A, A⁻¹} x anchors x D4h``, memo §3.1);
* **(b)** ``action_id`` is invariant under every D4h op (and any translation);
* **(c)** a species relabel changes ``action_id`` but **not** ``archetype``
  (species live on the arrows; the archetype is the grey level — ruling 1);
* **(d)** a schema-3 parquet still reads, new fields at their defaults
  (the v1->v2->v3 additive-read-compat precedent).

Pure numpy/stdlib except the parquet round-trips (``importorskip``), matching the
house style of ``test_ingest_canonical`` / ``test_ingest_oversnap``.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from pylatkmc.ingest import action as A
from pylatkmc.ingest import canonical as C
from pylatkmc.ingest import event_class as ecm
from pylatkmc.ingest.event_class import (
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    EventProjReport,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
    build_class_catalogue,
)
from pylatkmc.ingest.event_projection import project_event
from pylatkmc.ingest.lattice import D4H, apply_op
from pylatkmc.ingest.qc import (
    ACTION_REVIEW_FIELDS,
    append_action_review_rows,
    apply_qc,
)
from pylatkmc.ingest.reftable import (
    ReftableBuildReport,
    discard_ledger_path,
    project_reference_table,
    write_discard_ledger_parquet,
)

H = 1.76  # a/2 for a = 3.52 A
NN = H * math.sqrt(2.0)  # 1NN spacing ~ 2.489 A


# --------------------------------------------------------------------------- #
# Builders                                                                    #
# --------------------------------------------------------------------------- #
def _hop_arrows() -> tuple[Arrow, ...]:
    """A single Ni 1NN in-plane hop: (0,0,0) -> (1,1,0)."""
    return (Arrow((0, 0, 0), (1, 1, 0), Occ.NI),)


def _chain_arrows() -> tuple[Arrow, ...]:
    """A straight 2-chain (relay): B -> A's site, C -> B's site."""
    return (
        Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
        Arrow((-1, -1, 0), (0, 0, 0), Occ.CR),
    )


def _move(arrows, g, t=(0, 0, 0)) -> tuple[Arrow, ...]:
    """Rotate every arrow endpoint by ``g`` then translate by ``t``."""

    def tr(off):
        r = apply_op(g, off)
        return (r[0] + t[0], r[1] + t[1], r[2] + t[2])

    return tuple(Arrow(tr(a.start), tr(a.end), a.species) for a in arrows)


def _ball_sites(rad2: int) -> list[tuple[int, int, int]]:
    reach = int(math.isqrt(rad2)) + 1
    return sorted(
        (i, j, k)
        for i in range(-reach, reach + 1)
        for j in range(-reach, reach + 1)
        for k in range(-reach, reach + 1)
        if (i + j + k) % 2 == 0 and i * i + j * j + k * k <= rad2
    )


def _cart(off) -> np.ndarray:
    return H * np.asarray(off, dtype=float)


def _row(**kw):
    base = dict(
        energy_barrier=0.6,
        k=1.0e6,
        k_prefactor=1.0e13,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        source_row=0,
        cell=None,
    )
    base.update(kw)
    return base


class _FakeDF:
    """Minimal DataFrame stand-in for ``project_reference_table`` (len + iloc)."""

    def __init__(self, rows):
        self.iloc = rows

    def __len__(self) -> int:
        return len(self.iloc)


def _hop_row(idx: int = 0, *, mover_species: str = "Ni"):
    """A clean 1NN hop of the seed atom into the (1,1,0) vacancy."""
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]
    occ[(0, 0, 0)] = mover_species
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    mi = sites.index((0, 0, 0))
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))
    return _row(
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
        idx_ref=idx,
        source_row=idx,
        event_id=f"e{idx}",
    )


def _flicker_row(idx_ref: int = 0):
    """A snap-flicker phantom mover -> MOVER_OFFLATTICE (ledger row)."""
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]
    del occ[(1, -1, 2)]
    b_home = (0, 0, 2)
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    mi = sites.index((0, 0, 0))
    bi = sites.index(b_home)
    direction = (_cart((1, -1, 2)) - _cart(b_home)) / NN
    pos = pos.copy()
    pos[bi] = _cart(b_home) + 1.15 * direction
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    P2[bi] = _cart(b_home) + 1.35 * direction
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))
    return _row(
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
        idx_ref=idx_ref,
        source_row=idx_ref,
        event_id=f"flicker{idx_ref}",
    )


_NI = OccPredicate("SPECIES", frozenset({Occ.NI}))
_EMPTY = OccPredicate("EMPTY")


def _mk_pe(**kw) -> ProjectedEvent:
    """A minimal, well-formed ProjectedEvent (single in-plane <110> hop)."""
    base: dict[str, object] = dict(
        anchor0=(0, 0, 0),
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((1, 1, 0), _EMPTY),
            StencilSite((2, 0, 0), _EMPTY),
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


_CF = (3, 1, 0, 0, 8, ((0, 0, 0, 1, 1, 0, 1),), ((0, 0, 0, 1, 0), (1, 1, 0, 0, 1)), (), ())


def _mk_ec(cid: str, **kw) -> EventClass:
    """A minimal EventClass for the QC screens (no canonical machinery needed)."""
    base: dict[str, object] = dict(
        class_id=cid,
        canonical_form=_CF,
        canonical_blob=ecm._tlv_encode(_CF),
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        coloring=Coloring.FULL,
        move_shape=1,
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        delta_atoms=0,
        context=(),
        saddle_token=(PathToken(0, SaddleKind.BRIDGE, (8,)),),
        orientation_count=4,
        r_ctx_used=5.0,
        r_id_used=5.0,
        anchor_pred=_NI,
        t_ref_K=500.0,
        barriers_eV=(0.6,),
        nu0_f_list_hz=(1e13,),
        nu0_b_list_hz=(1e13,),
        dE_pair_list_eV=(0.0,),
        k_rate_mean_psinv=1.0,
        Ea_rep_eV=0.6,
        nu0_geo_psinv=10.0,
        Ea_std_eV=None,
        n_eff=1.0,
        Ea_mean_eV=0.6,
        Ea_median_eV=0.6,
        source_rows=(0,),
        source_idx_refs=(0,),
        arrows=_hop_arrows(),
        action_id=A.action_id(_hop_arrows()),
        archetype=A.archetype_id(_hop_arrows()),
    )
    base.update(kw)
    return EventClass(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# (a) reverse symmetry                                                        #
# --------------------------------------------------------------------------- #
def test_action_id_reverse_symmetric_single_hop() -> None:
    """A move and its reverse are the SAME action by construction (memo §3.1/D2)."""
    fwd = _hop_arrows()
    rev = A.invert_arrows(fwd)
    assert rev != fwd  # the arrow sets really are different objects
    assert A.action_id(fwd) == A.action_id(rev)
    assert A.archetype_id(fwd) == A.archetype_id(rev)


def test_action_id_reverse_symmetric_chain() -> None:
    """Reverse symmetry holds for a concerted 2-chain (species on the arrows)."""
    fwd = _chain_arrows()
    rev = A.invert_arrows(fwd)
    assert A.action_id(fwd) == A.action_id(rev)
    assert A.archetype_id(fwd) == A.archetype_id(rev)


def test_projected_event_and_reverse_share_action_id() -> None:
    """The whole projection path: an event and its reverse land on one action_id."""
    fwd = project_event(_hop_row(0), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0)
    assert fwd.arrows, "projection must capture arrows"
    rev = A.invert_arrows(fwd.arrows)
    assert A.action_id(fwd.arrows) == A.action_id(rev)


# --------------------------------------------------------------------------- #
# (b) D4h + translation invariance                                            #
# --------------------------------------------------------------------------- #
def test_action_id_invariant_under_every_d4h_op() -> None:
    """action_id / archetype are invariant under all 16 D4h ops and any translation."""
    for arrows in (_hop_arrows(), _chain_arrows()):
        aid = A.action_id(arrows)
        arch = A.archetype_id(arrows)
        for g in D4H:
            for t in ((0, 0, 0), (2, 0, 0), (-4, 2, 6)):
                moved = _move(arrows, g, t)
                assert A.action_id(moved) == aid, f"op {g.index} t={t} changed action_id"
                assert A.archetype_id(moved) == arch


def test_action_id_separates_inplane_from_out_of_plane() -> None:
    """D4h does not mix the in-plane and out-of-plane 1NN orbits (memo §4)."""
    inplane = (Arrow((0, 0, 0), (1, 1, 0), Occ.NI),)
    outofplane = (Arrow((0, 0, 0), (1, 0, 1), Occ.NI),)
    assert A.action_id(inplane) != A.action_id(outofplane)
    assert A.archetype_name(inplane) == "V1NN_inplane"
    assert A.archetype_name(outofplane) == "V1NN_outofplane"


# --------------------------------------------------------------------------- #
# (c) species labelling                                                       #
# --------------------------------------------------------------------------- #
def test_species_relabel_changes_action_but_not_archetype() -> None:
    """Cr vs Ni is a different ACTION but the same ARCHETYPE (ruling 1)."""
    ni = (Arrow((0, 0, 0), (1, 1, 0), Occ.NI),)
    cr = (Arrow((0, 0, 0), (1, 1, 0), Occ.CR),)
    assert A.action_id(ni) != A.action_id(cr)
    assert A.archetype_id(ni) == A.archetype_id(cr)


def test_grey_arrows_action_equals_archetype() -> None:
    """With no species information the action IS the archetype (grey catalogue)."""
    grey = (Arrow((0, 0, 0), (1, 1, 0), Occ.OCC_ANY),)
    assert A.action_id(grey) == A.archetype_id(grey)


# --------------------------------------------------------------------------- #
# (d) schema 3 -> 4 read compatibility                                        #
# --------------------------------------------------------------------------- #
def test_schema_version_is_5() -> None:
    assert ecm.CATALOGUE_SCHEMA_VERSION == 5


def test_schema3_parquet_still_reads_with_field_defaults(tmp_path: Path) -> None:
    """A parquet written without the v4 columns reads back at the field defaults."""
    pytest.importorskip("pyarrow")
    import pyarrow as pa
    import pyarrow.parquet as pq

    src = _mk_ec("aa" * 32, one_way=True)
    row = ecm._event_to_row(src)
    row["schema_version"] = 3
    row["family_id"] = 2  # a REAL v3 file carries the (v5-removed) column
    fields = [f for f in ecm.catalogue_arrow_schema() if f.name not in ecm.SCHEMA_V4_COLUMNS]
    pos = [f.name for f in fields].index("move_shape") + 1
    fields.insert(pos, pa.field("family_id", pa.int64()))
    schema = pa.schema(fields)
    cols = {f.name: pa.array([row[f.name]], type=f.type) for f in schema}
    path = tmp_path / "v3.parquet"
    pq.write_table(pa.Table.from_pydict(cols, schema=schema), path)

    (back,) = ecm.read_catalogue_parquet(path)
    assert back.schema_version == 3
    assert back.arrows == ()
    assert back.action_id is None
    assert back.archetype is None
    assert back.one_way is False
    assert back.action_pair_mismatch is False
    # the v3 payload itself is untouched
    assert back.delta == src.delta
    assert back.barriers_eV == src.barriers_eV


def test_v4_parquet_round_trips_the_new_columns(tmp_path: Path) -> None:
    """arrows / action_id / archetype / one_way survive a write -> read round trip."""
    pytest.importorskip("pyarrow")
    src = _mk_ec("bb" * 32, arrows=_chain_arrows(), one_way=True, action_pair_mismatch=True)
    src.action_id = A.action_id(src.arrows)
    src.archetype = A.archetype_id(src.arrows)
    path = tmp_path / "v4.parquet"
    ecm.write_catalogue_parquet([src], path)
    (back,) = ecm.read_catalogue_parquet(path)
    assert back.arrows == src.arrows
    assert back.action_id == src.action_id
    assert back.archetype == src.archetype
    assert back.one_way is True
    assert back.action_pair_mismatch is True
    assert back.schema_version == 5


# --------------------------------------------------------------------------- #
# one_way semantics (memo §2.1 / §5.2)                                        #
# --------------------------------------------------------------------------- #
def test_one_way_flag_semantics() -> None:
    """Alive (Ea < 1.4 eV) in exactly one direction, per the §2.1 convention."""
    cut = ecm.EA_ALIVE_CUT_EV
    assert cut == pytest.approx(1.4)
    # pair-aligned dE: Ea_b = Ea_f - dE
    assert not ecm.one_way_flag((0.5,), (0.1,), 0.1)  # Ea_b = 0.4 -> both alive
    assert ecm.one_way_flag((0.5,), (-1.0,), -1.0)  # Ea_b = 1.5 -> forward only
    assert ecm.one_way_flag((2.0,), (1.0,), 1.0)  # Ea_b = 1.0 -> backward only
    assert not ecm.one_way_flag((2.0,), (0.1,), 0.1)  # Ea_b = 1.9 -> both dead
    assert not ecm.one_way_flag((0.5,), (), None)  # no backward info at all
    # misaligned dE list -> class-level dEnergy fallback (probe/§2.1 convention)
    assert ecm.one_way_flag((0.5, 0.6), (-1.0,), -1.0)
    # one both-alive member disarms the flag even with a one-sided sibling
    assert not ecm.one_way_flag((0.5, 0.5), (0.1, -1.0), -0.45)


# --------------------------------------------------------------------------- #
# arrows capture: projection, catalogue, ledger                               #
# --------------------------------------------------------------------------- #
def test_projection_captures_species_labelled_arrows() -> None:
    """detect_movers' pairing survives to ProjectedEvent.arrows, species attached."""
    pe = project_event(
        _hop_row(0, mover_species="Cr"), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0
    )
    assert pe.arrows == (Arrow((0, 0, 0), (1, 1, 0), Occ.CR),)
    # arrows are aligned 1:1 with movers (same order, same start sites)
    assert tuple(a.start for a in pe.arrows) == pe.movers


def test_catalogue_columns_populated_from_projection() -> None:
    """build_class_catalogue fills arrows / action_id / archetype / one_way."""
    rows = [_hop_row(0), _hop_row(1)]
    rep = ReftableBuildReport()
    events = project_reference_table(
        _FakeDF(rows), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0, report=rep
    )
    th = GateThresholds(emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0)
    classes = build_class_catalogue(events, t_ref_K=500.0, thresholds=th, nu0_fallback_hz=1e12)
    assert classes
    ec0 = classes[0]
    assert len(ec0.arrows) == 1
    assert ec0.action_id == A.action_id(ec0.arrows)
    assert ec0.archetype == A.archetype_id(ec0.arrows)
    assert ec0.one_way is False  # unpaired members carry no backward information
    assert A.archetype_name(ec0.arrows, ec0.delta_atoms) == "V1NN_inplane"
    # stored arrows live in the same (canonical) frame as the stored delta
    delta_offs = {ds.off for ds in ec0.delta}
    assert {ec0.arrows[0].start, ec0.arrows[0].end} == delta_offs


def test_ledger_carries_unsnapped_arrow_provenance(tmp_path: Path) -> None:
    """An off-lattice discard keeps UNSNAPPED arrows; action_id/archetype stay null."""
    pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    rep = ReftableBuildReport()
    project_reference_table(
        _FakeDF([_flicker_row(0)]),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
        report=rep,
    )
    assert rep.n_mover_offlattice == 1
    (row,) = rep.discarded
    assert row.arrows, "ledger row must carry unsnapped arrow provenance (memo §5.1)"
    # unsnapped: real-valued lattice coordinates, not integers
    starts = [a.start for a in row.arrows]
    assert any(any(abs(c - round(c)) > 1e-6 for c in s) for s in starts)

    out = tmp_path / "catalogue.parquet"
    write_discard_ledger_parquet(rep.discarded, discard_ledger_path(out))
    table = pq.read_table(discard_ledger_path(out)).to_pylist()
    assert len(table[0]["arrows"]) == len(row.arrows)
    assert table[0]["action_id"] is None
    assert table[0]["archetype"] is None
    assert table[0]["one_way"] is None


# --------------------------------------------------------------------------- #
# NO_OP relabel (ruling 5)                                                    #
# --------------------------------------------------------------------------- #
def test_no_op_reason_relabel_and_census_carve_out() -> None:
    """Delta-less + mover-less classes are quarantined as NO_OP, not as a defect."""
    no_op = _mk_ec("11" * 32, delta=(), saddle_token=(), arrows=(), action_id=None, archetype=None)
    plain = _mk_ec("22" * 32)
    rep = apply_qc([no_op, plain])
    got = {c.class_id: c for c in rep.classes}
    assert got[no_op.class_id].audit_status == "quarantined"
    assert "NO_OP" in got[no_op.class_id].audit_reason
    # ruling 5: reason rename ONLY -- no new audit_status value
    assert got[no_op.class_id].audit_status in ("approved", "pending", "rejected", "quarantined")
    assert rep.no_op_quarantined == 1
    assert "NO_OP" in rep.summary()
    # a delta-less class WITH movers is a same-species permutation, not a no-op
    perm = _mk_ec("33" * 32, delta=(), arrows=_chain_arrows())
    rep2 = apply_qc([perm])
    assert rep2.no_op_quarantined == 0
    assert "NO_OP" not in rep2.classes[0].audit_reason


def test_no_op_relabel_survives_re_emission() -> None:
    """A carried (pre-existing) quarantine is still relabelled NO_OP on re-emission."""
    stale = _mk_ec(
        "44" * 32,
        delta=(),
        saddle_token=(),
        arrows=(),
        action_id=None,
        archetype=None,
        audit_status="quarantined",
        audit_reason="QC: empty delta — not executable",
    )
    rep = apply_qc([stale])
    assert "NO_OP" in rep.classes[0].audit_reason
    assert rep.no_op_quarantined == 1


# --------------------------------------------------------------------------- #
# linked-pair action screen (ruling 9: flag + review list, never quarantine)   #
# --------------------------------------------------------------------------- #
def test_linked_pair_action_mismatch_flags_both_and_lists_them() -> None:
    """A linked pair with two action_ids is FLAGGED (not quarantined) + listed."""
    a_arrows = _hop_arrows()
    b_arrows = (Arrow((0, 0, 0), (2, 0, 0), Occ.NI),)  # a 2NN "hop": different action
    fwd = _mk_ec(
        "aa" * 32,
        backward_class="bb" * 32,
        arrows=a_arrows,
        action_id=A.action_id(a_arrows),
        archetype=A.archetype_id(a_arrows),
    )
    bwd = _mk_ec(
        "bb" * 32,
        backward_class="aa" * 32,
        arrows=b_arrows,
        action_id=A.action_id(b_arrows),
        archetype=A.archetype_id(b_arrows),
    )
    rep = apply_qc([fwd, bwd])
    got = {c.class_id: c for c in rep.classes}
    assert got["aa" * 32].action_pair_mismatch is True
    assert got["bb" * 32].action_pair_mismatch is True
    # ruling 9: classes keep firing -- flag only, never a quarantine
    assert got["aa" * 32].audit_status != "quarantined"
    assert rep.action_pair_mismatch_pairs == 1
    assert rep.action_pair_mismatch_classes == 2
    assert len(rep.action_review_rows) == 1
    assert rep.action_review_rows[0]["class_id"] == "aa" * 32
    assert "action" in str(rep.action_review_rows[0]["review_group"])


def test_matching_linked_pair_is_not_flagged() -> None:
    """The normal case: a linked pair sharing one action_id raises nothing."""
    fwd_arrows = _hop_arrows()
    bwd_arrows = A.invert_arrows(fwd_arrows)
    fwd = _mk_ec(
        "aa" * 32,
        backward_class="bb" * 32,
        arrows=fwd_arrows,
        action_id=A.action_id(fwd_arrows),
    )
    bwd = _mk_ec(
        "bb" * 32,
        backward_class="aa" * 32,
        arrows=bwd_arrows,
        action_id=A.action_id(bwd_arrows),
    )
    rep = apply_qc([fwd, bwd])
    assert rep.action_pair_mismatch_pairs == 0
    assert all(not c.action_pair_mismatch for c in rep.classes)


def test_action_review_list_appends_once_and_dedupes(tmp_path: Path) -> None:
    """The review list is a STANDING list: appended to, header once, never doubled.

    A standing list is re-appended on every re-run of ``qc``/``merge``; duplicate
    rows would inflate the queue and re-open pairs a curator already ruled on.
    """
    path = tmp_path / "review_list.csv"
    row = dict.fromkeys(ACTION_REVIEW_FIELDS, "x")
    other = dict(row, class_id="aa", partner_class_id="bb")
    assert append_action_review_rows(path, [row]) == 1
    # same pair again (a re-run), plus a duplicate within the batch -> 1 new row only
    assert append_action_review_rows(path, [row, other, other]) == 1
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].split(",") == list(ACTION_REVIEW_FIELDS)
    assert len(lines) == 3  # 1 header + 2 distinct pairs
    assert "class_id" in ACTION_REVIEW_FIELDS  # remap --review-in compatibility
    # a recurrence with CHANGED digests is new evidence -> written, not suppressed
    changed = dict(row, action_id="y2", partner_action_id="z2")
    assert append_action_review_rows(path, [changed, changed]) == 1
    assert append_action_review_rows(path, [row, changed]) == 0
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4  # + the changed-digest recurrence, nothing doubled


# --------------------------------------------------------------------------- #
# taxonomy naming (memo §4)                                                   #
# --------------------------------------------------------------------------- #
def test_archetype_names_cover_the_taxonomy() -> None:
    assert A.archetype_name(()) == "NO_OP"
    assert A.archetype_name(_hop_arrows()) == "V1NN_inplane"
    assert A.archetype_name((Arrow((0, 0, 0), (2, 0, 0), Occ.NI),)) == "HOP_2NN"
    assert A.archetype_name((Arrow((0, 0, 0), (2, 1, 1), Occ.NI),)) == "HOP_3NN"
    # C2 sub-shapes keyed by the net displacement shell (memo §4: 0/60/90/120 deg)
    assert A.archetype_name(_chain_arrows()) == "C2_0deg"
    kink90 = (
        Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
        Arrow((1, -1, 0), (0, 0, 0), Occ.NI),
    )
    assert A.archetype_name(kink90) == "C2_90deg"
    ring = (
        Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
        Arrow((1, 1, 0), (0, 0, 0), Occ.CR),
    )
    assert A.archetype_name(ring) == "X2"
    assert A.archetype_name(_hop_arrows(), delta_atoms=-1) == "NC"


def test_action_census_panel_reports_the_taxonomy() -> None:
    """The census panel names archetypes, the one-way annex and the NO_OP bin."""
    hop = _mk_ec("aa" * 32)
    annex = _mk_ec("bb" * 32, one_way=True)
    no_op = _mk_ec(
        "cc" * 32,
        delta=(),
        saddle_token=(),
        arrows=(),
        action_id=A.action_id(()),
        archetype=A.archetype_id(()),
    )
    no_op.audit_status = "quarantined"
    no_op.audit_reason = ecm.NO_OP_REASON
    census = A.action_census([hop, annex, no_op])
    text = census.summary()
    assert "V1NN_inplane" in text
    assert "NO_OP" in text
    assert "one-way annex" in text
    assert census.n_classes == 3
    assert census.n_one_way == 1
    assert census.n_no_op == 1  # topological (empty arrow set) — available at build
    assert census.n_no_op_quarantined == 1  # reason-aware carve-out — set by QC
    assert census.by_archetype_name["V1NN_inplane"] == 2


# --------------------------------------------------------------------------- #
# determinism + the class_id guard                                            #
# --------------------------------------------------------------------------- #
_DETERMINISM_SCRIPT = r"""
from pylatkmc.ingest import action as A
from pylatkmc.ingest.event_class import Arrow, Occ

arrows = (
    Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
    Arrow((-1, -1, 0), (0, 0, 0), Occ.CR),
)
print(A.action_id(arrows), A.archetype_id(arrows))
"""


def test_action_id_independent_of_pythonhashseed() -> None:
    """blake2b over TLV ints -- never hash()/set ordering (contract 0.1)."""
    outs = []
    for seed in ("0", "1"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        proc = subprocess.run(
            [sys.executable, "-c", _DETERMINISM_SCRIPT],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        outs.append(proc.stdout)
    assert outs[0] == outs[1]


def test_action_axis_feeds_class_id_at_canon_v3() -> None:
    """CANON v3 (memo §7 Phase 2): the directed arrows ARE identity content.

    Phase 1's additive contract ("class_id is blind to arrows") retired with the
    v2->v3 bump: two events identical except for where the mover went are now
    distinct classes, and the redundant u32 ``family_id`` is gone (ruling 2).
    """
    assert C.CANON_SCHEMA_VERSION == 3
    hop = _mk_pe()
    longer = _mk_pe(arrows=(Arrow((0, 0, 0), (2, 0, 0), Occ.NI),))
    assert C.class_id(hop) != C.class_id(longer)
    assert not hasattr(C, "family_id")


# --------------------------------------------------------------------------- #
# Review-round fixes (2026-07-30): plumbing regressions around the action axis #
# --------------------------------------------------------------------------- #
def test_merge_one_way_uses_member_aligned_dE() -> None:
    """F1: merged `dE` must ride the SAME sorted member tuple as `barriers_eV`.

    Reproduction from the review: three linked members whose (Ea_f, dE) pairs are
    (0.5, -0.1), (1.35, -3.0), (1.36, -2.9). Truth: member 0 is alive in BOTH
    directions (Ea_b = 0.6), so the class is not one-way. Sorting `dE` independently
    of `barriers` puts -3.0 against the 0.5 eV barrier and -0.1 against 1.36, which
    makes every member look one-sided.
    """
    from pylatkmc.ingest.merge import union_classes

    ea = (0.50, 1.35, 1.36)
    de = (-0.10, -3.00, -2.90)
    assert ecm.one_way_flag(ea, de, sum(de) / 3) is False  # truth, aligned

    run = [
        _mk_ec(
            "dd" * 32,
            barriers_eV=ea,
            dE_pair_list_eV=de,
            nu0_f_list_hz=(1e13,) * 3,
            nu0_b_list_hz=(1e13,) * 3,
            dEnergy_eV=sum(de) / 3,
        )
    ]
    (merged,) = union_classes([("run_a", run)])
    assert merged.one_way is False, "merge mispaired barriers with another member's dE"
    # ... and the merged list is stored in the aligned convention
    assert len(merged.dE_pair_list_eV) == len(merged.barriers_eV)
    assert dict(zip(merged.barriers_eV, merged.dE_pair_list_eV)) == dict(zip(ea, de))


def test_merge_realigns_the_subset_dE_convention() -> None:
    """F1: a per-run build's SUBSET dE (linked members only) re-aligns by the nu0_b mask."""
    from pylatkmc.ingest.merge import union_classes

    # members 0 and 2 linked (finite nu0_b), member 1 unpaired -> subset dE of len 2
    run = [
        _mk_ec(
            "ee" * 32,
            barriers_eV=(0.50, 0.60, 0.70),
            nu0_f_list_hz=(1e13,) * 3,
            nu0_b_list_hz=(1e13, float("nan"), 2e13),
            dE_pair_list_eV=(-0.10, -0.20),
            dEnergy_eV=-0.15,
        )
    ]
    (merged,) = union_classes([("run_a", run)])
    aligned = dict(zip(merged.barriers_eV, merged.dE_pair_list_eV))
    assert aligned[0.50] == pytest.approx(-0.10)
    assert aligned[0.70] == pytest.approx(-0.20)
    assert math.isnan(aligned[0.60])  # the unpaired member keeps no dE
    assert merged.dEnergy_eV == pytest.approx(-0.15)  # unchanged reduction


def test_census_never_calls_an_unstamped_class_no_op() -> None:
    """F2: a schema<=3 class (arrows=(), action_id=None) is UNSTAMPED, not NO_OP."""
    pre_v4 = [_mk_ec(f"{i:02x}" * 32, arrows=(), action_id=None, archetype=None) for i in range(5)]
    census = A.action_census(pre_v4)
    assert census.n_unstamped == 5
    assert census.n_no_op == 0
    assert census.by_archetype_name == {}
    assert census.n_residual == 0
    text = census.summary()
    assert "no action_id      :     5 classes" in text
    assert "5 unstamped" in text
    # a genuine NO_OP (real digest of the empty arrow set) still counts as NO_OP
    real_no_op = _mk_ec(
        "ff" * 32, arrows=(), action_id=A.action_id(()), archetype=A.archetype_id(())
    )
    assert A.action_census([real_no_op]).n_no_op == 1


def test_no_op_relabel_preserves_a_curator_reason() -> None:
    """F4: ruling 5 renames the anonymous bin -- it must not delete curator provenance."""
    veto = "QC: human veto — Stephen 2026-07-24: subsurface artefact, do not fire"
    c = _mk_ec(
        "77" * 32,
        delta=(),
        saddle_token=(),
        arrows=(),
        action_id=A.action_id(()),
        archetype=A.archetype_id(()),
        audit_status="quarantined",
        audit_reason=veto,
    )
    (out,) = apply_qc([c]).classes
    assert "NO_OP" in out.audit_reason
    assert veto in out.audit_reason, "the curator's veto text was clobbered"
    # idempotent: a second QC pass (re-QC after merge/remap) must not re-prefix
    (out_again,) = apply_qc([out]).classes
    assert out_again.audit_reason == out.audit_reason
    assert out.audit_reason.count(ecm.NO_OP_REASON) == 1
    # the generic delta-less text carries no curator information -> replaced outright
    generic = _mk_ec(
        "88" * 32,
        delta=(),
        saddle_token=(),
        arrows=(),
        action_id=A.action_id(()),
        archetype=A.archetype_id(()),
        audit_status="quarantined",
        audit_reason="QC: empty delta — not executable",
    )
    (out2,) = apply_qc([generic]).classes
    assert out2.audit_reason == ecm.NO_OP_REASON


def test_grey_build_collapses_species_on_the_action_axis() -> None:
    """F6: a GREY catalogue must not leak species its identity dropped."""
    pe = project_event(
        _hop_row(0, mover_species="Cr"), coloring=Coloring.GREY, rcut=5.0, d_max=2, r_ctx_min=3.0
    )
    assert pe.arrows and all(a.species == Occ.OCC_ANY for a in pe.arrows)
    assert all(a.species == Occ.OCC_ANY for a in pe.arrows_raw)
    th = GateThresholds(emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0)
    (ec0,) = build_class_catalogue([pe], t_ref_K=500.0, thresholds=th, nu0_fallback_hz=1e12)
    assert ec0.action_id == ec0.archetype, "grey action_id still carries species"
    assert all(a.species == Occ.OCC_ANY for a in ec0.arrows)
    # the FULL-coloured build of the same event keeps the species (control)
    pe_full = project_event(
        _hop_row(0, mover_species="Cr"), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0
    )
    (ec_full,) = build_class_catalogue(
        [pe_full], t_ref_K=500.0, thresholds=th, nu0_fallback_hz=1e12
    )
    assert ec_full.action_id != ec_full.archetype


def test_occ_any_arrow_species_round_trips_through_parquet(tmp_path: Path) -> None:
    """F9: the species column must hold OCC_ANY (254) -- int8 cannot."""
    pytest.importorskip("pyarrow")
    grey_arrows = (Arrow((0, 0, 0), (1, 1, 0), Occ.OCC_ANY),)
    src = _mk_ec(
        "99" * 32,
        arrows=grey_arrows,
        action_id=A.action_id(grey_arrows),
        archetype=A.archetype_id(grey_arrows),
    )
    path = tmp_path / "grey.parquet"
    ecm.write_catalogue_parquet([src], path)
    (back,) = ecm.read_catalogue_parquet(path)
    assert back.arrows == grey_arrows

    from pylatkmc.ingest.event_class import RawArrow
    from pylatkmc.ingest.reftable import DiscardedRow, write_discard_ledger_parquet

    led = tmp_path / "led.parquet"
    write_discard_ledger_parquet(
        [
            DiscardedRow(
                row=0,
                idx_ref=0,
                source_row=0,
                event_id="e",
                reason="MOVER_OFFLATTICE",
                detail="d",
                mover_max_residual=0.9,
                max_residual=0.9,
                Ea_fwd_eV=0.6,
                move_atom_idx=0,
                arrows=(RawArrow((0.0, 0.0, 0.0), (1.1, 1.1, 0.0), Occ.OCC_ANY),),
            )
        ],
        led,
    )
    import pyarrow.parquet as pq

    assert pq.read_table(led).to_pylist()[0]["arrows"][0]["species"] == int(Occ.OCC_ANY)


def test_member_action_disagreement_is_structurally_split_at_v3() -> None:
    """F5 under CANON v3: differing arrows now SPLIT the class instead of hiding.

    Pre-v3 this fixture produced one class with a disagreeing member and the
    ``n_action_disagree`` monitor counted it. With the arrows in the digest the
    two events are different classes by construction, so the monitor (kept as a
    digest-corruption tripwire) must read 0.
    """
    from pylatkmc.ingest.event_class import CatalogueReport

    th = GateThresholds(emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0)
    pe = project_event(_hop_row(0), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0)
    # a second event identical except its arrow says something else entirely
    # (same mover start — the v3 guard requires arrow/mover alignment — but a
    # 2NN end instead of the real 1NN one).
    from dataclasses import replace as dc_replace

    a0 = pe.arrows[0]
    odd = dc_replace(
        pe,
        arrows=(Arrow(a0.start, (a0.start[0] + 2, a0.start[1], a0.start[2]), a0.species),),
        idx_ref=1,
        source_row=1,
        event_id="e1",
        Ea_fwd_eV=0.61,
    )
    rep = CatalogueReport()
    classes = build_class_catalogue(
        [pe, odd], t_ref_K=500.0, thresholds=th, nu0_fallback_hz=1e12, report=rep
    )
    assert len(classes) == 2
    assert all(len(c.barriers_eV) == 1 for c in classes)
    assert rep.n_action_disagree == 0
    assert all(c.action_pair_mismatch is False for c in classes)


def test_merge_appends_action_mismatches_to_the_review_list(tmp_path: Path) -> None:
    """F3: a corpus-level mismatch materialises at MERGE and must reach the list.

    A linked pair's two directions can arrive from different runs, so this is the
    only place the screen can see them together (ruling 9).
    """
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a_arrows = _hop_arrows()
    b_arrows = (Arrow((0, 0, 0), (2, 0, 0), Occ.NI),)  # a different action entirely
    fwd = _mk_ec(
        "aa" * 32,
        backward_class="bb" * 32,
        dEnergy_eV=0.1,
        dE_pair_list_eV=(0.1,),
        arrows=a_arrows,
        action_id=A.action_id(a_arrows),
        archetype=A.archetype_id(a_arrows),
    )
    bwd = _mk_ec(
        "bb" * 32,
        backward_class="aa" * 32,
        dEnergy_eV=-0.1,
        dE_pair_list_eV=(-0.1,),
        arrows=b_arrows,
        action_id=A.action_id(b_arrows),
        archetype=A.archetype_id(b_arrows),
    )
    run_a, run_b = tmp_path / "a.parquet", tmp_path / "b.parquet"
    ecm.write_catalogue_parquet([fwd], run_a)
    ecm.write_catalogue_parquet([bwd], run_b)

    out = tmp_path / "merged.parquet"
    review = tmp_path / "standing_review.csv"
    rc = main(
        [
            "merge",
            "--in",
            f"RUN_A={run_a}",
            "--in",
            f"RUN_B={run_b}",
            "--out",
            str(out),
            "--review",
            str(review),
        ]
    )
    assert rc == 0
    assert review.is_file(), "merge never appended the corpus-level mismatch"
    lines = review.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].split(",") == list(ACTION_REVIEW_FIELDS)
    assert len(lines) == 2  # header + the one pair
    assert lines[1].startswith("aa" * 32)
    # ruling 9: flagged, never quarantined
    merged = {c.class_id: c for c in ecm.read_catalogue_parquet(out)}
    assert merged["aa" * 32].action_pair_mismatch is True
    assert merged["bb" * 32].action_pair_mismatch is True
    assert merged["aa" * 32].audit_status != "quarantined"


def test_merge_default_review_path_is_beside_the_output(tmp_path: Path) -> None:
    """F3: --review is optional; the default sits next to --out like `graduate`'s."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.cli import main

    a_arrows = _hop_arrows()
    b_arrows = (Arrow((0, 0, 0), (2, 0, 0), Occ.NI),)
    fwd = _mk_ec(
        "aa" * 32,
        backward_class="bb" * 32,
        dEnergy_eV=0.1,
        dE_pair_list_eV=(0.1,),
        arrows=a_arrows,
        action_id=A.action_id(a_arrows),
    )
    bwd = _mk_ec(
        "bb" * 32,
        backward_class="aa" * 32,
        dEnergy_eV=-0.1,
        dE_pair_list_eV=(-0.1,),
        arrows=b_arrows,
        action_id=A.action_id(b_arrows),
    )
    run = tmp_path / "r.parquet"
    ecm.write_catalogue_parquet([fwd, bwd], run)
    out = tmp_path / "merged.parquet"
    assert main(["merge", "--in", f"R={run}", "--out", str(out)]) == 0
    assert (tmp_path / "merged_action_review.csv").is_file()
