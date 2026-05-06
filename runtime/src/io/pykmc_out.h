#ifndef LATKMC_PYKMC_OUT_H
#define LATKMC_PYKMC_OUT_H

#include <stdio.h>
#include <stdint.h>
#include "events.h"

/* Step log matching pyKMC's pykmc.out column format, so Analysis/ notebooks
 * and build_rate_table.py can read C output without modification.
 *
 * Columns (space-separated, single line per step):
 *   step  time_s  dt_s  n_vac  k_tot  k_event  Ea_eV  motif  direction
 *
 * The exact column set should be cross-referenced against pyKMC-develop's
 * real pykmc.out before M1 is declared done. */

typedef struct {
    FILE *fp;
} PykmcOutWriter;

int  pykmc_out_open(PykmcOutWriter *w, const char *path);
void pykmc_out_close(PykmcOutWriter *w);

int  pykmc_out_write_row(PykmcOutWriter *w,
                         uint64_t step, double time_s, double dt_s,
                         int32_t n_vac, double k_tot,
                         const Event *ev);

#endif /* LATKMC_PYKMC_OUT_H */
