# pylatkmc/engine/io_out.py
"""Output writers compatible with the C runtime's summary / aggregate JSON
(runtime/src/mpi/replica.c), so existing tools/compare_*.py work unchanged."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def write_summary_json(
    path: str | Path,
    *,
    rank: int,
    n_sites: int,
    n_vac: int,
    temperature_K: float,
    base_seed: int,
    n_steps: int,
    total_time_s: float,
    mean_msd_A2: float,
    run_rc: int,
    n_procs: int,
) -> None:
    d = {
        "rank": rank,
        "n_sites": n_sites,
        "n_vac": n_vac,
        "temperature_K": temperature_K,
        "base_seed": base_seed,
        "n_steps": n_steps,
        "total_time_s": total_time_s,
        "mean_msd_A2": mean_msd_A2,
        "run_rc": run_rc,
        "n_procs": n_procs,
    }
    Path(path).write_text(json.dumps(d, indent=2), encoding="utf-8")


def _mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean = sum(xs) / n
    if n <= 1:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)  # sample std (N-1)
    return mean, math.sqrt(var)


def aggregate_stats(per_replica: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(per_replica)
    n_success = sum(1 for r in per_replica if r["run_rc"] == 0)
    steps_mean, steps_std = _mean_std([float(r["n_steps"]) for r in per_replica])
    t_mean, t_std = _mean_std([float(r["total_time_s"]) for r in per_replica])
    m_mean, m_std = _mean_std([float(r["mean_msd_A2"]) for r in per_replica])
    return {
        "n_replicas": n,
        "n_success": n_success,
        "n_failed": n - n_success,
        "base_seed": per_replica[0].get("base_seed", 0) if per_replica else 0,
        "temperature_K": per_replica[0].get("temperature_K", 0.0) if per_replica else 0.0,
        "n_procs": per_replica[0].get("n_procs", 0) if per_replica else 0,
        "n_steps_mean": steps_mean,
        "n_steps_std": steps_std,
        "total_time_s_mean": t_mean,
        "total_time_s_std": t_std,
        "mean_msd_A2_mean": m_mean,
        "mean_msd_A2_std": m_std,
        "replicas": [
            {
                "rank": r["rank"],
                "run_rc": r["run_rc"],
                "n_steps": r["n_steps"],
                "total_time_s": r["total_time_s"],
                "mean_msd_A2": r["mean_msd_A2"],
            }
            for r in per_replica
        ],
    }


def write_aggregate_summary_json(path: str | Path, agg: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(agg, indent=2), encoding="utf-8")
