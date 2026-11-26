# tests/unit_py/test_engine_io_ini.py
from pathlib import Path

from pylatkmc.engine.io_ini import parse_input_ini

REPO = Path(__file__).resolve().parents[2]
EXAMPLE_INI = REPO / "models/ni_fe_cr_v1/examples/input.ini"


def test_parse_example_input_ini():
    cfg = parse_input_ini(EXAMPLE_INI)
    assert cfg.max_steps == 100000
    assert cfg.sample_every == 100
    assert cfg.base_seed == 42
    assert cfg.temperature_K == 500.0
    assert cfg.initconfig_path == "config.kmcinit"
    # resolved relative to the INI directory
    assert cfg.initconfig_abs == (EXAMPLE_INI.parent / "config.kmcinit")
    assert cfg.output_root_abs == (EXAMPLE_INI.parent / "output")


def test_defaults_and_comment_stripping(tmp_path):
    ini = tmp_path / "x.ini"
    ini.write_text(
        "[run]\nbase_seed = 7  # the seed\n[physics]\ntemperature_K = 300\n",
        encoding="utf-8",
    )
    cfg = parse_input_ini(ini)
    assert cfg.base_seed == 7
    assert cfg.max_steps == 1000000  # default
    assert cfg.temperature_K == 300.0
