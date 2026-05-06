#ifndef PYLATKMC_AVAIL_SITES_H
#define PYLATKMC_AVAIL_SITES_H

#include <stdint.h>

/* Dual-index event-availability bookkeeping for the pattern-DB runtime.
 *
 * Port of kmos's `avail_sites(proc, k, switch)` Fortran 3-D array
 * (`_archive/kmos-main/kmos/fortran_src/base.mpy:88-302`) to C.
 *
 * Layout
 * ------
 * For every (proc, site) pair we maintain *two* views, kept consistent:
 *
 *   site_at [proc][k    ]  for k in [0, n_sites_per_proc[proc])
 *       The k-th site currently enrolled for `proc`. Packed dense, no gaps,
 *       order is irrelevant (insertion-order in practice).
 *
 *   slot_of[proc][site]
 *       The slot k where `site` is stored in site_at[proc], or -1 if `site`
 *       is not currently enrolled for `proc`.
 *
 * Together these give O(1) `avail_sites_add` and `avail_sites_del`:
 *
 *   add(p, s):  k = n[p]++;    site_at[p][k]    = s;  slot_of[p][s] = k;
 *   del(p, s):  k = slot_of[p][s];
 *               last = --n[p];
 *               site_at[p][k]    = site_at[p][last];        // swap-last
 *               slot_of[p][site_at[p][k]] = k;
 *               slot_of[p][s]    = -1;
 *
 * BKL selection
 * -------------
 * `rates[p]` is the per-proc rate constant (one rate per proc; intra-proc
 * rate variation is handled by emitting separate procs in pylatkmc M-A).
 * `cum_rates[p] = sum_{j=0..p} rates[j] * n_sites_per_proc[j]`.
 *
 * `avail_sites_select(target)` binary-searches `cum_rates` for the smallest
 * proc p with cum_rates[p] > target, then picks the slot
 * k = floor((target - cum_rates[p-1]) / rates[p]) within that proc.
 *
 * Memory
 * ------
 * For (n_procs=358, n_sites=4096) this is ~12 MB total. We allocate
 * `site_at` and `slot_of` as full n_procs * n_sites tables — conservative
 * but trivial to index. If models ever exceed ~50 MB we can compress
 * `site_at` to be sparse-per-proc; not needed for v0.2.
 *
 * Caller pattern
 * --------------
 * The runtime calls
 *
 *   avail_sites_clear(as);                    // wipe all enrolments
 *   for site in active_sites:                 // see active_filter.h
 *       touchup_a(site);                      // generated; calls add_proc
 *   avail_sites_refresh_cum_rates(as);        // recompute cum_rates[]
 *   double r_tot = avail_sites_r_tot(as);
 *   target = r1 * r_tot;
 *   avail_sites_select(as, target, &p, &s);
 *
 * once per KMC step. Incremental rebuild (only the touchup-stencil sites)
 * is a future optimisation — M1-style full-rebuild semantics are correct
 * and acceptable for v0.2.
 */

typedef struct AvailSites AvailSites;

/* Allocate. n_procs and n_sites must be > 0.
 * Returns 0 on success; -EINVAL on bad args; -ENOMEM on allocation failure.
 * On failure, *out is set to NULL. */
int  avail_sites_alloc(AvailSites **out, int32_t n_procs, int32_t n_sites);

/* Free; safe to call with NULL. */
void avail_sites_free(AvailSites *as);

/* Configure the rate constant for `proc`. Must be called for every proc
 * before `avail_sites_refresh_cum_rates`. Negative rates are rejected. */
void avail_sites_set_rate(AvailSites *as, int32_t proc, double rate);

/* Wipe all enrolments. Rates are NOT touched (they're a model constant). */
void avail_sites_clear(AvailSites *as);

/* O(1) add: append `site` to `proc`'s dense list. It is a programming
 * error to add a (proc, site) pair that's already enrolled. */
void avail_sites_add(AvailSites *as, int32_t proc, int32_t site);

/* O(1) del: remove `site` from `proc`'s dense list. It is a programming
 * error to del a (proc, site) pair that isn't enrolled. */
void avail_sites_del(AvailSites *as, int32_t proc, int32_t site);

/* Recompute cum_rates[] from rates[] and n_sites_per_proc[]. Call after
 * any batch of add/del. O(n_procs). */
void avail_sites_refresh_cum_rates(AvailSites *as);

/* Total event rate. Returns 0 if the index is empty or rates aren't
 * populated. Reads cum_rates[n_procs - 1]; you must call
 * `avail_sites_refresh_cum_rates` first. */
double avail_sites_r_tot(const AvailSites *as);

/* BKL select: pick (proc, site) given a uniform random number scaled
 * to [0, r_tot). Returns 0 on success; -ENODATA if r_tot == 0. */
int avail_sites_select(const AvailSites *as, double target,
                       int32_t *out_proc, int32_t *out_site);

/* Introspection (also useful for testing). */
int32_t avail_sites_n_procs   (const AvailSites *as);
int32_t avail_sites_n_sites   (const AvailSites *as);
int32_t avail_sites_count     (const AvailSites *as, int32_t proc);
/* Returns 1 if (proc, site) is enrolled, 0 if not, -1 on bad args. */
int32_t avail_sites_is_enrolled(const AvailSites *as, int32_t proc, int32_t site);
/* Read the i-th site enrolled for proc; returns -1 if i is out of range. */
int32_t avail_sites_site_at   (const AvailSites *as, int32_t proc, int32_t k);
double  avail_sites_rate      (const AvailSites *as, int32_t proc);
double  avail_sites_cum_rate  (const AvailSites *as, int32_t proc);

#endif /* PYLATKMC_AVAIL_SITES_H */
