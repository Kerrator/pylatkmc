/* _surrogate_test_shim — ctypes bridge for the Phase C surrogate parity tests.
 *
 * Links against the generated proclist.c (which defines pylatkmc_surrogate and
 * the baked tables) + runtime/src/core/surrogate.c. Exposes the model pointer
 * and a thin surrogate_eval wrapper so a ctypes test can drive candidate
 * evaluation on a synthetic lattice and compare to the Python oracle. */

#include "proclist.h"     /* PYLATKMC_HAS_SURROGATE, pylatkmc_surrogate */

#ifdef PYLATKMC_HAS_SURROGATE
#include "surrogate.h"

const Surrogate *pylatkmc_test_surrogate(void) { return pylatkmc_surrogate; }

int pylatkmc_test_surrogate_eval(const Lattice *lat, const State *st,
                                 int32_t vac_site, int32_t dir_idx, uint8_t atom_sp,
                                 double T_K, SurrEval *out)
{
    return surrogate_eval(pylatkmc_surrogate, lat, st, vac_site, dir_idx, atom_sp,
                          T_K, /*k_floor=*/0.0, /*lev_gate=*/0.0, out);
}

int32_t pylatkmc_test_surrogate_ndir(void) { return pylatkmc_surrogate->ndir; }

/* SurrEval field size probe so the ctypes struct can be validated. */
int32_t pylatkmc_test_surreval_size(void) { return (int32_t)sizeof(SurrEval); }

/* Candidate-list probe (test_surrogate_covers): a live channel context on the
 * baked model, its rebuild against a touched-up avail_sites, its candidates. */
#include <stdlib.h>
SurrCtx *pylatkmc_test_surr_ctx_new(int32_t n_sites)
{
    SurrCtx *ctx = malloc(sizeof *ctx);
    if (ctx && surrogate_ctx_init(ctx, pylatkmc_surrogate, n_sites, /*enabled=*/1, 0.0,
                                  0.0, 0.0, /*capacity=*/0, 600.0) != 0) {
        free(ctx);
        ctx = NULL;
    }
    return ctx;
}

void pylatkmc_test_surr_ctx_free(SurrCtx *ctx)
{
    if (ctx) surrogate_ctx_free(ctx);
    free(ctx);
}

double pylatkmc_test_surr_rebuild(SurrCtx *ctx, const Lattice *lat, const State *st,
                                  const AvailSites *as, double T_K)
{
    return surrogate_rebuild(ctx, lat, st, as, T_K);
}

int32_t pylatkmc_test_surr_n_cand(const SurrCtx *ctx) { return ctx->n_cand; }

/* ints = {vac_site, neigh_site, dir_idx, atom_sp, trigger}, dbls = {k, ea_hat, leverage} */
void pylatkmc_test_surr_cand(const SurrCtx *ctx, int32_t i, int32_t *ints, double *dbls)
{
    const SurrCandidate *c = &ctx->cand[i];
    ints[0] = c->vac_site; ints[1] = c->neigh_site; ints[2] = c->dir_idx;
    ints[3] = c->atom_sp; ints[4] = (int32_t)c->trigger;
    dbls[0] = c->k; dbls[1] = c->ea_hat; dbls[2] = c->leverage;
}

/* V6/accumulator smoke: three measured fires (two with finite v6, one NaN). */
#include <math.h>
#include <string.h>
void pylatkmc_test_v6_probe(double *out_mean, double *out_max, uint64_t *out_nmeas)
{
    SurrCtx c;
    memset(&c, 0, sizeof c);
    c.enabled = 1;
    surrogate_note_measured(&c, 0.5, 0.7);   /* resid 0.2 */
    surrogate_note_measured(&c, 1.0, 1.0);   /* resid 0.0 */
    surrogate_note_measured(&c, NAN, 0.3);   /* counts as meas, no v6 */
    *out_mean = surrogate_v6_mean(&c);
    *out_max = c.v6_absresid_max;
    *out_nmeas = c.n_meas_fired;
}
#endif
