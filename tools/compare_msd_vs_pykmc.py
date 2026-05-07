"""compare_msd_vs_pykmc.py — MSD / diffusion comparison between a compiled
pylatkmc model binary and a completed pyKMC off-lattice run.

Reads `analysis/summary.json` from a pyKMC run directory (which has
total_sim_time + msd_final computed from the off-lattice trajectory),
regenerates a matching-size .kmcinit with the same composition, runs the
pylatkmc model binary, and prints D_pylatkmc / D_pyKMC.

M4 target: species-aware MSD ratio ≤ 3× on 95Ni_5Cr (was 5.8× with the legacy
scalar-key latkmc).

Usage:
    python compare_msd_vs_pykmc.py \\
        /Users/stephenkerr/kmc/Data/Research/Ni_Slab_Alloys/NiCr_Ni95_Cr05_T500_1vac_full \\
        --model ni_fe_cr_v1 \\
        --n-replicas 4 --steps 100000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PYLATKMC_ROOT = Path(__file__).resolve().parent.parent
OPENMPI_BIN = "/Users/stephenkerr/openmpi/bin"

A_NI = 3.524  # Ni lattice constant (used for all alloys)
NN_DIST = A_NI / np.sqrt(2.0)


def read_pykmc_summary(pykmc_dir: Path) -> dict:
    sj = pykmc_dir / "analysis" / "summary.json"
    if not sj.exists():
        sys.exit(f"error: {sj} not found; run Analysis/ first to generate it")
    return json.loads(sj.read_text())


def infer_slab_dims(pykmc_summary: dict, pykmc_dir: Path) -> tuple[int, int, int]:
    """Infer (nx, ny, nz) of the FCC(100) slab from frame 0 of trajkmc.xyz.
    Mirrors the legacy implementation."""
    traj = pykmc_dir / "trajkmc.xyz"
    with open(traj) as fp:
        n_atoms = int(fp.readline().strip())
        header = fp.readline()
    m = re.search(r'Lattice="([-\d.eE\s]+)"', header)
    if m is None:
        sys.exit("error: could not parse Lattice from trajkmc.xyz header")
    cell_vals = [float(x) for x in m.group(1).split()]
    Lx, Ly = cell_vals[0], cell_vals[4]
    nx = int(round(Lx / NN_DIST))
    ny = int(round(Ly / NN_DIST))
    n_vac = int(pykmc_summary["n_vacancies"])
    n_sites = n_atoms + n_vac
    nz = n_sites // (nx * ny)
    if nx * ny * nz != n_sites:
        sys.exit(f"error: nx*ny*nz ({nx}*{ny}*{nz}={nx * ny * nz}) != n_sites ({n_sites})")
    return nx, ny, nz


def composition_from_summary(summary: dict) -> str:
    """Convert the pyKMC summary into a --composition string for
    build_initial_config.py. Dir naming convention is e.g.
    'NiCr_Ni95_Cr05_T500_1vac_full' — we scan tokens that look like a
    known-element + integer, stopping at the first non-element token
    (e.g. 'T500' or '1vac' or 'full')."""
    KNOWN = {"Ni", "Fe", "Cr"}
    dn = summary.get("dirname", "")
    parts = dn.split("_")
    pairs: list[tuple[str, int]] = []
    pattern = re.compile(r"^([A-Z][a-z]?)(\d+)$")
    for tok in parts[1:]:
        m = pattern.match(tok)
        if m is None:
            continue
        name = m.group(1)
        if name not in KNOWN:
            break  # stop — we've left the element-fraction prefix
        pairs.append((name, int(m.group(2))))
        if len(pairs) >= 3:
            break
    if not pairs:
        # Fallback: homogeneous (single-element list).
        sp = summary.get("species", ["Ni"])
        return f"{sp[0]}100"
    return "_".join(f"{n}{p}" for n, p in pairs)


def build_kmcinit(
    tmp: Path, nx: int, ny: int, nz: int, n_vac: int, composition: str, seed: int
) -> Path:
    out = tmp / "config.kmcinit"
    subprocess.check_call(
        [
            sys.executable,
            str(PYLATKMC_ROOT / "tools" / "build_initial_config.py"),
            "--nx",
            str(nx),
            "--ny",
            str(ny),
            "--nz",
            str(nz),
            "--composition",
            composition,
            "--n-vacancies",
            str(n_vac),
            "--seed",
            str(seed),
            "-o",
            str(out),
        ],
        stdout=subprocess.DEVNULL,
    )
    return out


def run_pylatkmc(
    tmp: Path,
    model: str,
    ratetable: Path,
    initconfig: Path,
    temperature_K: float,
    steps: int,
    replicas: int,
    base_seed: int = 42,
) -> dict:
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
    if not binary.is_file():
        sys.exit(f"error: binary not found: {binary}; run `cmake --build build` first")
    env = os.environ.copy()
    env["PATH"] = OPENMPI_BIN + ":" + env.get("PATH", "")
    subprocess.check_call(
        [
            f"{OPENMPI_BIN}/mpirun",
            "--oversubscribe",
            "-n",
            str(replicas),
            str(binary),
            str(input_ini),
        ],
        cwd=str(tmp),
        env=env,
        stdout=subprocess.DEVNULL,
    )
    agg_path = tmp / "output" / "aggregate_summary.json"
    return json.loads(agg_path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "pykmc_dir", type=Path, help="completed pyKMC run dir (has analysis/summary.json)"
    )
    ap.add_argument(
        "--model", default="ni_fe_cr_v1", help="pylatkmc model name (matches models/<name>/)"
    )
    ap.add_argument("--n-replicas", type=int, default=4)
    ap.add_argument("--steps", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    # --- pyKMC reference ---
    py = read_pykmc_summary(args.pykmc_dir)
    T = float(py["temperature"])
    n_vac = int(py["n_vacancies"])
    t_py = float(py["total_sim_time"])
    msd_py_final = float(py["msd_final"][0])
    msd_py_max = float(py["msd_max"][0])
    D_py_final = msd_py_final / (6.0 * t_py)
    D_py_max = msd_py_max / (6.0 * t_py)
    species_list = py.get("species", ["Ni"])

    nx, ny, nz = infer_slab_dims(py, args.pykmc_dir)
    composition = composition_from_summary(py)
    print(f"[pyKMC] {args.pykmc_dir.name}")
    print(f"        species={species_list}, composition={composition}")
    print(f"        slab {nx}×{ny}×{nz}, n_atoms={py['n_atoms']}, n_vac={n_vac}, T={T:.1f} K")
    print(f"        t_total = {t_py:.3e} s, MSD_final = {msd_py_final:.2f} Å²")
    print(f"        D_final = {D_py_final:.3e} Å²/s  (MSD / 6t)")
    print()

    # --- pylatkmc binary ---
    ratetable = PYLATKMC_ROOT / "models" / args.model / "examples" / f"{args.model}.kmcrt"
    if not ratetable.is_file():
        sys.exit(
            f"error: {ratetable} not found; run `pylatkmc-gen rate models/{args.model}/{args.model}.kmcspec.toml` first"
        )
    with tempfile.TemporaryDirectory(prefix="pylatkmc_cmp_") as tmp_str:
        tmp = Path(tmp_str)
        initconfig = build_kmcinit(tmp, nx, ny, nz, n_vac, composition, args.seed)
        print(f"[pylatkmc] model={args.model}, steps={args.steps}, replicas={args.n_replicas}")
        agg = run_pylatkmc(
            tmp, args.model, ratetable, initconfig, T, args.steps, args.n_replicas, args.seed
        )

    t_lk = agg["total_time_s_mean"]
    msd_lk = agg["mean_msd_A2_mean"]
    D_lk = msd_lk / (6.0 * t_lk) if t_lk > 0 else float("nan")
    print(f"         mean t = {t_lk:.3e} s  (± {agg['total_time_s_std']:.2e})")
    print(f"         mean MSD = {msd_lk:.3e} Å²  (± {agg['mean_msd_A2_std']:.2e})")
    print(f"         D = {D_lk:.3e} Å²/s")

    motif_sum = agg["motif_counts_sum"]
    total_evts = sum(motif_sum.values())
    if total_evts > 0:
        print(
            "         motifs: "
            + "  ".join(
                f"{k.split('_', 1)[0][:7]}={v * 100 / total_evts:.1f}%"
                for k, v in motif_sum.items()
                if v > 0
            )
        )

    print()
    print("=" * 70)
    ratio_final = D_lk / D_py_final if D_py_final > 0 else float("nan")
    ratio_max = D_lk / D_py_max if D_py_max > 0 else float("nan")
    print(f"D_pylatkmc / D_pyKMC(final) = {ratio_final:.3f}")
    print(f"D_pylatkmc / D_pyKMC(max)   = {ratio_max:.3f}")

    # Translate ratio to effective-barrier offset.
    kB = 8.617333e-5
    kT = kB * T
    if np.isfinite(ratio_final) and ratio_final > 0:
        dEa_eff = kT * float(np.log(ratio_final))
        direction = "LOWER" if dEa_eff > 0 else "HIGHER"
        print(
            f"Effective Ea differs by {dEa_eff * 1000:+.0f} meV (pylatkmc has {direction} barrier)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
