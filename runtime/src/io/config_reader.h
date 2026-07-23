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
    double   overpotential_phi_eV;   /* electrochemical overpotential term Phi (eV); 0 = thermal only.
                                      * Subtracted from the bare barrier of electrochemical
                                      * (dissolution) Processes at startup: k = nu_E*exp(-(Ea-Phi)/kT). */
    double   dissolution_prefactor_Hz; /* optional nu_E override (Hz); 0 = use the baked value. */
    uint64_t max_dissolution_events; /* extra vacancy-list capacity to budget for dissolution events
                                      * (each dissolution is +1 vacancy). 0 = default slack only. */

    /* [surrogate] — Phase C surrogate rate channel (b). All inert on a v0.3 /
     * no-model build (the channel is compiled out). */
    int      surrogate_enable;       /* 1 = on when a model is baked (default 1) */
    double   surrogate_k_floor_Hz;   /* 0 = auto (tier0_nu0 * exp(-ea_hi/kT)) */
    double   surrogate_leverage_gate;/* 0 = model q75 */
    double   surrogate_flux_threshold; /* default 0.01 */
    uint64_t surrogate_flag_capacity; /* registry capacity; default 65536 */

    /* [validation] */
    char     rng_replay_path[512];   /* optional; empty if unused */
} InputConfig;

int input_config_load(InputConfig *out, const char *path);

#endif /* LATKMC_CONFIG_READER_H */
