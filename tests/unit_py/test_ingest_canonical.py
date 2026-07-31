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
    Arrow,
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
        arrows=tuple(Arrow(tr(a.start), tr(a.end), a.species) for a in pe.arrows),
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
    arrows = (
        Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
        Arrow((2, 2, 0), (3, 1, 0), Occ.NI),
    )
    pe = _mk(movers=movers, saddle_tokens=tokens, delta=delta, context=context, arrows=arrows)
    cid = C.class_id(pe)

    # Reverse delta + context order, and swap the mover/token/arrow pairing order
    # together (mover m1 must keep its token t1 and its arrow a1).
    shuffled = replace(
        pe,
        delta=tuple(reversed(delta)),
        context=tuple(reversed(context)),
        movers=(movers[1], movers[0]),
        saddle_tokens=(tokens[1], tokens[0]),
        arrows=(arrows[1], arrows[0]),
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
        arrows=(Arrow((0, 0, 0), (1, 0, 1), Occ.NI),),
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
        # The 180-about-z + translate-(2,0,0) symmetry maps arrow 1 onto arrow 2.
        arrows=(
            Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
            Arrow((2, 0, 0), (1, -1, 0), Occ.NI),
        ),
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


def test_reverse_event_rebinds_saddle_tokens_and_inverts_arrows() -> None:
    """The concerted reverse binds each endpoint to its own forward saddle (Sym-6).

    Regression for the positional-``zip`` mis-bind: a 2-mover exchange with distinct
    saddle kinds (BRIDGE for the atom leaving (0,0,0), TOP for the atom leaving
    (2,2,0)) plus a Cr/Ni asymmetry. The reverse mover at each endpoint must carry
    the saddle mechanism of the forward mover that reached it -- (2,2,0) keeps
    BRIDGE, (0,0,0) keeps TOP -- not the delta-order token. Asserted on the fields
    directly (sharper than the old digest comparison). The reverse's **arrows**
    must be the inverted forward arrows -- under v3 they feed ``class_id``, so a
    stale (un-inverted) arrow set corrupts ``is_self_reverse``.
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
        arrows=(
            Arrow((0, 0, 0), (2, 2, 0), Occ.NI),
            Arrow((2, 2, 0), (0, 0, 0), Occ.CR),
        ),
    )
    rev = C._reverse_event(pe)
    assert rev is not None
    # correct physical reverse: (2,2,0) <- BRIDGE (m1's endpoint), (0,0,0) <- TOP.
    assert rev.movers == ((2, 2, 0), (0, 0, 0))
    assert rev.saddle_tokens == (bridge, top)
    # arrows inverted, species carried along (forward order preserved).
    assert rev.arrows == (
        Arrow((2, 2, 0), (0, 0, 0), Occ.NI),
        Arrow((0, 0, 0), (2, 2, 0), Occ.CR),
    )


# --------------------------------------------------------------------------- #
# move_shape (contract 11.2, 7.4; CANON family_id dropped at v3, ruling 2)    #
# --------------------------------------------------------------------------- #
def test_move_shape_is_u32_and_family_id_is_gone() -> None:
    """move_shape stays a deterministic u32; the CANON family_id is deleted at v3.

    Ruling 2 (memo §11): the u32 ``family_id = move_shape ^ depth_hash`` was
    measured fully redundant (a pure function of ``move_shape``, 821 = 821) and is
    dropped with the v3 identity bump. The unrelated FAMILY_REGISTRY string
    ``family_id`` (``families.py``) is untouched.
    """
    pe = _mk()
    ms = C.move_shape(pe)
    assert 0 <= ms <= 0xFFFFFFFF
    assert C.move_shape(pe) == ms
    assert 0 <= C.depth_hash(pe.depth_sig) <= 0xFFFFFFFF
    assert not hasattr(C, "family_id")


def test_move_shape_class_id_seed_independent() -> None:
    """move_shape / class_id are identical across two PYTHONHASHSEED subprocesses."""
    script = (
        "from pylatkmc.ingest import canonical as C\n"
        "from pylatkmc.ingest.event_class import (Arrow, Coloring, DeltaSite, DepthKind, DepthSig,"
        " EventProjReport, Occ, OccPredicate, PathToken, ProjectedEvent, SaddleKind, StencilSite)\n"
        "pe = ProjectedEvent(anchor0=(0,0,0),"
        " delta=(DeltaSite((0,0,0),Occ.NI,Occ.EMPTY), DeltaSite((1,1,0),Occ.EMPTY,Occ.NI)),"
        " delta_atoms=0,"
        " context=(StencilSite((0,0,0),OccPredicate('SPECIES',frozenset({Occ.NI}))),"
        " StencilSite((1,1,0),OccPredicate('EMPTY')), StencilSite((2,0,0),OccPredicate('EMPTY'))),"
        " movers=((0,0,0),), saddle_tokens=(PathToken(0,SaddleKind.BRIDGE,(8,8)),),"
        " arrows=(Arrow((0,0,0),(1,1,0),Occ.NI),),"
        " depth_sig=DepthSig(DepthKind.SURFACE,8), coloring=Coloring.FULL, r_ctx_used=5.0,"
        " truncated=False, Ea_fwd_eV=0.6, nu0_fwd_hz=1e13, k_row=1.0, id_saddle='s',"
        " id_final='f', event_id='e', idx_ref=0, idx_backward=-1, move_atom_idx=0, source_row=0,"
        " proj_report=EventProjReport(0.3,0.2,4.0,True))\n"
        "print(C.move_shape(pe), C.class_id(pe))\n"
    )
    outs = []
    for seed in ("0", "1"):
        env = {**__import__("os").environ, "PYTHONHASHSEED": seed}
        res = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True
        )
        outs.append(res.stdout.strip())
    assert outs[0] == outs[1], f"seed-dependent output: {outs}"


# --------------------------------------------------------------------------- #
# CANON v3: class_id = action ‖ context (fingerprint memo §7 Phase 2)         #
# --------------------------------------------------------------------------- #
def test_v3_form_layout_and_action_row_lockstep() -> None:
    """The v3 form is (3, coloring, Δatoms, depth×2, action, delta, context, saddle).

    The action field holds the DIRECTED arrow rows in the winning joint
    ``(a*, g*)`` frame — byte-identical to ``action.serialize_action_variant``'s
    row encoding for the same transform (the lockstep that lets
    ``ACTION_SCHEMA_VERSION`` stay a separate namespace: an arrow-row encoding
    change must bump both versions).
    """
    from pylatkmc.ingest.action import serialize_action_variant

    pe = _mk()
    cf = C.canonical_form(pe)
    assert cf[0] == C.CANON_SCHEMA_VERSION == 3
    # version, coloring, delta_atoms, depth×2, action, delta, context, saddle
    assert len(cf) == 9
    a_star, g_star = C.argmin_orientation(pe)
    assert cf[5] == serialize_action_variant(pe.arrows, a_star, g_star, grey=False)
    assert len(cf[5]) == len(pe.movers)

    # GREY lockstep too (review 2026-07-31 #11): the canonical action rows must
    # match the action module's GREY serialization on a grey-coloured event.
    grey = replace(pe, coloring=Coloring.GREY)
    cf_g = C.canonical_form(grey)
    a_g, g_g = C.argmin_orientation(grey)
    assert cf_g[5] == serialize_action_variant(grey.arrows, a_g, g_g, grey=True)


def test_v3_chain_vs_hop_distinct() -> None:
    """A 120° 2-chain and a 1NN hop with identical delta+context split (§2.3).

    Chain: A=(0,0,0) → B=(1,0,1) → V=(1,1,0); net A→V is 1NN, so its ``delta``
    is *exactly* a 1NN hop's. The action axis must separate them.
    """
    shared_context = (
        StencilSite((0, 0, 0), _NI),
        StencilSite((1, 0, 1), _NI),
        StencilSite((1, 1, 0), _EMPTY),
        StencilSite((2, 0, 0), _EMPTY),
    )
    hop = _mk(context=shared_context)
    tok = PathToken(0, SaddleKind.BRIDGE, (8, 8))
    chain = _mk(
        context=shared_context,
        movers=((0, 0, 0), (1, 0, 1)),
        saddle_tokens=(tok, tok),
        arrows=(
            Arrow((0, 0, 0), (1, 0, 1), Occ.NI),
            Arrow((1, 0, 1), (1, 1, 0), Occ.NI),
        ),
    )
    assert hop.delta == chain.delta  # the conflation being fixed: same occupancy delta
    assert C.class_id(hop) != C.class_id(chain)


def _x3_ring(clockwise: bool) -> ProjectedEvent:
    """A same-species 3-ring A→B→C→A (or its reversal) with a chirality-pinning Cr.

    All three sites hold Ni before and after, so ``delta`` is EMPTY — the §2.3
    delta-less blindness. The Cr spectator at (0,2,0) breaks the triangle's only
    orientation-reversing D4h symmetry (x → 2−x), so the two ring orientations are
    genuinely different physical classes.
    """
    a, b, c = (0, 0, 0), (1, 1, 0), (2, 0, 0)
    fwd = (Arrow(a, b, Occ.NI), Arrow(b, c, Occ.NI), Arrow(c, a, Occ.NI))
    rev = tuple(Arrow(x.end, x.start, x.species) for x in fwd)
    tok = PathToken(0, SaddleKind.BRIDGE, (8, 8))
    return _mk(
        delta=(),
        delta_atoms=0,
        context=(
            StencilSite(a, _NI),
            StencilSite(b, _NI),
            StencilSite(c, _NI),
            StencilSite((0, 2, 0), _CR),
        ),
        movers=(a, b, c),
        saddle_tokens=(tok, tok, tok),
        arrows=fwd if clockwise else rev,
    )


def test_v3_ring_orientation_split_delta_less_blindness_retired() -> None:
    """Two orientations of a same-species X3 ring are distinct classes under v3.

    Both events have empty ``delta``, identical movers/tokens/context — under v2
    nothing separated them (§2.3: same-species intermediates are
    occupancy-invisible). The directed action rows must split them.
    """
    cw, ccw = _x3_ring(True), _x3_ring(False)
    assert cw.delta == ccw.delta == ()
    assert C.class_id(cw) != C.class_id(ccw)


def test_v3_same_species_exchange_distinct_from_no_op() -> None:
    """An X2 exchange (empty delta, real arrows) is not the NO_OP class.

    The arrows (and tokens) keep a same-species direct exchange distinct from
    true basin-internal NO_OP motion in the same context — under v3 the
    distinction is identity-bearing on the action axis, not only on token count.
    """
    ctx = (StencilSite((0, 0, 0), _NI), StencilSite((1, 1, 0), _NI))
    tok = PathToken(0, SaddleKind.BRIDGE, (8, 8))
    x2 = _mk(
        delta=(),
        context=ctx,
        movers=((0, 0, 0), (1, 1, 0)),
        saddle_tokens=(tok, tok),
        arrows=(
            Arrow((0, 0, 0), (1, 1, 0), Occ.NI),
            Arrow((1, 1, 0), (0, 0, 0), Occ.NI),
        ),
    )
    no_op = _mk(delta=(), context=ctx, movers=(), saddle_tokens=(), arrows=())
    assert C.class_id(x2) != C.class_id(no_op)


def test_v3_saddle_tokens_stay_in_the_digest() -> None:
    """Two events differing ONLY in saddle-token kind remain DISTINCT classes.

    Deliberate deviation from the memo §3.2 "not an identity fact" reading
    (adversarial review 2026-07-31, finding 3): the aggregate rate path fires one
    proc at the class mean, so pooling a genuine mechanism mixture would fire the
    dominant channel at half its measured rate. Mechanism channels stay separate
    classes (their procs' rates then ADD, as §3.2 requires); dropping tokens from
    identity must ride a future bump bundled with rate-side channel summing.
    """
    a = _mk()
    b = _mk(saddle_tokens=(PathToken(0, SaddleKind.HOLLOW_FCC, (7, 7, 7)),))
    assert a.saddle_tokens != b.saddle_tokens
    assert C.class_id(a) != C.class_id(b)


def _v2_emulated_key(pe: ProjectedEvent) -> tuple:
    """The v2 canonical key, emulated on the v3 serializer: drop the action field
    (index 2) from every variant and re-minimise over the same (anchor, g) set."""
    best = None
    for a in C.candidate_anchors(pe):
        for g in D4H:
            v = C.serialize_variant(pe, a, g)
            v2 = (v[0], v[1], v[3], v[4], v[5])
            if best is None or v2 < best:
                best = v2
    return (int(pe.coloring), int(pe.delta_atoms), best)


def test_v3_strictly_finer_than_v2_no_merges() -> None:
    """v3 identity = v2 fields + the action field, so a bump can only SPLIT.

    The real lock the migration gate battery (M4) relies on: over a deterministic
    fuzz corpus, equal v3 canonical forms imply equal v2-emulated keys — zero
    merges are possible. The corpus includes the targeted arrow-permutation pairs
    that v2 conflates and v3 splits (the converse direction).
    """
    events = [
        _mk(),
        _mk(depth_sig=DepthSig(DepthKind.SURFACE, 8)),
        _symmetric_divacancy(),
        _x3_ring(True),
        _x3_ring(False),
        _mk(
            delta=(
                DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
                DeltaSite((1, 0, 1), Occ.EMPTY, Occ.NI),
            ),
            context=(StencilSite((0, 0, 0), _NI), StencilSite((1, 0, 1), _EMPTY)),
            arrows=(Arrow((0, 0, 0), (1, 0, 1), Occ.NI),),
        ),
    ]
    forms = [C.canonical_form(e) for e in events]
    keys = [_v2_emulated_key(e) for e in events]
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if forms[i] == forms[j]:
                assert keys[i] == keys[j], "v3-equal events split under v2: merge possible"
    # converse: the ring pair is v2-equal but v3-distinct (a genuine split).
    cw, ccw = events[3], events[4]
    assert _v2_emulated_key(cw) == _v2_emulated_key(ccw)
    assert C.canonical_form(cw) != C.canonical_form(ccw)


def test_v3_movers_without_aligned_arrows_raise() -> None:
    """A mover-ful event with missing/misaligned arrows is rejected loudly.

    Under v3 the arrows feed ``class_id``; silently digesting an empty action
    for an event that moved atoms would resurrect the §2.3 blindness for any
    caller that forgot to thread ``arrows`` through.
    """
    with pytest.raises(ValueError, match="arrows"):
        C.class_id(_mk(arrows=()))
    with pytest.raises(ValueError, match="arrows"):
        C.class_id(
            _mk(arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.NI), Arrow((1, 1, 0), (2, 0, 0), Occ.NI)))
        )


def test_v3_grey_collapses_arrow_species() -> None:
    """In GREY colouring the action rows collapse species exactly as the context does."""
    ni = _mk(coloring=Coloring.GREY)
    cr = _mk(
        coloring=Coloring.GREY,
        delta=(DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY), DeltaSite((1, 1, 0), Occ.EMPTY, Occ.CR)),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.CR),),
    )
    assert C.class_id(ni) == C.class_id(cr)


def test_v3_pinned_digest_byte_stable() -> None:
    """The default hop fixture's v3 class_id is pinned byte-for-byte.

    Guards the digest against silent serialization drift (field order, TLV
    encoding, version prefix). Any deliberate identity change MUST bump
    ``CANON_SCHEMA_VERSION`` and re-pin this value.
    """
    assert C.class_id(_mk()) == _V3_PINNED_HOP_CLASS_ID


# Pinned 2026-07-31 against the landed v3 implementation (CANON_SCHEMA_VERSION 3);
# see test_v3_pinned_digest_byte_stable.
_V3_PINNED_HOP_CLASS_ID = "c2626bb111be8f6445941829bf83f0c832bf9b33ed557992d0a2d9742932d387"
