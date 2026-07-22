"""H(sigma) lattice energy model -- Phase C first leg (V2 gate).

Fits a cluster-expansion-style local energy model on lattice occupations:
point terms (per-species counts) + 1nn/2nn pair terms (species-pair bond
counts), so that  dE_H(event) = dPhi(sigma_before -> sigma_after) . theta.

Training channels (memo section 8-N3: same-potential pyKMC data ONLY):
  A. harvested linked-pair dE (445 events, this script)
  B. + direct same-potential LAMMPS evaluations (direct_evals CSV, if present)

Holdout: 10-fold CV split by PAIR-GROUP (forward/backward classes of one
physical pair share a fold -- class-level split would leak dE = -dE_bwd),
nested alpha. Pure numpy.

Run from inside ~/pykmc/pylatkmc (venv active):
  python ~/pykmc/onlattice_design/h_sigma_fit_2026-07-21.py

Conditions: catalogue_full_rcut8p5.parquet, production NiCr verify_fix_T500_1vac,
rcut 8.5 A, 439 classes / 445 events, T_ref = 500 K.
dE_model_version = H_sigma_v1_pair12 (channel A) / H_sigma_v1_pair12_aug (A+B).
"""

import csv
import itertools
import sys
from pathlib import Path

import numpy as np

from pylatkmc.ingest.event_class import read_catalogue_parquet

RNG_SEED = 20260721
KB_T = 8.6173e-5 * 500.0

DIRECT_CSV = Path("/home/kerr/pykmc/onlattice_design/direct_evals_2026-07-21.csv")

cat = read_catalogue_parquet(".scratch/phaseB/catalogue_full_rcut8p5.parquet")
by_id = {c.class_id: c for c in cat}

# ---- pair groups (union-find over backward links) ----
parent = {c.class_id: c.class_id for c in cat}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for c in cat:
    if c.backward_class in parent:
        ra, rb = find(c.class_id), find(c.backward_class)
        if ra != rb:
            parent[ra] = rb

group_of = {c.class_id: find(c.class_id) for c in cat}

# ---- quarantine sets ----
# (i) delta-less classes: dPhi == 0 identically, dE_H == 0 by construction
NO_DELTA = {c.class_id for c in cat if not c.delta}
# (ii) broken reciprocity: |dE_f + dE_b| > 0 -> mis-linked pair or self-link artifact
MISLINK = set()
for c in cat:
    b = by_id.get(c.backward_class)
    if b is not None and abs(c.dEnergy_eV + b.dEnergy_eV) > 1e-9:
        MISLINK.add(c.class_id)
print(f"quarantine candidates: no-delta={len(NO_DELTA)}  broken-reciprocity={len(MISLINK)}")

# ---- dPhi features: state-function difference on the local pattern ----
# 1nn: |off|^2 == 2 (12 nb), 2nn: |off|^2 == 4 (6 nb) in the tetragonal embedding.
NN1 = [o for o in itertools.product(range(-2, 3), repeat=3) if sum(x * x for x in o) == 2]
NN2 = [o for o in itertools.product(range(-2, 3), repeat=3) if sum(x * x for x in o) == 4]

FEATS = (
    ["pt_NI", "pt_CR"]
    + [f"b1_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
    + [f"b2_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
)
FIDX = {k: i for i, k in enumerate(FEATS)}


def occ_cat(pred):
    if pred.kind == "EMPTY":
        return "E"
    if pred.kind == "OUTSIDE":
        return "U"
    (sp,) = pred.species
    return "N" if sp.name == "NI" else "C"


def state_maps(c):
    """(before, after) occupancy category maps over the stencil."""
    base = {s.off: occ_cat(s.pred) for s in c.context}
    before, after = dict(base), dict(base)
    for d in c.delta:
        before[d.off] = {"NI": "N", "CR": "C", "EMPTY": "E"}[d.before.name]
        after[d.off] = {"NI": "N", "CR": "C", "EMPTY": "E"}[d.after.name]
    return before, after


def bond_key(shell, a, b):
    """Species-pair bond feature key; EMPTY bonds contribute nothing."""
    if a == "E" or b == "E":
        return None
    if a == "U" and b == "U":
        return None  # both unknown: unresolvable, dropped (counted)
    if a == "U" or b == "U":
        sp = a if b == "U" else b
        return f"b{shell}_{sp}U"
    return f"b{shell}_" + "".join(sorted((a, b), key=lambda s: "NC".index(s)))


N_UU = 0


def dphi(c):
    """Phi(after) - Phi(before); only terms touching a delta site survive."""
    global N_UU
    before, after, = state_maps(c)
    dset = {d.off for d in c.delta}
    v = np.zeros(len(FEATS))
    for d in c.delta:
        for cat_, sgn in ((after[d.off], +1), (before[d.off], -1)):
            if cat_ == "N":
                v[FIDX["pt_NI"]] += sgn
            elif cat_ == "C":
                v[FIDX["pt_CR"]] += sgn
        for shell, offs in ((1, NN1), (2, NN2)):
            for o in offs:
                n = tuple(a + b for a, b in zip(d.off, o))
                # pair (d.off, n): if n is also a delta site, count each pair once
                if n in dset and n < d.off:
                    continue
                for m, sgn in ((after, +1), (before, -1)):
                    nc = m.get(n, "U")  # missing-from-stencil -> unknown
                    k = bond_key(shell, m[d.off], nc)
                    if k is None:
                        if m[d.off] == "U" and nc == "U":
                            N_UU += 1
                        continue
                    v[FIDX[k]] += sgn
    return v


rows, y, grp, cid = [], [], [], []
for c in cat:
    v = dphi(c)
    for d_e in c.dE_pair_list_eV:
        rows.append(v)
        y.append(d_e)
        grp.append(group_of[c.class_id])
        cid.append(c.class_id)

X = np.array(rows)
y = np.array(y)
grp = np.array(grp)
cid = np.array(cid)
print(f"n_events={len(y)}  n_features={X.shape[1]}  null_rmse(dE)={y.std():.3f}")
print(f"feature column L1 norms: {dict(zip(FEATS, np.abs(X).sum(0).astype(int)))}")

# ---- optional channel B: direct LAMMPS evaluations ----
Xd, yd = None, None
if DIRECT_CSV.exists():
    feats_d, y_d = [], []
    with open(DIRECT_CSV) as fh:
        for r in csv.DictReader(fh):
            feats_d.append([float(r[k]) for k in FEATS])
            y_d.append(float(r["dE_eV"]))
    Xd, yd = np.array(feats_d), np.array(y_d)
    print(f"direct-eval channel: n={len(yd)}  dE range [{yd.min():.3f}, {yd.max():.3f}]")


# ---- ridge (no intercept: dE is antisymmetric; dPhi -> -dPhi flips dE) ----
def ridge_fit(Xtr, ytr, alpha, w=None):
    if w is None:
        w = np.ones(len(ytr))
    sw = np.sqrt(w)[:, None]
    A = (Xtr * sw).T @ (Xtr * sw) + alpha * np.eye(Xtr.shape[1])
    return np.linalg.solve(A, (Xtr * sw).T @ (ytr * np.sqrt(w)))


def cv_by_group(X, y, grp, alphas, aug=None, n_folds=10, seed=0, aug_weight=1.0):
    """Group-level CV; aug=(Xd,yd) is appended to every training fold."""
    groups = np.unique(grp)
    rng = np.random.default_rng(seed)
    folds = np.array_split(rng.permutation(groups), n_folds)
    yhat = np.full_like(y, np.nan)
    for fold in folds:
        te = np.isin(grp, fold)
        tr = ~te
        best, best_rmse = None, np.inf
        tr_groups = np.unique(grp[tr])
        inner = np.array_split(rng.permutation(tr_groups), 5)
        for a in alphas:
            errs = []
            for ifold in inner:
                ite = np.isin(grp, ifold) & tr
                itr = tr & ~ite
                Xt, yt = X[itr], y[itr]
                wt = np.ones(len(yt))
                if aug is not None:
                    Xt = np.vstack([Xt, aug[0]])
                    yt = np.concatenate([yt, aug[1]])
                    wt = np.concatenate([wt, np.full(len(aug[1]), aug_weight)])
                th = ridge_fit(Xt, yt, a, wt)
                errs.append(X[ite] @ th - y[ite])
            r = np.sqrt(np.mean(np.concatenate(errs) ** 2))
            if r < best_rmse:
                best_rmse, best = r, a
        Xt, yt = X[tr], y[tr]
        wt = np.ones(len(yt))
        if aug is not None:
            Xt = np.vstack([Xt, aug[0]])
            yt = np.concatenate([yt, aug[1]])
            wt = np.concatenate([wt, np.full(len(aug[1]), aug_weight)])
        th = ridge_fit(Xt, yt, best, wt)
        yhat[te] = X[te] @ th
    return yhat


ALPHAS = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]

quarantined = np.isin(cid, list(NO_DELTA | MISLINK))
clean = ~quarantined
print(f"\nevents: total={len(y)}  quarantined={quarantined.sum()}  clean={clean.sum()}")
print(f"unresolved U-U bond pairs skipped: {N_UU}")


def v2_report(tag, yhat, mask):
    m = mask & ~np.isnan(yhat)
    ae = np.abs(yhat[m] - y[m])
    print(
        f"  {tag:44s} n={m.sum():3d}  median|dE_H-dE|={np.median(ae):.3f} eV  "
        f"mean={ae.mean():.3f}  q75={np.quantile(ae, 0.75):.3f}  "
        f"q90={np.quantile(ae, 0.9):.3f}  RMSE={np.sqrt(np.mean(ae**2)):.3f}"
    )


print("\n=== H(sigma) channel A: harvested-only (dE_model_version=H_sigma_v1_pair12) ===")
yhatA = cv_by_group(X, y, grp, ALPHAS, seed=11)
v2_report("V2 all events", yhatA, np.ones_like(y, bool))
v2_report("V2 excl. quarantine (no-delta + mislink)", yhatA, clean)

# clean-hop cut for context (same def as ridge_anchor)
clean_hop = []
for c in cat:
    ch = (
        len(c.delta) == 2
        and c.delta_atoms == 0
        and sorted(d.before.name for d in c.delta) in (["EMPTY", "NI"], ["CR", "EMPTY"])
    )
    clean_hop.extend([ch] * len(c.dE_pair_list_eV))
clean_hop = np.array(clean_hop)
v2_report("V2 clean 2-site hops", yhatA, clean_hop & clean)
v2_report("V2 multi-site/non-conservative (clean)", yhatA, ~clean_hop & clean)

if Xd is not None:
    print("\n=== H(sigma) channel A+B: augmented (dE_model_version=H_sigma_v1_pair12_aug) ===")
    for aw in (1.0,):
        yhatB = cv_by_group(X, y, grp, ALPHAS, aug=(Xd, yd), seed=11, aug_weight=aw)
        v2_report(f"V2 all events (aug w={aw})", yhatB, np.ones_like(y, bool))
        v2_report("V2 excl. quarantine", yhatB, clean)
        v2_report("V2 clean 2-site hops", yhatB, clean_hop & clean)
        v2_report("V2 multi-site/non-conservative (clean)", yhatB, ~clean_hop & clean)
    # direct-eval self-fit sanity: how well does the pair model explain LAMMPS dE?
    thd = ridge_fit(Xd, yd, 0.1)
    rd = Xd @ thd - yd
    print(f"  direct-eval self-fit RMSE: {np.sqrt(np.mean(rd**2)):.4f} eV (n={len(yd)})")

# final production fit on ALL clean data (+aug if present), stamped
Xt, yt = X[clean], y[clean]
wt = np.ones(len(yt))
ver = "H_sigma_v1_pair12"
if Xd is not None:
    Xt = np.vstack([Xt, Xd])
    yt = np.concatenate([yt, yd])
    wt = np.concatenate([wt, np.ones(len(yd))])
    ver = "H_sigma_v1_pair12_aug"
# alpha by 5-fold group CV on the clean harvested part -- reuse best from holdout runs
theta = ridge_fit(Xt, yt, 0.1, wt)
out = Path("/home/kerr/pykmc/onlattice_design/H_sigma_theta_2026-07-21.csv")
with open(out, "w") as fh:
    fh.write(f"# dE_model_version={ver}  fit 2026-07-21, alpha=0.1, clean harvested"
             f"{' + direct evals' if Xd is not None else ''}\n")
    fh.write("feature,theta_eV\n")
    for k, t in zip(FEATS, theta):
        fh.write(f"{k},{t:.6f}\n")
print(f"\nstamped {ver} -> {out}")
print("theta:", {k: round(float(t), 4) for k, t in zip(FEATS, theta)})

# per-event predictions artifact for downstream V3 (holdout, channel A and B)
outp = Path("/home/kerr/pykmc/onlattice_design/H_sigma_holdout_pred_2026-07-21.csv")
with open(outp, "w") as fh:
    fh.write("class_id,dE_meas,dE_H_A" + (",dE_H_B" if Xd is not None else "") + ",quarantined\n")
    for i in range(len(y)):
        row = f"{cid[i]},{y[i]:.6f},{yhatA[i]:.6f}"
        if Xd is not None:
            row += f",{yhatB[i]:.6f}"
        fh.write(row + f",{int(quarantined[i])}\n")
print(f"holdout predictions -> {outp}")
