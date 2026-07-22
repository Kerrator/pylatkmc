"""Empirical anchor for the Phase C rate-model memo.

Fits the audit's floor candidate -- one-hot <=2-body ridge on initial-environment
occupations -- to the harvested pARTn barriers in the Phase A/B catalogue, with
class-level holdout CV. Pure numpy (no sklearn in the shared venv).

Run from inside ~/pykmc/pylatkmc (relative parquet path; never from the meta-root):
  source ~/pykmc/pykmc_env/bin/activate && cd ~/pykmc/pylatkmc
  python ~/pykmc/onlattice_design/ridge_anchor_2026-07-21.py

Conditions: catalogue_full_rcut8p5.parquet, production NiCrFe verify_fix_T500_1vac
ingest, rcut 8.5 A, 439 classes / 445 events, T_ref = 500 K.
"""

from collections import Counter

import numpy as np

from pylatkmc.ingest.event_class import read_catalogue_parquet

RNG = np.random.default_rng(20260721)
KB_T = 8.6173e-5 * 500.0  # eV at 500 K

cat = read_catalogue_parquet(".scratch/phaseB/catalogue_full_rcut8p5.parquet")

CATS = ["EMPTY", "NI", "CR"]  # OUTSIDE handled separately


def site_cat(pred):
    if pred.kind == "EMPTY":
        return "EMPTY"
    if pred.kind == "OUTSIDE":
        return "OUTSIDE"
    (sp,) = pred.species
    return sp.name


def occ_map(c):
    """off -> category, initial state (delta.before wins over context)."""
    m = {}
    for s in c.context:
        m[s.off] = site_cat(s.pred)
    for d in c.delta:
        m[d.off] = d.before.name
    return m


# shell buckets by squared offset norm (tetragonal integer embedding)
SHELLS = [2, 4, 6, 8, 10, 12, 14, 16, 18]  # distinct |off|^2 values; rest -> tail


def shell_of(off):
    r2 = sum(o * o for o in off)
    return SHELLS.index(r2) if r2 in SHELLS else len(SHELLS)


def features(c):
    m = occ_map(c)
    f = {}
    # 1-body: per-shell per-category counts (incl. OUTSIDE as its own cat)
    for off, cat_ in m.items():
        f[f"s{shell_of(off)}_{cat_}"] = f.get(f"s{shell_of(off)}_{cat_}", 0) + 1
    # 2-body: 1nn bond counts n_XY over stencil pairs (|d|^2 == 2), X,Y occupancy cats
    offs = list(m)
    offset_set = set(offs)
    for i, o1 in enumerate(offs):
        c1 = m[o1]
        if c1 == "OUTSIDE":
            continue
        for o2 in offs[i + 1 :]:
            d2 = sum((a - b) ** 2 for a, b in zip(o1, o2))
            if d2 != 2:
                continue
            c2 = m[o2]
            if c2 == "OUTSIDE":
                continue
            key = "b_" + "".join(sorted((c1[0], c2[0])))
            f[key] = f.get(key, 0) + 1
    # Erlebacher mover-local broken bonds: movers = delta sites occupied before
    for d in c.delta:
        if d.before.name in ("NI", "CR"):
            for off2 in offset_set:
                if sum((a - b) ** 2 for a, b in zip(d.off, off2)) == 2:
                    f[f"mv{d.before.name}_{m[off2]}"] = f.get(f"mv{d.before.name}_{m[off2]}", 0) + 1
    # scalars
    f["n_delta"] = len(c.delta)
    f["delta_atoms"] = c.delta_atoms
    f["depth_surface"] = 1 if c.depth_sig.kind.name == "SURFACE" else 0
    f["depth_param"] = c.depth_sig.param
    (anch,) = c.anchor_pred.species if c.anchor_pred.species else (None,)
    f["anchor_CR"] = 1 if (anch and anch.name == "CR") else 0
    f["anchor_NI"] = 1 if (anch and anch.name == "NI") else 0
    return f


rows, y, cls_idx, meta = [], [], [], []
for ci, c in enumerate(cat):
    f = features(c)
    for b in c.barriers_eV:
        rows.append(f)
        y.append(b)
        cls_idx.append(ci)
        mover_cr = any(d.before.name == "CR" for d in c.delta)
        clean_hop = (
            len(c.delta) == 2
            and c.delta_atoms == 0
            and sorted(d.before.name for d in c.delta) in (["EMPTY", "NI"], ["CR", "EMPTY"])
        )
        meta.append(
            dict(
                mover_cr=mover_cr,
                surface=f["depth_surface"],
                clean_hop=clean_hop,
                dE=c.dEnergy_eV,
            )
        )

keys = sorted({k for f in rows for k in f})
X = np.array([[f.get(k, 0.0) for k in keys] for f in rows], float)
y = np.array(y)
cls_idx = np.array(cls_idx)
print(f"n_events={len(y)} n_features={X.shape[1]} null_rmse={y.std():.3f}")


def ridge_fit(Xtr, ytr, alpha):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1.0
    Z = (Xtr - mu) / sd
    ym = ytr.mean()
    A = Z.T @ Z + alpha * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (ytr - ym))
    return mu, sd, ym, w


def ridge_pred(model, Xte):
    mu, sd, ym, w = model
    return ((Xte - mu) / sd) @ w + ym


def cv_by_class(X, y, cls_idx, alphas, n_folds=10, seed=0):
    classes = np.unique(cls_idx)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(classes)
    folds = np.array_split(perm, n_folds)
    yhat = np.full_like(y, np.nan)
    for fold in folds:
        te = np.isin(cls_idx, fold)
        tr = ~te
        # inner CV on training classes for alpha
        best, best_rmse = None, np.inf
        tr_classes = np.unique(cls_idx[tr])
        inner = np.array_split(rng.permutation(tr_classes), 5)
        for a in alphas:
            errs = []
            for ifold in inner:
                ite = np.isin(cls_idx, ifold) & tr
                itr = tr & ~ite
                m = ridge_fit(X[itr], y[itr], a)
                errs.append(ridge_pred(m, X[ite]) - y[ite])
            r = np.sqrt(np.mean(np.concatenate(errs) ** 2))
            if r < best_rmse:
                best_rmse, best = r, a
        m = ridge_fit(X[tr], y[tr], best)
        yhat[te] = ridge_pred(m, X[te])
    return yhat


ALPHAS = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0]


def report(tag, mask, yhat):
    m = mask & ~np.isnan(yhat)
    if m.sum() < 5:
        print(f"  {tag:34s} n={m.sum():4d}  (too few)")
        return
    err = yhat[m] - y[m]
    rmse = np.sqrt(np.mean(err**2))
    mae = np.abs(err).mean()
    med_ratefac = np.exp(np.median(np.abs(err)) / KB_T)
    print(
        f"  {tag:34s} n={m.sum():4d}  RMSE={rmse:.3f} eV  MAE={mae:.3f}  "
        f"null={y[m].std():.3f}  median rate-error x{med_ratefac:.0f} @500K"
    )


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return np.corrcoef(ra, rb)[0, 1]


mover_cr = np.array([m["mover_cr"] for m in meta])
surface = np.array([bool(m["surface"]) for m in meta])
clean = np.array([m["clean_hop"] for m in meta])
q1 = y <= np.percentile(y, 25)

print("\n=== A. Full catalogue (all 445 events, heterogeneous) ===")
yhat = cv_by_class(X, y, cls_idx, ALPHAS, seed=1)
report("all", np.ones_like(y, bool), yhat)
report("clean 2-site hops", clean, yhat)
report("multi-site / non-conservative", ~clean, yhat)
report("mover includes Cr", mover_cr, yhat)
report("mover Ni/empty only", ~mover_cr, yhat)
report("surface classes", surface, yhat)
report("bulk classes", ~surface, yhat)
report("lowest-quartile barriers (tail)", q1, yhat)
print(f"  Spearman rank corr (all): {spearman(y[~np.isnan(yhat)], yhat[~np.isnan(yhat)]):.3f}")

print("\n=== B. Clean-hop subpopulation only (train+test within) ===")
mc = clean
yc = y[mc]
Xc = X[mc]
cc = cls_idx[mc]
yhat_c = cv_by_class(Xc, yc, cc, ALPHAS, seed=2)
errc = yhat_c - yc
print(f"  n={mc.sum()}  RMSE={np.sqrt(np.mean(errc**2)):.3f} eV  null={yc.std():.3f}")
mcr = mover_cr[mc]
print(f"  Cr movers: RMSE={np.sqrt(np.mean(errc[mcr]**2)):.3f} (n={mcr.sum()}), "
      f"Ni movers: RMSE={np.sqrt(np.mean(errc[~mcr]**2)):.3f} (n={(~mcr).sum()})")
srf = surface[mc]
print(f"  surface: RMSE={np.sqrt(np.mean(errc[srf]**2)):.3f} (n={srf.sum()}), "
      f"bulk: RMSE={np.sqrt(np.mean(errc[~srf]**2)):.3f} (n={(~srf).sum()})")
print(f"  Spearman: {spearman(yc, yhat_c):.3f}")

print("\n=== C. KRA check: barrier vs driving force on our own data ===")
has_dE = np.array([m["dE"] is not None for m in meta])
dE = np.array([m["dE"] if m["dE"] is not None else np.nan for m in meta])
mm = has_dE
r = np.corrcoef(dE[mm], y[mm])[0, 1]
print(f"  n={mm.sum()}  corr(Ea_f, dE)={r:.3f}  r^2={r*r:.3f}")
# ridge with 1/2 dE added as a feature (KRA-informed), full population with pairs
X2 = np.column_stack([X[mm], 0.5 * dE[mm]])
yhat2 = cv_by_class(X2, y[mm], cls_idx[mm], ALPHAS, seed=3)
err2 = yhat2 - y[mm]
print(f"  ridge + 0.5*dE feature: RMSE={np.sqrt(np.mean(err2**2)):.3f} eV "
      f"(vs {np.sqrt(np.mean((yhat[mm]-y[mm])**2)):.3f} without)")

print("\n=== D. Sanity: training-set (non-holdout) fit, full population ===")
m_full = ridge_fit(X, y, 3.0)
res = ridge_pred(m_full, X) - y
print(f"  in-sample RMSE alpha=3: {np.sqrt(np.mean(res**2)):.3f} eV (optimism gauge)")
