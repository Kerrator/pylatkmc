"""Ctypes-driven tests for the C `active_filter` (M-C.4).

The C source under test is `runtime/src/core/active_filter.{h,c}` — a
coordination-based active-site gate that filters which sites need to
have the touchup decision tree run on them each step.

We exercise the *real* `Lattice` and `State` struct types: tests build
small synthetic systems (linear chain, FCC fragment) via the helper
shim `_runtime_test_helpers.c`, which mallocs a real `Lattice*` /
`State*` and only populates the fields active_filter actually reads.

Coverage:
* alloc / free
* compute_static: marks low-coordination sites, leaves bulk untouched
* mark / unmark / clear_dynamic round-trips
* rescan: union of static + vacancy + 1NN-of-vacancy
* idempotency (mark twice ≡ mark once)
* swap-last invariant on unmark
* rescan_vacancies (large-system-scaling WP4a): the vacancy-only active list
  the step loop touches up for vacancy-anchored models is the vacant
  subsequence of rescan's list, in rescan's order, on randomized FCC-slab
  states evolved through state_apply_actions; rescan's own order is the
  pre-WP4a one (static sites by a pass over every site, then the walk)
"""

from __future__ import annotations

import ctypes
import errno
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"
ACTIVE_FILTER_SRC = RUNTIME_CORE / "active_filter.c"
ACTIVE_FILTER_HDR = RUNTIME_CORE / "active_filter.h"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"

EINVAL = -errno.EINVAL


def _have_cc() -> bool:
    return shutil.which("cc") is not None


@pytest.fixture(scope="module")
def libfilter(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if not _have_cc():
        pytest.skip("cc not on PATH")
    if not ACTIVE_FILTER_SRC.is_file():
        pytest.fail(f"missing source: {ACTIVE_FILTER_SRC}")
    if not HELPERS_SRC.is_file():
        pytest.fail(f"missing helpers: {HELPERS_SRC}")

    builddir = tmp_path_factory.mktemp("active_filter_lib")
    libname = "libactive_filter.dylib" if os.uname().sysname == "Darwin" else "libactive_filter.so"
    libpath = builddir / libname

    cmd = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-DNDEBUG",
        "-fPIC",
        "-shared",
        "-I",
        str(RUNTIME_CORE),
        str(ACTIVE_FILTER_SRC),
        str(HELPERS_SRC),
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"active_filter + helpers failed to compile:\n  stderr:\n{res.stderr}")

    lib = ctypes.CDLL(str(libpath))

    # active_filter API
    lib.active_filter_alloc.restype = ctypes.c_int
    lib.active_filter_alloc.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_int32,
        ctypes.c_int32,
    ]
    lib.active_filter_free.restype = None
    lib.active_filter_free.argtypes = [ctypes.c_void_p]
    lib.active_filter_compute_static.restype = None
    lib.active_filter_compute_static.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.active_filter_rescan.restype = None
    lib.active_filter_rescan.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.active_filter_mark.restype = None
    lib.active_filter_mark.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.active_filter_unmark.restype = None
    lib.active_filter_unmark.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.active_filter_clear_dynamic.restype = None
    lib.active_filter_clear_dynamic.argtypes = [ctypes.c_void_p]
    lib.active_filter_n_active.restype = ctypes.c_int32
    lib.active_filter_n_active.argtypes = [ctypes.c_void_p]
    lib.active_filter_site_at.restype = ctypes.c_int32
    lib.active_filter_site_at.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.active_filter_is_active.restype = ctypes.c_int32
    lib.active_filter_is_active.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.active_filter_is_static.restype = ctypes.c_int32
    lib.active_filter_is_static.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.active_filter_n_sites.restype = ctypes.c_int32
    lib.active_filter_n_sites.argtypes = [ctypes.c_void_p]
    lib.active_filter_bulk_thr.restype = ctypes.c_int32
    lib.active_filter_bulk_thr.argtypes = [ctypes.c_void_p]

    # Test helpers: build small Lattice/State structs from Python.
    lib.pylatkmc_test_make_lattice.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_lattice.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.pylatkmc_test_free_lattice.restype = None
    lib.pylatkmc_test_free_lattice.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_make_state.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_free_state.restype = None
    lib.pylatkmc_test_free_state.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_lattice_n_sites.restype = ctypes.c_int32
    lib.pylatkmc_test_lattice_n_sites.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_lattice_nn1_degree.restype = ctypes.c_int32
    lib.pylatkmc_test_lattice_nn1_degree.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.pylatkmc_test_state_n_vac.restype = ctypes.c_int32
    lib.pylatkmc_test_state_n_vac.argtypes = [ctypes.c_void_p]

    return lib


# ---------------------------------------------------------------------------
# Helpers — Python-side wrappers
# ---------------------------------------------------------------------------


def _i32arr(values) -> ctypes.Array:
    return (ctypes.c_int32 * len(values))(*values)


class _Lattice:
    """RAII Lattice: build via test helper, free on exit."""

    def __init__(self, lib: ctypes.CDLL, n_sites: int, nn1_offsets, nn1_indices) -> None:
        self.lib = lib
        offsets_arr = _i32arr(nn1_offsets)
        indices_arr = _i32arr(nn1_indices)
        h = lib.pylatkmc_test_make_lattice(n_sites, offsets_arr, indices_arr)
        if not h:
            raise RuntimeError("pylatkmc_test_make_lattice returned NULL")
        self.h = h

    def __enter__(self) -> _Lattice:
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        if self.h is not None:
            self.lib.pylatkmc_test_free_lattice(self.h)
            self.h = None

    @property
    def ptr(self) -> int:
        return self.h


class _State:
    def __init__(
        self, lib: ctypes.CDLL, n_sites: int, n_vac_max: int, vac_list, species_init=None
    ) -> None:
        self.lib = lib
        vac_arr = _i32arr(vac_list)
        if species_init is None:
            species_ptr = ctypes.cast(None, ctypes.POINTER(ctypes.c_uint8))
        else:
            sp_arr = (ctypes.c_uint8 * len(species_init))(*species_init)
            species_ptr = sp_arr
        h = lib.pylatkmc_test_make_state(n_sites, n_vac_max, len(vac_list), vac_arr, species_ptr)
        if not h:
            raise RuntimeError("pylatkmc_test_make_state returned NULL")
        self.h = h

    def __enter__(self) -> _State:
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        if self.h is not None:
            self.lib.pylatkmc_test_free_state(self.h)
            self.h = None

    @property
    def ptr(self) -> int:
        return self.h


class _AF:
    def __init__(self, lib: ctypes.CDLL, n_sites: int, bulk_threshold: int) -> None:
        self.lib = lib
        h = ctypes.c_void_p()
        rc = lib.active_filter_alloc(ctypes.byref(h), n_sites, bulk_threshold)
        if rc != 0:
            raise RuntimeError(f"alloc failed rc={rc}")
        self.h = h
        self.n_sites = n_sites

    def __enter__(self) -> _AF:
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        if self.h:
            self.lib.active_filter_free(self.h)
            self.h = None

    def compute_static(self, lat: _Lattice) -> None:
        self.lib.active_filter_compute_static(self.h, lat.ptr)

    def rescan(self, lat: _Lattice, st: _State) -> None:
        self.lib.active_filter_rescan(self.h, lat.ptr, st.ptr)

    def mark(self, s: int) -> None:
        self.lib.active_filter_mark(self.h, s)

    def unmark(self, s: int) -> None:
        self.lib.active_filter_unmark(self.h, s)

    def clear_dynamic(self) -> None:
        self.lib.active_filter_clear_dynamic(self.h)

    def n_active(self) -> int:
        return int(self.lib.active_filter_n_active(self.h))

    def site_at(self, i: int) -> int:
        return int(self.lib.active_filter_site_at(self.h, i))

    def is_active(self, s: int) -> int:
        return int(self.lib.active_filter_is_active(self.h, s))

    def is_static(self, s: int) -> int:
        return int(self.lib.active_filter_is_static(self.h, s))

    def active_set(self) -> set[int]:
        return {self.site_at(i) for i in range(self.n_active())}


# ---------------------------------------------------------------------------
# Mini "linear chain" lattice for testing — every site has up to 2 1NN.
# Sites 0 and N-1 are endpoints (degree 1); the rest have degree 2.
# ---------------------------------------------------------------------------


def _linear_chain_csr(n_sites: int) -> tuple[list[int], list[int]]:
    """1NN CSR for a non-periodic 1D chain: site k is 1NN of k-1 and k+1."""
    offsets = [0]
    indices: list[int] = []
    for s in range(n_sites):
        if s > 0:
            indices.append(s - 1)
        if s < n_sites - 1:
            indices.append(s + 1)
        offsets.append(len(indices))
    return offsets, indices


def _square_grid_csr(nx: int, ny: int) -> tuple[list[int], list[int], int]:
    """1NN CSR for a non-periodic square grid: site (i,j) is 1NN of (i±1,j)
    and (i,j±1). Returns (offsets, indices, n_sites)."""
    n = nx * ny

    def idx(i: int, j: int) -> int:
        return i * ny + j

    offsets = [0]
    indices: list[int] = []
    for i in range(nx):
        for j in range(ny):
            for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ii, jj = i + di, j + dj
                if 0 <= ii < nx and 0 <= jj < ny:
                    indices.append(idx(ii, jj))
            offsets.append(len(indices))
    return offsets, indices, n


# ---------------------------------------------------------------------------
# Build helpers: minimal Lattice/State round-trip
# ---------------------------------------------------------------------------


def test_helper_round_trip_lattice(libfilter: ctypes.CDLL) -> None:
    """The C helper builds a Lattice* with the right n_sites and degrees."""
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with _Lattice(libfilter, n, offsets, indices) as lat:
        assert libfilter.pylatkmc_test_lattice_n_sites(lat.ptr) == n
        assert libfilter.pylatkmc_test_lattice_nn1_degree(lat.ptr, 0) == 1
        assert libfilter.pylatkmc_test_lattice_nn1_degree(lat.ptr, 4) == 2
        assert libfilter.pylatkmc_test_lattice_nn1_degree(lat.ptr, n - 1) == 1


def test_helper_round_trip_state(libfilter: ctypes.CDLL) -> None:
    """The C helper builds a State* with the right n_vac."""
    with _State(libfilter, n_sites=8, n_vac_max=2, vac_list=[3]) as st:
        assert libfilter.pylatkmc_test_state_n_vac(st.ptr) == 1


# ---------------------------------------------------------------------------
# active_filter alloc / introspection
# ---------------------------------------------------------------------------


def test_alloc_then_free(libfilter: ctypes.CDLL) -> None:
    h = ctypes.c_void_p()
    assert libfilter.active_filter_alloc(ctypes.byref(h), 32, 8) == 0
    assert libfilter.active_filter_n_sites(h) == 32
    assert libfilter.active_filter_bulk_thr(h) == 8
    assert libfilter.active_filter_n_active(h) == 0
    libfilter.active_filter_free(h)


def test_alloc_rejects_invalid(libfilter: ctypes.CDLL) -> None:
    h = ctypes.c_void_p()
    assert libfilter.active_filter_alloc(ctypes.byref(h), 0, 8) == EINVAL
    assert libfilter.active_filter_alloc(ctypes.byref(h), 32, -1) == EINVAL


# ---------------------------------------------------------------------------
# Static mask: low-coord sites are flagged, bulk is not
# ---------------------------------------------------------------------------


def test_compute_static_flags_endpoints_in_chain(libfilter: ctypes.CDLL) -> None:
    """In a 1D chain, sites 0 and N-1 have degree 1; with bulk_thr=2 they
    are 'low-coord' but interior sites (degree 2) are not."""
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with _Lattice(libfilter, n, offsets, indices) as lat, _AF(libfilter, n, 2) as af:
        af.compute_static(lat)
        # Without any rescan/mark, n_active is still 0 (static mask is just
        # the bitmap; we haven't seeded the active_list yet).
        assert af.n_active() == 0
        assert af.is_static(0) == 1
        assert af.is_static(n - 1) == 1
        for s in range(1, n - 1):
            assert af.is_static(s) == 0


def test_compute_static_on_square_grid_flags_perimeter(libfilter: ctypes.CDLL) -> None:
    """On a 4x4 square grid, perimeter sites have degree < 4; interior
    sites have degree 4. With bulk_thr=4, perimeter is static-active."""
    offsets, indices, n = _square_grid_csr(4, 4)
    with _Lattice(libfilter, n, offsets, indices) as lat, _AF(libfilter, n, 4) as af:
        af.compute_static(lat)
        # Interior is the 2x2 block at i,j in {1,2}.
        interior = {1 * 4 + 1, 1 * 4 + 2, 2 * 4 + 1, 2 * 4 + 2}
        for s in range(n):
            expected = 0 if s in interior else 1
            assert af.is_static(s) == expected, f"site {s} expected static={expected}"


def test_clear_dynamic_seeds_from_static_mask(libfilter: ctypes.CDLL) -> None:
    """clear_dynamic() copies static_mask into is_active and active_list."""
    n = 6
    offsets, indices = _linear_chain_csr(n)
    with _Lattice(libfilter, n, offsets, indices) as lat, _AF(libfilter, n, 2) as af:
        af.compute_static(lat)
        af.clear_dynamic()
        assert af.active_set() == {0, n - 1}
        assert af.n_active() == 2


# ---------------------------------------------------------------------------
# mark / unmark / clear
# ---------------------------------------------------------------------------


def test_mark_idempotent(libfilter: ctypes.CDLL) -> None:
    n = 16
    with _AF(libfilter, n, 0) as af:
        af.mark(5)
        af.mark(5)
        af.mark(5)
        assert af.n_active() == 1
        assert af.active_set() == {5}


def test_unmark_swap_last_invariant(libfilter: ctypes.CDLL) -> None:
    """Unmarking a non-last entry must move the last entry into the freed
    slot and update its list_idx[] reverse pointer."""
    n = 16
    with _AF(libfilter, n, 0) as af:
        for s in (1, 4, 9, 11):
            af.mark(s)
        assert af.n_active() == 4
        af.unmark(4)
        assert af.n_active() == 3
        assert af.active_set() == {1, 9, 11}
        af.unmark(11)
        assert af.n_active() == 2
        assert af.active_set() == {1, 9}


def test_unmark_unmarked_is_noop(libfilter: ctypes.CDLL) -> None:
    n = 8
    with _AF(libfilter, n, 0) as af:
        af.unmark(3)
        assert af.n_active() == 0
        af.mark(3)
        af.unmark(3)
        af.unmark(3)
        assert af.n_active() == 0


def test_clear_dynamic_drops_marks_keeps_static(libfilter: ctypes.CDLL) -> None:
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with _Lattice(libfilter, n, offsets, indices) as lat, _AF(libfilter, n, 2) as af:
        af.compute_static(lat)
        af.mark(3)
        af.mark(5)
        assert af.active_set() == {3, 5}

        af.clear_dynamic()
        # Post-clear: dynamic gone; static (endpoints 0, n-1) seeded.
        assert af.active_set() == {0, n - 1}


# ---------------------------------------------------------------------------
# Rescan: vacancies + their 1NN
# ---------------------------------------------------------------------------


def test_rescan_marks_vacancy_and_its_neighbours(libfilter: ctypes.CDLL) -> None:
    """Vacancy at site 4 in an 8-site chain → active = {3, 4, 5}."""
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[4]) as st,
        _AF(libfilter, n, 0) as af,
    ):
        af.compute_static(lat)  # bulk_thr=0 → no static-active sites
        af.rescan(lat, st)
        assert af.active_set() == {3, 4, 5}


def test_rescan_unions_static_with_dynamic(libfilter: ctypes.CDLL) -> None:
    """Endpoint static + middle vacancy → both flagged."""
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[4]) as st,
        _AF(libfilter, n, 2) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        # Active = static {0, 7} ∪ vacancy_dynamic {3, 4, 5}
        assert af.active_set() == {0, 3, 4, 5, 7}


def test_rescan_handles_multiple_vacancies(libfilter: ctypes.CDLL) -> None:
    n = 10
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[2, 6]) as st,
        _AF(libfilter, n, 0) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        # Stencils: {1,2,3} ∪ {5,6,7} = {1,2,3,5,6,7}
        assert af.active_set() == {1, 2, 3, 5, 6, 7}


def test_rescan_overlapping_stencils_dedupe(libfilter: ctypes.CDLL) -> None:
    """Two adjacent vacancies — overlap site present once, not twice."""
    n = 10
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[3, 4]) as st,
        _AF(libfilter, n, 0) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        # Stencils: {2,3,4} ∪ {3,4,5} = {2,3,4,5}; n_active should be 4.
        assert af.active_set() == {2, 3, 4, 5}
        assert af.n_active() == 4


def test_rescan_zero_vacancies_static_only(libfilter: ctypes.CDLL) -> None:
    n = 6
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[]) as st,
        _AF(libfilter, n, 2) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        assert af.active_set() == {0, n - 1}


def test_rescan_idempotent(libfilter: ctypes.CDLL) -> None:
    """Calling rescan twice with the same inputs gives the same set."""
    n = 8
    offsets, indices = _linear_chain_csr(n)
    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[4]) as st,
        _AF(libfilter, n, 2) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        first = af.active_set()
        af.rescan(lat, st)
        second = af.active_set()
        assert first == second


def test_rescan_on_square_grid_with_vacancy(libfilter: ctypes.CDLL) -> None:
    """4x4 grid, vacancy at (1,1). Active = perimeter ∪ {(1,1) and its 4 1NN}.
    Site (1,1) idx = 5; 1NN are (0,1), (2,1), (1,0), (1,2) = {1,9,4,6}. Plus
    perimeter (12 sites)."""
    nx, ny = 4, 4
    offsets, indices, n = _square_grid_csr(nx, ny)
    interior = {1 * 4 + 1, 1 * 4 + 2, 2 * 4 + 1, 2 * 4 + 2}
    perimeter = set(range(n)) - interior

    vac = 1 * 4 + 1  # site (1,1)
    nn1 = {(1 - 1) * 4 + 1, (1 + 1) * 4 + 1, 1 * 4 + (1 - 1), 1 * 4 + (1 + 1)}
    expected = perimeter | {vac} | nn1

    with (
        _Lattice(libfilter, n, offsets, indices) as lat,
        _State(libfilter, n_sites=n, n_vac_max=4, vac_list=[vac]) as st,
        _AF(libfilter, n, 4) as af,
    ):
        af.compute_static(lat)
        af.rescan(lat, st)
        assert af.active_set() == expected


# ---------------------------------------------------------------------------
# Vacancy-only rescan (large-system-scaling WP4a; step-loop-full-rescan/01)
#
# When every Process anchors on a vacancy, kmc.c touches up only the list
# active_filter_rescan_vacancies builds. touchup_a appends each enrolled site
# to its proc's avail_sites list and avail_sites_select picks a slot of that
# list, so for the selected events to stay bitwise identical that list must be
# the vacant sites of active_filter_rescan's list in the SAME order: the static
# vacancies by ascending site, then the others at their first appearance in
# the vacancy + 1NN walk (a vacancy can first appear as the 1NN of a vacancy
# ahead of it in vac_list). Neither vac_list order nor site order is right.
# ---------------------------------------------------------------------------

SP_VACANT, SP_NI, SP_FE, SP_CR = 0, 1, 2, 3  # events_base.h
FCC_BULK_NN1 = 12  # replica.c PYLATKMC_FCC_BULK_NN1


class _StateAction(ctypes.Structure):
    _fields_ = [("site", ctypes.c_int32), ("before", ctypes.c_uint8), ("after", ctypes.c_uint8)]


class _CStatePrefix(ctypes.Structure):
    """The leading fields of the C `State` (state.h)."""

    _fields_ = [
        ("species", ctypes.POINTER(ctypes.c_uint8)),
        ("vac_list", ctypes.POINTER(ctypes.c_int32)),
        ("vac_idx_of", ctypes.POINTER(ctypes.c_int32)),
        ("n_vac", ctypes.c_int32),
        ("n_vac_max", ctypes.c_int32),
    ]


@pytest.fixture(scope="module")
def libscan(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    """active_filter + state_actions + the test helpers, so a state can be
    evolved by the production vac_list bookkeeping between rescans."""
    if not _have_cc():
        pytest.skip("cc not on PATH")
    builddir = tmp_path_factory.mktemp("active_filter_scan_lib")
    libpath = builddir / ("libscan.dylib" if os.uname().sysname == "Darwin" else "libscan.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(RUNTIME_CORE), str(ACTIVE_FILTER_SRC), str(RUNTIME_CORE / "state_actions.c")]
    cmd += [str(HELPERS_SRC), "-o", str(libpath)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"active_filter + state_actions + helpers failed to compile:\n{res.stderr}")
    lib = ctypes.CDLL(str(libpath))
    vp, i32 = ctypes.c_void_p, ctypes.c_int32
    lib.active_filter_alloc.restype = ctypes.c_int
    lib.active_filter_alloc.argtypes = [ctypes.POINTER(vp), i32, i32]
    lib.active_filter_free.argtypes = [vp]
    lib.active_filter_compute_static.restype = ctypes.c_int
    lib.active_filter_compute_static.argtypes = [vp, vp]
    lib.active_filter_rescan.argtypes = [vp, vp, vp]
    lib.active_filter_rescan_vacancies.argtypes = [vp, vp, vp]
    lib.active_filter_n_active.restype = i32
    lib.active_filter_n_active.argtypes = [vp]
    lib.active_filter_site_at.restype = i32
    lib.active_filter_site_at.argtypes = [vp, i32]
    lib.state_apply_actions.restype = ctypes.c_int
    lib.state_apply_actions.argtypes = [vp, ctypes.POINTER(_StateAction), i32, ctypes.c_uint8]
    lib.pylatkmc_test_make_lattice.restype = vp
    lib.pylatkmc_test_make_lattice.argtypes = [i32, ctypes.POINTER(i32), ctypes.POINTER(i32)]
    lib.pylatkmc_test_free_lattice.argtypes = [vp]
    lib.pylatkmc_test_make_state.restype = vp
    lib.pylatkmc_test_make_state.argtypes = [
        i32,
        i32,
        i32,
        ctypes.POINTER(i32),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_free_state.argtypes = [vp]
    return lib


def _fcc_slab_csr(nx: int, ny: int, nz: int, rng: random.Random) -> tuple[list[int], list[int]]:
    """1NN CSR of an FCC(100) slab: nz layers of nx x ny sites, periodic in
    plane, open along z, so the top and bottom layers have 8 neighbours
    (static) and the rest 12. Odd layers sit at (i + 1/2, j + 1/2), so a
    site's cross-layer 1NN are the 4 cells around it in each adjacent layer.
    Every site's neighbour order is shuffled: the rescan walks CSR order."""

    def idx(k: int, i: int, j: int) -> int:
        return (k * nx + i % nx) * ny + j % ny

    offsets, indices = [0], []
    for k in range(nz):
        d = (0, 1) if k % 2 else (-1, 0)
        for i in range(nx):
            for j in range(ny):
                nbrs = [idx(k, i + 1, j), idx(k, i - 1, j), idx(k, i, j + 1), idx(k, i, j - 1)]
                for kk in (k - 1, k + 1):
                    if 0 <= kk < nz:
                        nbrs += [idx(kk, i + a, j + b) for a in d for b in d]
                rng.shuffle(nbrs)
                indices += nbrs
                offsets.append(len(indices))
    return offsets, indices


def _rescan_reference(offsets: list[int], indices: list[int], vac_list: list[int]) -> list[int]:
    """active_filter_rescan's order before WP4a: a pass over every site seeds
    the static (low-coordination) sites in ascending order, then each vacancy
    of vac_list and its 1NN in CSR order are listed at first appearance."""
    n_sites = len(offsets) - 1
    order = [s for s in range(n_sites) if offsets[s + 1] - offsets[s] < FCC_BULK_NN1]
    seen = set(order)
    for v in vac_list:
        for s in (v, *indices[offsets[v] : offsets[v + 1]]):
            if s not in seen:
                seen.add(s)
                order.append(s)
    return order


def _listed(lib: ctypes.CDLL, h: ctypes.c_void_p) -> list[int]:
    """The filter's active list, in order."""
    return [lib.active_filter_site_at(h, i) for i in range(lib.active_filter_n_active(h))]


class _ScanFilter:
    """An ActiveFilter over one lattice, with its static part computed."""

    def __init__(self, lib: ctypes.CDLL, n_sites: int, lat: int) -> None:
        self.lib = lib
        self.h = ctypes.c_void_p()
        assert lib.active_filter_alloc(ctypes.byref(self.h), n_sites, FCC_BULK_NN1) == 0
        assert lib.active_filter_compute_static(self.h, lat) == 0

    def rescan(self, lat: int, st: int) -> list[int]:
        self.lib.active_filter_rescan(self.h, lat, st)
        return _listed(self.lib, self.h)

    def rescan_vacancies(self, lat: int, st: int) -> list[int]:
        self.lib.active_filter_rescan_vacancies(self.h, lat, st)
        return _listed(self.lib, self.h)

    def free(self) -> None:
        self.lib.active_filter_free(self.h)


def test_rescan_vacancies_order_on_a_chain(libscan: ctypes.CDLL) -> None:
    """Hand-checked: in a 10-site chain (every site is static at the FCC bulk
    threshold, as at a surface) the order is ascending; with bulk_thr 2 only
    the endpoints are static and the walk order shows. vac_list [6, 2, 5, 9]:
    static vacancy 9 first, then 6, then 5 (the 1NN of 6, ahead of its own
    vac_list slot), then 2 — neither vac_list nor site order."""
    n = 10
    offsets, indices = _linear_chain_csr(n)
    vac = [6, 2, 5, 9]
    species = [SP_VACANT if s in vac else SP_NI for s in range(n)]
    lat = libscan.pylatkmc_test_make_lattice(n, _i32arr(offsets), _i32arr(indices))
    st = libscan.pylatkmc_test_make_state(
        n, 8, len(vac), _i32arr(vac), (ctypes.c_uint8 * n)(*species)
    )
    assert lat and st
    filters = []
    try:
        for thr, expected in ((FCC_BULK_NN1, [2, 5, 6, 9]), (2, [9, 6, 5, 2])):
            h = ctypes.c_void_p()
            assert libscan.active_filter_alloc(ctypes.byref(h), n, thr) == 0
            filters.append(h)
            assert libscan.active_filter_compute_static(h, lat) == 0
            libscan.active_filter_rescan(h, lat, st)
            full = _listed(libscan, h)
            libscan.active_filter_rescan_vacancies(h, lat, st)
            got = _listed(libscan, h)
            assert got == expected
            assert got == [s for s in full if species[s] == SP_VACANT]
    finally:
        for h in filters:
            libscan.active_filter_free(h)
        libscan.pylatkmc_test_free_state(st)
        libscan.pylatkmc_test_free_lattice(lat)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_rescan_vacancies_is_rescans_vacant_subsequence(libscan: ctypes.CDLL, seed: int) -> None:
    """On an FCC slab whose state is evolved by the production vac_list
    bookkeeping (state_apply_actions: hops swap-last a vacancy out of
    vac_list and append its new site, dissolutions append, refills
    swap-last) through adjacent vacancies, surface (static) vacancies and
    vacancies created mid-run, every state satisfies: rescan's list is the
    pre-WP4a order, and rescan_vacancies' list is its vacant subsequence. The
    filters are reused across states, as in the step loop, and one of them
    alternates between the two rescans."""
    rng = random.Random(seed)
    nx = ny = nz = 6
    n = nx * ny * nz
    offsets, indices = _fcc_slab_csr(nx, ny, nz, rng)
    nbrs = [indices[offsets[s] : offsets[s + 1]] for s in range(n)]
    static = [s for s in range(n) if len(nbrs[s]) < FCC_BULK_NN1]
    species = [rng.choice((SP_NI, SP_NI, SP_FE, SP_CR)) for _ in range(n)]
    seed_site = rng.randrange(n)
    vac = [seed_site, *rng.sample(nbrs[seed_site], 3)]  # an adjacent cluster
    vac = list(dict.fromkeys(vac + rng.sample(static, 4) + rng.sample(range(n), 4)))
    rng.shuffle(vac)
    for s in vac:
        species[s] = SP_VACANT
    lat = libscan.pylatkmc_test_make_lattice(n, _i32arr(offsets), _i32arr(indices))
    st = libscan.pylatkmc_test_make_state(
        n, 64, len(vac), _i32arr(vac), (ctypes.c_uint8 * n)(*species)
    )
    assert lat and st
    view = _CStatePrefix.from_address(st)
    af_full, af_vac, af_mixed = (_ScanFilter(libscan, n, lat) for _ in range(3))
    seen = {"not_vac_list_order": 0, "not_site_order": 0, "static_and_bulk": 0}
    try:
        for step in range(400):
            sp = [view.species[s] for s in range(n)]
            vac_list = [view.vac_list[i] for i in range(view.n_vac)]
            full = af_full.rescan(lat, st)
            assert full == _rescan_reference(offsets, indices, vac_list), f"seed {seed} step {step}"
            want = [s for s in full if sp[s] == SP_VACANT]
            assert sorted(want) == sorted(vac_list)
            assert af_vac.rescan_vacancies(lat, st) == want, f"seed {seed} step {step}"
            mixed = af_mixed.rescan(lat, st) if step % 2 else af_mixed.rescan_vacancies(lat, st)
            assert mixed == (full if step % 2 else want), f"seed {seed} step {step}"
            seen["not_vac_list_order"] += want != vac_list
            seen["not_site_order"] += want != sorted(want)
            seen["static_and_bulk"] += 0 < sum(s in static for s in want) < len(want)

            # Next state: a hop (60 %), a dissolution (25 %) or a refill (15 %).
            r = rng.random()
            if r < 0.6:
                v = rng.choice(vac_list)
                occupied = [j for j in nbrs[v] if sp[j] != SP_VACANT]
                if not occupied:
                    continue
                j = rng.choice(occupied)
                acts = [(v, SP_VACANT, sp[j]), (j, sp[j], SP_VACANT)]
            elif r < 0.85 and view.n_vac < view.n_vac_max:
                pool = static if rng.random() < 0.5 else range(n)
                s = rng.choice([s for s in pool if sp[s] != SP_VACANT])
                acts = [(s, sp[s], SP_VACANT)]
            elif view.n_vac > 1:
                acts = [(rng.choice(vac_list), SP_VACANT, SP_NI)]
            else:
                continue
            arr = (_StateAction * len(acts))(*(_StateAction(*a) for a in acts))
            assert libscan.state_apply_actions(st, arr, len(acts), SP_VACANT) == 0
    finally:
        for af in (af_full, af_vac, af_mixed):
            af.free()
        libscan.pylatkmc_test_free_state(st)
        libscan.pylatkmc_test_free_lattice(lat)
    # The states covered the orders a shortcut would get wrong.
    assert all(count > 20 for count in seen.values()), seen


def test_compute_static_rejects_a_lattice_without_csr(libscan: ctypes.CDLL) -> None:
    h = ctypes.c_void_p()
    assert libscan.active_filter_alloc(ctypes.byref(h), 4, FCC_BULK_NN1) == 0
    try:
        assert libscan.active_filter_compute_static(h, None) == EINVAL
    finally:
        libscan.active_filter_free(h)
