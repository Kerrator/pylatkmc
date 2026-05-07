#include "state.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "events_base.h"   /* SP_VACANT */

int state_alloc(State *st, int32_t n_sites, int32_t n_vac_max)
{
    if (!st || n_sites <= 0 || n_vac_max <= 0) return -EINVAL;
    memset(st, 0, sizeof(*st));
    st->n_vac_max      = n_vac_max;
    /* Allocate species[] with one extra "stub" slot at index n_sites. The
     * lattice's coord_table places `n_sites` (not -1) at every direction
     * code that doesn't have a real neighbour (e.g. NC_NN1_UP_* on a top-
     * surface site). Reading species[n_sites] returns the sentinel value
     * SP_OUTSIDE_LATTICE = 255, which doesn't match any real species, so
     * the decision tree's switch statements naturally fall through default
     * for those reads instead of segfaulting on species[-1]. */
    st->species        = calloc((size_t)n_sites + 1, sizeof *st->species);
    st->vac_idx_of     = malloc((size_t)n_sites  * sizeof *st->vac_idx_of);
    st->vac_list       = malloc((size_t)n_vac_max * sizeof *st->vac_list);
    st->unwrapped_xyz  = calloc((size_t)n_vac_max * 3, sizeof *st->unwrapped_xyz);
    if (!st->species || !st->vac_idx_of || !st->vac_list || !st->unwrapped_xyz) {
        state_free(st);
        return -ENOMEM;
    }
    for (int32_t i = 0; i < n_sites; ++i) st->vac_idx_of[i] = -1;
    /* Sentinel: 255 doesn't match SP_VACANT/SP_NI/SP_FE/SP_CR (0..3). */
    st->species[n_sites] = (uint8_t)255;
    return 0;
}

void state_free(State *st)
{
    if (!st) return;
    free(st->species);        st->species        = NULL;
    free(st->vac_idx_of);     st->vac_idx_of     = NULL;
    free(st->vac_list);       st->vac_list       = NULL;
    free(st->unwrapped_xyz);  st->unwrapped_xyz  = NULL;
    st->n_vac = 0;
    st->n_vac_max = 0;
}

/* Move the vacancy currently at either `a` or `b` to the other site.
 * After the call, exactly one of (a, b) is vacant and vac_list / vac_idx_of
 * remain consistent. unwrapped_xyz is not touched — that's the caller's job
 * because it needs to know the displacement vector (minimum-image PBC). */
void state_swap_vacancy(State *st, int32_t a, int32_t b)
{
    if (!st || a == b) return;
    int32_t vacant, occupied;
    if (st->species[a] == SP_VACANT && st->species[b] != SP_VACANT) {
        vacant = a; occupied = b;
    } else if (st->species[b] == SP_VACANT && st->species[a] != SP_VACANT) {
        vacant = b; occupied = a;
    } else {
        /* Both vacant or both occupied — caller bug. Leave state unchanged. */
        return;
    }
    int32_t v_idx = st->vac_idx_of[vacant];
    st->species[vacant]        = st->species[occupied];
    st->species[occupied]      = SP_VACANT;
    st->vac_list[v_idx]        = occupied;
    st->vac_idx_of[occupied]   = v_idx;
    st->vac_idx_of[vacant]     = -1;
}
