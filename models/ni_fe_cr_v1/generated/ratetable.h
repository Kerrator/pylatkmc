/* ratetable.h — GENERATED for model 'ni_fe_cr_v1'.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build models/ni_fe_cr_v1.kmcspec.toml`.
 *
 * N-axis flat-cube key. N = 9 for this model:
 *   axis 'site_class': max 3, stride 234375
 *   axis 'direction': max 5, stride 46875
 *   axis 'mover_species': max 3, stride 15625
 *   axis 'n_vac_nn1': max 5, stride 3125
 *   axis 'n_Fe_nn1': max 5, stride 625
 *   axis 'n_Cr_nn1': max 5, stride 125
 *   axis 'n_vac_nn2': max 5, stride 25
 *   axis 'n_Fe_nn2': max 5, stride 5
 *   axis 'n_Cr_nn2': max 5, stride 1
 *   cube size = 703125 entries
 *
 * Binary file magic: "KMCRTv01". JSON header fields (all integers, little-endian):
 *   - n_axes, n_entries, temperature_K, k0_Hz, model_name
 *   - strides[]              (length n_axes)
 *   - axis_maxes[]           (length n_axes)
 *   - axis_names[]           (length n_axes, string array)
 *   - motif_of_class_dir[]   (length n_classes * n_dirs)
 * Payload (after header):
 *   u32    n_entries
 *   f32[n] rate_s_inv
 *   f32[n] Ea_eV
 *   u32[n] count (provenance: 0 => filled by fallback)
 */
#ifndef PYLATKMC_RATETABLE_H
#define PYLATKMC_RATETABLE_H

#include <stdint.h>
#include <stddef.h>
#include "events.h"

/* Opaque-ish handle — callers should use the accessors below, not peek inside. */
typedef struct RateTable {
    float    temperature_K;
    float    k0_Hz;

    int32_t  n_axes;                  /* always 9 for this model */
    int32_t  n_entries;
    int32_t  strides[9];
    int32_t  axis_maxes[9];

    const float    *rate;             /* [n_entries] pre-exponentiated */
    const float    *Ea_eV;            /* [n_entries] for logging */
    const uint32_t *count;            /* [n_entries] provenance */

    /* [n_classes * n_dirs] motif enum per (site_class, direction) — for
     * logging / pykmc.out parity. Heap-allocated copy of the JSON field. */
    uint8_t *motif_of_class_dir;
    int32_t  motif_lookup_len;

    void    *_mmap_base;
    size_t   _mmap_size;
} RateTable;

int  ratetable_load(RateTable *out, const char *path);
void ratetable_free(RateTable *rt);

/* Key construction. `k` carries the N axis values (see RateKey in events.h);
 * strides are read from the RateTable. Inlined for the hot path. */
static inline int32_t ratetable_key(const RateTable *rt, const RateKey *k) {
    return
        (int32_t)k->site_class * rt->strides[0]
      + (int32_t)k->direction * rt->strides[1]
      + (int32_t)k->mover_species * rt->strides[2]
      + (int32_t)k->n_vac_nn1 * rt->strides[3]
      + (int32_t)k->n_Fe_nn1 * rt->strides[4]
      + (int32_t)k->n_Cr_nn1 * rt->strides[5]
      + (int32_t)k->n_vac_nn2 * rt->strides[6]
      + (int32_t)k->n_Fe_nn2 * rt->strides[7]
      + (int32_t)k->n_Cr_nn2 * rt->strides[8]
    ;
}

static inline float    ratetable_rate    (const RateTable *rt, int32_t key) { return rt->rate [key]; }
static inline float    ratetable_barrier (const RateTable *rt, int32_t key) { return rt->Ea_eV[key]; }
static inline uint32_t ratetable_count   (const RateTable *rt, int32_t key) { return rt->count[key]; }

/* Motif lookup by (site_class, direction). Always-safe even if the JSON
 * motif_of_class_dir is shorter than expected (returns MF_UNRESOLVED). */
static inline MotifFamily ratetable_motif(const RateTable *rt,
                                           SiteClass sc, DirectionFamily dir) {
    int32_t idx = (int32_t)sc * (int32_t)DF_COUNT + (int32_t)dir;
    if (idx < 0 || idx >= rt->motif_lookup_len) return MF_UNRESOLVED;
    return (MotifFamily)rt->motif_of_class_dir[idx];
}

#endif /* PYLATKMC_RATETABLE_H */
