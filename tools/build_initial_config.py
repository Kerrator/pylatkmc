"""build_initial_config.py — generate a .kmcinit for latkmc.

3D FCC(100) slab of nx × ny surface sites × nz layers (nz ≥ 3). Neighbours
are computed from Cartesian positions with PBC in xy only, mirroring
Analysis/lattice_3d.py.compute_3d_site_graph.

Site layout:
  - Even layers (k=0, 2, ...): sites at (i, j, k*ls) * (nn_dist, nn_dist, 1)
  - Odd  layers (k=1, 3, ...): sites at ((i+0.5), (j+0.5), k*ls) * (nn_dist, nn_dist, 1)
  where ls = layer spacing = nn_dist / sqrt(2) = a/2 for FCC(100).

Site classification:
  - Top layer (k = nz-1) → SC_SURFACE
  - Second-from-top (k = nz-2) → SC_SUBSURFACE
  - Everything else → SC_BULK_LIKE

Direction-family labels (computed from the Cartesian edge vector with PBC):
  - |dz| ≈ 0, |d_xy| ≈ nn_dist              → DF_110_INPLANE (1NN axial)
  - |dz| ≈ 0, |d_xy| ≈ sqrt(2)*nn_dist      → DF_100_INPLANE (2NN diag)
  - |dz| ≈ ls, any |d_xy|                   → DF_111_INTERLAYER (1NN across layers)
  - |dz| ≈ 2*ls, |d_xy| ≈ 0                 → DF_001_EXCHANGE (2NN axial z)
  - anything else                            → DF_UNRESOLVED
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from kmcfmt import INITCONFIG_MAGIC, write_header

SPECIES_ID = {"Ni": 1, "Fe": 2, "Cr": 3}
A_LATTICE  = {"Ni": 3.524, "Fe": 3.524, "Cr": 3.524}

SC_SURFACE    = 0
SC_SUBSURFACE = 1
SC_BULK_LIKE  = 2

DF_110_INPLANE    = 0
DF_100_INPLANE    = 1
DF_111_INTERLAYER = 2
DF_001_EXCHANGE   = 3
DF_UNRESOLVED     = 4


def build_fcc100_slab(nx: int, ny: int, nz: int, nn_dist: float,
                      vacuum_layers: float = 0.0,
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (positions [N,3], layer_index [N], site_class [N], cell [3]).

    Requires nz >= 3 so there's a real top surface, subsurface, and at least
    one bulk-like layer.
    """
    if nz < 3:
        raise ValueError(f"nz must be >= 3 (got {nz}); latkmc is 3D-only")

    if vacuum_layers < 0:
        raise ValueError(f"vacuum_layers must be >= 0 (got {vacuum_layers})")

    ls = nn_dist / np.sqrt(2.0)   # layer spacing, a/2 for FCC(100)
    sites: list[tuple[float, float, float, int]] = []
    for k in range(nz):
        dx = 0.5 * nn_dist if (k % 2 == 1) else 0.0
        dy = 0.5 * nn_dist if (k % 2 == 1) else 0.0
        for i in range(nx):
            for j in range(ny):
                x = i * nn_dist + dx
                y = j * nn_dist + dy
                z = k * ls
                sites.append((x, y, z, k))

    positions   = np.array([(s[0], s[1], s[2]) for s in sites], dtype=np.float32)
    layer_index = np.array([s[3] for s in sites], dtype=np.int8)

    top = nz - 1
    site_class = np.full(len(sites), SC_BULK_LIKE, dtype=np.uint8)
    site_class[layer_index == top]     = SC_SURFACE
    site_class[layer_index == top - 1] = SC_SUBSURFACE

    cell = np.array(
        [nx * nn_dist, ny * nn_dist, (nz + vacuum_layers) * ls],
        dtype=np.float32,
    )
    return positions, layer_index, site_class, cell


def compute_neighbors_with_pbc(positions: np.ndarray, cell: np.ndarray,
                                nn_dist: float, cutoff_factor: float
                                ) -> list[list[tuple[int, np.ndarray]]]:
    """For each site, return a list of (neighbor_index, minimum_image_displacement).

    Displacement is the Cartesian vector FROM the site TO the neighbor, already
    minimum-imaged. cutoff = cutoff_factor * nn_dist (use 1.1 for 1NN, sqrt(2)*1.05
    for 2NN). Sites don't include themselves.
    """
    n = len(positions)
    cell_arr = np.asarray(cell, dtype=np.float64)
    # Replicate positions to 3x3 in xy for PBC search (periodicity is only in xy
    # for a slab; z is non-periodic for n_z > 1 but we still ask for neighbours
    # naturally because our cutoff is much smaller than cell_z).
    offsets = [(ox, oy, 0.0)
               for ox in (-cell_arr[0], 0.0, cell_arr[0])
               for oy in (-cell_arr[1], 0.0, cell_arr[1])]
    images = np.vstack([positions + np.array(o, dtype=np.float64) for o in offsets])
    tree   = cKDTree(images)
    cutoff = cutoff_factor * nn_dist

    out: list[list[tuple[int, np.ndarray]]] = [[] for _ in range(n)]
    eps2 = 1e-8
    for i in range(n):
        p = positions[i].astype(np.float64)
        hits = tree.query_ball_point(p, cutoff)
        for h in hits:
            disp = images[h] - p
            if disp.dot(disp) < eps2:   # self at any image index
                continue
            j = h % n
            out[i].append((j, disp))
    return out


def classify_direction(disp: np.ndarray, nn_dist: float) -> int:
    """Classify a Cartesian edge displacement into a DF_* enum."""
    dx, dy, dz = float(disp[0]), float(disp[1]), float(disp[2])
    d_xy = np.hypot(dx, dy)
    ls = nn_dist / np.sqrt(2.0)
    tol = 0.1 * nn_dist

    if abs(dz) < tol:
        if abs(d_xy - nn_dist)                < tol: return DF_110_INPLANE
        if abs(d_xy - np.sqrt(2.0) * nn_dist) < tol: return DF_100_INPLANE
        return DF_UNRESOLVED
    if abs(abs(dz) - ls) < tol:
        return DF_111_INTERLAYER
    if abs(abs(dz) - 2 * ls) < tol and d_xy < tol:
        return DF_001_EXCHANGE
    return DF_UNRESOLVED


def adj_to_csr(adj: list[list[tuple[int, np.ndarray]]], classify_dir,
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deduplicate + sort each site's neighbour list, then pack into CSR.
    Returns (offsets, indices, dir_family)."""
    n = len(adj)
    offsets = np.zeros(n + 1, dtype=np.int32)
    all_items: list[tuple[int, int]] = []  # (neighbor_idx, dir_family)
    for s, items in enumerate(adj):
        seen: dict[int, int] = {}
        for j, disp in items:
            # PBC images can land the same neighbor j multiple times; prefer
            # the minimum-image displacement (smallest magnitude).
            df = classify_dir(disp)
            if j in seen:
                continue
            seen[j] = df
        sorted_neighbors = sorted(seen.items())
        offsets[s + 1] = offsets[s] + len(sorted_neighbors)
        all_items.extend(sorted_neighbors)
    indices    = np.array([it[0] for it in all_items], dtype=np.int32)
    dir_family = np.array([it[1] for it in all_items], dtype=np.uint8)
    return offsets, indices, dir_family


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lattice", choices=["fcc"], default="fcc")
    ap.add_argument("--orientation", choices=["100"], default="100")
    ap.add_argument("--nx", type=int, required=True)
    ap.add_argument("--ny", type=int, required=True)
    ap.add_argument("--nz", type=int, default=3,
                    help="Number of FCC(100) layers (>= 3)")
    ap.add_argument("--element", default="Ni", choices=list(SPECIES_ID),
                    help="Primary element; used for lattice constant. Ignored "
                         "when --composition is set.")
    ap.add_argument("--composition", default=None,
                    help="Random alloy composition, e.g. 'Ni0.95_Cr0.05' or "
                         "'Ni90_Fe5_Cr5'. Fractions are normalized automatically.")
    ap.add_argument("--n-vacancies", type=int, default=1)
    ap.add_argument("--vacancy-layer", type=int, default=None,
                    help="Restrict initial vacancies to this layer (default: any layer)")
    ap.add_argument("--vacuum-layers", type=float, default=0.0,
                    help="Extra empty FCC(100) layer spacings added above the slab")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    a       = A_LATTICE[args.element]
    nn_dist = a / np.sqrt(2.0)

    positions, layer_index, site_class, cell = build_fcc100_slab(
        args.nx, args.ny, args.nz, nn_dist, args.vacuum_layers)
    n_sites = positions.shape[0]

    # 1NN within 1.1*nn_dist; 2NN within sqrt(2)*nn_dist*1.05
    adj_1nn = compute_neighbors_with_pbc(positions, cell, nn_dist, 1.1)
    adj_2nn_raw = compute_neighbors_with_pbc(positions, cell, nn_dist,
                                             np.sqrt(2.0) * 1.05)
    # Exclude 1NN from 2NN list.
    adj_2nn: list[list[tuple[int, np.ndarray]]] = []
    for s in range(n_sites):
        nn1_set = {j for j, _ in adj_1nn[s]}
        adj_2nn.append([(j, d) for j, d in adj_2nn_raw[s] if j not in nn1_set])

    def classifier(d: np.ndarray) -> int:
        return classify_direction(d, nn_dist)
    nn1_offsets, nn1_indices, nn1_dir = adj_to_csr(adj_1nn, classifier)
    nn2_offsets, nn2_indices, nn2_dir = adj_to_csr(adj_2nn, classifier)

    # Species: either homogeneous (primary element) OR random alloy from --composition.
    rng = np.random.default_rng(args.seed)
    composition_report = f"100% {args.element}"
    if args.composition:
        # Parse 'Ni0.95_Cr0.05' / 'Ni90_Fe5_Cr5' etc. into (name, fraction) pairs.
        parts = args.composition.split("_")
        parsed: list[tuple[str, float]] = []
        pattern = __import__("re").compile(r"^([A-Za-z]+)(\d+\.?\d*|\.\d+)?$")
        for p in parts:
            m = pattern.match(p)
            if m is None:
                sys.exit(f"error: cannot parse composition token '{p}'")
            name = m.group(1)
            frac_str = m.group(2)
            if name not in SPECIES_ID:
                sys.exit(f"error: unknown species '{name}' (known: {list(SPECIES_ID)})")
            if frac_str is None:
                sys.exit(f"error: '{p}' has no fraction — "
                         "use e.g. 'Ni0.95_Cr0.05' or 'Ni95_Cr5'")
            parsed.append((name, float(frac_str)))
        tot = sum(f for _, f in parsed)
        if tot <= 0.0:
            sys.exit(f"error: composition fractions sum to {tot}")
        fracs = np.array([f / tot for _, f in parsed], dtype=np.float64)
        ids   = np.array([SPECIES_ID[n] for n, _ in parsed], dtype=np.uint8)
        species = rng.choice(ids, size=n_sites, p=fracs).astype(np.uint8)
        composition_report = ", ".join(
            f"{n} {100*f/tot:.1f}%" for n, f in parsed
        )
    else:
        species = np.full(n_sites, SPECIES_ID[args.element], dtype=np.uint8)

    # Punch vacancies.
    if args.vacancy_layer is not None:
        candidates = np.flatnonzero(layer_index == args.vacancy_layer)
    else:
        candidates = np.arange(n_sites)
    if args.n_vacancies > candidates.size:
        sys.exit(f"error: n_vacancies={args.n_vacancies} exceeds candidate sites {candidates.size}")
    if args.n_vacancies > 0:
        chosen = rng.choice(candidates, size=args.n_vacancies, replace=False)
        species[chosen] = 0  # SP_VACANT

    # Sanity check on neighbour counts: for bulk FCC, each atom should have
    # 12 1NN + 6 2NN. For surface sites, fewer.
    bulk_1nn_count = int(np.median(np.diff(nn1_offsets)[layer_index == layer_index[len(positions)//2]]))

    header = {
        "version": 1,
        "n_sites": int(n_sites),
        "n_layers": int(args.nz),
        "cell": [float(cell[0]), float(cell[1]), float(cell[2])],
        "nn_dist": float(nn_dist),
        "n_elements": len(SPECIES_ID) + 1,
        "element_names": ["X", "Ni", "Fe", "Cr"],
        "lattice": args.lattice,
        "orientation": args.orientation,
        "nx": args.nx, "ny": args.ny, "nz": args.nz,
        "primary_element": args.element,
        "n_vacancies": int(args.n_vacancies),
        "vacuum_layers": float(args.vacuum_layers),
        "vacuum_A": float(args.vacuum_layers * nn_dist / np.sqrt(2.0)),
        "seed": int(args.seed),
        "nn1_count": int(nn1_indices.size),
        "nn2_count": int(nn2_indices.size),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as fp:
        write_header(fp, INITCONFIG_MAGIC, header)
        fp.write(struct.pack("<I", 1))  # payload version

        fp.write(positions.astype(np.float32, copy=False).tobytes())
        fp.write(nn1_offsets.astype(np.int32, copy=False).tobytes())
        fp.write(nn1_indices.astype(np.int32, copy=False).tobytes())
        fp.write(nn2_offsets.astype(np.int32, copy=False).tobytes())
        fp.write(nn2_indices.astype(np.int32, copy=False).tobytes())
        fp.write(layer_index.tobytes())
        fp.write(site_class.tobytes())
        fp.write(species.tobytes())
        fp.write(nn1_dir.tobytes())
        fp.write(nn2_dir.tobytes())

    sz = args.output.stat().st_size
    nn1_avg = nn1_indices.size / n_sites
    nn2_avg = nn2_indices.size / n_sites
    print(f"wrote {args.output} ({sz} bytes)")
    print(f"  N={n_sites}  layers={args.nz}  cell={cell.tolist()}")
    print(f"  vacuum_layers={args.vacuum_layers:g}")
    print(f"  nn1_edges={nn1_indices.size} (avg {nn1_avg:.1f}/site); "
          f"nn2_edges={nn2_indices.size} (avg {nn2_avg:.1f}/site)")
    print(f"  mid-slab 1NN count = {bulk_1nn_count}")
    print(f"  site_class hist: surface={int((site_class==0).sum())}, "
          f"subsurface={int((site_class==1).sum())}, "
          f"bulk_like={int((site_class==2).sum())}")
    print(f"  composition: {composition_report}")
    print(f"  species hist: "
          + ", ".join(
              f"{name}={int((species == code).sum())}"
              for name, code in SPECIES_ID.items()
              if (species == code).sum() > 0
          )
          + f", vacant={int((species == 0).sum())}")
    print(f"  n_vacancies={args.n_vacancies}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
