#include "lattice.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

/* Lattice is populated by initconfig_load via a shared mmap. The mmap is
 * owned here; freeing releases it and clears all aliasing pointers.
 * coord_table is a separate heap allocation built by
 * lattice_build_coord_table; it is owned and freed here too. */

int lattice_load_kmcinit(Lattice *out, const char *path)
{
    /* Preserved for completeness; the main path is initconfig_load which also
     * populates a State. Delegating directly would force a dummy State, so we
     * leave this unimplemented for now. */
    (void)out; (void)path;
    return -ENOSYS;
}

void lattice_free(Lattice *l)
{
    if (!l) return;
    free(l->coord_table);
    l->coord_table = NULL;
    if (l->_mmap_base) {
        munmap(l->_mmap_base, l->_mmap_size);
    }
    l->_mmap_base    = NULL;
    l->_mmap_size    = 0;
    l->positions     = NULL;
    l->layer_index   = NULL;
    l->site_class    = NULL;
    l->nn1_offsets   = NULL;
    l->nn1_indices   = NULL;
    l->nn1_dir_family = NULL;
    l->nn2_offsets   = NULL;
    l->nn2_indices   = NULL;
    l->nn2_dir_family = NULL;
    l->n_sites = 0;
    l->n_layers = 0;
}

/* Min-image one-axis displacement: fold delta into [-L/2, L/2]. */
static inline float min_image1(float d, float L)
{
    if (d >  0.5f * L) return d - L;
    if (d < -0.5f * L) return d + L;
    return d;
}

/* Try to match a (dx, dy, dz) delta in nn_d units against every entry in
 * NEIGHBOUR_CODE_DELTAS. Returns the matching code, or -1 if no match
 * within COORD_MATCH_TOL. The anchor code (delta=0) is rejected here —
 * a CSR edge to ourselves shouldn't exist, and we never want to assign
 * NC_ANCHOR via match. */
static int match_code(float dx_n, float dy_n, float dz_n)
{
    /* Skip NC_ANCHOR (idx 0) — that's the self-edge and shouldn't appear in CSR. */
    for (int nc = 1; nc < N_NEIGHBOUR_CODES; ++nc) {
        const CoordDelta *cd = &NEIGHBOUR_CODE_DELTAS[nc];
        float ex = dx_n - cd->dx;
        float ey = dy_n - cd->dy;
        float ez = dz_n - cd->dz;
        if (fabsf(ex) < COORD_MATCH_TOL
         && fabsf(ey) < COORD_MATCH_TOL
         && fabsf(ez) < COORD_MATCH_TOL) {
            return nc;
        }
    }
    return -1;
}

int lattice_build_coord_table(Lattice *lat)
{
    if (!lat) return -EINVAL;
    if (lat->n_sites <= 0 || !lat->positions) return -EINVAL;
    if (!lat->nn1_offsets || !lat->nn1_indices) return -EINVAL;
    if (!lat->nn2_offsets || !lat->nn2_indices) return -EINVAL;
    if (lat->nn_dist <= 0.0f) return -EINVAL;

    size_t entries = (size_t)lat->n_sites * (size_t)N_NEIGHBOUR_CODES;
    int32_t *table = malloc(entries * sizeof *table);
    if (!table) return -ENOMEM;

    /* -1 everywhere by default; entries get filled in below. NC_ANCHOR
     * gets `site` written as a special case so caller can use it
     * uniformly. */
    for (size_t i = 0; i < entries; ++i) table[i] = -1;

    const float inv_nn = 1.0f / lat->nn_dist;
    const float Lx = lat->cell[0], Ly = lat->cell[1], Lz = lat->cell[2];

    for (int32_t s = 0; s < lat->n_sites; ++s) {
        size_t row = (size_t)s * (size_t)N_NEIGHBOUR_CODES;
        table[row + NC_ANCHOR] = s;

        const float sx = lat->positions[3 * s + 0];
        const float sy = lat->positions[3 * s + 1];
        const float sz = lat->positions[3 * s + 2];

        /* Walk 1NN edges. */
        int32_t b1 = lat->nn1_offsets[s];
        int32_t e1 = lat->nn1_offsets[s + 1];
        for (int32_t i = b1; i < e1; ++i) {
            int32_t n = lat->nn1_indices[i];
            float dx = min_image1(lat->positions[3 * n + 0] - sx, Lx) * inv_nn;
            float dy = min_image1(lat->positions[3 * n + 1] - sy, Ly) * inv_nn;
            float dz = min_image1(lat->positions[3 * n + 2] - sz, Lz) * inv_nn;
            int nc = match_code(dx, dy, dz);
            if (nc < 0) continue;  /* unrecognised direction — leave -1 */
            /* If two CSR edges PBC-alias to the same code (thin-slab case),
             * the first one wins; subsequent matches are silently dropped. */
            if (table[row + (size_t)nc] == -1) {
                table[row + (size_t)nc] = n;
            }
        }

        /* Walk 2NN edges. */
        int32_t b2 = lat->nn2_offsets[s];
        int32_t e2 = lat->nn2_offsets[s + 1];
        for (int32_t i = b2; i < e2; ++i) {
            int32_t n = lat->nn2_indices[i];
            float dx = min_image1(lat->positions[3 * n + 0] - sx, Lx) * inv_nn;
            float dy = min_image1(lat->positions[3 * n + 1] - sy, Ly) * inv_nn;
            float dz = min_image1(lat->positions[3 * n + 2] - sz, Lz) * inv_nn;
            int nc = match_code(dx, dy, dz);
            if (nc < 0) continue;
            if (table[row + (size_t)nc] == -1) {
                table[row + (size_t)nc] = n;
            }
        }
    }

    free(lat->coord_table);
    lat->coord_table = table;
    return 0;
}
