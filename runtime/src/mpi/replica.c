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
#include "avail_sites.h"
#include "active_filter.h"
#include "rng.h"
#include "../io/initconfig.h"
#include "../io/xyz_writer.h"
#include "../io/pykmc_out.h"

/* The generated proclist.h provides pylatkmc_n_procs and pylatkmc_rate_table. */
#include "proclist.h"

/* FCC bulk 1NN coordination. Sites with fewer 1NN are static-active in
 * the active_filter (surface, edge, corner). Hardcoded for FCC; if/when
 * we add BCC/HCP we'll plumb this through ModelSpec. */
#define PYLATKMC_FCC_BULK_NN1   12

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
                                    double T_K, const InputConfig *cfg)
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
            "  \"run_rc\": %d,\n"
            "  \"n_procs\": %d\n"
            "}\n",
            rep->rank, lat->n_sites, st->n_vac, T_K,
            (unsigned long long)cfg->base_seed,
            (unsigned long long)s->n_steps, s->total_time_s,
            s->mean_msd_A2, s->run_rc, (int)pylatkmc_n_procs);
    fclose(fp);
}

int replica_run(ReplicaContext *rep, const InputConfig *cfg)
{
    if (!rep || !cfg) return -EINVAL;

    Lattice       lat = {0};
    State         st  = {0};
    AvailSites   *as  = NULL;
    ActiveFilter *af  = NULL;
    Rng           rng = {0};

    int rc = initconfig_load(cfg->initconfig_path, &lat, &st);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] initconfig_load(%s) failed: %d\n",
                rep->rank, cfg->initconfig_path, rc);
        return rc;
    }

    /* Build the per-site NeighbourCode lookup table once at startup. */
    rc = lattice_build_coord_table(&lat);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] lattice_build_coord_table failed: %d\n",
                rep->rank, rc);
        state_free(&st); lattice_free(&lat);
        return rc;
    }

    /* Allocate avail_sites with N_PROCS from the generated proclist. */
    rc = avail_sites_alloc(&as, pylatkmc_n_procs, lat.n_sites);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] avail_sites_alloc failed: %d\n", rep->rank, rc);
        state_free(&st); lattice_free(&lat);
        return rc;
    }
    /* Seed per-proc rates from the generated rate_table. */
    for (int32_t p = 0; p < pylatkmc_n_procs; ++p) {
        avail_sites_set_rate(as, p, pylatkmc_rate_table[p].rate);
    }

    /* Allocate active_filter and precompute the static (geometry) mask. */
    rc = active_filter_alloc(&af, lat.n_sites, PYLATKMC_FCC_BULK_NN1);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] active_filter_alloc failed: %d\n", rep->rank, rc);
        avail_sites_free(as); state_free(&st); lattice_free(&lat);
        return rc;
    }
    active_filter_compute_static(af, &lat);

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
        .lat = &lat, .st = &st, .as = as, .af = af, .rng = &rng,
        .cfg = &run_cfg, .temperature_K = cfg->temperature_K,
    };

    printf("[rank %d] run: %d sites, %d vacancies, T=%.1f K, max_steps=%llu, n_procs=%d\n",
           rep->rank, lat.n_sites, st.n_vac, cfg->temperature_K,
           (unsigned long long)cfg->max_steps, (int)pylatkmc_n_procs);

    int run_rc = kmc_run(&ctx);

    /* Compute mean MSD across vacancies. */
    double msd_sum_A2 = 0.0;
    for (int32_t v = 0; v < st.n_vac; ++v) {
        double dx = st.unwrapped_xyz[3 * v + 0];
        double dy = st.unwrapped_xyz[3 * v + 1];
        double dz = st.unwrapped_xyz[3 * v + 2];
        msd_sum_A2 += dx * dx + dy * dy + dz * dz;
    }
    rep->stats.n_steps      = st.step;
    rep->stats.total_time_s = st.time_s;
    rep->stats.mean_msd_A2  = (st.n_vac > 0) ? (msd_sum_A2 / (double)st.n_vac) : 0.0;
    rep->stats.run_rc       = run_rc;
    /* motif_counts / direction_counts are zeroed (cube-era fields, kept for
     * MPI-ABI compatibility but no longer populated in v0.2). */

    write_per_rank_summary(summary_path, rep, &lat, &st, cfg->temperature_K, cfg);

    active_filter_free(af);
    avail_sites_free(as);
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
    int n_success = 0, n_failed = 0;
    for (int i = 0; i < N; ++i) {
        times[i] = gathered[i].total_time_s;
        msds[i]  = gathered[i].mean_msd_A2;
        steps[i] = (double)gathered[i].n_steps;
        if (gathered[i].run_rc == 0) n_success++;
        else                          n_failed++;
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
            "  \"n_procs\": %d,\n"
            "  \"n_steps_mean\": %.1f,\n"
            "  \"n_steps_std\":  %.1f,\n"
            "  \"total_time_s_mean\": %.9e,\n"
            "  \"total_time_s_std\":  %.9e,\n"
            "  \"mean_msd_A2_mean\":  %.6e,\n"
            "  \"mean_msd_A2_std\":   %.6e,\n",
            N, n_success, n_failed,
            (unsigned long long)cfg->base_seed, cfg->temperature_K,
            (int)pylatkmc_n_procs,
            s_mean, s_std, t_mean, t_std, m_mean, m_std);

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
