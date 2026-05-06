#include "pykmc_out.h"

#include <errno.h>
#include <string.h>

int pykmc_out_open(PykmcOutWriter *w, const char *path)
{
    if (!w || !path) return -EINVAL;
    memset(w, 0, sizeof(*w));
    w->fp = fopen(path, "w");
    if (!w->fp) return -errno;
    /* Column header. v0.2 schema; see pykmc_out.h for the column meanings. */
    fputs("# step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site\n", w->fp);
    return 0;
}

void pykmc_out_close(PykmcOutWriter *w)
{
    if (!w || !w->fp) return;
    fclose(w->fp);
    w->fp = NULL;
}

int pykmc_out_write_row(PykmcOutWriter *w,
                        uint64_t step, double time_s, double dt_s,
                        int32_t n_vac, double k_tot,
                        double k_event, double Ea_eV,
                        int32_t proc_id, int32_t site)
{
    if (!w || !w->fp) return -EINVAL;
    fprintf(w->fp,
            "%llu %.9e %.6e %d %.6e %.6e %.4f %d %d\n",
            (unsigned long long)step,
            time_s, dt_s, n_vac,
            k_tot, k_event, Ea_eV,
            proc_id, site);
    return 0;
}
