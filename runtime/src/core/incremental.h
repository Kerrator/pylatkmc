#ifndef PYLATKMC_INCREMENTAL_H
#define PYLATKMC_INCREMENTAL_H

#include <stdint.h>

#include "active_filter.h"
#include "avail_sites.h"
#include "lattice.h"
#include "state.h"

/* Incremental active-set rebuild (PYLATKMC_INCREMENTAL builds).
 *
 * The static reach of an anchor a is every site whose species can change what
 * is enrolled at a:
 *
 *   {a} + nn1(a) + {coord(a, X) for X in READ} + nn1(coord(a, X)) for X in SHELL
 *
 * READ and SHELL come from pt_reach_template.h, which CMake derives from the
 * model's touchup_a (tools/gen_reach_template.py). The context holds the
 * inverse: for each site c, the anchors whose reach contains c.
 *
 * A step from the changed-site set (changed_sites.h):
 *
 *   1. update the local active set on the changed sites and their nn1
 *   2. K = union of the inverse reach over the changed sites
 *   3. delete every enrolment at each anchor in K
 *   4. touchup_a each active anchor in K
 *
 * That leaves the same (process, site) pairs as a full rebuild; their order
 * within a process may differ. PYLATKMC_REPLAY_ORDER restores the full-rebuild
 * traversal order for the selected process. Species updates must go through
 * state_apply_actions or state_swap_vacancy to reach the update list.
 *
 * The functions exist only in incremental builds. */

#if defined(PYLATKMC_REPLAY_ORDER) && !defined(PYLATKMC_INCREMENTAL)
#error "PYLATKMC_REPLAY_ORDER needs PYLATKMC_INCREMENTAL"
#endif

#if defined(PYLATKMC_INCREMENTAL_ORACLE) && !defined(PYLATKMC_INCREMENTAL)
#error "PYLATKMC_INCREMENTAL_ORACLE needs PYLATKMC_INCREMENTAL"
#endif

typedef struct Incremental Incremental;

/* Allocate and build the inverse reach. Needs lat->coord_table. Returns 0;
 * -ENOMEM; or -EINVAL on bad args or a 1NN list that is not symmetric (then
 * nn1(a) would not list every vacancy that can make a active). */
int  incremental_create(Incremental **out, const Lattice *lat);
void incremental_free(Incremental *inc);

/* The first step's stages 1-3: a full rescan and rebuild, then the local
 * active set and the inverse reach. Creates *out; returns incremental_create's
 * codes. After this, the active filter is only read for its static mask. */
int incremental_start(Incremental **out, const Lattice *lat, const State *st,
                      AvailSites *as, ActiveFilter *af);

/* A later step's stages 1-3 (the four numbered above), from st->changed, for
 * the caller to clear afterwards. avail_sites_refresh_cum_rates still follows. */
void incremental_update(Incremental *inc, const Lattice *lat, const State *st,
                        AvailSites *as, const ActiveFilter *af);

/* The anchors whose reach contains `site`: returns their number and points
 * *out at them, each once, ascending. */
int32_t incremental_inverse_reach(const Incremental *inc, int32_t site, const int32_t **out);

#ifdef PYLATKMC_REPLAY_ORDER
/* Remap the unordered selection to the same slot in the legacy traversal. */
int incremental_replay_site(Incremental *inc, const Lattice *lat, const State *st,
                            const ActiveFilter *af, const AvailSites *as,
                            int32_t proc, int32_t *site);
#endif

#ifdef PYLATKMC_INCREMENTAL_ORACLE

/* A build value, not an INI key: check on every step whose number (0-based)
 * is a multiple of this, and on any step whose table came out empty. The
 * check at step 0 compares one full build with another, so it tests nothing
 * incremental. CMake sets the value from its cache variable. */
#ifndef PYLATKMC_ORACLE_EVERY
#define PYLATKMC_ORACLE_EVERY 1
#endif

/* Debug check, run after the update and before the RNG draws: build a separate
 * full table and compare the sorted (process, site) pairs, the active set and
 * r_tot with the live ones. The live table, the RNG and the state are never
 * written, so an oracle build runs the on-build's trajectory. The second
 * table has the same dimensions as the live one.
 *
 * Returns 0; -EILSEQ on a mismatch, after printing the step and the first
 * missing and first extra pair to stderr; -ENOMEM. */
int incremental_oracle(Incremental *inc, const Lattice *lat, const State *st,
                       const AvailSites *as, ActiveFilter *af);

/* Counters for summary.json; 0 for a NULL inc (no step was run). */
uint64_t incremental_oracle_checks  (const Incremental *inc);
uint64_t incremental_oracle_failures(const Incremental *inc);

#endif /* PYLATKMC_INCREMENTAL_ORACLE */

#endif /* PYLATKMC_INCREMENTAL_H */
