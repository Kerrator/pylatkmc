"""One retry round for failed classes: probe an ALTERNATE member geometry.

The graduation unit is the class, not the event: any member (run, idx_ref) is a
valid probe of the class context. The primary attempt used the member whose
harvested barrier is closest to Ea_rep_eV; for classes that ended refine_failed
/ acceptance_failed / refine_min_fallback and have >= 2 members, this retries
the NEXT-closest member in a fresh job dir (suffix __alt1). A measured retry
replaces the class's campaign_log row (the failed primary attempt is preserved
in campaign_log_primary_failures.csv); a failed retry leaves the log unchanged
(the class goes to review with both attempts on disk).

Usage: python rc_retry.py [--workers K]
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

import rc_common as C
from rc_campaign import LOG, run_one

FAIL = ("refine_failed", "acceptance_failed", "refine_min_fallback", "prep_failed",
        "min_failed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=7)
    args = ap.parse_args()

    log = pd.read_csv(LOG)
    failed = log[log["status"].isin(FAIL)]
    print(f"failed classes: {len(failed)}")

    cat = pd.read_parquet(
        C.STAMPED_PARQUET, columns=["class_id", "barriers_eV", "source_sim_paths"]
    ).set_index("class_id")
    tg = pd.read_csv(C.TARGETS_CSV).set_index("class_id")

    retries = []
    for cid in failed["class_id"]:
        row = cat.loc[cid]
        bars = np.asarray(row["barriers_eV"], float)
        if len(bars) < 2:
            print(f"  {cid[:12]}: singleton — no alternate member, stays on review")
            continue
        ea_rep = float(tg.loc[cid, "Ea_rep_eV"])
        order = np.argsort(np.abs(bars - ea_rep), kind="stable")
        j = int(order[1])  # next-closest member (order[0] was the primary attempt)
        run, idx = str(row["source_sim_paths"][j]).rsplit("#", 1)
        t = tg.loc[cid].to_dict()
        t.update(class_id=cid, search_run=run, search_idx=int(idx),
                 Ea_member_eV=float(bars[j]))
        retries.append(t)
        print(f"  {cid[:12]}: retry member {run}#{idx} "
              f"(Ea {bars[j]:.3f} vs rep {ea_rep:.3f}, {len(bars)} members)")

    if not retries:
        print("nothing to retry")
        return

    # the alternate member's canonical job dir jobs/{run}__idx{idx} can never
    # collide with the primary attempt's (a different event row), so run_one is
    # reused as-is and both attempts' state stays on disk
    rows = sorted(retries, key=lambda t: t["search_run"])
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        recs = list(ex.map(lambda t: run_one(pd.Series(t), do_nu0=False), rows))

    new = pd.DataFrame(recs)
    new.to_csv(C.CAMPAIGN_DIR / "retry_log.csv", index=False)
    print("\nretry outcomes:", dict(new["status"].value_counts()))

    log = pd.read_csv(LOG)
    won = new[new["status"].str.startswith("measured")]
    if len(won):
        log[log["class_id"].isin(won["class_id"])].to_csv(
            C.CAMPAIGN_DIR / "campaign_log_primary_failures.csv", mode="a",
            header=not (C.CAMPAIGN_DIR / "campaign_log_primary_failures.csv").exists(),
            index=False)
        log = log[~log["class_id"].isin(won["class_id"])]
        log = pd.concat([log, won], ignore_index=True).sort_values(
            "flux", ascending=False)
        log.to_csv(LOG, index=False)
    done = log[log["status"].str.startswith("measured")]
    print(f"log: {len(log)} rows | measured {len(done)} | in-band "
          f"{int(done['in_band'].sum())} | statuses: {dict(log['status'].value_counts())}")


if __name__ == "__main__":
    main()
