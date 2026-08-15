#!/usr/bin/env python3
"""Post-run verification of the NiFe p2_measure leg (read-only)."""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import pandas as pd

from pylatkmc.ingest.reftable import read_reference_table

RUNS = Path("/home/kerr/pykmc/production_NiCrFe/runs")
OUT = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15/p2_measure/NiFe")
CAT = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full")
MAN = CAT / "manifest_NiFe.csv"


def check(tag: str) -> dict:
    n_ref = len(read_reference_table(RUNS / tag / "reference_table.pickle"))
    p = OUT / f"{tag}.parquet"
    d = pd.read_parquet(p)
    return {
        "run_tag": tag,
        "exists": p.is_file(),
        "bytes": p.stat().st_size,
        "n_ref": n_ref,
        "n_parquet": len(d),
        "match": n_ref == len(d),
        "n_idx_ref_unique": int(d["idx_ref"].nunique()),
        "n_nan_res_P0": int(d["mover_max_residual_P0"].isna().sum()),
        "n_nan_res_P2": int(d["mover_max_residual_P2"].isna().sum()),
        "n_err": int((d["error"] != "").sum()),
    }


if __name__ == "__main__":
    tags = sorted(pd.read_csv(MAN)["run_tag"].tolist())
    with mp.get_context("fork").Pool(4) as pool:
        rows = pool.map(check, tags)
    df = pd.DataFrame(rows)
    df.to_csv(OUT.parent / "NiFe_verify.csv", index=False)
    print(f"manifest run_tags: {len(tags)}   parquets found: {int(df['exists'].sum())}")
    print(f"row-count match  : {int(df['match'].sum())}/{len(df)}")
    print(f"total reftable rows {int(df['n_ref'].sum())}  parquet rows {int(df['n_parquet'].sum())}")
    print(f"NaN res_P0 {int(df['n_nan_res_P0'].sum())}  NaN res_P2 {int(df['n_nan_res_P2'].sum())}  errors {int(df['n_err'].sum())}")
    bad = df[~df["match"]]
    if len(bad):
        print("MISMATCHES:\n", bad.to_string())

    # conservation vs the production catalogue: kept (qc parquet members) + discarded ledger
    man = pd.read_csv(MAN)
    tot_kept = 0
    tot_disc = 0
    miss = []
    for _, r in man.iterrows():
        qp = Path(r["parquet"])
        if not qp.is_file():
            miss.append(str(qp))
            continue
        q = pd.read_parquet(qp)
        col = "n_members" if "n_members" in q.columns else None
        if col:
            tot_kept += int(q[col].sum())
        elif "barriers_eV" in q.columns:
            tot_kept += int(sum(len(x) for x in q["barriers_eV"]))
        dp = qp.with_name(qp.name.replace("_qc.parquet", "_raw_discarded.parquet"))
        if dp.is_file():
            tot_disc += len(pd.read_parquet(dp))
    print(f"catalogue kept members {tot_kept}  discarded ledger rows {tot_disc}  sum {tot_kept + tot_disc}")
    if miss:
        print("missing catalogue parquets:", miss[:5])
