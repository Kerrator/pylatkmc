# Symmetric mover-keyed G3 projection gate (canon D6) — decision memo

**Status: DECISION REQUESTED — 2026-08-15. Nothing here is settled; every ruling below is
Stephen's.** This memo presents the first full-corpus measurement of the symmetric-residual
gate proposed as `TOKEN_MISMATCH_VERDICT_2026-08-15.md` §5 and carried to the brief as **D6**,
states what adopting it would cost, and records a labelled recommendation for each open ruling.
It does **not** authorise implementation. Nothing was built, migrated, committed or promoted for
it; `/data/pylatkmc_ingest/` and `production_NiCrFe/runs/` were read-only throughout.

**Author:** Claude Fable 5, 2026-08-15.
**Style precedent:** `OVERSNAP_DISCARD_EMPTY_SPLIT_DECISION_2026-07-29.md` (the approved
mover-keyed-G3 memo this one extends). Where that memo settled *which atom* the gate keys on,
this one asks *which snapshot* it looks at.

**Inputs:** tonight's 120-run measurement
(`pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15/`: `gate_impact_summary.md`,
`gate_impact_raw.json`, `gate_impact_by_class.parquet`, `validation_summary.csv`, the 120
per-run parquets under `p2_measure/`); `TOKEN_MISMATCH_VERDICT_2026-08-15.md` §§2e, 5, 10.3.1,
10.3.4, 10.4, 10.6; `NIFE_DECISION_BRIEF_2026-08-15.md` D1/D6; tonight's adversarially-verified
NiCr flux artifact `NICR_FLUX_RESTATEMENT_2026-08-15.md`; the same-night
`REVIEW_PACKET_15CLASSES_2026-08-15.md` (§7 below); live source
(`pylatkmc/ingest/event_projection.py`, `event_class.py`, `reftable.py`).

**Conditions stamp (applies to every number below):** branch `ingest` @ `5ff4bfc`, Linux box,
Python 3.12.3 venv. Catalogues: `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/`
`merged_v3_NiCr.parquet` (70,179 classes / 95,998 members) and `merged_v3_NiFe.parquet`
(20,293 / 34,629), NiFe policy + audit stamps read from
`merged_v3_NiFe_graduated_2026-08-15.parquet`. Residuals measured over **all 132,840**
reference-table rows of the 120 production runs (NiCr 97,976 / NiFe 34,864) with the production
projection parameters (`nominal_a = 3.52`, 1NN = 2.4890 Å, `mover_snap_tol = 0.5`,
`half_shift_frac = 0.7`); **P2 is measured in the P0 frame** (see §3.2 — this is load-bearing).
0 frame-unfit, 0 errors, 0 NaN residuals. Flux = reachability-corrected expected firings from
`class_flux_nicr.csv` / `class_flux_nife.csv`. These are **slab** systems at 5 at.% solute; the
fractions will not transfer unchanged to bulk/GB or higher-solute campaigns.

**Measurement integrity.** Row conservation holds run-by-run: the measurement carries exactly one
row per reference-table row for all 120 runs (`match_ref` 60/60 in both alloys). On one validated
run per alloy, four independent checks against the *production* artifacts — the build's
`MOVER_OFFLATTICE` discard ledger, the per-run raw catalogue (singletons and multiset), the
merged catalogue via `source_sim_paths`, and coverage in both directions — all reproduce the
stored `res_P0` with **max deviation 0.0 Å** and 0 orphans either way (`validation_summary.csv`).
Corpus join: **0 unmatched members** in either alloy, and membership reconciles exactly
(NiCr 97,976 = 95,998 + 1,978 P0-dropped; NiFe 34,864 = 34,629 + 235).

---

## 1. The question

Today's G3 gate (approved 2026-07-29 §4) is

```
G3 FAIL  iff  frame_unfit  OR  mover_max_residual(P0) >= 0.5 Å
```

— computed on the **initial** snapshot only (`event_projection.py:832-835`). D6 asks whether it
becomes

```
G3 FAIL  iff  frame_unfit  OR  max( res(P0), res(P2) ) >= 0.5 Å      (over movers)
```

i.e. whether an event whose mover never *arrives* at a lattice site is as unrepresentable as one
that never *starts* at one. Five things need a ruling: **R1** adopt or not, and under which
enforcement variant; **R2** the threshold; **R3** what happens to the two NiCr measured classes it
would cost; **R4** enforcement and migration mechanics; **R5** whether `pair_status = unpaired`
becomes a standing prescreen. §§2–7 are the evidence; §8 is the ruling sheet; §§9–13 are
mechanics, costs, scope and triggers; §14 records the adversarial verification this memo passed
before being put forward.

Two facts frame the stakes. Verdict §10.6 promoted this from "unranked follow-up" to a
**prerequisite for any bake that enables the recovered (token-mismatch) classes** — so an
`include_unstamped` bake or a future multi-mover graduation is blocked until it is settled either
way. And it does **not** gate D1: the NiFe graduated set is untouched (§4.2).

## 2. The structural argument — today's gate is blind on 87.5 % of the corpus by construction

This is the strongest evidence for D6 and it appears in none of the existing memos.

`fit_local_fcc` pins the local frame's **origin to the seed atom's P0 position**
(`event_projection.py:379-390`; the `LocalFrame` docstring, `:143-144`, states it outright: "the
seed snaps to `(0,0,0)` by construction"). Therefore, for any event whose single mover *is* the
seed, the mover's initial snap residual is not small — it is **identically zero, as an algebraic
identity, regardless of where the atom actually sits**.

Measured over the 132,840-row corpus:

| | count | share |
|---|---|---|
| events that are single-mover **and** seed-is-mover | 116,216 | **87.49 %** |
| …of those, `mover_max_residual(P0)` exactly 0.0 | 116,216 | **100 %** (set max = 0.0) |
| today's G3 firings, corpus-wide | 2,213 | 1.67 % |
| …on a multi-mover event | 1,954 | — |
| …on a non-seed mover | 439 | — (180 are both) |
| …on the 87.49 % single-mover-seed majority | **0** | **0 %** |

So the mover-keyed P0 gate can only ever fire on multi-mover events or non-seed movers. On the
overwhelming majority of the catalogue it is not merely permissive — it is *structurally
incapable* of failing. The final state carries no such degeneracy: within that same
87.49 % population, **4,161 events (3.58 %) read `res(P2) ≥ 0.5 Å`**, of which 816 are half-shifts
and 906 are mover-attributable (§3.2). Those 4,161 are invisible to every build-time gate today.

The defect is visible in the shipped production catalogue, not only in this measurement: both
NiCr casualties of §4.1 carry `mover_max_residual_list = [0.0, 0.0, 0.0]` / `[0.0, 0.0]` in
`merged_v3_NiCr.parquet` while their movers actually park ~1.2 Å off-lattice.

## 3. The measurement — corpus-wide impact, and the fork it exposes

### 3.1 Headline counts at 0.5 Å

Because `gate_sym = gate_P0 OR gate_P2`, every incremental discard is by construction a P2-only
failure.

| | NiCr | NiFe | corpus |
|---|---|---|---|
| harvested rows measured | 97,976 | 34,864 | 132,840 |
| fail P0 (already dropped today) | 1,978 | 235 | 2,213 |
| fail P2 | 5,753 | 1,203 | 6,956 |
| fail both | 1,900 | 198 | 2,098 |
| **fail P2 only → incremental discard** | **3,853** | **1,005** | **4,858** |
| incremental as share of surviving members | 4.01 % | 2.90 % | — |
| classes flipped (all members discard) | 2,860 | 715 | — |
| classes shrunk (some members discard) | 48 | 5 | — |
| of the flipped, singletons | 2,551 (89.2 %) | 620 (86.7 %) | — |
| **flux carried by flipped classes** | **2.6243 %** | **0.0338 %** | — |

**Flux exposure is asymmetric by 77.6×** (2.6243 % vs 0.0338 %). One attribution corrected under
verification (§14): this is **not** the quantity verdict §10.3.4 warned about. §10.3.4 hedged
that NiCr's *recovered-class* flux share might exceed NiFe's "plausibly by an order of
magnitude"; measured on that metric the ratio is only **1.63×** (0.083 % vs 0.051 % of
non-quarantined flux) — the warning's direction holds, its magnitude does not. The 77.6× is a
**half-shift-population** fact: half-shift classes carry 2.64 % of NiCr catalogue flux, 100 % of
them flip or shrink, and they account for 99.8 % of all flux the gate removes from NiCr (95.3 %
for NiFe).

Most of what the gate catches is *not* half-shift (72 % NiCr / 85 % NiFe), and most of it is not
concerted either (89.5 % / 78.6 % single-mover). Recovered (token-mismatch) classes are
**enriched** among the flips — flip rate 5.96 % vs a matched 3.93 % (NiCr, 1.5×) and 7.86 % vs
2.98 % (NiFe, 2.6×) — but they are still a **minority of the flips**: 10.45 % (299/2,860) and
24.76 % (177/715). This is a final-state filter that happens to hit concerted events harder, not
a concerted-event filter.

Where the damage lands, by curation status (`nu0_pair_policy` × `audit_status`):

- **`harvested_pair`** (the measured sets): NiCr **2 flipped of 32**, both from the 14 `approved`;
  NiFe **0 of 180**. §4.
- **`pending_research`**: NiCr 2,348 flipped + 14 shrunk (of 59,448); NiFe 539 flipped + 0 shrunk
  (of 16,510). These are exactly a future re-search campaign's target pool — the gate is cheapest
  applied *before* search budget is spent.
- **`unstamped | quarantined`**: NiCr 510 + 34, NiFe 176 + 5. Already excluded from every bake;
  bookkeeping, not loss.
- Worth noting: 50 NiCr `pending_research | approved` classes flip. `approved` at audit does not
  imply a sound projection — audit never looked at the final state. Same blind spot as §4.1.

### 3.2 The naive-vs-attributable fork — 75.9 % of the naive catch is a *different* defect

Because the frame origin is the seed's P0 position, a seed that is itself off-lattice displaces
the **whole registry**: every atom then reads a large residual in *both* snapshots, and the
mover's `res(P2)` is anchor error rather than a bad final state. The measurement implements the
discriminator as the column `mover_offlattice_P2_attributable`:

```
attributable  iff  res(P2) >= 0.5 Å  AND  static_max_residual(P2) < 0.5 Å
                   (mover off-lattice, static substrate clean)
```

| of the 4,858 incremental discards | n | share |
|---|---|---|
| **attributable** — the D6 target | **1,171** | **24.10 %** |
| non-attributable — whole registry off in P2 | 3,687 | 75.90 % |
| …of those, already visible on the **initial** state via non-mover-keyed `max_residual(P0) ≥ 0.5` | 3,640 | **98.73 %** |
| …visible by neither signal | 47 | 1.27 % |

The non-attributable bucket is an anchor problem, not a final-state problem, and the data says so
three ways: its `static_max_residual(P0)` median is **1.208 Å** (the substrate already reads
badly off-lattice in the initial snapshot); its coherent registry offset is **the same in both
snapshots** (`drift_P0` vs `drift_P2` correlation 0.9995, |Δ| median 0.005 Å, 99.9 % within
0.05 Å); and in 91.8 % of them the mover's P2 residual does not even exceed the static
substrate's — the mover is not exceptional, it is just one of many displaced atoms. This is the
defect the retired max-keyed `snap_tol` gate used to catch, and which 2026-07-29 §6 deliberately
demoted from a discard to a `WILDCARD` context mask.

The two buckets look nothing alike in what they contain:

| shortest mover hop / 1NN | attributable (1,171) | non-attributable (3,687) | whole corpus |
|---|---|---|---|
| 0.4–0.7 (half-shift) | **734 (62.7 %)** | 486 | 1,250 |
| 0.7–0.85 | 4 | 5 | 32 |
| **0.85–1.15 (ordinary complete 1NN hop)** | **0** | **469** | 70,029 |
| 1.15–1.5 | 146 | 83 | 2,906 |
| 1.5–2.0 | 286 | 2,604 | 54,934 |
| > 2.0 | 1 | 40 | 1,017 |

The attributable bucket contains **zero ordinary complete 1NN hops** — the bin that holds 53 % of
the corpus is empty after attribution. 953 of the 1,171 are single-mover. The non-attributable
bucket contains 469 of them: under a naive gate those 469 workhorse events would be discarded for
a reason that has nothing to do with their final state.

Class-level, at 0.5 Å, the fork costs and buys:

| variant | NiCr flipped / shrunk / members / flux | NiFe flipped / shrunk / members / flux |
|---|---|---|
| **naive** `max(res_P0, res_P2) ≥ 0.5` | 2,860 / 48 / 3,853 / **2.6243 %** | 715 / 5 / 1,005 / **0.0338 %** |
| **attributable only** | 860 / 38 / 1,089 / **2.2795 %** | 76 / 1 / 82 / **0.0234 %** |
| frame-anchor bucket alone | 2,000 / 10 / 2,764 / 0.3448 % | 639 / 4 / 923 / 0.0104 % |

The attributable variant removes **86.9 % (NiCr) / 69.2 % (NiFe) of the flux** the naive variant
removes while touching **28.3 % / 8.2 % of its events**. Whichever way R1 goes, the
measured/graduated verdict is identical: 2 NiCr casualties and 0 NiFe under naive, attributable,
and frame-anchor-only alike.

## 4. What it costs the measured kinetics

### 4.1 NiCr loses exactly 2 of its 32 measured classes

Both are `audit_status = approved`, `nu0_pair_policy = harvested_pair` — real re-searched
kinetics — and both are **single-mover, not concerted**: half-shift artifacts where the mover
travels ~0.52 × 1NN and parks ~1.2 Å (≈ half a 1NN) off-lattice. Their initial states are
*perfectly* on-lattice, which is exactly why today's gate cannot see them.

| class_id | Ea_rep | n_mem | member | res_P0 | res_P2 | hop | hop/1NN | flux |
|---|---|---|---|---|---|---|---|---|
| `9e29216860611db6…` | 0.7789 eV | 3 | `NiCr…T300_5vac#158` | 0.000 | 1.2006 | 1.315 Å | 0.528 | 18.407 |
| | | | `NiCr…T400_10vac#253` | 0.000 | 1.2008 | 1.315 Å | 0.528 | |
| | | | `NiCr…T400_4vac#183` | 0.000 | 1.2009 | 1.314 Å | 0.528 | |
| `bcbdc9625341d6f7…` | 0.7490 eV | 2 | `NiCr…T300_3vac#263` | 0.000 | 1.2296 | 1.294 Å | 0.520 | 0.085 |
| | | | `NiCr…T400_10vac#1180` | 0.000 | 1.2204 | 1.301 Å | 0.523 | |

Five corroborating signals, which is why this reads as a real defect and not a measurement edge
case:

1. **`pair_status = unpaired` is a perfect predictor inside the measured set.** Exactly 2 of the
   32 NiCr measured classes are `unpaired`; they are exactly the 2 that flip. The other 30 are
   `linked`, as are all 180 NiFe graduated. A final state that is not a lattice state has no
   reverse to link to — the pairing failure and the gate failure are the same fact seen twice.
2. **The barriers are reproducible**: 0.7727–0.7800 eV across all five members (7.3 meV spread).
   The energetics are real; it is the *lattice encoding of the final state* that is wrong.
3. **The substrate is clean**: `static_max_residual(P2)` 0.1225–0.1378 Å. Nothing drifted; one
   mover stopped halfway. All five members are `attributable` under §3.2's discriminator.
4. **The delta asserts a hop that did not happen.** Both classes' `delta` is an ordinary in-plane
   1NN vacancy exchange — `(0,0,0) Ni→Vacant`, `(-1,-1,0) Vacant→Ni` — under the workhorse action
   `6698383570156747695` (= `5cf5705e14817baf`, `V1NN_inplane`, the archetype carrying 98.97 % of
   NiCr corpus flux). The catalogue claims a complete lattice-to-lattice hop for an atom that
   moved 0.53 × 1NN.
5. **Independent flags on the same action.** 8 of the 11 rows in the campaign's standing
   `action_review.csv` (action-pair-mismatch, ruling 9) involve that same `action_id`. The two
   casualties are not themselves on that list — being `unpaired`, they have no partner to
   disagree with — but the action is already a known projection trouble spot.

Kinetic magnitude of the loss: 18.492 firings = **0.0159 % of NiCr catalogue flux**, 99.5 % of it
in the first class. The real cost is curational: **2 of 32 = 6.25 % of the measured class count**
(7.04 % of measured-set flux) would have to be withdrawn. One honest deduction: `bcbdc9625341d6f7…`
carries a **1.0e12 Hz placeholder ν₀** on one of its two members — it is already inside the
placeholder population the D1 post-brief addendum flagged (**26.3 % of the NiCr production
measured set**), so part of what would be lost is data of known-degraded quality.

### 4.2 NiFe loses none of its 180 graduated classes

Zero flipped, zero shrunk. The whole set tops out at `res_sym = 0.1746 Å` — **2.86× below the
cut**; median 0.0207 Å; zero half-shifts; all 180 `linked`. The surviving 30 NiCr measured classes
top out at 0.1788 Å (2.80× below). **D6 does not gate D1.**

## 5. Does D6 discharge the §10.3.1 prerequisite? Under one variant, yes; under the other, only with a companion

Verdict §10.3.1's population reproduces to the decimal on the translator-visible recovered set
(2,176 NiFe classes = 2,253 − 77 quarantined): top-10 = 51.4 % of recovered flux, top-100 =
99.1 %, and **43 of the top 100 are half-shift artifacts carrying 73.5 % of visible recovered
flux** (58.9 % of recovered flux including the 77 quarantined classes; ranking all 2,253 instead
gives 51 half-shift classes carrying 78.3 % — same conclusion, different denominator).

| | naive gate | attributable only | attributable + frame-anchor treated |
|---|---|---|---|
| NiFe top-100 half-shift recovered classes removed | **43 / 43** | 36 / 43 | **43 / 43** |
| …share of visible recovered NiFe flux removed | **73.7 %** | 64.7 % | 73.7 % |
| NiCr top-100 half-shift recovered classes removed | **43 / 43** | 34 / 43 | **43 / 43** |
| …share of visible recovered NiCr flux removed | 48.5 % | 39.3 % | 48.5 % |
| half-shift **events** surviving P0 (NiCr · NiFe), discarded or quarantined | 1,072/1,072 · 148/148 | 655 · 79 (discarded only) | 1,072 · 148 |
| classes with a half-shift member, touched | 845/845 · 130/130 | 559 · 74 | 845 · 130 |

The margin is what makes the naive result robust: the **smallest** residual in the entire
surviving half-shift population is **0.9609 Å (NiCr) / 1.0090 Å (NiFe)** — roughly **2× the cut**.
A half-shift parks the mover near the midpoint between sites (~0.5 × 1NN = 1.24 Å off-lattice), so
no threshold below ~0.96 Å can miss them.

The seven NiFe (and nine NiCr) top-100 classes that the attributable variant leaves behind are
**double defects** — half-shift *and* registry-displaced — so their members fall in the
frame-anchor bucket. They are covered if and only if that bucket gets its own treatment (§9.2).
If R1 chooses attribution and the frame-anchor bucket is left untouched, **the prerequisite is not
discharged** and ~9 pp of recovered NiFe flux stays bakeable.

## 6. Threshold — the verdict is threshold-independent; the bookkeeping is not

**There is no empty valley at 0.5 Å in either alloy.** The pure-Ni history (2026-07-29 §2: "moving
the cut 0.4→0.5 changes 2 rows in 6,604") does not repeat on the alloys.

| surviving-member residual bin (Å) | NiCr | NiFe |
|---|---|---|
| 0.40–0.45 | 1,064 | 266 |
| 0.45–0.50 | 852 | 142 |
| 0.50–0.55 | 829 | **419** |
| 0.55–0.60 | 486 | 138 |
| ≥ 1.00 | 1,508 | 159 |

- **NiCr: a flat shoulder, not a valley.** Density just above / just below the cut ≈ 0.98
  (829 vs 844 per half-open 0.05 Å bin). 1,681 members (1.75 % of the catalogue) sit within
  ±0.05 Å of it — those verdicts are threshold noise.
- **NiFe: an anti-valley.** The 0.50–0.55 bin holds **2.95×** the 0.45–0.50 bin. Moving the cut to
  0.55 Å would spare a distinct sub-population; moving it to 0.45 costs little. 561 members
  (1.62 %) sit within ±0.05 Å. Verification adds the attribution (§14): the pile-up is **100 %
  non-attributable** under §3.2's discriminator (NiCr's shoulder: 94 %) — it is the
  frame-anchor/relaxation population appearing as a distinct physical mode, not threshold noise,
  which is further weight behind R1-d's quarantine-don't-discard treatment of that bucket.
- In **both** alloys the true distribution minimum over [0.2, 1.0) is at **0.95 Å**, not 0.5 Å
  (NiCr 23 members in the minimum bin, NiFe 1) — the natural separation between "shoulder" and
  "half-shift mode" is near 0.95 Å.

Sensitivity across 0.4 / 0.5 / 0.6 Å:

| threshold | NiCr flipped | NiCr members | NiCr % flux | NiFe flipped | NiFe members | NiFe % flux |
|---|---|---|---|---|---|---|
| 0.4 | 4,277 | 5,769 (6.01 %) | 2.6928 % | 979 | 1,413 (4.08 %) | 0.0648 % |
| **0.5** | **2,860** | **3,853 (4.01 %)** | **2.6243 %** | **715** | **1,005 (2.90 %)** | **0.0338 %** |
| 0.6 | 1,842 | 2,538 (2.64 %) | 2.6182 % | 326 | 448 (1.29 %) | 0.0322 % |

Bulk counts move ~1.5× per 0.1 Å step. **Flux and the headline do not**: the kinetically heavy
discards all sit at ~1.2 Å, far above any candidate cut, and the measured/graduated verdict is
identical at all three thresholds. NiCr's 2 flips hold on a **1.02 Å-wide plateau**,
(0.1788 Å, 1.2006 Å]; NiFe's zero holds for any cut above 0.1746 Å. Choosing 0.4, 0.5 or 0.6
changes the bookkeeping, not the decision.

## 7. Convergent same-night evidence — the defect has named instances, found independently

`REVIEW_PACKET_15CLASSES_2026-08-15.md` (the July phase-2 15-class review list, a different
corpus and a different agent, the same night) reached this defect from the opposite direction. Its
finding **F6**: two of the fifteen, `idx_ref` **96** (`c6e67890a9dc…`) and **152**
(`245862556318…`), have **half-hop final states** — mover displacement 1.323 Å / 1.312 Å =
0.53 × 1NN, final-state mover snap residual **1.190 Å / 1.204 Å** — are the **only two `unpaired`
classes in the list**, and their re-relaxed final states sit +0.787 eV / +0.796 eV above the
initial with ~5 meV reverse barriers, i.e. **shoulders, not basins**. That packet names them as
"a concrete instance of the P0-only residual-gate item (token verdict §5)" and recommends a veto
with the reason recorded as off-lattice final state.

Three things this adds. (i) The signature is identical to §4.1's casualties (0.53 × 1NN, ~1.2 Å
final residual, `unpaired`) across two independent corpora. (ii) It supplies the piece §4.1
cannot: for these instances the "final state" was measured and is **not a basin at all** — which
bears directly on R3, because there is no lattice final state for a re-search to converge to.
(iii) `unpaired` flagged 2/2 there as well, which bears on R5. Cost recorded there: 3.13 firings
(0.98 % of that run's flux); neither class appears anywhere in the 60-run production NiCr corpus.

## 8. Rulings requested

Numbered like the 2026-07-29 precedent's §9 so that whatever Stephen decides can be recorded in
the same form. Every "recommendation" below is the author's, offered for acceptance or override.

### R1 — Adopt the symmetric gate, and in which variant?

| option | what is discarded | prerequisite (§5) | collateral |
|---|---|---|---|
| **R1-a** reject D6 | nothing | **not discharged** — recovered bake stays blocked, or bakes 73.5 % artifact flux | none, but §2's structural blindness stands |
| **R1-b** naive `max(res_P0,res_P2) ≥ 0.5`, one reason code | 4,858 events | fully discharged | 3,687 events (75.9 %) discarded for a *different* defect, incl. **469 ordinary complete 1NN hops**; two defects conflated in the ledger |
| **R1-c** naive discard, **two** ledger reason codes | 4,858 events | fully discharged | same 469 ordinary hops discarded; but the two populations stay separable for audit and for a future re-anchoring fix |
| **R1-d** attributable-only discard **+ frame-anchor bucket quarantined** under its own reason | 1,171 discarded, 3,687 quarantined | fully discharged (§5, col. 3) | 14 mixed classes over-quarantined (NiCr 10, 66 clean members, 0.00 flux; NiFe 4, 4 clean members, 3.40 flux) |
| **R1-e** attributable-only, frame-anchor bucket untouched | 1,171 events | **not discharged** (36/43, 64.7 %) | none, but D6's stated purpose is unmet |

**Recommendation: R1-d.** The 75.9 % number is the argument. Three quarters of what a naive
symmetric gate catches is not "the mover never arrived" but "the whole registry is displaced" —
a defect with its own signature (`static_max_residual(P0)` median 1.208 Å; identical drift in both
snapshots; the mover unexceptional in 91.8 %), already visible on the *initial* state in 98.7 % of
cases, and already partly handled by the 2026-07-29 `WILDCARD` mask. Discarding it under a
`MOVER_OFFLATTICE` label would put a wrong reason on 3,687 ledger rows and destroy 469 ordinary
complete 1NN hops that the attributable set contains **zero** of. Quarantine rather than discard
for that bucket keeps the prerequisite discharged (quarantined classes are excluded and counted by
`translator_v2`) while preserving a population that a better frame anchor might recover — its
flux cost is small either way (0.345 % NiCr / 0.010 % NiFe).
**If Stephen prefers one mechanism over two, R1-c is the fallback** — same discharge, simpler
enforcement, at the price of the 469 ordinary hops and a permanent loss of the frame-anchor
population. R1-b is not recommended: it costs the same as R1-c and buys a less useful ledger.

### R2 — Threshold: 0.5 Å or 0.55 Å?

Evidence: §6. The measured/graduated verdict is invariant across 0.4–0.6 Å (NiCr's 2 flips sit on
a 1.02 Å plateau; NiFe's zero holds above 0.1746 Å), and the flux removed barely moves. The only
substantive argument for a move is NiFe's **anti-valley**: a 2.95× pile-up in 0.50–0.55, so 0.5
cuts *through* a distinct sub-population rather than between two.

- **R2-a — keep 0.5 Å.** One constant, three named uses (`mover_snap_tol`, `bystander_mask_tol`,
  and now the P2 side), consistent with 2026-07-29 §11, and directly comparable with every
  existing catalogue. Cost: 419 NiFe members are decided by a cut placed inside their own mode.
- **R2-b — 0.55 Å for the P2 side only.** Spares that sub-population; costs a second constant and
  an asymmetric gate that is harder to explain.
- **R2-c — 0.95 Å** (the measured distribution minimum in both alloys). Cleanest separation of
  shoulder from half-shift mode; but it sits only **11 mÅ below** the smallest surviving half-shift
  residual in NiCr (0.9609 Å), so the §5 prerequisite would hold by a hair instead of by 2×, and
  any future corpus with a slightly tighter half-shift would breach it. Not recommended for that
  reason.

**Recommendation: R2-a (0.5 Å).** The decision is threshold-independent where it matters; a second
constant buys bookkeeping tidiness in one alloy and costs explanatory clarity everywhere. If
Stephen wants the pile-up spared, R2-b is defensible and changes no headline number.

### R3 — Disposition of the two NiCr measured casualties

They are `approved`, `harvested_pair`, reproducible (0.7727–0.7800 eV), and worth 0.0159 % of
catalogue flux — but their final states are not lattice states.

- **R3-a — discard via the ledger** (they simply cease to exist; the measured set drops 32 → 30).
  Honest and automatic; loses two barriers that were genuinely measured.
- **R3-b — veto overlay with the reason recorded as off-lattice final state**, i.e. keep them
  visible and permanently excluded, matching what the 15-class review packet recommends for its
  own two instances (§7) and what the existing `vetoes_v3.toml` mechanism already supports.
- **R3-c — re-search them.** Two targeted jobs is a trivial cost next to a 200-job leg, **but the
  evidence argues it will not work**: the packet's measured analogues are shoulders with ~5 meV
  reverse barriers, not basins, so there is no lattice final state to converge to; and both
  casualties are `unpaired`, which `rc_prep`/`rc_accept` handle poorly (the same reason the D3
  "wrong-mover" trio is described as unrecoverable by any search change). Note also that one of
  the two is already ν₀-placeholder-contaminated.

**Recommendation: R3-b**, with R3-a as an acceptable simplification. A veto keeps the two classes
auditable, records *why* two measured classes vanished, and cross-references the same reason code
the review packet wants to use — one vocabulary for one defect across both corpora. R3-c is
recommended only if Stephen wants the negative result on record.

### R4 — Enforcement and migration mechanics

Follows the 2026-07-29 precedent (§5/§8) unless overridden; the mechanics are set out in §9. What
needs a ruling:

- **R4-a — enforcement point.** Recommended: event-level drop at build, exactly as 2026-07-29 §5
  (a failing row never joins a class; mixed classes survive with cleaned member lists and an
  unchanged `class_id`; wholly-bad classes never form), with the sidecar ledger
  `<out>_discarded.parquet` extended by the new reason code(s) and the conservation identity
  `n_rows = n_projected + n_raised + n_discarded` preserved. Rejected alternatives are the same
  three the precedent rejected — QC quarantine (wrong granularity both ways), a per-member mask
  column (most code for least difference), translator-side skip (leaves rate aggregates polluted).
- **R4-b — CANON / catalogue version bump: yes or no?** Recommended **no CANON bump**. D6 changes
  *which rows exist*, not the canonical geometry a `class_id` hashes, so surviving ids are
  unchanged — and the 2026-08-14 campaign demonstrated empirically that content-based ids carry
  vetoes, measured stamps and review lists forward bit-exactly with **no `remap`** ("rebuild
  classes 584 / phase2 classes 584 / class_id sets identical: True / max |dEa_rep|: 0.0"). This is
  the sharpest difference from 2026-07-29, whose bump was forced by §6 masking changing canonical
  *content*. A catalogue-schema (parquet) version note recording the new gate in the conditions
  stamp is still warranted so old and new catalogues are distinguishable — with one verification
  caveat (§14): today's stamp **cannot** back a guard. `build` records `mover_snap_tol` only in
  free-text parquet schema metadata that `qc` and `merge` drop on the way through (all three
  /data candidates carry **no** gate-policy record at all), and schema metadata does not survive
  a plain pandas round-trip. The record needs §13's machine-readable, forward-carried form to
  have teeth. **If Stephen prefers the loud option**, a bump is available at the cost of a full
  `remap` campaign (§10).
- **R4-c — remap/rebuild scope.** Recommended: rebuild **all 120 runs** from their reference
  tables, re-QC, re-merge per alloy — the direct analogue of the 2026-07-29 slice-2 rebuild (that
  memo planned 47 runs; the executed migration covered 53). Cheaper alternatives exist (NiFe-only;
  or defer until the next campaign) but leave the
  two alloys on different gate policies, which is exactly the cross-policy merge hazard the
  version prefix exists to prevent.
- **R4-d — timing.** Recommended: **before** any NiCr re-search leg. The gate removes 2,348 NiCr
  `pending_research` classes; that is search budget not worth spending, and the leverage ladder
  (`targets_nicr.csv`) would be re-ranked by the rebuild.

### R5 — Should `pair_status = unpaired` become a standing prescreen/flag?

Measured honestly, corpus-wide:

| | NiCr | NiFe |
|---|---|---|
| P(flip \| `unpaired`) | 59.2 % (838/1,416) | 49.4 % (79/160) |
| P(flip \| `unpaired`), non-quarantined | 70.4 % | 55.2 % |
| P(flip \| `linked`) — base rate | 2.9 % | 3.2 % |
| enrichment | ~20× | ~15× |
| recall (share of flips that are `unpaired`) | 29.3 % | 11.0 % |

So: within the measured set it was a **perfect** predictor (2/2, 0 false positives among 30), and
it flagged 2/2 in the review packet as well — but on the full corpus it is a ~20× enrichment with
**low recall**. It is an excellent cheap prescreen and a bad substitute for the gate.

- **R5-a — adopt as a prescreen on the measured/graduation pipeline** (flag `unpaired` targets
  before spending search budget, and flag any `unpaired` class carrying a `harvested_pair` stamp
  for review). Costs one column read; would have caught both casualties at zero measurement cost.
- **R5-b — additionally surface it as a QC flag corpus-wide** (flag only, never a gate).
- **R5-c — no change**; the symmetric gate subsumes it.

**Recommendation: R5-a**, explicitly *as a prescreen and not as a gate* — the recall numbers
forbid promoting it further. R5-b is a low-cost extra if Stephen wants the corpus-wide view.

## 9. Enforcement mechanics, if R1 is adopted

### 9.1 The gate and the ledger

Pipeline order inside `project_event` is unchanged except for one added computation: project →
snap P0 **and P2** → detect movers → **mover gate on `max(res_P0, res_P2)`** (ledger) → mask
static bystanders → `compute_depth_sig` → canonicalise. `P2` and `s2` are already computed in
`project_event` (`event_projection.py:829-831`), so the residual and the static-substrate
discriminator are a few lines; no new inputs are needed from the reference table.

Ledger reason codes, under each R1 option:

- **R1-c**: `MOVER_OFFLATTICE` (unchanged, P0 side) · `MOVER_OFFLATTICE_P2` (attributable) ·
  `FRAME_ANCHOR_P2` (non-attributable) · `FRAME_UNFIT` (unchanged).
- **R1-d**: the first two and `FRAME_UNFIT` are ledger discards; `FRAME_ANCHOR_P2` becomes a **QC
  quarantine reason** on the class instead, joining the existing sticky-quarantine vocabulary.
- **R1-b**: one code, `MOVER_OFFLATTICE`, extended to the P2 side — simplest and least
  informative.

Both `res_P0` and `res_P2` (mover and static maxima) should be persisted as additive catalogue
columns regardless of the ruling, so §2-style audits never need a re-projection again — the same
precedent as 2026-07-29 §11.

### 9.2 What happens to the frame-anchor population under each ruling

- Under **R1-c** it is discarded with a truthful, distinct reason — recoverable only by re-running
  a future re-anchored build against the ledger's lineage.
- Under **R1-d** it is quarantined: excluded from every bake (`skipped_quarantined`), retained in
  the catalogue, and directly re-openable if the frame anchor is ever changed. The 14 mixed
  classes (NiCr 10 / NiFe 4) are over-quarantined by this — a class with some clean members loses
  them all. Their combined class flux is 3.40 firings (NiCr 0.00 + NiFe 3.40), i.e. negligible.
- Under **R1-b** it is swept into `MOVER_OFFLATTICE` and becomes indistinguishable from the D6
  target in every downstream audit. This is the option §3.2 argues against.

### 9.3 Migration

1. **No `CANON_SCHEMA_VERSION` bump** under R4-b as recommended; the conditions stamp records the
   new gate and its threshold(s). If a bump is ruled instead, the 2026-07-29 §8.3 lineage
   `remap` path applies unchanged (`pylatkmc.ingest.cli remap` exists and was exercised in the
   slice-2 migration).
2. **Rebuild all 120 runs** from `production_NiCrFe/runs/<tag>/reference_table.pickle` with the new
   policy, then re-QC and re-merge per alloy (`run_full_campaign.sh` is the template; flags pinned
   to the phase-2 baseline).
3. **Stamp carry-forward.** 30 of 32 NiCr measured and **180/180** NiFe graduated survive on
   unchanged content-based ids; `vetoes_v3.toml`, the action review list and `review_list_v3.csv`
   carry forward the same way. Only the 2 casualties need an explicit disposition (R3), and every
   old stamped class must end as *carried* or *explicitly reported unmatched with a reason* —
   proved by the rebuild report, not assumed.
4. **Shrunk classes change content.** 48 NiCr + 5 NiFe classes get new member lists, hence new
   `Ea_rep` / `Ea_std` / `n_eff` / `barriers_eV` / `nu0_*_list_hz`; QC re-runs on merged member
   lists, so their quarantine status can move. None of them is measured.
5. **Reciprocity partner loss reaches classes whose members never change** (verification finding,
   §14). Backward linkage is resolved at build time against the post-drop survivor set
   (`event_class.py:1221-1223, 1258-1281`), so a class can keep every member yet lose its
   `backward_class` to a flip — after which `qc.py`'s `partner is None → continue` silently skips
   its reciprocity screen. Measured at 0.5 Å: **1,607 NiCr + 505 NiFe** surviving classes lose
   their partner this way (1,598 / 504 of them otherwise untouched; **0 measured or graduated in
   either alloy**, so R3/§4 are unaffected). Three consequences: the migration report must count
   partner-loss separately from member-loss; the tol-1e-6 reciprocity band is evaluated on
   exactly this screen, so **ruling 3.6's evidence base shifts — re-measure the band
   post-rebuild before deciding 3.6 on it** (this qualifies any plan to fold the two into one
   re-merge); and post-migration `unpaired` acquires a second, unrelated cause, so the R5
   prescreen numbers must always be quoted from pre-gate catalogues.
6. **Proclists — two committed models now consume EventClass catalogues** (supersedes the
   2026-07-29 statement that none did; both have been committed since).
   `models/nife_v2_scratch` (`b3df55e`) bakes the 180 graduated NiFe classes — 0 affected, so its
   proclist is expected **byte-identical** after the rebuild (verify, don't assume).
   `models/nicr_v2_scratch` consumes the 2026-07-29 sweep catalogue; its casualty check was
   **executed under verification** rather than deferred (all 29 of that sweep's runs sit inside
   the 120-run measurement): **2 of its 22 baked classes flip** — `2986630951ae…` (2/2 members,
   Ea 0.7490) and `ac2488f17a71…` (3/3, Ea 0.7789), the same two physical half-shift events as
   §4.1's casualties under their older-CANON ids — occupying **80 of its 2,400 committed procs
   (3.33 %)**. Under any adopting ruling its proclist regenerates and shrinks (2,400 → 2,320
   procs, 22 → 20 `v2_class_ids`). `ni_example`'s v0.3 family-CSV path must stay
   **byte-identical** (validation gate).

## 10. Costs

**The rebuild campaign** (R4-c), from the measured 2026-08-14 campaign rather than an estimate:
build throughput **88 ms/row** (878 rows in 77.6 s, single core). All 120 runs = 132,840 rows ≈
**3.3 h serial, ~25 min at 8-way** under the ≤21-core budget; per-run artifacts ~700 M (the actual
campaign tree is 732 M); merges are minutes. The 2026-07-29 precedent's slice-2 analogue was a
53-run rebuild plus a full lineage `remap`; this one is 120 runs but, under R4-b as recommended,
**no remap** — the expensive half of the precedent's migration does not recur.

**What is *not* re-spendable:** the NiFe graduation campaign (180 classes) is untouched, so no
re-search work is invalidated by D6. The NiCr measured line loses 2 classes (R3). The gate removes
2,348 NiCr `pending_research` classes *before* any search budget reaches them — the timing
argument in R4-d is a saving, not a cost.

**Costs of the promotion D6 unblocks** (verdict §10.4 — recorded here because this is the memo
that carries the prerequisite): enabling the recovered classes grows
`PYLATKMC_V2_MAX_REACH_IJ` **8 → 10** on full NiFe (`reach_k` unchanged at 5), which *tightens*
the runtime's anti-aliasing startup guard — a slab configuration that starts today could be
refused after an `include_unstamped` bake; and oriented procs grow **232,000 → 266,768 (+15.0 %)**
with AvailSites memory O(n_procs × n_sites). Neither binds any shipping model today.

**Cost of not deciding:** the recovered-class bake stays blocked (verdict §10.6), and every future
NiCr campaign is planned against a target list that includes 2,348 classes the gate would remove.

## 11. What this memo does not change, and what is out of scope

- The five other gates (G1, G2, G4–G6), the QC screens, sticky-quarantine semantics, the
  permissive `V2_PRED_EMPTY` matcher and the strict delta-`Vacant` rule.
- The 2026-07-29 mover-keyed *P0* gate and the `WILDCARD` static-bystander mask — both stand
  exactly as approved. D6 adds a snapshot; it does not revisit which atom the gate keys on.
- **Extending the bystander mask to P2 is explicitly out of scope.** It is the natural sibling
  question (the frame-anchor bucket is precisely a P2 bystander problem), but masking changes
  canonical *content* and would force the full CANON bump + remap that R4-b avoids. Recorded as a
  separate item, not folded in.
- **Re-anchoring the local frame** (so `res_P0` is not structurally zero for seed movers) —
  the deeper fix suggested by §2. It would change every `class_id` and is a far larger decision;
  D6 is the cheap gate that makes the current anchor safe, not a replacement for it.
- Parked sibling items, untouched and unblocked by this memo: tol ruling 3.6 (reciprocity band —
  NiCr 10,699 classes / 38.30 % of corpus flux; NiFe 3,603 / 44.75 %), the 15-class review (§7
  overlaps it only in the two named instances), D1/D2/D3/D5 of the NiFe brief, the 22 same-action
  double-count collision pairs, and the V4 ν₀-placeholder gate.

## 12. Revisit triggers

1. **A mixed-geometry campaign** (bulk voids / GBs alongside surfaces, or higher solute fraction).
   Every fraction here is measured on 5 at.% slabs; the 87.49 % seed-mover share and the
   half-shift populations are geometry-dependent.
2. **A frame re-anchoring change.** If the anchor stops being the seed's P0 position, §2's
   structural argument dissolves and the frame-anchor bucket (75.9 % of the naive catch) should be
   re-measured before any of it is discarded or quarantined for good.
3. **Evidence that a half-shift final state is physical**, e.g. a re-search that converges to a
   genuine basin at ~0.5 × 1NN (a split interstitial or a crowdion-like configuration). The §7
   instances measured shoulders with ~5 meV reverse barriers, but only n = 2, on one corpus.
4. **Any bake that enables recovered classes**, which must re-check §5's coverage against the
   catalogue in force at that time — the 43/43 result is measured on the 2026-08-14 merges.
5. **A NiCr graduation leg**, after which the measured set is no longer 32 classes and the
   2-casualty arithmetic in §4.1 must be recomputed rather than quoted.

## 13. Implementation notes (non-binding, only if R1 is adopted)

- `GateThresholds`: add `mover_snap_tol_p2: float = 0.5` (or reuse `mover_snap_tol` if R2-a and a
  single constant are ruled) and, under R1-d, `frame_anchor_tol: float = 0.5` for the static
  discriminator. Conditions stamps must record whichever are in force.
- The discriminator is one expression, already validated in the measurement harness:
  `res_P2 >= tol and static_max_residual_P2 < tol`
  (`.scratch/phaseC/symmetric_gate_2026-08-15/measure_p2.py:295-297`).
- Tests to add: (i) an event clean in P0 and off-lattice in P2 must FAIL — the regression that
  would have caught this class of defect; (ii) a seed-mover event must be *capable* of failing
  (the §2 blindness regression); (iii) attribution unit test (mover off-lattice + clean substrate
  → attributable; both off → not); (iv) ledger conservation with the new reason codes;
  (v) unchanged-`class_id` round-trip for a shrunk class; (vi) two-seed byte-determinism of the
  rebuilt catalogue; (vii) `ni_example` proclist byte-identical.
- Extend `ReftableBuildReport` with per-reason counters for the new code(s): the reason split at
  `reftable.py:199-202` is a binary `if FRAME_UNFIT / else mover_offlattice`, so a third literal
  would silently fold P2 drops into `n_mover_offlattice` — and into the build conditions stamp
  (`cli.py:486-488`) — making §9.3's expected-delta checks unverifiable from the stamp.
- The R4-b gate-policy record must be **machine-readable and forward-carried**: a first-class key
  (e.g. `gate_policy = "symmetric_P0P2_v1"`) written by `build`, carried through `qc` (today
  `cli.py:583-591` writes only its own stamp and drops the build's) and `merge`, with
  **refuse-by-default** in `merge`/`remap` on an absent or mismatched policy (absent ⇒ treat as
  `P0_only`). Free-text `--conditions` cannot back the guard. Downstream artifacts that are not
  policy-guarded — flux CSVs, review lists, flag registries — must be regenerated after the
  rebuild, not carried.
- The `gate_g3_snap_residual` docstring and `reftable.py`'s ledger paragraph both need rewriting
  to name the snapshot, whichever way R1 goes.

## 14. Adversarial verification addendum (2026-08-15, second session)

Before being put in front of Stephen, this memo was adversarially verified by a 4-lens Opus
fleet commissioned from a second session (~568k tokens, 143 tool calls): an **independent
numeric re-derivation** working only from the 120 per-run parquets, the /data catalogues and the
flux CSVs (never this memo's aggregates); a **transcription audit** of every number and section
reference against its source; a **live-source audit** of every implementation claim against the
checkout at `5ff4bfc`; and a **logic skeptic** attacking the recommendations. Outcome:

- **Reproduced bit-for-bit from raw inputs:** the corpus counts (97,976 / 1,978 / 3,853 /
  2,860 + 48 · 34,864 / 235 / 1,005 / 715 + 5); the 2-of-32 casualties with member-level
  residuals and both `unpaired` stamps; 0-of-180 NiFe at max res_sym 0.174619; the flux shares
  (2.6243 % / 0.0338 % of totals 116,099.7 / 120,291.2) and casualty flux 18.407 + 0.085; the
  §3.2 attributability split (1,171 / 3,687 / 98.73 %); the §5 discharge chain (2,176 visible /
  43-of-top-100 / 73.5 % / 43-of-43 / 73.7 %); 100 % event-level half-shift capture with min
  surviving residual 0.9609 / 1.0090 Å; the full 0.4 / 0.5 / 0.6 sensitivity table; the R5
  precision/recall crosstab; and the (0.1788, 1.2006] Å plateau.
- **Corrected inline as a result of the pass:** the §3.1 flux-asymmetry attribution (77.6× is
  not §10.3.4's quantity; on §10.3.4's own metric the ratio is 1.63×); §5's "all recovered flux"
  scoped to *visible* (58.9 % of the total); §6's NiCr density ratio (≈0.98 on half-open bins)
  plus the pile-up attribution (NiFe's 0.50–0.55 mode is 100 % non-attributable — the
  frame-anchor/relaxation population, not threshold noise); the new §9.3.5 (reciprocity
  partner-loss cascade: 1,607 NiCr + 505 NiFe surviving classes silently lose their reciprocity
  screen via `qc.py`'s `partner is None → continue`, with the ruling-3.6 sequencing and R5
  confound that implies); and §9.3.6 (both v2-scratch models are **committed**, and the
  `nicr_v2_scratch` casualty check was executed rather than deferred — 2 of its 22 baked classes
  flip, 80 of 2,400 committed procs).
- **Confirmed against live source:** `class_id` membership-independence (the R4-b premise),
  `DiscardReason` and the ledger conservation identity, the two 0.5 Å `GateThresholds`
  constants, P0-only residual computation at `event_projection.py:832-835`, `measure_p2.py`'s
  P2-in-P0-frame convention, and §11's coupling (extending the mask to P2 ⇒ CANON bump).
- **Attacks that did not land:** direct D1↔D6 coupling via reverse partners (0 of the 180
  graduated and 0 of the 30 surviving measured classes lose a partner); the
  half-shift-states-might-be-real objection (the only measured analogues — §7's F6 pair — are
  shoulders with ~5 meV reverse barriers, not basins; kept honest as revisit trigger 3); and
  threshold sensitivity of any headline number.

A condensed same-day draft (`SYMMETRIC_GATE_DECISION_2026-08-15.md`, single-recommendation
form, written independently by the second session) was superseded by this document and deleted
to keep one decision surface; everything it added that survived verification is folded in above.

---

### Appendix — provenance

- **Inputs, read-only and mtime-verified post-run:**
  `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full` (2026-08-15 01:50),
  `/home/kerr/pykmc/production_NiCrFe/runs` (2026-08-07 21:03).
- **Measurement:** 120 per-run parquets in
  `.scratch/phaseC/symmetric_gate_2026-08-15/p2_measure/{NiCr,NiFe}/` (97,976 + 34,864 = 132,840
  rows, 41 columns incl. `mover_offlattice_P2_attributable`), produced by `measure_p2.py`;
  aggregated by `gate_impact.py` into `gate_impact_by_class.parquet` (90,472 rows × 39 cols),
  `gate_impact_raw.json`, `gate_impact_summary.md`; validated by `validate_p2.py`
  (`validation_summary.csv`) and `check_nicr_counts.py` / `verify_nife_run.py`.
- **Flux:** `class_flux_nicr.csv` (`.scratch/phaseC/research_campaign_nicr/`, adversarially
  verified — `NICR_FLUX_RESTATEMENT_2026-08-15.md` §9) and `class_flux_nife.csv`.
- **Numbers in this memo** were re-derived from the parquets for this memo rather than copied from
  `gate_impact_summary.md`; §§2, 3.2, 5 and R5 contain measurements that appear in no prior
  artifact. Three figures are stated here more precisely than in the source summary: the measured
  casualty share is **6.25 %** of the NiCr measured class count (7.04 % of measured-set flux);
  the NiCr/NiFe flux-exposure ratio is **77.6×** (2.6243 / 0.0338); and the NiCr threshold plateau
  closes at **1.2006 Å**, not 1.2009 Å — a whole-class flip is bound by the class's *minimum*
  member residual, and class `9e29216860611db6…` has members at 1.2006 / 1.2008 / 1.2009 Å.
- **Scope of the bit-for-bit validation**, stated exactly: `res_P0` reproduced the production
  ledger, per-run catalogue and merged catalogue with max deviation 0.0 Å on **one validated run
  per alloy** (four independent checks each); row conservation and join integrity (0 unmatched
  members, 0 duplicate keys) hold across **all 120 runs / 132,840 events**.
