"""Ingest quality-control screens over the ``EventClass`` catalogue (Phase C).

The approved Phase C rate-model architecture keeps the exact-match catalogue as the
identity/training/provenance layer and adds a small set of **ingest QC screens** that
flag or quarantine corpus-integrity defects before the rate model consumes the
catalogue (``PHASEC_RATE_MODEL_DECISION.md`` §4; ``PHASEC_VALIDATION_REPORT`` §7):

* **reciprocity** — a linked forward/backward pair must satisfy ``dE_f + dE_b ~= 0``.
  A residual above ``tol`` is a mislink or projection artifact; **both** directions are
  quarantined. A *self-linked* class (``backward_class == class_id``) whose ``dEnergy``
  is non-zero is the same defect (a true self-reverse has ``dE == 0``): quarantined.
* **delta-less** — an empty ``delta`` is not executable on-lattice: quarantined. A
  delta-less class that is also **mover-less** is relabelled ``NO_OP`` (action
  fingerprint memo 2026-07-29 §5.3 / ruling 5): its initial and final states snap
  identically, so it is the on-lattice image of basin-internal motion rather than a
  corpus defect. The status is unchanged (a **reason rename only** — a dedicated
  ``audit_status`` would be silently *included* by every ``== "quarantined"``
  exclusion); the reason-aware carve-out in :class:`QCReport` is what stops NO_OPs
  counting against catalogue quality.
* **linked-pair action** (memo §3.4 / ruling 9) — a linked forward/backward pair
  must share one ``action_id`` (the canon minimises over ``{A, A⁻¹}``). A mismatch
  sets the ``action_pair_mismatch`` column, logs a line, and appends the pair to the
  standing review list — it is **never** a quarantine and never a hard failure.
* **within-class dE spread** — a class with two or more members whose ``dE_pair_list``
  spread exceeds ``spread_tol`` at identical lattice context is context-underresolved
  by construction (no lattice identity can split it): **quarantined**
  (``PROJECTION_IDENTITY_REDESIGN_DECISION_2026-07-22.md`` §3.5 promoted the former
  CONTEXT_UNDERRESOLVED flag to quarantine; the class's flux routes via the surrogate
  + flag-registry channel like a pending-re-search class).
* **human-veto overlay** (memo §8-N8) — a curator-supplied ``class_id -> reason`` map,
  applied last; overlay quarantines are sticky. A class already ``quarantined`` on
  input **stays** quarantined on output — re-emission never resurrects an exclusion.
  Overlay entries that match **no** class in the catalogue are surfaced in
  ``QCReport.overlay_unmatched`` (never silently dropped), so a veto orphaned by a
  projector/identity relabeling is visible instead of silently lapsing.

The pending-re-search **rate-policy stamp** (:func:`stamp_rate_policy`) and the
re-search **graduation gate** (:func:`graduate_classes`) live here too: they are
re-emission passes with the same write discipline (memo §3.2–3.4).

Determinism (contract Phase A, hard gate)
-----------------------------------------
Every screen iterates a list **sorted by** ``class_id``; nothing depends on ``hash()``,
``set``/``dict`` iteration order, or ``PYTHONHASHSEED``. The screens are pure: they build
new ``EventClass`` instances via :func:`dataclasses.replace` and never mutate the inputs.

Load cost
---------
Only stdlib and :mod:`pylatkmc.ingest.event_class` are imported at module load, so
``import pylatkmc.ingest.qc`` stays cheap (``pyarrow``/``pandas`` are pulled only by the
Parquet I/O in ``event_class``, and only when a Parquet function is actually called).
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from pathlib import Path

from pylatkmc.ingest.event_class import (
    CATALOGUE_SCHEMA_VERSION,
    NO_OP_REASON,
    EventClass,
    GateOutcome,
    is_no_op,
)

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py310 fallback (matches loader.py)
    import tomli as tomllib  # type: ignore[no-redef]


# --------------------------------------------------------------------------- #
# Defaults                                                                    #
# --------------------------------------------------------------------------- #
DEFAULT_RECIPROCITY_TOL_EV: float = 1e-6
"""``|dE_f + dE_b|`` (and ``|dE|`` for a self-link) above this (eV) is a defect."""

DEFAULT_SPREAD_TOL_EV: float = 0.1
"""Within-class ``dE_pair_list`` spread above this (eV) quarantines the class
(CONTEXT_UNDERRESOLVED, decision memo 2026-07-22 §3.5)."""

# ν0 rate-policy stamps (memo 2026-07-22 §3.2–3.4). ``pylatkmc.translator_v2``
# mirrors these literals (the bare core cannot import the [ingest] extras at module
# load); ``tests/unit_py/test_translator_v2.py`` locks the pairs together.
NU0_POLICY_HARVESTED_PAIR: str = "harvested_pair"
"""Measured class: fires its raw harvested (ν0, Ea) pairs (Phase C §8-N6)."""

NU0_POLICY_PENDING_RESEARCH: str = "pending_research"
"""Recovered class with no previously-measured member: never emitted as a measured
proc; sites fall through to the surrogate channel + flag registry until the
re-search agreement gate graduates it."""

DEFAULT_GRADUATION_BAND_EV: float = 0.05
"""Re-search agreement gate (memo §3.4): ``|Ea_re-search − Ea_harvested|`` at or
below this (eV, the a-priori pair-noise band) graduates a pending class."""

# Screen attribution labels (a class is attributed to the FIRST screen that
# quarantines it, in this order; this only governs per-screen COUNTS, not status).
_SCREEN_PREEXISTING = "preexisting"
_SCREEN_DELTALESS = "deltaless"
_SCREEN_RECIPROCITY = "reciprocity"
_SCREEN_SPREAD = "spread"
_SCREEN_OVERLAY = "overlay"

# --- linked-pair action screen (action-fingerprint memo §3.4 + §11 ruling 9) ----
ACTION_REVIEW_FIELDS: tuple[str, ...] = (
    "class_id",
    "partner_class_id",
    "action_id",
    "partner_action_id",
    "archetype",
    "partner_archetype",
    "n_events",
    "review_reason",
    "review_group",
)
"""Column order of the standing action-review list (leads with ``class_id``, so
``python -m pylatkmc.ingest.cli remap --review-in`` carries it across a CANON bump,
and tails with the ``review_reason`` / ``review_group`` pair the gap-2 triage list
uses)."""

ACTION_REVIEW_GROUP: str = "action-pair-mismatch (Phase 1, memo 2026-07-30 ruling 9)"
"""``review_group`` tag every row this screen appends carries."""


@dataclass
class QCReport:
    """Per-screen counts + the QC'd (re-emitted, schema-v2) classes.

    ``classes`` is the modified catalogue, sorted by ``class_id`` with
    ``audit_status``/``audit_reason``/``schema_version`` set. All quarantine sets
    are disjoint by attribution, so ``total_quarantined`` equals
    ``preexisting_quarantined + deltaless_quarantined + reciprocity_quarantined +
    spread_quarantined + overlay_quarantined``. ``overlay_unmatched`` lists overlay
    ``class_id``\\ s absent from the catalogue (surfaced, never silently dropped).

    ``no_op_quarantined`` / ``no_op_events`` are a **reason-aware carve-out**, not a
    sixth addend: they count the quarantined classes whose reason is
    :data:`~pylatkmc.ingest.event_class.NO_OP_REASON` (a subset of the quarantine
    set, usually attributed to the delta-less screen). Ruling 5: NO_OPs are physical
    (the on-lattice image of basin-internal motion), so they must not read as a
    catalogue-quality defect -- the ``TOTAL`` line therefore also reports the count
    net of them.

    The ``action_pair_*`` fields are the linked-pair action screen (ruling 9): a
    **flag and a review row**, never a quarantine -- the classes keep firing.
    """

    n_input: int
    n_events_input: int
    reciprocity_quarantined: int
    reciprocity_events: int
    deltaless_quarantined: int
    deltaless_events: int
    spread_quarantined: int
    spread_events: int
    overlay_quarantined: int
    overlay_events: int
    overlay_unmatched: tuple[str, ...]
    preexisting_quarantined: int
    preexisting_events: int
    total_quarantined: int
    total_quarantined_events: int
    classes: list[EventClass]
    no_op_quarantined: int = 0
    no_op_events: int = 0
    action_pair_mismatch_pairs: int = 0
    action_pair_mismatch_classes: int = 0
    action_review_rows: list[dict[str, object]] = dataclass_field(default_factory=list)

    def summary(self) -> str:
        """A compact, multi-line human summary of the per-screen counts."""
        net_classes = self.total_quarantined - self.no_op_quarantined
        net_events = self.total_quarantined_events - self.no_op_events
        lines = [
            f"ingest QC: {self.n_input} classes / {self.n_events_input} events in",
            f"  reciprocity : {self.reciprocity_quarantined:3d} classes "
            f"/ {self.reciprocity_events} events  quarantined",
            f"  delta-less  : {self.deltaless_quarantined:3d} classes "
            f"/ {self.deltaless_events} events  quarantined",
            f"  dE-spread   : {self.spread_quarantined:3d} classes "
            f"/ {self.spread_events} events  quarantined "
            "(CONTEXT_UNDERRESOLVED, memo 2026-07-22 s3.5)",
            f"  human veto  : {self.overlay_quarantined:3d} classes "
            f"/ {self.overlay_events} events  quarantined",
            f"  pre-existing: {self.preexisting_quarantined:3d} classes "
            f"/ {self.preexisting_events} events  (carried, never downgraded)",
            f"  of which NO_OP: {self.no_op_quarantined:3d} classes "
            f"/ {self.no_op_events} events  — PHYSICAL (on-lattice image of "
            "basin-internal motion, memo 2026-07-29 §5.3), not a quality defect",
            f"  TOTAL       : {self.total_quarantined:3d} classes "
            f"/ {self.total_quarantined_events} events  quarantined "
            f"(excl. NO_OP: {net_classes} classes / {net_events} events)",
            f"  action pairs: {self.action_pair_mismatch_pairs:3d} linked pairs "
            f"/ {self.action_pair_mismatch_classes} classes  disagree on action_id "
            "— FLAGGED + review list, never quarantined (ruling 9)",
        ]
        if self.overlay_unmatched:
            lines.append(
                f"  WARNING: {len(self.overlay_unmatched)} overlay entr"
                f"{'y' if len(self.overlay_unmatched) == 1 else 'ies'} matched no "
                f"class (orphaned vetoes): "
                + ", ".join(cid[:12] + "…" for cid in self.overlay_unmatched)
            )
        return "\n".join(lines)


_DELTALESS_REASON = "QC: empty delta — not executable"
"""The generic delta-less quarantine reason the NO_OP relabel is allowed to replace."""


def _is_generic_deltaless(reason: str) -> bool:
    """True iff ``reason`` is this pass's own generic delta-less text (no curator info)."""
    return reason.strip() == _DELTALESS_REASON


def _n_events(ec: EventClass) -> int:
    """Number of harvested events (member rows) contributing to a class."""
    return len(ec.source_rows)


def load_overlay(path: str | Path) -> dict[str, str]:
    """Load a human-veto overlay (``class_id -> reason``) from TOML or JSON.

    Dispatch is by file extension: ``.toml`` -> :mod:`tomllib`, everything else
    (``.json`` and unknown) -> :mod:`json`. The top-level document must be a
    mapping of ``class_id`` (str) to reason (str); a nested ``{"overlay": {...}}``
    or ``{"vetoes": {...}}`` wrapper is unwrapped. Values are coerced to ``str``.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    parsed = tomllib.loads(text) if p.suffix.lower() == ".toml" else json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"overlay {p} must be a mapping class_id -> reason, got {type(parsed)!r}")
    data: dict[str, object] = {str(k): v for k, v in parsed.items()}
    for wrapper in ("overlay", "vetoes"):
        inner = data.get(wrapper)
        if isinstance(inner, dict):
            data = {str(k): v for k, v in inner.items()}
            break
    return {k: str(v) for k, v in data.items()}


def apply_qc(
    classes: Sequence[EventClass],
    *,
    tol: float = DEFAULT_RECIPROCITY_TOL_EV,
    spread_tol: float = DEFAULT_SPREAD_TOL_EV,
    overlay: Mapping[str, str] | None = None,
) -> QCReport:
    """Run every ingest QC screen over ``classes`` and re-emit them at the current schema.

    Screen order (attribution/priority): pre-existing input quarantines are carried
    first (never downgraded), then delta-less **and its NO_OP relabel**, then
    reciprocity (self-link before pair, so the self-reverse reason wins for a
    self-linked class), then the within-class dE-spread **quarantine** (memo
    2026-07-22 §3.5), then the human-veto overlay (last, sticky), and finally the
    **linked-pair action screen** (flag-only, memo 2026-07-30 ruling 9). A class
    attributed to an earlier screen keeps that attribution for counting; the overlay
    may still overwrite its ``audit_reason`` to record the veto.

    Returns a :class:`QCReport` whose ``classes`` are new ``EventClass`` instances
    (inputs untouched), sorted by ``class_id``, with ``schema_version`` set to the
    current :data:`~pylatkmc.ingest.event_class.CATALOGUE_SCHEMA_VERSION`.
    """
    ordered = sorted(classes, key=lambda c: c.class_id)
    by_id = {c.class_id: c for c in ordered}

    quarantined: set[str] = set()
    reason: dict[str, str] = {}
    attribution: dict[str, str] = {}

    def _quarantine(cid: str, screen: str, why: str) -> None:
        """First-screen-wins quarantine: status + reason + attribution, once."""
        if cid in quarantined:
            return
        quarantined.add(cid)
        reason[cid] = why
        attribution[cid] = screen

    # --- 0. carry pre-existing input quarantines (never downgrade) -----------
    for c in ordered:
        if c.audit_status == "quarantined":
            _quarantine(c.class_id, _SCREEN_PREEXISTING, c.audit_reason)

    # --- 1. delta-less screen ------------------------------------------------
    for c in ordered:
        if len(c.delta) == 0:
            _quarantine(c.class_id, _SCREEN_DELTALESS, _DELTALESS_REASON)

    # --- 1b. NO_OP relabel (ruling 5): reason rename ONLY, never a new status ---
    # A delta-less AND mover-less class is not an anonymous QC defect: initial and
    # final states snap identically, i.e. it is the on-lattice image of basin-internal
    # motion (memo §5.3). The assignment is direct (not via _quarantine's first-wins
    # reason) so the relabel also applies to a class carried in already-quarantined
    # from a previous emission; the human-veto overlay still runs later and wins.
    #
    # Ruling 5 renames the ANONYMOUS bin — it must not delete curator provenance. A
    # prior reason that is not the generic delta-less string (a migrated human veto,
    # a graduation/CONTEXT_SUSPECT note) is PREPENDED-to exactly once, never
    # overwritten: a re-QC pass keeps an already-prefixed reason verbatim.
    no_op_ids: list[str] = []
    for c in ordered:
        if is_no_op(c.delta, c.arrows, c.saddle_token):
            _quarantine(c.class_id, _SCREEN_DELTALESS, NO_OP_REASON)
            prior = (reason.get(c.class_id, c.audit_reason) or "").strip()
            if prior.startswith(NO_OP_REASON):
                reason[c.class_id] = prior  # idempotent: a re-QC pass never re-prefixes
            elif not prior or _is_generic_deltaless(prior):
                reason[c.class_id] = NO_OP_REASON
            else:
                reason[c.class_id] = f"{NO_OP_REASON} | {prior}"
            no_op_ids.append(c.class_id)

    # --- 2. reciprocity screen: self-link first, then linked pairs -----------
    for c in ordered:
        if c.backward_class == c.class_id and c.dEnergy_eV is not None and abs(c.dEnergy_eV) > tol:
            _quarantine(
                c.class_id,
                _SCREEN_RECIPROCITY,
                f"QC: self-reverse with dE != 0 (dE={c.dEnergy_eV:+.4f} eV)",
            )
    for c in ordered:
        b_id = c.backward_class
        if b_id is None or b_id == c.class_id:
            continue
        partner = by_id.get(b_id)
        if partner is None:  # backward_class not present in this catalogue
            continue
        de_f, de_b = c.dEnergy_eV, partner.dEnergy_eV
        if de_f is None or de_b is None:
            continue
        residual = abs(de_f + de_b)
        if residual > tol:
            why = (
                f"QC: pair reciprocity broken (|dE_f+dE_b|={residual:.4f} eV) "
                "— mislink/projection artifact"
            )
            _quarantine(c.class_id, _SCREEN_RECIPROCITY, why)
            _quarantine(b_id, _SCREEN_RECIPROCITY, why)

    # --- 3. within-class dE-spread quarantine (memo 2026-07-22 s3.5) ---------
    # A class whose members disagree in dE beyond spread_tol at identical lattice
    # context is context-underresolved BY CONSTRUCTION (no lattice identity can
    # split it); its flux routes via the surrogate + flag-registry channel.
    for c in ordered:
        finite = [d for d in c.dE_pair_list_eV if math.isfinite(d)]
        if len(c.barriers_eV) >= 2 and len(finite) >= 2:
            spread = max(finite) - min(finite)
            if spread > spread_tol:
                _quarantine(
                    c.class_id,
                    _SCREEN_SPREAD,
                    f"QC: within-class dE spread {spread:.4f} eV at identical "
                    "lattice context — CONTEXT_UNDERRESOLVED, quarantined "
                    "(decision memo 2026-07-22 §3.5)",
                )

    # --- 4. human-veto overlay (last, sticky; orphans surfaced) --------------
    overlay_unmatched: list[str] = []
    if overlay:
        for cid in sorted(overlay):
            if cid not in by_id:
                overlay_unmatched.append(cid)  # surfaced in the report, never silent
                continue
            note = str(overlay[cid]).strip()
            veto_reason = f"QC: human veto — {note}" if note else "QC: human veto"
            if cid not in quarantined:
                _quarantine(cid, _SCREEN_OVERLAY, veto_reason)
            else:
                reason[cid] = veto_reason  # sticky: the curator note wins

    # --- 5. linked-pair action screen (memo §3.4, ruling 9) ------------------
    # A linked pair's two arrow sets are each other's inverse, and the action canon
    # minimises over {A, A^-1} — so a linked pair MUST share one action_id. A
    # mismatch is a pairing/projection defect, but it is NOT quarantined (6 such
    # pairs exist on the v2 corpus; a hard assertion would fail the first rebuild):
    # flag the column, log the line, append the pair to the standing review list,
    # and let the classes keep firing on their measured rates until a human rules.
    mismatch_ids, action_review_rows = _screen_action_pairs(ordered, by_id)

    # --- assemble the re-emitted, schema-v4 classes --------------------------
    out: list[EventClass] = []
    for c in ordered:
        cid = c.class_id
        if cid in quarantined:
            out.append(
                replace(
                    c,
                    audit_status="quarantined",
                    audit_reason=reason.get(cid, c.audit_reason),
                    action_pair_mismatch=cid in mismatch_ids,
                    schema_version=CATALOGUE_SCHEMA_VERSION,
                )
            )
        else:
            out.append(
                replace(
                    c,
                    audit_reason=reason.get(cid, c.audit_reason),
                    action_pair_mismatch=cid in mismatch_ids,
                    schema_version=CATALOGUE_SCHEMA_VERSION,
                )
            )

    def _count(screen: str) -> tuple[int, int]:
        cids = [cid for cid, s in attribution.items() if s == screen]
        return len(cids), sum(_n_events(by_id[cid]) for cid in cids)

    n_pre, ev_pre = _count(_SCREEN_PREEXISTING)
    n_del, ev_del = _count(_SCREEN_DELTALESS)
    n_rec, ev_rec = _count(_SCREEN_RECIPROCITY)
    n_spr, ev_spr = _count(_SCREEN_SPREAD)
    n_ovl, ev_ovl = _count(_SCREEN_OVERLAY)
    total_events = sum(_n_events(by_id[cid]) for cid in quarantined)
    n_no_op = len(no_op_ids)
    ev_no_op = sum(_n_events(by_id[cid]) for cid in no_op_ids)

    return QCReport(
        n_input=len(ordered),
        n_events_input=sum(_n_events(c) for c in ordered),
        reciprocity_quarantined=n_rec,
        reciprocity_events=ev_rec,
        deltaless_quarantined=n_del,
        deltaless_events=ev_del,
        spread_quarantined=n_spr,
        spread_events=ev_spr,
        overlay_quarantined=n_ovl,
        overlay_events=ev_ovl,
        overlay_unmatched=tuple(overlay_unmatched),
        preexisting_quarantined=n_pre,
        preexisting_events=ev_pre,
        total_quarantined=len(quarantined),
        total_quarantined_events=total_events,
        classes=out,
        no_op_quarantined=n_no_op,
        no_op_events=ev_no_op,
        action_pair_mismatch_pairs=len(action_review_rows),
        action_pair_mismatch_classes=len(mismatch_ids),
        action_review_rows=action_review_rows,
    )


def _screen_action_pairs(
    ordered: Sequence[EventClass], by_id: Mapping[str, EventClass]
) -> tuple[set[str], list[dict[str, object]]]:
    """Linked forward/backward pairs that disagree on ``action_id`` (ruling 9).

    Returns ``(flagged_class_ids, review_rows)``. Deterministic: the input is
    ``class_id``-sorted and each pair is reported once, keyed on the smaller
    ``class_id`` so the row is stable whichever direction is visited first. A class
    whose ``action_id`` is ``None`` (a schema<=3 catalogue read forward) is skipped
    — "unknown" is not evidence of a mismatch.
    """
    flagged: set[str] = set()
    rows: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for c in ordered:
        b_id = c.backward_class
        if b_id is None or b_id == c.class_id:
            continue
        partner = by_id.get(b_id)
        if partner is None or c.action_id is None or partner.action_id is None:
            continue
        if c.action_id == partner.action_id:
            continue
        key = (min(c.class_id, b_id), max(c.class_id, b_id))
        flagged.add(c.class_id)
        flagged.add(b_id)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        first, second = (c, partner) if c.class_id == key[0] else (partner, c)
        rows.append(
            {
                "class_id": first.class_id,
                "partner_class_id": second.class_id,
                "action_id": first.action_id,
                "partner_action_id": second.action_id,
                "archetype": first.archetype,
                "partner_archetype": second.archetype,
                "n_events": _n_events(first) + _n_events(second),
                "review_reason": (
                    f"linked pair disagrees on action_id "
                    f"({first.action_id:016x} != {second.action_id:016x}) — the action "
                    "canon minimises over {A, A^-1}, so a linked pair must share one; "
                    "pairing or projection defect (memo §3.4)"
                ),
                "review_group": ACTION_REVIEW_GROUP,
            }
        )
    rows.sort(key=lambda r: str(r["class_id"]))
    return flagged, rows


def append_action_review_rows(path: str | Path, rows: Sequence[Mapping[str, object]]) -> int:
    """Append **new** action-review rows to the standing review list at ``path``.

    Appends (never truncates), writing the :data:`ACTION_REVIEW_FIELDS` header only
    when the file is new or empty — the same "one standing list, grown over time"
    mechanic the gap-2 triage list uses. Rows are **de-duplicated** against the
    ``(class_id, partner_class_id, action_id, partner_action_id)`` keys already in
    the file, and within the batch: a standing list is re-appended to on every
    re-run of ``qc``/``merge``, and duplicate rows would inflate the queue and
    re-open pairs a curator already ruled on. The digests are part of the key so a
    recurrence with *changed* action_ids (an action-schema bump, a re-projection)
    IS written -- new evidence must reach the curator. An existing file whose
    header is a *different* schema raises: silently
    writing misaligned rows into a curator's list is exactly the failure this screen
    exists to prevent. Returns the number of rows **actually written**.
    """
    import csv

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    exists = p.is_file() and p.stat().st_size > 0
    seen: set[tuple[str, str, str, str]] = set()
    if exists:
        with p.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            if tuple(header) != ACTION_REVIEW_FIELDS:
                raise ValueError(
                    f"{p} is not an action-review list (header {header!r} != "
                    f"{list(ACTION_REVIEW_FIELDS)!r}); point --review at a dedicated file"
                )
            idx = tuple(
                ACTION_REVIEW_FIELDS.index(f)
                for f in ("class_id", "partner_class_id", "action_id", "partner_action_id")
            )
            for line in reader:
                if len(line) > max(idx):
                    seen.add((line[idx[0]], line[idx[1]], line[idx[2]], line[idx[3]]))
    fresh: list[Mapping[str, object]] = []
    for row in rows:
        key = (
            str(row.get("class_id", "")),
            str(row.get("partner_class_id", "")),
            str(row.get("action_id", "")),
            str(row.get("partner_action_id", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        fresh.append(row)
    if not fresh and exists:
        return 0
    with p.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ACTION_REVIEW_FIELDS))
        if not exists:
            writer.writeheader()
        for row in fresh:
            writer.writerow({k: row.get(k, "") for k in ACTION_REVIEW_FIELDS})
    return len(fresh)


# --------------------------------------------------------------------------- #
# Rate-policy stamping + re-search graduation (memo 2026-07-22 §3.2–3.4)      #
# --------------------------------------------------------------------------- #
def _class_g3_pass(ec: EventClass) -> bool:
    """True iff the class's aggregated gate log holds a G3 PASS (representable)."""
    return any(g.gate == "G3" and g.outcome == GateOutcome.PASS for g in ec.gate_log)


@dataclass
class StampReport:
    """Counts + re-emitted classes from :func:`stamp_rate_policy`."""

    n_measured: int
    n_pending_research: int
    n_unstamped_nonrepresentable: int
    n_quarantined_untouched: int
    classes: list[EventClass]

    def summary(self) -> str:
        """A compact human summary of the stamp counts."""
        return "\n".join(
            (
                f"rate-policy stamp: {len(self.classes)} classes",
                f"  measured (harvested_pair)      : {self.n_measured}",
                f"  pending re-search (surrogate)  : {self.n_pending_research}",
                f"  non-representable (unstamped)  : {self.n_unstamped_nonrepresentable}",
                f"  quarantined (untouched)        : {self.n_quarantined_untouched}",
            )
        )


def stamp_rate_policy(
    classes: Sequence[EventClass],
    *,
    measured_idx_refs: frozenset[int] | set[int] = frozenset(),
    measured_class_ids: frozenset[str] | set[str] = frozenset(),
    pending_note: str = "",
) -> StampReport:
    """Stamp each class's ν0 rate policy after the QC screens (memo §3.2–3.3).

    A non-quarantined, representable class is **measured** iff it carries a
    previously-measured member — resolved by **either** carry-forward key:

    * ``measured_class_ids`` (content-based, portable across runs): the class's own
      ``class_id`` is in the set. This is the cross-run carry-forward the original
      docstring anticipated ("a future harvest carries forward the previous stamped
      catalogue's measured membership"); it is used by the cross-run merge, where the
      run-local ``idx_ref`` key does **not** survive. Membership is authoritative
      evidence of representability (the reference catalogue already validated the
      class as G3-PASS + measured). Historical note: this key used to *bypass* an
      aggregated G3 FAIL (a later run's snap noise could fail a measured class);
      since the 2026-07-29 build-time discard, G3-failing events never reach
      stamping, so on post-2026-07-29 catalogues the bypass has no object — it is
      kept only for reading pre-migration (CANON v1) catalogues.
    * ``measured_idx_refs`` (run-local): a member ``idx_ref`` is in the set. This is
      the one-time 2026-07-22 migration key (derived from the recorded old→new
      projection map); it keeps the historical G3-PASS precondition.

    Measured classes get ``nu0_pair_policy = "harvested_pair"`` and fire their raw
    harvested pairs.

    A representable (G3 PASS) class with **no** measured member was *recovered*: it
    gets ``"pending_research"`` — the v2 translator excludes it (counted), its sites
    fall through to the Phase C surrogate channel, and the flag registry ranks it (by
    carried flux) for the in-situ pARTn re-search campaign. It converts to measured
    only through :func:`graduate_classes`.

    Quarantined classes and non-representable (G3 FAIL, not in ``measured_class_ids``)
    classes are left unstamped. Pure re-emission: new instances, inputs untouched,
    deterministic ``class_id`` order.
    """
    measured = frozenset(int(r) for r in measured_idx_refs)
    measured_cids = frozenset(measured_class_ids)
    out: list[EventClass] = []
    n_meas = n_pend = n_unrep = n_quar = 0
    for c in sorted(classes, key=lambda k: k.class_id):
        if c.audit_status == "quarantined":
            n_quar += 1
            out.append(replace(c))
            continue
        measured_by_class = c.class_id in measured_cids
        if not _class_g3_pass(c) and not measured_by_class:
            n_unrep += 1
            out.append(replace(c))
            continue
        if measured_by_class or any(int(r) in measured for r in c.source_idx_refs):
            n_meas += 1
            out.append(replace(c, nu0_pair_policy=NU0_POLICY_HARVESTED_PAIR))
            continue
        n_pend += 1
        note = (
            "PENDING_RE_SEARCH: recovered by the 2026-07-22 frame fix with no "
            "previously-measured member; awaiting in-situ re-search verification "
            "(memo §3.2–3.3)"
        )
        if pending_note:
            note = f"{note} — {pending_note}"
        reason = f"{c.audit_reason} | {note}" if c.audit_reason else note
        out.append(
            replace(
                c,
                nu0_pair_policy=NU0_POLICY_PENDING_RESEARCH,
                audit_reason=reason,
            )
        )
    return StampReport(
        n_measured=n_meas,
        n_pending_research=n_pend,
        n_unstamped_nonrepresentable=n_unrep,
        n_quarantined_untouched=n_quar,
        classes=out,
    )


@dataclass
class GraduationReport:
    """Counts, review rows + re-emitted classes from :func:`graduate_classes`."""

    n_pending_in: int
    n_graduated: int
    n_context_suspect: int
    n_unresolved: int
    n_ignored_nonpending: int
    review_rows: list[dict[str, object]]
    classes: list[EventClass]

    def summary(self) -> str:
        """A compact human summary of the graduation outcomes."""
        return "\n".join(
            (
                f"re-search graduation: {self.n_pending_in} pending classes in",
                f"  graduated (agreement gate)     : {self.n_graduated}",
                f"  context-suspect (review list)  : {self.n_context_suspect}",
                f"  still pending (no result yet)  : {self.n_unresolved}",
                f"  research rows on non-pending   : {self.n_ignored_nonpending} (ignored)",
            )
        )


def graduate_classes(
    classes: Sequence[EventClass],
    *,
    research_ea_by_class: Mapping[str, float],
    band_eV: float = DEFAULT_GRADUATION_BAND_EV,
) -> GraduationReport:
    """Apply the re-search agreement gate (memo §3.4) to pending classes.

    For each ``pending_research`` class with a re-search result:
    ``|Ea_re-search − Ea_rep| <= band_eV`` (``Ea_rep_eV`` is the harvested
    representative barrier — the single member's barrier for the recovered
    singletons) → the class **graduates**: ``nu0_pair_policy = "harvested_pair"``,
    and the **harvested** pairs fire (the re-search only verifies the class
    context; the V4-validated per-pair ν0 and pair reciprocity are kept). Above
    the band → the class stays out of measured, its ``audit_reason`` is marked
    ``CONTEXT_SUSPECT``, and it goes on the review list (``review_rows``).

    Pending classes without a research row stay pending (counted). Research rows
    naming a non-pending class are ignored (counted) — graduation never touches a
    measured or quarantined class. Exclusions lift only through this documented,
    evidence-carrying gate (§8-N8 stickiness: never silently).
    """
    out: list[EventClass] = []
    review: list[dict[str, object]] = []
    n_pend = n_grad = n_susp = n_unres = n_ignored = 0
    pending_ids = {c.class_id for c in classes if c.nu0_pair_policy == NU0_POLICY_PENDING_RESEARCH}
    n_ignored = sum(1 for cid in research_ea_by_class if cid not in pending_ids)

    for c in sorted(classes, key=lambda k: k.class_id):
        if c.nu0_pair_policy != NU0_POLICY_PENDING_RESEARCH:
            out.append(replace(c))
            continue
        n_pend += 1
        if c.class_id not in research_ea_by_class:
            n_unres += 1
            out.append(replace(c))
            continue
        ea_research = float(research_ea_by_class[c.class_id])
        ea_harvested = float(c.Ea_rep_eV)
        dev = abs(ea_research - ea_harvested)
        if math.isfinite(dev) and dev <= band_eV:
            n_grad += 1
            note = (
                f"graduated: re-search Ea {ea_research:.4f} eV vs harvested "
                f"{ea_harvested:.4f} eV (|Δ|={dev:.4f} <= {band_eV:g}; memo §3.4)"
            )
            reason = f"{c.audit_reason} | {note}" if c.audit_reason else note
            out.append(
                replace(
                    c,
                    nu0_pair_policy=NU0_POLICY_HARVESTED_PAIR,
                    audit_reason=reason,
                )
            )
        else:
            n_susp += 1
            note = (
                f"CONTEXT_SUSPECT: re-search Ea {ea_research:.4f} eV vs harvested "
                f"{ea_harvested:.4f} eV (|Δ|={dev:.4f} > {band_eV:g}; memo §3.4) — "
                "stays out of measured, on the review list"
            )
            reason = f"{c.audit_reason} | {note}" if c.audit_reason else note
            review.append(
                {
                    "class_id": c.class_id,
                    "Ea_research_eV": ea_research,
                    "Ea_harvested_eV": ea_harvested,
                    "abs_dev_eV": dev,
                    "band_eV": band_eV,
                    "n_events": len(c.source_rows),
                }
            )
            out.append(replace(c, audit_reason=reason))
    return GraduationReport(
        n_pending_in=n_pend,
        n_graduated=n_grad,
        n_context_suspect=n_susp,
        n_unresolved=n_unres,
        n_ignored_nonpending=n_ignored,
        review_rows=review,
        classes=out,
    )
