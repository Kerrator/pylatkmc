/* active_filter — coordination-based active-site gate.
 *
 * See active_filter.h for the design.
 */

#include "active_filter.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

struct ActiveFilter {
    int32_t  n_sites;
    int32_t  bulk_threshold;

    uint8_t *is_active;     /* [n_sites] 1 if active, 0 if not */
    uint8_t *static_mask;   /* [n_sites] 1 if geometry-active, immutable */

    int32_t *active_list;   /* [n_sites] packed indices (length = n_active) */
    int32_t  n_active;

    /* Reverse map: list_idx[s] = position of s in active_list, or -1.
     * Lets unmark be O(1) via swap-last. */
    int32_t *list_idx;
};

int active_filter_alloc(ActiveFilter **out, int32_t n_sites, int32_t bulk_threshold)
{
    if (!out || n_sites <= 0 || bulk_threshold < 0) return -EINVAL;
    *out = NULL;

    ActiveFilter *af = calloc(1, sizeof *af);
    if (!af) return -ENOMEM;

    af->n_sites        = n_sites;
    af->bulk_threshold = bulk_threshold;
    af->is_active      = calloc((size_t)n_sites, sizeof *af->is_active);
    af->static_mask    = calloc((size_t)n_sites, sizeof *af->static_mask);
    af->active_list    = malloc((size_t)n_sites * sizeof *af->active_list);
    af->list_idx       = malloc((size_t)n_sites * sizeof *af->list_idx);

    if (!af->is_active || !af->static_mask || !af->active_list || !af->list_idx) {
        active_filter_free(af);
        return -ENOMEM;
    }

    for (int32_t s = 0; s < n_sites; ++s) af->list_idx[s] = -1;
    af->n_active = 0;

    *out = af;
    return 0;
}

void active_filter_free(ActiveFilter *af)
{
    if (!af) return;
    free(af->is_active);
    free(af->static_mask);
    free(af->active_list);
    free(af->list_idx);
    free(af);
}

void active_filter_compute_static(ActiveFilter *af, const Lattice *lat)
{
    if (!af || !lat || !lat->nn1_offsets) return;
    for (int32_t s = 0; s < af->n_sites; ++s) {
        int32_t deg = lat->nn1_offsets[s + 1] - lat->nn1_offsets[s];
        af->static_mask[s] = (deg < af->bulk_threshold) ? 1 : 0;
    }
}

/* Internal: append `site` to active_list if not already present.
 * Caller is responsible for setting is_active[site] = 1 first. */
static inline void _append(ActiveFilter *af, int32_t site)
{
    if (af->list_idx[site] >= 0) return;
    af->list_idx[site] = af->n_active;
    af->active_list[af->n_active++] = site;
}

void active_filter_clear_dynamic(ActiveFilter *af)
{
    if (!af) return;
    /* Drop everything we accumulated and re-seed from static_mask. */
    for (int32_t i = 0; i < af->n_active; ++i) {
        int32_t s = af->active_list[i];
        af->is_active[s] = 0;
        af->list_idx[s] = -1;
    }
    af->n_active = 0;
    for (int32_t s = 0; s < af->n_sites; ++s) {
        if (af->static_mask[s]) {
            af->is_active[s] = 1;
            _append(af, s);
        }
    }
}

void active_filter_mark(ActiveFilter *af, int32_t site)
{
    if (!af || site < 0 || site >= af->n_sites) return;
    if (!af->is_active[site]) {
        af->is_active[site] = 1;
    }
    _append(af, site);
}

void active_filter_unmark(ActiveFilter *af, int32_t site)
{
    if (!af || site < 0 || site >= af->n_sites) return;
    if (!af->is_active[site]) return;
    af->is_active[site] = 0;

    int32_t idx = af->list_idx[site];
    if (idx < 0) return;  /* defensive: bitmap and list out of sync */
    int32_t last = af->n_active - 1;
    if (idx != last) {
        int32_t moved = af->active_list[last];
        af->active_list[idx] = moved;
        af->list_idx[moved] = idx;
    }
    af->list_idx[site] = -1;
    af->n_active = last;
}

void active_filter_rescan(ActiveFilter *af,
                          const Lattice *lat,
                          const State *st)
{
    if (!af) return;

    /* 1. Reset to static_mask. */
    active_filter_clear_dynamic(af);

    if (!lat || !st || st->n_vac <= 0
        || !st->vac_list || !lat->nn1_offsets || !lat->nn1_indices) {
        return;
    }

    /* 2. Mark every vacancy and its 1NN. */
    for (int32_t v = 0; v < st->n_vac; ++v) {
        int32_t s = st->vac_list[v];
        if (s < 0 || s >= af->n_sites) continue;
        active_filter_mark(af, s);
        for (int32_t i = lat->nn1_offsets[s]; i < lat->nn1_offsets[s + 1]; ++i) {
            active_filter_mark(af, lat->nn1_indices[i]);
        }
    }
}

int32_t active_filter_n_active(const ActiveFilter *af)
{
    return af ? af->n_active : 0;
}

int32_t active_filter_site_at(const ActiveFilter *af, int32_t i)
{
    if (!af || i < 0 || i >= af->n_active) return -1;
    return af->active_list[i];
}

int32_t active_filter_is_active(const ActiveFilter *af, int32_t site)
{
    if (!af || site < 0 || site >= af->n_sites) return 0;
    return af->is_active[site] ? 1 : 0;
}

int32_t active_filter_is_static(const ActiveFilter *af, int32_t site)
{
    if (!af || site < 0 || site >= af->n_sites) return 0;
    return af->static_mask[site] ? 1 : 0;
}

int32_t active_filter_n_sites (const ActiveFilter *af) { return af ? af->n_sites : 0; }
int32_t active_filter_bulk_thr(const ActiveFilter *af) { return af ? af->bulk_threshold : 0; }
