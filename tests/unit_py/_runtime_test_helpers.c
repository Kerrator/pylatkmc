/* _runtime_test_helpers — tiny C shims for ctypes-based runtime tests.
 *
 * The runtime data structures (`Lattice`, `State`) are non-trivial to
 * construct directly from Python: the production loaders read .kmcinit
 * files, allocate via state_alloc(), and so on. For unit tests of
 * downstream modules (active_filter, eventually state_apply_actions), we
 * just need to populate a few fields without going through the full
 * runtime startup path.
 *
 * This file exposes minimal builders that:
 *   - malloc a Lattice / State struct
 *   - copy in just the fields the module under test reads
 *   - leave everything else NULL / 0
 *   - provide matching free functions
 *
 * Test code (Python via ctypes) drives these to assemble small
 * synthetic systems (e.g. linear chain, FCC fragment) without doing
 * file I/O. The structs returned are real `Lattice` and `State`
 * pointers, so the tested API is exercised against the production
 * struct layout.
 *
 * NOT a production component. Lives in tests/ to make that clear.
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "lattice.h"
#include "state.h"

/* Forward declarations so builders can call free() on error paths. */
void pylatkmc_test_free_lattice(Lattice *lat);
void pylatkmc_test_free_state(State *st);

/* Build a minimal Lattice. The earliest test (test_active_filter) only
 * needs nn1_offsets/nn1_indices populated, but later tests
 * (test_coord_table) need the full geometry: positions, cell, nn_dist,
 * AND nn2 CSR so lattice_build_coord_table can walk both shells.
 *
 * We provide ONE builder with optional inputs:
 *   - if positions is NULL, lat->positions stays NULL (caller can skip
 *     functions that need it)
 *   - if nn2_offsets is NULL, lat->nn2_offsets/nn2_indices stay NULL
 *
 * Inputs are int32_t / float arrays; we malloc-and-copy so the
 * Python-side arrays can go out of scope without dangling.
 *
 * Returns a malloc'd Lattice* that the caller must free via
 * pylatkmc_test_free_lattice(). */
Lattice *pylatkmc_test_make_lattice_full(int32_t n_sites,
                                         const float   *positions,    /* [n_sites*3] or NULL */
                                         const float   *cell,         /* [3] or NULL */
                                         float          nn_dist,
                                         const int32_t *nn1_offsets,
                                         const int32_t *nn1_indices,
                                         const int32_t *nn2_offsets,  /* or NULL */
                                         const int32_t *nn2_indices)
{
    if (n_sites <= 0 || !nn1_offsets || !nn1_indices) return NULL;
    Lattice *lat = calloc(1, sizeof *lat);
    if (!lat) return NULL;

    lat->n_sites = n_sites;
    lat->nn_dist = nn_dist;
    if (cell) {
        lat->cell[0] = cell[0]; lat->cell[1] = cell[1]; lat->cell[2] = cell[2];
    }

    if (positions) {
        size_t pos_bytes = (size_t)n_sites * 3 * sizeof(float);
        lat->positions = malloc(pos_bytes);
        if (!lat->positions) { free(lat); return NULL; }
        memcpy(lat->positions, positions, pos_bytes);
    }

    size_t off_bytes = (size_t)(n_sites + 1) * sizeof(int32_t);
    lat->nn1_offsets = malloc(off_bytes);
    if (!lat->nn1_offsets) { pylatkmc_test_free_lattice(lat); return NULL; }
    memcpy(lat->nn1_offsets, nn1_offsets, off_bytes);

    int32_t M1 = nn1_offsets[n_sites];
    if (M1 < 0) { pylatkmc_test_free_lattice(lat); return NULL; }
    if (M1 > 0) {
        size_t idx_bytes = (size_t)M1 * sizeof(int32_t);
        lat->nn1_indices = malloc(idx_bytes);
        if (!lat->nn1_indices) { pylatkmc_test_free_lattice(lat); return NULL; }
        memcpy(lat->nn1_indices, nn1_indices, idx_bytes);
    }

    if (nn2_offsets) {
        lat->nn2_offsets = malloc(off_bytes);
        if (!lat->nn2_offsets) { pylatkmc_test_free_lattice(lat); return NULL; }
        memcpy(lat->nn2_offsets, nn2_offsets, off_bytes);
        int32_t M2 = nn2_offsets[n_sites];
        if (M2 > 0 && nn2_indices) {
            size_t idx_bytes = (size_t)M2 * sizeof(int32_t);
            lat->nn2_indices = malloc(idx_bytes);
            if (!lat->nn2_indices) { pylatkmc_test_free_lattice(lat); return NULL; }
            memcpy(lat->nn2_indices, nn2_indices, idx_bytes);
        }
    }

    return lat;
}

/* Convenience wrapper: backwards-compatible 1NN-only builder. */
Lattice *pylatkmc_test_make_lattice(int32_t n_sites,
                                    const int32_t *nn1_offsets,
                                    const int32_t *nn1_indices)
{
    return pylatkmc_test_make_lattice_full(
        n_sites,
        /*positions=*/NULL, /*cell=*/NULL, /*nn_dist=*/0.0f,
        nn1_offsets, nn1_indices,
        /*nn2_offsets=*/NULL, /*nn2_indices=*/NULL);
}

void pylatkmc_test_free_lattice(Lattice *lat)
{
    if (!lat) return;
    free(lat->positions);
    free(lat->nn1_offsets);
    free(lat->nn1_indices);
    free(lat->nn2_offsets);
    free(lat->nn2_indices);
    free(lat->coord_table);
    free(lat);
}

/* Build a minimal State. Populates:
 *   - n_vac, n_vac_max
 *   - vac_list  (copied)
 *   - vac_idx_of (synthesised: -1 everywhere except enrolled vacancies)
 *   - species   (zero-initialised; caller can set after if needed)
 *
 * Caller can optionally pass `species_init` (length n_sites) to
 * pre-fill the species array. Pass NULL to leave it zero (which is
 * SP_VACANT in the model's enum convention).
 *
 * Returns a malloc'd State* that the caller must free via
 * pylatkmc_test_free_state(). */
State *pylatkmc_test_make_state(int32_t n_sites,
                                int32_t n_vac_max,
                                int32_t n_vac,
                                const int32_t *vac_list,
                                const uint8_t *species_init)
{
    if (n_sites <= 0 || n_vac_max < 0 || n_vac < 0 || n_vac > n_vac_max) return NULL;
    if (n_vac > 0 && !vac_list) return NULL;

    State *st = calloc(1, sizeof *st);
    if (!st) return NULL;

    st->n_vac = n_vac;
    st->n_vac_max = n_vac_max;
    st->time_s = 0.0;
    st->step = 0;

    st->species = calloc((size_t)n_sites, sizeof *st->species);
    st->vac_idx_of = malloc((size_t)n_sites * sizeof *st->vac_idx_of);
    /* Even with n_vac_max == 0, vac_list is given length 1 just so
     * malloc returns non-NULL; otherwise allocate n_vac_max. */
    size_t vac_alloc = (size_t)(n_vac_max > 0 ? n_vac_max : 1);
    st->vac_list = malloc(vac_alloc * sizeof *st->vac_list);
    st->unwrapped_xyz = calloc(vac_alloc * 3, sizeof *st->unwrapped_xyz);

    if (!st->species || !st->vac_idx_of || !st->vac_list || !st->unwrapped_xyz) {
        pylatkmc_test_free_state(st);
        return NULL;
    }

    if (species_init) {
        memcpy(st->species, species_init, (size_t)n_sites * sizeof *st->species);
    }

    /* Initialise vac_idx_of to -1 everywhere, then enrol the given vacancies. */
    for (int32_t s = 0; s < n_sites; ++s) st->vac_idx_of[s] = -1;
    for (int32_t v = 0; v < n_vac; ++v) {
        int32_t s = vac_list[v];
        if (s < 0 || s >= n_sites) {
            pylatkmc_test_free_state(st);
            return NULL;
        }
        st->vac_list[v] = s;
        st->vac_idx_of[s] = v;
    }
    return st;
}

void pylatkmc_test_free_state(State *st)
{
    if (!st) return;
    free(st->species);
    free(st->vac_idx_of);
    free(st->vac_list);
    free(st->unwrapped_xyz);
    free(st);
}

/* Read-only accessors so Python can verify the structs were built right. */
int32_t pylatkmc_test_lattice_n_sites(const Lattice *lat)
{
    return lat ? lat->n_sites : -1;
}

int32_t pylatkmc_test_lattice_nn1_degree(const Lattice *lat, int32_t site)
{
    if (!lat || !lat->nn1_offsets) return -1;
    if (site < 0 || site >= lat->n_sites) return -1;
    return lat->nn1_offsets[site + 1] - lat->nn1_offsets[site];
}

int32_t pylatkmc_test_state_n_vac(const State *st)
{
    return st ? st->n_vac : -1;
}
