/* coord_codes.c — canonical Cartesian deltas per NeighbourCode.
 *
 * The numeric values here ARE the contract: lattice_build_coord_table
 * compares each CSR edge's actual position-delta against these values
 * and assigns the matching code. Changing a delta here without
 * regenerating downstream tests will silently mis-route Processes.
 *
 * z-axis values use a/(2*nn_d) = 1/√2 ≈ 0.7071068 for cross-layer 1NN
 * (delta to next layer in (100) FCC) and √2 ≈ 1.4142136 for axial 2NN
 * (delta spanning 2 layers).
 *
 * For non-FCC lattices these constants would change; the slab
 * geometry (cell vectors, layer spacing) is implicit in build_coord_table
 * — for v0.2 we hardcode the (100) FCC convention. Generalise when we
 * add BCC/HCP support.
 */
#include "coord_codes.h"

/* 1/sqrt(2) and sqrt(2) literal constants. */
#define INVS2  0.70710678f
#define S2     1.41421356f

const CoordDelta NEIGHBOUR_CODE_DELTAS[N_NEIGHBOUR_CODES] = {
    [NC_ANCHOR]         = {  0.0f,  0.0f,   0.0f  },

    [NC_NN1_PX]         = { +1.0f,  0.0f,   0.0f  },
    [NC_NN1_MX]         = { -1.0f,  0.0f,   0.0f  },
    [NC_NN1_PY]         = {  0.0f, +1.0f,   0.0f  },
    [NC_NN1_MY]         = {  0.0f, -1.0f,   0.0f  },

    [NC_NN1_DOWN_PP]    = { +0.5f, +0.5f, -INVS2  },
    [NC_NN1_DOWN_PM]    = { +0.5f, -0.5f, -INVS2  },
    [NC_NN1_DOWN_MP]    = { -0.5f, +0.5f, -INVS2  },
    [NC_NN1_DOWN_MM]    = { -0.5f, -0.5f, -INVS2  },

    [NC_NN1_UP_PP]      = { +0.5f, +0.5f, +INVS2  },
    [NC_NN1_UP_PM]      = { +0.5f, -0.5f, +INVS2  },
    [NC_NN1_UP_MP]      = { -0.5f, +0.5f, +INVS2  },
    [NC_NN1_UP_MM]      = { -0.5f, -0.5f, +INVS2  },

    [NC_NN2_DIAG_PP]    = { +1.0f, +1.0f,   0.0f  },
    [NC_NN2_DIAG_PM]    = { +1.0f, -1.0f,   0.0f  },
    [NC_NN2_DIAG_MP]    = { -1.0f, +1.0f,   0.0f  },
    [NC_NN2_DIAG_MM]    = { -1.0f, -1.0f,   0.0f  },

    [NC_NN2_PX]         = { +2.0f,  0.0f,   0.0f  },
    [NC_NN2_MX]         = { -2.0f,  0.0f,   0.0f  },
    [NC_NN2_PY]         = {  0.0f, +2.0f,   0.0f  },
    [NC_NN2_MY]         = {  0.0f, -2.0f,   0.0f  },
    [NC_NN2_PZ]         = {  0.0f,  0.0f, +S2     },
    [NC_NN2_MZ]         = {  0.0f,  0.0f, -S2     },
};
