#include "phasec_out.h"

#include <errno.h>
#include <string.h>

int phasec_out_open(PhasecOutWriter *w, const char *path)
{
    if (!w || !path) return -EINVAL;
    memset(w, 0, sizeof(*w));
    w->fp = fopen(path, "w");
    if (!w->fp) return -errno;
    fputs("# step k_flag_frac_inst k_flag_frac_cum n_surr_inst "
          "n_surr_fired n_meas_fired v6_absresid_mean v6_absresid_max\n", w->fp);
    return 0;
}

void phasec_out_close(PhasecOutWriter *w)
{
    if (!w || !w->fp) return;
    fclose(w->fp);
    w->fp = NULL;
}

int phasec_out_write_row(PhasecOutWriter *w,
                         uint64_t step,
                         double k_flag_frac_inst, double k_flag_frac_cum,
                         int32_t n_surr_inst,
                         uint64_t n_surr_fired, uint64_t n_meas_fired,
                         double v6_mean, double v6_max)
{
    if (!w || !w->fp) return -EINVAL;
    fprintf(w->fp, "%llu %.6e %.6e %d %llu %llu %.6e %.6e\n",
            (unsigned long long)step, k_flag_frac_inst, k_flag_frac_cum,
            n_surr_inst, (unsigned long long)n_surr_fired,
            (unsigned long long)n_meas_fired, v6_mean, v6_max);
    return 0;
}
