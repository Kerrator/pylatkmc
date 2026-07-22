"""Direct same-potential lattice-configuration evaluations for H(sigma) (memo 8-N3).

Builds FCC(001) Ni/Cr slabs at the production lattice constant, generates
endpoint PAIRS that differ by a lattice move (vacancy hop or Ni<->Cr swap),
minimizes both endpoints with the production potential + minimizer settings,
and records dE together with the 12 dPhi bond-count features of
H_sigma_v1_pair12. No pARTn search -- endpoint minima only.

Potential: /home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam  (eam/alloy,
type 1 = Cr, type 2 = Ni -- alphabetical, per the pair_coeff gotcha).
Minimizer: cg, 1e-10 1e-12 10000 10000 (= production input.in).
Guard: after minimization every atom must sit < 1.0 A from its assigned ideal
site and the occupation must project back to the intended sigma; else the
sample is discarded and counted.

Output: direct_evals_2026-07-21.csv (features + dE_eV + provenance columns).
Run: venv active, any cwd.
"""

import csv
import itertools
import sys
import time
from pathlib import Path

import numpy as np
from lammps import lammps

A0 = 3.524  # production box: 54.82057 / 22 * sqrt(2)
POT = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
SCRATCH = Path("/tmp/claude-1000/-home-kerr-pykmc/1f3a6d40-a9b5-42dd-acfd-ceab36fa20bc/scratchpad")
OUT = Path("/home/kerr/pykmc/onlattice_design/direct_evals_2026-07-21.csv")
RNG = np.random.default_rng(20260721)

NX, NY, NZ = 7, 7, 8  # conventional cells; (001) slab, vacuum above
VAC_Z = 22.0

FEATS = (
    ["pt_NI", "pt_CR"]
    + [f"b1_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
    + [f"b2_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
)

# ---- ideal lattice ----
base = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]
sites = []
for i, j, k in itertools.product(range(NX), range(NY), range(NZ)):
    for b in base:
        sites.append(((i + b[0]) * A0, (j + b[1]) * A0, (k + b[2]) * A0))
sites = np.array(sites)
NS = len(sites)
LX, LY = NX * A0, NY * A0
LZ = NZ * A0 + VAC_Z
zmax = sites[:, 2].max()

# neighbour lists on the ideal lattice (pbc x,y only)
def _pdiff(a, b):
    d = a - b
    d[0] -= LX * round(d[0] / LX)
    d[1] -= LY * round(d[1] / LY)
    return d

d1, d2 = A0 / np.sqrt(2.0), A0
nb1 = [[] for _ in range(NS)]
nb2 = [[] for _ in range(NS)]
cell = {}
for idx, s in enumerate(sites):
    key = tuple((s // (A0 * 1.01)).astype(int))
    cell.setdefault(key, []).append(idx)
for idx, s in enumerate(sites):
    key = tuple((s // (A0 * 1.01)).astype(int))
    for dk in itertools.product((-1, 0, 1), repeat=3):
        k2 = ((key[0] + dk[0]) % max(NX, 1), (key[1] + dk[1]) % max(NY, 1), key[2] + dk[2])
        for j in cell.get(k2, []):
            if j <= idx:
                continue
            r = np.linalg.norm(_pdiff(sites[idx], sites[j]))
            if abs(r - d1) < 0.3:
                nb1[idx].append(j)
                nb1[j].append(idx)
            elif abs(r - d2) < 0.3:
                nb2[idx].append(j)
                nb2[j].append(idx)
co1 = [len(n) for n in nb1]
print(f"sites={NS}  1nn coord: bulk={max(co1)} surface-min={min(co1)}", flush=True)

# ---- occupation state: array of 'N','C',' ' (vacant) over sites ----
def bond_counts(occ):
    v = {k: 0.0 for k in FEATS}
    for k, sp in enumerate(occ):
        if sp == "N":
            v["pt_NI"] += 1
        elif sp == "C":
            v["pt_CR"] += 1
    for shell, nb in ((1, nb1), (2, nb2)):
        for i in range(NS):
            a = occ[i]
            if a == " ":
                continue
            for j in nb[i]:
                if j <= i:
                    continue
                b = occ[j]
                if b == " ":
                    continue
                key = f"b{shell}_" + "".join(sorted(a + b, key=lambda s: "NC".index(s)))
                v[key] += 1
    return v


def dphi_local(occA, occB, changed):
    """Feature difference B-A, computed only around changed sites (fast)."""
    v = {k: 0.0 for k in FEATS}
    for i in changed:
        for occ, sgn in ((occB, +1), (occA, -1)):
            if occ[i] == "N":
                v["pt_NI"] += sgn
            elif occ[i] == "C":
                v["pt_CR"] += sgn
        for shell, nb in ((1, nb1), (2, nb2)):
            for j in nb[i]:
                if j in changed and j < i:
                    continue
                for occ, sgn in ((occB, +1), (occA, -1)):
                    a, b = occ[i], occ[j]
                    if a == " " or b == " ":
                        continue
                    key = f"b{shell}_" + "".join(sorted(a + b, key=lambda s: "NC".index(s)))
                    v[key] += sgn
    return v


# ---- LAMMPS eval ----
def write_data(path, occ):
    idxs = [i for i in range(NS) if occ[i] != " "]
    with open(path, "w") as fh:
        fh.write("direct eval\n\n")
        fh.write(f"{len(idxs)} atoms\n2 atom types\n\n")
        fh.write(f"0.0 {LX} xlo xhi\n0.0 {LY} ylo yhi\n{-VAC_Z / 2} {LZ - VAC_Z / 2} zlo zhi\n\n")
        fh.write("Masses\n\n1 51.996\n2 58.71\n\nAtoms # atomic\n\n")
        for n, i in enumerate(idxs, 1):
            t = 1 if occ[i] == "C" else 2
            x, y, z = sites[i]
            fh.write(f"{n} {t} {x:.6f} {y:.6f} {z:.6f}\n")
    return idxs


def minimize(occ, tag):
    """Returns (energy, ok) with the projection guard."""
    data = SCRATCH / f"de_{tag}.data"
    idxs = write_data(data, occ)
    lmp = lammps(cmdargs=["-log", "none", "-screen", "none"])
    lmp.commands_string(
        f"""
units metal
boundary p p p
atom_style atomic
read_data {data}
pair_style eam/alloy
pair_coeff * * {POT} Cr Ni
min_style cg
minimize 1.0e-10 1.0e-12 10000 10000
"""
    )
    e = lmp.get_thermo("pe")
    x = np.array(lmp.gather_atoms("x", 1, 3)).reshape(-1, 3)
    lmp.close()
    # projection guard: order preserved by gather (id order = write order)
    ok = True
    for n, i in enumerate(idxs):
        d = _pdiff(x[n], sites[i])
        if np.linalg.norm([d[0], d[1], x[n][2] - sites[i][2]]) > 1.0:
            ok = False
            break
    return e, ok


# ---- template variants ----
def make_occ(cr_frac, seed, enrich_top=None, clusters=0):
    r = np.random.default_rng(seed)
    occ = np.full(NS, "N", dtype="U1")
    n_cr = int(round(cr_frac * NS))
    occ[r.choice(NS, n_cr, replace=False)] = "C"
    if enrich_top is not None:
        frac, nlayers = enrich_top
        zcut = zmax - (nlayers - 0.5) * A0 / 2
        top = [i for i in range(NS) if sites[i][2] > zcut]
        for i in top:
            if r.random() < frac:
                occ[i] = "C"
    for _ in range(clusters):
        c0 = int(r.integers(NS))
        occ[c0] = "C"
        for j in nb1[c0][:2]:
            occ[j] = "C"
    return occ


VARIANTS = {
    "v0_cr05_s1": make_occ(0.05, 1),
    "v1_cr05_s2": make_occ(0.05, 2),
    "v2_cr10": make_occ(0.10, 3),
    "v3_front": make_occ(0.05, 4, enrich_top=(0.20, 3)),
    "v4_clusters": make_occ(0.05, 5, clusters=5),
    "v5_pureNi": np.full(NS, "N", dtype="U1"),
}

surface_ids = [i for i in range(NS) if abs(sites[i][2] - zmax) < 0.1]
sub_ids = [i for i in range(NS) if abs(sites[i][2] - (zmax - A0 / 2)) < 0.1]
bulk_ids = [i for i in range(NS) if abs(sites[i][2] - zmax / 2) < A0 / 2]

rows_out = []
n_discard = 0
t0 = time.time()

for vname, occ0 in VARIANTS.items():
    r = np.random.default_rng(hash(vname) % 2**32)
    # vacancy placements: bulk, subsurface, surface, near-Cr (bulk)
    vac_picks = [
        ("bulk", int(r.choice(bulk_ids))),
        ("subsurf", int(r.choice(sub_ids))),
        ("surface", int(r.choice(surface_ids))),
    ]
    cr_adj = [i for i in bulk_ids if any(occ0[j] == "C" for j in nb1[i])]
    if cr_adj:
        vac_picks.append(("nearCr", int(r.choice(cr_adj))))
    for where, vs in vac_picks:
        occA = occ0.copy()
        occA[vs] = " "
        eA, okA = minimize(occA, f"{vname}_{where}_A")
        if not okA:
            n_discard += 1
            print(f"  DISCARD A {vname}/{where}", flush=True)
            continue
        # hop moves: up to 6 occupied 1nn, prefer species diversity
        occ_nb = [j for j in nb1[vs] if occA[j] != " "]
        cr_nb = [j for j in occ_nb if occA[j] == "C"]
        ni_nb = [j for j in occ_nb if occA[j] == "N"]
        picks = (cr_nb[:3] + ni_nb)[:6]
        for j in picks:
            occB = occA.copy()
            occB[vs] = occA[j]
            occB[j] = " "
            eB, okB = minimize(occB, f"{vname}_{where}_hop{j}")
            if not okB:
                n_discard += 1
                continue
            v = dphi_local(occA, occB, {vs, j})
            rows_out.append(
                dict(v, dE_eV=eB - eA, kind="hop", variant=vname, where=where,
                     mover=occA[j], site=vs)
            )
        # swaps from this A config (bulk placement only, reuse eA)
        if where == "bulk":
            cr_sites = [i for i in range(NS) if occA[i] == "C"]
            r.shuffle(cr_sites)
            for ci in cr_sites[:8]:
                # swap with a random Ni 1nn (local) or a random far Ni
                local = [j for j in nb1[ci] if occA[j] == "N"]
                far = [j for j in range(NS) if occA[j] == "N"]
                tgt = int(r.choice(local)) if (local and r.random() < 0.6) else int(r.choice(far))
                occB = occA.copy()
                occB[ci], occB[tgt] = occB[tgt], occB[ci]
                eB, okB = minimize(occB, f"{vname}_swap{ci}_{tgt}")
                if not okB:
                    n_discard += 1
                    continue
                v = dphi_local(occA, occB, {ci, tgt})
                rows_out.append(
                    dict(v, dE_eV=eB - eA, kind="swap", variant=vname, where="bulkA",
                         mover="X", site=ci)
                )
    print(f"[{vname}] done, rows={len(rows_out)}  discards={n_discard}  "
          f"t={time.time() - t0:.0f}s", flush=True)

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FEATS + ["dE_eV", "kind", "variant", "where", "mover", "site"])
    w.writeheader()
    for row in rows_out:
        w.writerow(row)
print(f"wrote {len(rows_out)} evals -> {OUT}  (discarded {n_discard})", flush=True)
