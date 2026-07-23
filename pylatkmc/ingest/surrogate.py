"""Phase C E_sym surrogate: feature ports, ridge fit, leverage, model I/O, stamping.

This module is the production port of the approved Phase C rate architecture's
E_sym leg (``PHASEC_RATE_MODEL_DECISION.md`` §8, ``PHASEC_VALIDATION_REPORT_2026-07-21``).
It carries three things a later codegen leg consumes:

1. **The exact feature definitions** from ``esym_v1v3v5_2026-07-21.py`` — the
   symmetrized ≤2-body+3-body E_sym one-hot basis (:func:`sym_features`,
   :data:`ESYM_FEATURE_KEYS`, :func:`phi_vector`) and the H(σ) v2 surfsplit ΔΦ
   basis (:func:`dphi2`, :data:`H2FEATS`). They are ported **verbatim** (the
   port-fidelity scratch test asserts exact equality against the original script
   over all 439 classes). The API is split into two layers: map-level functions
   (:func:`state_features`, :func:`sym_state_features`, :func:`dphi2_from_maps`)
   operating on plain ``dict[Offset, category-str]`` state maps so a later C-parity
   test can drive them without an ``EventClass``, and ``EventClass``-level wrappers
   (:func:`sym_features`, :func:`dphi2`) numerically identical to the script's.

2. **The ridge + leverage machinery** (:func:`ridge_fit_std`, :func:`ridge_pred`,
   :func:`ridge_fit_nointercept`, :func:`leverages`) — exact ports of the script's
   standardized ridge and the V5 leverage einsum ``z @ Ainv @ z`` with
   ``Ainv = inv(Z_train' Z_train + alpha·I)``.

3. **The model container + fit driver** (:class:`EsymModel`, :func:`fit_esym_model`,
   :func:`save_model`, :func:`load_model`, and the prediction helpers
   :func:`predict_esym` / :func:`predict_dE` / :func:`leverage` /
   :func:`surrogate_barrier`). ``surrogate_barrier`` is the V6 quantity
   ``predict_esym(φ) + ½·predict_dE(dphi2)`` a codegen leg bakes per class.

Determinism (contract 0.1)
--------------------------
No ``hash()``, no ``set``/``dict`` iteration that affects a value: the map-level
feature reductions are order-independent by construction (bond/triangle keys are
``sorted`` before counting; ΔΦ accumulations are ±1 sums whose value is
order-invariant), and every set walk here iterates a ``sorted`` list. Fold splits
use fixed seeds (42 outer, 7 inner). Model JSON is written with ``sort_keys=True``.

Units (contract 0.4)
--------------------
``tier0_nu0_hz`` is stored in Hz (pyKMC's native prefactor unit); divide by
``HZ_PER_PSINV`` (= 1e12) for the on-lattice ps⁻¹ unit. Barriers/E_sym are in eV.
"""

from __future__ import annotations

import csv
import itertools
import json
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from pylatkmc.ingest.event_class import (
    HZ_PER_PSINV,
    EventClass,
    OccPredicate,
)

Offset = tuple[int, int, int]
"""Integer FCC lattice offset (i, j, k)."""

StateMap = dict[Offset, str]
"""Sparse occupancy category map: offset -> one of ``"N"``/``"C"``/``"E"``/``"U"``."""

FloatArray = npt.NDArray[np.float64]


# --------------------------------------------------------------------------- #
# Geometry (verbatim port of esym_v1v3v5_2026-07-21.py)                        #
# --------------------------------------------------------------------------- #
NN1: tuple[Offset, ...] = tuple(
    (a, b, c) for a, b, c in itertools.product(range(-2, 3), repeat=3) if a * a + b * b + c * c == 2
)
"""The 12 first-nearest-neighbour offsets (|off|² == 2)."""

NN2: tuple[Offset, ...] = tuple(
    (a, b, c) for a, b, c in itertools.product(range(-2, 3), repeat=3) if a * a + b * b + c * c == 4
)
"""The 6 second-nearest-neighbour offsets (|off|² == 4)."""

SHELLS: tuple[int, ...] = (2, 4, 6, 8, 10, 12, 14, 16, 18)
"""Squared radii of the nine resolved neighbour shells; anything beyond -> shell 9."""


def shell_of(off: Offset) -> int:
    """Shell index of an offset: ``SHELLS.index(|off|²)`` or ``len(SHELLS)`` (=9) beyond."""
    r2 = sum(o * o for o in off)
    return SHELLS.index(r2) if r2 in SHELLS else len(SHELLS)


# --------------------------------------------------------------------------- #
# E_sym feature basis — map level (verbatim; order-independent reductions)     #
# --------------------------------------------------------------------------- #
def state_features(m: StateMap, movers: Collection[Offset]) -> dict[str, float]:
    """One-hot ≤2-body + selected 3-body features of ONE state map (script port).

    Per-shell per-category counts (``s{shell}_{cat}``), 1nn bond counts
    (``b_{sorted pair}``), mover-local broken bonds (``mv{sp}_{cat}``) and
    mover-adjacent 1nn triangles (``t3_{sorted pair}``). ``"U"`` (OUTSIDE/unknown)
    sites never enter a bond/triangle. All keys use ``sorted`` category pairs so the
    result is independent of iteration order (C-parity safe).
    """
    f: dict[str, float] = {}
    for off, cat_ in m.items():
        k = f"s{shell_of(off)}_{cat_}"
        f[k] = f.get(k, 0.0) + 1
    offs = list(m)
    for i, o1 in enumerate(offs):
        c1 = m[o1]
        if c1 == "U":
            continue
        for o2 in offs[i + 1 :]:
            if sum((a - b) ** 2 for a, b in zip(o1, o2, strict=True)) != 2:
                continue
            c2 = m[o2]
            if c2 == "U":
                continue
            key = "b_" + "".join(sorted((c1, c2)))
            f[key] = f.get(key, 0.0) + 1
    offset_set = set(offs)
    for mo in movers:
        sp = m.get(mo, "U")
        if sp not in ("N", "C"):
            continue
        nbs: list[Offset] = []
        for d1 in NN1:
            n = (mo[0] + d1[0], mo[1] + d1[1], mo[2] + d1[2])
            if n in offset_set:
                nbs.append(n)
                mk = f"mv{sp}_{m[n]}"
                f[mk] = f.get(mk, 0.0) + 1
        for i, n1 in enumerate(nbs):
            for n2 in nbs[i + 1 :]:
                if sum((a - b) ** 2 for a, b in zip(n1, n2, strict=True)) != 2:
                    continue
                key = "t3_" + "".join(sorted((m[n1], m[n2])))
                f[key] = f.get(key, 0.0) + 1
    return f


def sym_state_features(
    before: StateMap,
    after: StateMap,
    movers: Collection[Offset],
    *,
    n_delta: int,
    abs_delta_atoms: int,
    depth_surface: int,
    depth_param: int,
) -> dict[str, float]:
    """Endpoint-exchange-symmetrized E_sym feature dict from two state maps (script port).

    ``f_sym = ½·(f(before) + f(after))`` over the union of keys, plus the four
    ``(a,g)``-invariant scalars ``n_delta``/``abs_delta_atoms``/``depth_surface``/
    ``depth_param`` (appended un-symmetrized, exactly as the script). Symmetrizing the
    two endpoints makes the surrogate detailed-balance-safe by construction.
    """
    fb = state_features(before, movers)
    fa = state_features(after, movers)
    f: dict[str, float] = {}
    for k in sorted(set(fb) | set(fa)):
        f[k] = 0.5 * (fb.get(k, 0.0) + fa.get(k, 0.0))
    f["n_delta"] = n_delta
    f["abs_delta_atoms"] = abs_delta_atoms
    f["depth_surface"] = depth_surface
    f["depth_param"] = depth_param
    return f


# --------------------------------------------------------------------------- #
# H(σ) v2 surfsplit ΔΦ basis — map level (verbatim)                           #
# --------------------------------------------------------------------------- #
H2FEATS: tuple[str, ...] = tuple(
    ["pt_NI", "pt_CR"]
    + [f"b1{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
    + [f"b2{e}_{p}" for e in ("B", "S") for p in ("NN", "NC", "CC")]
    + ["b1_NU", "b1_CU", "b2_NU", "b2_CU"]
)
"""The 18 H(σ) v2 surfsplit features (bond terms split by endpoint surface exposure)."""

H2IDX: dict[str, int] = {k: i for i, k in enumerate(H2FEATS)}


def sp_key(a: str, b: str) -> str:
    """Occupied-species bond pair key, N-before-C ordered (``"NN"``/``"NC"``/``"CC"``)."""
    return "".join(sorted(a + b, key=lambda s: "NC".index(s)))


def _exposure(m: StateMap, off: Offset) -> int:
    """EMPTY count among the 12 1nn of ``off``; unknown/OUTSIDE counts as occupied."""
    n_e = 0
    for o in NN1:
        if m.get((off[0] + o[0], off[1] + o[1], off[2] + o[2]), "U") == "E":
            n_e += 1
    return n_e


def dphi2_from_maps(
    before: StateMap, after: StateMap, delta_offsets: Collection[Offset]
) -> FloatArray:
    """ΔΦ (surfsplit) feature vector from two state maps + the changed-site set (script port).

    ``dphi2 = f(after) - f(before)`` over point terms of the delta sites and their
    bonds to (delta ∪ affected-1nn) sites, with each bond routed to a bulk (``B``) or
    surface (``S``) channel by whether either endpoint has ≥3 EMPTY 1nn. Delta and
    affected sets are walked in ``sorted`` order; the ``j < i`` de-duplication and the
    ±1 accumulation make the result order-independent (C-parity safe).
    """
    dset = set(delta_offsets)
    aff: set[Offset] = set()
    for d in sorted(dset):
        for o in NN1:
            n = (d[0] + o[0], d[1] + o[1], d[2] + o[2])
            if n not in dset:
                aff.add(n)
    v: FloatArray = np.zeros(len(H2FEATS))
    for m, sgn in ((after, 1), (before, -1)):
        for i in sorted(dset):
            a = m[i]
            if a == "N":
                v[H2IDX["pt_NI"]] += sgn
            elif a == "C":
                v[H2IDX["pt_CR"]] += sgn
            if a not in ("N", "C"):
                continue
            for shell, offs in ((1, NN1), (2, NN2)):
                for o in offs:
                    j = (i[0] + o[0], i[1] + o[1], i[2] + o[2])
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
        for i in sorted(aff):
            a = m.get(i, "U")
            if a not in ("N", "C"):
                continue
            for shell, offs in ((1, NN1), (2, NN2)):
                for o in offs:
                    j = (i[0] + o[0], i[1] + o[1], i[2] + o[2])
                    if j in dset or (j in aff and j < i):
                        continue
                    b = m.get(j, "U")
                    if b not in ("N", "C"):
                        continue  # E: no bond; U: exposure-independent, cancels
                    surf = (_exposure(m, i) >= 3) or (_exposure(m, j) >= 3)
                    v[H2IDX[f"b{shell}{'S' if surf else 'B'}_{sp_key(a, b)}"]] += sgn
    return v


# --------------------------------------------------------------------------- #
# EventClass-level wrappers (verbatim state-map build)                         #
# --------------------------------------------------------------------------- #
OCCC: dict[str, str] = {"NI": "N", "CR": "C", "EMPTY": "E"}
"""Delta-site occupancy-name -> category (matches the script's per-delta mapping)."""


def occ_cat(pred: OccPredicate) -> str:
    """Context-predicate -> category ``"N"``/``"C"``/``"E"``/``"U"`` (script port).

    EMPTY -> ``"E"``, OUTSIDE -> ``"U"``; a single-species predicate -> ``"N"`` for Ni,
    ``"C"`` otherwise (Cr). Mirrors the script exactly (a non-SPECIES occupied predicate
    would raise on the single-element unpack, as in the original).
    """
    if pred.kind == "EMPTY":
        return "E"
    if pred.kind == "OUTSIDE":
        return "U"
    (sp,) = pred.species
    return "N" if sp.name == "NI" else "C"


def state_maps(cls: EventClass) -> tuple[StateMap, StateMap]:
    """Before/after category maps of a class: context decoration overlaid by the delta."""
    base: StateMap = {s.off: occ_cat(s.pred) for s in cls.context}
    before, after = dict(base), dict(base)
    for d in cls.delta:
        before[d.off] = OCCC[d.before.name]
        after[d.off] = OCCC[d.after.name]
    return before, after


def sym_features(cls: EventClass) -> dict[str, float]:
    """The symmetrized E_sym feature dict of one ``EventClass`` (numerically == script)."""
    before, after = state_maps(cls)
    movers = {d.off for d in cls.delta}
    return sym_state_features(
        before,
        after,
        movers,
        n_delta=len(cls.delta),
        abs_delta_atoms=abs(cls.delta_atoms),
        depth_surface=1 if cls.depth_sig.kind.name == "SURFACE" else 0,
        depth_param=cls.depth_sig.param,
    )


def dphi2(cls: EventClass) -> FloatArray:
    """The H(σ) v2 surfsplit ΔΦ feature vector of one ``EventClass`` (numerically == script)."""
    before, after = state_maps(cls)
    dset = {d.off for d in cls.delta}
    return dphi2_from_maps(before, after, dset)


# --------------------------------------------------------------------------- #
# Pinned E_sym feature order                                                   #
# --------------------------------------------------------------------------- #
ESYM_FEATURE_KEYS: tuple[str, ...] = (
    "abs_delta_atoms",
    "b_CC",
    "b_CE",
    "b_CN",
    "b_EE",
    "b_EN",
    "b_NN",
    "depth_param",
    "depth_surface",
    "mvC_C",
    "mvC_E",
    "mvC_N",
    "mvC_U",
    "mvN_C",
    "mvN_E",
    "mvN_N",
    "mvN_U",
    "n_delta",
    "s0_C",
    "s0_E",
    "s0_N",
    "s0_U",
    "s1_C",
    "s1_E",
    "s1_N",
    "s1_U",
    "s2_C",
    "s2_E",
    "s2_N",
    "s2_U",
    "s3_C",
    "s3_E",
    "s3_N",
    "s3_U",
    "s4_C",
    "s4_E",
    "s4_N",
    "s4_U",
    "s5_C",
    "s5_E",
    "s5_N",
    "s5_U",
    "s6_C",
    "s6_E",
    "s6_N",
    "s6_U",
    "s7_C",
    "s7_E",
    "s7_N",
    "s7_U",
    "s8_C",
    "s8_E",
    "s8_N",
    "s8_U",
    "s9_C",
    "s9_E",
    "s9_N",
    "s9_U",
    "t3_CC",
    "t3_CE",
    "t3_CN",
    "t3_CU",
    "t3_EE",
    "t3_EN",
    "t3_EU",
    "t3_NN",
    "t3_NU",
    "t3_UU",
)
"""The pinned sorted union of ``sym_features`` keys over the production corpus (68 keys).

Measured over all 439 classes of ``catalogue_qc_rcut8p5.parquet`` (identical to the
422 non-quarantined subset); matches the validation report's "68 feats". ``phi_vector``
emits values in exactly this order; a key produced by ``sym_features`` that is not here
raises (loud, not silent).
"""

_ESYM_KEY_SET: frozenset[str] = frozenset(ESYM_FEATURE_KEYS)


def phi_vector(cls: EventClass) -> tuple[float, ...]:
    """The E_sym feature vector of a class in the pinned :data:`ESYM_FEATURE_KEYS` order.

    Raises ``ValueError`` if ``sym_features`` produces a key absent from the pinned list
    (an out-of-corpus feature must never be silently dropped).
    """
    f = sym_features(cls)
    unknown = sorted(set(f) - _ESYM_KEY_SET)
    if unknown:
        raise ValueError(
            f"sym_features produced key(s) not in ESYM_FEATURE_KEYS: {unknown} "
            f"(class_id={cls.class_id}); the pinned basis must be regenerated deliberately"
        )
    return tuple(float(f.get(k, 0.0)) for k in ESYM_FEATURE_KEYS)


# --------------------------------------------------------------------------- #
# Ridge machinery + leverage (verbatim ports)                                 #
# --------------------------------------------------------------------------- #
RidgeModel = tuple[FloatArray, FloatArray, float, FloatArray, float]
"""``(mu, sd, ym, w, alpha)`` — a fitted standardized ridge (script's 5-tuple)."""


def ridge_fit_std(x_tr: FloatArray, y_tr: FloatArray, alpha: float) -> RidgeModel:
    """Standardized ridge with a mean intercept (verbatim port of ``ridge_fit_std``)."""
    mu = x_tr.mean(0)
    sd = x_tr.std(0)
    sd[sd == 0] = 1.0
    z = (x_tr - mu) / sd
    ym = float(y_tr.mean())
    a = z.T @ z + alpha * np.eye(z.shape[1])
    w: FloatArray = np.linalg.solve(a, z.T @ (y_tr - ym))
    return mu, sd, ym, w, alpha


def ridge_pred(model: RidgeModel, x_te: FloatArray) -> FloatArray:
    """Predict with a fitted standardized ridge (verbatim port of ``ridge_pred``)."""
    mu, sd, ym, w, _ = model
    out: FloatArray = ((x_te - mu) / sd) @ w + ym
    return out


def ridge_fit_nointercept(x_tr: FloatArray, y_tr: FloatArray, alpha: float) -> FloatArray:
    """No-intercept ridge on raw features (verbatim port; the H(σ) ΔΦ fitter)."""
    a = x_tr.T @ x_tr + alpha * np.eye(x_tr.shape[1])
    theta: FloatArray = np.linalg.solve(a, x_tr.T @ y_tr)
    return theta


def ridge_ainv(model: RidgeModel, x_tr: FloatArray) -> FloatArray:
    """``inv(Z_train' Z_train + alpha·I)`` for the standardized training design (V5)."""
    mu, sd, _, _, alpha = model
    z = (x_tr - mu) / sd
    ainv: FloatArray = np.linalg.inv(z.T @ z + alpha * np.eye(z.shape[1]))
    return ainv


def leverages(x: FloatArray, mu: FloatArray, sd: FloatArray, ainv: FloatArray) -> FloatArray:
    """Ridge leverage ``z @ Ainv @ z`` per row (verbatim port of ``cv_esym``'s einsum)."""
    z = (x - mu) / sd
    lev: FloatArray = np.einsum("ij,jk,ik->i", z, ainv, z)
    return lev


# --------------------------------------------------------------------------- #
# Model container + I/O                                                        #
# --------------------------------------------------------------------------- #
DEFAULT_MODEL_VERSION = "E_sym_v1_ridge_sym2b3b"
DEFAULT_DE_MODEL_VERSION = "H_sigma_v2_surfsplit_aug"
DEFAULT_NU0_PAIR_POLICY = "harvested_pair"


@dataclass
class EsymModel:
    """The fitted E_sym surrogate + everything a codegen/runtime leg consumes.

    ``mu``/``sd``/``ym``/``w`` are the standardized ridge (E_sym = ((φ−mu)/sd)·w + ym);
    ``ainv`` is ``inv(Z_train'Z_train + alpha·I)`` for leverage. ``h2_theta`` is the
    embedded H(σ) v2 surfsplit ΔΦ model (ΔE = dphi2·θ, no intercept). The leverage
    quantiles are over the FINAL-model in-sample training-event leverages (the runtime
    OOD gate thresholds). ``tier0_nu0_hz`` is the clean-hop pooled geometric-mean
    prefactor in Hz; ``context_count_ranges`` are the per-category before-state counts
    over clean-hop classes (the unseen-species-count trigger); ``ea_clamp`` bounds the
    surrogate barrier to the measured range.
    """

    model_version: str
    dE_model_version: str
    alpha: float
    feature_keys: tuple[str, ...]
    mu: FloatArray
    sd: FloatArray
    ym: float
    w: FloatArray
    h2_feature_names: tuple[str, ...]
    h2_theta: FloatArray
    ainv: FloatArray
    lev_q75: float
    lev_q90: float
    lev_q95: float
    tier0_nu0_hz: float
    context_count_ranges: dict[str, tuple[int, int]]
    ea_clamp: tuple[float, float]
    conditions: str
    n_train: int


def save_model(model: EsymModel, path: str | Path) -> None:
    """Serialize an :class:`EsymModel` to JSON (nested lists, deterministic key order)."""
    obj = {
        "model_version": model.model_version,
        "dE_model_version": model.dE_model_version,
        "alpha": model.alpha,
        "feature_keys": list(model.feature_keys),
        "mu": model.mu.tolist(),
        "sd": model.sd.tolist(),
        "ym": model.ym,
        "w": model.w.tolist(),
        "h2_feature_names": list(model.h2_feature_names),
        "h2_theta": model.h2_theta.tolist(),
        "ainv": model.ainv.tolist(),
        "lev_q75": model.lev_q75,
        "lev_q90": model.lev_q90,
        "lev_q95": model.lev_q95,
        "tier0_nu0_hz": model.tier0_nu0_hz,
        "context_count_ranges": {
            k: [int(v[0]), int(v[1])] for k, v in sorted(model.context_count_ranges.items())
        },
        "ea_clamp": [model.ea_clamp[0], model.ea_clamp[1]],
        "conditions": model.conditions,
        "n_train": model.n_train,
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def load_model(path: str | Path) -> EsymModel:
    """Inverse of :func:`save_model`."""
    obj = json.loads(Path(path).read_text())
    return EsymModel(
        model_version=obj["model_version"],
        dE_model_version=obj["dE_model_version"],
        alpha=float(obj["alpha"]),
        feature_keys=tuple(obj["feature_keys"]),
        mu=np.array(obj["mu"], dtype=np.float64),
        sd=np.array(obj["sd"], dtype=np.float64),
        ym=float(obj["ym"]),
        w=np.array(obj["w"], dtype=np.float64),
        h2_feature_names=tuple(obj["h2_feature_names"]),
        h2_theta=np.array(obj["h2_theta"], dtype=np.float64),
        ainv=np.array(obj["ainv"], dtype=np.float64),
        lev_q75=float(obj["lev_q75"]),
        lev_q90=float(obj["lev_q90"]),
        lev_q95=float(obj["lev_q95"]),
        tier0_nu0_hz=float(obj["tier0_nu0_hz"]),
        context_count_ranges={
            k: (int(v[0]), int(v[1])) for k, v in obj["context_count_ranges"].items()
        },
        ea_clamp=(float(obj["ea_clamp"][0]), float(obj["ea_clamp"][1])),
        conditions=obj["conditions"],
        n_train=int(obj["n_train"]),
    )


def predict_esym(model: EsymModel, phi: Sequence[float] | FloatArray) -> float:
    """E_sym prediction for a φ vector in :data:`ESYM_FEATURE_KEYS` order."""
    x = np.asarray(phi, dtype=np.float64)
    z = (x - model.mu) / model.sd
    return float(z @ model.w + model.ym)


def predict_dE(model: EsymModel, dphi2_vec: Sequence[float] | FloatArray) -> float:
    """ΔE prediction from a ``dphi2`` surfsplit vector (H(σ) v2, no intercept)."""
    x = np.asarray(dphi2_vec, dtype=np.float64)
    return float(x @ model.h2_theta)


def leverage(model: EsymModel, phi: Sequence[float] | FloatArray) -> float:
    """Ridge leverage ``z @ Ainv @ z`` of a φ vector under the fitted model (V5)."""
    x = np.asarray(phi, dtype=np.float64)
    z = (x - model.mu) / model.sd
    return float(z @ model.ainv @ z)


def surrogate_barrier(model: EsymModel, cls: EventClass) -> float:
    """The V6 runtime barrier ``E_sym_hat(φ) + ½·ΔE_H_hat(dphi2)`` for a class."""
    return predict_esym(model, phi_vector(cls)) + 0.5 * predict_dE(model, dphi2(cls))


# --------------------------------------------------------------------------- #
# Fit driver                                                                   #
# --------------------------------------------------------------------------- #
ALPHAS: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0)
"""E_sym ridge alpha grid (verbatim from the script)."""


def pair_group_of(classes: Sequence[EventClass]) -> dict[str, str]:
    """Union-find pair groups over ``backward_class`` (verbatim; over the FULL catalogue).

    A forward/backward physical pair shares an E_sym target, so it must share a CV fold;
    the union-find spans every class (a linked partner may itself be quarantined).
    """
    parent: dict[str, str] = {c.class_id: c.class_id for c in classes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in classes:
        if c.backward_class is not None and c.backward_class in parent:
            ra, rb = find(c.class_id), find(c.backward_class)
            if ra != rb:
                parent[ra] = rb
    return {c.class_id: find(c.class_id) for c in classes}


def _is_clean_hop(cls: EventClass) -> bool:
    """The script's clean-hop test: a 2-site conservative Ni↔vac or Cr↔vac exchange."""
    return (
        len(cls.delta) == 2
        and cls.delta_atoms == 0
        and sorted(d.before.name for d in cls.delta) in (["EMPTY", "NI"], ["CR", "EMPTY"])
    )


def _is_mover_cr(cls: EventClass) -> bool:
    """True if any delta site starts as Cr (the dealloying-critical subpopulation)."""
    return any(d.before.name == "CR" for d in cls.delta)


@dataclass(frozen=True)
class EsymRows:
    """The per-member E_sym training rows built from the non-quarantined corpus."""

    x: FloatArray
    y_ea: FloatArray
    y_de: FloatArray
    y_sym: FloatArray
    grp: npt.NDArray[np.str_]
    cid: npt.NDArray[np.str_]
    clean_hop: npt.NDArray[np.bool_]
    mover_cr: npt.NDArray[np.bool_]


def build_esym_rows(classes: Sequence[EventClass], group_of: Mapping[str, str]) -> EsymRows:
    """Build per-member rows over NON-quarantined classes: ``zip(barriers, dE_pairs)``.

    Target ``y_sym = Ea − ½·dE`` (the exchange-symmetric barrier component). A class with
    no linked ``dE_pair`` contributes no rows (``zip`` stops at the shorter list), exactly
    as the script. Features are in the pinned :data:`ESYM_FEATURE_KEYS` order.
    """
    frows: list[tuple[float, ...]] = []
    y_ea: list[float] = []
    y_de: list[float] = []
    grp: list[str] = []
    cid: list[str] = []
    clean: list[bool] = []
    mcr: list[bool] = []
    for c in classes:
        if c.audit_status == "quarantined":
            continue
        phi = phi_vector(c)
        ch = _is_clean_hop(c)
        cr = _is_mover_cr(c)
        # dE_pair_list may be shorter than barriers (unpaired members) — NOT strict.
        for b, d_e in zip(c.barriers_eV, c.dE_pair_list_eV, strict=False):
            frows.append(phi)
            y_ea.append(float(b))
            y_de.append(float(d_e))
            grp.append(group_of[c.class_id])
            cid.append(c.class_id)
            clean.append(ch)
            mcr.append(cr)
    x = np.array(frows, dtype=np.float64)
    yea = np.array(y_ea, dtype=np.float64)
    yde = np.array(y_de, dtype=np.float64)
    return EsymRows(
        x=x,
        y_ea=yea,
        y_de=yde,
        y_sym=yea - 0.5 * yde,
        grp=np.array(grp),
        cid=np.array(cid),
        clean_hop=np.array(clean, dtype=bool),
        mover_cr=np.array(mcr, dtype=bool),
    )


def _spearman(a: FloatArray, b: FloatArray) -> float:
    """Spearman rank correlation (verbatim port of the script's helper)."""
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def _make_folds(grp: npt.NDArray[np.str_], seed: int = 42) -> list[npt.NDArray[np.str_]]:
    """10-fold split by pair group (rng seed 42, verbatim)."""
    rng = np.random.default_rng(seed)
    groups = np.unique(grp)
    return list(np.array_split(rng.permutation(groups), 10))


def _nested_cv_esym(
    x: FloatArray,
    y: FloatArray,
    grp: npt.NDArray[np.str_],
    folds: Sequence[npt.NDArray[np.str_]],
    seed: int = 7,
) -> FloatArray:
    """Nested-alpha 10-fold holdout predictions (verbatim port of ``cv_esym``)."""
    yhat: FloatArray = np.full(len(y), np.nan)
    rng_i = np.random.default_rng(seed)
    for fold in folds:
        te = np.isin(grp, fold)
        tr = ~te
        if te.sum() == 0:
            continue
        best: float | None = None
        best_rmse = np.inf
        tr_groups = np.unique(grp[tr])
        inner = np.array_split(rng_i.permutation(tr_groups), 5)
        for a in ALPHAS:
            errs: list[FloatArray] = []
            for ifold in inner:
                ite = np.isin(grp, ifold) & tr
                itr = tr & ~ite
                m = ridge_fit_std(x[itr], y[itr], a)
                errs.append(ridge_pred(m, x[ite]) - y[ite])
            r = float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))
            if r < best_rmse:
                best_rmse, best = r, a
        assert best is not None
        m = ridge_fit_std(x[tr], y[tr], best)
        yhat[te] = ridge_pred(m, x[te])
    return yhat


def _select_alpha_pooled(
    x: FloatArray,
    y: FloatArray,
    grp: npt.NDArray[np.str_],
    folds: Sequence[npt.NDArray[np.str_]],
) -> tuple[float, dict[float, float]]:
    """Pick the alpha minimizing pooled outer-holdout RMSE (one 10-fold CV per alpha)."""
    scores: dict[float, float] = {}
    for a in ALPHAS:
        yhat: FloatArray = np.full(len(y), np.nan)
        for fold in folds:
            te = np.isin(grp, fold)
            tr = ~te
            if te.sum() == 0:
                continue
            m = ridge_fit_std(x[tr], y[tr], a)
            yhat[te] = ridge_pred(m, x[te])
        ok = ~np.isnan(yhat)
        scores[a] = float(np.sqrt(np.mean((yhat[ok] - y[ok]) ** 2)))
    best_alpha = min(ALPHAS, key=lambda a: (scores[a], a))
    return best_alpha, scores


def clean_hop_nu0_geo_hz(classes: Iterable[EventClass]) -> float:
    """Geometric mean over pooled per-member ν0_f + ν0_b (Hz) of clean-hop classes.

    Tier-0 ν0 (``PHASEC_RATE_MODEL_DECISION.md`` §8-N4): the per-move-topology constant
    the surrogate channel uses when no harvested per-pair Vineyard ratio is available.
    NaN / non-positive prefactors are dropped.
    """
    pool: list[float] = []
    for c in classes:
        if c.audit_status == "quarantined" or not _is_clean_hop(c):
            continue
        for x in list(c.nu0_f_list_hz) + list(c.nu0_b_list_hz):
            if np.isfinite(x) and x > 0:
                pool.append(float(x))
    if not pool:
        return float("nan")
    return float(np.exp(np.mean(np.log(np.array(pool, dtype=np.float64)))))


def clean_hop_context_ranges(classes: Iterable[EventClass]) -> dict[str, tuple[int, int]]:
    """Per-category before-state count [min, max] over clean-hop classes (unseen trigger)."""
    lo = {"N": None, "C": None, "E": None}
    hi = {"N": None, "C": None, "E": None}
    lod: dict[str, int] = {}
    hid: dict[str, int] = {}
    for c in classes:
        if c.audit_status == "quarantined" or not _is_clean_hop(c):
            continue
        before, _after = state_maps(c)
        cnt = {"N": 0, "C": 0, "E": 0}
        for cat_ in before.values():
            if cat_ in cnt:
                cnt[cat_] += 1
        for k, val in cnt.items():
            lod[k] = val if k not in lod else min(lod[k], val)
            hid[k] = val if k not in hid else max(hid[k], val)
    return {k: (lod[k], hid[k]) for k in ("N", "C", "E") if k in lod}


def fit_esym_model(
    classes: Sequence[EventClass],
    h2_theta: FloatArray,
    *,
    conditions: str,
    model_version: str = DEFAULT_MODEL_VERSION,
    dE_model_version: str = DEFAULT_DE_MODEL_VERSION,
) -> tuple[EsymModel, dict[str, object]]:
    """Fit the production E_sym model on the non-quarantined corpus + embed H(σ) θ.

    Returns ``(model, report)`` where ``report`` carries the alpha selection trace and the
    nested-CV holdout numbers (all / clean-hop / multi-site / Cr-mover RMSE + Spearman)
    for the artifact record and the §3 sanity check.
    """
    group_of = pair_group_of(classes)
    rows = build_esym_rows(classes, group_of)
    folds = _make_folds(rows.grp, seed=42)

    best_alpha, pooled_scores = _select_alpha_pooled(rows.x, rows.y_sym, rows.grp, folds)

    # nested-CV holdout numbers for the artifact / §3 sanity
    yhat = _nested_cv_esym(rows.x, rows.y_sym, rows.grp, folds, seed=7)
    ok = ~np.isnan(yhat)

    def _metrics(mask: npt.NDArray[np.bool_]) -> dict[str, float]:
        m = mask & ok
        e = yhat[m] - rows.y_sym[m]
        return {
            "n": int(m.sum()),
            "rmse": float(np.sqrt(np.mean(e**2))),
            "null": float(rows.y_sym[m].std()),
            "spearman": _spearman(rows.y_sym[m], yhat[m]),
        }

    cv = {
        "all": _metrics(np.ones(len(ok), dtype=bool)),
        "clean_hop": _metrics(rows.clean_hop),
        "multi_site": _metrics(~rows.clean_hop),
        "cr_mover": _metrics(rows.mover_cr),
    }

    # final model on ALL training rows at the chosen alpha
    model_t = ridge_fit_std(rows.x, rows.y_sym, best_alpha)
    mu, sd, ym, w, alpha = model_t
    ainv = ridge_ainv(model_t, rows.x)
    lev_tr = leverages(rows.x, mu, sd, ainv)

    aux_ranges = clean_hop_context_ranges(classes)
    ea_all = [float(b) for c in classes if c.audit_status != "quarantined" for b in c.barriers_eV]

    model = EsymModel(
        model_version=model_version,
        dE_model_version=dE_model_version,
        alpha=float(alpha),
        feature_keys=ESYM_FEATURE_KEYS,
        mu=mu,
        sd=sd,
        ym=ym,
        w=w,
        h2_feature_names=H2FEATS,
        h2_theta=np.asarray(h2_theta, dtype=np.float64),
        ainv=ainv,
        lev_q75=float(np.quantile(lev_tr, 0.75)),
        lev_q90=float(np.quantile(lev_tr, 0.90)),
        lev_q95=float(np.quantile(lev_tr, 0.95)),
        tier0_nu0_hz=clean_hop_nu0_geo_hz(classes),
        context_count_ranges=aux_ranges,
        ea_clamp=(min(ea_all), max(ea_all)),
        conditions=conditions,
        n_train=int(len(rows.y_sym)),
    )
    report: dict[str, object] = {
        "selected_alpha": best_alpha,
        "pooled_rmse_by_alpha": pooled_scores,
        "cv": cv,
        "n_train": int(len(rows.y_sym)),
        "n_pair_groups": int(len(np.unique(rows.grp))),
        "lev_q75": model.lev_q75,
        "lev_q90": model.lev_q90,
        "lev_q95": model.lev_q95,
        "tier0_nu0_hz": model.tier0_nu0_hz,
        "tier0_nu0_psinv": model.tier0_nu0_hz / HZ_PER_PSINV,
        "context_count_ranges": aux_ranges,
        "ea_clamp": model.ea_clamp,
    }
    return model, report


def load_h2_theta_csv(path: str | Path) -> FloatArray:
    """Load the H(σ) v2 theta CSV and assert its feature set/order == :data:`H2FEATS`."""
    names: list[str] = []
    vals: list[float] = []
    with open(path) as fh:
        for row in csv.reader(fh):
            if not row or row[0].startswith("#") or row[0] == "feature":
                continue
            names.append(row[0])
            vals.append(float(row[1]))
    if tuple(names) != H2FEATS:
        raise ValueError(
            f"H(σ) theta CSV feature order {names} != H2FEATS {list(H2FEATS)}; "
            "the dE_model basis and the embedded theta must agree exactly"
        )
    return np.array(vals, dtype=np.float64)


def stamp_catalogue(classes: Sequence[EventClass], model: EsymModel) -> None:
    """Populate the [C] Phase C fields on every class in place (quarantined included).

    ``phi`` = :func:`phi_vector`; ``model_version``/``dE_model_version``/
    ``nu0_pair_policy`` = the model stamps; ``fallback_stats`` =
    ``(leverage, leverage > lev_q75, model_version, tier)`` with ``tier`` =
    ``"measured_raw_pair"`` for non-quarantined and ``"quarantined"`` otherwise.
    Provenance is harmless on quarantined classes — ``audit_status`` stays the exclusion
    mechanism.
    """
    for c in classes:
        phi = phi_vector(c)
        lev = leverage(model, phi)
        tier = "quarantined" if c.audit_status == "quarantined" else "measured_raw_pair"
        c.phi = phi
        c.model_version = model.model_version
        c.dE_model_version = model.dE_model_version
        c.nu0_pair_policy = DEFAULT_NU0_PAIR_POLICY
        c.fallback_stats = (lev, bool(lev > model.lev_q75), model.model_version, tier)


def main() -> None:  # pragma: no cover - machine-local artifact driver
    """Fit the model, write artifacts, and stamp the [C] fields on the QC'd catalogue."""
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    from pylatkmc.ingest.event_class import read_catalogue_parquet, write_catalogue_parquet

    repo = Path(__file__).resolve().parents[2]
    qc_path = repo / ".scratch/phaseC/catalogue_qc_rcut8p5.parquet"
    out_parquet = repo / ".scratch/phaseC/catalogue_phasec_rcut8p5.parquet"
    model_json = repo / ".scratch/phaseC/esym_model_v1.json"
    theta_csv = Path("/home/kerr/pykmc/onlattice_design/E_sym_theta_2026-07-22.csv")
    h2_csv = Path("/home/kerr/pykmc/onlattice_design/H_sigma_v2_theta_2026-07-21.csv")

    conditions = (
        "production NiCr verify_fix_T500_1vac, rcut 8.5 A, QC'd corpus 422/422 "
        "(439 classes / 445 events; 17 classes / 23 events quarantined)"
    )

    classes = read_catalogue_parquet(qc_path)
    h2_theta = load_h2_theta_csv(h2_csv)
    model, report = fit_esym_model(classes, h2_theta, conditions=conditions)

    print("=== E_sym fit report ===")
    print(f"n_train={report['n_train']}  pair_groups={report['n_pair_groups']}  "
          f"features={len(model.feature_keys)}")
    print(f"selected alpha={report['selected_alpha']}")
    print(f"pooled RMSE by alpha: {report['pooled_rmse_by_alpha']}")
    for tag, met in report["cv"].items():  # type: ignore[attr-defined]
        print(f"  cv[{tag}]: {met}")
    print(f"leverage q75/q90/q95 = {report['lev_q75']:.4f} / "
          f"{report['lev_q90']:.4f} / {report['lev_q95']:.4f}")
    print(f"tier0_nu0 = {report['tier0_nu0_hz']:.6e} Hz  "
          f"({report['tier0_nu0_psinv']:.6f} ps^-1)")
    print(f"context ranges = {report['context_count_ranges']}")
    print(f"Ea clamp = {report['ea_clamp']}")

    save_model(model, model_json)
    print(f"wrote {model_json}")

    # human-readable theta record
    with open(theta_csv, "w") as fh:
        fh.write(
            f"# model_version={model.model_version} dE_model_version={model.dE_model_version} "
            f"alpha={model.alpha} n_train={model.n_train} date=2026-07-22\n"
        )
        fh.write(f"# conditions: {model.conditions}\n")
        fh.write("feature,mu,sd,theta\n")
        for k, mu_i, sd_i, w_i in zip(
            model.feature_keys, model.mu, model.sd, model.w, strict=True
        ):
            fh.write(f"{k},{mu_i:.10g},{sd_i:.10g},{w_i:.10g}\n")
        fh.write(f"intercept_ym,,,{model.ym:.10g}\n")
    print(f"wrote {theta_csv}")

    # stamp [C] fields + write phasec parquet, carrying forward QC conditions metadata
    stamp_catalogue(classes, model)
    src_md = pq.read_table(qc_path).schema.metadata or {}
    qc_cond = src_md.get(b"pylatkmc.qc.conditions", b"")
    phasec_stamp = (
        f"model_version={model.model_version} dE_model_version={model.dE_model_version} "
        f"nu0_pair_policy={DEFAULT_NU0_PAIR_POLICY} alpha={model.alpha} date=2026-07-22"
    ).encode()
    metadata = {b"pylatkmc.qc.conditions": qc_cond, b"pylatkmc.phasec.model": phasec_stamp}
    write_catalogue_parquet(classes, out_parquet, metadata=metadata)
    print(f"wrote {out_parquet}")


if __name__ == "__main__":  # pragma: no cover
    main()
