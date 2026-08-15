# Symmetric mover-keyed G3 gate (canon D6) — impact on both production catalogues

**Date:** 2026-08-15  **Gate:** an event is discarded when `max(res_P0, res_P2) >= 0.5 Å` (mover-keyed max snap residual, P2 measured in the P0 frame). A class is discarded only when **all** its members discard; otherwise the member list shrinks.

**Catalogues:** `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/merged_v3_NiCr.parquet` (70,179 classes) and `merged_v3_NiFe.parquet` (20,293 classes); policy/audit stamps for NiFe read from `merged_v3_NiFe_graduated_2026-08-15.parquet` (the base NiFe merge is unstamped). **Residuals:** the 120 per-run parquets under `p2_measure/`. Join key `run_tag#idx_ref` — **0 unmatched members in either alloy**, and catalogue membership reconciles exactly with the measurement (NiCr 97,976 harvested = 95,998 members + 1,978 P0-dropped; NiFe 34,864 = 34,629 + 235).

## Headline

**NiCr loses 2 of its 32 measured classes. NiFe loses none of its 180 graduated classes, with a 0.33 Å margin.**

Both NiCr casualties are `audit_status = approved`, `nu0_pair_policy = harvested_pair` — i.e. real re-searched kinetics — and both are **single-mover, not concerted**: they are half-shift artifacts where the mover travels only ~0.52 × 1NN and parks ~1.2 Å (≈ half a 1NN) off-lattice. Their initial states are *perfectly* on-lattice (`res_P0 = 0.000 Å`), which is exactly why today's P0-only gate cannot see them.

| | NiCr | NiFe |
|---|---|---|
| measured / graduated classes | 32 | 180 |
| **flipped to discard** | **2** | **0** |
| shrunk | 0 | 0 |
| members behind them | 289 | 936 |
| max `res_sym` over the set | 1.2296 Å | 0.1746 Å |
| margin to the 0.5 Å cut | −0.730 Å (over) | +0.3254 Å |
| verdict stable for any threshold in | (0.179 Å, 1.201 Å] | (0.174 Å, ∞) |

### The two NiCr casualties, member by member

| class_id | Ea_rep | n_mem | member | res_P0 | res_P2 | hop | hop/1NN | flux_firings |
|---|---|---|---|---|---|---|---|---|
| `9e29216860611db6…` | 0.7789 eV | 3 | `NiCr…T300_5vac#158` | 0.000 | 1.2006 | 1.315 Å | 0.528 | 18.407 |
| | | | `NiCr…T400_10vac#253` | 0.000 | 1.2008 | 1.315 Å | 0.528 | |
| | | | `NiCr…T400_4vac#183` | 0.000 | 1.2009 | 1.314 Å | 0.528 | |
| `bcbdc9625341d6f7…` | 0.7490 eV | 2 | `NiCr…T300_3vac#263` | 0.000 | 1.2296 | 1.294 Å | 0.520 | 0.085 |
| | | | `NiCr…T400_10vac#1180` | 0.000 | 1.2204 | 1.301 Å | 0.523 | |

Corroborating signals — all three agree, which is why I read this as a real defect and not a measurement edge case:

- **`pair_status = unpaired` is a perfect predictor inside the measured set.** Exactly 2 of the 32 NiCr measured classes are `unpaired`, and they are exactly the 2 that flip. The other 30 are `linked`. A final state that is not a lattice state has no reverse to link to — the pairing failure and the gate failure are the same fact seen twice. (All 180 NiFe graduated classes are `linked`.)
- **The barriers are tightly reproducible** (0.7727–0.7800 eV across all 5 members), so this is a real, repeatable relaxation — it is the *lattice encoding* of the final state that is wrong, not the energetics.
- **Bystanders are fine** (`static_max_residual_P2` 0.122–0.138 Å). The lattice did not drift; one mover stopped halfway.
- Both classes carry the **same `action_id` (6698383570156747695)** and archetype, and their Ea sits in the same 0.75–0.86 eV band as the NiFe half-shift recovered population — one physical artifact family, not two coincidences.

Kinetically the loss is small but not nil: the two together carry 18.492 flux_firings = 0.0159 % of NiCr catalogue flux (99.5 % of it in the first class). The real cost is not the flux — it is that 2/32 = 6.3 % of the only measured NiCr kinetics would have to be withdrawn and re-searched.

## 1. Events failing the symmetric gate that pass today's P0-only gate

Because `gate_sym = gate_P0 OR gate_P2`, every incremental discard is by construction a **P2-only** failure — the cross-tab has no fourth cell.

| | NiCr | NiFe |
|---|---|---|
| harvested rows measured | 97,976 | 34,864 |
| fail P0 (already dropped today) | 1,978 | 235 |
| fail P2 | 5,753 | 1,203 |
| fail **both** P0 and P2 | 1,900 | 198 |
| fail **P2 only** → the incremental discard | 3,853 | 1,005 |
| fail symmetric gate (= P0 + P2-only) | 5,831 | 1,240 |
| incremental as share of harvested | 3.93 % | 2.88 % |
| incremental as share of surviving members | **4.01 %** | **2.90 %** |

Consistency: NiCr 5,831 = 1,978 + 3,853 ✓; NiFe 1,240 = 235 + 1,005 ✓.

What the incremental population looks like:

| | NiCr | NiFe |
|---|---|---|
| half-shift (shortest hop < 0.7 × 1NN) | 1,072 (27.8 %) | 148 (14.7 %) |
| multi-mover | 405 (10.5 %) | 215 (21.4 %) |
| median `res_P2` | 0.7224 Å | 0.5606 Å |
| `res_P2` p75 / p90 | 1.189 / 1.241 Å | 0.703 / 1.144 Å |

So NiCr's incremental discards are **bimodal** — a shoulder just above the cut plus a hard mode at ~1.2 Å (the half-shift population) — while NiFe's are dominated by the shoulder, with the 1.2 Å mode a much smaller minority. Note the incremental set is *not* mostly concerted: 89.5 % (NiCr) / 78.6 % (NiFe) of it is single-mover.

## 2. Classes flipped vs shrunk, by policy and audit status

| | NiCr | NiFe |
|---|---|---|
| classes | 70,179 | 20,293 |
| **flipped** (all members discard) | 2,860 | 715 |
| **shrunk** (some members discard) | 48 | 5 |
| unchanged | 67,271 | 19,573 |
| members removed | 3,853 | 1,005 |
| of the flipped: singletons (n_members = 1) | 2,551 | 620 |
| of the flipped: multi-member | 309 | 95 |
| flipped share of catalogue | 4.08 % | 3.52 % |

Flipping dominates shrinking by ~60:1 (NiCr) and ~140:1 (NiFe), because 89 % / 87 % of flipped classes are singletons — the artifact is reproducible enough that when a class has several members they usually *all* fail together.

### Cross-tab — `nu0_pair_policy` × `audit_status` × outcome

**NiCr**

| nu0_pair_policy | audit_status | flipped | shrunk | unchanged | total |
|---|---|---|---|---|---|
| `harvested_pair` | approved | 2 | 0 | 12 | 14 |
| `harvested_pair` | pending | 0 | 0 | 18 | 18 |
| `pending_research` | approved | 50 | 2 | 2,328 | 2,380 |
| `pending_research` | pending | 2,298 | 12 | 54,758 | 57,068 |
| `unstamped` | quarantined | 510 | 34 | 10,155 | 10,699 |

**NiFe**

| nu0_pair_policy | audit_status | flipped | shrunk | unchanged | total |
|---|---|---|---|---|---|
| `harvested_pair` | approved | 0 | 0 | 69 | 69 |
| `harvested_pair` | pending | 0 | 0 | 111 | 111 |
| `pending_research` | approved | 0 | 0 | 880 | 880 |
| `pending_research` | pending | 539 | 0 | 15,091 | 15,630 |
| `unstamped` | quarantined | 176 | 5 | 3,422 | 3,603 |

Reading:

- **`harvested_pair` (the measured sets).** NiCr: 2 flipped, both from the 14 `approved` ones — none of the 18 `pending` are touched. NiFe: 0 of 180 (69 approved + 111 pending) touched.
- **`pending_research`** absorbs most of the damage: NiCr 2,348 classes affected (2,298 pending + 50 approved flipped, plus 14 shrunk); NiFe 539. These are exactly the classes a future re-search campaign would target, so the gate is cheapest to apply *before* spending search budget on them.
- **`unstamped | quarantined`** (NiCr 10,699 / NiFe 3,603 classes — the QC-rejected population; NaN policy) loses NiCr 510 flipped + 34 shrunk, NiFe 176 + 5. These are already excluded from any bake, so this is bookkeeping, not loss.
- Note NiCr's 50 flipped `pending_research | approved` classes: `approved` at audit does **not** imply the projection is sound, because audit never looked at the final state. That is the same blind spot the 2 measured casualties fell through.

## 3. THE HEADLINE — do the measured / graduated classes move?

Covered above; the numbers again, in full, because this is the decision:

**NiCr — 2 of 32 measured classes flip. Both listed individually above.** Neither shrinks (both are total losses: 3/3 and 2/2 members fail). The remaining 30 top out at `res_sym = 0.1788 Å`, i.e. **2.8× below the cut**.

**NiFe — 0 of 180 graduated classes flip or shrink.** The whole set tops out at `res_sym = 0.1746 Å`; the four worst (0.1746, 0.1743, 0.1720, 0.1719 Å) are still 2.9× below the cut. Median is 0.0207 Å. Zero of the 180 are half-shift; all 180 are `linked`.

**The verdict is threshold-independent across the whole sensitivity range.** NiCr's 2 flips hold for any cut in (0.1788 Å, 1.2009 Å] — a 1.02 Å-wide plateau containing 0.4, 0.5 and 0.6 with room to spare. NiFe's zero holds for any cut above 0.1746 Å. Moving the threshold within 0.4–0.6 Å cannot change either answer.

## 4. Overlap with the token-mismatch (recovered concerted) population

**First, a correction to the framing.** The brief asked for `len(saddle_token) != len(arrows)`. That predicate is **identically false** — 0 classes in either catalogue — because `n_tokens == n_arrows` always (verdict §2a). The verdict's actual predicate is `n_tokens != n_delta_movers`, where `n_delta_movers` counts delta rows with `before != EMPTY`. Using it reproduces the verdict's populations exactly: **NiCr 5,014** (verdict: 5,014) and **NiFe 2,253** (verdict: 2,253). I also cross-checked class-by-class against the precomputed `token_mismatch` column in `class_flux_nicr.csv` — exact agreement on all 70,179 rows.

| | NiCr | NiFe |
|---|---|---|
| recovered classes | 5,014 | 2,253 |
| recovered, flipped | 299 | 177 |
| recovered, shrunk | 0 | 1 |
| recovered share of catalogue | 7.14 % | 11.10 % |
| **flipped classes that are recovered** | **10.45 %** (299/2,860) | **24.76 %** (177/715) |
| flip rate among recovered | 5.96 % | 7.86 % |
| flip rate among matched | 3.93 % | 2.98 % |

Recovered classes are enriched among the flips — 1.5× (NiCr) and 2.6× (NiFe) the matched flip rate — but they are still a **minority of the flips** (10 % / 25 %). The gate is not a concerted-event filter; it is a final-state filter that happens to hit concerted events harder.

### 4b. The half-shift tail — how much does the gate actually catch?

**All of it. 100 %, at both event and class level, with a large margin.**

| | NiCr | NiFe |
|---|---|---|
| half-shift events (all harvested) | 2,931 | 335 |
| …surviving today's P0 gate | 1,072 | 148 |
| …caught by the symmetric gate | 1,072 | 148 |
| classes with a half-shift member | 845 | 130 |
| …flipped or shrunk | 845 | 130 |
| min `res_P2` among surviving half-shift events | 0.9609 Å | 1.0090 Å |

The margin is the point: the *smallest* residual in the entire surviving half-shift population is 0.96 Å, roughly **2× the cut**. A half-shift by definition parks the mover near the midpoint between sites, i.e. ~0.5 × 1NN = 1.24 Å off-lattice, so the gate cannot miss them at any threshold below ~0.96 Å. Conversely most of what the gate catches is *not* half-shift (72 % NiCr / 85 % NiFe), so half-shift and the gate are not the same population.

### 4c. Verdict §10.3.1 — the 43 top-100 recovered NiFe classes

**Reproduced exactly, and the gate removes 43 of 43 (100 %).**

Ranking the **translator-visible** recovered set (recovered minus quarantined, 2,176 classes — verdict §1's 2,253 − 77 = 2,176) by `flux_firings` from `class_flux_nife.csv`:

| quantity | verdict §10.3.1 | this measurement |
|---|---|---|
| top-10 share of recovered flux | 51.4 % | 51.4 % |
| top-100 share of recovered flux | 99.1 % | 99.1 % |
| half-shift classes in the top 100 | 43 | **43** |
| their share of recovered flux | 73.5 % | **73.5 %** |
| **removed by the symmetric gate** | — | **43 flipped + 0 shrunk = 43 / 43 (100 %)** |

Both §4-E3 exemplars are in the set and both flip: `3d47227ec6af2634…` (flux 2.985, res_P0 0.072 → res_P2 1.158, hop 0.530 × 1NN) and `2f5dd741e6347be7…` (flux 2.727, res_P0 0.069 → res_P2 1.209, hop 0.539 × 1NN).

Across the whole visible recovered set the gate removes 73.7 % of recovered NiFe flux and all 94 of its half-shift classes. **This closes verdict §10.3.1's prerequisite**: the P0-only G3 gate was blocking any bake that enables recovered classes precisely because 73.5 % of their flux was artifact; the symmetric gate removes that 73.5 % in full, leaving the ~26 % genuine remainder.

(Ranking the full 2,253 including quarantined instead gives top-10 44.9 %, 51 half-shift carrying 78.3 %, again 51/51 removed — same conclusion, different denominator. NiCr's visible recovered top-100 also contains exactly 43 half-shift classes, carrying 45.5 % of recovered NiCr flux, again 43/43 removed.)

## 5. Flux carried by flipped / shrunk classes

`class_flux_nicr.csv` **does now exist** (`.scratch/phaseC/research_campaign_nicr/`, 2026-08-15 04:22), so both alloys are flux-weighted here — NiCr is **not** pending.

| | NiCr | NiFe |
|---|---|---|
| total flux_firings | 116,099.7 | 120,291.2 |
| flux in flipped classes | 3,046.80 | 40.68 |
| **% flux flipped** | **2.62 %** | **0.0338 %** |
| flux in shrunk classes | 27.36 | 3.46 |
| % flux in shrunk classes | 0.0236 % | 0.0029 % |
| member-level flux removed | 3,070.02 (2.64 %) | 41.62 (0.0346 %) |

**NiCr's flux exposure is ~78× NiFe's** (2.62 % vs 0.034 %), which is the quantitative confirmation of verdict §10.3.4's warning that the NiFe → NiCr "not urgent" extrapolation was not conservative. Nearly all of NiCr's 2.62 % is the half-shift population: half-shift classes carry 2.64 % of NiCr catalogue flux and 100 % of them are flipped or shrunk — the half-shift artifact alone accounts for 99.8 % of all flux the gate removes from NiCr (95.3 % for NiFe).

Member-level and class-level flux agree closely in both alloys (2.644 % vs 2.624 % NiCr; 0.0346 % vs 0.0338 % NiFe), confirming that shrinking contributes almost nothing — the flux loss is concentrated in whole-class flips.

## 6. Sensitivity — 0.4 / 0.5 / 0.6 Å

| threshold | NiCr flipped | NiCr shrunk | NiCr members removed | NiCr % flux | NiFe flipped | NiFe shrunk | NiFe members removed | NiFe % flux |
|---|---|---|---|---|---|---|---|---|
| **0.4 Å** | 4,277 | 101 | 5,769 (6.01 %) | 2.6928 % | 979 | 25 | 1,413 (4.08 %) | 0.0648 % |
| **0.5 Å** | 2,860 | 48 | 3,853 (4.01 %) | 2.6243 % | 715 | 5 | 1,005 (2.90 %) | 0.0338 % |
| **0.6 Å** | 1,842 | 46 | 2,538 (2.64 %) | 2.6182 % | 326 | 1 | 448 (1.29 %) | 0.0322 % |

**There is no empty valley at 0.5 Å in either alloy** — the pure-Ni history holds. The residual distribution of surviving members through the cut:

| bin (Å) | NiCr | NiFe |
|---|---|---|
| 0.30–0.40 | 3,903 | 1,120 |
| 0.40–0.45 | 1,064 | 266 |
| 0.45–0.50 | 852 | 142 |
| 0.50–0.55 | 829 | 419 |
| 0.55–0.60 | 486 | 138 |
| 0.60–0.70 | 444 | 189 |
| ≥ 0.70 | 2,094 | 259 |
| ≥ 1.00 | 1,508 | 159 |

How sharp the boundary is:

- **NiCr: flat, not a valley.** Density just above / just below the cut = 0.97 (829 vs 852 per 0.05 Å). The cut lands on a smooth monotone shoulder. 1,681 members (1.75 % of the catalogue) sit within ±0.05 Å of it — those verdicts are threshold-noise.
- **NiFe: an anti-valley — a pile-up just above the cut.** Density ratio 2.95 (419 vs 142), i.e. the 0.50–0.55 bin holds ~3× the 0.45–0.50 bin. Moving the cut from 0.5 to 0.55 would spare a distinct sub-population; moving it to 0.45 costs little.
- In both alloys the true minimum of the distribution over [0.2, 1.0) sits at **0.95 Å**, not 0.5 Å (NiCr 23 members in the minimum bin, NiFe 1) — the natural separation between 'shoulder' and 'half-shift mode' is near 0.95 Å, not at the conventional 0.5 Å.
- Bulk counts are genuinely threshold-sensitive: NiCr flips move 4,277 → 2,860 → 1,842 and NiFe 979 → 715 → 326 across 0.4 → 0.6, roughly ×1.5 per 0.1 Å step.
- **But flux and the headline are not.** NiCr's flipped flux barely moves (2.693 % → 2.624 % → 2.618 %) and NiFe's is 0.065 % → 0.034 % → 0.032 %, because the kinetically heavy discards all sit at ~1.2 Å, far above any candidate cut. And the measured/graduated verdict is identical at all three thresholds (NiCr 2 flipped, NiFe 0). **Choosing 0.4, 0.5 or 0.6 changes the bookkeeping, not the decision.**

## What this means

1. **NiFe's 180 graduated classes are safe** with a 2.9× margin. D6 can be adopted without re-opening the NiFe graduation campaign.
2. **NiCr's measured set is not.** 2 of 32 must be withdrawn and re-searched. Because `pair_status = unpaired` flags both exactly, the same 2 could have been caught by a pairing check without any P2 measurement — worth adding as a cheap pre-filter.
3. **The gate is a prerequisite for enabling recovered classes, as verdict §10.3.1 argued, and it fully discharges that prerequisite** — 43/43 of the top-100 half-shift recovered NiFe classes and 73.5 % of recovered NiFe flux are removed.
4. **NiCr carries ~78× NiFe's flux exposure** (2.62 % vs 0.034 %). Any NiCr bake or NiCr re-search campaign should apply D6 first — 2,348 `pending_research` classes are removed by it, which is search budget not worth spending.
5. **Threshold choice is not load-bearing** in 0.4–0.6 Å. If a value is wanted on other grounds, 0.55 Å sits just past NiFe's pile-up, and ~0.95 Å is where the distribution actually separates.

## Provenance

- **Inputs (read-only, untouched — mtimes verified post-run):** `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full` (2026-08-15 01:50), `/home/kerr/pykmc/production_NiCrFe/runs` (2026-08-07 21:03).
- **Residuals:** 120 per-run parquets in `p2_measure/{NiCr,NiFe}/` (97,976 + 34,864 = 132,840 rows), `mover_snap_tol=0.5`, `half_shift_frac=0.7`, `nominal_a=3.52`, 1NN = 2.4890 Å, P2 measured in the P0 frame.
- **Flux:** `class_flux_nicr.csv` and `class_flux_nife.csv` (`flux_firings` per `class_id`), plus `flux_by_ref_*.csv` for member-level attribution.
- **Scripts:** `gate_impact.py` (analysis), `write_summary.py` (this memo).
- **Outputs:** `gate_impact_by_class.parquet` (90,472 rows × 39 cols — every class in both catalogues with per-threshold status, residuals, half-shift and token-mismatch flags, flux), `gate_impact_raw.json`, `gate_impact_summary.md`.
- Join integrity: 0 unmatched members, 0 duplicate member keys, member totals reconcile exactly with the build ledgers in both alloys.

