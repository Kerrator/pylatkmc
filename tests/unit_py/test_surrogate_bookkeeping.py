"""Regression tests for the Phase C surrogate channel's per-candidate bookkeeping
(large-system-scaling/10, 11).

- 10: the measured-channel de-dup ``pylatkmc_measured_covers_hop`` scanned every
  proc with ``avail_sites_is_enrolled`` for every surrogate candidate, every step.
  ``touchup_a`` now records, while it enrols, which baked 1NN hop directions the
  measured procs at an anchor perform (an ``avail_sites`` site tag), and the
  check reads that tag. The answer must not change: over random enrolment states
  on a periodic slab with vacuum (both surfaces and the periodic seams) and on a
  box smaller than the pattern reach (offsets alias), every (site, direction)
  answer equals the pre-fix scan (kept verbatim below as the brute-force
  reference), ``surrogate_rebuild`` keeps exactly the candidates that reference
  keeps, in order, and the generated code makes no ``avail_sites_is_enrolled``
  call.
- 11: ``flag_lookup`` scanned the flag registry linearly for every live candidate
  and again for the fired one. An open-addressing index now finds the entry.
  Driving ``surrogate_account`` with synthetic candidate streams, the registry
  (its entries, their insertion order = registry index, every field, and the
  silently-capped full registry) equals a Python port of the linear scan, and a
  lookup compares O(1) keys, counted by instrumenting the key comparison in a
  test copy of surrogate.c.

The proclist comes from the real ``codegen.generate`` (hand-built patterns and a
synthetic surrogate model fed in through monkeypatched catalogue and model
loading), so no machine-local catalogue is needed. ctypes level, no MPI; skips
without cc or numpy.
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

SP_VACANT, SP_NI, SP_FE, SP_CR = 0, 1, 2, 3  # events_base.h (by name: FE=2, CR=3)
ATOMS = (SP_NI, SP_FE, SP_CR)

# Runtime frame: tetragonal grid (nn/2, nn/2, nn/sqrt2), sites on the
# same-parity sublattice; the 12 1NN offsets in grid cells.
NN = 2.5
HX, HZ = NN / 2.0, NN / math.sqrt(2.0)
NN1_OFFSETS = (
    (2, 0, 0), (-2, 0, 0), (0, 2, 0), (0, -2, 0),
    (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
    (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
)  # fmt: skip


class Geometry(NamedTuple):
    nx: int  # in-plane grid planes (periodic)
    ny: int
    n_layers: int  # atomic layers, under ...
    n_vacuum: int  # ... this many empty grid planes (the k axis wraps too)


#: 10 x 10 in-plane planes, 5 layers under 4 vacuum planes: every axis at or
#: above 2 * reach + 1 for the patterns below except p_alias's 6-cell row.
SLAB = Geometry(10, 10, 5, 4)
#: 6 x 6 x 4 planes: p_alias's 6-cell vacancy origin wraps onto the anchor, so
#: that pattern covers a hop here and none on the slab (the runtime refuses
#: such a box at startup, but the de-dup must still be exact).
ALIAS_BOX = Geometry(6, 6, 3, 1)


def _patterns() -> list:
    """Hand-built runtime-frame patterns spanning every way a measured proc does
    or does not cover a surrogate candidate: 1NN hops in-plane (all ops, three
    members) and interlayer (an op subset; Cr and Fe movers), a vacancy landing on
    a 3NN site, a concerted chain landing two hops away, a divacancy (no unique
    vacancy origin: row -1), a Ni-anchored pattern (vacancy origin != anchor),
    and a vacancy origin six cells out (the anchor itself on the alias box)."""
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
        pat("p_cr_hop", v, [((0, 0, 0), v, cr), ((1, 1, 1), cr, v)],
            [((0, 2, 0), "EMPTY", None)], (0, 3, 5, 6, 9, 10, 12, 15), (cr,), 2),
        pat("p_fe_hop", v, [((0, 0, 0), v, fe), ((1, -1, -1), fe, v)],
            [((-1, 1, 1), "SPECIES", ni)], every, (fe,)),
        pat("p_3nn", v, [((0, 0, 0), v, ni), ((3, -1, 1), ni, v)], [], every, (ni,)),
        pat("p_chain", v, [((0, 0, 0), v, ni), ((2, 0, 0), ni, cr), ((4, 0, 0), cr, v)],
            [], (0, 1, 2, 3), (ni, cr)),
        pat("p_divac", v, [((0, 0, 0), v, ni), ((0, 2, 0), v, ni), ((2, 0, 0), ni, v),
                           ((2, 2, 0), ni, v)], [], every, (ni,)),
        pat("p_ni_anchor", ni, [((0, 0, 0), ni, v), ((0, 2, 0), v, ni)], [], every, (ni,)),
        pat("p_alias", v, [((6, 0, 0), v, ni), ((2, 0, 0), ni, v)],
            [((0, 0, 0), "SPECIES", v)], (0, 6, 8), (ni,)),
    ]  # fmt: skip


# --------------------------------------------------------------------------- #
# Build: real codegen.generate -> proclist.{c,h} -> one shared library        #
# --------------------------------------------------------------------------- #
# Prepended to the generated proclist.c: the generated code's
# avail_sites_is_enrolled calls are counted (the pre-fix check made N_PROCS of
# them per candidate). avail_sites.h is include-guarded, so the preamble's own
# include after this is a no-op.
_PRELUDE = r"""
#include "avail_sites.h"
long pylatkmc_test_is_enrolled_calls;
int32_t test_counted_is_enrolled(const AvailSites *as, int32_t proc, int32_t site);
int32_t test_counted_is_enrolled(const AvailSites *as, int32_t proc, int32_t site)
{
    ++pylatkmc_test_is_enrolled_calls;
    return avail_sites_is_enrolled(as, proc, site);
}
#define avail_sites_is_enrolled test_counted_is_enrolled
"""

# Appended to the generated proclist.c (same translation unit, so it sees the
# static pattern tables). The reference is the pre-fix pylatkmc_measured_covers_hop
# verbatim apart from its names.
_APPENDIX = r"""
#undef avail_sites_is_enrolled
static int32_t ref_proc_vsite(const Lattice *lat, int32_t anchor, int32_t proc, int row)
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
int pylatkmc_test_ref_covers(const Lattice *lat, const AvailSites *as,
                             int32_t vac_site, int32_t neigh_site);
int pylatkmc_test_ref_covers(const Lattice *lat, const AvailSites *as,
                             int32_t vac_site, int32_t neigh_site)
{
    for (int32_t p = 0; p < N_PROCS; ++p) {
        if (avail_sites_is_enrolled(as, p, vac_site) != 1) continue;
        const V2Pattern *pt = &v2_patterns[v2_procs[p].pat];
        int32_t vo = ref_proc_vsite(lat, vac_site, p, pt->v_origin_row);
        int32_t vd = ref_proc_vsite(lat, vac_site, p, pt->v_dest_row);
        if (vo == vac_site && vd == neigh_site) return 1;
    }
    return 0;
}
int pylatkmc_test_covers(const AvailSites *as, int32_t vac_site, int32_t dir_idx);
int pylatkmc_test_covers(const AvailSites *as, int32_t vac_site, int32_t dir_idx)
{
    return pylatkmc_measured_covers_hop(as, vac_site, dir_idx);
}
"""

# A separate translation unit driving the runtime channel (surrogate.h API).
_SHIM = r"""
#include <stdlib.h>
#include "proclist.h"
#include "surrogate.h"

SurrCtx *pylatkmc_test_ctx_new(int32_t capacity, double flux_threshold);
void pylatkmc_test_ctx_free(SurrCtx *c);
int32_t pylatkmc_test_rebuild(SurrCtx *c, const Lattice *lat, const State *st,
                              const AvailSites *as, int32_t *vac, int32_t *neigh,
                              int32_t *dir, int32_t cap);
int pylatkmc_test_account(SurrCtx *c, const Lattice *lat, int32_t n,
                          const int32_t *vac, const int32_t *neigh, const int32_t *dir,
                          const uint8_t *sp, const double *k, const double *ea,
                          const double *lev, const uint32_t *trig, int32_t fired,
                          double dt, double k_total);
int32_t pylatkmc_test_n_flags(const SurrCtx *c);
const SurrFlag *pylatkmc_test_flag(const SurrCtx *c, int32_t i);
int32_t pylatkmc_test_surrflag_size(void);
uint64_t pylatkmc_test_n_surr_fired(const SurrCtx *c);

SurrCtx *pylatkmc_test_ctx_new(int32_t capacity, double flux_threshold)
{
    SurrCtx *c = malloc(sizeof *c);
    if (!c) return NULL;
    if (surrogate_ctx_init(c, pylatkmc_surrogate, 0, 1, 0.0, 0.0, flux_threshold,
                           capacity, 500.0) != 0) {
        free(c);
        return NULL;
    }
    return c;
}

void pylatkmc_test_ctx_free(SurrCtx *c) { surrogate_ctx_free(c); free(c); }

int32_t pylatkmc_test_rebuild(SurrCtx *c, const Lattice *lat, const State *st,
                              const AvailSites *as, int32_t *vac, int32_t *neigh,
                              int32_t *dir, int32_t cap)
{
    surrogate_rebuild(c, lat, st, as, 500.0);
    for (int32_t i = 0; i < c->n_cand && i < cap; ++i) {
        vac[i] = c->cand[i].vac_site;
        neigh[i] = c->cand[i].neigh_site;
        dir[i] = c->cand[i].dir_idx;
    }
    return c->n_cand;
}

/* Load n synthetic live candidates (surr_rtot = their k sum, in order) and run
 * one step of registry accounting. */
int pylatkmc_test_account(SurrCtx *c, const Lattice *lat, int32_t n,
                          const int32_t *vac, const int32_t *neigh, const int32_t *dir,
                          const uint8_t *sp, const double *k, const double *ea,
                          const double *lev, const uint32_t *trig, int32_t fired,
                          double dt, double k_total)
{
    if (n > c->cap_cand) {
        SurrCandidate *p = realloc(c->cand, (size_t)n * sizeof *p);
        if (!p) return -1;
        c->cand = p;
        c->cap_cand = n;
    }
    double rtot = 0.0;
    for (int32_t i = 0; i < n; ++i) {
        SurrCandidate *s = &c->cand[i];
        s->vac_site = vac[i]; s->neigh_site = neigh[i]; s->dir_idx = dir[i];
        s->atom_sp = sp[i]; s->k = k[i]; s->ea_hat = ea[i]; s->leverage = lev[i];
        s->trigger = trig[i];
        rtot += k[i];
    }
    c->n_cand = n;
    c->surr_rtot = rtot;
    surrogate_account(c, lat, fired, dt, k_total);
    return 0;
}

int32_t pylatkmc_test_n_flags(const SurrCtx *c) { return c->n_flags; }
const SurrFlag *pylatkmc_test_flag(const SurrCtx *c, int32_t i) { return &c->flags[i]; }
int32_t pylatkmc_test_surrflag_size(void) { return (int32_t)sizeof(SurrFlag); }
uint64_t pylatkmc_test_n_surr_fired(const SurrCtx *c) { return c->n_surr_fired; }
"""

#: The registry key comparison in flag_lookup, counted in the test copy of
#: surrogate.c (matches the pre-fix linear scan's comparison too).
_KEY_CMP = re.compile(r"\b(\w+)->site_a == lo\b")


class SurrFlag(ctypes.Structure):
    """Mirror of surrogate.h's SurrFlag (natural alignment; size-checked)."""

    _fields_ = [
        ("site_a", ctypes.c_int32),
        ("site_b", ctypes.c_int32),
        ("dir_idx", ctypes.c_int32),
        ("used", ctypes.c_uint8),
        ("n_enrolled_steps", ctypes.c_uint64),
        ("n_fired", ctypes.c_uint64),
        ("carried_flux", ctypes.c_double),
        ("first_step", ctypes.c_uint64),
        ("last_ea_hat", ctypes.c_double),
        ("last_leverage", ctypes.c_double),
        ("trigger_or", ctypes.c_uint32),
        ("ru", ctypes.c_int32),
        ("rv", ctypes.c_int32),
        ("rw", ctypes.c_int32),
        ("sp_a", ctypes.c_uint8),
        ("sp_b", ctypes.c_uint8),
    ]


FLAG_FIELDS = [name for name, _ in SurrFlag._fields_]


def _generate(tmp: Path, patterns: list) -> Path:
    """Run the real codegen.generate on ``patterns`` + the synthetic v2 model
    (catalogue and model loading monkeypatched); return the generated dir."""
    from pylatkmc import codegen, translator_v2
    from pylatkmc.ingest import surrogate as ingest_surrogate
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

    from ._esym_fixture import synthetic_v2_model

    model = synthetic_v2_model()
    spec = ModelSpec(
        name="surr_bookkeeping",
        species=["Vacant", "Ni", "Fe", "Cr"],
        shells=[Shell(name="s1", cutoff_mult=1.05)],
        key=Key(axes=[KeyAxis(name="n_vac_s1", kind="count", max=2, shell="s1", match="vac")]),
        rate_data=RateData(
            event_class_table=Path("monkeypatched.parquet"),
            surrogate_model=Path("monkeypatched.json"),
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
        mp.setattr(ingest_surrogate, "load_model", lambda path: model)
        codegen.generate(spec, gen)
    return gen


_vp, _ci, _i32, _f64 = ctypes.c_void_p, ctypes.c_int, ctypes.c_int32, ctypes.c_double
_i32p, _f32p, _f64p = (ctypes.POINTER(t) for t in (_i32, ctypes.c_float, _f64))
_u8p, _u32p = ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint32)
#: ctypes signatures, set for the ones a library exports (the covered-hop hooks
#: live in the ticket-10 library only).
_SIGS = {
    "pylatkmc_test_make_lattice_full": (_vp, [_i32, _f32p, _f32p, ctypes.c_float] + [_i32p] * 4),
    "lattice_build_site_grid": (_ci, [_vp]),
    "pylatkmc_test_make_state": (_vp, [_i32, _i32, _i32, _i32p, _u8p]),
    "pylatkmc_test_free_lattice": (None, [_vp]),
    "pylatkmc_test_free_state": (None, [_vp]),
    "avail_sites_alloc": (_ci, [ctypes.POINTER(_vp), _i32, _i32]),
    "avail_sites_free": (None, [_vp]),
    "avail_sites_clear": (None, [_vp]),
    "avail_sites_count": (_i32, [_vp, _i32]),
    "touchup_a": (None, [_vp, _vp, _vp, _ci]),
    "pylatkmc_test_ref_covers": (_ci, [_vp, _vp, _i32, _i32]),
    "pylatkmc_test_covers": (_ci, [_vp, _i32, _i32]),
    "pylatkmc_test_ctx_new": (_vp, [_i32, _f64]),
    "pylatkmc_test_ctx_free": (None, [_vp]),
    "pylatkmc_test_rebuild": (_i32, [_vp, _vp, _vp, _vp, _i32p, _i32p, _i32p, _i32]),
    "pylatkmc_test_account": (
        _ci,
        [_vp, _vp, _i32, _i32p, _i32p, _i32p, _u8p, _f64p, _f64p, _f64p, _u32p, _i32, _f64, _f64],
    ),
    "pylatkmc_test_n_flags": (_i32, [_vp]),
    "pylatkmc_test_flag": (ctypes.POINTER(SurrFlag), [_vp, _i32]),
    "pylatkmc_test_surrflag_size": (_i32, []),
    "pylatkmc_test_n_surr_fired": (ctypes.c_uint64, [_vp]),
}


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """(scratch dir, generated dir) of the surrogate build both libraries use."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    pytest.importorskip("numpy")  # surrogate codegen + the D4h ops
    tmp = tmp_path_factory.mktemp("surr_bookkeeping")
    gen = _generate(tmp, _patterns())
    (tmp / "shim.c").write_text(_SHIM)
    return tmp, gen


def _build(tmp: Path, gen: Path, name: str, sources: list[Path]) -> ctypes.CDLL:
    """Compile ``sources`` + the channel shim + the runtime pieces they need."""
    lib = tmp / (f"lib{name}.dylib" if sys.platform == "darwin" else f"lib{name}.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(CORE), "-I", str(gen), *map(str, sources), str(tmp / "shim.c")]
    cmd += [str(CORE / f) for f in ("lattice.c", "coord_codes.c", "avail_sites.c")]
    cmd += [str(CORE / "state_actions.c"), str(HELPERS_SRC), "-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"{name} build failed:\n{res.stderr}")
    dll = ctypes.CDLL(str(lib))
    for sym, (restype, argtypes) in _SIGS.items():
        try:
            fn = getattr(dll, sym)
        except AttributeError:
            continue  # a hook of the other library
        fn.restype, fn.argtypes = restype, argtypes
    assert dll.pylatkmc_test_surrflag_size() == ctypes.sizeof(SurrFlag)
    return dll


@pytest.fixture(scope="module")
def covers_lib(generated: tuple[Path, Path]) -> ctypes.CDLL:
    """Ticket 10: the generated proclist behind the is_enrolled counter, plus
    the brute-force reference, with the real surrogate.c."""
    tmp, gen = generated
    proclist = (gen / "proclist.c").read_text()
    if "surr_tag_covered(lat, as, site, pt, ops);" not in proclist:
        pytest.fail("touchup_a does not record covered hops on a surrogate build")
    src = tmp / "proclist_covers.c"
    src.write_text(_PRELUDE + proclist + _APPENDIX)
    return _build(tmp, gen, "surr_covers", [src, CORE / "surrogate.c"])


@pytest.fixture(scope="module")
def registry_lib(generated: tuple[Path, Path]) -> ctypes.CDLL:
    """Ticket 11: the plain generated proclist with a copy of surrogate.c that
    counts registry key comparisons."""
    tmp, gen = generated
    counted, n_sub = _KEY_CMP.subn(
        r"(++pylatkmc_test_flag_key_cmps, \1->site_a == lo)", (CORE / "surrogate.c").read_text()
    )
    if n_sub != 1:
        pytest.fail(f"expected one registry key comparison in surrogate.c, found {n_sub}")
    surr = tmp / "surrogate_counted.c"
    surr.write_text("long pylatkmc_test_flag_key_cmps;\n" + counted)
    return _build(tmp, gen, "surr_registry", [gen / "proclist.c", surr])


class _Box:
    """A periodic-in-plane slab lattice (site grid from lattice.c) with the
    kmcinit-style 1NN CSR: in-plane neighbours wrap the seams, none across the
    vacuum. Each site's 1NN list is shuffled (surrogate_rebuild walks it)."""

    def __init__(self, lib: ctypes.CDLL, geom: Geometry, rng: random.Random) -> None:
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
                for du, dv, dw in NN1_OFFSETS
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
        assert self.lat
        assert lib.lattice_build_site_grid(self.lat) == 0

    def raw_neighbour(self, site: int, off: tuple[int, int, int]) -> int | None:
        """The site at site + off WITHOUT wrapping (the surrogate channel's
        candidate test: a raw site_ijk difference), or None."""
        c = tuple(self.cells[site][a] + off[a] for a in range(3))
        if any(not 0 <= c[a] < self.dims[a] for a in range(3)):
            return None
        return self.index.get(c)

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
            self.n,
            len(vac),
            (ctypes.c_int32 * max(1, len(vac)))(*vac),
            (ctypes.c_uint8 * self.n)(*species),
        )
        assert st
        return st

    def close(self) -> None:
        self.lib.pylatkmc_test_free_lattice(self.lat)


def _procs_of(patterns: list, name: str) -> list[int]:
    from pylatkmc.pattern_codegen import _proc_list

    _order, procs = _proc_list(patterns)
    return [p for p, (_t, _op, _m, pi) in enumerate(procs) if patterns[pi].name == name]


# --------------------------------------------------------------------------- #
# 10: measured-channel de-dup                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("geom", [SLAB, ALIAS_BOX], ids=["slab", "alias_box"])
def test_covers_hop_matches_the_proc_scan(covers_lib, geom: Geometry) -> None:
    """Every (site, baked direction) answer, and the surrogate candidate list,
    equal the pre-fix scan over every enrolled proc; no is_enrolled probe."""
    from pylatkmc.surrogate_codegen import bake_directions

    lib = covers_lib
    rng = random.Random(20261022 + geom.nx)
    box = _Box(lib, geom, rng)
    dirs = [g.runtime_dir for g in bake_directions()]
    n_procs = ctypes.c_int32.in_dll(lib, "pylatkmc_n_procs").value
    probes = ctypes.c_long.in_dll(lib, "pylatkmc_test_is_enrolled_calls")
    alias_procs = _procs_of(_patterns(), "p_alias")
    as_ = ctypes.c_void_p()
    assert lib.avail_sites_alloc(ctypes.byref(as_), n_procs, box.n) == 0
    ctx = lib.pylatkmc_test_ctx_new(0, 0.01)
    assert ctx
    n_covered = n_uncovered = n_edge_covered = n_dedup = n_alias_enrolled = 0
    try:
        for trial in range(12):
            species = rng.choices((SP_VACANT, SP_NI, SP_CR, SP_FE), (30, 45, 15, 10), k=box.n)
            st = box.state(species)
            try:
                # Enrolment as kmc_step_once makes it (clear, then touchup_a per
                # site); most trials touch up a random subset in random order,
                # so some vacancies carry no enrolment at all.
                lib.avail_sites_clear(as_)
                sites = [s for s in range(box.n) if trial % 3 == 0 or rng.random() < 0.7]
                rng.shuffle(sites)
                probes.value = 0
                for s in sites:
                    lib.touchup_a(box.lat, st, as_, s)
                n_alias_enrolled += sum(lib.avail_sites_count(as_, p) for p in alias_procs)
                covered: dict[tuple[int, int], int] = {}
                for v in range(box.n):
                    for d, off in enumerate(dirs):
                        nb = box.raw_neighbour(v, off)
                        if nb is None:
                            continue
                        want = lib.pylatkmc_test_ref_covers(box.lat, as_, v, nb)
                        got = lib.pylatkmc_test_covers(as_, v, d)
                        assert got == want, f"trial {trial}: site {v} dir {d} -> {nb}"
                        covered[(v, nb)] = want
                        n_covered += want
                        n_uncovered += 1 - want
                        n_edge_covered += want and box.on_seam_or_surface(v)
                # surrogate_rebuild keeps the candidates the reference keeps, in order.
                vac = [s for s in range(box.n) if species[s] == SP_VACANT]
                want_cands = []
                for v in vac:
                    for nb in box.nn1[v]:
                        if species[nb] not in ATOMS:
                            continue
                        off = tuple(box.cells[nb][a] - box.cells[v][a] for a in range(3))
                        if off not in dirs:
                            continue  # a seam neighbour: no baked direction
                        if covered[(v, nb)]:
                            n_dedup += 1
                            continue
                        want_cands.append((v, nb, dirs.index(off)))
                cap = 12 * max(1, len(vac))
                out = [(ctypes.c_int32 * cap)() for _ in range(3)]
                n = lib.pylatkmc_test_rebuild(ctx, box.lat, st, as_, *out, cap)
                got_cands = [(out[0][i], out[1][i], out[2][i]) for i in range(n)]
                assert got_cands == want_cands, f"trial {trial}: surrogate candidates differ"
                assert probes.value == 0, (
                    f"the generated code probed avail_sites_is_enrolled {probes.value} times"
                )
            finally:
                lib.pylatkmc_test_free_state(st)
    finally:
        lib.pylatkmc_test_ctx_free(ctx)
        lib.avail_sites_free(as_)
        box.close()
    # The comparison must have seen covered and uncovered hops, covers at the
    # seams and surfaces, and candidates the de-dup removed.
    assert n_covered > 50 and n_uncovered > 50
    assert n_edge_covered > 0
    assert n_dedup > 0
    if geom is ALIAS_BOX:
        assert n_alias_enrolled > 0, "p_alias never matched on the alias box"


def test_committed_surrogate_proclists_record_covered_hops() -> None:
    """CI links the committed proclists without regenerating them: a committed
    surrogate proclist must tag covered hops in touchup_a and must not scan
    procs in its covered-hop check; a v2 proclist without a surrogate model
    carries no hook at all."""
    found = 0
    for path in sorted((REPO_ROOT / "models").glob("*/generated/proclist.c")):
        text = path.read_text()
        if "V2Pattern" not in text:
            continue
        if "pylatkmc_measured_covers_hop" in text:
            found += 1
            assert "surr_tag_covered(lat, as, site, pt, ops);" in text, f"{path}: regenerate it"
            assert "avail_sites_is_enrolled" not in text, f"{path}: regenerate it"
        else:
            assert "surr_tag_covered" not in text, path
    if found == 0:
        pytest.skip("no committed surrogate proclist in this checkout")


# --------------------------------------------------------------------------- #
# 11: flag registry                                                           #
# --------------------------------------------------------------------------- #
class _RefRegistry:
    """Python port of the pre-fix registry: flag_lookup as a linear scan in
    registry-index (insertion) order, plus surrogate_account's bookkeeping."""

    def __init__(self, capacity: int, flux_threshold: float) -> None:
        self.capacity = capacity
        self.thr = flux_threshold
        self.flags: list[dict] = []
        self.n_surr_fired = 0

    def lookup(self, a: int, b: int, d: int) -> dict | None:
        lo, hi = min(a, b), max(a, b)
        for f in self.flags:
            if f["used"] and f["site_a"] == lo and f["site_b"] == hi and f["dir_idx"] == d:
                return f
        if len(self.flags) >= self.capacity:
            return None  # full: silently capped
        f = dict.fromkeys(FLAG_FIELDS, 0)
        f.update(site_a=lo, site_b=hi, dir_idx=d, used=1, carried_flux=0.0)
        f.update(last_ea_hat=0.0, last_leverage=0.0)
        self.flags.append(f)
        return f

    def account(self, cands: list[tuple], fired: int, dt: float, cells: list) -> None:
        k_flag = 0.0
        for c in cands:
            k_flag += c[4]
        for v, nb, d, sp, k, ea, lev, trig in cands:
            f = self.lookup(v, nb, d)
            if f is None:
                continue
            if f["n_enrolled_steps"] == 0:
                f["ru"], f["rv"], f["rw"] = cells[v]
                f["sp_a"], f["sp_b"] = SP_VACANT, sp
            f["n_enrolled_steps"] += 1
            f["carried_flux"] += k * dt
            f["last_ea_hat"], f["last_leverage"] = ea, lev
            t = trig | 4 if (k_flag > 0.0 and k / k_flag > self.thr) else trig & ~4
            f["trigger_or"] |= t
        if 0 <= fired < len(cands):
            f = self.lookup(*cands[fired][:3])
            if f is not None:
                f["n_fired"] += 1
            self.n_surr_fired += 1


def _account(lib, ctx, lat, cands: list[tuple], fired: int, dt: float) -> None:
    n = len(cands)
    cols = list(zip(*cands)) if cands else [()] * 8
    i32a = ctypes.c_int32 * max(1, n)
    f64a = ctypes.c_double * max(1, n)
    rc = lib.pylatkmc_test_account(
        ctx, lat, n,
        i32a(*cols[0]), i32a(*cols[1]), i32a(*cols[2]),
        (ctypes.c_uint8 * max(1, n))(*cols[3]),
        f64a(*cols[4]), f64a(*cols[5]), f64a(*cols[6]),
        (ctypes.c_uint32 * max(1, n))(*cols[7]),
        fired, dt, 1.0,
    )  # fmt: skip
    assert rc == 0


def _registry(lib, ctx) -> list[dict]:
    out = []
    for i in range(lib.pylatkmc_test_n_flags(ctx)):
        f = lib.pylatkmc_test_flag(ctx, i).contents
        out.append({name: getattr(f, name) for name in FLAG_FIELDS})
    return out


def _candidate(rng: random.Random, key: tuple[int, int, int]) -> tuple:
    """One synthetic live candidate on ``key``, either orientation of the pair.
    Dyadic k / dt keep every flux sum exact (no FMA dependence)."""
    v, nb, d = key if rng.random() < 0.5 else (key[1], key[0], key[2])
    return (v, nb, d, rng.choice(ATOMS), rng.randint(1, 64) / 16.0,
            rng.randint(0, 1024) / 256.0, rng.randint(0, 1024) / 1024.0, rng.randint(0, 15))  # fmt: skip


@pytest.mark.parametrize("capacity", [0, 64, 1], ids=["default_65536", "cap64_full", "cap1"])
def test_flag_registry_matches_the_linear_scan(registry_lib, capacity: int) -> None:
    """Entries, registry order and every field equal the linear-scan registry,
    including a registry that fills up and silently drops new keys."""
    lib = registry_lib
    rng = random.Random(1100 + capacity)
    box = _Box(lib, SLAB, rng)
    thr = 0.05
    ctx = lib.pylatkmc_test_ctx_new(capacity, thr)
    assert ctx
    ref = _RefRegistry(capacity if capacity > 0 else 65536, thr)
    # A key pool with shared pairs on different directions; steps draw from a
    # window that slides through it, so keys recur, then retire, then new ones
    # arrive after the small registries are full.
    pool = sorted(
        {(rng.randrange(box.n), rng.randrange(box.n), rng.randrange(12)) for _ in range(500)}
    )
    pool += [(a, b, (d + 5) % 12) for a, b, d in pool[:50]]
    try:
        for step in range(400):
            lo = (step * len(pool)) // 400
            window = pool[max(0, lo - 40) : lo + 40]
            cands = [_candidate(rng, rng.choice(window)) for _ in range(rng.randint(0, 30))]
            fired = rng.randrange(-1, len(cands)) if cands else -1
            dt = rng.randint(1, 8) / 8.0
            _account(lib, ctx, box.lat, cands, fired, dt)
            ref.account(cands, fired, dt, box.cells)
            if step % 50 == 49 or step == 399:
                assert _registry(lib, ctx) == ref.flags, f"registry differs after step {step}"
        assert lib.pylatkmc_test_n_surr_fired(ctx) == ref.n_surr_fired
    finally:
        lib.pylatkmc_test_ctx_free(ctx)
        box.close()
    if capacity > 0:
        assert len(ref.flags) == capacity  # the registry filled: later keys were dropped
    else:
        assert len(ref.flags) > 64


def test_flag_lookup_compares_o1_keys(registry_lib) -> None:
    """A lookup compares O(1) registry keys, hit or miss, at the registry's
    maximum load (full): the pre-fix linear scan compares O(n_flags)."""
    lib = registry_lib
    rng = random.Random(11)
    box = _Box(lib, SLAB, rng)
    cmps = ctypes.c_long.in_dll(lib, "pylatkmc_test_flag_key_cmps")
    cap = 4096
    ctx = lib.pylatkmc_test_ctx_new(cap, 0.01)
    assert ctx
    pairs = [(rng.randrange(box.n), rng.randrange(box.n), rng.randrange(12)) for _ in range(6000)]
    keys = sorted({(min(a, b), max(a, b), d) for a, b, d in pairs})  # registry keys
    rng.shuffle(keys)
    stored, extra = keys[:cap], keys[cap : cap + 1024]
    assert len(extra) == 1024

    def run(stream: list[tuple[int, int, int]]) -> float:
        cmps.value = 0
        for i in range(0, len(stream), 64):
            _account(lib, ctx, box.lat, [_candidate(rng, k) for k in stream[i : i + 64]], -1, 0.5)
        return cmps.value / len(stream)

    try:
        run(stored)  # fill the registry to capacity
        assert lib.pylatkmc_test_n_flags(ctx) == cap
        hits = run([rng.choice(stored) for _ in range(8192)])
        misses = run(extra)  # registry full: every new key probes, then is dropped
        assert lib.pylatkmc_test_n_flags(ctx) == cap
    finally:
        lib.pylatkmc_test_ctx_free(ctx)
        box.close()
    assert hits <= 3.0, f"{hits:.1f} key comparisons per hit (linear scan: ~{cap // 2})"
    assert misses <= 4.0, f"{misses:.1f} key comparisons per miss (linear scan: {cap})"
