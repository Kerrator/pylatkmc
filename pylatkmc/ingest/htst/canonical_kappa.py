"""Canonical-slab Vineyard ν₀ + RPA κ for representative FCC(100) Ni motifs.

Rather than try to compute Hessians on pARTn's per-event cluster geometries
(which fail because the cluster's outer atoms aren't true stationary points
of the cluster-only potential — they're equilibrated against the periphery
of the larger simulation), we build clean Ni(100) slab geometries from
scratch, find the saddle for each canonical mechanism via NEB + Dimer
refinement, then compute Hessians at the saddle for ν₀ + κ. The result
is a per-family correction that can be applied to all events of that
family in the rate table.

Supported motifs (canonical geometry per family_id):

    surface_1NN_inplane    — surface vacancy + 1NN in-plane hop into it
    subsurface_1NN_inplane — subsurface (layer-1) vacancy + 1NN hop
                             within layer 1 (the dominant motif at multi-vac)
    surface_2NN_diagonal   — surface vacancy + 2NN diagonal in-plane hop

This script is staged for the κ-track of the pylatkmc MSD-overshoot work.
The `surface_1NN_inplane` motif gates the question: is k₀ = 1×10¹³ Hz
correct, or does Vineyard ν₀ deviate enough to bias rates? The
`subsurface_1NN_inplane` motif covers the dominant kinetic motif in
multi-vacancy 100Ni at T ≤ 500 K (89.6% of physical time per the
10-vac analysis in `docs/pylatkmc_msd_diagnosis.md`).

Output: a JSON file with the standard schema (see `_RESULT_SCHEMA`)
containing ν₀, ω₀, κ_RPA, κ_HF, and provenance. Multiple motifs
accumulate into a single CSV via `--out-csv` for easier consumption
by `ratebuilder.py`'s per-family ν₀ override mechanism (TODO in
the integration follow-up).

History (May 2026):
    - First experiment: surface_1NN, n_free=41 → ν₀ = 21.4 THz vs assumed
      k₀ = 10 THz; κ_RPA = NaN (perturbation theory broke down).
    - The κ breakdown is suspected to be a saddle-convergence issue (the
      NEB-best-image isn't a true saddle and has spurious near-zero modes
      that inflate Λ entries). This refactor adds Dimer-method refinement
      after NEB to mitigate.
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
import warnings
from pathlib import Path

import numpy as np

POT_PATH_DEFAULT = "/Users/stephenkerr/kmc/Data/Research/NiAlH_jea.eam"

# ---------------------------------------------------------------------------
# Result schema — keep stable; ratebuilder.py will consume this
# ---------------------------------------------------------------------------
_RESULT_SCHEMA = (
    "motif",                # surface_1NN_inplane / subsurface_1NN_inplane / etc.
    "T_K",
    "n_free",               # number of free atoms in the Hessian region
    "Ea_eV",                # NEB-derived activation energy
    "omega0_eV",            # ℏω at saddle (imaginary mode)
    "omega0_THz",
    "nu0_Hz",               # Vineyard prefactor
    "nu0_THz",
    "kappa_RPA",            # RPA recrossing correction (NaN if breakdown)
    "kappa_HF",
    "alpha_h",
    "alpha_f",
    "alpha_f_kT",           # safety diagnostic for κ_RPA
    "k0_assumed_Hz",
    "rate_correction_factor",   # ν₀·κ / k₀_assumed
    "saddle_converged",     # whether Dimer refinement converged
    "fmax_at_saddle_eV_per_A",  # post-refinement force on the saddle
    "neb_n_images",
    "free_radius_A",
    "delta_q0",
    "dx",
    "notes",
)


# ===========================================================================
# Slab construction per motif
# ===========================================================================

def build_slab_for_motif(motif: str,
                         size=(4, 4, 5), vacuum=10.0, a=3.524):
    """Build the canonical slab geometry for a given motif.

    Returns (slab_with_vacancy, mover_seed_idx) where:
        slab_with_vacancy : ASE Atoms with vacancy already removed
        mover_seed_idx    : index of the atom that will hop (in the slab
                            BEFORE relaxation; this can shift after FIRE
                            relaxation but the physical site is preserved)

    The slab dimensions are chosen so that:
        size = (4, 4, 5) → 80 atoms - 1 vacancy = 79 atoms
        Layers (z-spacing a/2 = 1.762 Å):
            layer 0 (top)    : 16 atoms minus 1 vacancy = 15 atoms (surface)
            layer 1          : 16 atoms (subsurface)
            layer 2          : 16 atoms (bulk-like 1)
            layer 3          : 16 atoms (bulk-like 2)
            layer 4 (bottom) : 16 atoms (bottom)
    """
    from ase.build import fcc100
    slab = fcc100('Ni', size=size, a=a, vacuum=vacuum)
    pos = slab.get_positions()
    z_layers = np.unique(np.round(pos[:, 2], 2))   # ascending; top is last
    cx = slab.cell[0, 0] / 2
    cy = slab.cell[1, 1] / 2
    nn_dist = a / np.sqrt(2)

    if motif == "surface_1NN_inplane":
        # Vacancy at top layer, centre. Mover = a top-layer 1NN atom.
        target_z = z_layers[-1]
        target_layer = np.where(np.abs(pos[:, 2] - target_z) < 0.1)[0]
        in_plane_d = np.sqrt((pos[target_layer, 0] - cx) ** 2
                              + (pos[target_layer, 1] - cy) ** 2)
        vac_idx = int(target_layer[np.argmin(in_plane_d)])
        # Mover: a 1NN-of-vacancy atom in the SAME layer.
        # Will be re-identified after vacancy removal.
        mover_seed_pos = (pos[vac_idx][0] + nn_dist, pos[vac_idx][1], pos[vac_idx][2])
        del slab[vac_idx]
        return slab, mover_seed_pos

    if motif == "subsurface_1NN_inplane":
        # Vacancy at layer 1 (subsurface), centre. Mover = a layer-1 1NN atom.
        if len(z_layers) < 2:
            raise ValueError(f"subsurface_1NN motif needs ≥ 2 layers; got {len(z_layers)}")
        target_z = z_layers[-2]   # second from top
        target_layer = np.where(np.abs(pos[:, 2] - target_z) < 0.1)[0]
        in_plane_d = np.sqrt((pos[target_layer, 0] - cx) ** 2
                              + (pos[target_layer, 1] - cy) ** 2)
        vac_idx = int(target_layer[np.argmin(in_plane_d)])
        mover_seed_pos = (pos[vac_idx][0] + nn_dist, pos[vac_idx][1], pos[vac_idx][2])
        del slab[vac_idx]
        return slab, mover_seed_pos

    if motif == "surface_2NN_diagonal":
        # Vacancy at top. Mover = a 2NN-of-vacancy (face-diagonal, distance a) atom.
        target_z = z_layers[-1]
        target_layer = np.where(np.abs(pos[:, 2] - target_z) < 0.1)[0]
        in_plane_d = np.sqrt((pos[target_layer, 0] - cx) ** 2
                              + (pos[target_layer, 1] - cy) ** 2)
        vac_idx = int(target_layer[np.argmin(in_plane_d)])
        mover_seed_pos = (pos[vac_idx][0] + a, pos[vac_idx][1], pos[vac_idx][2])
        del slab[vac_idx]
        return slab, mover_seed_pos

    raise ValueError(f"Unknown motif: {motif!r}")


# ===========================================================================
# NEB + Dimer saddle refinement
# ===========================================================================

def _identify_mover_after_relax(positions: np.ndarray,
                                 mover_seed_pos: tuple[float, float, float],
                                 tol: float = 1.0) -> int:
    """After FIRE relaxation, find the atom closest to the mover_seed_pos.

    The seed position was a sketch of where the mover should be in the
    unrelaxed slab; after relaxation atoms shift slightly. Pick the
    closest atom within `tol` Å.
    """
    seed = np.asarray(mover_seed_pos)
    dists = np.linalg.norm(positions - seed[None, :], axis=1)
    closest = int(np.argmin(dists))
    if dists[closest] > tol:
        warnings.warn(f"mover seed → closest atom is {dists[closest]:.2f} Å away (>{tol})",
                       RuntimeWarning)
    return closest


def find_saddle_via_neb(
    slab,
    mover_seed_pos: tuple[float, float, float],
    target_displacement: np.ndarray,
    potential_path: str,
    workdir: Path,
    n_images: int = 7,
    fmax: float = 0.05,
    refine_with_dimer: bool = True,
    dimer_fmax: float = 0.02,
):
    """NEB to find the saddle, optionally followed by Dimer refinement.

    Parameters
    ----------
    slab : ASE Atoms with vacancy already removed.
    mover_seed_pos : approx (x,y,z) of the mover atom in the unrelaxed slab.
    target_displacement : (3,) ndarray — the mover's target displacement
        vector for the hop (e.g. (-nn_dist, 0, 0) for a 1NN hop in -x).
    potential_path : EAM file path.
    workdir : scratch dir.
    n_images : number of NEB images.
    fmax : NEB convergence (eV/Å).
    refine_with_dimer : if True, run Dimer after NEB to converge the saddle.
    dimer_fmax : Dimer convergence (eV/Å).

    Returns
    -------
    initial : ASE Atoms (relaxed initial state)
    saddle  : ASE Atoms (refined saddle)
    final   : ASE Atoms (relaxed final state)
    mover   : int — index of the mover in the post-relaxation slab
    energies : list[float] — per-image NEB energies (highest = sad_idx)
    saddle_converged : bool — Dimer fmax achieved
    final_fmax : float — actual fmax at the saddle
    """
    from ase.io import write
    from ase.mep import NEB
    from ase.optimize import FIRE

    from .hessian_lammps import make_lammps_calculator

    species_map = {'Ni': 1}

    def fresh_calc(tag):
        return make_lammps_calculator(
            potential_path, species_map, tmp_dir=str(workdir / tag)
        )

    # 1. Relax initial state
    initial = slab.copy()
    initial.calc = fresh_calc("init_relax")
    FIRE(initial, logfile=None).run(fmax=fmax, steps=200)

    # 2. Identify the mover after relaxation
    mover_global = _identify_mover_after_relax(initial.get_positions(), mover_seed_pos)

    # 3. Build final state — mover displaced by target_displacement
    final = initial.copy()
    final.calc = fresh_calc("final_relax")
    new_pos = final.get_positions()
    new_pos[mover_global] = initial.get_positions()[mover_global] + np.asarray(target_displacement)
    final.set_positions(new_pos)
    FIRE(final, logfile=None).run(fmax=fmax, steps=200)

    # 4. NEB
    images = [initial.copy()]
    for i in range(n_images - 2):
        img = initial.copy()
        img.calc = fresh_calc(f"neb_{i}")
        images.append(img)
    images.append(final.copy())
    neb = NEB(images, climb=True)
    neb.interpolate()

    for i, img in enumerate(images):
        if i in (0, len(images) - 1):
            img.calc = fresh_calc(f"neb_endpoint_{i}")
        else:
            img.calc = fresh_calc(f"neb_intermediate_{i}")

    optimizer = FIRE(neb, logfile=None)
    optimizer.run(fmax=fmax * 2, steps=400)

    energies = [img.get_potential_energy() for img in images]
    sad_idx = int(np.argmax(energies))
    saddle = images[sad_idx].copy()
    saddle.calc = fresh_calc("sad_neb_only")

    # 5. Optional Dimer refinement (gives a true saddle, not just NEB-best-image)
    final_fmax = float(np.max(np.linalg.norm(saddle.get_forces(), axis=1)))
    saddle_converged = (final_fmax < fmax * 2)

    if refine_with_dimer:
        try:
            from ase.dimer import DimerControl, MinModeAtoms, MinModeTranslate
            d_control = DimerControl(initial_eigenmode_method='displacement',
                                      displacement_method='vector',
                                      logfile=None,
                                      mask=[True] * len(saddle))
            d_atoms = MinModeAtoms(saddle, d_control)

            # Initial mode displacement: along the NEB tangent at the saddle image
            # (the direction the saddle is "unstable" along — moves between adjacent
            # NEB images give the negative-mode direction).
            tangent = images[sad_idx + 1].get_positions() - images[sad_idx - 1].get_positions() \
                      if sad_idx + 1 < len(images) and sad_idx - 1 >= 0 \
                      else np.zeros_like(saddle.get_positions())
            tangent = tangent.flatten()
            if np.linalg.norm(tangent) > 0:
                tangent /= np.linalg.norm(tangent)
                d_atoms.displace(displacement_vector=tangent.reshape(-1, 3) * 0.01)

            d_atoms.calc = fresh_calc("sad_dimer")
            translater = MinModeTranslate(d_atoms, logfile=None)
            translater.run(fmax=dimer_fmax, steps=100)

            # Pull positions back into a fresh Atoms
            saddle = saddle.copy()
            saddle.set_positions(d_atoms.get_positions())
            saddle.calc = fresh_calc("sad_dimer_final")
            final_fmax = float(np.max(np.linalg.norm(saddle.get_forces(), axis=1)))
            saddle_converged = (final_fmax < dimer_fmax * 1.5)
        except ImportError:
            warnings.warn("ASE Dimer not available; skipping refinement", RuntimeWarning)
        except Exception as exc:
            warnings.warn(f"Dimer refinement failed: {exc}; using NEB-best-image", RuntimeWarning)

    # Save snapshots for inspection / re-use
    write(str(workdir / "initial.traj"), initial)
    write(str(workdir / "saddle.traj"), saddle)
    write(str(workdir / "final.traj"), final)

    return initial, saddle, final, mover_global, energies, saddle_converged, final_fmax


# Legacy wrapper for backward compatibility
def find_1nn_hop_saddle(slab, potential_path, workdir, n_images=7, fmax=0.05):
    """Surface 1NN hop; returns (initial, saddle, final, mover, energies)."""
    a = 3.524
    nn_dist = a / np.sqrt(2)
    pos = slab.get_positions()
    cx, cy = slab.cell[0, 0] / 2, slab.cell[1, 1] / 2
    top_z = pos[:, 2].max()
    top_layer = np.where(np.abs(pos[:, 2] - top_z) < 0.5)[0]
    in_plane_d = np.sqrt((pos[top_layer, 0] - cx) ** 2 + (pos[top_layer, 1] - cy) ** 2)
    nn1_mask = np.abs(in_plane_d - nn_dist) < 0.5
    nn1_idx = top_layer[nn1_mask]
    if len(nn1_idx) == 0:
        raise RuntimeError("Couldn't find a 1NN-of-vacancy surface atom")
    mover_seed = pos[int(nn1_idx[0])]
    target_disp = np.array([cx, cy, top_z]) - mover_seed   # mover hops to the vacancy site
    initial, saddle, final, mover, energies, _, _ = find_saddle_via_neb(
        slab, mover_seed, target_disp, potential_path, workdir,
        n_images=n_images, fmax=fmax, refine_with_dimer=False,
    )
    return initial, saddle, final, mover, energies


def build_slab_with_vacancy(size=(4, 4, 5), vacuum=10.0, a=3.524):
    """Legacy: build slab with surface vacancy. Use build_slab_for_motif()
    in new code."""
    slab, _ = build_slab_for_motif("surface_1NN_inplane", size=size, vacuum=vacuum, a=a)
    return slab


# ===========================================================================
# Hessian + ν₀ + κ for one motif
# ===========================================================================

def compute_canonical_corrections(
    slab,
    initial,
    saddle,
    mover_global: int,
    potential_path: str,
    T_K: float,
    workdir: Path,
    free_radius: float = 6.0,
    delta_q0: float = 0.05,
    dx: float = 0.01,
    free_min_z: float | None = None,
) -> dict:
    """Given a relaxed initial + saddle slab, compute ν₀ and κ.

    Parameters
    ----------
    free_min_z : float or None
        If set, atoms with z > free_min_z are EXCLUDED from the free region
        (frozen). Use this for subsurface motifs to prevent surface-layer
        atoms from contributing low-frequency rattle modes that inflate the
        Vineyard prefactor. Pass `top_layer_z - 0.5 Å` to freeze the
        topmost layer.
    """
    from .hessian_lammps import (
        compute_mass_weighted_hessian,
        compute_three_hessians,
        select_free_atoms,
    )
    from .kappa_rpa import (
        coupling_matrix,
        kappa_hartree_fock,
        kappa_rpa,
        normal_modes_from_hessian,
        vineyard_prefactor,
    )

    free = select_free_atoms(saddle.get_positions(), mover_global, radius=free_radius)
    if mover_global not in free:
        free = np.unique(np.concatenate([free, [mover_global]]))
    if free_min_z is not None:
        sad_z = saddle.get_positions()[:, 2]
        excluded = sad_z[free] > free_min_z
        n_before = len(free)
        free = free[~excluded]
        print(f"[canonical] free_min_z={free_min_z:.2f}: removed {n_before - len(free)} "
              f"atoms above z; {len(free)} free atoms remaining")

    cell = saddle.cell.diagonal()
    types = saddle.get_chemical_symbols()

    H_init = compute_mass_weighted_hessian(
        initial.get_positions(), types, cell, free, potential_path,
        dx=dx, workdir=workdir / "H_init",
    )

    # Pre-flight: diagnose the saddle Hessian's eigenvalue spectrum so we
    # can debug "0 negative eigenvalues" failures without re-computing.
    H_sad_test = compute_mass_weighted_hessian(
        saddle.get_positions(), types, cell, free, potential_path,
        dx=dx, workdir=workdir / "H_sad_diag",
    )
    sad_eigs = np.linalg.eigvalsh(H_sad_test)
    n_neg = int((sad_eigs < -1e-6).sum())
    n_zero = int((np.abs(sad_eigs) < 1e-6).sum())
    n_pos = int((sad_eigs > 1e-6).sum())
    sorted_eigs = np.sort(sad_eigs)
    print("[canonical] saddle Hessian eigenvalue summary:")
    print(f"  total = {len(sad_eigs)}, neg = {n_neg}, |λ|<1e-6 = {n_zero}, pos = {n_pos}")
    print(f"  smallest 5 = {sorted_eigs[:5]}")
    print(f"  largest 5  = {sorted_eigs[-5:]}")
    if n_neg != 1:
        print(f"  ⚠ EXPECTED 1 imaginary mode at saddle, got {n_neg}.")
        print("  This suggests either Dimer over-relaxed (saddle → minimum) "
              "or a near-zero imaginary mode is being projected as a zero mode.")

    H_sad, H_plus, H_minus, omega0_eV, R, neg_idx = compute_three_hessians(
        saddle.get_positions(), types, cell, free, potential_path,
        delta_q0=delta_q0, dx=dx, workdir_root=workdir / "H_sad",
    )

    nu0_Hz = vineyard_prefactor(H_init, H_sad, n_zero_modes=3)

    Lambda = coupling_matrix(H_plus, H_minus, R, neg_idx, delta_q0)
    eigvals = np.linalg.eigvalsh(H_sad)
    # Pick zero modes from POSITIVE-or-near-zero eigenvalues only,
    # excluding the negative (imaginary) mode. Mirrors the May 5 fix in
    # `kappa_rpa.normal_modes_from_hessian`. Without this, a saddle whose
    # imaginary mode has |λ| smaller than some near-zero positive modes
    # gets the imaginary mode picked as a "zero mode" — Lambda then has
    # one too many rows/cols vs the omegas array.
    neg_full = np.where(eigvals < -1e-6)[0]
    candidate_idx = np.array([i for i in range(len(eigvals)) if i not in set(neg_full)])
    abs_candidate = np.abs(eigvals[candidate_idx])
    sort_order = np.argsort(abs_candidate)
    zero_indices_full = candidate_idx[sort_order[:3]]
    zero_in_lambda = []
    for z in zero_indices_full:
        if z == neg_idx:
            continue
        zero_in_lambda.append(z if z < neg_idx else z - 1)
    keep = np.ones(Lambda.shape[0], dtype=bool)
    for k in zero_in_lambda:
        keep[k] = False
    Lambda_trimmed = Lambda[np.ix_(keep, keep)]

    _, omegas_eV, _, _ = normal_modes_from_hessian(
        H_sad, n_zero_modes=3, expect_saddle=True,
    )

    kappa_RPA, diag = kappa_rpa(omega0_eV, omegas_eV, Lambda_trimmed, T_K)
    kappa_HF = kappa_hartree_fock(omega0_eV, omegas_eV, Lambda_trimmed, T_K)

    return {
        "n_free": int(len(free)),
        "omega0_eV": float(omega0_eV),
        "omega0_THz": float(omega0_eV / (2 * np.pi * 6.582119569e-16) / 1e12),
        "nu0_Hz": float(nu0_Hz),
        "nu0_THz": float(nu0_Hz / 1e12),
        "kappa_RPA": float(kappa_RPA) if np.isfinite(kappa_RPA) else float("nan"),
        "kappa_HF": float(kappa_HF) if np.isfinite(kappa_HF) else float("nan"),
        "alpha_h": float(diag["alpha_h"]),
        "alpha_f": float(diag["alpha_f"]),
        "alpha_f_kT": float(diag["alpha_f"] * diag["kT_eV"]),
    }


# ===========================================================================
# Motif-aware end-to-end driver
# ===========================================================================

_MOTIF_DISPLACEMENTS = {
    "surface_1NN_inplane":    "1nn_inplane_neg_x",
    "subsurface_1NN_inplane": "1nn_inplane_neg_x",
    "surface_2NN_diagonal":   "2nn_inplane_face_diag",
}


def _displacement_for_motif(motif: str, a: float = 3.524) -> np.ndarray:
    """Target displacement vector (in Å) for the mover atom under each motif.
    The convention: the mover hops INTO the vacancy site; we precomputed
    the seed position s.t. the vacancy is at seed - displacement.
    """
    nn_dist = a / np.sqrt(2)
    if _MOTIF_DISPLACEMENTS[motif] == "1nn_inplane_neg_x":
        return np.array([-nn_dist, 0.0, 0.0])
    if _MOTIF_DISPLACEMENTS[motif] == "2nn_inplane_face_diag":
        return np.array([-a, 0.0, 0.0])
    raise ValueError(f"No displacement template for motif {motif!r}")


def run_motif(
    motif: str,
    potential: str,
    T_K: float,
    workdir: Path,
    free_radius: float = 6.0,
    delta_q0: float = 0.05,
    dx: float = 0.01,
    refine_with_dimer: bool = True,
    n_images: int = 7,
    auto_freeze_above_mover: bool = True,
) -> dict:
    """End-to-end: build slab → NEB+Dimer saddle → Hessians → ν₀, κ.

    Parameters
    ----------
    auto_freeze_above_mover : bool
        For subsurface motifs, automatically freeze atoms above the mover's
        layer to prevent surface-layer rattle modes from inflating ν₀.
        Default True. Disable explicitly only when you need to retain
        surface flexibility (e.g. for surface-subsurface exchange).

    Returns a dict matching `_RESULT_SCHEMA`.
    """
    print(f"[canonical] motif={motif} T={T_K}K workdir={workdir}")
    slab, mover_seed_pos = build_slab_for_motif(motif)
    print(f"[canonical] slab: {len(slab)} atoms, cell={slab.cell.diagonal()}")
    print(f"[canonical] mover_seed_pos = {mover_seed_pos}")
    target_disp = _displacement_for_motif(motif)

    print("[canonical] running NEB + (optionally) Dimer refinement...")
    initial, saddle, final, mover, energies, sad_conv, fmax_at_sad = find_saddle_via_neb(
        slab, mover_seed_pos, target_disp, potential, workdir / "neb",
        n_images=n_images, refine_with_dimer=refine_with_dimer,
    )
    Ea = max(energies) - energies[0]
    print(f"[canonical] NEB Ea = {Ea:.3f} eV")
    print(f"[canonical] saddle converged = {sad_conv}, fmax = {fmax_at_sad:.4f} eV/Å")

    # Layer-aware free-atom selection: for subsurface motifs, freeze the
    # surface layer above the mover.
    free_min_z: float | None = None
    if auto_freeze_above_mover and "subsurface" in motif:
        mover_z = saddle.get_positions()[mover, 2]
        # Cut at half-layer-spacing above the mover (a/4 ≈ 0.88 Å for Ni)
        # so the next-up layer is excluded.
        free_min_z = float(mover_z + 0.88)
        print(f"[canonical] auto-freeze: mover_z = {mover_z:.2f}, "
              f"free_min_z = {free_min_z:.2f} (frees only atoms below)")

    print("[canonical] computing Hessians + ν₀ + κ...")
    res = compute_canonical_corrections(
        slab, initial, saddle, mover, potential, T_K, workdir / "hess",
        free_radius=free_radius, delta_q0=delta_q0, dx=dx,
        free_min_z=free_min_z,
    )

    rec = {
        "motif": motif,
        "T_K": T_K,
        "Ea_eV": float(Ea),
        "k0_assumed_Hz": 1.0e13,
        "saddle_converged": bool(sad_conv),
        "fmax_at_saddle_eV_per_A": float(fmax_at_sad),
        "neb_n_images": n_images,
        "free_radius_A": float(free_radius),
        "delta_q0": float(delta_q0),
        "dx": float(dx),
        "notes": "",
        **res,
    }
    if np.isfinite(res["kappa_RPA"]):
        rec["rate_correction_factor"] = res["nu0_Hz"] * res["kappa_RPA"] / 1.0e13
    else:
        rec["rate_correction_factor"] = res["nu0_Hz"] / 1.0e13   # bare Vineyard
        rec["notes"] = "kappa_RPA breakdown; rate_correction_factor uses ν₀ only"

    return rec


# ===========================================================================
# All-family ν₀ driver
# ===========================================================================

def fit_barrier_family_ids() -> list[str]:
    """family_id of every ``fit_barrier=True`` family in ``families.py``.

    These are the families whose barriers (and therefore rates) are fit from
    catalogue data; they are the candidates for a per-family Vineyard ν₀
    override. Multisite families (``fit_barrier=False``) are skipped — they
    have no single-mover saddle and always fall back to k₀.
    """
    import sys as _sys
    from pathlib import Path as _Path

    _analysis_dir = str(_Path(__file__).resolve().parent.parent)
    if _analysis_dir not in _sys.path:
        _sys.path.insert(0, _analysis_dir)
    from ..families import FAMILY_REGISTRY  # noqa: PLC0415

    return [f.family_id for f in FAMILY_REGISTRY if f.fit_barrier]


def _skipped_record(family_id: str, T_K: float, reason: str) -> dict:
    """A `_RESULT_SCHEMA`-shaped row for a family with no canonical geometry.

    ν₀ is left blank (→ NaN in the CSV → k₀ fallback downstream). We still
    emit a row so the prefactor table documents the gap rather than silently
    omitting the family.
    """
    rec = {k: "" for k in _RESULT_SCHEMA}
    rec["motif"] = family_id
    rec["T_K"] = T_K
    rec["k0_assumed_Hz"] = 1.0e13
    rec["saddle_converged"] = False
    rec["notes"] = reason
    return rec


def run_all_families(
    potential: str,
    T_K: float,
    workdir: Path,
    out_csv: Path,
    families: list[str] | None = None,
    limit: int | None = None,
    free_radius: float = 6.0,
    delta_q0: float = 0.05,
    dx: float = 0.01,
    refine_with_dimer: bool = False,
    n_images: int = 7,
    out_json_dir: Path | None = None,
) -> list[dict]:
    """Compute Vineyard ν₀ for every ``fit_barrier=True`` family and update CSV.

    Iterates the families from ``families.py`` (filtered by ``families`` /
    ``limit`` if given). For each family that has a canonical slab geometry
    (``_MOTIF_DISPLACEMENTS``), runs the existing
    ``build_slab_for_motif → find_saddle_via_neb → compute_three_hessians →
    vineyard_prefactor`` chain via :func:`run_motif` (which uses
    ``n_zero_modes=3`` and the auto-freeze-surface-above-mover step for
    subsurface families). Families without a canonical geometry are recorded
    as skipped rows so the prefactor table documents the coverage gap.

    The ``out_csv`` is updated in place: rows for families processed in this
    run REPLACE any pre-existing row for the same ``(motif, T_K)`` pair, while
    rows for families not touched here are preserved. This keeps repeated runs
    idempotent (no duplicate motif rows accumulate).

    Returns the list of records produced this run (one per requested family).
    """
    requested = list(families) if families else fit_barrier_family_ids()
    if limit is not None:
        requested = requested[:limit]

    workdir.mkdir(parents=True, exist_ok=True)
    if out_json_dir is not None:
        out_json_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for fam in requested:
        if fam not in _MOTIF_DISPLACEMENTS:
            print(f"[all-families] {fam}: no canonical slab geometry — "
                  f"recording skipped row (will fall back to k₀)")
            records.append(_skipped_record(
                fam, T_K,
                "no canonical slab geometry in canonical_kappa; "
                "ν₀ unavailable, falls back to k0",
            ))
            continue

        print(f"\n[all-families] === {fam} ===")
        try:
            rec = run_motif(
                fam, potential, T_K, workdir / fam,
                free_radius=free_radius, delta_q0=delta_q0, dx=dx,
                refine_with_dimer=refine_with_dimer, n_images=n_images,
            )
        except Exception as exc:  # noqa: BLE001 — record the failure, keep going
            print(f"[all-families] {fam} FAILED: {exc}")
            rec = _skipped_record(fam, T_K, f"run_motif failed: {exc}")
        records.append(rec)
        _print_result_table(rec)

        if out_json_dir is not None:
            json_path = out_json_dir / f"canonical_kappa_{fam}.json"
            with open(json_path, "w") as f:
                json.dump(rec, f, indent=2, default=str)
            print(f"[all-families] saved {json_path}")

    _upsert_csv(records, out_csv)
    print(f"\n[all-families] updated {out_csv} "
          f"({len(records)} families processed this run)")
    return records


def _upsert_csv(records: list[dict], csv_path: Path) -> None:
    """Append-or-replace rows keyed by (motif, T_K) into ``family_prefactors.csv``.

    Existing rows for motifs/T not in this run are preserved; rows for the
    (motif, T_K) pairs in ``records`` are overwritten. This keeps repeated
    runs idempotent instead of accumulating duplicate motif rows.
    """
    import pandas as pd  # noqa: PLC0415

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame(
        [{k: rec.get(k, "") for k in _RESULT_SCHEMA} for rec in records],
        columns=list(_RESULT_SCHEMA),
    )
    if csv_path.exists():
        old_df = pd.read_csv(csv_path)
        # Align columns to the canonical schema (tolerate legacy column order).
        for col in _RESULT_SCHEMA:
            if col not in old_df.columns:
                old_df[col] = ""
        old_df = old_df[list(_RESULT_SCHEMA)]
        new_keys = {(str(r["motif"]), str(r["T_K"])) for _, r in new_df.iterrows()}
        keep_mask = ~old_df.apply(
            lambda r: (str(r["motif"]), str(r["T_K"])) in new_keys, axis=1
        )
        combined = pd.concat([old_df[keep_mask], new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(csv_path, index=False)


# ===========================================================================
# CLI
# ===========================================================================

_ALL_MOTIFS = (
    "surface_1NN_inplane",
    "subsurface_1NN_inplane",
    "surface_2NN_diagonal",
)


def _print_result_table(rec: dict) -> None:
    print()
    print("=" * 60)
    print(f"  CANONICAL κ + ν₀ RESULT — {rec['motif']}")
    print("=" * 60)
    for k in _RESULT_SCHEMA:
        v = rec.get(k)
        if isinstance(v, float):
            print(f"  {k:30s} {v:.6g}")
        else:
            print(f"  {k:30s} {v}")
    print("=" * 60)


def _append_to_csv(rec: dict, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_RESULT_SCHEMA)
        if write_header:
            w.writeheader()
        w.writerow({k: rec.get(k, "") for k in _RESULT_SCHEMA})


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--motif", default="surface_1NN_inplane",
                   choices=_ALL_MOTIFS + ("all",),
                   help="canonical motif to compute (or 'all' for the full sweep). "
                        "Ignored when --all-families is set.")
    p.add_argument("--all-families", action="store_true", default=False,
                   help="iterate EVERY fit_barrier=True family in families.py "
                        "(not just the 3 canonical motifs), computing ν₀ via the "
                        "existing Vineyard chain for families with a canonical "
                        "geometry and recording skipped rows for the rest. "
                        "Requires --out-csv (the family_prefactors.csv to update).")
    p.add_argument("--limit", type=int, default=None,
                   help="with --all-families: only process the first N families")
    p.add_argument("--families", type=str, default=None,
                   help="with --all-families: comma-separated family_id list to "
                        "restrict the run (e.g. surface_1NN_inplane,surface_2NN_diagonal)")
    p.add_argument("--potential", default=POT_PATH_DEFAULT)
    p.add_argument("--T", type=float, default=500.0,
                   help="temperature for κ_RPA evaluation (K)")
    p.add_argument("--free-radius", type=float, default=6.0,
                   help="radius (Å) of the Hessian free-atom region around the mover")
    p.add_argument("--delta-q0", type=float, default=0.05,
                   help="FD step along negative mode (√amu·Å)")
    p.add_argument("--dx", type=float, default=0.01,
                   help="FD step for force-constant matrix (Å)")
    p.add_argument("--refine-saddle", action="store_true", default=False,
                   help="run Dimer refinement after NEB (default: False; the "
                        "NEB-best-image is usually already converged for cheap "
                        "EAM Hessians, and Dimer's tangent-seeded initial mode "
                        "can push the configuration AWAY from the saddle into "
                        "a minimum or wrong stationary point)")
    p.add_argument("--no-refine-saddle", dest="refine_saddle", action="store_false")
    p.add_argument("--n-images", type=int, default=7,
                   help="number of NEB images")
    p.add_argument("--out", required=False, default=None, type=Path,
                   help="output JSON for a single motif (or directory if --motif all). "
                        "Required unless --all-families is set.")
    p.add_argument("--out-csv", type=Path, default=None,
                   help="CSV — appended one row per motif (for ratebuilder). "
                        "Required when --all-families is set "
                        "(this IS the family_prefactors.csv to update).")
    p.add_argument("--workdir", type=Path, default=None,
                   help="scratch dir; if omitted, a fresh tmpdir is created")
    args = p.parse_args()

    workdir_root = args.workdir or Path(tempfile.mkdtemp(prefix="canonical_kappa_"))
    workdir_root.mkdir(parents=True, exist_ok=True)

    # ── all-families driver ──────────────────────────────────────────────
    if args.all_families:
        if args.out_csv is None:
            p.error("--all-families requires --out-csv (the family_prefactors.csv "
                    "to append/update)")
        family_list = (
            [s.strip() for s in args.families.split(",") if s.strip()]
            if args.families else None
        )
        run_all_families(
            args.potential, args.T, workdir_root, args.out_csv,
            families=family_list, limit=args.limit,
            free_radius=args.free_radius, delta_q0=args.delta_q0, dx=args.dx,
            refine_with_dimer=args.refine_saddle, n_images=args.n_images,
            out_json_dir=args.out,   # optional: per-family JSON if --out is a dir
        )
        return

    if args.out is None:
        p.error("--out is required unless --all-families is set")

    motifs = list(_ALL_MOTIFS) if args.motif == "all" else [args.motif]
    out_root = args.out
    if args.motif == "all":
        out_root.mkdir(parents=True, exist_ok=True)

    for mot in motifs:
        rec = run_motif(
            mot, args.potential, args.T, workdir_root / mot,
            free_radius=args.free_radius, delta_q0=args.delta_q0, dx=args.dx,
            refine_with_dimer=args.refine_saddle, n_images=args.n_images,
        )
        _print_result_table(rec)

        if args.motif == "all":
            json_path = out_root / f"canonical_kappa_{mot}.json"
        else:
            json_path = out_root
            json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(rec, f, indent=2, default=str)
        print(f"[canonical] saved {json_path}")

        if args.out_csv:
            _append_to_csv(rec, args.out_csv)
            print(f"[canonical] appended to {args.out_csv}")


if __name__ == "__main__":
    main()
