"""Ctypes tests for the runtime RNG (`runtime/src/core/rng.c`).

`rng_next2`'s second draw r2 feeds `dt = -log(r2) / r_tot` in kmc.c, so an
exact 0 would make dt = +inf (large-system-scaling/03). The fix redraws an
exact 0 instead of remapping every draw, so every fixed-seed trajectory that
never drew 0 stays bitwise identical; both halves are locked here.
"""

from __future__ import annotations

import ctypes
import math
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"
RNG_SRC = RUNTIME_CORE / "rng.c"
MASK64 = (1 << 64) - 1


class _Rng(ctypes.Structure):
    """Mirror of `Rng` in rng.h (xoshiro256++ state)."""

    _fields_ = [("s", ctypes.c_uint64 * 4)]


@pytest.fixture(scope="module")
def librng(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    builddir = tmp_path_factory.mktemp("rng_lib")
    libname = "librng.dylib" if os.uname().sysname == "Darwin" else "librng.so"
    libpath = builddir / libname
    cmd = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-fPIC",
        "-shared",
        "-I",
        str(RUNTIME_CORE),
        str(RNG_SRC),
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"rng.c failed to compile:\n{res.stderr}")
    lib = ctypes.CDLL(str(libpath))
    rng_p = ctypes.POINTER(_Rng)
    dbl_p = ctypes.POINTER(ctypes.c_double)
    lib.rng_seed.argtypes = [rng_p, ctypes.c_uint64, ctypes.c_uint32]
    lib.rng_seed.restype = None
    lib.rng_next_double.argtypes = [rng_p]
    lib.rng_next_double.restype = ctypes.c_double
    lib.rng_next2.argtypes = [rng_p, dbl_p, dbl_p]
    lib.rng_next2.restype = None
    return lib


def _zero_second_draw_state() -> _Rng:
    """A state whose SECOND output is 0, i.e. rng_next2 would draw r2 = 0.0.

    xoshiro256++ outputs rotl(s0 + s3, 23) + s0, which is 0 when s0 == s3 == 0.
    Inverting one state update shows (0, x, x ^ b, x) steps to (0, b, ., 0)
    for any x and b; nonzero x, b keep the state off the all-zero fixed point.
    """
    x, b = 0x9E3779B97F4A7C15, 0xD1B54A32D192ED03
    st = _Rng()
    for i, v in enumerate((0, x, x ^ b, x)):
        st.s[i] = v & MASK64
    return st


def test_forced_zero_r2_is_redrawn(librng: ctypes.CDLL) -> None:
    raw = _zero_second_draw_state()
    first = librng.rng_next_double(ctypes.byref(raw))
    second = librng.rng_next_double(ctypes.byref(raw))
    third = librng.rng_next_double(ctypes.byref(raw))
    assert second == 0.0, "fixture no longer forces an exact zero draw"

    st = _zero_second_draw_state()
    r1, r2 = ctypes.c_double(), ctypes.c_double()
    librng.rng_next2(ctypes.byref(st), ctypes.byref(r1), ctypes.byref(r2))
    assert r1.value == first  # the selection draw is untouched
    assert 0.0 < r2.value < 1.0
    assert math.isfinite(-math.log(r2.value))  # dt = -log(r2)/r_tot stays finite
    assert r2.value == third  # redrawn (next value), not remapped


def test_stream_without_zero_is_bitwise_unchanged(librng: ctypes.CDLL) -> None:
    """rng_next2 is exactly two consecutive rng_next_double draws whenever
    neither is 0: the fixed-seed golden trajectories cannot move."""
    a, b = _Rng(), _Rng()
    for rank in (0, 1):
        librng.rng_seed(ctypes.byref(a), 20261021, rank)
        librng.rng_seed(ctypes.byref(b), 20261021, rank)
        r1, r2 = ctypes.c_double(), ctypes.c_double()
        for _ in range(2000):
            librng.rng_next2(ctypes.byref(a), ctypes.byref(r1), ctypes.byref(r2))
            assert r1.value == librng.rng_next_double(ctypes.byref(b))
            assert r2.value == librng.rng_next_double(ctypes.byref(b))
