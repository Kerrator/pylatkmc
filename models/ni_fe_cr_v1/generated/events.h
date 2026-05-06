/* events.h — GENERATED for model 'ni_fe_cr_v1'.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build models/ni_fe_cr_v1.kmcspec.toml`.
 *
 * This file replaces the scaffold stub in runtime/src/core/events.h via the
 * CMake include-path order (generated/ is searched first).
 */
#ifndef PYLATKMC_EVENTS_H
#define PYLATKMC_EVENTS_H

#include <stdint.h>
#include "events_base.h"   /* Species, SiteClass, DirectionFamily, MotifFamily */

/* Per-model rate-table key. Fields match ModelSpec.all_axes() order, which
 * is what ratetable_key() below expects. Tightly packed to 1 byte per field
 * because every axis's max fits in uint8_t (ModelSpec caps max at pylatkmc.spec.MAX_COUNT_CAP). */
typedef struct RateKey {
    uint8_t site_class;
    uint8_t direction;
    uint8_t mover_species;
    uint8_t n_vac_nn1;
    uint8_t n_Fe_nn1;
    uint8_t n_Cr_nn1;
    uint8_t n_vac_nn2;
    uint8_t n_Fe_nn2;
    uint8_t n_Cr_nn2;
} RateKey;

/* Event emitted by avail_rebuild_all. The runtime (kmc.c, pykmc_out.c) only
 * reads the base fields. The RateKey below is carried alongside for logging
 * and debug dumps — it's not touched by the hot path. */
typedef struct Event {
    EVENT_BASE_FIELDS
    RateKey key;
} Event;

/* Compile-time constants derived from the spec. Exposed so tests / tools
 * can cross-check the shape without re-parsing the JSON header. */
#define PYLATKMC_MODEL_NAME "ni_fe_cr_v1"
#define PYLATKMC_N_AXES     9
#define PYLATKMC_CUBE_SIZE  703125

#endif /* PYLATKMC_EVENTS_H */
