"""V4 -- prefactor asymmetry: per-state Vineyard ratio vs harvested nu0_f/nu0_b.

Memo 8-N4 fires harvested per-pair nu0_f/nu0_b as-is, claiming the ratio is a
per-state quantity (prod omega(init) / prod omega(final); saddle cancels).
The catalogue's nu0_f and nu0_b come from DIFFERENT reference rows (separate
pARTn searches, own saddles/free sets), so the claim is only exact if the
cross-row ratio matches the per-state ratio. This script measures both on a
sample of harvested pairs using pyKMC's own HTST machinery
(select_free_indices / mass_weighted_partial_hessian / vineyard_prefactor,
editable install = SK_basin_htst_binary) with the production settings
(free_radius=6.0, fd_step=0.01, Cr Ni eam/alloy).

Per sampled pair (forward row F, backward row B = F.idx_backward):
  R_harv   = nu0(F) / nu0(B)                      [cross-row, what N4 fires]
  R_state  = prod omega(F.min1) / prod omega(F.min2)   [single row, one free set]
  nu0_f_re = vineyard(F.min1, F.saddle)           [harness validation vs F.nu0]

CONDITIONS / caveat: geometries are the stored ~130-atom active-volume
clusters evaluated in vacuum with a frozen periphery; at harvest time forces
came from the full slab. nu0_f_re vs stored nu0 quantifies that truncation.
The R_state ratio shares the truncation between its two endpoints (partial
cancellation).

Run from inside ~/pykmc/pylatkmc (venv active).
"""

import ctypes
import pickle
import time

import numpy as np
from lammps import lammps

from pykmc.htst.free_region import select_free_indices
from pykmc.htst.hessian import mass_weighted_partial_hessian
from pykmc.htst.vineyard import vineyard_prefactor

RT = "/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle"
POT = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
FREE_RADIUS = 6.0
FD_STEP = 0.01
MASS = {"Ni": 58.6934, "Cr": 51.9961}

rt = pickle.load(open(RT, "rb"))
rt = rt.set_index("idx_ref", drop=False)
print(f"rows={len(rt)}  (indexed by idx_ref)")

r0 = rt.iloc[0]
rb0 = rt.loc[r0.idx_backward]
match = np.allclose(np.array(r0.final_positions), np.array(rb0.initial_positions), atol=1e-6)
print(f"idx_ref-lookup pair endpoint match (row {r0.idx_ref} vs {r0.idx_backward}): {match}")


class ClusterForces:
    """Persistent LAMMPS instance; forces for arbitrary positions of the cluster."""

    def __init__(self, positions, types, tag):
        self.n = len(positions)
        lo = positions.min(0) - 12.0
        hi = positions.max(0) + 12.0
        self.lmp = lammps(cmdargs=["-log", "none", "-screen", "none"])
        cmds = [
            "units metal",
            "boundary f f f",
            "atom_style atomic",
            "atom_modify map array sort 0 0",
            f"region box block {lo[0]} {hi[0]} {lo[1]} {hi[1]} {lo[2]} {hi[2]}",
            "create_box 2 box",
        ]
        self.lmp.commands_string("\n".join(cmds))
        t_codes = [1 if t == "Cr" else 2 for t in types]
        for p, tc in zip(positions, t_codes):
            self.lmp.command(f"create_atoms {tc} single {p[0]} {p[1]} {p[2]} units box")
        self.lmp.commands_string(
            f"""
mass 1 {MASS['Cr']}
mass 2 {MASS['Ni']}
pair_style eam/alloy
pair_coeff * * {POT} Cr Ni
neigh_modify every 1 delay 0 check yes
run 0 post no"""
        )

    def __call__(self, positions):
        x = (ctypes.c_double * (3 * self.n))()
        flat = np.ascontiguousarray(positions, dtype=np.float64).ravel()
        for i, v in enumerate(flat):
            x[i] = v
        self.lmp.scatter_atoms("x", 1, 3, x)
        self.lmp.command("run 0 pre yes post no")
        f = np.array(self.lmp.gather_atoms("f", 1, 3)).reshape(-1, 3)
        return f

    def close(self):
        self.lmp.close()


def fnu(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


rows = []
for idx in rt.index:
    r = rt.loc[idx]
    if not np.isfinite(fnu(r.nu0)) or r.idx_backward < 0 or r.idx_backward not in rt.index:
        continue
    b = rt.loc[r.idx_backward]
    if not np.isfinite(fnu(b.nu0)):
        continue
    if b.idx_backward != idx:
        continue
    if idx > r.idx_backward:
        continue
    mover = r.initial_types[int(r.move_atom_idx)]
    rows.append((idx, int(r.idx_backward), float(r.energy_barrier), mover))
print(f"usable symmetric pairs with finite nu0 both ways: {len(rows)}")

rows.sort(key=lambda t: t[2])
rng = np.random.default_rng(20260721)
qs = np.array_split(np.arange(len(rows)), 4)
sample = []
for q in qs:
    cr_q = [rows[i] for i in q if rows[i][3] == "Cr"]
    ni_q = [rows[i] for i in q if rows[i][3] == "Ni"]
    for pool, k in ((cr_q, 3), (ni_q, 3)):
        if pool:
            take = rng.choice(len(pool), min(k, len(pool)), replace=False)
            sample.extend(pool[i] for i in take)
print(f"sampled pairs: {len(sample)} (per barrier quartile x mover species)")

CELL = np.eye(3) * 1000.0
PBC = np.array([False, False, False])

results = []
t0 = time.time()
for idx_f, idx_b, ea, mover in sample:
    F = rt.loc[idx_f]
    min1 = np.array(F.initial_positions)
    sad = np.array(F.saddle_positions)
    min2 = np.array(F.final_positions)
    types = list(F.initial_types)
    masses = np.array([MASS[t] for t in types])
    central = int(F.move_atom_idx)
    free = select_free_indices(min1, central, FREE_RADIUS, CELL, PBC)
    eng = ClusterForces(min1, types, f"p{idx_f}")
    try:
        h1 = mass_weighted_partial_hessian(eng, min1, masses, free, FD_STEP)
        h2 = mass_weighted_partial_hessian(eng, min2, masses, free, FD_STEP)
        hs = mass_weighted_partial_hessian(eng, sad, masses, free, FD_STEP)
    finally:
        eng.close()
    ev1 = np.linalg.eigvalsh(h1)
    ev2 = np.linalg.eigvalsh(h2)
    if ev1.min() <= 0 or ev2.min() <= 0:
        results.append(dict(idx_f=idx_f, ok=False,
                            reason=f"non-positive minimum mode ({ev1.min():.2e}/{ev2.min():.2e})"))
        print(f"  pair {idx_f}: SKIP non-positive mode", flush=True)
        continue
    ln_r_state = 0.5 * (np.sum(np.log(ev1)) - np.sum(np.log(ev2)))
    nu0_f_re = vineyard_prefactor(h1, hs, n_zero_modes=0)
    nu0_b_re = vineyard_prefactor(h2, hs, n_zero_modes=0)
    r_harv = float(F.nu0) / float(rt.loc[idx_b].nu0)
    results.append(dict(idx_f=idx_f, idx_b=idx_b, ea=ea, mover=mover, ok=True,
                        n_free=len(free), ln_r_state=ln_r_state,
                        ln_r_harv=np.log(r_harv),
                        nu0_f_re=nu0_f_re, nu0_stored=float(F.nu0),
                        nu0_b_re=nu0_b_re))
    print(f"  pair {idx_f:3d} (Ea={ea:.2f}, {mover}, n_free={len(free)}): "
          f"R_state={np.exp(ln_r_state):.3f}  R_harv={r_harv:.3f}  "
          f"nu0_re={nu0_f_re / 1e12:.1f}THz vs stored {float(F.nu0) / 1e12:.1f}THz  "
          f"t={time.time() - t0:.0f}s", flush=True)

okr = [r for r in results if r["ok"]]
print(f"\n=== V4 summary (n={len(okr)} pairs measured, {len(results) - len(okr)} skipped) ===")
if okr:
    d = np.array([r["ln_r_state"] - r["ln_r_harv"] for r in okr])
    ratio_fac = np.exp(np.abs(d))
    print(f"  |ln R_state - ln R_harv|: median factor x{np.median(ratio_fac):.2f}  "
          f"q90 x{np.quantile(ratio_fac, 0.9):.2f}  max x{ratio_fac.max():.2f}")
    within2 = (ratio_fac <= 2.0).mean()
    print(f"  harvested ratio within x2 of per-state ratio: {100 * within2:.0f}%")
    rs = np.array([r["ln_r_state"] for r in okr])
    rh = np.array([r["ln_r_harv"] for r in okr])
    print(f"  corr(ln R_state, ln R_harv) = {np.corrcoef(rs, rh)[0, 1]:.3f}")
    print(f"  spread of per-state ratio itself: q10-q90 = "
          f"{np.exp(np.quantile(rs, 0.1)):.2f} - {np.exp(np.quantile(rs, 0.9)):.2f}")
    v = np.array([r["nu0_f_re"] / r["nu0_stored"] for r in okr if np.isfinite(r["nu0_f_re"])])
    if len(v):
        print(f"  harness/stored nu0_f: median x{np.median(v):.2f}  "
              f"q10-q90 x{np.quantile(v, 0.1):.2f}-x{np.quantile(v, 0.9):.2f} "
              f"(vacuum-cluster truncation gauge)")
    import csv
    with open("/home/kerr/pykmc/onlattice_design/v4_prefactor_results_2026-07-21.csv", "w",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(okr[0].keys()))
        w.writeheader()
        w.writerows(okr)
    print("per-pair artifact -> v4_prefactor_results_2026-07-21.csv")
