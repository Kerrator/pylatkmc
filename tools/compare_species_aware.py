"""compare_species_aware.py — compare pylatkmc kinetics across alloy compositions.

M4 goal reframe: the per-event diffusion pattern should change with composition
for a species-aware rate cube. This script runs pylatkmc on the same slab size
but three compositions (pure Ni, 95Ni_5Cr, 95Ni_5Fe) and reports event rates,
motif distribution, and effective D per composition + per temperature.

Why this beats the original `compare_msd_vs_pykmc.py` gate for validation:
pyKMC uses basin acceleration whose "total_sim_time" is many orders of
magnitude larger than a raw-kinetics calculation. A direct D ratio vs pyKMC is
not meaningful without first disabling basin. A same-engine comparison across
compositions IS meaningful — the species-aware rate key should measurably
slow the vacancy when Cr/Fe neighbors are present.

Usage:
    python tools/compare_species_aware.py --model ni_fe_cr_v1 --temperatures 300 500 700
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PYLATKMC_ROOT = Path(__file__).resolve().parent.parent
OPENMPI_BIN = "/Users/stephenkerr/openmpi/bin"

A_NI = 3.524
NN_DIST = A_NI / np.sqrt(2.0)

COMPOSITIONS: dict[str, str] = {
    "100Ni":       "Ni100",
    "95Ni_5Cr":    "Ni95_Cr5",
    "95Ni_5Fe":    "Ni95_Fe5",
    "90Ni_10Cr":   "Ni90_Cr10",
    "90Ni_10Fe":   "Ni90_Fe10",
}


def build_kmcinit(tmp: Path, nx: int, ny: int, nz: int, n_vac: int,
                  composition: str, seed: int) -> Path:
    out = tmp / "config.kmcinit"
    subprocess.check_call([
        sys.executable, str(PYLATKMC_ROOT / "tools" / "build_initial_config.py"),
        "--nx", str(nx), "--ny", str(ny), "--nz", str(nz),
        "--composition", composition,
        "--n-vacancies", str(n_vac),
        "--seed", str(seed),
        "-o", str(out),
    ], stdout=subprocess.DEVNULL)
    return out


def run_pylatkmc(tmp: Path, model: str, ratetable: Path, initconfig: Path,
                temperature_K: float, steps: int, replicas: int,
                base_seed: int) -> dict:
    input_ini = tmp / "input.ini"
    input_ini.write_text(f"""\
[run]
max_steps      = {steps}
max_time_s     = 0
sample_every   = {max(1, steps // 20)}
summary_every  = 0
base_seed      = {base_seed}

[paths]
ratetable_path  = {ratetable}
initconfig_path = {initconfig}
output_root     = ./output

[physics]
temperature_K = {temperature_K}

[validation]
rng_replay_path =
""")
    binary = PYLATKMC_ROOT / "build" / f"pylatkmc_{model}"
    env = os.environ.copy()
    env["PATH"] = OPENMPI_BIN + ":" + env.get("PATH", "")
    subprocess.check_call([
        f"{OPENMPI_BIN}/mpirun", "--oversubscribe", "-n", str(replicas),
        str(binary), str(input_ini),
    ], cwd=str(tmp), env=env, stdout=subprocess.DEVNULL)
    return json.loads((tmp / "output" / "aggregate_summary.json").read_text())


def summarize(tag: str, T: float, agg: dict) -> dict:
    t = float(agg["total_time_s_mean"])
    msd = float(agg["mean_msd_A2_mean"])
    D = msd / (6.0 * t) if t > 0 else float("nan")
    motifs = {k: int(v) for k, v in agg["motif_counts_sum"].items() if v > 0}
    n_events = sum(motifs.values())
    return {
        "tag": tag,
        "T_K": T,
        "mean_time_s": t,
        "mean_msd_A2": msd,
        "D_A2_per_s": D,
        "n_events": n_events,
        "motifs": motifs,
    }


def print_row(row: dict) -> None:
    tag = row["tag"]
    T = row["T_K"]
    top_motif = max(row["motifs"].items(), key=lambda kv: kv[1])[0] if row["motifs"] else "-"
    top_pct = 100 * row["motifs"].get(top_motif, 0) / max(1, row["n_events"])
    print(f"  {tag:<10}  T={T:>5.0f}K  "
          f"t={row['mean_time_s']:>10.3e}s  "
          f"MSD={row['mean_msd_A2']:>10.3e}Å²  "
          f"D={row['D_A2_per_s']:>10.3e}Å²/s  "
          f"top_motif={top_motif:<25}({top_pct:>5.1f}%)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="ni_fe_cr_v1")
    ap.add_argument("--compositions", nargs="+",
                    default=["100Ni", "95Ni_5Cr", "95Ni_5Fe"])
    ap.add_argument("--temperatures", nargs="+", type=float,
                    default=[300, 500, 700, 1000])
    ap.add_argument("--nx", type=int, default=22)
    ap.add_argument("--ny", type=int, default=22)
    ap.add_argument("--nz", type=int, default=20)
    ap.add_argument("--n-vacancies", type=int, default=1)
    ap.add_argument("--n-replicas", type=int, default=4)
    ap.add_argument("--steps", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--out-json", type=Path, default=None,
                    help="Optional path to write the full result table as JSON")
    args = ap.parse_args()

    # Sanity check
    for comp in args.compositions:
        if comp not in COMPOSITIONS:
            sys.exit(f"unknown composition {comp!r}; known: {sorted(COMPOSITIONS)}")

    ratetable = (PYLATKMC_ROOT / "models" / args.model / "examples"
                 / f"{args.model}.kmcrt")
    if not ratetable.is_file():
        sys.exit(f"error: {ratetable} not found; run `pylatkmc-gen rate ...` first")
    binary = PYLATKMC_ROOT / "build" / f"pylatkmc_{args.model}"
    if not binary.is_file():
        sys.exit(f"error: {binary} not found; run `cmake --build build` first")

    print(f"Grid: compositions={args.compositions}  Ts={args.temperatures}")
    print(f"Slab: {args.nx}×{args.ny}×{args.nz} = "
          f"{args.nx*args.ny*args.nz} sites, n_vac={args.n_vacancies}, "
          f"{args.n_replicas} replicas × {args.steps} steps")
    print()

    all_rows: list[dict] = []
    for comp in args.compositions:
        for T in args.temperatures:
            with tempfile.TemporaryDirectory(prefix="pylatkmc_spec_") as tmp_str:
                tmp = Path(tmp_str)
                initconfig = build_kmcinit(
                    tmp, args.nx, args.ny, args.nz, args.n_vacancies,
                    COMPOSITIONS[comp], args.seed,
                )
                agg = run_pylatkmc(
                    tmp, args.model, ratetable, initconfig,
                    T, args.steps, args.n_replicas, args.seed,
                )
            row = summarize(comp, T, agg)
            all_rows.append(row)
            print_row(row)

    # Per-temperature composition ratios (D_100Ni / D_alloy).
    print()
    print("Species-awareness signal: D(100Ni) / D(alloy) per T")
    baseline = "100Ni"
    if baseline in args.compositions:
        for T in args.temperatures:
            base = next(r for r in all_rows
                        if r["tag"] == baseline and r["T_K"] == T)
            print(f"  T={T:>5.0f}K:  ", end="")
            parts: list[str] = []
            for comp in args.compositions:
                if comp == baseline:
                    continue
                r = next(rr for rr in all_rows
                         if rr["tag"] == comp and rr["T_K"] == T)
                ratio = (base["D_A2_per_s"] / r["D_A2_per_s"]
                         if r["D_A2_per_s"] > 0 else float("nan"))
                parts.append(f"{comp}: {ratio:.2f}×")
            print("  ".join(parts))

    if args.out_json:
        args.out_json.write_text(json.dumps(all_rows, indent=2))
        print(f"\nWrote {args.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
