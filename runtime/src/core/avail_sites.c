/* avail_sites — O(1) add/del dual-index event book-keeping.
 *
 * See avail_sites.h for the design rationale. The implementation is a
 * straight C port of kmos's Fortran avail_sites(proc, k, switch) array
 * (kmos-main/kmos/fortran_src/base.mpy:88-302), differing only in:
 *
 * 1. 0-indexed (Fortran was 1-indexed; we use -1 for "not enrolled"
 *    where Fortran used 0).
 * 2. Two separate flat allocations (`site_at`, `slot_of`) with explicit
 *    `proc * n_sites + …` strides instead of a Fortran 3-D allocatable.
 * 3. We carry per-proc rates and a cum_rates running-sum here, where
 *    kmos has those in a sibling `accum_rates[]` array. Same data,
 *    one struct.
 *
 * No internal allocations after avail_sites_alloc. All the per-step
 * book-keeping is in-place pointer arithmetic.
 */

#include "avail_sites.h"

#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

struct AvailSites {
    int32_t  n_procs;
    int32_t  n_sites;

    /* Dense list of enrolled sites per proc.
     * Indexed as site_at[proc * n_sites + k] for k in [0, n_sites_per_proc[proc]). */
    int32_t *site_at;

    /* Reverse map: slot_of[proc * n_sites + site] = k or -1 if not enrolled. */
    int32_t *slot_of;

    /* Per-proc enrolment count. */
    int32_t *n_sites_per_proc;

    /* Per-proc rate constant, set by avail_sites_set_rate. */
    double  *rates;

    /* Per-proc cumulative running sum of rates[j] * n_sites_per_proc[j].
     * Populated by avail_sites_refresh_cum_rates. */
    double  *cum_rates;
};

static inline size_t pair_idx(const AvailSites *as, int32_t proc, int32_t key)
{
    return (size_t)proc * (size_t)as->n_sites + (size_t)key;
}

int avail_sites_alloc(AvailSites **out, int32_t n_procs, int32_t n_sites)
{
    if (!out || n_procs <= 0 || n_sites <= 0) return -EINVAL;
    *out = NULL;

    AvailSites *as = calloc(1, sizeof *as);
    if (!as) return -ENOMEM;

    as->n_procs = n_procs;
    as->n_sites = n_sites;

    size_t pair = (size_t)n_procs * (size_t)n_sites;
    as->site_at          = malloc(pair * sizeof *as->site_at);
    as->slot_of          = malloc(pair * sizeof *as->slot_of);
    as->n_sites_per_proc = calloc((size_t)n_procs, sizeof *as->n_sites_per_proc);
    as->rates            = calloc((size_t)n_procs, sizeof *as->rates);
    as->cum_rates        = calloc((size_t)n_procs, sizeof *as->cum_rates);

    if (!as->site_at || !as->slot_of || !as->n_sites_per_proc
        || !as->rates || !as->cum_rates) {
        avail_sites_free(as);
        return -ENOMEM;
    }

    /* slot_of starts as -1 everywhere (no site enrolled for any proc). */
    for (size_t i = 0; i < pair; ++i) as->slot_of[i] = -1;
    /* site_at content is undefined while not enrolled; clear for cleanliness. */
    memset(as->site_at, 0, pair * sizeof *as->site_at);

    *out = as;
    return 0;
}

void avail_sites_free(AvailSites *as)
{
    if (!as) return;
    free(as->site_at);
    free(as->slot_of);
    free(as->n_sites_per_proc);
    free(as->rates);
    free(as->cum_rates);
    free(as);
}

void avail_sites_set_rate(AvailSites *as, int32_t proc, double rate)
{
    if (!as || proc < 0 || proc >= as->n_procs) return;
    if (rate < 0.0) return;
    as->rates[proc] = rate;
}

void avail_sites_clear(AvailSites *as)
{
    if (!as) return;
    /* Reset slot_of to -1 only for currently-enrolled (proc, site) pairs.
     * For typical workloads (fraction enrolled ≪ 1) this is much cheaper
     * than memset'ing the entire n_procs * n_sites table.
     *
     * We walk site_at[] up to n_sites_per_proc[proc] to find the enrolled
     * sites, then clear their slot_of entries.
     */
    for (int32_t p = 0; p < as->n_procs; ++p) {
        int32_t n = as->n_sites_per_proc[p];
        for (int32_t k = 0; k < n; ++k) {
            int32_t s = as->site_at[pair_idx(as, p, k)];
            as->slot_of[pair_idx(as, p, s)] = -1;
        }
        as->n_sites_per_proc[p] = 0;
        as->cum_rates[p] = 0.0;
    }
}

void avail_sites_add(AvailSites *as, int32_t proc, int32_t site)
{
    if (!as || proc < 0 || proc >= as->n_procs) return;
    if (site < 0 || site >= as->n_sites) return;

    /* It's a programming error to add a pair that's already enrolled; assert
     * in debug builds, no-op in release for safety. */
    assert(as->slot_of[pair_idx(as, proc, site)] == -1
           && "avail_sites_add: (proc, site) already enrolled");
    if (as->slot_of[pair_idx(as, proc, site)] != -1) return;

    int32_t k = as->n_sites_per_proc[proc];
    as->site_at[pair_idx(as, proc, k)] = site;
    as->slot_of[pair_idx(as, proc, site)] = k;
    as->n_sites_per_proc[proc] = k + 1;
}

void avail_sites_del(AvailSites *as, int32_t proc, int32_t site)
{
    if (!as || proc < 0 || proc >= as->n_procs) return;
    if (site < 0 || site >= as->n_sites) return;

    int32_t k = as->slot_of[pair_idx(as, proc, site)];
    assert(k >= 0 && "avail_sites_del: (proc, site) not enrolled");
    if (k < 0) return;

    int32_t last = as->n_sites_per_proc[proc] - 1;
    if (k != last) {
        /* Move the last entry into the freed slot. */
        int32_t moved_site = as->site_at[pair_idx(as, proc, last)];
        as->site_at[pair_idx(as, proc, k)] = moved_site;
        as->slot_of[pair_idx(as, proc, moved_site)] = k;
    }
    /* Mark our slot vacant; whoever moved into it is already pointed at by slot_of. */
    as->slot_of[pair_idx(as, proc, site)] = -1;
    as->n_sites_per_proc[proc] = last;
}

void avail_sites_refresh_cum_rates(AvailSites *as)
{
    if (!as) return;
    double cum = 0.0;
    for (int32_t p = 0; p < as->n_procs; ++p) {
        cum += as->rates[p] * (double)as->n_sites_per_proc[p];
        as->cum_rates[p] = cum;
    }
}

double avail_sites_r_tot(const AvailSites *as)
{
    if (!as || as->n_procs <= 0) return 0.0;
    return as->cum_rates[as->n_procs - 1];
}

int avail_sites_select(const AvailSites *as, double target,
                       int32_t *out_proc, int32_t *out_site)
{
    if (!as || !out_proc || !out_site) return -EINVAL;
    double r_tot = avail_sites_r_tot(as);
    if (r_tot <= 0.0) return -ENODATA;

    /* Clamp to be safe against caller-supplied target == r_tot exactly. */
    if (target < 0.0)         target = 0.0;
    if (target >= r_tot)      target = r_tot * (1.0 - 1e-15);

    /* Binary search for smallest p with cum_rates[p] > target. */
    int32_t lo = 0, hi = as->n_procs - 1;
    while (lo < hi) {
        int32_t mid = lo + (hi - lo) / 2;
        if (as->cum_rates[mid] > target) hi = mid;
        else                              lo = mid + 1;
    }
    int32_t proc = lo;
    /* Skip empty procs that snuck in (rate>0, count=0 → cum unchanged). */
    while (proc < as->n_procs && as->n_sites_per_proc[proc] == 0) ++proc;
    if (proc >= as->n_procs) return -ENODATA;  /* shouldn't happen if r_tot > 0 */

    double prev = (proc == 0) ? 0.0 : as->cum_rates[proc - 1];
    double rate = as->rates[proc];
    int32_t k;
    if (rate > 0.0) {
        k = (int32_t)((target - prev) / rate);
    } else {
        k = 0;  /* defensive: if rate==0 it shouldn't have made it past binary search */
    }
    if (k < 0) k = 0;
    if (k >= as->n_sites_per_proc[proc]) k = as->n_sites_per_proc[proc] - 1;

    *out_proc = proc;
    *out_site = as->site_at[pair_idx(as, proc, k)];
    return 0;
}

int32_t avail_sites_n_procs(const AvailSites *as)   { return as ? as->n_procs : 0; }
int32_t avail_sites_n_sites(const AvailSites *as)   { return as ? as->n_sites : 0; }

int32_t avail_sites_count(const AvailSites *as, int32_t proc)
{
    if (!as || proc < 0 || proc >= as->n_procs) return 0;
    return as->n_sites_per_proc[proc];
}

int32_t avail_sites_is_enrolled(const AvailSites *as, int32_t proc, int32_t site)
{
    if (!as) return -1;
    if (proc < 0 || proc >= as->n_procs) return -1;
    if (site < 0 || site >= as->n_sites) return -1;
    return (as->slot_of[pair_idx(as, proc, site)] >= 0) ? 1 : 0;
}

int32_t avail_sites_site_at(const AvailSites *as, int32_t proc, int32_t k)
{
    if (!as || proc < 0 || proc >= as->n_procs) return -1;
    if (k < 0 || k >= as->n_sites_per_proc[proc]) return -1;
    return as->site_at[pair_idx(as, proc, k)];
}

double avail_sites_rate(const AvailSites *as, int32_t proc)
{
    if (!as || proc < 0 || proc >= as->n_procs) return 0.0;
    return as->rates[proc];
}

double avail_sites_cum_rate(const AvailSites *as, int32_t proc)
{
    if (!as || proc < 0 || proc >= as->n_procs) return 0.0;
    return as->cum_rates[proc];
}
