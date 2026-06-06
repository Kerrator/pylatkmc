"""LAMMPS-backed mass-weighted Hessian computation for the κ_RPA / Vineyard
prefactor pipeline.

Uses ASE's `lammpsrun.LAMMPS` calculator + `ase.vibrations.Vibrations` to
compute the Hessian over a user-specified subset of "free" atoms (the
peripherally-frozen atoms remain fixed during pARTn search and must remain
fixed here so the saddle stays a saddle of *this* Hessian).

Output Hessian units: eV / (amu · Å²) (the natural unit used by
``kappa_rpa.py``). ASE's Vibrations class returns the dynamical matrix in
``eV / (amu · Å²)`` natively when ``nfree=2`` (central FD on forces).

Key design notes:
- The ASE ``lammpsrun.LAMMPS`` calculator spawns a fresh LAMMPS subprocess
  for every force call. For Hessian computation that's 6 × n_free force
  calls, which is OK for n_free ≤ 50 (a few seconds total) but painful
  beyond. We tolerate this for the per-bucket sweep (~30–60 buckets).
- The "frozen periphery" is enforced via ASE's ``constraints.FixAtoms`` —
  fixed atoms get zero forces, so their rows/cols of the Hessian are
  identically zero and we slice them out before returning.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

# We intentionally lazy-import ASE / LAMMPS bits inside the functions so this
# module can be imported in test environments that don't have LAMMPS on PATH.
# The type-only import below names `LAMMPS` for annotations without importing
# ASE at runtime (`from __future__ import annotations` keeps annotations as
# strings, so this is never evaluated at import time).
if TYPE_CHECKING:
    from ase.calculators.lammpsrun import LAMMPS

# ---------------------------------------------------------------------------
# Convention constants (mirrors kappa_rpa.py)
# ---------------------------------------------------------------------------
DEFAULT_DISPLACEMENT_X = 0.01   # Å, finite-difference step for Hessian
DEFAULT_DELTA_Q0 = 0.05         # √(amu)·Å, central FD along negative mode
LAMMPS_EXEC = os.environ.get("LAMMPS_COMMAND", "/opt/homebrew/bin/lmp_serial")
NI_MASS_AMU = 58.6934


# ---------------------------------------------------------------------------
# Atom selection: which atoms are "free" for the Hessian?
# ---------------------------------------------------------------------------

def select_free_atoms(
    positions: np.ndarray,
    move_atom_idx: int,
    radius: float = 6.0,
) -> np.ndarray:
    """Select atoms within `radius` of the moving atom as 'free' for Hessian.

    Default 6 Å captures up to 2NN (~3.52 Å) plus a buffer, which is
    sufficient to converge ν₀ for a localised hop. Atoms outside the
    radius are kept frozen — same convention as pARTn's saddle search
    (which freezes atoms beyond ~12 Å, but the Hessian only really needs
    the strongly coupled ones).

    Parameters
    ----------
    positions : (N, 3) ndarray
        Cluster atom positions.
    move_atom_idx : int
        Index of the moving atom (centre of the free region).
    radius : float
        Free-atom selection radius (Å).

    Returns
    -------
    free_indices : ndarray of int
        Sorted indices of free atoms in `positions`.
    """
    centre = positions[move_atom_idx]
    dists = np.linalg.norm(positions - centre, axis=1)
    return np.where(dists <= radius)[0]


# ---------------------------------------------------------------------------
# LAMMPS calculator factory
# ---------------------------------------------------------------------------

def make_lammps_calculator(
    potential_path: str,
    species_map: dict,
    tmp_dir: str | None = None,
) -> LAMMPS:
    """Build an ASE LAMMPS calculator for the given EAM potential.

    Parameters
    ----------
    potential_path : str
        Absolute path to the LAMMPS-format EAM file (e.g. NiAlH_jea.eam).
    species_map : dict[str, int]
        Mapping atom symbol → LAMMPS atom type. Example: {'Ni': 1}.
    tmp_dir : str or None
        Scratch directory for LAMMPS input/output files.

    Returns
    -------
    LAMMPS calculator instance configured for static energy/force calls.
    """
    from ase.calculators.lammpsrun import LAMMPS
    potential_path = os.path.abspath(potential_path)
    sym_in_order = sorted(species_map.keys(), key=lambda s: species_map[s])
    pair_coeff = f"* * {potential_path} " + " ".join(sym_in_order)

    kwargs = dict(
        pair_style='eam/alloy',
        pair_coeff=[pair_coeff],
        masses=[
            f"{species_map[sym]} {_mass_for_symbol(sym):.4f}"
            for sym in sym_in_order
        ],
        specorder=sym_in_order,
        keep_alive=False,
        command=LAMMPS_EXEC,
    )
    if tmp_dir is not None:
        # ASE LAMMPS calls os.mkdir() on tmp_dir without making parents,
        # so we must ensure the parent exists first.
        Path(tmp_dir).parent.mkdir(parents=True, exist_ok=True)
        kwargs['tmp_dir'] = tmp_dir
    return LAMMPS(**kwargs)


def _mass_for_symbol(symbol: str) -> float:
    from ase.data import atomic_masses, atomic_numbers
    return float(atomic_masses[atomic_numbers[symbol]])


# ---------------------------------------------------------------------------
# Hessian via ASE Vibrations
# ---------------------------------------------------------------------------

def compute_mass_weighted_hessian(
    positions: np.ndarray,
    types: Sequence[str],
    cell: Sequence[float],
    free_indices: Sequence[int],
    potential_path: str,
    dx: float = DEFAULT_DISPLACEMENT_X,
    pbc: bool = True,
    workdir: Path | None = None,
) -> np.ndarray:
    """Compute the mass-weighted Hessian over `free_indices` only.

    Parameters
    ----------
    positions : (N, 3) ndarray
        Atom Cartesian positions (Å).
    types : sequence of N str
        Atom element symbols, e.g. ['Ni', 'Ni', ...].
    cell : (3,) sequence
        Orthorhombic cell diagonal [Lx, Ly, Lz] (Å).
    free_indices : sequence of int
        Indices of free atoms; others are fixed.
    potential_path : str
        Absolute path to the EAM potential file.
    dx : float
        Finite-difference displacement (Å).
    pbc : bool
        Periodic boundary conditions in xy (z always free for slabs).
    workdir : Path or None
        Scratch directory. If None, uses tempfile.mkdtemp().

    Returns
    -------
    H_mw : (3M, 3M) ndarray
        Mass-weighted Hessian over the M = len(free_indices) free atoms,
        in eV / (amu · Å²). The 3M × 3M block is ordered (atom 0 x, y, z;
        atom 1 x, y, z; ...).
    """
    from ase import Atoms
    from ase.constraints import FixAtoms
    from ase.vibrations import Vibrations

    free_indices = np.asarray(free_indices, dtype=int)
    n_atoms = len(positions)
    fixed = [i for i in range(n_atoms) if i not in set(free_indices.tolist())]

    species_set = sorted(set(types))
    species_map = {s: i + 1 for i, s in enumerate(species_set)}

    atoms = Atoms(
        symbols=list(types),
        positions=positions,
        cell=[float(cell[0]), float(cell[1]), float(cell[2])],
        pbc=[pbc, pbc, False],  # slab: free in z
    )
    if fixed:
        atoms.set_constraint(FixAtoms(indices=fixed))

    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="kappa_hessian_"))
    workdir.mkdir(exist_ok=True, parents=True)
    atoms.calc = make_lammps_calculator(
        potential_path, species_map, tmp_dir=str(workdir / "lmp"),
    )

    cwd = os.getcwd()
    try:
        os.chdir(workdir)
        vib = Vibrations(atoms, indices=free_indices.tolist(), nfree=2, delta=dx)
        vib.run()
        # ASE returns the Hessian-on-displacement matrix; we need the
        # mass-weighted form. ase.vibrations exposes `H` (force-constant
        # matrix, eV/Å²) via the modal-analysis machinery — but the cleanest
        # extraction is via the eigenvalues + eigenvectors:
        #     λᵢ in eV/(amu·Å²) corresponds to ωᵢ² (mass-weighted).
        # We rebuild H_mw from those.
        H_mw = _extract_mass_weighted_hessian(vib, free_indices, types)
    finally:
        os.chdir(cwd)

    return H_mw


def _extract_mass_weighted_hessian(
    vib,                     # ase.vibrations.Vibrations instance after .run()
    free_indices: np.ndarray,
    types: Sequence[str],
) -> np.ndarray:
    """Reconstruct the mass-weighted Hessian from ASE's Vibrations cache.

    Vibrations stores per-displacement forces; we read them back, build the
    force-constant matrix H_FC (eV/Å²), then mass-weight:
        H_mw[ij,kl] = H_FC[ij,kl] / sqrt(m_i × m_k)
    """
    from ase.data import atomic_masses, atomic_numbers
    n_free = len(free_indices)
    n_dof = 3 * n_free

    # Pull the force-constant matrix that Vibrations builds internally.
    # The public API exposes get_frequencies(), but the FC matrix is what
    # we want for downstream κ work. Vibrations.summary() shows it computes
    # H from forces; we recompute here by reading the cached force files.
    H_FC = np.zeros((n_dof, n_dof))
    delta = vib.delta

    for i_dof in range(n_dof):
        i_atom_local = i_dof // 3
        i_dir = i_dof % 3
        atom_global = int(free_indices[i_atom_local])
        dir_char = ["x", "y", "z"][i_dir]
        # ASE Vibrations caches displacements as e.g. '13x+', '13x-'
        f_plus = vib.cache[f'{atom_global}{dir_char}+']['forces']
        f_minus = vib.cache[f'{atom_global}{dir_char}-']['forces']
        # Central FD: H_FC[i_dof, j_dof] = -dF_j / dx_i
        # (force on atom j when atom i is displaced — sign convention)
        df = -(f_plus - f_minus) / (2.0 * delta)  # shape (n_atoms, 3)
        # Pull only free atoms' forces and flatten
        H_FC[i_dof, :] = df[free_indices].flatten()

    # Symmetrise (FD noise can break symmetry)
    H_FC = 0.5 * (H_FC + H_FC.T)

    # Mass-weight: H_mw[ij,kl] = H_FC[ij,kl] / sqrt(m_i · m_k)
    masses_free = np.array([
        atomic_masses[atomic_numbers[types[int(idx)]]] for idx in free_indices
    ])
    inv_sqrt_m = 1.0 / np.sqrt(np.repeat(masses_free, 3))
    H_mw = H_FC * np.outer(inv_sqrt_m, inv_sqrt_m)

    return H_mw


# ---------------------------------------------------------------------------
# Three Hessians at saddle: H(sad), H(sad+δê₀), H(sad-δê₀)
# ---------------------------------------------------------------------------

def compute_three_hessians(
    positions_sad: np.ndarray,
    types: Sequence[str],
    cell: Sequence[float],
    free_indices: Sequence[int],
    potential_path: str,
    delta_q0: float = DEFAULT_DELTA_Q0,
    dx: float = DEFAULT_DISPLACEMENT_X,
    workdir_root: Path | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, np.ndarray, int]:
    """Compute the three Hessians needed for κ_RPA: H(sad), H(sad ± δQ₀).

    Steps:
    1. Compute H_sad = mass-weighted Hessian at the saddle.
    2. Diagonalise (via kappa_rpa.normal_modes_from_hessian) to get the
       negative-mode eigenvector ê₀ in mass-weighted Cartesian.
    3. Convert mass-weighted displacement δ Q₀ along ê₀ back to actual
       Cartesian displacement (atom i moves by δ·ê₀_{i*3:i*3+3} / sqrt(m_i)).
    4. Compute H_plus and H_minus at those displaced configurations.

    Returns
    -------
    H_sad, H_plus, H_minus : mass-weighted Hessians (n_dof, n_dof)
    omega0_eV : float — magnitude of imaginary frequency
    R : (n_dof, n_dof) eigenvector matrix at saddle
    neg_idx : int — column of R that's the negative-mode eigenvector
    """
    from ase.data import atomic_masses, atomic_numbers

    from .kappa_rpa import normal_modes_from_hessian

    if workdir_root is None:
        workdir_root = Path(tempfile.mkdtemp(prefix="kappa_three_hessians_"))
    workdir_root.mkdir(parents=True, exist_ok=True)

    # 1. Saddle Hessian
    H_sad = compute_mass_weighted_hessian(
        positions_sad, types, cell, free_indices, potential_path,
        dx=dx, workdir=workdir_root / "sad",
    )

    # 2. Diagonalise to get the negative-mode eigenvector
    omega0_eV, _, R, neg_idx = normal_modes_from_hessian(
        H_sad, n_zero_modes=3, expect_saddle=True,
    )
    eig_neg = R[:, neg_idx]   # length 3 × n_free, mass-weighted Cartesian

    # 3. Convert mass-weighted displacement to actual Cartesian
    free_indices = np.asarray(free_indices, dtype=int)
    masses_free = np.array([
        atomic_masses[atomic_numbers[types[int(idx)]]] for idx in free_indices
    ])
    inv_sqrt_m = 1.0 / np.sqrt(np.repeat(masses_free, 3))
    cartesian_disp = delta_q0 * eig_neg * inv_sqrt_m  # shape (3·n_free,)
    cartesian_disp_per_atom = cartesian_disp.reshape(-1, 3)

    # Build displaced configurations for the FREE atoms only
    pos_plus = positions_sad.copy()
    pos_plus[free_indices] += cartesian_disp_per_atom
    pos_minus = positions_sad.copy()
    pos_minus[free_indices] -= cartesian_disp_per_atom

    # 4. Hessians at the displaced configurations
    H_plus = compute_mass_weighted_hessian(
        pos_plus, types, cell, free_indices, potential_path,
        dx=dx, workdir=workdir_root / "plus",
    )
    H_minus = compute_mass_weighted_hessian(
        pos_minus, types, cell, free_indices, potential_path,
        dx=dx, workdir=workdir_root / "minus",
    )

    return H_sad, H_plus, H_minus, omega0_eV, R, neg_idx
