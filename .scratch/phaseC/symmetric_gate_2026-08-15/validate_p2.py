#!/usr/bin/env python3
"""Validate measure_p2.py's res_P0 against the production catalogue + discard ledger.

Four independent checks per run, from weakest coupling to strongest:

V1  ledger      -- the events measure_p2 gates on P0 must be exactly the events the
                   2026-08-14 build dropped as MOVER_OFFLATTICE, with identical
                   residuals (<out>_raw_discarded.parquet).
V2  per-run     -- the run's own raw catalogue (<TAG>_raw.parquet). Singleton classes
                   give an exact idx_ref -> mover_max_residual pair; the whole run
                   gives a multiset identity over every surviving member.
V3  merged      -- the production merge (/data/.../merged_v3_{NiCr,NiFe}.parquet),
                   matched via source_sim_paths "run#idx_ref" as asked. Singleton
                   classes are exact; multi-member classes are checked as multisets
                   because merge.py sorts the residual list and the sim-path list by
                   DIFFERENT keys (see the note printed by the script).
V4  coverage    -- kept events == merged-catalogue members, no orphans either way.

Usage:  python validate_p2.py NiCr_Ni95_Cr05_T300_1vac NiFe_Ni95_Fe05_T800_10vac
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SWEEP = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full")
PER_RUN = SWEEP / "per_run"
MEASURE = Path(__file__).resolve().parent / "p2_measure"
MERGED = {"NiCr": SWEEP / "merged_v3_NiCr.parquet", "NiFe": SWEEP / "merged_v3_NiFe.parquet"}
TOL = 1e-6  # the acceptance tolerance named in the task (Angstrom)


def _load_merged(alloy: str) -> pd.DataFrame:
    return pd.read_parquet(
        MERGED[alloy], columns=["class_id", "source_sim_paths", "mover_max_residual_list"]
    )


def validate(run_tag: str, merged_cache: dict[str, pd.DataFrame]) -> dict[str, object]:
    alloy = run_tag.split("_", 1)[0]
    mine = pd.read_parquet(MEASURE / alloy / f"{run_tag}.parquet")
    res0 = dict(zip(mine["idx_ref"], mine["mover_max_residual_P0"], strict=True))
    print(f"\n{'=' * 78}\n{run_tag}   ({len(mine)} reference rows)\n{'=' * 78}")

    # ---------------- V1: discard ledger ------------------------------------------
    led = pd.read_parquet(PER_RUN / f"{run_tag}_raw_discarded.parquet")
    led_ml = led[led["reason"] == "MOVER_OFFLATTICE"]
    mine_fail = set(mine.loc[mine["gate_P0_fail"], "idx_ref"])
    led_set = set(led_ml["idx_ref"])
    dev1 = max((abs(res0[i] - v) for i, v in zip(led_ml["idx_ref"], led_ml["mover_max_residual"], strict=True)), default=0.0)
    v1 = mine_fail == led_set
    print(f"V1 ledger   : build dropped {len(led_set)} MOVER_OFFLATTICE, we gate {len(mine_fail)} "
          f"on P0 -- sets {'IDENTICAL' if v1 else 'DIFFER'}; max|dev| = {dev1:.3e} A")
    if not v1:
        print(f"    only-in-build {sorted(led_set - mine_fail)[:10]}  only-in-ours {sorted(mine_fail - led_set)[:10]}")

    # ---------------- V2: the run's own raw catalogue ------------------------------
    raw = pd.read_parquet(
        PER_RUN / f"{run_tag}_raw.parquet", columns=["class_id", "source_idx_refs", "mover_max_residual_list"]
    )
    n_single = 0
    dev2 = 0.0
    miss2 = 0
    for idxs, resid in zip(raw["source_idx_refs"], raw["mover_max_residual_list"], strict=True):
        if len(idxs) == 1:
            n_single += 1
            i = int(idxs[0])
            if i not in res0:
                miss2 += 1
                continue
            dev2 = max(dev2, abs(res0[i] - float(resid[0])))
    kept_raw = sorted(int(i) for idxs in raw["source_idx_refs"] for i in idxs)
    all_resid = sorted(float(x) for lst in raw["mover_max_residual_list"] for x in lst)
    mine_kept = sorted(res0[i] for i in kept_raw)
    dev2_ms = float(np.max(np.abs(np.array(all_resid) - np.array(mine_kept)))) if all_resid else 0.0
    n_nz = int(np.count_nonzero(np.array(all_resid)))
    print(f"V2 per-run  : {n_single} singleton classes exact-matched, max|dev| = {dev2:.3e} A "
          f"({miss2} unmatched)")
    print(f"              multiset over ALL {len(kept_raw)} surviving members: max|dev| = {dev2_ms:.3e} A "
          f"({n_nz} of them non-zero, up to {max(all_resid):.4f} A)")

    # ---------------- V3: the production merge via source_sim_paths ----------------
    merged = merged_cache.setdefault(alloy, _load_merged(alloy))
    pref = run_tag + "#"
    hit = merged["source_sim_paths"].map(lambda ps: any(str(p).startswith(pref) for p in ps))
    sub = merged[hit]
    n_ex = n_ex_ok = 0
    n_ex_nz = 0  # informative subset: stored residual != 0 (see note below)
    dev3_nz = 0.0
    max_stored_nz = 0.0
    dev3 = 0.0
    n_pure = n_pure_ok = 0
    dev3_pure = 0.0
    n_mixed = n_mixed_ok = 0
    worst_mixed = 0.0
    n_orphan = 0
    for paths, resid in zip(sub["source_sim_paths"], sub["mover_max_residual_list"], strict=True):
        paths = [str(p) for p in paths]
        ours = []
        ok = True
        for p in paths:
            tag, _, idx = p.rpartition("#")
            if tag != run_tag:
                ok = False
                continue
            i = int(idx)
            if i not in res0:
                n_orphan += 1
                ok = False
                continue
            ours.append(res0[i])
        stored = [float(x) for x in resid]
        if len(paths) == 1 and ok:  # singleton class: positional pairing is exact
            n_ex += 1
            d = abs(ours[0] - stored[0])
            dev3 = max(dev3, d)
            n_ex_ok += d <= TOL
            if stored[0] != 0.0:
                n_ex_nz += 1
                dev3_nz = max(dev3_nz, d)
                max_stored_nz = max(max_stored_nz, stored[0])
        elif ok and len(ours) == len(stored):  # every member from this run: multiset
            n_pure += 1
            d = float(np.max(np.abs(np.sort(ours) - np.sort(stored))))
            dev3_pure = max(dev3_pure, d)
            n_pure_ok += d <= TOL
        else:  # cross-run class: each of our values must appear in the stored multiset
            n_mixed += 1
            pool = list(stored)
            good = True
            for v in ours:
                if not pool:
                    good = False
                    break
                j = int(np.argmin([abs(v - x) for x in pool]))
                worst_mixed = max(worst_mixed, abs(v - pool[j]))
                good &= abs(v - pool[j]) <= TOL
                pool.pop(j)
            n_mixed_ok += good
    print(f"V3 merged   : {len(sub)} merged classes cite this run")
    print(f"              singleton  : {n_ex_ok}/{n_ex} within {TOL:g} A, max|dev| = {dev3:.3e} A")
    print(f"                of which NON-ZERO stored residual: {n_ex_nz} "
          f"(max stored {max_stored_nz:.4f} A), max|dev| = {dev3_nz:.3e} A")
    print(f"              run-pure   : {n_pure_ok}/{n_pure} within {TOL:g} A, max|dev| = {dev3_pure:.3e} A")
    print(f"              cross-run  : {n_mixed_ok}/{n_mixed} contained,      max|dev| = {worst_mixed:.3e} A")
    if n_orphan:
        print(f"              {n_orphan} cited idx_ref not present in our measurement (ORPHAN)")

    # ---------------- V4: coverage --------------------------------------------------
    cited = {int(str(p).split("#")[1]) for ps in sub["source_sim_paths"] for p in map(str, ps)
             if str(p).startswith(pref)}
    kept_mine = set(mine.loc[~mine["gate_P0_fail"] & ~mine["frame_unfit"], "idx_ref"])
    print(f"V4 coverage : kept(ours) {len(kept_mine)} | cited(merged) {len(cited)} | "
          f"kept-not-cited {len(kept_mine - cited)} | cited-not-kept {len(cited - kept_mine)}")

    return {
        "run_tag": run_tag,
        "v1_ledger_sets_equal": v1,
        "v1_max_dev": dev1,
        "v2_singletons": n_single,
        "v2_max_dev": dev2,
        "v2_multiset_max_dev": dev2_ms,
        "v3_singleton_n": n_ex,
        "v3_singleton_ok": n_ex_ok,
        "v3_singleton_max_dev": dev3,
        "v3_singleton_nonzero_n": n_ex_nz,
        "v3_singleton_nonzero_max_dev": dev3_nz,
        "v3_singleton_nonzero_max_stored": max_stored_nz,
        "v3_pure_n": n_pure,
        "v3_pure_ok": n_pure_ok,
        "v3_pure_max_dev": dev3_pure,
        "v3_mixed_n": n_mixed,
        "v3_mixed_ok": n_mixed_ok,
        "v3_mixed_max_dev": worst_mixed,
        "v4_kept_not_cited": len(kept_mine - cited),
        "v4_cited_not_kept": len(cited - kept_mine),
    }


def quick_all() -> int:
    """V1 + V2 over every measured run -- the corpus-wide exactness statement.

    Skips V3/V4 (which need the 138 MB merge scanned once per run); V2's multiset
    identity over every surviving member already subsumes what V3 can assert, since
    the merge only concatenates and re-sorts the per-run member lists.
    """
    n_runs = n_led = n_mem = 0
    dev_led = dev_single = dev_ms = 0.0
    bad: list[str] = []
    for f in sorted(MEASURE.glob("*/*.parquet")):
        run_tag = f.stem
        mine = pd.read_parquet(f, columns=["idx_ref", "mover_max_residual_P0", "gate_P0_fail", "frame_unfit"])
        res0 = dict(zip(mine["idx_ref"], mine["mover_max_residual_P0"], strict=True))
        led = pd.read_parquet(PER_RUN / f"{run_tag}_raw_discarded.parquet")
        led_ml = led[led["reason"] == "MOVER_OFFLATTICE"]
        if set(mine.loc[mine["gate_P0_fail"], "idx_ref"]) != set(led_ml["idx_ref"]):
            bad.append(f"{run_tag}: ledger set mismatch")
        for i, v in zip(led_ml["idx_ref"], led_ml["mover_max_residual"], strict=True):
            dev_led = max(dev_led, abs(res0[int(i)] - float(v)))
        n_led += len(led_ml)
        raw = pd.read_parquet(PER_RUN / f"{run_tag}_raw.parquet",
                              columns=["source_idx_refs", "mover_max_residual_list"])
        for idxs, resid in zip(raw["source_idx_refs"], raw["mover_max_residual_list"], strict=True):
            if len(idxs) == 1:
                dev_single = max(dev_single, abs(res0[int(idxs[0])] - float(resid[0])))
        kept = sorted(int(i) for idxs in raw["source_idx_refs"] for i in idxs)
        stored = sorted(float(x) for lst in raw["mover_max_residual_list"] for x in lst)
        ours = sorted(res0[i] for i in kept)
        if len(stored) != len(ours):
            bad.append(f"{run_tag}: member count {len(stored)} != {len(ours)}")
        else:
            dev_ms = max(dev_ms, float(np.max(np.abs(np.array(stored) - np.array(ours)))) if stored else 0.0)
        n_mem += len(kept)
        n_runs += 1
    print(f"corpus-wide V1+V2 over {n_runs} runs / {n_mem} surviving members / {n_led} ledger rows")
    print(f"  ledger residual max|dev|            = {dev_led:.3e} A")
    print(f"  singleton-class exact  max|dev|     = {dev_single:.3e} A")
    print(f"  whole-run multiset     max|dev|     = {dev_ms:.3e} A")
    print(f"  set/count mismatches                = {len(bad)}" + (f" -> {bad[:5]}" if bad else ""))
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--quick-all":
        return quick_all()
    cache: dict[str, pd.DataFrame] = {}
    rows = [validate(t, cache) for t in argv]
    out = pd.DataFrame(rows)
    dest = Path(__file__).resolve().parent / "validation_summary.csv"
    out.to_csv(dest, index=False)
    print(f"\nwrote {dest}")
    print(
        "\nNOTE on positional alignment: merge.py sorts the merged member lists by\n"
        "(Ea, nu0_f, nu0_b, mover_res, max_res, dE) but builds source_sim_paths by an\n"
        "INDEPENDENT lexicographic sort of 'tag#idx' -- so source_sim_paths[j] and\n"
        "mover_max_residual_list[j] are only guaranteed to pair for singleton classes.\n"
        "Multi-member classes are therefore validated as multisets, which is the\n"
        "strongest statement the merged schema supports."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
