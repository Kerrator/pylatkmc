/* proclist.c — GENERATED from ni_dissolution_demo.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build ni_dissolution_demo.kmcspec.toml`.
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
    P_dissolution__ni__ni3,
    P_dissolution__ni__ni2_fe1,
    P_dissolution__ni__ni2_cr1,
    P_dissolution__ni__ni1_fe2,
    P_dissolution__ni__ni1_fe1_cr1,
    P_dissolution__ni__ni1_cr2,
    P_dissolution__ni__fe3,
    P_dissolution__ni__fe2_cr1,
    P_dissolution__ni__fe1_cr2,
    P_dissolution__ni__cr3,
    P_dissolution__ni__ni4,
    P_dissolution__ni__ni3_fe1,
    P_dissolution__ni__ni3_cr1,
    P_dissolution__ni__ni2_fe2,
    P_dissolution__ni__ni2_fe1_cr1,
    P_dissolution__ni__ni2_cr2,
    P_dissolution__ni__ni1_fe3,
    P_dissolution__ni__ni1_fe2_cr1,
    P_dissolution__ni__ni1_fe1_cr2,
    P_dissolution__ni__ni1_cr3,
    P_dissolution__ni__fe4,
    P_dissolution__ni__fe3_cr1,
    P_dissolution__ni__fe2_cr2,
    P_dissolution__ni__fe1_cr3,
    P_dissolution__ni__cr4,
    P_dissolution__ni__ni5,
    P_dissolution__ni__ni4_fe1,
    P_dissolution__ni__ni4_cr1,
    P_dissolution__ni__ni3_fe2,
    P_dissolution__ni__ni3_fe1_cr1,
    P_dissolution__ni__ni3_cr2,
    P_dissolution__ni__ni2_fe3,
    P_dissolution__ni__ni2_fe2_cr1,
    P_dissolution__ni__ni2_fe1_cr2,
    P_dissolution__ni__ni2_cr3,
    P_dissolution__ni__ni1_fe4,
    P_dissolution__ni__ni1_fe3_cr1,
    P_dissolution__ni__ni1_fe2_cr2,
    P_dissolution__ni__ni1_fe1_cr3,
    P_dissolution__ni__ni1_cr4,
    P_dissolution__ni__fe5,
    P_dissolution__ni__fe4_cr1,
    P_dissolution__ni__fe3_cr2,
    P_dissolution__ni__fe2_cr3,
    P_dissolution__ni__fe1_cr4,
    P_dissolution__ni__cr5,
    P_dissolution__ni__ni6,
    P_dissolution__ni__ni5_fe1,
    P_dissolution__ni__ni5_cr1,
    P_dissolution__ni__ni4_fe2,
    P_dissolution__ni__ni4_fe1_cr1,
    P_dissolution__ni__ni4_cr2,
    P_dissolution__ni__ni3_fe3,
    P_dissolution__ni__ni3_fe2_cr1,
    P_dissolution__ni__ni3_fe1_cr2,
    P_dissolution__ni__ni3_cr3,
    P_dissolution__ni__ni2_fe4,
    P_dissolution__ni__ni2_fe3_cr1,
    P_dissolution__ni__ni2_fe2_cr2,
    P_dissolution__ni__ni2_fe1_cr3,
    P_dissolution__ni__ni2_cr4,
    P_dissolution__ni__ni1_fe5,
    P_dissolution__ni__ni1_fe4_cr1,
    P_dissolution__ni__ni1_fe3_cr2,
    P_dissolution__ni__ni1_fe2_cr3,
    P_dissolution__ni__ni1_fe1_cr4,
    P_dissolution__ni__ni1_cr5,
    P_dissolution__ni__fe6,
    P_dissolution__ni__fe5_cr1,
    P_dissolution__ni__fe4_cr2,
    P_dissolution__ni__fe3_cr3,
    P_dissolution__ni__fe2_cr4,
    P_dissolution__ni__fe1_cr5,
    P_dissolution__ni__cr6,
    P_dissolution__ni__ni7,
    P_dissolution__ni__ni6_fe1,
    P_dissolution__ni__ni6_cr1,
    P_dissolution__ni__ni5_fe2,
    P_dissolution__ni__ni5_fe1_cr1,
    P_dissolution__ni__ni5_cr2,
    P_dissolution__ni__ni4_fe3,
    P_dissolution__ni__ni4_fe2_cr1,
    P_dissolution__ni__ni4_fe1_cr2,
    P_dissolution__ni__ni4_cr3,
    P_dissolution__ni__ni3_fe4,
    P_dissolution__ni__ni3_fe3_cr1,
    P_dissolution__ni__ni3_fe2_cr2,
    P_dissolution__ni__ni3_fe1_cr3,
    P_dissolution__ni__ni3_cr4,
    P_dissolution__ni__ni2_fe5,
    P_dissolution__ni__ni2_fe4_cr1,
    P_dissolution__ni__ni2_fe3_cr2,
    P_dissolution__ni__ni2_fe2_cr3,
    P_dissolution__ni__ni2_fe1_cr4,
    P_dissolution__ni__ni2_cr5,
    P_dissolution__ni__ni1_fe6,
    P_dissolution__ni__ni1_fe5_cr1,
    P_dissolution__ni__ni1_fe4_cr2,
    P_dissolution__ni__ni1_fe3_cr3,
    P_dissolution__ni__ni1_fe2_cr4,
    P_dissolution__ni__ni1_fe1_cr5,
    P_dissolution__ni__ni1_cr6,
    P_dissolution__ni__fe7,
    P_dissolution__ni__fe6_cr1,
    P_dissolution__ni__fe5_cr2,
    P_dissolution__ni__fe4_cr3,
    P_dissolution__ni__fe3_cr4,
    P_dissolution__ni__fe2_cr5,
    P_dissolution__ni__fe1_cr6,
    P_dissolution__ni__cr7,
    P_dissolution__ni__ni8,
    P_dissolution__ni__ni7_fe1,
    P_dissolution__ni__ni7_cr1,
    P_dissolution__ni__ni6_fe2,
    P_dissolution__ni__ni6_fe1_cr1,
    P_dissolution__ni__ni6_cr2,
    P_dissolution__ni__ni5_fe3,
    P_dissolution__ni__ni5_fe2_cr1,
    P_dissolution__ni__ni5_fe1_cr2,
    P_dissolution__ni__ni5_cr3,
    P_dissolution__ni__ni4_fe4,
    P_dissolution__ni__ni4_fe3_cr1,
    P_dissolution__ni__ni4_fe2_cr2,
    P_dissolution__ni__ni4_fe1_cr3,
    P_dissolution__ni__ni4_cr4,
    P_dissolution__ni__ni3_fe5,
    P_dissolution__ni__ni3_fe4_cr1,
    P_dissolution__ni__ni3_fe3_cr2,
    P_dissolution__ni__ni3_fe2_cr3,
    P_dissolution__ni__ni3_fe1_cr4,
    P_dissolution__ni__ni3_cr5,
    P_dissolution__ni__ni2_fe6,
    P_dissolution__ni__ni2_fe5_cr1,
    P_dissolution__ni__ni2_fe4_cr2,
    P_dissolution__ni__ni2_fe3_cr3,
    P_dissolution__ni__ni2_fe2_cr4,
    P_dissolution__ni__ni2_fe1_cr5,
    P_dissolution__ni__ni2_cr6,
    P_dissolution__ni__ni1_fe7,
    P_dissolution__ni__ni1_fe6_cr1,
    P_dissolution__ni__ni1_fe5_cr2,
    P_dissolution__ni__ni1_fe4_cr3,
    P_dissolution__ni__ni1_fe3_cr4,
    P_dissolution__ni__ni1_fe2_cr5,
    P_dissolution__ni__ni1_fe1_cr6,
    P_dissolution__ni__ni1_cr7,
    P_dissolution__ni__fe8,
    P_dissolution__ni__fe7_cr1,
    P_dissolution__ni__fe6_cr2,
    P_dissolution__ni__fe5_cr3,
    P_dissolution__ni__fe4_cr4,
    P_dissolution__ni__fe3_cr5,
    P_dissolution__ni__fe2_cr6,
    P_dissolution__ni__fe1_cr7,
    P_dissolution__ni__cr8,
    P_dissolution__ni__ni9,
    P_dissolution__ni__ni8_fe1,
    P_dissolution__ni__ni8_cr1,
    P_dissolution__ni__ni7_fe2,
    P_dissolution__ni__ni7_fe1_cr1,
    P_dissolution__ni__ni7_cr2,
    P_dissolution__ni__ni6_fe3,
    P_dissolution__ni__ni6_fe2_cr1,
    P_dissolution__ni__ni6_fe1_cr2,
    P_dissolution__ni__ni6_cr3,
    P_dissolution__ni__ni5_fe4,
    P_dissolution__ni__ni5_fe3_cr1,
    P_dissolution__ni__ni5_fe2_cr2,
    P_dissolution__ni__ni5_fe1_cr3,
    P_dissolution__ni__ni5_cr4,
    P_dissolution__ni__ni4_fe5,
    P_dissolution__ni__ni4_fe4_cr1,
    P_dissolution__ni__ni4_fe3_cr2,
    P_dissolution__ni__ni4_fe2_cr3,
    P_dissolution__ni__ni4_fe1_cr4,
    P_dissolution__ni__ni4_cr5,
    P_dissolution__ni__ni3_fe6,
    P_dissolution__ni__ni3_fe5_cr1,
    P_dissolution__ni__ni3_fe4_cr2,
    P_dissolution__ni__ni3_fe3_cr3,
    P_dissolution__ni__ni3_fe2_cr4,
    P_dissolution__ni__ni3_fe1_cr5,
    P_dissolution__ni__ni3_cr6,
    P_dissolution__ni__ni2_fe7,
    P_dissolution__ni__ni2_fe6_cr1,
    P_dissolution__ni__ni2_fe5_cr2,
    P_dissolution__ni__ni2_fe4_cr3,
    P_dissolution__ni__ni2_fe3_cr4,
    P_dissolution__ni__ni2_fe2_cr5,
    P_dissolution__ni__ni2_fe1_cr6,
    P_dissolution__ni__ni2_cr7,
    P_dissolution__ni__ni1_fe8,
    P_dissolution__ni__ni1_fe7_cr1,
    P_dissolution__ni__ni1_fe6_cr2,
    P_dissolution__ni__ni1_fe5_cr3,
    P_dissolution__ni__ni1_fe4_cr4,
    P_dissolution__ni__ni1_fe3_cr5,
    P_dissolution__ni__ni1_fe2_cr6,
    P_dissolution__ni__ni1_fe1_cr7,
    P_dissolution__ni__ni1_cr8,
    P_dissolution__ni__fe9,
    P_dissolution__ni__fe8_cr1,
    P_dissolution__ni__fe7_cr2,
    P_dissolution__ni__fe6_cr3,
    P_dissolution__ni__fe5_cr4,
    P_dissolution__ni__fe4_cr5,
    P_dissolution__ni__fe3_cr6,
    P_dissolution__ni__fe2_cr7,
    P_dissolution__ni__fe1_cr8,
    P_dissolution__ni__cr9,
    P_dissolution__fe__ni3,
    P_dissolution__fe__ni2_fe1,
    P_dissolution__fe__ni2_cr1,
    P_dissolution__fe__ni1_fe2,
    P_dissolution__fe__ni1_fe1_cr1,
    P_dissolution__fe__ni1_cr2,
    P_dissolution__fe__fe3,
    P_dissolution__fe__fe2_cr1,
    P_dissolution__fe__fe1_cr2,
    P_dissolution__fe__cr3,
    P_dissolution__fe__ni4,
    P_dissolution__fe__ni3_fe1,
    P_dissolution__fe__ni3_cr1,
    P_dissolution__fe__ni2_fe2,
    P_dissolution__fe__ni2_fe1_cr1,
    P_dissolution__fe__ni2_cr2,
    P_dissolution__fe__ni1_fe3,
    P_dissolution__fe__ni1_fe2_cr1,
    P_dissolution__fe__ni1_fe1_cr2,
    P_dissolution__fe__ni1_cr3,
    P_dissolution__fe__fe4,
    P_dissolution__fe__fe3_cr1,
    P_dissolution__fe__fe2_cr2,
    P_dissolution__fe__fe1_cr3,
    P_dissolution__fe__cr4,
    P_dissolution__fe__ni5,
    P_dissolution__fe__ni4_fe1,
    P_dissolution__fe__ni4_cr1,
    P_dissolution__fe__ni3_fe2,
    P_dissolution__fe__ni3_fe1_cr1,
    P_dissolution__fe__ni3_cr2,
    P_dissolution__fe__ni2_fe3,
    P_dissolution__fe__ni2_fe2_cr1,
    P_dissolution__fe__ni2_fe1_cr2,
    P_dissolution__fe__ni2_cr3,
    P_dissolution__fe__ni1_fe4,
    P_dissolution__fe__ni1_fe3_cr1,
    P_dissolution__fe__ni1_fe2_cr2,
    P_dissolution__fe__ni1_fe1_cr3,
    P_dissolution__fe__ni1_cr4,
    P_dissolution__fe__fe5,
    P_dissolution__fe__fe4_cr1,
    P_dissolution__fe__fe3_cr2,
    P_dissolution__fe__fe2_cr3,
    P_dissolution__fe__fe1_cr4,
    P_dissolution__fe__cr5,
    P_dissolution__fe__ni6,
    P_dissolution__fe__ni5_fe1,
    P_dissolution__fe__ni5_cr1,
    P_dissolution__fe__ni4_fe2,
    P_dissolution__fe__ni4_fe1_cr1,
    P_dissolution__fe__ni4_cr2,
    P_dissolution__fe__ni3_fe3,
    P_dissolution__fe__ni3_fe2_cr1,
    P_dissolution__fe__ni3_fe1_cr2,
    P_dissolution__fe__ni3_cr3,
    P_dissolution__fe__ni2_fe4,
    P_dissolution__fe__ni2_fe3_cr1,
    P_dissolution__fe__ni2_fe2_cr2,
    P_dissolution__fe__ni2_fe1_cr3,
    P_dissolution__fe__ni2_cr4,
    P_dissolution__fe__ni1_fe5,
    P_dissolution__fe__ni1_fe4_cr1,
    P_dissolution__fe__ni1_fe3_cr2,
    P_dissolution__fe__ni1_fe2_cr3,
    P_dissolution__fe__ni1_fe1_cr4,
    P_dissolution__fe__ni1_cr5,
    P_dissolution__fe__fe6,
    P_dissolution__fe__fe5_cr1,
    P_dissolution__fe__fe4_cr2,
    P_dissolution__fe__fe3_cr3,
    P_dissolution__fe__fe2_cr4,
    P_dissolution__fe__fe1_cr5,
    P_dissolution__fe__cr6,
    P_dissolution__fe__ni7,
    P_dissolution__fe__ni6_fe1,
    P_dissolution__fe__ni6_cr1,
    P_dissolution__fe__ni5_fe2,
    P_dissolution__fe__ni5_fe1_cr1,
    P_dissolution__fe__ni5_cr2,
    P_dissolution__fe__ni4_fe3,
    P_dissolution__fe__ni4_fe2_cr1,
    P_dissolution__fe__ni4_fe1_cr2,
    P_dissolution__fe__ni4_cr3,
    P_dissolution__fe__ni3_fe4,
    P_dissolution__fe__ni3_fe3_cr1,
    P_dissolution__fe__ni3_fe2_cr2,
    P_dissolution__fe__ni3_fe1_cr3,
    P_dissolution__fe__ni3_cr4,
    P_dissolution__fe__ni2_fe5,
    P_dissolution__fe__ni2_fe4_cr1,
    P_dissolution__fe__ni2_fe3_cr2,
    P_dissolution__fe__ni2_fe2_cr3,
    P_dissolution__fe__ni2_fe1_cr4,
    P_dissolution__fe__ni2_cr5,
    P_dissolution__fe__ni1_fe6,
    P_dissolution__fe__ni1_fe5_cr1,
    P_dissolution__fe__ni1_fe4_cr2,
    P_dissolution__fe__ni1_fe3_cr3,
    P_dissolution__fe__ni1_fe2_cr4,
    P_dissolution__fe__ni1_fe1_cr5,
    P_dissolution__fe__ni1_cr6,
    P_dissolution__fe__fe7,
    P_dissolution__fe__fe6_cr1,
    P_dissolution__fe__fe5_cr2,
    P_dissolution__fe__fe4_cr3,
    P_dissolution__fe__fe3_cr4,
    P_dissolution__fe__fe2_cr5,
    P_dissolution__fe__fe1_cr6,
    P_dissolution__fe__cr7,
    P_dissolution__fe__ni8,
    P_dissolution__fe__ni7_fe1,
    P_dissolution__fe__ni7_cr1,
    P_dissolution__fe__ni6_fe2,
    P_dissolution__fe__ni6_fe1_cr1,
    P_dissolution__fe__ni6_cr2,
    P_dissolution__fe__ni5_fe3,
    P_dissolution__fe__ni5_fe2_cr1,
    P_dissolution__fe__ni5_fe1_cr2,
    P_dissolution__fe__ni5_cr3,
    P_dissolution__fe__ni4_fe4,
    P_dissolution__fe__ni4_fe3_cr1,
    P_dissolution__fe__ni4_fe2_cr2,
    P_dissolution__fe__ni4_fe1_cr3,
    P_dissolution__fe__ni4_cr4,
    P_dissolution__fe__ni3_fe5,
    P_dissolution__fe__ni3_fe4_cr1,
    P_dissolution__fe__ni3_fe3_cr2,
    P_dissolution__fe__ni3_fe2_cr3,
    P_dissolution__fe__ni3_fe1_cr4,
    P_dissolution__fe__ni3_cr5,
    P_dissolution__fe__ni2_fe6,
    P_dissolution__fe__ni2_fe5_cr1,
    P_dissolution__fe__ni2_fe4_cr2,
    P_dissolution__fe__ni2_fe3_cr3,
    P_dissolution__fe__ni2_fe2_cr4,
    P_dissolution__fe__ni2_fe1_cr5,
    P_dissolution__fe__ni2_cr6,
    P_dissolution__fe__ni1_fe7,
    P_dissolution__fe__ni1_fe6_cr1,
    P_dissolution__fe__ni1_fe5_cr2,
    P_dissolution__fe__ni1_fe4_cr3,
    P_dissolution__fe__ni1_fe3_cr4,
    P_dissolution__fe__ni1_fe2_cr5,
    P_dissolution__fe__ni1_fe1_cr6,
    P_dissolution__fe__ni1_cr7,
    P_dissolution__fe__fe8,
    P_dissolution__fe__fe7_cr1,
    P_dissolution__fe__fe6_cr2,
    P_dissolution__fe__fe5_cr3,
    P_dissolution__fe__fe4_cr4,
    P_dissolution__fe__fe3_cr5,
    P_dissolution__fe__fe2_cr6,
    P_dissolution__fe__fe1_cr7,
    P_dissolution__fe__cr8,
    P_dissolution__fe__ni9,
    P_dissolution__fe__ni8_fe1,
    P_dissolution__fe__ni8_cr1,
    P_dissolution__fe__ni7_fe2,
    P_dissolution__fe__ni7_fe1_cr1,
    P_dissolution__fe__ni7_cr2,
    P_dissolution__fe__ni6_fe3,
    P_dissolution__fe__ni6_fe2_cr1,
    P_dissolution__fe__ni6_fe1_cr2,
    P_dissolution__fe__ni6_cr3,
    P_dissolution__fe__ni5_fe4,
    P_dissolution__fe__ni5_fe3_cr1,
    P_dissolution__fe__ni5_fe2_cr2,
    P_dissolution__fe__ni5_fe1_cr3,
    P_dissolution__fe__ni5_cr4,
    P_dissolution__fe__ni4_fe5,
    P_dissolution__fe__ni4_fe4_cr1,
    P_dissolution__fe__ni4_fe3_cr2,
    P_dissolution__fe__ni4_fe2_cr3,
    P_dissolution__fe__ni4_fe1_cr4,
    P_dissolution__fe__ni4_cr5,
    P_dissolution__fe__ni3_fe6,
    P_dissolution__fe__ni3_fe5_cr1,
    P_dissolution__fe__ni3_fe4_cr2,
    P_dissolution__fe__ni3_fe3_cr3,
    P_dissolution__fe__ni3_fe2_cr4,
    P_dissolution__fe__ni3_fe1_cr5,
    P_dissolution__fe__ni3_cr6,
    P_dissolution__fe__ni2_fe7,
    P_dissolution__fe__ni2_fe6_cr1,
    P_dissolution__fe__ni2_fe5_cr2,
    P_dissolution__fe__ni2_fe4_cr3,
    P_dissolution__fe__ni2_fe3_cr4,
    P_dissolution__fe__ni2_fe2_cr5,
    P_dissolution__fe__ni2_fe1_cr6,
    P_dissolution__fe__ni2_cr7,
    P_dissolution__fe__ni1_fe8,
    P_dissolution__fe__ni1_fe7_cr1,
    P_dissolution__fe__ni1_fe6_cr2,
    P_dissolution__fe__ni1_fe5_cr3,
    P_dissolution__fe__ni1_fe4_cr4,
    P_dissolution__fe__ni1_fe3_cr5,
    P_dissolution__fe__ni1_fe2_cr6,
    P_dissolution__fe__ni1_fe1_cr7,
    P_dissolution__fe__ni1_cr8,
    P_dissolution__fe__fe9,
    P_dissolution__fe__fe8_cr1,
    P_dissolution__fe__fe7_cr2,
    P_dissolution__fe__fe6_cr3,
    P_dissolution__fe__fe5_cr4,
    P_dissolution__fe__fe4_cr5,
    P_dissolution__fe__fe3_cr6,
    P_dissolution__fe__fe2_cr7,
    P_dissolution__fe__fe1_cr8,
    P_dissolution__fe__cr9,
    P_dissolution__cr__ni3,
    P_dissolution__cr__ni2_fe1,
    P_dissolution__cr__ni2_cr1,
    P_dissolution__cr__ni1_fe2,
    P_dissolution__cr__ni1_fe1_cr1,
    P_dissolution__cr__ni1_cr2,
    P_dissolution__cr__fe3,
    P_dissolution__cr__fe2_cr1,
    P_dissolution__cr__fe1_cr2,
    P_dissolution__cr__cr3,
    P_dissolution__cr__ni4,
    P_dissolution__cr__ni3_fe1,
    P_dissolution__cr__ni3_cr1,
    P_dissolution__cr__ni2_fe2,
    P_dissolution__cr__ni2_fe1_cr1,
    P_dissolution__cr__ni2_cr2,
    P_dissolution__cr__ni1_fe3,
    P_dissolution__cr__ni1_fe2_cr1,
    P_dissolution__cr__ni1_fe1_cr2,
    P_dissolution__cr__ni1_cr3,
    P_dissolution__cr__fe4,
    P_dissolution__cr__fe3_cr1,
    P_dissolution__cr__fe2_cr2,
    P_dissolution__cr__fe1_cr3,
    P_dissolution__cr__cr4,
    P_dissolution__cr__ni5,
    P_dissolution__cr__ni4_fe1,
    P_dissolution__cr__ni4_cr1,
    P_dissolution__cr__ni3_fe2,
    P_dissolution__cr__ni3_fe1_cr1,
    P_dissolution__cr__ni3_cr2,
    P_dissolution__cr__ni2_fe3,
    P_dissolution__cr__ni2_fe2_cr1,
    P_dissolution__cr__ni2_fe1_cr2,
    P_dissolution__cr__ni2_cr3,
    P_dissolution__cr__ni1_fe4,
    P_dissolution__cr__ni1_fe3_cr1,
    P_dissolution__cr__ni1_fe2_cr2,
    P_dissolution__cr__ni1_fe1_cr3,
    P_dissolution__cr__ni1_cr4,
    P_dissolution__cr__fe5,
    P_dissolution__cr__fe4_cr1,
    P_dissolution__cr__fe3_cr2,
    P_dissolution__cr__fe2_cr3,
    P_dissolution__cr__fe1_cr4,
    P_dissolution__cr__cr5,
    P_dissolution__cr__ni6,
    P_dissolution__cr__ni5_fe1,
    P_dissolution__cr__ni5_cr1,
    P_dissolution__cr__ni4_fe2,
    P_dissolution__cr__ni4_fe1_cr1,
    P_dissolution__cr__ni4_cr2,
    P_dissolution__cr__ni3_fe3,
    P_dissolution__cr__ni3_fe2_cr1,
    P_dissolution__cr__ni3_fe1_cr2,
    P_dissolution__cr__ni3_cr3,
    P_dissolution__cr__ni2_fe4,
    P_dissolution__cr__ni2_fe3_cr1,
    P_dissolution__cr__ni2_fe2_cr2,
    P_dissolution__cr__ni2_fe1_cr3,
    P_dissolution__cr__ni2_cr4,
    P_dissolution__cr__ni1_fe5,
    P_dissolution__cr__ni1_fe4_cr1,
    P_dissolution__cr__ni1_fe3_cr2,
    P_dissolution__cr__ni1_fe2_cr3,
    P_dissolution__cr__ni1_fe1_cr4,
    P_dissolution__cr__ni1_cr5,
    P_dissolution__cr__fe6,
    P_dissolution__cr__fe5_cr1,
    P_dissolution__cr__fe4_cr2,
    P_dissolution__cr__fe3_cr3,
    P_dissolution__cr__fe2_cr4,
    P_dissolution__cr__fe1_cr5,
    P_dissolution__cr__cr6,
    P_dissolution__cr__ni7,
    P_dissolution__cr__ni6_fe1,
    P_dissolution__cr__ni6_cr1,
    P_dissolution__cr__ni5_fe2,
    P_dissolution__cr__ni5_fe1_cr1,
    P_dissolution__cr__ni5_cr2,
    P_dissolution__cr__ni4_fe3,
    P_dissolution__cr__ni4_fe2_cr1,
    P_dissolution__cr__ni4_fe1_cr2,
    P_dissolution__cr__ni4_cr3,
    P_dissolution__cr__ni3_fe4,
    P_dissolution__cr__ni3_fe3_cr1,
    P_dissolution__cr__ni3_fe2_cr2,
    P_dissolution__cr__ni3_fe1_cr3,
    P_dissolution__cr__ni3_cr4,
    P_dissolution__cr__ni2_fe5,
    P_dissolution__cr__ni2_fe4_cr1,
    P_dissolution__cr__ni2_fe3_cr2,
    P_dissolution__cr__ni2_fe2_cr3,
    P_dissolution__cr__ni2_fe1_cr4,
    P_dissolution__cr__ni2_cr5,
    P_dissolution__cr__ni1_fe6,
    P_dissolution__cr__ni1_fe5_cr1,
    P_dissolution__cr__ni1_fe4_cr2,
    P_dissolution__cr__ni1_fe3_cr3,
    P_dissolution__cr__ni1_fe2_cr4,
    P_dissolution__cr__ni1_fe1_cr5,
    P_dissolution__cr__ni1_cr6,
    P_dissolution__cr__fe7,
    P_dissolution__cr__fe6_cr1,
    P_dissolution__cr__fe5_cr2,
    P_dissolution__cr__fe4_cr3,
    P_dissolution__cr__fe3_cr4,
    P_dissolution__cr__fe2_cr5,
    P_dissolution__cr__fe1_cr6,
    P_dissolution__cr__cr7,
    P_dissolution__cr__ni8,
    P_dissolution__cr__ni7_fe1,
    P_dissolution__cr__ni7_cr1,
    P_dissolution__cr__ni6_fe2,
    P_dissolution__cr__ni6_fe1_cr1,
    P_dissolution__cr__ni6_cr2,
    P_dissolution__cr__ni5_fe3,
    P_dissolution__cr__ni5_fe2_cr1,
    P_dissolution__cr__ni5_fe1_cr2,
    P_dissolution__cr__ni5_cr3,
    P_dissolution__cr__ni4_fe4,
    P_dissolution__cr__ni4_fe3_cr1,
    P_dissolution__cr__ni4_fe2_cr2,
    P_dissolution__cr__ni4_fe1_cr3,
    P_dissolution__cr__ni4_cr4,
    P_dissolution__cr__ni3_fe5,
    P_dissolution__cr__ni3_fe4_cr1,
    P_dissolution__cr__ni3_fe3_cr2,
    P_dissolution__cr__ni3_fe2_cr3,
    P_dissolution__cr__ni3_fe1_cr4,
    P_dissolution__cr__ni3_cr5,
    P_dissolution__cr__ni2_fe6,
    P_dissolution__cr__ni2_fe5_cr1,
    P_dissolution__cr__ni2_fe4_cr2,
    P_dissolution__cr__ni2_fe3_cr3,
    P_dissolution__cr__ni2_fe2_cr4,
    P_dissolution__cr__ni2_fe1_cr5,
    P_dissolution__cr__ni2_cr6,
    P_dissolution__cr__ni1_fe7,
    P_dissolution__cr__ni1_fe6_cr1,
    P_dissolution__cr__ni1_fe5_cr2,
    P_dissolution__cr__ni1_fe4_cr3,
    P_dissolution__cr__ni1_fe3_cr4,
    P_dissolution__cr__ni1_fe2_cr5,
    P_dissolution__cr__ni1_fe1_cr6,
    P_dissolution__cr__ni1_cr7,
    P_dissolution__cr__fe8,
    P_dissolution__cr__fe7_cr1,
    P_dissolution__cr__fe6_cr2,
    P_dissolution__cr__fe5_cr3,
    P_dissolution__cr__fe4_cr4,
    P_dissolution__cr__fe3_cr5,
    P_dissolution__cr__fe2_cr6,
    P_dissolution__cr__fe1_cr7,
    P_dissolution__cr__cr8,
    P_dissolution__cr__ni9,
    P_dissolution__cr__ni8_fe1,
    P_dissolution__cr__ni8_cr1,
    P_dissolution__cr__ni7_fe2,
    P_dissolution__cr__ni7_fe1_cr1,
    P_dissolution__cr__ni7_cr2,
    P_dissolution__cr__ni6_fe3,
    P_dissolution__cr__ni6_fe2_cr1,
    P_dissolution__cr__ni6_fe1_cr2,
    P_dissolution__cr__ni6_cr3,
    P_dissolution__cr__ni5_fe4,
    P_dissolution__cr__ni5_fe3_cr1,
    P_dissolution__cr__ni5_fe2_cr2,
    P_dissolution__cr__ni5_fe1_cr3,
    P_dissolution__cr__ni5_cr4,
    P_dissolution__cr__ni4_fe5,
    P_dissolution__cr__ni4_fe4_cr1,
    P_dissolution__cr__ni4_fe3_cr2,
    P_dissolution__cr__ni4_fe2_cr3,
    P_dissolution__cr__ni4_fe1_cr4,
    P_dissolution__cr__ni4_cr5,
    P_dissolution__cr__ni3_fe6,
    P_dissolution__cr__ni3_fe5_cr1,
    P_dissolution__cr__ni3_fe4_cr2,
    P_dissolution__cr__ni3_fe3_cr3,
    P_dissolution__cr__ni3_fe2_cr4,
    P_dissolution__cr__ni3_fe1_cr5,
    P_dissolution__cr__ni3_cr6,
    P_dissolution__cr__ni2_fe7,
    P_dissolution__cr__ni2_fe6_cr1,
    P_dissolution__cr__ni2_fe5_cr2,
    P_dissolution__cr__ni2_fe4_cr3,
    P_dissolution__cr__ni2_fe3_cr4,
    P_dissolution__cr__ni2_fe2_cr5,
    P_dissolution__cr__ni2_fe1_cr6,
    P_dissolution__cr__ni2_cr7,
    P_dissolution__cr__ni1_fe8,
    P_dissolution__cr__ni1_fe7_cr1,
    P_dissolution__cr__ni1_fe6_cr2,
    P_dissolution__cr__ni1_fe5_cr3,
    P_dissolution__cr__ni1_fe4_cr4,
    P_dissolution__cr__ni1_fe3_cr5,
    P_dissolution__cr__ni1_fe2_cr6,
    P_dissolution__cr__ni1_fe1_cr7,
    P_dissolution__cr__ni1_cr8,
    P_dissolution__cr__fe9,
    P_dissolution__cr__fe8_cr1,
    P_dissolution__cr__fe7_cr2,
    P_dissolution__cr__fe6_cr3,
    P_dissolution__cr__fe5_cr4,
    P_dissolution__cr__fe4_cr5,
    P_dissolution__cr__fe3_cr6,
    P_dissolution__cr__fe2_cr7,
    P_dissolution__cr__fe1_cr8,
    P_dissolution__cr__cr9,
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
    [P_dissolution__ni__ni3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.600000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.580000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.634000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.560000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.614000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.668000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.540000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.594000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.648000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.702000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.800000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.780000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.834000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.760000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.814000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.868000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.740000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.794000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.848000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.902000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.720000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.774000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.828000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.882000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.936000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.000000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.980000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.034000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.960000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.014000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.068000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.940000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.994000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.048000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.102000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.920000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.974000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.028000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.082000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.136000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.900000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.954000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.008000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.062000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.116000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.170000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.200000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.180000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.234000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.160000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.214000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.268000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.140000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.194000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.248000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.302000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.120000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.174000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.228000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.282000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.336000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.100000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.154000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.208000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.262000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.316000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.370000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.080000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.134000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.188000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.242000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.296000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.350000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.404000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.400000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.380000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.434000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.360000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.414000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.468000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.340000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.394000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.448000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.502000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.320000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.374000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.428000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.482000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.536000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.300000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.354000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.408000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.462000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.516000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.570000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.280000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.334000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.388000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.442000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.496000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.550000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.604000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.260000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.314000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.368000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.422000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.476000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.530000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.584000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.638000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.600000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.580000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.634000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.560000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.614000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.668000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.540000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.594000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.648000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.702000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.520000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.574000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.628000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.682000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.736000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.500000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.554000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.608000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.662000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.716000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.770000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.480000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.534000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.588000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.642000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.696000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.750000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.804000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.460000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.514000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.568000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.622000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.676000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.730000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.784000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.838000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.440000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.494000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.548000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.602000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.656000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.710000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.764000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.818000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.872000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.800000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni8_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.780000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.834000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.760000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.814000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.868000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.740000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.794000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.848000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.902000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.720000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.774000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.828000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.882000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.936000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.700000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.754000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.808000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.862000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.916000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.970000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.680000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.734000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.788000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.842000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.896000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.950000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.004000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.660000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.714000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.768000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.822000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.876000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.930000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.984000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.038000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.640000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.694000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.748000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.802000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.856000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.910000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.964000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.018000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__ni1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.072000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.620000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.674000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.728000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.782000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.836000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.890000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.944000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.998000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__fe1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.052000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__ni__cr9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.106000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.540000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.522000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.567000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.504000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.549000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.594000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.486000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.531000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.576000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.621000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.720000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.702000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.747000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.684000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.729000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.774000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.666000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.711000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.756000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.801000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.648000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.693000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.738000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.783000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.828000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.900000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.882000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.927000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.864000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.909000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.954000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.846000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.891000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.936000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.981000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.828000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.873000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.918000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.963000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.008000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.810000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.855000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.900000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.945000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.990000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.035000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.080000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.062000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.107000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.044000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.089000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.134000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.026000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.071000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.116000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.161000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.008000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.053000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.098000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.143000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.188000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.990000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.035000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.080000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.125000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.170000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.215000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.972000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.017000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.062000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.107000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.152000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.197000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.242000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.260000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.242000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.287000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.224000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.269000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.314000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.206000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.251000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.296000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.341000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.188000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.233000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.278000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.323000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.368000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.170000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.215000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.260000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.305000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.350000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.395000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.152000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.197000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.242000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.287000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.332000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.377000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.422000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.134000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.179000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.224000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.269000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.314000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.359000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.404000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.449000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.440000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.422000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.467000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.404000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.449000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.494000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.386000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.431000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.476000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.521000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.368000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.413000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.458000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.503000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.548000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.350000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.395000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.440000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.485000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.530000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.575000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.332000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.377000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.422000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.467000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.512000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.557000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.602000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.314000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.359000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.404000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.449000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.494000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.539000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.584000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.629000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.296000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.341000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.386000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.431000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.476000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.521000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.566000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.611000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.656000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.620000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni8_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.602000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.647000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.584000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.629000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.674000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.566000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.611000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.656000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.701000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.548000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.593000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.638000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.683000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.728000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.530000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.575000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.620000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.665000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.710000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.755000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.512000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.557000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.602000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.647000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.692000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.737000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.782000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.494000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.539000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.584000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.629000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.674000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.719000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.764000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.809000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.476000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.521000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.566000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.611000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.656000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.701000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.746000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.791000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__ni1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.836000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.458000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.503000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.548000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.593000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.638000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.683000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.728000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.773000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__fe1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.818000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__fe__cr9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.863000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.702000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.675000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.757000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.648000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.730000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.812000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.621000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.703000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.785000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.867000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.936000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.909000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.991000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.882000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.964000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.046000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.855000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.937000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.019000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.101000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.828000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.910000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 0.992000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.074000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.156000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.170000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.143000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.225000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.116000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.198000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.280000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.089000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.171000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.253000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.335000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.062000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.144000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.226000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.308000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.390000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.035000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.117000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.199000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.281000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.363000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.445000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.404000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.377000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.459000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.350000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.432000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.514000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.323000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.405000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.487000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.569000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.296000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.378000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.460000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.542000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.624000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.269000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.351000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.433000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.515000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.597000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.679000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.242000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.324000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.406000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.488000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.570000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.652000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.734000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.638000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.611000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.693000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.584000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.666000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.748000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.557000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.639000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.721000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.803000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.530000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.612000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.694000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.776000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.858000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.503000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.585000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.667000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.749000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.831000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.913000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.476000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.558000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.640000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.722000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.804000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.886000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.968000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.449000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.531000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.613000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.695000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.777000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.859000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.941000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.023000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.872000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.845000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.927000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.818000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.900000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.982000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.791000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.873000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.955000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.037000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.764000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.846000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.928000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.010000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.092000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.737000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.819000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.901000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.983000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.065000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.147000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.710000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.792000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.874000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.956000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.038000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.120000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.202000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.683000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.765000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.847000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.929000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.011000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.093000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.175000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.257000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.656000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.738000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.820000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.902000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.984000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.066000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.148000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.230000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.312000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.106000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni8_fe1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.079000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.161000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7_fe2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.052000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7_fe1_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.134000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.216000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.025000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe2_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.107000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_fe1_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.189000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.271000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.998000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe3_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.080000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe2_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.162000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_fe1_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.244000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.326000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.971000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe4_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.053000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe3_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.135000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe2_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.217000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_fe1_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.299000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.381000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.944000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe5_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.026000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe4_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.108000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe3_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.190000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe2_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.272000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_fe1_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.354000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.436000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.917000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe6_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.999000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe5_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.081000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe4_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.163000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe3_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.245000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe2_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.327000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_fe1_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.409000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.491000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.890000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe7_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.972000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe6_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.054000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe5_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.136000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe4_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.218000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe3_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.300000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe2_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.382000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_fe1_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.464000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__ni1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.546000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.863000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe8_cr1] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 1.945000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe7_cr2] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.027000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe6_cr3] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.109000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe5_cr4] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.191000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe4_cr5] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.273000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe3_cr6] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.355000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe2_cr7] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.437000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__fe1_cr8] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.519000, .is_electrochemical = 1, ._pad = 0 },
    [P_dissolution__cr__cr9] = { .prefactor_Hz = 1.0000000000e+04, .Ea_eV = 2.601000, .is_electrochemical = 1, ._pad = 0 },
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

static HopOutcome apply_actions_dissolution__ni__ni3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni8_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__ni1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__fe1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__ni__cr9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_NI, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni8_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__ni1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__fe1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__fe__cr9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_FE, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni8_fe1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7_fe2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7_fe1_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe2_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_fe1_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe3_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe2_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_fe1_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe4_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe3_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe2_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_fe1_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe5_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe4_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe3_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe2_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_fe1_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe6_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe5_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe4_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe3_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe2_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_fe1_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe7_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe6_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe5_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe4_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe3_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe2_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_fe1_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__ni1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe8_cr1(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe7_cr2(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe6_cr3(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe5_cr4(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe4_cr5(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe3_cr6(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe2_cr7(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__fe1_cr8(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
}

static HopOutcome apply_actions_dissolution__cr__cr9(State *st, const Lattice *lat, int site) {
    (void)lat;
    StateAction acts[1] = {
        { .site = site, .before = SP_CR, .after = SP_VACANT },
    };
    (void)state_apply_actions(st, acts, 1, SP_VACANT);
    return (HopOutcome){ .v_origin = -1, .v_dest = -1 };
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
    [P_dissolution__ni__ni3] = apply_actions_dissolution__ni__ni3,
    [P_dissolution__ni__ni2_fe1] = apply_actions_dissolution__ni__ni2_fe1,
    [P_dissolution__ni__ni2_cr1] = apply_actions_dissolution__ni__ni2_cr1,
    [P_dissolution__ni__ni1_fe2] = apply_actions_dissolution__ni__ni1_fe2,
    [P_dissolution__ni__ni1_fe1_cr1] = apply_actions_dissolution__ni__ni1_fe1_cr1,
    [P_dissolution__ni__ni1_cr2] = apply_actions_dissolution__ni__ni1_cr2,
    [P_dissolution__ni__fe3] = apply_actions_dissolution__ni__fe3,
    [P_dissolution__ni__fe2_cr1] = apply_actions_dissolution__ni__fe2_cr1,
    [P_dissolution__ni__fe1_cr2] = apply_actions_dissolution__ni__fe1_cr2,
    [P_dissolution__ni__cr3] = apply_actions_dissolution__ni__cr3,
    [P_dissolution__ni__ni4] = apply_actions_dissolution__ni__ni4,
    [P_dissolution__ni__ni3_fe1] = apply_actions_dissolution__ni__ni3_fe1,
    [P_dissolution__ni__ni3_cr1] = apply_actions_dissolution__ni__ni3_cr1,
    [P_dissolution__ni__ni2_fe2] = apply_actions_dissolution__ni__ni2_fe2,
    [P_dissolution__ni__ni2_fe1_cr1] = apply_actions_dissolution__ni__ni2_fe1_cr1,
    [P_dissolution__ni__ni2_cr2] = apply_actions_dissolution__ni__ni2_cr2,
    [P_dissolution__ni__ni1_fe3] = apply_actions_dissolution__ni__ni1_fe3,
    [P_dissolution__ni__ni1_fe2_cr1] = apply_actions_dissolution__ni__ni1_fe2_cr1,
    [P_dissolution__ni__ni1_fe1_cr2] = apply_actions_dissolution__ni__ni1_fe1_cr2,
    [P_dissolution__ni__ni1_cr3] = apply_actions_dissolution__ni__ni1_cr3,
    [P_dissolution__ni__fe4] = apply_actions_dissolution__ni__fe4,
    [P_dissolution__ni__fe3_cr1] = apply_actions_dissolution__ni__fe3_cr1,
    [P_dissolution__ni__fe2_cr2] = apply_actions_dissolution__ni__fe2_cr2,
    [P_dissolution__ni__fe1_cr3] = apply_actions_dissolution__ni__fe1_cr3,
    [P_dissolution__ni__cr4] = apply_actions_dissolution__ni__cr4,
    [P_dissolution__ni__ni5] = apply_actions_dissolution__ni__ni5,
    [P_dissolution__ni__ni4_fe1] = apply_actions_dissolution__ni__ni4_fe1,
    [P_dissolution__ni__ni4_cr1] = apply_actions_dissolution__ni__ni4_cr1,
    [P_dissolution__ni__ni3_fe2] = apply_actions_dissolution__ni__ni3_fe2,
    [P_dissolution__ni__ni3_fe1_cr1] = apply_actions_dissolution__ni__ni3_fe1_cr1,
    [P_dissolution__ni__ni3_cr2] = apply_actions_dissolution__ni__ni3_cr2,
    [P_dissolution__ni__ni2_fe3] = apply_actions_dissolution__ni__ni2_fe3,
    [P_dissolution__ni__ni2_fe2_cr1] = apply_actions_dissolution__ni__ni2_fe2_cr1,
    [P_dissolution__ni__ni2_fe1_cr2] = apply_actions_dissolution__ni__ni2_fe1_cr2,
    [P_dissolution__ni__ni2_cr3] = apply_actions_dissolution__ni__ni2_cr3,
    [P_dissolution__ni__ni1_fe4] = apply_actions_dissolution__ni__ni1_fe4,
    [P_dissolution__ni__ni1_fe3_cr1] = apply_actions_dissolution__ni__ni1_fe3_cr1,
    [P_dissolution__ni__ni1_fe2_cr2] = apply_actions_dissolution__ni__ni1_fe2_cr2,
    [P_dissolution__ni__ni1_fe1_cr3] = apply_actions_dissolution__ni__ni1_fe1_cr3,
    [P_dissolution__ni__ni1_cr4] = apply_actions_dissolution__ni__ni1_cr4,
    [P_dissolution__ni__fe5] = apply_actions_dissolution__ni__fe5,
    [P_dissolution__ni__fe4_cr1] = apply_actions_dissolution__ni__fe4_cr1,
    [P_dissolution__ni__fe3_cr2] = apply_actions_dissolution__ni__fe3_cr2,
    [P_dissolution__ni__fe2_cr3] = apply_actions_dissolution__ni__fe2_cr3,
    [P_dissolution__ni__fe1_cr4] = apply_actions_dissolution__ni__fe1_cr4,
    [P_dissolution__ni__cr5] = apply_actions_dissolution__ni__cr5,
    [P_dissolution__ni__ni6] = apply_actions_dissolution__ni__ni6,
    [P_dissolution__ni__ni5_fe1] = apply_actions_dissolution__ni__ni5_fe1,
    [P_dissolution__ni__ni5_cr1] = apply_actions_dissolution__ni__ni5_cr1,
    [P_dissolution__ni__ni4_fe2] = apply_actions_dissolution__ni__ni4_fe2,
    [P_dissolution__ni__ni4_fe1_cr1] = apply_actions_dissolution__ni__ni4_fe1_cr1,
    [P_dissolution__ni__ni4_cr2] = apply_actions_dissolution__ni__ni4_cr2,
    [P_dissolution__ni__ni3_fe3] = apply_actions_dissolution__ni__ni3_fe3,
    [P_dissolution__ni__ni3_fe2_cr1] = apply_actions_dissolution__ni__ni3_fe2_cr1,
    [P_dissolution__ni__ni3_fe1_cr2] = apply_actions_dissolution__ni__ni3_fe1_cr2,
    [P_dissolution__ni__ni3_cr3] = apply_actions_dissolution__ni__ni3_cr3,
    [P_dissolution__ni__ni2_fe4] = apply_actions_dissolution__ni__ni2_fe4,
    [P_dissolution__ni__ni2_fe3_cr1] = apply_actions_dissolution__ni__ni2_fe3_cr1,
    [P_dissolution__ni__ni2_fe2_cr2] = apply_actions_dissolution__ni__ni2_fe2_cr2,
    [P_dissolution__ni__ni2_fe1_cr3] = apply_actions_dissolution__ni__ni2_fe1_cr3,
    [P_dissolution__ni__ni2_cr4] = apply_actions_dissolution__ni__ni2_cr4,
    [P_dissolution__ni__ni1_fe5] = apply_actions_dissolution__ni__ni1_fe5,
    [P_dissolution__ni__ni1_fe4_cr1] = apply_actions_dissolution__ni__ni1_fe4_cr1,
    [P_dissolution__ni__ni1_fe3_cr2] = apply_actions_dissolution__ni__ni1_fe3_cr2,
    [P_dissolution__ni__ni1_fe2_cr3] = apply_actions_dissolution__ni__ni1_fe2_cr3,
    [P_dissolution__ni__ni1_fe1_cr4] = apply_actions_dissolution__ni__ni1_fe1_cr4,
    [P_dissolution__ni__ni1_cr5] = apply_actions_dissolution__ni__ni1_cr5,
    [P_dissolution__ni__fe6] = apply_actions_dissolution__ni__fe6,
    [P_dissolution__ni__fe5_cr1] = apply_actions_dissolution__ni__fe5_cr1,
    [P_dissolution__ni__fe4_cr2] = apply_actions_dissolution__ni__fe4_cr2,
    [P_dissolution__ni__fe3_cr3] = apply_actions_dissolution__ni__fe3_cr3,
    [P_dissolution__ni__fe2_cr4] = apply_actions_dissolution__ni__fe2_cr4,
    [P_dissolution__ni__fe1_cr5] = apply_actions_dissolution__ni__fe1_cr5,
    [P_dissolution__ni__cr6] = apply_actions_dissolution__ni__cr6,
    [P_dissolution__ni__ni7] = apply_actions_dissolution__ni__ni7,
    [P_dissolution__ni__ni6_fe1] = apply_actions_dissolution__ni__ni6_fe1,
    [P_dissolution__ni__ni6_cr1] = apply_actions_dissolution__ni__ni6_cr1,
    [P_dissolution__ni__ni5_fe2] = apply_actions_dissolution__ni__ni5_fe2,
    [P_dissolution__ni__ni5_fe1_cr1] = apply_actions_dissolution__ni__ni5_fe1_cr1,
    [P_dissolution__ni__ni5_cr2] = apply_actions_dissolution__ni__ni5_cr2,
    [P_dissolution__ni__ni4_fe3] = apply_actions_dissolution__ni__ni4_fe3,
    [P_dissolution__ni__ni4_fe2_cr1] = apply_actions_dissolution__ni__ni4_fe2_cr1,
    [P_dissolution__ni__ni4_fe1_cr2] = apply_actions_dissolution__ni__ni4_fe1_cr2,
    [P_dissolution__ni__ni4_cr3] = apply_actions_dissolution__ni__ni4_cr3,
    [P_dissolution__ni__ni3_fe4] = apply_actions_dissolution__ni__ni3_fe4,
    [P_dissolution__ni__ni3_fe3_cr1] = apply_actions_dissolution__ni__ni3_fe3_cr1,
    [P_dissolution__ni__ni3_fe2_cr2] = apply_actions_dissolution__ni__ni3_fe2_cr2,
    [P_dissolution__ni__ni3_fe1_cr3] = apply_actions_dissolution__ni__ni3_fe1_cr3,
    [P_dissolution__ni__ni3_cr4] = apply_actions_dissolution__ni__ni3_cr4,
    [P_dissolution__ni__ni2_fe5] = apply_actions_dissolution__ni__ni2_fe5,
    [P_dissolution__ni__ni2_fe4_cr1] = apply_actions_dissolution__ni__ni2_fe4_cr1,
    [P_dissolution__ni__ni2_fe3_cr2] = apply_actions_dissolution__ni__ni2_fe3_cr2,
    [P_dissolution__ni__ni2_fe2_cr3] = apply_actions_dissolution__ni__ni2_fe2_cr3,
    [P_dissolution__ni__ni2_fe1_cr4] = apply_actions_dissolution__ni__ni2_fe1_cr4,
    [P_dissolution__ni__ni2_cr5] = apply_actions_dissolution__ni__ni2_cr5,
    [P_dissolution__ni__ni1_fe6] = apply_actions_dissolution__ni__ni1_fe6,
    [P_dissolution__ni__ni1_fe5_cr1] = apply_actions_dissolution__ni__ni1_fe5_cr1,
    [P_dissolution__ni__ni1_fe4_cr2] = apply_actions_dissolution__ni__ni1_fe4_cr2,
    [P_dissolution__ni__ni1_fe3_cr3] = apply_actions_dissolution__ni__ni1_fe3_cr3,
    [P_dissolution__ni__ni1_fe2_cr4] = apply_actions_dissolution__ni__ni1_fe2_cr4,
    [P_dissolution__ni__ni1_fe1_cr5] = apply_actions_dissolution__ni__ni1_fe1_cr5,
    [P_dissolution__ni__ni1_cr6] = apply_actions_dissolution__ni__ni1_cr6,
    [P_dissolution__ni__fe7] = apply_actions_dissolution__ni__fe7,
    [P_dissolution__ni__fe6_cr1] = apply_actions_dissolution__ni__fe6_cr1,
    [P_dissolution__ni__fe5_cr2] = apply_actions_dissolution__ni__fe5_cr2,
    [P_dissolution__ni__fe4_cr3] = apply_actions_dissolution__ni__fe4_cr3,
    [P_dissolution__ni__fe3_cr4] = apply_actions_dissolution__ni__fe3_cr4,
    [P_dissolution__ni__fe2_cr5] = apply_actions_dissolution__ni__fe2_cr5,
    [P_dissolution__ni__fe1_cr6] = apply_actions_dissolution__ni__fe1_cr6,
    [P_dissolution__ni__cr7] = apply_actions_dissolution__ni__cr7,
    [P_dissolution__ni__ni8] = apply_actions_dissolution__ni__ni8,
    [P_dissolution__ni__ni7_fe1] = apply_actions_dissolution__ni__ni7_fe1,
    [P_dissolution__ni__ni7_cr1] = apply_actions_dissolution__ni__ni7_cr1,
    [P_dissolution__ni__ni6_fe2] = apply_actions_dissolution__ni__ni6_fe2,
    [P_dissolution__ni__ni6_fe1_cr1] = apply_actions_dissolution__ni__ni6_fe1_cr1,
    [P_dissolution__ni__ni6_cr2] = apply_actions_dissolution__ni__ni6_cr2,
    [P_dissolution__ni__ni5_fe3] = apply_actions_dissolution__ni__ni5_fe3,
    [P_dissolution__ni__ni5_fe2_cr1] = apply_actions_dissolution__ni__ni5_fe2_cr1,
    [P_dissolution__ni__ni5_fe1_cr2] = apply_actions_dissolution__ni__ni5_fe1_cr2,
    [P_dissolution__ni__ni5_cr3] = apply_actions_dissolution__ni__ni5_cr3,
    [P_dissolution__ni__ni4_fe4] = apply_actions_dissolution__ni__ni4_fe4,
    [P_dissolution__ni__ni4_fe3_cr1] = apply_actions_dissolution__ni__ni4_fe3_cr1,
    [P_dissolution__ni__ni4_fe2_cr2] = apply_actions_dissolution__ni__ni4_fe2_cr2,
    [P_dissolution__ni__ni4_fe1_cr3] = apply_actions_dissolution__ni__ni4_fe1_cr3,
    [P_dissolution__ni__ni4_cr4] = apply_actions_dissolution__ni__ni4_cr4,
    [P_dissolution__ni__ni3_fe5] = apply_actions_dissolution__ni__ni3_fe5,
    [P_dissolution__ni__ni3_fe4_cr1] = apply_actions_dissolution__ni__ni3_fe4_cr1,
    [P_dissolution__ni__ni3_fe3_cr2] = apply_actions_dissolution__ni__ni3_fe3_cr2,
    [P_dissolution__ni__ni3_fe2_cr3] = apply_actions_dissolution__ni__ni3_fe2_cr3,
    [P_dissolution__ni__ni3_fe1_cr4] = apply_actions_dissolution__ni__ni3_fe1_cr4,
    [P_dissolution__ni__ni3_cr5] = apply_actions_dissolution__ni__ni3_cr5,
    [P_dissolution__ni__ni2_fe6] = apply_actions_dissolution__ni__ni2_fe6,
    [P_dissolution__ni__ni2_fe5_cr1] = apply_actions_dissolution__ni__ni2_fe5_cr1,
    [P_dissolution__ni__ni2_fe4_cr2] = apply_actions_dissolution__ni__ni2_fe4_cr2,
    [P_dissolution__ni__ni2_fe3_cr3] = apply_actions_dissolution__ni__ni2_fe3_cr3,
    [P_dissolution__ni__ni2_fe2_cr4] = apply_actions_dissolution__ni__ni2_fe2_cr4,
    [P_dissolution__ni__ni2_fe1_cr5] = apply_actions_dissolution__ni__ni2_fe1_cr5,
    [P_dissolution__ni__ni2_cr6] = apply_actions_dissolution__ni__ni2_cr6,
    [P_dissolution__ni__ni1_fe7] = apply_actions_dissolution__ni__ni1_fe7,
    [P_dissolution__ni__ni1_fe6_cr1] = apply_actions_dissolution__ni__ni1_fe6_cr1,
    [P_dissolution__ni__ni1_fe5_cr2] = apply_actions_dissolution__ni__ni1_fe5_cr2,
    [P_dissolution__ni__ni1_fe4_cr3] = apply_actions_dissolution__ni__ni1_fe4_cr3,
    [P_dissolution__ni__ni1_fe3_cr4] = apply_actions_dissolution__ni__ni1_fe3_cr4,
    [P_dissolution__ni__ni1_fe2_cr5] = apply_actions_dissolution__ni__ni1_fe2_cr5,
    [P_dissolution__ni__ni1_fe1_cr6] = apply_actions_dissolution__ni__ni1_fe1_cr6,
    [P_dissolution__ni__ni1_cr7] = apply_actions_dissolution__ni__ni1_cr7,
    [P_dissolution__ni__fe8] = apply_actions_dissolution__ni__fe8,
    [P_dissolution__ni__fe7_cr1] = apply_actions_dissolution__ni__fe7_cr1,
    [P_dissolution__ni__fe6_cr2] = apply_actions_dissolution__ni__fe6_cr2,
    [P_dissolution__ni__fe5_cr3] = apply_actions_dissolution__ni__fe5_cr3,
    [P_dissolution__ni__fe4_cr4] = apply_actions_dissolution__ni__fe4_cr4,
    [P_dissolution__ni__fe3_cr5] = apply_actions_dissolution__ni__fe3_cr5,
    [P_dissolution__ni__fe2_cr6] = apply_actions_dissolution__ni__fe2_cr6,
    [P_dissolution__ni__fe1_cr7] = apply_actions_dissolution__ni__fe1_cr7,
    [P_dissolution__ni__cr8] = apply_actions_dissolution__ni__cr8,
    [P_dissolution__ni__ni9] = apply_actions_dissolution__ni__ni9,
    [P_dissolution__ni__ni8_fe1] = apply_actions_dissolution__ni__ni8_fe1,
    [P_dissolution__ni__ni8_cr1] = apply_actions_dissolution__ni__ni8_cr1,
    [P_dissolution__ni__ni7_fe2] = apply_actions_dissolution__ni__ni7_fe2,
    [P_dissolution__ni__ni7_fe1_cr1] = apply_actions_dissolution__ni__ni7_fe1_cr1,
    [P_dissolution__ni__ni7_cr2] = apply_actions_dissolution__ni__ni7_cr2,
    [P_dissolution__ni__ni6_fe3] = apply_actions_dissolution__ni__ni6_fe3,
    [P_dissolution__ni__ni6_fe2_cr1] = apply_actions_dissolution__ni__ni6_fe2_cr1,
    [P_dissolution__ni__ni6_fe1_cr2] = apply_actions_dissolution__ni__ni6_fe1_cr2,
    [P_dissolution__ni__ni6_cr3] = apply_actions_dissolution__ni__ni6_cr3,
    [P_dissolution__ni__ni5_fe4] = apply_actions_dissolution__ni__ni5_fe4,
    [P_dissolution__ni__ni5_fe3_cr1] = apply_actions_dissolution__ni__ni5_fe3_cr1,
    [P_dissolution__ni__ni5_fe2_cr2] = apply_actions_dissolution__ni__ni5_fe2_cr2,
    [P_dissolution__ni__ni5_fe1_cr3] = apply_actions_dissolution__ni__ni5_fe1_cr3,
    [P_dissolution__ni__ni5_cr4] = apply_actions_dissolution__ni__ni5_cr4,
    [P_dissolution__ni__ni4_fe5] = apply_actions_dissolution__ni__ni4_fe5,
    [P_dissolution__ni__ni4_fe4_cr1] = apply_actions_dissolution__ni__ni4_fe4_cr1,
    [P_dissolution__ni__ni4_fe3_cr2] = apply_actions_dissolution__ni__ni4_fe3_cr2,
    [P_dissolution__ni__ni4_fe2_cr3] = apply_actions_dissolution__ni__ni4_fe2_cr3,
    [P_dissolution__ni__ni4_fe1_cr4] = apply_actions_dissolution__ni__ni4_fe1_cr4,
    [P_dissolution__ni__ni4_cr5] = apply_actions_dissolution__ni__ni4_cr5,
    [P_dissolution__ni__ni3_fe6] = apply_actions_dissolution__ni__ni3_fe6,
    [P_dissolution__ni__ni3_fe5_cr1] = apply_actions_dissolution__ni__ni3_fe5_cr1,
    [P_dissolution__ni__ni3_fe4_cr2] = apply_actions_dissolution__ni__ni3_fe4_cr2,
    [P_dissolution__ni__ni3_fe3_cr3] = apply_actions_dissolution__ni__ni3_fe3_cr3,
    [P_dissolution__ni__ni3_fe2_cr4] = apply_actions_dissolution__ni__ni3_fe2_cr4,
    [P_dissolution__ni__ni3_fe1_cr5] = apply_actions_dissolution__ni__ni3_fe1_cr5,
    [P_dissolution__ni__ni3_cr6] = apply_actions_dissolution__ni__ni3_cr6,
    [P_dissolution__ni__ni2_fe7] = apply_actions_dissolution__ni__ni2_fe7,
    [P_dissolution__ni__ni2_fe6_cr1] = apply_actions_dissolution__ni__ni2_fe6_cr1,
    [P_dissolution__ni__ni2_fe5_cr2] = apply_actions_dissolution__ni__ni2_fe5_cr2,
    [P_dissolution__ni__ni2_fe4_cr3] = apply_actions_dissolution__ni__ni2_fe4_cr3,
    [P_dissolution__ni__ni2_fe3_cr4] = apply_actions_dissolution__ni__ni2_fe3_cr4,
    [P_dissolution__ni__ni2_fe2_cr5] = apply_actions_dissolution__ni__ni2_fe2_cr5,
    [P_dissolution__ni__ni2_fe1_cr6] = apply_actions_dissolution__ni__ni2_fe1_cr6,
    [P_dissolution__ni__ni2_cr7] = apply_actions_dissolution__ni__ni2_cr7,
    [P_dissolution__ni__ni1_fe8] = apply_actions_dissolution__ni__ni1_fe8,
    [P_dissolution__ni__ni1_fe7_cr1] = apply_actions_dissolution__ni__ni1_fe7_cr1,
    [P_dissolution__ni__ni1_fe6_cr2] = apply_actions_dissolution__ni__ni1_fe6_cr2,
    [P_dissolution__ni__ni1_fe5_cr3] = apply_actions_dissolution__ni__ni1_fe5_cr3,
    [P_dissolution__ni__ni1_fe4_cr4] = apply_actions_dissolution__ni__ni1_fe4_cr4,
    [P_dissolution__ni__ni1_fe3_cr5] = apply_actions_dissolution__ni__ni1_fe3_cr5,
    [P_dissolution__ni__ni1_fe2_cr6] = apply_actions_dissolution__ni__ni1_fe2_cr6,
    [P_dissolution__ni__ni1_fe1_cr7] = apply_actions_dissolution__ni__ni1_fe1_cr7,
    [P_dissolution__ni__ni1_cr8] = apply_actions_dissolution__ni__ni1_cr8,
    [P_dissolution__ni__fe9] = apply_actions_dissolution__ni__fe9,
    [P_dissolution__ni__fe8_cr1] = apply_actions_dissolution__ni__fe8_cr1,
    [P_dissolution__ni__fe7_cr2] = apply_actions_dissolution__ni__fe7_cr2,
    [P_dissolution__ni__fe6_cr3] = apply_actions_dissolution__ni__fe6_cr3,
    [P_dissolution__ni__fe5_cr4] = apply_actions_dissolution__ni__fe5_cr4,
    [P_dissolution__ni__fe4_cr5] = apply_actions_dissolution__ni__fe4_cr5,
    [P_dissolution__ni__fe3_cr6] = apply_actions_dissolution__ni__fe3_cr6,
    [P_dissolution__ni__fe2_cr7] = apply_actions_dissolution__ni__fe2_cr7,
    [P_dissolution__ni__fe1_cr8] = apply_actions_dissolution__ni__fe1_cr8,
    [P_dissolution__ni__cr9] = apply_actions_dissolution__ni__cr9,
    [P_dissolution__fe__ni3] = apply_actions_dissolution__fe__ni3,
    [P_dissolution__fe__ni2_fe1] = apply_actions_dissolution__fe__ni2_fe1,
    [P_dissolution__fe__ni2_cr1] = apply_actions_dissolution__fe__ni2_cr1,
    [P_dissolution__fe__ni1_fe2] = apply_actions_dissolution__fe__ni1_fe2,
    [P_dissolution__fe__ni1_fe1_cr1] = apply_actions_dissolution__fe__ni1_fe1_cr1,
    [P_dissolution__fe__ni1_cr2] = apply_actions_dissolution__fe__ni1_cr2,
    [P_dissolution__fe__fe3] = apply_actions_dissolution__fe__fe3,
    [P_dissolution__fe__fe2_cr1] = apply_actions_dissolution__fe__fe2_cr1,
    [P_dissolution__fe__fe1_cr2] = apply_actions_dissolution__fe__fe1_cr2,
    [P_dissolution__fe__cr3] = apply_actions_dissolution__fe__cr3,
    [P_dissolution__fe__ni4] = apply_actions_dissolution__fe__ni4,
    [P_dissolution__fe__ni3_fe1] = apply_actions_dissolution__fe__ni3_fe1,
    [P_dissolution__fe__ni3_cr1] = apply_actions_dissolution__fe__ni3_cr1,
    [P_dissolution__fe__ni2_fe2] = apply_actions_dissolution__fe__ni2_fe2,
    [P_dissolution__fe__ni2_fe1_cr1] = apply_actions_dissolution__fe__ni2_fe1_cr1,
    [P_dissolution__fe__ni2_cr2] = apply_actions_dissolution__fe__ni2_cr2,
    [P_dissolution__fe__ni1_fe3] = apply_actions_dissolution__fe__ni1_fe3,
    [P_dissolution__fe__ni1_fe2_cr1] = apply_actions_dissolution__fe__ni1_fe2_cr1,
    [P_dissolution__fe__ni1_fe1_cr2] = apply_actions_dissolution__fe__ni1_fe1_cr2,
    [P_dissolution__fe__ni1_cr3] = apply_actions_dissolution__fe__ni1_cr3,
    [P_dissolution__fe__fe4] = apply_actions_dissolution__fe__fe4,
    [P_dissolution__fe__fe3_cr1] = apply_actions_dissolution__fe__fe3_cr1,
    [P_dissolution__fe__fe2_cr2] = apply_actions_dissolution__fe__fe2_cr2,
    [P_dissolution__fe__fe1_cr3] = apply_actions_dissolution__fe__fe1_cr3,
    [P_dissolution__fe__cr4] = apply_actions_dissolution__fe__cr4,
    [P_dissolution__fe__ni5] = apply_actions_dissolution__fe__ni5,
    [P_dissolution__fe__ni4_fe1] = apply_actions_dissolution__fe__ni4_fe1,
    [P_dissolution__fe__ni4_cr1] = apply_actions_dissolution__fe__ni4_cr1,
    [P_dissolution__fe__ni3_fe2] = apply_actions_dissolution__fe__ni3_fe2,
    [P_dissolution__fe__ni3_fe1_cr1] = apply_actions_dissolution__fe__ni3_fe1_cr1,
    [P_dissolution__fe__ni3_cr2] = apply_actions_dissolution__fe__ni3_cr2,
    [P_dissolution__fe__ni2_fe3] = apply_actions_dissolution__fe__ni2_fe3,
    [P_dissolution__fe__ni2_fe2_cr1] = apply_actions_dissolution__fe__ni2_fe2_cr1,
    [P_dissolution__fe__ni2_fe1_cr2] = apply_actions_dissolution__fe__ni2_fe1_cr2,
    [P_dissolution__fe__ni2_cr3] = apply_actions_dissolution__fe__ni2_cr3,
    [P_dissolution__fe__ni1_fe4] = apply_actions_dissolution__fe__ni1_fe4,
    [P_dissolution__fe__ni1_fe3_cr1] = apply_actions_dissolution__fe__ni1_fe3_cr1,
    [P_dissolution__fe__ni1_fe2_cr2] = apply_actions_dissolution__fe__ni1_fe2_cr2,
    [P_dissolution__fe__ni1_fe1_cr3] = apply_actions_dissolution__fe__ni1_fe1_cr3,
    [P_dissolution__fe__ni1_cr4] = apply_actions_dissolution__fe__ni1_cr4,
    [P_dissolution__fe__fe5] = apply_actions_dissolution__fe__fe5,
    [P_dissolution__fe__fe4_cr1] = apply_actions_dissolution__fe__fe4_cr1,
    [P_dissolution__fe__fe3_cr2] = apply_actions_dissolution__fe__fe3_cr2,
    [P_dissolution__fe__fe2_cr3] = apply_actions_dissolution__fe__fe2_cr3,
    [P_dissolution__fe__fe1_cr4] = apply_actions_dissolution__fe__fe1_cr4,
    [P_dissolution__fe__cr5] = apply_actions_dissolution__fe__cr5,
    [P_dissolution__fe__ni6] = apply_actions_dissolution__fe__ni6,
    [P_dissolution__fe__ni5_fe1] = apply_actions_dissolution__fe__ni5_fe1,
    [P_dissolution__fe__ni5_cr1] = apply_actions_dissolution__fe__ni5_cr1,
    [P_dissolution__fe__ni4_fe2] = apply_actions_dissolution__fe__ni4_fe2,
    [P_dissolution__fe__ni4_fe1_cr1] = apply_actions_dissolution__fe__ni4_fe1_cr1,
    [P_dissolution__fe__ni4_cr2] = apply_actions_dissolution__fe__ni4_cr2,
    [P_dissolution__fe__ni3_fe3] = apply_actions_dissolution__fe__ni3_fe3,
    [P_dissolution__fe__ni3_fe2_cr1] = apply_actions_dissolution__fe__ni3_fe2_cr1,
    [P_dissolution__fe__ni3_fe1_cr2] = apply_actions_dissolution__fe__ni3_fe1_cr2,
    [P_dissolution__fe__ni3_cr3] = apply_actions_dissolution__fe__ni3_cr3,
    [P_dissolution__fe__ni2_fe4] = apply_actions_dissolution__fe__ni2_fe4,
    [P_dissolution__fe__ni2_fe3_cr1] = apply_actions_dissolution__fe__ni2_fe3_cr1,
    [P_dissolution__fe__ni2_fe2_cr2] = apply_actions_dissolution__fe__ni2_fe2_cr2,
    [P_dissolution__fe__ni2_fe1_cr3] = apply_actions_dissolution__fe__ni2_fe1_cr3,
    [P_dissolution__fe__ni2_cr4] = apply_actions_dissolution__fe__ni2_cr4,
    [P_dissolution__fe__ni1_fe5] = apply_actions_dissolution__fe__ni1_fe5,
    [P_dissolution__fe__ni1_fe4_cr1] = apply_actions_dissolution__fe__ni1_fe4_cr1,
    [P_dissolution__fe__ni1_fe3_cr2] = apply_actions_dissolution__fe__ni1_fe3_cr2,
    [P_dissolution__fe__ni1_fe2_cr3] = apply_actions_dissolution__fe__ni1_fe2_cr3,
    [P_dissolution__fe__ni1_fe1_cr4] = apply_actions_dissolution__fe__ni1_fe1_cr4,
    [P_dissolution__fe__ni1_cr5] = apply_actions_dissolution__fe__ni1_cr5,
    [P_dissolution__fe__fe6] = apply_actions_dissolution__fe__fe6,
    [P_dissolution__fe__fe5_cr1] = apply_actions_dissolution__fe__fe5_cr1,
    [P_dissolution__fe__fe4_cr2] = apply_actions_dissolution__fe__fe4_cr2,
    [P_dissolution__fe__fe3_cr3] = apply_actions_dissolution__fe__fe3_cr3,
    [P_dissolution__fe__fe2_cr4] = apply_actions_dissolution__fe__fe2_cr4,
    [P_dissolution__fe__fe1_cr5] = apply_actions_dissolution__fe__fe1_cr5,
    [P_dissolution__fe__cr6] = apply_actions_dissolution__fe__cr6,
    [P_dissolution__fe__ni7] = apply_actions_dissolution__fe__ni7,
    [P_dissolution__fe__ni6_fe1] = apply_actions_dissolution__fe__ni6_fe1,
    [P_dissolution__fe__ni6_cr1] = apply_actions_dissolution__fe__ni6_cr1,
    [P_dissolution__fe__ni5_fe2] = apply_actions_dissolution__fe__ni5_fe2,
    [P_dissolution__fe__ni5_fe1_cr1] = apply_actions_dissolution__fe__ni5_fe1_cr1,
    [P_dissolution__fe__ni5_cr2] = apply_actions_dissolution__fe__ni5_cr2,
    [P_dissolution__fe__ni4_fe3] = apply_actions_dissolution__fe__ni4_fe3,
    [P_dissolution__fe__ni4_fe2_cr1] = apply_actions_dissolution__fe__ni4_fe2_cr1,
    [P_dissolution__fe__ni4_fe1_cr2] = apply_actions_dissolution__fe__ni4_fe1_cr2,
    [P_dissolution__fe__ni4_cr3] = apply_actions_dissolution__fe__ni4_cr3,
    [P_dissolution__fe__ni3_fe4] = apply_actions_dissolution__fe__ni3_fe4,
    [P_dissolution__fe__ni3_fe3_cr1] = apply_actions_dissolution__fe__ni3_fe3_cr1,
    [P_dissolution__fe__ni3_fe2_cr2] = apply_actions_dissolution__fe__ni3_fe2_cr2,
    [P_dissolution__fe__ni3_fe1_cr3] = apply_actions_dissolution__fe__ni3_fe1_cr3,
    [P_dissolution__fe__ni3_cr4] = apply_actions_dissolution__fe__ni3_cr4,
    [P_dissolution__fe__ni2_fe5] = apply_actions_dissolution__fe__ni2_fe5,
    [P_dissolution__fe__ni2_fe4_cr1] = apply_actions_dissolution__fe__ni2_fe4_cr1,
    [P_dissolution__fe__ni2_fe3_cr2] = apply_actions_dissolution__fe__ni2_fe3_cr2,
    [P_dissolution__fe__ni2_fe2_cr3] = apply_actions_dissolution__fe__ni2_fe2_cr3,
    [P_dissolution__fe__ni2_fe1_cr4] = apply_actions_dissolution__fe__ni2_fe1_cr4,
    [P_dissolution__fe__ni2_cr5] = apply_actions_dissolution__fe__ni2_cr5,
    [P_dissolution__fe__ni1_fe6] = apply_actions_dissolution__fe__ni1_fe6,
    [P_dissolution__fe__ni1_fe5_cr1] = apply_actions_dissolution__fe__ni1_fe5_cr1,
    [P_dissolution__fe__ni1_fe4_cr2] = apply_actions_dissolution__fe__ni1_fe4_cr2,
    [P_dissolution__fe__ni1_fe3_cr3] = apply_actions_dissolution__fe__ni1_fe3_cr3,
    [P_dissolution__fe__ni1_fe2_cr4] = apply_actions_dissolution__fe__ni1_fe2_cr4,
    [P_dissolution__fe__ni1_fe1_cr5] = apply_actions_dissolution__fe__ni1_fe1_cr5,
    [P_dissolution__fe__ni1_cr6] = apply_actions_dissolution__fe__ni1_cr6,
    [P_dissolution__fe__fe7] = apply_actions_dissolution__fe__fe7,
    [P_dissolution__fe__fe6_cr1] = apply_actions_dissolution__fe__fe6_cr1,
    [P_dissolution__fe__fe5_cr2] = apply_actions_dissolution__fe__fe5_cr2,
    [P_dissolution__fe__fe4_cr3] = apply_actions_dissolution__fe__fe4_cr3,
    [P_dissolution__fe__fe3_cr4] = apply_actions_dissolution__fe__fe3_cr4,
    [P_dissolution__fe__fe2_cr5] = apply_actions_dissolution__fe__fe2_cr5,
    [P_dissolution__fe__fe1_cr6] = apply_actions_dissolution__fe__fe1_cr6,
    [P_dissolution__fe__cr7] = apply_actions_dissolution__fe__cr7,
    [P_dissolution__fe__ni8] = apply_actions_dissolution__fe__ni8,
    [P_dissolution__fe__ni7_fe1] = apply_actions_dissolution__fe__ni7_fe1,
    [P_dissolution__fe__ni7_cr1] = apply_actions_dissolution__fe__ni7_cr1,
    [P_dissolution__fe__ni6_fe2] = apply_actions_dissolution__fe__ni6_fe2,
    [P_dissolution__fe__ni6_fe1_cr1] = apply_actions_dissolution__fe__ni6_fe1_cr1,
    [P_dissolution__fe__ni6_cr2] = apply_actions_dissolution__fe__ni6_cr2,
    [P_dissolution__fe__ni5_fe3] = apply_actions_dissolution__fe__ni5_fe3,
    [P_dissolution__fe__ni5_fe2_cr1] = apply_actions_dissolution__fe__ni5_fe2_cr1,
    [P_dissolution__fe__ni5_fe1_cr2] = apply_actions_dissolution__fe__ni5_fe1_cr2,
    [P_dissolution__fe__ni5_cr3] = apply_actions_dissolution__fe__ni5_cr3,
    [P_dissolution__fe__ni4_fe4] = apply_actions_dissolution__fe__ni4_fe4,
    [P_dissolution__fe__ni4_fe3_cr1] = apply_actions_dissolution__fe__ni4_fe3_cr1,
    [P_dissolution__fe__ni4_fe2_cr2] = apply_actions_dissolution__fe__ni4_fe2_cr2,
    [P_dissolution__fe__ni4_fe1_cr3] = apply_actions_dissolution__fe__ni4_fe1_cr3,
    [P_dissolution__fe__ni4_cr4] = apply_actions_dissolution__fe__ni4_cr4,
    [P_dissolution__fe__ni3_fe5] = apply_actions_dissolution__fe__ni3_fe5,
    [P_dissolution__fe__ni3_fe4_cr1] = apply_actions_dissolution__fe__ni3_fe4_cr1,
    [P_dissolution__fe__ni3_fe3_cr2] = apply_actions_dissolution__fe__ni3_fe3_cr2,
    [P_dissolution__fe__ni3_fe2_cr3] = apply_actions_dissolution__fe__ni3_fe2_cr3,
    [P_dissolution__fe__ni3_fe1_cr4] = apply_actions_dissolution__fe__ni3_fe1_cr4,
    [P_dissolution__fe__ni3_cr5] = apply_actions_dissolution__fe__ni3_cr5,
    [P_dissolution__fe__ni2_fe6] = apply_actions_dissolution__fe__ni2_fe6,
    [P_dissolution__fe__ni2_fe5_cr1] = apply_actions_dissolution__fe__ni2_fe5_cr1,
    [P_dissolution__fe__ni2_fe4_cr2] = apply_actions_dissolution__fe__ni2_fe4_cr2,
    [P_dissolution__fe__ni2_fe3_cr3] = apply_actions_dissolution__fe__ni2_fe3_cr3,
    [P_dissolution__fe__ni2_fe2_cr4] = apply_actions_dissolution__fe__ni2_fe2_cr4,
    [P_dissolution__fe__ni2_fe1_cr5] = apply_actions_dissolution__fe__ni2_fe1_cr5,
    [P_dissolution__fe__ni2_cr6] = apply_actions_dissolution__fe__ni2_cr6,
    [P_dissolution__fe__ni1_fe7] = apply_actions_dissolution__fe__ni1_fe7,
    [P_dissolution__fe__ni1_fe6_cr1] = apply_actions_dissolution__fe__ni1_fe6_cr1,
    [P_dissolution__fe__ni1_fe5_cr2] = apply_actions_dissolution__fe__ni1_fe5_cr2,
    [P_dissolution__fe__ni1_fe4_cr3] = apply_actions_dissolution__fe__ni1_fe4_cr3,
    [P_dissolution__fe__ni1_fe3_cr4] = apply_actions_dissolution__fe__ni1_fe3_cr4,
    [P_dissolution__fe__ni1_fe2_cr5] = apply_actions_dissolution__fe__ni1_fe2_cr5,
    [P_dissolution__fe__ni1_fe1_cr6] = apply_actions_dissolution__fe__ni1_fe1_cr6,
    [P_dissolution__fe__ni1_cr7] = apply_actions_dissolution__fe__ni1_cr7,
    [P_dissolution__fe__fe8] = apply_actions_dissolution__fe__fe8,
    [P_dissolution__fe__fe7_cr1] = apply_actions_dissolution__fe__fe7_cr1,
    [P_dissolution__fe__fe6_cr2] = apply_actions_dissolution__fe__fe6_cr2,
    [P_dissolution__fe__fe5_cr3] = apply_actions_dissolution__fe__fe5_cr3,
    [P_dissolution__fe__fe4_cr4] = apply_actions_dissolution__fe__fe4_cr4,
    [P_dissolution__fe__fe3_cr5] = apply_actions_dissolution__fe__fe3_cr5,
    [P_dissolution__fe__fe2_cr6] = apply_actions_dissolution__fe__fe2_cr6,
    [P_dissolution__fe__fe1_cr7] = apply_actions_dissolution__fe__fe1_cr7,
    [P_dissolution__fe__cr8] = apply_actions_dissolution__fe__cr8,
    [P_dissolution__fe__ni9] = apply_actions_dissolution__fe__ni9,
    [P_dissolution__fe__ni8_fe1] = apply_actions_dissolution__fe__ni8_fe1,
    [P_dissolution__fe__ni8_cr1] = apply_actions_dissolution__fe__ni8_cr1,
    [P_dissolution__fe__ni7_fe2] = apply_actions_dissolution__fe__ni7_fe2,
    [P_dissolution__fe__ni7_fe1_cr1] = apply_actions_dissolution__fe__ni7_fe1_cr1,
    [P_dissolution__fe__ni7_cr2] = apply_actions_dissolution__fe__ni7_cr2,
    [P_dissolution__fe__ni6_fe3] = apply_actions_dissolution__fe__ni6_fe3,
    [P_dissolution__fe__ni6_fe2_cr1] = apply_actions_dissolution__fe__ni6_fe2_cr1,
    [P_dissolution__fe__ni6_fe1_cr2] = apply_actions_dissolution__fe__ni6_fe1_cr2,
    [P_dissolution__fe__ni6_cr3] = apply_actions_dissolution__fe__ni6_cr3,
    [P_dissolution__fe__ni5_fe4] = apply_actions_dissolution__fe__ni5_fe4,
    [P_dissolution__fe__ni5_fe3_cr1] = apply_actions_dissolution__fe__ni5_fe3_cr1,
    [P_dissolution__fe__ni5_fe2_cr2] = apply_actions_dissolution__fe__ni5_fe2_cr2,
    [P_dissolution__fe__ni5_fe1_cr3] = apply_actions_dissolution__fe__ni5_fe1_cr3,
    [P_dissolution__fe__ni5_cr4] = apply_actions_dissolution__fe__ni5_cr4,
    [P_dissolution__fe__ni4_fe5] = apply_actions_dissolution__fe__ni4_fe5,
    [P_dissolution__fe__ni4_fe4_cr1] = apply_actions_dissolution__fe__ni4_fe4_cr1,
    [P_dissolution__fe__ni4_fe3_cr2] = apply_actions_dissolution__fe__ni4_fe3_cr2,
    [P_dissolution__fe__ni4_fe2_cr3] = apply_actions_dissolution__fe__ni4_fe2_cr3,
    [P_dissolution__fe__ni4_fe1_cr4] = apply_actions_dissolution__fe__ni4_fe1_cr4,
    [P_dissolution__fe__ni4_cr5] = apply_actions_dissolution__fe__ni4_cr5,
    [P_dissolution__fe__ni3_fe6] = apply_actions_dissolution__fe__ni3_fe6,
    [P_dissolution__fe__ni3_fe5_cr1] = apply_actions_dissolution__fe__ni3_fe5_cr1,
    [P_dissolution__fe__ni3_fe4_cr2] = apply_actions_dissolution__fe__ni3_fe4_cr2,
    [P_dissolution__fe__ni3_fe3_cr3] = apply_actions_dissolution__fe__ni3_fe3_cr3,
    [P_dissolution__fe__ni3_fe2_cr4] = apply_actions_dissolution__fe__ni3_fe2_cr4,
    [P_dissolution__fe__ni3_fe1_cr5] = apply_actions_dissolution__fe__ni3_fe1_cr5,
    [P_dissolution__fe__ni3_cr6] = apply_actions_dissolution__fe__ni3_cr6,
    [P_dissolution__fe__ni2_fe7] = apply_actions_dissolution__fe__ni2_fe7,
    [P_dissolution__fe__ni2_fe6_cr1] = apply_actions_dissolution__fe__ni2_fe6_cr1,
    [P_dissolution__fe__ni2_fe5_cr2] = apply_actions_dissolution__fe__ni2_fe5_cr2,
    [P_dissolution__fe__ni2_fe4_cr3] = apply_actions_dissolution__fe__ni2_fe4_cr3,
    [P_dissolution__fe__ni2_fe3_cr4] = apply_actions_dissolution__fe__ni2_fe3_cr4,
    [P_dissolution__fe__ni2_fe2_cr5] = apply_actions_dissolution__fe__ni2_fe2_cr5,
    [P_dissolution__fe__ni2_fe1_cr6] = apply_actions_dissolution__fe__ni2_fe1_cr6,
    [P_dissolution__fe__ni2_cr7] = apply_actions_dissolution__fe__ni2_cr7,
    [P_dissolution__fe__ni1_fe8] = apply_actions_dissolution__fe__ni1_fe8,
    [P_dissolution__fe__ni1_fe7_cr1] = apply_actions_dissolution__fe__ni1_fe7_cr1,
    [P_dissolution__fe__ni1_fe6_cr2] = apply_actions_dissolution__fe__ni1_fe6_cr2,
    [P_dissolution__fe__ni1_fe5_cr3] = apply_actions_dissolution__fe__ni1_fe5_cr3,
    [P_dissolution__fe__ni1_fe4_cr4] = apply_actions_dissolution__fe__ni1_fe4_cr4,
    [P_dissolution__fe__ni1_fe3_cr5] = apply_actions_dissolution__fe__ni1_fe3_cr5,
    [P_dissolution__fe__ni1_fe2_cr6] = apply_actions_dissolution__fe__ni1_fe2_cr6,
    [P_dissolution__fe__ni1_fe1_cr7] = apply_actions_dissolution__fe__ni1_fe1_cr7,
    [P_dissolution__fe__ni1_cr8] = apply_actions_dissolution__fe__ni1_cr8,
    [P_dissolution__fe__fe9] = apply_actions_dissolution__fe__fe9,
    [P_dissolution__fe__fe8_cr1] = apply_actions_dissolution__fe__fe8_cr1,
    [P_dissolution__fe__fe7_cr2] = apply_actions_dissolution__fe__fe7_cr2,
    [P_dissolution__fe__fe6_cr3] = apply_actions_dissolution__fe__fe6_cr3,
    [P_dissolution__fe__fe5_cr4] = apply_actions_dissolution__fe__fe5_cr4,
    [P_dissolution__fe__fe4_cr5] = apply_actions_dissolution__fe__fe4_cr5,
    [P_dissolution__fe__fe3_cr6] = apply_actions_dissolution__fe__fe3_cr6,
    [P_dissolution__fe__fe2_cr7] = apply_actions_dissolution__fe__fe2_cr7,
    [P_dissolution__fe__fe1_cr8] = apply_actions_dissolution__fe__fe1_cr8,
    [P_dissolution__fe__cr9] = apply_actions_dissolution__fe__cr9,
    [P_dissolution__cr__ni3] = apply_actions_dissolution__cr__ni3,
    [P_dissolution__cr__ni2_fe1] = apply_actions_dissolution__cr__ni2_fe1,
    [P_dissolution__cr__ni2_cr1] = apply_actions_dissolution__cr__ni2_cr1,
    [P_dissolution__cr__ni1_fe2] = apply_actions_dissolution__cr__ni1_fe2,
    [P_dissolution__cr__ni1_fe1_cr1] = apply_actions_dissolution__cr__ni1_fe1_cr1,
    [P_dissolution__cr__ni1_cr2] = apply_actions_dissolution__cr__ni1_cr2,
    [P_dissolution__cr__fe3] = apply_actions_dissolution__cr__fe3,
    [P_dissolution__cr__fe2_cr1] = apply_actions_dissolution__cr__fe2_cr1,
    [P_dissolution__cr__fe1_cr2] = apply_actions_dissolution__cr__fe1_cr2,
    [P_dissolution__cr__cr3] = apply_actions_dissolution__cr__cr3,
    [P_dissolution__cr__ni4] = apply_actions_dissolution__cr__ni4,
    [P_dissolution__cr__ni3_fe1] = apply_actions_dissolution__cr__ni3_fe1,
    [P_dissolution__cr__ni3_cr1] = apply_actions_dissolution__cr__ni3_cr1,
    [P_dissolution__cr__ni2_fe2] = apply_actions_dissolution__cr__ni2_fe2,
    [P_dissolution__cr__ni2_fe1_cr1] = apply_actions_dissolution__cr__ni2_fe1_cr1,
    [P_dissolution__cr__ni2_cr2] = apply_actions_dissolution__cr__ni2_cr2,
    [P_dissolution__cr__ni1_fe3] = apply_actions_dissolution__cr__ni1_fe3,
    [P_dissolution__cr__ni1_fe2_cr1] = apply_actions_dissolution__cr__ni1_fe2_cr1,
    [P_dissolution__cr__ni1_fe1_cr2] = apply_actions_dissolution__cr__ni1_fe1_cr2,
    [P_dissolution__cr__ni1_cr3] = apply_actions_dissolution__cr__ni1_cr3,
    [P_dissolution__cr__fe4] = apply_actions_dissolution__cr__fe4,
    [P_dissolution__cr__fe3_cr1] = apply_actions_dissolution__cr__fe3_cr1,
    [P_dissolution__cr__fe2_cr2] = apply_actions_dissolution__cr__fe2_cr2,
    [P_dissolution__cr__fe1_cr3] = apply_actions_dissolution__cr__fe1_cr3,
    [P_dissolution__cr__cr4] = apply_actions_dissolution__cr__cr4,
    [P_dissolution__cr__ni5] = apply_actions_dissolution__cr__ni5,
    [P_dissolution__cr__ni4_fe1] = apply_actions_dissolution__cr__ni4_fe1,
    [P_dissolution__cr__ni4_cr1] = apply_actions_dissolution__cr__ni4_cr1,
    [P_dissolution__cr__ni3_fe2] = apply_actions_dissolution__cr__ni3_fe2,
    [P_dissolution__cr__ni3_fe1_cr1] = apply_actions_dissolution__cr__ni3_fe1_cr1,
    [P_dissolution__cr__ni3_cr2] = apply_actions_dissolution__cr__ni3_cr2,
    [P_dissolution__cr__ni2_fe3] = apply_actions_dissolution__cr__ni2_fe3,
    [P_dissolution__cr__ni2_fe2_cr1] = apply_actions_dissolution__cr__ni2_fe2_cr1,
    [P_dissolution__cr__ni2_fe1_cr2] = apply_actions_dissolution__cr__ni2_fe1_cr2,
    [P_dissolution__cr__ni2_cr3] = apply_actions_dissolution__cr__ni2_cr3,
    [P_dissolution__cr__ni1_fe4] = apply_actions_dissolution__cr__ni1_fe4,
    [P_dissolution__cr__ni1_fe3_cr1] = apply_actions_dissolution__cr__ni1_fe3_cr1,
    [P_dissolution__cr__ni1_fe2_cr2] = apply_actions_dissolution__cr__ni1_fe2_cr2,
    [P_dissolution__cr__ni1_fe1_cr3] = apply_actions_dissolution__cr__ni1_fe1_cr3,
    [P_dissolution__cr__ni1_cr4] = apply_actions_dissolution__cr__ni1_cr4,
    [P_dissolution__cr__fe5] = apply_actions_dissolution__cr__fe5,
    [P_dissolution__cr__fe4_cr1] = apply_actions_dissolution__cr__fe4_cr1,
    [P_dissolution__cr__fe3_cr2] = apply_actions_dissolution__cr__fe3_cr2,
    [P_dissolution__cr__fe2_cr3] = apply_actions_dissolution__cr__fe2_cr3,
    [P_dissolution__cr__fe1_cr4] = apply_actions_dissolution__cr__fe1_cr4,
    [P_dissolution__cr__cr5] = apply_actions_dissolution__cr__cr5,
    [P_dissolution__cr__ni6] = apply_actions_dissolution__cr__ni6,
    [P_dissolution__cr__ni5_fe1] = apply_actions_dissolution__cr__ni5_fe1,
    [P_dissolution__cr__ni5_cr1] = apply_actions_dissolution__cr__ni5_cr1,
    [P_dissolution__cr__ni4_fe2] = apply_actions_dissolution__cr__ni4_fe2,
    [P_dissolution__cr__ni4_fe1_cr1] = apply_actions_dissolution__cr__ni4_fe1_cr1,
    [P_dissolution__cr__ni4_cr2] = apply_actions_dissolution__cr__ni4_cr2,
    [P_dissolution__cr__ni3_fe3] = apply_actions_dissolution__cr__ni3_fe3,
    [P_dissolution__cr__ni3_fe2_cr1] = apply_actions_dissolution__cr__ni3_fe2_cr1,
    [P_dissolution__cr__ni3_fe1_cr2] = apply_actions_dissolution__cr__ni3_fe1_cr2,
    [P_dissolution__cr__ni3_cr3] = apply_actions_dissolution__cr__ni3_cr3,
    [P_dissolution__cr__ni2_fe4] = apply_actions_dissolution__cr__ni2_fe4,
    [P_dissolution__cr__ni2_fe3_cr1] = apply_actions_dissolution__cr__ni2_fe3_cr1,
    [P_dissolution__cr__ni2_fe2_cr2] = apply_actions_dissolution__cr__ni2_fe2_cr2,
    [P_dissolution__cr__ni2_fe1_cr3] = apply_actions_dissolution__cr__ni2_fe1_cr3,
    [P_dissolution__cr__ni2_cr4] = apply_actions_dissolution__cr__ni2_cr4,
    [P_dissolution__cr__ni1_fe5] = apply_actions_dissolution__cr__ni1_fe5,
    [P_dissolution__cr__ni1_fe4_cr1] = apply_actions_dissolution__cr__ni1_fe4_cr1,
    [P_dissolution__cr__ni1_fe3_cr2] = apply_actions_dissolution__cr__ni1_fe3_cr2,
    [P_dissolution__cr__ni1_fe2_cr3] = apply_actions_dissolution__cr__ni1_fe2_cr3,
    [P_dissolution__cr__ni1_fe1_cr4] = apply_actions_dissolution__cr__ni1_fe1_cr4,
    [P_dissolution__cr__ni1_cr5] = apply_actions_dissolution__cr__ni1_cr5,
    [P_dissolution__cr__fe6] = apply_actions_dissolution__cr__fe6,
    [P_dissolution__cr__fe5_cr1] = apply_actions_dissolution__cr__fe5_cr1,
    [P_dissolution__cr__fe4_cr2] = apply_actions_dissolution__cr__fe4_cr2,
    [P_dissolution__cr__fe3_cr3] = apply_actions_dissolution__cr__fe3_cr3,
    [P_dissolution__cr__fe2_cr4] = apply_actions_dissolution__cr__fe2_cr4,
    [P_dissolution__cr__fe1_cr5] = apply_actions_dissolution__cr__fe1_cr5,
    [P_dissolution__cr__cr6] = apply_actions_dissolution__cr__cr6,
    [P_dissolution__cr__ni7] = apply_actions_dissolution__cr__ni7,
    [P_dissolution__cr__ni6_fe1] = apply_actions_dissolution__cr__ni6_fe1,
    [P_dissolution__cr__ni6_cr1] = apply_actions_dissolution__cr__ni6_cr1,
    [P_dissolution__cr__ni5_fe2] = apply_actions_dissolution__cr__ni5_fe2,
    [P_dissolution__cr__ni5_fe1_cr1] = apply_actions_dissolution__cr__ni5_fe1_cr1,
    [P_dissolution__cr__ni5_cr2] = apply_actions_dissolution__cr__ni5_cr2,
    [P_dissolution__cr__ni4_fe3] = apply_actions_dissolution__cr__ni4_fe3,
    [P_dissolution__cr__ni4_fe2_cr1] = apply_actions_dissolution__cr__ni4_fe2_cr1,
    [P_dissolution__cr__ni4_fe1_cr2] = apply_actions_dissolution__cr__ni4_fe1_cr2,
    [P_dissolution__cr__ni4_cr3] = apply_actions_dissolution__cr__ni4_cr3,
    [P_dissolution__cr__ni3_fe4] = apply_actions_dissolution__cr__ni3_fe4,
    [P_dissolution__cr__ni3_fe3_cr1] = apply_actions_dissolution__cr__ni3_fe3_cr1,
    [P_dissolution__cr__ni3_fe2_cr2] = apply_actions_dissolution__cr__ni3_fe2_cr2,
    [P_dissolution__cr__ni3_fe1_cr3] = apply_actions_dissolution__cr__ni3_fe1_cr3,
    [P_dissolution__cr__ni3_cr4] = apply_actions_dissolution__cr__ni3_cr4,
    [P_dissolution__cr__ni2_fe5] = apply_actions_dissolution__cr__ni2_fe5,
    [P_dissolution__cr__ni2_fe4_cr1] = apply_actions_dissolution__cr__ni2_fe4_cr1,
    [P_dissolution__cr__ni2_fe3_cr2] = apply_actions_dissolution__cr__ni2_fe3_cr2,
    [P_dissolution__cr__ni2_fe2_cr3] = apply_actions_dissolution__cr__ni2_fe2_cr3,
    [P_dissolution__cr__ni2_fe1_cr4] = apply_actions_dissolution__cr__ni2_fe1_cr4,
    [P_dissolution__cr__ni2_cr5] = apply_actions_dissolution__cr__ni2_cr5,
    [P_dissolution__cr__ni1_fe6] = apply_actions_dissolution__cr__ni1_fe6,
    [P_dissolution__cr__ni1_fe5_cr1] = apply_actions_dissolution__cr__ni1_fe5_cr1,
    [P_dissolution__cr__ni1_fe4_cr2] = apply_actions_dissolution__cr__ni1_fe4_cr2,
    [P_dissolution__cr__ni1_fe3_cr3] = apply_actions_dissolution__cr__ni1_fe3_cr3,
    [P_dissolution__cr__ni1_fe2_cr4] = apply_actions_dissolution__cr__ni1_fe2_cr4,
    [P_dissolution__cr__ni1_fe1_cr5] = apply_actions_dissolution__cr__ni1_fe1_cr5,
    [P_dissolution__cr__ni1_cr6] = apply_actions_dissolution__cr__ni1_cr6,
    [P_dissolution__cr__fe7] = apply_actions_dissolution__cr__fe7,
    [P_dissolution__cr__fe6_cr1] = apply_actions_dissolution__cr__fe6_cr1,
    [P_dissolution__cr__fe5_cr2] = apply_actions_dissolution__cr__fe5_cr2,
    [P_dissolution__cr__fe4_cr3] = apply_actions_dissolution__cr__fe4_cr3,
    [P_dissolution__cr__fe3_cr4] = apply_actions_dissolution__cr__fe3_cr4,
    [P_dissolution__cr__fe2_cr5] = apply_actions_dissolution__cr__fe2_cr5,
    [P_dissolution__cr__fe1_cr6] = apply_actions_dissolution__cr__fe1_cr6,
    [P_dissolution__cr__cr7] = apply_actions_dissolution__cr__cr7,
    [P_dissolution__cr__ni8] = apply_actions_dissolution__cr__ni8,
    [P_dissolution__cr__ni7_fe1] = apply_actions_dissolution__cr__ni7_fe1,
    [P_dissolution__cr__ni7_cr1] = apply_actions_dissolution__cr__ni7_cr1,
    [P_dissolution__cr__ni6_fe2] = apply_actions_dissolution__cr__ni6_fe2,
    [P_dissolution__cr__ni6_fe1_cr1] = apply_actions_dissolution__cr__ni6_fe1_cr1,
    [P_dissolution__cr__ni6_cr2] = apply_actions_dissolution__cr__ni6_cr2,
    [P_dissolution__cr__ni5_fe3] = apply_actions_dissolution__cr__ni5_fe3,
    [P_dissolution__cr__ni5_fe2_cr1] = apply_actions_dissolution__cr__ni5_fe2_cr1,
    [P_dissolution__cr__ni5_fe1_cr2] = apply_actions_dissolution__cr__ni5_fe1_cr2,
    [P_dissolution__cr__ni5_cr3] = apply_actions_dissolution__cr__ni5_cr3,
    [P_dissolution__cr__ni4_fe4] = apply_actions_dissolution__cr__ni4_fe4,
    [P_dissolution__cr__ni4_fe3_cr1] = apply_actions_dissolution__cr__ni4_fe3_cr1,
    [P_dissolution__cr__ni4_fe2_cr2] = apply_actions_dissolution__cr__ni4_fe2_cr2,
    [P_dissolution__cr__ni4_fe1_cr3] = apply_actions_dissolution__cr__ni4_fe1_cr3,
    [P_dissolution__cr__ni4_cr4] = apply_actions_dissolution__cr__ni4_cr4,
    [P_dissolution__cr__ni3_fe5] = apply_actions_dissolution__cr__ni3_fe5,
    [P_dissolution__cr__ni3_fe4_cr1] = apply_actions_dissolution__cr__ni3_fe4_cr1,
    [P_dissolution__cr__ni3_fe3_cr2] = apply_actions_dissolution__cr__ni3_fe3_cr2,
    [P_dissolution__cr__ni3_fe2_cr3] = apply_actions_dissolution__cr__ni3_fe2_cr3,
    [P_dissolution__cr__ni3_fe1_cr4] = apply_actions_dissolution__cr__ni3_fe1_cr4,
    [P_dissolution__cr__ni3_cr5] = apply_actions_dissolution__cr__ni3_cr5,
    [P_dissolution__cr__ni2_fe6] = apply_actions_dissolution__cr__ni2_fe6,
    [P_dissolution__cr__ni2_fe5_cr1] = apply_actions_dissolution__cr__ni2_fe5_cr1,
    [P_dissolution__cr__ni2_fe4_cr2] = apply_actions_dissolution__cr__ni2_fe4_cr2,
    [P_dissolution__cr__ni2_fe3_cr3] = apply_actions_dissolution__cr__ni2_fe3_cr3,
    [P_dissolution__cr__ni2_fe2_cr4] = apply_actions_dissolution__cr__ni2_fe2_cr4,
    [P_dissolution__cr__ni2_fe1_cr5] = apply_actions_dissolution__cr__ni2_fe1_cr5,
    [P_dissolution__cr__ni2_cr6] = apply_actions_dissolution__cr__ni2_cr6,
    [P_dissolution__cr__ni1_fe7] = apply_actions_dissolution__cr__ni1_fe7,
    [P_dissolution__cr__ni1_fe6_cr1] = apply_actions_dissolution__cr__ni1_fe6_cr1,
    [P_dissolution__cr__ni1_fe5_cr2] = apply_actions_dissolution__cr__ni1_fe5_cr2,
    [P_dissolution__cr__ni1_fe4_cr3] = apply_actions_dissolution__cr__ni1_fe4_cr3,
    [P_dissolution__cr__ni1_fe3_cr4] = apply_actions_dissolution__cr__ni1_fe3_cr4,
    [P_dissolution__cr__ni1_fe2_cr5] = apply_actions_dissolution__cr__ni1_fe2_cr5,
    [P_dissolution__cr__ni1_fe1_cr6] = apply_actions_dissolution__cr__ni1_fe1_cr6,
    [P_dissolution__cr__ni1_cr7] = apply_actions_dissolution__cr__ni1_cr7,
    [P_dissolution__cr__fe8] = apply_actions_dissolution__cr__fe8,
    [P_dissolution__cr__fe7_cr1] = apply_actions_dissolution__cr__fe7_cr1,
    [P_dissolution__cr__fe6_cr2] = apply_actions_dissolution__cr__fe6_cr2,
    [P_dissolution__cr__fe5_cr3] = apply_actions_dissolution__cr__fe5_cr3,
    [P_dissolution__cr__fe4_cr4] = apply_actions_dissolution__cr__fe4_cr4,
    [P_dissolution__cr__fe3_cr5] = apply_actions_dissolution__cr__fe3_cr5,
    [P_dissolution__cr__fe2_cr6] = apply_actions_dissolution__cr__fe2_cr6,
    [P_dissolution__cr__fe1_cr7] = apply_actions_dissolution__cr__fe1_cr7,
    [P_dissolution__cr__cr8] = apply_actions_dissolution__cr__cr8,
    [P_dissolution__cr__ni9] = apply_actions_dissolution__cr__ni9,
    [P_dissolution__cr__ni8_fe1] = apply_actions_dissolution__cr__ni8_fe1,
    [P_dissolution__cr__ni8_cr1] = apply_actions_dissolution__cr__ni8_cr1,
    [P_dissolution__cr__ni7_fe2] = apply_actions_dissolution__cr__ni7_fe2,
    [P_dissolution__cr__ni7_fe1_cr1] = apply_actions_dissolution__cr__ni7_fe1_cr1,
    [P_dissolution__cr__ni7_cr2] = apply_actions_dissolution__cr__ni7_cr2,
    [P_dissolution__cr__ni6_fe3] = apply_actions_dissolution__cr__ni6_fe3,
    [P_dissolution__cr__ni6_fe2_cr1] = apply_actions_dissolution__cr__ni6_fe2_cr1,
    [P_dissolution__cr__ni6_fe1_cr2] = apply_actions_dissolution__cr__ni6_fe1_cr2,
    [P_dissolution__cr__ni6_cr3] = apply_actions_dissolution__cr__ni6_cr3,
    [P_dissolution__cr__ni5_fe4] = apply_actions_dissolution__cr__ni5_fe4,
    [P_dissolution__cr__ni5_fe3_cr1] = apply_actions_dissolution__cr__ni5_fe3_cr1,
    [P_dissolution__cr__ni5_fe2_cr2] = apply_actions_dissolution__cr__ni5_fe2_cr2,
    [P_dissolution__cr__ni5_fe1_cr3] = apply_actions_dissolution__cr__ni5_fe1_cr3,
    [P_dissolution__cr__ni5_cr4] = apply_actions_dissolution__cr__ni5_cr4,
    [P_dissolution__cr__ni4_fe5] = apply_actions_dissolution__cr__ni4_fe5,
    [P_dissolution__cr__ni4_fe4_cr1] = apply_actions_dissolution__cr__ni4_fe4_cr1,
    [P_dissolution__cr__ni4_fe3_cr2] = apply_actions_dissolution__cr__ni4_fe3_cr2,
    [P_dissolution__cr__ni4_fe2_cr3] = apply_actions_dissolution__cr__ni4_fe2_cr3,
    [P_dissolution__cr__ni4_fe1_cr4] = apply_actions_dissolution__cr__ni4_fe1_cr4,
    [P_dissolution__cr__ni4_cr5] = apply_actions_dissolution__cr__ni4_cr5,
    [P_dissolution__cr__ni3_fe6] = apply_actions_dissolution__cr__ni3_fe6,
    [P_dissolution__cr__ni3_fe5_cr1] = apply_actions_dissolution__cr__ni3_fe5_cr1,
    [P_dissolution__cr__ni3_fe4_cr2] = apply_actions_dissolution__cr__ni3_fe4_cr2,
    [P_dissolution__cr__ni3_fe3_cr3] = apply_actions_dissolution__cr__ni3_fe3_cr3,
    [P_dissolution__cr__ni3_fe2_cr4] = apply_actions_dissolution__cr__ni3_fe2_cr4,
    [P_dissolution__cr__ni3_fe1_cr5] = apply_actions_dissolution__cr__ni3_fe1_cr5,
    [P_dissolution__cr__ni3_cr6] = apply_actions_dissolution__cr__ni3_cr6,
    [P_dissolution__cr__ni2_fe7] = apply_actions_dissolution__cr__ni2_fe7,
    [P_dissolution__cr__ni2_fe6_cr1] = apply_actions_dissolution__cr__ni2_fe6_cr1,
    [P_dissolution__cr__ni2_fe5_cr2] = apply_actions_dissolution__cr__ni2_fe5_cr2,
    [P_dissolution__cr__ni2_fe4_cr3] = apply_actions_dissolution__cr__ni2_fe4_cr3,
    [P_dissolution__cr__ni2_fe3_cr4] = apply_actions_dissolution__cr__ni2_fe3_cr4,
    [P_dissolution__cr__ni2_fe2_cr5] = apply_actions_dissolution__cr__ni2_fe2_cr5,
    [P_dissolution__cr__ni2_fe1_cr6] = apply_actions_dissolution__cr__ni2_fe1_cr6,
    [P_dissolution__cr__ni2_cr7] = apply_actions_dissolution__cr__ni2_cr7,
    [P_dissolution__cr__ni1_fe8] = apply_actions_dissolution__cr__ni1_fe8,
    [P_dissolution__cr__ni1_fe7_cr1] = apply_actions_dissolution__cr__ni1_fe7_cr1,
    [P_dissolution__cr__ni1_fe6_cr2] = apply_actions_dissolution__cr__ni1_fe6_cr2,
    [P_dissolution__cr__ni1_fe5_cr3] = apply_actions_dissolution__cr__ni1_fe5_cr3,
    [P_dissolution__cr__ni1_fe4_cr4] = apply_actions_dissolution__cr__ni1_fe4_cr4,
    [P_dissolution__cr__ni1_fe3_cr5] = apply_actions_dissolution__cr__ni1_fe3_cr5,
    [P_dissolution__cr__ni1_fe2_cr6] = apply_actions_dissolution__cr__ni1_fe2_cr6,
    [P_dissolution__cr__ni1_fe1_cr7] = apply_actions_dissolution__cr__ni1_fe1_cr7,
    [P_dissolution__cr__ni1_cr8] = apply_actions_dissolution__cr__ni1_cr8,
    [P_dissolution__cr__fe9] = apply_actions_dissolution__cr__fe9,
    [P_dissolution__cr__fe8_cr1] = apply_actions_dissolution__cr__fe8_cr1,
    [P_dissolution__cr__fe7_cr2] = apply_actions_dissolution__cr__fe7_cr2,
    [P_dissolution__cr__fe6_cr3] = apply_actions_dissolution__cr__fe6_cr3,
    [P_dissolution__cr__fe5_cr4] = apply_actions_dissolution__cr__fe5_cr4,
    [P_dissolution__cr__fe4_cr5] = apply_actions_dissolution__cr__fe4_cr5,
    [P_dissolution__cr__fe3_cr6] = apply_actions_dissolution__cr__fe3_cr6,
    [P_dissolution__cr__fe2_cr7] = apply_actions_dissolution__cr__fe2_cr7,
    [P_dissolution__cr__fe1_cr8] = apply_actions_dissolution__cr__fe1_cr8,
    [P_dissolution__cr__cr9] = apply_actions_dissolution__cr__cr9,
};

void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {
    switch (st->species[site]) {
        case SP_CR:
            {
                /* shell-count loops for bucket-key gating */
                int nr_1nn_cr_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_cr_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_CR) nr_1nn_cr_at_anchor++;
                        }
                    }
                }
                int nr_1nn_fe_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_fe_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_FE) nr_1nn_fe_at_anchor++;
                        }
                    }
                }
                int nr_1nn_ni_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_ni_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_NI) nr_1nn_ni_at_anchor++;
                        }
                    }
                }
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr8, site);
                if (nr_1nn_cr_at_anchor == 9 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__cr9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 9 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__cr__fe9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__cr__ni1_fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__cr__ni2_fe7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__cr__ni3_fe6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__cr__ni4_fe5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__cr__ni5_fe4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__cr__ni6_fe3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__cr__ni7_fe2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__cr__ni8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__cr__ni8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__cr__ni8_fe1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 9) avail_sites_add(as, P_dissolution__cr__ni9, site);
            }
            break;
        case SP_FE:
            {
                /* shell-count loops for bucket-key gating */
                int nr_1nn_cr_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_cr_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_CR) nr_1nn_cr_at_anchor++;
                        }
                    }
                }
                int nr_1nn_fe_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_fe_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_FE) nr_1nn_fe_at_anchor++;
                        }
                    }
                }
                int nr_1nn_ni_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_ni_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_NI) nr_1nn_ni_at_anchor++;
                        }
                    }
                }
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr8, site);
                if (nr_1nn_cr_at_anchor == 9 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__cr9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 9 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__fe__fe9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__fe__ni1_fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__fe__ni2_fe7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__fe__ni3_fe6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__fe__ni4_fe5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__fe__ni5_fe4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__fe__ni6_fe3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__fe__ni7_fe2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__fe__ni8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__fe__ni8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__fe__ni8_fe1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 9) avail_sites_add(as, P_dissolution__fe__ni9, site);
            }
            break;
        case SP_NI:
            {
                /* shell-count loops for bucket-key gating */
                int nr_1nn_cr_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_cr_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_CR) nr_1nn_cr_at_anchor++;
                        }
                    }
                }
                int nr_1nn_fe_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_fe_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_FE) nr_1nn_fe_at_anchor++;
                        }
                    }
                }
                int nr_1nn_ni_at_anchor = -1;  /* sentinel: stub-site mover → no match */
                {
                    int _m = site;
                    if (_m >= 0 && _m < lat->n_sites) {
                        nr_1nn_ni_at_anchor = 0;
                        for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                            if (st->species[lat->nn1_indices[_i]] == SP_NI) nr_1nn_ni_at_anchor++;
                        }
                    }
                }
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr8, site);
                if (nr_1nn_cr_at_anchor == 9 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__cr9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 9 && nr_1nn_ni_at_anchor == 0) avail_sites_add(as, P_dissolution__ni__fe9, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr7, site);
                if (nr_1nn_cr_at_anchor == 8 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_cr8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe1_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe2_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe3_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe4_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe5_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe6_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe7_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 8 && nr_1nn_ni_at_anchor == 1) avail_sites_add(as, P_dissolution__ni__ni1_fe8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr6, site);
                if (nr_1nn_cr_at_anchor == 7 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_cr7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe1_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe2_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe3_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe4_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe5_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe6_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 7 && nr_1nn_ni_at_anchor == 2) avail_sites_add(as, P_dissolution__ni__ni2_fe7, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr5, site);
                if (nr_1nn_cr_at_anchor == 6 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_cr6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe1_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe2_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe3_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe4_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe5_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 6 && nr_1nn_ni_at_anchor == 3) avail_sites_add(as, P_dissolution__ni__ni3_fe6, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_cr4, site);
                if (nr_1nn_cr_at_anchor == 5 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_cr5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe1_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe2_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe3_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe4, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe4_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 5 && nr_1nn_ni_at_anchor == 4) avail_sites_add(as, P_dissolution__ni__ni4_fe5, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_cr3, site);
                if (nr_1nn_cr_at_anchor == 4 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_cr4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe1_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe2_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe3, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe3_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 4 && nr_1nn_ni_at_anchor == 5) avail_sites_add(as, P_dissolution__ni__ni5_fe4, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_cr2, site);
                if (nr_1nn_cr_at_anchor == 3 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_cr3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe1_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe2, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe2_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 3 && nr_1nn_ni_at_anchor == 6) avail_sites_add(as, P_dissolution__ni__ni6_fe3, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7_cr1, site);
                if (nr_1nn_cr_at_anchor == 2 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7_cr2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7_fe1, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7_fe1_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 2 && nr_1nn_ni_at_anchor == 7) avail_sites_add(as, P_dissolution__ni__ni7_fe2, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__ni__ni8, site);
                if (nr_1nn_cr_at_anchor == 1 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__ni__ni8_cr1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 1 && nr_1nn_ni_at_anchor == 8) avail_sites_add(as, P_dissolution__ni__ni8_fe1, site);
                if (nr_1nn_cr_at_anchor == 0 && nr_1nn_fe_at_anchor == 0 && nr_1nn_ni_at_anchor == 9) avail_sites_add(as, P_dissolution__ni__ni9, site);
            }
            break;
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
