/* kmc.c — pylatkmc v0.2 main step loop (pattern-DB pipeline).
 *
 * Per-step algorithm:
 *
 *   1. active_filter_rescan(af, lat, st)
 *      → marks every vacant site, every 1NN of vacant, and every static
 *        (geometry-derived) low-coordination site
 *
 *   2. avail_sites_clear(as)
 *      → wipes all enrolments from the previous step (rates stay)
 *
 *   3. for i in [0, active_filter_n_active(af)):
 *          touchup_a(lat, st, as, active_filter_site_at(af, i))
 *      → the generated decision tree calls avail_sites_add for every
 *        eligible Process at each active site
 *
 *   4. avail_sites_refresh_cum_rates(as)
 *      → recomputes cum_rates[] = running sum of rates[p] * n_sites_per_proc[p]
 *
 *   5. r_tot = avail_sites_r_tot(as); if r_tot == 0 → trapped (-ENODATA)
 *
 *   6. (r1, r2) = rng_next2(); dt = -log(r2)/r_tot; target = r1*r_tot
 *
 *   7. avail_sites_select(as, target, &proc, &site) → picks (proc, site)
 *
 *   8. apply_event(ctx, proc, site)
 *      → calls apply_table[proc](st, lat, site) → HopOutcome
 *      → updates st->unwrapped_xyz for the moved vacancy (single-vacancy
 *        hop heuristic: only when v_origin and v_dest are both valid and
 *        the slot identity is preserved)
 *
 *   9. step++, time += dt; record stats
 *
 * The generated `proclist.c` provides:
 *   - touchup_a() — the decision tree
 *   - apply_table[] — dispatch from proc id to apply function
 *   - rate_table[] — per-proc Arrhenius rates (consumed by replica.c at
 *     startup to seed avail_sites_set_rate)
 */
#include "kmc.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../io/xyz_writer.h"
#include "../io/pykmc_out.h"
#include "../io/phasec_out.h"

/* The generated proclist.h declares apply_table, rate_table, touchup_a,
 * pylatkmc_n_procs, etc. — and, on a Phase C surrogate build, defines
 * PYLATKMC_HAS_SURROGATE + the surrogate externs. */
#include "proclist.h"

#ifdef PYLATKMC_HAS_SURROGATE
#include "surrogate.h"
#endif

/* Min-image displacement on one axis. */
static inline double min_image(double d, double L) {
    if (d >  0.5 * L) return d - L;
    if (d < -0.5 * L) return d + L;
    return d;
}

/* MSD heuristic counter — log on first multi-vacancy concerted event. */
static int g_msd_warning_emitted = 0;

/* Update unwrapped_xyz for a single-vacancy hop v_origin → v_dest (shared by the
 * measured and surrogate channels). See the multi-vacancy caveat below. */
static void update_msd(const Lattice *lat, State *st, int32_t v_origin, int32_t v_dest)
{
    if (v_origin >= 0 && v_dest >= 0) {
        int32_t new_idx = st->vac_idx_of[v_dest];
        if (new_idx >= 0 && new_idx < st->n_vac) {
            double ox = lat->positions[3 * v_origin + 0];
            double oy = lat->positions[3 * v_origin + 1];
            double oz = lat->positions[3 * v_origin + 2];
            double tx = lat->positions[3 * v_dest   + 0];
            double ty = lat->positions[3 * v_dest   + 1];
            double tz = lat->positions[3 * v_dest   + 2];
            double dx = min_image(tx - ox, (double)lat->cell[0]);
            double dy = min_image(ty - oy, (double)lat->cell[1]);
            double dz = min_image(tz - oz, (double)lat->cell[2]);
            /* state_apply_actions doesn't preserve unwrapped_xyz slot identity
             * across the swap; correct for the single-vacancy case, approximate
             * (swap-last shuffle) for multi-vacancy — see mean_msd_A2 caveat. */
            st->unwrapped_xyz[3 * new_idx + 0] += dx;
            st->unwrapped_xyz[3 * new_idx + 1] += dy;
            st->unwrapped_xyz[3 * new_idx + 2] += dz;
        }
    } else if (!g_msd_warning_emitted) {
        fprintf(stderr,
            "[kmc] note: event is not a single-vacancy hop "
            "(v_origin=%d, v_dest=%d); MSD will be approximate. "
            "(This warning fires once.)\n",
            v_origin, v_dest);
        g_msd_warning_emitted = 1;
    }
}

/* Apply the selected measured Process at the given anchor site. */
static void apply_event(KmcContext *ctx, int32_t proc, int32_t site)
{
    State *st = ctx->st;
    const Lattice *lat = ctx->lat;

    HopOutcome ho = pylatkmc_apply_table[proc](st, lat, site);
    if (pylatkmc_rate_table[proc].is_electrochemical) st->n_dissolution++;
    update_msd(lat, st, ho.v_origin, ho.v_dest);
}

int kmc_step_once(KmcContext *ctx,
                  int32_t *out_proc, int32_t *out_site, double *out_dt)
{
    if (!ctx || !ctx->lat || !ctx->st || !ctx->as || !ctx->af || !ctx->rng)
        return -EINVAL;

    /* 1. Rescan the active set. */
    active_filter_rescan(ctx->af, ctx->lat, ctx->st);

    /* 2. Wipe last step's enrolments. */
    avail_sites_clear(ctx->as);

    /* 3. Touchup at every active site. The generated touchup_a() walks
     * the decision tree and calls avail_sites_add(as, P_<name>, site)
     * for every eligible Process. */
    int32_t n_active = active_filter_n_active(ctx->af);
    for (int32_t i = 0; i < n_active; ++i) {
        int32_t s = active_filter_site_at(ctx->af, i);
        touchup_a(ctx->lat, ctx->st, ctx->as, s);
    }

    /* 4. Refresh cum_rates. */
    avail_sites_refresh_cum_rates(ctx->as);

    /* 5. Total rate across both channels: measured (avail_sites) + surrogate. */
    double pat_rtot = avail_sites_r_tot(ctx->as);
    double surr_rtot = 0.0;
#ifdef PYLATKMC_HAS_SURROGATE
    if (ctx->surr)
        surr_rtot = surrogate_rebuild(ctx->surr, ctx->lat, ctx->st, ctx->as,
                                      ctx->temperature_K);
#endif
    double r_tot = pat_rtot + surr_rtot;
    if (r_tot <= 0.0) return -ENODATA;

    /* 6. Draw RNG. */
    double r1, r2;
    rng_next2(ctx->rng, &r1, &r2);
    double dt     = -log(r2) / r_tot;
    double target = r1 * r_tot;

    /* 7. Select across both channels; measured occupies [0, pat_rtot). */
    int32_t proc = -1, site = -1;
    int32_t surr_fired = -1;
    if (target < pat_rtot || surr_rtot <= 0.0) {
        int rc = avail_sites_select(ctx->as, target, &proc, &site);
        if (rc != 0) return rc;
        apply_event(ctx, proc, site);
#ifdef PYLATKMC_HAS_SURROGATE
        if (ctx->surr)
            surrogate_note_measured(ctx->surr, pylatkmc_proc_v6_ea[proc],
                                    pylatkmc_rate_table[proc].Ea_eV);
#endif
    }
#ifdef PYLATKMC_HAS_SURROGATE
    else {
        surr_fired = surrogate_select(ctx->surr, target - pat_rtot);
        int32_t vo = -1, vd = -1;
        int rc = surrogate_apply(ctx->surr, ctx->st, ctx->lat, surr_fired, &vo, &vd);
        if (rc != 0) return rc;
        update_msd(ctx->lat, ctx->st, vo, vd);
        site = vo;   /* report the vacancy anchor; proc stays -1 (surrogate) */
    }
    if (ctx->surr)
        surrogate_account(ctx->surr, ctx->lat, surr_fired, dt, r_tot);
#endif
    (void)surr_fired;

    /* 9. Tick. */
    ctx->st->time_s += dt;
    ctx->st->step   += 1;

    if (out_proc) *out_proc = proc;
    if (out_site) *out_site = site;
    if (out_dt)   *out_dt   = dt;
    return 0;
}

int kmc_run(KmcContext *ctx)
{
    if (!ctx || !ctx->cfg) return -EINVAL;
    const KmcRunConfig *cfg = ctx->cfg;

    XyzWriter       xyz = {0};
    PykmcOutWriter  out_log = {0};
    PhasecOutWriter phasec = {0};
    int rc;

    if (cfg->traj_path && cfg->traj_path[0]) {
        rc = xyz_open(&xyz, cfg->traj_path, ctx->lat, ctx->temperature_K);
        if (rc != 0) {
            fprintf(stderr, "kmc_run: xyz_open(%s) failed: %d\n", cfg->traj_path, rc);
            return rc;
        }
    }
    if (cfg->log_path && cfg->log_path[0]) {
        rc = pykmc_out_open(&out_log, cfg->log_path);
        if (rc != 0) {
            fprintf(stderr, "kmc_run: pykmc_out_open(%s) failed: %d\n", cfg->log_path, rc);
            xyz_close(&xyz);
            return rc;
        }
    }

#ifdef PYLATKMC_HAS_SURROGATE
    if (ctx->surr && cfg->phasec_path && cfg->phasec_path[0]) {
        rc = phasec_out_open(&phasec, cfg->phasec_path);
        if (rc != 0)
            fprintf(stderr, "kmc_run: phasec_out_open(%s) failed: %d\n",
                    cfg->phasec_path, rc);
    }
#endif

    /* Emit the t=0 frame before any step. */
    if (xyz.fp) xyz_write_frame(&xyz, ctx->st);

    int last_rc = 0;
    while (ctx->st->step < cfg->max_steps) {
        if (cfg->max_time_s > 0 && ctx->st->time_s >= cfg->max_time_s) break;

        int32_t proc_done = -1, site_done = -1;
        double  dt_done   = 0.0;
        int step_rc = kmc_step_once(ctx, &proc_done, &site_done, &dt_done);
        if (step_rc == -ENODATA) {
            fprintf(stderr, "kmc_run: trapped at step %llu\n",
                    (unsigned long long)ctx->st->step);
            last_rc = -ENODATA;
            break;
        }
        if (step_rc != 0) { last_rc = step_rc; break; }

        if (cfg->sample_every > 0 && (ctx->st->step % cfg->sample_every) == 0) {
            if (xyz.fp) xyz_write_frame(&xyz, ctx->st);
            if (out_log.fp) {
                double k_event = (proc_done >= 0)
                    ? rateconst_eval(pylatkmc_rate_table[proc_done],
                                     ctx->temperature_K, ctx->overpotential_phi_eV)
                    : 0.0;
                double Ea_eV   = (proc_done >= 0) ? pylatkmc_rate_table[proc_done].Ea_eV : 0.0;
                pykmc_out_write_row(&out_log,
                                     ctx->st->step, ctx->st->time_s, dt_done,
                                     ctx->st->n_vac,
                                     avail_sites_r_tot(ctx->as),
                                     k_event, Ea_eV,
                                     proc_done, site_done);
            }
#ifdef PYLATKMC_HAS_SURROGATE
            if (phasec.fp && ctx->surr) {
                const struct SurrCtx *s = ctx->surr;
                double frac_inst = (s->last_k_total_inst > 0.0)
                    ? s->last_k_flag_inst / s->last_k_total_inst : 0.0;
                double frac_cum = (s->flux_total_cum > 0.0)
                    ? s->flux_flag_cum / s->flux_total_cum : 0.0;
                phasec_out_write_row(&phasec, ctx->st->step,
                                     frac_inst, frac_cum, s->last_n_cand,
                                     s->n_surr_fired, s->n_meas_fired,
                                     surrogate_v6_mean(s), s->v6_absresid_max);
            }
#endif
        }
    }

    xyz_close(&xyz);
    pykmc_out_close(&out_log);
    phasec_out_close(&phasec);
    return last_rc;
}
