#!/usr/bin/env python3
"""Cross-check the NiCr p2_measure parquets against the production catalogue.

For each of the 60 NiCr run tags:
  * n_rows(p2 parquet)              -- one row per reference-table row (conservation)
  * len(reference_table.pickle)     -- the authoritative row count (read-only)
  * len(<tag>_raw.parquet) + len(<tag>_raw_discarded.parquet) -- build-side total
All three must agree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from pylatkmc.ingest.reftable import read_reference_table

RUNS = Path("/home/kerr/pykmc/production_NiCrFe/runs")
CAT = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/per_run")
P2 = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15/p2_measure/NiCr")
MAN = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/manifest_NiCr.csv")


def main() -> int:
    tags = list(pd.read_csv(MAN)["run_tag"])
    rows = []
    for t in tags:
        p2 = P2 / f"{t}.parquet"
        d = pd.read_parquet(p2)
        ref = read_reference_table(RUNS / t / "reference_table.pickle")
        n_ref = len(ref)
        raw = CAT / f"{t}_raw.parquet"
        dis = CAT / f"{t}_raw_discarded.parquet"
        n_raw = len(pd.read_parquet(raw)) if raw.is_file() else -1
        n_dis = len(pd.read_parquet(dis)) if dis.is_file() else 0
        rows.append(
            dict(
                run_tag=t,
                n_p2=len(d),
                n_ref=n_ref,
                n_raw=n_raw,
                n_discarded=n_dis,
                n_build_total=n_raw + n_dis,
                match_ref=len(d) == n_ref,
                match_build=len(d) == n_raw + n_dis,
                n_P0_fail=int(d["gate_P0_fail"].sum()),
                n_P2_fail=int(d["gate_P2_fail"].sum()),
                n_sym_fail=int(d["gate_sym_fail"].sum()),
                n_frame_unfit=int(d["frame_unfit"].sum()),
                n_error=int((d["error"] != "").sum() - d["frame_unfit"].sum()),
            )
        )
    df = pd.DataFrame(rows)
    out = P2.parent / "NiCr_count_check.csv"
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print("\nTOTALS")
    print(df[["n_p2", "n_ref", "n_raw", "n_discarded", "n_build_total",
              "n_P0_fail", "n_P2_fail", "n_sym_fail", "n_frame_unfit", "n_error"]].sum().to_string())
    print(f"\nruns={len(df)}  match_ref={int(df.match_ref.sum())}  match_build={int(df.match_build.sum())}")
    print(f"wrote {out}")
    return 0 if df.match_ref.all() and df.match_build.all() else 1


if __name__ == "__main__":
    sys.exit(main())
