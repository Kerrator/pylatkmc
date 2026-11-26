import json
from pathlib import Path

import pytest

from pylatkmc.engine.runner import run

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml"
CATALOGUE = SPEC.parent / "generated" / "catalogue.json"
KMCINIT = REPO / "models/ni_fe_cr_v1/examples/config.kmcinit"

pytestmark = pytest.mark.skipif(
    not CATALOGUE.exists(),
    reason="needs committed generated/catalogue.json (run export-catalogue once)",
)


def test_run_two_replicas_produces_aggregate(tmp_path):
    ini = tmp_path / "input.ini"
    ini.write_text(
        "[run]\nmax_steps = 200\nsample_every = 0\nbase_seed = 42\n"
        "[paths]\n"
        f"initconfig_path = {KMCINIT}\n"
        f"output_root = {tmp_path / 'output'}\n"
        "[physics]\ntemperature_K = 500.0\n",
        encoding="utf-8",
    )
    agg_path = run(SPEC, ini, n_replicas=2)
    agg = json.loads(Path(agg_path).read_text())
    assert agg["n_replicas"] == 2
    assert agg["n_success"] == 2
    assert "mean_msd_A2_mean" in agg and "total_time_s_mean" in agg
    assert agg["total_time_s_mean"] > 0.0
    # determinism: same call → identical aggregate MSD
    agg2 = json.loads(Path(run(SPEC, ini, n_replicas=2)).read_text())
    assert agg2["mean_msd_A2_mean"] == agg["mean_msd_A2_mean"]
