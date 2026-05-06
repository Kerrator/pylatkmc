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
    int rc = input_config_load(&cfg, argv[1]);
    if (rc != 0 && rc != -ENOSYS /* pre-M1 stub */) {
        if (rank == 0) fprintf(stderr, "input_config_load failed: %d\n", rc);
        MPI_Finalize();
        return 1;
    }

    ReplicaContext rep;
    rc = replica_init(&rep, &cfg, rank, nranks);
    if (rc != 0) {
        fprintf(stderr, "[rank %d] replica_init failed: %d\n", rank, rc);
        MPI_Finalize();
        return 1;
    }

    rc = replica_run(&rep, &cfg);
    /* Pre-M1: run() returns -ENOSYS. Treat that as a successful scaffold
     * smoke test; M1 will return 0 on real completion. */
    if (rc != 0 && rc != -ENOSYS) {
        fprintf(stderr, "[rank %d] replica_run failed: %d\n", rank, rc);
    }

    MPI_Barrier(MPI_COMM_WORLD);
    replica_aggregate(&rep, &cfg);

    MPI_Finalize();
    return 0;
}
