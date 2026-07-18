"""Canonical identity tests (Agent A5, contract 11.2).

Every test asserts the named property of ``pylatkmc.ingest.canonical``: the
complete orbit invariant (invariance under D4h x translation x anchor/atom-order
shuffle), grey-vs-full colour, geometric + depth distinctness, the symmetric
divacancy Sym-2 case, sigma_h top/bottom coverage, byte-exact TLV, brute-force
orientation_count, and ``PYTHONHASHSEED``-independent move_shape/family_id.

Pure numpy/stdlib: ``canonical`` / ``event_class`` / ``lattice`` import without the
``[ingest]`` extras, so no importorskip guard is needed.
"""

from __future__ import annotations

import hashlib
import struct
import subprocess
import sys
from dataclasses import replace

import pytest

from pylatkmc.ingest import canonical as C
from pylatkmc.ingest.event_class import (
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventProjReport,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
)
from pylatkmc.ingest.lattice import D4H, IDENTITY, apply_op

# --------------------------------------------------------------------------- #
# Fixtures / builders                                                         #
# --------------------------------------------------------------------------- #
_NI = OccPredicate("SPECIES", frozenset({Occ.NI}))
_CR = OccPredicate("SPECIES", frozenset({Occ.CR}))
_EMPTY = OccPredicate("EMPTY")


def _mk(**kw: object) -> ProjectedEvent:
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


def _op_by_matrix(mat: tuple[tuple[int, int, int], ...]) -> object:
    """Return the D4h SymOp with the given integer matrix."""
    for g in D4H:
        if g.mat == mat:
            return g
    raise AssertionError(f"no D4h op with matrix {mat}")


def _transform(pe: ProjectedEvent, g: object, t: tuple[int, int, int]) -> ProjectedEvent:
    """Rotate every offset by ``g`` then translate by ``t`` (a whole-event move)."""

    def tr(off: tuple[int, int, int]) -> tuple[int, int, int]:
        r = apply_op(g, off)  # type: ignore[arg-type]
        return (r[0] + t[0], r[1] + t[1], r[2] + t[2])

    return replace(
        pe,
        anchor0=tr(pe.anchor0),
        delta=tuple(DeltaSite(tr(d.off), d.before, d.after) for d in pe.delta),
        context=tuple(StencilSite(tr(c.off), c.pred) for c in pe.context),
        movers=tuple(tr(m) for m in pe.movers),
    )


# --------------------------------------------------------------------------- #
# Canonical invariance (contract 11.2)                                        #
# --------------------------------------------------------------------------- #
def test_class_id_invariant_under_d4h_and_translation() -> None:
    """class_id is invariant under every D4h op and any integer translation."""
    pe = _mk()
    cid = C.class_id(pe)
    seed = 1234567
    for g in D4H:
        # a small deterministic pseudo-random translation (parity-preserving even).
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        t = (2 * ((seed % 7) - 3), 2 * ((seed // 7 % 7) - 3), 2 * ((seed // 49 % 7) - 3))
        assert C.class_id(_transform(pe, g, t)) == cid, f"invariance fail op={g.index} t={t}"


def test_class_id_invariant_under_atom_and_anchor_shuffle() -> None:
    """Shuffling delta/context order and mover/token pairing preserves class_id."""
    movers = ((0, 0, 0), (2, 2, 0))
    tokens = (
        PathToken(0, SaddleKind.BRIDGE, (8, 8)),
        PathToken(0, SaddleKind.HOLLOW_FCC, (7, 7, 7)),
    )
    delta = (
        DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
        DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI),
        DeltaSite((2, 2, 0), Occ.NI, Occ.EMPTY),
        DeltaSite((3, 1, 0), Occ.EMPTY, Occ.NI),
    )
    context = (
        StencilSite((0, 0, 0), _NI),
        StencilSite((2, 2, 0), _NI),
        StencilSite((1, 1, 0), _EMPTY),
        StencilSite((3, 1, 0), _EMPTY),
    )
    pe = _mk(movers=movers, saddle_tokens=tokens, delta=delta, context=context)
    cid = C.class_id(pe)

    # Reverse delta + context order, and swap the mover/token pairing order
    # together (mover m1 must keep its token t1).
    shuffled = replace(
        pe,
        delta=tuple(reversed(delta)),
        context=tuple(reversed(context)),
        movers=(movers[1], movers[0]),
        saddle_tokens=(tokens[1], tokens[0]),
    )
    assert C.class_id(shuffled) == cid


# --------------------------------------------------------------------------- #
# Distinctness (contract 11.2)                                                #
# --------------------------------------------------------------------------- #
def test_in_plane_vs_interlayer_hop_distinct() -> None:
    """A bulk in-plane <110> hop and an inter-layer <110> hop are distinct."""
    in_plane = _mk(
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        context=(StencilSite((0, 0, 0), _NI), StencilSite((1, 1, 0), _EMPTY)),
    )
    inter_layer = _mk(
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 0, 1), Occ.EMPTY, Occ.NI)),
        context=(StencilSite((0, 0, 0), _NI), StencilSite((1, 0, 1), _EMPTY)),
    )
    # D4h fixes |z|, so a z=0 hop vector can never map onto a |z|=1 one.
    assert C.class_id(in_plane) != C.class_id(inter_layer)


def test_two_different_decorated_events_distinct() -> None:
    """Two genuinely different decorated contexts give different class_ids."""
    a = _mk(context=(StencilSite((0, 0, 0), _NI), StencilSite((2, 0, 0), _NI)))
    b = _mk(context=(StencilSite((0, 0, 0), _NI), StencilSite((2, 0, 0), _EMPTY)))
    assert C.class_id(a) != C.class_id(b)


def test_ni_near_cr_full_distinct_grey_same() -> None:
    """Ni-hop-near-Cr vs pure-Ni differ in FULL colour but match in GREY."""
    near_cr_full = _mk(
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((2, 0, 0), _CR),
            StencilSite((1, 1, 0), _EMPTY),
        ),
        coloring=Coloring.FULL,
    )
    pure_ni_full = _mk(
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((2, 0, 0), _NI),
            StencilSite((1, 1, 0), _EMPTY),
        ),
        coloring=Coloring.FULL,
    )
    assert C.class_id(near_cr_full) != C.class_id(pure_ni_full)

    near_cr_grey = replace(near_cr_full, coloring=Coloring.GREY)
    pure_ni_grey = replace(pure_ni_full, coloring=Coloring.GREY)
    assert C.class_id(near_cr_grey) == C.class_id(pure_ni_grey)


# --------------------------------------------------------------------------- #
# Symmetric divacancy — Sym-2 (contract 11.2)                                 #
# --------------------------------------------------------------------------- #
def _symmetric_divacancy() -> ProjectedEvent:
    """A concerted 2-mover event symmetric under (180-about-z, translate (2,0,0)).

    Movers m1=(0,0,0), m2=(2,0,0) are related by a translation, not a point-group
    op about a single anchor -- the case a group-only-about-anchor0 scheme splits.
    """
    delta = (
        DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
        DeltaSite((2, 0, 0), Occ.NI, Occ.EMPTY),
        DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI),
        DeltaSite((1, -1, 0), Occ.EMPTY, Occ.NI),
    )
    context = (
        StencilSite((0, 0, 0), _NI),
        StencilSite((2, 0, 0), _NI),
        StencilSite((1, 1, 0), _EMPTY),
        StencilSite((1, -1, 0), _EMPTY),
    )
    tokens = (
        PathToken(0, SaddleKind.BRIDGE, (8, 8)),
        PathToken(0, SaddleKind.BRIDGE, (8, 8)),
    )
    return _mk(
        movers=((0, 0, 0), (2, 0, 0)),
        delta=delta,
        context=context,
        saddle_tokens=tokens,
    )


def test_symmetric_divacancy_both_movers_equivalent_anchors() -> None:
    """Anchoring at either symmetric mover yields the same minimal variant (Sym-2)."""
    pe = _symmetric_divacancy()
    m1, m2 = (0, 0, 0), (2, 0, 0)
    best_at_m1 = min(C.serialize_variant(pe, m1, g) for g in D4H)
    best_at_m2 = min(C.serialize_variant(pe, m2, g) for g in D4H)
    assert best_at_m1 == best_at_m2


def test_symmetric_divacancy_two_orientations_one_class() -> None:
    """Two harvest orientations of the divacancy land on one class_id (Sym-2)."""
    pe = _symmetric_divacancy()
    cid = C.class_id(pe)
    # A second harvest that anchored at the OTHER mover and rotated by 180-about-z:
    # a legitimately different frame_e, which group-only-about-anchor0 would split.
    rot180 = _op_by_matrix(((-1, 0, 0), (0, -1, 0), (0, 0, 1)))
    other = _transform(pe, rot180, (0, 0, 0))
    assert C.class_id(other) == cid


# --------------------------------------------------------------------------- #
# sigma_h top/bottom surface coverage (contract 11.2)                         #
# --------------------------------------------------------------------------- #
def test_sigma_h_top_bottom_same_class() -> None:
    """A top-surface event and its sigma_h (bottom-surface) image share a class."""
    top = _mk(
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((1, 1, 0), _EMPTY),
            StencilSite((0, 0, 2), _EMPTY),  # vacuum above (top surface)
            StencilSite((0, 0, -2), _NI),  # backing below
        ),
    )
    sigma_h = _op_by_matrix(((1, 0, 0), (0, 1, 0), (0, 0, -1)))
    bottom = _transform(top, sigma_h, (0, 0, 0))  # vacuum now below
    assert C.class_id(bottom) == C.class_id(top)


# --------------------------------------------------------------------------- #
# depth_sig splitting (contract 11.2)                                         #
# --------------------------------------------------------------------------- #
def test_depth_sig_splits_identical_stencils() -> None:
    """Identical stencils with SURFACE / SUBSURF / BULK depth are distinct classes."""
    surface = _mk(depth_sig=DepthSig(DepthKind.SURFACE, 8))
    subsurf = _mk(depth_sig=DepthSig(DepthKind.SUBSURF, 1))
    bulk = _mk(depth_sig=DepthSig(DepthKind.BULK_OR_DEEPER, -1))
    ids = {C.class_id(surface), C.class_id(subsurf), C.class_id(bulk)}
    assert len(ids) == 3


# --------------------------------------------------------------------------- #
# Byte-exact TLV / class_id (contract 11.2, 7.3)                              #
# --------------------------------------------------------------------------- #
def _ref_tlv(obj: object) -> bytes:
    """Independent reference implementation of the contract-7.3 TLV encoding."""
    if isinstance(obj, bool):
        return b"\x01" + struct.pack(">q", int(obj))
    if isinstance(obj, int):
        return b"\x01" + struct.pack(">q", int(obj))
    if isinstance(obj, (tuple, list)):
        return b"\x02" + struct.pack(">I", len(obj)) + b"".join(_ref_tlv(e) for e in obj)
    raise TypeError(type(obj))


def test_tlv_hand_encoded_golden() -> None:
    """canonical_blob matches a fully hand-spelled TLV byte string."""
    # (7,) -> SEQ_TAG + len(1) + [ INT_TAG + int64(7) ]
    golden = b"\x02" + b"\x00\x00\x00\x01" + b"\x01" + b"\x00\x00\x00\x00\x00\x00\x00\x07"
    assert C.canonical_blob((7,)) == golden
    # a negative int uses two's complement big-endian.
    assert C.canonical_blob((-1,)) == (
        b"\x02\x00\x00\x00\x01\x01" + b"\xff\xff\xff\xff\xff\xff\xff\xff"
    )


def test_canonical_blob_and_class_id_byte_exact() -> None:
    """canonical_blob equals the reference TLV; class_id is its blake2b-256 hex."""
    pe = _mk()
    cf = C.canonical_form(pe)
    blob = C.canonical_blob(cf)
    assert blob == _ref_tlv(cf)
    assert C.class_id(pe) == hashlib.blake2b(blob, digest_size=32).hexdigest()
    assert len(C.class_id(pe)) == 64
    # class_id accepts a pre-computed canonical form too.
    assert C.class_id(cf) == C.class_id(pe)


def test_tlv_injectivity_distinct_structures() -> None:
    """Distinct nested structures produce distinct blobs (self-delimiting TLV)."""
    forms = [(1, 2), (1, (2,)), ((1, 2),), (1, 2, 0), ((),), (), (0,)]
    blobs = [C.canonical_blob(f) for f in forms]
    assert len(set(blobs)) == len(forms)


# --------------------------------------------------------------------------- #
# orientation_count (contract 11.2, 4.5)                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "pe",
    [
        _mk(),
        _mk(depth_sig=DepthSig(DepthKind.SURFACE, 8)),
        _symmetric_divacancy(),
        _mk(
            context=(
                StencilSite((0, 0, 0), _NI),
                StencilSite((2, 0, 0), _CR),
                StencilSite((1, 1, 0), _EMPTY),
            ),
        ),
    ],
)
def test_orientation_count_matches_orbit_stabilizer(pe: ProjectedEvent) -> None:
    """orientation_count == |orbit|, and |orbit| * |stabiliser| == |D4h| == 16."""
    oc = C.orientation_count(pe)
    a_star, _g = C.argmin_orientation(pe)
    identity = _op_by_matrix(IDENTITY)
    base = C.serialize_variant(pe, a_star, identity)
    stab = sum(1 for g in D4H if C.serialize_variant(pe, a_star, g) == base)
    assert oc * stab == 16
    assert 16 % oc == 0


# --------------------------------------------------------------------------- #
# self-reverse (contract 7.2, Sym-5)                                          #
# --------------------------------------------------------------------------- #
def test_self_reverse_symmetric_hop_true() -> None:
    """A hop whose endpoints have mirror-image contexts is self-reverse."""
    symmetric = _mk(
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
        context=(StencilSite((0, 0, 0), _NI), StencilSite((1, 1, 0), _EMPTY)),
    )
    assert C.is_self_reverse(symmetric) is True


def test_self_reverse_asymmetric_hop_false() -> None:
    """A hop into an asymmetric environment is not self-reverse."""
    asymmetric = _mk(
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((2, 0, 0), _CR),
            StencilSite((1, 1, 0), _EMPTY),
        ),
    )
    assert C.is_self_reverse(asymmetric) is False


def test_reverse_event_rebinds_saddle_tokens_multimover() -> None:
    """The concerted reverse binds each endpoint to its own forward saddle (Sym-6).

    Regression for the positional-``zip`` mis-bind: a 2-mover exchange with distinct
    saddle kinds (BRIDGE for the atom leaving (0,0,0), TOP for the atom leaving
    (2,2,0)) plus a Cr/Ni asymmetry. The reverse mover at each endpoint must carry the
    saddle mechanism of the forward mover that reached it -- (2,2,0) keeps BRIDGE,
    (0,0,0) keeps TOP -- not the delta-order token. A positional zip binds them
    swapped, yielding a different class_id.
    """
    bridge = PathToken(0, SaddleKind.BRIDGE, (6, 6))
    top = PathToken(0, SaddleKind.TOP, (7, 7))
    pe = _mk(
        delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.CR), DeltaSite((2, 2, 0), Occ.CR, Occ.NI)),
        context=(
            StencilSite((0, 0, 0), _NI),
            StencilSite((2, 2, 0), _CR),
            StencilSite((1, 1, 0), _EMPTY),
        ),
        movers=((0, 0, 0), (2, 2, 0)),
        saddle_tokens=(bridge, top),
    )
    rev = C._reverse_event(pe)
    assert rev is not None
    # correct physical reverse: (2,2,0) <- BRIDGE (m1's endpoint), (0,0,0) <- TOP.
    correct = _mk(
        delta=(DeltaSite((0, 0, 0), Occ.CR, Occ.NI), DeltaSite((2, 2, 0), Occ.NI, Occ.CR)),
        context=rev.context,
        movers=((2, 2, 0), (0, 0, 0)),
        saddle_tokens=(bridge, top),
    )
    wrong = replace(correct, saddle_tokens=(top, bridge))  # swapped (mis-bound) tokens
    assert C.class_id(rev) == C.class_id(correct)
    assert C.class_id(rev) != C.class_id(wrong)


# --------------------------------------------------------------------------- #
# move_shape / family_id (contract 11.2, 7.4)                                 #
# --------------------------------------------------------------------------- #
def test_move_shape_family_id_are_u32() -> None:
    """move_shape and family_id are 32-bit unsigned and deterministic in-process."""
    pe = _mk()
    ms, fid = C.move_shape(pe), C.family_id(pe)
    assert 0 <= ms <= 0xFFFFFFFF
    assert 0 <= fid <= 0xFFFFFFFF
    assert C.move_shape(pe) == ms and C.family_id(pe) == fid
    # family_id XORs in the packed depth; depth_hash is u32.
    assert C.family_id(pe) == (ms ^ C.depth_hash(pe.depth_sig)) & 0xFFFFFFFF


def test_move_shape_family_id_seed_independent() -> None:
    """move_shape / family_id are identical across two PYTHONHASHSEED subprocesses."""
    script = (
        "from pylatkmc.ingest import canonical as C\n"
        "from pylatkmc.ingest.event_class import (Coloring, DeltaSite, DepthKind, DepthSig,"
        " EventProjReport, Occ, OccPredicate, PathToken, ProjectedEvent, SaddleKind, StencilSite)\n"
        "pe = ProjectedEvent(anchor0=(0,0,0),"
        " delta=(DeltaSite((0,0,0),Occ.NI,Occ.EMPTY), DeltaSite((1,1,0),Occ.EMPTY,Occ.NI)),"
        " delta_atoms=0,"
        " context=(StencilSite((0,0,0),OccPredicate('SPECIES',frozenset({Occ.NI}))),"
        " StencilSite((1,1,0),OccPredicate('EMPTY')), StencilSite((2,0,0),OccPredicate('EMPTY'))),"
        " movers=((0,0,0),), saddle_tokens=(PathToken(0,SaddleKind.BRIDGE,(8,8)),),"
        " depth_sig=DepthSig(DepthKind.SURFACE,8), coloring=Coloring.FULL, r_ctx_used=5.0,"
        " truncated=False, Ea_fwd_eV=0.6, nu0_fwd_hz=1e13, k_row=1.0, id_saddle='s',"
        " id_final='f', event_id='e', idx_ref=0, idx_backward=-1, move_atom_idx=0, source_row=0,"
        " proj_report=EventProjReport(0.3,0.2,4.0,True))\n"
        "print(C.move_shape(pe), C.family_id(pe), C.class_id(pe))\n"
    )
    outs = []
    for seed in ("0", "1"):
        env = {**__import__("os").environ, "PYTHONHASHSEED": seed}
        res = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True
        )
        outs.append(res.stdout.strip())
    assert outs[0] == outs[1], f"seed-dependent output: {outs}"
