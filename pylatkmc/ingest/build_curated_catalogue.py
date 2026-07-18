"""One-pass curated-catalogue builder: classified events → pylatkmc rate table.

This is the single entry point for the pyKMC→pylatkmc bridge's offline step. It
composes the two stages that were historically separate scripts:

    classified_events.csv  +  audit_log.csv
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

The individual `family_assignment` / `build_family_rate_table` CLIs remain for
stage-by-stage use; this orchestrator just calls their library functions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .build_family_rate_table import (
    DEFAULT_T_REF_K,
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
    audit_csv: Path,
    out_events_csv: Path,
    out_rate_csv: Path,
    prefactors_bucket_csv: Path,
    prefactors_family_csv: Path,
    report_path: Path | None = None,
    *,
    t_ref_K: float = DEFAULT_T_REF_K,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run assignment + rate-table build in one pass. Returns (assigned, rate_table).

    ``t_ref_K`` (default 500 K) is the reference temperature stamped into the
    rate-space columns (``k_rate_mean_psinv``, ``Ea_rep_eV``, ``nu0_geo_psinv``,
    ``T_ref_K``). The nu0 maps are loaded once and threaded into both the rate-space
    aggregation and the ``nu0_Hz`` column so they stay consistent.
    """
    events = pd.read_csv(events_csv)
    audit = load_audit(audit_csv)
    assigned = assign_events(events, audit)
    out_events_csv.parent.mkdir(parents=True, exist_ok=True)
    assigned.to_csv(out_events_csv, index=False)

    if report_path is not None:
        report = build_report(assigned, audit, FAMILY_REGISTRY)
        report_path.write_text(json.dumps(report, indent=2, default=str))

    bucket_nu0 = load_bucket_nu0(prefactors_bucket_csv)
    family_nu0 = load_family_nu0(prefactors_family_csv)
    tbl = build_family_table(assigned, t_ref_K=t_ref_K, bucket_nu0=bucket_nu0, family_nu0=family_nu0)
    tbl = attach_nu0(tbl, bucket_nu0, family_nu0)
    out_rate_csv.parent.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(out_rate_csv, index=False)
    return assigned, tbl


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", type=Path, default=_LEC / "classified_events.csv")
    ap.add_argument("--audit", type=Path, default=_LEC / "audit_log.csv")
    ap.add_argument("--out-events", type=Path, default=_LEC / "classified_events_with_families.csv")
    ap.add_argument("--out-rate", type=Path, default=_LEC / "rate_lookup_table_family.csv")
    ap.add_argument("--report", type=Path, default=_LEC / "family_assignment_report.json")
    ap.add_argument("--prefactors-bucket", type=Path, default=_LEC / "family_prefactors_bucket.csv")
    ap.add_argument("--prefactors", type=Path, default=_LEC / "family_prefactors.csv")
    ap.add_argument("--t-ref", type=float, default=DEFAULT_T_REF_K,
                    help="reference temperature (K) for the rate-space columns (campaign: 500)")
    args = ap.parse_args(argv)

    print(f"[curated-catalogue] events={args.events}  audit={args.audit}  T_ref={args.t_ref} K")
    assigned, tbl = build_curated_catalogue(
        args.events, args.audit, args.out_events, args.out_rate,
        args.prefactors_bucket, args.prefactors, args.report,
        t_ref_K=args.t_ref,
    )
    n_acc = int((assigned["assignment_status"] == "accepted").sum())
    src = tbl["nu0_source"].value_counts().to_dict()
    print(f"[curated-catalogue] assigned {len(assigned)} events ({n_acc} accepted) -> {args.out_events}")
    print(f"[curated-catalogue] rate table {len(tbl)} buckets; nu0 provenance {src} -> {args.out_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
