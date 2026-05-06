#include "replica.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <mpi.h>

#include "kmc.h"
#include "lattice.h"
#include "state.h"
#include "ratetable.h"
#include "avail.h"
#include "rng.h"
#include "../io/initconfig.h"
#include "../io/xyz_writer.h"
#include "../io/pykmc_out.h"

/* String names for MotifFamily and DirectionFamily enums, used in JSON output.
 * These must stay in sync with:
 *   - the enum declarations in src/core/events.h
 *   - MOTIF_NAMES / DIR_NAMES in tools/build_binary_rate_table.py
 * The preprocessor also bakes motif_of_class_dir into the binary header, which
 * is the semantic source of truth — these arrays are display-only. */
static const char *MOTIF_NAMES[] = {
    "surface_1nn_translation",      "surface_2nn_translation",
    "subsurface_1nn_translation",   "surface_subsurface_exchange",
    "interlayer_translation",       "subsurface_exchange",
    "concerted_3d",                 "unresolved_multisite",
};
static const char *DIR_NAMES[] = {
    "<110>_inplane", "<100>_inplane", "<111>_interlayer",
    "<001>_exchange", "unresolved",
};

/* Emit a "<label>": { "<name>": count, ... } object into fp. Shared by the
 * per-rank summary and the ensemble aggregate to keep the two layouts in sync. */
static void emit_named_counts(FILE *fp, const char *label,
                              const char *const *names, int n,
                              const uint64_t *counts, const char *trailing)
{
    fprintf(fp, "  \"%s\": {\n", label);
    for (int i = 0; i < n; ++i) {
        fprintf(fp, "    \"%s\": %llu%s\n",
                names[i], (unsigned long long)counts[i],
                (i == n - 1) ? "" : ",");
    }
    fprintf(fp, "  }%s\n", trailing);
}

static int ensure_dir(const char *path) {
    struct stat st;
    if (stat(path, &st) == 0 && S_ISDIR(st.st_mode)) return 0;
    if (mkdir(path, 0755) == 0) return 0;
    if (errno == EEXIST) return 0;
    return -errno;
}

int replica_init(ReplicaContext *rep, const InputConfig *cfg, int rank, int nranks)
{
    if (!rep || !cfg) return -EINVAL;
    memset(rep, 0, sizeof(*rep));
    rep->rank   = rank;
    rep->nranks = nranks;
    rep->stats.rank = rank;
    snprintf(rep->out_dir, sizeof(rep->out_dir),
             "%s/replica_%04d", cfg->output_root, rank);
    int rc = ensure_dir(cfg->output_root); if (rc != 0 && rc != -EEXIST) return rc;
    rc     = ensure_dir(rep->out_dir);     if (rc != 0 && rc != -EEXIST) return rc;
    return 0;
}

static void write_per_rank_summary(const char *path, const ReplicaContext *rep,
                                    const Lattice *lat, const State *st,
                                    const RateTable *rt, const InputConfig *cfg)
{
    FILE *fp = fopen(path, "w");
    if (!fp) return;
    const ReplicaStats *s = &rep->stats;
    fprintf(fp,
            "{\n"
            "  \"rank\": %d,\n"
            "  \"n_sites\": %d,\n"
            "  \"n_vac\": %d,\n"
            "  \"temperature_K\": %.3f,\n"
            "  \"base_seed\": %llu,\n"
            "  \"n_steps\": %llu,\n"
            "  \"total_time_s\": %.9e,\n"
            "  \"mean_msd_A2\": %.6e,\n"
            "  \"run_rc\": %d,\n",
            rep->rank, lat->n_sites, st->n_vac, (double)rt->temperature_K,
            (unsigned long long)cfg->base_seed,
            (unsigned long long)s->n_steps, s->total_time_s,
            s->mean_msd_A2, s->run_rc);

    emit_named_counts(fp, "motif_counts",     MOTIF_NAMES, 8, s->motif_counts,     ",");
    emit_named_counts(fp, "direction_counts", DIR_NAMES,   5, s->direction_counts, "");
    fputs("}\n", fp);
    fclose(fp);
}

int replica_run(ReplicaContext *rep, const InputConfig *cfg)
{
    if (!rep || !cfg) return -EINVAL;

    Lattice   lat;
    State     st;
    RateTable rt;
    AvailEvents av;
    Rng       rng;

    int rc = initconfig_load(cfg->initconfig_path, &lat, &st);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] initconfig_load(%s) failed: %d\n",
                rep->rank, cfg->initconfig_path, rc);
        return rc;
    }
    rc = ratetable_load(&rt, cfg->ratetable_path);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] ratetable_load(%s) failed: %d\n",
                rep->rank, cfg->ratetable_path, rc);
        lattice_free(&lat); state_free(&st);
        return rc;
    }
    if (fabsf(rt.temperature_K - (float)cfg->temperature_K) > 0.5f) {
        fprintf(stderr, "[rank %d] temperature mismatch: input says %.2f K, "
                "rate table is for %.2f K\n",
                rep->rank, cfg->temperature_K, (double)rt.temperature_K);
        ratetable_free(&rt); lattice_free(&lat); state_free(&st);
        return -EINVAL;
    }
    rc = avail_alloc(&av, st.n_vac_max);
    if (rc != 0) {
        ratetable_free(&rt); lattice_free(&lat); state_free(&st);
        return rc;
    }

    rng_seed(&rng, cfg->base_seed, (uint32_t)rep->rank);

    char traj_path[600], log_path[600], summary_path[600];
    snprintf(traj_path,    sizeof traj_path,    "%s/trajkmc.xyz",  rep->out_dir);
    snprintf(log_path,     sizeof log_path,     "%s/pykmc.out",    rep->out_dir);
    snprintf(summary_path, sizeof summary_path, "%s/summary.json", rep->out_dir);

    KmcRunConfig run_cfg = {
        .max_steps     = cfg->max_steps,
        .max_time_s    = cfg->max_time_s,
        .sample_every  = cfg->sample_every,
        .summary_every = cfg->summary_every,
        .out_dir       = rep->out_dir,
        .traj_path     = traj_path,
        .log_path      = log_path,
        .summary_path  = summary_path,
        .rng_replay_path = (cfg->rng_replay_path[0] ? cfg->rng_replay_path : NULL),
    };
    KmcContext ctx = {
        .lat = &lat, .rt = &rt, .st = &st, .av = &av, .rng = &rng, .cfg = &run_cfg,
    };

    printf("[rank %d] run: %d sites, %d vacancies, T=%.1f K, max_steps=%llu\n",
           rep->rank, lat.n_sites, st.n_vac, (double)rt.temperature_K,
           (unsigned long long)cfg->max_steps);

    int run_rc = kmc_run(&ctx);

    /* Compute mean MSD across vacancies. */
    double msd_sum_A2 = 0.0;
    for (int32_t v = 0; v < st.n_vac; ++v) {
        double dx = st.unwrapped_xyz[3 * v + 0];
        double dy = st.unwrapped_xyz[3 * v + 1];
        double dz = st.unwrapped_xyz[3 * v + 2];
        msd_sum_A2 += dx * dx + dy * dy + dz * dz;
    }
    rep->stats.n_steps       = st.step;
    rep->stats.total_time_s  = st.time_s;
    rep->stats.mean_msd_A2   = (st.n_vac > 0) ? (msd_sum_A2 / (double)st.n_vac) : 0.0;
    rep->stats.run_rc        = run_rc;
    memcpy(rep->stats.motif_counts,     st.motif_counts,     sizeof rep->stats.motif_counts);
    memcpy(rep->stats.direction_counts, st.direction_counts, sizeof rep->stats.direction_counts);

    write_per_rank_summary(summary_path, rep, &lat, &st, &rt, cfg);

    avail_free(&av);
    ratetable_free(&rt);
    state_free(&st);
    lattice_free(&lat);
    return run_rc;
}

/* Small helper — mean and sample std over an array. */
static void mean_std(const double *x, int n, double *mean, double *std) {
    double s = 0.0;
    for (int i = 0; i < n; ++i) s += x[i];
    double m = (n > 0) ? s / n : 0.0;
    double v = 0.0;
    for (int i = 0; i < n; ++i) { double d = x[i] - m; v += d * d; }
    double sd = (n > 1) ? sqrt(v / (n - 1)) : 0.0;
    *mean = m; *std = sd;
}

int replica_aggregate(ReplicaContext *rep, const InputConfig *cfg)
{
    if (!rep || !cfg) return -EINVAL;

    ReplicaStats *gathered = NULL;
    if (rep->rank == 0) {
        gathered = calloc((size_t)rep->nranks, sizeof *gathered);
        if (!gathered) return -ENOMEM;
    }

    /* All ranks have an identical struct layout — gather as MPI_BYTE. */
    int rc = MPI_Gather(&rep->stats, (int)sizeof(ReplicaStats), MPI_BYTE,
                        gathered,     (int)sizeof(ReplicaStats), MPI_BYTE,
                        0, MPI_COMM_WORLD);
    if (rc != MPI_SUCCESS) {
        free(gathered);
        return -EIO;
    }

    if (rep->rank != 0) { free(gathered); return 0; }

    /* Rank 0: write the aggregate summary. */
    int N = rep->nranks;
    double *times = malloc((size_t)N * sizeof *times);
    double *msds  = malloc((size_t)N * sizeof *msds);
    double *steps = malloc((size_t)N * sizeof *steps);
    if (!times || !msds || !steps) {
        free(times); free(msds); free(steps); free(gathered);
        return -ENOMEM;
    }
    uint64_t motif_sum[8] = {0}, dir_sum[5] = {0};
    int n_success = 0, n_failed = 0;
    for (int i = 0; i < N; ++i) {
        times[i] = gathered[i].total_time_s;
        msds[i]  = gathered[i].mean_msd_A2;
        steps[i] = (double)gathered[i].n_steps;
        if (gathered[i].run_rc == 0) n_success++;
        else                          n_failed++;
        for (int m = 0; m < 8; ++m) motif_sum[m] += gathered[i].motif_counts[m];
        for (int d = 0; d < 5; ++d) dir_sum[d]   += gathered[i].direction_counts[d];
    }
    double t_mean, t_std, m_mean, m_std, s_mean, s_std;
    mean_std(times, N, &t_mean, &t_std);
    mean_std(msds,  N, &m_mean, &m_std);
    mean_std(steps, N, &s_mean, &s_std);

    char agg_path[600];
    snprintf(agg_path, sizeof agg_path, "%s/aggregate_summary.json", cfg->output_root);
    FILE *fp = fopen(agg_path, "w");
    if (!fp) {
        free(times); free(msds); free(steps); free(gathered);
        return -errno;
    }
    fprintf(fp,
            "{\n"
            "  \"n_replicas\": %d,\n"
            "  \"n_success\": %d,\n"
            "  \"n_failed\": %d,\n"
            "  \"base_seed\": %llu,\n"
            "  \"temperature_K\": %.3f,\n"
            "  \"n_steps_mean\": %.1f,\n"
            "  \"n_steps_std\":  %.1f,\n"
            "  \"total_time_s_mean\": %.9e,\n"
            "  \"total_time_s_std\":  %.9e,\n"
            "  \"mean_msd_A2_mean\":  %.6e,\n"
            "  \"mean_msd_A2_std\":   %.6e,\n",
            N, n_success, n_failed,
            (unsigned long long)cfg->base_seed, cfg->temperature_K,
            s_mean, s_std, t_mean, t_std, m_mean, m_std);

    emit_named_counts(fp, "motif_counts_sum",     MOTIF_NAMES, 8, motif_sum, ",");
    emit_named_counts(fp, "direction_counts_sum", DIR_NAMES,   5, dir_sum,   ",");
    fputs("  \"replicas\": [\n", fp);
    for (int i = 0; i < N; ++i) {
        fprintf(fp,
                "    {\"rank\": %d, \"run_rc\": %d, \"n_steps\": %llu, "
                "\"total_time_s\": %.9e, \"mean_msd_A2\": %.6e}%s\n",
                gathered[i].rank, gathered[i].run_rc,
                (unsigned long long)gathered[i].n_steps,
                gathered[i].total_time_s, gathered[i].mean_msd_A2,
                (i == N - 1) ? "" : ",");
    }
    fputs("  ]\n}\n", fp);
    fclose(fp);

    printf("[rank 0] wrote %s  (n=%d, %d ok / %d failed)\n",
           agg_path, N, n_success, n_failed);

    free(times); free(msds); free(steps); free(gathered);
    return 0;
}
