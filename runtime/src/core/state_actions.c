/* state_actions — multi-site Action application.
 *
 * Companion file to state.c. Kept separate so it can be tested in
 * isolation: the production state.c #includes events.h for SP_VACANT
 * (used by state_swap_vacancy), which is model-specific and would
 * couple unit tests to a generated header. state_apply_actions takes
 * the vacant-species byte as a parameter, so this .c is fully
 * self-contained and tests compile against it directly.
 *
 * Implements the M-C.5 semantics:
 *   1. Validate every action's `before` matches current species.
 *   2. Validate uniqueness of `site` across the action list.
 *   3. Validate that the post-apply n_vac stays in [0, n_vac_max].
 *   4. Mutate species[].
 *   5. Update vac_list[] / vac_idx_of[] for sites whose vacant-ness changed.
 *
 * On any validation failure, returns -EINVAL with no state mutation.
 *
 * We deliberately skip same-site dedup logic (it'd let one action's
 * `after` be the next action's `before`). Catalogue-derived Processes
 * always have unique action coords; the codegen guarantees this. The
 * uniqueness check here is a safety net.
 */

#include "state.h"

#include <errno.h>

int state_apply_actions(State *st,
                        const StateAction *actions,
                        int32_t n_actions,
                        uint8_t vacant_species)
{
    if (!st) return -EINVAL;
    if (n_actions < 0) return -EINVAL;
    if (n_actions == 0) return 0;
    if (!actions) return -EINVAL;

    /* --- Pass 1: validate each action's `before` and bounds. --- */
    for (int32_t i = 0; i < n_actions; ++i) {
        int32_t s = actions[i].site;
        if (s < 0) return -EINVAL;
        /* We don't have st->n_sites, but vac_idx_of[] is sized [n_sites].
         * The caller (codegen-emitted apply fn) is responsible for valid sites;
         * we accept the species[s] read as the bounds check. */
        if (st->species[s] != actions[i].before) return -EINVAL;
    }

    /* --- Pass 2: reject duplicate sites. O(n^2) is fine for n ≤ 4. --- */
    for (int32_t i = 0; i < n_actions; ++i) {
        for (int32_t j = i + 1; j < n_actions; ++j) {
            if (actions[i].site == actions[j].site) return -EINVAL;
        }
    }

    /* --- Pass 3: compute net vacancy delta and check overflow. --- */
    int32_t delta = 0;
    for (int32_t i = 0; i < n_actions; ++i) {
        int was_vac = (actions[i].before == vacant_species);
        int now_vac = (actions[i].after  == vacant_species);
        delta += now_vac - was_vac;
    }
    int32_t new_n_vac = st->n_vac + delta;
    if (new_n_vac < 0 || new_n_vac > st->n_vac_max) return -EINVAL;

    /* --- Pass 4: mutate species[]. --- */
    for (int32_t i = 0; i < n_actions; ++i) {
        st->species[actions[i].site] = actions[i].after;
    }

    /* --- Pass 5: update vac_list/vac_idx_of.
     *
     * Process *removals* before *additions* so that a hop event
     * (1 removal + 1 addition) doesn't transiently exceed n_vac_max
     * while building the new list. */
    for (int32_t i = 0; i < n_actions; ++i) {
        int was_vac = (actions[i].before == vacant_species);
        int now_vac = (actions[i].after  == vacant_species);
        if (was_vac && !now_vac) {
            int32_t s = actions[i].site;
            int32_t k = st->vac_idx_of[s];
            int32_t last = st->n_vac - 1;
            if (k != last) {
                int32_t moved = st->vac_list[last];
                st->vac_list[k] = moved;
                st->vac_idx_of[moved] = k;
            }
            st->vac_idx_of[s] = -1;
            st->n_vac = last;
        }
    }
    for (int32_t i = 0; i < n_actions; ++i) {
        int was_vac = (actions[i].before == vacant_species);
        int now_vac = (actions[i].after  == vacant_species);
        if (!was_vac && now_vac) {
            int32_t s = actions[i].site;
            int32_t k = st->n_vac;
            st->vac_list[k] = s;
            st->vac_idx_of[s] = k;
            st->n_vac = k + 1;
        }
    }

    return 0;
}
