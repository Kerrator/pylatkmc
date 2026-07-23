"""C-vs-Python parity for the Phase C surrogate rate channel (b).

The critical test: the runtime feature port (runtime/src/core/surrogate.c) must
reproduce the Python oracle (pylatkmc.surrogate_codegen.eval_candidate, itself
built on pylatkmc.ingest.surrogate's map-level functions) to float precision on
identical local configurations. Also checks DB-exactness of the KRA form
(k_f/k_b == exp(-dE/kT)) which the whole channel rests on.

Compile-gated: skips without cc, or without the Phase C catalogue + surrogate
model artifacts (machine-local under .scratch/phaseC/).
"""

from __future__ import annotations

import ctypes
import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"
SHIM_SRC = Path(__file__).parent / "_surrogate_test_shim.c"
MODEL_JSON = REPO_ROOT / ".scratch" / "phaseC" / "esym_model_v1.json"
NICR_SPEC = REPO_ROOT / "models" / "nicr_v2_scratch" / "nicr_v2_scratch.kmcspec.toml"
GEN_DIR = REPO_ROOT / "models" / "nicr_v2_scratch" / "generated"

KB = 8.617333262e-5


def _have_cc() -> bool:
    return shutil.which("cc") is not None


class SurrEval(ctypes.Structure):
    _fields_ = [
        ("phi", ctypes.c_double * 68),
        ("e_sym", ctypes.c_double),
        ("dE_H", ctypes.c_double),
        ("ea_hat", ctypes.c_double),
        ("ea_clamped", ctypes.c_double),
        ("leverage", ctypes.c_double),
        ("k", ctypes.c_double),
        ("trigger", ctypes.c_uint32),
        ("n_ctx", ctypes.c_int32),
        ("c_ctx", ctypes.c_int32),
        ("e_ctx", ctypes.c_int32),
    ]


@pytest.fixture(scope="module")
def libsurr(tmp_path_factory: pytest.TempPathFactory):
    if not _have_cc():
        pytest.skip("cc not on PATH")
    if not MODEL_JSON.exists():
        pytest.skip("surrogate model artifact absent (.scratch/phaseC)")
    # Regenerate the nicr proclist (needs the phaseC catalogue + model).
    try:
        from pylatkmc import codegen, loader
    except Exception as e:  # pragma: no cover
        pytest.skip(f"pylatkmc import failed: {e}")
    spec = loader.load(NICR_SPEC)
    try:
        codegen.generate(spec, GEN_DIR, spec_path=NICR_SPEC)
    except Exception as e:
        pytest.skip(f"nicr codegen failed (catalogue absent?): {e}")

    builddir = tmp_path_factory.mktemp("surr_lib")
    libname = "libsurr.dylib" if os.uname().sysname == "Darwin" else "libsurr.so"
    libpath = builddir / libname
    cmd = [
        "cc", "-std=c11", "-O2", "-fPIC", "-shared",
        "-I", str(RUNTIME_CORE), "-I", str(GEN_DIR),
        str(GEN_DIR / "proclist.c"),
        str(RUNTIME_CORE / "surrogate.c"),
        str(RUNTIME_CORE / "state.c"),
        str(RUNTIME_CORE / "state_actions.c"),
        str(RUNTIME_CORE / "avail_sites.c"),
        str(HELPERS_SRC),
        str(SHIM_SRC),
        "-lm", "-o", str(libpath),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.fail("surrogate lib build failed:\n" + r.stderr)
    lib = ctypes.CDLL(str(libpath))
    lib.pylatkmc_test_make_lattice_grid.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_lattice_grid.argtypes = [
        ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.c_void_p, ctypes.c_void_p,
    ]
    lib.pylatkmc_test_make_state.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_surrogate_eval.restype = ctypes.c_int
    lib.pylatkmc_test_surrogate_eval.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
        ctypes.c_uint8, ctypes.c_double, ctypes.POINTER(SurrEval),
    ]
    lib.pylatkmc_test_surreval_size.restype = ctypes.c_int32
    lib.pylatkmc_test_free_lattice.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_free_state.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_v6_probe.argtypes = [
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_uint64),
    ]
    assert lib.pylatkmc_test_surreval_size() == ctypes.sizeof(SurrEval)
    return lib


SP_VACANT, SP_NI, SP_CR = 0, 1, 3


def _to_runtime(o):
    return (o[0] + o[1], o[1] - o[0], o[2])


def _build_config(rng, kcut):
    """Physical crystal sites (even parity, |i|,|j|,|k|<=7) minus surface cut.

    Returns (phys: dict off->name, present: set of physical offsets)."""
    phys = {}
    present = set()
    for i in range(-7, 8):
        for j in range(-7, 8):
            for k in range(-7, 8):
                if (i + j + k) % 2 != 0:
                    continue
                if k > kcut:  # vacuum above the surface
                    continue
                off = (i, j, k)
                present.add(off)
                phys[off] = "Cr" if rng.random() < 0.25 else "Ni"
    phys[(0, 0, 0)] = "Vacant"
    return phys, present


def _c_eval(lib, phys, present, dir_off, dir_idx, atom_name):
    """Drive the C surrogate_eval on a lattice built from `phys`."""
    sp_code = {"Vacant": SP_VACANT, "Ni": SP_NI, "Cr": SP_CR}
    ordered = [(0, 0, 0)] + sorted(o for o in present if o != (0, 0, 0))
    n = len(ordered)
    cells = (ctypes.c_int32 * (3 * n))()
    species = (ctypes.c_uint8 * n)()
    idx_of = {o: i for i, o in enumerate(ordered)}
    for i, o in enumerate(ordered):
        ru = _to_runtime(o)
        cells[3 * i], cells[3 * i + 1], cells[3 * i + 2] = ru
        species[i] = sp_code[phys[o]]
    species[idx_of[dir_off]] = sp_code[atom_name]
    lat = lib.pylatkmc_test_make_lattice_grid(n, cells, 14, None, None)
    vac = (ctypes.c_int32 * 1)(idx_of[(0, 0, 0)])
    st = lib.pylatkmc_test_make_state(n, 4, 1, vac, species)
    out = SurrEval()
    rc = lib.pylatkmc_test_surrogate_eval(
        lat, st, idx_of[(0, 0, 0)], dir_idx, sp_code[atom_name], 500.0, ctypes.byref(out)
    )
    lib.pylatkmc_test_free_state(st)
    lib.pylatkmc_test_free_lattice(lat)
    assert rc == 0
    return out


def _py_eval(model, g, phys, atom_name):
    from pylatkmc.surrogate_codegen import eval_candidate

    species_at = {o: phys.get(o, "absent") for o in g.offs}
    return eval_candidate(model, g, species_at, atom_name)


@pytest.mark.parametrize("kcut", [7, 1, 0, -1])
def test_c_python_feature_parity(libsurr, kcut):
    from pylatkmc.ingest.surrogate import load_model
    from pylatkmc.surrogate_codegen import DIRECTIONS, bake_direction

    model = load_model(MODEL_JSON)
    rng = np.random.default_rng(1234 + kcut)
    worst = 0.0
    for dir_idx, dir_off in enumerate(DIRECTIONS):
        phys, present = _build_config(rng, kcut)
        # ensure the atom neighbour exists and is occupied
        if dir_off not in present:
            continue
        atom_name = "Cr" if rng.random() < 0.4 else "Ni"
        g = bake_direction(dir_off)
        c = _c_eval(libsurr, phys, present, dir_off, dir_idx, atom_name)
        p = _py_eval(model, g, phys, atom_name)
        cphi = np.array(c.phi)
        worst = max(worst, float(np.max(np.abs(cphi - p["phi"]))))
        for key, cval in (("e_sym", c.e_sym), ("dE_H", c.dE_H), ("leverage", c.leverage)):
            denom = max(1.0, abs(p[key]))
            rel = abs(cval - p[key]) / denom
            assert rel < 1e-10, f"kcut={kcut} dir={dir_off} {key}: C={cval} PY={p[key]} rel={rel}"
    assert worst < 1e-9, f"max phi abs deviation {worst}"


def test_db_exactness(libsurr):
    """k_f/k_b == exp(-dE_H/kT): E_sym + nu0 cancel; only dE survives."""
    from pylatkmc.surrogate_codegen import DIRECTIONS, bake_direction

    rng = np.random.default_rng(99)
    kT = KB * 500.0
    for dir_idx, dir_off in enumerate(DIRECTIONS):
        phys, present = _build_config(rng, kcut=1)
        rdir = (-dir_off[0], -dir_off[1], -dir_off[2])
        # reverse candidate: vacancy at n=dir_off, atom (same species) at v=0.
        # Build a physical config where BOTH endpoints and full context exist.
        phys[dir_off] = "Vacant"  # place vacancy at n for the reverse
        present.add(dir_off)
        atom = "Cr" if rng.random() < 0.4 else "Ni"
        # forward: vacancy at 0, atom at dir_off
        phys_f = dict(phys); phys_f[(0, 0, 0)] = "Vacant"; phys_f[dir_off] = atom
        cf = _c_eval(libsurr, phys_f, present | {(0, 0, 0), dir_off}, dir_off, dir_idx, atom)
        # reverse: vacancy at dir_off, atom at 0. Shift so the reverse vacancy is origin.
        # Build a phys map keyed relative to n (=dir_off): phys_r[o'] = phys_f[dir_off+o'].
        rdir_idx = DIRECTIONS.index(rdir)
        gr = bake_direction(rdir)
        present_r = set()
        phys_r = {}
        for op in gr.offs:
            abs_off = (dir_off[0] + op[0], dir_off[1] + op[1], dir_off[2] + op[2])
            name = phys_f.get(abs_off, "absent")
            if name != "absent":
                present_r.add(op)
                phys_r[op] = name
        phys_r[(0, 0, 0)] = "Vacant"     # reverse vacancy at its origin (=phys n)
        phys_r[rdir] = atom              # reverse atom at gr.dir (=phys v=0)
        present_r |= {(0, 0, 0), rdir}
        cr = _c_eval(libsurr, phys_r, present_r, rdir, rdir_idx, atom)
        assert abs(cf.e_sym - cr.e_sym) < 1e-9, f"E_sym asym dir={dir_off}"
        assert abs(cf.dE_H + cr.dE_H) < 1e-9, f"dE not antisym dir={dir_off}"
        kf = math.exp(-cf.ea_clamped / kT)
        kb = math.exp(-cr.ea_clamped / kT)
        # unclamped DB: use ea_hat (clamp can break DB by design near the floor)
        kf2 = math.exp(-cf.ea_hat / kT)
        kb2 = math.exp(-cr.ea_hat / kT)
        assert abs((kf2 / kb2) - math.exp(-cf.dE_H / kT)) < 1e-6 * (kf2 / kb2), dir_off
        _ = (kf, kb)


def test_v6_accumulator(libsurr):
    """C V6 residual accumulator: mean over finite-v6 fires, count over all."""
    mean = ctypes.c_double()
    mx = ctypes.c_double()
    nmeas = ctypes.c_uint64()
    libsurr.pylatkmc_test_v6_probe(ctypes.byref(mean), ctypes.byref(mx), ctypes.byref(nmeas))
    assert nmeas.value == 3           # all three fires counted as measured
    assert abs(mean.value - 0.1) < 1e-12   # (0.2 + 0.0) / 2 finite-v6 fires
    assert abs(mx.value - 0.2) < 1e-12
