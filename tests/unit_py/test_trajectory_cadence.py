"""run.traj_every: a trajkmc.xyz cadence of its own (large-system-scaling/15).

trajkmc.xyz writes every atom as text (~50 MB per frame at 1e6 sites) and used
to be written on pykmc.out's sample_every cadence. run.traj_every sets the frame
cadence separately (0 = only the t=0 frame) and defaults to sample_every, so an
input without the key writes exactly what it wrote before. The key must change
which frames are written and nothing else: not their content, not pykmc.out,
not the summaries, whichever order the keys come in.

Builds ni_example from its committed proclist and runs it with 2 ranks through
_mpi_harness (private TMPDIR / OMPI_MCA_orte_tmpdir_base, a timeout that tears
the job down). Skipped without cmake / mpirun / an MPI toolchain.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from ._mpi_harness import REPO_ROOT, build_model, mpirun, private_mpi_env

NI_SLAB_1VAC = REPO_ROOT / "models" / "ni_example" / "examples" / "slab_ni_1vac.kmcinit"
MAX_STEPS, SAMPLE_EVERY = 600, 50
#: run name -> the [run] cadence lines, in file order (traj_every absent: the default)
RUNS = {
    "default": [("sample_every", SAMPLE_EVERY)],
    "same": [("sample_every", SAMPLE_EVERY), ("traj_every", SAMPLE_EVERY)],
    "sparse": [("sample_every", SAMPLE_EVERY), ("traj_every", 75)],
    "sparse_key_first": [("traj_every", 75), ("sample_every", SAMPLE_EVERY)],
    "dense": [("sample_every", SAMPLE_EVERY), ("traj_every", 1)],
    "none": [("sample_every", SAMPLE_EVERY), ("traj_every", 0)],
    "no_log": [("sample_every", 0)],
    "no_log_frames": [("sample_every", 0), ("traj_every", 150)],
}
REPLICAS = ["replica_0000", "replica_0001"]


@pytest.fixture(scope="module")
def mpi_env() -> Iterator[dict[str, str]]:
    yield from private_mpi_env()


@pytest.fixture(scope="module")
def runs(mpi_env: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Output root of each RUNS entry: same seed and step count."""
    if not NI_SLAB_1VAC.is_file():
        pytest.skip(f"example slab missing: {NI_SLAB_1VAC}")
    tmp = tmp_path_factory.mktemp("cadence")
    binary = build_model("ni_example", tmp)
    roots = {}
    for name, cadence in RUNS.items():
        root = tmp / name
        ini = tmp / f"{name}.ini"
        ini.write_text(
            "[run]\n"
            f"max_steps = {MAX_STEPS}\n"
            + "".join(f"{key} = {value}\n" for key, value in cadence)
            + "base_seed = 7\n"
            "[paths]\n"
            f"initconfig_path = {NI_SLAB_1VAC}\n"
            f"output_root = {root}\n"
            "[physics]\n"
            "temperature_K = 500.0\n"
        )
        res = mpirun([(binary, ini)] * 2, mpi_env)
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


def _files(root: Path, *, skip_traj: bool = False) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not (skip_traj and p.name == "trajkmc.xyz")
    }


def _multiples(every: int) -> list[int]:
    """The t=0 frame, then every multiple of `every` up to MAX_STEPS."""
    return [0] + (list(range(every, MAX_STEPS + 1, every)) if every else [])


def test_default_cadence_is_sample_every(runs: dict[str, Path]) -> None:
    """Without the key, frames follow sample_every (the cadence before the key
    existed), and an explicit traj_every = sample_every changes no byte."""
    for rep in REPLICAS:
        assert list(_frames(runs["default"], rep)) == _multiples(SAMPLE_EVERY)
        assert _log_steps(runs["default"], rep) == _multiples(SAMPLE_EVERY)[1:]
    assert _files(runs["same"]) == _files(runs["default"])


@pytest.mark.parametrize(("name", "every"), [("sparse", 75), ("dense", 1), ("none", 0)])
def test_traj_every_sets_only_the_frame_cadence(
    runs: dict[str, Path], name: str, every: int
) -> None:
    """Frames at 0 and every multiple of traj_every (only 0 when traj_every = 0),
    each byte-identical to the dense run's frame of that step; every other
    output byte-identical to the default run."""
    for rep in REPLICAS:
        frames = _frames(runs[name], rep)
        assert list(frames) == _multiples(every)
        dense = _frames(runs["dense"], rep)
        assert all(frames[s] == dense[s] for s in frames)
        default = _frames(runs["default"], rep)
        assert all(default[s] == dense[s] for s in default)
    assert _files(runs[name], skip_traj=True) == _files(runs["default"], skip_traj=True)


def test_key_order_does_not_matter(runs: dict[str, Path]) -> None:
    """traj_every before sample_every in the file: the same outputs."""
    assert _files(runs["sparse_key_first"]) == _files(runs["sparse"])


@pytest.mark.parametrize(("name", "every"), [("no_log", 0), ("no_log_frames", 150)])
def test_sample_every_zero_writes_no_log_rows(runs: dict[str, Path], name: str, every: int) -> None:
    """sample_every = 0 writes no pykmc.out rows; frames still follow traj_every,
    which without the key is that same 0 (only the t=0 frame, as before)."""
    for rep in REPLICAS:
        assert _log_steps(runs[name], rep) == []
        frames = _frames(runs[name], rep)
        assert list(frames) == _multiples(every)
        dense = _frames(runs["dense"], rep)
        assert all(frames[s] == dense[s] for s in frames)
    no_logs = {k: v for k, v in _files(runs[name], skip_traj=True).items() if "pykmc.out" not in k}
    default = {
        k: v for k, v in _files(runs["default"], skip_traj=True).items() if "pykmc.out" not in k
    }
    assert no_logs == default
