/* changed_sites -- the changed-site set of incremental builds.
 * See changed_sites.h. Empty unless PYLATKMC_INCREMENTAL is defined. */
#include "changed_sites.h"

#ifdef PYLATKMC_INCREMENTAL

#include <errno.h>
#include <stdlib.h>

struct ChangedSites {
    int32_t  n_sites;
    int32_t  n;
    int32_t *sites;     /* [n_sites]; the first n are the set */
    uint8_t *marked;    /* [n_sites]; 1 if the site is in the set */
};

int changed_sites_alloc(ChangedSites **out, int32_t n_sites)
{
    if (!out || n_sites <= 0) return -EINVAL;
    *out = NULL;
    ChangedSites *cs = calloc(1, sizeof *cs);
    if (!cs) return -ENOMEM;
    cs->n_sites = n_sites;
    cs->sites   = malloc((size_t)n_sites * sizeof *cs->sites);
    cs->marked  = calloc((size_t)n_sites, sizeof *cs->marked);
    if (!cs->sites || !cs->marked) {
        changed_sites_free(cs);
        return -ENOMEM;
    }
    *out = cs;
    return 0;
}

void changed_sites_free(ChangedSites *cs)
{
    if (!cs) return;
    free(cs->sites);
    free(cs->marked);
    free(cs);
}

void changed_sites_add(ChangedSites *cs, int32_t site)
{
    if (!cs || site < 0 || site >= cs->n_sites || cs->marked[site]) return;
    cs->marked[site] = 1;
    cs->sites[cs->n++] = site;
}

void changed_sites_clear(ChangedSites *cs)
{
    if (!cs) return;
    for (int32_t i = 0; i < cs->n; ++i) cs->marked[cs->sites[i]] = 0;
    cs->n = 0;
}

int32_t changed_sites_get(const ChangedSites *cs, const int32_t **out)
{
    if (out) *out = cs ? cs->sites : NULL;
    return cs ? cs->n : 0;
}

#endif /* PYLATKMC_INCREMENTAL */
