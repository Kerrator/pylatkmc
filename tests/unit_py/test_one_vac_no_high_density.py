"""Regression test: a 1-vacancy config must NEVER fire Processes whose
bucket key requires nv1 >= 2.

This is the v0.3 ShellCondition smoke gate. Before the IR change, the
translator dropped the bucket-key context (`nv1=4_nv2=1` was emitted as
a Process whose Conditions only checked anchor + direction species),
so the same Process fired at every (vacant, atom_neighbour) pair —
including 1-vacancy systems where nv1 cannot exceed 1.

The test:
1. Runs the existing `pylatkmc_ni_fe_cr_v1` binary on a real
   pyKMC-converted 1-vacancy config (22×22×20 slab).
2. Logs every step's `proc_id` to `pykmc.out`.
3. Parses the generated proclist enum to map proc_id → name.
4. Asserts that no fired Process has `nv1_<k>` in its name with k >= 2.

Prerequisites:
- The binary `build/pylatkmc_ni_fe_cr_v1` exists (built at T=500 K).
- The converted config `models/ni_fe_cr_v1/examples/full_100Ni/configs/
  1vac_T500.kmcinit` exists.

Both are produced by the v0.3 pre-test setup; if missing, the test is
skipped (so CI without a built binary doesn't fail spuriously).
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BINARY = REPO_ROOT / "build" / "pylatkmc_ni_fe_cr_v1"
CONFIG = REPO_ROOT / "models/ni_fe_cr_v1/examples/full_100Ni/configs/1vac_T500.kmcinit"
PROCLIST = REPO_ROOT / "models/ni_fe_cr_v1/generated/proclist.c"
MPIRUN = "/Users/stephenkerr/openmpi/bin/mpirun"


def _load_proc_enum(proclist_path: Path) -> dict[int, str]:
    """Parse the generated `enum { P_..., N_PROCS };` to map id → name."""
    enum: dict[int, str] = {}
    proc_idx = 0
    in_enum = False
    with open(proclist_path) as f:
        for line in f:
            s = line.strip()
            if s == "enum {":
                in_enum = True
                continue
            if in_enum:
                if s.startswith("}") or s == "N_PROCS,":
                    in_enum = False
                    continue
                m = re.match(r"^(P_\w+)", s)
                if m:
                    enum[proc_idx] = m.group(1)
                    proc_idx += 1
    return enum


def _parse_nv1(proc_name: str) -> int | None:
    m = re.search(r"nv1_(\d+)", proc_name)
    return int(m.group(1)) if m else None


@pytest.mark.skipif(
    not BINARY.is_file()
    or not CONFIG.is_file()
    or not PROCLIST.is_file()
    or not Path(MPIRUN).is_file(),
    reason="binary, config, proclist, or mpirun not available",
)
def test_one_vac_never_fires_high_nv1_buckets(tmp_path: Path) -> None:
    """Run a short 5k-step trajectory on a 1-vac config and assert no
    nv1>=2 Process fires. This is the regression gate for the v0.3
    ShellCondition fix."""
    # Build a per-test input.ini with sample_every=1 so every step
    # writes a row to pykmc.out (we need proc_id per event).
    out_dir = tmp_path / "out"
    ini = tmp_path / "input.ini"
    ini.write_text(
        "[run]\n"
        "max_steps      = 5000\n"
        "sample_every   = 1\n"
        "summary_every  = 0\n"
        "base_seed      = 42\n"
        "\n"
        "[paths]\n"
        "ratetable_path  = unused.kmcrt\n"
        f"initconfig_path = {CONFIG}\n"
        f"output_root     = {out_dir}\n"
        "\n"
        "[physics]\n"
        "temperature_K = 500.0\n"
        "\n"
        "[validation]\n"
        "rng_replay_path =\n"
    )

    res = subprocess.run(
        [MPIRUN, "--oversubscribe", "-n", "1", str(BINARY), str(ini)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert res.returncode == 0, (
        f"binary crashed:\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
    )

    log_path = out_dir / "replica_0000" / "pykmc.out"
    assert log_path.is_file(), f"no per-step log at {log_path}"

    # Parse the generated enum so we can map proc_id → name.
    enum = _load_proc_enum(PROCLIST)
    assert enum, "couldn't parse proclist enum"

    nv1_counter: Counter[int] = Counter()
    high_nv1_examples: list[str] = []
    n_total = 0
    with open(log_path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                proc_id = int(parts[7])
            except ValueError:
                continue
            n_total += 1
            name = enum.get(proc_id)
            if name is None:
                continue
            nv1 = _parse_nv1(name)
            if nv1 is not None:
                nv1_counter[nv1] += 1
                if nv1 >= 2 and len(high_nv1_examples) < 5:
                    high_nv1_examples.append(name)

    assert n_total > 0, "no events were logged"

    # Critical assertion: nv1>=2 must never fire on a 1-vac system.
    high_nv1_total = sum(c for k, c in nv1_counter.items() if k >= 2)
    assert high_nv1_total == 0, (
        f"v0.3 regression FAILED: {high_nv1_total} firings of Processes "
        f"with nv1 >= 2 on a 1-vacancy system. Examples:\n"
        + "\n".join(f"  - {n}" for n in high_nv1_examples)
        + "\n\nFull nv1 distribution:\n"
        + "\n".join(f"  nv1={k}: {c}" for k, c in sorted(nv1_counter.items()))
    )

    # Sanity: at least SOME nv1=1 events should fire (the legitimate ones).
    assert nv1_counter[1] > 0, (
        f"no nv1=1 firings observed in {n_total} events — something is "
        f"wrong with the catalogue or the test config."
    )
