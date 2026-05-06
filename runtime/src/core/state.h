#ifndef LATKMC_STATE_H
#define LATKMC_STATE_H

#include <stdint.h>
#include "lattice.h"

/* Mutable per-replica simulation state. Kept synchronised as a triple:
 *   species[s]   = SP_VACANT iff s is vacant
 *   vac_list     = dense list of vacant site ids, length n_vac
 *   vac_idx_of[s] = index in vac_list, or -1 if site is occupied
 * All three are updated atomically after each accepted event. */
typedef struct State {
    uint8_t  *species;              /* [n_sites] */
    int32_t  *vac_list;             /* [n_vac_max] */
    int32_t  *vac_idx_of;           /* [n_sites]; -1 if occupied */
    int32_t   n_vac;
    int32_t   n_vac_max;

    double    time_s;
    uint64_t  step;

    /* Unwrapped cumulative displacement per vacancy for MSD, in Ångström.
     * [n_vac_max * 3], indexed by the vacancy's current position in vac_list.
     * Updated by the caller using minimum-image displacement at each hop. */
    double   *unwrapped_xyz;

    /* Per-event-family counters for summary.json. */
    uint64_t  motif_counts[8];      /* MF_COUNT; fixed for ABI stability */
    uint64_t  direction_counts[5];  /* DF_COUNT */
} State;

int  state_alloc(State *st, int32_t n_sites, int32_t n_vac_max);
void state_free(State *st);

/* Swap species at two sites and keep the triple in sync.
 * Exactly one of (a, b) must be vacant before the call; the vacancy moves from
 * the vacant site to the other site. */
void state_swap_vacancy(State *st, int32_t a, int32_t b);

/* ---- Multi-site Action application (pylatkmc v2) ----
 *
 * StateAction records one mutation in a Process's `actions` list:
 *   - site:   absolute site index (caller resolves coord-offsets first)
 *   - before: species expected at site BEFORE the mutation (validation)
 *   - after:  species written to site
 *
 * Atomic across the whole list: either every action validates and applies,
 * or nothing is mutated and -EINVAL is returned. */
typedef struct StateAction {
    int32_t site;
    uint8_t before;
    uint8_t after;
} StateAction;

/* Apply a list of actions to `st` atomically.
 *
 * Returns 0 on success.
 * Returns -EINVAL on any of:
 *   - a NULL/invalid argument
 *   - duplicate site across actions (rejected; v0.2 simplification)
 *   - site out of range
 *   - any action's `before` doesn't match current species
 *   - the post-apply n_vac would exceed n_vac_max (or go negative)
 *
 * Side effects on success:
 *   - st->species[site] = after for every action
 *   - vac_list[]/vac_idx_of[] updated for any site whose vacant-ness changed
 *     (where "vacant" = `vacant_species`). Removals use swap-last; additions
 *     append. n_vac is updated accordingly.
 *
 * Does NOT touch st->unwrapped_xyz: MSD-tracking displacement is the
 * caller's responsibility (kmc.c apply_event reads the Process's hop
 * geometry to compute it). The slot in unwrapped_xyz that corresponds
 * to a removed vacancy may carry stale data; the slot for a newly-added
 * vacancy is left as-is by this function. */
int state_apply_actions(State *st,
                        const StateAction *actions,
                        int32_t n_actions,
                        uint8_t vacant_species);

#endif /* LATKMC_STATE_H */
