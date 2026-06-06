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
    char     ratetable_path[512];    /* DEPRECATED/unused: v0.2 loaded a baked .kmcrt
                                      * rate cube here. In v0.3 rates are compiled into the
                                      * generated proclist (prefactor+Ea) and evaluated at
                                      * runtime T, so the runtime never reads this. Parsed
                                      * only so existing .ini files don't warn; remove with
                                      * the example .ini files in a future cleanup. */
    char     initconfig_path[512];
    char     output_root[512];       /* default: "./output" */

    /* [physics] */
    double   temperature_K;          /* runtime Arrhenius T; rates computed from it at startup */

    /* [validation] */
    char     rng_replay_path[512];   /* optional; empty if unused */
} InputConfig;

int input_config_load(InputConfig *out, const char *path);

#endif /* LATKMC_CONFIG_READER_H */
