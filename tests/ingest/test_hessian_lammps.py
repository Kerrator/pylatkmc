"""Integration tests for hessian_lammps.py.

These require a working LAMMPS executable (lmp_serial or lmp_mpi) and the
NiAlH_jea.eam potential. Skipped on systems without LAMMPS.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

POT_PATH = Path("/Users/stephenkerr/kmc/Data/Research/NiAlH_jea.eam")
LMP_BIN = Path("/opt/homebrew/bin/lmp_serial")

requires_lammps = pytest.mark.skipif(
    not (LMP_BIN.exists() and POT_PATH.exists()),
    reason=f"LAMMPS at {LMP_BIN} or potential at {POT_PATH} not available",
)


@requires_lammps
def test_hessian_symmetric_and_positive_for_ni_slab():
    """A small Ni(100) slab Hessian should be symmetric, with all eigenvalues
    above the zero-mode threshold for the bulk-like atoms (no soft modes).

    Frequencies should land in the Ni Debye range (5–8 THz).
    """
    from ase.build import fcc100

    from pylatkmc.ingest.htst.hessian_lammps import compute_mass_weighted_hessian
    from pylatkmc.ingest.htst.kappa_rpa import HBAR_EV_S, normal_modes_from_hessian

    slab = fcc100('Ni', size=(3, 3, 4), a=3.524, vacuum=10.0)
    positions = slab.get_positions()
    types = slab.get_chemical_symbols()
    cell = slab.cell.diagonal()

    # Free the 4 central atoms (12-DOF Hessian — quick to compute)
    centre = positions.mean(axis=0)
    dists = np.linalg.norm(positions - centre, axis=1)
    free = np.argsort(dists)[:4]

    work = Path(tempfile.mkdtemp(prefix='test_hess_'))
    try:
        H_mw = compute_mass_weighted_hessian(
            positions, types, cell, free, str(POT_PATH), dx=0.01, workdir=work,
        )
        # Shape + symmetry
        assert H_mw.shape == (12, 12)
        assert np.allclose(H_mw, H_mw.T, atol=1e-6)

        # Diagonalise; expect no negative modes for bulk-like atoms
        omega0, omegas, _, _ = normal_modes_from_hessian(
            H_mw, n_zero_modes=3, expect_saddle=False,
        )
        assert omega0 is None, "Should have no imaginary modes for stable cluster"

        # All frequencies positive, in physical range
        nu_THz = omegas / (2 * np.pi * HBAR_EV_S) / 1e12
        assert nu_THz.min() > 0
        # Ni Debye is ~6.7 THz; our 4-atom subset should mean ~5–8 THz
        assert 3.0 < nu_THz.mean() < 12.0, f"mean ν = {nu_THz.mean()} THz outside reasonable range"
    finally:
        shutil.rmtree(work, ignore_errors=True)


@requires_lammps
def test_select_free_atoms_radius():
    """select_free_atoms should pick atoms within radius and exclude others."""
    from pylatkmc.ingest.htst.hessian_lammps import select_free_atoms

    positions = np.array([
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [0.0, 5.0, 0.0],
    ])
    free = select_free_atoms(positions, move_atom_idx=0, radius=5.5)
    # Should include atoms 0, 1, 3 (distances 0, 2, 5); exclude atom 2 (dist 10)
    assert sorted(free.tolist()) == [0, 1, 3]
