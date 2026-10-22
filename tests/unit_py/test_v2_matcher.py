"""Regression tests for the generated v2 matcher (large-system-scaling/08).

- 08: ``touchup_a`` matches each (pattern, op) once per anchor, however many
  harvested members (procs) share it, and a match enrols every member proc.
- This is a pure speed-up, so enrolment must not change: on a periodic slab
  with vacuum (both surfaces, the periodic seams, every site an anchor) the
  exact ``avail_sites_add`` call sequence equals a reference built from the
  per-proc matcher semantics (rotate each row, resolve it through the site
  grid; delta rows need the exact before-state, context ``EMPTY`` = vacant OR
  absent, ``OCC_ANY`` = any occupied).

The generated proclist.c is compiled behind a test prelude that counts the grid
lookups of the generated code and logs every ``avail_sites_add`` call. ctypes
level, no MPI; skips without cc (or numpy, which the D4h ops import).
"""

from __future__ import annotations

import ctypes
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"

SP = {"Vacant": 0, "Ni": 1, "Fe": 2, "Cr": 3}  # events_base.h
STUB = 255  # species[n_sites]: the absent-site sentinel

# Slab geometry in the runtime frame: tetragonal grid (nn/2, nn/2, nn/sqrt2),
# sites on the same-parity sublattice. 10 x 10 in-plane grid planes (>= 2 *
# reach + 1 for the patterns below) and 5 atomic layers under 4 vacuum planes.
NN = 2.5
HX, HZ = NN / 2.0, NN / math.sqrt(2.0)
NX = NY = 10
N_LAYERS, N_VACUUM = 5, 4

# The generated code's grid lookups are counted and its enrolments logged.
# lattice.h is include-guarded, so the generated `#include "lattice.h"` after
# this prelude is a no-op and every lattice_site_at_ijk call in proclist.c goes
# through the counter.
_PRELUDE = r"""
#include "lattice.h"
#include "avail_sites.h"

long pylatkmc_test_lookups;
static inline int32_t test_counted_site_at_ijk(const Lattice *lat, int32_t i,
                                               int32_t j, int32_t k)
{
    ++pylatkmc_test_lookups;
    return lattice_site_at_ijk(lat, i, j, k);
}
#define lattice_site_at_ijk test_counted_site_at_ijk

#define TEST_LOG_CAP 200000
int32_t pylatkmc_test_log[2 * TEST_LOG_CAP];
long pylatkmc_test_n_log;
void avail_sites_add(AvailSites *as, int32_t proc, int32_t site)
{
    (void)as;
    if (pylatkmc_test_n_log < TEST_LOG_CAP) {
        pylatkmc_test_log[2 * pylatkmc_test_n_log] = proc;
        pylatkmc_test_log[2 * pylatkmc_test_n_log + 1] = site;
    }
    ++pylatkmc_test_n_log;
}
"""

_GLUE = """
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""


def _patterns(n_members: dict[str, int]) -> list:
    """Four hand-built runtime-frame patterns: an in-plane Ni hop, an
    interlayer Cr hop on a subset of the ops (with a strict SPECIES-Vacant
    context row), a concerted three-row chain, and a Ni-anchored pattern (a
    second species bucket). ``n_members`` sets each pattern's member count."""
    from pylatkmc.translator_v2 import CtxRow, DeltaRow, LatticePattern, MemberRate

    def pat(name, anchor, delta, context, ops, movers):
        members = tuple(
            MemberRate(1.0e13 * (m + 1), 0.4 + 0.05 * m, math.nan) for m in range(n_members[name])
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

    all_ops = tuple(range(16))
    return [
        pat(
            "p_ni_hop",
            "Vacant",
            [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Vacant")],
            [
                ((-2, 0, 0), "EMPTY", None),
                ((1, 1, 1), "OCC_ANY", None),
                ((1, -1, -1), "SPECIES", "Ni"),
                ((0, 2, 0), "SPECIES", "Cr"),
            ],
            all_ops,
            ("Ni",),
        ),
        pat(
            "p_cr_hop",
            "Vacant",
            [((0, 0, 0), "Vacant", "Cr"), ((1, 1, 1), "Cr", "Vacant")],
            [
                ((2, 0, 0), "EMPTY", None),
                ((-1, -1, 1), "SPECIES", "Ni"),
                ((0, 0, 2), "OCC_ANY", None),
                ((0, -2, 0), "SPECIES", "Vacant"),
            ],
            (0, 3, 5, 6, 9, 10, 12, 15),
            ("Cr",),
        ),
        pat(
            "p_chain",
            "Vacant",
            [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Cr"), ((4, 0, 0), "Cr", "Vacant")],
            [((-1, 1, 1), "EMPTY", None), ((3, 1, -1), "SPECIES", "Ni")],
            (0, 1, 2, 3),
            ("Ni", "Cr"),
        ),
        pat(
            "p_ni_anchor",
            "Ni",
            [((0, 0, 0), "Ni", "Vacant"), ((0, 2, 0), "Vacant", "Ni")],
            [((0, -2, 0), "SPECIES", "Ni"), ((1, 1, -1), "EMPTY", None)],
            all_ops,
            ("Ni",),
        ),
    ]


MULTI = {"p_ni_hop": 3, "p_cr_hop": 2, "p_chain": 1, "p_ni_anchor": 2}
SINGLE = dict.fromkeys(MULTI, 1)


def _build(tmp: Path, name: str, patterns: list) -> ctypes.CDLL:
    """Compile the patterns' generated proclist.c (behind the test prelude)
    with the real site-grid builder into a shared library."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    from pylatkmc.codegen import _PROCLIST_C_PREAMBLE
    from pylatkmc.pattern_codegen import emit_pattern_tables, emit_v2_enum, emit_v2_rate_table

    src = tmp / f"{name}.c"
    src.write_text(
        _PRELUDE
        + _PROCLIST_C_PREAMBLE.format(spec_name=name, temperature_K=500.0, k0_Hz=1e13)
        + emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + emit_pattern_tables(patterns)
        + _GLUE
    )
    lib = tmp / (f"lib{name}.dylib" if sys.platform == "darwin" else f"lib{name}.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2", "-fPIC"]
    cmd += ["-shared", "-I", str(CORE), str(src)]
    cmd += [str(CORE / f) for f in ("lattice.c", "coord_codes.c", "state_actions.c")]
    cmd += [str(HELPERS_SRC), "-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")
    dll = ctypes.CDLL(str(lib))
    i32p, f32p = ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_float)
    dll.pylatkmc_test_make_lattice_full.restype = ctypes.c_void_p
    dll.pylatkmc_test_make_lattice_full.argtypes = [
        ctypes.c_int32,
        f32p,
        f32p,
        ctypes.c_float,
        i32p,
        i32p,
        i32p,
        i32p,
    ]
    dll.lattice_build_site_grid.restype = ctypes.c_int
    dll.lattice_build_site_grid.argtypes = [ctypes.c_void_p]
    dll.pylatkmc_test_make_state.restype = ctypes.c_void_p
    dll.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        i32p,
        ctypes.POINTER(ctypes.c_uint8),
    ]
    dll.pylatkmc_test_resolve_offset.restype = ctypes.c_int32
    dll.pylatkmc_test_resolve_offset.argtypes = [ctypes.c_void_p] + [ctypes.c_int32] * 4
    dll.touchup_a.restype = None
    dll.touchup_a.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    dll.pylatkmc_test_free_lattice.argtypes = [ctypes.c_void_p]
    dll.pylatkmc_test_free_state.argtypes = [ctypes.c_void_p]
    return dll


class _Slab:
    """One built library + its slab lattice (site grid from lattice.c)."""

    def __init__(self, lib: ctypes.CDLL, patterns: list) -> None:
        self.lib, self.patterns = lib, patterns
        self.cells = [
            (u, v, w)
            for w in range(N_LAYERS)
            for u in range(NX)
            for v in range(NY)
            if (u - v) % 2 == 0 and (v - w) % 2 == 0
        ]  # site 0 at cell (0, 0, 0)
        n = self.n = len(self.cells)
        pos = [c for (u, v, w) in self.cells for c in (u * HX, v * HX, w * HZ)]
        cell = (NX * HX, NY * HX, (N_LAYERS + N_VACUUM) * HZ)
        self.lat = lib.pylatkmc_test_make_lattice_full(
            n,
            (ctypes.c_float * (3 * n))(*pos),
            (ctypes.c_float * 3)(*cell),
            NN,
            (ctypes.c_int32 * (n + 1))(),  # no CSR edges: the matcher needs none
            (ctypes.c_int32 * 1)(),
            None,
            None,
        )
        assert self.lat
        assert lib.lattice_build_site_grid(self.lat) == 0

    def resolve(self, site: int, off: tuple[int, int, int]) -> int:
        return self.lib.pylatkmc_test_resolve_offset(self.lat, site, *off)

    def touchup(self, species: list[int], sites) -> tuple[list[tuple[int, int]], list[int]]:
        """Run touchup_a over ``sites`` -> (enrolment log, lookups per call)."""
        lib = self.lib
        st = lib.pylatkmc_test_make_state(self.n, 1, 0, None, (ctypes.c_uint8 * self.n)(*species))
        assert st
        lookups = ctypes.c_long.in_dll(lib, "pylatkmc_test_lookups")
        n_log = ctypes.c_long.in_dll(lib, "pylatkmc_test_n_log")
        n_log.value = 0
        per_call = []
        try:
            for s in sites:
                lookups.value = 0
                lib.touchup_a(self.lat, st, None, s)
                per_call.append(lookups.value)
        finally:
            lib.pylatkmc_test_free_state(st)
        raw = (ctypes.c_int32 * (2 * n_log.value)).in_dll(lib, "pylatkmc_test_log")
        return [(raw[2 * i], raw[2 * i + 1]) for i in range(n_log.value)], per_call

    def close(self) -> None:
        self.lib.pylatkmc_test_free_lattice(self.lat)


@pytest.fixture(scope="module")
def slabs(tmp_path_factory: pytest.TempPathFactory):
    pytest.importorskip("numpy")  # D4h ops come from pylatkmc.ingest.lattice
    tmp = tmp_path_factory.mktemp("v2matcher")
    built = {}
    for key, members in (("multi", MULTI), ("single", SINGLE)):
        patterns = _patterns(members)
        built[key] = _Slab(_build(tmp, f"v2m_{key}", patterns), patterns)
    yield built
    for slab in built.values():
        slab.close()


def _rotate(m, off):
    return tuple(sum(m[r][c] * off[c] for c in range(3)) for r in range(3))


def _proc_order(patterns: list) -> list[tuple[object, int]]:
    """(pattern, op) per proc id: patterns by (anchor species code, name),
    then member-major, then orientation (the rate-table order)."""
    order = sorted(patterns, key=lambda p: (SP[p.anchor_species], p.name))
    return [(p, op) for p in order for _m in p.members for op in p.orientation_ops]


def _reference_log(slab: _Slab, species: list[int]) -> list[tuple[int, int]]:
    """avail_sites_add sequence of the per-proc matcher: for every site, every
    proc of the site species' bucket, each row rotated and resolved alone."""
    from pylatkmc.translator_v2 import d4h_matrices

    mats = d4h_matrices()
    procs = _proc_order(slab.patterns)
    spx = [*species, STUB]
    cache: dict[tuple[int, tuple[int, int, int]], int] = {}

    def at(site: int, op: int, off: tuple[int, int, int]) -> int:
        key = (site, _rotate(mats[op], off))
        if key not in cache:
            cache[key] = slab.resolve(*key)
        return spx[cache[key]]

    def ctx_ok(v: int, c) -> bool:
        if c.kind == "EMPTY":
            return v in (SP["Vacant"], STUB)
        if c.kind == "OCC_ANY":
            return v not in (SP["Vacant"], STUB)
        return v == SP[c.species]

    log = []
    for s in range(slab.n):
        for pid, (p, op) in enumerate(procs):
            if SP[p.anchor_species] != species[s]:
                continue
            if all(at(s, op, d.off) == SP[d.before] for d in p.delta) and all(
                ctx_ok(at(s, op, c.off), c) for c in p.context
            ):
                log.append((pid, s))
    return log


def _random_species(rng: random.Random, n: int) -> list[int]:
    return rng.choices([SP["Vacant"], SP["Ni"], SP["Cr"], SP["Fe"]], [3, 4, 2, 1], k=n)


def test_touchup_enrolment_matches_per_proc_reference(slabs) -> None:
    """Every enrolment, in call order, equals the per-proc matcher's, on a slab
    whose anchors include both surfaces and the periodic seams."""
    rng = random.Random(20261022)
    matched: dict[str, set[str]] = {key: set() for key in slabs}
    for _trial in range(8):
        species = _random_species(rng, slabs["multi"].n)
        for key, slab in slabs.items():
            got, _ = slab.touchup(species, range(slab.n))
            want = _reference_log(slab, species)
            assert got == want, f"{key}: touchup_a enrolment differs from the per-proc matcher"
            procs = _proc_order(slab.patterns)
            matched[key].update(procs[pid][0].name for pid, _s in want)
    # The comparison is only as good as its matches: every pattern fired.
    for key in slabs:
        assert matched[key] == set(MULTI), matched[key]


def test_matched_pattern_op_enrols_every_member_with_member_independent_work(slabs) -> None:
    """08: a (pattern, op) is matched once per anchor, whatever its member count.
    The grid lookups of a touchup do not grow with the members, and each match
    enrols all of its member procs (members sit len(ops) apart in proc order)."""
    rng = random.Random(8)
    multi, single = slabs["multi"], slabs["single"]
    procs_m, procs_s = _proc_order(multi.patterns), _proc_order(single.patterns)
    for _trial in range(4):
        species = _random_species(rng, multi.n)
        log_m, lookups_m = multi.touchup(species, range(multi.n))
        log_s, lookups_s = single.touchup(species, range(single.n))
        assert lookups_m == lookups_s  # per touchup_a call, member-independent
        hits_s = sorted((procs_s[p][0].name, procs_s[p][1], s) for p, s in log_s)
        per_hit: dict[tuple[str, int, int], list[int]] = {}
        for p, s in log_m:
            per_hit.setdefault((procs_m[p][0].name, procs_m[p][1], s), []).append(p)
        assert sorted(per_hit) == hits_s
        for (name, _op, _s), pids in per_hit.items():
            assert len(pids) == MULTI[name] and pids == sorted(pids)
