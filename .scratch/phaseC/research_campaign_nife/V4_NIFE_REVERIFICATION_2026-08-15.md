# V4 re-verification — NiFe line (2026-08-15)

**Verdict: PARTIAL.** The V4 gate **as defined cannot be evaluated on NiFe with the data this slice
was allowed to touch** — its criterion compares the harvested cross-row ν₀ ratio against a
*recomputed per-state Vineyard ratio*, which requires LAMMPS Hessians. Every catalogue-side and
reference-table-side analogue that *can* be measured is consistent with the NiCr PASS **for the
77.4 % of NiFe harvested pairs that carry a real HTST ν₀** — and a new defect, invisible to the
July gate by construction, makes the per-state claim **false** for the remaining 22.6 %.

Scope: analysis only. No re-search, no graduation, no writes to `/data` or
`production_NiCrFe/runs/`. Conditions stamp: Linux box, 2026-08-15,
`pykmc_env` (py 3.12.3), pandas/numpy/scipy only; `pykmc.htst.free_region.select_free_indices`
used as a pure-geometry helper (no LAMMPS, no force calls).

---

## 1. The V4 gate as originally defined, and the NiCr result

### 1.1 Definition (verbatim, `onlattice_design/v4_prefactor_2026-07-21.py` docstring)

> ```
> V4 -- prefactor asymmetry: per-state Vineyard ratio vs harvested nu0_f/nu0_b.
>
> Memo 8-N4 fires harvested per-pair nu0_f/nu0_b as-is, claiming the ratio is a
> per-state quantity (prod omega(init) / prod omega(final); saddle cancels).
> The catalogue's nu0_f and nu0_b come from DIFFERENT reference rows (separate
> pARTn searches, own saddles/free sets), so the claim is only exact if the
> cross-row ratio matches the per-state ratio. This script measures both on a
> sample of harvested pairs using pyKMC's own HTST machinery
> (select_free_indices / mass_weighted_partial_hessian / vineyard_prefactor,
> editable install = SK_basin_htst_binary) with the production settings
> (free_radius=6.0, fd_step=0.01, Cr Ni eam/alloy).
>
> Per sampled pair (forward row F, backward row B = F.idx_backward):
>   R_harv   = nu0(F) / nu0(B)                      [cross-row, what N4 fires]
>   R_state  = prod omega(F.min1) / prod omega(F.min2)   [single row, one free set]
>   nu0_f_re = vineyard(F.min1, F.saddle)           [harness validation vs F.nu0]
> ```

The acceptance statistic is `|ln R_state − ln R_harv|`, reported as a multiplicative factor, with
"within ×2" as the stated pass band and `corr(ln R_state, ln R_harv)` as a supporting measure.

### 1.2 The NiCr result, 2026-07-21 (verbatim, `PHASEC_VALIDATION_REPORT_2026-07-21.md` §5)

> ## 5. V4 — prefactor asymmetry → **PASS (N4 tier-1 policy validated)**
>
> 21 pairs sampled (stratified: barrier quartile × mover species) from the 213 symmetric
> finite-ν0 pairs in `reference_table.pickle`; per-state ∏ω(min1)/∏ω(min2) computed with
> **pyKMC's own HTST machinery** … production settings (free_radius 6.0 → n_free 45–49,
> fd_step 0.01) [measured]:
>
> - Harvested cross-row ν0_f/ν0_b vs per-state ratio: **median deviation ×1.01, q90 ×1.02,
>   max ×1.06; 100% within ×2; corr(ln,ln) = 1.000.** …
> - Harness validation: recomputed ν0_f vs stored = ×0.98–1.01 (q10–q90) …
> - The asymmetry itself is real physics, not noise: per-state ratio q10–q90 = 0.91–9.3 (max ×21
>   in-sample), confirming §2.4's "ν0_f = ν0_b is false" from state properties alone.
>
> **Verdict:** firing harvested per-pair Vineyard ratios (N4 tier 1) is measured to be per-state
> consistent and hence DB-safe as designed.

Source corpus: `production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle`, 445 rows, T_ref
500 K, single run. Per-pair artifact: `onlattice_design/v4_prefactor_results_2026-07-21.csv`
(21 rows).

---

## 2. Applicability to NiFe — the self-check, up front

**The gate is not evaluable as defined, for two independent reasons.**

1. **`R_state` is not in the catalogue.** It is a Hessian quantity (∏ω over 47–49 free atoms at two
   minima), obtainable only by re-running `mass_weighted_partial_hessian` under LAMMPS with the
   production EAM potential. This slice was scoped to pandas/pyarrow; per the hard rule I did the
   catalogue-side portion only. *Which portion I could not mirror:* the entire `R_state` channel and
   the `nu0_f_re` harness-validation channel — i.e. both of V4's two measured quantities.
2. **The premise is genuinely non-trivial, so no structural argument substitutes for the
   measurement.** I verified directly (§5) that the forward and backward reference rows do **not**
   share a cluster: different atom counts, different index orders, different mover indices, and
   **free regions that overlap only ~71 %**. The saddle *geometry* is bitwise identical between the
   two rows, but ~29 % of the Vineyard saddle block is evaluated over different atoms, so the
   cancellation is approximate, not exact. That residual is exactly what V4's ×1.01/×1.06 number
   quantified — and it can only be quantified with Hessians.

The parent brief's paraphrase of V4 — *"harvested ν₀ pairs are per-state, not family aggregates"* —
**is** evaluable catalogue-side, and is a weaker but non-vacuous claim (it excludes ν₀ being a
class/family constant, which is the failure mode Phase C's per-member `RateConst` emission would
launder). §3 and §4 measure that claim like-for-like. Read §2 of this report as: *gate NOT
EVALUATED as defined; nearest measurable analogue measured, with one hard failure.*

### 2.1 The object under test

`/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/merged_v3_NiFe_graduated_2026-08-15.parquet`
— 20,293 classes, of which **180** carry `nu0_pair_policy == "harvested_pair"`.

| | value |
|---|---|
| measured classes | 180 (Fe-mover **153**, Ni-mover **27**; all single-arrow) |
| harvested ν₀ pairs (members) | **936** (Fe-mover classes hold 400, Ni-mover classes hold 536) |
| `pair_status` | `linked` 180/180; `self_reverse` 0; unpaired members **0** (936/936 finite `nu0_b`) |
| `audit_status` | pending 111, approved 69 |
| `t_ref_K` | 300 (17) / 400 (5) / 500 (21) / 600 (53) / 700 (45) / 800 (39) |
| member barriers | 0.2501 – 0.8753 eV (quartiles 0.648 / 0.780 / 0.822) |

Note the **conditions gap vs NiCr V4**: the July gate sampled one 500 K run across barriers
0.62–2.27 eV; the NiFe measured set is 60 runs at six temperatures but is barrier-homogeneous
(0.25–0.88 eV — the vacancy-hop workhorse, campaign caveat §6.6). Any comparison of *asymmetry
magnitude* between the two lines is confounded by that.

---

## 3. The NiFe measurement, like-for-like

### 3.0 A blocking discovery: 22.6 % of the harvested pairs are not HTST ν₀ at all

`event_projection._resolve_nu0_hz` falls back to `k_prefactor × 1e12` when a reference row has no
HTST `nu0`. For pyKMC's default `k0 = 1.0 ps⁻¹` that yields **exactly 1.0e12 Hz** — a placeholder,
not a Vineyard prefactor. Measured over the 936 members:

| | members | % |
|---|---|---|
| real HTST ν₀ **both** directions | **724** | 77.4 |
| k₀ placeholder (`ν₀_f = ν₀_b = 1.0e12` exactly) | **212** | 22.6 |
| mixed (one side placeholder) | **0** | — |

Confirmed at source: of 120 sampled members traced back to their reference rows, 33 had
`nu0 is None` with `k_prefactor = 1.0`, and in **33/33** the backward partner row was also `None`
(HTST is skipped per event-pair, so the placeholder always arrives in pairs — which is why
`R ≡ 1` rather than a random ×50). Corpus-wide, the 60 NiFe reference tables hold 34,864 rows of
which 25,244 (72.4 %) have a finite HTST ν₀ and **9,620 (27.6 %) do not**.

For those 212 members the harvested pair asserts `ν₀_f/ν₀_b = 1` **identically**, while their
`dE_pair` spans ±0.446 eV (71 of them exceed 0.05 eV). That is precisely the *global-constant*
prefactor V4 exists to exclude — a strictly worse case than a family aggregate. **Every statistic
below is therefore reported on the 724 real-HTST members**, with the contaminated set treated as a
separate finding.

### 3.1 Cross-row ratio R = ν₀_f/ν₀_b — the statistic V4 reported as "the asymmetry itself"

Real-HTST members only (this is the NiFe counterpart of V4's "per-state ratio q10–q90 = 0.91–9.3,
max ×21"; on NiCr the harvested ratio equalled the per-state ratio to ×1.01, so the two are
comparable there — on NiFe that equality is assumed, not measured):

| population | n | min | q10 | median | q90 | max | geo-mean | \|ln R\| > ln 2 |
|---|---|---|---|---|---|---|---|---|
| **ALL** | 724 | 0.467 | 0.818 | 0.969 | 1.222 | 2.140 | 0.987 | 1.2 % |
| **Fe-mover** (153 cls) | 314 | 0.467 | 0.762 | 0.969 | 1.313 | 2.140 | 0.996 | 1.9 % |
| **Ni-mover** (27 cls) | 410 | 0.479 | 0.864 | 0.969 | 1.158 | 2.088 | 0.980 | 0.7 % |

Including the 212 placeholders the distribution collapses toward 1 artificially (q10 0.864,
median **exactly** 1.000, q90 1.158; 216 members at R = 1.000 exactly) — a second reason the
contamination must be reported, not averaged over.

**Comparison anchors** (same statistic, computed here for the first time):

| corpus | n real-HTST pairs | q10 | med | q90 | min | max | \|ln R\|>ln2 |
|---|---|---|---|---|---|---|---|
| NiFe measured (this report) | 724 | 0.818 | 0.969 | 1.222 | 0.467 | 2.140 | 1.2 % |
| NiCr production measured (`merged_v3_NiCr`, 32 cls / 289 mem) | 213 | 0.978 | 1.040 | 1.085 | 0.102 | 8.537 | 5.2 % |
| NiCr V4 sample (`verify_fix_T500_1vac`, 21 pairs) | 21 | 0.91 | — | 9.3 | — | ×21 | — |

NiFe's asymmetry is far narrower than NiCr's. That is a **population** effect, not a physics
disagreement: the ν₀ asymmetry is barrier/energy-driven (§3.3) and the NiFe measured set has no
high-barrier tail. Fe-mover pairs carry the wider tail of the two NiFe sub-populations.

### 3.2 Per-state vs family-aggregate — the paraphrased gate, measured

If the harvested pairs were a family aggregate relabelled per member, members of one class would
share a ν₀ value. They do not:

- **724 / 724 distinct `nu0_f` values** (100 %). Across the 64 classes with ≥2 real-HTST members,
  **zero** exact within-class duplicates.
- Within-class ν₀ variation is small but real: `nu0_f` max/min per class = ×1.013 median,
  ×1.097 q90, ×1.156 max. Within-class ratio `R` max/min = ×1.003 median, ×1.256 max.
- Across classes ν₀ spans **6.39 – 57.70 THz** (ln sd 0.489).
- Variance decomposition over the 64 multi-member classes:
  `ln ν₀_f` between-class sd **0.396** vs within-class sd **0.0129** → **within/between = 0.033**.
  For `ln R`: between 0.169, within 0.021 → 0.124.

Read: the class identity predicts ν₀ to ~1 %, i.e. the on-lattice class *is* a good ν₀ descriptor —
but the stored values are per-member measurements, not one number copied n times. The
family-aggregate hypothesis is falsified for all 724; it is **true by construction** for the 212
placeholders (all 212 carry the identical constant 1.0e12 Hz).

### 3.3 ν₀ asymmetry vs the energy asymmetry (state-property signature)

Not enforced by construction — `dE_pair = Ea_f − Ea_b` comes from the barrier channel, ν₀ from two
independent Hessian computations:

| population | n | Pearson(ln R, dE) | Spearman | slope | R² |
|---|---|---|---|---|---|
| NiFe real-HTST, all | 724 | **0.731** | 0.472 | **+1.559 /eV** | 0.534 |
| NiFe Fe-mover | 314 | 0.727 | — | +1.698 /eV | — |
| NiFe Ni-mover | 410 | 0.750 | — | +1.382 /eV | — |
| NiCr production measured | 213 | 0.984 | — | +1.783 /eV | — |

Positive slope = the higher-energy minimum is the softer one (smaller ∏ω), so R > 1 when dE > 0 —
the sign HTST predicts for a *state* quantity. **The two alloy lines agree on the slope to ~15 %**
(1.56 vs 1.78 per eV), which is the strongest like-for-like comparability result available without
Hessians. The 212 placeholder members sit at `ln R ≡ 0` against the same dE spread — off this line
by up to a factor 2.0 in the ratio the fit would predict.

---

## 4. Distributional checks

### 4.1 Forward/backward reciprocity of the ν₀ pairs vs the dE pairs — **enforced, not measured**

177 of the 180 measured classes have their `backward_class` present in the catalogue (156 of those
partners are themselves measured). Over all 177:

| quantity | result |
|---|---|
| \|ln R_fwd + ln R_bwd\| | ≤ **1.4e-16** (median 5.6e-17) — machine epsilon |
| \|dE_fwd + dE_bwd\| | **exactly 0** for all 177 |
| ν₀ multiset mirror (every fwd `nu0_f` appears as a bwd `nu0_b`) | **177/177** |
| classes with \|Σ ln R\| > 0.05 | **0** |

This is **construction, not evidence**: `build_class_catalogue` sets `nu0_b := partner.nu0_fwd_hz`
and `dE_pair := m.Ea_fwd − partner.Ea_fwd` (`event_class.py` ~L1262). Reciprocity therefore cannot
serve as an independent noise gauge on NiFe — exactly the finding NiCr §7.3 recorded ("dE and
barrier reciprocity are enforced by construction in the ingest … so reciprocity cannot serve as an
independent noise gauge"). Reported because the brief asked; it carries **zero** V4 information.
The one thing it does confirm is the *absence* of the NiCr §7.1 defect class: no NiFe measured class
shows broken pair reciprocity.

### 4.2 Spread within classes vs across classes

Covered numerically in §3.2. Companion figures for the same 64 classes: within-class `Ea` spread
median 0.53 meV / max 8.1 meV; within-class `dE` spread (all 69 multi-member classes, incl.
placeholders) median 0.19 meV / max 0.61 meV. The catalogue's G2 fold-in detector (`db_tol` 0.05 eV)
has ~80× headroom here — these classes are tight, and the ν₀ variation in §3.2 is not a fold-in
artifact.

### 4.3 Pathological members (listed individually where countable)

**(a) k₀-placeholder members — 212, the material defect.** Class-level breakdown:

| | classes | measured flux (firings) | % of measured flux |
|---|---|---|---|
| fully placeholder (every member ν₀ = 1e12) | **10** (8 Fe, 2 Ni) | 676 | 1.2 % (0.6 % of corpus) |
| partially contaminated | **46** (28 Fe, 18 Ni) | 39,254 | **70.0 %** |
| fully real HTST | 124 (117 Fe, 7 Ni) | 16,142 | 28.8 % |

Flux-weighted placeholder member fraction across the measured set: **18.9 %**.

Phase C emits one `RateConst` per member, so inside a partially contaminated class some emitted
procs carry 1 THz and their siblings ~50 THz at the same barrier. Taking the class rate as the sum
over members, the as-is rate vs the same class with placeholders replaced by the class's real-HTST
median ν₀: **median ×0.750, min ×0.269**; all 46 lose >10 %, 19 lose >30 %, 5 lose >50 %. Worst by
flux:

| class_id (16) | mover | placeholders | Ea_rep | corpus flux | k_as-is / k_repaired |
|---|---|---|---|---|---|
| `b4f4ceda979340fa` | Fe | 5/28 | 0.6110 | 8.44 % | 0.825 |
| `41ab56e07af137c7` | Fe | 5/28 | 0.5768 | 8.33 % | 0.826 |
| `1edeb41f3ffdba8d` | Fe | 14/42 | 0.6247 | 4.52 % | 0.677 |
| `df0efe62afd9f7d5` | Fe | 14/42 | 0.6235 | 3.76 % | 0.676 |
| `3d916077253024e1` | Fe | 1/4 | 0.6404 | 1.18 % | 0.752 |
| `ef7eed87336db10b` | Fe | 1/4 | 0.2688 | 1.13 % | 0.767 |
| `cab20a6975d3a954` | Fe | 1/3 | 0.6013 | 0.42 % | 0.665 |
| `18ffec260b71bd90` | Fe | 1/3 | 0.5975 | 0.36 % | 0.665 |

The two top-flux classes are the same `b4f4ceda…` / `41ab56e0…` pair that anchored the full-state
control arm (§8 of the campaign report) — i.e. the defect sits on the best-validated classes.
Highest-flux fully-placeholder classes: `e40e87481c8af178` (Fe, 0.09 % corpus),
`43ca8d657100dde2` (Fe, 0.08 %), `bb09fbc5982d166b` (Ni, 0.07 %), `925348170914e63c` (Fe, 0.06 %),
`ad7fbf7a67d09d70` (Ni, 0.06 %).

**(b) ν₀ above the ingest acceptance band.** `provenance.NU0_MIN_HZ/NU0_MAX_HZ = 1e12 … 5e13` (the
band the `recover` path gates on; the harvested-pair path is not gated by it). Of the 724 real-HTST
members, **110 (15.2 %) have `nu0_f` > 5e13** (max **5.770e13**) and 113 have `nu0_b` > 5e13. None
fall below 1e12. NiCr production measured: only 2/213 above the band (max 6.96e13). Not a physics
error — 58 THz is a legitimate Vineyard result for a stiff Fe-in-Ni hop — but it means the
harvested-pair channel routinely ships values the recovery channel would reject, an inconsistency
worth a policy line rather than a silent divergence.

**(c) Exactly-symmetric members — 4, benign.** Four members in three classes have
`nu0_f == nu0_b` bit-exactly with `dE = 0.0` exactly: `562a533097d2…` (1 member, 51.47 THz),
`5cb99912a626…` (2 members, 49.16 / 49.11 THz), `d43a1885e750…` (1 member, 49.03 THz). All three are
**self-linked** (`backward_class == class_id`) with `self_reverse = False`. dE = 0 is
thermodynamically consistent for a self-reverse, so these are *not* the NiCr §7.1 pathology
("two self-linked classes with dE ≠ 0 — thermodynamically impossible"). Flagged for completeness.

**(d) Largest asymmetries — none are outliers.** Top |ln R|: `5a59cd142d31` (Fe, R = 2.140,
dE +0.418), `6d6baac136de` (Ni, 2.088, +0.489), `3d9160772530` (Fe, 2.045, +0.379),
`350f950fa5ec` (Ni, 2.024, +0.348), and their reciprocal partners at 1/R. All four lie on the
`ln R = 1.56·dE` line of §3.3 — they are the physics, not error. No member has ν₀ non-finite, ≤ 0,
or below 1e12.

---

## 5. Structural probe of V4's premise (reference tables, no LAMMPS)

The closest LAMMPS-free approach to V4's mechanism: does the saddle actually cancel between the two
independent rows? All 936 measured-backing rows were located across the 60 NiFe reference tables
(936/936 matched by `(Ea, ν₀)` inside the class's own `source_sim_paths`), and all 936 have a
reciprocal backward link (`B.idx_backward == F`).

| probe | NiFe measured-backing (724 HTST pairs) | NiCr V4 source table (415 HTST pairs) |
|---|---|---|
| fwd/bwd store the *same* cluster? | **no** — sizes 128/129/130, index orders differ (types identical 0/120), mover index differs (2/120 sampled) | no (same structure) |
| cluster centroid shift f→b | 2.531 Å median, max 2.611 (= one 1NN) | 2.540 Å median, max 4.285 |
| **saddle geometry**, on atoms common to both free sets | **identical to 0.000e+00 Å** (max over all 724) | identical to 0.000e+00 Å |
| free-set sizes (r = 6.0 Å) | 47 / 48 / 49; same size in **721/724** | 28/29/30 **and** 45/49; same size in only 165/415 |
| geometric overlap of the two free sets | median **0.714** (35 of 49), min 0.673, max 1.000 | median 0.714, **min 0.367**, q10 0.378 |
| non-shared free atoms | outer shell — r from mover median 4.97 Å of a 6.0 Å sphere | — |

Two conclusions:

1. **The saddle is genuinely shared** — both rows store bit-identical saddle coordinates for the
   atoms they have in common, so the two pARTn searches converged to the same transition state.
   The cancellation V4 relies on is physically available.
2. **It is not exact** — ~29 % of the Vineyard saddle block is evaluated over different atoms
   (outer shell of the free sphere). Non-zero residual is guaranteed; only its size is unknown.
   **NiFe's geometry is strictly more uniform than NiCr's** (721/724 equal free-set sizes vs
   165/415; worst-case overlap 0.673 vs 0.367), so if the residual scales with free-set mismatch —
   which is the only plausible mechanism — NiFe's should be **no worse** than NiCr's measured
   ×1.01 median / ×1.06 max. That is an argument, not a measurement.

---

## 6. Verdict

**PARTIAL.**

| criterion | NiCr 2026-07-21 | NiFe 2026-08-15 |
|---|---|---|
| `median |ln R_state − ln R_harv|` ≤ ×2 | ×1.01 (q90 ×1.02, max ×1.06); 100 % within ×2 | **NOT EVALUATED** — needs LAMMPS Hessians |
| `corr(ln R_state, ln R_harv)` | 1.000 | **NOT EVALUATED** |
| harness ν₀ reproduction | ×0.98–1.01 | **NOT EVALUATED** |
| ν₀ pairs are per-state, not a family/global constant | assumed (finite-ν₀ rows only) | **PASS for 724/936 (77.4 %)**, **FAIL for 212/936 (22.6 %)** |
| ν₀ asymmetry is real state physics (ln R tracks dE) | ratio spread ×0.91–9.3, max ×21 | **PASS** — r = 0.731, slope +1.56/eV, matching NiCr's +1.78/eV |
| saddle-cancellation premise structurally available | (implicit) | **PASS** — same saddle to 0.000 Å; free sets 71 % shared, more uniform than NiCr |
| fwd/bwd reciprocity | enforced by construction (§7.3) | enforced by construction — **no information** |

**Why not FAIL:** nothing measured contradicts V4. The 724 real-HTST pairs behave exactly as
per-state Vineyard ratios should — all distinct, tightly clustered within a class and spread ×9
across classes, tracking dE with the same slope as NiCr, and their two source rows demonstrably
share the same saddle.

**Why not PASS:** V4's own criterion was not computed, and 22.6 % of the NiFe harvested pairs are
not HTST prefactors at all — for those, `nu0_pair_policy = "harvested_pair"` is factually wrong and
`k0_eff` is a 1 THz placeholder that Phase C would bake as a measured rate.

### 6.1 Caveats — honest list

1. **Both of V4's measured channels are missing.** No Hessian was computed. Any statement about
   `R_state` here is inference from geometry, tier *[extrapolated]* at best.
2. **The comparison population differs.** NiFe measured barriers span 0.25–0.88 eV against NiCr
   V4's 0.62–2.27 eV. NiFe's narrower ratio spread (max ×2.1 vs ×21) is a population artifact.
   Six T_ref values (300–800 K) vs NiCr's single 500 K run; ν₀ is T-independent so this affects
   only the `dE`/rate-scale statistics, not R.
3. **The July gate could not have seen the placeholder defect.** Its source table
   (`verify_fix_T500_1vac`) is 96.4 % finite-ν₀, and the harness explicitly filtered to
   `np.isfinite(nu0)` rows. It is not a NiFe-specific regression: **the NiCr production measured
   set is 26.3 % placeholder** (213 real of 289 members) and the whole NiCr catalogue is 29.0 %.
   The V4 PASS was measured on a population that is not representative of either production corpus
   Phase C actually bakes.
4. **Reciprocity is tautological in this catalogue** (§4.1) — reported per the brief, but it is not
   an independent check and should not be cited as corroboration.
5. **Sample-level tracing was on 120 of 936 members** for the source-row provenance checks
   (index ordering, mover index, `nu0 is None` confirmation); the free-region/saddle probe (§5) ran
   on all 724.
6. **The rate-distortion figures in §4.3(a) assume the class rate is the sum over members.** If the
   translator's effective semantics are a mean, the direction and rough size are unchanged
   (placeholders drag the class rate down by roughly their member share) but the exact ratios
   differ. This interacts with the known "mean-vs-sum rate hazard" from the action-fingerprint
   review and is not settled here.
7. **`nu0_geo_psinv` / the legacy aggregate columns were not examined** — only the per-member
   `nu0_f_list_hz` / `nu0_b_list_hz` that the `harvested_pair` policy fires.

### 6.2 What would close the gate

Run the July harness against NiFe: point `RT` at each `production_NiCrFe/runs/NiFe_*/
reference_table.pickle`, keep `FREE_RADIUS = 6.0`, `FD_STEP = 0.01`, `n_zero_modes = 0`
(frozen-boundary cluster — the `canonical_kappa` value of 3 is for periodic slabs and would shift
ν₀ by orders of magnitude with no error raised), and change `MASS`/`pair_coeff` to `Fe Ni`
(alphabetical type order). Sample stratified by barrier × mover from the **724 real-HTST**
members only. ~21 pairs took ~15 s on NiCr; NiFe would be comparable. Everything else in the
harness transfers unchanged.

Independently and more urgently: decide the policy for the 212 placeholder members — exclude them
from the `harvested_pair` stamp, back-fill their ν₀ from the class's real-HTST members, or make
`qc`/`graduate` refuse to stamp a class whose members carry `nu0_f == k_prefactor × 1e12`. Today
that condition is silent in every artifact between the reference table and the generated C.

---

## 7. Reproduction

```bash
source /home/kerr/pykmc/pykmc_env/bin/activate     # never run with ~/pykmc as cwd
cd /home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign_nife
python v4_reverify_catalogue_2026-08-15.py   # sections 3.0-3.3, 4.1-4.3; ~20 s
python v4_reverify_flux_2026-08-15.py        # section 4.3(a) flux + rate distortion; ~15 s
python v4_reverify_geometry_2026-08-15.py    # section 5 structural probe; ~90 s, loads 60 pickles
python v4_reverify_nicr_anchor_2026-08-15.py # NiCr comparison rows in 3.1/3.3/6.1.3; ~30 s
```

Run in that order — the flux script consumes `v4_nife_members.csv` / `v4_nife_classes.csv`
written by the catalogue script.

Inputs (all read-only): the graduated parquet above, `flux_restatement_post_graduation.csv`,
`/home/kerr/pykmc/production_NiCrFe/runs/NiFe_*/reference_table.pickle`,
`/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle` (NiCr anchor),
`/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/merged_v3_NiCr.parquet` (NiCr anchor).
Per-member / per-class / per-probe CSVs are written next to the scripts.
