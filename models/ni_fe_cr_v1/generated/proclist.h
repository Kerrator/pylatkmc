/* proclist.h — GENERATED from ni_fe_cr_v1.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build ni_fe_cr_v1.kmcspec.toml`.
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

#include "lattice.h"
#include "state.h"
#include "avail_sites.h"

/* Number of Processes in this model. Defined by the generated enum
 * in proclist.c; exposed here as a const for sizeof / loop bounds. */
extern const int32_t pylatkmc_n_procs;

/* Rate table: per-Process Arrhenius rate (s^-1) baked at codegen time.
 * Read by replica.c at startup to seed avail_sites_set_rate.
 *
 * Declared as a pointer (not an array) so the storage in proclist.c can
 * be a `const RateConst *const` alias to a file-static array. */
typedef struct { double rate; double Ea_eV; } RateConst;
extern const RateConst *const pylatkmc_rate_table;

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
