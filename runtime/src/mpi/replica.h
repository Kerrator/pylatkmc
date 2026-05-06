#ifndef LATKMC_REPLICA_H
#define LATKMC_REPLICA_H

#include <stdint.h>
#include "../io/config_reader.h"

/* Per-replica terminal statistics. Fixed layout so MPI_Gather can treat it
 * as MPI_BYTE without a custom datatype — all ranks use the same compiler
 * and ABI. */
typedef struct {
    int      rank;
    int      run_rc;
    uint64_t n_steps;
    double   total_time_s;
    double   mean_msd_A2;
    uint64_t motif_counts[8];
    uint64_t direction_counts[5];
} ReplicaStats;

typedef struct {
    int            rank;
    int            nranks;
    char           out_dir[512];    /* "${output_root}/replica_NNNN" */
    ReplicaStats   stats;
} ReplicaContext;

int replica_init(ReplicaContext *rep, const InputConfig *cfg, int rank, int nranks);

/* Runs one replica. On return, rep->stats is populated. */
int replica_run(ReplicaContext *rep, const InputConfig *cfg);

/* Collective. Rank 0 gathers per-replica stats and writes
 * ${output_root}/aggregate_summary.json. */
int replica_aggregate(ReplicaContext *rep, const InputConfig *cfg);

#endif /* LATKMC_REPLICA_H */
