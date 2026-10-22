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

    /* Agree on startup collectively: a rank that failed alone and exited
     * would leave the others blocked in the collectives after their runs
     * (the job hangs until walltime). If any rank failed, all exit non-zero
     * before running. */
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
    /* A replica that completed or trapped (-ENODATA: no event left, a normal
     * physical end; kmc_run reports it) exits cleanly — as does the pre-M1
     * -ENOSYS scaffold stub. Any other failure (a setup error such as ENOMEM
     * or an unreadable initconfig, or a failed step) makes every rank exit
     * non-zero so sweeps and job queues see it. The reduction also serves as
     * the barrier before the aggregate. */
    int run_failed = (rc != 0 && rc != -ENOSYS && rc != -ENODATA), n_run_failed = 0;
    if (run_failed) fprintf(stderr, "[rank %d] replica_run failed: %d\n", rank, rc);
    MPI_Allreduce(&run_failed, &n_run_failed, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
    replica_aggregate(&rep, &cfg);

    MPI_Finalize();
    return n_run_failed > 0 ? 1 : 0;
}
