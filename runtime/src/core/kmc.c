#include "kmc.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../io/xyz_writer.h"
#include "../io/pykmc_out.h"

/* Minimum-image displacement on one axis for cell length L.
 * Assumes the hop is < L/2, which is true for any NN hop. */
static inline double min_image(double d, double L) {
    if (d >  0.5 * L) return d - L;
    if (d < -0.5 * L) return d + L;
    return d;
}

static void apply_event(const Lattice *lat, State *st, const Event *ev)
{
    int32_t v_idx = st->vac_idx_of[ev->vac_origin];
    if (v_idx < 0) return;

    double ox = lat->positions[3 * ev->vac_origin + 0];
    double oy = lat->positions[3 * ev->vac_origin + 1];
    double oz = lat->positions[3 * ev->vac_origin + 2];
    double tx = lat->positions[3 * ev->vac_dest + 0];
    double ty = lat->positions[3 * ev->vac_dest + 1];
    double tz = lat->positions[3 * ev->vac_dest + 2];
    double dx = min_image(tx - ox, (double)lat->cell[0]);
    double dy = min_image(ty - oy, (double)lat->cell[1]);
    double dz = min_image(tz - oz, (double)lat->cell[2]);

    state_swap_vacancy(st, ev->vac_origin, ev->vac_dest);

    st->unwrapped_xyz[3 * v_idx + 0] += dx;
    st->unwrapped_xyz[3 * v_idx + 1] += dy;
    st->unwrapped_xyz[3 * v_idx + 2] += dz;
}

int kmc_step_once(KmcContext *ctx, Event *out_ev, double *out_dt)
{
    if (!ctx || !ctx->av || !ctx->lat || !ctx->st || !ctx->rt || !ctx->rng)
        return -EINVAL;

    avail_rebuild_all(ctx->av, ctx->lat, ctx->st, ctx->rt);

    if (ctx->av->n_events <= 0 || ctx->av->r_tot <= 0.0) return -ENODATA;

    double r1, r2;
    rng_next2(ctx->rng, &r1, &r2);

    double dt     = -log(r2) / ctx->av->r_tot;
    double target = r1 * ctx->av->r_tot;

    const Event *ev = NULL;
    int32_t idx = avail_select(ctx->av, target, &ev);
    if (idx < 0 || ev == NULL) return -ENODATA;

    Event ev_copy = *ev;   /* avail.events[] may get invalidated by next rebuild */
    apply_event(ctx->lat, ctx->st, &ev_copy);

    ctx->st->time_s += dt;
    ctx->st->step   += 1;
    ctx->st->motif_counts    [ev_copy.motif    ]++;
    ctx->st->direction_counts[ev_copy.direction]++;

    if (out_ev) *out_ev = ev_copy;
    if (out_dt) *out_dt = dt;
    return 0;
}

int kmc_run(KmcContext *ctx)
{
    if (!ctx || !ctx->cfg) return -EINVAL;
    const KmcRunConfig *cfg = ctx->cfg;

    XyzWriter       xyz = {0};
    PykmcOutWriter  out_log = {0};
    int rc;

    if (cfg->traj_path && cfg->traj_path[0]) {
        rc = xyz_open(&xyz, cfg->traj_path, ctx->lat, (double)ctx->rt->temperature_K);
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

    /* Emit the t=0 frame before any step. */
    if (xyz.fp) xyz_write_frame(&xyz, ctx->st);

    int last_rc = 0;
    while (ctx->st->step < cfg->max_steps) {
        if (cfg->max_time_s > 0 && ctx->st->time_s >= cfg->max_time_s) break;

        Event  ev_done;
        double dt_done;
        int step_rc = kmc_step_once(ctx, &ev_done, &dt_done);
        if (step_rc == -ENODATA) {
            fprintf(stderr, "kmc_run: trapped at step %llu\n",
                    (unsigned long long)ctx->st->step);
            last_rc = -ENODATA;
            break;
        }
        if (step_rc != 0) { last_rc = step_rc; break; }

        if (cfg->sample_every > 0 && (ctx->st->step % cfg->sample_every) == 0) {
            if (xyz.fp) xyz_write_frame(&xyz, ctx->st);
            if (out_log.fp) pykmc_out_write_row(&out_log, ctx->st->step,
                                                 ctx->st->time_s, dt_done,
                                                 ctx->st->n_vac,
                                                 ctx->av->r_tot, &ev_done);
        }
    }

    xyz_close(&xyz);
    pykmc_out_close(&out_log);
    return last_rc;
}
