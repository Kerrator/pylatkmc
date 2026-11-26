/* Hexadecimal dt retains every bit that rounding in pykmc.out would hide. */
#include <stdio.h>
#include "initconfig.h"
#include "kmc.h"
#include "proclist.h"

int main(int argc, char **argv)
{
    Lattice lat = {0};
    State st = {0};
    Rng rng;
    KmcRunConfig cfg = {0};
    KmcContext ctx = {.lat=&lat, .st=&st, .rng=&rng, .cfg=&cfg, .temperature_K=500.0};
    int rc = 1;
    if (argc != 2 || initconfig_load(argv[1], &lat, &st, 256)) return 1;
    if (lattice_build_coord_table(&lat) ||
        active_filter_alloc(&ctx.af, lat.n_sites, 12) ||
        avail_sites_alloc(&ctx.as, pylatkmc_n_procs, lat.n_sites)) goto done;
    active_filter_compute_static(ctx.af, &lat);
    for (int p = 0; p < pylatkmc_n_procs; ++p)
        avail_sites_set_rate(ctx.as, p, rateconst_eval(pylatkmc_rate_table[p], ctx.temperature_K, 0));
    rng_seed(&rng, 19, 0);
    int swapped = 0;
    for (int i = 0; i < 800; ++i) {
        /* Exercise the public swap API between KMC steps, after the initial
         * table has been built. Both builds make the same external change. */
        if (i == 400 && st.n_vac > 0) {
            int32_t vac = st.vac_list[0];
            for (int j = lat.nn1_offsets[vac]; j < lat.nn1_offsets[vac + 1]; ++j) {
                int32_t site = lat.nn1_indices[j];
                if (st.vac_idx_of[site] < 0) {
                    state_swap_vacancy(&st, vac, site);
                    swapped = 1;
                    break;
                }
            }
        }
        int32_t proc, site;
        double dt;
        if (kmc_step_once(&ctx, &proc, &site, &dt)) goto done;
        printf("%d %d %a\n", proc, site, dt);
    }
    rc = swapped ? 0 : 1;
done:
#ifdef PYLATKMC_INCREMENTAL
    incremental_free(ctx.inc);
#endif
    avail_sites_free(ctx.as);
    active_filter_free(ctx.af);
    state_free(&st);
    lattice_free(&lat);
    return rc;
}
