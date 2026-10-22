#ifndef PYLATKMC_ACTIVE_FILTER_H
#define PYLATKMC_ACTIVE_FILTER_H

#include <stdint.h>

#include "lattice.h"
#include "state.h"

/* Coordination-based active-site filter (port of pyKMC's atomic_environment
 * threshold; see `pyKMC-develop/pykmc/atomic_environment.py:31-67` and
 * `environments/coordination.py:4-26`).
 *
 * A site `s` is "active" — i.e. worth running the touchup decision tree at —
 * iff at least one of:
 *
 *   1. `species[s] == SP_VACANT`        (vacancies host outgoing events)
 *   2. some 1NN neighbour of s is vacant (s can be a hop *destination*)
 *   3. `nn1_degree[s] < bulk_threshold` (low-coord: surface / edge / corner)
 *
 * Bulk atoms with full 1NN coordination and no nearby vacancy will never
 * have any pattern-DB Process match (every condition's anchor needs at
 * least one Vacant or non-bulk feature) — so we save the wasted touchup
 * call.
 *
 * Layout
 * ------
 *
 *   is_active   : 1 byte per site, 1 = active
 *   active_list : packed list of active site indices, length n_active
 *   static_mask : precomputed bitmap of geometry-active sites (cond 3)
 *   static_list : the same sites, ascending (n_static of them)
 *
 * The static mask and list are computed once at lattice-load time. The
 * dynamic part is recomputed per step from the State's vacancy list and
 * the Lattice's 1NN CSR.
 *
 * Usage from the runtime:
 *
 *   active_filter_alloc(&af, lat->n_sites, BULK_NN1_DEGREE);
 *   active_filter_compute_static(af, lat);             // once at startup
 *
 *   for each KMC step:
 *       active_filter_rescan(af, lat, st);             // or _rescan_vacancies
 *       avail_sites_clear(as);
 *       for i in [0, active_filter_n_active(af)):
 *           touchup_a(active_filter_site_at(af, i));   // generated code
 *       avail_sites_refresh_cum_rates(as);
 *       avail_sites_select(as, ...);
 *
 * Order matters: touchup_a appends each enrolled site to its proc's
 * avail_sites list, and avail_sites_select picks a slot of that list, so
 * the order of the active list over the sites that enrol something decides
 * which event a random number selects. The rescan lists the static sites
 * in ascending site order, then walks st->vac_list: each vacancy, then its
 * 1NN in CSR order, every site at its first appearance only.
 */

typedef struct ActiveFilter ActiveFilter;

/* Allocate. Returns 0 on success; -EINVAL or -ENOMEM on failure.
 * `bulk_threshold` is the 1NN coordination at which a site stops being
 * considered "low-coord": for FCC bulk the degree is 12, so passing 12
 * means "every site below 12 nn1 is geometry-active". */
int  active_filter_alloc(ActiveFilter **out, int32_t n_sites,
                         int32_t bulk_threshold);
void active_filter_free(ActiveFilter *af);

/* Precompute the static (geometry-derived) active mask, and the ascending
 * list of its sites, from `lat`'s 1NN CSR. Idempotent. Returns 0; -EINVAL
 * on bad args; -ENOMEM (the filter is then unchanged). */
int  active_filter_compute_static(ActiveFilter *af, const Lattice *lat);

/* Full rescan: union of static_mask, vacant sites, and 1NN of vacant, in
 * the order described above. O(n_static + n_vac * <degree>) per call, plus
 * the previous call's n_active. */
void active_filter_rescan(ActiveFilter *af,
                          const Lattice *lat,
                          const State *st);

/* Vacancy-only rescan: the active list is exactly the vacant sites of the
 * list active_filter_rescan builds, in the same relative order: the static
 * vacancies by ascending site index, then the others at their first
 * appearance in the vac_list walk (a vacancy can first appear as the 1NN of
 * a vacancy ahead of it in vac_list). For a model whose Processes all
 * anchor on a vacancy (PYLATKMC_ANCHOR_SPECIES_MASK in the generated
 * proclist.h), touchup_a enrols nothing anywhere else, so touching up this
 * list builds the same avail_sites lists, slot for slot, as the full
 * rescan. Requires the State invariant that vac_list holds every vacant
 * site. O(n_vac * <degree>) plus a sort of the static vacancies; no pass
 * over the static sites. */
void active_filter_rescan_vacancies(ActiveFilter *af,
                                    const Lattice *lat,
                                    const State *st);

/* Manual marking (for incremental rebuild after an event).
 * `mark`: idempotently sets the site active and appends to active_list if
 *   it wasn't already there.
 * `unmark`: clears the bit and removes from active_list (O(1) via swap-last).
 * `clear_dynamic`: resets the active set to the static mask alone. */
void active_filter_mark           (ActiveFilter *af, int32_t site);
void active_filter_unmark         (ActiveFilter *af, int32_t site);
void active_filter_clear_dynamic  (ActiveFilter *af);

/* Iteration / introspection. */
int32_t active_filter_n_active   (const ActiveFilter *af);
int32_t active_filter_site_at    (const ActiveFilter *af, int32_t i);
int32_t active_filter_is_active  (const ActiveFilter *af, int32_t site);
int32_t active_filter_is_static  (const ActiveFilter *af, int32_t site);
int32_t active_filter_n_sites    (const ActiveFilter *af);
int32_t active_filter_bulk_thr   (const ActiveFilter *af);

#endif /* PYLATKMC_ACTIVE_FILTER_H */
