"""The O(n_vac) active set keeps the touchup order (step-loop-full-rescan/01).

``avail_sites`` keeps each proc's sites in ``touchup_a`` call order and BKL
selection indexes into those lists, so the order of the active list is part
of every fixed-seed trajectory. Before the fix every step re-seeded the
static (low-coordination) sites with a pass over all ``n_sites`` and touched
up every one of them, although on a model whose processes all anchor on a
vacancy (every shipped model except ``ni_dissolution_demo``) only vacancies
can enrol anything. Now:

- ``active_filter_rescan`` re-seeds the static sites from a list built once
  at startup; its order must equal the old one (static sites ascending, then
  each vac_list entry and its 1NN in CSR order, first appearance wins);
- ``active_filter_rescan_vacancies`` lists exactly the vacant sites of that
  order, in the same relative order (static vacancies ascending first; a
  vacancy that is a 1NN of an earlier vac_list entry comes before its own
  slot);
- ``kmc_step_once`` picks the vacancy rescan iff the generated proclist.h's
  ``PYLATKMC_ANCHOR_SPECIES_MASK`` is ``SP_VACANT`` alone, and the
  trajectory is bitwise the one the full rescan gives;
- codegen emits that mask from the processes' anchor species, and every
  committed proclist.h carries the mask its committed touchup implies.

The order tests run on a small FCC slab with free surfaces and shuffled CSR
neighbour order, on random multi-vacancy states: adjacent vacancies, surface
vacancies, and vacancies that dissolution adds (state_apply_actions appends
them; hops reorder vac_list by swap-last). ctypes and compile level only;
everything skips cleanly without cc.
"""

from __future__ import annotations

import ctypes
import random
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
MODELS = REPO_ROOT / "models"

SP_VACANT, SP_NI, SP_FE, SP_CR = 0, 1, 2, 3  # events_base.h
BULK_NN1 = 12  # replica.c PYLATKMC_FCC_BULK_NN1


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


def _i32(values: list[int]) -> ctypes.Array:
    return (ctypes.c_int32 * max(1, len(values)))(*values)


# ---------------------------------------------------------------------------
# A small FCC slab: free surfaces, shuffled CSR order
# ---------------------------------------------------------------------------


def _fcc_slab(
    nx: int, ny: int, nz: int, rng: random.Random
) -> tuple[list[int], list[int], list[int]]:
    """1NN CSR of an FCC slab of cubic half-cells (i, j, k), i + j + k even:
    periodic over 2*nx x 2*ny in-plane, free surfaces at k = 0 and nz - 1
    (8 1NN there, 12 inside). Each site's neighbour order is shuffled, so CSR
    order differs from index order. Returns (offsets, indices, layer)."""
    assert nx >= 2 and ny >= 2  # no duplicate neighbours through the wrap
    cells = [
        (i, j, k)
        for k in range(nz)
        for j in range(2 * ny)
        for i in range(2 * nx)
        if (i + j + k) % 2 == 0
    ]
    index = {c: n for n, c in enumerate(cells)}
    steps = [
        (a, b, c)
        for a in (-1, 0, 1)
        for b in (-1, 0, 1)
        for c in (-1, 0, 1)
        if abs(a) + abs(b) + abs(c) == 2
    ]
    offsets, indices = [0], []
    for i, j, k in cells:
        nbrs = [
            index[((i + a) % (2 * nx), (j + b) % (2 * ny), k + c)]
            for a, b, c in steps
            if 0 <= k + c < nz
        ]
        rng.shuffle(nbrs)
        indices += nbrs
        offsets.append(len(indices))
    return offsets, indices, [k for _, _, k in cells]


def _old_rescan_order(offsets: list[int], indices: list[int], vac_list: list[int]) -> list[int]:
    """The pre-fix active_filter_rescan, ported: every static site (1NN
    degree < 12) in ascending site order, then for each vac_list entry the
    vacancy and its 1NN in CSR order, each site where it first appears."""
    n = len(offsets) - 1
    order = [s for s in range(n) if offsets[s + 1] - offsets[s] < BULK_NN1]
    seen = set(order)
    for v in vac_list:
        for s in [v, *indices[offsets[v] : offsets[v + 1]]]:
            if s not in seen:
                seen.add(s)
                order.append(s)
    return order


def _random_species(
    offsets: list[int], indices: list[int], layer: list[int], n_vac: int, rng: random.Random
) -> list[int]:
    """Ni/Fe/Cr occupancy with n_vac vacancies: a few adjacent pairs, a few in
    the surface layers, the rest anywhere."""
    n = len(offsets) - 1
    species = [rng.choice((SP_NI, SP_NI, SP_FE, SP_CR)) for _ in range(n)]
    top = max(layer)
    surface = [s for s in range(n) if layer[s] in (0, top)]
    vac: set[int] = set()
    while len(vac) < n_vac:
        r = rng.random()
        if r < 0.4:  # an adjacent pair
            s = rng.randrange(n)
            vac.update((s, rng.choice(indices[offsets[s] : offsets[s + 1]])))
        elif r < 0.7:
            vac.add(rng.choice(surface))
        else:
            vac.add(rng.randrange(n))
    for s in vac:
        species[s] = SP_VACANT
    return species


# ---------------------------------------------------------------------------
# active_filter level: rescan orders on evolving states
# ---------------------------------------------------------------------------


class _CStatePrefix(ctypes.Structure):
    """The leading fields of runtime/src/core/state.h's State."""

    _fields_ = [
        ("species", ctypes.POINTER(ctypes.c_uint8)),
        ("vac_list", ctypes.POINTER(ctypes.c_int32)),
        ("vac_idx_of", ctypes.POINTER(ctypes.c_int32)),
        ("n_vac", ctypes.c_int32),
        ("n_vac_max", ctypes.c_int32),
    ]


class _StateAction(ctypes.Structure):
    _fields_ = [("site", ctypes.c_int32), ("before", ctypes.c_uint8), ("after", ctypes.c_uint8)]


@pytest.fixture(scope="module")
def libaf(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    tmp = tmp_path_factory.mktemp("active_set_order")
    lib = _build_lib(
        tmp, "afstate", [CORE / "active_filter.c", CORE / "state_actions.c", HELPERS_SRC]
    )
    vp, i32 = ctypes.c_void_p, ctypes.c_int32
    for fn, res, args in [
        ("active_filter_alloc", ctypes.c_int, [ctypes.POINTER(vp), i32, i32]),
        ("active_filter_free", None, [vp]),
        ("active_filter_compute_static", None, [vp, vp]),
        ("active_filter_rescan", None, [vp, vp, vp]),
        ("active_filter_rescan_vacancies", None, [vp, vp, vp]),
        ("active_filter_n_active", i32, [vp]),
        ("active_filter_site_at", i32, [vp, i32]),
        ("active_filter_is_active", i32, [vp, i32]),
        ("pylatkmc_test_make_lattice", vp, [i32, ctypes.POINTER(i32), ctypes.POINTER(i32)]),
        ("pylatkmc_test_free_lattice", None, [vp]),
        (
            "pylatkmc_test_make_state",
            vp,
            [i32, i32, i32, ctypes.POINTER(i32), ctypes.POINTER(ctypes.c_uint8)],
        ),
        ("pylatkmc_test_free_state", None, [vp]),
        (
            "state_apply_actions",
            ctypes.c_int,
            [vp, ctypes.POINTER(_StateAction), i32, ctypes.c_uint8],
        ),
    ]:
        getattr(lib, fn).restype = res
        getattr(lib, fn).argtypes = args
    return lib


def _active(lib: ctypes.CDLL, af: ctypes.c_void_p) -> list[int]:
    return [lib.active_filter_site_at(af, i) for i in range(lib.active_filter_n_active(af))]


def _check_orders(lib: ctypes.CDLL, af, lat, st, offsets, indices) -> list[int]:
    """Both rescans against the old order on the C state's current
    (species, vac_list). Returns the vacancy-rescan list."""
    view = _CStatePrefix.from_address(st)
    vac_list = [view.vac_list[i] for i in range(view.n_vac)]
    species = [view.species[s] for s in range(len(offsets) - 1)]
    old = _old_rescan_order(offsets, indices, vac_list)

    lib.active_filter_rescan(af, lat, st)
    assert _active(lib, af) == old, "active_filter_rescan changed the touchup order"

    lib.active_filter_rescan_vacancies(af, lat, st)
    got = _active(lib, af)
    assert got == [s for s in old if species[s] == SP_VACANT], (
        "the vacancy rescan is not the full order restricted to vacancies"
    )
    assert sorted(got) == sorted(vac_list)  # every vacancy, nothing else
    assert all(lib.active_filter_is_active(af, s) == (species[s] == SP_VACANT) for s in old)
    return got


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_rescans_keep_the_old_order_on_evolving_states(libaf: ctypes.CDLL, seed: int) -> None:
    """Random multi-vacancy states, then 150 random hops and dissolutions
    applied with state_apply_actions (removals reorder vac_list by swap-last,
    dissolution appends vacancies, mostly at the surface): after every one,
    the full rescan equals the old order and the vacancy rescan equals the
    old order restricted to vacant sites."""
    rng = random.Random(seed)
    offsets, indices, layer = _fcc_slab(4, 3, 6, rng)
    n = len(offsets) - 1
    species = _random_species(offsets, indices, layer, n_vac=10 + seed, rng=rng)
    vac_list = [s for s in range(n) if species[s] == SP_VACANT]
    rng.shuffle(vac_list)  # any vac_list order, not only initconfig's ascending one
    n_vac_max = len(vac_list) + 40

    lat = libaf.pylatkmc_test_make_lattice(n, _i32(offsets), _i32(indices))
    st = libaf.pylatkmc_test_make_state(
        n, n_vac_max, len(vac_list), _i32(vac_list), (ctypes.c_uint8 * n)(*species)
    )
    af = ctypes.c_void_p()
    assert lat and st and libaf.active_filter_alloc(ctypes.byref(af), n, BULK_NN1) == 0
    try:
        libaf.active_filter_compute_static(af, lat)
        static_vacancies = 0
        for _ in range(150):
            got = _check_orders(libaf, af, lat, st, offsets, indices)
            static_vacancies = max(
                static_vacancies,
                sum(1 for s in got if offsets[s + 1] - offsets[s] < BULK_NN1),
            )
            view = _CStatePrefix.from_address(st)
            vacs = [view.vac_list[i] for i in range(view.n_vac)]
            if rng.random() < 0.2 and view.n_vac < view.n_vac_max:
                # dissolution: an atom leaves, mostly from a surface layer
                pool = [
                    s
                    for s in range(n)
                    if view.species[s] != SP_VACANT
                    and (layer[s] in (0, max(layer)) or rng.random() < 0.05)
                ]
                if not pool:
                    continue
                s = rng.choice(pool)
                acts = (_StateAction * 1)(_StateAction(s, view.species[s], SP_VACANT))
                assert libaf.state_apply_actions(st, acts, 1, SP_VACANT) == 0
            else:  # a hop: a vacancy swaps with an occupied 1NN
                v = rng.choice(vacs)
                occ = [
                    m for m in indices[offsets[v] : offsets[v + 1]] if view.species[m] != SP_VACANT
                ]
                if not occ:
                    continue
                m = rng.choice(occ)
                sp = view.species[m]
                acts = (_StateAction * 2)(
                    _StateAction(v, SP_VACANT, sp), _StateAction(m, sp, SP_VACANT)
                )
                assert libaf.state_apply_actions(st, acts, 2, SP_VACANT) == 0
        _check_orders(libaf, af, lat, st, offsets, indices)
        assert static_vacancies >= 2, "the states never had surface vacancies to order"
    finally:
        libaf.active_filter_free(af)
        libaf.pylatkmc_test_free_state(st)
        libaf.pylatkmc_test_free_lattice(lat)


def test_vacancy_rescan_lists_a_neighbour_vacancy_before_its_own_slot(
    libaf: ctypes.CDLL,
) -> None:
    """Chain 0-1-...-9 (bulk_threshold 2: the ends are static). vac_list =
    [6, 5, 9, 0]: the static vacancies come first, ascending (0, 9 — not in
    vac_list order); then the walk lists 6 and its 1NN 5 (ahead of 5's own
    slot). Plain vac_list order or index order would both be wrong."""
    n = 10
    offsets, indices = [0], []
    for s in range(n):
        indices += [t for t in (s - 1, s + 1) if 0 <= t < n]
        offsets.append(len(indices))
    species = [SP_NI] * n
    vac_list = [6, 5, 9, 0]
    for s in vac_list:
        species[s] = SP_VACANT
    lat = libaf.pylatkmc_test_make_lattice(n, _i32(offsets), _i32(indices))
    st = libaf.pylatkmc_test_make_state(n, 4, 4, _i32(vac_list), (ctypes.c_uint8 * n)(*species))
    af = ctypes.c_void_p()
    assert lat and st and libaf.active_filter_alloc(ctypes.byref(af), n, 2) == 0
    try:
        libaf.active_filter_compute_static(af, lat)
        libaf.active_filter_rescan(af, lat, st)
        assert _active(libaf, af) == [0, 9, 6, 5, 7, 4, 8, 1]
        libaf.active_filter_rescan_vacancies(af, lat, st)
        assert _active(libaf, af) == [0, 9, 6, 5]
        assert libaf.active_filter_is_active(af, 7) == 0  # the full rescan's marks are gone
        libaf.active_filter_rescan(af, lat, st)  # and back: no stale vacancy-only marks
        assert _active(libaf, af) == [0, 9, 6, 5, 7, 4, 8, 1]
    finally:
        libaf.active_filter_free(af)
        libaf.pylatkmc_test_free_state(st)
        libaf.pylatkmc_test_free_lattice(lat)


# ---------------------------------------------------------------------------
# kmc_step_once level: the vacancy path is bitwise the full path
# ---------------------------------------------------------------------------

#: A 12-proc fake model whose every process anchors on a vacancy: proc j
#: swaps the vacancy at `site` with its j-th CSR 1NN (if occupied). Each proc
#: has many sites, so any change in the touchup order changes the selected
#: event. touchup_a counts its calls.
_FAKE_PROCLIST_C = r"""
#include <stdlib.h>
#include <string.h>

#include "proclist.h"
#include "events_base.h"
#include "kmc.h"

#define N_SLOTS 12

static const RateConst rate_table[N_SLOTS] = {
    { 1.0e13, 0.50, 0, 0 }, { 2.0e13, 0.55, 0, 0 }, { 1.0e13, 0.45, 0, 0 },
    { 3.0e13, 0.60, 0, 0 }, { 1.0e13, 0.52, 0, 0 }, { 5.0e12, 0.40, 0, 0 },
    { 1.0e13, 0.48, 0, 0 }, { 2.0e13, 0.58, 0, 0 }, { 1.0e13, 0.47, 0, 0 },
    { 4.0e13, 0.62, 0, 0 }, { 1.0e13, 0.51, 0, 0 }, { 8.0e12, 0.43, 0, 0 },
};

static long long g_touchups = 0;

static HopOutcome hop(struct State *st, const struct Lattice *lat, int site, int j)
{
    int32_t m = lat->nn1_indices[lat->nn1_offsets[site] + j];
    uint8_t sp = st->species[m];
    StateAction acts[2] = { { site, SP_VACANT, sp }, { m, sp, SP_VACANT } };
    if (state_apply_actions(st, acts, 2, SP_VACANT) != 0)
        return (HopOutcome){ PYLATKMC_HOP_REJECTED, PYLATKMC_HOP_REJECTED };
    return (HopOutcome){ site, m };
}

#define HOP(j) static HopOutcome hop_##j(struct State *st, const struct Lattice *lat, \
                                         int site) { return hop(st, lat, site, j); }
HOP(0) HOP(1) HOP(2) HOP(3) HOP(4) HOP(5) HOP(6) HOP(7) HOP(8) HOP(9) HOP(10) HOP(11)
#undef HOP

static const ApplyFn apply_table[N_SLOTS] = {
    hop_0, hop_1, hop_2, hop_3, hop_4, hop_5, hop_6, hop_7, hop_8, hop_9, hop_10, hop_11,
};
const int32_t pylatkmc_n_procs = N_SLOTS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;

void touchup_a(const struct Lattice *lat, const struct State *st,
               struct AvailSites *as, int site)
{
    ++g_touchups;
    if (st->species[site] != SP_VACANT) return;
    for (int32_t j = 0; j < lat->nn1_offsets[site + 1] - lat->nn1_offsets[site]; ++j)
        if (st->species[lat->nn1_indices[lat->nn1_offsets[site] + j]] != SP_VACANT)
            avail_sites_add(as, j, site);
}

/* Run n_steps from (species, vac_list) and record every step's event. */
int pylatkmc_test_run(int32_t n_sites, int32_t *off, int32_t *idx,
                      const uint8_t *species, const int32_t *vac_list, int32_t n_vac,
                      int32_t n_steps, unsigned long long seed,
                      int32_t *out_proc, int32_t *out_site, double *out_dt,
                      long long *out_touchups)
{
    Lattice lat;
    memset(&lat, 0, sizeof lat);
    lat.n_sites = n_sites;
    lat.nn1_offsets = off;
    lat.nn1_indices = idx;
    lat.cell[0] = lat.cell[1] = lat.cell[2] = 1.0f;
    lat.positions = calloc((size_t)n_sites * 3, sizeof *lat.positions);  /* MSD only */
    State st;
    if (!lat.positions || state_alloc(&st, n_sites, n_vac) != 0) return -1000;
    memcpy(st.species, species, (size_t)n_sites);
    for (int32_t v = 0; v < n_vac; ++v) {
        st.vac_list[v] = vac_list[v];
        st.vac_idx_of[vac_list[v]] = v;
    }
    st.n_vac = n_vac;
    AvailSites *as = NULL;
    ActiveFilter *af = NULL;
    if (avail_sites_alloc(&as, N_SLOTS, n_sites) != 0
        || active_filter_alloc(&af, n_sites, 12) != 0) return -1001;
    for (int32_t p = 0; p < N_SLOTS; ++p)
        avail_sites_set_rate(as, p, rateconst_eval(rate_table[p], 600.0, 0.0));
    active_filter_compute_static(af, &lat);
    Rng rng;
    rng_seed(&rng, seed, 0);
    KmcRunConfig cfg;
    memset(&cfg, 0, sizeof cfg);
    KmcContext ctx = { .lat = &lat, .st = &st, .as = as, .af = af, .rng = &rng,
                       .cfg = &cfg, .temperature_K = 600.0 };
    g_touchups = 0;
    int rc = 0;
    for (int32_t i = 0; i < n_steps && rc == 0; ++i)
        rc = kmc_step_once(&ctx, &out_proc[i], &out_site[i], &out_dt[i], NULL);
    *out_touchups = g_touchups;
    active_filter_free(af);
    avail_sites_free(as);
    state_free(&st);
    free(lat.positions);
    return rc;
}
"""


@pytest.fixture(scope="module")
def step_libs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, ctypes.CDLL]:
    """The fake model built against three proclist.h renderings: the anchor
    mask codegen emits for vacancy-only anchors, one with an occupied anchor
    species, and the bare template (no mask: a pre-mask proclist)."""
    from pylatkmc.codegen import _PROCLIST_H_TEMPLATE, _anchor_species_define
    from pylatkmc.rate_expression import KB_EV_PER_K

    tmp = tmp_path_factory.mktemp("active_set_step")
    libs = {}
    for name, extra in [
        ("vacancy", _anchor_species_define(["Vacant"])),
        ("occupied", _anchor_species_define(["Ni", "Vacant"])),
        ("bare", ""),
    ]:
        d = tmp / name
        d.mkdir()
        (d / "proclist.h").write_text(
            _PROCLIST_H_TEMPLATE.format(
                spec_name="fake", kb_ev_per_k=KB_EV_PER_K, extra_defines=extra
            )
        )
        (d / "fake_proclist.c").write_text(_FAKE_PROCLIST_C)
        srcs = [d / "fake_proclist.c"] + [
            CORE / f
            for f in (
                "kmc.c",
                "avail_sites.c",
                "active_filter.c",
                "state.c",
                "state_actions.c",
                "rng.c",
            )
        ]
        srcs += [IO / f for f in ("xyz_writer.c", "pykmc_out.c", "phasec_out.c")]
        lib = _build_lib(d, f"step_{name}", srcs, includes=(d,))
        lib.pylatkmc_test_run.restype = ctypes.c_int
        libs[name] = lib
    return libs


def _run(lib: ctypes.CDLL, offsets, indices, species, vac_list, n_steps: int, seed: int):
    n = len(offsets) - 1
    proc = (ctypes.c_int32 * n_steps)()
    site = (ctypes.c_int32 * n_steps)()
    dt = (ctypes.c_double * n_steps)()
    touchups = ctypes.c_longlong()
    rc = lib.pylatkmc_test_run(
        ctypes.c_int32(n),
        _i32(offsets),
        _i32(indices),
        (ctypes.c_uint8 * n)(*species),
        _i32(vac_list),
        ctypes.c_int32(len(vac_list)),
        ctypes.c_int32(n_steps),
        ctypes.c_ulonglong(seed),
        proc,
        site,
        dt,
        ctypes.byref(touchups),
    )
    assert rc == 0
    # dt as its IEEE bits: the comparison is bitwise
    dt_bits = bytes(dt)
    return list(proc), list(site), dt_bits, touchups.value


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_vacancy_only_step_loop_is_bitwise_and_touches_up_vacancies_only(
    step_libs: dict[str, ctypes.CDLL], seed: int
) -> None:
    """On random multi-vacancy slabs, 400 kmc_step_once steps select the same
    (proc, site, dt) bit for bit whichever rescan runs, while the vacancy-only
    model touches up exactly its n_vac vacancies per step instead of every
    static site as well (the ticket's per-step O(N) work). A mask with an
    occupied anchor species keeps the full rescan."""
    rng = random.Random(seed)
    offsets, indices, layer = _fcc_slab(3, 3, 6, rng)
    n = len(offsets) - 1
    species = _random_species(offsets, indices, layer, n_vac=16, rng=rng)
    vac_list = [s for s in range(n) if species[s] == SP_VACANT]
    rng.shuffle(vac_list)
    n_steps = 400

    runs = {
        name: _run(lib, offsets, indices, species, vac_list, n_steps, seed)
        for name, lib in step_libs.items()
    }
    vac, occ, bare = runs["vacancy"], runs["occupied"], runs["bare"]
    assert vac[:3] == bare[:3], "the vacancy-only rescan changed the trajectory"
    assert occ[:3] == bare[:3]
    assert len(set(vac[1])) > 8, "the trajectory should visit many sites"

    n_static = sum(1 for s in range(n) if offsets[s + 1] - offsets[s] < BULK_NN1)
    assert vac[3] == n_steps * len(vac_list)  # the vacancies, nothing else
    assert bare[3] >= n_steps * n_static  # every static site, every step
    assert bare[3] > 2 * vac[3]
    assert occ[3] == bare[3]


# ---------------------------------------------------------------------------
# codegen: the anchor-species mask
# ---------------------------------------------------------------------------


def test_anchor_species_of_the_v03_paths() -> None:
    """ni_example's hops all anchor on a vacancy; the dissolution family
    anchors on every occupied species; a Process without an anchor Condition
    may enrol anywhere (None -> ~0u)."""
    from pylatkmc import load
    from pylatkmc.codegen import _anchor_species_define, _build_dissolution_processes
    from pylatkmc.decision_tree import anchor_species
    from pylatkmc.processes import Action, Condition, CoordOffset, Process
    from pylatkmc.translator import load_family_rate_table, translate_all

    spec_path = MODELS / "ni_example" / "ni_example.kmcspec.toml"
    spec = load(spec_path)
    csv = Path(spec.rate_data.family_table)
    csv = csv if csv.is_absolute() else (spec_path.parent / csv).resolve()
    hops = translate_all(
        load_family_rate_table(csv),
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
        mover_species="Ni",
        style=spec.rate_data.prefactor_style,
    )
    assert len(hops) > 100
    assert anchor_species(hops) == ["Vacant"]

    demo_path = MODELS / "ni_dissolution_demo" / "ni_dissolution_demo.kmcspec.toml"
    demo = load(demo_path)
    assert demo.dissolution is not None
    diss = _build_dissolution_processes(demo, demo.dissolution)
    assert anchor_species(diss) == ["Cr", "Fe", "Ni"]
    assert anchor_species(hops + diss) == ["Cr", "Fe", "Ni", "Vacant"]

    free = Process(
        name="unanchored",
        family_id="test",
        conditions=(Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),),
        actions=(Action(coord=CoordOffset(code="NC_NN1_PX"), before="Ni", after="Vacant"),),
        rate_constant=1.0,
        Ea_eV=0.5,
    )
    assert anchor_species([*hops, free]) is None
    assert anchor_species([]) == []

    assert "#define PYLATKMC_ANCHOR_SPECIES_MASK (1u << SP_VACANT)\n" in _anchor_species_define(
        ["Vacant"]
    )
    assert (
        "#define PYLATKMC_ANCHOR_SPECIES_MASK ((1u << SP_CR) | (1u << SP_FE) | "
        "(1u << SP_NI) | (1u << SP_VACANT))\n"
    ) in _anchor_species_define(["Cr", "Fe", "Ni", "Vacant"])
    assert "#define PYLATKMC_ANCHOR_SPECIES_MASK (~0u)\n" in _anchor_species_define(None)
    assert "#define PYLATKMC_ANCHOR_SPECIES_MASK 0u\n" in _anchor_species_define([])


def test_v2_anchor_species() -> None:
    from pylatkmc.pattern_codegen import v2_anchor_species
    from pylatkmc.translator_v2 import DeltaRow, LatticePattern

    def pat(name: str, anchor: str) -> LatticePattern:
        other = "Ni" if anchor == "Vacant" else "Vacant"
        return LatticePattern(
            class_id=name,
            name=name,
            anchor_species=anchor,
            delta=(DeltaRow((0, 0, 0), anchor, other), DeltaRow((2, 0, 0), other, anchor)),
            context=(),
            orientation_ops=(0,),
            prefactor_Hz=1.0e13,
            Ea_eV=0.5,
            mover_species=("Ni",),
            n_members=1,
            depth_kind=0,
            depth_param=0,
        )

    assert v2_anchor_species([pat("a", "Vacant"), pat("b", "Vacant")]) == ["Vacant"]
    assert v2_anchor_species([pat("a", "Vacant"), pat("b", "Ni")]) == ["Ni", "Vacant"]
    assert v2_anchor_species([]) == []


_MASK_RE = re.compile(r"^#define PYLATKMC_ANCHOR_SPECIES_MASK (.+)$", re.MULTILINE)


def _mask_symbols(header: str) -> set[str]:
    m = _MASK_RE.search(header)
    assert m, "proclist.h lacks PYLATKMC_ANCHOR_SPECIES_MASK (regenerate it)"
    return set(re.findall(r"SP_[A-Z]+", m.group(1)))


@pytest.mark.parametrize(
    "model",
    ["ni_example", "ni_fe_cr_v1", "ni_dissolution_demo", "nife_v2_scratch", "nicr_v2_scratch"],
)
def test_committed_proclist_mask_matches_its_touchup(model: str) -> None:
    """CI links the committed proclists without regenerating them, so each
    committed proclist.h must carry the mask its committed touchup implies:
    the v2 species with a non-empty v2_pattern_bucket_begin bucket, or the
    case labels of the v0.3 tree's top-level switch on the anchor."""
    gen = MODELS / model / "generated"
    symbols = _mask_symbols((gen / "proclist.h").read_text())
    src = (gen / "proclist.c").read_text()
    buckets = re.search(r"v2_pattern_bucket_begin\[5\] = \{([0-9,]+)\};", src)
    if buckets:
        b = [int(x) for x in buckets.group(1).split(",")]
        codes = ["SP_VACANT", "SP_NI", "SP_FE", "SP_CR"]  # events_base.h order
        expected = {codes[i] for i in range(4) if b[i + 1] > b[i]}
    else:
        start = re.search(r"^void touchup_a\(", src, re.MULTILINE)
        assert start
        lines = src[start.start() :].splitlines()
        assert lines[1] == "    switch (st->species[site]) {", (
            "top-level switch is not on the anchor"
        )
        end = lines.index("    }")
        expected = {
            m.group(1) for line in lines[2:end] if (m := re.match(r"^        case (SP_\w+):", line))
        }
    assert symbols == expected
    vacancy_only = expected == {"SP_VACANT"}
    assert vacancy_only == (model != "ni_dissolution_demo")
