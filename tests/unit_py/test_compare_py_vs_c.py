import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
import compare_py_vs_c as cmp  # noqa: E402


def test_diffusivity_and_relative_diff():
    assert cmp.diffusivity(6.0, 1.0) == 1.0
    assert cmp.diffusivity(1.0, 0.0) == 0.0
    assert cmp.relative_diff(1.0, 1.0) == 0.0
    assert abs(cmp.relative_diff(1.0, 1.1) - 0.0909090909) < 1e-6


def test_compare_passes_within_tol_fails_outside():
    py = {"mean_msd_A2_mean": 6.0, "total_time_s_mean": 1.0}
    c_ok = {"mean_msd_A2_mean": 6.3, "total_time_s_mean": 1.0}
    c_bad = {"mean_msd_A2_mean": 12.0, "total_time_s_mean": 1.0}
    ok, _ = cmp.compare(py, c_ok, tol=0.10)
    assert ok is True
    bad, _ = cmp.compare(py, c_bad, tol=0.10)
    assert bad is False
