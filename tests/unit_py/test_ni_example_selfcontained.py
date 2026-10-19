"""Every model must stay self-contained; ni_example is the reference case.

Each model vendors its family table under models/<m>/data/ (ni_dissolution_demo
reuses ni_fe_cr_v1's), so a standalone pylatkmc clone with no PyKMC_Analysis
checkout can REGENERATE it. These tests guard that property: every spec data
path resolves inside the repo, and ni_example regenerates + compiles using only
the vendored CSV.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from pylatkmc import load
from pylatkmc.codegen import generate

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
SPEC = REPO_ROOT / "models" / "ni_example" / "ni_example.kmcspec.toml"


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


ALL_SPECS = sorted((REPO_ROOT / "models").glob("*/*.kmcspec.toml"))


@pytest.mark.parametrize("spec_path", ALL_SPECS, ids=lambda p: p.parent.name)
def test_all_rate_data_paths_are_in_repo(spec_path: Path) -> None:
    """No spec data path may point outside the pylatkmc repo (e.g. ../../apps)."""
    spec = load(spec_path)
    rd = spec.rate_data
    paths = {name: getattr(rd, name) for name in ("primary", "family_table", "fallback_scalar")}
    if spec.dissolution is not None:
        paths["dissolution.epsilon_table"] = spec.dissolution.epsilon_table
    for name, p in paths.items():
        if p is None:
            continue
        resolved = Path(p).resolve()
        assert REPO_ROOT in resolved.parents, (
            f"{name} = {resolved} is OUTSIDE the repo {REPO_ROOT}; "
            "models must stay self-contained (vendor it under data/)."
        )
    # family_table must exist locally; the per-event `primary` is optional/omitted.
    assert rd.family_table is not None and Path(rd.family_table).is_file()


def test_regenerates_from_vendored_csv(tmp_path: Path) -> None:
    """generate() must succeed reading ONLY the vendored data/ CSV (no apps/)."""
    spec = load(SPEC)
    written = generate(spec, tmp_path, spec_path=SPEC)
    proclist_c = tmp_path / "proclist.c"
    assert proclist_c in written and proclist_c.is_file()
    text = proclist_c.read_text()
    assert "enum {" in text and "N_PROCS" in text
    # the full pure-Ni catalogue expands to many hop Processes
    assert text.count("apply_actions_") > 100


@pytest.mark.skipif(not _have("cmake"), reason="cmake not on PATH")
def test_regenerated_model_compiles(tmp_path: Path) -> None:
    """The vendored model builds a binary (regenerate into canonical dir, then cmake)."""
    spec = load(SPEC)
    generate(spec, SPEC.parent / "generated", spec_path=SPEC)  # idempotent

    build_dir = tmp_path / "build"
    cfg = subprocess.run(
        ["cmake", "-B", str(build_dir), "-S", str(REPO_ROOT),
         "-DMODEL=ni_example", "-DREQUIRE_GENERATED=ON"],
        capture_output=True, text=True, check=False,
    )
    if cfg.returncode != 0:
        if "MPI" in cfg.stderr:
            pytest.skip(f"MPI not available: {cfg.stderr[:200]}")
        raise AssertionError(f"cmake configure failed:\n{cfg.stdout}\n{cfg.stderr}")
    bld = subprocess.run(
        ["cmake", "--build", str(build_dir), "-j", "4"],
        capture_output=True, text=True, check=False,
    )
    assert bld.returncode == 0, f"cmake build failed:\n{bld.stdout}\n{bld.stderr}"
    assert (build_dir / "pylatkmc_ni_example").is_file()
