#ifndef PYLATKMC_AVAIL_H
#define PYLATKMC_AVAIL_H

#include <stdint.h>
#include "events.h"
#include "state.h"
#include "lattice.h"
#include "ratetable.h"

/* Available-events index.
 *
 * M1: rebuild the full dense events[] array every step (no dirty-bit logic).
 * At ≤ n_vac * 18 events per step and ~100 ns/event, this is << 100 µs/step
 * even at 100 vacancies. Incremental updates ship in M5.
 *
 * Layout: events[] is packed dense (no gaps). cum_rates[] is a parallel
 * running sum so that avail_select() can binary-search. */

enum { AVAIL_MAX_EVENTS_PER_VAC = 18 };  /* 12 1NN + 6 2NN for FCC bulk */

typedef struct {
    Event    *events;       /* [n_vac_max * K], dense */
    double   *cum_rates;    /* parallel to events */
    int32_t   n_events;     /* populated count */
    double    r_tot;        /* cum_rates[n_events - 1] if n_events > 0, else 0 */
    int32_t   n_vac_max;
} AvailEvents;

int  avail_alloc(AvailEvents *av, int32_t n_vac_max);
void avail_free(AvailEvents *av);

/* Rebuild events[] and cum_rates[] from scratch. O(n_vac * K). */
void avail_rebuild_all(AvailEvents *av,
                       const Lattice *lat, const State *st, const RateTable *rt);

/* Binary-search select: returns dense index in events[], with target ∈ [0, r_tot).
 * Writes the selected Event pointer through *out_ev. Returns -1 if n_events==0. */
int32_t avail_select(const AvailEvents *av, double target, const Event **out_ev);

#endif /* PYLATKMC_AVAIL_H */
