# Phase C first-leg validation report — H(σ) + E_sym fits, gates V1–V5 (+V4)

**Written:** 2026-07-21, Claude Fable 5 (first Phase C leg, per handoff).
**Scope:** offline only — the two models the approved architecture consumes
(`PHASEC_RATE_MODEL_DECISION.md` §1, §8) now exist as versioned artifacts, and every gate has a
measured verdict. No runtime/codegen work was done. **Gate outcomes: V1 FAIL, V2 FAIL (raw-pairs
regime stands, §8-N6), V3 FAIL (expected; now quantified end-to-end), V4 PASS, V5 PARTIAL.**

**Conditions stamp (applies to every number unless overridden inline):** production NiCr
`verify_fix_T500_1vac` ingest, rcut 8.5 Å, Linux box; 439 classes / 445 harvested events
(433 singletons), **222 forward/backward pair groups**; T_ref = 500 K (kT = 0.0431 eV);
holdout = 10-fold CV split **by pair group** (fwd/bwd of one physical pair share a fold — a
class-level split would leak the E_sym target, which is identical for the two directions),
nested α selection; ±0.02–0.05 eV a-priori sampling noise on all barriers.
Direct-evaluation channel: production potential `Clusters/Research/NiFeCr_LKB2017.eam`
(eam/alloy, type order **Cr Ni**), production minimizer (cg, 1e-10 1e-12), FCC(001) slab
7×7×8 cells @ a0 = 3.524 Å (production box constant) + 22 Å vacuum, deterministic seed 20260721.

Evidence tiers used throughout: **[measured]** (this leg, conditions as stamped) >
**[extrapolated]** (fit through measured points) > **[assumed]** (carried from memo/a-priori).

---

## 0. Reproduction of the sign-off baselines — exact

`ridge_anchor_2026-07-21.py` and `v3_tail_check_2026-07-21.py` reproduce memo §2 and §8-N7 to
the third decimal [measured]: static φ 0.451/0.354/0.552/0.558/0.491 eV (all/clean/multi/Cr/tail),
×414 median rate error, in-sample 0.377; KRA-informed full corpus 0.295 eV; V3 baselines
static +0.377 eV / 95% / 0.567 (Cr 0.287), KRA +0.155 eV / 77% / 0.709 (Cr 0.319), full-pop
Spearman 0.575 / 0.804.

**Split-leakage check** [measured]: the memo's numbers used class-level CV; re-run under the
honest pair-group split the KRA-informed clean-hop fit is 0.163 eV (pair split) vs 0.165 (class
split) vs 0.175 (memo, different feature symmetrization). The fwd/bwd leakage was negligible —
the memo's baselines stand.

## 1. Artifacts produced (versioned)

| Artifact | Version stamp | File (this directory) |
|---|---|---|
| H(σ) channel A (harvested-only, pair basis) | `H_sigma_v1_pair12` | `H_sigma_theta_2026-07-21.csv` |
| H(σ) headline (surfsplit basis + direct evals) | `H_sigma_v2_surfsplit_aug` | `H_sigma_v2_theta_2026-07-21.csv` |
| E_sym ridge tier (symmetrized ≤2-body + 3-body triangles, 68 feats) | `E_sym_v1_ridge_sym2b3b` | `esym_holdout_pred_2026-07-21.csv` (per-event holdout) |
| Direct same-potential evaluations (N3 channel) | campaign v2, 244 evals | `direct_evals_v2_2026-07-21.csv` (+ superseded `direct_evals_2026-07-21.csv`, see §7) |
| V4 per-pair prefactor measurements | 21 pairs | `v4_prefactor_results_2026-07-21.csv` |
| Fit/measure harness | — | `h_sigma_fit_2026-07-21.py`, `esym_v1v3v5_2026-07-21.py`, `direct_evals_v2_2026-07-21.py`, `v4_prefactor_2026-07-21.py` |

`nu0_pair_policy` named value for phaseA_contract §2.5: **`harvested_pair`** (tier 1, validated
by V4 below). H(σ) trains only on same-potential pyKMC data per §8-N3: harvested linked-pair dE
+ direct LAMMPS evaluations of constructed lattice configurations (no DFT/literature; the
non-conservative point terms `pt_NI`/`pt_CR` are constrained only by the harvested
projection-non-conserving events and mean "energy of an atom leaving the lattice
representation", not a vacuum chemical potential — documented model semantics, not a bug).

## 2. V2 — ΔE channel error → **FAIL; N6 switch verdict: raw-pairs regime stands**

Holdout |ΔE_H − dE_pair| over the 445 linked pairs (pair-group CV, quarantine of 23 events
excluded where noted; see §6) [measured]:

| H model / training | median | q75 | q90 | clean hops | multi-site |
|---|---|---|---|---|---|
| v1 pair12, harvested only | 0.367 | 0.769 | 1.034 | 0.269 | 0.553 |
| v2 surfsplit, harvested only | 0.406 | 0.773 | 1.014 | 0.286 | 0.532 |
| v1 pair12, + 244 direct evals | 0.375 | 0.807 | 1.043 | 0.281 | 0.581 |
| **v2 surfsplit, + direct (headline)** | **0.390** | 0.772 | 1.051 | 0.283 | 0.557 |

**The measured pair-noise scale** (the §8-N6 switch criterion) has three channels, reported
separately because they disagree:
- Within-class barrier repeatability [measured, n = 6 duplicate classes only]: Ea spread
  2–8 meV — barrier measurement itself is very repeatable.
- A-priori sampling noise [assumed, memo conditions]: 0.02–0.05 eV.
- Within-class **dE** spread [measured, same 6 duplicates]: 4 of 6 show 0.38–0.77 eV — see §6;
  this is context-underresolution, not measurement noise.

**Verdict:** median |ΔE_H − dE_pair| = 0.39 eV is **~8–20× above the 0.02–0.05 eV noise band**.
The N6 staged switch does **not** fire: measured classes keep firing raw harvested pairs at
Phase C entry. No anchored-form migration.

Two structural findings behind the number [measured]:
1. **The direct-eval augmentation does not reduce harvested-pair error** (0.367→0.375 v1;
   0.406→0.390 v2), although on the noise-free direct data itself the bases achieve
   0.096 eV (v1) / **0.050 eV** (v2 surfsplit) 5-fold CV. The dominant V2 error is therefore
   *not* fitting noise or basis capacity on lattice configurations — it is that harvested
   dE_pair contains off-lattice relaxation content that no function of the local σ can see.
2. **Direct proof of an irreducible floor:** 4 of the 6 duplicate classes (identical full
   rcut-8.5 context, i.e. identical σ) have members whose measured dE differs by 0.38–0.77 eV.
   No σ-function can split them. V2's error on this corpus is bounded below by projection
   underresolution of the ΔE channel — remedy is projection/identity work (gap-2 territory) or
   more context, not more H training data. (§8-N3's "remedy is more same-potential data" is
   measured to be insufficient *alone* for this corpus.)

The surfsplit basis is still the right H for the *on-lattice* energetics (halves the
representation floor on clean lattice configurations: 0.096 → 0.050 eV CV, and its zero-ΔΦ
degeneracies are strictly fewer); it is stamped as the headline `dE_model_version`.

## 3. V1 — learning curve → **FAIL; acceptance unreachable by data volume alone (this basis)**

E_sym (`E_sym_v1_ridge_sym2b3b`) holdout, pair-group CV [measured]:
all events 0.305 eV (null 0.467, Spearman 0.730); clean hops 0.217; multi-site 0.383;
Cr movers 0.324; clean-hop-only-trained variant 0.163 eV.

Learning curve, corpus-wide refit, clean-hop holdout RMSE (10 replicates per N) [measured]:
0.306 (N=100) → 0.217 (N=200) → 0.227 (N=300) → 0.218 ± 0.049 (N=445). The curve is flat
beyond N ≈ 200.

Extrapolation RMSE(N) = √(floor² + k/N) [extrapolated]: **floor = 0.171 eV**, i.e. the
0.10 eV clean-hop acceptance is **not reachable at any N with this feature basis on this
event population** — consistent with the memo's in-sample saturation argument (§2.1) and the
0.163 eV clean-hop-trained floor. Distance to gate: current 0.218/0.10 = 2.2×; asymptotic
0.171/0.10 = 1.7×. The tail-bias half of V1's acceptance also fails (V3 below).
Consequence (by the memo's own design): surrogate-rated flux keeps its on-the-fly routing;
rate authority does not shift. Unlocking V1 requires a richer E_sym (denser 3-body/GP tier)
*and* a cleaner/larger corpus — not more of the same corpus.

## 4. V3 — tail gate on the full runtime-form surrogate → **FAIL (9.2× kT), quantified**

Full surrogate Ea_hat = E_sym_hat + ½·ΔE_H_hat, both factors holdout on shared folds
[measured]; tail = lowest-quartile measured Ea (n = 112); thresholds: |bias| < kT = 0.0431 eV
AND tail Spearman > 0.9 (verbatim, no noise-ceiling clause — §8-N7):

| surrogate | tail signed bias | over-pred | tail Spearman | Cr-mover tail (n=47) | full-pop Spearman |
|---|---|---|---|---|---|
| E_sym + ½ΔE_H (v1/harvested) | +0.413 eV (9.6× kT) | 84% | 0.172 | +0.492, Sp −0.335 | 0.654 |
| **E_sym + ½ΔE_H (v2+direct, headline)** | **+0.397 eV (9.2× kT)** | 82% | **0.235** | +0.464, Sp **−0.308** | 0.660 |
| reference: E_sym + ½·dE_measured | +0.193 eV (4.5× kT) | — | 0.684 | — | (full RMSE 0.305) |
| baseline (memo, KRA + measured ΔE, class split) | +0.155 eV (3.6× kT) | 77% | 0.709 | Sp 0.319 | 0.804 |

Both V3 conditions fail. Three reads [measured]:
- The H-predicted ΔE makes the tail **worse** than the measured-ΔE baseline (bias 0.155 → 0.40;
  Spearman 0.71 → 0.24): V2's error lands disproportionately on the low-barrier tail.
- The Cr-mover tail Spearman is **negative** (−0.31): within the dealloying-critical
  subpopulation the surrogate currently anti-ranks candidates.
- Per the memo's design intent this is the safe outcome: at Phase C entry the low-barrier tail
  routes through the on-the-fly channel *by design*. This report records distance, not
  disappointment: bias must fall 9.2× and tail rank correlation roughly quadruple before any
  tail flux may be surrogate-rated.

## 5. V4 — prefactor asymmetry → **PASS (N4 tier-1 policy validated)**

21 pairs sampled (stratified: barrier quartile × mover species) from the 213 symmetric
finite-ν0 pairs in `reference_table.pickle`; per-state ∏ω(min1)/∏ω(min2) computed with
**pyKMC's own HTST machinery** (`select_free_indices`/`mass_weighted_partial_hessian`/
`vineyard_prefactor`, editable install = `SK_basin_htst_binary`), production settings
(free_radius 6.0 → n_free 45–49, fd_step 0.01) [measured]:

- Harvested cross-row ν0_f/ν0_b vs per-state ratio: **median deviation ×1.01, q90 ×1.02,
  max ×1.06; 100% within ×2; corr(ln,ln) = 1.000.** The saddle-cancellation identity holds in
  the harvested data even though ν0_f and ν0_b come from separate searches.
- Harness validation: recomputed ν0_f vs stored = ×0.98–1.01 (q10–q90) — the vacuum-cluster
  truncation (stored ~130-atom active-volume clusters, frozen periphery, no full slab) is a
  ≤2% effect on ν0 and cancels further in the ratio. Conditions caveat stamped.
- The asymmetry itself is real physics, not noise: per-state ratio q10–q90 = 0.91–9.3 (max ×21
  in-sample), confirming §2.4's "ν0_f = ν0_b is false" from state properties alone.

**Verdict:** firing harvested per-pair Vineyard ratios (N4 tier 1) is measured to be per-state
consistent and hence DB-safe as designed. The surrogate channel's tier-0 (`Δln Z_vib = 0`,
per-tier constant) still carries the acknowledged ×11 band — unchanged, and now confirmed to be
systematically barrier-correlated (high-barrier pairs show the largest asymmetry).

## 6. V5 — OOD-gate calibration → **PARTIAL PASS (fires preferentially, coverage incomplete)**

Ridge leverage in the E_sym feature space, holdout [measured]:
- Spearman(leverage, |err|) = 0.33 (n = 422); mean |err| above/below the q75 leverage gate:
  0.370 vs 0.163 eV (**2.3× separation**).
- The gate fires on the worst-fit subpopulation preferentially: 40% of Cr-mover events above
  the q75 gate vs 20% of Ni-only (2× enrichment; Cr median leverage 0.109 vs 0.081).
- Leave-out-Cr-rich probe (train on local-Cr ≤ q80, n = 347; held-out Cr-enriched n = 75; gate
  = train-leverage q95): held-out median leverage 0.306 (≈ train q90+), **32% above the gate**;
  gate-fired events err 0.442 eV vs 0.234 eV for silent ones.

**Verdict:** the M2 leverage mechanism is directionally valid — it enriches on exactly the
population the dealloying guard needs and its firing predicts elevated error. But at this
corpus size it catches only ~⅓ of a genuinely Cr-enriched held-out population while the silent
⅔ still carry ~0.23 eV error. As sole OOD authority it under-covers; §8-N1's fallback (revisit
ensemble disagreement if leverage proves insufficient) now has measured cause to stay on the
table. Recommended for the implementation leg: pair the leverage gate with the species-count
trigger (§6.4 already includes it) and treat gate-silent Cr-rich flux as still-flagged until V1
moves.

## 7. Corpus-integrity findings (new; feed to ingest QC and gap-2 triage)

All [measured] on this catalogue:
1. **14 classes with broken pair reciprocity** (|dE_f + dE_b| up to 0.774 eV, incl. two
   self-linked classes with dE ≠ 0 — thermodynamically impossible for a true self-reverse).
   These are mis-links or projection artifacts. Quarantined here (with the 3 delta-less
   classes: 23 events total; headline numbers change only in the third decimal).
2. **4 of 6 duplicate classes have within-class dE spread 0.38–0.77 eV at 2–8 meV Ea spread** —
   the ΔE channel is context-underresolved at identical full-context identity (§2's V2 floor).
3. dE and barrier reciprocity are **enforced by construction** in the ingest (median residual
   exactly 0), so reciprocity cannot serve as an independent noise gauge; only duplicates and
   a-priori noise can.
4. Recommended ingest QC additions: reciprocity screen (|dE_f + dE_b| > tol → audit),
   within-class dE-spread screen (complementing the existing Ea-based `split_tol`), and a
   self-link sanity check (self-reverse ⇒ dE ≡ 0).
5. Campaign v1 (`direct_evals_2026-07-21.csv`, 178 evals) is superseded: RNG seeded from
   salted `hash()` (not reproducible) and configurations not recorded. Kept as record; all
   conclusions use campaign v2 (deterministic, occupation signatures recorded).

## 8. What this means for the implementation leg (summary)

- **Rate authority at Phase C entry is exactly as the memo designed for the failing-gates
  branch:** measured classes fire raw harvested pairs (+ per-pair ν0, validated); the
  surrogate rates only unflagged lattice-representable flux; the low-barrier tail and
  Cr-enriched/out-of-hull environments route on-the-fly. Nothing in this leg licenses
  loosening any of that.
- **V2's failure is structural, not statistical** — driven by off-lattice relaxation content
  in harvested dE (projection underresolution), so the N6 migration should not be expected to
  unlock from H-side improvements alone; it now depends on gap-2/projection work. This is a
  sharper statement than the memo's (which budgeted V2 as model error).
- **V1's floor (0.171 eV ≫ 0.10) means the learning-curve gate cannot be passed by harvesting
  more of the same** — basis enrichment (GP tier / deeper 3-body) plus corpus cleaning are
  prerequisites for any future rate-authority shift.
- **V4 closes N4 tier 1**: `nu0_pair_policy = harvested_pair` is safe to implement as specified.
- **V5 supports M2 as a flag source, not as sole authority** — keep the species-count and
  flux-threshold triggers co-equal (§6.4), and log the flagged-flux fraction from day one.

## 9. Reproduction record

```
source ~/pykmc/pykmc_env/bin/activate && cd ~/pykmc/pylatkmc     # never the meta-root
python ~/pykmc/onlattice_design/ridge_anchor_2026-07-21.py        # memo §2 baselines
python ~/pykmc/onlattice_design/v3_tail_check_2026-07-21.py       # §8-N7 baselines
python ~/pykmc/onlattice_design/direct_evals_v2_2026-07-21.py     # 244 evals, ~35 s, deterministic
python ~/pykmc/onlattice_design/h_sigma_fit_2026-07-21.py         # H channel A + V2_A (v1 basis)
python ~/pykmc/onlattice_design/esym_v1v3v5_2026-07-21.py         # E_sym + V1 + V2 (4 variants) + V3 + V5
python ~/pykmc/onlattice_design/v4_prefactor_2026-07-21.py        # V4, ~15 s, 21 pairs
```
The esym/V-gate script consumes `direct_evals_v2_2026-07-21.csv` if present (headline numbers);
without it, only the harvested-only H variants run. sklearn is not in the venv — all numpy.
