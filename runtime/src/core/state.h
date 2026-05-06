#ifndef LATKMC_STATE_H
#define LATKMC_STATE_H

#include <stdint.h>
#include "lattice.h"

/* Mutable per-replica simulation state. Kept synchronised as a triple:
 *   species[s]   = SP_VACANT iff s is vacant
 *   vac_list     = dense list of vacant site ids, length n_vac
 *   vac_idx_of[s] = index in vac_list, or -1 if site is occupied
 * All three are updated atomically after each accepted event. */
typedef struct {
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

#endif /* LATKMC_STATE_H */
