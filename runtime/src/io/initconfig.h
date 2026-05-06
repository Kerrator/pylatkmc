#ifndef LATKMC_INITCONFIG_H
#define LATKMC_INITCONFIG_H

#include "lattice.h"
#include "state.h"

/* Binary initial-config (.kmcinit) layout:
 *   u8[8]   magic = "KMCICv01"
 *   u32     header_bytes
 *   u8[H]   JSON header (UTF-8):
 *             {"version":1, "n_sites":N, "n_layers":L, "cell":[Lx,Ly,Lz],
 *              "nn_dist":D, "n_elements":E, "element_names":[...]}
 *   packed payload:
 *     f32[N*3]  positions
 *     i8[N]     layer_index
 *     u8[N]     site_class
 *     u8[N]     initial_species
 *     i32[N+1]  nn1_offsets
 *     i32[M1]   nn1_indices       (M1 = nn1_offsets[N])
 *     u8[M1]    nn1_dir_family
 *     i32[N+1]  nn2_offsets
 *     i32[M2]   nn2_indices
 *     u8[M2]    nn2_dir_family
 *
 * C mmaps the file PROT_READ; Lattice and initial species pointers alias into
 * the mapping.
 */

/* Loads lattice topology AND initial species array. Caller owns State's
 * dynamic buffers (vac_list, vac_idx_of, unwrapped_ijk); initial species are
 * copied from the mmap into st->species so the state is freely mutable. */
int initconfig_load(const char *path, Lattice *lat_out, State *st_out);

#endif /* LATKMC_INITCONFIG_H */
