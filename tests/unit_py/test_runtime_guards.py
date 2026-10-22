"""Regression tests for runtime / codegen guards (large-system-scaling WP1).

ctypes and compile level only — no MPI launch:

- 03: ``rng_next2`` never returns r2 = 0.0 (``dt = -log(r2)/r_tot`` stays
  finite) and leaves every non-zero draw bitwise unchanged.

Each test skips cleanly without cc.
"""

from __future__ import annotations

import ctypes
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "runtime" / "src" / "core"
IO = REPO_ROOT / "runtime" / "src" / "io"


def _build_lib(tmp: Path, name: str, sources: list[Path], includes: tuple[Path, ...] = ()):
    """Compile ``sources`` into a shared library and load it (skip without cc)."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    lib = tmp / (f"lib{name}.dylib" if sys.platform == "darwin" else f"lib{name}.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    for inc in (*includes, CORE, IO):
        cmd += ["-I", str(inc)]
    cmd += [str(s) for s in sources] + ["-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")
    return ctypes.CDLL(str(lib))


# ---------------------------------------------------------------------------
# 03 — an exact-zero r2 is redrawn (finite dt), non-zero draws untouched
# ---------------------------------------------------------------------------

_M64 = (1 << 64) - 1


def _rotl(x: int, k: int) -> int:
    return ((x << k) | (x >> (64 - k))) & _M64


def _xoshiro_next(s: list[int]) -> int:
    """One xoshiro256++ step (mirrors rng.c): return the output, advance ``s``."""
    result = (_rotl((s[0] + s[3]) & _M64, 23) + s[0]) & _M64
    t = (s[1] << 17) & _M64
    s[2] ^= s[0]
    s[3] ^= s[1]
    s[1] ^= s[2]
    s[0] ^= s[3]
    s[2] ^= t
    s[3] = _rotl(s[3], 45)
    return result


def _xoshiro_prev(b: list[int]) -> list[int]:
    """Invert one state transition: the state whose successor is ``b``."""
    c3 = _rotl(b[3], 19)  # undoes rotl(., 45): c3 = a1 ^ a3
    a0 = b[0] ^ c3
    y = b[1] ^ b[2]  # = a1 ^ (a1 << 17)
    a1 = (y ^ (y << 17) ^ (y << 34) ^ (y << 51)) & _M64
    return [a0, a1, b[1] ^ a0 ^ a1, c3 ^ a1]


def _draw(u64: int) -> float:
    """rng_next_double's mapping of one raw output to [0, 1)."""
    return (u64 >> 11) * 2.0**-53


class _Rng(ctypes.Structure):
    _fields_ = [("s", ctypes.c_uint64 * 4)]


@pytest.fixture(scope="module")
def librng(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    lib = _build_lib(tmp_path_factory.mktemp("rng"), "rng", [CORE / "rng.c"])
    lib.rng_seed.argtypes = [ctypes.POINTER(_Rng), ctypes.c_uint64, ctypes.c_uint32]
    lib.rng_seed.restype = None
    lib.rng_next_double.argtypes = [ctypes.POINTER(_Rng)]
    lib.rng_next_double.restype = ctypes.c_double
    lib.rng_next2.argtypes = [
        ctypes.POINTER(_Rng),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
    ]
    lib.rng_next2.restype = None
    return lib


def test_rng_next2_redraws_an_exact_zero_r2(librng: ctypes.CDLL) -> None:
    """Force the time-increment draw to be exactly 0.0: dt must stay finite."""
    # From state {0, 1, 0, 0} xoshiro256++ outputs rotl(0 + 0, 23) + 0 = 0, i.e.
    # a draw of exactly 0.0. Start one step earlier so that zero lands on r2.
    zero_state = [0, 1, 0, 0]
    start = _xoshiro_prev(zero_state)
    probe = list(start)
    _xoshiro_next(probe)
    assert probe == zero_state  # the inversion is exact
    assert _draw(_xoshiro_next(list(zero_state))) == 0.0  # the forced zero

    rng = _Rng((ctypes.c_uint64 * 4)(*start))
    r1, r2 = ctypes.c_double(), ctypes.c_double()
    librng.rng_next2(ctypes.byref(rng), ctypes.byref(r1), ctypes.byref(r2))

    py = list(start)
    assert r1.value == _draw(_xoshiro_next(py))  # r1: the untouched first draw
    assert _draw(_xoshiro_next(py)) == 0.0  # the draw rng_next2 must skip
    assert r2.value == _draw(_xoshiro_next(py))  # r2: the redraw
    assert r2.value > 0.0
    assert math.isfinite(-math.log(r2.value) / 1.0)  # dt at r_tot = 1 Hz


def test_rng_next2_leaves_nonzero_draws_bitwise_unchanged(librng: ctypes.CDLL) -> None:
    """Every fixed-seed stream that never draws 0.0 is unchanged by the redraw."""
    a, b = _Rng(), _Rng()
    librng.rng_seed(ctypes.byref(a), 20261021, 1)
    librng.rng_seed(ctypes.byref(b), 20261021, 1)
    r1, r2 = ctypes.c_double(), ctypes.c_double()
    for _ in range(10000):
        librng.rng_next2(ctypes.byref(a), ctypes.byref(r1), ctypes.byref(r2))
        assert r1.value == librng.rng_next_double(ctypes.byref(b))
        assert r2.value == librng.rng_next_double(ctypes.byref(b))
