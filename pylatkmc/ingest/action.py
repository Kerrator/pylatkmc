"""The action axis: a reverse-symmetric, species-labelled site permutation.

Phase 1 of the approved action x context fingerprint design
(``onlattice_design/ACTION_FINGERPRINT_DESIGN_2026-07-29.md`` §7, under the
2026-07-30 interview rulings §11). Today's ``class_id`` fuses *what the atoms did*
with *what surrounded them* into one digest; this module makes the first half an
explicit, separately-addressable field.

An event's **action** is its arrow set ``A = {(x_a -> y_a, s_a)}`` -- atom ``a`` of
species ``s_a`` started on site ``x_a`` and ended on ``y_a``. Its identity is::

    action_canon = min over {A, A^-1} x candidate anchors x D4H of serialize(A)

-- the same argmin / TLV / ``blake2b`` machinery as :mod:`pylatkmc.ingest.canonical`,
over a much smaller tuple. Because the minimisation ranges over ``A`` **and** its
inverse, **a move and its reverse are the same action by construction** (memo §3.1
/ D2): that is the invariant no existing field has (only 8.9% of linked pairs share
a ``move_shape``, memo §2.4).

Two levels:

* ``action_id`` -- u64 digest of the canon with species **on** the arrows. Cr and Ni
  1NN hop barriers differ by 0.15 eV ~ 3.5 kT, so species belong to the action
  (ruling 1).
* ``archetype`` -- the same canon computed GREY (species dropped): the species-blind
  arrow topology (memo §4 taxonomy v1: ``V1NN`` / ``C2`` / ``C3+`` / ``X2`` / ``NC``).
  On a GREY catalogue the two coincide, correctly: there is no species level to have.

Deliberately **not** in the action (memo §3.2): context and ``depth_sig`` (the other
axis), saddle tokens (mechanism labels, 38% ``OTHER`` -- hashing them would fragment
the taxonomy on classifier flicker), and energetics (a slightly-uphill hop and its
downhill reverse are one action; the asymmetry lives in the rate).

Group parameter (ruling 4): the identity group is :data:`IDENTITY_GROUP` (``D4h``,
the (100)-slab point group). ``action_id``\\ s are comparable only within a group --
already true of ``class_id``. The build records it in the conditions stamp next to
``rcut``/``d_max``.

Determinism (contract 0.1, hard gate)
-------------------------------------
No ``hash()``, no ``set``/``dict`` iteration order, no floating point: every
reduction sorts integer tuples and the only digest is ``blake2b`` over integer TLV
bytes, so the digests are ``PYTHONHASHSEED``-independent.

Module-load DAG (contract 0.2)
------------------------------
``action -> canonical -> lattice, event_class``. Nothing here pulls
``pandas``/``pyarrow``/``ase``; the TLV encoder is reused from ``canonical`` rather
than duplicated (a second encoder is a silent-divergence trap).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pylatkmc.ingest.canonical import canonical_blob
from pylatkmc.ingest.event_class import Arrow, Occ
from pylatkmc.ingest.lattice import D4H, Offset, SymOp, apply_op

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #
ACTION_SCHEMA_VERSION: int = 1
"""Serialization version prefix of the action canon.

Bumping it changes every ``action_id``/``archetype``. It is **independent of**
``CANON_SCHEMA_VERSION`` (the ``class_id`` prefix) and stays so at CANON v3: the
class digest embeds the DIRECTED arrow rows under CANON's sole authority (no
``{A, A⁻¹}`` minimisation, no embedded action version -- see
``canonical.CANON_SCHEMA_VERSION``), while this version governs only the
standalone reverse-symmetric ``action_id``/``archetype`` digests. The two share
the 7-int arrow-row encoding of :func:`serialize_action_variant`
(lockstep-tested); changing that row encoding requires bumping BOTH versions.
"""

IDENTITY_GROUP: str = "D4h"
"""The identity group the action canon minimises over (ruling 4: a build parameter).

``D4h`` is the ideal (100)-slab point group (16 integer signed-permutation matrices,
:data:`pylatkmc.ingest.lattice.D4H`). A bulk corpus under a full ``Oh`` identity
would merge the in-plane and out-of-plane 1NN orbits; the enumeration *rule* is
fixed, the group is recorded.
"""

_GREY_SPECIES_CODE: int = int(Occ.OCC_ANY)
"""Species code used by the GREY (archetype) canon -- every occupied species collapses."""

_ONE_NN_SQ: int = 2
"""Squared integer length of a 1NN arrow on the h = a/2 even-parity grid."""

#: |d|^2 -> neighbour-shell name on the h = a/2 grid (exact integer arithmetic).
_SHELL_NAME: dict[int, str] = {2: "1NN", 4: "2NN", 6: "3NN", 8: "4NN"}

#: C2 net-displacement |d|^2 -> the angle between the two 1NN arrows (memo §4:
#: cos(theta) = (|d_net|^2 - 4) / 4, so 8/6/4/2 -> 0/60/90/120 deg -> net 4NN/3NN/2NN/1NN).
_C2_ANGLE_BY_NET_SQ: dict[int, str] = {8: "0deg", 6: "60deg", 4: "90deg", 2: "120deg"}

ActionForm = tuple[Any, ...]
"""The authoritative nested-integer action canon (ints + int rows only)."""


# --------------------------------------------------------------------------- #
# Arrow algebra                                                               #
# --------------------------------------------------------------------------- #
def invert_arrows(arrows: Sequence[Arrow]) -> tuple[Arrow, ...]:
    """The inverse action ``A^-1``: every arrow reversed, species carried along."""
    return tuple(Arrow(a.end, a.start, a.species) for a in arrows)


def transform_arrows(
    arrows: Sequence[Arrow], anchor: Offset, mat: tuple[tuple[int, int, int], ...]
) -> tuple[Arrow, ...]:
    """Re-express ``arrows`` relative to ``anchor`` and rotate by the matrix ``mat``."""
    a0, a1, a2 = anchor

    def t(off: Offset) -> Offset:
        return apply_op(mat, (off[0] - a0, off[1] - a1, off[2] - a2))  # type: ignore[arg-type]

    return tuple(Arrow(t(a.start), t(a.end), a.species) for a in arrows)


def candidate_anchors(arrows: Sequence[Arrow]) -> list[Offset]:
    """Every arrow endpoint is a candidate anchor (tails **and** heads), sorted.

    The set must be an *inversion-equivariant* function of the arrow set, or the
    ``min`` over ``{A, A^-1}`` would compare canons taken about different anchor
    families. Tails-union-heads is invariant under inversion by construction (it is
    the same set for ``A`` and ``A^-1``), which makes the reverse symmetry hold
    arrow-set-wise rather than only in aggregate. ``[(0, 0, 0)]`` for the empty
    (NO_OP) action so the ``min`` stays well defined.
    """
    if not arrows:
        return [(0, 0, 0)]
    seen = sorted({a.start for a in arrows} | {a.end for a in arrows})
    return seen


def _species_code(sp: Occ, *, grey: bool) -> int:
    """Species integer for the canon: real ``Occ`` in colour, ``OCC_ANY`` in grey."""
    return _GREY_SPECIES_CODE if grey else int(sp)


# --------------------------------------------------------------------------- #
# Canon                                                                       #
# --------------------------------------------------------------------------- #
def serialize_action_variant(
    arrows: Sequence[Arrow], anchor: Offset, g: SymOp, *, grey: bool = False
) -> tuple[tuple[int, ...], ...]:
    """The comparable integer tuple for one ``(arrows, anchor, g)`` variant.

    With ``T(x) = apply_op(g, x - anchor)`` each arrow becomes the 7-int row
    ``(T(start), T(end), species_code)``; the rows are **sorted**, so atom order in
    the input never reaches the key.
    """
    a0, a1, a2 = anchor

    def t(off: Offset) -> Offset:
        return apply_op(g, (off[0] - a0, off[1] - a1, off[2] - a2))

    rows: list[tuple[int, ...]] = []
    for a in arrows:
        s = t(a.start)
        e = t(a.end)
        rows.append((s[0], s[1], s[2], e[0], e[1], e[2], _species_code(a.species, grey=grey)))
    return tuple(sorted(rows))


def action_form(arrows: Sequence[Arrow], *, grey: bool = False) -> ActionForm:
    """The authoritative action canon: ``min`` over ``{A, A^-1} x anchors x D4H``.

    Returns ``(ACTION_SCHEMA_VERSION, n_arrows, best_rows)`` -- tolerance-free nested
    integers, totally ordered by ordinary tuple comparison. ``action_id`` /
    ``archetype`` are digests over this.
    """
    best: tuple[tuple[int, ...], ...] | None = None
    for candidate in (tuple(arrows), invert_arrows(arrows)):
        for anchor in candidate_anchors(candidate):
            for g in D4H:
                v = serialize_action_variant(candidate, anchor, g, grey=grey)
                if best is None or v < best:
                    best = v
    assert best is not None
    return (ACTION_SCHEMA_VERSION, len(arrows), best)


def action_blob(form: ActionForm) -> bytes:
    """TLV bytes of an action canon (the hashed form; shares ``canonical``'s encoder)."""
    return canonical_blob(form)


def _digest_u64(blob: bytes) -> int:
    """u64 ``blake2b`` digest (seed-independent; never ``hash()``)."""
    return int.from_bytes(hashlib.blake2b(blob, digest_size=8).digest(), "big")


def action_id(arrows: Sequence[Arrow], *, grey: bool = False) -> int:
    """u64 digest of the reverse-symmetric, species-labelled action canon."""
    return _digest_u64(action_blob(action_form(arrows, grey=grey)))


def archetype_id(arrows: Sequence[Arrow]) -> int:
    """u64 digest of the GREY (species-blind) action canon -- the archetype level."""
    return action_id(arrows, grey=True)


# --------------------------------------------------------------------------- #
# Taxonomy v1 display names (memo §4)                                         #
# --------------------------------------------------------------------------- #
def _sq(a: Offset, b: Offset) -> int:
    """Squared integer lattice distance between two offsets."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _chain_or_ring(arrows: Sequence[Arrow]) -> str | None:
    """``"ring"`` / ``"chain"`` / ``None`` for the arrow graph's shape.

    A *ring* is a single cycle (every head is some arrow's tail); a *chain* is a
    single head-to-tail path (exactly one tail is nobody's head). Anything else --
    a fork, a disconnected pair, a repeated site -- returns ``None`` and lands in
    the ``UNCLASSIFIED`` residual bin, which is the point of having one.
    """
    starts = [a.start for a in arrows]
    ends = [a.end for a in arrows]
    if len(set(starts)) != len(starts) or len(set(ends)) != len(ends):
        return None
    heads_not_tails = [e for e in ends if e not in set(starts)]
    tails_not_heads = [s for s in starts if s not in set(ends)]
    if not heads_not_tails and not tails_not_heads:
        # every head is a tail: one cycle iff the successor walk closes in n steps
        nxt = {a.start: a.end for a in arrows}
        cur = starts[0]
        for _ in range(len(arrows)):
            cur = nxt[cur]
        return "ring" if cur == starts[0] else None
    if len(heads_not_tails) == 1 and len(tails_not_heads) == 1:
        nxt = {a.start: a.end for a in arrows}
        cur = tails_not_heads[0]
        steps = 0
        while cur in nxt and steps <= len(arrows):
            cur = nxt[cur]
            steps += 1
        return "chain" if steps == len(arrows) else None
    return None


def archetype_name(arrows: Sequence[Arrow], delta_atoms: int = 0) -> str:
    """Human taxonomy-v1 name for an arrow topology (memo §4) -- display only.

    The *stored* column is the grey digest ``archetype``; this is its label for the
    census panel and review lists. Names: ``NO_OP`` (no arrows), ``NC``
    (non-conserving, ``delta_atoms != 0``), ``V1NN_inplane`` / ``V1NN_outofplane``
    (one 1NN arrow, split by the D4h orbit), ``HOP_{2NN,3NN,4NN,far}`` (a single
    longer jump -- outside taxonomy v1, part of the residual), ``C{k}`` chains
    (``C2`` sub-labelled by the 0/60/90/120 deg angle its net displacement implies),
    ``X{k}`` rings (``X2`` = direct exchange), and ``UNCLASSIFIED`` for anything the
    taxonomy does not explain.
    """
    if delta_atoms != 0:
        return "NC"
    if not arrows:
        return "NO_OP"
    if len(arrows) == 1:
        d2 = _sq(arrows[0].start, arrows[0].end)
        if d2 == _ONE_NN_SQ:
            dz = arrows[0].end[2] - arrows[0].start[2]
            return "V1NN_inplane" if dz == 0 else "V1NN_outofplane"
        return f"HOP_{_SHELL_NAME.get(d2, 'far')}"
    shape = _chain_or_ring(arrows)
    if shape is None:
        return "UNCLASSIFIED"
    if shape == "ring":
        return f"X{len(arrows)}"
    if any(_sq(a.start, a.end) != _ONE_NN_SQ for a in arrows):
        return "UNCLASSIFIED"
    if len(arrows) == 2:
        net = (
            sum(a.end[0] - a.start[0] for a in arrows),
            sum(a.end[1] - a.start[1] for a in arrows),
            sum(a.end[2] - a.start[2] for a in arrows),
        )
        angle = _C2_ANGLE_BY_NET_SQ.get(_sq((0, 0, 0), net))
        return f"C2_{angle}" if angle else "UNCLASSIFIED"
    return f"C{len(arrows)}"


#: Archetype names that taxonomy v1 does NOT explain -- the memo §4 residual bucket
#: (routed to the standing review list, ruling 6). ``NC`` is bucket (iii), deferred.
_RESIDUAL_NAMES: frozenset[str] = frozenset({"UNCLASSIFIED", "NC"})


# --------------------------------------------------------------------------- #
# Census panel (memo §2.2 / §7 "census tooling")                              #
# --------------------------------------------------------------------------- #
@dataclass
class ActionCensus:
    """Per-archetype / per-action composition of a catalogue (memo §2.2 table).

    Report channel only: computing it never touches identity, gates or rates.

    Two NO_OP counts, deliberately: ``n_no_op`` is **topological** (empty arrow set --
    available straight out of ``build``, before any QC pass runs) and
    ``n_no_op_quarantined`` is the **reason-aware carve-out** ruling 5 asks for (the
    subset already quarantined *and* labelled :data:`NO_OP_REASON`). They coincide on
    a QC'd catalogue; on a raw build the second is 0 because nothing is quarantined
    yet. NO_OP classes are quarantined but physical, so neither count is a quality
    defect.

    ``n_unstamped`` counts classes with **no** ``action_id`` -- a schema<=3 catalogue
    read through the v4 reader. Those are excluded from *every* other tally: their
    ``arrows`` default to ``()``, which is topologically indistinguishable from a
    genuine NO_OP, so counting them by name would report a whole pre-v4 corpus as
    NO_OP. ``n_classes`` is the row count; ``n_classes - n_unstamped`` is the
    population the named tallies (and ``n_residual``'s percentage) are over.
    """

    n_classes: int = 0
    n_actions: int = 0
    n_archetypes: int = 0
    n_one_way: int = 0
    n_no_op: int = 0
    n_no_op_events: int = 0
    n_no_op_quarantined: int = 0
    n_residual: int = 0
    n_pair_mismatch: int = 0
    n_unstamped: int = 0
    by_archetype_name: dict[str, int] = field(default_factory=dict)
    actions_by_archetype_name: dict[str, int] = field(default_factory=dict)
    one_way_by_archetype_name: dict[str, int] = field(default_factory=dict)
    top_actions: list[tuple[str, int, int]] = field(default_factory=list)

    def summary(self) -> str:
        """A compact, deterministic, multi-line panel (sorted, never dict order)."""
        lines = [
            f"action census (memo 2026-07-30 §2.2/§4; identity group {IDENTITY_GROUP}, "
            f"action schema v{ACTION_SCHEMA_VERSION}):",
            f"  classes {self.n_classes} "
            f"({self.n_classes - self.n_unstamped} with an action_id, "
            f"{self.n_unstamped} unstamped) | distinct action_id {self.n_actions} "
            f"| distinct archetype {self.n_archetypes}",
        ]
        order = sorted(self.by_archetype_name.items(), key=lambda kv: (-kv[1], kv[0]))
        for name, n in order:
            na = self.actions_by_archetype_name.get(name, 0)
            lines.append(
                f"    {name:<18s}: {n:5d} classes  "
                f"({na:3d} action{'' if na == 1 else 's'})  "
                f"one_way {self.one_way_by_archetype_name.get(name, 0):5d}"
            )
        for aid, n, _rank in self.top_actions:
            lines.append(f"    action {aid}: {n} classes")
        n_stamped = self.n_classes - self.n_unstamped
        frac = (100.0 * self.n_residual / n_stamped) if n_stamped else 0.0
        lines.extend(
            (
                f"  one-way annex     : {self.n_one_way:5d} classes "
                f"(alive in exactly one direction, Ea < 1.4 eV; memo §5.2 — not an exclusion)",
                f"  NO_OP             : {self.n_no_op:5d} classes / {self.n_no_op_events} events "
                f"({self.n_no_op_quarantined} already quarantined+labelled) "
                "— PHYSICAL (memo §5.3), excluded from catalogue-quality counts",
                f"  UNCLASSIFIED/NC   : {self.n_residual:5d} classes ({frac:.2f}%) "
                "— taxonomy-v1 residual, COUNTED here only; ruling-6 routing to the "
                "standing review list happens at corpus curation, not in this pass",
                f"  action_pair_mismatch: {self.n_pair_mismatch:3d} classes "
                "(linked pair disagrees on action_id; flag only — ruling 9)",
            )
        )
        lines.append(
            f"  no action_id      : {self.n_unstamped:5d} classes "
            "(schema<=3 rows read without the v4 columns — excluded from every "
            "tally above, NOT counted as NO_OP; rebuild to populate the action axis)"
        )
        return "\n".join(lines)


def action_census(classes: Sequence[Any], *, top_n: int = 8) -> ActionCensus:
    """Build the action panel over an ``EventClass`` sequence (memo §2.2 style).

    Deterministic: every tally is a sorted reduction over ``class_id``-sorted input;
    ties in ``top_actions`` break on the digest string.
    """
    ordered = sorted(classes, key=lambda c: c.class_id)
    by_name: Counter[str] = Counter()
    one_way_by_name: Counter[str] = Counter()
    actions_by_name: dict[str, set[int]] = {}
    per_action: Counter[int] = Counter()
    action_name: dict[int, str] = {}
    archetypes: set[int] = set()
    census = ActionCensus(n_classes=len(ordered))

    for c in ordered:
        # UNSTAMPED FIRST. A schema<=3 class reads back with `arrows == ()` (the
        # field default), and an empty arrow set is indistinguishable from a genuine
        # NO_OP by topology alone — tallying before this guard reported an entire
        # pre-v4 corpus as NO_OP. "No action recorded" is its own bin, not a name.
        aid = getattr(c, "action_id", None)
        if aid is None:
            census.n_unstamped += 1
            continue
        name = archetype_name(c.arrows, c.delta_atoms)
        by_name[name] += 1
        if getattr(c, "one_way", False):
            one_way_by_name[name] += 1
            census.n_one_way += 1
        if name in _RESIDUAL_NAMES:
            census.n_residual += 1
        if getattr(c, "action_pair_mismatch", False):
            census.n_pair_mismatch += 1
        if name == "NO_OP":
            census.n_no_op += 1
            census.n_no_op_events += len(c.source_rows)
            if c.audit_status == "quarantined" and "NO_OP" in (c.audit_reason or ""):
                census.n_no_op_quarantined += 1
        per_action[int(aid)] += 1
        action_name.setdefault(int(aid), name)
        actions_by_name.setdefault(name, set()).add(int(aid))
        arch = getattr(c, "archetype", None)
        if arch is not None:
            archetypes.add(int(arch))

    census.n_actions = len(per_action)
    census.n_archetypes = len(archetypes)
    census.by_archetype_name = dict(by_name)
    census.one_way_by_archetype_name = dict(one_way_by_name)
    census.actions_by_archetype_name = {k: len(v) for k, v in actions_by_name.items()}
    ranked = sorted(per_action.items(), key=lambda kv: (-kv[1], f"{kv[0]:016x}"))[:top_n]
    census.top_actions = [
        (f"{aid:016x} {action_name.get(aid, '?')}", n, i) for i, (aid, n) in enumerate(ranked)
    ]
    return census
