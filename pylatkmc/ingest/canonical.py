"""Class identity: the complete orbit invariant (Phase A, Agent A5).

Produces the authoritative class identity of a :class:`ProjectedEvent` under the
group ``translation x D4h x internal automorphism``, minimised **jointly over
anchor choice and group element** (contract sections 6 + 7; ``FINAL_DESIGN``
section 4). Two harvest orientations of the same physical event -- including a
symmetric divacancy where the two movers tie, or a top/bottom surface pair
related by the horizontal mirror -- canonicalise to the **same** ``class_id``.

The pipeline is:

1. :func:`serialize_variant` re-expresses everything relative to a chosen anchor,
   rotates by a chosen ``g in D4H``, and builds a totally-ordered **integer** tuple
   (contract 7.1).
2. :func:`canonical_form` takes the ``min`` of that variant over every candidate
   anchor x every group op, then prepends the ``(version, coloring, delta_atoms)``
   plus ``depth`` prefix (contract 7.2). This nested integer tuple is
   **authoritative and tolerance-free**.
3. :func:`canonical_blob` serialises the form with the normative self-delimiting
   TLV encoding (contract 7.3); :func:`class_id` is its ``blake2b`` digest -- the
   index into the catalogue.

Determinism (contract 0.1, hard gate)
-------------------------------------
Nothing here uses ``hash()``, ``set``/``dict`` iteration order, ``PYTHONHASHSEED``,
or any floating point. Identity is computed over integer lattice offsets and
integer categorical codes only; every reduction iterates a **sorted** list; the
only digest is ``hashlib.blake2b`` over the integer TLV bytes. ``move_shape``
is a ``blake2b``-derived u32, likewise seed-independent.

Module-load DAG (contract 0.2)
------------------------------
``canonical -> lattice, event_class``. Both are imported at module level (safe:
``event_class`` never imports ``canonical`` at load time; ``event_class``'s
assembly path imports this module lazily).
"""

from __future__ import annotations

import hashlib
import itertools
import struct
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from pylatkmc.ingest.event_class import (
    Arrow,
    Coloring,
    DeltaSite,
    DepthSig,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    StencilSite,
)
from pylatkmc.ingest.lattice import D4H, NN12_OFFSETS, Offset, SymOp, apply_op

# --------------------------------------------------------------------------- #
# 0.4 Constants                                                               #
# --------------------------------------------------------------------------- #
CANON_SCHEMA_VERSION: int = 3
"""Serialization version prefix. Bumping it changes every ``class_id``.

v1 -> v2 (2026-07-29, over-snapping memo §8.1): the §6 bystander mask changes
canonical content for ~1/5 of classes, so every ``class_id`` changes loudly —
the version prefix exists precisely to make cross-policy merges impossible
(an unbumped merge would silently double-count masked classes under two ids).

v2 -> v3 (2026-07-30, action x context fingerprint memo §7 Phase 2, ruling 8):
``class_id`` gains the event's DIRECTED arrow rows as a separate TLV field —
the action axis becomes identity content. This splits the §2.3 chain-vs-hop
conflation and retires the delta-less identity blindness at the identity level
(X2 rings / same-species intermediates get distinct ids; they remain
quarantined/skipped downstream — a delta-less class is still not executable
on-lattice). ``delta_seq`` is retained: for conserving events it is a pure
function of the arrows (harmless), and for the deferred non-conserving bucket
(memo §5.3 — SINK-terminal arrows not yet formalised) it still carries identity
the arrows cannot.

**Deliberate deviation from the memo's literal "action ‖ context" split:** the
saddle-token field STAYS in the digest at v3. Memo §3.2 argues mechanism labels
are "not an identity fact" — but its remedy for a genuine mechanism split
("parallel channels and their rates add") only holds while the channels are
separate classes emitting separate procs: the aggregate rate path
(``aggregate_rate_space`` -> one proc at ``Ea_rep``) AVERAGES a class's members,
so merging a 0.55 eV BRIDGE channel with a 0.95 eV TOP channel would fire the
dominant channel at half its measured rate (adversarial review 2026-07-31,
finding 3). Dropping tokens from identity therefore must ride a future bump
bundled with a rate-side change that sums parallel channels. Consequence kept
by the migration gates: v3 identity is strictly FINER than v2 (v3 = v2 fields +
action field), so a v2->v3 rebuild can only SPLIT classes, never merge them.

Version-namespace composition (decided at Phase 2): the class digest embeds the
arrow ROWS under **this** version's sole authority — it does not embed
``action.ACTION_SCHEMA_VERSION``, which keeps governing only the standalone
``action_id``/``archetype`` digests. The two share the 7-int arrow-row encoding
(pinned by ``test_v3_form_layout_and_action_row_lockstep``); changing that row
encoding therefore requires bumping BOTH versions.
"""

_INT_TAG = b"\x01"
"""TLV tag for an integer leaf (contract 7.3)."""

_SEQ_TAG = b"\x02"
"""TLV tag for a sequence node (contract 7.3)."""

#: The authoritative nested-integer canonical form / per-variant tuple. Kept as
#: ``tuple[Any, ...]`` because the nesting is heterogeneous (ints + int-rows +
#: token rows); the total order is ordinary Python tuple comparison over ints.
CanonicalForm = tuple[Any, ...]
Variant = tuple[Any, ...]


# --------------------------------------------------------------------------- #
# Integer categorical codes (contract 7.1)                                    #
# --------------------------------------------------------------------------- #
def _occ_code(o: Occ, coloring: Coloring) -> int:
    """Occupancy integer code for the canonical key (contract 7.1).

    ``EMPTY -> 0``, ``OUTSIDE -> 255``, ``OCC_ANY -> 254``; a real occupied
    species keeps its ``Occ`` int in FULL colour and collapses to ``254`` in GREY.
    """
    io = int(o)
    if io == int(Occ.EMPTY):
        return 0
    if io == int(Occ.OUTSIDE):
        return 255
    if io == int(Occ.OCC_ANY):
        return int(Occ.OCC_ANY)
    if coloring == Coloring.GREY:
        return int(Occ.OCC_ANY)
    return io


def _occ_is_occupied(o: Occ) -> bool:
    """True iff ``o`` is a real/collapsed occupancy (not EMPTY / OUTSIDE)."""
    io = int(o)
    return io != int(Occ.EMPTY) and io != int(Occ.OUTSIDE)


def _pred_is_occupied(pred: OccPredicate) -> bool:
    """True iff a context predicate marks an occupied site (SPECIES or OCC_ANY)."""
    return pred.kind in ("SPECIES", "OCC_ANY")


def _occ_to_pred(o: Occ) -> OccPredicate:
    """Map an occupancy code to the equivalent per-site predicate."""
    io = int(o)
    if io == int(Occ.EMPTY):
        return OccPredicate(kind="EMPTY")
    if io == int(Occ.OUTSIDE):
        return OccPredicate(kind="OUTSIDE")
    if io == int(Occ.OCC_ANY):
        return OccPredicate(kind="OCC_ANY")
    return OccPredicate(kind="SPECIES", species=frozenset({Occ(io)}))


# --------------------------------------------------------------------------- #
# 6 / 4.2 Candidate anchors                                                   #
# --------------------------------------------------------------------------- #
def candidate_anchors(pe: ProjectedEvent) -> list[Offset]:
    """Every moved site is a candidate anchor (contract 4.2 / 6).

    Reference semantics: return all of ``pe.movers``. No ``lex(offset)`` tie-break
    ever enters identity -- offsets are frame-dependent. Falls back to
    ``pe.anchor0`` only for the degenerate (mover-free) event so the ``min`` is
    always well-defined.
    """
    if pe.movers:
        return list(pe.movers)
    return [pe.anchor0]


# --------------------------------------------------------------------------- #
# 6 Deterministic mover order in a given (anchor, g)                           #
# --------------------------------------------------------------------------- #
def canonical_rank_map(movers: Sequence[Offset], anchor: Offset, g: SymOp) -> dict[Offset, int]:
    """Deterministic mover order in this ``(anchor, g)`` (contract 6).

    ``key(m) = apply_op(g, m - anchor)``; ``rank`` is the position of ``m`` after
    a lexicographic sort of the keys. Movers are distinct sites and ``g`` is a
    bijection, so keys are distinct -> no ties.
    """
    a0, a1, a2 = anchor
    keyed: list[tuple[Offset, Offset]] = []
    for m in movers:
        k = apply_op(g, (m[0] - a0, m[1] - a1, m[2] - a2))
        keyed.append((k, m))
    keyed.sort(key=lambda p: p[0])
    return {m: i for i, (_k, m) in enumerate(keyed)}


# --------------------------------------------------------------------------- #
# 7.1 Per-(anchor, g) variant tuple                                           #
# --------------------------------------------------------------------------- #
def serialize_variant(pe: ProjectedEvent, anchor: Offset, g: SymOp) -> Variant:
    """Build the comparable integer tuple for one ``(anchor, g)`` (contract 7.1).

    With ``T(x) = apply_op(g, x - anchor)`` returns
    ``(depth_kind, depth_param, action_seq, delta_seq, context_seq, saddle_seq)``
    -- all nested tuples of ints, totally ordered by ordinary Python tuple
    comparison.

    v3 (fingerprint memo §7 Phase 2): ``action_seq`` is the event's DIRECTED
    arrow rows ``(T(start), T(end), species_code)`` -- the same 7-int row
    encoding as ``action.serialize_action_variant`` (lockstep-tested), but with
    **no** ``{A, A⁻¹}`` minimisation: a class is directional (``backward_class``
    links forward and backward classes; merging them here would destroy the
    pairing/rate machinery). ``saddle_seq`` stays -- see the
    :data:`CANON_SCHEMA_VERSION` deviation note (dropping it must ride a
    rate-side change that sums parallel channels).
    """
    coloring = pe.coloring
    a0, a1, a2 = anchor

    def _t(off: Offset) -> Offset:
        return apply_op(g, (off[0] - a0, off[1] - a1, off[2] - a2))

    action_rows: list[tuple[int, ...]] = []
    for arw in pe.arrows:
        s = _t(arw.start)
        e = _t(arw.end)
        action_rows.append((s[0], s[1], s[2], e[0], e[1], e[2], _occ_code(arw.species, coloring)))
    action_seq = tuple(sorted(action_rows))

    delta_rows: list[tuple[int, ...]] = []
    for ds in pe.delta:
        t = _t(ds.off)
        delta_rows.append(
            (t[0], t[1], t[2], _occ_code(ds.before, coloring), _occ_code(ds.after, coloring))
        )
    delta_seq = tuple(sorted(delta_rows))

    context_rows: list[tuple[int, ...]] = []
    for cs in pe.context:
        t = _t(cs.off)
        context_rows.append((t[0], t[1], t[2], cs.pred.code(coloring)))
    context_seq = tuple(sorted(context_rows))

    ranks = canonical_rank_map(pe.movers, anchor, g)
    mover_tokens = list(zip(pe.movers, pe.saddle_tokens, strict=True))
    mover_tokens.sort(key=lambda mt: ranks[mt[0]])
    saddle_seq = tuple(
        (ranks[m], int(tok.kind), tuple(int(c) for c in tok.coord_sig)) for m, tok in mover_tokens
    )

    depth_kind = int(pe.depth_sig.kind)
    depth_param = int(pe.depth_sig.param)
    return (depth_kind, depth_param, action_seq, delta_seq, context_seq, saddle_seq)


# --------------------------------------------------------------------------- #
# 7.2 Authoritative canonical form + argmin orientation                       #
# --------------------------------------------------------------------------- #
def _argmin(pe: ProjectedEvent) -> tuple[Variant, Offset, SymOp]:
    """Return ``(best_variant, a*, g*)`` -- the joint anchor x group minimum.

    Iteration order is anchors (in ``candidate_anchors`` = mover order) then ops
    (in ``D4H`` index order); a strict ``<`` keeps the **first** ``(a, g)`` that
    achieves the minimum, giving the ``(mover_index, op_index)`` tie-break of
    resolution 7 without affecting the key.

    Hard guard (v3): the arrows feed ``class_id``, so an event that moved atoms
    but carries no (or misaligned) arrows would silently digest an empty action
    -- resurrecting the §2.3 blindness for any caller that forgot to thread
    ``arrows`` through. Rejected loudly instead.
    """
    if len(pe.arrows) != len(pe.movers) or sorted(a.start for a in pe.arrows) != sorted(pe.movers):
        raise ValueError(
            f"ProjectedEvent has movers {tuple(pe.movers)} but arrows starting at "
            f"{tuple(a.start for a in pe.arrows)}; the v3 identity digests the action "
            "axis, so arrows must align 1:1 with movers (same start sites)"
        )
    best_v: Variant | None = None
    best_a: Offset | None = None
    best_g: SymOp | None = None
    for a in candidate_anchors(pe):
        for g in D4H:
            v = serialize_variant(pe, a, g)
            if best_v is None or v < best_v:
                best_v = v
                best_a = a
                best_g = g
    assert best_v is not None and best_a is not None and best_g is not None
    return best_v, best_a, best_g


def canonical_form(pe: ProjectedEvent) -> CanonicalForm:
    """The authoritative nested-integer canonical form (contract 7.2).

    ``min`` over ``candidate_anchors(pe) x D4H`` of :func:`serialize_variant`, with
    the ``(a, g)``-invariant ``(version, coloring, delta_atoms, depth_kind,
    depth_param)`` prefix prepended after the argmin. Tolerance-free; the digest
    is an index over this tuple. The action and context axes are separate TLV
    fields minimised **jointly** -- minimising them independently would forget
    their relative orientation and collide distinct classes.
    """
    best, _a, _g = _argmin(pe)
    return (
        CANON_SCHEMA_VERSION,
        int(pe.coloring),
        int(pe.delta_atoms),
        best[0],  # depth_kind
        best[1],  # depth_param
        best[2],  # action_seq (directed arrow rows)
        best[3],  # delta_seq
        best[4],  # context_seq
        best[5],  # saddle_seq
    )


def argmin_orientation(pe: ProjectedEvent) -> tuple[Offset, SymOp]:
    """Return the winning ``(a*, g*)`` -- the execution orientation (contract 6)."""
    _v, a_star, g_star = _argmin(pe)
    return a_star, g_star


# --------------------------------------------------------------------------- #
# 7.3 TLV byte encoding -> class_id                                           #
# --------------------------------------------------------------------------- #
def _encode(obj: Any) -> bytes:
    """Self-delimiting TLV encoding of a nested int/tuple form (contract 7.3).

    ``INT_TAG + pack('>q', v)`` for an int (``bool`` handled first: it is an
    ``int`` subclass); ``SEQ_TAG + pack('>I', n) + children`` for a sequence. This
    matches ``event_class._tlv_encode`` byte-for-byte so a catalogue round-trips.
    """
    if isinstance(obj, bool):
        return _INT_TAG + struct.pack(">q", int(obj))
    if isinstance(obj, int):
        return _INT_TAG + struct.pack(">q", int(obj))
    if isinstance(obj, (tuple, list)):
        return _SEQ_TAG + struct.pack(">I", len(obj)) + b"".join(_encode(e) for e in obj)
    raise TypeError(f"canonical_form may only hold ints and tuples, got {type(obj)!r}")


def canonical_blob(cf: CanonicalForm) -> bytes:
    """TLV bytes of a canonical form (contract 7.3) -- the hashed, stored form."""
    return _encode(cf)


def class_id(pe_or_cf: ProjectedEvent | CanonicalForm) -> str:
    """64-char ``blake2b``-256 hex of the canonical blob (contract 7.3).

    Accepts either a :class:`ProjectedEvent` (canonicalised first) or an
    already-computed canonical form.
    """
    cf = canonical_form(pe_or_cf) if isinstance(pe_or_cf, ProjectedEvent) else pe_or_cf
    return hashlib.blake2b(canonical_blob(cf), digest_size=32).hexdigest()


# --------------------------------------------------------------------------- #
# 4.5 Orientation orbit count                                                 #
# --------------------------------------------------------------------------- #
def orientation_count(pe: ProjectedEvent) -> int:
    """``|D4h| / |Stab|`` -- distinct oriented patterns of the class (contract 4.5).

    The 16 images of the canonical decorated stencil (taken about the canonical
    anchor ``a*``) are de-duplicated. The count is a class invariant: two events
    with the same ``class_id`` share the same canonical pattern, hence the same
    orbit. Counted by a sort + adjacent-compare (no ``set``/``hash``).
    """
    _v, a_star, _g = _argmin(pe)
    images = sorted(serialize_variant(pe, a_star, g) for g in D4H)
    count = 1
    for i in range(1, len(images)):
        if images[i] != images[i - 1]:
            count += 1
    return count


# --------------------------------------------------------------------------- #
# 7.2 / Sym-5 Self-reverse                                                     #
# --------------------------------------------------------------------------- #
#: Largest mover count for exact (permutation) start->endpoint matching in
#: :func:`_match_reverse_movers`; above it, a deterministic greedy fallback runs.
_MAX_MATCH_BRUTE = 7


def _sq_dist(a: Offset, b: Offset) -> int:
    """Squared integer lattice distance between two offsets."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _match_reverse_movers(
    starts: Sequence[Offset],
    tokens: Sequence[PathToken],
    endpoints: Sequence[Offset],
) -> tuple[tuple[Offset, ...], tuple[PathToken, ...]] | None:
    """Bind each forward saddle token to the endpoint its forward mover reached.

    The reverse of forward mover ``i`` (which started at ``starts[i]`` and traversed
    saddle ``tokens[i]``) starts at that mover's *endpoint* and traverses the **same**
    saddle back. We recover the start->endpoint pairing by the minimum total squared
    displacement -- the atoms moved to the sites they are nearest to -- forbidding a
    self-match (a mover never "reaches" its own start, which correctly handles the
    exchange case where a start site is also an endpoint). Ties break on the
    lexicographically smallest permutation, so the result is deterministic.

    Returns paired ``(rev_movers, rev_tokens)`` with ``rev_movers[i]`` (an endpoint)
    bound to ``rev_tokens[i]`` (the token of the forward mover that reached it), or
    ``None`` when no self-avoiding matching exists.
    """
    n = len(starts)
    if n != len(endpoints) or n != len(tokens):
        return None

    def cost(i: int, j: int) -> int | None:
        if starts[i] == endpoints[j]:
            return None  # forbidden self-match
        return _sq_dist(starts[i], endpoints[j])

    if n <= _MAX_MATCH_BRUTE:
        best_key: tuple[int, tuple[int, ...]] | None = None
        best_perm: tuple[int, ...] | None = None
        for perm in itertools.permutations(range(n)):
            total = 0
            ok = True
            for i, j in enumerate(perm):
                c = cost(i, j)
                if c is None:
                    ok = False
                    break
                total += c
            if not ok:
                continue
            key = (total, perm)
            if best_key is None or key < best_key:
                best_key = key
                best_perm = perm
        if best_perm is None:
            return None
        rev_movers = tuple(endpoints[best_perm[i]] for i in range(n))
        rev_tokens = tuple(tokens[i] for i in range(n))
        return rev_movers, rev_tokens

    # Greedy nearest self-avoiding matching (rare: many concerted movers).
    remaining = list(range(n))
    rev_movers_list: list[Offset] = [(0, 0, 0)] * n
    for i in sorted(range(n), key=lambda idx: starts[idx]):
        cands = sorted(
            ((c, endpoints[j], j) for j in remaining if (c := cost(i, j)) is not None),
            key=lambda t: (t[0], t[1]),
        )
        if not cands:
            return None
        j = cands[0][2]
        remaining.remove(j)
        rev_movers_list[i] = endpoints[j]
    return tuple(rev_movers_list), tuple(tokens)


def _reverse_event(pe: ProjectedEvent) -> ProjectedEvent | None:
    """The reverse event: ``before <-> after`` swapped, context -> after-state.

    Each reverse mover starts at a forward *endpoint* (an after-occupied site) and is
    re-bound to the saddle token of the forward mover that reached it -- **not** the
    positional forward order -- via :func:`_match_reverse_movers`. Without this
    re-binding, ``serialize_variant``'s positional ``zip(movers, saddle_tokens)`` would
    pair each reverse mover with an arbitrary forward mover's saddle mechanism whenever
    the offset ordering of endpoints differs from that of the starts (any concerted
    multi-mover event), corrupting the self-reverse test.

    Returns ``None`` when a well-defined reverse cannot be built (no site is occupied
    after the forward move, the endpoint count does not match the saddle-token / mover
    count, or no self-avoiding start->endpoint matching exists).
    """
    rev_delta = tuple(DeltaSite(ds.off, ds.after, ds.before) for ds in pe.delta)
    after_occ: dict[Offset, Occ] = {ds.off: ds.after for ds in pe.delta}
    rev_context = tuple(
        StencilSite(cs.off, _occ_to_pred(after_occ[cs.off])) if cs.off in after_occ else cs
        for cs in pe.context
    )
    endpoints = tuple(ds.off for ds in pe.delta if _occ_is_occupied(ds.after))
    if not endpoints or len(endpoints) != len(pe.saddle_tokens) or len(endpoints) != len(pe.movers):
        return None
    matched = _match_reverse_movers(pe.movers, pe.saddle_tokens, endpoints)
    if matched is None:
        return None
    rev_movers, rev_tokens = matched
    # v3: the arrows feed class_id, so the reverse event must carry the INVERTED
    # arrow set (species riding along); stale forward arrows would corrupt the
    # is_self_reverse comparison. When the inverted starts (= forward arrow ends)
    # do not cover the delta-derived reverse movers -- a delta-invisible arrival
    # or a non-conserving oddity -- there is no well-defined reverse: return
    # ``None`` rather than hand ``canonical_form`` a guard-tripping event.
    rev_arrows = tuple(Arrow(a.end, a.start, a.species) for a in pe.arrows)
    if sorted(a.start for a in rev_arrows) != sorted(rev_movers):
        return None
    return replace(
        pe,
        delta=rev_delta,
        delta_atoms=-pe.delta_atoms,
        context=rev_context,
        movers=rev_movers,
        saddle_tokens=rev_tokens,
        arrows=rev_arrows,
    )


def is_self_reverse(pe: ProjectedEvent) -> bool:
    """True iff the reverse event canonicalises to the same class (contract 7.2).

    A ``g in D4h`` (and anchor) maps the ``before <-> after``-swapped decorated
    event onto the forward one exactly when their canonical forms coincide -- the
    ``min`` over anchor x group is precisely that existential quantifier.
    """
    rev = _reverse_event(pe)
    if rev is None:
        return False
    return canonical_form(rev) == canonical_form(pe)


# --------------------------------------------------------------------------- #
# 7.4 move_shape / depth_hash (u32)                                           #
# --------------------------------------------------------------------------- #
def _grey_core_event(pe: ProjectedEvent) -> ProjectedEvent:
    """The species-blind core sub-event (contract 7.4).

    GREY coloring; context restricted to the **occupied** 1st shell (``NN12``) of
    the moved sites. ``delta`` / ``movers`` / ``saddle_tokens`` / ``depth_sig`` are
    retained so :func:`canonical_form` canonicalises the core the same way.
    """
    shell1: set[Offset] = set()
    for ds in pe.delta:
        m = ds.off
        for nn in NN12_OFFSETS:
            shell1.add((m[0] + nn[0], m[1] + nn[1], m[2] + nn[2]))
    core_context = tuple(cs for cs in pe.context if cs.off in shell1 and _pred_is_occupied(cs.pred))
    return replace(pe, coloring=Coloring.GREY, context=core_context)


def move_shape(pe: ProjectedEvent) -> int:
    """u32 species-blind core digest (contract 7.4).

    ``blake2b-4`` of the TLV-encoded GREY core canonical form; deterministic and
    ``PYTHONHASHSEED``-independent (``blake2b``, not ``hash()``). Values changed
    at CANON v3 (the core form now carries the action rows and no token field),
    which is fine: ``move_shape`` is a report/context-tier column, never a key
    that survives a CANON bump.

    The u32 ``family_id = move_shape ^ depth_hash`` that used to live here was
    **deleted at CANON v3** (fingerprint memo ruling 2): measured fully redundant
    (a pure function of ``move_shape``, 821 = 821); its fallback-regressor role
    is re-keyed to ``action_id``. The curated FAMILY_REGISTRY string
    ``family_id`` (``families.py``) is unrelated and untouched.
    """
    core = _grey_core_event(pe)
    blob = canonical_blob(canonical_form(core))
    return int.from_bytes(hashlib.blake2b(blob, digest_size=4).digest(), "big")


def depth_hash(ds: DepthSig) -> int:
    """u32 packed depth signature (contract 7.4): ``kind<<16 | param``."""
    return ((int(ds.kind) & 0xFFFF) << 16) | (int(ds.param) & 0xFFFF)
