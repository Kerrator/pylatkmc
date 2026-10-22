"""Regression tests for runtime / codegen guards (large-system-scaling WP1).

ctypes and compile level only — no MPI launch (those live in
test_mpi_failure_modes.py):

- 03: ``rng_next2`` never returns r2 = 0.0 (``dt = -log(r2)/r_tot`` stays
  finite) and leaves every non-zero draw bitwise unchanged.
- 05: a generated v2 apply whose ``state_apply_actions`` call is rejected
  reports ``STATE_APPLY_REJECTED`` with the state untouched, and
  ``kmc_step_once`` then fails the step without advancing the clock.
- 06: ``initconfig_load`` rejects header counts beyond int32 instead of
  truncating them; the emitters index ``coord_table`` / ``site_ijk`` in
  ``size_t`` (committed proclists included).
- 07: the ``PYLATKMC_NATIVE`` CMake option (default ON keeps today's flags).

Each test skips cleanly without cc / cmake (or numpy+scipy for the kmcinit
fixture).
"""

from __future__ import annotations

import ctypes
import errno
import importlib.util
import json
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
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"


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


# ---------------------------------------------------------------------------
# 05 — a rejected v2 apply is reported, and the step fails without ticking
# ---------------------------------------------------------------------------


def _v2_hop_proclist_c() -> str:
    """A complete v2 proclist.c for one hand-built pattern: a Ni atom at
    runtime cell (2, 0, 0) hops into the vacant anchor (identity orientation),
    plus a test hook around the file-static apply table."""
    pytest.importorskip("numpy")  # D4h ops come from pylatkmc.ingest.lattice
    from pylatkmc.codegen import _PROCLIST_C_PREAMBLE
    from pylatkmc.pattern_codegen import emit_pattern_tables, emit_v2_enum, emit_v2_rate_table
    from pylatkmc.translator_v2 import CtxRow, DeltaRow, LatticePattern, d4h_matrices

    identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    op = next(i for i, m in enumerate(d4h_matrices()) if tuple(map(tuple, m)) == identity)
    pat = LatticePattern(
        class_id="c0",
        name="ni_hop",
        anchor_species="Vacant",
        delta=(DeltaRow((0, 0, 0), "Vacant", "Ni"), DeltaRow((2, 0, 0), "Ni", "Vacant")),
        context=(CtxRow((-2, 0, 0), "EMPTY"),),
        orientation_ops=(op,),
        prefactor_Hz=1.0e13,
        Ea_eV=0.5,
        mover_species=("Ni",),
        n_members=1,
        depth_kind=0,
        depth_param=0,
    )
    pre = _PROCLIST_C_PREAMBLE.format(spec_name="t", temperature_K=500.0, k0_Hz=1e13)
    body = (
        emit_v2_enum([pat]) + "\n" + emit_v2_rate_table([pat]) + "\n" + emit_pattern_tables([pat])
    )
    hook = """
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;

int pylatkmc_test_rejected_value(void) { return STATE_APPLY_REJECTED; }
void pylatkmc_test_apply(int proc, State *st, const Lattice *lat, int site,
                         int *v_origin, int *v_dest)
{
    HopOutcome ho = apply_table[proc](st, lat, site);
    *v_origin = ho.v_origin;
    *v_dest = ho.v_dest;
}
"""
    return pre + body + hook


@pytest.fixture(scope="module")
def libv2(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    tmp = tmp_path_factory.mktemp("v2apply")
    src = tmp / "proclist.c"
    src.write_text(_v2_hop_proclist_c())
    lib = _build_lib(
        tmp, "v2apply", [src, CORE / "state_actions.c", CORE / "avail_sites.c", HELPERS_SRC]
    )
    i32p = ctypes.POINTER(ctypes.c_int32)
    lib.pylatkmc_test_make_lattice_grid.argtypes = [
        ctypes.c_int32,
        i32p,
        ctypes.c_int32,
        i32p,
        i32p,
    ]
    lib.pylatkmc_test_make_lattice_grid.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        i32p,
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_make_state.restype = ctypes.c_void_p
    lib.pylatkmc_test_free_lattice.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_free_state.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_state_n_vac.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_state_n_vac.restype = ctypes.c_int32
    lib.pylatkmc_test_apply.argtypes = [
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.pylatkmc_test_apply.restype = None
    lib.pylatkmc_test_rejected_value.restype = ctypes.c_int
    return lib


def _apply_hop(lib: ctypes.CDLL, b_species: int) -> tuple[tuple[int, int], list[int], int]:
    """Anchor site 0 (vacant) at cell (0,0,0), site 1 (species ``b_species``) at
    (2,0,0); apply proc 0 at site 0 → (HopOutcome, species after, n_vac after)."""
    cells = (ctypes.c_int32 * 6)(0, 0, 0, 2, 0, 0)
    lat = lib.pylatkmc_test_make_lattice_grid(2, cells, 2, None, None)
    st = lib.pylatkmc_test_make_state(
        2, 1, 1, (ctypes.c_int32 * 1)(0), (ctypes.c_uint8 * 2)(0, b_species)
    )
    assert lat and st
    try:
        vo, vd = ctypes.c_int(), ctypes.c_int()
        lib.pylatkmc_test_apply(0, st, lat, 0, ctypes.byref(vo), ctypes.byref(vd))
        species = ctypes.cast(
            ctypes.c_void_p.from_address(st).value, ctypes.POINTER(ctypes.c_uint8)
        )  # State.species
        return (vo.value, vd.value), [species[0], species[1]], lib.pylatkmc_test_state_n_vac(st)
    finally:
        lib.pylatkmc_test_free_state(st)
        lib.pylatkmc_test_free_lattice(lat)


def test_generated_v2_apply_reports_a_rejected_apply(libv2: ctypes.CDLL) -> None:
    sp_ni, sp_fe = 1, 2  # events_base.h
    # Control: the pattern's before-states hold, the hop applies.
    assert _apply_hop(libv2, sp_ni) == ((0, 1), [sp_ni, 0], 1)
    # Fe where the pattern expects Ni: state_apply_actions rejects the actions.
    # The apply must say so (it used to return the hop sites of a no-op).
    rejected = libv2.pylatkmc_test_rejected_value()
    assert rejected not in (-1, 0, 1)
    assert _apply_hop(libv2, sp_fe) == ((rejected, rejected), [0, sp_fe], 1)


_REJECTING_PROCLIST_C = r"""
/* A one-proc fake proclist whose apply always reports a rejected apply, plus a
 * harness that runs one kmc_step_once on a two-site chain (site 0 vacant). */
#include <string.h>

#include "proclist.h"
#include "events_base.h"
#include "kmc.h"

static const RateConst rate_table[1] = { { 1.0e13, 0.5, 0, 0 } };

static HopOutcome rejected_apply(struct State *st, const struct Lattice *lat, int site)
{
    (void)st; (void)lat; (void)site;
    return (HopOutcome){ STATE_APPLY_REJECTED, STATE_APPLY_REJECTED };
}

static const ApplyFn apply_table[1] = { rejected_apply };
const int32_t pylatkmc_n_procs = 1;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;

void touchup_a(const struct Lattice *lat, const struct State *st,
               struct AvailSites *as, int site)
{
    (void)lat;
    if (st->species[site] == SP_VACANT) avail_sites_add(as, 0, site);
}

int pylatkmc_test_step_rejected(double *time_s, unsigned long long *step)
{
    int32_t off[3] = { 0, 1, 2 }, idx[2] = { 1, 0 };
    Lattice lat;
    memset(&lat, 0, sizeof lat);
    lat.n_sites = 2;
    lat.nn1_offsets = off;
    lat.nn1_indices = idx;
    State st;
    if (state_alloc(&st, 2, 1) != 0) return -1000;
    st.species[0] = SP_VACANT;
    st.species[1] = SP_NI;
    st.vac_list[0] = 0;
    st.vac_idx_of[0] = 0;
    st.n_vac = 1;
    AvailSites *as = NULL;
    ActiveFilter *af = NULL;
    if (avail_sites_alloc(&as, 1, 2) != 0 || active_filter_alloc(&af, 2, 12) != 0)
        return -1001;
    avail_sites_set_rate(as, 0, rateconst_eval(rate_table[0], 500.0, 0.0));
    active_filter_compute_static(af, &lat);
    Rng rng;
    rng_seed(&rng, 42, 0);
    KmcRunConfig cfg;
    memset(&cfg, 0, sizeof cfg);
    KmcContext ctx = { .lat = &lat, .st = &st, .as = as, .af = af, .rng = &rng,
                       .cfg = &cfg, .temperature_K = 500.0 };
    int rc = kmc_step_once(&ctx, NULL, NULL, NULL, NULL);
    *time_s = st.time_s;
    *step = (unsigned long long)st.step;
    active_filter_free(af);
    avail_sites_free(as);
    state_free(&st);
    return rc;
}
"""


def test_rejected_apply_fails_the_step_without_advancing_the_clock(tmp_path: Path) -> None:
    header_dir = REPO_ROOT / "models" / "ni_example" / "generated"  # a v0.3 proclist.h
    src = tmp_path / "fake_proclist.c"
    src.write_text(_REJECTING_PROCLIST_C)
    srcs = [
        src,
        CORE / "kmc.c",
        CORE / "avail_sites.c",
        CORE / "active_filter.c",
        CORE / "state.c",
        CORE / "state_actions.c",
        CORE / "rng.c",
        IO / "xyz_writer.c",
        IO / "pykmc_out.c",
        IO / "phasec_out.c",
    ]
    lib = _build_lib(tmp_path, "kmcstep", srcs, includes=(header_dir,))
    lib.pylatkmc_test_step_rejected.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_ulonglong),
    ]
    lib.pylatkmc_test_step_rejected.restype = ctypes.c_int
    time_s, step = ctypes.c_double(-1.0), ctypes.c_ulonglong(99)
    rc = lib.pylatkmc_test_step_rejected(ctypes.byref(time_s), ctypes.byref(step))
    assert rc == -errno.EINVAL
    assert (time_s.value, step.value) == (0.0, 0), "a rejected event must not tick the clock"


# ---------------------------------------------------------------------------
# 07 — PYLATKMC_NATIVE: ON (default) keeps today's flags, OFF is portable
# ---------------------------------------------------------------------------


def _lib_compile_command(build: Path, *defs: str) -> str:
    """Configure (no build) and return the compile command of a runtime source."""
    if shutil.which("cmake") is None:
        pytest.skip("cmake not on PATH")
    res = subprocess.run(
        [
            "cmake",
            "-S",
            str(REPO_ROOT),
            "-B",
            str(build),
            "-DMODEL=ni_example",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
            *defs,
        ],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        if "MPI" in res.stderr:
            pytest.skip(f"MPI not available: {res.stderr[:200]}")
        raise AssertionError(f"cmake configure failed:\n{res.stdout}\n{res.stderr}")
    commands = json.loads((build / "compile_commands.json").read_text())
    return next(c["command"] for c in commands if c["file"].endswith("core/kmc.c"))


def test_pylatkmc_native_option(tmp_path: Path) -> None:
    default = _lib_compile_command(tmp_path / "default")
    portable = _lib_compile_command(tmp_path / "portable", "-DPYLATKMC_NATIVE=OFF")
    assert "-O3 -march=native -Wall -Wextra -Wpedantic" in default  # unchanged flags
    assert "-march=native" not in portable
    assert "-O3 -Wall -Wextra -Wpedantic" in portable
