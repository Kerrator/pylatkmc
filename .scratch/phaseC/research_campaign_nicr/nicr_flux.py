"""NiCr corpus flux ranking — reachability-corrected, per merged class.

Direct adaptation of the validated NiFe precedent
(`.scratch/phaseC/research_campaign_nife/nife_flux.py`, whose per-run totals were
audited to 1e-11 against an independent parser).  Same measure, same framing:

    per-event expected firings = sum over applicable steps of k * dt, where dt is
    the residence time of the state listed at '#Step: N' (row N of pykmc.out),

aggregated per idx_ref, then mapped onto merged classes via `source_sim_paths`
entries of the form 'run_tag#idx_ref' and summed corpus-wide over the 60 NiCr runs
named in `manifest_NiCr.csv`.

Differences vs the NiFe script (all deliberate):

1.  Catalogue = `/data/.../merged_v3_NiCr.parquet` directly — the production NiCr
    merge already carries `nu0_pair_policy` (32 `harvested_pair`, 59,448
    `pending_research`, 10,699 quarantined/NaN), so there is no separate
    `_stamped` file to build.
2.  APPEND-CONTAMINATION POLICY (see `KEEP_LAST_SEGMENT` below).
3.  Per-class aggregation goes through plain dicts instead of a DataFrame
    `.get` per (class, column) — 70,179 classes is 3.5x the NiFe corpus.

Read-only w.r.t. both /data and production_NiCrFe/runs.  Outputs land in this
directory:

    flux_by_ref_nicr.csv    one row per (run_tag, idx_ref)
    class_flux_nicr.csv     all 70,179 merged classes + corpus flux + policy
    targets_nicr.csv        pending_research classes, flux-desc, with the
                            primary-donor (run, idx_ref) a search job would use

Run from the pylatkmc repo root (or any dir that is not the meta-root) under
pykmc_env:  `python .scratch/phaseC/research_campaign_nicr/nicr_flux.py`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

CAMP = Path(__file__).parent
RUNS = Path("/home/kerr/pykmc/production_NiCrFe/runs")
D = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full")
MANIFEST = D / "manifest_NiCr.csv"
CATALOGUE = D / "merged_v3_NiCr.parquet"

STEP_RE = re.compile(r"^#Step:\s*(\d+)")
SEL_RE = re.compile(r"Selected=(\d+)")
SPECIES = {"Ni", "Fe", "Cr"}

# ---------------------------------------------------------------------------
# Append-contamination policy
# ---------------------------------------------------------------------------
#
# `NiCr_Ni95_Cr05_T300_1vac` has an append-contaminated `pykmc.out` /
# `pykmc.events` (and `trajkmc.xyz`): the directory was reused, so both text logs
# hold TWO concatenated run segments —
#
#     segment A : steps 1..30    (aborted attempt; second '# Simulation Progress
#                                 Tracking File' header at pykmc.out line 48)
#     segment B : steps 1..2000  (the completed run; `DONE`, `restart_2000.npz`)
#
# The two are different trajectories (step 1 picks ref 0 in A, ref 4 in B), i.e.
# different RNG streams — A is not a prefix of B.  Crucially, `idx_ref` is an
# index INTO `reference_table.pickle`, and only ONE reference table survives on
# disk: the completed run's (it is rewritten each run, and the task brief
# confirms it is clean).  Segment A's ref indices therefore point into a
# reference table that no longer exists; scoring them against the surviving table
# would attribute A's rate constants to B's event identities.  The merged
# catalogue's lineage (`source_sim_paths` = 'run_tag#idx_ref') is likewise keyed
# to the surviving table.
#
# POLICY (`KEEP_LAST_SEGMENT = True`): split both files on a non-increasing step
# index and keep ONLY the final segment, in both `pykmc.out` and `pykmc.events`,
# with an assertion that the two files segment identically.  This is:
#   * correct for the contaminated run (keeps exactly the lineage-consistent
#     2000-step segment), and
#   * a provable no-op for the other 59 runs (each has a single monotone
#     1..2000 segment) — verified by the `n_segments` column of the run log.
#
# Set to False (or pass `--include-dirty-segments`) to reproduce the naive
# whole-file parse; `NICR_FLUX_RESTATEMENT_2026-08-15.md` quotes the delta.
KEEP_LAST_SEGMENT = True


def _last_segment(records: list[tuple[int, object]]) -> tuple[list[tuple[int, object]], int]:
    """Split a step-ordered record list on step-index restarts; keep the last.

    Returns (kept_records, n_segments).  A restart is any position whose step
    index is <= its predecessor's — the signature of a fresh run appended to an
    existing log.
    """
    if not records:
        return records, 0
    starts = [0] + [i for i in range(1, len(records)) if records[i][0] <= records[i - 1][0]]
    n_seg = len(starts)
    if not KEEP_LAST_SEGMENT:
        return records, n_seg
    return records[starts[-1]:], n_seg


def parse_out(run_dir: Path) -> tuple["pd.Series", int]:
    """pykmc.out -> dT_s indexed by step (data rows have 10 columns)."""
    recs: list[tuple[int, object]] = []
    with open(run_dir / "pykmc.out") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 10 and parts[0].isdigit():
                recs.append((int(parts[0]), float(parts[1])))
    recs, n_seg = _last_segment(recs)
    steps = [r[0] for r in recs]
    dts = [r[1] for r in recs]
    ser = pd.Series(dts, index=steps, name="dt_s")
    if ser.index.has_duplicates:
        if KEEP_LAST_SEGMENT:  # pragma: no cover - guard, never hit on this corpus
            raise RuntimeError(f"{run_dir.name}: duplicate step index after segmentation")
        # Diagnostic mode only.  The NiFe precedent parser CANNOT parse a
        # contaminated run at all: `app['step'].map(dt)` raises on a duplicate
        # index.  Last-wins dedup is the closest runnable analogue of the naive
        # whole-file parse, and is what the quoted "naive" number below uses.
        ser = ser[~ser.index.duplicated(keep="last")]
    return ser, n_seg


def parse_events(run_dir: Path) -> tuple[pd.DataFrame, int]:
    """pykmc.events -> one row per (step, applicable event)."""
    blocks: list[tuple[int, object]] = []  # (step, rows)
    step = None
    sel = None
    rows: list[tuple] = []
    with open(run_dir / "pykmc.events") as f:
        for line in f:
            m = STEP_RE.match(line)
            if m:
                if step is not None:
                    blocks.append((step, rows))
                step = int(m.group(1))
                sel = None
                rows = []
                continue
            if "Applicable Events" in line:
                ms = SEL_RE.search(line)
                sel = int(ms.group(1)) if ms else None
                continue
            parts = line.split()
            if step is None or len(parts) < 11 or parts[0].startswith("#"):
                continue
            if parts[1] not in SPECIES:
                continue
            rows.append((step, int(parts[3]), float(parts[7]), int(parts[0]) == sel))
    if step is not None:
        blocks.append((step, rows))
    blocks, n_seg = _last_segment(blocks)
    flat = [r for _, rr in blocks for r in rr]  # type: ignore[misc]
    return pd.DataFrame(flat, columns=["step", "idx_ref", "k_psinv", "selected"]), n_seg


def flux_one_run(tag: str) -> tuple[pd.DataFrame, dict]:
    run_dir = RUNS / tag
    dt, n_seg_out = parse_out(run_dir)
    app, n_seg_ev = parse_events(run_dir)
    if n_seg_out != n_seg_ev:
        raise RuntimeError(
            f"{tag}: pykmc.out has {n_seg_out} segments but pykmc.events has {n_seg_ev}"
        )
    n_rows_raw = len(app)
    app = app[app["step"].isin(dt.index)].copy()
    app["dt_s"] = app["step"].map(dt)
    app["firings"] = app["k_psinv"] * 1e12 * app["dt_s"]
    g = app.groupby("idx_ref")
    out = pd.DataFrame({
        "flux_firings": g["firings"].sum(),
        "n_selected": g["selected"].sum(),
        "occupancy_s": g.apply(lambda x: x.drop_duplicates("step")["dt_s"].sum(),
                               include_groups=False),
        "n_instances": g.size(),
    }).reset_index()
    out.insert(0, "run_tag", tag)
    meta = {
        "run_tag": tag,
        "n_segments": n_seg_out,
        "n_out_rows": int(len(dt)),
        "max_step": int(dt.index.max()),
        "n_event_rows": n_rows_raw,
        "n_idx_refs": int(len(out)),
        "flux_firings": float(out["flux_firings"].sum()),
        "n_selected": int(out["n_selected"].sum()),
    }
    return out, meta


def main() -> None:
    global KEEP_LAST_SEGMENT
    suffix = ""
    if "--include-dirty-segments" in sys.argv:
        KEEP_LAST_SEGMENT = False
        suffix = "_dirtyall"
        print("!! KEEP_LAST_SEGMENT disabled — naive whole-file parse (diagnostic only)")

    tags = pd.read_csv(MANIFEST)["run_tag"].tolist()
    per_run, metas = [], []
    for i, tag in enumerate(tags):
        fr, meta = flux_one_run(tag)
        per_run.append(fr)
        metas.append(meta)
        flag = "  <-- MULTI-SEGMENT" if meta["n_segments"] > 1 else ""
        print(f"[{i + 1:2d}/{len(tags)}] {tag}: {len(fr)} idx_refs, "
              f"flux {fr['flux_firings'].sum():.3f}, "
              f"selected {int(fr['n_selected'].sum())}, "
              f"out_rows {meta['n_out_rows']}{flag}")
    flux = pd.concat(per_run, ignore_index=True)
    flux.to_csv(CAMP / f"flux_by_ref_nicr{suffix}.csv", index=False)
    pd.DataFrame(metas).to_csv(CAMP / f"run_log_nicr{suffix}.csv", index=False)

    fx = {}
    for col in ("flux_firings", "n_selected", "occupancy_s", "n_instances"):
        fx[col] = dict(zip(flux["run_tag"] + "#" + flux["idx_ref"].astype(str),
                           flux[col].to_numpy()))

    cat = pd.read_parquet(CATALOGUE)
    for col in ("flux_firings", "n_selected", "occupancy_s", "n_instances"):
        d = fx[col]
        cat[col] = [float(sum(d.get(p, 0.0) for p in pp))
                    for pp in cat["source_sim_paths"]]
    cat["reachable"] = cat["occupancy_s"] > 0.0
    cat["donor"] = cat["source_sim_paths"].apply(lambda pp: pp[0])
    cat["n_members"] = cat["source_sim_paths"].apply(len)
    # token-mismatch (recovered concerted) flag — the verdict's predicate:
    # len(saddle_token) != #(delta rows whose `before` is not EMPTY/Occ 0), i.e.
    # the delta-derived mover count the pre-8f49e18 translator used.
    cat["n_tokens"] = cat["saddle_token"].apply(len)
    cat["n_arrows"] = cat["arrows"].apply(len)
    cat["n_delta_movers"] = cat["delta"].apply(
        lambda d: sum(1 for r in d if int(r["before"]) != 0))
    cat["token_mismatch"] = cat["n_tokens"] != cat["n_delta_movers"]

    keep = ["class_id", "nu0_pair_policy", "audit_status", "audit_reason", "archetype",
            "action_id", "one_way", "move_shape", "delta_atoms", "Ea_rep_eV", "Ea_std_eV",
            "n_eff", "n_tokens", "n_arrows", "n_delta_movers", "token_mismatch",
            "flux_firings", "n_selected", "occupancy_s", "n_instances",
            "reachable", "n_members", "donor"]
    per_class = cat[keep].copy()
    per_class.to_csv(CAMP / f"class_flux_nicr{suffix}.csv", index=False)

    tot = per_class["flux_firings"].sum()
    pend = per_class[per_class["nu0_pair_policy"] == "pending_research"].copy()
    pend = pend.sort_values("flux_firings", ascending=False).reset_index(drop=True)
    pend[["donor_run", "donor_idx"]] = pend["donor"].str.split("#", expand=True)
    pend["donor_idx"] = pend["donor_idx"].astype(int)
    pend["cum_flux_frac_pend"] = pend["flux_firings"].cumsum() / pend["flux_firings"].sum()
    pend.to_csv(CAMP / f"targets_nicr{suffix}.csv", index=False)

    print(f"\ncorpus: {len(per_class)} classes, total flux {tot:.3f} expected firings, "
          f"selections {int(per_class['n_selected'].sum())}")
    q = per_class["audit_status"].astype(str).str.contains("quarantin", case=False, na=False)
    print(f"quarantined: {int(q.sum())} classes, "
          f"{100 * per_class.loc[q, 'flux_firings'].sum() / tot:.2f}% of corpus flux")
    meas = per_class["nu0_pair_policy"] == "harvested_pair"
    print(f"measured (harvested_pair): {int(meas.sum())} classes, "
          f"{100 * per_class.loc[meas, 'flux_firings'].sum() / tot:.2f}%")
    print(f"pending classes: {len(pend)}, flux {pend['flux_firings'].sum():.3f} "
          f"({100 * pend['flux_firings'].sum() / tot:.2f}% of total); "
          f"reachable {int(pend['reachable'].sum())}")
    for n in (10, 25, 50, 100, 200, 300, 500):
        if n <= len(pend):
            print(f"  top {n:4d} pending classes carry "
                  f"{100 * pend['flux_firings'].head(n).sum() / pend['flux_firings'].sum():6.2f}% "
                  f"of pending flux "
                  f"({100 * pend['flux_firings'].head(n).sum() / tot:6.2f}% of total)")


if __name__ == "__main__":
    main()
