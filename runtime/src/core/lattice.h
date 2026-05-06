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
