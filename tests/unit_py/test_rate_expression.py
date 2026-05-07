"""Tests for the catalogue → rate-constant bridge."""

from __future__ import annotations

import math

import pytest

from pylatkmc.rate_expression import (
    BUCKET_EA_STD_WARN_EV,
    KB_EV_PER_K,
    BoostFit,
    arrhenius_scalar,
    bucket_warns_on_scatter,
    fit_boost_along_axis,
)

# ---------------------------------------------------------------------------
# arrhenius_scalar
# ---------------------------------------------------------------------------


def test_arrhenius_zero_Ea() -> None:
    """Ea = 0 → rate is exactly k0."""
    assert arrhenius_scalar(Ea_eV=0.0, k0_Hz=1.0e13, T_K=500.0) == pytest.approx(1.0e13)


def test_arrhenius_canonical_500K_0p6eV() -> None:
    """k0 = 1e13 Hz, Ea = 0.6 eV, T = 500 K → rate = 1e13 * exp(-13.92)."""
    rate = arrhenius_scalar(Ea_eV=0.6, k0_Hz=1.0e13, T_K=500.0)
    expected = 1.0e13 * math.exp(-0.6 / (KB_EV_PER_K * 500.0))
    assert rate == pytest.approx(expected)
    assert rate == pytest.approx(8.95e6, rel=0.01)  # within 1% of pencil estimate


def test_arrhenius_T_dependence() -> None:
    """Lowering T makes the rate smaller (Arrhenius)."""
    r_low = arrhenius_scalar(Ea_eV=0.6, k0_Hz=1.0e13, T_K=300.0)
    r_high = arrhenius_scalar(Ea_eV=0.6, k0_Hz=1.0e13, T_K=900.0)
    assert r_low < r_high


def test_arrhenius_rejects_negative_Ea() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        arrhenius_scalar(Ea_eV=-0.1, k0_Hz=1.0e13, T_K=500.0)


def test_arrhenius_rejects_zero_T() -> None:
    with pytest.raises(ValueError, match="T_K"):
        arrhenius_scalar(Ea_eV=0.5, k0_Hz=1.0e13, T_K=0.0)


def test_arrhenius_rejects_zero_k0() -> None:
    with pytest.raises(ValueError, match="k0"):
        arrhenius_scalar(Ea_eV=0.5, k0_Hz=0.0, T_K=500.0)


# ---------------------------------------------------------------------------
# bucket_warns_on_scatter
# ---------------------------------------------------------------------------


def test_warn_low_scatter_no_warning() -> None:
    """Tight bucket (std=0.01 eV) should NOT warn."""
    assert bucket_warns_on_scatter(Ea_std_eV=0.01, n_events=1000) is None


def test_warn_high_scatter_warns() -> None:
    """Wide bucket (std=0.20 eV) at 1000 events should warn."""
    msg = bucket_warns_on_scatter(Ea_std_eV=0.20, n_events=1000)
    assert msg is not None
    assert "0.200" in msg or "0.2" in msg


def test_warn_threshold_at_default() -> None:
    """Sanity: the 0.05 eV threshold matches the BUCKET_EA_STD_WARN_EV constant."""
    just_above = bucket_warns_on_scatter(Ea_std_eV=0.06, n_events=100)
    just_below = bucket_warns_on_scatter(Ea_std_eV=0.04, n_events=100)
    assert just_above is not None
    assert just_below is None
    assert BUCKET_EA_STD_WARN_EV == 0.05


def test_warn_small_buckets_never_warn() -> None:
    """A bucket with < 10 events doesn't warn regardless of std."""
    assert bucket_warns_on_scatter(Ea_std_eV=1.0, n_events=2) is None
    assert bucket_warns_on_scatter(Ea_std_eV=1.0, n_events=9) is None
    # Threshold for warning is n_events >= 10
    assert bucket_warns_on_scatter(Ea_std_eV=1.0, n_events=10) is not None


# ---------------------------------------------------------------------------
# fit_boost_along_axis
# ---------------------------------------------------------------------------


def test_fit_boost_perfect_linear() -> None:
    """Ea(n) = 0.5 + 0.05*n → slope = 0.05, R² = 1, boost = exp(-0.05/kT)."""
    counts = [0, 1, 2, 3]
    Ea = [0.50, 0.55, 0.60, 0.65]
    fit = fit_boost_along_axis(counts, Ea, T_K=500.0)
    assert fit is not None
    assert fit.Ea_0_eV == pytest.approx(0.50, abs=1e-9)
    assert fit.Ea_per_count_eV == pytest.approx(0.05, abs=1e-9)
    assert pytest.approx(1.0, abs=1e-9) == fit.R2
    expected_boost = math.exp(-0.05 / (KB_EV_PER_K * 500.0))
    assert fit.boost == pytest.approx(expected_boost, rel=1e-9)
    assert fit.n_buckets_fitted == 4


def test_fit_boost_constant_Ea() -> None:
    """Constant Ea → slope = 0, boost = 1, R² = 1."""
    fit = fit_boost_along_axis(
        counts=[0, 1, 2],
        Ea_means_eV=[0.6, 0.6, 0.6],
        T_K=500.0,
    )
    assert fit is not None
    assert fit.Ea_per_count_eV == pytest.approx(0.0, abs=1e-9)
    assert fit.boost == pytest.approx(1.0, rel=1e-9)


def test_fit_boost_rejects_nonmonotone() -> None:
    """Ea(n) goes up-then-down → R² < 0.5 → returns None."""
    fit = fit_boost_along_axis(
        counts=[0, 1, 2, 3],
        Ea_means_eV=[0.5, 0.7, 0.7, 0.5],  # peak in the middle
        T_K=500.0,
    )
    assert fit is None  # poor linear fit


def test_fit_boost_rejects_single_count() -> None:
    """Only one distinct count → can't fit a line."""
    fit = fit_boost_along_axis(counts=[2], Ea_means_eV=[0.6], T_K=500.0)
    assert fit is None


def test_fit_boost_rejects_repeated_counts() -> None:
    """All counts identical → can't fit a slope."""
    fit = fit_boost_along_axis(
        counts=[1, 1, 1],
        Ea_means_eV=[0.5, 0.6, 0.7],
        T_K=500.0,
    )
    assert fit is None


def test_fit_boost_with_weights() -> None:
    """Weighted LS gives less influence to small-N buckets."""
    # Tail bucket (n=3) is an outlier; weight = 1 vs weight = 1000 for others.
    counts = [0, 1, 2, 3]
    Ea = [0.50, 0.55, 0.60, 0.99]  # n=3 is outlier
    weights = [1000, 1000, 1000, 1]
    fit = fit_boost_along_axis(counts, Ea, weights=weights, T_K=500.0)
    assert fit is not None
    # Heavily-weighted points dominate; slope ≈ 0.05 from first 3 points
    assert fit.Ea_per_count_eV == pytest.approx(0.05, abs=0.02)


def test_fit_boost_evaluate_rate_consistent() -> None:
    """BoostFit.evaluate_rate(n) should match Arrhenius at Ea_0 + n*slope."""
    fit = BoostFit(
        Ea_0_eV=0.5,
        boost=0.5,  # rate halves per count
        Ea_per_count_eV=KB_EV_PER_K * 500.0 * math.log(2),  # ≈ 0.0299 eV
        R2=1.0,
        n_buckets_fitted=3,
    )
    # rate(0) should equal arrhenius(Ea=0.5)
    r0 = fit.evaluate_rate(0, k0_Hz=1.0e13, T_K=500.0)
    assert r0 == pytest.approx(arrhenius_scalar(0.5, 1.0e13, 500.0), rel=1e-9)
    # rate(1) should be exactly r0 / 2 (boost = 0.5)
    r1 = fit.evaluate_rate(1, k0_Hz=1.0e13, T_K=500.0)
    assert r1 == pytest.approx(r0 * 0.5, rel=1e-9)


def test_fit_boost_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="weights must be positive"):
        fit_boost_along_axis(
            counts=[0, 1],
            Ea_means_eV=[0.5, 0.6],
            weights=[1, -1],
        )


def test_fit_boost_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        fit_boost_along_axis(counts=[0, 1, 2], Ea_means_eV=[0.5, 0.6])


def test_boostfit_is_frozen() -> None:
    """BoostFit is a dataclass(frozen=True) for hashability."""
    fit = BoostFit(Ea_0_eV=0.5, boost=1.0, Ea_per_count_eV=0.0, R2=1.0, n_buckets_fitted=2)
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError
        fit.boost = 0.99  # type: ignore[misc]
