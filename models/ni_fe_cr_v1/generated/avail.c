/* avail.c — GENERATED for model 'ni_fe_cr_v1'.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build models/ni_fe_cr_v1.kmcspec.toml`.
 *
 * Per-step event enumeration. For each vacancy:
 *   1. scan_shell counts species in the 1NN and 2NN shells of the vacancy
 *   2. one Event is emitted per occupied neighbour, keyed on:
 *      site_class, direction, mover_species, n_vac_nn1, n_Fe_nn1, n_Cr_nn1, n_vac_nn2, n_Fe_nn2, n_Cr_nn2
 *   3. events are appended to the packed array; cum_rates tracks the
 *      running total for O(log N) binary-search selection later.
 *
 * M2 scope: full rebuild every step (same as latkmc v1). Incremental
 * add_proc/del_proc logic (kmos-style) is a future M6 candidate.
 */
#include "avail.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "events.h"
#include "lattice.h"
#include "state.h"
#include "ratetable.h"

/* SP_* code → mover_species axis index. Built from ModelSpec.species order
 * (minus 'Vacant' since a mover is never vacant). Out-of-range codes map
 * to 0 to keep the flat-cube lookup well-defined. */
static const uint8_t MOVER_SP_IDX[SP_COUNT] = {
    [SP_VACANT] = 0,
    [SP_NI] = 0,
    [SP_FE] = 1,
    [SP_CR] = 2,
};

int avail_alloc(AvailEvents *av, int32_t n_vac_max)
{
    if (!av || n_vac_max <= 0) return -EINVAL;
    memset(av, 0, sizeof(*av));
    av->n_vac_max = n_vac_max;
    size_t cap = (size_t)n_vac_max * AVAIL_MAX_EVENTS_PER_VAC;
    av->events    = malloc(cap * sizeof *av->events);
    av->cum_rates = calloc(cap,   sizeof *av->cum_rates);
    if (!av->events || !av->cum_rates) {
        avail_free(av);
        return -ENOMEM;
    }
    return 0;
}

void avail_free(AvailEvents *av)
{
    if (!av) return;
    free(av->events);      av->events    = NULL;
    free(av->cum_rates);   av->cum_rates = NULL;
    av->n_events  = 0;
    av->r_tot     = 0.0;
    av->n_vac_max = 0;
}

/* Per-shell scan: counts vacancies and each species of interest, and
 * stashes the edge indices of OCCUPIED neighbours for event emission. */
typedef struct ShellCounts {
    uint8_t n_vac;
    /* Extra per-species fields appear per shell via the scan_nn{1,2}() functions. */
} ShellCounts;

/* ---- nn1 shell scan ---- */
typedef struct ScanOut_nn1 {
    uint8_t n_vac;
    uint8_t n_Fe;
    uint8_t n_Cr;
    int32_t n_occ;
    int32_t occ_edges[AVAIL_MAX_EVENTS_PER_VAC];
} ScanOut_nn1;

static inline void scan_nn1(const Lattice *lat, const State *st,
                                 int32_t site, ScanOut_nn1 *out) {
    out->n_vac = 0;
    out->n_Fe = 0;
    out->n_Cr = 0;
    out->n_occ = 0;
    int32_t b = lat->nn1_offsets[site], e = lat->nn1_offsets[site + 1];
    for (int32_t k = b; k < e; ++k) {
        uint8_t sp = st->species[lat->nn1_indices[k]];
        if (sp == SP_VACANT) { out->n_vac++; }
        else if (sp == SP_FE) { out->n_Fe++; out->occ_edges[out->n_occ++] = k; }
        else if (sp == SP_CR) { out->n_Cr++; out->occ_edges[out->n_occ++] = k; }
        else { out->occ_edges[out->n_occ++] = k; }
    }
}

/* ---- nn2 shell scan ---- */
typedef struct ScanOut_nn2 {
    uint8_t n_vac;
    uint8_t n_Fe;
    uint8_t n_Cr;
    int32_t n_occ;
    int32_t occ_edges[AVAIL_MAX_EVENTS_PER_VAC];
} ScanOut_nn2;

static inline void scan_nn2(const Lattice *lat, const State *st,
                                 int32_t site, ScanOut_nn2 *out) {
    out->n_vac = 0;
    out->n_Fe = 0;
    out->n_Cr = 0;
    out->n_occ = 0;
    int32_t b = lat->nn2_offsets[site], e = lat->nn2_offsets[site + 1];
    for (int32_t k = b; k < e; ++k) {
        uint8_t sp = st->species[lat->nn2_indices[k]];
        if (sp == SP_VACANT) { out->n_vac++; }
        else if (sp == SP_FE) { out->n_Fe++; out->occ_edges[out->n_occ++] = k; }
        else if (sp == SP_CR) { out->n_Cr++; out->occ_edges[out->n_occ++] = k; }
        else { out->occ_edges[out->n_occ++] = k; }
    }
}

/* Clamp a count to the axis's configured max so ratetable_key stays in-bounds. */
static inline uint8_t clamp_max(uint8_t v, int32_t max_val) {
    int32_t cap = max_val - 1;
    if (cap < 0) cap = 0;
    return (v > (uint8_t)cap) ? (uint8_t)cap : v;
}

void avail_rebuild_all(AvailEvents *av,
                       const Lattice *lat, const State *st, const RateTable *rt)
{
    if (!av || !lat || !st || !rt) return;
    av->n_events = 0;
    av->r_tot    = 0.0;

    for (int32_t v = 0; v < st->n_vac; ++v) {
        int32_t s  = st->vac_list[v];
        uint8_t sc = lat->site_class[s];

        ScanOut_nn1 nn1 = {0};
        ScanOut_nn2 nn2 = {0};
        scan_nn1(lat, st, s, &nn1);
        scan_nn2(lat, st, s, &nn2);

        /* Emit one event per occupied 1NN edge. */
        for (int32_t i = 0; i < nn1.n_occ; ++i) {
            int32_t k    = nn1.occ_edges[i];
            int32_t t    = lat->nn1_indices[k];
            uint8_t dir  = lat->nn1_dir_family[k];
            uint8_t sp_t = st->species[t];

            RateKey key = {0};
            key.mover_species = MOVER_SP_IDX[sp_t];
            key.n_vac_nn1 = clamp_max(nn1.n_vac, rt->axis_maxes[3]);
            key.n_Fe_nn1 = clamp_max(nn1.n_Fe, rt->axis_maxes[4]);
            key.n_Cr_nn1 = clamp_max(nn1.n_Cr, rt->axis_maxes[5]);
            key.n_vac_nn2 = clamp_max(nn1.n_vac, rt->axis_maxes[6]);
            key.n_Fe_nn2 = clamp_max(nn2.n_Fe, rt->axis_maxes[7]);
            key.n_Cr_nn2 = clamp_max(nn2.n_Cr, rt->axis_maxes[8]);
            key.site_class = sc;
            key.direction  = dir;

            int32_t ki   = ratetable_key(rt, &key);
            double  rate = (double)rt->rate[ki];
            if (!isfinite(rate) || rate <= 0.0) continue;

            Event *ev = &av->events[av->n_events];
            ev->vac_origin = s;
            ev->vac_dest   = t;
            ev->motif      = (uint8_t)ratetable_motif(rt,
                                     (SiteClass)sc, (DirectionFamily)dir);
            ev->direction  = dir;
            ev->site_class = sc;
            ev->_pad0      = 0;
            ev->Ea_eV      = rt->Ea_eV[ki];
            ev->rate_s_inv = rate;
            ev->key        = key;
            av->r_tot += rate;
            av->cum_rates[av->n_events] = av->r_tot;
            av->n_events++;
        }

        /* And one per occupied 2NN edge. */
        for (int32_t i = 0; i < nn2.n_occ; ++i) {
            int32_t k    = nn2.occ_edges[i];
            int32_t t    = lat->nn2_indices[k];
            uint8_t dir  = lat->nn2_dir_family[k];
            uint8_t sp_t = st->species[t];

            RateKey key = {0};
            key.mover_species = MOVER_SP_IDX[sp_t];
            key.n_vac_nn1 = clamp_max(nn2.n_vac, rt->axis_maxes[3]);
            key.n_Fe_nn1 = clamp_max(nn1.n_Fe, rt->axis_maxes[4]);
            key.n_Cr_nn1 = clamp_max(nn1.n_Cr, rt->axis_maxes[5]);
            key.n_vac_nn2 = clamp_max(nn2.n_vac, rt->axis_maxes[6]);
            key.n_Fe_nn2 = clamp_max(nn2.n_Fe, rt->axis_maxes[7]);
            key.n_Cr_nn2 = clamp_max(nn2.n_Cr, rt->axis_maxes[8]);
            key.site_class = sc;
            key.direction  = dir;

            int32_t ki   = ratetable_key(rt, &key);
            double  rate = (double)rt->rate[ki];
            if (!isfinite(rate) || rate <= 0.0) continue;

            Event *ev = &av->events[av->n_events];
            ev->vac_origin = s;
            ev->vac_dest   = t;
            ev->motif      = (uint8_t)ratetable_motif(rt,
                                     (SiteClass)sc, (DirectionFamily)dir);
            ev->direction  = dir;
            ev->site_class = sc;
            ev->_pad0      = 0;
            ev->Ea_eV      = rt->Ea_eV[ki];
            ev->rate_s_inv = rate;
            ev->key        = key;
            av->r_tot += rate;
            av->cum_rates[av->n_events] = av->r_tot;
            av->n_events++;
        }
    }
}

int32_t avail_select(const AvailEvents *av, double target, const Event **out_ev)
{
    if (!av || av->n_events <= 0) { if (out_ev) *out_ev = NULL; return -1; }
    int32_t lo = 0, hi = av->n_events;
    while (lo < hi) {
        int32_t mid = lo + ((hi - lo) >> 1);
        if (av->cum_rates[mid] < target) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= av->n_events) lo = av->n_events - 1;
    if (out_ev) *out_ev = &av->events[lo];
    return lo;
}
