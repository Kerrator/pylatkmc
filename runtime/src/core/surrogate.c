/* surrogate.c — Phase C surrogate rate channel (b).
 *
 * Exact C port of pylatkmc/ingest/surrogate.py's map-level feature functions
 * (state_features, dphi2_from_maps) + a depth-signature port, evaluated over the
 * baked per-1NN-direction context tables from surrogate_codegen. The channel is
 * compiled out entirely unless the generated proclist.h defines
 * PYLATKMC_HAS_SURROGATE (v0.3 / no-model builds → empty TU). */

#include "proclist.h"   /* PYLATKMC_HAS_SURROGATE, PYLATKMC_KB_EV_PER_K, pylatkmc_surrogate */

#ifdef PYLATKMC_HAS_SURROGATE

#include "surrogate.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "events_base.h"   /* SP_VACANT, SP_NI, SP_CR */

/* Covered-hop check emitted into proclist.c (measured-channel de-dup). */
int pylatkmc_measured_covers_hop(const Lattice *lat, const State *st,
                                 const AvailSites *as,
                                 int32_t vac_site, int32_t neigh_site);

/* ---- feature category codes (match the s{shell}_{cat} ordering C,E,N,U) ---- */
enum { CAT_C = 0, CAT_E = 1, CAT_N = 2, CAT_U = 3 };

static inline int sp_base_cat(uint8_t sp)
{
    if (sp == SP_NI) return CAT_N;
    if (sp == SP_CR) return CAT_C;
    return CAT_E;   /* SP_VACANT, stub(255), anything else → empty */
}

/* phi feature-index helpers (ESYM_FEATURE_KEYS order) */
#define PHI_ABS_DELTA   0
#define PHI_DEPTH_PARAM 7
#define PHI_DEPTH_SURF  8
#define PHI_N_DELTA     17
#define SHELL_IDX(sh, cat) (18 + (sh) * 4 + (cat))

/* bond index for a sorted {C,E,N} pair (U excluded): C=0<E=1<N=2 */
static const int BOND_IDX[3][3] = { {1, 2, 3}, {2, 4, 5}, {3, 5, 6} };

/* triangle index for a sorted {C,E,N,U} pair, base 58 */
static const int TRI_BASE[4] = {0, 4, 7, 9};
static inline int tri_idx(int a, int b)
{
    int lo = a < b ? a : b, hi = a < b ? b : a;
    return 58 + TRI_BASE[lo] + (hi - lo);
}
/* mv index: mover species cat (C or N) × neighbour cat (C,E,N,U) */
static inline int mv_idx(int mover_cat, int nb_cat)
{
    return (mover_cat == CAT_C ? 9 : 13) + nb_cat;
}

/* --- one direction's live category map for a (config, mask) --- */
enum { CFG_ATOM_AT_N = 0, CFG_ATOM_AT_V = 1 };
enum { MASK_N = 0, MASK_V = 1, MASK_MID = 2 };

static inline uint8_t site_near(const SurrSite *s, int mask_sel)
{
    if (mask_sel == MASK_N)  return s->near_n;
    if (mask_sel == MASK_V)  return s->near_v;
    return s->near_mid;
}

/* Fill cat[] for every ball site given the resolved base category per site
 * (base_cat[], config-independent context) plus the two mover overrides. */
static void fill_cat(const SurrDir *D, const int8_t *base_cat, int atom_cat,
                     int config, int mask_sel, int8_t *cat)
{
    for (int32_t i = 0; i < D->n_sites; ++i) {
        int base;
        if (i == D->vac_idx)
            base = (config == CFG_ATOM_AT_V) ? atom_cat : CAT_E;
        else if (i == D->atom_idx)
            base = (config == CFG_ATOM_AT_N) ? atom_cat : CAT_E;
        else
            base = base_cat[i];
        if (base == CAT_E)
            cat[i] = site_near(&D->sites[i], mask_sel) ? CAT_E : CAT_U;
        else
            cat[i] = (int8_t)base;   /* N/C never U */
    }
}

/* Accumulate weight * state_features(cat) into phi. `shell_v_frame` selects the
 * per-site shell array (0 = shell_n, 1 = shell_v). */
static void sf_accumulate(const SurrDir *D, const int8_t *cat, int shell_v_frame,
                          double *phi, double weight)
{
    /* shells: every ball site contributes (U included). */
    for (int32_t i = 0; i < D->n_sites; ++i) {
        int sh = shell_v_frame ? D->sites[i].shell_v : D->sites[i].shell_n;
        phi[SHELL_IDX(sh, cat[i])] += weight;
    }
    /* 1NN bonds (both endpoints non-U). */
    for (int32_t b = 0; b < D->n_bond; ++b) {
        int ci = cat[D->bond_i[b]], cj = cat[D->bond_j[b]];
        if (ci == CAT_U || cj == CAT_U) continue;
        phi[BOND_IDX[ci][cj]] += weight;
    }
    /* mover-local broken bonds + triangles, for each occupied mover. */
    for (int mv = 0; mv < 2; ++mv) {
        int32_t moidx = mv == 0 ? D->vac_idx : D->atom_idx;
        int mcat = cat[moidx];
        if (mcat != CAT_N && mcat != CAT_C) continue;
        int32_t n_nbr = mv == 0 ? D->n_vac_nbr : D->n_atom_nbr;
        const int16_t *nbr = mv == 0 ? D->vac_nbr : D->atom_nbr;
        for (int32_t k = 0; k < n_nbr; ++k)
            phi[mv_idx(mcat, cat[nbr[k]])] += weight;
        int32_t n_tri = mv == 0 ? D->n_vac_tri : D->n_atom_tri;
        const int16_t *tri = mv == 0 ? D->vac_tri : D->atom_tri;
        for (int32_t t = 0; t < n_tri; ++t)
            phi[tri_idx(cat[tri[2 * t]], cat[tri[2 * t + 1]])] += weight;
    }
}

/* depth signature (port of ingest compute_depth_sig), operating on cat[]. */
#define SURR_DMAX 2
static void depth_sig(const SurrDir *D, const int8_t *cat, int32_t seed_idx,
                      int *out_surface, int *out_param)
{
    int32_t n_nbr = (seed_idx == D->vac_idx) ? D->n_vac_nbr : D->n_atom_nbr;
    const int16_t *nbr = (seed_idx == D->vac_idx) ? D->vac_nbr : D->atom_nbr;
    const int8_t *nbr_o = (seed_idx == D->vac_idx) ? D->vac_nbr_o : D->atom_nbr_o;
    int coordination = 0, n_empty = 0;
    double net[3] = {0.0, 0.0, 0.0};
    for (int32_t k = 0; k < n_nbr; ++k) {
        int c = cat[nbr[k]];
        if (c == CAT_N || c == CAT_C) {
            coordination++;
        } else if (c == CAT_E) {
            n_empty++;
            for (int a = 0; a < 3; ++a)
                net[a] += (double)nbr_o[3 * k + a] / sqrt(2.0);
        }
    }
    if (coordination < 12 && n_empty >= 3) {
        double nrm = sqrt(net[0] * net[0] + net[1] * net[1] + net[2] * net[2]);
        if (nrm >= 0.5 * (double)n_empty) {
            *out_surface = 1;
            *out_param = coordination;
            return;
        }
    }
    /* subsurface: min layer distance from seed to an EMPTY-with-occupied-nbr. */
    int seed_k = D->sites[seed_idx].ck;
    int dmin = -1;
    for (int32_t i = 0; i < D->n_sites; ++i) {
        if (cat[i] != CAT_E) continue;
        int has_occ = 0;
        for (int k = 0; k < 12; ++k) {
            int32_t j = D->nn1_adj[12 * i + k];
            if (j >= 0 && (cat[j] == CAT_N || cat[j] == CAT_C)) { has_occ = 1; break; }
        }
        if (!has_occ) continue;
        int dk = D->sites[i].ck - seed_k;
        if (dk < 0) dk = -dk;
        if (dmin < 0 || dk < dmin) dmin = dk;
    }
    *out_surface = 0;
    *out_param = (dmin >= 0 && dmin <= SURR_DMAX) ? dmin : -1;
}

/* exposure(off): EMPTY count among in-ball 1NN of ball index `idx`. */
static inline int exposure(const SurrDir *D, const int8_t *cat, int32_t idx)
{
    int n = 0;
    for (int k = 0; k < 12; ++k) {
        int32_t j = D->nn1_adj[12 * idx + k];
        if (j >= 0 && cat[j] == CAT_E) ++n;
    }
    return n;
}

/* sp_key p-index for a delta/affected pair (both in {N,C}); N-before-C. */
static inline int spkey_p(int a, int b)
{
    if (a == CAT_N && b == CAT_N) return 0;   /* NN */
    if (a == CAT_C && b == CAT_C) return 2;   /* CC */
    return 1;                                  /* NC */
}

/* dphi2_from_maps port. `bef`/`aft` are cat[] arrays (midpoint mask). */
static void dphi2(const SurrDir *D, const int8_t *bef, const int8_t *aft, double *v)
{
    for (int i = 0; i < SURR_NH2; ++i) v[i] = 0.0;
    int32_t va = D->vac_idx, at = D->atom_idx;
    int32_t dset0 = va < at ? va : at, dset1 = va < at ? at : va;   /* sorted */
    /* aff membership flag */
    /* dset/aff tests: ball index order == crystal-offset lex order. */
    for (int pass = 0; pass < 2; ++pass) {
        const int8_t *m = pass == 0 ? aft : bef;
        double sgn = pass == 0 ? 1.0 : -1.0;
        int32_t dvals[2] = {dset0, dset1};
        for (int di = 0; di < 2; ++di) {
            int32_t i = dvals[di];
            int a = m[i];
            if (a == CAT_N) v[0] += sgn;
            else if (a == CAT_C) v[1] += sgn;
            if (a != CAT_N && a != CAT_C) continue;
            for (int shell = 1; shell <= 2; ++shell) {
                int nadj = shell == 1 ? 12 : 6;
                const int16_t *adj = shell == 1 ? D->nn1_adj : D->nn2_adj;
                for (int k = 0; k < nadj; ++k) {
                    int32_t j = adj[(shell == 1 ? 12 : 6) * i + k];
                    if (j >= 0 && (j == dset0 || j == dset1) && j < i) continue;
                    int b = (j < 0) ? CAT_U : m[j];
                    if (b == CAT_E) continue;
                    if (b == CAT_U) {
                        v[(shell == 1 ? 14 : 16) + (a == CAT_N ? 0 : 1)] += sgn;
                        continue;
                    }
                    int surf = (exposure(D, m, i) >= 3) ||
                               (j >= 0 && exposure(D, m, j) >= 3);
                    int p = spkey_p(a, b);
                    v[(shell == 1 ? 2 : 8) + (surf ? 3 : 0) + p] += sgn;
                }
            }
        }
        for (int32_t ai = 0; ai < D->n_aff; ++ai) {
            int32_t i = D->aff[ai];
            int a = m[i];
            if (a != CAT_N && a != CAT_C) continue;
            for (int shell = 1; shell <= 2; ++shell) {
                int nadj = shell == 1 ? 12 : 6;
                const int16_t *adj = shell == 1 ? D->nn1_adj : D->nn2_adj;
                for (int k = 0; k < nadj; ++k) {
                    int32_t j = adj[nadj * i + k];
                    if (j >= 0 && (j == dset0 || j == dset1)) continue;
                    /* j in aff and j < i ? */
                    if (j >= 0 && j < i) {
                        int in_aff = 0;
                        for (int32_t t = 0; t < D->n_aff; ++t)
                            if (D->aff[t] == j) { in_aff = 1; break; }
                        if (in_aff) continue;
                    }
                    int b = (j < 0) ? CAT_U : m[j];
                    if (b != CAT_N && b != CAT_C) continue;
                    int surf = (exposure(D, m, i) >= 3) ||
                               (j >= 0 && exposure(D, m, j) >= 3);
                    int p = spkey_p(a, b);
                    v[(shell == 1 ? 2 : 8) + (surf ? 3 : 0) + p] += sgn;
                }
            }
        }
    }
}

/* ------------------------------------------------------------------------- */
/* Candidate evaluation                                                      */
/* ------------------------------------------------------------------------- */
int surrogate_eval(const Surrogate *S, const Lattice *lat, const State *st,
                   int32_t vac_site, int32_t dir_idx, uint8_t atom_sp,
                   double T_K, double k_floor, double lev_gate, SurrEval *out)
{
    if (!S || !lat || !st || !out || dir_idx < 0 || dir_idx >= S->ndir)
        return -EINVAL;
    const SurrDir *D = &S->dirs[dir_idx];
    int atom_cat = sp_base_cat(atom_sp);

    /* Resolve the ball + base (context) categories from the live state. */
    static int8_t base_cat[512];
    static int8_t cbn[512], can[512], cbv[512], cav[512], cbm[512], cam[512];
    if (D->n_sites > 512) return -EINVAL;
    const int16_t *c0 = &lat->site_ijk[3 * vac_site];
    for (int32_t i = 0; i < D->n_sites; ++i) {
        const SurrSite *s = &D->sites[i];
        int32_t rs = lattice_site_at_ijk(lat, c0[0] + s->ru, c0[1] + s->rv, c0[2] + s->rw);
        base_cat[i] = (int8_t)sp_base_cat(st->species[rs]);
    }

    double *phi = out->phi;
    for (int i = 0; i < SURR_NPHI; ++i) phi[i] = 0.0;

    /* directional n (atom-end anchor): shell_n, near_n */
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_N, MASK_N, cbn);
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_V, MASK_N, can);
    sf_accumulate(D, cbn, /*shell_v=*/0, phi, 0.25);
    sf_accumulate(D, can, 0, phi, 0.25);
    /* directional v (vac-end anchor): shell_v, near_v */
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_V, MASK_V, cbv);
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_N, MASK_V, cav);
    sf_accumulate(D, cbv, /*shell_v=*/1, phi, 0.25);
    sf_accumulate(D, cav, 1, phi, 0.25);

    int ds_n, dp_n, ds_v, dp_v;
    depth_sig(D, cbn, D->atom_idx, &ds_n, &dp_n);
    depth_sig(D, cbv, D->vac_idx, &ds_v, &dp_v);
    phi[PHI_ABS_DELTA]   = 0.0;
    phi[PHI_N_DELTA]     = 2.0;
    phi[PHI_DEPTH_SURF]  = 0.5 * (double)(ds_n + ds_v);
    phi[PHI_DEPTH_PARAM] = 0.5 * (double)(dp_n + dp_v);

    /* E_sym = z.w + ym ; leverage = z.Ainv.z ; z = (phi-mu)/sd */
    static double z[SURR_NPHI];
    double e = S->ym, lev = 0.0;
    for (int i = 0; i < SURR_NPHI; ++i) {
        z[i] = (phi[i] - S->mu[i]) / S->sd[i];
        e += z[i] * S->w[i];
    }
    for (int i = 0; i < SURR_NPHI; ++i) {
        double az = 0.0;
        const double *row = &S->ainv[(size_t)i * SURR_NPHI];
        for (int j = 0; j < SURR_NPHI; ++j) az += row[j] * z[j];
        lev += z[i] * az;
    }

    /* dphi2 (midpoint mask): forward = atom n→v */
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_N, MASK_MID, cbm);
    fill_cat(D, base_cat, atom_cat, CFG_ATOM_AT_V, MASK_MID, cam);
    double dv[SURR_NH2];
    dphi2(D, cbm, cam, dv);
    double dE = 0.0;
    for (int i = 0; i < SURR_NH2; ++i) dE += dv[i] * S->h2_theta[i];

    /* context counts (species trigger): before-midpoint map N/C/E. */
    int nN = 0, nC = 0, nE = 0;
    for (int32_t i = 0; i < D->n_sites; ++i) {
        if (cbm[i] == CAT_N) nN++;
        else if (cbm[i] == CAT_C) nC++;
        else if (cbm[i] == CAT_E) nE++;
    }

    double ea = e + 0.5 * dE;
    uint32_t trig = 0;
    double eac = ea;
    if (eac < S->ea_lo) { eac = S->ea_lo; trig |= SURR_TRIG_CLAMP; }
    if (eac > S->ea_hi) { eac = S->ea_hi; trig |= SURR_TRIG_CLAMP; }
    double kT = PYLATKMC_KB_EV_PER_K * T_K;
    double k = S->tier0_nu0_hz * exp(-eac / kT);
    double floor_k = (k_floor > 0.0) ? k_floor : S->tier0_nu0_hz * exp(-S->ea_hi / kT);
    if (k < floor_k) k = floor_k;

    if (lev > (lev_gate > 0.0 ? lev_gate : S->lev_q75)) trig |= SURR_TRIG_LEVERAGE;
    if (nN < S->ctx_n_lo || nN > S->ctx_n_hi ||
        nC < S->ctx_c_lo || nC > S->ctx_c_hi ||
        nE < S->ctx_e_lo || nE > S->ctx_e_hi) trig |= SURR_TRIG_SPECIES;

    out->e_sym = e;
    out->dE_H = dE;
    out->ea_hat = ea;
    out->ea_clamped = eac;
    out->leverage = lev;
    out->k = k;
    out->trigger = trig;
    out->n_ctx = nN; out->c_ctx = nC; out->e_ctx = nE;
    return 0;
}

/* ------------------------------------------------------------------------- */
/* Runtime channel driver                                                    */
/* ------------------------------------------------------------------------- */
int surrogate_ctx_init(SurrCtx *ctx, const Surrogate *model, int32_t n_sites,
                       int enabled, double k_floor, double lev_gate,
                       double flux_threshold, int32_t capacity, double T_K)
{
    if (!ctx) return -EINVAL;
    memset(ctx, 0, sizeof(*ctx));
    ctx->model = model;
    ctx->enabled = enabled && model != NULL;
    ctx->k_floor = k_floor;
    ctx->lev_gate = lev_gate;
    ctx->flux_threshold = flux_threshold > 0.0 ? flux_threshold : 0.01;
    ctx->capacity = capacity > 0 ? capacity : 65536;
    (void)n_sites; (void)T_K;
    if (!ctx->enabled) return 0;
    ctx->cap_cand = 256;
    ctx->cand = calloc((size_t)ctx->cap_cand, sizeof *ctx->cand);
    ctx->flags = calloc((size_t)ctx->capacity, sizeof *ctx->flags);
    if (!ctx->cand || !ctx->flags) { surrogate_ctx_free(ctx); return -ENOMEM; }
    return 0;
}

void surrogate_ctx_free(SurrCtx *ctx)
{
    if (!ctx) return;
    free(ctx->cand); free(ctx->flags);
    ctx->cand = NULL; ctx->flags = NULL;
}

static SurrFlag *flag_lookup(SurrCtx *ctx, int32_t a, int32_t b, int32_t dir)
{
    int32_t lo = a < b ? a : b, hi = a < b ? b : a;
    for (int32_t i = 0; i < ctx->n_flags; ++i) {
        SurrFlag *f = &ctx->flags[i];
        if (f->used && f->site_a == lo && f->site_b == hi && f->dir_idx == dir)
            return f;
    }
    if (ctx->n_flags >= ctx->capacity) return NULL;   /* full: drop silently-capped */
    SurrFlag *f = &ctx->flags[ctx->n_flags++];
    f->used = 1; f->site_a = lo; f->site_b = hi; f->dir_idx = dir;
    f->first_step = 0; f->n_enrolled_steps = 0; f->n_fired = 0;
    f->carried_flux = 0.0; f->trigger_or = 0;
    return f;
}

double surrogate_rebuild(SurrCtx *ctx, const Lattice *lat, const State *st,
                         const AvailSites *as, double T_K)
{
    ctx->n_cand = 0;
    ctx->surr_rtot = 0.0;
    if (!ctx->enabled) return 0.0;
    const Surrogate *S = ctx->model;
    for (int32_t vi = 0; vi < st->n_vac; ++vi) {
        int32_t v = st->vac_list[vi];
        for (int32_t e = lattice_nn1_begin(lat, v); e < lattice_nn1_end(lat, v); ++e) {
            int32_t n = lat->nn1_indices[e];
            uint8_t sp = st->species[n];
            if (sp != SP_NI && sp != SP_CR) continue;   /* real atom only */
            /* which baked direction is this neighbour? match runtime offset */
            int32_t du = lat->site_ijk[3 * n + 0] - lat->site_ijk[3 * v + 0];
            int32_t dv = lat->site_ijk[3 * n + 1] - lat->site_ijk[3 * v + 1];
            int32_t dw = lat->site_ijk[3 * n + 2] - lat->site_ijk[3 * v + 2];
            int dir_idx = -1;
            for (int32_t d = 0; d < S->ndir; ++d) {
                const SurrDir *D = &S->dirs[d];
                if (D->ru_dir == du && D->rv_dir == dv && D->rw_dir == dw) { dir_idx = d; break; }
            }
            if (dir_idx < 0) continue;
            /* de-dup vs the measured channel */
            if (as && pylatkmc_measured_covers_hop(lat, st, as, v, n)) continue;

            SurrEval ev;
            if (surrogate_eval(S, lat, st, v, dir_idx, sp, T_K,
                               ctx->k_floor, ctx->lev_gate, &ev) != 0) continue;
            if (ctx->n_cand >= ctx->cap_cand) {
                int32_t nc = ctx->cap_cand * 2;
                SurrCandidate *p = realloc(ctx->cand, (size_t)nc * sizeof *p);
                if (!p) break;
                ctx->cand = p; ctx->cap_cand = nc;
            }
            SurrCandidate *c = &ctx->cand[ctx->n_cand++];
            c->vac_site = v; c->neigh_site = n; c->dir_idx = dir_idx;
            c->atom_sp = sp; c->k = ev.k; c->ea_hat = ev.ea_hat;
            c->leverage = ev.leverage; c->trigger = ev.trigger | SURR_TRIG_FLUX;
            ctx->surr_rtot += ev.k;
        }
    }
    return ctx->surr_rtot;
}

int32_t surrogate_select(const SurrCtx *ctx, double target)
{
    double acc = 0.0;
    for (int32_t i = 0; i < ctx->n_cand; ++i) {
        acc += ctx->cand[i].k;
        if (target < acc) return i;
    }
    return ctx->n_cand > 0 ? ctx->n_cand - 1 : -1;
}

int surrogate_apply(SurrCtx *ctx, State *st, const Lattice *lat, int32_t idx,
                    int32_t *v_origin, int32_t *v_dest)
{
    (void)lat;
    if (idx < 0 || idx >= ctx->n_cand) return -EINVAL;
    SurrCandidate *c = &ctx->cand[idx];
    /* atom at neigh_site hops into the vacancy vac_site (species swap). */
    StateAction acts[2];
    acts[0].site = c->vac_site;   acts[0].before = SP_VACANT;   acts[0].after = c->atom_sp;
    acts[1].site = c->neigh_site; acts[1].before = c->atom_sp;  acts[1].after = SP_VACANT;
    int rc = state_apply_actions(st, acts, 2, SP_VACANT);
    if (rc != 0) return rc;
    if (v_origin) *v_origin = c->vac_site;   /* vacancy originates here */
    if (v_dest)   *v_dest   = c->neigh_site; /* and moves to the atom's old site */
    return 0;
}

void surrogate_note_measured(SurrCtx *ctx, double v6_ea, double ea_fired)
{
    if (!ctx->enabled) return;
    ctx->n_meas_fired++;
    if (isnan(v6_ea)) return;
    double r = fabs(v6_ea - ea_fired);
    ctx->v6_absresid_sum += r;
    if (r > ctx->v6_absresid_max) ctx->v6_absresid_max = r;
    ctx->v6_n++;
}

double surrogate_v6_mean(const SurrCtx *ctx)
{
    return ctx->v6_n ? ctx->v6_absresid_sum / (double)ctx->v6_n : 0.0;
}

void surrogate_account(SurrCtx *ctx, const Lattice *lat, int32_t fired_idx,
                       double dt, double k_total)
{
    if (!ctx->enabled) return;
    double k_flag = ctx->surr_rtot;
    ctx->flux_flag_cum += k_flag * dt;
    ctx->flux_total_cum += k_total * dt;
    ctx->last_k_flag_inst = k_flag;
    ctx->last_k_total_inst = k_total;
    ctx->last_n_cand = ctx->n_cand;
    /* flux-share trigger + registry bookkeeping over live candidates. */
    for (int32_t i = 0; i < ctx->n_cand; ++i) {
        SurrCandidate *c = &ctx->cand[i];
        SurrFlag *f = flag_lookup(ctx, c->vac_site, c->neigh_site, c->dir_idx);
        if (!f) continue;
        if (f->n_enrolled_steps == 0) {
            const int16_t *ijk = &lat->site_ijk[3 * c->vac_site];
            f->ru = ijk[0]; f->rv = ijk[1]; f->rw = ijk[2];
            f->sp_a = SP_VACANT; f->sp_b = c->atom_sp;
        }
        f->n_enrolled_steps++;
        f->carried_flux += c->k * dt;
        f->last_ea_hat = c->ea_hat;
        f->last_leverage = c->leverage;
        uint32_t trig = c->trigger;
        if (k_flag > 0.0 && (c->k / k_flag) > ctx->flux_threshold) trig |= SURR_TRIG_FLUX;
        else trig &= ~SURR_TRIG_FLUX;
        f->trigger_or |= trig;
    }
    if (fired_idx >= 0 && fired_idx < ctx->n_cand) {
        SurrCandidate *c = &ctx->cand[fired_idx];
        SurrFlag *f = flag_lookup(ctx, c->vac_site, c->neigh_site, c->dir_idx);
        if (f) f->n_fired++;
        ctx->n_surr_fired++;
    }
}

#endif /* PYLATKMC_HAS_SURROGATE */
