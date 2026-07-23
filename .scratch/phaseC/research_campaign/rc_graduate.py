"""Do-4 fold: campaign log -> research CSV -> ingest.cli graduate -> flux restatement
+ Do-5 review list (search failures + acceptance failures + gate CONTEXT_SUSPECTs).

Usage: python rc_graduate.py [--dry-run]
"""
from __future__ import annotations

import argparse
import subprocess

import pandas as pd

import rc_common as C

OUT = C.CAMPAIGN_DIR
RESEARCH_CSV = OUT / "research_results.csv"
GRAD_PARQUET = OUT / "catalogue_v3_graduated.parquet"
GRAD_REVIEW = OUT / "graduate_review.csv"
REVIEW_LIST = OUT / "review_list.csv"
FLUX_OUT = OUT / "flux_restatement_post_graduation.csv"
VENV_PY = "/home/kerr/pykmc/pykmc_env/bin/python"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    log = pd.read_csv(OUT / "campaign_log.csv")

    # research CSV: ONLY accepted measurements (protocol Q3/Q7); the ±0.05 gate
    # itself is applied by ingest.cli graduate (in-band -> harvested_pair fires,
    # out-of-band -> CONTEXT_SUSPECT + review).
    acc = log[log["accepted"] == True]  # noqa: E712 — NaN-safe
    acc[["class_id", "Ea_meas_eV"]].rename(columns={"Ea_meas_eV": "Ea_eV"}) \
        .to_csv(RESEARCH_CSV, index=False)
    print(f"research CSV: {len(acc)} accepted classes -> {RESEARCH_CSV.name}")

    # Do-5 review list: everything that is NOT a clean accepted measurement.
    rev = log[log["accepted"] != True].copy()  # noqa: E712
    rev["review_reason"] = rev["status"]
    rev.to_csv(REVIEW_LIST, index=False)
    print(f"review list: {len(rev)} rows -> {REVIEW_LIST.name} "
          f"({dict(rev['status'].value_counts())})")

    if args.dry_run:
        return

    cmd = [VENV_PY, "-m", "pylatkmc.ingest.cli", "graduate",
           "--in", str(C.STAMPED_PARQUET), "--research", str(RESEARCH_CSV),
           "--band", str(C.GRAD_BAND_EV), "--out", str(GRAD_PARQUET),
           "--review", str(GRAD_REVIEW)]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd="/home/kerr/pykmc/pylatkmc")
    print(proc.stdout[-1500:] or proc.stderr[-1500:])
    proc.check_returncode()

    # flux restatement: pending classes that graduated move to measured.
    cat = pd.read_parquet(GRAD_PARQUET)
    pol = cat.set_index("class_id")["nu0_pair_policy"]
    flux = pd.read_csv(C.FLUX_CSV)
    pend_lbl = [s for s in flux["status"].unique() if "pending" in s][0]
    meas_lbl = [s for s in flux["status"].unique() if s.startswith("measured")][0]

    def restate(r):
        if r["status"] != pend_lbl:
            return r["status"]
        p = pol.get(r["class_id"])
        if p == "harvested_pair":
            return meas_lbl + " [graduated]"
        if p == "CONTEXT_SUSPECT":
            return "context-suspect (review)"
        return pend_lbl

    flux["status_post"] = flux.apply(restate, axis=1)
    flux.to_csv(FLUX_OUT, index=False)
    tot = flux["flux"].sum()
    print("\nflux restatement (post-graduation):")
    g = flux.groupby("status_post").agg(classes=("class_id", "size"),
                                        flux=("flux", "sum"))
    g["pct"] = 100 * g["flux"] / tot
    print(g.sort_values("flux", ascending=False).round(2).to_string())
    meas_tot = flux.loc[flux["status_post"].str.startswith("measured"), "flux"].sum()
    print(f"\nmeasured share: {100 * meas_tot / tot:.1f}% "
          f"(was 25.9%; representable ceiling 86.7%)")


if __name__ == "__main__":
    main()
