#ifndef LATKMC_PYKMC_OUT_H
#define LATKMC_PYKMC_OUT_H

#include <stdio.h>
#include <stdint.h>

/* Step log for pylatkmc v0.2. Columns:
 *   step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site
 *
 * v0.2 changes from the M1 cube version:
 *   - The old `motif` and `direction` columns are removed (cube-era key
 *     enums; superseded by per-Process identity).
 *   - `proc_id` (the P_<name> integer index from proclist.h) replaces
 *     them. To map back to a human-readable Process name, cross-reference
 *     proclist.c's `enum { P_<name>, ... }` for the model.
 *   - `site` is the absolute anchor site index where the event fired.
 */

typedef struct {
    FILE *fp;
} PykmcOutWriter;

int  pykmc_out_open(PykmcOutWriter *w, const char *path);
void pykmc_out_close(PykmcOutWriter *w);

int  pykmc_out_write_row(PykmcOutWriter *w,
                         uint64_t step, double time_s, double dt_s,
                         int32_t n_vac, double k_tot,
                         double k_event, double Ea_eV,
                         int32_t proc_id, int32_t site);

#endif /* LATKMC_PYKMC_OUT_H */
