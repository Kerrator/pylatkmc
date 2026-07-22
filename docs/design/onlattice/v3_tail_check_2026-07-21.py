"""V3 tail-gate check for the Phase C interview (Q7).

Same fit as ridge_anchor_2026-07-21.py, same conditions stamp; adds the two V3
metrics -- signed mean error and Spearman *within the lowest-quartile-barrier
holdout* -- for (i) the static phi model and (ii) the KRA-informed model
(+0.5*dE feature), so V3's threshold realism is a number, not a guess.

Run from inside ~/pykmc/pylatkmc (venv active).
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

ANCHOR = Path("/home/kerr/pykmc/onlattice_design/ridge_anchor_2026-07-21.py")

# Import the anchor script as a module, but stop it from printing its own report
# by running it whole (cheap: one CV pass each section). Simpler + provenance-safe:
# reuse its code verbatim via exec into a namespace, then compute the extras.
src = ANCHOR.read_text()
ns: dict = {"__name__": "anchor"}
exec(compile(src, str(ANCHOR), "exec"), ns)

np_ = ns["np"]
y = ns["y"]
X = ns["X"]
cls_idx = ns["cls_idx"]
meta = ns["meta"]
cv_by_class = ns["cv_by_class"]
spearman = ns["spearman"]
ALPHAS = ns["ALPHAS"]
KB_T = ns["KB_T"]
yhat_static = ns["yhat"]  # section A holdout predictions (static phi)

q1 = y <= np.percentile(y, 25)
mover_cr = np.array([m["mover_cr"] for m in meta])

print("\n=== V3 tail metrics (lowest-quartile-barrier holdout) ===")
print(f"kT(500K) = {KB_T:.4f} eV; tail n = {q1.sum()}")


def tail_report(tag, yhat, mask_all):
    m = mask_all & ~np.isnan(yhat)
    t = m & q1
    err = yhat[t] - y[t]
    print(
        f"  {tag:28s} n_tail={t.sum():3d}  signed-mean={err.mean():+.3f} eV  "
        f"over-pred={100.0 * (err > 0).mean():.0f}%  "
        f"tail-Spearman={spearman(y[t], yhat[t]):.3f}"
    )
    tc = t & mover_cr
    if tc.sum() >= 5:
        ec = yhat[tc] - y[tc]
        print(
            f"  {tag + ' [Cr movers]':28s} n_tail={tc.sum():3d}  "
            f"signed-mean={ec.mean():+.3f} eV  tail-Spearman={spearman(y[tc], yhat[tc]):.3f}"
        )


all_mask = np.ones_like(y, bool)
tail_report("static phi (A)", yhat_static, all_mask)

# KRA-informed: X + 0.5*dE feature, on the linked-pair subset (section C conditions)
has_dE = np.array([m["dE"] is not None for m in meta])
dE = np.array([m["dE"] if m["dE"] is not None else np.nan for m in meta])
X2 = np.column_stack([X[has_dE], 0.5 * dE[has_dE]])
y2 = y[has_dE]
c2 = cls_idx[has_dE]
yhat_kra = cv_by_class(X2, y2, c2, ALPHAS, seed=3)  # same seed as section C

q1_2 = y2 <= np.percentile(y2, 25)
mcr2 = mover_cr[has_dE]


def tail_report2(tag, yhat):
    m = ~np.isnan(yhat)
    t = m & q1_2
    err = yhat[t] - y2[t]
    print(
        f"  {tag:28s} n_tail={t.sum():3d}  signed-mean={err.mean():+.3f} eV  "
        f"over-pred={100.0 * (err > 0).mean():.0f}%  "
        f"tail-Spearman={spearman(y2[t], yhat[t]):.3f}"
    )
    tc = t & mcr2
    if tc.sum() >= 5:
        ec = yhat[tc] - y2[tc]
        print(
            f"  {tag + ' [Cr movers]':28s} n_tail={tc.sum():3d}  "
            f"signed-mean={ec.mean():+.3f} eV  tail-Spearman={spearman(y2[tc], yhat[tc]):.3f}"
        )


print(f"  (linked-pair subset n={has_dE.sum()}, tail n={q1_2.sum()})")
tail_report2("KRA-informed (C)", yhat_kra)

# Reference: full-population Spearman for both, for scale
m = ~np.isnan(yhat_static)
print(f"\n  full-pop Spearman: static={spearman(y[m], yhat_static[m]):.3f}", end="")
m2 = ~np.isnan(yhat_kra)
print(f"  KRA-informed={spearman(y2[m2], yhat_kra[m2]):.3f}")
