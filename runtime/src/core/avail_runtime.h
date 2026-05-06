/* avail_runtime.h — runtime's view of the available-events interface.
 *
 * The actual implementation (scan_shell, avail_rebuild_all) is GENERATED
 * per-model and lives in models/<name>/generated/avail.c. The runtime
 * backbone (kmc.c, main.c) only sees the interface declared here.
 *
 * The Event type itself is also model-specific (species counts per shell
 * differ between models). kmc.c and main.c operate on forward-declared
 * pointers — they never dereference Event directly, only pass it through
 * to pykmc_out.c (whose writer is also generated per model).
 *
 * pylatkmc M1 scaffolding (2026-04-19).
 */
#ifndef PYLATKMC_AVAIL_RUNTIME_H
#define PYLATKMC_AVAIL_RUNTIME_H

#include <stdint.h>
#include "events_base.h"  /* Species, SiteClass, DirectionFamily */

/* Forward declarations — the generated events.h completes Event's layout. */
struct Event;
struct Lattice;
struct State;
struct RateTable;

/* Incrementally packed event list. Dense, no gaps. */
typedef struct AvailEvents AvailEvents;

int  avail_alloc(AvailEvents **out_av, int32_t n_vac_max);
void avail_free(AvailEvents *av);

/* Rebuild events[] and cum_rates[] from scratch. O(n_vac * K). */
void avail_rebuild_all(AvailEvents *av,
                       const struct Lattice    *lat,
                       const struct State      *st,
                       const struct RateTable  *rt);

/* Binary-search select: returns dense index in events[], with target
 * in [0, r_tot). Writes the selected Event pointer through *out_ev.
 * Returns -1 if n_events == 0. */
int32_t avail_select(const AvailEvents *av, double target,
                     const struct Event **out_ev);

/* Totals accessors (the generated struct is opaque to the runtime). */
int32_t avail_n_events(const AvailEvents *av);
double  avail_r_tot   (const AvailEvents *av);

#endif /* PYLATKMC_AVAIL_RUNTIME_H */
