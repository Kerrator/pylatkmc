"""Bridge from curated-catalogue Ea statistics to a Process's rate constant.

The curated FCC family catalogue (`rate_lookup_table_family.csv`) gives
per-family-bucket statistics:

    Ea_mean_eV, Ea_std_eV, Ea_min_eV, Ea_max_eV, Ea_median_eV, n_events.

The pattern-DB needs to convert each row into something the runtime can
use. There are three regimes:

1. **Scalar rate (default).** No Bystanders. The Process's
   `rate_constant` is `k0 * exp(-Ea_mean / kT)`, baked at codegen time.

2. **Multiplicative-boost rate (Bystanders present).** When the
   catalogue's bucket key includes a count axis (e.g. `n_Fe_nn1`) that
   we want to model as a Bystander rather than a separate Process per
   count, we fit:

       rate(n) = k0 * exp(-Ea_0 / kT) * boost^n

   where `Ea_0` is the bucket's Ea at `n=0` and `boost` captures how
   the rate scales with each additional count. The runtime evaluates
   `boost^nr_<species>_<flag>` per touchup. Cheap if the count
   distribution is narrow.

3. **Per-bucket Process (fallback).** When the rate-vs-count relationship
   is non-monotone (e.g. Ea peaks at intermediate count) or has wide
   scatter (`Ea_std > 0.05 eV` within a bucket), we don't fit a smooth
   expression. Instead, we emit one Process per bucket with the bucket's
   mean rate. The translator's `BUCKET_AS_CONDITIONS` mode handles this.

This module is consumed by `pylatkmc.translator` and exposes:

    arrhenius_scalar(Ea_eV, k0_Hz, T_K) -> float
    fit_boost_along_axis(buckets, axis_name) -> BoostFit | None
    bucket_warns_on_scatter(bucket_row) -> str | None

It is **pure-Python, NumPy-only**. No I/O.

References:
- kmos's OTF rate-expression machinery: `kmos-main/kmos/io/__init__.py`
  (search for `otf_rate`, `evaluate_rate`)
- The curated catalogue's family table:
  `apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table_family.csv`
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Boltzmann constant (matches `pylatkmc.ratebuilder` and friends).
KB_EV_PER_K = 8.617333e-5  # eV/K

# A bucket whose Ea standard deviation exceeds this is flagged as
# "too noisy" — the per-bucket mean is unlikely to be a good summary.
# 0.05 eV ~ 10x kT at 500 K → rate factor ~e^10 ≈ 22,000x scatter.
BUCKET_EA_STD_WARN_EV = 0.05


def arrhenius_scalar(Ea_eV: float, k0_Hz: float, T_K: float) -> float:
    """Plain Arrhenius: ``k = k0 * exp(-Ea / kT)``.

    The "default" rate path: if a Process has no Bystanders, its rate is
    just this scalar baked in at codegen.

    Parameters
    ----------
    Ea_eV : float
        Activation energy in eV. Must be ≥ 0 (raises if not).
    k0_Hz : float
        Attempt frequency / prefactor in Hz. Must be > 0.
    T_K : float
        Temperature in K. Must be > 0.

    Returns
    -------
    float
        Rate in Hz (= s^-1).
    """
    if not (Ea_eV >= 0):
        raise ValueError(f"Ea_eV must be non-negative; got {Ea_eV}")
    if not (k0_Hz > 0):
        raise ValueError(f"k0_Hz must be positive; got {k0_Hz}")
    if not (T_K > 0):
        raise ValueError(f"T_K must be positive; got {T_K}")
    return float(k0_Hz * math.exp(-Ea_eV / (KB_EV_PER_K * T_K)))


def bucket_warns_on_scatter(
    Ea_std_eV: float,
    n_events: int,
    threshold_eV: float = BUCKET_EA_STD_WARN_EV,
) -> str | None:
    """Return a human-readable warning if a bucket's Ea scatter is too
    wide for its mean to be a reliable summary; otherwise None.

    Two-event buckets are not flagged regardless of std (small-N
    noise dominates). Buckets with n_events ≥ 10 and std > threshold
    are flagged.

    Parameters
    ----------
    Ea_std_eV : float
        Bucket's standard deviation of Ea (from the family rate table).
    n_events : int
        Number of catalogue events that contributed to this bucket.
    threshold_eV : float
        Warn threshold; default 0.05 eV (~10x kT at 500K).

    Returns
    -------
    str | None
        Warning message if scatter is wide, else None.
    """
    if n_events < 10:
        return None
    if not (Ea_std_eV > threshold_eV):
        return None
    return (
        f"bucket Ea_std={Ea_std_eV:.3f} eV exceeds threshold "
        f"{threshold_eV:.3f} eV across {n_events} events; per-bucket "
        f"mean rate may not be a good summary"
    )


@dataclass(frozen=True)
class BoostFit:
    """Multiplicative-boost rate fit along a single count axis.

        rate(n) = base_rate * boost^n

    where ``n`` is the count of a specific (species, flag) Bystander
    pair and ``base_rate = k0 * exp(-Ea_0 / kT)``. Equivalently, in
    Arrhenius form:

        Ea(n) = Ea_0 - n * kT * ln(boost)
              = Ea_0 + n * (Ea_per_count)

    so a boost factor < 1 means each additional count slows the
    process; > 1 speeds it up.

    Attributes
    ----------
    Ea_0_eV : float
        Activation energy at count = 0.
    boost : float
        Multiplicative factor per unit count. boost < 1 raises the
        barrier; boost > 1 lowers it.
    Ea_per_count_eV : float
        Equivalent in eV per count: ``-kT * ln(boost)``.
    R2 : float
        Coefficient of determination of the linear fit of Ea vs count.
        Above 0.9 = high confidence; below 0.5 = poor fit, fall back to
        per-bucket Processes.
    n_buckets_fitted : int
        Number of (count, Ea_mean) pairs in the fit.
    """

    Ea_0_eV: float
    boost: float
    Ea_per_count_eV: float
    R2: float
    n_buckets_fitted: int

    def evaluate_rate(self, n_count: int, k0_Hz: float, T_K: float) -> float:
        """Concrete rate at a given count. For tests / sanity-checks."""
        Ea = self.Ea_0_eV + n_count * self.Ea_per_count_eV
        return arrhenius_scalar(Ea_eV=Ea, k0_Hz=k0_Hz, T_K=T_K)


def fit_boost_along_axis(
    counts: list[int],
    Ea_means_eV: list[float],
    weights: list[int] | None = None,
    T_K: float = 500.0,
) -> BoostFit | None:
    """Fit ``Ea(n) = Ea_0 + slope * n`` via weighted least-squares,
    returning a BoostFit if the fit is statistically reasonable.

    The Bystander rate is then ``rate(n) = k0 * exp(-Ea_0 / kT) * boost^n``
    with ``boost = exp(-slope / kT)``.

    Parameters
    ----------
    counts : list[int]
        Bystander counts (e.g. n_Fe_nn1 = 0, 1, 2, ...) — one per bucket.
    Ea_means_eV : list[float]
        Bucket-mean Ea at each count.
    weights : list[int] | None
        Number of catalogue events per bucket (used for weighted LS).
        If None, equal weights.
    T_K : float
        Temperature for the boost-factor computation. The BoostFit
        encodes Ea_per_count, which is T-independent; the boost factor
        is T-dependent and emitted for the caller's convenience.

    Returns
    -------
    BoostFit | None
        None if there are fewer than 2 distinct counts (can't fit a line)
        or if R² < 0.5 (relationship is non-monotone or noisy).
    """
    if len(counts) != len(Ea_means_eV):
        raise ValueError(
            f"counts and Ea_means_eV must have same length; got {len(counts)} vs {len(Ea_means_eV)}"
        )
    n = len(counts)
    if n < 2:
        return None
    distinct_counts = len(set(counts))
    if distinct_counts < 2:
        return None

    x = np.asarray(counts, dtype=float)
    y = np.asarray(Ea_means_eV, dtype=float)
    w = np.asarray(weights, dtype=float) if weights is not None else np.ones(n, dtype=float)
    if (w <= 0).any():
        raise ValueError(f"weights must be positive; got {weights}")

    # Weighted LS: minimise sum_i w_i * (y_i - (Ea_0 + slope * x_i))^2
    # Closed form: slope = cov_w(x,y) / var_w(x)
    W = w.sum()
    x_mean = (w * x).sum() / W
    y_mean = (w * y).sum() / W
    var_x = (w * (x - x_mean) ** 2).sum() / W
    if var_x == 0:
        return None
    cov_xy = (w * (x - x_mean) * (y - y_mean)).sum() / W
    slope = cov_xy / var_x
    Ea_0 = y_mean - slope * x_mean

    # Weighted R²: 1 - SS_res / SS_tot
    y_pred = Ea_0 + slope * x
    ss_res = (w * (y - y_pred) ** 2).sum()
    ss_tot = (w * (y - y_mean) ** 2).sum()
    # ss_tot == 0 means constant Ea → fit is trivially perfect (slope = 0).
    R2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot

    if R2 < 0.5:
        # The relationship isn't monotone enough to summarise as a
        # single boost factor; caller should fall back to per-bucket.
        return None

    boost = float(math.exp(-slope / (KB_EV_PER_K * T_K)))

    return BoostFit(
        Ea_0_eV=float(Ea_0),
        boost=boost,
        Ea_per_count_eV=float(slope),
        R2=float(R2),
        n_buckets_fitted=n,
    )


__all__ = (
    "KB_EV_PER_K",
    "BUCKET_EA_STD_WARN_EV",
    "arrhenius_scalar",
    "bucket_warns_on_scatter",
    "BoostFit",
    "fit_boost_along_axis",
)
