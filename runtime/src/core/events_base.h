/* events_base.h — stable base for generated events.h (per-model).
 *
 * Every model's generated events.h starts with `#include "events_base.h"` and
 * then adds model-specific fields (e.g. species counts per shell) to the Event
 * struct and extra enum values to SiteClass / DirectionFamily if needed.
 *
 * Everything in this file MUST stay stable across models. Anything model-
 * specific lives in the generated events.h.
 *
 * pylatkmc M1 scaffolding (2026-04-19).
 */
#ifndef PYLATKMC_EVENTS_BASE_H
#define PYLATKMC_EVENTS_BASE_H

#include <stdint.h>

/* Species enum — extended only when a new element is added to the codebase-
 * wide Species namespace (rare). Individual models subset this list via
 * ModelSpec.species. Values MUST match the integer codes used by initconfig.c
 * and xyz_writer.c. */
typedef enum {
    SP_VACANT = 0,
    SP_NI     = 1,
    SP_FE     = 2,
    SP_CR     = 3,
    SP_COUNT
} Species;

/* Site class and direction family are the two permanent key axes. All other
 * axes (n_vac_*, n_<element>_*) are model-specific and live in the generated
 * events.h / ratetable.h. */
typedef enum {
    SC_SURFACE    = 0,
    SC_SUBSURFACE = 1,
    SC_BULK_LIKE  = 2,
    SC_COUNT
} SiteClass;

typedef enum {
    DF_110_INPLANE    = 0,
    DF_100_INPLANE    = 1,
    DF_111_INTERLAYER = 2,
    DF_001_EXCHANGE   = 3,
    DF_UNRESOLVED     = 4,
    DF_COUNT
} DirectionFamily;

/* Motif family — present for logging / pykmc.out parity with latkmc v1.
 * Derived deterministically from (site_class, direction) for single-vacancy
 * hops; stored in the .kmcrt header's motif_of_class_dir[] lookup. */
typedef enum {
    MF_SURFACE_1NN             = 0,
    MF_SURFACE_2NN             = 1,
    MF_SUBSURFACE_1NN          = 2,
    MF_SURF_SUBSURF_EXCHANGE   = 3,
    MF_INTERLAYER              = 4,
    MF_SUBSURFACE_EXCHANGE     = 5,
    MF_CONCERTED_3D            = 6,
    MF_UNRESOLVED              = 7,
    MF_COUNT
} MotifFamily;

/* Base Event fields. Generated events.h extends this via an EVENT_FIELDS_MODEL
 * macro so codegen can inject species-count fields without forking the type
 * for every model. See generated events.h for the full Event definition. */
#define EVENT_BASE_FIELDS                  \
    int32_t vac_origin;   /* vacant site */  \
    int32_t vac_dest;     /* occupied neighbor */ \
    uint8_t motif;                         \
    uint8_t direction;                     \
    uint8_t site_class;                    \
    uint8_t _pad0;                         \
    float   Ea_eV;                         \
    double  rate_s_inv;

#endif /* PYLATKMC_EVENTS_BASE_H */
