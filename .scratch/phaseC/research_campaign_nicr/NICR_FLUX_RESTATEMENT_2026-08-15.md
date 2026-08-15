# NiCr per-class flux restatement — 2026-08-15

**Corpus:** `merged_v3_NiCr.parquet` (70,179 classes) × the 60 runs of `manifest_NiCr.csv`
(`/home/kerr/pykmc/production_NiCrFe/runs/<tag>`, read-only).
**Measure:** reachability-corrected expected firings, Σ_steps k·Δt per applicable event,
aggregated per `idx_ref`, mapped to merged classes via `source_sim_paths` ('run_tag#idx_ref') —
the identical measure and parser lineage as the audited NiFe artifact.
**Builder:** `nicr_flux.py` (this directory). **Nothing under `/data/…` or `runs/` was written.**

Artifacts: `flux_by_ref_nicr.csv`, `class_flux_nicr.csv`, `targets_nicr.csv`,
`run_log_nicr.csv` (+ `flux_by_ref_nicr_dirtyall.csv` / `run_log_nicr_dirtyall.csv`, diagnostic).

---

## 0. Calibration — NiFe headline reproduced before touching NiCr

Every predicate was locked by re-deriving the NiFe numbers from
`class_flux_nife.csv` + `merged_v3_NiFe.parquet` first. (Provenance note: the merged parquet's
`nu0_pair_policy` column is NULL for all rows — `class_flux_nife.csv` carries the policy from
`merged_v3_NiFe_stamped.parquet`; every calibration number below uses only columns identical
across the two files.)

| quantity | published | reproduced | ✓ |
|---|---|---|---|
| corpus expected firings | 120,291 | **120,291.152** | ✓ |
| corpus selections | 119,931 | **119,931** | ✓ |
| quarantine band, classes | 3,603 | **3,603** | ✓ |
| quarantine band, flux share | 44.8 % | **44.7534 %** | ✓ |
| token-mismatch share of NON-quarantined flux | 0.0512 % | **0.0512 %** | ✓ |
| mismatch classes ever selected / selections (non-q) | 23 / 30 | **23 / 30** | ✓ |
| median `Ea_rep` recovered vs matched (non-q) | 1.618 / 0.952 | **1.6183 / 0.9521** | ✓ |
| whole-corpus medians (§10.2) | 1.6147 / 0.9892 | **1.6147 / 0.9892** | ✓ |
| recovered flux concentration, top-10 / top-100 | 51.4 % / 99.1 % | **51.41 % / 99.13 %** | ✓ |
| per-T mismatch share, 300 K → 800 K (§10.3.3) | 0.0006 % → 0.1055 % | **0.00062 % → 0.10547 %** | ✓ |
| §2a bucket table (both alloys) | all rows | **all rows exact** | ✓ |

**Predicates fixed by that calibration (used verbatim for NiCr):**

- **Quarantine band ("tol = 1e-6 reciprocity band")** = `audit_status == 'quarantined'`.
  This is what produced NiFe's 3,603 / 44.8 %. The *strict* reciprocity subset
  (`audit_reason` contains "reciprocity") is 3,436 / 39.79 % for NiFe — both are reported
  below for NiCr, **explicitly labelled**, because the brief's headline number is the
  whole-quarantine one.
- **Token mismatch (recovered concerted)** = `len(saddle_token) != #{delta rows with
  before != Occ.EMPTY}` — the *delta-derived* mover count the pre-`8f49e18` translator used.
  Note the task brief's phrasing "`len(saddle_token) != len(arrows)`" is the *identity that
  never fires* (`arrows == tokens` on 90,472/90,472); the skip predicate is the delta one.
  Verified: 2,253 (NiFe) / 5,014 (NiCr) raw, 2,176 / 4,864 non-quarantined, and every §2a and
  §2c bucket reproduces exactly in both alloys.
- **Per-T trend denominators**: verdict §10.3.3's 0.0006 → 0.1055 % is *all* mismatch flux over
  *all* flux at that T (whole-corpus denominator). Both bases are tabulated for NiCr in §5.

---

## 1. Dirty-run policy — `NiCr_Ni95_Cr05_T300_1vac`

**What is wrong.** `pykmc.out` and `pykmc.events` each hold **two concatenated run segments**
(a second `# Simulation Progress Tracking File` header at `pykmc.out:48`;
`#Step:` restarts at `pykmc.events:309`):

| segment | steps | rows | |
|---|---|---|---|
| A | 1 … 30 | 30 | aborted attempt |
| B | 1 … 2000 | 2000 | the completed run (`DONE`, `restart_2000.npz`, `restart_latest.xyz`) |

A is **not** a prefix of B — they are different RNG streams (step 1 selects `Ref event 0` in A,
`Ref event 4` in B). `reference_table.pickle` is clean, i.e. it is **B's** table: it is rewritten
by each run, so A's `idx_ref` values index a reference table that no longer exists on disk. The
merged catalogue's lineage (`source_sim_paths = run_tag#idx_ref`) is keyed to that same surviving
table.

**Policy adopted — `KEEP_LAST_SEGMENT = True`** (implemented in `nicr_flux.py::_last_segment`,
applied to both files, with an assertion that they segment identically):

> Split the step-ordered record list wherever the step index fails to increase, and keep only
> the **final** segment. Scoring segment A would attribute A's rate constants to B's event
> identities — a silent mislabel, not a rounding error. The surviving reference table, the
> `DONE` marker and the catalogue's lineage all name segment B.

The policy is a **provable no-op on the other 59 runs**: `run_log_nicr.csv` records
`n_segments == 1`, `n_out_rows == 2000`, `max_step == 2000` for all of them, and exactly one row
flagged `n_segments = 2`.

**Quantitative effect.**

| treatment | run refs | run flux | run selections | corpus flux | corpus selections |
|---|---|---|---|---|---|
| **policy (segment B only)** | 324 (310 class-mapped) | **1,987.318** | 2,000 | **116,099.734** | **116,653** |
| naive whole-file (last-wins `dt`) | 330 (316) | 2,055.507 | 2,030 | 116,167.923 | 116,683 |
| run excluded entirely | — | — | — | 114,122.410 | 114,666 |

- The naive whole-file row is **not** "A+B": last-wins `dt` dedup re-dates segment A's event
  rows with segment B's Δt values. Decomposed (verify-fleet attack 3): segment A scored
  self-consistently contributes only **+26.515 firings** (+1.334 % of the run, **+0.0229 %** of
  corpus); the remaining **+41.674** of the +68.189 total is a pure artifact of the last-wins
  construction. Either way the naive parse also adds 30 spurious "selections" and invents 6
  `idx_ref`s (1, 9, 10, 18, 27, 29) that exist only in the aborted segment.
- The NiFe precedent parser does **not** error on this file — pandas' duplicate-key mapping
  silently last-wins — so it would produce exactly the mislabelled "naive" row above without
  any diagnostic. That silence is the reason the policy is implemented as an explicit segment
  split with an assertion (the "naive" row stays reachable via `--include-dirty-segments`).
- Dropping the run entirely would cost **1.703 %** of corpus flux and 1,987 selections — a real
  loss with no justification, since segment B is a complete, clean 2000-step run.

**Sensitivity of the headline shares to the treatment (material, disclosed).** Policy vs
excluding the run entirely moves: corpus quarantine share **38.302 % → 37.931 %** (−0.37 pp),
pending share **61.472 % → 61.839 %** (+0.37 pp), strict-reciprocity share
**35.858 % → 35.614 %** (−0.24 pp), and the §5.1 300 K quarantine column
**64.77 % → 65.35 %** (+0.58 pp). The §6 "32.6× at 300 K" multiplier becomes 36.4× under
exclusion. All exceed a 0.1 pp materiality bar, so the ruling-3.6 numbers in §4 and the 300 K
rows in §5.1 should be read with a ≈±0.4 pp treatment band; every other conclusion is
policy-invariant at the quoted precision.

**Not touched:** `trajkmc.xyz` is contaminated the same way but is not read by this pipeline.

**Sanity gate (all 60 runs, post-policy):** every run has exactly 2,000 ten-column `pykmc.out`
data rows (each file also carries one zero-Δt 3-field step-0 row — two in the dirty file, one
per segment — which no parser scores), `max_step = 2000`, and exactly 2,000 selected events;
per-run Σk·Δt lands in 1,895.8–2,100.5 (the Σk·Δt ≈ 1/step identity). Parsed rows are
10-column (`pykmc.out`) / 11-field (`pykmc.events`) with `parts[1] ∈ {Ni, Cr}` throughout —
the NiFe formats hold. Audit-trail caveat: `run_log_nicr.csv`'s `n_out_rows = 2000` for the
dirty run is the **post-policy kept** count (the raw file holds 2,030 data rows); the dropped
segment is visible only via `n_segments = 2`. One source-data precision floor affects both this
parser and any other reader of `pykmc.events`: the printed k column collapses to fixed-point
6 dp on all-slow steps (331 of 2,682,310 rows ≤3 significant digits; worst single event
+19.2 %), with a corpus effect of +0.233 firings = **+0.00019 %** — immaterial.

Per-ref total 119,845.845 firings / 120,000 selections; the class-mapped corpus is
116,099.734 / 116,653 — the 3.13 % gap (1,452 refs / 3,746.111 firings) is refs with no merged
class, overwhelmingly build-time `FRAME_UNFIT` / `MOVER_OFFLATTICE` discards plus a small
residue of reference-table index gaps (e.g. 2 of the dirty run's fired refs are absent from its
`reference_table.pickle`). NiFe's analogous gap is 0.22 %.

---

## 2. Corpus totals

| quantity | NiCr | NiFe (for reference) |
|---|---|---|
| classes | **70,179** | 20,293 |
| expected firings (corpus flux) | **116,099.734** | 120,291.152 |
| selections | **116,653** | 119,931 |
| reachable classes (`occupancy_s > 0`) | **43,053** (61.3 %) | 12,717 (62.7 %) |
| unreachable classes | 27,126 | 7,576 |

Flux is overwhelmingly one archetype: **`V1NN_inplane` = 98.966 %** of corpus flux
(31,021 classes), then `NO_OP` 0.890 %, `C2_0deg` 0.084 %, `HOP_3NN` 0.048 %.

## 3. Policy / status shares

| bucket | classes | flux | % corpus | % non-quarantined | reachable |
|---|---|---|---|---|---|
| **measured** (`nu0_pair_policy == harvested_pair`) | **32** | 262.544 | **0.226 %** | 0.367 % | 21 |
| **pending_research** | **59,448** | 71,368.346 | **61.472 %** | 99.633 % | 35,702 |
| **quarantined** (`audit_status`) | **10,699** | 44,468.845 | **38.302 %** | — | 7,330 |
| non-quarantined total | 59,480 | 71,630.889 | 61.698 % | 100 % | 35,723 |

The measured count is exactly the expected **32**. NiCr's measured line carries **0.23 %** of its
corpus flux, against NiFe's post-graduation **46.6 %** — the two alloys are not comparable states
of maturity, and this is the single sharpest number for sequencing a NiCr graduation leg.

## 4. The tol = 1e-6 reciprocity band — NiCr analogue of NiFe's 3,603 / 44.8 %

| basis | NiCr classes | NiCr flux | NiCr % corpus | NiFe classes | NiFe % corpus |
|---|---|---|---|---|---|
| **whole quarantine** (`audit_status == 'quarantined'` — the brief's basis) | **10,699** | 44,468.845 | **38.302 %** | 3,603 | 44.753 % |
| **strict reciprocity** (`audit_reason` ⊃ "reciprocity") | **9,957** | 41,631.475 | **35.858 %** | 3,436 | 39.790 % |

Quarantine composition (NiCr, by flux):

| reason | classes | flux | % corpus |
|---|---|---|---|
| pair reciprocity broken | 9,957 | 41,631.475 | 35.858 |
| self-reverse with dE ≠ 0 | 231 | 1,734.172 | 1.494 |
| NO_OP | 425 | 904.087 | 0.779 |
| human veto (CANON v2→v3 migrated) | 86 | 199.110 | 0.171 |

(NiCr has **no** dE-spread quarantine reason: the 129.364-firing class initially tabulated as
"dE spread" is a human veto whose migrated provenance text merely *mentions* dE spread —
corrected per verify-fleet attack 2.)

**Reading for ruling 3.6.** NiCr's band is **2.97× larger in class count** (10,699 vs 3,603) but
**smaller in flux share** (38.30 % vs 44.75 %). In absolute expected firings the two are close:
44,469 (NiCr) vs 53,834 (NiFe). The ruling is the largest single unaddressed lever on **both**
alloys — for NiCr it is ~170× the flux the 32 measured classes carry today. The band's
temperature profile is strongly non-flat (§5): 64.8 % of NiCr flux at 300 K vs 20.1 % at 700 K.

## 5. Token-mismatch (recovered concerted) classes

Denominators are labelled explicitly — verdict §10.2 flags this exact mislabeling hazard.

| quantity | NiCr | NiFe |
|---|---|---|
| mismatch classes, raw | **5,014** (7.14 %) | 2,253 (11.10 %) |
| mismatch classes, non-quarantined | **4,864** | 2,176 |
| all-mismatch flux | **77.811** | 42.447 |
| non-q-mismatch flux | **59.692** | 34.026 |
| **non-q-mismatch flux ÷ NON-QUARANTINED flux** *(the 0.0512 % basis)* | **0.0833 %** | **0.0512 %** |
| non-q-mismatch flux ÷ **whole-corpus** flux | **0.0514 %** | 0.0283 % |
| all-mismatch flux ÷ **whole-corpus** flux | **0.0670 %** | 0.0353 % |
| all-mismatch flux ÷ non-quarantined flux | 0.1086 % | 0.0639 % |
| classes ever selected / selections (non-q; ÷ 72,231 non-q selections) | **52 / 57** (0.079 %) | 23 / 30 |
| classes ever selected / selections (all; ÷ 116,653 corpus selections) | 69 / 76 (0.065 %) | 30 / 38 |
| reachable non-q mismatch classes | 2,251 of 4,864 | — |
| median `Ea_rep`, recovered vs matched (non-q) | **1.393 / 0.989** (gap **0.404 eV**) | 1.618 / 0.952 (gap 0.666 eV) |
| all 4,864 non-q mismatches are `pending_research` | **yes** | (2,176 pending) |
| mismatch by arrow count (non-q) | 2-arrow 4,258 · 3-arrow 606 | 2-arrow · 3-arrow |

The 0.404 eV NiCr / 0.666 eV NiFe median gaps reproduce verdict §10.3.4 exactly.

**Recovered flux by archetype (NiCr, non-quarantined):**

| archetype | classes | flux | % of recovered | selections |
|---|---|---|---|---|
| `C2_0deg` | 870 | 48.561 | **81.35 %** | 53 |
| `C2_60deg` | 2,886 | 7.233 | 12.12 % | 4 |
| `C3` | 597 | 3.487 | 5.84 % | 0 |
| `C2_90deg` | 447 | 0.411 | 0.69 % | 0 |
| `UNCLASSIFIED` | 64 | 0.000 | 0.00 % | 0 |

**Concentration.** NiCr recovered flux: **top-10 = 35.21 %**, **top-100 = 89.16 %** of recovered
flux (all-mismatch basis: 28.92 % / 85.90 %). NiFe is markedly *more* concentrated
(51.41 % / 99.13 %) — NiCr's recovered population is both larger and flatter, so a
half-shift-artifact triage of NiCr's top 100 would cover less of its recovered flux than the
43-of-100 / 73.5 % result did for NiFe.

### 5.1 Per-temperature trend (mirrors verdict §10.3.3)

Mismatch share by run temperature, both denominators, side by side:

| T (K) | NiCr, all-mm ÷ all | NiCr, non-q-mm ÷ non-q | NiFe, all-mm ÷ all | NiFe, non-q-mm ÷ non-q | NiCr quarantine share |
|---|---|---|---|---|---|
| 300 | **0.0202 %** | 0.0223 % | 0.0006 % | 0.0006 % | 64.77 % |
| 400 | 0.0280 % | 0.0273 % | 0.0021 % | 0.0055 % | 41.22 % |
| 500 | 0.0195 % | 0.0225 % | 0.0204 % | 0.0118 % | 37.59 % |
| 600 | 0.0386 % | 0.0499 % | 0.0132 % | 0.0089 % | 32.86 % |
| 700 | 0.0824 % | 0.0820 % | 0.0706 % | 0.0863 % | 20.13 % |
| 800 | **0.2074 %** | **0.2535 %** | 0.1055 % | 0.1432 % | 34.45 % |

Same monotone-ish rise with T as NiFe, but NiCr's floor is **32.6× higher at 300 K** and its
800 K value is **1.97×** NiFe's. NiCr never has a temperature at which the recovered population
is invisible.

## 6. Did verdict §10.3.4's prediction hold?

> §10.3.4: *"Expect NiCr's recovered flux share to exceed NiFe's, plausibly by an order of
> magnitude. Measure it before repeating §8.6 for NiCr."*

**Direction: YES. Magnitude: NO — it is ~1.6–1.9×, not ~10×, on any corpus-average basis.**

| like-for-like basis | NiFe | NiCr | ratio |
|---|---|---|---|
| non-q mismatch ÷ non-quarantined flux | 0.0512 % | 0.0833 % | **1.63×** |
| non-q mismatch ÷ whole-corpus flux | 0.0283 % | 0.0514 % | 1.82× |
| all mismatch ÷ whole-corpus flux | 0.0353 % | 0.0670 % | 1.90× |

The order-of-magnitude claim **does** hold at fixed low temperature — 300 K: 0.0006 % (NiFe) vs
0.0202 % (NiCr) = **32.6×** — and it dissolves at high T (800 K: 1.97×). The corpus averages are
dominated by the hot runs, where the two alloys converge. The prediction's *reasoning* also
holds: NiCr's median barrier gap is the smaller one (0.404 vs 0.666 eV) and its concerted
population is far larger (4,405 + 553 + 56 mismatch buckets vs 1,727 + 356 + 170).

**Practical reading, stated plainly:** on the measured 60-run NiCr corpus the recovered concerted
population is **still kinetically small — 0.083 % of non-quarantined flux; 57 of 72,231
non-quarantined selections (0.079 %), 76 of 116,653 corpus selections (0.065 %)** — but it is no
longer *negligible at every temperature* the way NiFe's is, and 81 % of
it sits in a single archetype (`C2_0deg`). §8.6's "kinetically almost irrelevant" phrasing should
not be transplanted to NiCr without the 300 K/800 K qualifier; verdict §10.6's amendment stands,
now with the NiCr number attached. It does **not** overturn §10.3.1's ranking: the P0-only G3
gate remains the prerequisite for any bake that enables these classes, and NiCr's flatter
concentration profile makes that triage *more* work, not less.

## 7. Pending-class leverage ladder (for a NiCr re-search leg)

Pending = 59,448 classes / 71,368.346 firings / 61.472 % of corpus flux; 35,702 reachable
(23,746 pending classes carry exactly zero flux — unreachable, worthless as search targets).

| top-N pending by flux | % of pending flux | % of corpus flux |
|---|---|---|
| 10 | 13.14 % | 8.08 % |
| 25 | 20.22 % | 12.43 % |
| 50 | 27.86 % | 17.13 % |
| **100** | **35.79 %** | **22.00 %** |
| **200** | **45.19 %** | **27.78 %** |
| 300 | 51.47 % | 31.64 % |
| 500 | 59.76 % | 36.74 % |

**Contrast with NiFe:** NiFe's top-200 pending carried **88.1 %** of pending flux / 48.65 % of
corpus. NiCr's top-200 carries **45.19 %** / 27.78 % — the same job size buys roughly half the
pending-flux coverage, because the NiCr pending pool is 3.6× larger and much flatter. A NiCr leg
sized like NiFe's leg 1 (200 jobs) would move measured corpus flux from 0.23 % to at most
~28 % (assuming a NiFe-like ~90 % graduation rate, ~25 %).

Top-200 target profile (from `targets_nicr.csv`): **one archetype** (`V1NN_inplane`), 2 distinct
`action_id`s, drawn from **47 of 60 runs**, `Ea_rep` 0.005–0.904 eV, 118 singletons (no alternate
member for a retry), **0 token-mismatch classes** — i.e. structurally the same, single-mover,
`rc_prep`-compatible target shape as the NiFe leg. One outlier worth a look before launch: a
0.005 eV `Ea_rep` class (`n_eff = 2`, 64.0 firings, donor `NiCr_Ni95_Cr05_T300_4vac#107`).

---

## 8. Files

| file | what |
|---|---|
| `nicr_flux.py` | builder (policy in `KEEP_LAST_SEGMENT`; `--include-dirty-segments` for the diagnostic) |
| `flux_by_ref_nicr.csv` | 59,518 rows, one per (run_tag, idx_ref) |
| `class_flux_nicr.csv` | all 70,179 classes + flux/selections/occupancy/reachability + policy + `token_mismatch` |
| `targets_nicr.csv` | 59,448 pending classes, flux-desc, primary donor (`donor_run`, `donor_idx`), cumulative pending-flux fraction |
| `run_log_nicr.csv` | per-run segment count, row counts, flux, selections — the dirty-run audit trail |
| `flux_by_ref_nicr_dirtyall.csv`, `run_log_nicr_dirtyall.csv` | naive-parse diagnostic (do NOT use for analysis) |

---

## 9. Adversarial verification addendum (2026-08-15, pre-commit)

Three independent Opus verifiers attacked this artifact before it was committed; none reused
the builder's code. **Every headline number in §§2–7 reproduced exactly; the corrections they
demanded are already applied in place above** (this section records what changed and what the
attacks established).

**Attack 1 — independent parser, all 60 runs.** A from-scratch parser written from the raw
file formats reproduced `flux_by_ref_nicr.csv` to a worst-case relative deviation of
**5.3 × 10⁻¹⁵** over all 59,518 (run, idx_ref) rows — float64 summation noise, four orders of
magnitude tighter than the 1e-11 the NiFe audit achieved. Ref sets, per-ref selection counts,
and every `run_log_nicr.csv` column matched 60/60. Stronger semantic check: decoding
`Selected=S` as a 0-based row index and comparing against `pykmc.out`'s independent
`Ref event` column matches at **all 120,000 steps**. It also surfaced the step-0-row format
nuance and the printed-k precision floor now documented in §1.

**Attack 2 — independent share recomputation (pyarrow, re-implemented archetype taxonomy).**
All NiFe calibration rows, all NiCr corpus/policy/band/mismatch shares, concentration, medians,
per-bucket tables, and the partition-cleanliness claim (measured ∩ quarantined = 0, policy ⇔
status crosstab exact) reproduced. Two defects found and fixed above: the quarantine
composition table's "dE spread" row was a mislabelled human veto (NiCr has no dE-spread
quarantine), and §6's selection share paired a non-quarantined numerator with the whole-corpus
selection denominator (correct like-for-like: 57/72,231 = 0.079 %).

**Attack 3 — dirty-run adjudication.** `KEEP_LAST_SEGMENT` is **CONFIRMED**, on evidence
stronger than the builder's: comparing every observed (idx_ref, dE_forward) pair against
`reference_table.pickle`'s barriers gives segment B a median |ΔE| of **0.000 eV** (96.9 % within
1 meV) vs segment A's **0.458 eV** (0 % within 1 meV) — the surviving table is unambiguously
B's; 4 physically identical events appear in both segments under *different* idx_refs, so the
segments are not relabel-compatible; chronology (orphaned `run.log` 6 h older; `restart_2000.npz`
holds B's terminus) confirms A is a dead aborted attempt. The attack also produced the honest
inflation decomposition (+26.5 real vs +41.7 last-wins artifact) and the material
policy-vs-exclude sensitivity band, both now in §1.

Residual caveats a reader should keep: (i) §4's ruling-3.6 numbers and §5.1's 300 K rows carry
the ≈±0.4 pp / ±0.6 pp dirty-run treatment band stated in §1; (ii) the 3.13 % class-mapped gap
is *mostly* but not exclusively build-time discards (reference-table index gaps contribute);
(iii) the k-column precision floor (+0.00019 % corpus) is a property of the source files, shared
by any parser of `pykmc.events`.
