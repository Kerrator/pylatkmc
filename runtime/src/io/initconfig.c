#include "initconfig.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kmcfmt.h"
#include "json_mini.h"

static const char INITCONFIG_MAGIC[8] = { 'K','M','C','I','C','v','0','1' };

/* Payload layout (see tools/build_initial_config.py):
 *   u32        payload_version
 *   f32[N*3]   positions
 *   i32[N+1]   nn1_offsets
 *   i32[M1]    nn1_indices
 *   i32[N+1]   nn2_offsets
 *   i32[M2]    nn2_indices
 *   i8 [N]     layer_index
 *   u8 [N]     site_class
 *   u8 [N]     initial_species
 *   u8 [M1]    nn1_dir_family
 *   u8 [M2]    nn2_dir_family
 */

int initconfig_load(const char *path, Lattice *lat_out, State *st_out)
{
    if (!path || !lat_out || !st_out) return -EINVAL;
    memset(lat_out, 0, sizeof(*lat_out));

    KmcMap map;
    int rc = kmcfmt_mmap(&map, path, INITCONFIG_MAGIC);
    if (rc != 0) return rc;

    long long n_sites_ll, n_layers_ll, nn1_count_ll, nn2_count_ll;
    long long version_ll;
    double nn_dist_d;
    double cell_d[3];

    if (json_find_int(map.header, map.header_len, "version", &version_ll) != 0 ||
        json_find_int(map.header, map.header_len, "n_sites",  &n_sites_ll) != 0 ||
        json_find_int(map.header, map.header_len, "n_layers", &n_layers_ll) != 0 ||
        json_find_int(map.header, map.header_len, "nn1_count", &nn1_count_ll) != 0 ||
        json_find_int(map.header, map.header_len, "nn2_count", &nn2_count_ll) != 0 ||
        json_find_double(map.header, map.header_len, "nn_dist", &nn_dist_d) != 0)
    {
        fprintf(stderr, "initconfig_load: missing required header fields in %s\n", path);
        kmcfmt_unmap(&map);
        return -EPROTO;
    }
    if (json_find_double_array(map.header, map.header_len, "cell", cell_d, 3) != 0) {
        /* Backward-compatible fallback for older malformed headers. */
        long long nx, ny;
        if (json_find_int(map.header, map.header_len, "nx", &nx) != 0 ||
            json_find_int(map.header, map.header_len, "ny", &ny) != 0)
        {
            kmcfmt_unmap(&map); return -EPROTO;
        }
        cell_d[0] = (double)nx * nn_dist_d;
        cell_d[1] = (double)ny * nn_dist_d;
        cell_d[2] = 2.0 * nn_dist_d;
    }

    (void)version_ll;  /* reserved for future format migrations */

    int32_t N   = (int32_t)n_sites_ll;
    int32_t M1  = (int32_t)nn1_count_ll;
    int32_t M2  = (int32_t)nn2_count_ll;
    if (N <= 0 || M1 < 0 || M2 < 0) {
        kmcfmt_unmap(&map); return -EPROTO;
    }

    /* Compute payload offsets. */
    const unsigned char *pl = (const unsigned char *)map.payload;
    size_t               pn = map.payload_len;
    size_t off = 0;
    if (off + 4 > pn) { kmcfmt_unmap(&map); return -EPROTO; }
    off += 4;  /* payload_version */

    const float   *positions       = (const float *)  (pl + off); off += (size_t)N * 3 * sizeof(float);
    const int32_t *nn1_offsets     = (const int32_t *)(pl + off); off += ((size_t)N + 1) * sizeof(int32_t);
    const int32_t *nn1_indices     = (const int32_t *)(pl + off); off += (size_t)M1 * sizeof(int32_t);
    const int32_t *nn2_offsets     = (const int32_t *)(pl + off); off += ((size_t)N + 1) * sizeof(int32_t);
    const int32_t *nn2_indices     = (const int32_t *)(pl + off); off += (size_t)M2 * sizeof(int32_t);
    const int8_t  *layer_index     = (const int8_t  *)(pl + off); off += (size_t)N;
    const uint8_t *site_class      = (const uint8_t *)(pl + off); off += (size_t)N;
    const uint8_t *initial_species = (const uint8_t *)(pl + off); off += (size_t)N;
    const uint8_t *nn1_dir_family  = (const uint8_t *)(pl + off); off += (size_t)M1;
    const uint8_t *nn2_dir_family  = (const uint8_t *)(pl + off); off += (size_t)M2;

    if (off > pn) {
        fprintf(stderr, "initconfig_load: payload truncated (need %zu, have %zu)\n", off, pn);
        kmcfmt_unmap(&map);
        return -EPROTO;
    }

    /* Sanity-check CSR. */
    if (nn1_offsets[N] != M1 || nn2_offsets[N] != M2) {
        fprintf(stderr, "initconfig_load: CSR offset/count mismatch "
                "(nn1[N]=%d vs M1=%d; nn2[N]=%d vs M2=%d)\n",
                nn1_offsets[N], M1, nn2_offsets[N], M2);
        kmcfmt_unmap(&map);
        return -EPROTO;
    }

    /* Fill Lattice. Pointers alias into the mmap (read-only). */
    lat_out->n_sites         = N;
    lat_out->n_layers        = (int32_t)n_layers_ll;
    lat_out->cell[0]         = (float)cell_d[0];
    lat_out->cell[1]         = (float)cell_d[1];
    lat_out->cell[2]         = (float)cell_d[2];
    lat_out->nn_dist         = (float)nn_dist_d;
    lat_out->positions       = (float *)  positions;
    lat_out->layer_index     = (int8_t *) layer_index;
    lat_out->site_class      = (uint8_t *)site_class;
    lat_out->nn1_offsets     = (int32_t *)nn1_offsets;
    lat_out->nn1_indices     = (int32_t *)nn1_indices;
    lat_out->nn1_dir_family  = (uint8_t *)nn1_dir_family;
    lat_out->nn2_offsets     = (int32_t *)nn2_offsets;
    lat_out->nn2_indices     = (int32_t *)nn2_indices;
    lat_out->nn2_dir_family  = (uint8_t *)nn2_dir_family;
    lat_out->_mmap_base      = map.base;
    lat_out->_mmap_size      = map.size;

    /* Count vacancies to size State. */
    int32_t n_vac_initial = 0;
    for (int32_t s = 0; s < N; ++s) {
        if (initial_species[s] == 0 /* SP_VACANT */) n_vac_initial++;
    }
    /* Budget some slack for future vacancies arising from exchanges
     * (M2+). For M1 the count never changes. */
    int32_t n_vac_max = n_vac_initial > 0 ? n_vac_initial + 4 : 4;

    int scode = state_alloc(st_out, N, n_vac_max);
    if (scode != 0) {
        kmcfmt_unmap(&map);
        lat_out->_mmap_base = NULL;
        return scode;
    }
    memcpy(st_out->species, initial_species, (size_t)N);
    int32_t v = 0;
    for (int32_t s = 0; s < N; ++s) {
        if (st_out->species[s] == 0 /* SP_VACANT */) {
            st_out->vac_list[v] = s;
            st_out->vac_idx_of[s] = v;
            v++;
        }
    }
    st_out->n_vac = v;
    st_out->time_s = 0.0;
    st_out->step   = 0;

    return 0;
}
