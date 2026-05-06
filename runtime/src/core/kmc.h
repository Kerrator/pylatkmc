#ifndef LATKMC_KMC_H
#define LATKMC_KMC_H

#include <stdint.h>

#include "lattice.h"
#include "state.h"
#include "rng.h"
#include "avail_sites.h"
#include "active_filter.h"

/* Per-run config (paths, step caps). Same shape as M1; just the meaning
 * of which paths are read changed (no .kmcrt anymore). */
typedef struct {
    uint64_t max_steps;
    double   max_time_s;        /* 0 means no cap */
    uint64_t sample_every;      /* emit trajectory + step-log every N steps */
    uint64_t summary_every;     /* flush summary.json every N steps (0 = end only) */

    const char *out_dir;
    const char *traj_path;
    const char *log_path;
    const char *summary_path;

    /* Hook for cross-validation; currently unused. */
    const char *rng_replay_path;
} KmcRunConfig;

/* Per-run context. Shapes for v0.2 (pattern-DB):
 *   - lat: lattice + coord_table (built once at startup)
 *   - st:  per-replica state (species, vac_list, time, step, MSD)
 *   - as:  avail_sites index (cleared and rebuilt every step)
 *   - af:  active_filter (re-scanned every step)
 *   - rng: per-replica RNG
 *   - temperature_K: Arrhenius rates were baked at this T
 *     (the runtime carries it for trajectory headers / logs only)
 */
typedef struct {
    const Lattice    *lat;
    State            *st;
    AvailSites       *as;
    ActiveFilter     *af;
    Rng              *rng;
    const KmcRunConfig *cfg;
    double            temperature_K;
} KmcContext;

/* One rejection-free step:
 *   1. active_filter_rescan(af, lat, st)
 *   2. avail_sites_clear(as)
 *   3. for each active site: touchup_a(lat, st, as, site)
 *   4. avail_sites_refresh_cum_rates(as)
 *   5. draw r1, r2; dt = -log(r2)/r_tot; target = r1*r_tot
 *   6. avail_sites_select(as, target, &proc, &site)
 *   7. apply_table[proc](st, lat, site) → HopOutcome
 *   8. update unwrapped_xyz for the moved vacancy (single-vacancy hop heuristic)
 *
 * Writes (proc, site, dt) to the out parameters if non-NULL. Returns
 * 0 on success, -ENODATA if trapped (r_tot == 0), -EINVAL on bad args.
 */
int kmc_step_once(KmcContext *ctx,
                  int32_t *out_proc, int32_t *out_site, double *out_dt);

/* Run until max_steps or max_time_s; emits trajectory + step log as
 * configured. */
int kmc_run(KmcContext *ctx);

#endif /* LATKMC_KMC_H */
