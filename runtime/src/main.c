#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <mpi.h>

#include "io/config_reader.h"
#include "mpi/replica.h"

#define LATKMC_VERSION "0.1.0-scaffold"

static void print_usage(const char *argv0) {
    fprintf(stderr,
        "latkmc %s\n"
        "usage: %s <input.ini>\n"
        "\n"
        "Run one replica per MPI rank. See README.md for input-file format.\n",
        LATKMC_VERSION, argv0);
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank = 0, nranks = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    if (argc < 2) {
        if (rank == 0) print_usage(argv[0]);
        MPI_Finalize();
        return 2;
    }

    if (rank == 0) {
        printf("latkmc %s — %d rank%s\n",
               LATKMC_VERSION, nranks, nranks == 1 ? "" : "s");
    }

    InputConfig cfg;
    ReplicaContext rep;
    int rc = input_config_load(&cfg, argv[1]);
    if (rc != 0 && rc != -ENOSYS /* pre-M1 stub */) {
        fprintf(stderr, "[rank %d] input_config_load failed: %d\n", rank, rc);
    } else {
        rc = replica_init(&rep, &cfg, rank, nranks);
        if (rc != 0)
            fprintf(stderr, "[rank %d] replica_init failed: %d\n", rank, rc);
    }

    /* Agree on startup before anyone runs: a rank that failed and returned
     * alone would leave the others blocked in the post-run collectives (the
     * MPI_Allreduce below, replica_aggregate's MPI_Gather) until walltime.
     * If any rank failed, every rank exits non-zero and no replica runs. */
    int init_failed = (rc != 0), n_init_failed = 0;
    MPI_Allreduce(&init_failed, &n_init_failed, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    if (n_init_failed > 0) {
        if (rank == 0)
            fprintf(stderr, "startup failed on %d of %d rank%s; no replica was run\n",
                    n_init_failed, nranks, nranks == 1 ? "" : "s");
        MPI_Finalize();
        return 1;
    }

    rc = replica_run(&rep, &cfg);
    /* Process exit status (sweeps, job queues): a replica that completed or
     * trapped (-ENODATA: no event left, a normal physical end, already
     * reported by kmc_run) succeeds. Any other result, a setup failure (an
     * unreadable .kmcinit, ENOMEM, a refused geometry, ...) or a failed step,
     * fails the job on every rank. The reduction is also the barrier before
     * the aggregate. */
    int run_failed = (rc != 0 && rc != -ENODATA), n_run_failed = 0;
    if (run_failed) fprintf(stderr, "[rank %d] replica_run failed: %d\n", rank, rc);
    MPI_Allreduce(&run_failed, &n_run_failed, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    replica_aggregate(&rep, &cfg);
    if (rank == 0 && n_run_failed > 0)
        fprintf(stderr, "%d of %d replica%s failed (setup or run error); exit status 1\n",
                n_run_failed, nranks, nranks == 1 ? "" : "s");

    MPI_Finalize();
    return n_run_failed > 0 ? 1 : 0;
}
