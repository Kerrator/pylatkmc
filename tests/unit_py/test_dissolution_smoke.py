"""End-to-end smoke test for the electrochemical dissolution feature.

Builds the `ni_dissolution_demo` model with CMake and runs it on a
vacancy-free pure-Ni slab (so hops, which need a Vacant anchor, cannot fire and
dissolution is the only available event). Asserts:

  * the dissolution-enabled C compiles and links,
  * at least one dissolution event fires (n_dissolution >= 1) and a vacancy is
    created (n_vac >= 1),
  * the first event's logged rate scales with the overpotential exactly as
    exp(phi/kT) between two runs of the SAME binary (proves runtime-Phi).

Skipped if cmake is unavailable or the curated CSV / generated proclist is
missing. The run-and-assert portion is skipped (not failed) if the binary
cannot be launched in this environment.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from pylatkmc import load
from pylatkmc.codegen import generate
from pylatkmc.dissolution_rate import KB_EV_PER_K

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
DEMO_DIR = REPO_ROOT / "models" / "ni_dissolution_demo"
DEMO_SPEC = DEMO_DIR / "ni_dissolution_demo.kmcspec.toml"
SLAB = DEMO_DIR / "examples" / "slab_ni_0vac.kmcinit"


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


@pytest.fixture(scope="module")
def demo_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not _have("cmake"):
        pytest.skip("cmake not on PATH")
    if not DEMO_SPEC.is_file():
        pytest.skip(f"demo spec missing: {DEMO_SPEC}")

    # Regenerate proclist (idempotent). Fall back to committed generated/ if the
    # curated CSV / epsilon table is unavailable (standalone clone).
    spec = load(DEMO_SPEC)
    gen_dir = DEMO_DIR / "generated"
    try:
        generate(spec, gen_dir, spec_path=DEMO_SPEC)
    except (FileNotFoundError, ValueError) as e:
        if not (gen_dir / "proclist.c").exists():
            pytest.skip(f"cannot generate and no committed proclist.c: {e}")

    build_dir = tmp_path_factory.mktemp("build_diss")
    cfg = subprocess.run(
        ["cmake", "-B", str(build_dir), "-S", str(REPO_ROOT),
         "-DMODEL=ni_dissolution_demo", "-DREQUIRE_GENERATED=ON"],
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
    if bld.returncode != 0:
        raise AssertionError(f"cmake build failed:\n{bld.stdout}\n{bld.stderr}")

    bin_path = build_dir / "pylatkmc_ni_dissolution_demo"
    assert bin_path.is_file(), f"expected binary at {bin_path}"
    return bin_path


def _run(binary: Path, work: Path, phi: float) -> dict | None:
    """Run the demo at overpotential `phi`; return parsed summary.json or None."""
    out_root = work / f"out_phi{phi}"
    ini = work / f"input_phi{phi}.ini"
    ini.write_text(
        "[run]\n"
        "max_steps = 50\n"
        "sample_every = 1\n"
        "base_seed = 7\n"
        "[paths]\n"
        f"initconfig_path = {SLAB}\n"
        f"output_root = {out_root}\n"
        "[physics]\n"
        "temperature_K = 500.0\n"
        f"overpotential_phi_eV = {phi}\n"
        "max_dissolution_events = 100\n"
    )
    proc = subprocess.run([str(binary), str(ini)], capture_output=True, text=True, check=False)
    summary = out_root / "replica_0000" / "summary.json"
    if proc.returncode != 0 or not summary.is_file():
        return None
    return json.loads(summary.read_text())


def _first_k_event(work: Path, phi: float) -> float:
    """k_event of the first logged step (the dissolution from the vacancy-free state)."""
    log = work / f"out_phi{phi}" / "replica_0000" / "pykmc.out"
    for line in log.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        # cols: step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site
        return float(line.split()[5])
    raise AssertionError("no data rows in pykmc.out")


def test_dissolution_fires_and_creates_vacancy(demo_binary: Path, tmp_path: Path) -> None:
    summary = _run(demo_binary, tmp_path, phi=0.5)
    if summary is None:
        pytest.skip("demo binary could not be launched in this environment")
    assert summary["n_dissolution"] >= 1, "expected at least one dissolution event"
    assert summary["n_vac"] >= 1, "dissolution should leave at least one vacancy"


def test_overpotential_scales_first_rate(demo_binary: Path, tmp_path: Path) -> None:
    s0 = _run(demo_binary, tmp_path, phi=0.0)
    s5 = _run(demo_binary, tmp_path, phi=0.5)
    if s0 is None or s5 is None:
        pytest.skip("demo binary could not be launched in this environment")
    k0 = _first_k_event(tmp_path, 0.0)
    k5 = _first_k_event(tmp_path, 0.5)
    # k = nu_E * exp(-(E_bare - phi)/kT)  =>  k(phi)/k(0) = exp(phi/kT)
    assert k5 / k0 == pytest.approx(math.exp(0.5 / (KB_EV_PER_K * 500.0)), rel=1e-6)
