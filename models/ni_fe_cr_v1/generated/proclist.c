/* proclist.c — GENERATED from ni_fe_cr_v1.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build ni_fe_cr_v1.kmcspec.toml`.
 *
 * This file is the heart of the pylatkmc v2 pattern-DB runtime: it
 * bundles the per-model Process catalogue (translated from the curated
 * FCC family CSV) into a single C compilation unit consumed by the
 * runtime backbone in `runtime/src/core/`.
 *
 * Contents (in order):
 *   1. enum { P_<name>, ..., N_PROCS }      — Process IDs
 *   2. static const RateConst rate_table[]   — per-proc Arrhenius rate
 *      baked at T = 500.0 K, k0 = 1.000e+13 Hz
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
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni,
    P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni,
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

typedef struct { double rate; double Ea_eV; } RateConst;
static const RateConst rate_table[N_PROCS] = {
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni] = { .rate = 7.2551754184e+05, .Ea_eV = 0.708300 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni] = { .rate = 1.6307720048e+07, .Ea_eV = 0.574193 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni] = { .rate = 1.0008586605e+06, .Ea_eV = 0.694438 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni] = { .rate = 1.5188769549e+10, .Ea_eV = 0.279623 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni] = { .rate = 3.4086253247e+04, .Ea_eV = 0.840059 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni] = { .rate = 3.8184228480e+10, .Ea_eV = 0.239903 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni] = { .rate = 2.7326744957e+09, .Ea_eV = 0.353529 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni] = { .rate = 8.1873572499e+08, .Ea_eV = 0.405460 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni] = { .rate = 1.3762873076e+10, .Ea_eV = 0.283871 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni] = { .rate = 2.3395498444e+09, .Ea_eV = 0.360221 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni] = { .rate = 3.4523406609e+09, .Ea_eV = 0.343456 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni] = { .rate = 5.1211358394e+06, .Ea_eV = 0.624098 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni] = { .rate = 2.1405283598e+03, .Ea_eV = 0.959316 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni] = { .rate = 5.3394514867e+02, .Ea_eV = 1.019142 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni] = { .rate = 1.3175830035e+02, .Ea_eV = 1.079435 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni] = { .rate = 1.8407140250e+02, .Ea_eV = 1.065028 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni] = { .rate = 2.7350148232e+02, .Ea_eV = 1.047967 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni] = { .rate = 1.4051514378e+03, .Ea_eV = 0.977451 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni] = { .rate = 2.6656148978e+02, .Ea_eV = 1.049074 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni] = { .rate = 1.0691805045e+03, .Ea_eV = 0.989225 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni] = { .rate = 1.6290948215e+02, .Ea_eV = 1.070290 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni] = { .rate = 5.6571423924e+02, .Ea_eV = 1.016652 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni] = { .rate = 5.6571423924e+02, .Ea_eV = 1.016652 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni] = { .rate = 5.6571423924e+02, .Ea_eV = 1.016652 },
    [P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni] = { .rate = 5.6571423924e+02, .Ea_eV = 1.016652 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni] = { .rate = 3.1036694609e+05, .Ea_eV = 0.744886 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni] = { .rate = 3.1036694609e+05, .Ea_eV = 0.744886 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni] = { .rate = 3.1036694609e+05, .Ea_eV = 0.744886 },
    [P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni] = { .rate = 3.1036694609e+05, .Ea_eV = 0.744886 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni] = { .rate = 7.8353679547e+05, .Ea_eV = 0.704985 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni] = { .rate = 7.8353679547e+05, .Ea_eV = 0.704985 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni] = { .rate = 7.8353679547e+05, .Ea_eV = 0.704985 },
    [P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni] = { .rate = 7.8353679547e+05, .Ea_eV = 0.704985 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni] = { .rate = 3.3838873121e+07, .Ea_eV = 0.542741 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni] = { .rate = 3.3838873121e+07, .Ea_eV = 0.542741 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni] = { .rate = 3.3838873121e+07, .Ea_eV = 0.542741 },
    [P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni] = { .rate = 3.3838873121e+07, .Ea_eV = 0.542741 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni] = { .rate = 3.1059363269e+06, .Ea_eV = 0.645644 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni] = { .rate = 3.1059363269e+06, .Ea_eV = 0.645644 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni] = { .rate = 3.1059363269e+06, .Ea_eV = 0.645644 },
    [P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni] = { .rate = 3.1059363269e+06, .Ea_eV = 0.645644 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni] = { .rate = 2.0579300603e+04, .Ea_eV = 0.861801 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni] = { .rate = 2.0579300603e+04, .Ea_eV = 0.861801 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni] = { .rate = 2.0579300603e+04, .Ea_eV = 0.861801 },
    [P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni] = { .rate = 2.0579300603e+04, .Ea_eV = 0.861801 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni] = { .rate = 5.6036561725e+04, .Ea_eV = 0.818640 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni] = { .rate = 5.6036561725e+04, .Ea_eV = 0.818640 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni] = { .rate = 5.6036561725e+04, .Ea_eV = 0.818640 },
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni] = { .rate = 5.6036561725e+04, .Ea_eV = 0.818640 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni] = { .rate = 3.9355822811e+03, .Ea_eV = 0.933076 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni] = { .rate = 3.9355822811e+03, .Ea_eV = 0.933076 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni] = { .rate = 3.9355822811e+03, .Ea_eV = 0.933076 },
    [P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni] = { .rate = 3.9355822811e+03, .Ea_eV = 0.933076 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni] = { .rate = 2.3489993542e+08, .Ea_eV = 0.459258 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni] = { .rate = 2.3489993542e+08, .Ea_eV = 0.459258 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni] = { .rate = 2.3489993542e+08, .Ea_eV = 0.459258 },
    [P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni] = { .rate = 2.3489993542e+08, .Ea_eV = 0.459258 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni] = { .rate = 2.1086877065e+07, .Ea_eV = 0.563119 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni] = { .rate = 2.1086877065e+07, .Ea_eV = 0.563119 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni] = { .rate = 2.1086877065e+07, .Ea_eV = 0.563119 },
    [P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni] = { .rate = 2.1086877065e+07, .Ea_eV = 0.563119 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni] = { .rate = 2.1482407909e+06, .Ea_eV = 0.661529 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni] = { .rate = 2.1482407909e+06, .Ea_eV = 0.661529 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni] = { .rate = 2.1482407909e+06, .Ea_eV = 0.661529 },
    [P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni] = { .rate = 2.1482407909e+06, .Ea_eV = 0.661529 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni] = { .rate = 1.2866658542e+06, .Ea_eV = 0.683615 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni] = { .rate = 1.2866658542e+06, .Ea_eV = 0.683615 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni] = { .rate = 1.2866658542e+06, .Ea_eV = 0.683615 },
    [P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni] = { .rate = 1.2866658542e+06, .Ea_eV = 0.683615 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni] = { .rate = 8.2414920366e+09, .Ea_eV = 0.305965 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni] = { .rate = 8.2414920366e+09, .Ea_eV = 0.305965 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni] = { .rate = 8.2414920366e+09, .Ea_eV = 0.305965 },
    [P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni] = { .rate = 8.2414920366e+09, .Ea_eV = 0.305965 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni] = { .rate = 2.5976616157e+10, .Ea_eV = 0.256501 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni] = { .rate = 2.5976616157e+10, .Ea_eV = 0.256501 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni] = { .rate = 2.5976616157e+10, .Ea_eV = 0.256501 },
    [P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni] = { .rate = 2.5976616157e+10, .Ea_eV = 0.256501 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni] = { .rate = 5.2863156650e+09, .Ea_eV = 0.325098 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni] = { .rate = 5.2863156650e+09, .Ea_eV = 0.325098 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni] = { .rate = 5.2863156650e+09, .Ea_eV = 0.325098 },
    [P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni] = { .rate = 5.2863156650e+09, .Ea_eV = 0.325098 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni] = { .rate = 4.1764261175e+08, .Ea_eV = 0.434463 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni] = { .rate = 4.1764261175e+08, .Ea_eV = 0.434463 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni] = { .rate = 4.1764261175e+08, .Ea_eV = 0.434463 },
    [P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni] = { .rate = 4.1764261175e+08, .Ea_eV = 0.434463 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni] = { .rate = 8.9759452569e+05, .Ea_eV = 0.699130 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni] = { .rate = 8.9759452569e+05, .Ea_eV = 0.699130 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni] = { .rate = 8.9759452569e+05, .Ea_eV = 0.699130 },
    [P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni] = { .rate = 8.9759452569e+05, .Ea_eV = 0.699130 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni] = { .rate = 7.5315729133e+10, .Ea_eV = 0.210636 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni] = { .rate = 7.5315729133e+10, .Ea_eV = 0.210636 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni] = { .rate = 7.5315729133e+10, .Ea_eV = 0.210636 },
    [P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni] = { .rate = 7.5315729133e+10, .Ea_eV = 0.210636 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni] = { .rate = 2.0944137628e+11, .Ea_eV = 0.166569 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni] = { .rate = 2.0944137628e+11, .Ea_eV = 0.166569 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni] = { .rate = 2.0944137628e+11, .Ea_eV = 0.166569 },
    [P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni] = { .rate = 2.0944137628e+11, .Ea_eV = 0.166569 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni] = { .rate = 6.1453648313e+10, .Ea_eV = 0.219400 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni] = { .rate = 6.1453648313e+10, .Ea_eV = 0.219400 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni] = { .rate = 6.1453648313e+10, .Ea_eV = 0.219400 },
    [P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni] = { .rate = 6.1453648313e+10, .Ea_eV = 0.219400 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni] = { .rate = 4.1900779164e+09, .Ea_eV = 0.335112 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni] = { .rate = 4.1900779164e+09, .Ea_eV = 0.335112 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni] = { .rate = 4.1900779164e+09, .Ea_eV = 0.335112 },
    [P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni] = { .rate = 4.1900779164e+09, .Ea_eV = 0.335112 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni] = { .rate = 2.6976276219e+07, .Ea_eV = 0.552506 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni] = { .rate = 2.6976276219e+07, .Ea_eV = 0.552506 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni] = { .rate = 2.6976276219e+07, .Ea_eV = 0.552506 },
    [P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni] = { .rate = 2.6976276219e+07, .Ea_eV = 0.552506 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni] = { .rate = 1.6930712461e+11, .Ea_eV = 0.175734 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni] = { .rate = 1.6930712461e+11, .Ea_eV = 0.175734 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni] = { .rate = 1.6930712461e+11, .Ea_eV = 0.175734 },
    [P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni] = { .rate = 1.6930712461e+11, .Ea_eV = 0.175734 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni] = { .rate = 6.6841926335e+12, .Ea_eV = 0.017357 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni] = { .rate = 6.6841926335e+12, .Ea_eV = 0.017357 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni] = { .rate = 6.6841926335e+12, .Ea_eV = 0.017357 },
    [P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni] = { .rate = 6.6841926335e+12, .Ea_eV = 0.017357 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni] = { .rate = 8.8182012923e+12, .Ea_eV = 0.005419 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni] = { .rate = 8.8182012923e+12, .Ea_eV = 0.005419 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni] = { .rate = 8.8182012923e+12, .Ea_eV = 0.005419 },
    [P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni] = { .rate = 8.8182012923e+12, .Ea_eV = 0.005419 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni] = { .rate = 9.8348789746e+12, .Ea_eV = 0.000717 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni] = { .rate = 9.8348789746e+12, .Ea_eV = 0.000717 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni] = { .rate = 9.8348789746e+12, .Ea_eV = 0.000717 },
    [P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni] = { .rate = 9.8348789746e+12, .Ea_eV = 0.000717 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni] = { .rate = 7.4144263696e+02, .Ea_eV = 1.004997 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni] = { .rate = 7.4144263696e+02, .Ea_eV = 1.004997 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni] = { .rate = 7.4144263696e+02, .Ea_eV = 1.004997 },
    [P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni] = { .rate = 7.4144263696e+02, .Ea_eV = 1.004997 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni] = { .rate = 5.4867076443e+03, .Ea_eV = 0.918759 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni] = { .rate = 5.4867076443e+03, .Ea_eV = 0.918759 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni] = { .rate = 5.4867076443e+03, .Ea_eV = 0.918759 },
    [P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni] = { .rate = 5.4867076443e+03, .Ea_eV = 0.918759 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni] = { .rate = 5.3725953031e+04, .Ea_eV = 0.820454 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni] = { .rate = 5.3725953031e+04, .Ea_eV = 0.820454 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni] = { .rate = 5.3725953031e+04, .Ea_eV = 0.820454 },
    [P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni] = { .rate = 5.3725953031e+04, .Ea_eV = 0.820454 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni] = { .rate = 1.2562368884e+08, .Ea_eV = 0.486225 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni] = { .rate = 1.2562368884e+08, .Ea_eV = 0.486225 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni] = { .rate = 1.2562368884e+08, .Ea_eV = 0.486225 },
    [P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni] = { .rate = 1.2562368884e+08, .Ea_eV = 0.486225 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni] = { .rate = 9.8455776414e+12, .Ea_eV = 0.000671 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni] = { .rate = 9.8455776414e+12, .Ea_eV = 0.000671 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni] = { .rate = 9.8455776414e+12, .Ea_eV = 0.000671 },
    [P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni] = { .rate = 9.8455776414e+12, .Ea_eV = 0.000671 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni] = { .rate = 8.3199395508e+02, .Ea_eV = 1.000032 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni] = { .rate = 5.4783083198e+02, .Ea_eV = 1.018036 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni] = { .rate = 5.4783083198e+02, .Ea_eV = 1.018036 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni] = { .rate = 5.4783083198e+02, .Ea_eV = 1.018036 },
    [P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni] = { .rate = 5.4783083198e+02, .Ea_eV = 1.018036 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni] = { .rate = 2.0741847185e+03, .Ea_eV = 0.960672 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni] = { .rate = 2.0741847185e+03, .Ea_eV = 0.960672 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni] = { .rate = 2.0741847185e+03, .Ea_eV = 0.960672 },
    [P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni] = { .rate = 2.0741847185e+03, .Ea_eV = 0.960672 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni] = { .rate = 2.8235147641e+02, .Ea_eV = 1.046595 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni] = { .rate = 2.8235147641e+02, .Ea_eV = 1.046595 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni] = { .rate = 2.8235147641e+02, .Ea_eV = 1.046595 },
    [P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni] = { .rate = 2.8235147641e+02, .Ea_eV = 1.046595 },
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

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[2] = {
        { .site = site, .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP], .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){ .v_origin = acts[0].site, .v_dest = acts[1].site };
}

static HopOutcome apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni(State *st, const Lattice *lat, int site) {
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
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni,
    [P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni] = apply_actions_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni,
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
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_py__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_py__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MX]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_mx__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_mx__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_MY]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_my__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_my__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_1_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_2_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_3_nv2_4__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_2__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_3__nn1_px__ni, site);
                    avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_4__nn1_px__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MM]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mm__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_MP]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_mp__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PP]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pp__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_DOWN_PM]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_5__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_6__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_7__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_interlayer_hop__li_0_nv1_8__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_1__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_2__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_3__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_4__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_down__nv1_5__nn1_down_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_down_pm__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MP]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_mp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_mp__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PP]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_pp__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_pp__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_MM]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_mm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_mm__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_UP_PM]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_0_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_1_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_2_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_0__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_3_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_2__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_4_nv2_3__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_2__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_3__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_1nn_inplane__nv1_5_nv2_4__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_2__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_interlayer_hop__nv1_3__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_2__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_3__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_4__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_subsurface_migration_interlayer__nv1_5__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_lateral__nv1_4__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_1__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_2__nn1_up_pm__ni, site);
                    avail_sites_add(as, P_surface_subsurface_exchange_up__nv1_3__nn1_up_pm__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PY]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_py__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MZ]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_mz__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PZ]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_pz__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MY]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_my__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_MX]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_mx__ni, site);
                    break;
                default: break;
            }
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN2_PX]]) {
                case SP_NI:
                    avail_sites_add(as, P_subsurface_2nn_diagonal__nv1_3__nn2_px__ni, site);
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
