"""MPI-level regression tests for replica failure handling (large-system-scaling WP1).

Builds ni_example and nicr_v2_scratch from their COMMITTED proclists (CMake,
Release, -j2, temp build dirs) and launches them with at most 2 ranks:

- 01: a replica whose setup fails is counted as failed in
  aggregate_summary.json and the job exits non-zero; a replica that traps (no
  event left — a normal physical end) still exits 0.
- 02: when only ONE rank fails startup, every rank terminates promptly with a
  non-zero exit instead of hanging in the post-run collectives.
- 05: a v2 model refuses, at startup, a periodic axis shorter than
  2*reach+1 grid planes (the 8x8-surface box); a 9x9 box still runs.
- 04: on a surrogate build, pykmc.out's k_tot column is the total rate the
  step's dt used (measured + surrogate), never 0 on a surrogate-only step.

Every launch gets a private TMPDIR / OMPI_MCA_orte_tmpdir_base (an Open MPI
singleton sharing /tmp/ompi.* can disturb unrelated jobs) and a hard timeout
that tears the whole job down. Skipped without cmake / mpirun (or numpy+scipy
for the generated .kmcinit boxes).
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
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


# ---------------------------------------------------------------------------
# 02 — one rank failing startup must not hang the others
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["replica_init", "input_config_load"])
def test_one_rank_startup_failure_terminates_every_rank(
    ni_binary: Path, mpi_env: dict[str, str], tmp_path: Path, stage: str
) -> None:
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    good_out = tmp_path / "out"
    good = _ini(tmp_path / "good.ini", NI_SLAB_1VAC, good_out)
    if stage == "replica_init":
        blocker = tmp_path / "blocker"  # a regular FILE: no output dir below it
        blocker.write_text("not a directory\n")
        bad = _ini(tmp_path / "bad.ini", NI_SLAB_1VAC, blocker / "out")
    else:
        bad = tmp_path / "no_such_input.ini"
    res = _mpirun([(ni_binary, good), (ni_binary, bad)], mpi_env, timeout=60.0)
    assert res is not None, "rank 0 hung after rank 1 failed startup"
    assert res.returncode != 0
    assert f"[rank 1] {stage} failed" in res.stderr
    assert "startup failed on 1 of 2 ranks" in res.stderr
    assert not list(good_out.rglob("pykmc.out")), "no replica may run"


# ---------------------------------------------------------------------------
# 05 — a periodic axis shorter than 2*reach+1 is refused at startup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def nicr_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build("nicr_v2_scratch", tmp_path_factory.mktemp("nicr"))


def _nicr_box(tmp: Path, n: int) -> Path:
    """Random Ni90Cr10 n x n x 10 slab + 8 vacuum layers (as the golden boxes)."""
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    out = tmp / f"box{n}.kmcinit"
    subprocess.run(
        [
            sys.executable,
            str(TOOLS / "build_initial_config.py"),
            "--nx",
            str(n),
            "--ny",
            str(n),
            "--nz",
            "10",
            "--composition",
            "Ni90_Cr10",
            "--n-vacancies",
            "2",
            "--vacuum-layers",
            "8",
            "--seed",
            "7",
            "-o",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out


def test_short_periodic_axis_is_refused_at_startup(
    nicr_binary: Path, mpi_env: dict[str, str], tmp_path: Path
) -> None:
    # 8 surface sites per row => grid_nx = 16 < 2*reach+1 = 17 (reach_ij = 8):
    # offsets +8 and -8 alias to the same site.
    out = tmp_path / "out"
    ini = _ini(tmp_path / "in.ini", _nicr_box(tmp_path, 8), out, temperature_K=600.0)
    res = _mpirun([(nicr_binary, ini)], mpi_env)
    assert res is not None, "job hung"
    assert res.returncode != 0
    assert "periodic with only 16 grid planes" in res.stderr
    assert "reach" in res.stderr
    assert not list(out.rglob("pykmc.out")), "the run must be refused before any step"


@pytest.fixture(scope="module")
def nicr_box9_run(
    nicr_binary: Path, mpi_env: dict[str, str], tmp_path_factory: pytest.TempPathFactory
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """10 logged steps on a 9x9 box (grid_nx = 18 >= 17: allowed)."""
    tmp = tmp_path_factory.mktemp("box9")
    out = tmp / "out"
    ini = _ini(
        tmp / "in.ini", _nicr_box(tmp, 9), out, max_steps=10, sample_every=1, temperature_K=600.0
    )
    res = _mpirun([(nicr_binary, ini)], mpi_env)
    assert res is not None, "job hung"
    return res, out


def test_periodic_axis_of_2_reach_plus_1_runs(
    nicr_box9_run: tuple[subprocess.CompletedProcess[str], Path],
) -> None:
    res, out = nicr_box9_run
    assert res.returncode == 0, res.stderr
    assert (out / "replica_0000" / "pykmc.out").is_file()


# ---------------------------------------------------------------------------
# 04 — k_tot on a surrogate build is the total rate used for dt
# ---------------------------------------------------------------------------


def test_ktot_is_the_total_rate_used_for_dt_on_a_surrogate_build(
    nicr_box9_run: tuple[subprocess.CompletedProcess[str], Path],
) -> None:
    res, out = nicr_box9_run
    assert res.returncode == 0, res.stderr
    rows = [
        line.split()
        for line in (out / "replica_0000" / "pykmc.out").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    assert len(rows) == 10
    # cols: step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site
    assert any(r[7] == "-1" for r in rows), "expected surrogate-channel fires"
    for r in rows:
        dt, k_tot = float(r[2]), float(r[4])
        # dt = -log(r2)/k_tot with r2 in (0, 1): dt*k_tot = -log(r2) lies in
        # (0, -log(2^-53) ~ 36.7]. The measured-only column was 0 on these steps.
        assert k_tot > 0.0, r
        assert 0.0 < dt * k_tot < 37.0, r
