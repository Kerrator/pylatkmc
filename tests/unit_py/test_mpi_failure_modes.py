"""MPI-level regression tests for replica failure handling (large-system-scaling WP1).

Builds models from their COMMITTED proclists (CMake Release, -j2, into pytest
temp dirs) and launches them with at most 2 ranks:

- 01: a replica whose setup fails is counted as failed in
  aggregate_summary.json and the job exits non-zero, also when only one rank
  fails; a replica that completes or traps (no event left, a normal physical
  end) still exits 0, because job queues mark any non-zero exit as a failed
  job.
- 02: when only ONE rank fails startup (input_config_load or replica_init),
  every rank terminates promptly with a non-zero exit and no replica runs,
  instead of the healthy rank hanging in the post-run collectives.

Every launch gets a private, short TMPDIR / OMPI_MCA_orte_tmpdir_base (an Open
MPI singleton sharing /tmp/ompi.* can disturb unrelated jobs) and a hard
timeout that tears the whole job down, so a hang fails the test instead of
blocking the suite; MPIEXEC_TIMEOUT is a backstop should the test process die
mid-launch. Skipped without mpirun / cmake / an MPI toolchain.
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

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
NI_SLAB_0VAC = REPO_ROOT / "models" / "ni_dissolution_demo" / "examples" / "slab_ni_0vac.kmcinit"
LAUNCH_TIMEOUT_S = 120.0


def _teardown(proc: subprocess.Popen[str]) -> None:
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


def _mpirun(
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
        _teardown(proc)
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


@pytest.fixture(scope="module")
def mpi_env() -> Iterator[dict[str, str]]:
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
    assert binary.is_file(), f"expected binary at {binary}"
    return binary


@pytest.fixture(scope="module")
def ni_binary(mpi_env: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build("ni_example", tmp_path_factory.mktemp("ni"))


def _ini(
    path: Path,
    initconfig: Path,
    output_root: Path,
    *,
    max_steps: int = 200,
    sample_every: int = 1,
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
# 01: setup failures are failures; traps and completions exit 0
# ---------------------------------------------------------------------------


def test_setup_failure_counts_as_failed_and_exits_nonzero(
    mpi_env: dict[str, str], ni_binary: Path, tmp_path: Path
) -> None:
    """A missing .kmcinit fails setup on both ranks. Before the fix run_rc
    stayed 0, the aggregate listed both ranks under n_success, exit 0."""
    out = tmp_path / "out"
    ini = _ini(tmp_path / "in.ini", tmp_path / "missing.kmcinit", out)
    res = _mpirun([(ni_binary, ini)] * 2, mpi_env)
    assert res is not None, "job hung"
    assert res.returncode != 0, res.stderr
    agg = _aggregate(out)
    assert (agg["n_success"], agg["n_failed"]) == (0, 2)
    assert [r["run_rc"] for r in agg["replicas"]] == [-errno.ENOENT] * 2
    assert "2 of 2 replicas failed" in res.stderr


def test_setup_failure_on_one_rank_is_counted_and_fails_the_job(
    mpi_env: dict[str, str], ni_binary: Path, tmp_path: Path
) -> None:
    """Uneven setup failure (the OOM-on-some-ranks scenario): rank 0 runs to
    completion, rank 1 cannot load its .kmcinit."""
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    out = tmp_path / "out"
    good = _ini(tmp_path / "good.ini", NI_SLAB_1VAC, out)
    bad = _ini(tmp_path / "bad.ini", tmp_path / "missing.kmcinit", out)
    res = _mpirun([(ni_binary, good), (ni_binary, bad)], mpi_env)
    assert res is not None, "job hung"
    assert res.returncode != 0, res.stderr
    agg = _aggregate(out)
    assert (agg["n_success"], agg["n_failed"]) == (1, 1)
    assert [r["run_rc"] for r in agg["replicas"]] == [0, -errno.ENOENT]
    assert (out / "replica_0000" / "pykmc.out").is_file()
    assert "[rank 1] replica_run failed" in res.stderr


@pytest.mark.parametrize(
    ("slab", "run_rc", "counts"),
    [(NI_SLAB_1VAC, 0, (2, 0)), (NI_SLAB_0VAC, -errno.ENODATA, (0, 2))],
    ids=["completes", "traps"],
)
def test_completed_or_trapped_run_exits_zero(
    mpi_env: dict[str, str],
    ni_binary: Path,
    tmp_path: Path,
    slab: Path,
    run_rc: int,
    counts: tuple[int, int],
) -> None:
    """A trap (vacancy-free slab: no hop can fire) is a physical end, not a job
    failure: job queues mark any non-zero exit as a failed run. The aggregate
    still lists a trapped replica under n_failed (unchanged semantics)."""
    if not slab.is_file():
        pytest.skip(f"example slab missing: {slab}")
    out = tmp_path / "out"
    res = _mpirun([(ni_binary, _ini(tmp_path / "in.ini", slab, out))] * 2, mpi_env)
    assert res is not None, "job hung"
    assert res.returncode == 0, res.stderr
    agg = _aggregate(out)
    assert [r["run_rc"] for r in agg["replicas"]] == [run_rc] * 2
    assert (agg["n_success"], agg["n_failed"]) == counts
    assert "replica_run failed" not in res.stderr  # a trap is not reported as a failure


# ---------------------------------------------------------------------------
# 02: one rank failing startup must not hang the others
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stage", "failure"),
    [
        ("input_config_load", "missing_ini"),
        ("replica_init", "output_root_under_a_file"),
        ("replica_init", "replica_dir_is_a_file"),
    ],
    ids=["missing_ini", "output_root_under_a_file", "replica_dir_is_a_file"],
)
def test_one_rank_startup_failure_terminates_every_rank(
    mpi_env: dict[str, str], ni_binary: Path, tmp_path: Path, stage: str, failure: str
) -> None:
    """Only rank 1 fails startup. Before the fix rank 0 ran its replica and
    then blocked in MPI_Barrier / MPI_Gather until killed; now every rank
    exits non-zero promptly and no replica runs."""
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    out = tmp_path / "out"
    good = _ini(tmp_path / "good.ini", NI_SLAB_1VAC, out)
    if failure == "missing_ini":
        bad = tmp_path / "no_such_input.ini"
    elif failure == "output_root_under_a_file":
        blocker = tmp_path / "blocker"  # a regular FILE: no directory below it
        blocker.write_text("not a directory\n")
        bad = _ini(tmp_path / "bad.ini", NI_SLAB_1VAC, blocker / "out")
    else:
        # Same input on both ranks, but a regular file sits where rank 1's
        # replica directory must go (replica_init used to accept it as an
        # existing directory, and the run failed later at its first open).
        out.mkdir()
        (out / "replica_0001").write_text("")
        bad = good
    res = _mpirun([(ni_binary, good), (ni_binary, bad)], mpi_env, timeout=60.0)
    assert res is not None, "rank 0 hung after rank 1 failed startup"
    assert res.returncode != 0
    assert f"[rank 1] {stage} failed" in res.stderr
    assert "startup failed on 1 of 2 ranks" in res.stderr
    assert not list(out.rglob("pykmc.out")), "no replica may run"
