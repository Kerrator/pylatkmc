"""Regression tests for the generated v2 matcher (large-system-scaling/08, 09).

- 08: ``touchup_a`` matches each (pattern, op) once per anchor, however many
  harvested members (procs) share it, and a match enrols every member proc.
  The matcher ``v2_match_ops`` tests one pattern under all of its ops at once,
  so an anchored ``touchup_a`` call makes exactly one matcher evaluation per
  pattern of the anchor species' bucket, with one member per pattern or many.
- 09: ``touchup_a`` resolves each site of the pattern ball (``v2_ball``: every
  row offset under every D4h op) once per anchor, instead of rotating and
  wrapping every row of every (pattern, member, op) through
  ``lattice_site_at_ijk``.
- Both are pure speed-ups, so enrolment must not change: the exact
  ``avail_sites_add`` call sequence, for the site order 0..n-1 and for a
  shuffled one, equals a reference built from the per-proc matcher semantics
  (rotate each row, resolve it through the site grid; delta rows need the
  exact before-state, context ``EMPTY`` = vacant OR absent, ``OCC_ANY`` = any
  occupied). That holds on a periodic slab with vacuum (both surfaces, the
  periodic seams, every site an anchor; the matches read stub cells and cross
  the seams) and on a box smaller than the pattern reach, where offsets alias.

The generated proclist.c is compiled behind a test prelude that counts the grid
lookups and the matcher evaluations of the generated code and logs every
``avail_sites_add`` call. ctypes level, no MPI; skips without cc (or numpy,
which the D4h ops import).
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

SP = {"Vacant": 0, "Ni": 1, "Fe": 2, "Cr": 3}  # events_base.h
STUB = 255  # species[n_sites]: the absent-site sentinel

# Runtime frame: tetragonal grid (nn/2, nn/2, nn/sqrt2), sites on the
# same-parity sublattice.
NN = 2.5
HX, HZ = NN / 2.0, NN / math.sqrt(2.0)


class Geometry(NamedTuple):
    nx: int  # in-plane grid planes (periodic)
    ny: int
    n_layers: int  # atomic layers, under ...
    n_vacuum: int  # ... this many empty grid planes (the k axis wraps too)


#: 10 x 10 in-plane grid planes and 5 layers under 4 vacuum planes: at or above
#: 2 * reach + 1 on every axis for the patterns below (reach 4 in-plane, 2 in k).
SLAB = Geometry(10, 10, 5, 4)
#: 6 x 6 x 4 grid planes, below 2 * reach + 1 on every axis: offsets alias (the
#: runtime refuses such a box at startup, but the matcher must still be exact).
ALIAS_BOX = Geometry(6, 6, 3, 1)

# The generated code's grid lookups are counted and its enrolments logged.
# lattice.h is include-guarded, so the generated `#include "lattice.h"` after
# this prelude is a no-op and every lattice_site_at_ijk call in proclist.c goes
# through the counter. _build instruments the matcher with the evaluation
# counter.
_PRELUDE = r"""
#include "lattice.h"
#include "avail_sites.h"

long pylatkmc_test_lookups;
long pylatkmc_test_match_evals;
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

#: The generated matcher, whose evaluations _build counts.
_MATCHER = re.compile(r"(static uint32_t v2_match_ops\([^)]*\)\n\{\n)")


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
    """Compile the patterns' generated proclist.c (behind the test prelude,
    with the matcher counting its evaluations) with the real site-grid
    builder into a shared library."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    from pylatkmc.codegen import _PROCLIST_C_PREAMBLE
    from pylatkmc.pattern_codegen import emit_pattern_tables, emit_v2_enum, emit_v2_rate_table

    tables, n_matchers = _MATCHER.subn(
        r"\1    ++pylatkmc_test_match_evals;\n", emit_pattern_tables(patterns)
    )
    if n_matchers != 1:
        pytest.fail("the emitted proclist.c has no v2_match_ops matcher to count")
    src = tmp / f"{name}.c"
    src.write_text(
        _PRELUDE
        + _PROCLIST_C_PREAMBLE.format(spec_name=name, temperature_K=500.0, k0_Hz=1e13)
        + emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + tables
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


class Run(NamedTuple):
    log: list[tuple[int, int]]  # every avail_sites_add call: (proc, site)
    lookups: list[int]  # grid lookups per touchup_a call
    evals: list[int]  # matcher evaluations per touchup_a call


class _Slab:
    """One built library + a slab lattice of ``geom`` (site grid from lattice.c)."""

    def __init__(self, lib: ctypes.CDLL, patterns: list, geom: Geometry) -> None:
        self.lib, self.patterns = lib, patterns
        self.dims = (geom.nx, geom.ny, geom.n_layers + geom.n_vacuum)  # grid planes
        self.cells = [
            (u, v, w)
            for w in range(geom.n_layers)
            for u in range(geom.nx)
            for v in range(geom.ny)
            if (u - v) % 2 == 0 and (v - w) % 2 == 0
        ]  # site 0 at cell (0, 0, 0), so site_ijk == cell
        n = self.n = len(self.cells)
        pos = [c for (u, v, w) in self.cells for c in (u * HX, v * HX, w * HZ)]
        cell = (geom.nx * HX, geom.ny * HX, self.dims[2] * HZ)
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

    def crosses_seam(self, site: int, off: tuple[int, int, int]) -> bool:
        """Whether site + off leaves the grid box, i.e. wraps a periodic axis."""
        return any(not 0 <= self.cells[site][a] + off[a] < self.dims[a] for a in range(3))

    def touchup(self, species: list[int], sites) -> Run:
        """Run touchup_a over ``sites`` in that order."""
        lib = self.lib
        st = lib.pylatkmc_test_make_state(self.n, 1, 0, None, (ctypes.c_uint8 * self.n)(*species))
        assert st
        lookups = ctypes.c_long.in_dll(lib, "pylatkmc_test_lookups")
        evals = ctypes.c_long.in_dll(lib, "pylatkmc_test_match_evals")
        n_log = ctypes.c_long.in_dll(lib, "pylatkmc_test_n_log")
        n_log.value = 0
        per_lookups, per_evals = [], []
        try:
            for s in sites:
                lookups.value = evals.value = 0
                lib.touchup_a(self.lat, st, None, s)
                per_lookups.append(lookups.value)
                per_evals.append(evals.value)
        finally:
            lib.pylatkmc_test_free_state(st)
        raw = (ctypes.c_int32 * (2 * n_log.value)).in_dll(lib, "pylatkmc_test_log")
        log = [(raw[2 * i], raw[2 * i + 1]) for i in range(n_log.value)]
        return Run(log, per_lookups, per_evals)

    def close(self) -> None:
        self.lib.pylatkmc_test_free_lattice(self.lat)


@pytest.fixture(scope="module")
def slabs(tmp_path_factory: pytest.TempPathFactory):
    pytest.importorskip("numpy")  # D4h ops come from pylatkmc.ingest.lattice
    tmp = tmp_path_factory.mktemp("v2matcher")
    libs = {}
    for key, members in (("multi", MULTI), ("single", SINGLE)):
        patterns = _patterns(members)
        libs[key] = (_build(tmp, f"v2m_{key}", patterns), patterns)
    built = {
        "multi": _Slab(*libs["multi"], SLAB),
        "single": _Slab(*libs["single"], SLAB),
        "alias": _Slab(*libs["multi"], ALIAS_BOX),  # the same library on a smaller box
    }
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


def _reference(slab: _Slab, species: list[int]) -> tuple[list[list[int]], Counter]:
    """The per-proc matcher, each row rotated and resolved alone.

    Returns ``(matches, coverage)``: ``matches[s]`` lists the procs that match
    at site ``s`` in id order (the avail_sites_add sequence of a touchup over
    any site order is their concatenation in that order), and ``coverage``
    counts the matched (proc, site) pairs that read a stub cell and that read
    a real site across a periodic seam."""
    from pylatkmc.translator_v2 import d4h_matrices

    mats = d4h_matrices()
    procs = _proc_order(slab.patterns)
    spx = [*species, STUB]
    cache: dict[tuple[int, tuple[int, int, int]], int] = {}

    def at(site: int, op: int, off: tuple[int, int, int]) -> int:
        key = (site, _rotate(mats[op], off))
        if key not in cache:
            cache[key] = slab.resolve(*key)
        return cache[key]

    def ctx_ok(v: int, c) -> bool:
        if c.kind == "EMPTY":
            return v in (SP["Vacant"], STUB)
        if c.kind == "OCC_ANY":
            return v not in (SP["Vacant"], STUB)
        return v == SP[c.species]

    matches: list[list[int]] = [[] for _ in range(slab.n)]
    coverage: Counter = Counter()
    for s in range(slab.n):
        for pid, (p, op) in enumerate(procs):
            if SP[p.anchor_species] != species[s]:
                continue
            if all(spx[at(s, op, d.off)] == SP[d.before] for d in p.delta) and all(
                ctx_ok(spx[at(s, op, c.off)], c) for c in p.context
            ):
                matches[s].append(pid)
                rows = [r.off for r in (*p.delta, *p.context)]
                coverage["stub"] += any(at(s, op, o) == slab.n for o in rows)
                coverage["seam"] += any(
                    at(s, op, o) != slab.n and slab.crosses_seam(s, _rotate(mats[op], o))
                    for o in rows
                )
    return matches, coverage


def _log(matches: list[list[int]], order) -> list[tuple[int, int]]:
    return [(pid, s) for s in order for pid in matches[s]]


def _random_species(rng: random.Random, n: int) -> list[int]:
    return rng.choices([SP["Vacant"], SP["Ni"], SP["Cr"], SP["Fe"]], [3, 4, 2, 1], k=n)


def test_touchup_enrolment_matches_per_proc_reference(slabs) -> None:
    """Every enrolment, in call order, equals the per-proc matcher's: for the
    site order 0..n-1 and a shuffled one (each proc's site list follows the
    touchup call order), on a slab whose anchors include both surfaces and the
    periodic seams, and on a box smaller than the pattern reach."""
    from pylatkmc.pattern_codegen import ball_tables, pattern_reach

    rng = random.Random(20261022)
    fired: dict[str, set[str]] = {key: set() for key in slabs}
    coverage: dict[str, Counter] = {key: Counter() for key in slabs}
    for _trial in range(8):
        species_of_n: dict[int, list[int]] = {}
        for key, slab in slabs.items():
            if slab.n not in species_of_n:
                species_of_n[slab.n] = _random_species(rng, slab.n)
            species = species_of_n[slab.n]
            matches, cov = _reference(slab, species)
            order = list(range(slab.n))
            got = slab.touchup(species, order).log
            assert got == _log(matches, order), f"{key}: enrolment differs from the reference"
            rng.shuffle(order)
            got = slab.touchup(species, order).log
            assert got == _log(matches, order), f"{key}: shuffled-order enrolment differs"
            coverage[key].update(cov)
            procs = _proc_order(slab.patterns)
            fired[key].update(procs[pid][0].name for site in matches for pid in site)
    # The comparison is only as good as its matches: every pattern fired, and
    # matches read stub cells and real sites across a periodic seam.
    for key in slabs:
        assert fired[key] == set(MULTI), (key, fired[key])
        assert coverage[key]["stub"] > 0 and coverage[key]["seam"] > 0, (key, coverage[key])
    # The small box really aliases: it is below 2 * reach + 1 on every axis,
    # and distinct ball offsets resolve to one site.
    alias = slabs["alias"]
    reach_ij, reach_k = pattern_reach(alias.patterns)
    assert max(alias.dims[:2]) < 2 * reach_ij + 1 and alias.dims[2] < 2 * reach_k + 1
    ball_sites = [alias.resolve(0, off) for off in ball_tables(alias.patterns)[0]]
    real = [s for s in ball_sites if s != alias.n]
    assert len(set(real)) < len(real)


def test_each_pattern_is_matched_once_per_anchor_whatever_its_members(slabs) -> None:
    """08: a (pattern, op) is matched once per anchor, not once per member.

    v2_match_ops tests one pattern under all of its ops, so an anchored
    touchup_a call makes exactly one evaluation per pattern of the anchor
    species' bucket (none at a site whose species anchors no pattern), the
    same with 3/2/1/2 members per pattern as with one. Each matched (pattern,
    op, site) enrols all of its member procs, in id order, len(ops) apart."""
    rng = random.Random(8)
    multi, single = slabs["multi"], slabs["single"]
    procs_m, procs_s = _proc_order(multi.patterns), _proc_order(single.patterns)
    assert len(procs_m) > len(procs_s)  # the members multiply the procs ...
    n_bucket = Counter(SP[p.anchor_species] for p in multi.patterns)
    n_ops = {p.name: len(p.orientation_ops) for p in multi.patterns}
    n_hits = 0
    for _trial in range(4):
        species = _random_species(rng, multi.n)
        run_m = multi.touchup(species, range(multi.n))
        run_s = single.touchup(species, range(single.n))
        want = [n_bucket[sp] for sp in species]  # ... but not the matching
        assert run_m.evals == want, "a (pattern, op) is re-matched per member proc"
        assert run_s.evals == want
        assert run_m.lookups == run_s.lookups
        hits_s = sorted((procs_s[p][0].name, procs_s[p][1], s) for p, s in run_s.log)
        per_hit: dict[tuple[str, int, int], list[int]] = {}
        for p, s in run_m.log:
            per_hit.setdefault((procs_m[p][0].name, procs_m[p][1], s), []).append(p)
        assert sorted(per_hit) == hits_s
        for (name, _op, _s), pids in per_hit.items():
            assert pids == [pids[0] + m * n_ops[name] for m in range(MULTI[name])]
        n_hits += len(per_hit)
    assert n_hits > 0


def test_touchup_resolves_each_ball_site_once(slabs) -> None:
    """09: a touchup at an anchor makes exactly one grid lookup per distinct
    oriented row offset (the ball), however many (pattern, member, op) rows
    read it; a site whose species anchors no pattern makes none."""
    from pylatkmc.translator_v2 import d4h_matrices

    mats = d4h_matrices()
    slab = slabs["multi"]
    offsets = {r.off for p in slab.patterns for r in (*p.delta, *p.context)}
    n_ball = len({_rotate(m, o) for m in mats for o in offsets})
    n_rows = sum(len(p.delta) + len(p.context) for p in slab.patterns)
    n_row_ops = sum(
        len(p.members) * len(p.orientation_ops) * (len(p.delta) + len(p.context))
        for p in slab.patterns
    )
    assert n_ball < n_row_ops  # the per-row scan could cost more than the ball
    species = _random_species(random.Random(9), slab.n)
    lookups = slab.touchup(species, range(slab.n)).lookups
    for s, n in enumerate(lookups):
        anchors = species[s] in (SP["Vacant"], SP["Ni"])
        assert n == (n_ball if anchors else 0), (s, species[s], n, n_ball, n_rows)


def test_ball_tables_cover_every_oriented_row() -> None:
    """The ball is the keys (all canonical row offsets) followed by their other
    D4h images, sorted, and rot[k][g] is the ball index of op g applied to key
    k, so every oriented row offset is a ball site."""
    pytest.importorskip("numpy")
    from pylatkmc.pattern_codegen import ball_tables
    from pylatkmc.translator_v2 import d4h_matrices

    mats = d4h_matrices()
    patterns = _patterns(MULTI)
    ball, n_keys, rot = ball_tables(patterns)
    keys = sorted({r.off for p in patterns for r in (*p.delta, *p.context)})
    assert ball[:n_keys] == keys
    assert ball[n_keys:] == sorted(set(ball[n_keys:])) and not set(ball[n_keys:]) & set(keys)
    assert set(ball) == {_rotate(m, o) for m in mats for o in keys}
    assert all(
        ball[rot[k][g]] == _rotate(mats[g], keys[k]) for k in range(n_keys) for g in range(16)
    )


def test_committed_v2_proclists_use_the_ball_matcher() -> None:
    """CI links the committed proclists without regenerating them: every
    committed v2 proclist.c must carry the ball matcher, not the per-proc
    rotate-and-wrap scan."""
    v2 = [
        p
        for p in sorted((REPO_ROOT / "models").glob("*/generated/proclist.c"))
        if "V2Pattern" in p.read_text()
    ]
    assert v2
    for path in v2:
        text = path.read_text()
        assert "v2_ball_pass(lat, st, site, pass);" in text, f"{path}: regenerate it"
        assert _MATCHER.search(text), f"{path}: regenerate it"
        assert "v2_ctx_rows" not in text, f"{path}: regenerate it"
