"""run.traj_every: a trajkmc.xyz cadence of its own (large-system-scaling/15).

trajkmc.xyz writes every atom as text (~50 MB per frame at 1e6 sites) and used
to be written on pykmc.out's sample_every cadence. run.traj_every sets the frame
cadence separately (0 = only the t=0 frame) and defaults to sample_every, so an
input without the key writes exactly what it wrote before. The key must change
which frames are written and nothing else: not their content, not pykmc.out,
not the summaries.

Builds ni_example from its committed proclist (CMake Release, -j2) and runs it
with 2 ranks under a private TMPDIR / OMPI_MCA_orte_tmpdir_base and a timeout
that tears the job down. Skipped without cmake / mpirun / an MPI toolchain.
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
NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
LAUNCH_TIMEOUT_S = 120.0
MAX_STEPS, SAMPLE_EVERY = 600, 50
#: run name -> the [run] traj_every line (None: key absent)
RUNS = {"default": None, "same": 50, "sparse": 75, "dense": 1, "none": 0}


def _teardown(proc: subprocess.Popen[str]) -> None:
    """SIGKILL every process in mpirun's session (Open MPI gives each rank its
    own process group, so killing mpirun alone would orphan them)."""
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
    cmd: list[str], env: dict[str, str], timeout: float = LAUNCH_TIMEOUT_S
) -> subprocess.CompletedProcess[str] | None:
    """Run `mpirun cmd`; None if it outlived `timeout` (after tearing it down)."""
    full = ["mpirun", "--oversubscribe", "--bind-to", "none", *cmd]
    proc = subprocess.Popen(
        full,
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
    return subprocess.CompletedProcess(full, proc.returncode, out, err)


@pytest.fixture(scope="module")
def mpi_env() -> Iterator[dict[str, str]]:
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun not on PATH")
    # A short private dir: Open MPI puts Unix sockets under it (paths are
    # capped at 104 bytes on macOS, whose default TMPDIR is already long).
    darwin = os.uname().sysname == "Darwin"
    tmp = tempfile.mkdtemp(prefix="plk-ompi-", dir="/tmp" if darwin else None)
    env = {**os.environ, "TMPDIR": tmp, "OMPI_MCA_orte_tmpdir_base": tmp, "OMP_NUM_THREADS": "1"}
    probe = _mpirun(["-n", "1", shutil.which("true") or "/usr/bin/true"], env, 60.0)
    if probe is None or probe.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        pytest.skip(f"mpirun cannot launch a trivial job here: {probe and probe.stderr[:200]}")
    yield env
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def ni_binary(mpi_env: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("cmake") is None:
        pytest.skip("cmake not on PATH")
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    build = tmp_path_factory.mktemp("ni") / "build"
    cfg = subprocess.run(
        ["cmake", "-S", str(REPO_ROOT), "-B", str(build), "-DMODEL=ni_example"]
        + ["-DCMAKE_BUILD_TYPE=Release"],
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
    binary = build / "pylatkmc_ni_example"
    assert binary.is_file(), f"expected binary at {binary}"
    return binary


@pytest.fixture(scope="module")
def runs(
    mpi_env: dict[str, str], ni_binary: Path, tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Path]:
    """Output root of each RUNS entry: same seed, steps and sample_every."""
    tmp = tmp_path_factory.mktemp("cadence")
    roots = {}
    for name, traj_every in RUNS.items():
        root = tmp / name
        ini = tmp / f"{name}.ini"
        ini.write_text(
            "[run]\n"
            f"max_steps = {MAX_STEPS}\n"
            f"sample_every = {SAMPLE_EVERY}\n"
            + ("" if traj_every is None else f"traj_every = {traj_every}\n")
            + "base_seed = 7\n"
            "[paths]\n"
            f"initconfig_path = {NI_SLAB_1VAC}\n"
            f"output_root = {root}\n"
            "[physics]\n"
            "temperature_K = 500.0\n"
        )
        res = _mpirun(["-n", "2", str(ni_binary), str(ini)], mpi_env)
        assert res is not None, f"{name}: job hung"
        assert res.returncode == 0, f"{name}:\n{res.stderr}"
        assert "unknown key" not in res.stderr, res.stderr
        roots[name] = root
    return roots


def _frames(root: Path, replica: str) -> dict[int, str]:
    """trajkmc.xyz frames of one replica, keyed by the step in their header."""
    lines = (root / replica / "trajkmc.xyz").read_text().splitlines(keepends=True)
    frames: dict[int, str] = {}
    i = 0
    while i < len(lines):
        n_atoms = int(lines[i])
        step = int(lines[i + 1].split("step=")[1].split()[0])
        assert step not in frames, f"step {step} written twice"
        frames[step] = "".join(lines[i : i + n_atoms + 2])
        i += n_atoms + 2
    return frames


def _log_steps(root: Path, replica: str) -> list[int]:
    rows = (root / replica / "pykmc.out").read_text().splitlines()
    return [int(r.split()[0]) for r in rows if r.strip() and not r.startswith("#")]


def _files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


REPLICAS = ["replica_0000", "replica_0001"]


def test_default_cadence_is_sample_every(runs: dict[str, Path]) -> None:
    """Without the key, frames follow sample_every (the cadence before the key
    existed), and an explicit traj_every = sample_every changes no byte."""
    for rep in REPLICAS:
        assert list(_frames(runs["default"], rep)) == list(range(0, MAX_STEPS + 1, SAMPLE_EVERY))
        assert _log_steps(runs["default"], rep) == list(
            range(SAMPLE_EVERY, MAX_STEPS + 1, SAMPLE_EVERY)
        )
    assert _files(runs["same"]) == _files(runs["default"])


@pytest.mark.parametrize(("name", "every"), [("sparse", 75), ("dense", 1), ("none", 0)])
def test_traj_every_sets_only_the_frame_cadence(
    runs: dict[str, Path], name: str, every: int
) -> None:
    """Frames at 0 and every multiple of traj_every (only 0 when traj_every = 0),
    each byte-identical to the dense run's frame of that step; every other
    output byte-identical to the default run."""
    expected_steps = [0] + (list(range(every, MAX_STEPS + 1, every)) if every else [])
    for rep in REPLICAS:
        frames = _frames(runs[name], rep)
        assert list(frames) == expected_steps
        dense = _frames(runs["dense"], rep)
        assert all(frames[s] == dense[s] for s in frames)
        default = _frames(runs["default"], rep)
        assert all(default[s] == dense[s] for s in default)
    others = {k: v for k, v in _files(runs[name]).items() if not k.endswith("trajkmc.xyz")}
    default = {k: v for k, v in _files(runs["default"]).items() if not k.endswith("trajkmc.xyz")}
    assert others == default
