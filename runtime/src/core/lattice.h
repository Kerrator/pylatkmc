#ifndef LATKMC_LATTICE_H
#define LATKMC_LATTICE_H

#include <stdint.h>
#include <stddef.h>

#include "coord_codes.h"

/* Immutable lattice topology. Loaded once from .kmcinit, shared across
 * MPI replicas on a node via OS page cache. */
typedef struct Lattice {
    int32_t   n_sites;
    int32_t   n_layers;
    float     cell[3];              /* Lx, Ly, Lz in Å */
    float     nn_dist;              /* 1NN distance, e.g. 2.492 Å for Ni */

    float    *positions;            /* [n_sites * 3], packed xyz */
    int8_t   *layer_index;          /* [n_sites] 0 = bottom */
    uint8_t  *site_class;           /* [n_sites] SiteClass enum */

    /* CSR 1NN adjacency */
    int32_t  *nn1_offsets;          /* [n_sites + 1] */
    int32_t  *nn1_indices;          /* [nn1_offsets[n_sites]] */
    uint8_t  *nn1_dir_family;       /* [nn1_offsets[n_sites]] per-edge DF */

    /* CSR 2NN adjacency */
    int32_t  *nn2_offsets;          /* [n_sites + 1] */
    int32_t  *nn2_indices;          /* [nn2_offsets[n_sites]] */
    uint8_t  *nn2_dir_family;       /* [nn2_offsets[n_sites]] */

    /* Per-site neighbour-code lookup table.
     *   coord_table[site * N_NEIGHBOUR_CODES + nc] = neighbour idx, or -1.
     * Built once after lattice load by lattice_build_coord_table().
     * Heap-allocated; freed by lattice_free.
     * NULL until built. */
    int32_t  *coord_table;

    /* Integer site grid (v2 pattern matcher). In the runtime's [110]-in-plane
     * slab frame, FCC sites are the same-parity sublattice (u = v = w mod 2)
     * of a TETRAGONAL grid of spacing (nn_dist/2, nn_dist/2, nn_dist/sqrt2)
     * — the body-centred-tetragonal description of FCC. site_grid maps a
     * wrapped integer cell (u, v, w) to its site index, or to the stub index
     * n_sites for empty cells (off-sublattice, vacuum, out of slab).
     * site_ijk stores each site's integer cell (relative to site 0's cell)
     * so offsets resolve with pure integer arithmetic — this replaces
     * per-NeighbourCode coord_table growth for arbitrary-offset patterns.
     * Built by lattice_build_site_grid(); NULL until built; freed by
     * lattice_free. */
    int32_t  *site_grid;            /* [grid_nx * grid_ny * grid_nz] */
    int32_t   grid_nx, grid_ny, grid_nz;
    int16_t  *site_ijk;             /* [n_sites * 3] integer cell per site */

    /* mmap bookkeeping (opaque; zero when buffers are heap-allocated) */
    void    *_mmap_base;
    size_t   _mmap_size;
} Lattice;

int  lattice_load_kmcinit(Lattice *out, const char *path);
void lattice_free(Lattice *l);

/* Allocate and populate coord_table by walking each site's nn1/nn2 CSR
 * edges and matching their PBC-wrapped Cartesian deltas (in nn_d units)
 * against NEIGHBOUR_CODE_DELTAS within COORD_MATCH_TOL.
 *
 * Postcondition: every (site, nc) entry is either a valid neighbour
 * index in [0, n_sites) or -1 if the site has no neighbour at that
 * direction (e.g. surface sites have no NC_NN1_UP_*).
 *
 * Returns 0 on success, -EINVAL on bad input, -ENOMEM if alloc fails. */
int lattice_build_coord_table(Lattice *lat);

/* Allocate and populate site_grid + site_ijk from positions. Cell (i, j, k)
 * indices derive from round((pos - pos[site 0]) / h) with h = nn_dist/sqrt(2);
 * all three axes wrap modulo the grid dims. An offset into a slab's vacuum
 * gap resolves to the stub ("absent") ONLY while the gap is at least as
 * thick as the offset — past that, the wrap aliases the far surface. The
 * runtime enforces gap >= pattern reach at startup (replica.c, using
 * lattice_max_empty_axis_run below).
 *
 * Fails (-EINVAL) if two sites collide in one cell or if any site's cell has
 * odd parity relative to site 0 — both indicate a non-FCC or mis-scaled
 * config that the coord_table path would also mis-handle.
 *
 * Returns 0 on success, -EINVAL on bad input, -ENOMEM if alloc fails. */
int lattice_build_site_grid(Lattice *lat);

/* Longest cyclic run of grid planes perpendicular to `axis` (0 = i, 1 = j,
 * 2 = k) that contain no site — i.e. the vacuum-gap thickness in grid cells
 * (0 for a fully periodic axis). Requires the site grid to be built.
 * Returns the run length (>= 0), -EINVAL on bad input, -ENOMEM. */
int lattice_max_empty_axis_run(const Lattice *lat, int axis);

/* Resolve the site at integer cell (i, j, k) (relative to site 0's cell,
 * i.e. the same frame as site_ijk). All axes wrap. Returns the site index,
 * or the stub index n_sites for an empty cell (species[n_sites] = 255, so
 * species reads through the stub are self-sentineling). */
static inline int32_t lattice_site_at_ijk(const Lattice *lat,
                                          int32_t i, int32_t j, int32_t k)
{
    int32_t nx = lat->grid_nx, ny = lat->grid_ny, nz = lat->grid_nz;
    int32_t wi = (int32_t)(((i % nx) + nx) % nx);
    int32_t wj = (int32_t)(((j % ny) + ny) % ny);
    int32_t wk = (int32_t)(((k % nz) + nz) % nz);
    return lat->site_grid[((size_t)wi * (size_t)ny + (size_t)wj) * (size_t)nz
                          + (size_t)wk];
}

/* Resolve site + integer offset (di, dj, dk) in h units. */
static inline int32_t lattice_resolve_offset(const Lattice *lat, int32_t site,
                                             int32_t di, int32_t dj, int32_t dk)
{
    const int16_t *c = &lat->site_ijk[3 * site];
    return lattice_site_at_ijk(lat, (int32_t)c[0] + di, (int32_t)c[1] + dj,
                               (int32_t)c[2] + dk);
}

/* O(1) lookup. Returns -1 for invalid args or absent neighbour. */
static inline int32_t lattice_coord_at(const Lattice *lat, int32_t site,
                                        NeighbourCode nc)
{
    if (!lat || !lat->coord_table) return -1;
    if (site < 0 || site >= lat->n_sites) return -1;
    if ((int)nc < 0 || (int)nc >= N_NEIGHBOUR_CODES) return -1;
    return lat->coord_table[(size_t)site * N_NEIGHBOUR_CODES + (size_t)nc];
}

/* Iterate over 1NN of site s: for (int i = lattice_nn1_begin(l, s); i < lattice_nn1_end(l, s); ++i) {
 *     int32_t neighbor = l->nn1_indices[i];
 *     uint8_t dir      = l->nn1_dir_family[i];
 * }
 */
static inline int32_t lattice_nn1_begin(const Lattice *l, int32_t s) { return l->nn1_offsets[s];     }
static inline int32_t lattice_nn1_end  (const Lattice *l, int32_t s) { return l->nn1_offsets[s + 1]; }
static inline int32_t lattice_nn2_begin(const Lattice *l, int32_t s) { return l->nn2_offsets[s];     }
static inline int32_t lattice_nn2_end  (const Lattice *l, int32_t s) { return l->nn2_offsets[s + 1]; }

#endif /* LATKMC_LATTICE_H */
