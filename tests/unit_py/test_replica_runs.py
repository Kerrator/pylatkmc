"""Binary-level tests: replica startup, process exit status, and the logged k_tot.

Builds models with CMake (into pytest tmp dirs) and launches each case with
`mpirun -n 2` (large-system-scaling WP1):

- ni_example: a completed run and a trapped run (no event left, a normal
  physical end) exit 0, since job queues treat any non-zero exit as a failed
  job; a setup failure (missing .kmcinit) is counted as failed in
  aggregate_summary.json and exits non-zero (01).
- ni_example: one rank failing replica_init makes every rank exit non-zero
  promptly, instead of the others blocking in MPI collectives until walltime
  (02).
- nicr_v2_scratch (surrogate build): pykmc.out's k_tot is the total rate each
  dt was drawn from, surrogate channel included (04).
- nicr_v2_scratch: a box whose periodic in-plane axis is shorter than
  2*reach+1 grid cells is refused at startup (05).

Skips without cmake / MPI / mpirun (and numpy for the v2 boxes). Every launch
gets a private TMPDIR + OMPI_MCA_orte_tmpdir_base, two ranks, and
MPIEXEC_TIMEOUT, so a hang fails the test and mpirun reaps its own ranks.
"""

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
NI_SLAB_0VAC = REPO_ROOT / "models" / "ni_dissolution_demo" / "examples" / "slab_ni_0vac.kmcinit"
NICR_PROCLIST_H = REPO_ROOT / "models" / "nicr_v2_scratch" / "generated" / "proclist.h"
BUILD_INITIAL_CONFIG = REPO_ROOT / "tools" / "build_initial_config.py"
LAUNCH_TIMEOUT_S = 60


def _build(model: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    for tool in ("cmake", "mpirun"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not on PATH")
    build_dir = tmp_path_factory.mktemp(f"build_{model}")
    cfg = subprocess.run(
        ["cmake", "-B", str(build_dir), "-S", str(REPO_ROOT), f"-DMODEL={model}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if cfg.returncode != 0:
        if "MPI" in cfg.stderr:
            pytest.skip(f"MPI not available: {cfg.stderr[:200]}")
        raise AssertionError(f"cmake configure failed:\n{cfg.stdout}\n{cfg.stderr}")
    bld = subprocess.run(
        ["cmake", "--build", str(build_dir), "-j", "2"],
        capture_output=True,
        text=True,
        check=False,
    )
    if bld.returncode != 0:
        raise AssertionError(f"cmake build failed:\n{bld.stdout}\n{bld.stderr}")
    binary = build_dir / f"pylatkmc_{model}"
    assert binary.is_file(), f"expected binary at {binary}"
    return binary


@pytest.fixture(scope="module")
def ni_example_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build("ni_example", tmp_path_factory)


@pytest.fixture(scope="module")
def nicr_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build("nicr_v2_scratch", tmp_path_factory)


def _ini(
    tmp_path: Path, initconfig: Path, *, max_steps: int = 20, temperature_K: float = 500.0
) -> Path:
    ini = tmp_path / "input.ini"
    ini.write_text(
        "[run]\n"
        f"max_steps = {max_steps}\n"
        "sample_every = 1\n"
        "base_seed = 7\n"
        "[paths]\n"
        f"initconfig_path = {initconfig}\n"
        f"output_root = {tmp_path / 'out'}\n"
        "[physics]\n"
        f"temperature_K = {temperature_K}\n"
    )
    return ini


def _launch(binary: Path, ini: Path) -> tuple[subprocess.CompletedProcess[str], float]:
    """`mpirun -n 2` with a private Open MPI tmpdir; returns (result, wall seconds).

    MPIEXEC_TIMEOUT makes mpirun abort a hung job and reap its ranks (each rank
    runs in its own process group, so killing mpirun alone would orphan them);
    the subprocess timeout is only a backstop.
    """
    ompi_tmp = tempfile.mkdtemp(prefix="plk-ompi-")  # short path: OMPI puts sockets under it
    env = {
        **os.environ,
        "TMPDIR": ompi_tmp,
        "OMPI_MCA_orte_tmpdir_base": ompi_tmp,
        "MPIEXEC_TIMEOUT": str(LAUNCH_TIMEOUT_S),
    }
    cmd = ["mpirun", "-n", "2", "--bind-to", "none", "--oversubscribe", str(binary), str(ini)]
    t0 = time.monotonic()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=LAUNCH_TIMEOUT_S + 60,
            check=False,
        )
    finally:
        shutil.rmtree(ompi_tmp, ignore_errors=True)
    out = ini.parent / "out"
    if res.returncode != 0 and not (out / "replica_0000").is_dir():
        pytest.skip(f"mpirun could not launch the binary here:\n{res.stderr[-600:]}")
    return res, time.monotonic() - t0


def _aggregate(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "out" / "aggregate_summary.json").read_text())


def _log_rows(tmp_path: Path) -> list[list[str]]:
    """Data rows of every replica's pykmc.out
    (`step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site`)."""
    rows = []
    for log in sorted((tmp_path / "out").glob("replica_*/pykmc.out")):
        for line in log.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                rows.append(line.split())
    return rows


def _assert_k_tot_is_the_dt_rate(rows: list[list[str]]) -> None:
    """dt = -log(r2) / r_tot, so dt * k_tot must be a positive Exp(1) draw on
    every row (mean ~1) when k_tot is the total rate dt was drawn from."""
    products = [float(r[2]) * float(r[4]) for r in rows]
    assert products, "no logged steps"
    assert min(products) > 0.0, "a logged k_tot is not the rate its dt was drawn from"
    mean = sum(products) / len(products)
    assert 0.75 < mean < 1.3, f"mean dt*k_tot = {mean:.3f}, expected ~1"


def _nicr_reach() -> tuple[int, int]:
    hdr = NICR_PROCLIST_H.read_text()
    ij = re.search(r"#define PYLATKMC_V2_MAX_REACH_IJ (\d+)", hdr)
    k = re.search(r"#define PYLATKMC_V2_MAX_REACH_K (\d+)", hdr)
    assert ij and k, "nicr_v2_scratch proclist.h lacks the v2 reach macros"
    return int(ij.group(1)), int(k.group(1))


def _nicr_box(tmp_path: Path, n_surface: int) -> Path:
    """Random Ni90Cr10 slab, n_surface x n_surface (grid_nx = grid_ny = 2*n),
    vacuum thicker than the axial reach so only the in-plane axes can fail."""
    pytest.importorskip("numpy")
    _, reach_k = _nicr_reach()
    out = tmp_path / f"box_{n_surface}.kmcinit"
    res = subprocess.run(
        [
            sys.executable,
            str(BUILD_INITIAL_CONFIG),
            "--nx",
            str(n_surface),
            "--ny",
            str(n_surface),
            "--nz",
            "10",
            "--composition",
            "Ni90_Cr10",
            "--n-vacancies",
            "4",
            "--vacuum-layers",
            str(reach_k + 3),
            "--seed",
            "7",
            "-o",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"build_initial_config.py failed:\n{res.stderr}"
    return out


def test_completed_run_exits_zero(ni_example_bin: Path, tmp_path: Path) -> None:
    res, _ = _launch(ni_example_bin, _ini(tmp_path, NI_SLAB_1VAC, max_steps=200))
    assert res.returncode == 0, res.stderr
    agg = _aggregate(tmp_path)
    assert (agg["n_success"], agg["n_failed"]) == (2, 0)
    # Without a surrogate channel k_tot is the measured r_tot, as before.
    _assert_k_tot_is_the_dt_rate(_log_rows(tmp_path))


def test_trapped_run_exits_zero(ni_example_bin: Path, tmp_path: Path) -> None:
    """No event left (vacancy-free slab, hops only) is a normal physical end:
    run_rc = -ENODATA in the summaries, but the job itself succeeded."""
    res, _ = _launch(ni_example_bin, _ini(tmp_path, NI_SLAB_0VAC))
    assert res.returncode == 0, res.stderr
    assert [r["run_rc"] for r in _aggregate(tmp_path)["replicas"]] == [-errno.ENODATA] * 2


def test_setup_failure_counts_as_failed_and_exits_nonzero(
    ni_example_bin: Path, tmp_path: Path
) -> None:
    res, _ = _launch(ni_example_bin, _ini(tmp_path, tmp_path / "missing.kmcinit"))
    assert res.returncode != 0
    agg = _aggregate(tmp_path)
    assert (agg["n_success"], agg["n_failed"]) == (0, 2)
    assert [r["run_rc"] for r in agg["replicas"]] == [-errno.ENOENT] * 2


def test_init_failure_on_one_rank_fails_every_rank_promptly(
    ni_example_bin: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "replica_0001").write_text("")  # a file where rank 1's replica dir must go
    res, wall = _launch(ni_example_bin, _ini(tmp_path, NI_SLAB_1VAC))
    assert wall < LAUNCH_TIMEOUT_S, "job hung: the healthy rank blocked in an MPI collective"
    assert res.returncode != 0
    assert "[rank 1] replica_init failed" in res.stderr
    assert not (out / "replica_0000" / "pykmc.out").exists(), "rank 0 ran without rank 1"


def test_surrogate_build_logs_total_rate(nicr_bin: Path, tmp_path: Path) -> None:
    """Random NiCr fires mostly through the surrogate channel, where k_tot used
    to log the measured channel only (0.0 on surrogate-only steps); it must be
    the total rate dt was drawn from. The box is one cell pair wider than
    2*reach so the v2 startup geometry checks accept it."""
    reach_ij, _ = _nicr_reach()
    box = _nicr_box(tmp_path, reach_ij + 1)
    res, _ = _launch(nicr_bin, _ini(tmp_path, box, max_steps=200, temperature_K=600.0))
    assert res.returncode == 0, res.stderr
    rows = _log_rows(tmp_path)
    assert any(r[7] == "-1" for r in rows), "no surrogate-channel step was exercised"
    _assert_k_tot_is_the_dt_rate(rows)


def test_short_periodic_axis_is_refused_at_startup(nicr_bin: Path, tmp_path: Path) -> None:
    """grid_nx = 2*reach < 2*reach+1: offsets +reach and -reach alias onto one
    site (the 8x8-surface case for reach 8), so refuse before any output."""
    reach_ij, _ = _nicr_reach()
    res, _ = _launch(nicr_bin, _ini(tmp_path, _nicr_box(tmp_path, reach_ij), temperature_K=600.0))
    assert res.returncode != 0
    assert "periodic" in res.stderr and "reach" in res.stderr
    assert not _log_rows(tmp_path)
