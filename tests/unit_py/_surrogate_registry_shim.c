/* _surrogate_registry_shim — ctypes bridge for the flag-registry tests
 * (test_surrogate_registry, large-system-scaling/11).
 *
 * Drives runtime/src/core/surrogate.c's per-step registry accounting
 * (surrogate_account -> flag_lookup) with caller-given candidate lists, reads
 * the registry back in index order, and runs a registry-full workload in C so
 * a test can time it. Compiled against a generated-template proclist.h that
 * defines PYLATKMC_HAS_SURROGATE. NOT a production component. */

#include "proclist.h"   /* PYLATKMC_HAS_SURROGATE */
#include "surrogate.h"

#include <stdlib.h>
#include <string.h>

/* surrogate.c's measured-channel de-dup hook; these tests never rebuild
 * candidates, so no proclist.c is linked. */
int pylatkmc_measured_covers_hop(const Lattice *lat, const State *st,
                                 const AvailSites *as, int32_t vac_site,
                                 int32_t neigh_site)
{
    (void)lat; (void)st; (void)as; (void)vac_site; (void)neigh_site;
    return 0;
}

/* Zeroed: only its address matters (a non-NULL model enables the channel). */
static const Surrogate test_model;

SurrCtx *pylatkmc_test_reg_new(int32_t capacity)
{
    SurrCtx *ctx = malloc(sizeof *ctx);
    if (ctx && surrogate_ctx_init(ctx, &test_model, 0, /*enabled=*/1, 0.0, 0.0,
                                  /*flux_threshold=*/0.0, capacity, 600.0) != 0) {
        free(ctx);
        ctx = NULL;
    }
    return ctx;
}

void pylatkmc_test_reg_free(SurrCtx *ctx)
{
    if (ctx) surrogate_ctx_free(ctx);
    free(ctx);
}

/* Load n candidates as surrogate_rebuild leaves them (surr_rtot = their k
 * summed in list order), then run one step's surrogate_account. */
int pylatkmc_test_reg_step(SurrCtx *ctx, const Lattice *lat, int32_t n,
                           const int32_t *vac, const int32_t *neigh,
                           const int32_t *dir, const uint8_t *sp, const double *k,
                           const double *ea, const double *lev, const uint32_t *trig,
                           int32_t fired, double dt, double k_total)
{
    if (n > ctx->cap_cand) {
        SurrCandidate *p = realloc(ctx->cand, (size_t)n * sizeof *p);
        if (!p) return -1;
        ctx->cand = p;
        ctx->cap_cand = n;
    }
    ctx->n_cand = n;
    ctx->surr_rtot = 0.0;
    for (int32_t i = 0; i < n; ++i) {
        SurrCandidate *c = &ctx->cand[i];
        c->vac_site = vac[i]; c->neigh_site = neigh[i]; c->dir_idx = dir[i];
        c->atom_sp = sp[i]; c->k = k[i]; c->ea_hat = ea[i]; c->leverage = lev[i];
        c->trigger = trig[i];
        ctx->surr_rtot += k[i];
    }
    surrogate_account(ctx, lat, fired, dt, k_total);
    return 0;
}

int32_t pylatkmc_test_reg_n_flags(const SurrCtx *ctx) { return ctx->n_flags; }

/* flags[i]: ints = {site_a, site_b, dir_idx, used, n_enrolled_steps, n_fired,
 * first_step, trigger_or, ru, rv, rw, sp_a, sp_b},
 * dbls = {carried_flux, last_ea_hat, last_leverage}. */
void pylatkmc_test_reg_flag(const SurrCtx *ctx, int32_t i, int64_t *ints, double *dbls)
{
    const SurrFlag *f = &ctx->flags[i];
    int64_t v[13] = {f->site_a, f->site_b, f->dir_idx, f->used,
                     (int64_t)f->n_enrolled_steps, (int64_t)f->n_fired,
                     (int64_t)f->first_step, f->trigger_or, f->ru, f->rv, f->rw,
                     f->sp_a, f->sp_b};
    memcpy(ints, v, sizeof v);
    dbls[0] = f->carried_flux; dbls[1] = f->last_ea_hat; dbls[2] = f->last_leverage;
}

/* A long run against a full default-capacity registry: one step enrols
 * `capacity` distinct keys (key q = (q mod 4096, 4096 + q / 4096, q mod 12),
 * registry index q), then `n_steps` steps of `n_per_step` candidates, half
 * registered keys and half new ones (which the full registry drops). Checks
 * every flag afterwards. Returns 0 if all checks pass, else a nonzero code. */
int pylatkmc_test_reg_bench(int32_t n_steps, int32_t n_per_step)
{
    enum { N_VAC_SITES = 4096 };
    SurrCtx *ctx = pylatkmc_test_reg_new(0);   /* 0 -> the default capacity */
    if (!ctx) return 1;
    const int32_t cap = ctx->capacity;
    int16_t *ijk = calloc(3 * (size_t)N_VAC_SITES, sizeof *ijk);
    uint64_t *want = calloc((size_t)cap, sizeof *want);
    int32_t n_max = cap > n_per_step ? cap : n_per_step;
    int32_t *vac = malloc((size_t)n_max * sizeof *vac);
    int32_t *neigh = malloc((size_t)n_max * sizeof *neigh);
    int32_t *dir = malloc((size_t)n_max * sizeof *dir);
    uint8_t *sp = malloc((size_t)n_max);
    double *k = malloc((size_t)n_max * sizeof *k);
    uint32_t *trig = calloc((size_t)n_max, sizeof *trig);
    Lattice lat;   /* only site_ijk is read (the first-enrolment ru/rv/rw) */
    memset(&lat, 0, sizeof lat);
    lat.n_sites = N_VAC_SITES;
    lat.site_ijk = ijk;
    int rc = 0;
    if (!ijk || !want || !vac || !neigh || !dir || !sp || !k || !trig) { rc = 2; goto done; }

    for (int32_t q = 0; q < cap; ++q) {
        vac[q] = q % N_VAC_SITES; neigh[q] = N_VAC_SITES + q / N_VAC_SITES;
        dir[q] = q % 12; sp[q] = 1; k[q] = 1.0;
    }
    if (pylatkmc_test_reg_step(ctx, &lat, cap, vac, neigh, dir, sp, k, k, k, trig,
                               -1, 1e-9, 1.0) != 0) { rc = 3; goto done; }
    uint64_t x = 88172645463325252ull;   /* xorshift64: a fixed schedule */
    for (int32_t s = 0; s < n_steps; ++s) {
        for (int32_t i = 0; i < n_per_step; ++i) {
            x ^= x << 13; x ^= x >> 7; x ^= x << 17;
            int32_t q = (int32_t)(x % (uint64_t)cap);
            if (i % 2) q += cap;       /* a new key: dropped, the registry is full */
            else want[q]++;
            vac[i] = q % N_VAC_SITES; neigh[i] = N_VAC_SITES + q / N_VAC_SITES;
            dir[i] = q % 12; sp[i] = 1; k[i] = 1.0;
        }
        if (pylatkmc_test_reg_step(ctx, &lat, n_per_step, vac, neigh, dir, sp, k, k,
                                   k, trig, 0, 1e-9, 1.0) != 0) { rc = 4; goto done; }
    }
    if (ctx->n_flags != cap) { rc = 5; goto done; }
    for (int32_t q = 0; q < cap; ++q) {
        const SurrFlag *f = &ctx->flags[q];
        if (f->site_a != q % N_VAC_SITES || f->site_b != N_VAC_SITES + q / N_VAC_SITES
            || f->dir_idx != q % 12 || f->n_enrolled_steps != 1 + want[q]) { rc = 6; goto done; }
    }
done:
    free(ijk); free(want); free(vac); free(neigh); free(dir); free(sp); free(k); free(trig);
    pylatkmc_test_reg_free(ctx);
    return rc;
}
