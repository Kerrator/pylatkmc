#ifndef LATKMC_LATTICE_H
#define LATKMC_LATTICE_H

#include <stdint.h>
#include <stddef.h>

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

    /* mmap bookkeeping (opaque; zero when buffers are heap-allocated) */
    void    *_mmap_base;
    size_t   _mmap_size;
} Lattice;

int  lattice_load_kmcinit(Lattice *out, const char *path);
void lattice_free(Lattice *l);

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
