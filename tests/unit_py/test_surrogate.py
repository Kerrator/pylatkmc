"""Phase C E_sym surrogate tests: feature ports, ridge/leverage, model I/O, stamping.

Three tiers, matching the handoff:

- **Always-run synthetic** (numpy only): a real ``build_class_catalogue`` EventClass with
  pinned literal ``sym_features`` / ``dphi2`` / ``phi_vector``; the ``H2FEATS`` order pinned
  as a literal; ridge fit + leverage on a tiny fixed matrix with hardcoded expected outputs;
  ``EsymModel`` JSON round-trip; ``phi_vector`` unknown-key raise.
- **Stamping** (pyarrow-guarded): stamp a synthetic mini-catalogue, round-trip the Parquet,
  assert the [C] fields (``phi`` / versions / ``fallback_stats``) and ``schema_version`` survive.
- **Production pinned vectors** (skips without the machine-local QC'd Parquet): full ``phi`` +
  ``dphi2`` literals for four known class_ids spanning clean-hop Ni/Cr and multi-site Ni/Cr.

The feature literals are computed once against the verbatim script definitions (the
port-fidelity scratch check asserts exact equality) and hardcoded here.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pylatkmc.ingest import surrogate as S
from pylatkmc.ingest.event_class import (
    CATALOGUE_SCHEMA_VERSION,
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    EventProjReport,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
    build_class_catalogue,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_QC_PARQUET = REPO_ROOT / ".scratch/phaseC/catalogue_qc_rcut8p5.parquet"

_THRESHOLDS = GateThresholds(
    emin_event=0.0, emax_event=10.0, backward_emin_event=0.0, snap_tol=0.9, db_tol=0.05, rcut=5.0
)


def _sp(occ: Occ) -> OccPredicate:
    return OccPredicate("SPECIES", frozenset({occ}))


def _synth_class() -> EventClass:
    """A Cr 1NN in-plane surface hop with five context rows, via the REAL assembler."""
    pe = ProjectedEvent(
        anchor0=(0, 0, 0),
        delta=(
            DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.CR),
        ),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _sp(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), _sp(Occ.NI)),
            StencilSite((1, -1, 0), _sp(Occ.NI)),
            StencilSite((0, 2, 0), _sp(Occ.NI)),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.CR),),
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        coloring=Coloring.FULL,
        r_ctx_used=5.0,
        truncated=False,
        Ea_fwd_eV=0.6,
        nu0_fwd_hz=1.0e13,
        k_row=1.0,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        move_atom_idx=0,
        source_row=0,
        proj_report=EventProjReport(0.3, 0.2, 6.0, True),
    )
    return build_class_catalogue(
        [pe], t_ref_K=500.0, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )[0]


# ---------------------------------------------------------------------------
# Synthetic feature ports — pinned literals
# ---------------------------------------------------------------------------

_SYNTH_SYM = {
    "abs_delta_atoms": 0,
    "b_CE": 1.0,
    "b_CN": 1.5,
    "b_EN": 1.5,
    "b_NN": 1.0,
    "depth_param": 8,
    "depth_surface": 1,
    "mvC_E": 1.0,
    "mvC_N": 1.5,
    "n_delta": 2,
    "s0_C": 0.5,
    "s0_E": 0.5,
    "s0_N": 1.0,
    "s1_N": 2.0,
    "s9_C": 0.5,
    "s9_E": 0.5,
}

_SYNTH_DPHI2 = (
    0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 1.0,
)

_SYNTH_PHI = (
    0.0, 0.0, 1.0, 1.5, 0.0, 1.5, 1.0, 8.0, 1.0, 0.0, 1.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0,
    0.5, 0.5, 1.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
)


def test_sym_features_synthetic_pinned() -> None:
    """The symmetrized E_sym dict of a known synthetic class matches the pinned literal."""
    assert S.sym_features(_synth_class()) == _SYNTH_SYM


def test_dphi2_synthetic_pinned() -> None:
    """The surfsplit ΔΦ vector of the synthetic class matches the pinned literal (18 entries)."""
    v = S.dphi2(_synth_class())
    assert v.shape == (18,)
    assert tuple(v.tolist()) == _SYNTH_DPHI2


def test_phi_vector_synthetic_pinned() -> None:
    """phi_vector emits the pinned-order 68-vector; equals sym_features read by key."""
    phi = S.phi_vector(_synth_class())
    assert len(phi) == 68
    assert phi == _SYNTH_PHI


def test_h2feats_order_pinned() -> None:
    """The H(σ) v2 surfsplit feature order is byte-stable (index contract into theta)."""
    assert S.H2FEATS == (
        "pt_NI", "pt_CR",
        "b1B_NN", "b1B_NC", "b1B_CC", "b1S_NN", "b1S_NC", "b1S_CC",
        "b2B_NN", "b2B_NC", "b2B_CC", "b2S_NN", "b2S_NC", "b2S_CC",
        "b1_NU", "b1_CU", "b2_NU", "b2_CU",
    )
    assert len(S.H2FEATS) == 18
    assert S.H2IDX["pt_NI"] == 0 and S.H2IDX["b2_CU"] == 17


def test_esym_feature_keys_pinned_length() -> None:
    """The pinned E_sym basis is exactly the 68-feature validated corpus union, sorted."""
    assert len(S.ESYM_FEATURE_KEYS) == 68
    assert list(S.ESYM_FEATURE_KEYS) == sorted(S.ESYM_FEATURE_KEYS)
    assert S.ESYM_FEATURE_KEYS[0] == "abs_delta_atoms"
    assert S.ESYM_FEATURE_KEYS[-1] == "t3_UU"


def test_phi_vector_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sym_features key outside the pinned basis raises (loud, never silently dropped)."""
    cls = _synth_class()
    orig = S.sym_features

    def _fake(c: EventClass) -> dict[str, float]:
        d = orig(c)
        d["s99_Z"] = 1.0
        return d

    monkeypatch.setattr(S, "sym_features", _fake)
    with pytest.raises(ValueError, match="not in ESYM_FEATURE_KEYS"):
        S.phi_vector(cls)


# ---------------------------------------------------------------------------
# Ridge + leverage — tiny fixed matrix with hardcoded expected outputs
# ---------------------------------------------------------------------------

_X = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
_Y = np.array([1.0, 2.0, 1.5, 2.5, 3.0])


def test_ridge_fit_std_fixed() -> None:
    """ridge_fit_std reproduces the hand-computed standardized ridge on a 5x2 matrix."""
    mu, sd, ym, w, alpha = S.ridge_fit_std(_X, _Y, 1.0)
    assert alpha == 1.0
    np.testing.assert_allclose(mu, [0.8, 0.6])
    np.testing.assert_allclose(sd, [0.7483314773547883, 0.48989794855663565])
    assert ym == pytest.approx(2.0)
    np.testing.assert_allclose(w, [0.5012938621079772, 0.20346779749806673])


def test_ridge_pred_fixed() -> None:
    """ridge_pred on held-out points matches the hand-computed predictions."""
    m = S.ridge_fit_std(_X, _Y, 1.0)
    pred = S.ridge_pred(m, np.array([[0.5, 0.5], [2.0, 2.0]]))
    np.testing.assert_allclose(pred, [1.757502679528403, 3.385316184351554])


def test_leverage_fixed() -> None:
    """Ainv + z@Ainv@z leverages match the hand-computed values (V5 einsum)."""
    m = S.ridge_fit_std(_X, _Y, 1.0)
    mu, sd, _, _, _ = m
    ainv = S.ridge_ainv(m, _X)
    np.testing.assert_allclose(
        ainv,
        [[0.18006430868167206, -0.04911656693414619],
         [-0.04911656693414619, 0.18006430868167203]],
    )
    lev = S.leverages(_X, mu, sd, ainv)
    np.testing.assert_allclose(
        lev,
        [0.34726688102893893, 0.315112540192926, 0.41157556270096474,
         0.1114683815648446, 0.45444801714898186],
    )


def test_ridge_fit_nointercept_fixed() -> None:
    """The no-intercept ridge (H(σ) ΔΦ fitter) matches the hand-computed theta."""
    theta = S.ridge_fit_nointercept(_X, _Y, 0.5)
    np.testing.assert_allclose(theta, [1.1454545454545455, 1.0181818181818179])


# ---------------------------------------------------------------------------
# EsymModel container + prediction helpers + JSON round-trip
# ---------------------------------------------------------------------------


def _tiny_model() -> S.EsymModel:
    """A small, exactly-round-trippable EsymModel over 3 E_sym + 2 H features."""
    return S.EsymModel(
        model_version="E_sym_v1_ridge_sym2b3b",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        alpha=30.0,
        feature_keys=("a", "b", "c"),
        mu=np.array([0.5, 1.0, 2.0]),
        sd=np.array([1.0, 2.0, 0.5]),
        ym=0.25,
        w=np.array([0.1, -0.2, 0.3]),
        h2_feature_names=("h0", "h1"),
        h2_theta=np.array([1.5, -0.5]),
        ainv=np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]]),
        lev_q75=0.11,
        lev_q90=0.21,
        lev_q95=0.29,
        tier0_nu0_hz=4.17e12,
        context_count_ranges={"N": (63, 128), "C": (1, 11), "E": (83, 174)},
        ea_clamp=(0.0, 2.31),
        conditions="unit-test tiny model",
        n_train=3,
    )


def test_esym_model_json_round_trip(tmp_path: Path) -> None:
    """save_model → load_model reproduces every field exactly (float64 JSON is exact)."""
    m = _tiny_model()
    p = tmp_path / "m.json"
    S.save_model(m, p)
    r = S.load_model(p)
    assert r.model_version == m.model_version
    assert r.dE_model_version == m.dE_model_version
    assert r.alpha == m.alpha
    assert r.feature_keys == m.feature_keys
    assert r.h2_feature_names == m.h2_feature_names
    np.testing.assert_array_equal(r.mu, m.mu)
    np.testing.assert_array_equal(r.sd, m.sd)
    np.testing.assert_array_equal(r.w, m.w)
    np.testing.assert_array_equal(r.h2_theta, m.h2_theta)
    np.testing.assert_array_equal(r.ainv, m.ainv)
    assert r.ym == m.ym
    assert (r.lev_q75, r.lev_q90, r.lev_q95) == (m.lev_q75, m.lev_q90, m.lev_q95)
    assert r.tier0_nu0_hz == m.tier0_nu0_hz
    assert r.context_count_ranges == m.context_count_ranges
    assert r.ea_clamp == m.ea_clamp
    assert r.n_train == m.n_train


def test_prediction_helpers() -> None:
    """predict_esym / predict_dE / leverage / surrogate_barrier match closed-form values."""
    m = _tiny_model()
    phi = [1.5, 3.0, 1.0]  # z = (1.0, 1.0, -2.0)
    # E_sym = z·w + ym = 0.1 - 0.2 - 0.6 + 0.25 = -0.45
    assert S.predict_esym(m, phi) == pytest.approx(-0.45)
    # ΔE = dphi2·theta ; dphi2 = (2, 4) -> 2*1.5 + 4*-0.5 = 1.0
    assert S.predict_dE(m, [2.0, 4.0]) == pytest.approx(1.0)
    # leverage = z·Ainv·z = 2*1 + 0.5*1 + 1*4 = 6.5
    assert S.leverage(m, phi) == pytest.approx(6.5)


def test_json_key_order_deterministic(tmp_path: Path) -> None:
    """The model JSON is written with a deterministic (sorted) key order."""
    m = _tiny_model()
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    S.save_model(m, p1)
    S.save_model(m, p2)
    assert p1.read_text() == p2.read_text()
    import json

    keys = list(json.loads(p1.read_text()).keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Stamping round-trip (pyarrow-guarded)
# ---------------------------------------------------------------------------


def test_stamp_catalogue_parquet_round_trip(tmp_path: Path) -> None:
    """Stamping a mini-catalogue then Parquet round-trip preserves the [C] fields."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.event_class import read_catalogue_parquet, write_catalogue_parquet

    # a small model whose leverage on phi = ||phi||^2 (identity Ainv, zero mu/unit sd)
    n = len(S.ESYM_FEATURE_KEYS)
    model = S.EsymModel(
        model_version="E_sym_v1_ridge_sym2b3b",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        alpha=30.0,
        feature_keys=S.ESYM_FEATURE_KEYS,
        mu=np.zeros(n),
        sd=np.ones(n),
        ym=0.0,
        w=np.zeros(n),
        h2_feature_names=S.H2FEATS,
        h2_theta=np.zeros(len(S.H2FEATS)),
        ainv=np.eye(n),
        lev_q75=50.0,
        lev_q90=80.0,
        lev_q95=100.0,
        tier0_nu0_hz=4.17e12,
        context_count_ranges={"N": (1, 2), "C": (0, 1), "E": (1, 3)},
        ea_clamp=(0.0, 2.0),
        conditions="unit-test",
        n_train=1,
    )

    cls = _synth_class()
    # give the catalogue a second, quarantined class to exercise the tier branch
    cls_q = _synth_class()
    cls_q.class_id = cls.class_id[:-1] + ("0" if cls.class_id[-1] != "0" else "1")
    cls_q.audit_status = "quarantined"
    classes = [cls, cls_q]

    S.stamp_catalogue(classes, model)

    # in-memory checks
    assert len(cls.phi) == 68
    assert cls.model_version == "E_sym_v1_ridge_sym2b3b"
    assert cls.dE_model_version == "H_sigma_v2_surfsplit_aug"
    assert cls.nu0_pair_policy == "harvested_pair"
    lev, hull, mv, tier = cls.fallback_stats
    assert mv == "E_sym_v1_ridge_sym2b3b"
    assert tier == "measured_raw_pair"
    assert isinstance(hull, bool) and lev == pytest.approx(sum(x * x for x in cls.phi))
    assert cls_q.fallback_stats[3] == "quarantined"

    p = tmp_path / "stamped.parquet"
    write_catalogue_parquet(classes, p, metadata={b"pylatkmc.phasec.model": b"unit-test-stamp"})
    back = {c.class_id: c for c in read_catalogue_parquet(p)}

    rc = back[cls.class_id]
    assert tuple(rc.phi) == tuple(cls.phi)
    assert rc.model_version == "E_sym_v1_ridge_sym2b3b"
    assert rc.dE_model_version == "H_sigma_v2_surfsplit_aug"
    assert rc.nu0_pair_policy == "harvested_pair"
    assert rc.fallback_stats[0] == pytest.approx(lev)
    assert rc.fallback_stats[1] is True or rc.fallback_stats[1] is False
    assert rc.fallback_stats[2] == "E_sym_v1_ridge_sym2b3b"
    assert rc.fallback_stats[3] == "measured_raw_pair"
    assert rc.schema_version == CATALOGUE_SCHEMA_VERSION
    assert back[cls_q.class_id].fallback_stats[3] == "quarantined"


# ---------------------------------------------------------------------------
# Production pinned vectors (skips without the machine-local QC'd Parquet)
# ---------------------------------------------------------------------------

# class_id -> (phi 68-vector, dphi2 18-vector), computed once vs the verbatim script.
_PROD_CLEAN_NI = "0257804f0370b043a626d6a19268ca300d999ca2c738327169cd1b842f1c9197"
_PROD_CLEAN_CR = "011d29b208dc43fcca8bc17b944f125d2c11ef0ea7a4aff5059a556b5f7f231f"
_PROD_MULTI_CR = "00821ba9a9a190860f55d0f74f53735de51dacd8c3281ecdcd8bb3dda2463e0e"
_PROD_MULTI_NI = "00fbe757ebeaa250b5dd26affa09885c32d6c2ff54eaf997a488599b3863d9b1"

_PROD_PHI = {
    _PROD_CLEAN_NI: (
        0.0, 0.0, 10.5, 53.5, 381.0, 200.5, 398.5, 7.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.5, 5.0, 6.5,
        0.0, 2.0, 1.0, 5.0, 6.0, 0.0, 0.0, 3.0, 3.0, 0.0, 0.0, 7.0, 17.0, 0.0, 1.0, 5.0, 6.0,
        0.0, 0.0, 11.0, 13.0, 0.0, 1.0, 4.0, 3.0, 0.0, 2.0, 18.0, 20.0, 0.0, 0.0, 2.0, 2.0, 0.0,
        1.0, 10.0, 10.0, 0.0, 0.0, 44.0, 30.0, 0.0, 0.0, 0.5, 1.5, 0.0, 5.0, 9.5, 0.0, 7.5, 0.0,
        0.0,
    ),
    _PROD_CLEAN_CR: (
        0.0, 0.5, 13.0, 22.0, 319.5, 150.0, 337.0, 7.0, 1.0, 0.5, 7.5, 4.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 2.0, 1.0, 5.0, 6.0, 0.0, 1.5, 2.5, 2.0, 0.0, 0.0, 10.0, 14.0, 0.0, 0.0, 4.0, 8.0,
        0.0, 0.0, 10.0, 14.0, 0.0, 0.0, 3.0, 5.0, 0.0, 0.0, 18.0, 22.0, 0.0, 0.0, 2.0, 2.0, 0.0,
        0.0, 14.0, 7.0, 0.0, 0.5, 24.5, 10.0, 39.0, 0.0, 1.0, 1.0, 0.0, 11.5, 6.0, 0.0, 4.5, 0.0,
        0.0,
    ),
    _PROD_MULTI_CR: (
        1.0, 0.0, 9.0, 13.0, 304.5, 134.0, 291.5, 6.0, 1.0, 0.0, 8.0, 4.0, 0.0, 0.0, 1.5, 4.5,
        0.0, 3.0, 0.0, 0.0, 12.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 1.0, 14.0, 0.0, 0.5, 2.5, 6.0,
        0.0, 1.0, 1.0, 10.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 6.5, 9.5, 2.0, 0.0, 0.0, 3.0, 0.0,
        0.0, 5.0, 7.0, 3.0, 0.5, 71.5, 10.0, 52.0, 0.0, 0.0, 0.0, 0.0, 14.0, 10.0, 0.0, 12.0,
        0.0, 0.0,
    ),
    _PROD_MULTI_NI: (
        1.0, 1.0, 8.5, 25.5, 314.5, 296.5, 183.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 12.5, 13.0,
        4.0, 5.0, 1.0, 5.0, 6.0, 0.0, 0.0, 3.0, 3.0, 0.0, 0.0, 15.0, 9.0, 0.0, 0.0, 5.0, 5.0,
        0.0, 1.0, 7.0, 10.0, 0.0, 0.0, 3.0, 2.0, 0.0, 0.0, 20.0, 10.0, 0.0, 0.0, 2.0, 1.0, 0.0,
        1.0, 11.0, 5.0, 2.0, 0.0, 41.5, 17.5, 63.0, 0.0, 0.0, 2.0, 0.0, 13.0, 17.5, 6.5, 15.0,
        2.5, 3.5,
    ),
}

_PROD_DPHI2 = {
    _PROD_CLEAN_NI: (0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     0.0, 0.0, 0.0),
    _PROD_CLEAN_CR: (0.0, 0.0, -5.0, -1.0, 0.0, 5.0, -3.0, -1.0, -4.0, 0.0, 0.0, 4.0, 0.0, -1.0,
                     0.0, 0.0, 0.0, 0.0),
    _PROD_MULTI_CR: (-1.0, 0.0, -14.0, 0.0, 0.0, 5.0, -4.0, 0.0, -5.0, 0.0, 0.0, 2.0, -2.0, 0.0,
                     0.0, 0.0, -1.0, 1.0),
    _PROD_MULTI_NI: (1.0, 0.0, 14.0, 6.0, 0.0, -6.0, -5.0, 0.0, 5.0, 2.0, 1.0, 3.0, -3.0, -1.0,
                     4.0, 0.0, 3.0, 0.0),
}


@pytest.mark.parametrize("class_id", sorted(_PROD_PHI))
def test_production_pinned_vectors(class_id: str) -> None:
    """Known production class_ids reproduce their pinned phi + dphi2 vectors exactly."""
    pytest.importorskip("pyarrow")
    if not _QC_PARQUET.exists():
        pytest.skip(f"machine-local QC'd catalogue absent: {_QC_PARQUET}")
    from pylatkmc.ingest.event_class import read_catalogue_parquet

    by_id = {c.class_id: c for c in read_catalogue_parquet(_QC_PARQUET)}
    cls = by_id[class_id]
    assert S.phi_vector(cls) == _PROD_PHI[class_id]
    assert tuple(S.dphi2(cls).tolist()) == _PROD_DPHI2[class_id]
