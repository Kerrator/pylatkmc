"""MPI-level regression tests for replica failure handling (large-system-scaling WP1).

Builds ni_example from its COMMITTED proclist (CMake, Release, -j2, temp
build dir) and launches it with at most 2 ranks:

- 01: a replica whose setup fails is counted as failed in
  aggregate_summary.json and the job exits non-zero; a replica that traps (no
  event left — a normal physical end) still exits 0.

Every launch gets a private TMPDIR / OMPI_MCA_orte_tmpdir_base (an Open MPI
singleton sharing /tmp/ompi.* can disturb unrelated jobs) and a hard timeout
that tears the whole job down. Skipped without cmake / mpirun.
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
NI_SLAB_0VAC = REPO_ROOT / "models" / "ni_dissolution_demo" / "examples" / "slab_ni_0vac.kmcinit"


@pytest.fixture(scope="module")
def mpi_env() -> Iterator[dict[str, str]]:
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun not on PATH")
    # Short private dir: Open MPI puts Unix sockets under it (paths capped at
    # 104 bytes on macOS, whose default TMPDIR is already long).
    darwin = os.uname().sysname == "Darwin"
    tmp = tempfile.mkdtemp(prefix="plk-ompi-", dir="/tmp" if darwin else None)
    env = {**os.environ, "TMPDIR": tmp, "OMPI_MCA_orte_tmpdir_base": tmp, "OMP_NUM_THREADS": "1"}
    probe = _mpirun([(Path(shutil.which("true") or "/usr/bin/true"), Path("probe"))], env, 60.0)
    if probe is None or probe.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        pytest.skip(f"mpirun cannot launch a trivial job here: {probe and probe.stderr[:200]}")
    yield env
    shutil.rmtree(tmp, ignore_errors=True)


def _build(model: str, tmp: Path) -> Path:
    if shutil.which("cmake") is None:
        pytest.skip("cmake not on PATH")
    build = tmp / f"build_{model}"
    cfg = subprocess.run(
        [
            "cmake",
            "-S",
            str(REPO_ROOT),
            "-B",
            str(build),
            f"-DMODEL={model}",
            "-DCMAKE_BUILD_TYPE=Release",
        ],
        capture_output=True,
        text=True,
    )
    if cfg.returncode != 0:
        if "MPI" in cfg.stderr:
            pytest.skip(f"MPI not available: {cfg.stderr[:200]}")
        raise AssertionError(f"cmake configure failed:\n{cfg.stdout}\n{cfg.stderr}")
    bld = subprocess.run(
        ["cmake", "--build", str(build), "-j", "2"], capture_output=True, text=True
    )
    assert bld.returncode == 0, f"cmake build failed:\n{bld.stdout}\n{bld.stderr}"
    binary = build / f"pylatkmc_{model}"
    assert binary.is_file()
    return binary


@pytest.fixture(scope="module")
def ni_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build("ni_example", tmp_path_factory.mktemp("ni"))


def _kill_session(sid: int) -> None:
    """SIGKILL whatever is left in mpirun's session (Linux /proc only): Open MPI
    gives each rank its own process group, so killpg(mpirun) would miss them."""
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
            if int(fields[3]) == sid:  # state ppid pgrp SESSION ...
                os.kill(int(stat.parent.name), signal.SIGKILL)
        except (OSError, IndexError, ValueError):
            continue


def _mpirun(
    apps: list[tuple[Path, Path]], env: dict[str, str], timeout: float = 120.0
) -> subprocess.CompletedProcess[str] | None:
    """Launch one 1-rank app context per (binary, ini) — MPMD, so ranks can get
    different inputs. Returns None on timeout, after tearing the job down."""
    cmd = ["mpirun", "--oversubscribe", "--bind-to", "none"]
    for i, (binary, ini) in enumerate(apps):
        cmd += ([":"] if i else []) + ["-n", "1", str(binary), str(ini)]
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.terminate()  # mpirun forwards SIGTERM to its ranks
        try:
            proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        _kill_session(proc.pid)
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def _ini(
    path: Path,
    initconfig: Path,
    output_root: Path,
    *,
    max_steps: int = 200,
    sample_every: int = 100,
    temperature_K: float = 500.0,
) -> Path:
    path.write_text(
        "[run]\n"
        f"max_steps = {max_steps}\n"
        f"sample_every = {sample_every}\n"
        "base_seed = 7\n"
        "[paths]\n"
        f"initconfig_path = {initconfig}\n"
        f"output_root = {output_root}\n"
        "[physics]\n"
        f"temperature_K = {temperature_K}\n"
    )
    return path


def _aggregate(output_root: Path) -> dict:
    return json.loads((output_root / "aggregate_summary.json").read_text())


# ---------------------------------------------------------------------------
# 01 — setup failures are failures; traps and completions exit 0
# ---------------------------------------------------------------------------


def test_setup_failure_counts_as_failed_and_exits_nonzero(
    ni_binary: Path, mpi_env: dict[str, str], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    ini = _ini(tmp_path / "in.ini", tmp_path / "missing.kmcinit", out)
    res = _mpirun([(ni_binary, ini)] * 2, mpi_env)
    assert res is not None, "job hung"
    assert res.returncode != 0, res.stderr
    agg = _aggregate(out)
    assert (agg["n_success"], agg["n_failed"]) == (0, 2)
    assert [r["run_rc"] for r in agg["replicas"]] == [-errno.ENOENT] * 2


@pytest.mark.parametrize(
    ("slab", "run_rc"),
    [(NI_SLAB_1VAC, 0), (NI_SLAB_0VAC, -errno.ENODATA)],
    ids=["completes", "traps"],
)
def test_completed_or_trapped_run_exits_zero(
    ni_binary: Path, mpi_env: dict[str, str], tmp_path: Path, slab: Path, run_rc: int
) -> None:
    """A trap (vacancy-free slab: no hop can fire) is a physical end, not a
    failure of the job — job queues treat any non-zero exit as a failed run."""
    if not slab.is_file():
        pytest.skip(f"example slab missing: {slab}")
    out = tmp_path / "out"
    res = _mpirun([(ni_binary, _ini(tmp_path / "in.ini", slab, out))] * 2, mpi_env)
    assert res is not None, "job hung"
    assert res.returncode == 0, res.stderr
    assert [r["run_rc"] for r in _aggregate(out)["replicas"]] == [run_rc] * 2
