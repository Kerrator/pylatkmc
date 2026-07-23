#ifndef LATKMC_PHASEC_OUT_H
#define LATKMC_PHASEC_OUT_H

#include <stdio.h>
#include <stdint.h>

/* Phase C surrogate-channel step log (first-class contract output, memo §8-N5).
 * Columns (space-delimited, 8):
 *   step k_flag_frac_inst k_flag_frac_cum n_surr_inst n_surr_fired n_meas_fired
 *        v6_absresid_mean v6_absresid_max
 * Written at the sample_every cadence, alongside (never replacing) pykmc.out. */

typedef struct { FILE *fp; } PhasecOutWriter;

int  phasec_out_open(PhasecOutWriter *w, const char *path);
void phasec_out_close(PhasecOutWriter *w);
int  phasec_out_write_row(PhasecOutWriter *w,
                          uint64_t step,
                          double k_flag_frac_inst, double k_flag_frac_cum,
                          int32_t n_surr_inst,
                          uint64_t n_surr_fired, uint64_t n_meas_fired,
                          double v6_mean, double v6_max);

#endif /* LATKMC_PHASEC_OUT_H */
