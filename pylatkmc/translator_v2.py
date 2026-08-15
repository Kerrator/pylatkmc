"""Translator v2 — EventClass catalogue → oriented lattice patterns (Phase B).

Consumes the Phase A ``EventClass`` Parquet catalogue (``pylatkmc.ingest``,
FINAL_DESIGN §5.1 / COMPARISON §4 "Phase B") and produces the data-driven
pattern IR that ``pattern_codegen`` emits as packed static tables + a generic
matcher into ``generated/proclist.c``. This replaces the family-CSV path for
v2 models; the two paths are selected explicitly per spec via
``rate_data.event_class_table`` (v2) vs ``rate_data.family_table`` (v0.3).

Key properties (the Phase B contract):

- **Species-resolved movers.** Every delta row carries the species harvested
  from the EventClass delta — there is no mover-species default anywhere on
  this path. Species are mapped by NAME (``"Ni"``/``"Cr"``/``"Fe"``), never by
  integer code: the ingest ``Occ`` enum (NI=1, CR=2, FE=3) and the runtime
  ``Species`` enum (SP_NI=1, SP_FE=2, SP_CR=3) DISAGREE on Cr/Fe integers.
- **D4h orientation expansion at translate time.** Each class emits
  ``|D4h| / |Stab(decorated event)|`` oriented patterns; the orbit transversal
  is computed by deduplicating the 16 images of (delta ∪ context ∪ ordered
  saddle-token binding) exactly as ``canonical.orientation_count`` counts them,
  reusing ``pylatkmc.ingest.lattice.D4H_OPS`` — the group is never re-derived.
- **Rate baking.** ``prefactor_Hz = nu0_geo_psinv * 1e12`` (the ps⁻¹→Hz
  conversion happens HERE, exactly once) and ``Ea_eV = Ea_rep_eV``, so the
  runtime's ``prefactor * exp(-Ea/kBT)`` reproduces the class's rate-space
  mean ``k_rate_mean`` exactly at the catalogue's ``t_ref_K``.
- **Determinism.** Classes are processed in ``class_id`` order, group ops in
  fixed ``D4H_OPS`` index order, every reduction iterates sorted sequences.
  No ``hash()`` / set-iteration anywhere.

Translation policy (counted, never silent — see ``TranslationReport``):

- Classes with an **empty delta** (occupancy-identical endpoints after
  snapping) are untranslatable no-ops → skipped.
- Classes with ``delta_atoms != 0`` (non-conserving: an atom appears or
  vanishes) are skipped by default: on-lattice these would fire as
  spontaneous atom creation/deletion, which is unphysical for the diffusion
  catalogue (dissolution is the separate analytical family). Pass
  ``include_nonconserving=True`` to translate them anyway.
- Context predicates of kind ``OUTSIDE``/``WILDCARD`` (unknown at harvest)
  constrain nothing and are dropped from the matched context.

``pylatkmc.ingest`` is imported lazily inside functions: the core package
stays importable without the ``[ingest]`` extras, and only a spec that opts
into the v2 path requires them.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pylatkmc.ingest.event_class import EventClass

#: Integer lattice offset. Ingest-side: crystal-frame a/2 units. Pattern-side
#: (everything after ``to_runtime_frame``): runtime tetragonal cells
#: ``(nn_d/2, nn_d/2, nn_d/√2)`` — see :func:`to_runtime_frame`.
Offset = tuple[int, int, int]

#: ps^-1 → Hz. Single conversion point on the v2 path (the pyKMC k0-units
#: incident is the cautionary tale: convert exactly once, at translation).
HZ_PER_PSINV: float = 1.0e12

#: Species name used for an empty site (matches ModelSpec.species[0]).
VACANT: str = "Vacant"


# ---------------------------------------------------------------------------
# Pattern IR
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeltaRow:
    """One occupancy change: ``before`` → ``after`` at ``off`` (species names)."""

    off: Offset
    before: str
    after: str


@dataclass(frozen=True)
class CtxRow:
    """One matched context predicate at ``off``.

    ``kind`` is ``"SPECIES"`` (exact species named in ``species``),
    ``"EMPTY"`` (vacant-or-absent site), or ``"OCC_ANY"`` (any occupied).
    """

    off: Offset
    kind: str
    species: str | None = None


@dataclass(frozen=True)
class MemberRate:
    """One rate channel of a pattern: a single (prefactor, barrier) pair.

    In Phase C mode (``nu0_pair_policy == "harvested_pair"``) there is one
    ``MemberRate`` per harvested class member (raw pair: ``prefactor_Hz =
    nu0_f_list_hz[i]``, already Hz; ``Ea_eV = barriers_eV[i]``); the aggregate
    (schema-1) path emits a single member (``nu0_geo × 1e12`` / ``Ea_rep``).
    ``v6_ea_surrogate`` is the per-class V6 surrogate barrier
    (``surrogate.surrogate_barrier``); ``nan`` when no model is baked. It is a
    provenance/diagnostic quantity (identical for every member of a class),
    never the executed rate.
    """

    prefactor_Hz: float
    Ea_eV: float
    v6_ea_surrogate: float


@dataclass(frozen=True)
class LatticePattern:
    """One translated EventClass: canonical-frame rows + orientation transversal.

    Offsets are re-anchored so ``(0, 0, 0)`` is the enumeration anchor (the
    rarest delta predicate, FINAL_DESIGN §5.2); ``anchor_species`` is the
    species required at the anchor site (the O(1) screen). Orientation ``g``
    of this pattern places row ``r`` at ``D4H_OPS[g] @ r.off`` relative to the
    matched anchor site.

    ``members`` carries the pattern's rate channels (§8-N6): each ``(member,
    op)`` pair is one oriented process, so a class with ``n`` members expands
    to ``n × len(orientation_ops)`` procs sharing this pattern's geometry.
    ``prefactor_Hz`` / ``Ea_eV`` mirror ``members[0]`` for backward compat.
    """

    class_id: str
    name: str
    anchor_species: str
    delta: tuple[DeltaRow, ...]  # runtime-frame cells (to_runtime_frame)
    context: tuple[CtxRow, ...]  # runtime-frame cells
    orientation_ops: tuple[int, ...]
    prefactor_Hz: float
    Ea_eV: float
    mover_species: tuple[str, ...]
    n_members: int
    depth_kind: int
    depth_param: int
    members: tuple[MemberRate, ...] = ()


@dataclass
class TranslationReport:
    """Per-run accounting: what translated, what was skipped and why."""

    n_classes_in: int = 0
    n_translated: int = 0
    n_oriented_patterns: int = 0
    skipped_quarantined: int = 0
    skipped_pending_research: int = 0
    skipped_unstamped: int = 0
    skipped_empty_delta: int = 0
    skipped_nonconserving: int = 0
    skipped_token_mismatch: int = 0
    skipped_unsupported_pred: int = 0
    skipped_offset_overflow: int = 0
    n_negative_ea: int = 0
    phase_c: bool = False
    n_members_total: int = 0
    mover_pattern_counts: dict[str, int] = field(default_factory=dict)
    mover_proc_counts: dict[str, int] = field(default_factory=dict)
    orientation_histogram: dict[int, int] = field(default_factory=dict)
    orientation_mismatches: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        """Human-readable summary (stable ordering)."""
        out = [
            f"classes in catalogue:      {self.n_classes_in}",
            f"rate mode:                 {'phase-C raw-pairs' if self.phase_c else 'aggregate'}",
            f"classes translated:        {self.n_translated}",
            f"oriented patterns (procs): {self.n_oriented_patterns}",
            f"member rate channels:      {self.n_members_total}",
            f"skipped quarantined:       {self.skipped_quarantined}",
            f"skipped pending-research:  {self.skipped_pending_research}",
            f"skipped unstamped:         {self.skipped_unstamped}",
            f"skipped empty-delta:       {self.skipped_empty_delta}",
            f"skipped non-conserving:    {self.skipped_nonconserving}",
            f"skipped token-mismatch:    {self.skipped_token_mismatch}",
            f"skipped unsupported-pred:  {self.skipped_unsupported_pred}",
            f"skipped offset-overflow:   {self.skipped_offset_overflow}",
            f"classes with Ea_rep < 0:   {self.n_negative_ea}",
        ]
        for sp in sorted(self.mover_pattern_counts):
            out.append(
                f"mover {sp}: {self.mover_pattern_counts[sp]} patterns, "
                f"{self.mover_proc_counts.get(sp, 0)} oriented procs"
            )
        for n in sorted(self.orientation_histogram):
            out.append(f"orientation_count={n}: {self.orientation_histogram[n]} classes")
        if self.orientation_mismatches:
            out.append(
                f"orientation-count mismatches vs Phase A: {len(self.orientation_mismatches)}"
            )
        return out


# ---------------------------------------------------------------------------
# D4h access (lazy; the group lives in pylatkmc.ingest.lattice)
# ---------------------------------------------------------------------------


def d4h_matrices() -> tuple[tuple[tuple[int, int, int], ...], ...]:
    """The 16 D4h integer matrices in canonical index order (ingest source)."""
    from pylatkmc.ingest.lattice import D4H_OPS

    return D4H_OPS


def _apply(mat: Sequence[Sequence[int]], v: Offset) -> Offset:
    """Apply one integer 3x3 matrix to an offset."""
    return (
        mat[0][0] * v[0] + mat[0][1] * v[1] + mat[0][2] * v[2],
        mat[1][0] * v[0] + mat[1][1] * v[1] + mat[1][2] * v[2],
        mat[2][0] * v[0] + mat[2][1] * v[1] + mat[2][2] * v[2],
    )


# ---------------------------------------------------------------------------
# Catalogue loading
# ---------------------------------------------------------------------------


def load_event_class_catalogue(path: str | Path) -> list[EventClass]:
    """Read the Phase A EventClass Parquet catalogue (requires ``[ingest]``)."""
    try:
        from pylatkmc.ingest.event_class import read_catalogue_parquet

        # The call must stay inside the try: event_class imports pyarrow
        # lazily (module import succeeds without it), so a missing pyarrow
        # only surfaces here, at read time.
        return read_catalogue_parquet(path)
    except ImportError as e:
        raise ImportError(
            "the v2 translator reads the EventClass Parquet catalogue, which "
            "requires the [ingest] extras (pip install -e '.[ingest]')"
        ) from e


# ---------------------------------------------------------------------------
# Per-class translation helpers
# ---------------------------------------------------------------------------


def _occ_name(occ: Any) -> str:
    """Map an ingest ``Occ`` code to a species NAME (never an integer code)."""
    from pylatkmc.ingest.event_class import Occ, occ_to_symbol

    o = Occ(int(occ))
    if o == Occ.EMPTY:
        return VACANT
    return occ_to_symbol(o)


def to_runtime_frame(off: Offset) -> Offset:
    """Crystal-frame a/2 offset → runtime tetragonal cell (u, v, w).

    The ingest identity layer works in the crystal cube-axis frame (integer
    a/2 offsets, even parity). The runtime slab frame has its in-plane axes
    along the crystal [110] directions (see ``coord_codes.h``: in-plane 1NN
    at ``(±nn_d, 0, 0)``) with tetragonal cells ``(nn_d/2, nn_d/2, nn_d/√2)``.
    The bridge is the integer map ``(u, v, w) = (i+j, j−i, k)``: a proper
    rotation by 45° about z plus the in-plane rescale, taking even-parity
    crystal sites bijectively onto the runtime's same-parity sublattice
    (``u ≡ v ≡ w mod 2``). The in-plane orientation choice this map makes is
    absorbed by the D4h orbit expansion (the alternative choices differ by a
    D4h element), but the D4h transversal must be computed AFTER this map —
    coset representatives chosen in one frame are not valid in the other
    when the stabiliser is non-normal.
    """
    i, j, k = off
    return (i + j, j - i, k)


def _delta_rows(cls: EventClass) -> tuple[DeltaRow, ...]:
    """EventClass delta → species-named runtime-frame rows, sorted by offset."""
    rows = [
        DeltaRow(
            off=to_runtime_frame(tuple(ds.off)),
            before=_occ_name(ds.before),
            after=_occ_name(ds.after),
        )
        for ds in cls.delta
    ]
    return tuple(sorted(rows, key=lambda r: r.off))


def _ctx_rows(cls: EventClass) -> tuple[CtxRow, ...] | None:
    """EventClass context → matched predicate rows (sorted); None = unsupported.

    ``OUTSIDE``/``WILDCARD`` rows constrain nothing and are dropped. A
    ``SPECIES`` predicate with more than one allowed species is not
    representable as an exact-match row → the class is skipped (counted).
    Context rows at delta offsets are also dropped: the delta rows already
    pin those sites exactly (before-state), and emitting both would be
    redundant work in the inner matcher loop.
    """
    delta_offs = {to_runtime_frame(tuple(ds.off)) for ds in cls.delta}
    rows: list[CtxRow] = []
    for cs in cls.context:
        off = to_runtime_frame(tuple(cs.off))
        kind = cs.pred.kind
        if kind in ("OUTSIDE", "WILDCARD"):
            continue
        if off in delta_offs:
            continue
        if kind == "EMPTY":
            rows.append(CtxRow(off=off, kind="EMPTY"))
        elif kind == "OCC_ANY":
            rows.append(CtxRow(off=off, kind="OCC_ANY"))
        elif kind == "SPECIES":
            if len(cs.pred.species) != 1:
                return None
            (occ,) = tuple(cs.pred.species)
            rows.append(CtxRow(off=off, kind="SPECIES", species=_occ_name(occ)))
        else:  # pragma: no cover - contract lists exactly five kinds
            return None
    return tuple(sorted(rows, key=lambda r: (r.off, r.kind, r.species or "")))


def _movers_in_token_order(cls: EventClass) -> list[Offset]:
    """Runtime-frame mover offsets, index-aligned with ``cls.saddle_token``.

    Phase A stores ``saddle_token`` sorted by ``start_rank`` — the lex rank
    of the mover's CRYSTAL-frame canonical offset (``canonical_rank_map``:
    key = ``apply_op(g*, m − a*)``, exactly the offsets ``cls.delta`` is
    stored in). So token ``i`` belongs to the ``i``-th mover in crystal-frame
    lex order. Sort in the crystal frame FIRST, then map each offset to the
    runtime frame: ``to_runtime_frame`` does not preserve lex order, so
    sorting the runtime offsets instead would mis-bind tokens whenever a
    multi-mover class's order flips under the frame map.
    """
    mover_offs_crystal = sorted(tuple(ds.off) for ds in cls.delta if _occ_name(ds.before) != VACANT)
    return [to_runtime_frame(off) for off in mover_offs_crystal]


def _pick_anchor(delta: Sequence[DeltaRow]) -> tuple[Offset, str]:
    """The enumeration anchor: rarest delta predicate (FINAL_DESIGN §5.2).

    A ``before == Vacant`` site (the vacancy) wins when present — vacancies
    are the rarest occupancy in a dilute-defect crystal. Otherwise the rarest
    before-species within the delta (ties: fewest rows, then species name),
    at its lexicographically smallest offset. Deterministic by construction.
    """
    vac = sorted(r.off for r in delta if r.before == VACANT)
    if vac:
        return vac[0], VACANT
    counts: dict[str, int] = {}
    for r in delta:
        counts[r.before] = counts.get(r.before, 0) + 1
    rarest = min(sorted(counts), key=lambda sp: (counts[sp], sp))
    off = sorted(r.off for r in delta if r.before == rarest)[0]
    return off, rarest


def _orientation_transversal(
    delta: Sequence[DeltaRow],
    context: Sequence[CtxRow],
    tokens: Sequence[tuple[int, tuple[int, ...]]],
    movers: Sequence[Offset],
) -> tuple[int, ...]:
    """Dedup the 16 D4h images of (delta, context, ordered token binding).

    Mirrors ``canonical.orientation_count``: two ops are equivalent iff they
    produce the same transformed-and-sorted delta rows, context rows, and the
    same saddle-token sequence when tokens follow their movers into the new
    frame. ``movers`` must be index-aligned with ``tokens`` — i.e. in
    crystal-frame canonical rank order (``_movers_in_token_order``), NOT
    runtime-lex order. Returns the op indices (fixed D4H order) of the first
    op in each equivalence class — the orbit transversal.
    """
    mats = d4h_matrices()
    seen: dict[tuple[Any, ...], int] = {}
    transversal: list[int] = []
    for gi, mat in enumerate(mats):
        d_img = tuple(sorted((_apply(mat, r.off), r.before, r.after) for r in delta))
        c_img = tuple(sorted((_apply(mat, r.off), r.kind, r.species or "") for r in context))
        ranked = sorted(range(len(movers)), key=lambda i: _apply(mat, movers[i]))
        t_img = tuple(tokens[i] for i in ranked)
        key = (d_img, c_img, t_img)
        if key not in seen:
            seen[key] = gi
            transversal.append(gi)
    return tuple(transversal)


def _reanchor(rows: Iterable[Any], anchor: Offset) -> list[Any]:
    """Shift every row's offset by -anchor (dataclass ``replace``-free copy)."""
    out = []
    for r in rows:
        off = (r.off[0] - anchor[0], r.off[1] - anchor[1], r.off[2] - anchor[2])
        if isinstance(r, DeltaRow):
            out.append(DeltaRow(off=off, before=r.before, after=r.after))
        else:
            out.append(CtxRow(off=off, kind=r.kind, species=r.species))
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


#: Phase C trigger: a stamped catalogue names this ν0 policy on every class.
HARVESTED_PAIR_POLICY: str = "harvested_pair"

#: Re-search seed policy (identity-redesign memo 2026-07-22 §3.2): a class recovered
#: by the frame fix with NO previously-measured member. Such a class must NOT emit
#: measured procs — its sites fall through to the Phase C surrogate channel and the
#: flag registry ranks it for the in-situ re-search campaign. Stamped by
#: ``pylatkmc.ingest.qc.stamp_rate_policy`` (the ingest package cannot be imported
#: here at module load — the bare core stays importable without the [ingest]
#: extras — so the literal is mirrored; a unit test locks the two together).
PENDING_RESEARCH_POLICY: str = "pending_research"

#: N6 staged-migration switch (memo §8-N6). Ships OFF: measured classes fire their
#: raw harvested pairs. If ever turned ON — gated on V2's |ΔE_H − dE_pair| dropping
#: below the measured pair-noise scale — measured classes would instead fire the
#: DB-safe anchored form ``Ea = E_sym_measured + ½·ΔE_H`` with ``E_sym_measured =
#: (Ea_f + Ea_b)/2``. Not wired to any behaviour yet; the generated proclist stamps
#: its state as ``PYLATKMC_MEASURED_ANCHORED_FORM``.
MEASURED_ANCHORED_FORM: bool = False


def _member_rates(cls: EventClass, *, phase_c: bool, v6: float) -> tuple[MemberRate, ...]:
    """The rate channels of a class (§8-N6).

    Phase C raw-pair mode (``cls.nu0_pair_policy == "harvested_pair"``): one
    ``MemberRate`` per harvested member — ``prefactor_Hz = nu0_f_list_hz[i]``
    (already Hz, NOT ×1e12) and ``Ea_eV = barriers_eV[i]``. Aggregate mode:
    the single ``nu0_geo_psinv × 1e12`` / ``Ea_rep_eV`` channel (unchanged).
    ``v6`` (identical for every member) is the surrogate barrier for provenance.
    """
    use_pairs = phase_c and cls.nu0_pair_policy == HARVESTED_PAIR_POLICY
    if use_pairs and cls.barriers_eV:
        # nu0_f may be shorter/longer than barriers only on malformed data; the
        # catalogue guarantees len(nu0_f_list_hz) == len(barriers_eV) per class.
        n = len(cls.barriers_eV)
        nu0 = list(cls.nu0_f_list_hz)
        if len(nu0) < n:  # defensive: pad with the aggregate prefactor
            nu0 = nu0 + [float(cls.nu0_geo_psinv) * HZ_PER_PSINV] * (n - len(nu0))
        return tuple(
            MemberRate(
                prefactor_Hz=float(nu0[i]), Ea_eV=float(cls.barriers_eV[i]), v6_ea_surrogate=v6
            )
            for i in range(n)
        )
    return (
        MemberRate(
            prefactor_Hz=float(cls.nu0_geo_psinv) * HZ_PER_PSINV,
            Ea_eV=float(cls.Ea_rep_eV),
            v6_ea_surrogate=v6,
        ),
    )


def translate_event_classes(
    classes: Sequence[EventClass],
    *,
    include_nonconserving: bool = False,
    include_unstamped: bool = False,
    max_offset: int = 127,
    phase_c: bool = False,
    esym_model: Any = None,
) -> tuple[list[LatticePattern], TranslationReport]:
    """Translate EventClass rows into LatticePatterns (+ accounting report).

    Deterministic: classes are processed in ``class_id`` order; every skip is
    counted in the report, never silent. ``max_offset`` guards the emitter's
    int8 offset packing (a component beyond it skips the class, counted).

    ``phase_c`` selects the §8-N6 raw-pair rate bake (one proc per harvested
    member); it is auto-detected in :func:`translate_catalogue` from the
    ``nu0_pair_policy`` stamp. ``esym_model`` (an ``EsymModel`` or ``None``)
    supplies the per-class V6 surrogate barrier baked into proclist provenance.
    Quarantined classes (``audit_status == "quarantined"``) are EXCLUDED and
    counted (``skipped_quarantined``) — never silently translated. Likewise
    pending-re-search classes (``nu0_pair_policy == "pending_research"``, memo
    2026-07-22 §3.2): recovered classes with no previously-measured member are
    EXCLUDED and counted (``skipped_pending_research``) until the re-search
    agreement gate graduates them — their sites fall through to the Phase C
    surrogate channel + flag registry at runtime.

    UNSTAMPED classes (``nu0_pair_policy`` neither ``"harvested_pair"`` nor
    ``"pending_research"`` — a merge run without ``--measured-catalogue``
    leaves ``None``) are likewise EXCLUDED and counted (``skipped_unstamped``)
    unless ``include_unstamped=True``: baking them would emit procs at
    unvalidated aggregate rates with no diagnostic (the 2026-08-14 ingest
    pilot's gate G6). The opt-in restores the legacy schema-1 aggregate path
    for deliberately unstamped catalogues.
    """
    report = TranslationReport(n_classes_in=len(classes), phase_c=phase_c)
    patterns: list[LatticePattern] = []
    names_seen: set[str] = set()

    surrogate_barrier = None
    if esym_model is not None:
        from pylatkmc.ingest.surrogate import surrogate_barrier as _sb

        surrogate_barrier = _sb

    for cls in sorted(classes, key=lambda k: k.class_id):
        if cls.audit_status == "quarantined":
            report.skipped_quarantined += 1
            continue
        if cls.nu0_pair_policy == PENDING_RESEARCH_POLICY:
            report.skipped_pending_research += 1
            continue
        if cls.nu0_pair_policy != HARVESTED_PAIR_POLICY and not include_unstamped:
            report.skipped_unstamped += 1
            continue
        delta = _delta_rows(cls)
        if not delta:
            report.skipped_empty_delta += 1
            continue
        if cls.delta_atoms != 0 and not include_nonconserving:
            report.skipped_nonconserving += 1
            continue
        context = _ctx_rows(cls)
        if context is None:
            report.skipped_unsupported_pred += 1
            continue

        movers = _movers_in_token_order(cls)
        tokens = tuple((int(t.kind), tuple(int(c) for c in t.coord_sig)) for t in cls.saddle_token)
        if len(tokens) != len(movers):
            report.skipped_token_mismatch += 1
            continue

        orientation_ops = _orientation_transversal(delta, context, tokens, movers)
        if len(orientation_ops) != cls.orientation_count:
            report.orientation_mismatches.append(
                f"{cls.class_id[:12]}: transversal {len(orientation_ops)} "
                f"vs Phase A {cls.orientation_count}"
            )

        anchor, anchor_species = _pick_anchor(delta)
        r_delta = tuple(_reanchor(delta, anchor))
        r_ctx = tuple(_reanchor(context, anchor))
        all_offs = [r.off for r in r_delta] + [r.off for r in r_ctx]
        if any(abs(c) > max_offset for off in all_offs for c in off):
            report.skipped_offset_overflow += 1
            continue

        v6 = float("nan")
        if surrogate_barrier is not None:
            v6 = float(surrogate_barrier(esym_model, cls))
        members = _member_rates(cls, phase_c=phase_c, v6=v6)
        prefactor_hz = members[0].prefactor_Hz
        ea_ev = members[0].Ea_eV
        if any(m.Ea_eV < 0.0 for m in members):
            report.n_negative_ea += 1

        name = f"v2_{cls.class_id[:12]}"
        if name in names_seen:
            raise ValueError(f"pattern name collision on {name!r}; widen the class_id prefix")
        names_seen.add(name)

        mover_species = tuple(sorted(r.before for r in delta if r.before != VACANT))
        pat = LatticePattern(
            class_id=cls.class_id,
            name=name,
            anchor_species=anchor_species,
            delta=r_delta,
            context=r_ctx,
            orientation_ops=orientation_ops,
            prefactor_Hz=prefactor_hz,
            Ea_eV=ea_ev,
            mover_species=mover_species,
            n_members=len(cls.barriers_eV),
            depth_kind=int(cls.depth_sig.kind),
            depth_param=int(cls.depth_sig.param),
            members=members,
        )
        patterns.append(pat)

        report.n_translated += 1
        n_orient = len(orientation_ops)
        n_proc = n_orient * len(members)
        report.n_oriented_patterns += n_proc
        report.n_members_total += len(members)
        report.orientation_histogram[n_orient] = report.orientation_histogram.get(n_orient, 0) + 1
        for sp in sorted(set(mover_species)):
            report.mover_pattern_counts[sp] = report.mover_pattern_counts.get(sp, 0) + 1
            report.mover_proc_counts[sp] = report.mover_proc_counts.get(sp, 0) + n_proc

    return patterns, report


def catalogue_is_phase_c(classes: Sequence[EventClass]) -> bool:
    """True iff any class is stamped with the Phase C raw-pair ν0 policy.

    The stamp (``nu0_pair_policy == "harvested_pair"``) is written by the
    surrogate-fit / ingest-QC leg; an unstamped (schema-1) catalogue keeps the
    aggregate rate path — but only via the explicit ``include_unstamped=True``
    opt-in of :func:`translate_event_classes` (unstamped classes are skipped
    and counted by default).
    """
    return any(c.nu0_pair_policy == HARVESTED_PAIR_POLICY for c in classes)


def translate_catalogue(
    path: str | Path,
    *,
    include_nonconserving: bool = False,
    include_unstamped: bool = False,
    esym_model: Any = None,
) -> tuple[list[LatticePattern], TranslationReport]:
    """Load an EventClass Parquet catalogue and translate it (convenience).

    Phase C mode is auto-detected from the catalogue's ``nu0_pair_policy``
    stamp; ``esym_model`` (optional) supplies the V6 surrogate barrier baked
    into provenance.
    """
    classes = load_event_class_catalogue(path)
    return translate_event_classes(
        classes,
        include_nonconserving=include_nonconserving,
        include_unstamped=include_unstamped,
        phase_c=catalogue_is_phase_c(classes),
        esym_model=esym_model,
    )


__all__ = (
    "CtxRow",
    "DeltaRow",
    "HARVESTED_PAIR_POLICY",
    "HZ_PER_PSINV",
    "LatticePattern",
    "MemberRate",
    "TranslationReport",
    "VACANT",
    "catalogue_is_phase_c",
    "d4h_matrices",
    "load_event_class_catalogue",
    "to_runtime_frame",
    "translate_catalogue",
    "translate_event_classes",
)
