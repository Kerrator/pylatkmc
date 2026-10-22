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
    int init_ok = (rc == 0 || rc == -ENOSYS /* pre-M1 stub */);
    if (!init_ok) {
        fprintf(stderr, "[rank %d] input_config_load failed: %d\n", rank, rc);
    } else {
        rc = replica_init(&rep, &cfg, rank, nranks);
        init_ok = (rc == 0);
        if (!init_ok) fprintf(stderr, "[rank %d] replica_init failed: %d\n", rank, rc);
    }
    /* Agree on the init status before anyone runs: a rank that bailed out
     * alone would leave the others blocked in MPI_Gather (replica_aggregate)
     * until walltime. */
    MPI_Allreduce(MPI_IN_PLACE, &init_ok, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
    if (!init_ok) {
        if (rank == 0)
            fprintf(stderr, "initialisation failed on at least one rank; no replica ran\n");
        MPI_Finalize();
        return 1;
    }

    rc = replica_run(&rep, &cfg);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] replica_run failed: %d\n", rank, rc);
    }

    /* Process exit status (sweeps, job queues): a replica that completed or
     * trapped (-ENODATA: no event left, a normal physical end) succeeds; a
     * setup or run failure on ANY rank fails the job, on every rank. */
    int failed = (rc != 0 && rc != -ENODATA);
    MPI_Allreduce(MPI_IN_PLACE, &failed, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    replica_aggregate(&rep, &cfg);

    MPI_Finalize();
    return failed ? 1 : 0;
}
