"""Unit tests for the comparison-grid Phase 1 + Phase 2 helpers.

Builds tiny on-disk fixtures (synthetic ``summary.json`` and
``aggregate_summary.json``) so we can assert the loaders, the D
computation, the per-vac → mean reconciliation, and the time-aligned
n_steps_target estimator without depending on real sim data.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

# Make `tools/` importable.
TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))


# ---------------------------------------------------------------------------
# compute_D
# ---------------------------------------------------------------------------


def test_compute_D_3D_formula() -> None:
    from compare_grid_vs_pykmc import compute_D

    # MSD = 6, t = 1 → D = 1
    assert compute_D(6.0, 1.0) == pytest.approx(1.0)
    # MSD = 1200, t = 0.04 → D = 1200/(6*0.04) = 5000
    assert compute_D(1200.0, 0.04) == pytest.approx(5000.0)


def test_compute_D_returns_nan_for_zero_time() -> None:
    from compare_grid_vs_pykmc import compute_D

    assert math.isnan(compute_D(123.4, 0.0))
    assert math.isnan(compute_D(0.0, 0.0))
    assert math.isnan(compute_D(123.4, -1.0))


# ---------------------------------------------------------------------------
# pyKMC per-vac → mean reconciliation
# ---------------------------------------------------------------------------


def _write_pykmc_summary(path: Path, msd_final: list[float], t_end: float, n_events: int = 10) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {
                "dirname": str(path.parent),
                "temperature": 500.0,
                "n_vacancies": len(msd_final),
                "n_frames": 2001,
                "total_sim_time": t_end,
                "n_events": n_events,
                "msd_final": msd_final,
                "msd_max": [m * 1.5 for m in msd_final],
            },
            f,
        )


def _write_pylat_aggregate(
    path: Path, msd_mean: float, msd_std: float, t_end: float, n_replicas: int = 4, n_steps: int = 500_000
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {
                "n_replicas": n_replicas,
                "n_success": n_replicas,
                "temperature_K": 500.0,
                "n_steps_mean": n_steps,
                "total_time_s_mean": t_end,
                "mean_msd_A2_mean": msd_mean,
                "mean_msd_A2_std": msd_std,
            },
            f,
        )


def test_pykmc_row_mean_and_sem(tmp_path: Path) -> None:
    """msd_final = [10, 20, 30] → mean = 20, sem = std/sqrt(3) where std
    is the sample standard deviation."""
    from sim_discovery_dual import DualCell

    summary_path = tmp_path / "fake" / "analysis" / "summary.json"
    _write_pykmc_summary(summary_path, [10.0, 20.0, 30.0], t_end=1e-3)

    # Hand-build a SimInfo that points at the fake path. We can't easily
    # build a real SimInfo, but pykmc_row only needs the cell's
    # pykmc_summary_path property — which is derived. Instead, monkey-
    # patch via direct DualCell construction.
    class _FakeSim:
        path = tmp_path / "fake"

    cell = DualCell(
        composition="100Ni",
        n_vacancies=3,
        temperature_K=500.0,
        pykmc_sim=_FakeSim(),  # type: ignore[arg-type]
        pylat_path=None,
    )
    assert cell.pykmc_summary_path == summary_path

    from compare_grid_vs_pykmc import pykmc_row

    row = pykmc_row(cell)
    assert row is not None
    assert row.MSD_A2 == pytest.approx(20.0)
    # sample std of [10, 20, 30] = sqrt(((10-20)^2+(20-20)^2+(30-20)^2)/2) = sqrt(100) = 10
    # sem = 10 / sqrt(3) ≈ 5.77
    assert row.MSD_sem == pytest.approx(10.0 / math.sqrt(3), rel=1e-6)
    assert row.error_kind == "within_traj_per_vac"
    assert row.D_A2_per_s == pytest.approx(20.0 / (6.0 * 1e-3))


def test_pykmc_row_returns_none_for_zero_events(tmp_path: Path) -> None:
    """When pyKMC fired 0 events, msd_final = [0.0]; pykmc_row should
    return a valid Row with MSD = 0 (let the heatmap mark it as "—")."""
    from sim_discovery_dual import DualCell

    summary_path = tmp_path / "fake" / "analysis" / "summary.json"
    _write_pykmc_summary(summary_path, [0.0], t_end=0.5, n_events=0)

    class _FakeSim:
        path = tmp_path / "fake"

    cell = DualCell("100Ni", 1, 300.0, _FakeSim(), None)  # type: ignore[arg-type]
    from compare_grid_vs_pykmc import pykmc_row

    row = pykmc_row(cell)
    # We KEEP the row (even with MSD=0) so the heatmap can still render
    # the cell as "no events" rather than "missing data".
    assert row is not None
    assert row.MSD_A2 == 0.0
    assert row.D_A2_per_s == 0.0


# ---------------------------------------------------------------------------
# pylatkmc loader + SEM
# ---------------------------------------------------------------------------


def test_pylat_row_sem_uses_replica_count(tmp_path: Path) -> None:
    from sim_discovery_dual import DualCell

    cell_dir = tmp_path / "pl"
    _write_pylat_aggregate(cell_dir / "aggregate_summary.json", msd_mean=1000.0, msd_std=100.0, t_end=0.04, n_replicas=4)
    cell = DualCell("100Ni", 1, 500.0, None, cell_dir)
    from compare_grid_vs_pykmc import pylat_row

    row = pylat_row(cell)
    assert row is not None
    assert row.MSD_A2 == pytest.approx(1000.0)
    # sem = 100 / sqrt(4) = 50
    assert row.MSD_sem == pytest.approx(50.0)
    assert row.n_replicas == 4
    assert row.error_kind == "across_replica"


# ---------------------------------------------------------------------------
# Phase 2 estimator
# ---------------------------------------------------------------------------


def _write_full_pair(
    tmp_path: Path,
    t_pk: float,
    t_pl: float,
    n_events: int = 10,
    msd_final: list[float] | None = None,
    n_frames: int = 2001,
) -> "DualCell":
    """Helper: write a paired (pyKMC, pylatkmc) cell with arbitrary t_end values."""
    from sim_discovery_dual import DualCell

    pk_dir = tmp_path / "pk"
    if msd_final is None:
        msd_final = [12.0, 18.0]
    summary_path = pk_dir / "analysis" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(
            {
                "dirname": str(summary_path.parent),
                "temperature": 500.0,
                "n_vacancies": len(msd_final),
                "n_frames": n_frames,
                "total_sim_time": t_pk,
                "n_events": n_events,
                "msd_final": msd_final,
                "msd_max": [m * 1.5 for m in msd_final],
            },
            f,
        )
    pl_dir = tmp_path / "pl"
    _write_pylat_aggregate(pl_dir / "aggregate_summary.json", msd_mean=2.0e6, msd_std=1e5, t_end=t_pl, n_steps=500_000)

    class _FakeSim:
        path = pk_dir

    return DualCell("100Ni", 2, 500.0, _FakeSim(), pl_dir)  # type: ignore[arg-type]


def test_plan_cell_skips_zero_events(tmp_path: Path) -> None:
    """msd_final == [0, 0] with n_events=0 should be skipped (no MSD signal)."""
    from timealigned_sweep import plan_cell

    cell = _write_full_pair(tmp_path, t_pk=0.5, t_pl=0.04, n_events=0, msd_final=[0.0, 0.0])
    plan = plan_cell(cell)
    assert not plan.is_runnable
    assert "0 events" in plan.skip_reason or "zero" in plan.skip_reason.lower()


def test_plan_cell_skips_truncated_trajectory(tmp_path: Path) -> None:
    """msd == 0 with n_frames == 1 means the trajectory was clipped; skip
    with the truncation-specific reason."""
    from timealigned_sweep import plan_cell

    cell = _write_full_pair(
        tmp_path, t_pk=0.5, t_pl=0.04, n_events=7, msd_final=[0.0], n_frames=1
    )
    plan = plan_cell(cell)
    assert not plan.is_runnable
    assert "under-sampled" in plan.skip_reason
    assert "7 events" in plan.skip_reason


def test_plan_cell_skips_when_pykmc_ahead(tmp_path: Path) -> None:
    from timealigned_sweep import plan_cell

    # pylatkmc finishes earlier than pyKMC → cannot truncate.
    cell = _write_full_pair(tmp_path, t_pk=10.0, t_pl=0.001)
    plan = plan_cell(cell)
    assert not plan.is_runnable
    assert "pyKMC ahead" in plan.skip_reason


def test_plan_cell_runnable_when_pylat_ahead(tmp_path: Path) -> None:
    from timealigned_sweep import plan_cell

    # pylatkmc reached 0.04 s, pyKMC reached 4.8e-5 → re-run pylatkmc to t_pyKMC * 1.05.
    cell = _write_full_pair(tmp_path, t_pk=4.8e-5, t_pl=0.04)
    plan = plan_cell(cell)
    assert plan.is_runnable
    assert plan.t_target_s == pytest.approx(4.8e-5 * 1.05)
    # n_steps target should be roughly t_target / dt_avg_existing
    # dt_avg = 0.04 / 500_000 = 8e-8
    # n_steps = ceil(5.04e-5 / 8e-8) = ceil(630) = 630
    assert 600 <= plan.n_steps_target <= 700


def test_plan_cell_caps_at_n_steps_max(tmp_path: Path) -> None:
    """If t_target requires > N_STEPS_CAP steps at the existing dt, we cap."""
    from timealigned_sweep import N_STEPS_CAP, plan_cell

    # pylatkmc t_pl = 10.0, n_steps_mean = 500k → dt_avg = 2e-5 s/step.
    # t_pk = 50.0 → t_target = 52.5 → n_steps_est = 2.625e6 → caps at N_STEPS_CAP.
    # We also need pylatkmc ahead in time, so t_pl > t_pk: bump t_pl to 100.
    cell = _write_full_pair(tmp_path, t_pk=50.0, t_pl=100.0)
    plan = plan_cell(cell)
    assert plan.is_runnable
    assert plan.n_steps_target == N_STEPS_CAP


def test_plan_cell_floor(tmp_path: Path) -> None:
    """If t_target * 1.05 / dt_avg is small, we still allocate at least
    the floor of N_STEPS_FLOOR steps."""
    from timealigned_sweep import N_STEPS_FLOOR, plan_cell

    # pyKMC reached 1e-12 s; pylatkmc dt_avg = 8e-8 → bare 1 step needed
    # but we floor at N_STEPS_FLOOR.
    cell = _write_full_pair(tmp_path, t_pk=1e-12, t_pl=0.04)
    plan = plan_cell(cell)
    assert plan.is_runnable
    assert plan.n_steps_target >= N_STEPS_FLOOR


# ---------------------------------------------------------------------------
# DualCell coloring glob (smoke against real disk; trivially skipped if
# the user's research dir layout isn't there).
# ---------------------------------------------------------------------------


def test_dual_cells_pair_real_data() -> None:
    from sim_discovery_dual import find_dual_cells

    cells = find_dual_cells()
    if not cells:
        pytest.skip("No real dual-cell data on this machine")
    # Both `full` and `NiAlH_full` (and `NiAlH`) are valid coloring names; ensure
    # the walker found at least some coverage of all 8 temperatures.
    Ts = sorted({c.temperature_K for c in cells})
    assert len(Ts) >= 5, f"expected coverage across 5+ temperatures, got {Ts}"
    n_complete = sum(1 for c in cells if c.is_complete)
    assert n_complete >= 50, f"too few complete pairs: {n_complete}"
