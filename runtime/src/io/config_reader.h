#ifndef LATKMC_CONFIG_READER_H
#define LATKMC_CONFIG_READER_H

#include <stdint.h>
#include <stddef.h>

/* INI-style input file for one run. See the input.ini under any
 * examples/ subdirectory. Minimal parser (no deps): [section] and key = value. */

typedef struct {
    /* [run] */
    uint64_t max_steps;
    double   max_time_s;
    uint64_t sample_every;
    uint64_t summary_every;
    uint64_t base_seed;

    /* [paths] */
    char     ratetable_path[512];
    char     initconfig_path[512];
    char     output_root[512];       /* default: "./output" */

    /* [physics] */
    double   temperature_K;          /* must match rate table; checked at load */

    /* [validation] */
    char     rng_replay_path[512];   /* optional; empty if unused */
} InputConfig;

int input_config_load(InputConfig *out, const char *path);

#endif /* LATKMC_CONFIG_READER_H */
