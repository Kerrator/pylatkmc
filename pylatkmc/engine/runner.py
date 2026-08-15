# pylatkmc/engine/runner.py
"""Orchestrate a Python-engine run: load model + lattice, loop replicas, write outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pylatkmc.engine.catalogue import CompiledProcess, compile_catalogue, load_catalogue
from pylatkmc.engine.executor import step_once
from pylatkmc.engine.io_ini import RunConfig, parse_input_ini
from pylatkmc.engine.io_out import (
    aggregate_stats,
    write_aggregate_summary_json,
    write_summary_json,
)
from pylatkmc.engine.lattice import Lattice, read_kmcinit
from pylatkmc.engine.rng import make_rng
from pylatkmc.engine.state import state_from_lattice
from pylatkmc.loader import load


def run_replica(
    lat: Lattice,
    compiled: list[CompiledProcess],
    cfg: RunConfig,
    rank: int,
    n_procs: int,
    out_dir: Path,
) -> dict[str, Any]:
    st = state_from_lattice(lat)
    rng = make_rng(cfg.base_seed, rank)
    run_rc = 0
    while st.step < cfg.max_steps:
        if cfg.max_time_s > 0.0 and st.time_s >= cfg.max_time_s:
            break
        if step_once(lat, st, compiled, rng) is None:
            break  # no events (trapped)
    rep_dir = out_dir / f"replica_{rank:04d}"
    rep_dir.mkdir(parents=True, exist_ok=True)
    write_summary_json(
        rep_dir / "summary.json",
        rank=rank, n_sites=lat.n_sites, n_vac=st.n_vac,
        temperature_K=cfg.temperature_K, base_seed=cfg.base_seed,
        n_steps=st.step, total_time_s=st.time_s, mean_msd_A2=st.mean_msd_A2(),
        run_rc=run_rc, n_procs=n_procs,
    )
    return {
        "rank": rank, "run_rc": run_rc, "n_steps": st.step,
        "total_time_s": st.time_s, "mean_msd_A2": st.mean_msd_A2(),
        "base_seed": cfg.base_seed, "temperature_K": cfg.temperature_K,
        "n_procs": n_procs,
    }


def run(
    spec_path: str | Path,
    input_ini: str | Path,
    n_replicas: int = 1,
    family_csv: str | Path | None = None,
) -> Path:
    spec_path = Path(spec_path).resolve()
    spec = load(spec_path)
    cfg = parse_input_ini(input_ini)
    lat = read_kmcinit(cfg.initconfig_abs)
    processes = load_catalogue(spec_path, family_csv=family_csv)
    compiled = compile_catalogue(processes, list(spec.species))
    n_procs = len(compiled)
    out_dir = cfg.output_root_abs
    out_dir.mkdir(parents=True, exist_ok=True)
    per = [
        run_replica(lat, compiled, cfg, rank, n_procs, out_dir)
        for rank in range(n_replicas)
    ]
    agg = aggregate_stats(per)
    agg_path = out_dir / "aggregate_summary.json"
    write_aggregate_summary_json(agg_path, agg)
    return agg_path
