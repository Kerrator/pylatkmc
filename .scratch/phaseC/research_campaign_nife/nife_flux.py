"""NiFe corpus flux ranking — reachability-corrected, per merged class.

Mirrors the gap-2 triage framing (.scratch/phaseC/gap2/reconstitute_and_flux.py):
per-event expected firings = sum over applicable steps of k * dt (residence time
of the state listed at '#Step: N' is dT of pykmc.out row N), aggregated per
idx_ref, then mapped onto merged classes via source_sim_paths ('run#idx_ref')
and summed corpus-wide over the 60 NiFe runs.

Outputs (this directory):
    flux_by_ref_nife.csv    one row per (run_tag, idx_ref)
    class_flux_nife.csv     all 20,293 merged classes + corpus flux + policy
    targets_nife.csv        pending_research classes, flux-desc, with the
                            primary-donor (run, idx_ref) the search job uses

Run from the pylatkmc repo root under pykmc_env.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

CAMP = Path(__file__).parent
RUNS = Path("/home/kerr/pykmc/production_NiCrFe/runs")
MANIFEST = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/manifest_NiFe.csv")
STAMPED = CAMP / "merged_v3_NiFe_stamped.parquet"

STEP_RE = re.compile(r"^#Step:\s*(\d+)")
SEL_RE = re.compile(r"Selected=(\d+)")
SPECIES = {"Ni", "Fe", "Cr"}


def parse_out(run_dir: Path) -> "pd.Series":
    """pykmc.out -> dT_s indexed by step (data rows have 10 columns)."""
    steps, dts = [], []
    with open(run_dir / "pykmc.out") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 10 and parts[0].isdigit():
                steps.append(int(parts[0]))
                dts.append(float(parts[1]))
    return pd.Series(dts, index=steps, name="dt_s")


def parse_events(run_dir: Path) -> pd.DataFrame:
    rows = []
    step = None
    sel = None
    with open(run_dir / "pykmc.events") as f:
        for line in f:
            m = STEP_RE.match(line)
            if m:
                step = int(m.group(1))
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
            rows.append((step, int(parts[3]), float(parts[7]),
                         int(parts[0]) == sel))
    return pd.DataFrame(rows, columns=["step", "idx_ref", "k_psinv", "selected"])


def flux_one_run(tag: str) -> pd.DataFrame:
    run_dir = RUNS / tag
    dt = parse_out(run_dir)
    app = parse_events(run_dir)
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
    return out


def main() -> None:
    tags = pd.read_csv(MANIFEST)["run_tag"].tolist()
    per_run = []
    for i, tag in enumerate(tags):
        fr = flux_one_run(tag)
        per_run.append(fr)
        print(f"[{i + 1:2d}/{len(tags)}] {tag}: {len(fr)} idx_refs, "
              f"flux {fr['flux_firings'].sum():.3f}, "
              f"selected {int(fr['n_selected'].sum())}")
    flux = pd.concat(per_run, ignore_index=True)
    flux.to_csv(CAMP / "flux_by_ref_nife.csv", index=False)
    fx = flux.set_index(flux["run_tag"] + "#" + flux["idx_ref"].astype(str))

    cat = pd.read_parquet(STAMPED)
    def agg(paths, col):
        return float(sum(fx[col].get(p, 0.0) for p in paths))
    for col in ("flux_firings", "n_selected", "occupancy_s", "n_instances"):
        cat[col] = cat["source_sim_paths"].apply(lambda pp: agg(pp, col))
    cat["reachable"] = cat["occupancy_s"] > 0.0
    cat["donor"] = cat["source_sim_paths"].apply(lambda pp: pp[0])
    cat["n_members"] = cat["source_sim_paths"].apply(len)

    keep = ["class_id", "nu0_pair_policy", "audit_status", "archetype", "action_id",
            "one_way", "move_shape", "delta_atoms", "Ea_rep_eV", "Ea_std_eV",
            "n_eff", "flux_firings", "n_selected", "occupancy_s", "n_instances",
            "reachable", "n_members", "donor"]
    per_class = cat[keep].copy()
    per_class.to_csv(CAMP / "class_flux_nife.csv", index=False)

    tot = per_class["flux_firings"].sum()
    pend = per_class[per_class["nu0_pair_policy"] == "pending_research"].copy()
    pend = pend.sort_values("flux_firings", ascending=False).reset_index(drop=True)
    pend[["donor_run", "donor_idx"]] = pend["donor"].str.split("#", expand=True)
    pend["donor_idx"] = pend["donor_idx"].astype(int)
    pend["cum_flux_frac_pend"] = pend["flux_firings"].cumsum() / pend["flux_firings"].sum()
    pend.to_csv(CAMP / "targets_nife.csv", index=False)

    print(f"\ncorpus: {len(per_class)} classes, total flux {tot:.3f} expected firings, "
          f"selections {int(per_class['n_selected'].sum())}")
    q = per_class[per_class["audit_status"].astype(str).str.contains("quarantin", case=False, na=False)]
    print(f"quarantined flux share: {100 * q['flux_firings'].sum() / tot:.2f}%")
    print(f"pending classes: {len(pend)}, flux {pend['flux_firings'].sum():.3f} "
          f"({100 * pend['flux_firings'].sum() / tot:.2f}% of total); "
          f"reachable {int(pend['reachable'].sum())}")
    for n in (10, 25, 50, 100, 150, 200, 300, 500):
        if n <= len(pend):
            print(f"  top {n:4d} pending classes carry "
                  f"{100 * pend['flux_firings'].head(n).sum() / pend['flux_firings'].sum():6.2f}% "
                  f"of pending flux "
                  f"({100 * pend['flux_firings'].head(n).sum() / tot:6.2f}% of total)")


if __name__ == "__main__":
    main()
