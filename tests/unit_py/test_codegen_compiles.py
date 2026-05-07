"""End-to-end CI check: generate the example model and compile it with CMake.

Skipped if the system doesn't have cmake or an MPI C compiler available.
This is the gate that catches template bugs that produce syntactically
invalid C — the pure-Python test_codegen.py misses those.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from pylatkmc import load
from pylatkmc.codegen import generate

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
EXAMPLE_SPEC = REPO_ROOT / "models" / "ni_fe_cr_v1" / "ni_fe_cr_v1.kmcspec.toml"


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


@pytest.fixture(scope="module")
def built_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run codegen for the example spec and compile with CMake in a temp tree.

    Returns the path to the built binary. Skipped if cmake / MPI missing.
    """
    if not _have("cmake"):
        pytest.skip("cmake not on PATH")

    # 1. Regenerate the example model into its canonical spot (idempotent).
    #    The curated FCC family CSV lives in the upstream PyKMC_Analysis
    #    repo (kmc/apps/PyKMC_Analysis/...), not in pylatkmc itself. In a
    #    standalone pylatkmc clone (e.g. a fresh GitHub Actions runner)
    #    the CSV won't exist; in that case we skip the regen step and
    #    just build whatever proclist.{c,h} is committed under
    #    models/<spec>/generated/. That still gates the CMake link of
    #    the committed generated C — which is what users will compile.
    spec = load(EXAMPLE_SPEC)
    gen_dir = EXAMPLE_SPEC.parent / "generated"
    try:
        generate(spec, gen_dir, spec_path=EXAMPLE_SPEC)
    except FileNotFoundError as e:
        # Family CSV missing → fall back to committed proclist.{c,h}.
        if not (gen_dir / "proclist.c").exists():
            pytest.skip(f"family CSV missing and no committed proclist.c: {e}")

    # 2. Out-of-tree build directory (pytest tmp so runs in parallel don't collide).
    build_dir = tmp_path_factory.mktemp("build")
    env_hint = ""

    # 3. Configure.
    cfg = subprocess.run(
        [
            "cmake",
            "-B",
            str(build_dir),
            "-S",
            str(REPO_ROOT),
            f"-DMODEL={spec.name}",
            "-DREQUIRE_GENERATED=ON",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if cfg.returncode != 0:
        if "Could NOT find MPI" in cfg.stderr or "MPI" in cfg.stderr:
            pytest.skip(f"MPI not available on this system. stderr: {cfg.stderr[:300]}")
        raise AssertionError(
            f"cmake configure failed (rc={cfg.returncode})\n"
            f"stdout:\n{cfg.stdout}\nstderr:\n{cfg.stderr}{env_hint}"
        )

    # 4. Build.
    bld = subprocess.run(
        ["cmake", "--build", str(build_dir), "-j", "4"],
        capture_output=True,
        text=True,
        check=False,
    )
    if bld.returncode != 0:
        raise AssertionError(
            f"cmake build failed (rc={bld.returncode})\n"
            f"stdout:\n{bld.stdout}\nstderr:\n{bld.stderr}"
        )

    bin_path = build_dir / f"pylatkmc_{spec.name}"
    assert bin_path.is_file(), f"Expected binary at {bin_path}"
    return bin_path


def test_generated_sources_compile(built_binary: Path) -> None:
    """Sanity: binary exists and is executable."""
    import os

    assert os.access(built_binary, os.X_OK), f"{built_binary} is not executable"


def test_binary_has_expected_name(built_binary: Path) -> None:
    assert built_binary.name == "pylatkmc_ni_fe_cr_v1"
