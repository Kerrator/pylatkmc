#ifndef PYLATKMC_COORD_CODES_H
#define PYLATKMC_COORD_CODES_H

#include <stdint.h>

/* NeighbourCode — flat enum naming every neighbour direction the
 * pylatkmc catalogue references.
 *
 * Adapted from kmos's `Coord(name, offset, layer)` direction-resolution
 * scheme (kmos-main/kmos/types.py:1778) but flattened: each code is a
 * specific neighbour relative to the anchor, with a documented
 * Cartesian delta in `nn_d` units (where `nn_d` is the FCC 1NN
 * distance, a/√2 for lattice constant a).
 *
 * Why not integer (di, dj, dk) offsets? For FCC (100) slabs, the
 * cross-layer 1NN sit at face-shifted positions like (±0.5, ±0.5,
 * ±a/2), which can't be expressed as integer triples in any basis
 * that *also* keeps in-plane axial offsets integer. NeighbourCode
 * sidesteps this by enumerating each direction as a named atom, and
 * the runtime builds a per-site lookup table at lattice load to
 * resolve each code to a concrete neighbour index.
 *
 * Catalogue coverage (FCC):
 *   - In-plane axial 1NN  : 4 codes (±x, ±y at delta nn_d)
 *   - Cross-layer 1NN     : 8 codes (4 down + 4 up)
 *   - In-plane diagonal 2NN: 4 codes (±x±y at √2*nn_d)
 *   - Axial 2NN           : 6 codes (±2nn_d in x/y, ±√2*nn_d in z)
 *   - Anchor (self)       : 1 code
 *   Total                 : 23 codes
 *
 * Lookup table semantics (built in lattice_build_coord_table):
 *   coord_table[site * N_NEIGHBOUR_CODES + nc] = neighbour_idx, or -1
 *   if `site` doesn't have that neighbour (e.g. surface sites have no
 *   `NC_NN1_UP_*` codes; bulk sites have all NN codes; PBC-thin slabs
 *   may have aliased ±z 2NN codes resolving to the same neighbour).
 *
 * The catalogue translator (pylatkmc/translator.py) emits Process
 * actions in terms of these codes; the codegen
 * (pylatkmc/decision_tree.py) emits C source that does
 *   coord_table[site * N_NEIGHBOUR_CODES + NC_<name>]
 * inline.
 */
typedef enum {
    NC_ANCHOR              = 0,    /* (0, 0, 0) — the site itself */

    /* In-plane axial 1NN (4): catalogue's surface_1NN_inplane and
     * subsurface_1NN_inplane families enumerate all four. */
    NC_NN1_PX,                     /* (+1, 0, 0) */
    NC_NN1_MX,                     /* (-1, 0, 0) */
    NC_NN1_PY,                     /* (0, +1, 0) */
    NC_NN1_MY,                     /* (0, -1, 0) */

    /* Cross-layer 1NN going DOWN (4): toward layer (k-1).
     * Cartesian delta (in nn_d units): (±0.5, ±0.5, -a/(2*nn_d))
     * = (±0.5, ±0.5, -1/√2) ≈ (±0.5, ±0.5, -0.707).
     * Used by surface_interlayer_hop, subsurface_interlayer_hop,
     * bulk_1NN_inplane (cross-layer subset). */
    NC_NN1_DOWN_PP,                /* (+0.5, +0.5, -0.707) */
    NC_NN1_DOWN_PM,                /* (+0.5, -0.5, -0.707) */
    NC_NN1_DOWN_MP,                /* (-0.5, +0.5, -0.707) */
    NC_NN1_DOWN_MM,                /* (-0.5, -0.5, -0.707) */

    /* Cross-layer 1NN going UP (4): toward layer (k+1).
     * Cartesian delta: (±0.5, ±0.5, +0.707). */
    NC_NN1_UP_PP,                  /* (+0.5, +0.5, +0.707) */
    NC_NN1_UP_PM,                  /* (+0.5, -0.5, +0.707) */
    NC_NN1_UP_MP,                  /* (-0.5, +0.5, +0.707) */
    NC_NN1_UP_MM,                  /* (-0.5, -0.5, +0.707) */

    /* In-plane diagonal 2NN (4): at (±1, ±1, 0) * nn_d.
     * Used by surface_2NN_diagonal, subsurface_2NN_diagonal. */
    NC_NN2_DIAG_PP,                /* (+1, +1, 0) */
    NC_NN2_DIAG_PM,                /* (+1, -1, 0) */
    NC_NN2_DIAG_MP,                /* (-1, +1, 0) */
    NC_NN2_DIAG_MM,                /* (-1, -1, 0) */

    /* Axial 2NN (6): used by surface_subsurface_exchange (z-axial 2NN
     * is the canonical exchange direction) and bulk_2NN_diagonal.
     * In thin slabs the ±z codes may PBC-alias to the same neighbour
     * — a known v0.2 limitation; the translator emits both codes
     * blindly and rely on Process-level dedup if it matters. */
    NC_NN2_PX,                     /* (+2, 0, 0) */
    NC_NN2_MX,                     /* (-2, 0, 0) */
    NC_NN2_PY,                     /* (0, +2, 0) */
    NC_NN2_MY,                     /* (0, -2, 0) */
    NC_NN2_PZ,                     /* (0, 0, +√2) — 2 layers up */
    NC_NN2_MZ,                     /* (0, 0, -√2) — 2 layers down */

    N_NEIGHBOUR_CODES              /* sentinel = 23 */
} NeighbourCode;

/* The canonical Cartesian delta (in nn_d units) for each NeighbourCode.
 * Defined in coord_codes.c so build_coord_table can iterate it. */
typedef struct {
    float dx, dy, dz;     /* in nn_d units; z uses 1/√2 ≈ 0.707 for cross-layer */
} CoordDelta;

extern const CoordDelta NEIGHBOUR_CODE_DELTAS[N_NEIGHBOUR_CODES];

/* Tolerance (in nn_d units) for matching a CSR edge's actual delta to
 * a canonical code delta. Small enough to discriminate ±0.5 from 0,
 * generous enough to accept f32 round-off. */
#define COORD_MATCH_TOL  0.05f

#endif /* PYLATKMC_COORD_CODES_H */
