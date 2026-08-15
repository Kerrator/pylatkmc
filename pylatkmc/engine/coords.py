"""Neighbour-code geometry: the 23 canonical FCC deltas and the per-site
``coord_table`` builder.

This is the Python port of ``runtime/src/core/coord_codes.{h,c}`` and
``lattice_build_coord_table`` in ``runtime/src/core/lattice.c``. The deltas and the
0.05 match tolerance ARE the contract — they must match the C constants exactly.
"""

from __future__ import annotations

import numpy as np

from pylatkmc.processes import NEIGHBOUR_CODES

COORD_MATCH_TOL: float = 0.05

CODE_INDEX: dict[str, int] = {name: i for i, name in enumerate(NEIGHBOUR_CODES)}

# 1/sqrt(2) and sqrt(2), matching coord_codes.c (INVS2, S2). z uses 1/√2 for
# cross-layer 1NN, √2 for axial 2NN, in nn_d units.
_INVS2 = 0.70710678
_S2 = 1.41421356

# Index order MUST match pylatkmc.processes.NEIGHBOUR_CODES (== the C enum order).
NEIGHBOUR_CODE_DELTAS: np.ndarray = np.array(
    [
        [0.0, 0.0, 0.0],          # NC_ANCHOR
        [+1.0, 0.0, 0.0],         # NC_NN1_PX
        [-1.0, 0.0, 0.0],         # NC_NN1_MX
        [0.0, +1.0, 0.0],         # NC_NN1_PY
        [0.0, -1.0, 0.0],         # NC_NN1_MY
        [+0.5, +0.5, -_INVS2],    # NC_NN1_DOWN_PP
        [+0.5, -0.5, -_INVS2],    # NC_NN1_DOWN_PM
        [-0.5, +0.5, -_INVS2],    # NC_NN1_DOWN_MP
        [-0.5, -0.5, -_INVS2],    # NC_NN1_DOWN_MM
        [+0.5, +0.5, +_INVS2],    # NC_NN1_UP_PP
        [+0.5, -0.5, +_INVS2],    # NC_NN1_UP_PM
        [-0.5, +0.5, +_INVS2],    # NC_NN1_UP_MP
        [-0.5, -0.5, +_INVS2],    # NC_NN1_UP_MM
        [+1.0, +1.0, 0.0],        # NC_NN2_DIAG_PP
        [+1.0, -1.0, 0.0],        # NC_NN2_DIAG_PM
        [-1.0, +1.0, 0.0],        # NC_NN2_DIAG_MP
        [-1.0, -1.0, 0.0],        # NC_NN2_DIAG_MM
        [+2.0, 0.0, 0.0],         # NC_NN2_PX
        [-2.0, 0.0, 0.0],         # NC_NN2_MX
        [0.0, +2.0, 0.0],         # NC_NN2_PY
        [0.0, -2.0, 0.0],         # NC_NN2_MY
        [0.0, 0.0, +_S2],         # NC_NN2_PZ
        [0.0, 0.0, -_S2],         # NC_NN2_MZ
    ],
    dtype=np.float32,
)


def _min_image1(d: float, length: float) -> float:
    """Fold a one-axis displacement into [-L/2, L/2] (matches min_image1 in lattice.c)."""
    if d > 0.5 * length:
        return d - length
    if d < -0.5 * length:
        return d + length
    return d


def _match_code(dx_n: float, dy_n: float, dz_n: float) -> int:
    """Return the NeighbourCode index whose delta matches (dx, dy, dz) in nn_d units,
    or -1 if none within COORD_MATCH_TOL. NC_ANCHOR (index 0) is never matched here."""
    for nc in range(1, len(NEIGHBOUR_CODES)):
        cd = NEIGHBOUR_CODE_DELTAS[nc]
        if (
            abs(dx_n - cd[0]) < COORD_MATCH_TOL
            and abs(dy_n - cd[1]) < COORD_MATCH_TOL
            and abs(dz_n - cd[2]) < COORD_MATCH_TOL
        ):
            return nc
    return -1


def build_coord_table(
    positions: np.ndarray,
    nn1_offsets: np.ndarray,
    nn1_indices: np.ndarray,
    nn2_offsets: np.ndarray,
    nn2_indices: np.ndarray,
    cell: tuple[float, float, float],
    nn_dist: float,
) -> np.ndarray:
    """Build ``coord_table[n_sites, 23]`` of neighbour site indices.

    Entry ``[s, 0]`` (NC_ANCHOR) is ``s``. Every other entry is the matched
    neighbour site index, or the stub value ``n_sites`` when ``s`` has no such
    neighbour. First match wins on PBC alias (matches lattice.c). Mirrors
    ``lattice_build_coord_table``.
    """
    n_sites = int(positions.shape[0])
    n_codes = len(NEIGHBOUR_CODES)
    stub = n_sites
    table = np.full((n_sites, n_codes), stub, dtype=np.int32)
    inv_nn = 1.0 / nn_dist
    lx, ly, lz = float(cell[0]), float(cell[1]), float(cell[2])

    for s in range(n_sites):
        table[s, 0] = s
        sx, sy, sz = (
            float(positions[s, 0]),
            float(positions[s, 1]),
            float(positions[s, 2]),
        )
        for offsets, indices in (
            (nn1_offsets, nn1_indices),
            (nn2_offsets, nn2_indices),
        ):
            for i in range(int(offsets[s]), int(offsets[s + 1])):
                n = int(indices[i])
                dx = _min_image1(float(positions[n, 0]) - sx, lx) * inv_nn
                dy = _min_image1(float(positions[n, 1]) - sy, ly) * inv_nn
                dz = _min_image1(float(positions[n, 2]) - sz, lz) * inv_nn
                nc = _match_code(dx, dy, dz)
                if nc < 0:
                    continue
                if table[s, nc] == stub:
                    table[s, nc] = n
    return table
