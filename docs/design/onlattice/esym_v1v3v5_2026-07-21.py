"""E_sym fit + gates V1 / V3 / V5 -- Phase C first leg.

E_sym: ridge regression of the symmetric barrier component  Esym = Ea - 0.5*dE
(= (Ea_f+Ea_b)/2 on linked pairs, identical for the two directions) on
ENDPOINT-EXCHANGE-SYMMETRIZED one-hot occupation features:
  f_sym = 0.5 * (f(sigma_before) + f(sigma_after))
so the surrogate is DB-safe by construction. Basis: <=2-body (per-shell
per-category counts, 1nn bond counts, mover-local broken bonds, scalars)
+ selected 3-body (mover-adjacent 1nn triangles by species pair).

Holdout everywhere: 10-fold CV by PAIR-GROUP (fwd/bwd share a fold -- the
Esym target is identical for the two directions, so a class-level split
would leak the answer), nested alpha. The SAME fold partition drives the
H(sigma) CV so V3's end-to-end surrogate  Ea_hat = Esym_hat + 0.5*dE_H_hat
is holdout in both factors.

V1: learning curve N=100..445 (pair-group subsamples), clean-hop holdout RMSE
    vs N + sqrt(floor^2 + k/N) extrapolation against the 0.10 eV acceptance.
V3: tail gate (lowest-quartile measured Ea): signed bias vs kT, tail Spearman
    vs 0.9, Cr-mover breakout -- for the FULL surrogate (predicted dE).
V5: ridge leverage in the E_sym feature space vs realized holdout error;
    gate-firing check on Cr-enriched environments + leave-out-Cr-rich probe.

Run from inside ~/pykmc/pylatkmc (venv active).
Conditions: catalogue_full_rcut8p5.parquet, verify_fix_T500_1vac, rcut 8.5 A,
439 classes / 445 events / 222 pair groups, T_ref = 500 K (kT = 0.0431 eV).
model_version = E_sym_v1_ridge_sym2b3b.
"""

import csv
import itertools
from pathlib import Path

import numpy as np

from pylatkmc.ingest.event_class import read_catalogue_parquet

KB_T = 8.6173e-5 * 500.0
DIRECT_CSV = Path("/home/kerr/pykmc/onlattice_design/direct_evals_v2_2026-07-21.csv")

cat = read_catalogue_parquet(".scratch/phaseB/catalogue_full_rcut8p5.parquet")
by_id = {c.class_id: c for c in cat}

# ---- pair groups ----
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

NO_DELTA = {c.class_id for c in cat if not c.delta}
MISLINK = set()
for c in cat:
    b = by_id.get(c.backward_class)
    if b is not None and abs(c.dEnergy_eV + b.dEnergy_eV) > 1e-9:
        MISLINK.add(c.class_id)

# ---- geometry ----
NN1 = [o for o in itertools.product(range(-2, 3), repeat=3) if sum(x * x for x in o) == 2]
NN2 = [o for o in itertools.product(range(-2, 3), repeat=3) if sum(x * x for x in o) == 4]
SHELLS = [2, 4, 6, 8, 10, 12, 14, 16, 18]


def shell_of(off):
    r2 = sum(o * o for o in off)
    return SHELLS.index(r2) if r2 in SHELLS else len(SHELLS)


def occ_cat(pred):
    if pred.kind == "EMPTY":
        return "E"
    if pred.kind == "OUTSIDE":
        return "U"
    (sp,) = pred.species
    return "N" if sp.name == "NI" else "C"


OCCC = {"NI": "N", "CR": "C", "EMPTY": "E"}


def state_maps(c):
    base = {s.off: occ_cat(s.pred) for s in c.context}
    before, after = dict(base), dict(base)
    for d in c.delta:
        before[d.off] = OCCC[d.before.name]
        after[d.off] = OCCC[d.after.name]
    return before, after


def state_features(m, movers, offs_nn1_cache):
    """One-hot <=2-body + selected 3-body features of ONE state."""
    f = {}
    for off, cat_ in m.items():
        k = f"s{shell_of(off)}_{cat_}"
        f[k] = f.get(k, 0) + 1
    offs = list(m)
    for i, o1 in enumerate(offs):
        c1 = m[o1]
        if c1 == "U":
            continue
        for o2 in offs[i + 1 :]:
            if sum((a - b) ** 2 for a, b in zip(o1, o2)) != 2:
                continue
            c2 = m[o2]
            if c2 == "U":
                continue
            key = "b_" + "".join(sorted((c1, c2)))
            f[key] = f.get(key, 0) + 1
    # mover-local broken bonds + mover-adjacent 3-body triangles (this state)
    offset_set = set(offs)
    for mo in movers:
        sp = m.get(mo, "U")
        if sp not in ("N", "C"):
            continue
        nbs = []
        for d1 in NN1:
            n = tuple(a + b for a, b in zip(mo, d1))
            if n in offset_set:
                nbs.append(n)
                f[f"mv{sp}_{m[n]}"] = f.get(f"mv{sp}_{m[n]}", 0) + 1
        for i, n1 in enumerate(nbs):
            for n2 in nbs[i + 1 :]:
                if sum((a - b) ** 2 for a, b in zip(n1, n2)) != 2:
                    continue
                key = "t3_" + "".join(sorted((m[n1], m[n2])))
                f[key] = f.get(key, 0) + 1
    return f


def sym_features(c):
    before, after = state_maps(c)
    movers = {d.off for d in c.delta}
    fb = state_features(before, movers, None)
    fa = state_features(after, movers, None)
    f = {}
    for k in set(fb) | set(fa):
        f[k] = 0.5 * (fb.get(k, 0) + fa.get(k, 0))
    f["n_delta"] = len(c.delta)
    f["abs_delta_atoms"] = abs(c.delta_atoms)
    f["depth_surface"] = 1 if c.depth_sig.kind.name == "SURFACE" else 0
    f["depth_param"] = c.depth_sig.param
    return f


# ---- H(sigma) dPhi features (same as h_sigma_fit script) ----
HFEATS = (
    ["pt_NI", "pt_CR"]
    + [f"b1_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
    + [f"b2_{p}" for p in ("NN", "NC", "CC", "NU", "CU")]
)
HIDX = {k: i for i, k in enumerate(HFEATS)}


def h_bond_key(shell, a, b):
    if a == "E" or b == "E":
        return None
    if a == "U" and b == "U":
        return None
    if a == "U" or b == "U":
        sp = a if b == "U" else b
        return f"b{shell}_{sp}U"
    return f"b{shell}_" + "".join(sorted((a, b), key=lambda s: "NC".index(s)))


def dphi(c):
    before, after = state_maps(c)
    dset = {d.off for d in c.delta}
    v = np.zeros(len(HFEATS))
    for d in c.delta:
        for cat_, sgn in ((after[d.off], +1), (before[d.off], -1)):
            if cat_ == "N":
                v[HIDX["pt_NI"]] += sgn
            elif cat_ == "C":
                v[HIDX["pt_CR"]] += sgn
        for shell, offs in ((1, NN1), (2, NN2)):
            for o in offs:
                n = tuple(a + b for a, b in zip(d.off, o))
                if n in dset and n < d.off:
                    continue
                for m, sgn in ((after, +1), (before, -1)):
                    k = h_bond_key(shell, m[d.off], m.get(n, "U"))
                    if k is not None:
                        v[HIDX[k]] += sgn
    return v



# ---- H basis v2: bond terms split by endpoint surface exposure (surfsplit) ----
H2FEATS = (["pt_NI", "pt_CR"]
           + [f"b1{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
           + [f"b2{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
           + ["b1_NU", "b1_CU", "b2_NU", "b2_CU"])
H2IDX = {k: i for i, k in enumerate(H2FEATS)}


def sp_key(a, b):
    return "".join(sorted(a + b, key=lambda s: "NC".index(s)))


def _exposure(m, off):
    """EMPTY count among the 12 1nn; unknown/OUTSIDE counts as occupied."""
    n_e = 0
    for o in NN1:
        if m.get(tuple(a + b for a, b in zip(off, o)), "U") == "E":
            n_e += 1
    return n_e


def dphi2(c):
    before, after = state_maps(c)
    dset = {d.off for d in c.delta}
    aff = set()
    for d in c.delta:
        for o in NN1:
            n = tuple(a + b for a, b in zip(d.off, o))
            if n not in dset:
                aff.add(n)
    v = np.zeros(len(H2FEATS))
    for m, sgn in ((after, +1), (before, -1)):
        for i in dset:
            a = m[i]
            if a == "N":
                v[H2IDX["pt_NI"]] += sgn
            elif a == "C":
                v[H2IDX["pt_CR"]] += sgn
            if a not in ("N", "C"):
                continue
            for shell, offs in ((1, NN1), (2, NN2)):
                for o in offs:
                    j = tuple(x + y for x, y in zip(i, o))
                    if j in dset and j < i:
                        continue
                    b = m.get(j, "U")
                    if b == "E":
                        continue
                    if b == "U":
                        v[H2IDX[f"b{shell}_{a}U"]] += sgn
                        continue
                    surf = (_exposure(m, i) >= 3) or (_exposure(m, j) >= 3)
                    v[H2IDX[f"b{shell}{'S' if surf else 'B'}_{sp_key(a, b)}"]] += sgn
        for i in aff:
            a = m.get(i, "U")
            if a not in ("N", "C"):
                continue
            for shell, offs in ((1, NN1), (2, NN2)):
                for o in offs:
                    j = tuple(x + y for x, y in zip(i, o))
                    if j in dset or (j in aff and j < i):
                        continue
                    b = m.get(j, "U")
                    if b not in ("N", "C"):
                        continue  # E: no bond; U: exposure-independent, cancels
                    surf = (_exposure(m, i) >= 3) or (_exposure(m, j) >= 3)
                    v[H2IDX[f"b{shell}{'S' if surf else 'B'}_{sp_key(a, b)}"]] += sgn
    return v


# ---- assemble event-level arrays ----
frows, hrows, hrows2, y_ea, y_de, grp, cid, meta = [], [], [], [], [], [], [], []
for c in cat:
    fs = sym_features(c)
    hv = dphi(c)
    hv2 = dphi2(c)
    for b, d_e in zip(c.barriers_eV, c.dE_pair_list_eV):
        frows.append(fs)
        hrows.append(hv)
        hrows2.append(hv2)
        y_ea.append(b)
        y_de.append(d_e)
        grp.append(group_of[c.class_id])
        cid.append(c.class_id)
        mover_cr = any(d.before.name == "CR" for d in c.delta)
        clean_hop = (
            len(c.delta) == 2
            and c.delta_atoms == 0
            and sorted(d.before.name for d in c.delta) in (["EMPTY", "NI"], ["CR", "EMPTY"])
        )
        meta.append(dict(mover_cr=mover_cr, clean_hop=clean_hop,
                         quar=c.class_id in (NO_DELTA | MISLINK),
                         cr_local=sum(v for k, v in fs.items()
                                      if k.startswith(("s0_C", "s1_C", "mvC", "mvN_C")))))

keys = sorted({k for f in frows for k in f})
X = np.array([[f.get(k, 0.0) for k in keys] for f in frows])
XH = np.array(hrows)
XH2 = np.array(hrows2)
y_ea = np.array(y_ea)
y_de = np.array(y_de)
y_sym = y_ea - 0.5 * y_de
grp = np.array(grp)
cid = np.array(cid)
mover_cr = np.array([m["mover_cr"] for m in meta])
clean_hop = np.array([m["clean_hop"] for m in meta])
quar = np.array([m["quar"] for m in meta])
cr_local = np.array([m["cr_local"] for m in meta])
print(f"n_events={len(y_ea)}  esym_features={X.shape[1]}  pair_groups={len(set(grp))}")
print(f"Esym target: mean={y_sym.mean():.3f}  std={y_sym.std():.3f} (null RMSE)")
neg = (y_sym < 0).sum()
print(f"negative Esym targets (unphysical, from mislinks): {neg}")

# ---- direct-eval augmentation for H, if the campaign has finished ----
Xd = yd = Xd2 = None
if DIRECT_CSV.exists():
    fd, fd2, ydl = [], [], []
    with open(DIRECT_CSV) as fh:
        for r in csv.DictReader(fh):
            fd.append([float(r["v1_" + k]) for k in HFEATS])
            fd2.append([float(r["v2_" + k]) for k in H2FEATS])
            ydl.append(float(r["dE_eV"]))
    Xd, Xd2, yd = np.array(fd), np.array(fd2), np.array(ydl)
    print(f"H augmentation: {len(yd)} direct evals loaded (both bases)")


# ---- ridge machinery ----
def ridge_fit_std(Xtr, ytr, alpha):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1.0
    Z = (Xtr - mu) / sd
    ym = ytr.mean()
    A = Z.T @ Z + alpha * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (ytr - ym))
    return mu, sd, ym, w, alpha


def ridge_pred(model, Xte):
    mu, sd, ym, w, _ = model
    return ((Xte - mu) / sd) @ w + ym


def ridge_fit_nointercept(Xtr, ytr, alpha):
    A = Xtr.T @ Xtr + alpha * np.eye(Xtr.shape[1])
    return np.linalg.solve(A, Xtr.T @ ytr)


ALPHAS = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0]
ALPHAS_H = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]

rng = np.random.default_rng(42)
groups = np.unique(grp)
FOLDS = np.array_split(rng.permutation(groups), 10)


def cv_esym(Xf, yf, grpf, folds, seed=0, leverage=False):
    yhat = np.full(len(yf), np.nan)
    lev = np.full(len(yf), np.nan)
    rng_i = np.random.default_rng(seed)
    for fold in folds:
        te = np.isin(grpf, fold)
        tr = ~te
        if te.sum() == 0:
            continue
        best, best_rmse = None, np.inf
        tr_groups = np.unique(grpf[tr])
        inner = np.array_split(rng_i.permutation(tr_groups), 5)
        for a in ALPHAS:
            errs = []
            for ifold in inner:
                ite = np.isin(grpf, ifold) & tr
                itr = tr & ~ite
                m = ridge_fit_std(Xf[itr], yf[itr], a)
                errs.append(ridge_pred(m, Xf[ite]) - yf[ite])
            r = np.sqrt(np.mean(np.concatenate(errs) ** 2))
            if r < best_rmse:
                best_rmse, best = r, a
        m = ridge_fit_std(Xf[tr], yf[tr], best)
        yhat[te] = ridge_pred(m, Xf[te])
        if leverage:
            mu, sd, _, _, a = m
            Ztr = (Xf[tr] - mu) / sd
            Ainv = np.linalg.inv(Ztr.T @ Ztr + a * np.eye(Ztr.shape[1]))
            Zte = (Xf[te] - mu) / sd
            lev[te] = np.einsum("ij,jk,ik->i", Zte, Ainv, Zte)
    return yhat, lev


def cv_h(folds, XHm, aug=None, seed=0):
    yhat = np.full(len(y_de), np.nan)
    rng_i = np.random.default_rng(seed)
    for fold in folds:
        te = np.isin(grp, fold)
        tr = ~te
        best, best_rmse = None, np.inf
        tr_groups = np.unique(grp[tr])
        inner = np.array_split(rng_i.permutation(tr_groups), 5)
        for a in ALPHAS_H:
            errs = []
            for ifold in inner:
                ite = np.isin(grp, ifold) & tr
                itr = tr & ~ite
                Xt, yt = XHm[itr], y_de[itr]
                if aug is not None:
                    Xt = np.vstack([Xt, aug[0]])
                    yt = np.concatenate([yt, aug[1]])
                th = ridge_fit_nointercept(Xt, yt, a)
                errs.append(XHm[ite] @ th - y_de[ite])
            r = np.sqrt(np.mean(np.concatenate(errs) ** 2))
            if r < best_rmse:
                best_rmse, best = r, a
        Xt, yt = XHm[tr], y_de[tr]
        if aug is not None:
            Xt = np.vstack([Xt, aug[0]])
            yt = np.concatenate([yt, aug[1]])
        th = ridge_fit_nointercept(Xt, yt, best)
        yhat[te] = XHm[te] @ th
    return yhat


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return np.corrcoef(ra, rb)[0, 1]


# ============ E_sym holdout ============
print("\n=== E_sym holdout (pair-group 10-fold, nested alpha) ===")
yhat_sym, lev = cv_esym(X, y_sym, grp, FOLDS, seed=7, leverage=True)
ok = ~np.isnan(yhat_sym)


def rep(tag, mask):
    m = mask & ok
    e = yhat_sym[m] - y_sym[m]
    print(f"  {tag:40s} n={m.sum():3d}  RMSE={np.sqrt(np.mean(e**2)):.3f} eV  "
          f"null={y_sym[m].std():.3f}  Spearman={spearman(y_sym[m], yhat_sym[m]):.3f}")


rep("all events", np.ones_like(ok))
rep("excl. quarantine", ~quar)
rep("clean 2-site hops", clean_hop & ~quar)
rep("multi-site/non-conservative", ~clean_hop & ~quar)
rep("Cr movers", mover_cr & ~quar)

# clean-hop-only trained variant (memo section B analogue, honest pair split)
mc = clean_hop & ~quar
yhat_c, _ = cv_esym(X[mc], y_sym[mc], grp[mc], [f for f in FOLDS], seed=8)
okc = ~np.isnan(yhat_c)
ec = yhat_c[okc] - y_sym[mc][okc]
print(f"  clean-hop-only trained:                  n={okc.sum():3d}  "
      f"RMSE={np.sqrt(np.mean(ec**2)):.3f} eV")

# comparison: barrier-target KRA-informed with CLASS split (memo 0.175 repro) vs PAIR split
print("\n  [split-leakage check: KRA-informed barrier fit on clean hops]")
Xk = np.column_stack([X[mc], 0.5 * y_de[mc]])
cls_arr = cid[mc]
rng2 = np.random.default_rng(3)
cls_folds = np.array_split(rng2.permutation(np.unique(cls_arr)), 10)
yh_cls, _ = cv_esym(Xk, y_ea[mc], cls_arr, cls_folds, seed=9)
okk = ~np.isnan(yh_cls)
print(f"    class-level split RMSE = {np.sqrt(np.mean((yh_cls[okk]-y_ea[mc][okk])**2)):.3f} eV"
      f"  (memo baseline 0.175)")
yh_pg, _ = cv_esym(Xk, y_ea[mc], grp[mc], FOLDS, seed=9)
okp = ~np.isnan(yh_pg)
print(f"    pair-group split RMSE  = {np.sqrt(np.mean((yh_pg[okp]-y_ea[mc][okp])**2)):.3f} eV"
      f"  (honest, no fwd/bwd leakage)")

# ============ H(sigma) holdout with the SAME folds ============
print("\n=== H(sigma) holdout, shared folds ===")
h_variants = {}
h_variants["v1 pair12 / harvested"] = cv_h(FOLDS, XH, aug=None, seed=7)
h_variants["v2 surfsplit / harvested"] = cv_h(FOLDS, XH2, aug=None, seed=7)
if Xd is not None:
    h_variants["v1 pair12 / +direct"] = cv_h(FOLDS, XH, aug=(Xd, yd), seed=7)
    h_variants["v2 surfsplit / +direct"] = cv_h(FOLDS, XH2, aug=(Xd2, yd), seed=7)
for t, yh in h_variants.items():
    ae = np.abs(yh - y_de)
    m = ~quar
    print(f"  {t:26s} V2 median|dE_H-dE| = {np.median(ae[m]):.3f} eV  "
          f"(q75={np.quantile(ae[m], 0.75):.3f}, q90={np.quantile(ae[m], 0.9):.3f}; "
          f"clean hops {np.median(ae[m & clean_hop]):.3f}, "
          f"multi {np.median(ae[m & ~clean_hop]):.3f})")
yhat_h = h_variants["v1 pair12 / harvested"]
yhat_hB = h_variants.get("v2 surfsplit / +direct")

# ============ V3: full surrogate tail gate ============
print("\n=== V3: full runtime-form surrogate  Ea_hat = Esym_hat + 0.5*dE_H_hat ===")
q1 = y_ea <= np.percentile(y_ea, 25)
for t, yh_h in [("dE from H v1/harvested", yhat_h)] + ([("dE from H v2/+direct (headline)", yhat_hB)] if yhat_hB is not None else []):
    ea_hat = yhat_sym + 0.5 * yh_h
    m = ok & ~np.isnan(ea_hat)
    e_all = ea_hat[m] - y_ea[m]
    t_ = m & q1
    e_t = ea_hat[t_] - y_ea[t_]
    print(f"  [{t}]")
    print(f"    full-pop: RMSE={np.sqrt(np.mean(e_all**2)):.3f} eV  "
          f"Spearman={spearman(y_ea[m], ea_hat[m]):.3f}")
    print(f"    tail (n={t_.sum()}): signed-mean={e_t.mean():+.3f} eV  "
          f"over-pred={100 * (e_t > 0).mean():.0f}%  "
          f"tail-Spearman={spearman(y_ea[t_], ea_hat[t_]):.3f}")
    tc = t_ & mover_cr
    e_tc = ea_hat[tc] - y_ea[tc]
    print(f"    tail Cr movers (n={tc.sum()}): signed-mean={e_tc.mean():+.3f} eV  "
          f"tail-Spearman={spearman(y_ea[tc], ea_hat[tc]):.3f}")
    # gate verdict vs thresholds
    print(f"    V3 thresholds: bias < kT={KB_T:.4f} -> {'PASS' if abs(e_t.mean()) < KB_T else 'FAIL'}"
          f" ({abs(e_t.mean()) / KB_T:.1f}x kT); Spearman > 0.9 -> "
          f"{'PASS' if spearman(y_ea[t_], ea_hat[t_]) > 0.9 else 'FAIL'}")

# for reference: surrogate with MEASURED dE (isolates the H contribution)
ea_meas = yhat_sym + 0.5 * y_de
m = ok
e_t = ea_meas[m & q1] - y_ea[m & q1]
print(f"  [reference: Esym_hat + 0.5*dE_measured]")
print(f"    full RMSE={np.sqrt(np.mean((ea_meas[m]-y_ea[m])**2)):.3f}  "
      f"tail signed-mean={e_t.mean():+.3f}  "
      f"tail-Spearman={spearman(y_ea[m & q1], ea_meas[m & q1]):.3f}  "
      f"clean-hop RMSE={np.sqrt(np.mean((ea_meas[m & clean_hop & ~quar]-y_ea[m & clean_hop & ~quar])**2)):.3f}")

# ============ V1: learning curve ============
print("\n=== V1: learning curve (clean-hop holdout RMSE vs N, corpus-wide refit) ===")
Ns = [100, 150, 200, 250, 300, 350, 400, 445]
R = 10
rng_lc = np.random.default_rng(1234)
curve = {}
for N in Ns:
    vals_ch, vals_all = [], []
    for r_i in range(R):
        gperm = rng_lc.permutation(groups)
        n_te = max(1, len(gperm) // 10)
        te_g, pool_g = gperm[:n_te], gperm[n_te:]
        te = np.isin(grp, te_g)
        # accumulate pool groups until >= N events
        tr = np.zeros(len(y_sym), bool)
        cnt = 0
        for g in pool_g:
            sel = grp == g
            tr |= sel
            cnt += sel.sum()
            if cnt >= N:
                break
        # inner alpha selection (3-fold by group on tr)
        tr_groups = np.unique(grp[tr])
        inner = np.array_split(rng_lc.permutation(tr_groups), 3)
        best, best_rmse = None, np.inf
        for a in ALPHAS:
            errs = []
            for ifold in inner:
                ite = np.isin(grp, ifold) & tr
                itr = tr & ~ite
                if itr.sum() < 10 or ite.sum() < 3:
                    continue
                mdl = ridge_fit_std(X[itr], y_sym[itr], a)
                errs.append(ridge_pred(mdl, X[ite]) - y_sym[ite])
            if not errs:
                continue
            rr = np.sqrt(np.mean(np.concatenate(errs) ** 2))
            if rr < best_rmse:
                best_rmse, best = rr, a
        mdl = ridge_fit_std(X[tr], y_sym[tr], best)
        pred = ridge_pred(mdl, X[te])
        ch = te & clean_hop & ~quar
        if ch.sum() >= 3:
            vals_ch.append(np.sqrt(np.mean((ridge_pred(mdl, X[ch]) - y_sym[ch]) ** 2)))
        va = te & ~quar
        vals_all.append(np.sqrt(np.mean((pred[va[te.nonzero()[0]] if False else (te & ~quar)[te]] - y_sym[te & ~quar]) ** 2)) if False else
                        np.sqrt(np.mean((ridge_pred(mdl, X[va]) - y_sym[va]) ** 2)))
    curve[N] = (np.mean(vals_ch), np.std(vals_ch), np.mean(vals_all))
    print(f"  N={N:3d}: clean-hop RMSE={curve[N][0]:.3f} +/- {curve[N][1]:.3f}  "
          f"all RMSE={curve[N][2]:.3f}  (R={R})")

# extrapolation: RMSE(N) = sqrt(floor^2 + k/N), least squares on clean-hop means
Narr = np.array(Ns, float)
Rarr = np.array([curve[N][0] for N in Ns])
best_fl, best_sse = 0.0, np.inf
for fl in np.linspace(0, Rarr.min(), 200):
    k = np.mean((Rarr**2 - fl**2) * Narr)
    pred = np.sqrt(np.maximum(fl**2 + k / Narr, 0))
    sse = np.sum((pred - Rarr) ** 2)
    if sse < best_sse:
        best_sse, best_fl, best_k = sse, fl, k
print(f"  fit RMSE(N)=sqrt(floor^2+k/N): floor={best_fl:.3f} eV  k={best_k:.2f}")
if best_fl < 0.10:
    n_needed = best_k / (0.10**2 - best_fl**2)
    print(f"  -> extrapolated N for 0.10 eV clean-hop acceptance: ~{n_needed:.0f} events")
else:
    print(f"  -> floor {best_fl:.3f} eV > 0.10 eV: acceptance UNREACHABLE for this "
          f"basis/corpus by data volume alone")

# ============ V5: leverage / OOD gate ============
print("\n=== V5: leverage vs realized error (holdout), OOD-gate calibration ===")
mL = ok & ~np.isnan(lev) & ~quar
ae = np.abs(yhat_sym - y_sym)
print(f"  Spearman(leverage, |err|) all: {spearman(lev[mL], ae[mL]):.3f}  (n={mL.sum()})")
thr = np.quantile(lev[mL], 0.75)
hi, lo = mL & (lev > thr), mL & (lev <= thr)
print(f"  |err| above/below leverage q75: {ae[hi].mean():.3f} / {ae[lo].mean():.3f} eV "
      f"(ratio {ae[hi].mean() / ae[lo].mean():.2f})")
for tag_, msk in [("Cr movers", mover_cr), ("Ni-only movers", ~mover_cr)]:
    mm = mL & msk
    print(f"  {tag_:16s}: median leverage={np.median(lev[mm]):.3f}  "
          f"frac above q75 gate={100 * (lev[mm] > thr).mean():.0f}%  "
          f"mean|err|={ae[mm].mean():.3f}")

# leave-out-Cr-rich probe: train on low local-Cr, test on Cr-enriched
med_cr = np.quantile(cr_local[~quar], 0.8)
tr = (cr_local <= med_cr) & ~quar
te = (cr_local > med_cr) & ~quar
mdl = ridge_fit_std(X[tr], y_sym[tr], 10.0)
mu, sd, _, _, a = mdl
Ztr = (X[tr] - mu) / sd
Ainv = np.linalg.inv(Ztr.T @ Ztr + a * np.eye(Ztr.shape[1]))
lev_tr = np.einsum("ij,jk,ik->i", Ztr, Ainv, Ztr)
Zte = (X[te] - mu) / sd
lev_te = np.einsum("ij,jk,ik->i", Zte, Ainv, Zte)
gate = np.quantile(lev_tr, 0.95)
err_te = np.abs(ridge_pred(mdl, X[te]) - y_sym[te])
print(f"\n  leave-out-Cr-rich (train n={tr.sum()}, held-out Cr-enriched n={te.sum()}):")
print(f"    gate = train-leverage q95 = {gate:.3f}")
print(f"    held-out: median leverage={np.median(lev_te):.3f}, "
      f"{100 * (lev_te > gate).mean():.0f}% above gate, "
      f"RMSE={np.sqrt(np.mean(err_te**2)):.3f} eV")
fired, silent = err_te[lev_te > gate], err_te[lev_te <= gate]
if len(fired) and len(silent):
    print(f"    |err| gate-fired vs not: {fired.mean():.3f} vs {silent.mean():.3f} eV")

# save per-event artifact for the report
outp = Path("/home/kerr/pykmc/onlattice_design/esym_holdout_pred_2026-07-21.csv")
with open(outp, "w") as fh:
    fh.write("class_id,Ea,dE,Esym,Esym_hat,dE_H_A" +
             (",dE_H_AB" if yhat_hB is not None else "") +
             ",leverage,clean_hop,mover_cr,quarantined\n")
    for i in range(len(y_ea)):
        row = (f"{cid[i]},{y_ea[i]:.6f},{y_de[i]:.6f},{y_sym[i]:.6f},"
               f"{yhat_sym[i]:.6f},{yhat_h[i]:.6f}")
        if yhat_hB is not None:
            row += f",{yhat_hB[i]:.6f}"
        fh.write(row + f",{lev[i]:.4f},{int(clean_hop[i])},{int(mover_cr[i])},{int(quar[i])}\n")
print(f"\nper-event artifact -> {outp}")
print("model_version stamp: E_sym_v1_ridge_sym2b3b")

# stamp the headline H model: v2 surfsplit, all clean harvested + direct evals
if Xd2 is not None:
    Xt = np.vstack([XH2[~quar], Xd2])
    yt = np.concatenate([y_de[~quar], yd])
    thH = ridge_fit_nointercept(Xt, yt, 0.1)
    outh = Path("/home/kerr/pykmc/onlattice_design/H_sigma_v2_theta_2026-07-21.csv")
    with open(outh, "w") as fh:
        fh.write("# dE_model_version=H_sigma_v2_surfsplit_aug  fit 2026-07-21  "
                 "alpha=0.1  clean harvested (n=%d) + direct evals (n=%d)\n"
                 % ((~quar).sum(), len(yd)))
        fh.write("feature,theta_eV\n")
        for k, t in zip(H2FEATS, thH):
            fh.write(f"{k},{t:.6f}\n")
    print(f"stamped H_sigma_v2_surfsplit_aug -> {outh}")
