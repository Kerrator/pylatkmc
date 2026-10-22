"""Regression tests for the generated v2 matcher (large-system-scaling WP2).

- 08: ``touchup_a`` matches each unique (pattern, op) ONCE per anchor and, on
  a match, enrols every member proc of it. It used to loop over procs, so a
  pattern with n harvested members was re-matched n times per op.
- 09: ``v2_match`` no longer rotates and wraps every row through
  ``lattice_site_at_ijk``: ``touchup_a`` gathers the anchor's context-ball
  species once per op and the rows index that local array. The enrolment
  must stay exactly what the per-row semantics give (context EMPTY = vacant
  or absent, OCC_ANY = any real species, delta rows strict), across the
  periodic wrap and the stub cells, with each proc's site order unchanged.

The emitted proclist.c is compiled with the real avail_sites.c and checked
against a pure-Python reference of the per-row semantics, through ctypes.
Each test skips cleanly without cc.
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

from pylatkmc.codegen import _PROCLIST_C_PREAMBLE
from pylatkmc.pattern_codegen import (
    _proc_list,
    emit_pattern_tables,
    emit_v2_enum,
    emit_v2_rate_table,
)
from pylatkmc.translator_v2 import (
    CtxRow,
    DeltaRow,
    LatticePattern,
    MemberRate,
    d4h_matrices,
)

pytest.importorskip("numpy")  # the D4h ops come from pylatkmc.ingest.lattice

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"

_SP = {"Vacant": 0, "Ni": 1, "Fe": 2, "Cr": 3}
_STUB = 255


def _pat(name, anchor, delta, ctx, ops, n_members):
    return LatticePattern(
        class_id=name,
        name=name,
        anchor_species=anchor,
        delta=tuple(DeltaRow(off, b, a) for off, b, a in delta),
        context=tuple(CtxRow(off, kind, sp) for off, kind, sp in ctx),
        orientation_ops=ops,
        prefactor_Hz=1.0e13,
        Ea_eV=0.5,
        mover_species=("Ni",),
        n_members=n_members,
        depth_kind=0,
        depth_param=0,
        members=tuple(MemberRate(1.0e13, 0.5 + 0.01 * m, float("nan")) for m in range(n_members)),
    )


#: Multi-member patterns on two anchor species, a 3-row delta, every predicate
#: kind, offsets reaching across the test grid's periodic wrap.
PATTERNS = [
    _pat(
        "v2_a",
        "Vacant",
        [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Vacant")],
        [
            ((-2, 0, 0), "EMPTY", None),
            ((4, 0, 0), "SPECIES", "Fe"),
            ((0, 2, 2), "OCC_ANY", None),
            ((-4, 2, 0), "SPECIES", "Ni"),
        ],
        (0, 2, 5, 9, 14),
        3,
    ),
    _pat(
        "v2_b",
        "Vacant",
        [((0, 0, 0), "Vacant", "Fe"), ((1, 1, 1), "Fe", "Vacant")],
        [
            ((-1, -1, -1), "SPECIES", "Ni"),
            ((1, 1, 3), "EMPTY", None),
            ((3, 3, 1), "OCC_ANY", None),
            ((-3, 1, 1), "SPECIES", "Fe"),
        ],
        (0, 1, 7, 8, 13),
        2,
    ),
    _pat(
        "v2_c",
        "Ni",
        [((0, 0, 0), "Ni", "Cr"), ((0, 2, 0), "Cr", "Ni")],
        [((2, 2, 0), "SPECIES", "Cr"), ((-2, 0, 0), "OCC_ANY", None)],
        (0, 4, 10),
        1,
    ),
    _pat(
        "v2_d",
        "Vacant",
        [((0, 0, 0), "Vacant", "Ni"), ((2, 0, 0), "Ni", "Cr"), ((4, 0, 0), "Cr", "Vacant")],
        [((2, 2, 0), "EMPTY", None)],
        tuple(range(16)),
        1,
    ),
]

#: Same-parity runtime cells of an 8 x 8 x 4 block; the helper pads the grid by
#: MARGIN cells per axis (10 x 10 x 6), so offsets up to 4 both hit stub cells
#: and wrap round onto the far side of the block.
CELLS = [
    (u, v, w)
    for u in range(8)
    for v in range(8)
    for w in range(4)
    if (u - v) % 2 == 0 and (v - w) % 2 == 0
]
MARGIN = 1


def _proclist_c(patterns: list[LatticePattern]) -> str:
    """A complete proclist.c, with a v2_match call counter for ticket 08."""
    pre = _PROCLIST_C_PREAMBLE.format(spec_name="t", temperature_K=500.0, k0_Hz=1e13)
    body = (
        emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + emit_pattern_tables(patterns)
    )
    body, n = re.subn(
        r"(static int v2_match\([^)]*\)\s*\{)",
        r"static long g_v2_match_calls;\n\1\n    ++g_v2_match_calls;",
        body,
        count=1,
    )
    assert n == 1, "emitted proclist.c has no v2_match function"
    hook = """
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;

long pylatkmc_test_v2_match_calls(void)
{
    long c = g_v2_match_calls;
    g_v2_match_calls = 0;
    return c;
}
"""
    return pre + body + hook


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    tmp = tmp_path_factory.mktemp("v2matcher")
    src = tmp / "proclist.c"
    src.write_text(_proclist_c(PATTERNS))
    so = tmp / ("libv2matcher.dylib" if sys.platform == "darwin" else "libv2matcher.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(CORE), str(src), str(CORE / "avail_sites.c")]
    cmd += [str(CORE / "state_actions.c"), str(HELPERS_SRC), "-o", str(so), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        pytest.fail(f"generated v2 proclist.c failed to build:\n{res.stderr}")
    lib = ctypes.CDLL(str(so))
    i32p = ctypes.POINTER(ctypes.c_int32)
    vp = ctypes.c_void_p
    lib.pylatkmc_test_make_lattice_grid.argtypes = [
        ctypes.c_int32,
        i32p,
        ctypes.c_int32,
        i32p,
        i32p,
    ]
    lib.pylatkmc_test_make_lattice_grid.restype = vp
    lib.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        i32p,
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_make_state.restype = vp
    lib.pylatkmc_test_free_lattice.argtypes = [vp]
    lib.pylatkmc_test_free_state.argtypes = [vp]
    lib.avail_sites_alloc.argtypes = [ctypes.POINTER(vp), ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_alloc.restype = ctypes.c_int
    lib.avail_sites_free.argtypes = [vp]
    lib.avail_sites_count.argtypes = [vp, ctypes.c_int32]
    lib.avail_sites_count.restype = ctypes.c_int32
    lib.avail_sites_site_at.argtypes = [vp, ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_site_at.restype = ctypes.c_int32
    lib.touchup_a.argtypes = [vp, vp, vp, ctypes.c_int]
    lib.touchup_a.restype = None
    lib.pylatkmc_test_v2_match_calls.restype = ctypes.c_long
    return lib


class _Grid:
    """Python mirror of pylatkmc_test_make_lattice_grid's site grid."""

    def __init__(self, cells: list[tuple[int, int, int]], margin: int) -> None:
        o = cells[0]
        self.rel = [(c[0] - o[0], c[1] - o[1], c[2] - o[2]) for c in cells]
        self.dims = [
            max(c[a] for c in cells) - min(c[a] for c in cells) + 1 + 2 * margin for a in range(3)
        ]
        self.n = len(cells)
        self.at = {self._wrap(r): s for s, r in enumerate(self.rel)}

    def _wrap(self, x: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(x[a] % self.dims[a] for a in range(3))  # == ((x % n) + n) % n

    def lookup(self, site: int, off: tuple[int, int, int]) -> tuple[int, bool]:
        """(site index or the stub n, whether the offset wrapped)."""
        raw = tuple(self.rel[site][a] + off[a] for a in range(3))
        w = self._wrap(raw)
        return self.at.get(w, self.n), w != raw


def _rot(m, off):
    return tuple(m[r][0] * off[0] + m[r][1] * off[1] + m[r][2] * off[2] for r in range(3))


def _reference(grid: _Grid, species: list[int]) -> tuple[list[list[int]], dict[str, int]]:
    """Per-row reference semantics: per-proc site lists (touchup order 0..n-1)."""
    sp = species + [_STUB]
    mats = d4h_matrices()
    _order, procs = _proc_list(PATTERNS)
    out: list[list[int]] = [[] for _ in procs]
    seen = {"match": 0, "miss": 0, "stub_in_match": 0, "wrap_in_match": 0}
    for site in range(grid.n):
        for p, (_t, op, _m, pi) in enumerate(procs):
            pat = PATTERNS[pi]
            if sp[site] != _SP[pat.anchor_species]:
                continue
            ok, stub, wrapped = True, False, False
            for r in pat.delta:
                s, w = grid.lookup(site, _rot(mats[op], r.off))
                wrapped |= w
                ok &= sp[s] == _SP[r.before]
            for c in pat.context:
                s, w = grid.lookup(site, _rot(mats[op], c.off))
                wrapped |= w
                stub |= s == grid.n
                v = sp[s]
                if c.kind == "EMPTY":
                    ok &= v in (_SP["Vacant"], _STUB)
                elif c.kind == "OCC_ANY":
                    ok &= v not in (_SP["Vacant"], _STUB)
                else:
                    ok &= v == _SP[c.species]
            if ok:
                out[p].append(site)
                seen["match"] += 1
                seen["stub_in_match"] += stub
                seen["wrap_in_match"] += wrapped
            else:
                seen["miss"] += 1
    return out, seen


def _touchup_all(lib: ctypes.CDLL, species: list[int], sites: list[int]) -> list[list[int]]:
    """Run the generated touchup_a over ``sites`` in order; per-proc site lists."""
    n = len(CELLS)
    flat = (ctypes.c_int32 * (3 * n))(*[c for cell in CELLS for c in cell])
    lat = lib.pylatkmc_test_make_lattice_grid(n, flat, MARGIN, None, None)
    vac = [s for s in range(n) if species[s] == _SP["Vacant"]]
    st = lib.pylatkmc_test_make_state(
        n,
        max(1, len(vac)),
        len(vac),
        (ctypes.c_int32 * max(1, len(vac)))(*vac),
        (ctypes.c_uint8 * n)(*species),
    )
    as_ = ctypes.c_void_p()
    n_procs = len(_proc_list(PATTERNS)[1])
    assert lat and st and lib.avail_sites_alloc(ctypes.byref(as_), n_procs, n) == 0
    try:
        for s in sites:
            lib.touchup_a(lat, st, as_, s)
        return [
            [lib.avail_sites_site_at(as_, p, k) for k in range(lib.avail_sites_count(as_, p))]
            for p in range(n_procs)
        ]
    finally:
        lib.avail_sites_free(as_)
        lib.pylatkmc_test_free_state(st)
        lib.pylatkmc_test_free_lattice(lat)


# ---------------------------------------------------------------------------
# 08: one match per unique (pattern, op); every member proc enrolled
# ---------------------------------------------------------------------------


def test_touchup_matches_each_pattern_op_once(lib: ctypes.CDLL) -> None:
    _order, procs = _proc_list(PATTERNS)
    for anchor in ("Vacant", "Ni"):
        n_patops = sum(len(p.orientation_ops) for p in PATTERNS if p.anchor_species == anchor)
        n_bucket = sum(1 for (_t, _op, _m, pi) in procs if PATTERNS[pi].anchor_species == anchor)
        species = [_SP["Fe"]] * len(CELLS)
        species[0] = _SP[anchor]
        lib.pylatkmc_test_v2_match_calls()  # reset
        _touchup_all(lib, species, [0])
        calls = lib.pylatkmc_test_v2_match_calls()
        assert calls == n_patops, (
            f"{anchor}-anchored site: {calls} v2_match calls for {n_patops} unique "
            f"(pattern, op) entries ({n_bucket} procs): a (pattern, op) is re-matched per member"
        )
    # A site with no anchored pattern is never matched at all.
    lib.pylatkmc_test_v2_match_calls()
    _touchup_all(lib, [_SP["Cr"]] * len(CELLS), [0])
    assert lib.pylatkmc_test_v2_match_calls() == 0


def test_one_match_enrols_every_member_proc(lib: ctypes.CDLL) -> None:
    """Paint v2_a (3 members) at op 0 around site 0; all 3 procs enrol, nothing else."""
    grid = _Grid(CELLS, MARGIN)
    species = [_SP["Cr"]] * len(CELLS)
    want = {(0, 0, 0): "Vacant", (2, 0, 0): "Ni", (4, 0, 0): "Fe", (0, 2, 2): "Ni"}
    want[(-4, 2, 0)] = "Ni"
    for off, name in want.items():
        s, _w = grid.lookup(0, off)
        assert s < grid.n
        species[s] = _SP[name]
    s, _w = grid.lookup(0, (-2, 0, 0))
    if s < grid.n:
        species[s] = _SP["Vacant"]
    ref, _seen = _reference(grid, species)
    _order, procs = _proc_list(PATTERNS)
    a = next(i for i, p in enumerate(PATTERNS) if p.name == "v2_a")
    members = [p for p, (_t, op, _m, pi) in enumerate(procs) if pi == a and op == 0]
    assert len(members) == 3
    assert all(0 in ref[p] for p in members)
    got = _touchup_all(lib, species, [0])
    assert got == [[0] if 0 in ref[p] else [] for p in range(len(procs))]
    assert all(got[p] == [0] for p in members)


# ---------------------------------------------------------------------------
# 09: gathered-ball matching == per-row rotate-and-wrap semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_touchup_enrolment_equals_per_row_reference(lib: ctypes.CDLL, seed: int) -> None:
    """Every (proc, site) pair and every proc's site order match the per-row
    reference on random configurations of a small grid whose pattern offsets
    hit stub cells and wrap round the periodic axes."""
    rng = random.Random(seed)
    grid = _Grid(CELLS, MARGIN)
    weights = [0.3, 0.3, 0.2, 0.2]  # Vacant, Ni, Fe, Cr
    species = rng.choices(range(4), weights=weights, k=len(CELLS))
    ref, seen = _reference(grid, species)
    assert seen["match"] > 0 and seen["miss"] > 0
    order = list(range(len(CELLS)))
    assert _touchup_all(lib, species, order) == ref
    # The site order of each proc is the touchup call order, whatever it is.
    rng.shuffle(order)
    rank = {s: i for i, s in enumerate(order)}
    shuffled = [sorted(sites, key=rank.__getitem__) for sites in ref]
    assert _touchup_all(lib, species, order) == shuffled


def test_reference_configurations_exercise_stub_and_wrap() -> None:
    """The random configurations above do match through stub cells and wrapped
    offsets (otherwise the equivalence test would not cover them)."""
    grid = _Grid(CELLS, MARGIN)
    stub = wrap = 0
    for seed in range(12):
        species = random.Random(seed).choices(range(4), weights=[0.3, 0.3, 0.2, 0.2], k=len(CELLS))
        _ref, seen = _reference(grid, species)
        stub += seen["stub_in_match"]
        wrap += seen["wrap_in_match"]
    assert stub > 0 and wrap > 0


def _function_body(src: str, signature: str) -> str:
    """The text of the function DEFINED with ``signature`` at column 0."""
    start = src.index("\n" + signature) + 1
    return src[start : src.index("\n}\n", start)]


def test_matcher_does_not_rotate_or_wrap_per_row() -> None:
    """The emitted matcher reads the gathered ball: no 3x3 rotation and no
    lattice_site_at_ijk per row, in fresh emission and in every committed v2
    proclist.c (CI links those without regenerating them)."""
    sources = {"emitted": emit_pattern_tables(PATTERNS)}
    for path in sorted((REPO_ROOT / "models").glob("*/generated/proclist.c")):
        text = path.read_text()
        if "static const V2Pattern v2_patterns" in text:
            sources[str(path.relative_to(REPO_ROOT))] = text
    assert len(sources) > 1, "no committed v2 proclist.c found"
    for where, src in sources.items():
        match = _function_body(src, "static int v2_match(")
        touchup = _function_body(src, "void touchup_a(const Lattice *lat")
        for body in (match, touchup):
            assert "lattice_site_at_ijk(" not in body, f"{where}: per-row grid lookup"
            assert "V2_OPS[" not in body, f"{where}: per-row rotation"
        assert "v2_ball_off[" in touchup and "v2_patops[" in touchup, where
