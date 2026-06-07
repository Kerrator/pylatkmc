"""Assign every row of classified_events.csv to exactly one FCC family bucket.

Inputs:
  * classified_events.csv   — raw classifier output (56 columns)
  * audit_log.csv           — per-event verdicts from event_viewer
  * FAMILY_REGISTRY         — declarative seed + env rules (families.py)

Output: classified_events_with_families.csv with 7 new columns documenting
the per-row family + bucket + audit-aware assignment status.

The assignment order is:
  1. Audit ``ignore`` / ``unset`` / flagged-bad → excluded.
  2. Audit ``reclassify`` with ``override_family_id`` → bypass seed rules and
     assign the chosen family directly. An optional ``override_bucket_id``
     overrides the family's ``environment_rule`` output.
  3. Audit ``reclassify`` with only ``override_move_type`` → inject the
     override into a row copy and seed via the registry against the patched
     move_type.
  4. Audit ``confirm`` or no audit entry → seed predicates in priority order.
  5. No match → ``unresolved`` (collected into the report's
     ``unresolved_signatures`` for registry iteration).

The audit log is produced by ``Analysis/event_viewer/`` — the family and
bucket overrides come from the dropdowns next to the verdict radio.

Run with:
    python family_assignment.py \\
        --events      lattice_event_classification/classified_events.csv \\
        --audit       lattice_event_classification/audit_log.csv \\
        --output      lattice_event_classification/classified_events_with_families.csv \\
        --report      lattice_event_classification/family_assignment_report.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError

from .families import FAMILY_REGISTRY, FCCFamily, family_by_id, validate_registry

AUDIT_KEY_COLS = ["composition", "nvac", "temp", "idx_ref"]

AuditVerdict = Literal["confirm", "reclassify", "flag", "ignore", "unset"]


class AuditEntry(BaseModel):
    """One human-audit verdict from ``audit_log.csv`` (the event_viewer ↔
    family_assignment contract). The key (composition, nvac, temp, idx_ref)
    identifies the event; ``verdict`` + the optional overrides steer assignment.
    """

    model_config = ConfigDict(frozen=True)

    composition: str
    nvac: int
    temp: float
    idx_ref: int
    verdict: AuditVerdict
    override_move_type: str | None = None
    override_family_id: str | None = None
    override_bucket_id: str | None = None
    override_direction_id: str | None = None
    notes: str | None = None

    @property
    def key(self) -> tuple[str, int, float, int]:
        return (self.composition, self.nvac, self.temp, self.idx_ref)


def load_audit(path) -> dict:
    """Return {(composition, nvac, temp, idx_ref): audit_row_dict}.

    Each row is validated through :class:`AuditEntry`; malformed rows (missing
    key fields, unknown verdict, non-numeric nvac/temp/idx_ref) are skipped with
    a one-line warning rather than crashing. Returns an empty dict if the file is
    missing. Accepts a ``pathlib.Path`` or a plain string path.
    """
    path = Path(path)
    if not path.exists():
        return {}
    df = pd.read_csv(path, on_bad_lines="skip")
    need = set(AUDIT_KEY_COLS) | {"verdict"}
    if not need.issubset(df.columns):
        return {}
    # Coerce nvac/temp to the same dtype as classified_events.csv for keying.
    df["nvac"] = pd.to_numeric(df["nvac"], errors="coerce").astype("Int64")
    df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
    df["idx_ref"] = pd.to_numeric(df["idx_ref"], errors="coerce").astype("Int64")

    def _nz(val):
        return None if pd.isna(val) or not val else str(val)

    out: dict = {}
    n_skipped = 0
    for _, row in df.iterrows():
        if pd.isna(row["nvac"]) or pd.isna(row["temp"]) or pd.isna(row["idx_ref"]):
            n_skipped += 1
            continue
        try:
            entry = AuditEntry(
                composition=str(row["composition"]),
                nvac=int(row["nvac"]),
                temp=float(row["temp"]),
                idx_ref=int(row["idx_ref"]),
                verdict=str(row["verdict"]),
                override_move_type=_nz(row.get("override_move_type")),
                override_family_id=_nz(row.get("override_family_id")),
                override_bucket_id=_nz(row.get("override_bucket_id")),
                override_direction_id=_nz(row.get("override_direction_id")),
                notes=_nz(row.get("notes")),
            )
        except ValidationError:
            n_skipped += 1
            continue
        out[entry.key] = {
            "verdict": entry.verdict,
            "override_move_type": entry.override_move_type,
            "override_family_id": entry.override_family_id,
            "override_bucket_id": entry.override_bucket_id,
            "override_direction_id": entry.override_direction_id,
            "notes": entry.notes,
        }
    if n_skipped:
        print(f"[family_assignment] load_audit: skipped {n_skipped} invalid audit row(s)")
    return out


def _assign_one(row: pd.Series,
                audit: dict,
                registry: list[FCCFamily]) -> dict:
    """Return the 7 new columns for a single row."""
    key = (str(row["composition"]), int(row["nvac"]),
           float(row["temp"]), int(row["idx_ref"]))
    av = audit.get(key)
    if av:
        av = {
            "verdict": av.get("verdict"),
            "override_move_type": av.get("override_move_type"),
            "override_family_id": av.get("override_family_id"),
            "override_bucket_id": av.get("override_bucket_id"),
            "override_direction_id": av.get("override_direction_id"),
            "notes": av.get("notes"),
        }

    # 1. Audit-driven exclusion. "unset" = audited but not decided → exclude
    #    defensively so the curated table never silently fits over rows that
    #    a human flagged for review.
    if av and av["verdict"] in ("ignore", "unset", "bad"):
        return {
            "family_id": "",
            "family_name": "",
            "family_bucket_id": "",
            "family_bucket_name": "",
            "assignment_status": "excluded",
            "assignment_note": f"audit:{av['verdict']}",
            "audit_excluded": True,
        }

    # 2. Audit-driven DIRECT family override. When the user picked a family in
    #    the event_viewer, trust it: skip seed-rule matching and assign the
    #    chosen family_id. An override_bucket_id is used verbatim when present;
    #    otherwise the family's environment_rule derives the bucket from the
    #    (possibly patched) row.
    if av and av["verdict"] == "reclassify" and av["override_family_id"]:
        fam = family_by_id(av["override_family_id"], registry)
        if fam is not None:
            working = row
            if av["override_move_type"]:
                working = row.copy()
                working["move_type"] = av["override_move_type"]
            bucket_id = (av["override_bucket_id"]
                         or fam.environment_rule(working))
            return {
                "family_id":          fam.family_id,
                "family_name":        fam.family_name,
                "family_bucket_id":   bucket_id,
                "family_bucket_name": bucket_id,
                "assignment_status":  "accepted",
                "assignment_note": f"audit:override_family({fam.family_id})"
                                    + (f"|bucket({av['override_bucket_id']})"
                                       if av["override_bucket_id"] else ""),
                "audit_excluded":     False,
            }

    # 3. Audit-driven reclassification via move_type. The override_move_type
    #    flows back through the base classifier's outputs — we patch the
    #    move_type on a row copy and re-derive motif_family_3d via the
    #    existing mapping; for fields the classifier would have recomputed
    #    (direction_family_3d, site_class_3d, n_moved) we assume the hop
    #    geometry is the same so those stay. Callers can always re-run the
    #    full classifier if they need the override to propagate further.
    #
    #    A separate direction override (override_direction_id) patches the
    #    ``direction_family_3d`` column on the working row so seed rules that
    #    depend on it (several families do — see families.py) re-evaluate
    #    against the human-corrected direction. This is additive with the
    #    move_type override.
    note_prefix = ""
    working = row
    if av and av["verdict"] == "reclassify" and av["override_move_type"]:
        working = row.copy()
        working["move_type"] = av["override_move_type"]
        note_prefix = f"audit:reclassify({av['override_move_type']})|"
    if av and av["verdict"] == "reclassify" and av["override_direction_id"]:
        if working is row:
            working = row.copy()
        working["direction_family_3d"] = av["override_direction_id"]
        note_prefix += f"direction({av['override_direction_id']})|"

    # 4. Seed predicates in priority order. First match wins.
    for f in sorted(registry, key=lambda x: x.priority):
        if f.seed_rule(working):
            bucket_id = f.environment_rule(working)
            return {
                "family_id":        f.family_id,
                "family_name":      f.family_name,
                "family_bucket_id": bucket_id,
                "family_bucket_name": bucket_id,  # same for now; registry can
                                                  # later carry a bucket namer
                "assignment_status": "accepted",
                "assignment_note":   note_prefix + f"seed:{f.family_id}",
                "audit_excluded":    False,
            }

    # 5. No seed match — unresolved.
    return {
        "family_id": "",
        "family_name": "",
        "family_bucket_id": "",
        "family_bucket_name": "",
        "assignment_status": "unresolved",
        "assignment_note": "no_seed_match",
        "audit_excluded": False,
    }


def assign_events(events_df: pd.DataFrame,
                  audit: dict,
                  registry: list[FCCFamily] | None = None,
                  ) -> pd.DataFrame:
    registry = list(registry if registry is not None else FAMILY_REGISTRY)
    validate_registry(events_df.head(500), registry)  # fast overlap check
    new_cols = events_df.apply(
        lambda r: _assign_one(r, audit, registry), axis=1, result_type="expand",
    )
    out = pd.concat([events_df, new_cols], axis=1)
    return out


def build_report(assigned_df: pd.DataFrame,
                 audit: dict,
                 registry: list[FCCFamily]) -> dict:
    n_total = len(assigned_df)
    n_accepted   = int((assigned_df["assignment_status"] == "accepted").sum())
    n_excluded   = int((assigned_df["assignment_status"] == "excluded").sum())
    n_unresolved = int((assigned_df["assignment_status"] == "unresolved").sum())

    # Audit verdict distribution (from rows that were actually audited).
    verdict_counts = Counter(av["verdict"] for av in audit.values())

    # Per-family event counts + bucket breakdowns.
    per_family = []
    for f in registry:
        sub = assigned_df[(assigned_df["family_id"] == f.family_id)
                          & (assigned_df["assignment_status"] == "accepted")]
        bucket_counts = dict(sub["family_bucket_id"].value_counts().head(20))
        per_family.append({
            "family_id":    f.family_id,
            "family_name":  f.family_name,
            "fit_barrier":  f.fit_barrier,
            "n_events":     int(len(sub)),
            "bucket_counts": bucket_counts,
        })

    # Unresolved-signature diagnosis: group unresolved rows by the existing
    # classifier-label tuple to reveal what the registry is missing.
    unresolved = assigned_df[assigned_df["assignment_status"] == "unresolved"]
    sig_cols = ["move_type", "motif_family_3d",
                "direction_family_3d", "site_class_3d"]
    if len(unresolved) > 0:
        sig = (unresolved.groupby(sig_cols).size()
                         .sort_values(ascending=False)
                         .head(25).reset_index(name="n_events"))
        unresolved_signatures = sig.to_dict(orient="records")
    else:
        unresolved_signatures = []

    return {
        "n_total_events": n_total,
        "n_accepted": n_accepted,
        "n_excluded_audit": n_excluded,
        "n_unresolved": n_unresolved,
        "audit_verdict_counts": dict(verdict_counts),
        "per_family": per_family,
        "unresolved_signatures": unresolved_signatures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", type=Path,
                    default=Path("lattice_event_classification/classified_events.csv"))
    ap.add_argument("--audit",  type=Path,
                    default=Path("lattice_event_classification/audit_log.csv"))
    ap.add_argument("--output", type=Path,
                    default=Path("lattice_event_classification/classified_events_with_families.csv"))
    ap.add_argument("--report", type=Path,
                    default=Path("lattice_event_classification/family_assignment_report.json"))
    args = ap.parse_args()

    print(f"[family_assignment] reading {args.events}")
    df = pd.read_csv(args.events)
    print(f"  {len(df)} rows")

    print(f"[family_assignment] reading {args.audit}")
    audit = load_audit(args.audit)
    print(f"  {len(audit)} audit entries")

    print("[family_assignment] assigning families ...")
    out = assign_events(df, audit)

    print(f"[family_assignment] writing {args.output}")
    out.to_csv(args.output, index=False)

    report = build_report(out, audit, FAMILY_REGISTRY)
    print(f"[family_assignment] writing {args.report}")
    args.report.write_text(json.dumps(report, indent=2, default=str))

    print("\n=== summary ===")
    print(f"  accepted:   {report['n_accepted']:6d} / {report['n_total_events']} "
          f"({report['n_accepted']/report['n_total_events']*100:.1f}%)")
    print(f"  excluded:   {report['n_excluded_audit']:6d}")
    print(f"  unresolved: {report['n_unresolved']:6d} "
          f"({report['n_unresolved']/report['n_total_events']*100:.2f}%)")
    print("  per-family (populated only):")
    for pf in report["per_family"]:
        if pf["n_events"] > 0:
            print(f"    {pf['family_id']:45s} {pf['n_events']:6d}")
    if report["unresolved_signatures"]:
        print("  unresolved signatures (top):")
        for sig in report["unresolved_signatures"][:5]:
            print(f"    {sig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
