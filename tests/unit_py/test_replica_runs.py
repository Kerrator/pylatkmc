"""Binary-level tests: replica startup and process exit status.

Builds models with CMake (into pytest tmp dirs) and launches each case with
`mpirun -n 2` (large-system-scaling WP1):

- ni_example: a completed run and a trapped run (no event left, a normal
  physical end) exit 0, since job queues treat any non-zero exit as a failed
  job; a setup failure (missing .kmcinit) is counted as failed in
  aggregate_summary.json and exits non-zero (01).

Skips without cmake / MPI / mpirun. Every launch gets a private TMPDIR +
OMPI_MCA_orte_tmpdir_base, two ranks, and MPIEXEC_TIMEOUT, so a hang fails
the test and mpirun reaps its own ranks.
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
NI_SLAB_0VAC = REPO_ROOT / "models" / "ni_dissolution_demo" / "examples" / "slab_ni_0vac.kmcinit"
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


def test_completed_run_exits_zero(ni_example_bin: Path, tmp_path: Path) -> None:
    res, _ = _launch(ni_example_bin, _ini(tmp_path, NI_SLAB_1VAC, max_steps=200))
    assert res.returncode == 0, res.stderr
    agg = _aggregate(tmp_path)
    assert (agg["n_success"], agg["n_failed"]) == (2, 0)


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
