"""Compare v0.2 vs v0.3 codegen on the full 80-config sweep.

Reads:
  output_T<T>_<n>vac/aggregate_summary.json     ← v0.3 (current)
  v0_2_baseline/output_T<T>_<n>vac/aggregate_summary.json  ← v0.2

Reports the D matrix delta and Arrhenius Eₐ shifts per n_vac.

Usage:
  cd models/ni_fe_cr_v1/examples/full_100Ni
  python3 compare_v02_v03.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

KB = 8.617333262e-5
TEMPS = [300, 400, 500, 600, 700, 800, 900, 1200]
NVS = list(range(1, 11))


def _load(out_dir: Path, T: int, n: int):
    p = out_dir / f"output_T{T}_{n}vac" / "aggregate_summary.json"
    if not p.is_file():
        return None
    j = json.load(open(p))
    msd = j["mean_msd_A2_mean"]
    t = j["total_time_s_mean"]
    D = (msd * 1e-16) / (6.0 * t) if t > 0 else float("nan")
    return {"MSD": msd, "sim_t": t, "D": D, "wall_s": j.get("wall_seconds")}


def _arrhenius(rows):
    """Linear regression of ln D vs 1/T; returns (D0, Ea_eV, R²)."""
    pts = [(1.0 / r["T"], math.log(r["D"]))
           for r in rows if r["D"] > 0 and r["D"] == r["D"]]
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    N = len(pts)
    sx = sum(xs); sy = sum(ys); sxx = sum(x*x for x in xs); sxy = sum(x*y for x, y in zip(xs, ys))
    slope = (N*sxy - sx*sy) / (N*sxx - sx*sx)
    intercept = (sy - slope*sx) / N
    Ea = -slope * KB; D0 = math.exp(intercept)
    ymean = sy / N
    ss_t = sum((y - ymean)**2 for y in ys)
    ss_r = sum((y - (slope*x + intercept))**2 for x, y in zip(xs, ys))
    r2 = 1 - ss_r/ss_t if ss_t > 0 else float("nan")
    return D0, Ea, r2


def main():
    base_v02 = Path("v0_2_baseline")
    base_v03 = Path(".")

    print("=" * 110)
    print(f"  v0.2 (baseline) vs v0.3 (ShellCondition gating) — D ratio = D_v03 / D_v02")
    print("=" * 110)
    print(f"\n{'T':>5}", end="")
    for n in NVS: print(f" {'nv='+str(n):>10}", end="")
    print()
    print("-" * 110)
    for T in TEMPS:
        print(f"{T:>5}", end="")
        for n in NVS:
            v02 = _load(base_v02, T, n); v03 = _load(base_v03, T, n)
            if v02 is None or v03 is None or v02["D"] <= 0:
                print(f" {'-':>10}", end=""); continue
            ratio = v03["D"] / v02["D"]
            s = f"{ratio:.2e}"
            print(f" {s:>10}", end="")
        print()

    print("\nArrhenius D = D0·exp(-Eₐ/kT)")
    print("-" * 80)
    print(f"{'n_vac':>6}  {'v0.2 Eₐ':>9} {'v0.2 R²':>8}  {'v0.3 Eₐ':>9} {'v0.3 R²':>8}  {'ΔEₐ':>9}")
    print("-" * 80)
    v02_results, v03_results = [], []
    for T in TEMPS:
        for n in NVS:
            for tag, base, store in (("v02", base_v02, v02_results), ("v03", base_v03, v03_results)):
                r = _load(base, T, n)
                if r:
                    store.append({"T": T, "n_vac": n, **r})
    for n in NVS:
        v02_fit = _arrhenius([r for r in v02_results if r["n_vac"] == n])
        v03_fit = _arrhenius([r for r in v03_results if r["n_vac"] == n])
        if v02_fit and v03_fit:
            d_ea = v03_fit[1] - v02_fit[1]
            print(f"{n:>6}  {v02_fit[1]:>9.3f} {v02_fit[2]:>8.3f}  "
                  f"{v03_fit[1]:>9.3f} {v03_fit[2]:>8.3f}  {d_ea:>+9.3f}")

    # Total wall time comparison
    wall_02 = sum(r.get("wall_s", 0) or 0 for r in v02_results)
    wall_03 = sum(r.get("wall_s", 0) or 0 for r in v03_results)
    print(f"\nWall time: v0.2 = {wall_02:.0f}s, v0.3 = {wall_03:.0f}s "
          f"(ratio {wall_03/wall_02 if wall_02 > 0 else float('nan'):.2f}×)")


if __name__ == "__main__":
    main()
