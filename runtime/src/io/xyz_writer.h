#ifndef LATKMC_XYZ_WRITER_H
#define LATKMC_XYZ_WRITER_H

#include <stdio.h>
#include "lattice.h"
#include "state.h"

/* Streaming Extended-XYZ writer matching pyKMC's trajkmc.xyz format.
 * Header example:
 *   N_ATOMS
 *   Lattice="Lx 0 0 0 Ly 0 0 0 Lz" Properties=species:S:1:pos:R:3:id:I:1 \
 *     time=1.234e-5 step=42 Temperature=500.0
 *   Ni  0.000  0.000  0.000  1
 *   Ni  2.492  0.000  0.000  2
 *   ...
 *
 * Vacancies are omitted (pyKMC convention: only atoms are written).
 */

typedef struct {
    FILE *fp;
    const Lattice *lat;
    double temperature_K;
    const char *element_names[8]; /* index by Species enum */
} XyzWriter;

int  xyz_open(XyzWriter *w, const char *path, const Lattice *lat, double T_K);
void xyz_close(XyzWriter *w);

int  xyz_write_frame(XyzWriter *w, const State *st);

#endif /* LATKMC_XYZ_WRITER_H */
