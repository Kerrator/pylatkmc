"""Harmonic Transition State Theory (Vineyard ν₀ + Sharia & Henkelman κ_RPA).

See `apps/PyKMC_Analysis/Analysis/HTST.md` for the comprehensive reference.

Modules:
    kappa_rpa         — pure-NumPy κ + Vineyard math (LAMMPS-free)
    hessian_lammps    — LAMMPS-backed mass-weighted Hessian via ASE Vibrations
    canonical_kappa   — multi-motif driver (preferred entry point)

CLI:
    python -m pylatkmc.ingest.htst.canonical_kappa --motif surface_1NN_inplane --T 500 ...

Public API (re-exports):
    vineyard_prefactor, kappa_rpa, kappa_hartree_fock,
    normal_modes_from_hessian, coupling_matrix, build_G,
    HBAR_EV_S, HBAR_OMEGA_EV, KB_EV_PER_K
"""

from .kappa_rpa import (
    HBAR_EV_S,
    HBAR_OMEGA_EV,
    KB_EV_PER_K,
    build_G,
    coupling_matrix,
    kappa_hartree_fock,
    kappa_rpa,
    normal_modes_from_hessian,
    vineyard_prefactor,
)

__all__ = [
    "HBAR_EV_S",
    "HBAR_OMEGA_EV",
    "KB_EV_PER_K",
    "build_G",
    "coupling_matrix",
    "kappa_hartree_fock",
    "kappa_rpa",
    "normal_modes_from_hessian",
    "vineyard_prefactor",
]
