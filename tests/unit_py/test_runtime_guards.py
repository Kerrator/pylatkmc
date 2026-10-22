"""Regression tests for runtime / codegen guards (large-system-scaling WP1).

ctypes and compile level only — no MPI launch:

- 03: ``rng_next2`` never returns r2 = 0.0 (``dt = -log(r2)/r_tot`` stays
  finite) and leaves every non-zero draw bitwise unchanged.
- 06: ``initconfig_load`` rejects header counts beyond int32 instead of
  truncating them; the emitters index ``coord_table`` / ``site_ijk`` in
  ``size_t`` (committed proclists included).

Each test skips cleanly without cc / cmake (or numpy+scipy for the kmcinit
fixture).
"""

from __future__ import annotations

import ctypes
import errno
import importlib.util
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "runtime" / "src" / "core"
IO = REPO_ROOT / "runtime" / "src" / "io"
TOOLS = REPO_ROOT / "tools"


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


# ---------------------------------------------------------------------------
# 06 — header counts beyond int32 are rejected, never truncated
# ---------------------------------------------------------------------------


def _kmcfmt():
    """tools/kmcfmt.py (the .kmcinit header reader/writer), loaded by path."""
    spec = importlib.util.spec_from_file_location("_kmcfmt_tool", TOOLS / "kmcfmt.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_header(path: Path) -> tuple[dict, bytes]:
    kf = _kmcfmt()
    with open(path, "rb") as fp:
        header = kf.read_header(fp, kf.INITCONFIG_MAGIC)
        return header, fp.read()


def _rewrite_header(src: Path, dst: Path, **override: int) -> None:
    """Copy a .kmcinit, overriding header fields (payload untouched)."""
    kf = _kmcfmt()
    header, payload = _read_header(src)
    header.update(override)
    with open(dst, "wb") as fp:
        kf.write_header(fp, kf.INITCONFIG_MAGIC, header)
        fp.write(payload)


@pytest.fixture(scope="module")
def small_kmcinit(tmp_path_factory: pytest.TempPathFactory) -> Path:
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    out = tmp_path_factory.mktemp("kmcinit") / "small.kmcinit"
    subprocess.run(
        [
            sys.executable,
            str(TOOLS / "build_initial_config.py"),
            "--nx",
            "2",
            "--ny",
            "2",
            "--nz",
            "3",
            "--n-vacancies",
            "1",
            "--seed",
            "3",
            "-o",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out


@pytest.fixture(scope="module")
def libinit(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    srcs = [
        IO / "initconfig.c",
        CORE / "kmcfmt.c",
        CORE / "json_mini.c",
        CORE / "state.c",
        CORE / "lattice.c",
        CORE / "coord_codes.c",
    ]
    lib = _build_lib(tmp_path_factory.mktemp("initconfig"), "initconfig", srcs)
    lib.initconfig_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
    ]
    lib.initconfig_load.restype = ctypes.c_int
    lib.state_free.argtypes = [ctypes.c_void_p]
    lib.state_free.restype = None
    lib.lattice_free.argtypes = [ctypes.c_void_p]
    lib.lattice_free.restype = None
    return lib


def _load(lib: ctypes.CDLL, path: Path) -> tuple[int, int]:
    """initconfig_load → (rc, lat->n_sites). Lattice/State are opaque buffers
    (Lattice.n_sites is its first int32 field)."""
    lat = ctypes.create_string_buffer(1024)
    st = ctypes.create_string_buffer(1024)
    rc = lib.initconfig_load(str(path).encode(), lat, st, 0)
    n_sites = ctypes.c_int32.from_buffer(lat).value
    if rc == 0:
        lib.state_free(st)
        lib.lattice_free(lat)
    return rc, n_sites


def test_initconfig_rejects_counts_beyond_int32(
    libinit: ctypes.CDLL, small_kmcinit: Path, tmp_path: Path
) -> None:
    header, _ = _read_header(small_kmcinit)
    n, m1, m2 = header["n_sites"], header["nn1_count"], header["nn2_count"]
    rc, n_loaded = _load(libinit, small_kmcinit)
    assert (rc, n_loaded) == (0, n), "the unmodified fixture must load"

    # 2^32 + n narrows to exactly n: before the range check these headers
    # loaded silently as a valid n-site lattice.
    too_big = {
        "n_sites_wraps": {"n_sites": 2**32 + n},
        "n_sites_int32_max_plus_1": {"n_sites": 2**31},
        "nn1_count_wraps": {"nn1_count": 2**32 + m1},
        "nn2_count_wraps": {"nn2_count": 2**32 + m2},
    }
    for name, override in too_big.items():
        bad = tmp_path / f"{name}.kmcinit"
        _rewrite_header(small_kmcinit, bad, **override)
        assert _load(libinit, bad)[0] == -errno.EOVERFLOW, name

    # A negative count that would narrow to a valid int32 is a malformed header.
    bad = tmp_path / "negative_wraps.kmcinit"
    _rewrite_header(small_kmcinit, bad, n_sites=-(2**32) + n)
    assert _load(libinit, bad)[0] == -errno.EPROTO


# ---------------------------------------------------------------------------
# 06 — emitted indices are size_t-wide (and the committed proclists agree)
# ---------------------------------------------------------------------------

#: int-width site*stride indexing that overflows on large lattices.
_INT_INDEX = re.compile(r"\[\s*(?:site\s*\*\s*N_NEIGHBOUR_CODES|3\s*\*\s*(?:site|anchor))\b")


def test_emitted_site_indices_are_size_t() -> None:
    from pylatkmc.decision_tree import _coord_macro
    from pylatkmc.processes import CoordOffset

    assert _coord_macro(CoordOffset(code="NC_NN1_PX")) == (
        "lat->coord_table[(size_t)site * N_NEIGHBOUR_CODES + NC_NN1_PX]"
    )
    assert _coord_macro(CoordOffset(code="NC_ANCHOR")) == "site"
    proclists = sorted((REPO_ROOT / "models").glob("*/generated/proclist.c"))
    assert proclists
    for path in proclists:
        hit = _INT_INDEX.search(path.read_text())
        assert hit is None, f"{path}: int-width index {hit.group(0)!r} (regenerate it)"
