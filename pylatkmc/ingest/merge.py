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
* **Concatenate member lists** across runs: the aligned ``(Ea, ν0_f, ν0_b)`` member
  triples, the linked-member ``dE_pair_list_eV``, and the run-local provenance
  (``source_rows`` / ``source_idx_refs``). All concatenations are re-sorted so the
  stored tuples are order-independent.
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

    def summary(self) -> str:
        """A compact, multi-line human summary of the merge."""
        lines = [
            f"cross-run merge: {self.n_runs} runs / {self.n_input_class_instances} "
            f"(run,class) instances -> {self.n_merged_classes} merged classes",
            f"  quarantined in >=1 run          : {self.quarantined_in_any_run}",
            f"  status conflicts (survive merge): {self.status_conflict_count}",
            f"  non-conserving surviving merge  : {self.nonconserving_surviving} "
            "(delta_atoms != 0; counted, not quarantined — see module docstring)",
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

    # --- aligned (Ea, nu0_f, nu0_b) member triples, concatenated then re-sorted ----
    triples: list[tuple[float, float, float]] = []
    for _tag, ec in instances:
        n = len(ec.barriers_eV)
        nu0_b = ec.nu0_b_list_hz if len(ec.nu0_b_list_hz) == n else (float("nan"),) * n
        for i in range(n):
            triples.append((float(ec.barriers_eV[i]), float(ec.nu0_f_list_hz[i]), float(nu0_b[i])))
    triples.sort(key=lambda t: (t[0], _sortable(t[1]), _sortable(t[2])))
    barriers = tuple(t[0] for t in triples)
    nu0_f = tuple(t[1] for t in triples)
    nu0_b = tuple(t[2] for t in triples)

    # --- linked-member dE_pair list (standalone subset), concatenated + sorted -----
    dE_pairs = sorted(
        float(d) for _tag, ec in instances for d in ec.dE_pair_list_eV if math.isfinite(d)
    )

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
        dE_pair_list_eV=tuple(dE_pairs),
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
    )


def measured_class_ids_from_catalogue(classes: Sequence[EventClass]) -> frozenset[str]:
    """The ``harvested_pair`` (measured) ``class_id`` set of a stamped/graduated catalogue."""
    from pylatkmc.ingest.qc import NU0_POLICY_HARVESTED_PAIR

    return frozenset(c.class_id for c in classes if c.nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR)
