"""trajkmc.xyz frame cadence: `[run] traj_every` (large-system-scaling/15).

Trajectory frames were written only on the pykmc.out cadence (`sample_every`):
every atom as text at every sample, ~50 MB per frame at 1e6 sites. The new
`traj_every` key sets the frame cadence on its own; without it frames keep the
`sample_every` cadence, so existing inputs write the same bytes.

Builds ni_example from its COMMITTED proclist (CMake Release, -j2, into a
pytest temp dir) and runs 300 steps of the shipped 1-vacancy slab, one rank
per launch, with `sample_every = 10` and `traj_every` unset / 10 / 50 / 0:

- unset and `traj_every = sample_every` write byte-identical outputs, with a
  frame at step 0 and every 10 steps after it (the `sample_every` cadence);
- `traj_every = 50` writes exactly the unset run's frames for steps 0, 50, ...;
- `traj_every = 0` writes only the t=0 frame;
- pykmc.out, summary.json and aggregate_summary.json never change: the key
  touches neither the step log nor the RNG stream.

Launches use test_mpi_failure_modes' harness: a private TMPDIR /
OMPI_MCA_orte_tmpdir_base and a hard timeout. Skipped without mpirun / cmake /
an MPI toolchain.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from .test_mpi_failure_modes import NI_SLAB_1VAC, _build, _mpirun

MAX_STEPS = 300
SAMPLE_EVERY = 10


@pytest.fixture(scope="module")
def mpi_env() -> Iterator[dict[str, str]]:
    if shutil.which("mpirun") is None:
        pytest.skip("mpirun not on PATH")
    darwin = os.uname().sysname == "Darwin"  # short socket paths on macOS
    tmp = tempfile.mkdtemp(prefix="plk-ompi-", dir="/tmp" if darwin else None)
    env = {**os.environ, "TMPDIR": tmp, "OMPI_MCA_orte_tmpdir_base": tmp, "OMP_NUM_THREADS": "1"}
    probe = _mpirun([(Path(shutil.which("true") or "/usr/bin/true"), Path("probe"))], env, 60.0)
    if probe is None or probe.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        pytest.skip(f"mpirun cannot launch a trivial job here: {probe and probe.stderr[:200]}")
    yield env
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def runs(mpi_env: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Output root (replica_0000/ + aggregate_summary.json) per traj_every value."""
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    tmp = tmp_path_factory.mktemp("traj_cadence")
    binary = _build("ni_example", tmp)
    roots = {}
    for traj_every in ("unset", "10", "50", "0"):
        out = tmp / f"out_{traj_every}"
        ini = tmp / f"in_{traj_every}.ini"
        ini.write_text(
            "[run]\n"
            f"max_steps = {MAX_STEPS}\n"
            f"sample_every = {SAMPLE_EVERY}\n"
            + ("" if traj_every == "unset" else f"traj_every = {traj_every}\n")
            + "base_seed = 7\n"
            "[paths]\n"
            f"initconfig_path = {NI_SLAB_1VAC}\n"
            f"output_root = {out}\n"
            "[physics]\n"
            "temperature_K = 500.0\n"
        )
        res = _mpirun([(binary, ini)], mpi_env)
        assert res is not None, f"traj_every={traj_every}: job hung"
        assert res.returncode == 0, res.stderr
        assert "unknown key" not in res.stderr, res.stderr
        roots[traj_every] = out
    return roots


def _frames(root: Path) -> list[tuple[int, str]]:
    """(step, frame text) for every frame of replica 0's trajkmc.xyz."""
    lines = (root / "replica_0000" / "trajkmc.xyz").read_text().splitlines(keepends=True)
    frames, i = [], 0
    while i < len(lines):
        n_atoms = int(lines[i])
        step = re.search(r"\bstep=(\d+)", lines[i + 1])
        assert step, f"no step= in frame header: {lines[i + 1]!r}"
        frames.append((int(step.group(1)), "".join(lines[i : i + 2 + n_atoms])))
        i += 2 + n_atoms
    return frames


def _same_bytes(a: Path, b: Path, rel: str) -> bool:
    return (a / rel).read_bytes() == (b / rel).read_bytes()


LOGS = ("replica_0000/pykmc.out", "replica_0000/summary.json", "aggregate_summary.json")


def test_default_cadence_is_sample_every(runs: dict[str, Path]) -> None:
    """No traj_every: one frame at step 0, then one every sample_every steps,
    byte-identical to traj_every = sample_every."""
    default = _frames(runs["unset"])
    assert [s for s, _ in default] == list(range(0, MAX_STEPS + 1, SAMPLE_EVERY))
    for rel in ("replica_0000/trajkmc.xyz", *LOGS):
        assert _same_bytes(runs["unset"], runs["10"], rel), rel


def test_traj_every_thins_frames_only(runs: dict[str, Path]) -> None:
    """traj_every = 50 keeps the default run's frames at steps 0, 50, ...,
    byte for byte, and leaves the step log untouched."""
    wanted = [f for f in _frames(runs["unset"]) if f[0] % 50 == 0]
    assert [s for s, _ in wanted] == list(range(0, MAX_STEPS + 1, 50))
    assert _frames(runs["50"]) == wanted
    for rel in LOGS:
        assert _same_bytes(runs["unset"], runs["50"], rel), rel


def test_traj_every_zero_writes_only_the_initial_frame(runs: dict[str, Path]) -> None:
    assert _frames(runs["0"]) == _frames(runs["unset"])[:1]
    for rel in LOGS:
        assert _same_bytes(runs["unset"], runs["0"], rel), rel
