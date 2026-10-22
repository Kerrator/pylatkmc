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

Scaling: positions are generated with numpy and both neighbour lists come from
one periodic cKDTree pass (compute_neighbor_csr), so 1e6+ sites take seconds,
not hours, with output byte-identical to the original per-site loop. Limits:
nx, ny >= 2 (in a one-site-wide periodic cell every site neighbours itself) and
at most 128 layers in total, atom + adatom (the .kmcinit stores layer_index as
int8, read by runtime/src/io/initconfig.c).
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from kmcfmt import INITCONFIG_MAGIC, write_header
from scipy.spatial import cKDTree

SPECIES_ID = {"Ni": 1, "Fe": 2, "Cr": 3}
A_LATTICE = {"Ni": 3.524, "Fe": 3.524, "Cr": 3.524}

SC_SURFACE = 0
SC_SUBSURFACE = 1
SC_BULK_LIKE = 2

DF_110_INPLANE = 0
DF_100_INPLANE = 1
DF_111_INTERLAYER = 2
DF_001_EXCHANGE = 3
DF_UNRESOLVED = 4


def build_fcc100_slab(
    nx: int,
    ny: int,
    nz: int,
    nn_dist: float,
    vacuum_layers: float = 0.0,
    n_adatom_layers: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (positions [N,3], layer_index [N], site_class [N], cell [3]).

    Requires nz >= 3 so there's a real top surface, subsurface, and at least
    one bulk-like layer.

    `n_adatom_layers`: number of additional FCC(100) layers to generate
    *above* the top atom-occupied layer. These layers contribute lattice
    SITES but the caller is expected to leave their initial_species as
    SP_VACANT. They give exchange-up events somewhere to land an
    adatom; without them the runtime's coord_table points stub-site for
    NC_NN1_UP_* and the forward exchange-up Action gets rejected by
    state_apply_actions validation. With n_adatom_layers >= 1 the top
    surface's NC_NN1_UP_* points to a real (initially vacant) lattice
    site.
    """
    if nz < 3:
        raise ValueError(f"nz must be >= 3 (got {nz}); latkmc is 3D-only")

    if vacuum_layers < 0:
        raise ValueError(f"vacuum_layers must be >= 0 (got {vacuum_layers})")
    if n_adatom_layers < 0:
        raise ValueError(f"n_adatom_layers must be >= 0 (got {n_adatom_layers})")

    ls = nn_dist / np.sqrt(2.0)  # layer spacing, a/2 for FCC(100)
    nz_total = nz + n_adatom_layers
    # layer_index is int8 in the .kmcinit payload (initconfig.c reads int8):
    # refuse instead of wrapping (NumPy 1.x) or an opaque OverflowError (2.x).
    max_layers = int(np.iinfo(np.int8).max) + 1
    if nz_total > max_layers:
        raise ValueError(
            f"nz + n_adatom_layers = {nz_total} layers, but the .kmcinit format stores "
            f"layer_index as int8: at most {max_layers} layers"
        )

    # Site order k (layer), then i, then j. Odd layers sit on the hollows,
    # shifted by half a 1NN spacing in x and y.
    k, i, j = (
        a.ravel()
        for a in np.meshgrid(np.arange(nz_total), np.arange(nx), np.arange(ny), indexing="ij")
    )
    shift = np.where(k % 2 == 1, 0.5 * nn_dist, 0.0)
    positions = np.stack([i * nn_dist + shift, j * nn_dist + shift, k * ls], axis=1).astype(
        np.float32
    )
    layer_index = k.astype(np.int8)

    # Site class is computed for the *atom-occupied* slab — the adatom
    # layers above are flagged SC_BULK_LIKE because the static-active
    # filter already picks them up via 1NN-degree (they have only 4
    # downward 1NN, well below bulk's 12, so they're "active" by
    # geometry).
    top = nz - 1  # top atom layer (NOT top of total grid)
    site_class = np.full(len(positions), SC_BULK_LIKE, dtype=np.uint8)
    site_class[layer_index == top] = SC_SURFACE
    site_class[layer_index == top - 1] = SC_SUBSURFACE

    cell = np.array(
        [nx * nn_dist, ny * nn_dist, (nz_total + vacuum_layers) * ls],
        dtype=np.float32,
    )
    return positions, layer_index, site_class, cell


def compute_neighbors_with_pbc(
    positions: np.ndarray, cell: np.ndarray, nn_dist: float, cutoff_factor: float
) -> list[list[tuple[int, np.ndarray]]]:
    """For each site, return a list of (neighbor_index, minimum_image_displacement).

    Displacement is the Cartesian vector FROM the site TO the neighbor, already
    minimum-imaged. cutoff = cutoff_factor * nn_dist (use 1.1 for 1NN, sqrt(2)*1.05
    for 2NN). Sites don't include themselves.

    Per-site Python loop over 9 xy image copies: fine for small slabs only.
    main() uses compute_neighbor_csr; this stays for tools/xyz_to_kmcinit.py,
    whose CSR keeps this function's hit order.
    """
    n = len(positions)
    cell_arr = np.asarray(cell, dtype=np.float64)
    # Replicate positions to 3x3 in xy for PBC search (periodicity is only in xy
    # for a slab; z is non-periodic for n_z > 1 but we still ask for neighbours
    # naturally because our cutoff is much smaller than cell_z).
    offsets = [
        (ox, oy, 0.0)
        for ox in (-cell_arr[0], 0.0, cell_arr[0])
        for oy in (-cell_arr[1], 0.0, cell_arr[1])
    ]
    images = np.vstack([positions + np.array(o, dtype=np.float64) for o in offsets])
    tree = cKDTree(images)
    cutoff = cutoff_factor * nn_dist

    out: list[list[tuple[int, np.ndarray]]] = [[] for _ in range(n)]
    eps2 = 1e-8
    for i in range(n):
        p = positions[i].astype(np.float64)
        hits = tree.query_ball_point(p, cutoff)
        for h in hits:
            disp = images[h] - p
            if disp.dot(disp) < eps2:  # self at any image index
                continue
            j = h % n
            out[i].append((j, disp))
    return out


def classify_direction(disp: np.ndarray, nn_dist: float) -> np.ndarray:
    """Classify Cartesian edge displacements (shape (..., 3)) into DF_* enums (uint8, shape (...))."""
    disp = np.asarray(disp, dtype=np.float64)
    dz = np.abs(disp[..., 2])
    d_xy = np.hypot(disp[..., 0], disp[..., 1])
    ls = nn_dist / np.sqrt(2.0)
    tol = 0.1 * nn_dist
    in_plane = dz < tol
    # First matching rule wins, as in the original scalar if-chain.
    rules = [
        (in_plane & (np.abs(d_xy - nn_dist) < tol), DF_110_INPLANE),
        (in_plane & (np.abs(d_xy - np.sqrt(2.0) * nn_dist) < tol), DF_100_INPLANE),
        (in_plane, DF_UNRESOLVED),
        (np.abs(dz - ls) < tol, DF_111_INTERLAYER),
        ((np.abs(dz - 2 * ls) < tol) & (d_xy < tol), DF_001_EXCHANGE),
    ]
    return np.select(
        [cond for cond, _ in rules], [df for _, df in rules], default=DF_UNRESOLVED
    ).astype(np.uint8)


def compute_neighbor_csr(
    positions: np.ndarray, cell: np.ndarray, nn_dist: float, chunk: int = 1 << 16
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return the 1NN and 2NN lists as CSR: (nn1_offsets, nn1_indices, nn1_dir,
    nn2_offsets, nn2_indices, nn2_dir).

    1NN = within 1.1*nn_dist; 2NN = within sqrt(2)*1.05*nn_dist and not 1NN. PBC
    in xy only; each site's neighbours sorted by index; direction family from
    the minimum-image displacement. One periodic cKDTree (boxsize = the cell in
    xy, and a z box tall enough never to wrap) is queried in chunks of `chunk`
    sites and the lists are packed with numpy: no image copies, no per-site
    Python loop, no per-edge Python objects. The output is byte-identical to the
    original per-site loop (compute_neighbors_with_pbc, first image per
    neighbour, sorted): the displacement is computed with the same float
    operations, (position_j + image_offset) - position_i.

    The cell must be wider than the 2NN cutoff in x and y (nx, ny >= 2): in a
    one-site-wide cell every site is its own in-plane neighbour through a
    periodic image, which the per-site loop wrote as a self-edge.
    """
    n = len(positions)
    pos = positions.astype(np.float64)
    box_xy = np.asarray(cell, dtype=np.float64)[:2]
    r1 = 1.1 * nn_dist
    r2 = np.sqrt(2.0) * 1.05 * nn_dist
    if box_xy.min() <= r2:
        raise ValueError(
            f"cell {box_xy[0]:g} x {box_xy[1]:g} A is not wider than the 2NN cutoff "
            f"{r2:.4g} A: every site would neighbour itself through a periodic image "
            "(use nx, ny >= 2)"
        )
    z_box = float(pos[:, 2].max()) + 2.0 * r2 + 1.0
    tree = cKDTree(pos, boxsize=[box_xy[0], box_xy[1], z_box])
    # At most 19 sites (self + 12 1NN + 6 2NN) lie within the 2NN cutoff of an
    # FCC site; the 20th column must stay empty or a neighbour was cut off.
    k_query = 20
    parts: list[tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]] = [
        ([], [], []),
        ([], [], []),
    ]
    for a in range(0, n, chunk):
        p = pos[a : a + chunk]
        dist, nbr = tree.query(p, k=k_query, distance_upper_bound=r2 * (1.0 + 1e-6))
        if np.isfinite(dist[:, -1]).any():
            raise RuntimeError(f"more than {k_query - 1} sites within the 2NN cutoff of a site")
        found = nbr < n
        nbr = np.where(found, nbr, 0)  # placeholder index for empty columns (masked below)
        q = pos[nbr]
        # Image offset -L, 0 or +L per periodic axis: the one bringing j nearest i.
        offset = np.zeros_like(q)
        offset[..., :2] = -np.rint((q[..., :2] - p[:, None, :2]) / box_xy) * box_xy
        disp = (q + offset) - p[:, None, :]
        d2 = disp[..., 0] ** 2 + disp[..., 1] ** 2 + disp[..., 2] ** 2
        found &= d2 >= 1e-8  # drop the site itself
        dir_family = classify_direction(disp, nn_dist)
        in_shell = (found & (d2 <= r1 * r1), found & (d2 > r1 * r1) & (d2 <= r2 * r2))
        for (indices, dirs, counts), mask in zip(parts, in_shell):
            key = np.where(mask, nbr, n)  # absent entries sort last
            order = np.argsort(key, axis=1, kind="stable")
            key = np.take_along_axis(key, order, axis=1)
            keep = key < n
            indices.append(key[keep].astype(np.int32))
            dirs.append(np.take_along_axis(dir_family, order, axis=1)[keep])
            counts.append(keep.sum(axis=1))

    def pack(
        indices: list[np.ndarray], dirs: list[np.ndarray], counts: list[np.ndarray]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        offsets = np.zeros(n + 1, dtype=np.int64)
        np.cumsum(np.concatenate(counts), out=offsets[1:])
        if offsets[-1] > np.iinfo(np.int32).max:
            raise ValueError(f"{offsets[-1]} edges exceed the .kmcinit int32 CSR offsets")
        return offsets.astype(np.int32), np.concatenate(indices), np.concatenate(dirs)

    return (*pack(*parts[0]), *pack(*parts[1]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lattice", choices=["fcc"], default="fcc")
    ap.add_argument("--orientation", choices=["100"], default="100")
    ap.add_argument("--nx", type=int, required=True)
    ap.add_argument("--ny", type=int, required=True)
    ap.add_argument("--nz", type=int, default=3, help="Number of FCC(100) layers (>= 3)")
    ap.add_argument(
        "--element",
        default="Ni",
        choices=list(SPECIES_ID),
        help="Primary element; used for lattice constant. Ignored when --composition is set.",
    )
    ap.add_argument(
        "--composition",
        default=None,
        help="Random alloy composition, e.g. 'Ni0.95_Cr0.05' or "
        "'Ni90_Fe5_Cr5'. Fractions are normalized automatically.",
    )
    ap.add_argument("--n-vacancies", type=int, default=1)
    ap.add_argument(
        "--vacancy-layer",
        type=int,
        default=None,
        help="Restrict initial vacancies to this layer (default: any layer)",
    )
    ap.add_argument(
        "--vacuum-layers",
        type=float,
        default=0.0,
        help="Extra empty FCC(100) layer spacings added above the slab "
        "(empty cell space, no lattice sites)",
    )
    ap.add_argument(
        "--n-adatom-layers",
        type=int,
        default=0,
        help="Number of FCC(100) layers ADDED ABOVE the top atom layer "
        "as VACANT lattice sites — gives exchange-up events landing "
        "positions for adatoms. Default 0 (no adatom region). "
        "Recommended: 3 for full adatom-cycle support.",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    a = A_LATTICE[args.element]
    nn_dist = a / np.sqrt(2.0)

    try:
        positions, layer_index, site_class, cell = build_fcc100_slab(
            args.nx,
            args.ny,
            args.nz,
            nn_dist,
            vacuum_layers=args.vacuum_layers,
            n_adatom_layers=args.n_adatom_layers,
        )
        # 1NN within 1.1*nn_dist; 2NN within sqrt(2)*nn_dist*1.05, minus the 1NN
        nn1_offsets, nn1_indices, nn1_dir, nn2_offsets, nn2_indices, nn2_dir = compute_neighbor_csr(
            positions, cell, nn_dist
        )
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    n_sites = positions.shape[0]
    nz_total = args.nz + args.n_adatom_layers

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
                sys.exit(f"error: '{p}' has no fraction — use e.g. 'Ni0.95_Cr0.05' or 'Ni95_Cr5'")
            parsed.append((name, float(frac_str)))
        tot = sum(f for _, f in parsed)
        if tot <= 0.0:
            sys.exit(f"error: composition fractions sum to {tot}")
        fracs = np.array([f / tot for _, f in parsed], dtype=np.float64)
        ids = np.array([SPECIES_ID[n] for n, _ in parsed], dtype=np.uint8)
        species = rng.choice(ids, size=n_sites, p=fracs).astype(np.uint8)
        composition_report = ", ".join(f"{n} {100 * f / tot:.1f}%" for n, f in parsed)
    else:
        species = np.full(n_sites, SPECIES_ID[args.element], dtype=np.uint8)

    # Adatom layers (k >= args.nz) are sites WITHOUT atoms — clear them
    # to SP_VACANT regardless of any composition assignment above.
    if args.n_adatom_layers > 0:
        adatom_mask = layer_index >= args.nz
        species[adatom_mask] = 0  # SP_VACANT
        n_adatom_sites = int(adatom_mask.sum())

    # Punch vacancies — restrict candidates to the atom-occupied layers
    # (k < args.nz) so we don't accidentally place "vacancies" where no
    # atom ever lived.
    if args.vacancy_layer is not None:
        candidates = np.flatnonzero(layer_index == args.vacancy_layer)
    else:
        candidates = np.flatnonzero(layer_index < args.nz)
    if args.n_vacancies > candidates.size:
        sys.exit(f"error: n_vacancies={args.n_vacancies} exceeds candidate sites {candidates.size}")
    if args.n_vacancies > 0:
        chosen = rng.choice(candidates, size=args.n_vacancies, replace=False)
        species[chosen] = 0  # SP_VACANT

    # Sanity check on neighbour counts: for bulk FCC, each atom should have
    # 12 1NN + 6 2NN. For surface sites, fewer.
    bulk_1nn_count = int(
        np.median(np.diff(nn1_offsets)[layer_index == layer_index[len(positions) // 2]])
    )

    header = {
        "version": 1,
        "n_sites": int(n_sites),
        "n_layers": int(nz_total),  # total layer count (atoms + adatom region)
        "n_atom_layers": int(args.nz),  # of which `n_atom_layers` are initially Ni
        "n_adatom_layers": int(args.n_adatom_layers),
        "cell": [float(cell[0]), float(cell[1]), float(cell[2])],
        "nn_dist": float(nn_dist),
        "n_elements": len(SPECIES_ID) + 1,
        "element_names": ["X", "Ni", "Fe", "Cr"],
        "lattice": args.lattice,
        "orientation": args.orientation,
        "nx": args.nx,
        "ny": args.ny,
        "nz": args.nz,
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
    print(
        f"  nn1_edges={nn1_indices.size} (avg {nn1_avg:.1f}/site); "
        f"nn2_edges={nn2_indices.size} (avg {nn2_avg:.1f}/site)"
    )
    print(f"  mid-slab 1NN count = {bulk_1nn_count}")
    print(
        f"  site_class hist: surface={int((site_class == 0).sum())}, "
        f"subsurface={int((site_class == 1).sum())}, "
        f"bulk_like={int((site_class == 2).sum())}"
    )
    print(f"  composition: {composition_report}")
    print(
        "  species hist: "
        + ", ".join(
            f"{name}={int((species == code).sum())}"
            for name, code in SPECIES_ID.items()
            if (species == code).sum() > 0
        )
        + f", vacant={int((species == 0).sum())}"
    )
    print(f"  n_vacancies={args.n_vacancies}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
