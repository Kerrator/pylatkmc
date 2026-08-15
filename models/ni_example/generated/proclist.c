/* proclist.c — GENERATED from ni_example.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build ni_example.kmcspec.toml`.
 *
 * This file is the heart of the pylatkmc v2 pattern-DB runtime: it
 * bundles the per-model Process catalogue (translated from the curated
 * FCC family CSV) into a single C compilation unit consumed by the
 * runtime backbone in `runtime/src/core/`.
 *
 * Contents (in order):
 *   1. enum { P_<name>, ..., N_PROCS }      — Process IDs
 *   2. static const RateConst rate_table[]   — per-proc {prefactor_Hz, Ea_eV}.
 *      The Arrhenius rate is computed by the runtime at startup from the
 *      *runtime* temperature (physics.temperature_K), NOT baked here. The
 *      prefactor is the per-family Vineyard ν₀ (style=htst) or the global
 *      k0 = 1.000e+13 Hz fallback. Spec reference T = 500.0 K.
 *   3. static HopOutcome apply_actions_<name>(...)  — one per Process
 *      (calls state_apply_actions on a StateAction[] from each Process's
 *      actions list)
 *   4. static const ApplyFn apply_table[N_PROCS]    — dispatch table
 *   5. void touchup_a(lat, st, as, site)            — decision tree
 *
 * The runtime calls `touchup_a(...)` for each active site in
 * active_filter to enrol firing Processes via avail_sites_add. After
 * BKL selects (proc, site), the runtime calls apply_table[proc](st, lat,
 * site) to apply the actions atomically.
 */
#include <stdint.h>

#include "events_base.h"     /* SP_VACANT, SP_NI, SP_FE, SP_CR */
#include "coord_codes.h"     /* NeighbourCode enum, N_NEIGHBOUR_CODES */
#include "lattice.h"         /* struct Lattice */
#include "state.h"           /* struct State, StateAction, state_apply_actions */
#include "avail_sites.h"     /* AvailSites, avail_sites_add */

enum {
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni,
    P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni,
    P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni,
    P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni,
    P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni,
    P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni,
    P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni,
    P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni,
    P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni,
    P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni,
    P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni,
    P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni,
    P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni,
    P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni,
    P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni,
    P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni,
    P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni,
    P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni,
    P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni,
    P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni,
    P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni,
    P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni,
    P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni,
    P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni,
    P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni,
    P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni,
    P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni,
    P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni,
    P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni,
    P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni,
    P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni,
    P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni,
    P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni,
    P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni,
    P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni,
    P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni,
    P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni,
    P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni,
    P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni,
    P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni,
    P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni,
    P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni,
    P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni,
    P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni,
    P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni,
    P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni,
    P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni,
    P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni,
    P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni,
    P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni,
    P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni,
    P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni,
    P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni,
    P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni,
    P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni,
    P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni,
    P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni,
    P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni,
    P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni,
    P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni,
    P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni,
    P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni,
    P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni,
    P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni,
    P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni,
    P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni,
    P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni,
    P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni,
    P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni,
    P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni,
    P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni,
    P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni,
    P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni,
    P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni,
    P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni,
    P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni,
    P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni,
    P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni,
    P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni,
    P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni,
    P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni,
    P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni,
    P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni,
    P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni,
    P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni,
    P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni,
    P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni,
    P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni,
    P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni,
    P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni,
    P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni,
    P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni,
    P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni,
    P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni,
    P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni,
    P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni,
    P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni,
    P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni,
    P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni,
    P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni,
    P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni,
    P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni,
    P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni,
    P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni,
    P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni,
    P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni,
    P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni,
    P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni,
    P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni,
    P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni,
    P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni,
    P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni,
    P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni,
    P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni,
    P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni,
    P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni,
    P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni,
    P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni,
    P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni,
    P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni,
    P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni,
    P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni,
    P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni,
    P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni,
    P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni,
    P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni,
    N_PROCS
};

typedef struct { double prefactor_Hz; double Ea_eV; int32_t is_electrochemical; int32_t _pad; } RateConst;
_Static_assert(sizeof(RateConst) == 24, "RateConst layout drift vs proclist.h");
static const RateConst rate_table[N_PROCS] = {
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 7.8815317534e+12, .Ea_eV = 0.708300, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 1.1495715134e+13, .Ea_eV = 0.574193, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 9.2268737707e+12, .Ea_eV = 0.694438, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni] = { .prefactor_Hz = 1.4087452203e+13, .Ea_eV = 0.279623, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 1.2404124079e+13, .Ea_eV = 0.840059, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 1.6313262119e+13, .Ea_eV = 0.239903, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni] = { .prefactor_Hz = 1.6486049136e+13, .Ea_eV = 0.353529, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni] = { .prefactor_Hz = 1.5296765451e+13, .Ea_eV = 0.405460, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni] = { .prefactor_Hz = 1.9971617510e+13, .Ea_eV = 0.283871, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni] = { .prefactor_Hz = 1.2729133453e+13, .Ea_eV = 0.360221, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni] = { .prefactor_Hz = 1.0055510290e+13, .Ea_eV = 0.343456, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni] = { .prefactor_Hz = 2.5319576760e+13, .Ea_eV = 0.624098, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.959316, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni] = { .prefactor_Hz = 4.1499899794e+13, .Ea_eV = 1.019142, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni] = { .prefactor_Hz = 3.4128693046e+13, .Ea_eV = 1.079435, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni] = { .prefactor_Hz = 4.9564757728e+13, .Ea_eV = 1.065028, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.047967, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni] = { .prefactor_Hz = 3.6960324556e+12, .Ea_eV = 0.977451, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.049074, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.989225, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 1.070290, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni] = { .prefactor_Hz = 1.5060286067e+13, .Ea_eV = 1.016652, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 1.5060286067e+13, .Ea_eV = 1.016652, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni] = { .prefactor_Hz = 1.5060286067e+13, .Ea_eV = 1.016652, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni] = { .prefactor_Hz = 1.5060286067e+13, .Ea_eV = 1.016652, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.5775084314e+13, .Ea_eV = 0.744886, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.5775084314e+13, .Ea_eV = 0.744886, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.5775084314e+13, .Ea_eV = 0.744886, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.5775084314e+13, .Ea_eV = 0.744886, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni] = { .prefactor_Hz = 1.4511147960e+13, .Ea_eV = 0.704985, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 1.4511147960e+13, .Ea_eV = 0.704985, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni] = { .prefactor_Hz = 1.4511147960e+13, .Ea_eV = 0.704985, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni] = { .prefactor_Hz = 1.4511147960e+13, .Ea_eV = 0.704985, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni] = { .prefactor_Hz = 1.2902636083e+13, .Ea_eV = 0.542741, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 1.2902636083e+13, .Ea_eV = 0.542741, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni] = { .prefactor_Hz = 1.2902636083e+13, .Ea_eV = 0.542741, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni] = { .prefactor_Hz = 1.2902636083e+13, .Ea_eV = 0.542741, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni] = { .prefactor_Hz = 1.3093685319e+13, .Ea_eV = 0.645644, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 1.3093685319e+13, .Ea_eV = 0.645644, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni] = { .prefactor_Hz = 1.3093685319e+13, .Ea_eV = 0.645644, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni] = { .prefactor_Hz = 1.3093685319e+13, .Ea_eV = 0.645644, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = { .prefactor_Hz = 1.4820364436e+13, .Ea_eV = 0.861801, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 1.4820364436e+13, .Ea_eV = 0.861801, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = { .prefactor_Hz = 1.4820364436e+13, .Ea_eV = 0.861801, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = { .prefactor_Hz = 1.4820364436e+13, .Ea_eV = 0.861801, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni] = { .prefactor_Hz = 1.6864904526e+13, .Ea_eV = 0.818640, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 1.6864904526e+13, .Ea_eV = 0.818640, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni] = { .prefactor_Hz = 1.6864904526e+13, .Ea_eV = 0.818640, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni] = { .prefactor_Hz = 1.6864904526e+13, .Ea_eV = 0.818640, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni] = { .prefactor_Hz = 2.6919979564e+13, .Ea_eV = 0.933076, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 2.6919979564e+13, .Ea_eV = 0.933076, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni] = { .prefactor_Hz = 2.6919979564e+13, .Ea_eV = 0.933076, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni] = { .prefactor_Hz = 2.6919979564e+13, .Ea_eV = 0.933076, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni] = { .prefactor_Hz = 8.8229804391e+12, .Ea_eV = 0.459258, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 8.8229804391e+12, .Ea_eV = 0.459258, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni] = { .prefactor_Hz = 8.8229804391e+12, .Ea_eV = 0.459258, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni] = { .prefactor_Hz = 8.8229804391e+12, .Ea_eV = 0.459258, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = { .prefactor_Hz = 7.9974822382e+12, .Ea_eV = 0.563119, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 7.9974822382e+12, .Ea_eV = 0.563119, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = { .prefactor_Hz = 7.9974822382e+12, .Ea_eV = 0.563119, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = { .prefactor_Hz = 7.9974822382e+12, .Ea_eV = 0.563119, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni] = { .prefactor_Hz = 8.1147539000e+12, .Ea_eV = 0.661529, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 8.1147539000e+12, .Ea_eV = 0.661529, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni] = { .prefactor_Hz = 8.1147539000e+12, .Ea_eV = 0.661529, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni] = { .prefactor_Hz = 8.1147539000e+12, .Ea_eV = 0.661529, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni] = { .prefactor_Hz = 6.1178876039e+12, .Ea_eV = 0.683615, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 6.1178876039e+12, .Ea_eV = 0.683615, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni] = { .prefactor_Hz = 6.1178876039e+12, .Ea_eV = 0.683615, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni] = { .prefactor_Hz = 6.1178876039e+12, .Ea_eV = 0.683615, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = { .prefactor_Hz = 6.0827564138e+12, .Ea_eV = 0.305965, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 6.0827564138e+12, .Ea_eV = 0.305965, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = { .prefactor_Hz = 6.0827564138e+12, .Ea_eV = 0.305965, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = { .prefactor_Hz = 6.0827564138e+12, .Ea_eV = 0.305965, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = { .prefactor_Hz = 5.2022574282e+12, .Ea_eV = 0.256501, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 5.2022574282e+12, .Ea_eV = 0.256501, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = { .prefactor_Hz = 5.2022574282e+12, .Ea_eV = 0.256501, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = { .prefactor_Hz = 5.2022574282e+12, .Ea_eV = 0.256501, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni] = { .prefactor_Hz = 4.5254055435e+12, .Ea_eV = 0.325098, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 4.5254055435e+12, .Ea_eV = 0.325098, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni] = { .prefactor_Hz = 4.5254055435e+12, .Ea_eV = 0.325098, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni] = { .prefactor_Hz = 4.5254055435e+12, .Ea_eV = 0.325098, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni] = { .prefactor_Hz = 7.1547207311e+12, .Ea_eV = 0.434463, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 7.1547207311e+12, .Ea_eV = 0.434463, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni] = { .prefactor_Hz = 7.1547207311e+12, .Ea_eV = 0.434463, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni] = { .prefactor_Hz = 7.1547207311e+12, .Ea_eV = 0.434463, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni] = { .prefactor_Hz = 1.0323502899e+13, .Ea_eV = 0.699130, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni] = { .prefactor_Hz = 1.0323502899e+13, .Ea_eV = 0.699130, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni] = { .prefactor_Hz = 1.0323502899e+13, .Ea_eV = 0.699130, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni] = { .prefactor_Hz = 1.0323502899e+13, .Ea_eV = 0.699130, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni] = { .prefactor_Hz = 1.0596116969e+13, .Ea_eV = 0.210636, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni] = { .prefactor_Hz = 1.0596116969e+13, .Ea_eV = 0.210636, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni] = { .prefactor_Hz = 1.0596116969e+13, .Ea_eV = 0.210636, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni] = { .prefactor_Hz = 1.0596116969e+13, .Ea_eV = 0.210636, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = { .prefactor_Hz = 7.3096029650e+12, .Ea_eV = 0.166569, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = { .prefactor_Hz = 7.3096029650e+12, .Ea_eV = 0.166569, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = { .prefactor_Hz = 7.3096029650e+12, .Ea_eV = 0.166569, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = { .prefactor_Hz = 7.3096029650e+12, .Ea_eV = 0.166569, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = { .prefactor_Hz = 5.6339683037e+12, .Ea_eV = 0.219400, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = { .prefactor_Hz = 5.6339683037e+12, .Ea_eV = 0.219400, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = { .prefactor_Hz = 5.6339683037e+12, .Ea_eV = 0.219400, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = { .prefactor_Hz = 5.6339683037e+12, .Ea_eV = 0.219400, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = { .prefactor_Hz = 4.7086757895e+12, .Ea_eV = 0.335112, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = { .prefactor_Hz = 4.7086757895e+12, .Ea_eV = 0.335112, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = { .prefactor_Hz = 4.7086757895e+12, .Ea_eV = 0.335112, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = { .prefactor_Hz = 4.7086757895e+12, .Ea_eV = 0.335112, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni] = { .prefactor_Hz = 8.8037795076e+12, .Ea_eV = 0.552506, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni] = { .prefactor_Hz = 8.8037795076e+12, .Ea_eV = 0.552506, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni] = { .prefactor_Hz = 8.8037795076e+12, .Ea_eV = 0.552506, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni] = { .prefactor_Hz = 8.8037795076e+12, .Ea_eV = 0.552506, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni] = { .prefactor_Hz = 5.6608913704e+12, .Ea_eV = 0.175734, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni] = { .prefactor_Hz = 5.6608913704e+12, .Ea_eV = 0.175734, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni] = { .prefactor_Hz = 5.6608913704e+12, .Ea_eV = 0.175734, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni] = { .prefactor_Hz = 5.6608913704e+12, .Ea_eV = 0.175734, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni] = { .prefactor_Hz = 1.8128692259e+12, .Ea_eV = 0.017357, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni] = { .prefactor_Hz = 1.8128692259e+12, .Ea_eV = 0.017357, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni] = { .prefactor_Hz = 1.8128692259e+12, .Ea_eV = 0.017357, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni] = { .prefactor_Hz = 1.8128692259e+12, .Ea_eV = 0.017357, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni] = { .prefactor_Hz = 1.7149604280e+12, .Ea_eV = 0.005419, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni] = { .prefactor_Hz = 1.7149604280e+12, .Ea_eV = 0.005419, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni] = { .prefactor_Hz = 1.7149604280e+12, .Ea_eV = 0.005419, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni] = { .prefactor_Hz = 1.7149604280e+12, .Ea_eV = 0.005419, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000717, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000717, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000717, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000717, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni] = { .prefactor_Hz = 3.9944002653e+13, .Ea_eV = 1.004997, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni] = { .prefactor_Hz = 3.9944002653e+13, .Ea_eV = 1.004997, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni] = { .prefactor_Hz = 3.9944002653e+13, .Ea_eV = 1.004997, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni] = { .prefactor_Hz = 3.9944002653e+13, .Ea_eV = 1.004997, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni] = { .prefactor_Hz = 4.4777194169e+13, .Ea_eV = 0.918759, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni] = { .prefactor_Hz = 4.4777194169e+13, .Ea_eV = 0.918759, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni] = { .prefactor_Hz = 4.4777194169e+13, .Ea_eV = 0.918759, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni] = { .prefactor_Hz = 4.4777194169e+13, .Ea_eV = 0.918759, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni] = { .prefactor_Hz = 1.2255951728e+12, .Ea_eV = 0.820454, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni] = { .prefactor_Hz = 1.2255951728e+12, .Ea_eV = 0.820454, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni] = { .prefactor_Hz = 1.2255951728e+12, .Ea_eV = 0.820454, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni] = { .prefactor_Hz = 1.2255951728e+12, .Ea_eV = 0.820454, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni] = { .prefactor_Hz = 2.1959910367e+13, .Ea_eV = 0.486225, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni] = { .prefactor_Hz = 2.1959910367e+13, .Ea_eV = 0.486225, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni] = { .prefactor_Hz = 2.1959910367e+13, .Ea_eV = 0.486225, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni] = { .prefactor_Hz = 2.1959910367e+13, .Ea_eV = 0.486225, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000671, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000671, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000671, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni] = { .prefactor_Hz = 1.0000000000e+13, .Ea_eV = 0.000671, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni] = { .prefactor_Hz = 3.8854713005e+13, .Ea_eV = 1.018036, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni] = { .prefactor_Hz = 3.8854713005e+13, .Ea_eV = 1.018036, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni] = { .prefactor_Hz = 3.8854713005e+13, .Ea_eV = 1.018036, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni] = { .prefactor_Hz = 3.8854713005e+13, .Ea_eV = 1.018036, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni] = { .prefactor_Hz = 3.5638321863e+13, .Ea_eV = 0.960672, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni] = { .prefactor_Hz = 3.5638321863e+13, .Ea_eV = 0.960672, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni] = { .prefactor_Hz = 3.5638321863e+13, .Ea_eV = 0.960672, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni] = { .prefactor_Hz = 3.5638321863e+13, .Ea_eV = 0.960672, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni] = { .prefactor_Hz = 4.6923837126e+13, .Ea_eV = 1.046595, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni] = { .prefactor_Hz = 4.6923837126e+13, .Ea_eV = 1.046595, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni] = { .prefactor_Hz = 4.6923837126e+13, .Ea_eV = 1.046595, .is_electrochemical = 0, ._pad = 0 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni] = { .prefactor_Hz = 4.6923837126e+13, .Ea_eV = 1.046595, .is_electrochemical = 0, ._pad = 0 },
};

typedef struct { int v_origin; int v_dest; } HopOutcome;
typedef HopOutcome (*ApplyFn)(State *st, const Lattice *lat, int site);

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PZ], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MZ], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static const ApplyFn apply_table[N_PROCS] = {
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni,
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni] = apply_actions_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_px__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_py__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_my__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni,
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni] = apply_actions_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni,
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni,
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni,
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni] = apply_actions_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni,
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni,
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni,
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni,
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni,
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni] = apply_actions_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni,
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni] = apply_actions_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni,
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni,
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni,
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni,
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni,
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni,
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni,
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni,
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni,
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni,
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni,
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni,
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni,
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni,
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni,
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni,
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni] = apply_actions_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni,
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni,
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni,
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni,
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni,
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni,
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni,
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni,
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni,
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni,
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni,
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni] = apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni,
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni] = apply_actions_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni,
};

void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {
    switch (st->species[site]) {
        case SP_VACANT:
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_py = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_py = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_py++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_py = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_py = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_py++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_py == 0 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 1 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 2 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 5 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 5 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 5 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 5 && nr_2nn_vacant_at_nn1_py == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 0 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 0 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 0 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 0 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 1 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 1 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 1 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 1 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 2 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 2 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 2 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 2 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 3 && nr_2nn_vacant_at_nn1_py == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni, site);
                        if (nr_1nn_vacant_at_nn1_py == 4 && nr_2nn_vacant_at_nn1_py == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_px = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_px = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_px++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_px = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_px = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_px++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 1 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 2 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 5 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 5 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 5 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 5 && nr_2nn_vacant_at_nn1_px == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 1 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 1 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 1 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 1 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 2 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 2 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 2 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 2 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 3 && nr_2nn_vacant_at_nn1_px == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni, site);
                        if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_my = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_my = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_my++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_my = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_my = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_my++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_my == 0 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 1 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 2 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 5 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 5 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 5 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 5 && nr_2nn_vacant_at_nn1_my == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 0 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 0 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 0 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 0 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 1 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 1 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 1 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 1 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 2 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 2 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 2 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 2 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 3 && nr_2nn_vacant_at_nn1_my == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni, site);
                        if (nr_1nn_vacant_at_nn1_my == 4 && nr_2nn_vacant_at_nn1_my == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_mx = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_mx = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_mx++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_mx = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_mx = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_mx++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_mx == 0 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 1 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 2 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 5 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 5 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 5 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 5 && nr_2nn_vacant_at_nn1_mx == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 0 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 0 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 0 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 0 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 1 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 1 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 1 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 1 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 2 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 2 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 2 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 2 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 3 && nr_2nn_vacant_at_nn1_mx == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 0) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 1) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 2) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 3) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni, site);
                        if (nr_1nn_vacant_at_nn1_mx == 4 && nr_2nn_vacant_at_nn1_mx == 4) avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_down_pp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_down_pp = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_down_pp++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_down_pp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_down_pp = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_down_pp++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_down_pp == 0 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 1 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 2 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 3 && nr_2nn_vacant_at_nn1_down_pp == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 3 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 4 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 4 && nr_2nn_vacant_at_nn1_down_pp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 4 && nr_2nn_vacant_at_nn1_down_pp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5 && nr_2nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5 && nr_2nn_vacant_at_nn1_down_pp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5 && nr_2nn_vacant_at_nn1_down_pp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5 && nr_2nn_vacant_at_nn1_down_pp == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 6) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 7) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 8) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 1) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 2) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 3) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 4) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pp == 5) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_down_pm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_down_pm = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_down_pm++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_down_pm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_down_pm = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_down_pm++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_down_pm == 0 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 1 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 2 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 3 && nr_2nn_vacant_at_nn1_down_pm == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 3 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 4 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 4 && nr_2nn_vacant_at_nn1_down_pm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 4 && nr_2nn_vacant_at_nn1_down_pm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5 && nr_2nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5 && nr_2nn_vacant_at_nn1_down_pm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5 && nr_2nn_vacant_at_nn1_down_pm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5 && nr_2nn_vacant_at_nn1_down_pm == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 6) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 7) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 8) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 1) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 2) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 3) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 4) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_pm == 5) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_down_mp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_down_mp = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_down_mp++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_down_mp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_down_mp = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_down_mp++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_down_mp == 0 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 1 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 2 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 3 && nr_2nn_vacant_at_nn1_down_mp == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 3 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 4 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 4 && nr_2nn_vacant_at_nn1_down_mp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 4 && nr_2nn_vacant_at_nn1_down_mp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5 && nr_2nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5 && nr_2nn_vacant_at_nn1_down_mp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5 && nr_2nn_vacant_at_nn1_down_mp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5 && nr_2nn_vacant_at_nn1_down_mp == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 6) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 7) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 8) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 1) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 2) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 3) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 4) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mp == 5) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_down_mm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_down_mm = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_down_mm++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_down_mm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_down_mm = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_down_mm++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_down_mm == 0 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 1 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 2 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 3 && nr_2nn_vacant_at_nn1_down_mm == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 3 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 4 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 4 && nr_2nn_vacant_at_nn1_down_mm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 4 && nr_2nn_vacant_at_nn1_down_mm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5 && nr_2nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5 && nr_2nn_vacant_at_nn1_down_mm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5 && nr_2nn_vacant_at_nn1_down_mm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5 && nr_2nn_vacant_at_nn1_down_mm == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 6) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 7) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 8) avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 1) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 2) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 3) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 4) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_down_mm == 5) avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_up_pp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_up_pp = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_up_pp++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_up_pp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_up_pp = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_up_pp++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_up_pp == 0 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 1 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 2 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 3 && nr_2nn_vacant_at_nn1_up_pp == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 3 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 4 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 4 && nr_2nn_vacant_at_nn1_up_pp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 4 && nr_2nn_vacant_at_nn1_up_pp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 5 && nr_2nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 5 && nr_2nn_vacant_at_nn1_up_pp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 5 && nr_2nn_vacant_at_nn1_up_pp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 5 && nr_2nn_vacant_at_nn1_up_pp == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 1) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 2) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pp == 3) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_up_pm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_up_pm = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_up_pm++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_up_pm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_up_pm = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_up_pm++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_up_pm == 0 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 1 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 2 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 3 && nr_2nn_vacant_at_nn1_up_pm == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 3 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 4 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 4 && nr_2nn_vacant_at_nn1_up_pm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 4 && nr_2nn_vacant_at_nn1_up_pm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 5 && nr_2nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 5 && nr_2nn_vacant_at_nn1_up_pm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 5 && nr_2nn_vacant_at_nn1_up_pm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 5 && nr_2nn_vacant_at_nn1_up_pm == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 1) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 2) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_pm == 3) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_up_mp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_up_mp = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_up_mp++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_up_mp = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_up_mp = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_up_mp++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_up_mp == 0 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 1 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 2 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 3 && nr_2nn_vacant_at_nn1_up_mp == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 3 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 4 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 4 && nr_2nn_vacant_at_nn1_up_mp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 4 && nr_2nn_vacant_at_nn1_up_mp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 5 && nr_2nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 5 && nr_2nn_vacant_at_nn1_up_mp == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 5 && nr_2nn_vacant_at_nn1_up_mp == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 5 && nr_2nn_vacant_at_nn1_up_mp == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 1) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 2) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mp == 3) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn1_up_mm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn1_up_mm = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn1_up_mm++;
                                }
                            }
                        }
                        int nr_2nn_vacant_at_nn1_up_mm = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_2nn_vacant_at_nn1_up_mm = 0;
                                for (int _i = lat->nn2_offsets[_m]; _i < lat->nn2_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn2_indices[_i]] == SP_VACANT) nr_2nn_vacant_at_nn1_up_mm++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn1_up_mm == 0 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 1 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 2 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 3 && nr_2nn_vacant_at_nn1_up_mm == 0) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 3 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 4 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 4 && nr_2nn_vacant_at_nn1_up_mm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 4 && nr_2nn_vacant_at_nn1_up_mm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 5 && nr_2nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 5 && nr_2nn_vacant_at_nn1_up_mm == 2) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 5 && nr_2nn_vacant_at_nn1_up_mm == 3) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 5 && nr_2nn_vacant_at_nn1_up_mm == 4) avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 2) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 3) avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 2) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 3) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 4) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 5) avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 1) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 2) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni, site);
                        if (nr_1nn_vacant_at_nn1_up_mm == 3) avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PZ]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_pz = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PZ];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_pz = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_pz++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_pz == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PY]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_py = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_py = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_py++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_py == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PX]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_px = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_px = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_px++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_px == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MZ]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_mz = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MZ];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_mz = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_mz++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_mz == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MY]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_my = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MY];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_my = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_my++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_my == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni, site);
                    }
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MX]]) {
                case SP_NI:
                    {
                        /* shell-count loops for bucket-key gating */
                        int nr_1nn_vacant_at_nn2_mx = -1;  /* sentinel: stub-site mover → no match */
                        {
                            int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MX];
                            if (_m >= 0 && _m < lat->n_sites) {
                                nr_1nn_vacant_at_nn2_mx = 0;
                                for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                                    if (st->species[lat->nn1_indices[_i]] == SP_VACANT) nr_1nn_vacant_at_nn2_mx++;
                                }
                            }
                        }
                        if (nr_1nn_vacant_at_nn2_mx == 3) avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni, site);
                    }
                    break;
                default: break;
            }
            break;
        default: break;
    }
}


/* ---- Public linkage (mirrored in proclist.h) ----
 *
 * The internal `rate_table` / `apply_table` are file-static. The runtime
 * accesses them through these `pylatkmc_*` aliases, decoupling the
 * call site from the static-storage symbols.
 */
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
