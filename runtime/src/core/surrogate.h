#ifndef PYLATKMC_SURROGATE_H
#define PYLATKMC_SURROGATE_H

#include <stdint.h>

#include "lattice.h"
#include "state.h"
#include "avail_sites.h"

/* Phase C surrogate rate channel (b) — see pylatkmc/surrogate_codegen.py.
 *
 * The generated proclist.c bakes the E_sym model + per-1NN-direction feature
 * tables into instances of the structs below and exports a single const
 * `pylatkmc_surrogate`. This header carries the exact struct layout so both the
 * generated TU (proclist.c) and this runtime TU (surrogate.c) agree — like the
 * RateConst duplicate-typedef contract, the layout MUST stay in lockstep with
 * surrogate_codegen.emit_surrogate_tables.
 *
 * The whole channel compiles out unless the generated proclist.h defines
 * PYLATKMC_HAS_SURROGATE (i.e. a model was baked); v0.3 / no-model builds get an
 * empty translation unit. */

/* SURR_NPHI is len(pylatkmc.ingest.surrogate.ESYM_FEATURE_KEYS) — the CLOSED v2
 * basis over the six-category alphabet {C,E,F,N,U,W}: 6 scalars + 60 shell counts
 * + 10 bonds + 18 mover-neighbour + 21 triangles. SURR_NH2 is the (unchanged)
 * H(sigma) v2 surfsplit basis. Both are cross-checked in Python by
 * test_surrogate_index_layout / test_surrogate_parity. */
#define SURR_NPHI 115
#define SURR_NH2  18

/* One context-ball site (offsets/shells baked relative to the vacancy). */
typedef struct {
    int8_t  ru, rv, rw;       /* runtime-frame offset from the vacancy site */
    uint8_t shell_n, shell_v; /* crystal shell (0..9) from the atom / vacancy end */
    int8_t  ck;               /* crystal k component (depth layer distances) */
    uint8_t near_n, near_v, near_mid; /* within rcut+0.25h of atom / vac / midpoint */
} SurrSite;

/* One of the 12 crystal 1NN hop directions. Index lists reference the sorted
 * `sites` ball; index order == crystal-offset lex order (the dphi2 j<i dedup). */
typedef struct {
    int32_t n_sites;
    const SurrSite *sites;
    const int16_t  *nn1_adj;      /* [n_sites*12] ball index or -1 */
    const int16_t  *nn2_adj;      /* [n_sites*6]  ball index or -1 */
    int32_t n_bond;
    const int16_t  *bond_i, *bond_j;
    int32_t vac_idx, atom_idx;    /* ball indices of the two mover sites */
    int8_t  ru_dir, rv_dir, rw_dir; /* runtime offset of the atom from the vacancy */
    int32_t n_vac_nbr;
    const int16_t *vac_nbr;       /* ball indices of the vacancy's in-ball 1NN */
    const int8_t  *vac_nbr_o;     /* [n_vac_nbr*3] their crystal offsets */
    int32_t n_atom_nbr;
    const int16_t *atom_nbr;
    const int8_t  *atom_nbr_o;
    int32_t n_vac_tri;
    const int16_t *vac_tri;       /* [n_vac_tri*2] NN1 pairs among vac_nbr */
    int32_t n_atom_tri;
    const int16_t *atom_tri;
    int32_t n_aff;
    const int16_t *aff;           /* affected set (1NN of movers, not movers) */
} SurrDir;

/* The baked model container. */
typedef struct Surrogate {
    int32_t nphi, nh2, ndir;
    const double *mu, *sd, *w, *ainv, *h2_theta;
    double ym, tier0_nu0_hz, lev_q75, ea_lo, ea_hi;
    /* Trained clean-hop context count ranges (the unseen-composition trigger).
     * F is baked as [0,0] by an all-NiCr corpus, which flags every runtime Fe
     * context — intended (dE_H has no Fe terms). There is deliberately NO W
     * range: W is harvest-side only, so a W floor would flag everything. */
    int32_t ctx_n_lo, ctx_n_hi, ctx_c_lo, ctx_c_hi, ctx_e_lo, ctx_e_hi,
            ctx_f_lo, ctx_f_hi;
    const SurrDir *dirs;
} Surrogate;

/* ---- trigger bitmask (per surrogate instance) ---- */
#define SURR_TRIG_LEVERAGE 0x1u  /* leverage > gate */
#define SURR_TRIG_SPECIES  0x2u  /* an N/C/F/E context count outside the trained range */
#define SURR_TRIG_FLUX     0x4u  /* integrated-flux share > flux_threshold */
#define SURR_TRIG_CLAMP    0x8u  /* Ea_hat out of the model's clamp range */

/* Result of evaluating one candidate hop. */
typedef struct {
    double phi[SURR_NPHI];
    double e_sym;
    double dE_H;
    double ea_hat;       /* E_sym + 0.5*dE_H, before clamp */
    double ea_clamped;   /* clamped into [ea_lo, ea_hi] */
    double leverage;
    double k;            /* tier0_nu0 * exp(-ea_clamped/kT), floored */
    uint32_t trigger;    /* bitmask (flux bit set later during accounting) */
    int32_t n_ctx, c_ctx, e_ctx, f_ctx; /* N/C/E/F counts (before/midpoint map) */
} SurrEval;

/* Evaluate a candidate: vacancy at `vac_site`, atom (`atom_sp` = SP_NI/SP_CR/SP_FE)
 * at its 1NN reached by direction `dir_idx` (0..11), hopping into the vacancy.
 * Fills `out` (phi/e_sym/dE/ea/leverage/k/trigger). `k_floor` (>0) floors k;
 * `lev_gate` is the leverage trigger threshold. Returns 0, or -EINVAL. */
int surrogate_eval(const Surrogate *S, const Lattice *lat, const State *st,
                   int32_t vac_site, int32_t dir_idx, uint8_t atom_sp,
                   double T_K, double k_floor, double lev_gate, SurrEval *out);

/* ---- runtime channel state (per replica) ---- */

/* One live surrogate candidate this step. */
typedef struct {
    int32_t vac_site, neigh_site, dir_idx;
    uint8_t atom_sp;
    double  k, ea_hat, leverage;
    uint32_t trigger;
} SurrCandidate;

/* Deterministic fixed-capacity flag registry keyed by (min(site),max(site),dir). */
typedef struct {
    int32_t site_a, site_b, dir_idx; /* site_a < site_b (undirected key) */
    uint8_t used;
    uint64_t n_enrolled_steps, n_fired;
    double   carried_flux;           /* Σ k*dt */
    uint64_t first_step;
    double   last_ea_hat, last_leverage;
    uint32_t trigger_or;
    int32_t  ru, rv, rw;             /* runtime ijk of site_a (for the report) */
    uint8_t  sp_a, sp_b;
} SurrFlag;

typedef struct SurrCtx {
    const Surrogate *model;
    /* config */
    int      enabled;
    double   k_floor;
    double   lev_gate;
    double   flux_threshold;
    int32_t  capacity;
    /* per-step candidate list */
    SurrCandidate *cand;
    int32_t n_cand, cap_cand;
    double  surr_rtot;
    /* registry */
    SurrFlag *flags;
    int32_t   n_flags;
    /* accounting */
    double   flux_flag_cum;   /* Σ over steps of k_flag * dt */
    double   flux_total_cum;  /* Σ over steps of k_total * dt */
    uint64_t n_surr_fired, n_meas_fired;
    double   v6_absresid_sum; /* Σ |v6_ea - Ea_fired| over measured fires */
    double   v6_absresid_max;
    uint64_t v6_n;
    /* last-step instantaneous values (for phasec.out) */
    double   last_k_flag_inst, last_k_total_inst;
    int32_t  last_n_cand;
} SurrCtx;

/* Lifecycle. `model` may be NULL (channel disabled). */
int  surrogate_ctx_init(SurrCtx *ctx, const Surrogate *model, int32_t n_sites,
                        int enabled, double k_floor, double lev_gate,
                        double flux_threshold, int32_t capacity, double T_K);
void surrogate_ctx_free(SurrCtx *ctx);

/* Rebuild the candidate list for the current state (after the pattern scan).
 * `as` is used to skip candidates already covered by an enrolled measured proc
 * (via the generated pylatkmc_measured_covers_hop). Returns Σ surrogate k. */
double surrogate_rebuild(SurrCtx *ctx, const Lattice *lat, const State *st,
                         const AvailSites *as, double T_K);

/* BKL: pick a candidate given a target in [0, surr_rtot). Returns index or -1. */
int32_t surrogate_select(const SurrCtx *ctx, double target);

/* Apply candidate `idx`: swap the atom into the vacancy, keeping the state
 * triple + MSD bookkeeping. Fills v_origin/v_dest (like a measured HopOutcome). */
int surrogate_apply(SurrCtx *ctx, State *st, const Lattice *lat, int32_t idx,
                    int32_t *v_origin, int32_t *v_dest);

/* Per-step flux/registry accounting after selection. `fired_idx` is the chosen
 * surrogate candidate (or -1 if a measured proc fired). `dt` advances flux;
 * `k_total` = pattern r_tot + surrogate r_tot. */
void surrogate_account(SurrCtx *ctx, const Lattice *lat, int32_t fired_idx,
                       double dt, double k_total);

/* Record one fired measured proc: bumps n_meas_fired and (if v6_ea is finite)
 * the V6 residual |v6_ea - Ea_fired|. */
void surrogate_note_measured(SurrCtx *ctx, double v6_ea, double ea_fired);

/* phasec.out row accessors (mean V6 residual = 0 when none). */
double surrogate_v6_mean(const SurrCtx *ctx);

#endif /* PYLATKMC_SURROGATE_H */
