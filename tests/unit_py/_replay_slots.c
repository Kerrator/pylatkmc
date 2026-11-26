/* Every slot of every eligible subset must match a rescan, even when a CSR
 * row visits a site twice and the vacancy list is in swap-last order. */
#include <stdio.h>
#include <string.h>
#include "events_base.h"
#include "incremental.h"
#include "proclist.h"

enum { N = 7 };

static int check_order(const int32_t *order, int n_vac)
{
    int32_t offsets[] = {0, 1, 5, 9, 12, 15, 18, 20};
    int32_t neighbors[] = {1, 4,2,0,2, 3,1,5,1, 6,2,4, 5,3,1, 4,2,6, 3,5};
    int32_t coords[N * N_NEIGHBOUR_CODES] = {0};
    Lattice lat = {.n_sites=N, .nn1_offsets=offsets, .nn1_indices=neighbors,
                   .coord_table=coords};
    State st = {0};
    ActiveFilter *af = NULL;
    AvailSites *as = NULL;
    Incremental *inc = NULL;
    int rc = 1;
    if (state_alloc(&st, N, N) || active_filter_alloc(&af, N, 3) ||
        avail_sites_alloc(&as, pylatkmc_n_procs, N)) goto done;

    memset(st.species, SP_NI, N);
    st.n_vac = n_vac;
    for (int i = 0; i < n_vac; ++i) {
        const int32_t site = order[i];
        st.species[site] = SP_VACANT;
        st.vac_list[i] = site;
        st.vac_idx_of[site] = i;
    }
    active_filter_compute_static(af, &lat);
    if (incremental_start(&inc, &lat, &st, as, af)) goto done;
    active_filter_rescan(af, &lat, &st);
    for (unsigned members = 0; members < (1u << N); ++members) {
        int32_t expected[N];
        int n = 0;
        for (int i = 0; i < active_filter_n_active(af); ++i) {
            int32_t site = active_filter_site_at(af, i);
            if (members & (1u << site)) expected[n++] = site;
        }
        avail_sites_clear(as);
        for (int i = n; i > 0; --i) avail_sites_add(as, 0, expected[i - 1]);
        for (int i = 0; i < n; ++i) {
            int32_t site = avail_sites_site_at(as, 0, i);
            if (incremental_replay_site(inc, &lat, &st, af, as, 0, &site)
                || site != expected[i]) {
                fprintf(stderr, "mask %u, slot %d: got %d, expected %d\n",
                        members, i, site, expected[i]);
                goto done;
            }
        }
    }
    rc = 0;
done:
    incremental_free(inc);
    avail_sites_free(as);
    active_filter_free(af);
    state_free(&st);
    return rc;
}

int main(void)
{
    int32_t order[3] = {0};
    if (check_order(order, 0)) return 1;
    for (order[0] = 0; order[0] < N; ++order[0]) {
        if (check_order(order, 1)) return 1;
        for (order[1] = 0; order[1] < N; ++order[1]) {
            if (order[1] == order[0]) continue;
            if (check_order(order, 2)) return 1;
            for (order[2] = 0; order[2] < N; ++order[2]) {
                if (order[2] == order[0] || order[2] == order[1]) continue;
                if (check_order(order, 3)) return 1;
            }
        }
    }
    return 0;
}
