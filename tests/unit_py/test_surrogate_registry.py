"""Regression tests for the Phase C flag registry (large-system-scaling/11).

surrogate_account looks every live surrogate candidate (and the fired one) up
in the flag registry, keyed on (min(site), max(site), dir_idx). The lookup
used to scan the registry linearly (``flag_registry_capacity`` defaults to
65536), so a long run with a full registry paid n_cand x n_flags comparisons
per step. It now goes through an open-addressing index beside the array. The
array (registry index = first-seen order), the silent cap at capacity and
every per-flag field are what the linear scan produced, so
``flag_registry.csv``, which replica.c writes from the array (sorted by
``carried_flux * max(n_fired, 1)``, ties by key), is unchanged too.

- The registry equals a model of the linear-scan semantics, field for field
  and in index order, after every step of random schedules with repeated,
  reversed and same-pair keys that recur, retire and arrive after the small
  registries are full (new keys dropped, registered keys still accounted), at
  capacities 1, 64, 4096 and the default; ``n_surr_fired`` too. k and dt are
  dyadic, so every flux sum is exact whether or not the compiler fuses the
  multiply-add.
- A lookup compares O(1) registry keys, hit or miss, on a full registry:
  counted by instrumenting the key comparison in a test copy of surrogate.c
  (the pre-fix scan compares about n_flags / 2 per hit, n_flags per miss).
- The default 65536-flag registry, filled, then 50000 steps of 128
  candidates (half registered keys, half new keys it drops): every flag's
  key, n_enrolled_steps and n_fired are checked in C, and the comparison
  count stays O(1) per lookup. A short run is counted first, so a linear scan
  fails in seconds instead of running for minutes.

ctypes level, no MPI; skips without cc.
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
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"
SHIM_SRC = Path(__file__).parent / "_surrogate_registry_shim.c"

SURR_TRIG_FLUX = 0x4  # surrogate.h
DEFAULT_CAPACITY = 65536  # surrogate_ctx_init's default
N_SITES = 64

#: The registry key comparison in flag_lookup, counted in the test copy of
#: surrogate.c (the pre-fix linear scan has the same comparison).
_KEY_CMP = re.compile(r"\b(\w+)->site_a == lo\b")

_INT_FIELDS = (
    "site_a",
    "site_b",
    "dir_idx",
    "used",
    "n_enrolled_steps",
    "n_fired",
    "first_step",
    "trigger_or",
    "ru",
    "rv",
    "rw",
    "sp_a",
    "sp_b",
)
_FLOAT_FIELDS = ("carried_flux", "last_ea_hat", "last_leverage")

#: ctypes element type per candidate column (vac, neigh, dir, sp, k, ea, lev, trig).
_COLUMN_TYPES = (ctypes.c_int32,) * 3 + (ctypes.c_uint8,) + (ctypes.c_double,) * 3
_COLUMN_TYPES += (ctypes.c_uint32,)


def _bind(dll: ctypes.CDLL) -> ctypes.CDLL:
    vp, i32, f64 = ctypes.c_void_p, ctypes.c_int32, ctypes.c_double
    i32p, f64p = ctypes.POINTER(i32), ctypes.POINTER(f64)
    dll.pylatkmc_test_reg_new.restype = vp
    dll.pylatkmc_test_reg_new.argtypes = [i32, f64]
    dll.pylatkmc_test_reg_free.argtypes = [vp]
    dll.pylatkmc_test_reg_step.restype = ctypes.c_int
    dll.pylatkmc_test_reg_step.argtypes = [vp, vp, i32] + [ctypes.POINTER(t) for t in _COLUMN_TYPES]
    dll.pylatkmc_test_reg_step.argtypes += [i32, f64, f64]
    dll.pylatkmc_test_reg_n_flags.restype = i32
    dll.pylatkmc_test_reg_n_flags.argtypes = [vp]
    dll.pylatkmc_test_reg_capacity.restype = i32
    dll.pylatkmc_test_reg_capacity.argtypes = [vp]
    dll.pylatkmc_test_reg_n_surr_fired.restype = ctypes.c_uint64
    dll.pylatkmc_test_reg_n_surr_fired.argtypes = [vp]
    dll.pylatkmc_test_reg_dump.restype = None
    dll.pylatkmc_test_reg_dump.argtypes = [vp, ctypes.POINTER(ctypes.c_int64), f64p]
    dll.pylatkmc_test_reg_bench.restype = ctypes.c_int
    dll.pylatkmc_test_reg_bench.argtypes = [i32, i32]
    dll.pylatkmc_test_make_lattice_grid.restype = vp
    dll.pylatkmc_test_make_lattice_grid.argtypes = [i32, i32p, i32, vp, vp]
    dll.pylatkmc_test_free_lattice.argtypes = [vp]
    return dll


@pytest.fixture(scope="module")
def libs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, ctypes.CDLL]:
    """The registry shim against surrogate.c ("plain") and against a test copy
    that counts registry key comparisons ("counted"), both with a
    generated-template proclist.h of a surrogate build."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    pytest.importorskip("numpy")  # the synthetic model behind the externs
    from pylatkmc.codegen import _PROCLIST_H_TEMPLATE
    from pylatkmc.rate_expression import KB_EV_PER_K
    from pylatkmc.surrogate_codegen import emit_surrogate_externs

    from ._esym_fixture import synthetic_v2_model

    tmp = tmp_path_factory.mktemp("surr_registry")
    (tmp / "proclist.h").write_text(
        _PROCLIST_H_TEMPLATE.format(
            spec_name="registry",
            kb_ev_per_k=KB_EV_PER_K,
            extra_defines=emit_surrogate_externs(synthetic_v2_model()),
        )
    )
    counted, n_sub = _KEY_CMP.subn(
        r"(++pylatkmc_test_flag_key_cmps, \1->site_a == lo)", (CORE / "surrogate.c").read_text()
    )
    if n_sub != 1:
        pytest.fail(f"expected one registry key comparison in surrogate.c, found {n_sub}")
    (tmp / "surrogate_counted.c").write_text("long pylatkmc_test_flag_key_cmps;\n" + counted)
    out = {}
    for name, surrogate_c in (
        ("plain", CORE / "surrogate.c"),
        ("counted", tmp / "surrogate_counted.c"),
    ):
        lib = tmp / (f"libreg_{name}.dylib" if sys.platform == "darwin" else f"libreg_{name}.so")
        cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
        cmd += ["-I", str(tmp), "-I", str(CORE), str(SHIM_SRC), str(surrogate_c)]
        cmd += [str(CORE / "state_actions.c"), str(HELPERS_SRC), "-o", str(lib), "-lm"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            pytest.fail(f"{name} build failed:\n{res.stderr}")
        out[name] = _bind(ctypes.CDLL(str(lib)))
    return out


class _LinearScanRegistry:
    """surrogate_account's registry bookkeeping over the pre-fix linear-scan
    registry. Keys are unique, so the first match of a scan in index order is
    the dict entry of that key, and dict order is the registry index."""

    def __init__(self, capacity: int, flux_threshold: float) -> None:
        self.capacity = capacity
        self.thr = flux_threshold
        self.flags: dict[tuple[int, int, int], dict] = {}
        self.n_surr_fired = 0

    def lookup(self, c: tuple) -> dict | None:
        key = (min(c[0], c[1]), max(c[0], c[1]), c[2])
        if key not in self.flags:
            if len(self.flags) >= self.capacity:
                return None  # full: dropped, silently capped
            self.flags[key] = dict.fromkeys(_INT_FIELDS, 0) | dict.fromkeys(_FLOAT_FIELDS, 0.0)
            self.flags[key].update(site_a=key[0], site_b=key[1], dir_idx=key[2], used=1)
        return self.flags[key]

    def account(self, cands: list[tuple], fired: int, dt: float, ijk) -> None:
        k_flag = 0.0
        for c in cands:
            k_flag += c[4]
        for c in cands:
            vac, _neigh, _dir, sp, k, ea, lev, trig = c
            f = self.lookup(c)
            if f is None:
                continue
            if f["n_enrolled_steps"] == 0:
                f["ru"], f["rv"], f["rw"] = ijk[vac]
                f["sp_a"], f["sp_b"] = 0, sp
            f["n_enrolled_steps"] += 1
            f["carried_flux"] += k * dt
            f["last_ea_hat"], f["last_leverage"] = ea, lev
            if k_flag > 0.0 and k / k_flag > self.thr:
                trig |= SURR_TRIG_FLUX
            else:
                trig &= ~SURR_TRIG_FLUX
            f["trigger_or"] |= trig
        if 0 <= fired < len(cands):
            f = self.lookup(cands[fired])
            if f is not None:
                f["n_fired"] += 1
            self.n_surr_fired += 1

    def rows(self) -> list[tuple]:
        return [
            (*(f[k] for k in _INT_FIELDS), *(float(f[k]).hex() for k in _FLOAT_FIELDS))
            for f in self.flags.values()
        ]


def _registry(lib: ctypes.CDLL, ctx) -> list[tuple]:
    """The C registry in index order, floats as bit patterns (hex)."""
    n = lib.pylatkmc_test_reg_n_flags(ctx)
    ints, dbls = (ctypes.c_int64 * (13 * max(1, n)))(), (ctypes.c_double * (3 * max(1, n)))()
    lib.pylatkmc_test_reg_dump(ctx, ints, dbls)
    return [
        (*ints[13 * i : 13 * i + 13], *(x.hex() for x in dbls[3 * i : 3 * i + 3])) for i in range(n)
    ]


def _step(lib: ctypes.CDLL, ctx, lat, cands: list[tuple], fired: int, dt: float) -> None:
    cols = list(zip(*cands)) if cands else [()] * len(_COLUMN_TYPES)
    arrays = [(t * max(1, len(cands)))(*c) for t, c in zip(_COLUMN_TYPES, cols)]
    assert lib.pylatkmc_test_reg_step(ctx, lat, len(cands), *arrays, fired, dt, 1.0) == 0


def _candidate(rng: random.Random, key: tuple[int, int, int]) -> tuple:
    """One synthetic live candidate on ``key``, either orientation of the pair.
    Dyadic k and ea/leverage keep every sum exact (no FMA dependence)."""
    v, nb, d = key if rng.random() < 0.5 else (key[1], key[0], key[2])
    return (
        v,
        nb,
        d,
        rng.choice((1, 2, 3)),
        rng.randint(1, 64) / 16.0,
        rng.randint(0, 1024) / 256.0,
        rng.randint(0, 1024) / 1024.0,
        rng.randrange(16),
    )


def _lattice(lib: ctypes.CDLL):
    """N_SITES sites on a small grid; returns (lattice, site_ijk relative to
    site 0 as surrogate_account reads it)."""
    cells = [(2 * i, 2 * (i % 7), 2 * (i % 3)) for i in range(N_SITES)]
    flat = (ctypes.c_int32 * (3 * N_SITES))(*(x for c in cells for x in c))
    lat = lib.pylatkmc_test_make_lattice_grid(N_SITES, flat, 2, None, None)
    assert lat
    return lat, [tuple(c[a] - cells[0][a] for a in range(3)) for c in cells]


@pytest.mark.parametrize("capacity", [1, 64, 4096, 0], ids=["cap1", "cap64", "cap4096", "default"])
def test_registry_matches_the_linear_scan(libs, capacity: int) -> None:
    """Entries, registry order and every field equal the linear-scan registry
    after every step, including registries that fill up and then silently drop
    new keys while still accounting their registered ones."""
    lib = libs["plain"]
    rng = random.Random(1100 + capacity)
    thr = 0.05
    lat, ijk = _lattice(lib)
    ctx = lib.pylatkmc_test_reg_new(capacity, thr)
    assert ctx
    cap = lib.pylatkmc_test_reg_capacity(ctx)
    assert cap == (capacity or DEFAULT_CAPACITY)
    ref = _LinearScanRegistry(cap, thr)
    # ~400 keys over 64 sites, both site orders, pairs shared by two
    # directions and pairs on every direction (their keys differ in dir_idx
    # only); steps draw from a window sliding through the sorted pool, so keys
    # recur, then retire, and new ones keep arriving after a small registry
    # is full.
    pool = sorted(
        {(rng.randrange(N_SITES), rng.randrange(N_SITES), rng.randrange(12)) for _ in range(240)}
    )
    pool += [(a, b, (d + 5) % 12) for a, b, d in pool[:40]]
    pool += [(a, a + 1 + rng.randrange(8), d) for a in range(0, N_SITES - 9, 6) for d in range(12)]
    pool = sorted(set(pool))
    try:
        for step in range(300):
            lo = (step * len(pool)) // 300
            window = pool[max(0, lo - 30) : lo + 30]
            cands = [_candidate(rng, rng.choice(window)) for _ in range(rng.randrange(41))]
            fired = rng.randrange(-1, len(cands)) if cands else -1
            dt = rng.randint(1, 8) / 8.0
            _step(lib, ctx, lat, cands, fired, dt)
            ref.account(cands, fired, dt, ijk)
            assert _registry(lib, ctx) == ref.rows(), f"capacity {cap}: step {step}"
        assert lib.pylatkmc_test_reg_n_surr_fired(ctx) == ref.n_surr_fired
    finally:
        lib.pylatkmc_test_reg_free(ctx)
        lib.pylatkmc_test_free_lattice(lat)
    n_keys = len({(min(a, b), max(a, b), d) for a, b, d in pool})
    assert len(ref.flags) == min(cap, n_keys)
    if capacity in (1, 64):
        assert n_keys > cap  # the full path really ran


def test_flag_lookup_compares_o1_keys(libs) -> None:
    """On a full 4096-flag registry a lookup compares O(1) keys, hit or miss
    (the pre-fix linear scan compares ~2048 per hit and 4096 per miss)."""
    lib = libs["counted"]
    rng = random.Random(11)
    cmps = ctypes.c_long.in_dll(lib, "pylatkmc_test_flag_key_cmps")
    lat, _ijk = _lattice(lib)
    cap = 4096
    ctx = lib.pylatkmc_test_reg_new(cap, 0.01)
    assert ctx
    # Registry keys over the lattice's sites (a candidate's vacancy end is
    # read back through site_ijk on its first enrolment).
    keys = [(a, b, d) for a in range(N_SITES) for b in range(a + 1, N_SITES) for d in range(12)]
    rng.shuffle(keys)
    stored, extra = keys[:cap], keys[cap : cap + 1024]
    assert len(extra) == 1024

    def run(stream: list[tuple[int, int, int]]) -> float:
        cmps.value = 0
        for i in range(0, len(stream), 64):
            _step(lib, ctx, lat, [_candidate(rng, k) for k in stream[i : i + 64]], -1, 0.5)
        return cmps.value / len(stream)

    try:
        run(stored)  # fill the registry to capacity
        assert lib.pylatkmc_test_reg_n_flags(ctx) == cap
        hits = run([rng.choice(stored) for _ in range(8192)])
        misses = run(extra)  # registry full: every new key probes, then is dropped
        assert lib.pylatkmc_test_reg_n_flags(ctx) == cap
    finally:
        lib.pylatkmc_test_reg_free(ctx)
        lib.pylatkmc_test_free_lattice(lat)
    assert hits <= 3.0, f"{hits:.1f} key comparisons per hit (linear scan: ~{cap // 2})"
    assert misses <= 4.0, f"{misses:.1f} key comparisons per miss (linear scan: {cap})"


def test_full_default_registry_workload(libs) -> None:
    """The default 65536-flag registry, filled, then steps of 128 candidates
    (half registered keys, half new ones it drops, the first fired): every
    flag checked in C, and O(1) key comparisons per lookup. A short counted
    run goes first, so a linear-scan lookup fails here in seconds."""
    lib = libs["counted"]
    cmps = ctypes.c_long.in_dll(lib, "pylatkmc_test_flag_key_cmps")
    for n_steps in (64, 50000):
        cmps.value = 0
        rc = lib.pylatkmc_test_reg_bench(n_steps, 128)
        n_lookups = DEFAULT_CAPACITY + n_steps * (128 + 1)
        per_lookup = cmps.value / n_lookups
        assert per_lookup <= 3.0, (
            f"{n_steps} steps: {per_lookup:.1f} key comparisons per lookup on a full "
            f"default registry (a linear scan compares ~{DEFAULT_CAPACITY // 2})"
        )
        assert rc == 0, f"{n_steps} steps: registry check failed (code {rc})"
