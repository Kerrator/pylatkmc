"""NiFe campaign orchestrator: prep -> driver subprocess -> acceptance -> log.

Adapted from research_campaign/rc_campaign.py (NiCr leg). Differences:
  - targets are merged classes with a per-class search member (run_tag, idx_ref)
    from rc_common.load_targets(); job dirs and the campaign log are keyed by
    class_id (idx_ref is run-local and NOT unique across the 60-run corpus).
  - reference tables are loaded per run (lru-cached); execution order is grouped
    by search_run for cache locality (the log stays flux-sorted).

Usage:
  python rc_campaign.py --top N               # top-N by corpus flux
  python rc_campaign.py --class-id CID ...    # explicit classes
  python rc_campaign.py --all                 # every pending class (don't)
  Options: --nu0 (diagnostic Vineyard), --workers K (default 14; box budget
  <=21 of 24 cores — each driver is one serial LAMMPS process)

Each driver runs in its own workdir with isolated TMPDIR (OMPI gotcha).
Appends/updates campaign_log.csv keyed by class_id.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import rc_accept
import rc_common as C
import rc_prep

LOG = C.CAMPAIGN_DIR / "campaign_log.csv"
VENV_PY = "/home/kerr/pykmc/pykmc_env/bin/python"


def run_phases(wd: Path, do_nu0: bool) -> dict:
    """Drive min -> refine ladder -> (nu0) for a prepared job dir. Resumable."""
    rec: dict = {}

    def driver(*extra):
        env = dict(__import__("os").environ)
        env["PYTHONPATH"] = C.ARTN_INTERFACE
        return subprocess.run(
            [VENV_PY, str(C.CAMPAIGN_DIR / "rc_driver.py"), str(wd), *extra],
            capture_output=True, text=True, timeout=3600, env=env)

    if not (wd / "mins.npz").exists():
        proc = driver("--phase", "min")
        if proc.returncode != 0 or not (wd / "mins.npz").exists():
            rec["status"] = "min_failed"
            rec["error"] = (proc.stderr or proc.stdout)[-400:]
            return rec

    ok = (wd / "sadstate.npz").exists()
    ladder = []
    if not ok:
        for rung in (1, 2, 3):
            for attempt in range(5):
                zseed = 1000 * rung + attempt
                proc = driver("--phase", "refine", "--rung", str(rung),
                              "--zseed", str(zseed))
                jf = wd / f"refine_r{rung}_z{zseed}.json"
                if jf.exists():
                    att = json.loads(jf.read_text())
                else:
                    att = {"rung": rung, "zseed": zseed, "ok": False,
                           "crash": (proc.stderr or proc.stdout)[-200:]}
                ladder.append(att)
                if att.get("ok"):
                    ok = True
                    break
            if ok:
                break
        (wd / "ladder.json").write_text(json.dumps(ladder, indent=1))
    elif (wd / "ladder.json").exists():
        ladder = json.loads((wd / "ladder.json").read_text())
    rec["refine_ok"] = ok
    rec["ladder_len"] = len(ladder)
    if not ok:
        rec["status"] = "refine_failed"
        rec["error"] = json.dumps(ladder[-1:])[-400:]
        return rec

    mins = np.load(wd / "mins.npz")
    sad = np.load(wd / "sadstate.npz")
    rec["Ea_meas_eV"] = float(sad["E_sad"]) - float(mins["E_min1"])
    rec["dE_meas_eV"] = float(mins["E_min2"]) - float(mins["E_min1"])
    if do_nu0:
        if not (wd / "nu0.json").exists():
            driver("--phase", "nu0")
        if (wd / "nu0.json").exists():
            nu = json.loads((wd / "nu0.json").read_text())
            rec["nu0_diag_hz"] = nu.get("nu0_diag_hz")
            rec["n_imag_sad"] = nu.get("n_imag_sad")
    rec["_states"] = {"R1": mins["R1"], "Rsad": sad["Rsad"], "R2": mins["R2"]}
    return rec


def run_one(target, do_nu0: bool) -> dict:
    run_tag = str(target["search_run"])
    idx = int(target["search_idx"])
    rec: dict = {
        "class_id": target["class_id"],
        "search_run": run_tag,
        "idx_ref": idx,
        "flux": float(target["flux_firings"]) if pd.notna(target["flux_firings"]) else 0.0,
        "Ea_rep_eV": float(target["Ea_rep_eV"]),
        "Ea_member_eV": float(target["Ea_member_eV"]),
        "archetype": target.get("archetype", ""),
        "status": "prep_failed",
    }
    wd = C.CAMPAIGN_DIR / "jobs" / f"{run_tag}__idx{idx}"
    wd.mkdir(parents=True, exist_ok=True)
    ref_df = C.load_ref_table(run_tag)
    row = ref_df[ref_df["idx_ref"] == idx].iloc[0]
    try:
        cl = rc_prep.build_padded_cluster(row)
    except Exception as e:  # noqa: BLE001 — recorded, never silently dropped
        rec["error"] = f"prep: {e}"
        return rec
    rec.update(n_pad=cl["n_pad"], n_bad_snap=len(cl["bad_snap"]),
               pad_unresolved_top=cl["surface"]["pad_unresolved_top"],
               pad_unresolved_bot=cl["surface"]["pad_unresolved_bot"])
    rc_prep.write_lammps_data(wd / "data.lmp", cl)
    np.savez_compressed(wd / "arrays.npz", init=cl["init"], sad=cl["sad"],
                        fin=cl["fin"], n_all=len(cl["init"]),
                        n_real=cl["n_real"], mover=cl["mover"])

    ph = run_phases(wd, do_nu0)
    states = ph.pop("_states", None)
    rec.update(ph)
    if states is None:
        return rec
    a = rc_accept.assess(row, cl["n_real"], states, target["class_id"])
    rec.update({k: a[k] for k in (
        "mover_ok", "dra_ok", "dra_stored", "dra_meas", "relax_shift_max",
        "class_id_stored_matches", "class_id_ok", "class_id_after",
        "saddle_token_flicker", "max_residual_before", "max_residual_after",
        "accepted")})
    rec["dEa_eV"] = rec["Ea_meas_eV"] - rec["Ea_rep_eV"]
    rec["in_band"] = abs(rec["dEa_eV"]) <= C.GRAD_BAND_EV
    # minimum-fallback guard: pARTn "converged" but onto the basin, not a saddle
    if rec["Ea_meas_eV"] < 0.05 or rec["dra_meas"] < 0.5 * rec["dra_stored"]:
        rec["status"] = "refine_min_fallback"
        # rc_graduate selects on accepted==True, so the guard must also clear
        # accepted or a fallback that passed the geometric gates would leak
        # into the research CSV (2026-08-15 audit finding; never fired to date)
        rec["accepted"] = False
    elif not rec["accepted"]:
        rec["status"] = "acceptance_failed"
    else:
        rec["status"] = "measured_in_band" if rec["in_band"] else "measured_out_of_band"
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class-id", nargs="*")
    ap.add_argument("--top", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--nu0", action="store_true")
    ap.add_argument("--workers", type=int, default=14)
    args = ap.parse_args()

    targets = C.load_targets()
    if args.class_id:
        sel = targets[targets["class_id"].isin(args.class_id)]
    elif args.top:
        sel = targets.head(args.top)
    elif args.all:
        sel = targets
    else:
        sys.exit("choose --class-id/--top/--all")

    # execute grouped by run (pickle-cache locality); log stays flux-sorted
    sel = sel.sort_values(["search_run", "flux_firings"], ascending=[True, False])
    rows = [t for _, t in sel.iterrows()]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        recs = list(ex.map(lambda t: run_one(t, args.nu0), rows))

    log = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame()
    new = pd.DataFrame(recs)
    if len(log):
        log = log[~log["class_id"].isin(new["class_id"])]
    log = pd.concat([log, new], ignore_index=True).sort_values("flux", ascending=False)
    log.to_csv(LOG, index=False)
    done = log[log["status"].str.startswith("measured")]
    print(f"log: {len(log)} rows | measured {len(done)} | in-band "
          f"{int(done['in_band'].sum())} | statuses: {dict(log['status'].value_counts())}")


if __name__ == "__main__":
    main()
