"""xyz_to_kmcinit.py — convert a pyKMC initial_config.xyz to a .kmcinit.

The pyKMC .xyz file is "off-lattice" — it lists only the atoms that are
present, omitting vacant sites. To convert, we:

1. Parse the pyKMC .xyz (positions + cell + species).
2. Reconstruct the *complete* FCC(100) slab grid that the pyKMC generator
   started from (every site in the lattice, including the ones that were
   removed to make vacancies).
3. Match each pyKMC atom against a generator-grid site (within tolerance);
   leftover unmatched grid sites are flagged as vacant.
4. Compute 1NN/2NN CSR adjacency (with PBC in xy, none in z).
5. Write the .kmcinit binary.

Usage:
    python tools/xyz_to_kmcinit.py \\
        --xyz /path/to/initial_config.xyz \\
        --out /path/to/config.kmcinit
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

# Allow relative import of kmcfmt from the same tools/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_initial_config import (
    A_LATTICE,
    DF_001_EXCHANGE,
    DF_100_INPLANE,
    DF_110_INPLANE,
    DF_111_INTERLAYER,
    DF_UNRESOLVED,
    SC_BULK_LIKE,
    SC_SUBSURFACE,
    SC_SURFACE,
    SPECIES_ID,
    build_fcc100_slab,
    compute_neighbors_with_pbc,
)
from kmcfmt import INITCONFIG_MAGIC, write_header

LATTICE_RE = re.compile(r'Lattice="([^"]+)"')


def parse_xyz(xyz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (positions[N,3] float64, species[N] str, cell[3] float64).

    Assumes orthogonal cell. Reads the first frame only.
    """
    with open(xyz_path) as f:
        n_atoms = int(f.readline().strip())
        header = f.readline().strip()
        m = LATTICE_RE.search(header)
        if not m:
            raise RuntimeError(f"no Lattice attribute in xyz header: {header[:200]}")
        lattice_floats = [float(x) for x in m.group(1).split()]
        if len(lattice_floats) != 9:
            raise RuntimeError(f"Lattice should have 9 floats, got {len(lattice_floats)}")
        # 3x3 cell — assume orthogonal: take diagonal.
        cell = np.array([lattice_floats[0], lattice_floats[4], lattice_floats[8]])

        positions = np.zeros((n_atoms, 3), dtype=np.float64)
        species = np.empty(n_atoms, dtype=object)
        for i in range(n_atoms):
            parts = f.readline().split()
            species[i] = parts[0]
            positions[i, 0] = float(parts[1])
            positions[i, 1] = float(parts[2])
            positions[i, 2] = float(parts[3])
    return positions, species, cell


def infer_slab_shape(cell: np.ndarray, positions: np.ndarray,
                      nn_dist: float) -> tuple[int, int, int, float]:
    """Infer (nx, ny, nz, vacuum_layers) for an FCC(100) slab.

    nx, ny derived from the cell extent in xy (assuming nn_dist spacing
    in-plane). nz from distinct z-values in positions. vacuum_layers from
    cell_z minus the slab's z-extent.
    """
    nx = int(round(cell[0] / nn_dist))
    ny = int(round(cell[1] / nn_dist))

    # Quantise z values to detect distinct layers (within a small tol).
    ls = nn_dist / np.sqrt(2.0)
    layer_idx = np.round(positions[:, 2] / ls).astype(int)
    nz = int(layer_idx.max()) + 1

    # Match cell_z exactly (vacuum_layers is a float — it doesn't have
    # to be an integer).
    vacuum_layers = max(0.0, cell[2] / ls - nz)
    return nx, ny, nz, vacuum_layers


def build_kmcinit(xyz_path: Path, kmcinit_path: Path,
                  primary_element: str = "Ni",
                  cutoff_nn1: float = 1.10,
                  cutoff_nn2: float = 1.45,
                  n_adatom_layers: int = 0) -> dict:
    positions_pykmc, species_pykmc, cell_pykmc = parse_xyz(xyz_path)
    a = A_LATTICE[primary_element]
    nn_dist = a / np.sqrt(2.0)

    nx, ny, nz, vacuum_layers = infer_slab_shape(cell_pykmc, positions_pykmc, nn_dist)
    n_atoms_pykmc = positions_pykmc.shape[0]

    # Build the full grid (all sites that *would* exist before vacancy removal).
    # n_adatom_layers > 0 adds extra empty layers above the top atom layer,
    # giving exchange-up events landing positions for adatoms.
    full_positions, layer_index, site_class, cell_pred = build_fcc100_slab(
        nx, ny, nz, nn_dist,
        vacuum_layers=vacuum_layers,
        n_adatom_layers=n_adatom_layers,
    )
    n_sites_full = full_positions.shape[0]

    # If our predicted cell differs from the pyKMC cell, prefer the pyKMC one
    # for the atom-occupied region. The adatom layers extend the cell in z;
    # we need to override the cell_z to match cell_pred (which already
    # accounts for n_adatom_layers + vacuum).
    cell = np.array([
        float(cell_pykmc[0]),
        float(cell_pykmc[1]),
        float(cell_pred[2]),
    ], dtype=np.float32)

    # Match pyKMC atoms to grid sites (tolerance: 10% of nn_dist).
    tol = 0.10 * nn_dist
    tree = cKDTree(full_positions)
    dists, idx_match = tree.query(positions_pykmc, k=1)
    if dists.max() > tol:
        bad = int((dists > tol).sum())
        raise RuntimeError(
            f"{bad}/{n_atoms_pykmc} pyKMC atoms didn't match grid (max miss "
            f"= {dists.max():.4f} Å, tol = {tol:.4f}). Did the pyKMC generator "
            "use a different lattice constant or orientation?"
        )

    # Initial species: SP_VACANT (=0) at every grid site, then overwrite
    # with the pyKMC species at matched sites. Adatom-region sites
    # (k >= nz) stay vacant by default — those are the new "above-surface"
    # landing positions.
    initial_species = np.zeros(n_sites_full, dtype=np.uint8)
    for pykmc_i, grid_i in enumerate(idx_match):
        sp = species_pykmc[pykmc_i]
        initial_species[grid_i] = SPECIES_ID.get(sp, 0)

    n_vacancies = int((initial_species == 0).sum())
    n_adatom_sites = int((layer_index >= nz).sum())
    # Expected vacancies = (n_sites_full - n_adatom_sites) - n_atoms_pykmc + n_adatom_sites
    #                    = n_sites_full - n_atoms_pykmc
    # (the n_adatom_sites are "vacant" in our count too)
    expected_vacancies = n_sites_full - n_atoms_pykmc
    if n_vacancies != expected_vacancies:
        raise RuntimeError(
            f"vacancy count mismatch: detected {n_vacancies}, expected "
            f"{expected_vacancies} (n_sites_full={n_sites_full}, "
            f"n_atoms_pykmc={n_atoms_pykmc}, n_adatom_sites={n_adatom_sites})"
        )

    # Build CSR neighbour lists.
    nn1_lists = compute_neighbors_with_pbc(full_positions, cell, nn_dist, cutoff_nn1)
    nn2_lists = compute_neighbors_with_pbc(full_positions, cell, nn_dist, cutoff_nn2)
    # Strip 1NN from 2NN list (the cKDTree returns all neighbours within
    # cutoff; the 2NN cutoff includes the 1NN distance).
    for s in range(n_sites_full):
        nn1_set = {n for n, _ in nn1_lists[s]}
        nn2_lists[s] = [(n, d) for n, d in nn2_lists[s] if n not in nn1_set]

    nn1_offsets = np.zeros(n_sites_full + 1, dtype=np.int32)
    nn2_offsets = np.zeros(n_sites_full + 1, dtype=np.int32)
    for s in range(n_sites_full):
        nn1_offsets[s + 1] = nn1_offsets[s] + len(nn1_lists[s])
        nn2_offsets[s + 1] = nn2_offsets[s] + len(nn2_lists[s])
    M1 = int(nn1_offsets[-1])
    M2 = int(nn2_offsets[-1])

    nn1_indices = np.zeros(M1, dtype=np.int32)
    nn1_dir_family = np.full(M1, DF_UNRESOLVED, dtype=np.uint8)
    nn2_indices = np.zeros(M2, dtype=np.int32)
    nn2_dir_family = np.full(M2, DF_UNRESOLVED, dtype=np.uint8)

    ls = nn_dist / np.sqrt(2.0)
    for s in range(n_sites_full):
        for i, (n, d) in enumerate(nn1_lists[s]):
            slot = nn1_offsets[s] + i
            nn1_indices[slot] = n
            # Tag direction family
            dx, dy, dz = full_positions[n] - full_positions[s]
            for axis, lc in zip([0, 1, 2], cell):
                if abs([dx, dy, dz][axis]) > 0.5 * lc:
                    delta = (dx, dy, dz)
                    delta = list(delta); delta[axis] -= np.sign(delta[axis]) * lc
                    dx, dy, dz = delta
            if abs(dz) < 0.1 * nn_dist:
                # in-plane 1NN
                if abs(abs(dx) - nn_dist) < 0.1 * nn_dist or abs(abs(dy) - nn_dist) < 0.1 * nn_dist:
                    nn1_dir_family[slot] = DF_110_INPLANE
                else:
                    nn1_dir_family[slot] = DF_UNRESOLVED
            else:
                nn1_dir_family[slot] = DF_111_INTERLAYER
        for i, (n, d) in enumerate(nn2_lists[s]):
            slot = nn2_offsets[s] + i
            nn2_indices[slot] = n
            dx, dy, dz = full_positions[n] - full_positions[s]
            for axis, lc in zip([0, 1, 2], cell):
                if abs([dx, dy, dz][axis]) > 0.5 * lc:
                    delta = list((dx, dy, dz)); delta[axis] -= np.sign(delta[axis]) * lc
                    dx, dy, dz = delta
            if abs(dz) < 0.1 * nn_dist:
                nn2_dir_family[slot] = DF_100_INPLANE
            else:
                nn2_dir_family[slot] = DF_001_EXCHANGE

    # Element name list, ordered by SPECIES_ID value.
    elem_names = ["X"] + sorted(SPECIES_ID.keys(), key=lambda k: SPECIES_ID[k])

    header = {
        "version": 1,
        "n_sites": n_sites_full,
        "n_layers": nz + n_adatom_layers,    # total layers in the lattice grid
        "n_atom_layers": nz,                  # initially atom-occupied
        "n_adatom_layers": n_adatom_layers,   # initially vacant, above top atom layer
        "cell": [float(x) for x in cell],
        "nn_dist": nn_dist,
        "nn1_count": M1,
        "nn2_count": M2,
        "n_elements": len(elem_names),
        "element_names": elem_names,
        "n_vacancies": n_vacancies,
        "primary_element": primary_element,
        "lattice": "fcc",
        "orientation": "100",
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "source": str(xyz_path),
    }
    header_bytes = json.dumps(header).encode("utf-8")

    with open(kmcinit_path, "wb") as f:
        f.write(INITCONFIG_MAGIC)
        f.write(struct.pack("<I", len(header_bytes)))
        f.write(header_bytes)
        # Payload: u32 payload_version, then arrays in initconfig.c's order
        f.write(struct.pack("<I", 1))                              # payload_version
        f.write(full_positions.astype(np.float32).tobytes())       # f32[N*3]
        f.write(nn1_offsets.tobytes())                             # i32[N+1]
        f.write(nn1_indices.tobytes())                             # i32[M1]
        f.write(nn2_offsets.tobytes())                             # i32[N+1]
        f.write(nn2_indices.tobytes())                             # i32[M2]
        f.write(layer_index.astype(np.int8).tobytes())             # i8[N]
        f.write(site_class.astype(np.uint8).tobytes())             # u8[N]
        f.write(initial_species.tobytes())                         # u8[N]
        f.write(nn1_dir_family.tobytes())                          # u8[M1]
        f.write(nn2_dir_family.tobytes())                          # u8[M2]

    return header


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xyz", type=Path, required=True, help="pyKMC initial_config.xyz")
    ap.add_argument("--out", type=Path, required=True, help="output .kmcinit")
    ap.add_argument("--element", default="Ni", choices=list(SPECIES_ID))
    ap.add_argument("--n-adatom-layers", type=int, default=0,
                    help="Add this many empty FCC(100) layers above the top atom "
                         "layer to give exchange-up events landing positions. "
                         "Recommended: 3 to support adatom create/destroy cycles.")
    args = ap.parse_args()
    h = build_kmcinit(args.xyz, args.out, primary_element=args.element,
                      n_adatom_layers=args.n_adatom_layers)
    print(f"wrote {args.out}")
    print(f"  n_sites={h['n_sites']}, n_vacancies={h['n_vacancies']}, "
          f"layout={h['nx']}x{h['ny']}x{h['nz']}")
    print(f"  nn1_count={h['nn1_count']}, nn2_count={h['nn2_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
