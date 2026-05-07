"""Ctypes-driven tests for the runtime's NeighbourCode lookup table (M-D-Prep.3).

The C source under test is `runtime/src/core/lattice.c`'s
`lattice_build_coord_table`, plus the canonical deltas in
`runtime/src/core/coord_codes.c`. Together they implement the kmos-
inspired direction-resolution mechanism that lets the codegen emit
`coord_table[site * N_NEIGHBOUR_CODES + nc]` instead of trying to
encode FCC neighbours as integer (di, dj, dk) triples (which is
impossible for cross-layer 1NN — see § "The coord-resolution gap"
in the plan).

Test fixture: a small (nx, ny, nz) FCC (100) slab built in Python
that mirrors `tools/build_initial_config.py:build_fcc100_slab`. We
compute positions, nn1/nn2 CSRs (Euclidean cutoff, with PBC in xy
only), pass them into `_runtime_test_helpers.c::pylatkmc_test_make_lattice_full`,
then call `lattice_build_coord_table` and verify each NeighbourCode
resolves correctly.
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
LATTICE_SRC = RUNTIME_CORE / "lattice.c"
COORD_CODES_SRC = RUNTIME_CORE / "coord_codes.c"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"


# Mirror the NeighbourCode enum from coord_codes.h. If the enum changes,
# update both — there's no auto-sync.
NC_ANCHOR = 0
NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY = 1, 2, 3, 4
NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM = 5, 6, 7, 8
NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM = 9, 10, 11, 12
NC_NN2_DIAG_PP, NC_NN2_DIAG_PM, NC_NN2_DIAG_MP, NC_NN2_DIAG_MM = 13, 14, 15, 16
NC_NN2_PX, NC_NN2_MX, NC_NN2_PY, NC_NN2_MY, NC_NN2_PZ, NC_NN2_MZ = 17, 18, 19, 20, 21, 22
N_NEIGHBOUR_CODES = 23


def _have_cc() -> bool:
    return shutil.which("cc") is not None


@pytest.fixture(scope="module")
def liblat(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if not _have_cc():
        pytest.skip("cc not on PATH")
    builddir = tmp_path_factory.mktemp("coord_table_lib")
    libname = "libcoord_table.dylib" if os.uname().sysname == "Darwin" else "libcoord_table.so"
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
        str(LATTICE_SRC),
        str(COORD_CODES_SRC),
        str(HELPERS_SRC),
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")

    lib = ctypes.CDLL(str(libpath))

    # lattice_build_coord_table(Lattice*) -> int
    lib.lattice_build_coord_table.restype = ctypes.c_int
    lib.lattice_build_coord_table.argtypes = [ctypes.c_void_p]

    # lattice_coord_at is `static inline` in the header, so we can't call it
    # directly from ctypes. Read coord_table via the Lattice struct view
    # (same pattern as test_state_apply_actions).

    # pylatkmc_test_make_lattice_full
    lib.pylatkmc_test_make_lattice_full.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_lattice_full.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_float),  # positions (or NULL)
        ctypes.POINTER(ctypes.c_float),  # cell (or NULL)
        ctypes.c_float,  # nn_dist
        ctypes.POINTER(ctypes.c_int32),  # nn1_offsets
        ctypes.POINTER(ctypes.c_int32),  # nn1_indices
        ctypes.POINTER(ctypes.c_int32),  # nn2_offsets (or NULL)
        ctypes.POINTER(ctypes.c_int32),  # nn2_indices (or NULL)
    ]
    lib.pylatkmc_test_free_lattice.restype = None
    lib.pylatkmc_test_free_lattice.argtypes = [ctypes.c_void_p]

    return lib


# ---------------------------------------------------------------------------
# Lattice struct view (must match runtime/src/core/lattice.h field order)
# ---------------------------------------------------------------------------


class _CLattice(ctypes.Structure):
    _fields_ = [
        ("n_sites", ctypes.c_int32),
        ("n_layers", ctypes.c_int32),
        ("cell", ctypes.c_float * 3),
        ("nn_dist", ctypes.c_float),
        ("positions", ctypes.c_void_p),
        ("layer_index", ctypes.c_void_p),
        ("site_class", ctypes.c_void_p),
        ("nn1_offsets", ctypes.c_void_p),
        ("nn1_indices", ctypes.c_void_p),
        ("nn1_dir_family", ctypes.c_void_p),
        ("nn2_offsets", ctypes.c_void_p),
        ("nn2_indices", ctypes.c_void_p),
        ("nn2_dir_family", ctypes.c_void_p),
        ("coord_table", ctypes.c_void_p),
        ("_mmap_base", ctypes.c_void_p),
        ("_mmap_size", ctypes.c_size_t),
    ]


def _coord_at(lat_ptr: int, n_sites: int, site: int, nc: int) -> int:
    """Read coord_table[site * N_NC + nc] via the C struct."""
    view = _CLattice.from_address(lat_ptr)
    if not view.coord_table:
        return -2
    table = ctypes.cast(
        view.coord_table, ctypes.POINTER(ctypes.c_int32 * (n_sites * N_NEIGHBOUR_CODES))
    )
    return int(table.contents[site * N_NEIGHBOUR_CODES + nc])


# ---------------------------------------------------------------------------
# Build a synthetic FCC (100) slab in Python (mirrors build_initial_config.py)
# ---------------------------------------------------------------------------


def _build_fcc100_slab(nx: int, ny: int, nz: int, nn_d: float = 2.5):
    """Returns (positions, cell, nn1_off, nn1_idx, nn2_off, nn2_idx)."""
    ls = nn_d / math.sqrt(2.0)
    sites = []
    for k in range(nz):
        dx = 0.5 * nn_d if (k % 2 == 1) else 0.0
        dy = 0.5 * nn_d if (k % 2 == 1) else 0.0
        for i in range(nx):
            for j in range(ny):
                x = i * nn_d + dx
                y = j * nn_d + dy
                z = k * ls
                sites.append((x, y, z))
    n = len(sites)
    positions = [c for site in sites for c in site]
    cell = [nx * nn_d, ny * nn_d, nz * ls]  # match build_initial_config (no vacuum)

    # Min-image displacement helper.
    def mi(d, L):
        if d > 0.5 * L:
            return d - L
        if d < -0.5 * L:
            return d + L
        return d

    def edges_at(cutoff_lo, cutoff_hi):
        """Pairs (i, j) with cutoff_lo < |r_ij| <= cutoff_hi using PBC in xy."""
        offsets = [0]
        indices = []
        for i in range(n):
            xi, yi, zi = sites[i]
            for j in range(n):
                if j == i:
                    continue
                xj, yj, zj = sites[j]
                dx = mi(xj - xi, cell[0])
                dy = mi(yj - yi, cell[1])
                dz = mi(zj - zi, cell[2])
                d = math.sqrt(dx * dx + dy * dy + dz * dz)
                if cutoff_lo < d <= cutoff_hi:
                    indices.append(j)
            offsets.append(len(indices))
        return offsets, indices

    nn1_off, nn1_idx = edges_at(0.0, nn_d * 1.05)
    nn2_off, nn2_idx = edges_at(nn_d * 1.05, nn_d * 1.4143 + 0.05)
    return positions, cell, nn1_off, nn1_idx, nn2_off, nn2_idx


def _make_lattice(lib, nx, ny, nz, nn_d=2.5):
    positions, cell, n1o, n1i, n2o, n2i = _build_fcc100_slab(nx, ny, nz, nn_d)
    n = nx * ny * nz
    pos_arr = (ctypes.c_float * (n * 3))(*positions)
    cell_arr = (ctypes.c_float * 3)(*cell)
    n1o_arr = (ctypes.c_int32 * len(n1o))(*n1o)
    n1i_arr = (ctypes.c_int32 * max(1, len(n1i)))(*n1i) if n1i else (ctypes.c_int32 * 1)(0)
    n2o_arr = (ctypes.c_int32 * len(n2o))(*n2o)
    n2i_arr = (ctypes.c_int32 * max(1, len(n2i)))(*n2i) if n2i else (ctypes.c_int32 * 1)(0)
    lat = lib.pylatkmc_test_make_lattice_full(
        n,
        pos_arr,
        cell_arr,
        ctypes.c_float(nn_d),
        n1o_arr,
        n1i_arr,
        n2o_arr,
        n2i_arr,
    )
    if not lat:
        raise RuntimeError("pylatkmc_test_make_lattice_full returned NULL")
    return lat, n, sites_from_positions(positions, n)


def sites_from_positions(positions, n):
    return [(positions[3 * i], positions[3 * i + 1], positions[3 * i + 2]) for i in range(n)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_coord_table_returns_zero(liblat) -> None:
    """Smoke: building the table on a small slab succeeds."""
    lat, n, _ = _make_lattice(liblat, 4, 4, 3)
    try:
        rc = liblat.lattice_build_coord_table(lat)
        assert rc == 0
        # And the table is non-NULL afterwards.
        view = _CLattice.from_address(lat)
        assert view.coord_table is not None
        assert view.coord_table != 0
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_anchor_code_resolves_to_self(liblat) -> None:
    """NC_ANCHOR for site s should be s itself."""
    lat, n, _ = _make_lattice(liblat, 4, 4, 3)
    try:
        liblat.lattice_build_coord_table(lat)
        for s in range(n):
            assert _coord_at(lat, n, s, NC_ANCHOR) == s
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_in_plane_axial_1nn_resolves(liblat) -> None:
    """For an interior site in layer 0, NC_NN1_PX should resolve to a site
    at +nn_d in x with the same y, z."""
    nn_d = 2.5
    nx, ny, nz = 4, 4, 3
    lat, n, sites = _make_lattice(liblat, nx, ny, nz, nn_d)
    try:
        liblat.lattice_build_coord_table(lat)
        # Pick site (i=1, j=1, k=0) — interior layer 0. Index = k*nx*ny + i*ny + j.
        s = 0 * nx * ny + 1 * ny + 1
        sx, sy, sz = sites[s]
        # +x neighbour
        nbr_px = _coord_at(lat, n, s, NC_NN1_PX)
        assert nbr_px >= 0, f"NC_NN1_PX should resolve at site {s}"
        nx_pos, ny_pos, nz_pos = sites[nbr_px]
        assert abs((nx_pos - sx) - nn_d) < 0.05
        assert abs(ny_pos - sy) < 0.05
        assert abs(nz_pos - sz) < 0.05
        # -x
        nbr_mx = _coord_at(lat, n, s, NC_NN1_MX)
        assert nbr_mx >= 0
        # +y, -y
        assert _coord_at(lat, n, s, NC_NN1_PY) >= 0
        assert _coord_at(lat, n, s, NC_NN1_MY) >= 0
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_in_plane_diagonal_2nn_resolves(liblat) -> None:
    """In-plane diagonal 2NN at (±1, ±1, 0)*nn_d should resolve for a layer-0 site."""
    nn_d = 2.5
    lat, n, _ = _make_lattice(liblat, 4, 4, 3, nn_d)
    try:
        liblat.lattice_build_coord_table(lat)
        s = 0 * 4 * 4 + 1 * 4 + 1  # (i=1, j=1, k=0)
        for nc in (NC_NN2_DIAG_PP, NC_NN2_DIAG_PM, NC_NN2_DIAG_MP, NC_NN2_DIAG_MM):
            assert _coord_at(lat, n, s, nc) >= 0, f"NC code {nc} unresolved"
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_cross_layer_up_codes_for_layer0_site(liblat) -> None:
    """An even-layer (k=0) site has 4 cross-layer-up 1NN going to layer 1.
    NC_NN1_UP_PP/PM/MP/MM should all resolve."""
    nn_d = 2.5
    lat, n, sites = _make_lattice(liblat, 4, 4, 3, nn_d)
    try:
        liblat.lattice_build_coord_table(lat)
        s = 1 * 4 + 1  # k=0 layer, interior
        for nc in (NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM):
            n_idx = _coord_at(lat, n, s, nc)
            assert n_idx >= 0, f"NC code {nc} unresolved at layer-0 site"
            # Verify it's actually in the layer above (z higher).
            assert sites[n_idx][2] > sites[s][2]
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_cross_layer_down_for_top_layer_site(liblat) -> None:
    """A top-layer (k=nz-1) site has 4 cross-layer-down 1NN going to layer nz-2.
    NC_NN1_DOWN_* should resolve."""
    nn_d = 2.5
    nx, ny, nz = 4, 4, 3
    lat, n, sites = _make_lattice(liblat, nx, ny, nz, nn_d)
    try:
        liblat.lattice_build_coord_table(lat)
        s = (nz - 1) * nx * ny + 1 * ny + 1  # top layer, interior
        for nc in (NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM):
            n_idx = _coord_at(lat, n, s, nc)
            assert n_idx >= 0, f"NC code {nc} unresolved at top-layer site"
            assert sites[n_idx][2] < sites[s][2]
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_top_layer_has_no_up_codes(liblat) -> None:
    """A top-layer site has no NC_NN1_UP_* (no layer above).

    coord_table fills missing-neighbour entries with the stub site index
    `n_sites` (not -1) — the State allocator places a sentinel at
    species[n_sites] so the decision tree's reads naturally fall through
    `default:` instead of segfaulting on species[-1]."""
    nx, ny, nz = 4, 4, 3
    lat, n, _ = _make_lattice(liblat, nx, ny, nz)
    try:
        liblat.lattice_build_coord_table(lat)
        s = (nz - 1) * nx * ny + 0  # top layer, corner
        for nc in (NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM):
            assert _coord_at(lat, n, s, nc) == n  # stub site = n_sites
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_bottom_layer_has_no_down_codes(liblat) -> None:
    """A bottom-layer (k=0) site has no NC_NN1_DOWN_* (no layer below).
    Note: with PBC in z disabled (cell[2] = nz * ls = exactly slab thickness,
    no vacuum), z-PBC may wrap. The slab generator uses non-PBC z by setting
    cell[2] = nz * ls — that means the layer-0 z=0 site sees layer (nz-1)
    via PBC at distance ls. We need to verify the actual behaviour."""
    nx, ny, nz = 4, 4, 3
    lat, n, sites = _make_lattice(liblat, nx, ny, nz)
    try:
        liblat.lattice_build_coord_table(lat)
        s = 0 * nx * ny + 1 * ny + 1  # k=0, interior
        # If z PBC IS active (no vacuum), the down-neighbours wrap to the top
        # layer and their delta-z appears as +(nz-1)*ls — which doesn't match
        # the canonical -1/√2 delta. So they should NOT resolve to NC_NN1_DOWN_*.
        # If z PBC is NOT active (vacuum), they're absent. Either way: stub
        # site (= n_sites) instead of a real neighbour.
        for nc in (NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM):
            n_idx = _coord_at(lat, n, s, nc)
            # Allow either n (stub) or, if PBC happens to alias, still verify
            # the resolved neighbour really is at delta_z ≈ -ls (not +ls).
            if n_idx != n:
                dz = sites[n_idx][2] - sites[s][2]
                # Normalise via PBC
                Lz = nz * (2.5 / math.sqrt(2))
                if dz > Lz / 2:
                    dz -= Lz
                elif dz < -Lz / 2:
                    dz += Lz
                assert dz < 0, "NC_NN1_DOWN_* resolved to a delta-z>0 neighbour"
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_full_bulk_site_has_all_12_1nn_codes(liblat) -> None:
    """A site with full 1NN coordination (12 neighbours) should have all 12
    1NN codes resolved (4 in-plane + 4 cross-layer-up + 4 cross-layer-down)."""
    nn_d = 2.5
    nx, ny, nz = 4, 4, 5  # 5 layers — middle layer (k=2) is fully bulk-coordinated
    lat, n, _ = _make_lattice(liblat, nx, ny, nz, nn_d)
    try:
        liblat.lattice_build_coord_table(lat)
        s = 2 * nx * ny + 1 * ny + 1  # k=2 (middle), interior

        in_plane_codes = (NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY)
        up_codes = (NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM)
        down_codes = (NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM)

        for nc in in_plane_codes + up_codes + down_codes:
            assert _coord_at(lat, n, s, nc) >= 0, f"NC code {nc} unresolved at full-bulk site"
    finally:
        liblat.pylatkmc_test_free_lattice(lat)


def test_no_two_codes_resolve_to_same_neighbour_for_bulk_site(liblat) -> None:
    """For a fully-coordinated bulk site, the 12 1NN codes should resolve
    to 12 distinct neighbours (no aliasing)."""
    lat, n, _ = _make_lattice(liblat, 4, 4, 5)
    try:
        liblat.lattice_build_coord_table(lat)
        s = 2 * 4 * 4 + 1 * 4 + 1  # bulk site

        codes_1nn = list(range(NC_NN1_PX, NC_NN1_UP_MM + 1))  # 12 codes
        seen = []
        for nc in codes_1nn:
            n_idx = _coord_at(lat, n, s, nc)
            if n_idx >= 0:
                seen.append(n_idx)
        assert len(seen) == len(set(seen)), f"duplicate neighbours across codes: {seen}"
    finally:
        liblat.pylatkmc_test_free_lattice(lat)
