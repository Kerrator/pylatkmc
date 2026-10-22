"""Regression tests for runtime / codegen guards (large-system-scaling WP1).

ctypes and compile level only, no MPI launch (those live in
test_mpi_failure_modes.py):

- 05: a generated v2 apply whose ``state_apply_actions`` call is rejected
  reports ``PYLATKMC_HOP_REJECTED`` with the state untouched, and
  ``kmc_step_once`` then fails the step without advancing the clock.
- 06: the emitters index ``coord_table`` / ``site_ijk`` in ``size_t``, and so
  does every COMMITTED proclist.c (CI links them without regenerating). The
  ``initconfig_load`` range check lives in test_initconfig_range.py.
- 07: the ``PYLATKMC_NATIVE`` CMake option (default ON keeps today's flags,
  OFF drops ``-march=native``), checked at configure time only.

Each test skips cleanly without cc (or cmake / an MPI toolchain for 07).
"""

from __future__ import annotations

import ctypes
import errno
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
CORE = REPO_ROOT / "runtime" / "src" / "core"
IO = REPO_ROOT / "runtime" / "src" / "io"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"


def _build_lib(
    tmp: Path, name: str, sources: list[Path], includes: tuple[Path, ...] = ()
) -> ctypes.CDLL:
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
# 05: a rejected v2 apply is reported, and the step fails without ticking
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

int pylatkmc_test_rejected_value(void) { return PYLATKMC_HOP_REJECTED; }
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
    (2,0,0); apply proc 0 at site 0 -> (HopOutcome, species after, n_vac after)."""
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
    return (HopOutcome){ PYLATKMC_HOP_REJECTED, PYLATKMC_HOP_REJECTED };
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
# 06: emitted site indices are size_t-wide (and the committed proclists agree)
# ---------------------------------------------------------------------------

#: int-width site*stride indexing, which overflows on large lattices.
_INT_INDEX = re.compile(
    r"\[\s*(?:(?:site|anchor|vac_site|neigh_site|vd)\s*\*\s*(?:N_NEIGHBOUR_CODES|3)"
    r"|3\s*\*\s*(?:site|anchor|vac_site|neigh_site|vd))\b"
)


def test_emitted_site_indices_are_size_t() -> None:
    """coord_table / site_ijk indexes are computed in size_t by the emitters
    (an int ``site * N_NEIGHBOUR_CODES`` overflows above ~93M sites) and in
    every committed proclist.c, which CI links without regenerating."""
    from pylatkmc.decision_tree import _coord_macro
    from pylatkmc.processes import CoordOffset
    from pylatkmc.surrogate_codegen import _MEASURED_COVERS_C

    assert _coord_macro(CoordOffset(code="NC_NN1_PX")) == (
        "lat->coord_table[(size_t)site * N_NEIGHBOUR_CODES + NC_NN1_PX]"
    )
    assert _coord_macro(CoordOffset(code="NC_ANCHOR")) == "site"
    assert "&lat->site_ijk[(size_t)vac_site * 3]" in _MEASURED_COVERS_C
    assert "&lat->site_ijk[(size_t)neigh_site * 3]" in _MEASURED_COVERS_C
    assert _INT_INDEX.search(_MEASURED_COVERS_C) is None
    v2 = _v2_hop_proclist_c()  # v2_match + v2_apply from pattern_codegen
    assert v2.count("&lat->site_ijk[(size_t)site * 3]") == 2
    assert _INT_INDEX.search(v2) is None
    proclists = sorted((REPO_ROOT / "models").glob("*/generated/proclist.c"))
    assert proclists
    for path in proclists:
        hit = _INT_INDEX.search(path.read_text())
        assert hit is None, f"{path}: int-width index {hit.group(0)!r} (regenerate it)"


# ---------------------------------------------------------------------------
# 07: PYLATKMC_NATIVE: ON (default) keeps today's flags, OFF is portable
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
