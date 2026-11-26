"""Statistical cross-engine gate: run the same input.ini through the pure-Python
engine and (when available) the compiled C+MPI binary, then assert D = MSD/(6t)
agrees within a relative tolerance.

Skips cleanly (rc 0, message) when the C binary or mpirun is unavailable — this is a
maintainer-machine check, mirroring the existing cross-engine validation scripts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_EPS = 1e-300


def diffusivity(mean_msd_A2: float, total_time_s: float) -> float:
    if total_time_s <= 0.0:
        return 0.0
    return mean_msd_A2 / (6.0 * total_time_s)


def relative_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), _EPS)


def compare(py_agg: dict, c_agg: dict, tol: float) -> tuple[bool, str]:
    d_py = diffusivity(py_agg["mean_msd_A2_mean"], py_agg["total_time_s_mean"])
    d_c = diffusivity(c_agg["mean_msd_A2_mean"], c_agg["total_time_s_mean"])
    rd = relative_diff(d_py, d_c)
    msg = f"D_py={d_py:.6e}  D_c={d_c:.6e}  rel_diff={rd:.4f}  tol={tol:.4f}"
    return rd <= tol, msg


def _run_python_engine(spec: Path, input_ini: Path, replicas: int) -> dict:
    # import the package run() to avoid a subprocess round-trip.
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from pylatkmc.engine.runner import run

    agg_path = run(spec, input_ini, n_replicas=replicas)
    return json.loads(Path(agg_path).read_text())


def _run_c_engine(binary: Path, input_ini: Path, replicas: int) -> dict | None:
    mpirun = shutil.which("mpirun")
    if mpirun is None or not binary.exists():
        return None
    out_root = input_ini.parent / "output"
    subprocess.run(
        [mpirun, "--oversubscribe", "-n", str(replicas), str(binary), str(input_ini)],
        cwd=input_ini.parent, check=True,
    )
    return json.loads((out_root / "aggregate_summary.json").read_text())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Python-vs-C statistical cross-engine gate")
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--input", required=True, type=Path, help="input.ini")
    ap.add_argument("--binary", type=Path, default=None, help="compiled C binary")
    ap.add_argument("--replicas", type=int, default=4)
    ap.add_argument("--tol", type=float, default=0.15, help="relative-D tolerance")
    args = ap.parse_args(argv)

    py_agg = _run_python_engine(args.spec, args.input, args.replicas)
    c_agg = _run_c_engine(args.binary, args.input, args.replicas) if args.binary else None
    if c_agg is None:
        print("SKIP: C binary or mpirun unavailable; ran Python engine only.")
        print(f"  D_py={diffusivity(py_agg['mean_msd_A2_mean'], py_agg['total_time_s_mean']):.6e}")
        return 0
    ok, msg = compare(py_agg, c_agg, args.tol)
    print(("PASS: " if ok else "FAIL: ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
