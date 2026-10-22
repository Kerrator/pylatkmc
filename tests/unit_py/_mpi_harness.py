"""Build a model from its COMMITTED proclist and launch it under mpirun, safely.

Shared by the tests that run real binaries (test_mpi_failure_modes,
test_trajectory_cadence). Every launch gets a private, short TMPDIR /
OMPI_MCA_orte_tmpdir_base (an Open MPI singleton sharing /tmp/ompi.* can
disturb unrelated jobs) and a hard timeout that tears the whole job down, so a
hang fails the test instead of blocking the suite; MPIEXEC_TIMEOUT is a
backstop should the test process die mid-launch. Missing mpirun / cmake / an
MPI toolchain skips the calling test.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
LAUNCH_TIMEOUT_S = 120.0


def teardown(proc: subprocess.Popen[str]) -> None:
    """Tear down a job that outlived its timeout. On Linux, SIGKILL every
    process in mpirun's session while mpirun is still unreaped (so the session
    id cannot have been reused): Open MPI gives each rank its own process
    group, so killing mpirun alone would orphan them. Elsewhere, ask mpirun to
    forward SIGTERM to its ranks."""
    if Path("/proc/self/stat").exists():
        for stat in Path("/proc").glob("[0-9]*/stat"):
            try:
                fields = stat.read_text().rsplit(")", 1)[1].split()
                if int(fields[3]) == proc.pid:  # state ppid pgrp SESSION ...
                    os.kill(int(stat.parent.name), signal.SIGKILL)
            except (OSError, IndexError, ValueError):
                continue
    else:
        proc.terminate()
    try:
        proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def mpirun(
    apps: list[tuple[Path, Path]], env: dict[str, str], timeout: float = LAUNCH_TIMEOUT_S
) -> subprocess.CompletedProcess[str] | None:
    """Launch one single-rank app context per (binary, ini): MPMD, so ranks can
    get different inputs. Returns None if the job outlived ``timeout``, after
    tearing it down."""
    cmd = ["mpirun", "--oversubscribe", "--bind-to", "none"]
    for i, (binary, ini) in enumerate(apps):
        cmd += ([":"] if i else []) + ["-n", "1", str(binary), str(ini)]
    proc = subprocess.Popen(
        cmd,
        env={**env, "MPIEXEC_TIMEOUT": str(int(timeout) + 30)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        teardown(proc)
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def private_mpi_env() -> Iterator[dict[str, str]]:
    """Body of a module-scoped ``mpi_env`` fixture (``yield from`` it): the
    environment for every launch, with its own TMPDIR, removed afterwards.
    Skips when mpirun is missing or cannot launch a trivial job."""
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun not on PATH")
    # A short private dir: Open MPI puts Unix sockets under it (paths are
    # capped at 104 bytes on macOS, whose default TMPDIR is already long).
    darwin = os.uname().sysname == "Darwin"
    tmp = tempfile.mkdtemp(prefix="plk-ompi-", dir="/tmp" if darwin else None)
    env = {
        **os.environ,
        "TMPDIR": tmp,
        "OMPI_MCA_orte_tmpdir_base": tmp,
        "OMP_NUM_THREADS": "1",
    }
    probe = mpirun([(Path(shutil.which("true") or "/usr/bin/true"), Path("probe"))], env, 60.0)
    if probe is None or probe.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        pytest.skip(f"mpirun cannot launch a trivial job here: {probe and probe.stderr[:200]}")
    yield env
    shutil.rmtree(tmp, ignore_errors=True)


def build_model(model: str, tmp: Path) -> Path:
    """CMake Release build (-j2) of ``model`` into ``tmp``; the binary's path."""
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
    assert binary.is_file(), f"expected binary at {binary}"
    return binary
