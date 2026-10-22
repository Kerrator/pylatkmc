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

- The registry equals a Python model of the linear-scan semantics, field for
  field and in index order, over random multi-step schedules with repeated,
  reversed and same-pair keys, fired candidates and a capacity-full phase
  (new keys dropped, registered keys still accounted), at capacities 1, 64
  and above the key count.
- A 50000-step run of 128 candidates against a full default-capacity
  registry finishes in about a second (the linear scan needs minutes).

ctypes level, no MPI; skips without cc.
"""

from __future__ import annotations

import ctypes
import random
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
FLUX_THRESHOLD = 0.01  # surrogate_ctx_init's default (the shim passes 0)
N_SITES = 64


@pytest.fixture(scope="module")
def reg_lib(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """surrogate.c + the registry shim, against a generated-template
    proclist.h of a surrogate build."""
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
    lib = tmp / ("libsurr_registry.dylib" if sys.platform == "darwin" else "libsurr_registry.so")
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(tmp), "-I", str(CORE), str(SHIM_SRC), str(CORE / "surrogate.c")]
    cmd += [str(CORE / "state_actions.c"), str(HELPERS_SRC), "-o", str(lib), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")
    return lib


def _bind(path: Path) -> ctypes.CDLL:
    dll = ctypes.CDLL(str(path))
    vp, i32 = ctypes.c_void_p, ctypes.c_int32
    i32p, f64p = ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_double)
    dll.pylatkmc_test_reg_new.restype = vp
    dll.pylatkmc_test_reg_new.argtypes = [i32]
    dll.pylatkmc_test_reg_free.argtypes = [vp]
    dll.pylatkmc_test_reg_step.restype = ctypes.c_int
    dll.pylatkmc_test_reg_step.argtypes = [vp, vp, i32, i32p, i32p, i32p]
    dll.pylatkmc_test_reg_step.argtypes += [ctypes.POINTER(ctypes.c_uint8), f64p, f64p, f64p]
    dll.pylatkmc_test_reg_step.argtypes += [ctypes.POINTER(ctypes.c_uint32), i32]
    dll.pylatkmc_test_reg_step.argtypes += [ctypes.c_double, ctypes.c_double]
    dll.pylatkmc_test_reg_n_flags.restype = i32
    dll.pylatkmc_test_reg_n_flags.argtypes = [vp]
    dll.pylatkmc_test_reg_flag.restype = None
    dll.pylatkmc_test_reg_flag.argtypes = [vp, i32, ctypes.POINTER(ctypes.c_int64), f64p]
    dll.pylatkmc_test_make_lattice_grid.restype = vp
    dll.pylatkmc_test_make_lattice_grid.argtypes = [i32, i32p, i32, vp, vp]
    dll.pylatkmc_test_free_lattice.argtypes = [vp]
    return dll


def _account(reg: dict, cap: int, cands: list[tuple], fired: int, dt: float, ijk) -> None:
    """surrogate_account's registry bookkeeping over a linear-scan registry:
    ``reg`` maps key -> flag fields in first-seen (registry index) order."""

    def lookup(c: tuple) -> dict | None:
        key = (min(c[0], c[1]), max(c[0], c[1]), c[2])
        if key not in reg:
            if len(reg) >= cap:
                return None  # full: dropped, silently capped
            reg[key] = dict(
                used=1,
                n_enrolled_steps=0,
                n_fired=0,
                first_step=0,
                trigger_or=0,
                ru=0,
                rv=0,
                rw=0,
                sp_a=0,
                sp_b=0,
                carried_flux=0.0,
                last_ea_hat=0.0,
                last_leverage=0.0,
            )
        return reg[key]

    k_flag = 0.0
    for c in cands:
        k_flag += c[4]
    for c in cands:
        vac, _neigh, _dir, sp, k, ea, lev, trig = c
        f = lookup(c)
        if f is None:
            continue
        if f["n_enrolled_steps"] == 0:
            f["ru"], f["rv"], f["rw"] = ijk[vac]
            f["sp_a"], f["sp_b"] = 0, sp
        f["n_enrolled_steps"] += 1
        f["carried_flux"] += k * dt
        f["last_ea_hat"], f["last_leverage"] = ea, lev
        if k_flag > 0.0 and k / k_flag > FLUX_THRESHOLD:
            trig |= SURR_TRIG_FLUX
        else:
            trig &= ~SURR_TRIG_FLUX
        f["trigger_or"] |= trig
    if 0 <= fired < len(cands):
        f = lookup(cands[fired])
        if f is not None:
            f["n_fired"] += 1


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


#: ctypes element type per candidate column (vac, neigh, dir, sp, k, ea, lev, trig).
_COLUMN_TYPES = (ctypes.c_int32,) * 3 + (ctypes.c_uint8,) + (ctypes.c_double,) * 3
_COLUMN_TYPES += (ctypes.c_uint32,)


def _registry(lib: ctypes.CDLL, ctx) -> list[tuple]:
    ints, dbls = (ctypes.c_int64 * 13)(), (ctypes.c_double * 3)()
    out = []
    for i in range(lib.pylatkmc_test_reg_n_flags(ctx)):
        lib.pylatkmc_test_reg_flag(ctx, i, ints, dbls)
        out.append((*ints, *(x.hex() for x in dbls)))
    return out


def _expected(reg: dict) -> list[tuple]:
    rows = []
    for (lo, hi, d), f in reg.items():
        vals = {"site_a": lo, "site_b": hi, "dir_idx": d, **f}
        rows.append(
            (
                *(vals[k] for k in _INT_FIELDS),
                *(float(vals[k]).hex() for k in ("carried_flux", "last_ea_hat", "last_leverage")),
            )
        )
    return rows


@pytest.mark.parametrize("capacity", [1, 64, 4096])
def test_registry_matches_the_linear_scan_model(reg_lib: Path, capacity: int) -> None:
    """Field for field, in registry-index order, after every step."""
    lib = _bind(reg_lib)
    rng = random.Random(1100 + capacity)
    cells = [(2 * i, 2 * (i % 7), 2 * (i % 3)) for i in range(N_SITES)]
    flat = (ctypes.c_int32 * (3 * N_SITES))(*(x for c in cells for x in c))
    lat = lib.pylatkmc_test_make_lattice_grid(N_SITES, flat, 2, None, None)
    ijk = [tuple(c[a] - cells[0][a] for a in range(3)) for c in cells]  # rel. site 0
    # ~150 keys over 64 sites: both site orders, and pairs in several dirs.
    pool = [(rng.randrange(N_SITES), rng.randrange(N_SITES), rng.randrange(12)) for _ in range(150)]
    ctx = lib.pylatkmc_test_reg_new(capacity)
    assert lat and ctx
    reg: dict = {}
    try:
        for step in range(300):
            cands = []
            for _ in range(rng.randrange(41)):
                vac, neigh, d = rng.choice(pool)
                k = 10.0 ** rng.uniform(-3.0, 12.0)
                cands.append(
                    (
                        vac,
                        neigh,
                        d,
                        rng.choice((1, 2, 3)),
                        k,
                        rng.uniform(0.1, 2.5),
                        rng.uniform(0.0, 3.0),
                        rng.randrange(16),
                    )
                )
            fired = rng.randrange(-1, len(cands)) if cands else -1
            dt = 10.0 ** rng.uniform(-14.0, -6.0)
            cols = list(zip(*cands)) if cands else [()] * len(_COLUMN_TYPES)
            arrays = [(t * max(1, len(cands)))(*c) for t, c in zip(_COLUMN_TYPES, cols)]
            rc = lib.pylatkmc_test_reg_step(ctx, lat, len(cands), *arrays, fired, dt, 1.0)
            assert rc == 0
            _account(reg, capacity, cands, fired, dt, ijk)
            assert _registry(lib, ctx) == _expected(reg), f"capacity {capacity}, step {step}"
    finally:
        lib.pylatkmc_test_reg_free(ctx)
        lib.pylatkmc_test_free_lattice(lat)
    n_keys = len({(min(a, b), max(a, b), d) for a, b, d in pool})
    assert len(reg) == min(capacity, n_keys)  # the full path really ran at 1 and 64


def test_full_registry_lookups_do_not_scan(reg_lib: Path) -> None:
    """50000 steps x 128 candidates (half registered keys, half new ones the
    full registry drops) against the default 65536-flag registry, every flag
    checked afterwards: about a second through the hash index, minutes for a
    linear scan of the registry. Run in a child process with a timeout."""
    code = (
        "import ctypes, sys; "
        f"sys.exit(ctypes.CDLL({str(reg_lib)!r}).pylatkmc_test_reg_bench(50000, 128))"
    )
    try:
        res = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        pytest.fail("a full flag registry still costs n_flags per lookup (linear scan?)")
    assert res.returncode == 0, f"registry check failed (code {res.returncode}): {res.stderr}"
