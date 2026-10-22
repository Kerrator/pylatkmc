"""Regression tests for the surrogate channel's measured-cover check
(large-system-scaling/10).

``pylatkmc_measured_covers_hop(lat, st, as, v, n)`` asks, for every surrogate
candidate (each vacancy ``v`` times each 1NN ``n`` one raw ``site_ijk`` step
away along a baked surrogate direction): does a measured proc enrolled at
``v`` move the vacancy from ``v`` (its v_origin row) to ``n`` (its v_dest
row)? It used to scan all N_PROCS through ``avail_sites_is_enrolled`` per
candidate. The v2 ``touchup_a`` of a surrogate build now records the answer
in the anchor's ``avail_sites`` cover word while it enrols, and the check
reads that word.

- The O(1) answer equals the old scan (compiled verbatim against the same
  tables as the reference) for every site x surrogate direction, after
  touchups over all sites in shuffled order and over random subsets, across
  avail_sites_clear rounds, on a periodic slab with vacuum (the seams, both
  surfaces) and on a box smaller than the pattern reach, where offsets alias.
  The hand-built patterns include ones that must never cover: a vacancy hop
  that starts off the anchor, a concerted move whose vacancy rows are -1, a
  Ni-anchored pattern, and a 2-step destination (which aliases onto a 1NN on
  the small box, where the scan does count it).
- The check probes no proc's enrolment and resolves no site.
- surrogate_rebuild's candidate list (order, k, triggers) is bit-identical
  with the O(1) check and with the scan.
- Every committed surrogate proclist carries the O(1) check, with the
  surrogate's own directions; a build without a surrogate records no covers.

ctypes level, no MPI; skips without cc.
"""

from __future__ import annotations

import ctypes
import math
import random
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"
SHIM_SRC = Path(__file__).parent / "_surrogate_test_shim.c"

SP = {"Vacant": 0, "Ni": 1, "Fe": 2, "Cr": 3}  # events_base.h

# Runtime frame: tetragonal grid (nn/2, nn/2, nn/sqrt2), sites on the
# same-parity sublattice.
NN = 2.5
HX, HZ = NN / 2.0, NN / math.sqrt(2.0)


class Geometry(NamedTuple):
    nx: int  # in-plane grid planes (periodic)
    ny: int
    n_layers: int  # atomic layers, under ...
    n_vacuum: int  # ... this many empty grid planes (the k axis wraps too)


#: Every axis at or above 2 * reach + 1 for the patterns below (reach 4, 2).
SLAB = Geometry(10, 10, 5, 4)
#: Below 2 * reach + 1 on every axis: offsets alias (refused at startup by the
#: runtime, but the check must still equal the scan).
ALIAS_BOX = Geometry(6, 6, 3, 1)

# Counts the proc-enrolment probes and grid lookups of the generated code (the
# headers are include-guarded, so the generated #includes are no-ops). The
# scan reference, appended last, undefines the counters and calls the real
# functions.
_PRELUDE = r"""
#include "lattice.h"
#include "avail_sites.h"

long pylatkmc_test_probes;
long pylatkmc_test_lookups;
static inline int32_t test_counted_is_enrolled(const AvailSites *as, int32_t proc,
                                               int32_t site)
{
    ++pylatkmc_test_probes;
    return avail_sites_is_enrolled(as, proc, site);
}
static inline int32_t test_counted_site_at_ijk(const Lattice *lat, int32_t i,
                                               int32_t j, int32_t k)
{
    ++pylatkmc_test_lookups;
    return lattice_site_at_ijk(lat, i, j, k);
}
#define avail_sites_is_enrolled test_counted_is_enrolled
#define lattice_site_at_ijk test_counted_site_at_ijk
"""

#: The check before large-system-scaling/10, verbatim but for the names.
_SCAN = r"""
#undef avail_sites_is_enrolled
#undef lattice_site_at_ijk
static int32_t scan_proc_vsite(const Lattice *lat, int32_t anchor, int32_t proc, int row)
{
    if (row < 0) return -1;
    const V2Proc *pr = &v2_procs[proc];
    const V2Pattern *pt = &v2_patterns[pr->pat];
    const int8_t *R = V2_OPS[pr->op];
    const V2DeltaRow *dr = &v2_delta_rows[pt->delta_begin + row];
    const int16_t *c0 = &lat->site_ijk[(size_t)anchor * 3];
    int32_t di = R[0]*dr->di + R[1]*dr->dj + R[2]*dr->dk;
    int32_t dj = R[3]*dr->di + R[4]*dr->dj + R[5]*dr->dk;
    int32_t dk = R[6]*dr->di + R[7]*dr->dj + R[8]*dr->dk;
    return lattice_site_at_ijk(lat, c0[0]+di, c0[1]+dj, c0[2]+dk);
}
int SCAN_NAME(const Lattice *lat, const State *st, const AvailSites *as,
              int32_t vac_site, int32_t neigh_site)
{
    (void)st;
    for (int32_t p = 0; p < N_PROCS; ++p) {
        if (avail_sites_is_enrolled(as, p, vac_site) != 1) continue;
        const V2Pattern *pt = &v2_patterns[v2_procs[p].pat];
        int32_t vo = scan_proc_vsite(lat, vac_site, p, pt->v_origin_row);
        int32_t vd = scan_proc_vsite(lat, vac_site, p, pt->v_dest_row);
        if (vo == vac_site && vd == neigh_site) return 1;
    }
    return 0;
}
"""

_GLUE = """
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""


def _patterns() -> list:
    """Hand-built runtime-frame patterns, all but one vacancy-anchored:

    - ``c_hop``: in-plane Ni hop, 2 members, ops 0 and 1 only (covers +u);
    - ``c_up``: interlayer Cr hop on an op subset (covers some (1,1,1) images);
    - ``c_far``: a chain whose vacancy lands 2 steps away (aliases onto -u on
      the small box);
    - ``c_two_vac``: two vacancies move at once (vacancy rows -1);
    - ``c_off_anchor``: the hopping vacancy is NOT the anchor (all ops);
    - ``c_ni_anchor``: Ni-anchored (never enrolled at a vacancy)."""
    from pylatkmc.translator_v2 import CtxRow, DeltaRow, LatticePattern, MemberRate

    def pat(name, anchor, delta, context, ops, n_members=1):
        members = tuple(
            MemberRate(1.0e13 * (m + 1), 0.4 + 0.05 * m, math.nan) for m in range(n_members)
        )
        return LatticePattern(
            class_id=name,
            name=name,
            anchor_species=anchor,
            delta=tuple(DeltaRow(o, b, a) for o, b, a in delta),
            context=tuple(CtxRow(o, k, s) for o, k, s in context),
            orientation_ops=tuple(ops),
            prefactor_Hz=members[0].prefactor_Hz,
            Ea_eV=members[0].Ea_eV,
            mover_species=("Ni",),
            n_members=n_members,
            depth_kind=0,
            depth_param=0,
            members=members,
        )

    all_ops = tuple(range(16))
    return [
        pat(
            "c_hop",
            "Vacant",
            [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Vacant")],
            [((-2, 0, 0), "EMPTY", None)],
            (0, 1),
            n_members=2,
        ),
        pat(
            "c_up",
            "Vacant",
            [((0, 0, 0), "Vacant", "Cr"), ((1, 1, 1), "Cr", "Vacant")],
            [((0, 0, 2), "OCC_ANY", None)],
            (0, 3, 5, 6, 9, 10, 12, 15),
        ),
        pat(
            "c_far",
            "Vacant",
            [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Cr"), ((4, 0, 0), "Cr", "Vacant")],
            [],
            (0, 1, 2, 3),
        ),
        pat(
            "c_two_vac",
            "Vacant",
            [
                ((0, 0, 0), "Vacant", "Ni"),
                ((2, 0, 0), "Ni", "Vacant"),
                ((0, 2, 0), "Vacant", "Fe"),
                ((2, 2, 0), "Fe", "Vacant"),
            ],
            [],
            all_ops,
        ),
        pat(
            "c_off_anchor",
            "Vacant",
            [((2, 0, 0), "Vacant", "Ni"), ((4, 0, 0), "Ni", "Vacant")],
            [],
            all_ops,
        ),
        pat(
            "c_ni_anchor",
            "Ni",
            [((0, 0, 0), "Ni", "Vacant"), ((0, 2, 0), "Vacant", "Ni")],
            [],
            all_ops,
            n_members=2,
        ),
    ]


def _proc_names(patterns: list) -> list[str]:
    """Pattern name per proc id (the emitter's (anchor species, name),
    member-major, then op order)."""
    order = sorted(patterns, key=lambda p: (SP[p.anchor_species], p.name))
    return [p.name for p in order for _m in p.members for _op in p.orientation_ops]


def _compile(tmp: Path, name: str, source: str, extra: list[Path], include: Path | None = None):
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    src = tmp / f"{name}.c"
    src.write_text(source)
    lib = tmp / (f"lib{name}.dylib" if sys.platform == "darwin" else f"lib{name}.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2", "-fPIC"]
    cmd += ["-shared", "-I", str(CORE)] + (["-I", str(include)] if include else [])
    cmd += [str(src)] + [str(CORE / f) for f in ("lattice.c", "coord_codes.c")]
    cmd += [str(CORE / f) for f in ("state_actions.c", "avail_sites.c")]
    cmd += [str(p) for p in extra] + [str(HELPERS_SRC), "-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")
    return _bind(ctypes.CDLL(str(lib)))


def _bind(dll: ctypes.CDLL) -> ctypes.CDLL:
    vp, i32, i32p = ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)
    f32p = ctypes.POINTER(ctypes.c_float)
    dll.pylatkmc_test_make_lattice_full.restype = vp
    dll.pylatkmc_test_make_lattice_full.argtypes = [i32, f32p, f32p, ctypes.c_float]
    dll.pylatkmc_test_make_lattice_full.argtypes += [i32p, i32p, i32p, i32p]
    dll.lattice_build_site_grid.restype = ctypes.c_int
    dll.lattice_build_site_grid.argtypes = [vp]
    dll.pylatkmc_test_make_state.restype = vp
    dll.pylatkmc_test_make_state.argtypes = [i32, i32, i32, i32p, ctypes.POINTER(ctypes.c_uint8)]
    dll.pylatkmc_test_free_lattice.argtypes = [vp]
    dll.pylatkmc_test_free_state.argtypes = [vp]
    dll.avail_sites_alloc.restype = ctypes.c_int
    dll.avail_sites_alloc.argtypes = [ctypes.POINTER(vp), i32, i32]
    dll.avail_sites_free.argtypes = [vp]
    dll.avail_sites_clear.argtypes = [vp]
    dll.avail_sites_count.restype = i32
    dll.avail_sites_count.argtypes = [vp, i32]
    dll.touchup_a.restype = None
    dll.touchup_a.argtypes = [vp, vp, vp, ctypes.c_int]
    dll.pylatkmc_measured_covers_hop.restype = ctypes.c_int
    dll.pylatkmc_measured_covers_hop.argtypes = [vp, vp, vp, i32, i32]
    return dll


def _tables(patterns: list) -> str:
    """Preamble + enum + rate table + pattern tables of a surrogate build."""
    from pylatkmc.codegen import _PROCLIST_C_PREAMBLE
    from pylatkmc.pattern_codegen import emit_pattern_tables, emit_v2_enum, emit_v2_rate_table
    from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

    return (
        _PROCLIST_C_PREAMBLE.format(spec_name="covers", temperature_K=600.0, k0_Hz=1e13)
        + emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + emit_pattern_tables(patterns, cover_dirs=RUNTIME_DIRECTIONS)
    )


class _Box:
    """A slab lattice of ``geom`` in one library (site grid from lattice.c,
    1NN CSR with the periodic in-plane images), plus an avail_sites."""

    def __init__(self, lib: ctypes.CDLL, geom: Geometry) -> None:
        from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

        self.lib = lib
        self.dims = (geom.nx, geom.ny, geom.n_layers + geom.n_vacuum)
        self.cells = [
            (u, v, w)
            for w in range(geom.n_layers)
            for u in range(geom.nx)
            for v in range(geom.ny)
            if (u - v) % 2 == 0 and (v - w) % 2 == 0
        ]  # site 0 at cell (0, 0, 0), so site_ijk == cell
        n = self.n = len(self.cells)
        self.site_of = {c: s for s, c in enumerate(self.cells)}
        # The 1NN CSR a kmcinit carries: wrapped in every axis (the k wrap
        # lands in the vacuum), so the in-plane seams are crossed.
        offsets, indices = [0], []
        for c in self.cells:
            for d in RUNTIME_DIRECTIONS:
                w = tuple((c[a] + d[a]) % self.dims[a] for a in range(3))
                if w in self.site_of:
                    indices.append(self.site_of[w])
            offsets.append(len(indices))
        pos = [x for (u, v, w) in self.cells for x in (u * HX, v * HX, w * HZ)]
        cell = (geom.nx * HX, geom.ny * HX, self.dims[2] * HZ)
        self.lat = lib.pylatkmc_test_make_lattice_full(
            n,
            (ctypes.c_float * (3 * n))(*pos),
            (ctypes.c_float * 3)(*cell),
            NN,
            (ctypes.c_int32 * (n + 1))(*offsets),
            (ctypes.c_int32 * max(1, len(indices)))(*indices),
            None,
            None,
        )
        assert self.lat and lib.lattice_build_site_grid(self.lat) == 0
        n_procs = ctypes.c_int32.in_dll(lib, "pylatkmc_n_procs").value
        self.as_ = ctypes.c_void_p()
        assert lib.avail_sites_alloc(ctypes.byref(self.as_), n_procs, n) == 0
        self.n_procs = n_procs

    def raw_pairs(self) -> list[tuple[int, int]]:
        """Every (site, neighbour one raw step away along a surrogate
        direction): the pairs surrogate_rebuild can ask about."""
        from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

        pairs = []
        for s, c in enumerate(self.cells):
            for d in RUNTIME_DIRECTIONS:
                n = self.site_of.get((c[0] + d[0], c[1] + d[1], c[2] + d[2]))
                if n is not None:
                    pairs.append((s, n))
        return pairs

    def on_seam(self, s: int) -> bool:
        """Whether some 1NN of site s wraps a periodic axis."""
        from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

        c = self.cells[s]
        return any(
            not 0 <= c[a] + d[a] < self.dims[a] for d in RUNTIME_DIRECTIONS for a in range(2)
        )

    def state(self, species: list[int]):
        vac = [s for s, sp in enumerate(species) if sp == SP["Vacant"]]
        st = self.lib.pylatkmc_test_make_state(
            self.n,
            max(1, len(vac)),
            len(vac),
            (ctypes.c_int32 * max(1, len(vac)))(*vac),
            (ctypes.c_uint8 * self.n)(*species),
        )
        assert st
        return st

    def touchup(self, st, sites) -> None:
        for s in sites:
            self.lib.touchup_a(self.lat, st, self.as_, s)

    def close(self) -> None:
        self.lib.avail_sites_free(self.as_)
        self.lib.pylatkmc_test_free_lattice(self.lat)


@pytest.fixture(scope="module")
def covers_lib(tmp_path_factory: pytest.TempPathFactory):
    """The generated tables + the O(1) check + the old scan, in one library."""
    pytest.importorskip("numpy")  # D4h ops (pylatkmc.ingest.lattice), surrogate_codegen
    from pylatkmc.surrogate_codegen import _MEASURED_COVERS_C

    patterns = _patterns()
    tmp = tmp_path_factory.mktemp("covers")
    source = _PRELUDE + _tables(patterns) + "\n" + _MEASURED_COVERS_C
    source += _SCAN.replace("SCAN_NAME", "pylatkmc_test_covers_scan") + _GLUE
    lib = _compile(tmp, "covers", source, [])
    lib.pylatkmc_test_covers_scan.restype = ctypes.c_int
    lib.pylatkmc_test_covers_scan.argtypes = lib.pylatkmc_measured_covers_hop.argtypes
    return lib, patterns


def _species(rng: random.Random, n: int) -> list[int]:
    return rng.choices([SP["Vacant"], SP["Ni"], SP["Cr"], SP["Fe"]], [3, 4, 2, 1], k=n)


def test_covers_hop_equals_the_proc_scan(covers_lib) -> None:
    """For every site x surrogate direction, the O(1) answer is the scan's,
    after full shuffled and partial touchups, across clear rounds that reuse
    one avail_sites, on the periodic slab and on the aliasing box. The O(1)
    check never probes a proc's enrolment or resolves a site."""
    lib, patterns = covers_lib
    names = _proc_names(patterns)
    probes = ctypes.c_long.in_dll(lib, "pylatkmc_test_probes")
    lookups = ctypes.c_long.in_dll(lib, "pylatkmc_test_lookups")
    rng = random.Random(20261022)
    fired: dict[str, set[str]] = {}
    covered: dict[str, Counter] = {}
    for key, geom in (("slab", SLAB), ("alias", ALIAS_BOX)):
        box = _Box(lib, geom)
        pairs = box.raw_pairs()
        fired[key], covered[key] = set(), Counter()
        try:
            for trial in range(12):
                species = _species(rng, box.n)
                st = box.state(species)
                try:
                    lib.avail_sites_clear(box.as_)
                    order = list(range(box.n))
                    rng.shuffle(order)
                    if trial % 3 == 2:  # a partial touchup: some anchors untouched
                        order = order[: box.n // 2]
                    box.touchup(st, order)
                    fired[key].update(
                        names[p] for p in range(box.n_procs) if lib.avail_sites_count(box.as_, p)
                    )
                    for v, n in pairs:
                        probes.value = lookups.value = 0
                        got = lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, n)
                        assert (probes.value, lookups.value) == (0, 0), (
                            "the cover check probes the proc table / the site grid"
                        )
                        want = lib.pylatkmc_test_covers_scan(box.lat, st, box.as_, v, n)
                        assert got == want, (key, trial, v, n, species[v], species[n])
                        if want:
                            covered[key]["pairs"] += 1
                            covered[key]["seam"] += box.on_seam(v)
                finally:
                    lib.pylatkmc_test_free_state(st)
        finally:
            box.close()
    # The comparison is only as good as its matches: every pattern was
    # enrolled somewhere, covered pairs exist (also at vacancies on a periodic
    # seam), and on the small box the 2-step c_far lands on a 1NN.
    for key in fired:
        assert fired[key] == {p.name for p in patterns}, (key, fired[key])
        assert covered[key]["pairs"] > 0 and covered[key]["seam"] > 0, (key, covered[key])
    assert _far_covers_on_alias_box(lib, patterns) > 0


def _far_covers_on_alias_box(lib: ctypes.CDLL, patterns: list) -> int:
    """Covered pairs on the aliasing box when only c_far can match: its
    2-step destination wraps onto the anchor's -u neighbour there (the scan
    counts it, so the O(1) check must too)."""
    box = _Box(lib, ALIAS_BOX)
    hits = 0
    try:
        for u0 in range(0, ALIAS_BOX.nx, 2):  # one chain per in-plane row, layer 0
            species = [SP["Ni"]] * box.n
            row = [box.site_of[((u0 + du) % ALIAS_BOX.nx, 0, 0)] for du in (0, 2, 4)]
            species[row[0]], species[row[1]], species[row[2]] = SP["Vacant"], SP["Ni"], SP["Cr"]
            st = box.state(species)
            try:
                lib.avail_sites_clear(box.as_)
                box.touchup(st, range(box.n))
                v = row[0]
                for n in sorted({n for (s, n) in box.raw_pairs() if s == v}):
                    got = lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, n)
                    want = lib.pylatkmc_test_covers_scan(box.lat, st, box.as_, v, n)
                    assert got == want, (u0, v, n)
                    hits += got
            finally:
                lib.pylatkmc_test_free_state(st)
    finally:
        box.close()
    return hits


@pytest.fixture(scope="module")
def rebuild_libs(tmp_path_factory: pytest.TempPathFactory):
    """Two surrogate builds of the same patterns + a synthetic model: one with
    the O(1) check, one with the old scan as pylatkmc_measured_covers_hop."""
    pytest.importorskip("numpy")
    from pylatkmc.codegen import _PROCLIST_H_TEMPLATE
    from pylatkmc.rate_expression import KB_EV_PER_K
    from pylatkmc.surrogate_codegen import (
        _MEASURED_COVERS_C,
        emit_surrogate_externs,
        emit_surrogate_tables,
    )

    from ._esym_fixture import synthetic_v2_model

    model = synthetic_v2_model()
    patterns = _patterns()
    tmp = tmp_path_factory.mktemp("covers_rebuild")
    inc = tmp / "include"
    inc.mkdir()
    (inc / "proclist.h").write_text(
        _PROCLIST_H_TEMPLATE.format(
            spec_name="covers",
            kb_ev_per_k=KB_EV_PER_K,
            extra_defines=emit_surrogate_externs(model),
        )
    )
    tables = _tables(patterns)
    surr = emit_surrogate_tables(model)
    assert surr.count(_MEASURED_COVERS_C) == 1
    glue = _GLUE + "const Surrogate *const pylatkmc_surrogate = &g_surrogate;\n"
    scan = _SCAN.replace("SCAN_NAME", "pylatkmc_measured_covers_hop")
    extra = [CORE / "surrogate.c", SHIM_SRC]
    libs = {
        "o1": _compile(tmp, "rb_o1", _PRELUDE + tables + "\n" + surr + glue, extra, inc),
        "scan": _compile(
            tmp,
            "rb_scan",
            _PRELUDE + tables + "\n" + surr.replace(_MEASURED_COVERS_C, scan) + glue,
            extra,
            inc,
        ),
    }
    for lib in libs.values():
        vp = ctypes.c_void_p
        lib.pylatkmc_test_surr_ctx_new.restype = vp
        lib.pylatkmc_test_surr_ctx_new.argtypes = [ctypes.c_int32]
        lib.pylatkmc_test_surr_ctx_free.argtypes = [vp]
        lib.pylatkmc_test_surr_rebuild.restype = ctypes.c_double
        lib.pylatkmc_test_surr_rebuild.argtypes = [vp, vp, vp, vp, ctypes.c_double]
        lib.pylatkmc_test_surr_n_cand.restype = ctypes.c_int32
        lib.pylatkmc_test_surr_n_cand.argtypes = [vp]
        lib.pylatkmc_test_surr_cand.restype = None
        lib.pylatkmc_test_surr_cand.argtypes = [
            vp,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_double),
        ]
    return libs


def _candidates(lib: ctypes.CDLL, box: _Box, st, sites) -> tuple[float, list[tuple]]:
    """touchup_a over ``sites``, then surrogate_rebuild: (r_tot, candidates)."""
    lib.avail_sites_clear(box.as_)
    box.touchup(st, sites)
    ctx = lib.pylatkmc_test_surr_ctx_new(box.n)
    assert ctx
    try:
        rtot = lib.pylatkmc_test_surr_rebuild(ctx, box.lat, st, box.as_, 600.0)
        ints, dbls = (ctypes.c_int32 * 5)(), (ctypes.c_double * 3)()
        cands = []
        for i in range(lib.pylatkmc_test_surr_n_cand(ctx)):
            lib.pylatkmc_test_surr_cand(ctx, i, ints, dbls)
            cands.append((*ints, *(x.hex() for x in dbls)))
    finally:
        lib.pylatkmc_test_surr_ctx_free(ctx)
    return rtot, cands


def test_surrogate_candidates_are_unchanged(rebuild_libs) -> None:
    """surrogate_rebuild walks the same candidates in the same order with
    the same k (bit for bit) whether the measured channel's cover check is the
    O(1) word or the old proc scan; some candidates are de-duplicated."""
    rng = random.Random(10)
    boxes = {key: _Box(lib, SLAB) for key, lib in rebuild_libs.items()}
    real = {SP["Ni"], SP["Cr"], SP["Fe"]}
    n_dedup = 0
    try:
        for _trial in range(6):
            species = _species(rng, boxes["o1"].n)
            order = list(range(boxes["o1"].n))
            rng.shuffle(order)
            got = {}
            for key, box in boxes.items():
                st = box.state(species)
                try:
                    got[key] = _candidates(rebuild_libs[key], box, st, order)
                finally:
                    rebuild_libs[key].pylatkmc_test_free_state(st)
            assert got["o1"][0].hex() == got["scan"][0].hex()
            assert got["o1"][1] == got["scan"][1]
            n_pairs = sum(
                species[v] == SP["Vacant"] and species[n] in real
                for v, n in boxes["o1"].raw_pairs()
            )
            assert 0 < len(got["o1"][1]) <= n_pairs
            n_dedup += n_pairs - len(got["o1"][1])
    finally:
        for box in boxes.values():
            box.close()
    assert n_dedup > 0, "no candidate was covered by a measured proc: the de-dup is untested"


def test_cover_directions_are_the_surrogate_directions() -> None:
    """The cover bit order is the surrogate channel's own direction order."""
    pytest.importorskip("numpy")
    from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS, bake_directions

    baked = tuple(g.runtime_dir for g in bake_directions())
    assert baked == RUNTIME_DIRECTIONS
    assert len(set(RUNTIME_DIRECTIONS)) == 12


def test_no_covers_without_a_surrogate() -> None:
    """A build without a surrogate model emits exactly the tables it did
    before: no cover table, no recording in touchup_a."""
    pytest.importorskip("numpy")
    from pylatkmc.pattern_codegen import emit_pattern_tables

    text = emit_pattern_tables(_patterns())
    assert "v2_cover" not in text and "avail_sites_cover" not in text
    with pytest.raises(ValueError, match="cover_dirs"):
        emit_pattern_tables(_patterns(), cover_dirs=[(0, 0, 0)])


def test_committed_surrogate_proclists_use_the_cover_words() -> None:
    """CI links the committed proclists without regenerating them: each
    committed surrogate build records covers in touchup_a and answers the
    de-dup from them, with the cover table equal to its surr_dirs; the other
    v2 builds record none."""
    surrogate, plain = [], []
    for path in sorted((REPO_ROOT / "models").glob("*/generated/proclist.c")):
        text = path.read_text()
        if "V2Pattern" in text:
            (surrogate if "g_surrogate" in text else plain).append((path, text))
    assert surrogate
    entry = re.compile(r"\{(-?\d+),(-?\d+),(-?\d+)\},")
    for path, text in surrogate:
        assert "avail_sites_is_enrolled" not in text, f"{path}: regenerate it"
        assert "v2_record_covers(lat, as, site, pt, ops);" in text, f"{path}: regenerate it"
        table = text.split("v2_cover_dirs[V2_N_COVER_DIRS][3] = {", 1)[1].split("};", 1)[0]
        cover_dirs = [tuple(map(int, m)) for m in entry.findall(table)]
        surr = text.split("static const SurrDir surr_dirs[", 1)[1].split("};", 1)[0]
        surr_dirs = [
            tuple(map(int, m))
            for m in re.findall(r"^\s+(-?\d+),(-?\d+),(-?\d+),$", surr, flags=re.M)
        ]
        assert cover_dirs == surr_dirs and len(cover_dirs) == 12, f"{path}: regenerate it"
    for path, text in plain:
        assert "v2_cover" not in text, f"{path}: a build without a surrogate records covers"
