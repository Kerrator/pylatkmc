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
    free(l->site_grid);
    l->site_grid = NULL;
    free(l->site_ijk);
    l->site_ijk = NULL;
    l->grid_nx = l->grid_ny = l->grid_nz = 0;
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

int lattice_build_site_grid(Lattice *lat)
{
    if (!lat) return -EINVAL;
    if (lat->n_sites <= 0 || !lat->positions) return -EINVAL;
    if (lat->nn_dist <= 0.0f) return -EINVAL;

    /* The runtime's FCC (100) slab frame has its in-plane axes along the
     * crystal [110] directions (in-plane 1NN at (+-nn_d, 0, 0) — see
     * coord_codes.h), NOT along the cube axes. In this frame the sites form
     * the same-parity sublattice (u = v = w mod 2) of a TETRAGONAL grid:
     *
     *   spacing (hx, hy, hz) = (nn_d/2, nn_d/2, nn_d/sqrt(2))
     *
     * (the body-centred-tetragonal description of FCC). The pattern
     * translator emits offsets in these cells via the integer frame map
     * (u, v, w) = (i+j, j-i, k) from the ingest crystal-frame a/2 offsets. */
    const double hx = (double)lat->nn_dist / 2.0;
    const double hy = hx;
    const double hz = (double)lat->nn_dist / 1.4142135623730951;
    int32_t nx = (int32_t)lround((double)lat->cell[0] / hx);
    int32_t ny = (int32_t)lround((double)lat->cell[1] / hy);
    int32_t nz = (int32_t)lround((double)lat->cell[2] / hz);
    if (nx < 1) nx = 1;
    if (ny < 1) ny = 1;
    if (nz < 1) nz = 1;

    size_t n_cells = (size_t)nx * (size_t)ny * (size_t)nz;
    int32_t *grid = malloc(n_cells * sizeof *grid);
    int16_t *ijk  = malloc((size_t)lat->n_sites * 3 * sizeof *ijk);
    if (!grid || !ijk) {
        free(grid);
        free(ijk);
        return -ENOMEM;
    }
    const int32_t stub = lat->n_sites;
    for (size_t c = 0; c < n_cells; ++c) grid[c] = stub;

    const double x0 = lat->positions[0];
    const double y0 = lat->positions[1];
    const double z0 = lat->positions[2];

    for (int32_t s = 0; s < lat->n_sites; ++s) {
        double ui = ((double)lat->positions[3 * s + 0] - x0) / hx;
        double uj = ((double)lat->positions[3 * s + 1] - y0) / hy;
        double uk = ((double)lat->positions[3 * s + 2] - z0) / hz;
        long ri = lround(ui), rj = lround(uj), rk = lround(uk);
        /* Sites must sit on the grid (kmcinit configs are ideal-lattice). */
        if (fabs(ui - (double)ri) > 0.25 || fabs(uj - (double)rj) > 0.25
         || fabs(uk - (double)rk) > 0.25) {
            free(grid); free(ijk);
            return -EINVAL;    /* off-grid position: not an ideal FCC config */
        }
        /* Same-parity constraint u = v = w (mod 2), relative to site 0
         * (checked before wrapping so an odd wrapped dimension cannot mask a
         * genuine violation). */
        if (((ri ^ rj) & 1L) != 0 || ((rj ^ rk) & 1L) != 0) {
            free(grid); free(ijk);
            return -EINVAL;    /* off-sublattice site: not FCC in this frame */
        }
        if (ri < INT16_MIN || ri > INT16_MAX || rj < INT16_MIN || rj > INT16_MAX
         || rk < INT16_MIN || rk > INT16_MAX) {
            free(grid); free(ijk);
            return -EINVAL;
        }
        ijk[3 * s + 0] = (int16_t)ri;
        ijk[3 * s + 1] = (int16_t)rj;
        ijk[3 * s + 2] = (int16_t)rk;
        int32_t wi = (int32_t)(((ri % nx) + nx) % nx);
        int32_t wj = (int32_t)(((rj % ny) + ny) % ny);
        int32_t wk = (int32_t)(((rk % nz) + nz) % nz);
        size_t cell = ((size_t)wi * (size_t)ny + (size_t)wj) * (size_t)nz
                      + (size_t)wk;
        if (grid[cell] != stub) {
            free(grid); free(ijk);
            return -EINVAL;    /* two sites in one cell: mis-scaled config */
        }
        grid[cell] = s;
    }

    free(lat->site_grid);
    free(lat->site_ijk);
    lat->site_grid = grid;
    lat->site_ijk  = ijk;
    lat->grid_nx = nx;
    lat->grid_ny = ny;
    lat->grid_nz = nz;
    return 0;
}

int lattice_max_empty_axis_run(const Lattice *lat, int axis)
{
    if (!lat || !lat->site_grid || !lat->site_ijk) return -EINVAL;
    if (axis < 0 || axis > 2) return -EINVAL;
    int32_t dim = (axis == 0) ? lat->grid_nx
                : (axis == 1) ? lat->grid_ny
                              : lat->grid_nz;
    if (dim <= 0) return -EINVAL;

    unsigned char *occupied = calloc((size_t)dim, sizeof *occupied);
    if (!occupied) return -ENOMEM;
    for (int32_t s = 0; s < lat->n_sites; ++s) {
        long v = (long)lat->site_ijk[3 * s + axis] % dim;
        if (v < 0) v += dim;
        occupied[v] = 1;
    }
    /* Longest cyclic run of empty planes: two passes with the counter kept
     * across the seam so a run wrapping the boundary is counted whole. */
    int best = 0, cur = 0;
    for (int pass = 0; pass < 2; ++pass) {
        for (int32_t p = 0; p < dim; ++p) {
            if (occupied[p]) {
                cur = 0;
            } else if (++cur > best) {
                best = cur;
            }
        }
    }
    free(occupied);
    return (best > (int)dim) ? (int)dim : best;
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

    /* Initialise to the "stub site" index n_sites for every entry; real
     * neighbours overwrite below. The State allocator places a sentinel
     * value (255) at species[n_sites] so the decision tree's species
     * reads fall through default for every direction that isn't a real
     * neighbour (e.g. NC_NN1_UP_* on a top-surface site). This avoids a
     * `species[-1]` segfault that would otherwise occur for surface or
     * edge sites whose coord_table entry was -1. */
    int32_t stub = lat->n_sites;
    for (size_t i = 0; i < entries; ++i) table[i] = stub;

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
            if (nc < 0) continue;  /* unrecognised direction — leave stub */
            /* If two CSR edges PBC-alias to the same code (thin-slab case),
             * the first one wins; subsequent matches are silently dropped. */
            if (table[row + (size_t)nc] == stub) {
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
            if (table[row + (size_t)nc] == stub) {
                table[row + (size_t)nc] = n;
            }
        }
    }

    free(lat->coord_table);
    lat->coord_table = table;
    return 0;
}
