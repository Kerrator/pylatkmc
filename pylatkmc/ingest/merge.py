"""Cross-run class-level merge of per-run ``EventClass`` catalogues (ingest bridge).

The ingest pipeline builds and QCs **one reference table per pyKMC run** (``build`` +
``qc``). A sweep produces many such per-run catalogues that must be folded into a
single, class-level catalogue before the translator/codegen or the re-search campaign
consumes it. This module is that fold. It is the fifth (and only) cross-run
catalogue writer, and it keeps the same write discipline as the rest of the ingest
layer: pure functions, new ``EventClass`` instances, deterministic ``class_id`` order,
no ``hash()``/``set``/``dict`` iteration-order dependence.

Why per-run build+qc, never a raw-reference-table concat
--------------------------------------------------------
``idx_ref`` is **run-local and zero-based** in every pyKMC run, and backward-partner
linkage in ``build_class_catalogue`` resolves through a per-build ``by_idx_ref`` dict.
Concatenating raw reference tables silently cross-links the wrong forward/backward
partners into the G2/reciprocity gates (two runs both have ``idx_ref == 0``). The
correct unit is therefore **one build + one QC per run**, whose per-run ``by_idx_ref``
linkage is already baked into each class's member lists (``dE_pair_list_eV``,
``backward_class``). This module unions those *already-linked* per-run catalogues on
the content-based ``class_id`` — portable across runs by construction (same geometry →
same digest; verified on 58 shared classes, |ΔEa_rep| median 1 meV).

What the merge does, per shared ``class_id``
--------------------------------------------
* **Concatenate member lists** across runs: the aligned
  ``(Ea, ν0_f, ν0_b, residuals, dE)`` member rows and the run-local provenance
  (``source_rows`` / ``source_idx_refs``). All concatenations are re-sorted so the
  stored tuples are order-independent — and every per-member column rides **one**
  tuple through that sort, so a barrier can never end up paired with another
  member's ``dE``. The merged ``dE_pair_list_eV`` is therefore emitted in the
  **aligned** convention (one entry per member, ``NaN`` where unpaired); see
  :func:`_aligned_dE` for the two conventions and how a per-run subset form is
  re-aligned.
* **Run-qualify provenance** in ``source_sim_paths`` (empty in a per-run build): one
  ``"<run_tag>#<idx_ref>"`` entry per member, so a cross-run ``idx_ref`` collision
  stays disambiguated (two runs' ``idx_ref == 0`` become distinct provenance strings).
* **Recompute the rate representative** over the merged member list
  (:func:`aggregate_rate_space`), ``dEnergy_eV`` (mean of merged ``dE_pair``), and
  ``pair_status``. Identity fields and ``t_ref_K`` come from a deterministic
  **primary donor** — the contributing run whose ``run_tag`` sorts first. Per-run
  ``t_ref_K`` is carried, never re-baked to a common T: the raw member barriers/ν0 are
  the T-independent Arrhenius data the engine fires at runtime, and ``t_ref_K`` only
  enters kT-normalized display and the graduation band (≫ the ~1 meV cross-T spread).
* **Aggregate the gate log** to the per-gate worst outcome across runs (the natural
  generalization of ``build``'s worst-over-members aggregation) and recompute
  ``audit_status`` (approved iff every gate PASS/NA and ≥ 2 merged members).

Statuses are NOT unioned
------------------------
Quarantine is **run-composition-dependent**, not geometry-intrinsic: a class linked
into a broken reciprocity pair in one run can survive once a second run contributes a
clean member. The merge therefore resets every merged class to a non-quarantined
status and **re-runs the QC screens** (:func:`apply_qc`: reciprocity + delta-less +
dE-spread + the class_id-keyed human-veto overlay) on the *merged* member lists.
:attr:`MergeReport.status_conflict_count` records classes quarantined in some
contributing run that survive merged QC (the audit trail of that decision).

Measured stamping is class_id-keyed
-----------------------------------
The measured ν0 policy is carried forward by **class_id set**, not by run-local
``idx_ref`` (:func:`stamp_rate_policy` grew a ``measured_class_ids`` keyword for this).
The set is the ``nu0_pair_policy == "harvested_pair"`` class_ids of a
previously-stamped/graduated reference catalogue; membership is authoritative evidence
of representability, so a measured class is stamped ``harvested_pair`` even if a
sweep run's snap noise would fail its merged G3.

Element sets are guarded, not assumed
-------------------------------------
``class_id`` is content-keyed, so merging two *different alloys* raises no
collision and no error — it just concatenates them into an artifact no model spec
can name (B4, 2026-08-14 ingest-readiness review). :func:`element_census` measures
each input's element set from its class records (so legacy catalogues written
before this guard are measured, never assumed) and reports incomparable pairs;
the CLI refuses on a conflict unless the operator opts in explicitly.

``delta_atoms != 0`` stance (decision, 2026-07-24)
--------------------------------------------------
Non-conserving classes (``delta_atoms != 0``) are **counted and surfaced**
(:attr:`MergeReport.nonconserving_surviving`), not quarantined. Rationale: a
non-conserving delta is not a corpus-integrity *defect* — it is a physically real
event class whose on-lattice non-conservation is already (a) recorded in the merged
gate log as a ``G5`` FAIL, and (b) handled downstream by ``translator_v2``'s explicit,
counted non-conserving skip (off by default; it would otherwise fire as spontaneous
atom creation/deletion). Quarantining here would conflate a legitimate non-conserving
mechanism (e.g. an adatom/dissolution-adjacent event) with a mislink/projection
defect and discard its audit trail. The count keeps them visible; the gate log and the
translator keep them safe.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from pylatkmc.ingest.event_class import (
    _OUTCOME_SEVERITY,
    CATALOGUE_SCHEMA_VERSION,
    EventClass,
    GateOutcome,
    GateResult,
    aggregate_rate_space,
    catalogue_elements,
    one_way_flag,
)
from pylatkmc.ingest.qc import (
    DEFAULT_RECIPROCITY_TOL_EV,
    DEFAULT_SPREAD_TOL_EV,
    QCReport,
    StampReport,
    apply_qc,
    stamp_rate_policy,
)

DEFAULT_NU0_FALLBACK_HZ: float = 1.0e12
"""ν0 fallback (Hz) for merged members without a usable prefactor (matches ``build``)."""


def format_elements(elements: Sequence[str]) -> str:
    """Render an element set for a stamp / log line (``"Cr,Ni"``; GREY -> a marker)."""
    return ",".join(elements) if elements else "<species-blind>"


def parse_elements(text: str) -> tuple[str, ...]:
    """Parse a ``"Ni,Cr"`` CLI expectation into a sorted, validated symbol tuple.

    Raises ``ValueError`` on a symbol ``pylatkmc.ingest`` has no occupancy code for
    (a typo must never widen or silently narrow an element expectation).
    """
    from pylatkmc.ingest.event_class import SYMBOL_TO_OCC

    want = tuple(sorted({s.strip() for s in text.split(",") if s.strip()}))
    bad = [s for s in want if s not in SYMBOL_TO_OCC]
    if bad:
        raise ValueError(
            f"unknown element symbol(s) {bad}: ingest knows {sorted(SYMBOL_TO_OCC)} "
            "(extend SYMBOL_TO_OCC per campaign)"
        )
    return want


@dataclass(frozen=True)
class ElementCensus:
    """Which elements each merge input is written over, and whether they agree (B4).

    Element sets are **content-derived** (:func:`~pylatkmc.ingest.event_class.
    catalogue_elements`), so this works identically on catalogues written before the
    guard existed — a legacy input is never assumed compatible, it is measured.

    Comparison policy: a strict-**subset** relation is *not* a disagreement. A run of
    the same alloy that happened to catalogue no solute event contributes a narrower
    set, and refusing that would reject legitimate corpora (in a 10-run sample of the
    2026-08-14 corpus every run reported its full binary set, so the subset case is
    rare — but it is not a defect). What is a defect is an **incomparable** pair
    (``{Ni,Cr}`` vs ``{Ni,Fe}``): two different alloys, silently concatenated into an
    artifact no model spec can name — B4 of the 2026-08-14 ingest-readiness review.
    """

    #: ``(elements, tags)`` per distinct element set, sorted; tags sorted within.
    tags_by_elements: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]
    #: Union over every input (the element set the merged artifact would carry).
    union: tuple[str, ...]
    #: Pairs of distinct element sets that are incomparable — the refusal condition.
    conflicts: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]
    #: Inputs contributing NO species at all (GREY or empty): a subset of everything,
    #: so never a conflict — but the guard is blind to them, so they are surfaced.
    speciesless_tags: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True iff no two inputs are written over incomparable element sets."""
        return not self.conflicts

    def summary(self) -> str:
        """A compact, multi-line human summary of the element census."""
        n_inputs = sum(len(tags) for _elems, tags in self.tags_by_elements)
        lines = [f"element census: union=[{format_elements(self.union)}] over {n_inputs} inputs"]
        for elems, tags in self.tags_by_elements:
            shown = ", ".join(tags[:3])
            more = f" (+{len(tags) - 3} more)" if len(tags) > 3 else ""
            lines.append(f"  [{format_elements(elems)}] x{len(tags)}: {shown}{more}")
        if self.speciesless_tags:
            lines.append(
                f"  species-blind inputs (guard cannot discriminate): {len(self.speciesless_tags)}"
            )
        for a, b in self.conflicts:
            lines.append(
                f"  CONFLICT: [{format_elements(a)}] vs [{format_elements(b)}] — "
                "incomparable element sets (different alloys)"
            )
        return "\n".join(lines)


def element_census(
    per_input: Sequence[tuple[str, Sequence[EventClass]]],
) -> ElementCensus:
    """Element sets of the merge inputs + the incomparable pairs among them (B4).

    ``per_input`` is ``(tag, classes)`` per catalogue — the per-run inputs, and any
    other catalogue the pass joins against (e.g. a measured stamp source, whose
    class_ids would silently stamp nothing if it came from another alloy).
    Deterministic: every output tuple is sorted, nothing iterates a set/dict order.
    """
    by_elements: dict[tuple[str, ...], list[str]] = {}
    speciesless: list[str] = []
    for tag, classes in per_input:
        elems = catalogue_elements(classes)
        by_elements.setdefault(elems, []).append(tag)
        if not elems:
            speciesless.append(tag)
    distinct = sorted(by_elements)
    conflicts = tuple(
        (a, b)
        for i, a in enumerate(distinct)
        for b in distinct[i + 1 :]
        if not (set(a) <= set(b) or set(b) <= set(a))
    )
    union: set[str] = set()
    for elems in distinct:
        union |= set(elems)
    return ElementCensus(
        tags_by_elements=tuple((e, tuple(sorted(by_elements[e]))) for e in distinct),
        union=tuple(sorted(union)),
        conflicts=conflicts,
        speciesless_tags=tuple(sorted(speciesless)),
    )


@dataclass
class MergeReport:
    """Counts + the merged, QC'd, stamped catalogue from :func:`merge_qcd_catalogues`.

    ``classes`` is the merged catalogue (sorted by ``class_id``, schema v2). All the
    per-run inputs are left untouched.
    """

    n_runs: int
    n_merged_classes: int
    n_input_class_instances: int
    per_run_class_counts: dict[str, int]
    quarantined_in_any_run: int
    status_conflict_count: int
    nonconserving_surviving: int
    qc: QCReport
    stamp: StampReport | None
    classes: list[EventClass]
    #: Classes whose contributing per-run instances do not all carry one
    #: ``action_id`` (action-fingerprint memo Phase 1). Monitor **only** — no column,
    #: no quarantine, no review row: the merged class stores the primary donor's
    #: arrows, so a non-zero count says that geometry does not describe every run's
    #: members. Unstamped (schema<=3) instances are ignored, not counted as a
    #: disagreement.
    action_disagree_classes: int = 0

    def summary(self) -> str:
        """A compact, multi-line human summary of the merge."""
        lines = [
            f"cross-run merge: {self.n_runs} runs / {self.n_input_class_instances} "
            f"(run,class) instances -> {self.n_merged_classes} merged classes",
            f"  quarantined in >=1 run          : {self.quarantined_in_any_run}",
            f"  status conflicts (survive merge): {self.status_conflict_count}",
            f"  non-conserving surviving merge  : {self.nonconserving_surviving} "
            "(delta_atoms != 0; counted, not quarantined — see module docstring)",
            f"  member action_id disagreement   : {self.action_disagree_classes} classes "
            "(stored arrows are the primary donor's; monitor only — no column, no "
            "quarantine)",
        ]
        if self.stamp is not None:
            lines.append(
                f"  stamped measured / pending / non-rep: "
                f"{self.stamp.n_measured} / {self.stamp.n_pending_research} / "
                f"{self.stamp.n_unstamped_nonrepresentable}"
            )
        return "\n".join(lines)


def _merge_gate_logs(gate_logs: Sequence[Sequence[GateResult]]) -> tuple[GateResult, ...]:
    """Fold per-run class gate logs into one, keeping the worst outcome per gate.

    The worst-outcome-per-gate policy is the natural cross-run generalization of
    ``build``'s worst-over-members aggregation (``_aggregate_gates``): a class that is
    unmappable / non-conserving / straddling in *any* contributing run keeps that
    verdict in the merged audit record. Ties break on the first-seen detail, and the
    result is emitted in deterministic gate-name order.
    """
    worst: dict[str, GateResult] = {}
    for log in gate_logs:
        for g in log:
            cur = worst.get(g.gate)
            if cur is None or _OUTCOME_SEVERITY[g.outcome] > _OUTCOME_SEVERITY[cur.outcome]:
                worst[g.gate] = g
    return tuple(worst[name] for name in sorted(worst))


def _sortable(x: float) -> float:
    """Map NaN to +inf so member sort keys are total and deterministic."""
    return x if math.isfinite(x) else float("inf")


def _aligned_dE(ec: EventClass) -> tuple[tuple[float, ...], list[float]]:
    """Per-member ``dE`` for one instance, aligned with ``ec.barriers_eV``.

    Two stored conventions exist for ``dE_pair_list_eV`` and both must round-trip
    through a merge without mispairing a barrier with another member's ``dE``:

    * **aligned** (``len == len(barriers_eV)``) -- one entry per member, ``NaN`` for
      an unpaired one. What :func:`_merge_one_class` writes, and what a per-run build
      produces whenever every member is linked.
    * **subset** (``len < len(barriers_eV)``) -- the historical per-run build form:
      only the linked members contribute, in member order. It is re-aligned here by
      the ``nu0_b_list_hz`` mask, which ``build_class_catalogue`` fills in the *same*
      member loop (``NaN`` exactly for an unpaired member). Measured on the 53-run
      production corpus: 5/5 subset-form classes re-align exactly, 0 ambiguous.

    Returns ``(aligned, leftover)``. ``leftover`` is non-empty only in the defensive
    case where the mask cannot resolve the subset (a linked member whose partner had
    a non-finite nu0 would blur the mask): those values stay out of the aligned array
    -- guessing an alignment is exactly the defect this function exists to prevent --
    but are still handed to ``dEnergy``/``pair_status``, so no class loses backward
    information it has today.

    The mask re-alignment is exact under the build invariant that
    ``nu0_b_list_hz[i]`` is ``NaN`` for exactly the unpaired members (both lists are
    filled in the same member loop of ``build_class_catalogue``); an input violating
    it -- an *unpaired* member carrying a *finite* ``nu0_b`` -- would mis-slot, and
    no in-tree producer can emit that shape.
    """
    n = len(ec.barriers_eV)
    de = [float(d) for d in ec.dE_pair_list_eV]
    if len(de) == n:
        return tuple(de), []
    if not de:
        return (float("nan"),) * n, []
    nb = ec.nu0_b_list_hz
    if len(nb) == n:
        linked = [i for i in range(n) if math.isfinite(float(nb[i]))]
        if len(linked) == len(de):
            out = [float("nan")] * n
            for k, i in enumerate(linked):
                out[i] = de[k]
            return tuple(out), []
    return (float("nan"),) * n, de


def _merge_one_class(
    class_id: str,
    instances: Sequence[tuple[str, EventClass]],
    *,
    nu0_fallback_hz: float,
) -> EventClass:
    """Merge all per-run instances of one ``class_id`` into a single ``EventClass``.

    ``instances`` is ``(run_tag, EventClass)`` for every run that saw this class,
    given in **run_tag-sorted** order (the first is the primary donor).
    """
    primary = instances[0][1]

    # --- aligned (Ea, nu0_f, nu0_b, residuals, dE) member rows, concatenated then
    # re-sorted AS ONE TUPLE. The v3 per-member residual columns ride along, aligned
    # by member; a pre-v3 instance contributes NaN residuals (read-compat).
    #
    # dE must ride the SAME tuple: it used to be collected into its own
    # independently-``sorted()`` list, so whenever every member happened to be linked
    # the two lists were the same LENGTH but a different ORDER — enough for the
    # length-keyed alignment guard in ``one_way_flag`` (and the positional zip in
    # ``surrogate``) to pair barriers[i] with an unrelated member's dE.
    rows: list[tuple[float, float, float, float, float, float]] = []
    leftover_dE: list[float] = []
    for _tag, ec in instances:
        n = len(ec.barriers_eV)
        nu0_b = ec.nu0_b_list_hz if len(ec.nu0_b_list_hz) == n else (float("nan"),) * n
        m_res = (
            ec.mover_max_residual_list
            if len(ec.mover_max_residual_list) == n
            else (float("nan"),) * n
        )
        x_res = ec.max_residual_list if len(ec.max_residual_list) == n else (float("nan"),) * n
        de_i, leftover = _aligned_dE(ec)
        leftover_dE.extend(leftover)
        for i in range(n):
            rows.append(
                (
                    float(ec.barriers_eV[i]),
                    float(ec.nu0_f_list_hz[i]),
                    float(nu0_b[i]),
                    float(m_res[i]),
                    float(x_res[i]),
                    float(de_i[i]),
                )
            )
    rows.sort(key=lambda t: tuple(_sortable(x) for x in t))
    barriers = tuple(t[0] for t in rows)
    nu0_f = tuple(t[1] for t in rows)
    nu0_b = tuple(t[2] for t in rows)
    mover_resid = tuple(t[3] for t in rows)
    max_resid = tuple(t[4] for t in rows)
    # Stored in the ALIGNED convention: one entry per member, NaN where unpaired.
    dE_aligned = tuple(t[5] for t in rows)
    # The finite subset drives the order-independent reductions (dEnergy, pairing).
    dE_pairs = sorted([d for d in dE_aligned if math.isfinite(d)] + leftover_dE)

    # --- run-qualified provenance --------------------------------------------------
    source_rows = tuple(sorted(int(r) for _tag, ec in instances for r in ec.source_rows))
    source_idx_refs = tuple(sorted(int(r) for _tag, ec in instances for r in ec.source_idx_refs))
    sim_paths = tuple(
        sorted(f"{tag}#{int(r)}" for tag, ec in instances for r in ec.source_idx_refs)
    )

    # --- recompute the rate representative over the merged member list -------------
    agg = aggregate_rate_space(
        list(barriers), list(nu0_f), primary.t_ref_K, nu0_fallback_hz=nu0_fallback_hz
    )

    # --- pairing (content-based class_ids agree across runs; take min non-None) -----
    backward_candidates = sorted(
        {ec.backward_class for _tag, ec in instances if ec.backward_class is not None}
    )
    backward_class = backward_candidates[0] if backward_candidates else None
    self_reverse = primary.self_reverse
    if self_reverse:
        pair_status: str = "self"
    elif dE_pairs:
        pair_status = "linked"
    else:
        pair_status = "unpaired"
    dEnergy = (math.fsum(dE_pairs) / len(dE_pairs)) if dE_pairs else None

    # --- merged gate log + fresh (non-quarantined) audit status --------------------
    gate_log = _merge_gate_logs([ec.gate_log for _tag, ec in instances])
    gate_ok = all(g.outcome in (GateOutcome.PASS, GateOutcome.NA) for g in gate_log)
    audit_status = "approved" if gate_ok and len(barriers) >= 2 else "pending"

    return replace(
        primary,
        barriers_eV=barriers,
        nu0_f_list_hz=nu0_f,
        nu0_b_list_hz=nu0_b,
        dE_pair_list_eV=dE_aligned,
        mover_max_residual_list=mover_resid,
        max_residual_list=max_resid,
        k_rate_mean_psinv=agg.k_rate_mean_psinv,
        Ea_rep_eV=agg.Ea_rep_eV,
        nu0_geo_psinv=agg.nu0_geo_psinv,
        Ea_std_eV=agg.Ea_std_eV,
        n_eff=agg.n_eff,
        Ea_mean_eV=agg.Ea_mean_eV,
        Ea_median_eV=agg.Ea_median_eV,
        backward_class=backward_class,
        self_reverse=self_reverse,
        dEnergy_eV=dEnergy,
        pair_status=pair_status,  # type: ignore[arg-type]
        source_rows=source_rows,
        source_idx_refs=source_idx_refs,
        source_sim_paths=sim_paths,
        gate_log=gate_log,
        audit_status=audit_status,  # type: ignore[arg-type]
        audit_reason="",
        nu0_pair_policy=None,
        # Action identity (arrows / action_id / archetype) is geometry, so it rides
        # along from the primary donor with the rest of the identity fields. The two
        # *derived* action columns are re-decided on the merged data: `one_way` over
        # the merged member list, `action_pair_mismatch` by the merged QC pass.
        one_way=one_way_flag(barriers, dE_aligned, dEnergy),
        action_pair_mismatch=False,
        schema_version=CATALOGUE_SCHEMA_VERSION,
    )


def union_classes(
    per_run: Sequence[tuple[str, Sequence[EventClass]]],
    *,
    nu0_fallback_hz: float = DEFAULT_NU0_FALLBACK_HZ,
) -> list[EventClass]:
    """Class-level union of per-run catalogues (no QC / stamp), sorted by ``class_id``.

    ``per_run`` is ``(run_tag, classes)`` per pyKMC run. Runs are processed in
    **run_tag-sorted** order so the primary donor (identity + ``t_ref_K`` source) and
    every reduction are deterministic regardless of the caller's argument order.
    """
    ordered_runs = sorted(per_run, key=lambda rc: rc[0])
    groups: dict[str, list[tuple[str, EventClass]]] = {}
    for tag, classes in ordered_runs:
        for ec in classes:
            groups.setdefault(ec.class_id, []).append((tag, ec))
    merged = [
        _merge_one_class(cid, groups[cid], nu0_fallback_hz=nu0_fallback_hz)
        for cid in sorted(groups)
    ]
    return merged


def merge_qcd_catalogues(
    per_run: Sequence[tuple[str, Sequence[EventClass]]],
    *,
    tol: float = DEFAULT_RECIPROCITY_TOL_EV,
    spread_tol: float = DEFAULT_SPREAD_TOL_EV,
    overlay: Mapping[str, str] | None = None,
    measured_class_ids: frozenset[str] | set[str] = frozenset(),
    nu0_fallback_hz: float = DEFAULT_NU0_FALLBACK_HZ,
    pending_note: str = "",
) -> MergeReport:
    """Union per-run catalogues on ``class_id``, re-run QC, then class_id-key stamp.

    Steps: (1) :func:`union_classes` folds the per-run member lists; (2) :func:`apply_qc`
    re-runs the reciprocity / delta-less / dE-spread screens and the human-veto overlay
    on the *merged* members (statuses are re-decided, never unioned); (3)
    :func:`stamp_rate_policy` stamps the class_id-keyed measured set carried forward from
    a reference catalogue (``measured_class_ids``); recovered representable classes
    become ``pending_research``. When ``measured_class_ids`` is empty the stamp step is
    skipped (``MergeReport.stamp is None``) and every representable class stays
    unstamped.
    """
    merged = union_classes(per_run, nu0_fallback_hz=nu0_fallback_hz)
    qc = apply_qc(merged, tol=tol, spread_tol=spread_tol, overlay=overlay)
    out_classes = qc.classes

    stamp: StampReport | None = None
    measured = frozenset(measured_class_ids)
    if measured:
        stamp = stamp_rate_policy(
            out_classes,
            measured_class_ids=measured,
            pending_note=pending_note,
        )
        out_classes = stamp.classes

    # provenance metrics (deterministic string sets) --------------------------------
    quarantined_in_any_run = {
        ec.class_id
        for _tag, classes in per_run
        for ec in classes
        if ec.audit_status == "quarantined"
    }
    survived = {c.class_id for c in out_classes if c.audit_status != "quarantined"}
    status_conflict = quarantined_in_any_run & survived
    nonconserving_surviving = sum(
        1 for c in out_classes if c.delta_atoms != 0 and c.audit_status != "quarantined"
    )

    per_run_counts = {tag: len(classes) for tag, classes in sorted(per_run, key=lambda rc: rc[0])}
    n_instances = sum(len(classes) for _tag, classes in per_run)

    # Cross-run action agreement (monitor only, action-fingerprint memo Phase 1): the
    # merged class stores the PRIMARY DONOR's arrows, so a class whose per-run
    # instances disagree on action_id is holding geometry that does not describe every
    # run's members. `action_id` is frame-invariant, so comparing the stored digests
    # is enough — no re-canonicalisation. Unstamped (schema<=3) instances carry None
    # and are ignored rather than counted as a disagreement.
    by_class: dict[str, set[int]] = {}
    for _tag, classes in per_run:
        for ec in classes:
            if ec.action_id is not None:
                by_class.setdefault(ec.class_id, set()).add(int(ec.action_id))
    action_disagree = sum(1 for ids in by_class.values() if len(ids) > 1)

    return MergeReport(
        n_runs=len(per_run),
        n_merged_classes=len(out_classes),
        n_input_class_instances=n_instances,
        per_run_class_counts=per_run_counts,
        quarantined_in_any_run=len(quarantined_in_any_run),
        status_conflict_count=len(status_conflict),
        nonconserving_surviving=nonconserving_surviving,
        qc=qc,
        stamp=stamp,
        classes=out_classes,
        action_disagree_classes=action_disagree,
    )


def measured_class_ids_from_catalogue(classes: Sequence[EventClass]) -> frozenset[str]:
    """The ``harvested_pair`` (measured) ``class_id`` set of a stamped/graduated catalogue."""
    from pylatkmc.ingest.qc import NU0_POLICY_HARVESTED_PAIR

    return frozenset(c.class_id for c in classes if c.nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR)
