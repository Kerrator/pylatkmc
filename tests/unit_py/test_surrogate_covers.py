"""Regression tests for the surrogate channel's measured-cover check
(large-system-scaling/10).

``pylatkmc_measured_covers_hop(lat, st, as, v, n)`` asks, for every surrogate
candidate (each vacancy ``v`` x each real-atom 1NN ``n`` one raw ``site_ijk``
step away along a baked surrogate direction), every step: does a measured proc
enrolled at ``v`` move the vacancy from ``v`` (its v_origin row) to ``n`` (its
v_dest row)? It used to scan all N_PROCS through ``avail_sites_is_enrolled``
per candidate. A surrogate build's v2 ``touchup_a`` now records the answer in
the anchor's ``avail_sites`` cover word while it enrols, and the check reads
that word.

The proclist comes from the real ``codegen.generate``: hand-built patterns and
the synthetic surrogate model are fed in through monkeypatched catalogue and
model loading, so no machine-local catalogue is needed, and ``_generate_v2``'s
wiring (cover recording exactly when a surrogate model is baked) is tested too.

- The O(1) answer equals the pre-fix scan (compiled verbatim against the same
  tables) for every site x surrogate direction, after full and partial
  touchups in shuffled order, across avail_sites_clear rounds that reuse one
  avail_sites, on a periodic slab with vacuum (the seams, both surfaces) and
  on a box below the pattern reach (offsets alias). The check probes no proc's
  enrolment and resolves no site, and surrogate_rebuild keeps exactly the
  candidates the scan keeps, in order.
- Constructed states pin both aliasing cases on the small box, which only the
  synthetic patterns exercise: a vacancy-origin row that wraps onto the anchor
  and a two-hop destination that wraps onto a 1NN. The scan counts both.
- surrogate_rebuild's candidates (order, k, ea_hat, leverage, trigger, as bit
  patterns) and r_tot are bit-identical between the O(1) build and a build
  whose check is the old scan.
- The cover bit order is the surrogate's own direction order (codegen refuses
  a drift); builds without a surrogate model emit no cover code; every
  committed surrogate proclist carries the O(1) check; an empty catalogue with
  a surrogate model still compiles.

ctypes level, no MPI; skips without cc or numpy.
"""

from __future__ import annotations

import ctypes
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"
SHIM_SRC = Path(__file__).parent / "_surrogate_test_shim.c"

SP_VACANT, SP_NI, SP_FE, SP_CR = 0, 1, 2, 3  # events_base.h (by name: FE=2, CR=3)
ATOMS = (SP_NI, SP_FE, SP_CR)

# Runtime frame: tetragonal grid (nn/2, nn/2, nn/sqrt2), sites on the
# same-parity sublattice.
NN = 2.5
HX, HZ = NN / 2.0, NN / math.sqrt(2.0)


class Geometry(NamedTuple):
    nx: int  # in-plane grid planes (periodic)
    ny: int
    n_layers: int  # atomic layers, under ...
    n_vacuum: int  # ... this many empty grid planes (the k axis wraps too)


#: 10 x 10 in-plane planes, 5 layers under 4 vacuum planes: no pattern row
#: aliases onto another row's site (p_alias's 6-cell row lands 4 cells back).
SLAB = Geometry(10, 10, 5, 4)
#: 6 x 6 x 4 planes, below 2 * reach + 1: p_alias's 6-cell vacancy origin wraps
#: onto the anchor and p_chain's 4-cell destination onto a 1NN (the runtime
#: refuses such a box at startup, but the de-dup must still equal the scan).
ALIAS_BOX = Geometry(6, 6, 3, 1)


def _patterns() -> list:
    """Hand-built runtime-frame patterns spanning every way a measured proc does
    or does not cover a surrogate candidate: 1NN hops in-plane (all ops, three
    members; a Cr hop on two ops that both map +u to +u) and interlayer (an op
    subset; Cr and Fe movers), a vacancy landing on a 3NN site, a concerted
    chain landing two hops away, a divacancy (no unique vacancy origin: rows
    -1), a hop whose vacancy starts off the anchor, a Ni-anchored pattern, and a
    vacancy origin six cells out (the anchor itself on the alias box)."""
    from pylatkmc.translator_v2 import CtxRow, DeltaRow, LatticePattern, MemberRate

    def pat(name, anchor, delta, context, ops, movers, n_members=1):
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
            mover_species=movers,
            n_members=len(members),
            depth_kind=0,
            depth_param=0,
            members=members,
        )

    every = tuple(range(16))
    v, ni, cr, fe = "Vacant", "Ni", "Cr", "Fe"
    return [
        pat("p_ni_hop", v, [((0, 0, 0), v, ni), ((2, 0, 0), ni, v)],
            [((-2, 0, 0), "OCC_ANY", None)], every, (ni,), 3),
        pat("p_cr_inplane", v, [((0, 0, 0), v, cr), ((2, 0, 0), cr, v)],
            [((-2, 0, 0), "EMPTY", None)], (0, 1), (cr,), 2),
        pat("p_cr_hop", v, [((0, 0, 0), v, cr), ((1, 1, 1), cr, v)],
            [((0, 2, 0), "EMPTY", None)], (0, 3, 5, 6, 9, 10, 12, 15), (cr,), 2),
        pat("p_fe_hop", v, [((0, 0, 0), v, fe), ((1, -1, -1), fe, v)],
            [((-1, 1, 1), "SPECIES", ni)], every, (fe,)),
        pat("p_3nn", v, [((0, 0, 0), v, ni), ((3, -1, 1), ni, v)], [], every, (ni,)),
        pat("p_chain", v, [((0, 0, 0), v, ni), ((2, 0, 0), ni, cr), ((4, 0, 0), cr, v)],
            [], (0, 1, 2, 3), (ni, cr)),
        pat("p_divac", v, [((0, 0, 0), v, ni), ((0, 2, 0), v, ni), ((2, 0, 0), ni, v),
                           ((2, 2, 0), ni, v)], [], every, (ni,)),
        pat("p_off_anchor", v, [((2, 0, 0), v, ni), ((4, 0, 0), ni, v)], [], every, (ni,)),
        pat("p_ni_anchor", ni, [((0, 0, 0), ni, v), ((0, 2, 0), v, ni)], [], every, (ni,), 2),
        pat("p_alias", v, [((6, 0, 0), v, ni), ((2, 0, 0), ni, v)],
            [((0, 0, 0), "SPECIES", v)], (0, 6, 8), (ni,)),
    ]  # fmt: skip


def _proc_names(patterns: list) -> list[str]:
    """Pattern name per proc id (the emitter's proc order)."""
    from pylatkmc.pattern_codegen import _proc_list

    _order, procs = _proc_list(patterns)
    return [patterns[pi].name for (_t, _op, _m, pi) in procs]


# --------------------------------------------------------------------------- #
# Build: real codegen.generate -> proclist.{c,h} -> shared libraries          #
# --------------------------------------------------------------------------- #
def _generate(tmp: Path, patterns: list, *, surrogate: bool = True) -> Path:
    """Run the real codegen.generate on ``patterns`` (+ the synthetic v2 model
    when ``surrogate``), catalogue and model loading monkeypatched; return the
    generated dir."""
    from pylatkmc import codegen, translator_v2
    from pylatkmc.ingest import surrogate as ingest_surrogate
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

    from ._esym_fixture import synthetic_v2_model

    spec = ModelSpec(
        name="surr_covers",
        species=["Vacant", "Ni", "Fe", "Cr"],
        shells=[Shell(name="s1", cutoff_mult=1.05)],
        key=Key(axes=[KeyAxis(name="n_vac_s1", kind="count", max=2, shell="s1", match="vac")]),
        rate_data=RateData(
            event_class_table=Path("monkeypatched.parquet"),
            surrogate_model=Path("monkeypatched.json") if surrogate else None,
            temperature_K=500.0,
            k0_Hz=1.0e13,
        ),
    )
    gen = tmp / "generated"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(translator_v2, "load_event_class_catalogue", lambda path: [])
        mp.setattr(translator_v2, "catalogue_is_phase_c", lambda classes: True)
        mp.setattr(
            translator_v2,
            "translate_event_classes",
            lambda classes, **kw: (patterns, translator_v2.TranslationReport(phase_c=True)),
        )
        mp.setattr(ingest_surrogate, "load_model", lambda path: synthetic_v2_model())
        codegen.generate(spec, gen)
    return gen


# Prepended to the generated proclist.c: counts the generated code's proc
# enrolment probes and grid lookups. The headers are include-guarded, so the
# generated #includes after this are no-ops and the macros rename only the
# generated calls. External linkage: an unused static function would warn.
_PRELUDE = r"""
#include "lattice.h"
#include "avail_sites.h"

long pylatkmc_test_probes;
long pylatkmc_test_lookups;
int32_t test_counted_is_enrolled(const AvailSites *as, int32_t proc, int32_t site);
int32_t test_counted_is_enrolled(const AvailSites *as, int32_t proc, int32_t site)
{
    ++pylatkmc_test_probes;
    return avail_sites_is_enrolled(as, proc, site);
}
int32_t test_counted_site_at_ijk(const Lattice *lat, int32_t i, int32_t j, int32_t k);
int32_t test_counted_site_at_ijk(const Lattice *lat, int32_t i, int32_t j, int32_t k)
{
    ++pylatkmc_test_lookups;
    return lattice_site_at_ijk(lat, i, j, k);
}
#define avail_sites_is_enrolled test_counted_is_enrolled
#define lattice_site_at_ijk test_counted_site_at_ijk
"""

#: The check before large-system-scaling/10, verbatim but for the names. Placed
#: after the pattern tables (it reads them); calls the real, uncounted functions.
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
              int32_t vac_site, int32_t neigh_site);
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


def _bind(dll: ctypes.CDLL) -> ctypes.CDLL:
    vp, ci, i32, f64 = ctypes.c_void_p, ctypes.c_int, ctypes.c_int32, ctypes.c_double
    i32p, f32p, f64p = (ctypes.POINTER(t) for t in (i32, ctypes.c_float, f64))
    sigs = {
        "pylatkmc_test_make_lattice_full": (vp, [i32, f32p, f32p, ctypes.c_float] + [i32p] * 4),
        "lattice_build_site_grid": (ci, [vp]),
        "pylatkmc_test_make_state": (vp, [i32, i32, i32, i32p, ctypes.POINTER(ctypes.c_uint8)]),
        "pylatkmc_test_free_lattice": (None, [vp]),
        "pylatkmc_test_free_state": (None, [vp]),
        "avail_sites_alloc": (ci, [ctypes.POINTER(vp), i32, i32]),
        "avail_sites_free": (None, [vp]),
        "avail_sites_clear": (None, [vp]),
        "avail_sites_count": (i32, [vp, i32]),
        "touchup_a": (None, [vp, vp, vp, ci]),
        "pylatkmc_measured_covers_hop": (ci, [vp, vp, vp, i32, i32]),
        "pylatkmc_test_covers_scan": (ci, [vp, vp, vp, i32, i32]),
        "pylatkmc_test_surr_ctx_new": (vp, [i32]),
        "pylatkmc_test_surr_ctx_free": (None, [vp]),
        "pylatkmc_test_surr_rebuild": (f64, [vp, vp, vp, vp, f64]),
        "pylatkmc_test_surr_n_cand": (i32, [vp]),
        "pylatkmc_test_surr_cand": (None, [vp, i32, i32p, f64p]),
    }
    for sym, (restype, argtypes) in sigs.items():
        try:
            fn = getattr(dll, sym)
        except AttributeError:
            continue  # the scan reference lives in the O(1) library only
        fn.restype, fn.argtypes = restype, argtypes
    return dll


def _build(tmp: Path, gen: Path, name: str, proclist_c: str) -> ctypes.CDLL:
    """Compile ``proclist_c`` (a generated proclist.c, possibly instrumented)
    with the real surrogate.c, the surrogate test shim and the runtime pieces."""
    src = tmp / f"{name}_proclist.c"
    src.write_text(proclist_c)
    lib = tmp / (f"lib{name}.dylib" if sys.platform == "darwin" else f"lib{name}.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(CORE), "-I", str(gen), str(src), str(CORE / "surrogate.c"), str(SHIM_SRC)]
    cmd += [str(CORE / f) for f in ("lattice.c", "coord_codes.c", "avail_sites.c")]
    cmd += [str(CORE / "state_actions.c"), str(HELPERS_SRC), "-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"{name} build failed:\n{res.stderr}")
    return _bind(ctypes.CDLL(str(lib)))


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """(scratch dir, generated dir) of the surrogate build of ``_patterns()``."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    pytest.importorskip("numpy")  # surrogate codegen + the D4h ops
    tmp = tmp_path_factory.mktemp("surr_covers")
    return tmp, _generate(tmp, _patterns())


@pytest.fixture(scope="module")
def o1_lib(generated: tuple[Path, Path]) -> ctypes.CDLL:
    """The generated proclist behind the probe/lookup counters, plus the
    pre-fix scan as pylatkmc_test_covers_scan."""
    tmp, gen = generated
    proclist = (gen / "proclist.c").read_text()
    if "v2_record_covers(lat, as, site, pt, ops);" not in proclist:
        pytest.fail("touchup_a does not record measured-hop covers on a surrogate build")
    scan = _SCAN.replace("SCAN_NAME", "pylatkmc_test_covers_scan")
    return _build(tmp, gen, "covers_o1", _PRELUDE + proclist + scan)


@pytest.fixture(scope="module")
def scan_lib(generated: tuple[Path, Path]) -> ctypes.CDLL:
    """The same generated proclist with its O(1) check replaced by the
    pre-fix scan, which surrogate_rebuild then calls."""
    from pylatkmc.surrogate_codegen import _MEASURED_COVERS_C

    tmp, gen = generated
    proclist = (gen / "proclist.c").read_text()
    assert proclist.count(_MEASURED_COVERS_C) == 1
    scan = _SCAN.replace("SCAN_NAME", "pylatkmc_measured_covers_hop")
    return _build(tmp, gen, "covers_scan", proclist.replace(_MEASURED_COVERS_C, scan))


class _Box:
    """A periodic-in-plane slab (site grid from lattice.c) with the
    kmcinit-style 1NN CSR: in-plane neighbours wrap the seams, none cross the
    vacuum. Each site's 1NN list is shuffled with ``seed`` (surrogate_rebuild
    walks it in that order). Owns one avail_sites, reused across clears."""

    def __init__(self, lib: ctypes.CDLL, geom: Geometry, seed: int) -> None:
        from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

        rng = random.Random(seed)
        self.lib, self.geom = lib, geom
        self.dims = (geom.nx, geom.ny, geom.n_layers + geom.n_vacuum)
        self.cells = [
            (u, v, w)
            for w in range(geom.n_layers)
            for u in range(geom.nx)
            for v in range(geom.ny)
            if (u - v) % 2 == 0 and (v - w) % 2 == 0
        ]  # site 0 at cell (0, 0, 0), so site_ijk == cell
        self.index = {c: i for i, c in enumerate(self.cells)}
        n = self.n = len(self.cells)
        self.nn1: list[list[int]] = []
        for u, v, w in self.cells:
            nbrs = [
                self.index[((u + du) % geom.nx, (v + dv) % geom.ny, w + dw)]
                for du, dv, dw in RUNTIME_DIRECTIONS
                if 0 <= w + dw < geom.n_layers
            ]
            rng.shuffle(nbrs)
            self.nn1.append(nbrs)
        off = [0]
        for nb in self.nn1:
            off.append(off[-1] + len(nb))
        flat = [s for nb in self.nn1 for s in nb]
        pos = [c for (u, v, w) in self.cells for c in (u * HX, v * HX, w * HZ)]
        cell = (geom.nx * HX, geom.ny * HX, self.dims[2] * HZ)
        self.lat = lib.pylatkmc_test_make_lattice_full(
            n,
            (ctypes.c_float * (3 * n))(*pos),
            (ctypes.c_float * 3)(*cell),
            NN,
            (ctypes.c_int32 * (n + 1))(*off),
            (ctypes.c_int32 * max(1, len(flat)))(*flat),
            None,
            None,
        )
        assert self.lat and lib.lattice_build_site_grid(self.lat) == 0
        self.n_procs = ctypes.c_int32.in_dll(lib, "pylatkmc_n_procs").value
        self.as_ = ctypes.c_void_p()
        assert lib.avail_sites_alloc(ctypes.byref(self.as_), max(1, self.n_procs), n) == 0

    def raw_neighbour(self, site: int, off: tuple[int, int, int]) -> int | None:
        """The site at site + off WITHOUT wrapping (the surrogate channel's
        candidate test: a raw site_ijk difference), or None."""
        c = tuple(self.cells[site][a] + off[a] for a in range(3))
        if any(not 0 <= c[a] < self.dims[a] for a in range(3)):
            return None
        return self.index.get(c)

    def raw_pairs(self) -> list[tuple[int, int, int]]:
        """Every (site, direction index, neighbour one raw step away along it):
        the pairs surrogate_rebuild can ask about, wherever the atoms are."""
        from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

        out = []
        for s in range(self.n):
            for d, off in enumerate(RUNTIME_DIRECTIONS):
                nb = self.raw_neighbour(s, off)
                if nb is not None:
                    out.append((s, d, nb))
        return out

    def on_seam_or_surface(self, site: int) -> bool:
        """Whether a 1NN of ``site`` wraps a periodic seam or ``site`` is in a
        surface layer."""
        u, v, w = self.cells[site]
        g = self.geom
        seam = u in (0, 1, g.nx - 2, g.nx - 1) or v in (0, 1, g.ny - 2, g.ny - 1)
        return seam or w in (0, g.n_layers - 1)

    def state(self, species: list[int]) -> int:
        vac = [s for s in range(self.n) if species[s] == SP_VACANT]
        st = self.lib.pylatkmc_test_make_state(
            self.n,
            max(1, len(vac)),
            len(vac),
            (ctypes.c_int32 * max(1, len(vac)))(*vac),
            (ctypes.c_uint8 * self.n)(*species),
        )
        assert st
        return st

    def touchup(self, st: int, sites) -> None:
        """One step's enrolment as kmc_step_once makes it: clear, then touchup_a
        per site."""
        self.lib.avail_sites_clear(self.as_)
        for s in sites:
            self.lib.touchup_a(self.lat, st, self.as_, s)

    def candidates(self, st: int) -> tuple[float, list[tuple]]:
        """surrogate_rebuild on the current enrolment: (r_tot, candidates as
        (vac, neigh, dir, atom_sp, trigger, k, ea_hat, leverage), floats hex)."""
        ctx = self.lib.pylatkmc_test_surr_ctx_new(self.n)
        assert ctx
        try:
            rtot = self.lib.pylatkmc_test_surr_rebuild(ctx, self.lat, st, self.as_, 600.0)
            ints, dbls = (ctypes.c_int32 * 5)(), (ctypes.c_double * 3)()
            cands = []
            for i in range(self.lib.pylatkmc_test_surr_n_cand(ctx)):
                self.lib.pylatkmc_test_surr_cand(ctx, i, ints, dbls)
                cands.append((*ints, *(x.hex() for x in dbls)))
        finally:
            self.lib.pylatkmc_test_surr_ctx_free(ctx)
        return rtot, cands

    def close(self) -> None:
        self.lib.avail_sites_free(self.as_)
        self.lib.pylatkmc_test_free_lattice(self.lat)


def _species(rng: random.Random, n: int) -> list[int]:
    return rng.choices((SP_VACANT, SP_NI, SP_CR, SP_FE), (30, 40, 20, 10), k=n)


def _touchup_order(rng: random.Random, n: int, trial: int) -> list[int]:
    """All sites shuffled, a random ~70 % subset, or the first half of a
    shuffle, by trial: some anchors carry no enrolment at all."""
    order = list(range(n))
    rng.shuffle(order)
    if trial % 3 == 1:
        return [s for s in order if rng.random() < 0.7]
    if trial % 3 == 2:
        return order[: n // 2]
    return order


# --------------------------------------------------------------------------- #
# The O(1) answer is the scan's                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("geom", [SLAB, ALIAS_BOX], ids=["slab", "alias_box"])
def test_covers_hop_equals_the_proc_scan(o1_lib, geom: Geometry) -> None:
    """Every (site, surrogate direction) answer equals the pre-fix scan over
    every enrolled proc, and surrogate_rebuild keeps exactly the candidates the
    scan keeps, in order. Neither the check nor the rebuild probes a proc's
    enrolment or resolves a site through the generated code."""
    from pylatkmc.surrogate_codegen import RUNTIME_DIRECTIONS

    lib = o1_lib
    rng = random.Random(20261022 + geom.nx)
    box = _Box(lib, geom, seed=geom.nx)
    names = _proc_names(_patterns())
    probes = ctypes.c_long.in_dll(lib, "pylatkmc_test_probes")
    lookups = ctypes.c_long.in_dll(lib, "pylatkmc_test_lookups")
    pairs = box.raw_pairs()
    enrolled: set[str] = set()
    n_covered = n_uncovered = n_edge_covered = n_dedup = 0
    try:
        for trial in range(12):
            species = _species(rng, box.n)
            st = box.state(species)
            try:
                box.touchup(st, _touchup_order(rng, box.n, trial))
                enrolled.update(
                    names[p] for p in range(box.n_procs) if lib.avail_sites_count(box.as_, p)
                )
                covered: dict[tuple[int, int], int] = {}
                for v, d, nb in pairs:
                    probes.value = lookups.value = 0
                    got = lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, nb)
                    assert (probes.value, lookups.value) == (0, 0), (
                        "the cover check probes the proc table / resolves a site"
                    )
                    want = lib.pylatkmc_test_covers_scan(box.lat, st, box.as_, v, nb)
                    assert got == want, f"trial {trial}: site {v} dir {d} -> {nb}"
                    covered[(v, nb)] = want
                    n_covered += want
                    n_uncovered += 1 - want
                    n_edge_covered += want and box.on_seam_or_surface(v)
                # The candidates the scan keeps: each vacancy (vac_list order) x
                # its real-atom 1NN (CSR order) one raw step along a direction.
                want_cands = []
                for v in (s for s in range(box.n) if species[s] == SP_VACANT):
                    for nb in box.nn1[v]:
                        if species[nb] not in ATOMS:
                            continue
                        off = tuple(box.cells[nb][a] - box.cells[v][a] for a in range(3))
                        if off not in RUNTIME_DIRECTIONS:
                            continue  # a seam neighbour: no surrogate direction
                        if covered[(v, nb)]:
                            n_dedup += 1
                            continue
                        want_cands.append((v, nb, RUNTIME_DIRECTIONS.index(off)))
                probes.value = lookups.value = 0
                _rtot, cands = box.candidates(st)
                assert (probes.value, lookups.value) == (0, 0)
                got_cands = [c[:3] for c in cands]
                assert got_cands == want_cands, f"trial {trial}: surrogate candidates differ"
            finally:
                lib.pylatkmc_test_free_state(st)
    finally:
        box.close()
    # The comparison is only as good as its matches: every pattern was enrolled
    # somewhere, both answers occur, covers occur at the seams and surfaces, and
    # the de-dup removed candidates.
    assert enrolled == {p.name for p in _patterns()}, sorted(enrolled)
    assert n_covered > 50 and n_uncovered > 50, (n_covered, n_uncovered)
    assert n_edge_covered > 0
    assert n_dedup > 0


def _isolated_cover(lib: ctypes.CDLL, vacancies, cr_sites, ask) -> tuple[int, int]:
    """On the alias box (layer 0 row v = 0), all Ni but ``vacancies`` and
    ``cr_sites`` (u coordinates): touch up every site, then (O(1), scan) for
    the vacancy at u = ``ask[0]`` and its raw neighbour ``ask[1]`` cells along
    u. Every other raw pair must agree too."""
    box = _Box(lib, ALIAS_BOX, seed=7)
    try:
        species = [SP_NI] * box.n
        for u in vacancies:
            species[box.index[(u % ALIAS_BOX.nx, 0, 0)]] = SP_VACANT
        for u in cr_sites:
            species[box.index[(u % ALIAS_BOX.nx, 0, 0)]] = SP_CR
        st = box.state(species)
        try:
            box.touchup(st, range(box.n))
            for v, d, nb in box.raw_pairs():
                got = lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, nb)
                want = lib.pylatkmc_test_covers_scan(box.lat, st, box.as_, v, nb)
                assert got == want, (v, d, nb)
            v = box.index[(ask[0], 0, 0)]
            nb = box.index[(ask[0] + ask[1], 0, 0)]
            return (
                lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, nb),
                lib.pylatkmc_test_covers_scan(box.lat, st, box.as_, v, nb),
            )
        finally:
            lib.pylatkmc_test_free_state(st)
    finally:
        box.close()


@pytest.mark.parametrize("u0", [2, 4])
def test_chain_destination_wrapping_onto_a_1nn_covers_it(o1_lib, u0: int) -> None:
    """p_chain moves the vacancy 4 cells along +u; on the 6-plane box that site
    is the anchor's raw -u neighbour, and nothing else covers that hop here
    (Ni everywhere, the Cr at u0 - 2): the scan counts it, so must the word."""
    assert _isolated_cover(o1_lib, [u0], [u0 + 4], (u0, -2)) == (1, 1)


@pytest.mark.parametrize("u0", [0, 2])
def test_vacancy_origin_wrapping_onto_the_anchor_covers(o1_lib, u0: int) -> None:
    """p_alias's vacancy origin is 6 cells along +u: the anchor itself on the
    6-plane box. With the anchor's -u neighbour vacant, no other pattern covers
    its +u hop: the scan counts p_alias's, so must the word."""
    assert _isolated_cover(o1_lib, [u0, u0 - 2], [], (u0, 2)) == (1, 1)


def test_surrogate_candidates_are_bit_identical_to_the_scan_build(o1_lib, scan_lib) -> None:
    """surrogate_rebuild walks the same candidates in the same order with the
    same k, ea_hat, leverage and trigger (bit for bit), and the same r_tot,
    whether the de-dup is the O(1) word or the old proc scan."""
    rng = random.Random(10)
    n_dedup = 0
    for geom in (SLAB, ALIAS_BOX):
        boxes = {"o1": _Box(o1_lib, geom, seed=3), "scan": _Box(scan_lib, geom, seed=3)}
        try:
            n = boxes["o1"].n
            pairs = boxes["o1"].raw_pairs()
            for trial in range(6):
                species = _species(rng, n)
                order = _touchup_order(rng, n, trial)
                got = {}
                for key, box in boxes.items():
                    st = box.state(species)
                    try:
                        box.touchup(st, order)
                        rtot, cands = box.candidates(st)
                        got[key] = (rtot.hex(), cands)
                    finally:
                        box.lib.pylatkmc_test_free_state(st)
                assert got["o1"] == got["scan"], f"{geom}: trial {trial}"
                n_live = sum(
                    species[v] == SP_VACANT and species[nb] in ATOMS for v, _d, nb in pairs
                )
                assert 0 < len(got["o1"][1]) <= n_live
                n_dedup += n_live - len(got["o1"][1])
        finally:
            for box in boxes.values():
                box.close()
    assert n_dedup > 0, "no candidate was covered by a measured proc: the de-dup is untested"


# --------------------------------------------------------------------------- #
# Emission                                                                    #
# --------------------------------------------------------------------------- #
def test_cover_bit_order_is_the_surrogate_direction_order(monkeypatch) -> None:
    """The cover table (RUNTIME_DIRECTIONS) is surr_dirs' runtime directions,
    in order, and emit_surrogate_tables refuses to bake a drift."""
    pytest.importorskip("numpy")
    from pylatkmc import surrogate_codegen as sc

    from ._esym_fixture import synthetic_v2_model

    baked = tuple(g.runtime_dir for g in sc.bake_directions())
    assert baked == sc.RUNTIME_DIRECTIONS
    assert len(set(sc.RUNTIME_DIRECTIONS)) == 12
    monkeypatch.setattr(sc, "RUNTIME_DIRECTIONS", sc.RUNTIME_DIRECTIONS[::-1])
    with pytest.raises(RuntimeError, match="RUNTIME_DIRECTIONS"):
        sc.emit_surrogate_tables(synthetic_v2_model())


def test_no_cover_code_without_a_surrogate_model(tmp_path: Path) -> None:
    """A v2 build without a surrogate model emits exactly the pattern tables
    it did before (no cover table, no recording in touchup_a); a cover list
    the 16-bit word or int8 table cannot hold is refused."""
    pytest.importorskip("numpy")
    from pylatkmc.pattern_codegen import emit_pattern_tables

    patterns = _patterns()
    plain = emit_pattern_tables(patterns)
    assert "v2_cover" not in plain and "avail_sites_cover" not in plain
    text = (_generate(tmp_path, patterns, surrogate=False) / "proclist.c").read_text()
    assert plain in text
    assert "v2_cover" not in text and "avail_sites_cover" not in text
    for bad in ([], [(0, 0, 0)], [(2, 0, 0), (2, 0, 0)], [(128, 0, 0)], [(2, 0, 0)] * 17):
        with pytest.raises(ValueError, match="cover_dirs"):
            emit_pattern_tables(patterns, cover_dirs=bad)


def test_empty_catalogue_with_a_surrogate_model_compiles(tmp_path: Path) -> None:
    """An all-skipped catalogue still emits a compilable stub when a surrogate
    model is baked: no measured proc covers anything, so every live candidate
    stays a surrogate candidate."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    pytest.importorskip("numpy")
    gen = _generate(tmp_path, [])
    proclist = (gen / "proclist.c").read_text()
    assert "static int32_t v2_cover_dir(" in proclist
    assert "static void v2_record_covers(" not in proclist  # nothing to record
    lib = _build(tmp_path, gen, "covers_empty", proclist)
    assert ctypes.c_int32.in_dll(lib, "pylatkmc_n_procs").value == 0
    rng = random.Random(5)
    box = _Box(lib, SLAB, seed=5)
    try:
        species = _species(rng, box.n)
        st = box.state(species)
        try:
            box.touchup(st, range(box.n))
            pairs = box.raw_pairs()
            assert not any(
                lib.pylatkmc_measured_covers_hop(box.lat, st, box.as_, v, nb) for v, _d, nb in pairs
            )
            n_live = sum(species[v] == SP_VACANT and species[nb] in ATOMS for v, _d, nb in pairs)
            assert len(box.candidates(st)[1]) == n_live > 0
        finally:
            lib.pylatkmc_test_free_state(st)
    finally:
        box.close()


def test_committed_surrogate_proclists_use_the_cover_words() -> None:
    """CI links the committed proclists without regenerating them: each
    committed surrogate build records covers in touchup_a and answers the
    de-dup from them, with its cover table equal to its surr_dirs; the other
    v2 builds carry no cover code."""
    surrogate, plain = [], []
    for path in sorted((REPO_ROOT / "models").glob("*/generated/proclist.c")):
        text = path.read_text()
        if "V2Pattern" in text:
            (surrogate if "g_surrogate" in text else plain).append((path, text))
    if not surrogate:
        pytest.skip("no committed surrogate proclist in this checkout")
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
        assert "v2_cover" not in text and "avail_sites_cover" not in text, path
