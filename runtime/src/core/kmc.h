#ifndef LATKMC_KMC_H
#define LATKMC_KMC_H

#include <stdint.h>
#include "lattice.h"
#include "state.h"
#include "events.h"
#include "ratetable.h"
#include "avail.h"
#include "rng.h"

typedef struct {
    uint64_t max_steps;
    double   max_time_s;        /* 0 means no cap */
    uint64_t sample_every;      /* emit trajectory + step-log every N steps */
    uint64_t summary_every;     /* flush summary.json every N steps (0 = end only) */

    const char *out_dir;
    const char *traj_path;
    const char *log_path;
    const char *summary_path;

    /* Hook for future cross-validation: when non-NULL, will skip the RNG and
     * read (r1, r2) ASCII pairs from this file. Currently unused — kmc_run
     * always draws from ctx->rng. Wire up in a validation milestone. */
    const char *rng_replay_path;
} KmcRunConfig;

typedef struct {
    const Lattice    *lat;
    const RateTable  *rt;
    State            *st;
    AvailEvents      *av;
    Rng              *rng;
    const KmcRunConfig *cfg;
} KmcContext;

/* One rejection-free step. On success, the selected event is copied into
 * *out_ev (if non-NULL) and dt is written to *out_dt. Returns 0 on success,
 * -ENODATA if trapped (no events), -EINVAL on bad arguments. */
int kmc_step_once(KmcContext *ctx, Event *out_ev, double *out_dt);

/* Run until max_steps or max_time_s; emits trajectory + step log as configured. */
int kmc_run(KmcContext *ctx);

#endif /* LATKMC_KMC_H */
