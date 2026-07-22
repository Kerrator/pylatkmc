"""Direct same-potential lattice evaluations, campaign v2 (memo 8-N3).

Supersedes direct_evals_2026-07-21.py / .csv (kept as record): that campaign
used salted-hash RNG seeds (not reproducible) and emitted only the pair12
basis. This one is deterministic, emits BOTH candidate H(sigma) bases per
eval, and records the occupation pair (Cr site indices + vacancy index) for
full provenance.

Bases:
  v1 "pair12":     point + 1nn/2nn species-pair bond counts (12 features)
  v2 "surfsplit":  bond counts split by endpoint surface exposure
                   (surface := >= 3 EMPTY/vacuum among the 12 1nn), the
                   exposure reclassification of neighbours included -- still
                   a pure function of sigma (higher-order occupancy terms).

Potential + minimizer: production (NiFeCr_LKB2017.eam, type1=Cr type2=Ni,
cg 1e-10 1e-12). Guard: post-minimize projection < 1.0 A. Slab 7x7x8 FCC(001)
cells @ a0=3.524 + 22 A vacuum (production a0).

Output: direct_evals_v2_2026-07-21.csv
Run: venv active, any cwd. Deterministic (seed 20260721).
"""

import csv
import itertools
import time
from pathlib import Path

import numpy as np
from lammps import lammps

A0 = 3.524
POT = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
SCRATCH = Path("/tmp/claude-1000/-home-kerr-pykmc/1f3a6d40-a9b5-42dd-acfd-ceab36fa20bc/scratchpad")
OUT = Path("/home/kerr/pykmc/onlattice_design/direct_evals_v2_2026-07-21.csv")

NX, NY, NZ = 7, 7, 8
VAC_Z = 22.0

V1FEATS = (["pt_NI", "pt_CR"]
           + [f"b1_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
           + [f"b2_{p}" for p in ("NN", "NC", "CC", "NU", "CU")])
V2FEATS = (["pt_NI", "pt_CR"]
           + [f"b1{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
           + [f"b2{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
           + ["b1_NU", "b1_CU", "b2_NU", "b2_CU"])

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
    cell.setdefault(tuple((s // (A0 * 1.01)).astype(int)), []).append(idx)
for idx, s in enumerate(sites):
    key = tuple((s // (A0 * 1.01)).astype(int))
    for dk in itertools.product((-1, 0, 1), repeat=3):
        k2 = ((key[0] + dk[0]) % NX, (key[1] + dk[1]) % NY, key[2] + dk[2])
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
print(f"sites={NS}", flush=True)


def empty_coord(occ, i):
    """EMPTY/vacuum count among the 12 geometric 1nn of site i."""
    return sum(1 for j in nb1[i] if occ[j] == " ") + (12 - len(nb1[i]))


def sp_key(a, b):
    return "".join(sorted(a + b, key=lambda s: "NC".index(s)))


def dphi_v1(occA, occB, changed):
    v = {}
    for i in changed:
        for occ, sgn in ((occB, +1), (occA, -1)):
            if occ[i] == "N":
                v["pt_NI"] = v.get("pt_NI", 0) + sgn
            elif occ[i] == "C":
                v["pt_CR"] = v.get("pt_CR", 0) + sgn
        for shell, nbs in ((1, nb1), (2, nb2)):
            for j in nbs[i]:
                if j in changed and j < i:
                    continue
                for occ, sgn in ((occB, +1), (occA, -1)):
                    a, b = occ[i], occ[j]
                    if a == " " or b == " ":
                        continue
                    k = f"b{shell}_" + sp_key(a, b)
                    v[k] = v.get(k, 0) + sgn
    return v


def dphi_v2(occA, occB, changed):
    v = {}

    def add(k, x):
        v[k] = v.get(k, 0) + x

    aff = set()
    for i in changed:
        for j in nb1[i]:
            aff.add(j)
    aff -= set(changed)
    for occ, sgn in ((occB, +1), (occA, -1)):
        for i in changed:
            if occ[i] == " ":
                continue
            for shell, nbs in ((1, nb1), (2, nb2)):
                for j in nbs[i]:
                    if j in changed and j < i:
                        continue
                    if occ[j] == " ":
                        continue
                    surf = (empty_coord(occ, i) >= 3) or (empty_coord(occ, j) >= 3)
                    add(f"b{shell}{'S' if surf else 'B'}_" + sp_key(occ[i], occ[j]), sgn)
            if occ[i] == "N":
                add("pt_NI", sgn)
            elif occ[i] == "C":
                add("pt_CR", sgn)
        for i in aff:
            if occ[i] == " ":
                continue
            for shell, nbs in ((1, nb1), (2, nb2)):
                for j in nbs[i]:
                    if j in changed or (j in aff and j < i):
                        continue
                    if occ[j] == " ":
                        continue
                    surf = (empty_coord(occ, i) >= 3) or (empty_coord(occ, j) >= 3)
                    add(f"b{shell}{'S' if surf else 'B'}_" + sp_key(occ[i], occ[j]), sgn)
    return v


def write_data(path, occ):
    idxs = [i for i in range(NS) if occ[i] != " "]
    with open(path, "w") as fh:
        fh.write("direct eval v2\n\n")
        fh.write(f"{len(idxs)} atoms\n2 atom types\n\n")
        fh.write(f"0.0 {LX} xlo xhi\n0.0 {LY} ylo yhi\n{-VAC_Z / 2} {LZ - VAC_Z / 2} zlo zhi\n\n")
        fh.write("Masses\n\n1 51.996\n2 58.71\n\nAtoms # atomic\n\n")
        for n, i in enumerate(idxs, 1):
            t = 1 if occ[i] == "C" else 2
            fh.write(f"{n} {t} {sites[i][0]:.6f} {sites[i][1]:.6f} {sites[i][2]:.6f}\n")
    return idxs


def minimize(occ, tag):
    data = SCRATCH / f"dev2_{tag}.data"
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
    ok = True
    for n, i in enumerate(idxs):
        d = _pdiff(x[n], sites[i])
        if np.linalg.norm([d[0], d[1], x[n][2] - sites[i][2]]) > 1.0:
            ok = False
            break
    return e, ok


def occ_sig(occ):
    cr = [str(i) for i in range(NS) if occ[i] == "C"]
    vac = [str(i) for i in range(NS) if occ[i] == " "]
    return "cr:" + "|".join(cr) + ";vac:" + "|".join(vac)


def make_occ(cr_frac, seed, enrich_top=None, clusters=0):
    r = np.random.default_rng(seed)
    occ = np.full(NS, "N", dtype="U1")
    n_cr = int(round(cr_frac * NS))
    if n_cr:
        occ[r.choice(NS, n_cr, replace=False)] = "C"
    if enrich_top is not None:
        frac, nlayers = enrich_top
        zcut = zmax - (nlayers - 0.5) * A0 / 2
        for i in range(NS):
            if sites[i][2] > zcut and r.random() < frac:
                occ[i] = "C"
    for _ in range(clusters):
        c0 = int(r.integers(NS))
        occ[c0] = "C"
        for j in nb1[c0][:2]:
            occ[j] = "C"
    return occ


VARIANTS = [
    ("v0_cr05_s1", make_occ(0.05, 101)),
    ("v1_cr05_s2", make_occ(0.05, 102)),
    ("v2_cr10", make_occ(0.10, 103)),
    ("v3_front", make_occ(0.05, 104, enrich_top=(0.20, 3))),
    ("v4_clusters", make_occ(0.05, 105, clusters=5)),
    ("v5_pureNi", np.full(NS, "N", dtype="U1")),
]

surface_ids = [i for i in range(NS) if abs(sites[i][2] - zmax) < 0.1]
sub_ids = [i for i in range(NS) if abs(sites[i][2] - (zmax - A0 / 2)) < 0.1]
sub2_ids = [i for i in range(NS) if abs(sites[i][2] - (zmax - A0)) < 0.1]
bulk_ids = [i for i in range(NS) if abs(sites[i][2] - zmax / 2) < A0 / 2]

rows_out = []
n_discard = 0
t0 = time.time()

for vidx, (vname, occ0) in enumerate(VARIANTS):
    r = np.random.default_rng([20260721, vidx])
    placements = [
        ("bulk", int(r.choice(bulk_ids))),
        ("subsurf", int(r.choice(sub_ids))),
        ("sub2", int(r.choice(sub2_ids))),
        ("surface", int(r.choice(surface_ids))),
    ]
    cr_adj_b = [i for i in bulk_ids if any(occ0[j] == "C" for j in nb1[i])]
    cr_adj_s = [i for i in sub_ids if any(occ0[j] == "C" for j in nb1[i])]
    if cr_adj_b:
        placements.append(("nearCr_b", int(r.choice(cr_adj_b))))
    if cr_adj_s:
        placements.append(("nearCr_s", int(r.choice(cr_adj_s))))
    for where, vs in placements:
        occA = occ0.copy()
        occA[vs] = " "
        eA, okA = minimize(occA, f"{vname}_{where}_A")
        if not okA:
            n_discard += 1
            print(f"  DISCARD A {vname}/{where}", flush=True)
            continue
        occ_nb = [j for j in nb1[vs] if occA[j] != " "]
        picks = ([j for j in occ_nb if occA[j] == "C"][:3]
                 + [j for j in occ_nb if occA[j] == "N"])[:6]
        for j in picks:
            occB = occA.copy()
            occB[vs] = occA[j]
            occB[j] = " "
            eB, okB = minimize(occB, f"{vname}_{where}_hop{j}")
            if not okB:
                n_discard += 1
                continue
            rows_out.append((dphi_v1(occA, occB, {vs, j}), dphi_v2(occA, occB, {vs, j}),
                             eB - eA, eA, "hop", vname, where, occA[j], occ_sig(occA)))
        if where == "bulk" and vname != "v5_pureNi":
            cr_sites = [i for i in range(NS) if occA[i] == "C"]
            r.shuffle(cr_sites)
            for ci in cr_sites[:8]:
                local = [j for j in nb1[ci] if occA[j] == "N"]
                tgt = (int(r.choice(local)) if (local and r.random() < 0.6)
                       else int(r.choice([j for j in range(NS) if occA[j] == "N"])))
                occB = occA.copy()
                occB[ci], occB[tgt] = occB[tgt], occB[ci]
                eB, okB = minimize(occB, f"{vname}_swap{ci}_{tgt}")
                if not okB:
                    n_discard += 1
                    continue
                rows_out.append((dphi_v1(occA, occB, {ci, tgt}), dphi_v2(occA, occB, {ci, tgt}),
                                 eB - eA, eA, "swap", vname, "bulkA", "X", occ_sig(occA)))
    print(f"[{vname}] rows={len(rows_out)} discards={n_discard} t={time.time() - t0:.0f}s",
          flush=True)

with open(OUT, "w", newline="") as fh:
    cols = ([f"v1_{k}" for k in V1FEATS] + [f"v2_{k}" for k in V2FEATS]
            + ["dE_eV", "E_A_eV", "kind", "variant", "where", "mover", "occA_sig"])
    w = csv.writer(fh)
    w.writerow(cols)
    for f1, f2, dE, eA, kind, vname, where, mover, sig in rows_out:
        w.writerow([f1.get(k, 0) for k in V1FEATS] + [f2.get(k, 0) for k in V2FEATS]
                   + [f"{dE:.8f}", f"{eA:.6f}", kind, vname, where, mover, sig])
print(f"wrote {len(rows_out)} evals -> {OUT}  (discarded {n_discard})", flush=True)
