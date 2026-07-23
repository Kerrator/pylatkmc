"""Serial per-event driver — ONE phase per process, isolated workdir.

Phases (a Fortran abort in pARTn kills only its own attempt-process):
  python rc_driver.py <wd> --phase min                       -> mins.npz
  python rc_driver.py <wd> --phase refine --rung 1 --zseed S -> refine_r<rung>_z<S>.json
                                                                (+ sadstate.npz on success)
  python rc_driver.py <wd> --phase nu0                       -> nu0.json

Mirrors pyKMC _partn_refine_impl (AV=False) with pyKMC config defaults: FIRE
minimize under `fix artn`; success = artn error 0 and delr_sad < 0.4. Padding is
frozen by setforce fixes bracketing fix artn (pyKMC f_frozen_pre/post pattern).
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("workdir")
ap.add_argument("--phase", required=True, choices=["min", "refine", "nu0"])
ap.add_argument("--rung", type=int, default=1)
ap.add_argument("--zseed", type=int, default=1000)
ARGS = ap.parse_args()

# --- TMPDIR isolation BEFORE lammps import (OMPI shared-/tmp gotcha) ---
WD = Path(ARGS.workdir).resolve()
TMP = WD / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(TMP)
os.chdir(WD)

sys.path.insert(0, "/home/kerr/pykmc/artn-plugin/interface")

import numpy as np
from lammps import lammps

POTENTIAL = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
MIN_CMD = "minimize 1e-10 1e-12 10000 10000"   # production [Lammps] minimize
RUNGS = {
    1: dict(delr_thr=0.1, push_step_size=1e-4, ninit=0,
            lanczos_min_size=20, lanczos_max_size=50, lanczos_disp=5e-4,
            lanczos_eval_conv_thr=1e-3, eigval_thr=-0.01, eigen_step_size=0.005,
            nsmooth=0, neigen=1, alpha_mix_cr=0.2, nnewchance=0,
            nperp=3, nperp_limitation=[100], forc_thr=1e-3, dmax=1.0,
            # 2.0, not pyKMC's 0.4: the padded-cluster saddle drifts 0.4-1.1 A
            # (config-space norm over 130 atoms) from the harvested start; this
            # gate only rejects absurd escapes. Minimum-fallback is detected
            # downstream (Ea ~ 0 / dra collapse) and acceptance
            # (mover/dra/class_id) adjudicates identity.
            nevalf_max=300, delr_sad_thr=2.0),
}
RUNGS[2] = dict(RUNGS[1], eigen_step_size=0.002, lanczos_eval_conv_thr=1e-4,
                nevalf_max=800)
RUNGS[3] = dict(RUNGS[1], nevalf_max=3000)
MASS = {1: 51.996, 2: 58.6934}                 # Cr, Ni (amu)
EV_A2_AMU_TO_S2 = 1.602176634e-19 / (1e-20 * 1.66053906660e-27)


def scatter(lmp, P):
    lmp.scatter_atoms("x", 1, 3, np.ascontiguousarray(P, dtype=np.float64)
                      .ctypes.data_as(ctypes.POINTER(ctypes.c_double)))


def gather(lmp, n, name="x"):
    raw = lmp.gather_atoms(name, 1, 3)
    return np.array(raw[:], dtype=float).reshape(n, 3)


def setup(n, n_real):
    lmp = lammps(cmdargs=["-log", f"lammps_{ARGS.phase}.log", "-screen", "none"])
    lmp.command("units metal")
    lmp.command("dimension 3")
    lmp.command("boundary p p p")
    lmp.command("atom_style atomic")
    lmp.command("atom_modify map array sort 0 0.0")
    lmp.command(f"read_data {WD / 'data.lmp'}")
    lmp.command("pair_style eam/alloy")
    lmp.command(f"pair_coeff * * {POTENTIAL} Cr Ni")
    lmp.command("neighbor 2.0 bin")
    lmp.command("neigh_modify every 1 delay 0 check yes")
    lmp.command(f"group free id 1:{n_real}")
    if n_real < n:
        lmp.command(f"group frozen id {n_real + 1}:{n}")
        lmp.command("fix frz frozen setforce 0.0 0.0 0.0")
    else:
        lmp.command("group frozen empty")
    return lmp


def phase_min(d, n, n_real):
    lmp = setup(n, n_real)
    lmp.command("min_style cg")
    scatter(lmp, d["init"])
    lmp.command(MIN_CMD)
    E1 = lmp.get_thermo("pe")
    R1 = gather(lmp, n)
    scatter(lmp, d["fin"])
    lmp.command(MIN_CMD)
    E2 = lmp.get_thermo("pe")
    R2 = gather(lmp, n)
    np.savez_compressed(WD / "mins.npz", R1=R1, R2=R2, E_min1=E1, E_min2=E2)
    print(json.dumps({"E_min1": E1, "E_min2": E2}))


def phase_refine(d, n, n_real):
    import pypARTn
    p = RUNGS[ARGS.rung]
    mover_id = int(d["mover"]) + 1
    out = {"rung": ARGS.rung, "zseed": ARGS.zseed, "ok": False}
    tag = f"refine_r{ARGS.rung}_z{ARGS.zseed}"
    lmp = setup(n, n_real)
    artn = pypARTn.artn(engine="lmp")
    lmp.command(f"plugin load {artn.lib._name}")
    artn.reset_input()
    artn.set("filout", f"{tag}.artn.out")
    artn.set("engine_units", "lammps/metal")
    artn.set("verbose", 1)
    artn.set("struc_format_out", "none")
    artn.set("delr_thr", p["delr_thr"])
    artn.set("lpush_final", False)
    artn.set("lmove_nextmin", False)
    artn.set("zseed", ARGS.zseed)
    artn.set("push_mode", "list")
    artn.set("push_step_size", p["push_step_size"])
    artn.set("push_ids", [mover_id])
    artn.set("ninit", p["ninit"])
    artn.set("lanczos_min_size", p["lanczos_min_size"])
    artn.set("lanczos_max_size", p["lanczos_max_size"])
    artn.set("lanczos_disp", p["lanczos_disp"])
    artn.set("lanczos_eval_conv_thr", p["lanczos_eval_conv_thr"])
    artn.set("eigval_thr", p["eigval_thr"])
    artn.set("eigen_step_size", p["eigen_step_size"])
    artn.set("nsmooth", p["nsmooth"])
    artn.set("neigen", p["neigen"])
    artn.set("alpha_mix_cr", p["alpha_mix_cr"])
    artn.set("nnewchance", p["nnewchance"])
    artn.set("nperp", p["nperp"])
    artn.set("nperp_limitation", np.array(p["nperp_limitation"]))
    artn.set("forc_thr", p["forc_thr"])

    # start from the re-relaxed environment's stored saddle: real saddle coords
    # over the relaxed pads/mins are identical here (pads never move)
    scatter(lmp, d["sad"])
    lmp.command(f"fix 10 all artn dmax {p['dmax']}")
    lmp.command("fix frz2 frozen setforce 0.0 0.0 0.0")
    lmp.command("min_style fire")
    lmp.command(f"minimize 1e-6 1e-8 10000 {p['nevalf_max']}")
    lmp.command("unfix 10")
    lmp.command("unfix frz2")

    err = artn.get_error()
    out["artn_error"] = str(err)
    try:
        errcode = int(np.atleast_1d(np.asarray(err[0])).ravel()[0])
    except Exception:  # noqa: BLE001
        errcode = -1
    if errcode == 0:
        out["delr_sad"] = float(artn.extract("delr_sad"))
        if out["delr_sad"] < p["delr_sad_thr"]:
            out["ok"] = True
            out["E_sad"] = float(artn.extract("etot_sad"))
            np.savez_compressed(WD / "sadstate.npz", Rsad=gather(lmp, n),
                                E_sad=out["E_sad"])
    (WD / f"{tag}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


def phase_nu0(d, n, n_real):
    mins = np.load(WD / "mins.npz")
    sad = np.load(WD / "sadstate.npz")
    lmp = setup(n, n_real)
    type_ids = [int(t) for t in lmp.gather_atoms("type", 0, 1)[:n]]
    m = np.array([MASS[t] for t in type_ids[:n_real]])
    w = np.repeat(np.sqrt(m), 3)

    def modes(P, dx=0.01):
        ndof = 3 * n_real
        H = np.zeros((ndof, ndof))
        for i in range(n_real):
            for c in range(3):
                Pp = P.copy(); Pp[i, c] += dx
                Pm = P.copy(); Pm[i, c] -= dx
                scatter(lmp, Pp); lmp.command("run 0 post no")
                fp = gather(lmp, n, "f")[:n_real]
                scatter(lmp, Pm); lmp.command("run 0 post no")
                fm = gather(lmp, n, "f")[:n_real]
                H[3 * i + c] = ((fm - fp) / (2 * dx)).ravel()
        H = 0.5 * (H + H.T)
        return np.linalg.eigvalsh(H / np.outer(w, w)) * EV_A2_AMU_TO_S2

    lam_min = modes(mins["R1"])
    lam_sad = modes(sad["Rsad"])
    out = {"n_imag_min": int((lam_min < 0).sum()),
           "n_imag_sad": int((lam_sad < 0).sum())}
    pos_min, pos_sad = lam_min[lam_min > 0], lam_sad[lam_sad > 0]
    if len(pos_min) == len(pos_sad) + 1:
        out["nu0_diag_hz"] = float(np.exp(
            0.5 * (np.log(pos_min).sum() - np.log(pos_sad).sum())) / (2 * np.pi))
    else:
        out["nu0_diag_hz"] = None
    (WD / "nu0.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


def main():
    d = np.load(WD / "arrays.npz")
    n, n_real = int(d["n_all"]), int(d["n_real"])
    {"min": phase_min, "refine": phase_refine, "nu0": phase_nu0}[ARGS.phase](d, n, n_real)


if __name__ == "__main__":
    main()
