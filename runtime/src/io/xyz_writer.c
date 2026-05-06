#include "xyz_writer.h"

#include <errno.h>
#include <string.h>

#include "events_base.h"   /* Species enum (SP_VACANT, SP_NI, SP_FE, SP_CR) */

int xyz_open(XyzWriter *w, const char *path, const Lattice *lat, double T_K)
{
    if (!w || !path || !lat) return -EINVAL;
    memset(w, 0, sizeof(*w));
    w->fp = fopen(path, "w");
    if (!w->fp) return -errno;
    w->lat           = lat;
    w->temperature_K = T_K;
    w->element_names[0] = "X";  /* vacancies are omitted from frames */
    w->element_names[1] = "Ni";
    w->element_names[2] = "Fe";
    w->element_names[3] = "Cr";
    return 0;
}

void xyz_close(XyzWriter *w)
{
    if (!w || !w->fp) return;
    fclose(w->fp);
    w->fp = NULL;
}

int xyz_write_frame(XyzWriter *w, const State *st)
{
    if (!w || !w->fp || !w->lat || !st) return -EINVAL;
    const Lattice *lat = w->lat;

    /* Count atoms (non-vacant sites). */
    int32_t n_atoms = 0;
    for (int32_t s = 0; s < lat->n_sites; ++s) {
        if (st->species[s] != SP_VACANT) n_atoms++;
    }

    fprintf(w->fp, "%d\n", n_atoms);
    /* Extended-XYZ header: orthorhombic cell, species:pos:id. */
    fprintf(w->fp,
            "Lattice=\"%.6f 0.0 0.0 0.0 %.6f 0.0 0.0 0.0 %.6f\" "
            "Properties=species:S:1:pos:R:3:id:I:1 "
            "time=%.9e step=%llu Temperature=%.3f\n",
            (double)lat->cell[0], (double)lat->cell[1], (double)lat->cell[2],
            st->time_s, (unsigned long long)st->step, w->temperature_K);

    for (int32_t s = 0; s < lat->n_sites; ++s) {
        uint8_t sp = st->species[s];
        if (sp == SP_VACANT) continue;
        const char *name = (sp < 8 && w->element_names[sp]) ? w->element_names[sp] : "X";
        fprintf(w->fp, "%-2s %12.6f %12.6f %12.6f %d\n",
                name,
                (double)lat->positions[3 * s + 0],
                (double)lat->positions[3 * s + 1],
                (double)lat->positions[3 * s + 2],
                s + 1);
    }
    return 0;
}
