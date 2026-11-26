#ifndef PYLATKMC_CHANGED_SITES_H
#define PYLATKMC_CHANGED_SITES_H

#include <stdint.h>

/* The changed-site set of incremental builds (PYLATKMC_INCREMENTAL).
 *
 * Holds every site whose species changed since the set was last cleared, once
 * each. state_apply_actions and state_swap_vacancy record changes here.
 * Initialisation copies species directly and is covered by the first full
 * build instead.
 *
 * Preallocated to n_sites entries plus a mark per site, so adding never
 * allocates and the number of recorded sites cannot exceed n_sites.
 * The functions exist only in incremental builds. */

typedef struct ChangedSites ChangedSites;

/* Returns 0; -EINVAL on bad args; -ENOMEM (and *out = NULL) on failure. */
int  changed_sites_alloc(ChangedSites **out, int32_t n_sites);
void changed_sites_free(ChangedSites *cs);

/* Record `site`. A no-op if cs is NULL, the site is already recorded or the
 * site is outside [0, n_sites). */
void changed_sites_add(ChangedSites *cs, int32_t site);

/* Empty the set. O(its size). */
void changed_sites_clear(ChangedSites *cs);

/* Size of the set. *out points at the sites, valid until the next add/clear. */
int32_t changed_sites_get(const ChangedSites *cs, const int32_t **out);

#endif /* PYLATKMC_CHANGED_SITES_H */
