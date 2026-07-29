"""Lineage stamp remap for identity migrations (over-snapping memo 2026-07-29 §8.3).

A ``CANON_SCHEMA_VERSION`` bump relabels every ``class_id``: catalogues rebuilt
under the new policy share **no** ids with previously stamped/graduated
catalogues, so measured (``harvested_pair``) stamps, graduation records, veto
overlays, and review lists must be carried across by **event lineage**, not by
id. The mechanics (memo §8.3): old class -> member provenance (``source_rows``
/ ``source_idx_refs`` into the stamp-source reference table) -> the member's
fate in the NEW build of that same reference table (its new ``class_id``, or
its discard-ledger reason) -> transfer ``nu0_pair_policy`` + audit provenance
onto the new class.

Guarantees:

* **Total accounting** — every old class ends ``REMAPPED`` / ``REMAPPED_SPLIT``
  (onto >=1 new class) or ``UNMATCHED_*`` with an explicit reason (e.g. all
  members discarded to the ledger); nothing is silently dropped.
* **Deterministic** — sorted iteration everywhere; no ``hash()``/set order
  reaches an output.
* **One key** — lineage is keyed on ``idx_ref`` (the run-local event id both
  catalogue ``source_idx_refs`` and the ledger record; catalogue
  ``source_rows`` carries ``source_row`` semantics, NOT the positional row, so
  it is never used as a key). An ``idx_ref`` claimed twice in the new build
  (two classes, or a class and the ledger) is a hard error; pairing the wrong
  reference table surfaces as reported ``UNMATCHED_MEMBERS_MISSING`` classes,
  never a silent no-op.

Splits (old members landing in >1 new class — the §6 mask can split a class)
transfer the stamp to **every** landing class and are reported. Joins (>1 old
class landing on one new class) resolve deterministically — ``harvested_pair``
outranks ``pending_research`` — and are reported. The remap sets only
``nu0_pair_policy`` and appends provenance to ``audit_reason``; QC verdicts
(``audit_status``) belong to the QC pass and are left untouched.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from .event_class import EventClass
from .qc import NU0_POLICY_HARVESTED_PAIR, NU0_POLICY_PENDING_RESEARCH

#: Outcome vocabulary for a remapped old class (report column ``outcome``).
OUTCOME_REMAPPED = "REMAPPED"
OUTCOME_SPLIT = "REMAPPED_SPLIT"
OUTCOME_DISCARDED = "UNMATCHED_ALL_MEMBERS_DISCARDED"
OUTCOME_MISSING = "UNMATCHED_MEMBERS_MISSING"

_STAMPED_POLICIES = (NU0_POLICY_HARVESTED_PAIR, NU0_POLICY_PENDING_RESEARCH)


@dataclass(frozen=True)
class MemberFate:
    """One event's fate in the new build, keyed by ``idx_ref``."""

    idx_ref: int
    new_class_id: str | None  #: ``None`` when the event never joined a new class
    note: str  #: ``""`` for kept events; ledger reason or ``"MISSING"`` otherwise


@dataclass(frozen=True)
class ClassRemap:
    """The lineage verdict for one old class (report row)."""

    old_class_id: str
    old_policy: str | None
    old_audit_status: str
    old_audit_reason: str
    fates: tuple[MemberFate, ...]
    new_class_ids: tuple[str, ...]  #: sorted unique landing ids ((), if unmatched)
    outcome: str
    discard_reasons: tuple[str, ...]  #: sorted unique ledger reasons among members


@dataclass
class RemapReport:
    """Every old class's verdict + the join conflicts seen while stamping."""

    classes: list[ClassRemap] = field(default_factory=list)
    join_conflicts: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        by_outcome: dict[str, int] = defaultdict(int)
        for cr in self.classes:
            by_outcome[cr.outcome] += 1
        stamped = [cr for cr in self.classes if cr.old_policy in _STAMPED_POLICIES]
        return {
            "old_classes": len(self.classes),
            "old_stamped": len(stamped),
            "old_stamped_unmatched": sum(1 for cr in stamped if not cr.new_class_ids),
            **{k: by_outcome[k] for k in sorted(by_outcome)},
        }


def build_lineage(
    new_classes: Sequence[EventClass],
    ledger_rows: Sequence[Mapping[str, Any]],
) -> dict[int, MemberFate]:
    """``idx_ref`` -> fate in the new build (kept class or ledger reason).

    ``ledger_rows`` are the sidecar ledger records (needs ``idx_ref``,
    ``reason``). An ``idx_ref`` appearing in two new classes, or in both a
    class and the ledger, is a corrupt build and raises.
    """
    lineage: dict[int, MemberFate] = {}
    for c in sorted(new_classes, key=lambda c: c.class_id):
        for idx in c.source_idx_refs:
            idx = int(idx)
            if idx in lineage:
                raise ValueError(
                    f"idx_ref {idx} appears in classes {lineage[idx].new_class_id} "
                    f"and {c.class_id} — corrupt new catalogue"
                )
            lineage[idx] = MemberFate(idx, c.class_id, "")
    for entry in ledger_rows:
        idx = int(entry["idx_ref"])
        if idx in lineage:
            raise ValueError(
                f"idx_ref {idx} is both in class {lineage[idx].new_class_id} and "
                "the discard ledger — corrupt new build"
            )
        lineage[idx] = MemberFate(idx, None, str(entry["reason"]))
    return lineage


def remap_classes(
    old_classes: Sequence[EventClass],
    lineage: Mapping[int, MemberFate],
) -> RemapReport:
    """Resolve every old class through the lineage map (memo §8.3)."""
    report = RemapReport()
    for old in sorted(old_classes, key=lambda c: c.class_id):
        fates: list[MemberFate] = []
        for idx in old.source_idx_refs:
            idx = int(idx)
            fate = lineage.get(idx)
            fates.append(fate if fate is not None else MemberFate(idx, None, "MISSING"))
        new_ids = tuple(sorted({f.new_class_id for f in fates if f.new_class_id is not None}))
        reasons = tuple(sorted({f.note for f in fates if f.note and f.note != "MISSING"}))
        if new_ids:
            outcome = OUTCOME_REMAPPED if len(new_ids) == 1 else OUTCOME_SPLIT
        elif reasons:
            outcome = OUTCOME_DISCARDED
        else:
            outcome = OUTCOME_MISSING
        report.classes.append(
            ClassRemap(
                old_class_id=old.class_id,
                old_policy=old.nu0_pair_policy,
                old_audit_status=old.audit_status,
                old_audit_reason=old.audit_reason,
                fates=tuple(fates),
                new_class_ids=new_ids,
                outcome=outcome,
                discard_reasons=reasons,
            )
        )
    return report


def _provenance_line(cr: ClassRemap, note: str) -> str:
    head = f"remapped from {cr.old_class_id[:12]} [{cr.old_policy}]"
    if note:
        head = f"{head} ({note})"
    return f"{head}: {cr.old_audit_reason}" if cr.old_audit_reason else head


def apply_stamps(
    new_classes: Sequence[EventClass],
    report: RemapReport,
    *,
    note: str = "",
) -> list[EventClass]:
    """Transfer old stamps onto the new classes; returns stamped copies.

    Only old classes whose ``nu0_pair_policy`` is set transfer anything. A new
    class hit by conflicting policies takes ``harvested_pair`` (measured
    evidence outranks a pending flag) and the conflict is recorded on
    ``report.join_conflicts``. Output order matches ``new_classes``.
    """
    hits: dict[str, list[ClassRemap]] = defaultdict(list)
    for cr in report.classes:
        if cr.old_policy not in _STAMPED_POLICIES:
            continue
        for nid in cr.new_class_ids:
            hits[nid].append(cr)

    out: list[EventClass] = []
    for c in new_classes:
        stamps = hits.get(c.class_id)
        if not stamps:
            out.append(c)
            continue
        stamps = sorted(stamps, key=lambda cr: cr.old_class_id)
        policies = sorted({cr.old_policy for cr in stamps if cr.old_policy})
        policy = NU0_POLICY_HARVESTED_PAIR if NU0_POLICY_HARVESTED_PAIR in policies else policies[0]
        if len(policies) > 1:
            report.join_conflicts.append(
                f"{c.class_id[:12]} <- {{{', '.join(cr.old_class_id[:12] for cr in stamps)}}} "
                f"policies {policies}: kept {policy}"
            )
        prov = " | ".join(_provenance_line(cr, note) for cr in stamps)
        reason = f"{c.audit_reason} | {prov}" if c.audit_reason else prov
        out.append(replace(c, nu0_pair_policy=policy, audit_reason=reason))
    return out


def remap_payload(
    payload: Mapping[str, str],
    report: RemapReport,
    *,
    note: str = "",
) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Remap a ``class_id -> reason`` mapping (veto overlay) through the lineage.

    Returns ``(new_payload, records)`` where ``records`` rows are
    ``(old_class_id, outcome, ';'-joined new ids)``; an old id absent from the
    old catalogue is reported as ``UNMATCHED_NOT_IN_OLD_CATALOGUE``. Two old
    entries landing on one new id merge their reasons (sorted, ``" | "``).
    """
    by_old = {cr.old_class_id: cr for cr in report.classes}
    new_reasons: dict[str, list[str]] = defaultdict(list)
    records: list[tuple[str, str, str]] = []
    for old_id in sorted(payload):
        cr = by_old.get(old_id)
        if cr is None:
            records.append((old_id, "UNMATCHED_NOT_IN_OLD_CATALOGUE", ""))
            continue
        records.append((old_id, cr.outcome, ";".join(cr.new_class_ids)))
        prefix = f"migrated from {old_id[:12]}"
        if note:
            prefix = f"{prefix} ({note})"
        for nid in cr.new_class_ids:
            new_reasons[nid].append(f"{prefix}: {payload[old_id]}")
    merged = {nid: " | ".join(sorted(reasons)) for nid, reasons in sorted(new_reasons.items())}
    return merged, records
