"""Pure-NumPy implementation of the Sharia & Henkelman 2016 RPA recrossing
correction κ and the Vineyard harmonic prefactor ν₀.

Reference:
    Sharia, O. & Henkelman, G. *New J. Phys.* 18, 013023 (2016).
    "Analytic dynamical corrections to transition state theory."

This module is intentionally LAMMPS-free. The Hessians come in as ndarrays;
how they were obtained is the driver's problem (see hessian_lammps.py).

------------------------------------------------------------------------------
Units convention (DO NOT MIX)
------------------------------------------------------------------------------
- Mass-weighted Hessian H_mw : eV / (amu · Å²)
- Eigenvalues of H_mw         : same; equal to (ωᵢ_rad/s)² in atomic-style natural units
- ℏω frequencies              : eV (matches kᵇ = 8.617333e-5 eV/K)
- Conversion factor           : ℏω_eV = HBAR_OMEGA_EV * sqrt(eigenvalue_in_natural)
                                with HBAR_OMEGA_EV ≈ 0.06466 eV / sqrt(eV/(amu·Å²))
- Coupling Λ                  : eV (after mass-weighting and FD; same units as ω²)
- ν₀ output                   : Hz
- T input                     : K (converted internally to kᵇT in eV)

The 0.06466 prefactor comes from:
    ℏω [eV] = (ℏ [J·s] / e [J/eV]) × sqrt(λ [J/(kg·m²)])
            = (ℏ × sqrt(amu·Å² → kg·m²)) / e × sqrt(λ_natural)
which numerically evaluates to 0.06466. Verified by 5-THz round-trip (see tests).
"""

from __future__ import annotations

import warnings

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
KB_EV_PER_K = 8.617333e-5         # eV/K, matches build_rate_table.py:138
HBAR_EV_S = 6.582119569e-16       # ℏ in eV·s
HBAR_OMEGA_EV = 0.06466           # eV / sqrt(eV/(amu·Å²)); see module docstring
ZERO_MODE_TOL_EV2 = 1.0e-6        # eigenvalues with |λ| < this are projected out as zero modes
KAPPA_UPPER_BOUND = 1.0001        # numerical excursions above 1 are tolerable up to here


# ---------------------------------------------------------------------------
# Normal-mode analysis
# ---------------------------------------------------------------------------

def normal_modes_from_hessian(
    H_mw: np.ndarray,
    n_zero_modes: int = 3,
    expect_saddle: bool = True,
) -> tuple[float | None, np.ndarray, np.ndarray, int]:
    """Diagonalise a mass-weighted Hessian and return frequency data.

    Parameters
    ----------
    H_mw : (M, M) ndarray
        Mass-weighted Hessian over M = 3 × n_free_atoms degrees of freedom.
    n_zero_modes : int
        Number of translational/rotational zero modes to project out
        (3 for periodic slabs, 6 for free clusters). Identified as the
        smallest-|eigenvalue| modes after diagonalisation.
    expect_saddle : bool
        If True, exactly ONE negative eigenvalue is expected (first-order
        saddle). If False (e.g. minimum), no negative mode required.

    Returns
    -------
    omega0_eV : float or None
        Positive magnitude of ℏω at the imaginary mode. None if no saddle
        (when expect_saddle=False and no negative eigenvalue found).
    omegas_eV : (N,) ndarray
        Positive ℏω of the real modes (after dropping zero modes and the
        negative mode). N = M - n_zero_modes - 1 (saddle) or M - n_zero_modes (min).
    R : (M, M) ndarray
        Eigenvectors as columns, in the same order as the SORTED eigenvalues
        (most-negative first). Used by `coupling_matrix` to transform the
        Hessian derivative into normal-mode basis.
    neg_idx : int
        Column index in R of the negative-mode eigenvector (-1 if none).

    Raises
    ------
    ValueError
        If H_mw is not symmetric, or if `expect_saddle=True` and the
        spectrum has !=1 negative eigenvalue (after zero-mode removal).
    """
    if H_mw.ndim != 2 or H_mw.shape[0] != H_mw.shape[1]:
        raise ValueError(f"H_mw must be square, got shape {H_mw.shape}")
    if not np.allclose(H_mw, H_mw.T, atol=1e-8):
        raise ValueError("H_mw must be symmetric")

    eigvals, eigvecs = np.linalg.eigh(H_mw)  # ascending order

    # Identify negative mode(s) FIRST. For a first-order saddle, exactly
    # one eigenvalue is below -ZERO_MODE_TOL_EV2; we must NOT confuse it
    # with a "zero mode". Without this step, a saddle whose imaginary mode
    # has |λ| smaller than some near-zero positive modes (common for
    # NEB-only saddles where translations haven't fully relaxed to 0) gets
    # the imaginary mode misclassified as a zero mode.
    neg_full_indices = np.where(eigvals < -ZERO_MODE_TOL_EV2)[0]

    # Pick zero modes from the POSITIVE-or-near-zero eigenvalue subset,
    # excluding any negative modes found above. We sort the remaining by
    # |λ| ascending and take the n_zero_modes smallest as zero modes.
    keep_mask_for_zero_picking = np.ones(len(eigvals), dtype=bool)
    keep_mask_for_zero_picking[neg_full_indices] = False
    candidate_indices = np.where(keep_mask_for_zero_picking)[0]
    abs_candidate_eigs = np.abs(eigvals[candidate_indices])
    sort_order = np.argsort(abs_candidate_eigs)
    zero_mode_indices = candidate_indices[sort_order[:n_zero_modes]]

    keep_mask = np.ones(len(eigvals), dtype=bool)
    keep_mask[zero_mode_indices] = False

    eigvals_kept = eigvals[keep_mask]
    eigvecs_kept = eigvecs[:, keep_mask]

    # Identify negative mode(s) among the kept (now reliably the
    # imaginary mode if expect_saddle).
    neg_indices = np.where(eigvals_kept < -ZERO_MODE_TOL_EV2)[0]

    if expect_saddle:
        if len(neg_indices) != 1:
            raise ValueError(
                f"Expected exactly 1 negative eigenvalue at saddle, got "
                f"{len(neg_indices)} (eigenvalues: {eigvals_kept[neg_indices]})"
            )
        neg_idx = int(neg_indices[0])
        omega0_natural = float(np.sqrt(-eigvals_kept[neg_idx]))
        omega0_eV = HBAR_OMEGA_EV * omega0_natural

        # Drop the negative mode for the positive-frequency list
        keep_pos = np.ones(len(eigvals_kept), dtype=bool)
        keep_pos[neg_idx] = False
        positive_eigvals = eigvals_kept[keep_pos]
    else:
        if len(neg_indices) > 0:
            warnings.warn(
                f"Expected minimum (no negative mode) but found {len(neg_indices)} "
                f"negative eigenvalues. Treating as warning.", RuntimeWarning,
            )
        neg_idx = -1
        omega0_eV = None
        positive_eigvals = eigvals_kept[eigvals_kept > 0]

    # Convert positive eigenvalues to ℏω in eV
    if (positive_eigvals < 0).any():
        # After saddle removal, all should be positive. Anything still negative
        # is a soft mode that should have been projected; clamp to 0.
        positive_eigvals = np.maximum(positive_eigvals, 0.0)
    omegas_eV = HBAR_OMEGA_EV * np.sqrt(positive_eigvals)

    # Reconstruct full eigenvector matrix in original sorted order
    # (with zero modes still included so neg_idx maps consistently)
    return omega0_eV, omegas_eV, eigvecs, _absolute_neg_idx(eigvals, neg_idx, zero_mode_indices)


def _absolute_neg_idx(eigvals_full: np.ndarray, neg_idx_kept: int,
                      zero_mode_indices: np.ndarray) -> int:
    """Map neg_idx from the post-zero-mode-removal ordering back to the
    full eigenvalue ordering returned by eigh."""
    if neg_idx_kept < 0:
        return -1
    keep_mask = np.ones(len(eigvals_full), dtype=bool)
    keep_mask[zero_mode_indices] = False
    full_indices = np.where(keep_mask)[0]
    return int(full_indices[neg_idx_kept])


# ---------------------------------------------------------------------------
# Vineyard prefactor
# ---------------------------------------------------------------------------

def vineyard_prefactor(
    H_mw_init: np.ndarray,
    H_mw_sad: np.ndarray,
    n_zero_modes: int = 3,
) -> float:
    """Compute the Vineyard harmonic prefactor ν₀ in Hz.

        ν₀ = ∏ωᵢ_init / ∏ωᵢ_sad  (sad excludes the imaginary mode)

    Parameters
    ----------
    H_mw_init : (M, M) ndarray
        Mass-weighted Hessian at the initial-state minimum (free atoms only).
    H_mw_sad : (M, M) ndarray
        Mass-weighted Hessian at the saddle (free atoms only, same dimension).
    n_zero_modes : int
        Translational zero modes to project out. Default 3 (slab geometry).

    Returns
    -------
    nu0_Hz : float
        Harmonic prefactor in Hz. Typical for FCC Ni: 1–10 THz.

    Notes
    -----
    Both Hessians must use the same free-atom subset for the products to be
    physically meaningful. The unit cancellation works because the prefactor
    is a ratio: each ω is in (eV/(amu·Å²))^0.5, so the natural-unit ratio
    is dimensionless. We convert one ω to Hz at the end via ω_Hz = ω_eV / (2π·ℏ_eV·s).
    """
    _, omegas_init_eV, _, _ = normal_modes_from_hessian(
        H_mw_init, n_zero_modes=n_zero_modes, expect_saddle=False,
    )
    _, omegas_sad_eV, _, _ = normal_modes_from_hessian(
        H_mw_sad, n_zero_modes=n_zero_modes, expect_saddle=True,
    )

    if len(omegas_init_eV) != len(omegas_sad_eV) + 1:
        raise ValueError(
            f"Vineyard prefactor expects N(init) = N(sad) + 1 positive modes; "
            f"got init={len(omegas_init_eV)}, sad={len(omegas_sad_eV)}."
        )

    # The ratio of ωs is the same in any unit; pick eV.
    log_ratio = np.sum(np.log(omegas_init_eV)) - np.sum(np.log(omegas_sad_eV))
    nu0_eV = np.exp(log_ratio)  # this is ν in eV (i.e. ℏν), still needs conversion
    # Actually log(prod_init/prod_sad) gives ratio of ω products. The result
    # has units of ω (since #init = #sad + 1, one ω is left over). So nu0_eV
    # is an ℏω in eV, which we now convert to Hz.
    nu0_Hz = nu0_eV / (2.0 * np.pi * HBAR_EV_S)
    return float(nu0_Hz)


# ---------------------------------------------------------------------------
# Coupling matrix Λ (paper eq. 9)
# ---------------------------------------------------------------------------

def coupling_matrix(
    H_mw_plus: np.ndarray,
    H_mw_minus: np.ndarray,
    R: np.ndarray,
    neg_idx: int,
    dQ: float,
) -> np.ndarray:
    """Compute Λ from the central FD of the saddle Hessian along Q₀.

    Λᵢⱼ = (R^T · ∂H/∂Q₀ · R) with row/col `neg_idx` dropped.

    Parameters
    ----------
    H_mw_plus, H_mw_minus : (M, M) ndarrays
        Mass-weighted Hessians at saddle ± dQ along the negative-mode
        eigenvector.
    R : (M, M) ndarray
        Eigenvector matrix at the saddle (output of normal_modes_from_hessian).
    neg_idx : int
        Column index of the negative-mode eigenvector in R.
    dQ : float
        Finite-difference step size in mass-weighted normal-mode coords
        (Å · sqrt(amu)).

    Returns
    -------
    Lambda : (N, N) ndarray
        Coupling matrix in eV units, with N = M - 1 (negative mode dropped).
        For n_zero_modes > 0, the caller is responsible for further trimming
        zero-mode rows/cols if the saddle's R contains them.

    Notes
    -----
    Λ is invariant under sign flip of the negative-mode eigenvector
    (because of the central difference). Verified by unit test.
    """
    if H_mw_plus.shape != H_mw_minus.shape:
        raise ValueError("H_mw_plus and H_mw_minus must have same shape")
    if dQ <= 0:
        raise ValueError(f"dQ must be > 0, got {dQ}")

    # Central finite difference of the Hessian along Q₀
    dH_dQ0 = (H_mw_plus - H_mw_minus) / (2.0 * dQ)

    # Transform into saddle's normal-mode basis
    Lambda_full = R.T @ dH_dQ0 @ R

    # Drop the negative-mode row/column
    keep_mask = np.ones(Lambda_full.shape[0], dtype=bool)
    keep_mask[neg_idx] = False
    Lambda = Lambda_full[np.ix_(keep_mask, keep_mask)]

    # Symmetrise for numerical hygiene (FD noise can break symmetry)
    Lambda = 0.5 * (Lambda + Lambda.T)
    return Lambda


# ---------------------------------------------------------------------------
# G matrix (paper eqs. 16-18)
# ---------------------------------------------------------------------------

def build_G(
    omega0_eV: float,
    omegas_eV: np.ndarray,
    Lambda: np.ndarray,
) -> np.ndarray:
    """Assemble the 2N × 2N matrix G from eqs. 16–18.

    G = [[A, C],
         [Cᵀ, B]]

    A_{ij} = Λᵢⱼ · (ω₀² + (ωᵢ + ωⱼ)²) / [2 ωᵢ ωⱼ D_{ij}]
    B_{ij} = Λᵢⱼ · ω₀ / D_{ij}
    C_{ij} = -Λᵢⱼ · (ωᵢ² - ωⱼ² - ω₀²) / [2 ωᵢ D_{ij}]
    where D_{ij} = (ωᵢ² - ωⱼ² + ω₀²)² + (2 ωᵢ ω₀)²

    All quantities in eV (i.e. ω is ℏω in eV).
    """
    N = len(omegas_eV)
    if Lambda.shape != (N, N):
        raise ValueError(
            f"Lambda shape {Lambda.shape} doesn't match omega count {N}"
        )

    w0 = omega0_eV
    wi = omegas_eV[:, None]   # column → broadcast over j
    wj = omegas_eV[None, :]   # row → broadcast over i

    D = (wi**2 - wj**2 + w0**2)**2 + (2.0 * wi * w0)**2

    A = Lambda * (w0**2 + (wi + wj)**2) / (2.0 * wi * wj * D)
    B = Lambda * w0 / D
    C = -Lambda * (wi**2 - wj**2 - w0**2) / (2.0 * wi * D)

    G = np.zeros((2 * N, 2 * N))
    G[:N, :N] = A
    G[:N, N:] = C
    G[N:, :N] = C.T
    G[N:, N:] = B
    return G


# ---------------------------------------------------------------------------
# κ — Hartree-Fock and RPA
# ---------------------------------------------------------------------------

def _alpha_h_f(G: np.ndarray) -> tuple[float, float]:
    """Compute the Hartree (αₕ) and Fock (α_f) scalars from G.

    αₕ = ½ [Tr(G)]²
    α_f = Tr(G Gᵀ)
    """
    tr_G = float(np.trace(G))
    alpha_h = 0.5 * tr_G * tr_G
    alpha_f = float(np.sum(G * G))  # Tr(G G^T) = sum of squared elements
    return alpha_h, alpha_f


def kappa_hartree_fock(
    omega0_eV: float,
    omegas_eV: np.ndarray,
    Lambda: np.ndarray,
    T_K: float,
) -> float:
    """Hartree–Fock κ (paper eq. 29):  κ_HF = exp(-αₕ · kᵇT).

    Returns
    -------
    kappa_HF : float in (0, 1.0001]
    """
    G = build_G(omega0_eV, omegas_eV, Lambda)
    alpha_h, _ = _alpha_h_f(G)
    kT = KB_EV_PER_K * T_K
    kappa = float(np.exp(-alpha_h * kT))
    if kappa > KAPPA_UPPER_BOUND:
        warnings.warn(
            f"kappa_HF={kappa} > 1; perturbation theory may have failed.",
            RuntimeWarning,
        )
    return kappa


def kappa_rpa(
    omega0_eV: float,
    omegas_eV: np.ndarray,
    Lambda: np.ndarray,
    T_K: float,
    perturbation_safety: float = 0.5,
) -> tuple[float, dict]:
    """RPA κ (paper eq. 33):

        κ_RPA = exp[ -(αₕ + α_f) kᵇT / (1 + α_f kᵇT) ]

    Parameters
    ----------
    omega0_eV : positive ℏω at the negative mode (eV).
    omegas_eV : positive ℏω of the other modes (eV).
    Lambda : (N, N) coupling matrix (eV).
    T_K : temperature (K).
    perturbation_safety : float
        Returns NaN with a warning if α_f · kᵇT > perturbation_safety.

    Returns
    -------
    kappa_RPA : float in (0, 1.0001] or NaN if perturbation theory unreliable.
    diagnostics : dict with α_h, α_f, kT, denom (1 + α_f · kT), Tr(G).
    """
    G = build_G(omega0_eV, omegas_eV, Lambda)
    alpha_h, alpha_f = _alpha_h_f(G)
    kT = KB_EV_PER_K * T_K
    denom = 1.0 + alpha_f * kT
    diagnostics = {
        'alpha_h': alpha_h,
        'alpha_f': alpha_f,
        'kT_eV': kT,
        'denom': denom,
        'tr_G': float(np.trace(G)),
        'omega0_eV': omega0_eV,
    }
    if alpha_f * kT > perturbation_safety:
        warnings.warn(
            f"alpha_F · kT = {alpha_f * kT:.3f} > safety threshold "
            f"{perturbation_safety}; RPA perturbation theory unreliable.",
            RuntimeWarning,
        )
        return float('nan'), diagnostics

    exponent = -(alpha_h + alpha_f) * kT / denom
    kappa = float(np.exp(exponent))
    if kappa > KAPPA_UPPER_BOUND:
        warnings.warn(
            f"kappa_RPA={kappa} > 1; perturbation theory may have failed.",
            RuntimeWarning,
        )
        return float('nan'), diagnostics
    return kappa, diagnostics
