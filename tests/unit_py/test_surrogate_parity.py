"""C-vs-Python parity for the Phase C surrogate rate channel (b).

The critical test: the runtime feature port (runtime/src/core/surrogate.c) must
reproduce the Python oracle (pylatkmc.surrogate_codegen.eval_candidate, itself
built on pylatkmc.ingest.surrogate's map-level functions) to float precision on
identical local configurations. Also checks DB-exactness of the KRA form
(k_f/k_b == exp(-dE/kT)) which the whole channel rests on.

Basis v2 (2026-08-15, blockers B2+B3): the synthetic configurations include SP_FE
atoms and Fe hopping candidates, so CAT_F is exercised on both sides — the whole
point of the Fe leg. (CAT_W cannot be exercised here: the runtime never observes a
masked site; W parity is covered on the Python side by test_surrogate.py.)

Compile-gated: skips without cc, or without the machine-local EventClass
catalogue the nicr spec names. The surrogate model is SYNTHESIZED here (see
_esym_fixture) rather than read from .scratch, so this test does not depend on any
particular fit — and never silently skips because a model artifact is stale.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from ._esym_fixture import catalogue_available, synthetic_v2_model, write_v2_spec

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"
SHIM_SRC = Path(__file__).parent / "_surrogate_test_shim.c"

#: len(pylatkmc.ingest.surrogate.ESYM_FEATURE_KEYS) == SURR_NPHI. Mirrored by hand
#: (like tests/unit_py/test_coord_table.py mirrors the NeighbourCode enum) so a
#: one-sided basis change fails here loudly instead of reading past the struct.
SURR_NPHI = 115

KB = 8.617333262e-5


def _have_cc() -> bool:
    return shutil.which("cc") is not None


class SurrEval(ctypes.Structure):
    _fields_ = [
        ("phi", ctypes.c_double * SURR_NPHI),
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
        ("f_ctx", ctypes.c_int32),
    ]


@pytest.fixture(scope="module")
def esym_model():
    """The synthetic v2 model both the C bake and the Python oracle are driven from."""
    return synthetic_v2_model()


@pytest.fixture(scope="module")
def libsurr(tmp_path_factory: pytest.TempPathFactory):
    if not _have_cc():
        pytest.skip("cc not on PATH")
    if not catalogue_available():
        pytest.skip("machine-local EventClass catalogue absent (.scratch/phaseC)")
    try:
        from pylatkmc import codegen, loader
    except Exception as e:  # pragma: no cover
        pytest.skip(f"pylatkmc import failed: {e}")

    workdir = tmp_path_factory.mktemp("surr_spec")
    spec_path = write_v2_spec(workdir)
    GEN_DIR = workdir / "generated"
    spec = loader.load(spec_path)
    try:
        codegen.generate(spec, GEN_DIR, spec_path=spec_path)
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


#: Runtime Species enum values (events_base.h). NOTE SP_FE=2 / SP_CR=3 — the
#: ingest Occ enum has them the other way round; the bridge is by NAME only.
SP_VACANT, SP_NI, SP_FE, SP_CR = 0, 1, 2, 3

#: species NAME -> runtime code, by NAME (never by an Occ integer).
_SP_CODE = {"Vacant": SP_VACANT, "Ni": SP_NI, "Fe": SP_FE, "Cr": SP_CR}


def _to_runtime(o):
    return (o[0] + o[1], o[1] - o[0], o[2])


def _build_config(rng, kcut, *, with_fe=True):
    """Physical crystal sites (even parity, |i|,|j|,|k|<=7) minus surface cut.

    A ternary Ni-Cr-Fe decoration by default, so CAT_F appears in shells, bonds,
    mover-neighbour counts, triangles and the coordination/depth reductions.

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
                r = rng.random()
                if r < 0.25:
                    phys[off] = "Cr"
                elif with_fe and r < 0.45:
                    phys[off] = "Fe"
                else:
                    phys[off] = "Ni"
    phys[(0, 0, 0)] = "Vacant"
    return phys, present


def _c_eval(lib, phys, present, dir_off, dir_idx, atom_name):
    """Drive the C surrogate_eval on a lattice built from `phys`."""
    sp_code = _SP_CODE
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
def test_c_python_feature_parity(libsurr, esym_model, kcut):
    """Every phi entry / E_sym / dE_H / leverage agrees C-vs-Python to <=1e-10.

    Ternary Ni-Cr-Fe contexts with the hopping candidate cycling through all three
    species: this is what locks CAT_F into the same reductions on both sides.
    """
    from pylatkmc.surrogate_codegen import DIRECTIONS, bake_direction

    model = esym_model
    rng = np.random.default_rng(1234 + kcut)
    worst = 0.0
    n_fe_mover = 0
    for dir_idx, dir_off in enumerate(DIRECTIONS):
        phys, present = _build_config(rng, kcut)
        # ensure the atom neighbour exists and is occupied
        if dir_off not in present:
            continue
        # cycle the mover species so Ni / Cr / Fe all appear across the 12 directions
        atom_name = ("Ni", "Cr", "Fe")[dir_idx % 3]
        n_fe_mover += atom_name == "Fe"
        g = bake_direction(dir_off)
        c = _c_eval(libsurr, phys, present, dir_off, dir_idx, atom_name)
        p = _py_eval(model, g, phys, atom_name)
        cphi = np.array(c.phi)
        assert len(cphi) == len(p["phi"]) == SURR_NPHI
        worst = max(worst, float(np.max(np.abs(cphi - p["phi"]))))
        for key, cval in (("e_sym", c.e_sym), ("dE_H", c.dE_H), ("leverage", c.leverage)):
            denom = max(1.0, abs(p[key]))
            rel = abs(cval - p[key]) / denom
            assert rel < 1e-10, f"kcut={kcut} dir={dir_off} {key}: C={cval} PY={p[key]} rel={rel}"
    assert worst < 1e-9, f"max phi abs deviation {worst}"
    if kcut >= 0:
        assert n_fe_mover > 0, "the Fe mover leg never ran"


def test_fe_context_trips_species_trigger(libsurr, esym_model):
    """An Fe-bearing context flags OOD: the model bakes ctx_f = [0, 0] (all-NiCr fit).

    This is the safety net that makes the untrained-Fe ΔE_H acceptable — every Fe
    candidate lands on the priority re-search flag registry.
    """
    from pylatkmc.surrogate_codegen import DIRECTIONS

    assert esym_model.context_count_ranges["F"] == (0, 0)
    rng = np.random.default_rng(7)
    dir_idx, dir_off = 0, DIRECTIONS[0]

    pure, present = _build_config(rng, kcut=7, with_fe=False)
    c_pure = _c_eval(libsurr, pure, present, dir_off, dir_idx, "Ni")
    assert c_pure.f_ctx == 0

    ternary = dict(pure)
    # a single Fe well inside the ball is enough
    ternary[(2, 0, 0)] = "Fe"
    c_fe = _c_eval(libsurr, ternary, present, dir_off, dir_idx, "Ni")
    assert c_fe.f_ctx > 0
    assert c_fe.trigger & 0x2, "SURR_TRIG_SPECIES not set for an Fe context"


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
        atom = ("Ni", "Cr", "Fe")[dir_idx % 3]
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
        # DB in LOG space: k_f/k_b == exp(-dE/kT)  <=>  Ea_f - Ea_b == dE_H.
        # Stated this way it is exact and cannot overflow (a synthetic model's
        # random weights put ea_hat far outside any physical range; exp() of that
        # over kT ~ 0.043 eV overflows a double while the identity itself holds).
        # Use ea_hat, not ea_clamped: the clamp breaks DB near the bounds by design.
        assert abs((cf.ea_hat - cr.ea_hat) - cf.dE_H) < 1e-9, f"DB broken dir={dir_off}"
        assert kT > 0.0


def test_v6_accumulator(libsurr):
    """C V6 residual accumulator: mean over finite-v6 fires, count over all."""
    mean = ctypes.c_double()
    mx = ctypes.c_double()
    nmeas = ctypes.c_uint64()
    libsurr.pylatkmc_test_v6_probe(ctypes.byref(mean), ctypes.byref(mx), ctypes.byref(nmeas))
    assert nmeas.value == 3           # all three fires counted as measured
    assert abs(mean.value - 0.1) < 1e-12   # (0.2 + 0.0) / 2 finite-v6 fires
    assert abs(mx.value - 0.2) < 1e-12
