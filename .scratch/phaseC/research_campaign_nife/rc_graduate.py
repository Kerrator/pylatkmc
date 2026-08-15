"""NiFe Do-4 fold: campaign log -> research CSV -> ingest.cli graduate ->
re-merge with the graduated measured set -> corpus flux restatement.
+ Do-5 review list (search failures + acceptance failures + gate CONTEXT_SUSPECTs).

Adapted from research_campaign/rc_graduate.py (NiCr leg). The re-merge step is
new here: the NiCr leg's graduated parquet fed the 2026-08-14 merge via
--measured-catalogue; this script closes that loop for NiFe in one pass.
The 2026-08-14 production candidate merged_v3_NiFe.parquet is NOT overwritten —
the re-merged artifact lands in this directory (promotion is Stephen's call).

Usage: python rc_graduate.py [--dry-run]
"""
from __future__ import annotations

import argparse
import subprocess

import pandas as pd

import rc_common as C

OUT = C.CAMPAIGN_DIR
RESEARCH_CSV = OUT / "research_results.csv"
GRAD_PARQUET = OUT / "catalogue_v3_NiFe_graduated.parquet"
GRAD_REVIEW = OUT / "graduate_review.csv"
REVIEW_LIST = OUT / "review_list.csv"
REMERGED = OUT / "merged_v3_NiFe_graduated.parquet"
FLUX_OUT = OUT / "flux_restatement_post_graduation.csv"
MANIFEST = "/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/manifest_NiFe.csv"
CLASS_FLUX = OUT / "class_flux_nife.csv"
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

    # re-merge the 60 per-run catalogues with the graduated measured set
    # (mirrors run_full_campaign.sh's NiCr merge invocation, incl. tolerances)
    cmd = [VENV_PY, "-m", "pylatkmc.ingest.cli", "merge",
           "--manifest", MANIFEST,
           "--out", str(REMERGED),
           "--tol", "1e-6", "--spread-tol", "0.1",
           "--measured-catalogue", str(GRAD_PARQUET),
           "--review", str(OUT / "action_review.csv"),
           "--conditions",
           "full 60-run NiFe re-merge | CANON v3 | per-alloy split | measured set = "
           "2026-08-15 re-search graduation (decision 3.4) | 2026-08-15"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd="/home/kerr/pykmc/pylatkmc")
    (OUT / "merge_NiFe_graduated.log").write_text(proc.stdout + proc.stderr)
    print(proc.stdout[-600:] or proc.stderr[-600:])
    proc.check_returncode()

    # corpus flux restatement against the re-merged policy stamps
    cat = pd.read_parquet(REMERGED)
    pol = cat.set_index("class_id")["nu0_pair_policy"]
    flux = pd.read_csv(CLASS_FLUX)
    flux["policy_post"] = flux["class_id"].map(pol)
    flux.to_csv(FLUX_OUT, index=False)
    tot = flux["flux_firings"].sum()
    g = flux.groupby(flux["policy_post"].fillna("quarantined (unstamped)")).agg(
        classes=("class_id", "size"), flux=("flux_firings", "sum"))
    g["pct_total"] = 100 * g["flux"] / tot
    print("\ncorpus flux restatement (post-graduation):")
    print(g.sort_values("flux", ascending=False).round(2).to_string())
    meas = flux.loc[flux["policy_post"] == "harvested_pair", "flux_firings"].sum()
    nq = flux.loc[flux["policy_post"].notna(), "flux_firings"].sum()
    print(f"\nmeasured share: {100 * meas / tot:.1f}% of total corpus flux "
          f"(was 0.0%); {100 * meas / nq:.1f}% of non-quarantined flux")


if __name__ == "__main__":
    main()
