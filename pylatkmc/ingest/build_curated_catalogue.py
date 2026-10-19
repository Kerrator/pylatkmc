"""One-pass curated-catalogue builder: classified events → pylatkmc rate table.

This is the single entry point for the pyKMC→pylatkmc bridge's offline step. It
composes the two stages that were historically separate scripts:

    classified_events.csv  +  audit_log.csv (optional, per-user)
        │
        ├─ family_assignment.assign_events  ─→  classified_events_with_families.csv
        │
        └─ build_family_rate_table.build_family_table + attach_nu0
                                            ─→  rate_lookup_table_family.csv  (+ nu0_Hz, nu0_source)

Running it as one command (one `FAMILY_REGISTRY` import, one dependency graph)
replaces the manual two-step invocation and keeps the two outputs consistent.

    python -m pylatkmc.ingest.build_curated_catalogue \
        --events       .../classified_events.csv \
        --audit        .../audit_log.csv \
        --out-events   .../classified_events_with_families.csv \
        --out-rate     .../rate_lookup_table_family.csv \
        --prefactors-bucket .../family_prefactors_bucket.csv \
        --prefactors        .../family_prefactors.csv

``--audit`` is required: pass the audit log of human verdicts written by the
PyKMC_Analysis event viewer, or ``--no-audit`` to seed every event from the
registry alone. A named audit file that does not exist is an error, never a
silent "no verdicts".

The individual `family_assignment` / `build_family_rate_table` CLIs remain for
stage-by-stage use; this orchestrator just calls their library functions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .build_family_rate_table import (
    attach_nu0,
    build_family_table,
    load_bucket_nu0,
    load_family_nu0,
)
from .families import FAMILY_REGISTRY
from .family_assignment import assign_events, build_report, load_audit

_LEC = Path("lattice_event_classification")


def build_curated_catalogue(
    events_csv: Path,
    audit_csv: Path | None,
    out_events_csv: Path,
    out_rate_csv: Path,
    prefactors_bucket_csv: Path,
    prefactors_family_csv: Path,
    report_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run assignment + rate-table build in one pass. Returns (assigned, rate_table).

    ``audit_csv=None`` applies no human verdicts.
    """
    events = pd.read_csv(events_csv)
    audit = load_audit(audit_csv) if audit_csv is not None else {}
    assigned = assign_events(events, audit)
    out_events_csv.parent.mkdir(parents=True, exist_ok=True)
    assigned.to_csv(out_events_csv, index=False)

    if report_path is not None:
        report = build_report(assigned, audit, FAMILY_REGISTRY)
        report_path.write_text(json.dumps(report, indent=2, default=str))

    tbl = build_family_table(assigned)
    tbl = attach_nu0(tbl, load_bucket_nu0(prefactors_bucket_csv), load_family_nu0(prefactors_family_csv))
    out_rate_csv.parent.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(out_rate_csv, index=False)
    return assigned, tbl


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", type=Path, default=_LEC / "classified_events.csv")
    audit_src = ap.add_mutually_exclusive_group(required=True)
    audit_src.add_argument("--audit", type=Path,
                           help="audit_log.csv of human verdicts (per-user state)")
    audit_src.add_argument("--no-audit", action="store_true",
                           help="apply no human verdicts")
    ap.add_argument("--out-events", type=Path, default=_LEC / "classified_events_with_families.csv")
    ap.add_argument("--out-rate", type=Path, default=_LEC / "rate_lookup_table_family.csv")
    ap.add_argument("--report", type=Path, default=_LEC / "family_assignment_report.json")
    ap.add_argument("--prefactors-bucket", type=Path, default=_LEC / "family_prefactors_bucket.csv")
    ap.add_argument("--prefactors", type=Path, default=_LEC / "family_prefactors.csv")
    args = ap.parse_args(argv)
    if args.audit is not None and not args.audit.is_file():
        ap.error(f"--audit file not found: {args.audit}")

    print(f"[curated-catalogue] events={args.events}  audit={args.audit or 'none'}")
    assigned, tbl = build_curated_catalogue(
        args.events, args.audit, args.out_events, args.out_rate,
        args.prefactors_bucket, args.prefactors, args.report,
    )
    n_acc = int((assigned["assignment_status"] == "accepted").sum())
    src = tbl["nu0_source"].value_counts().to_dict()
    print(f"[curated-catalogue] assigned {len(assigned)} events ({n_acc} accepted) -> {args.out_events}")
    print(f"[curated-catalogue] rate table {len(tbl)} buckets; nu0 provenance {src} -> {args.out_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
