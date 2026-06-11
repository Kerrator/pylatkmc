/* proclist.h — GENERATED from ni_example.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build ni_example.kmcspec.toml`.
 *
 * Public interface: just enough symbols for the runtime backbone
 * (kmc.c, replica.c, main.c) to call into proclist.c. Internal
 * symbols (apply_actions_<name>, the decision-tree helpers) stay
 * `static` inside proclist.c.
 *
 * The N_PROCS macro and the rate_table sizing are exposed so the
 * runtime can configure avail_sites at startup.
 */
#ifndef PYLATKMC_PROCLIST_H
#define PYLATKMC_PROCLIST_H

#include <stdint.h>
#include <math.h>

#include "lattice.h"
#include "state.h"
#include "avail_sites.h"

/* Boltzmann constant in eV/K. GENERATED from
 * pylatkmc.rate_expression.KB_EV_PER_K — the single source of truth shared
 * by the Python codegen and this C runtime, so the two cannot drift. */
#define PYLATKMC_KB_EV_PER_K 8.6173330000e-05

/* Number of Processes in this model. Defined by the generated enum
 * in proclist.c; exposed here as a const for sizeof / loop bounds. */
extern const int32_t pylatkmc_n_procs;

/* Rate table: per-Process Arrhenius **prefactor** (Hz = s^-1) + activation
 * energy (eV). The rate k = prefactor_Hz * exp(-Ea_eV / (kB * T)) is computed
 * by the runtime at startup from the *runtime* temperature
 * (physics.temperature_K in input.ini) via rateconst_eval() below — NOT baked
 * at codegen time. One compiled binary therefore runs at any temperature.
 *
 * Declared as a pointer (not an array) so the storage in proclist.c can
 * be a `const RateConst *const` alias to a file-static array.
 *
 * NOTE: this typedef MUST stay layout-identical to the copy emitted by
 * pylatkmc.decision_tree.emit_rate_table into proclist.c (which does not
 * include this header). */
typedef struct { double prefactor_Hz; double Ea_eV; } RateConst;
extern const RateConst *const pylatkmc_rate_table;

/* Evaluate one Process's Arrhenius rate (Hz) at temperature T_K (Kelvin).
 * This is the single place the runtime un-bakes a rate from a prefactor. */
static inline double rateconst_eval(RateConst rc, double T_K) {
    return rc.prefactor_Hz * exp(-rc.Ea_eV / (PYLATKMC_KB_EV_PER_K * T_K));
}

/* HopOutcome: returned by every apply function. The runtime uses
 * v_origin / v_dest to update unwrapped_xyz for MSD tracking on simple
 * hops; multi-vacancy concerted events return -1 in both fields and
 * the runtime skips the MSD update. */
typedef struct { int v_origin; int v_dest; } HopOutcome;

typedef HopOutcome (*ApplyFn)(struct State *st, const struct Lattice *lat, int site);
extern const ApplyFn *const pylatkmc_apply_table;

/* Decision tree: enrol every eligible Process at `site` into `as`. */
void touchup_a(const struct Lattice *lat, const struct State *st,
               struct AvailSites *as, int site);

#endif /* PYLATKMC_PROCLIST_H */
