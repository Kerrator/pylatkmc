"""NiFe full-state control arm (handoff slice 2, 2026-08-15).

Adapted from research_campaign/rc_fullstate.py (NiCr leg, single run): registers
each GRADUATED class's searched cluster into ITS OWN production run's trajectory
frame at the harvest step (pykmc.events first-seen central atom + exact per-atom
matching), re-searches in the full 9,674-9,679-atom system with ALL atoms free,
and logs Ea_full alongside the padded-cluster arm for the
|Ea_cluster - Ea_full| bias measurement.

Differences from the July arm: per-run frames/events (natoms varies with the
vacancy count; cell identical across the 60 runs — rc_common.CELL), targets come
from campaign_log.csv restricted to measured_in_band graduated classes.

Usage: python rc_fullstate.py [--n-tail 5] [--workers 7] [--class-id CID ...]
       (default selection: top-10 corpus flux + n-tail stratified tail)
"""
from __future__ import annotations

import re
from functools import lru_cache
from itertools import islice
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

import rc_accept
import rc_common as C
import rc_prep
from rc_campaign import run_phases

CENTER = np.array([C.CELL[0, 0] / 2, C.CELL[1, 1] / 2, C.CELL[2, 2] / 2])
BOX = C.CELL.diagonal()
LOG = C.CAMPAIGN_DIR / "fullstate_log.csv"
MATCH_TOL = 0.2


@lru_cache(maxsize=64)
def frame_natoms(run_tag: str) -> int:
    with open(C.RUNS_ROOT / run_tag / "trajkmc.xyz") as f:
        return int(f.readline().split()[0])


@lru_cache(maxsize=64)
def parse_events_first_seen(run_tag: str) -> pd.DataFrame:
    """idx_ref -> (first step listed, central atom) from the run's pykmc.events."""
    rows = []
    step = None
    with open(C.RUNS_ROOT / run_tag / "pykmc.events") as f:
        for line in f:
            m = re.match(r"#Step:\s*(\d+)", line)
            if m:
                step = int(m.group(1))
                continue
            if step is None or not line.strip() or line.lstrip().startswith(("#", "=", "Types")):
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                rows.append((int(parts[3]), step, int(parts[2])))
    df = pd.DataFrame(rows, columns=["idx_ref", "step", "central_atom"])
    return df.sort_values("step").groupby("idx_ref").first().reset_index()


def read_frame(run_tag: str, k: int):
    frame_lines = frame_natoms(run_tag) + 2
    with open(C.RUNS_ROOT / run_tag / "trajkmc.xyz") as f:
        chunk = list(islice(f, k * frame_lines, (k + 1) * frame_lines))
    if len(chunk) < frame_lines:
        return None, None
    spec, pos = [], []
    for line in chunk[2:]:
        p = line.split()
        spec.append(p[0])
        pos.append([float(p[1]), float(p[2]), float(p[3])])
    return np.array(spec), np.array(pos)


def register(row, X, spec, central: int):
    """Find translation t with cluster == X + t on all cluster atoms; exact matching."""
    P0 = np.asarray(row["initial_positions"], float)
    types = np.array([str(t) for t in row["initial_types"]])
    Xw = np.mod(X, BOX)
    tree = cKDTree(Xw, boxsize=BOX)
    best = None
    for i in range(len(P0)):
        t = P0[i] - X[central]
        pred = np.mod(P0 - t, BOX)
        dist, idx = tree.query(pred)
        if dist.max() < MATCH_TOL and len(set(idx)) == len(idx) \
                and (spec[idx] == types).all():
            cand = {"t": t, "match": idx, "max_dev": float(dist.max())}
            if best is None or cand["max_dev"] < best["max_dev"]:
                best = cand
    return best


def build_job(wd: Path, row, X, spec, reg):
    Psad = np.asarray(row["saddle_positions"], float)
    Pfin = np.asarray(row["final_positions"], float)
    t, match = reg["t"], reg["match"]
    n = len(X)
    init = X.copy()
    sad = X.copy()
    sad[match] = Psad - t
    fin = X.copy()
    fin[match] = Pfin - t
    mover_global = int(match[int(row["move_atom_idx"])])
    types = [str(s) for s in spec]
    wd.mkdir(parents=True, exist_ok=True)
    cl = {"init": init, "types": types}
    rc_prep.write_lammps_data(wd / "data.lmp", cl)
    np.savez_compressed(wd / "arrays.npz", init=init, sad=sad, fin=fin,
                        n_all=n, n_real=n, mover=mover_global)
    return mover_global


def run_target(target) -> dict:
    run_tag = str(target["search_run"])
    idx = int(target["idx_ref"])
    rec = {"class_id": target["class_id"], "search_run": run_tag, "idx_ref": idx,
           "flux": float(target["flux"]) if pd.notna(target["flux"]) else 0.0,
           "Ea_rep_eV": float(target["Ea_rep_eV"]),
           "Ea_cluster_eV": float(target["Ea_meas_eV"]),
           "status": "no_events_record"}
    ref_df = C.load_ref_table(run_tag)
    row = ref_df[ref_df["idx_ref"] == idx].iloc[0]
    first_seen = parse_events_first_seen(run_tag)
    fs = first_seen[first_seen["idx_ref"] == idx]
    if not len(fs):
        return rec
    step, central = int(fs["step"].iloc[0]), int(fs["central_atom"].iloc[0])
    rec.update(step=step, central_atom=central, status="register_failed")

    wd = C.CAMPAIGN_DIR / "jobs_fullstate" / f"{run_tag}__idx{idx}"
    reg = None
    for k in (step - 1, step, max(step - 2, 0)):
        spec, X = read_frame(run_tag, k)
        if spec is None:
            continue
        reg = register(row, X, spec, central)
        if reg is not None:
            rec["frame"] = k
            rec["reg_max_dev"] = reg["max_dev"]
            break
    if reg is None:
        return rec

    mover_global = build_job(wd, row, X, spec, reg)
    ph = run_phases(wd, do_nu0=False)
    states_full = ph.pop("_states", None)
    rec.update({k: v for k, v in ph.items()
                if k in ("status", "error", "refine_ok", "ladder_len",
                         "Ea_meas_eV", "dE_meas_eV")})
    if states_full is None:
        return rec

    # acceptance on the extracted cluster (back-translated to cluster coords).
    # Min-image each atom against the stored initial cluster: registration
    # matched WRAPPED images (np.mod), so a bare "+ t" teleports any atom whose
    # cluster straddles the periodic boundary by a full box length (seen as
    # relax_shift_max == Lx on the smoke target) and corrupts the re-projection.
    t, match = reg["t"], reg["match"]
    P0 = np.asarray(row["initial_positions"], float)

    def back_translate(s):
        s = np.asarray(s, float)[match] + t
        d = s - P0
        d -= BOX * np.round(d / BOX)
        return P0 + d

    states = {n: back_translate(states_full[n]) for n in ("R1", "Rsad", "R2")}
    a = rc_accept.assess(row, len(match), states, target["class_id"])
    rec.update({k: a[k] for k in (
        "mover_ok", "dra_ok", "dra_stored", "dra_meas", "relax_shift_max",
        "class_id_ok", "class_id_after", "saddle_token_flicker",
        "max_residual_before", "max_residual_after", "accepted")})
    rec["mover_global"] = mover_global
    rec["dEa_eV"] = rec["Ea_meas_eV"] - rec["Ea_rep_eV"]
    rec["dEa_vs_cluster_eV"] = rec["Ea_meas_eV"] - rec["Ea_cluster_eV"]
    rec["in_band"] = abs(rec["dEa_eV"]) <= C.GRAD_BAND_EV
    rec["status"] = ("measured_in_band" if rec["in_band"] else
                     "measured_out_of_band") if rec["accepted"] else "acceptance_failed"
    return rec


def load_graduated() -> pd.DataFrame:
    log = pd.read_csv(C.CAMPAIGN_DIR / "campaign_log.csv")
    grad = pd.read_csv(C.CAMPAIGN_DIR / "research_results.csv")
    m = log[log["class_id"].isin(grad["class_id"])
            & (log["status"] == "measured_in_band")]
    return m.sort_values("flux", ascending=False).reset_index(drop=True)


def main() -> None:
    import argparse
    from concurrent.futures import ThreadPoolExecutor
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-tail", type=int, default=5)
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--class-id", nargs="*")
    args = ap.parse_args()

    targets = load_graduated()
    if args.class_id:
        sel = targets[targets["class_id"].isin(args.class_id)]
    else:
        top = targets.head(10)
        tail_pool = targets.iloc[10:].reset_index(drop=True)
        picks = np.linspace(0, len(tail_pool) - 1, args.n_tail).astype(int)
        sel = pd.concat([top, tail_pool.iloc[picks]])

    rows = [t for _, t in sel.iterrows()]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        recs = list(ex.map(run_target, rows))

    log = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame()
    new = pd.DataFrame(recs)
    if len(log):
        log = log[~log["class_id"].isin(new["class_id"])]
    log = pd.concat([log, new], ignore_index=True).sort_values("flux", ascending=False)
    log.to_csv(LOG, index=False)
    cols = ["search_run", "idx_ref", "status", "Ea_rep_eV"] + \
        [c for c in ("Ea_cluster_eV", "Ea_meas_eV", "dEa_eV", "dEa_vs_cluster_eV",
                     "reg_max_dev") if c in log]
    print(log[cols].to_string())


if __name__ == "__main__":
    main()
