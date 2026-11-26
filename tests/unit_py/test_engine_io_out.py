# tests/unit_py/test_engine_io_out.py
import json

from pylatkmc.engine.io_out import (
    aggregate_stats,
    write_aggregate_summary_json,
    write_summary_json,
)


def test_summary_json_has_expected_fields(tmp_path):
    p = tmp_path / "summary.json"
    write_summary_json(
        p, rank=0, n_sites=192, n_vac=1, temperature_K=500.0, base_seed=42,
        n_steps=100, total_time_s=1.23e-6, mean_msd_A2=4.5e0, run_rc=0, n_procs=358,
    )
    d = json.loads(p.read_text())
    assert d["rank"] == 0 and d["n_procs"] == 358
    assert d["mean_msd_A2"] == 4.5
    assert set(d) == {
        "rank", "n_sites", "n_vac", "temperature_K", "base_seed", "n_steps",
        "total_time_s", "mean_msd_A2", "run_rc", "n_procs",
    }


def test_aggregate_sample_std_and_keys(tmp_path):
    per = [
        {"rank": 0, "run_rc": 0, "n_steps": 100, "total_time_s": 1.0, "mean_msd_A2": 2.0},
        {"rank": 1, "run_rc": 0, "n_steps": 200, "total_time_s": 3.0, "mean_msd_A2": 4.0},
    ]
    agg = aggregate_stats(per)
    assert agg["n_replicas"] == 2 and agg["n_success"] == 2 and agg["n_failed"] == 0
    assert agg["mean_msd_A2_mean"] == 3.0
    # sample std (N-1) of [2,4] = sqrt(2) ~ 1.4142
    assert abs(agg["mean_msd_A2_std"] - 1.4142135623730951) < 1e-9
    p = tmp_path / "aggregate_summary.json"
    write_aggregate_summary_json(p, agg)
    back = json.loads(p.read_text())
    assert len(back["replicas"]) == 2
