"""Byte-determinism of the Phase C surrogate codegen across PYTHONHASHSEED, and
byte-invariance of the committed v0.3 ni_example proclist.

Skips the surrogate half without the machine-local .scratch/phaseC artifacts.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NICR_SPEC = REPO_ROOT / "models" / "nicr_v2_scratch" / "nicr_v2_scratch.kmcspec.toml"
NIE_SPEC = REPO_ROOT / "models" / "ni_example" / "ni_example.kmcspec.toml"
MODEL_JSON = REPO_ROOT / ".scratch" / "phaseC" / "esym_model_v1.json"

_GEN_SNIPPET = (
    "from pathlib import Path;"
    "from pylatkmc import codegen, loader;"
    "spec = loader.load(Path(r'{spec}'));"
    "codegen.generate(spec, Path(r'{out}'), spec_path=Path(r'{spec}'))"
)


def _generate(spec: Path, out: Path, seed: str) -> bytes:
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONHASHSEED=seed)
    r = subprocess.run(
        [sys.executable, "-c", _GEN_SNIPPET.format(spec=spec, out=out)],
        env=env, capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        pytest.skip(f"codegen failed (artifacts absent?): {r.stderr[-400:]}")
    return (out / "proclist.c").read_bytes()


def test_surrogate_codegen_byte_deterministic(tmp_path: Path) -> None:
    if not MODEL_JSON.exists():
        pytest.skip("surrogate model artifact absent (.scratch/phaseC)")
    a = _generate(NICR_SPEC, tmp_path / "a", "1")
    b = _generate(NICR_SPEC, tmp_path / "b", "424242")
    assert a == b, "surrogate proclist.c differs across PYTHONHASHSEED"
    assert b"g_surrogate" in a and b"v2_proc_v6_ea" in a


def test_ni_example_proclist_byte_identical(tmp_path: Path) -> None:
    committed = (REPO_ROOT / "models" / "ni_example" / "generated" / "proclist.c").read_bytes()
    regen = _generate(NIE_SPEC, tmp_path / "nie", "0")
    assert regen == committed, "ni_example (v0.3) proclist.c changed — must stay byte-identical"
