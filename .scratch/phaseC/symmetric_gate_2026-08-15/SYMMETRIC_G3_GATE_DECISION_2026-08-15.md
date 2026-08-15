# Symmetric mover-keyed G3 projection gate (canon D6) — decision memo

**Status: DECISION REQUESTED — 2026-08-15. Nothing here is settled; every ruling below is
Stephen's.** This memo presents the first full-corpus measurement of the symmetric-residual
gate proposed as `TOKEN_MISMATCH_VERDICT_2026-08-15.md` §5 and carried to the brief as **D6**,
states what adopting it would cost, and records a labelled recommendation for each open ruling.
It does **not** authorise implementation: **no gate implementation was committed** — nothing was
built, merged, migrated or promoted against any recommendation below. The *measurement* behind it
is complete and committed (branch `ingest` @ `5ff4bfc`; see the conditions stamp);
`/data/pylatkmc_ingest/` and `production_NiCrFe/runs/` were read-only throughout.

**Supersedes an earlier same-night draft** of the same D6 decision
(`SYMMETRIC_GATE_DECISION_2026-08-15.md`, 05:20 — since **deleted**, so exactly one D6 decision
surface exists); everything load-bearing it carried is folded in here (§14.3).

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

One column of the harness's own count check reads `False` for **all 60 NiCr runs**, and it is
**benign** — recorded here so an auditor opening `p2_measure/NiCr_count_check.csv` is not left to
guess. `check_nicr_counts.py`'s `match_build` compares the measurement's row count against
`n_raw + n_discarded`, but `n_raw` counts per-run **classes**, not member rows: for
`NiCr…T300_10vac`, 828 classes cover 844 `idx_ref`s, plus 59 ledgered `MOVER_OFFLATTICE` = 903 =
`n_ref` exactly. The check is mis-specified, not a conservation defect; the conserving column is
`match_ref`, which is 60/60 in both alloys.

---

## 1. The question

Today's G3 gate (approved 2026-07-29 §4) is

```
G3 FAIL  iff  frame_unfit  OR  mover_max_residual(P0) >= 0.5 Å
```

— computed on the **initial** snapshot only. The gate itself is `gate_g3_snap_residual`
(`event_class.py:894-934`); the P0 residual array it reads is built at
`event_projection.py:832-835`. D6 asks whether it becomes

```
G3 FAIL  iff  frame_unfit  OR  max( res(P0), res(P2) ) >= 0.5 Å      (over movers)
```

i.e. whether an event whose mover never *arrives* at a lattice site is as unrepresentable as one
that never *starts* at one. Six things need a ruling: **R1** adopt or not, and under which
enforcement variant; **R2** the threshold; **R3** what happens to the two NiCr measured classes it
would cost; **R4** enforcement and migration mechanics; **R5** whether `pair_status = unpaired`
becomes a standing prescreen; **R6** whether the audit/review protocol gains a final-state
residual column. §§2–7 are the evidence; §8 is the ruling sheet; §§9–13 are
mechanics, costs, scope and triggers; §14 records the two adversarial verification passes this
memo went through before being put forward.

Two facts frame the stakes. Verdict §10.6 promoted this from "unranked follow-up" to a
**prerequisite for any bake that enables the recovered (token-mismatch) classes** — so an
`include_unstamped` bake or a future multi-mover graduation is blocked until it is settled either
way. And it does **not** gate D1: the NiFe graduated set is untouched (§4.2).

## 2. The structural argument — today's gate is blind on 87.5 % of the corpus by construction

This is the strongest evidence for D6 and it appears in none of the existing memos.

`fit_local_fcc` pins the local frame's **origin to the seed atom's P0 position**
(`event_projection.py:379-390`; the `LocalFrame` docstring, `:143-144`, states it outright: "the
seed snaps to `(0,0,0)` by construction"). Therefore, for any event whose single mover *is* the
seed, the mover's initial snap residual is not small — it is **zero for the seed atom by
construction, regardless of where that atom actually sits**.

Stated precisely, because the strength of the claim matters: the construction forces it for the
seed *atom*. It does not by itself force it for every mover atom of such an event —
`mover_max_residual(P0)` is a maximum over mover **atoms**, while `n_movers` counts mover
**pairs**, so the two need not coincide a priori. That they do coincide here is therefore an
**empirical result on this corpus, not an algebraic identity**: over the 116,216 single-mover
seed-is-mover events, `mover_max_residual(P0)` is exactly 0.0 on **116,216 of 116,216** (set
maximum 0.0). The conclusion is unaffected; the claim is that the gate is measured blind on this
corpus, and structurally *expected* to be.

Measured over the 132,840-row corpus:

| | count | share |
|---|---|---|
| events that are single-mover **and** seed-is-mover | 116,216 | **87.49 %** |
| …of those, `mover_max_residual(P0)` exactly 0.0 | 116,216 | **100 %** (set max = 0.0) |
| events with `n_movers == 0` (**both** gates vacuous) | 656 | 0.49 % |
| …of those, `max_residual(P2) ≥ 0.5 Å` | 638 | 97 % |
| …of those, `max_residual(P0) ≥ 0.5 Å` | 288 | 44 % |
| today's G3 firings, corpus-wide | 2,213 | 1.67 % |
| …on a multi-mover event | 1,954 | — |
| …on a non-seed mover | 439 | — (180 are both) |
| …on the 87.49 % single-mover-seed majority | **0** | **0 %** |

So the mover-keyed P0 gate can only ever fire on multi-mover events or non-seed movers — and, as
the next paragraph adds, there is a third population on which it cannot fire at all. On the
overwhelming majority of the catalogue it is not merely permissive — it is *structurally
incapable* of failing.

**A third blind spot, which D6 does not close either.** 656 events have `n_movers == 0`. Because
`mover_max = float(np.max(residuals[mover_atoms])) if mover_atoms else 0.0`
(`event_projection.py:1112`), a zero-mover event scores 0.0 on the mover key by definition — so
today's G3 **and** the proposed symmetric gate are both **vacuous** on them, even though 638 of the
656 (97 %) carry `max_residual(P2) ≥ 0.5 Å` and 288 carry `max_residual(P0) ≥ 0.5 Å`. The
mitigation is downstream and not this gate: `translator_v2`'s **counted empty-delta skip** — a
zero-mover event produces an empty delta and is skipped with a counter rather than baked — which
is why these rows do not reach a proclist. Stating it explicitly rather than leaving it to be
inferred, because "the gate can only fire on multi-mover or non-seed events" is incomplete
without it. These 656 rows are also excluded from §3.2's hop table (they have no mover hop to
bin).

The final state carries no such degeneracy for the events that *do* have movers: within that same
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
verification (§14.1): this is **not** the quantity verdict §10.3.4 warned about. §10.3.4 hedged
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

Two label caveats on that table. (i) The **whole-corpus column sums to 130,168, not 132,840**: it
omits the **2,016 events below 0.4 × 1NN** and the **656 zero-mover events** of §2, neither of
which has a binnable mover hop. The attributable (1,171) and non-attributable (3,687) columns do
sum exactly. (ii) The `0.4–0.7` row is labelled *half-shift*, but the measurement's own definition
is `min(hops) < 0.7 × 1NN` (`measure_p2.py:267`), so the **`< 0.4` bin is half-shift too** — the
row therefore *understates* corpus half-shift, which totals **2,931 NiCr + 335 NiFe = 3,266**
events, of which 2,016 sit below 0.4 × 1NN. Nothing downstream in this memo uses the corpus column
as a denominator; §5's capture results are computed on the half-shift population directly.

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
   `6698383570156747695` (hex `5cf5705e14817baf`, which is how `action_review.csv` prints it),
   carrying **45.409 % of NiCr corpus flux**. That action sits inside the `V1NN_inplane`
   **archetype** `4972478298379930765`, which carries **98.967 %** of NiCr corpus flux across its
   two actions — the sibling action `2629093754657442946` carries the other 53.558 %. (Corrected
   under second-pass verification: an earlier form of this line attached the archetype's 98.97 %
   to the action, overstating the implicated action's concentration by 2.2×; §2 of
   `NICR_FLUX_RESTATEMENT_2026-08-15.md` attributes the 98.97 % to the archetype.) The catalogue
   claims a complete lattice-to-lattice hop for an atom that moved 0.53 × 1NN.
5. **Independent flags on the same action.** 8 of the 11 rows in the campaign's standing
   `action_review.csv` (action-pair-mismatch, ruling 9) involve that same `action_id`. The two
   casualties are not themselves on that list — being `unpaired`, they have no partner to
   disagree with — but the action is already a known projection trouble spot.

Kinetic magnitude of the loss: 18.492 firings = **0.0159 % of NiCr catalogue flux**, 99.5 % of it
in the first class. The real cost is curational: **2 of 32 = 6.25 % of the measured class count**
(7.04 % of measured-set flux) would have to be withdrawn.

One clarification that is deliberately **not** a discount. `bcbdc9625341d6f7…` carries a
**1.0e12 Hz placeholder ν₀** on one of its two members — 1 of the 5 casualty members, **20 %**,
against a **26.3 %** placeholder base rate over the NiCr production measured set
(`pylatkmc/.scratch/phaseC/research_campaign_nife/V4_NIFE_REVERIFICATION_2026-08-15.md` §6.1.3,
commit `09f518d`; the same figure reaches this memo one hop away via the D1 post-brief addendum).
The casualties are therefore *at or marginally below* the average contamination of the set they
come from, so the observation carries no information about their relative worth and no deduction
is taken from the 6.25 % cost. Recorded because an earlier form of this paragraph used it as a
discount. **Different defect, different memo:** D6 changes *which rows exist*; V4 changes *what
ν₀ a surviving row carries*. Neither implies the other, and neither is a reason to rule the other
way (V4 is parked separately — §11).

### 4.2 NiFe loses none of its 180 graduated classes

Zero flipped, zero shrunk. The whole set tops out at `res_sym = 0.1746 Å` — **2.86× below the
cut**; **class-level** median of per-class max `res_sym` 0.0207 Å (the member-level median over
the same 936 members is 0.0346 Å — both are far below the cut, but the bases differ and the
class-level one is quoted here); zero half-shifts; all 180 `linked`. The surviving 30 NiCr
measured classes top out at 0.1788 Å (2.80× below). **D6 does not gate D1.**

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

**Two bases, one line apart — quote the basis, not just the number.** The **73.5 %** in the
paragraph above is the share those 43 classes *carry*; the **73.7 %** in the table is the share
the gate *removes* across the whole visible recovered set (it removes those 43 and others outside
the top 100). In NiFe they are near-equal (73.45 % carried vs 73.70 % removed) and the conflation
is harmless; in NiCr they visibly differ (**45.49 % carried** by its 43 vs **48.46 % removed**),
so the two must not be swapped.

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

**There is no empty valley at 0.5 Å in either alloy.** The precedent's near-empty-valley result
(2026-07-29 §2: "moving the cut 0.4→0.5 changes 2 rows in 6,604") does not repeat here.

**That precedent measurement was not pure Ni** — corrected under second-pass verification, where an
earlier form of this line called it "the pure-Ni history" and then invented a composition
explanation for the difference. It was **NiCr Ni95Cr05**, over **6 runs**
(`onlattice_design/mover_vs_bystander_2026-07-29.py:17-23` lists them; the precedent's own
conditions stamp names a 29-run NiCr Ni95Cr05 merged catalogue). Composition is therefore not the
explanation. Two things actually differ: (i) **a different quantity** — that valley was measured on
the *mover P0* residual, this distribution is the *symmetric* (P0-or-P2) residual, and §2 shows
the P0 side is pinned to zero by the frame construction on 87.49 % of events, which is part of
what made the P0 distribution look cleanly bimodal in the first place; and (ii) **a different
corpus** — 6 runs then, 120 runs across two alloys now.

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
  (1.62 %) sit within ±0.05 Å. Verification adds the attribution (§14.1): the pile-up is **100 %
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

Bulk counts move ~1.5× per 0.1 Å step **in NiCr** (4,277 → 2,860 → 1,842 = 1.50×, 1.55×); NiFe's
steps are uneven (979 → 715 → 326 = 1.37×, then 2.19×), so the "~1.5×" is a NiCr statement, not a
joint one. **Flux and the headline do not move**: the kinetically heavy
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
| **R1-a** reject D6 | nothing | **not discharged** — recovered bake stays blocked, or bakes 73.5 % artifact flux | §2's structural blindness stands, quantified: **2.6243 % NiCr / 0.0338 % NiFe** catalogue flux keeps firing from events with off-lattice final states, **100 %** of half-shift classes stay bakeable, and the **4,161** seed-mover P2 failures stay invisible to every build-time gate |
| **R1-b** naive `max(res_P0,res_P2) ≥ 0.5`, one reason code | 4,858 events | fully discharged | 3,687 events (75.9 %) discarded for a *different* defect, incl. **469 ordinary complete 1NN hops**; two defects conflated in the ledger |
| **R1-c** naive discard, **two** ledger reason codes | 4,858 events | fully discharged | same 469 ordinary hops discarded; but the two populations stay separable for audit and for a future re-anchoring fix |
| **R1-d** attributable-only discard **+ frame-anchor bucket quarantined** under its own reason | 1,171 events discarded; 3,687 events quarantined — at **class** level that is 2,000 flipped + 10 shrunk NiCr and 639 + 4 NiFe classes | fully discharged (§5, col. 3) | 14 mixed classes over-quarantined (NiCr 10, 66 clean members, 0.00 flux; NiFe 4, 4 clean members, 3.40 flux) |
| **R1-e** attributable-only, frame-anchor bucket untouched | 1,171 events | **not discharged** (36/43, 64.7 %) | none, but D6's stated purpose is unmet |
| **R1-f** flag, don't drop — persist `res_P2` / `static_max_residual_P2` and raise a QC flag; discard nothing | nothing | **not discharged** — a flag does not stop a bake | zero-cost, fully reversible, no rebuild; but 2026-07-29 §6 is the standing precedent *against* flag-only |
| **R1-g** extend the `WILDCARD` bystander mask to P2 instead of gating (the direct fix for the 75.9 %) | nothing on the frame-anchor axis — masking replaces gating there | not measured; the frame-anchor bucket ceases to be a gate question | changes canonical **content** ⇒ forces the CANON bump + full `remap` that R4-b avoids; not costed in §10. Carried here as an option because §11 defers it on cost, not principle |

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

**R1-f deserves its own sentence**, because it is the only zero-cost, fully reversible variant and
because §9.1 already proposes persisting both residual columns *regardless of the ruling* — R1-f is
that proposal plus a QC flag and nothing else: no rebuild, no migration, no ledger change, no class
removed. It does **not** discharge the §5 prerequisite (a flag does not stop a bake), which is why
it is not recommended. It is also, precisely, the option **Stephen overrode in 2026-07-29 §6** when
he chose the `WILDCARD` mask over flag-only; re-overriding that is his call to make, not the
author's to assume.

**Recorded, not recommended** (carried over from the deleted earlier draft, which listed it as a
considered-and-rejected alternative): *gate only the recovered / token-mismatch population.* It
partitions the corpus by discovery history rather than physics, violates one-policy-per-catalogue,
and would leave both §4.1 casualties untouched — they are not recovered classes.

### R2 — Threshold (0.5 Å, 0.55 Å, or another), and does the discriminator's tolerance follow it?

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
- **R2-d — 0.45 Å.** Named in §6's prose ("moving it to 0.45 costs little" for NiFe) but carried by
  no option until now, so it is added for completeness. It *tightens* rather than loosens, so the
  §5 prerequisite and the measured/graduated verdict are untouched (both hold across 0.4–0.6 Å).
  Its bookkeeping cost sits between the 0.4 and 0.5 rows of the sensitivity table above; 0.45 was
  not measured exactly, so no figure is quoted for it here.

**A per-alloy threshold is a further option, and the evidence does not rule it out.** §6's own
finding is that the two distributions differ *qualitatively* — NiCr a flat shoulder straight
through the cut (density ratio ≈ 0.98), NiFe a **2.95× anti-valley pile-up** just above it — so one
constant for both alloys is a choice, not something the data forces. Against it: two constants,
per-alloy catalogues that are no longer directly comparable, and a policy stamp that must record
both (§13). The author does not recommend it and did not cost it; it is recorded so the option is
visible rather than absent.

**A second policy constant rides on R2.** §3.2's attribution discriminator carries its own
tolerance — the `< 0.5 Å` static-substrate side, hard-coded as `frame_anchor_tol` in the
measurement harness (`measure_p2.py:295-297`) and proposed as a `GateThresholds` field in §13. If
R2-b moves the P2 gate to 0.55 Å, it is **unspecified whether the discriminator moves with it**.
The two are independent in principle (one asks "is the mover off-lattice", the other "is the
substrate clean"), but changing one alone re-partitions the attributable / non-attributable fork
that R1-d is built on. Author's proposal, overridable: whatever R2 rules, `frame_anchor_tol`
**stays at 0.5 Å**, and the conditions stamp records both constants explicitly.

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
- **R3-c — re-search them.** Two targeted jobs is a trivial cost next to a 200-job leg. *Against:*
  the packet's measured analogues are shoulders with ~5 meV reverse barriers, not basins, so there
  may be no lattice final state to converge to; and both casualties are `unpaired`, which
  `rc_prep`/`rc_accept` handle poorly (the same reason the D3 "wrong-mover" trio is described as
  unrecoverable by any search change). *For* — correcting an argument that ran backwards in an
  earlier form of this option: a re-search is exactly what would **replace** `bcbdc9625341d6f7…`'s
  1.0e12 Hz placeholder ν₀ with a real Vineyard value, so the placeholder contamination argues
  **for** re-searching, not against it (and it touches only one of the two classes, at a rate no
  worse than the measured-set average — §4.1).
  The deleted earlier draft recommended precisely this **in combination with R3-a**: *withdraw at
  rebuild and queue both for re-search*, treating them as targets rather than losses on the grounds
  that the barriers are reproducible and it is only the final-state encoding that is wrong. That
  combination is available and is recorded here as its own choice.
- **R3-d — re-harvest from the trajectory** (distinct from R3-c, and the option
  `REVIEW_PACKET_15CLASSES_2026-08-15.md` §4 actually recommends for its own two instances: "if the
  channel is wanted, re-harvest it from the trajectory rather than repair it"). Rather than
  re-running a saddle search out of a broken final state, go back to the source trajectory for a
  correctly-projected instance of the same channel. Cheaper than a search leg and does not depend
  on a lattice final state existing for *these* events; it does depend on the channel appearing
  elsewhere in the trajectory, which is unmeasured for these two.
- **R3-e — grandfather them, pending a sub-lattice representation.** Retain both — excluded from
  bakes but not withdrawn — against the **sub-lattice-subdivision escape hatch** that the
  2026-07-29 precedent §10.1 left open as Stephen's own deferral. These two classes are that
  hatch's **first concrete customers**: if a re-search or re-harvest ever confirms the saddles are
  real but the final states are genuinely interstitial-like, a sub-lattice site is the
  representation that would make them encodable at all. Cost: two classes stay in the catalogue
  carrying a lattice encoding now known to be wrong — which is what R3-b's veto avoids by recording
  the reason alongside them.

**Recommendation: R3-b**, with R3-a as an acceptable simplification. A veto keeps the two classes
auditable, records *why* two measured classes vanished, and cross-references the same reason code
the review packet wants to use — one vocabulary for one defect across both corpora. R3-b and R3-e
differ mainly in what the record says happens *next*, and they compose: a veto whose reason names
the sub-lattice hatch is R3-b and R3-e at once. R3-c and R3-d are the two recovery routes — R3-d is
the cheaper of them and the one the review packet prefers; R3-c is recommended only if Stephen
wants the negative result on record, or wants the placeholder ν₀ replaced while he is there.

### R4 — Enforcement and migration mechanics

Follows the 2026-07-29 precedent (§5/§8) unless overridden; the mechanics are set out in §9. What
needs a ruling:

- **R4-a — enforcement point.** Recommended: event-level drop at build, exactly as 2026-07-29 §5
  (a failing row never joins a class; mixed classes survive with cleaned member lists and an
  unchanged `class_id`; wholly-bad classes never form), with the sidecar ledger
  `<out>_discarded.parquet` extended by the new reason code(s) and the conservation identity
  `n_rows = n_projected + n_raised + n_discarded` preserved. **Not recommended, rather than
  settled** (these are the author's positions, not rulings already made): the same three the
  precedent rejected — QC quarantine (wrong granularity both ways), a per-member mask column (most
  code for least difference), and translator-side skip (leaves rate aggregates polluted).
  One thing about the third is **genuinely new under D6** and belongs in front of Stephen before he
  rules: translator-side enforcement needs **no 120-run rebuild, no re-QC, no re-merge and no
  migration — it erases the entire §10 rebuild cost line**. What it does not do is clean the
  catalogue: `Ea_rep` / `n_eff` / `k_rate` aggregates keep averaging over members with off-lattice
  final states, so every consumer *other* than the translator — flux CSVs, target ladders, review
  lists, the surrogate — keeps seeing them, and the §5 prerequisite would be discharged only for
  the one consumer that implements the skip. The author still recommends build-time enforcement for
  that reason, but the cost asymmetry is real and is not a reason the precedent had to weigh.
- **R4-b — CANON / catalogue version bump: yes or no?** Recommended **no CANON bump — conditional
  on a mandatory cross-policy guard**. The two are one package, not a bump plus a nice-to-have.

  *The premise.* D6 changes *which rows exist*, not the canonical geometry a `class_id` hashes, so
  surviving ids should be unchanged. This is the sharpest difference from 2026-07-29, whose bump was
  forced by §6 masking changing canonical *content*. The evidence usually cited for it — the
  2026-08-14 result "rebuild classes 584 / phase2 classes 584 / class_id sets identical: True /
  max |dEa_rep|: 0.0", **no `remap`** — needs restating honestly (second-pass verification finding,
  §14.2): that was a **same-policy** rebuild, so it demonstrates *build determinism and
  content-addressing*, **not** id-invariance under a **policy change**. The premise remains sound
  (ids hash canonical geometry; §9.3.4's "shrunk classes change content but not id"), but it is
  **asserted, not demonstrated**. §13 specifies the cheap demonstration that would settle it —
  rebuild **one** run under the D6 policy and show the new id set equals the old minus the flipped
  ids, with shrunk classes keeping their ids. It costs one run and should be done **before**
  implementing, not after.

  *The guard — mandatory, not a version note.* Without a bump, the only thing separating a pre-D6
  catalogue from a post-D6 one is a stamp — and **because the ids are unchanged, a pre-D6 per-run
  catalogue merged with a post-D6 one silently re-admits gate-failing members under the same
  `class_id`**: no error, no id-namespace signal, and arguably worse than the double-count the
  2026-07-29 bump prevented. That precedent **explicitly rejected bare no-bump** on exactly this
  ground (its §8.1, "no-bump-with-rebuild-discipline"), so no-bump is defensible here only if the
  discipline is *mechanised*: a **machine-readable `gate_policy` field stamped on every catalogue**,
  written by `build` and forward-carried through `qc` and `merge`, plus **refuse-by-default in
  `merge` and `remap`** on an absent or mismatched policy (absent ⇒ treat as `P0_only`). The
  pattern already exists in this repo — tonight's **B4 element-set guard** (commit `9c18a79`) does
  exactly this for element sets, and the deleted earlier draft required the same thing for the same
  reason. Verification confirms today's stamp **cannot** back such a guard: `build` records
  `mover_snap_tol` only in free-text parquet schema metadata that `qc` and `merge` drop on the way
  through (all three /data candidates carry **no** gate-policy record at all), and schema metadata
  does not survive a plain pandas round-trip. §13 gives the required form. **If the guard is not
  implemented, the recommendation flips to a bump** — the id namespace is then the only thing left
  that can separate the policies.

  **If Stephen prefers the loud option**, a bump is available at the cost of a full `remap` campaign
  (§10), and it makes the guard redundant rather than merely advisable.
- **R4-c — remap/rebuild scope.** Recommended: rebuild **all 120 runs** from their reference
  tables, re-QC, re-merge per alloy — the direct analogue of the 2026-07-29 slice-2 rebuild (that
  memo planned 47 runs; the executed migration covered 53). Cheaper alternatives exist but leave
  the two alloys on different gate policies, which is exactly the cross-policy merge hazard R4-b's
  guard (or a bump) exists to prevent: **NiFe-only** — 60 runs, roughly half the §10 rebuild cost,
  and it protects the graduated set that is already 0-affected while leaving every NiCr consumer on
  the old policy; **defer to the next campaign** — zero cost now, but the 2,348 NiCr
  `pending_research` classes stay on the target ladder in the meantime (R4-d). Neither is costed
  further here. One sub-question R4-c as written does **not** cover: `nicr_v2_scratch` consumes the
  2026-07-29 sweep catalogue, which is outside the 120-run tree, so a 120-run rebuild does not
  reach it (§9.3.6).
- **R4-d — timing.** Recommended: **before** any NiCr re-search leg. The gate removes 2,348 NiCr
  `pending_research` classes; that is search budget not worth spending, and the leverage ladder
  (`targets_nicr.csv`) would be re-ranked by the rebuild.
- **R4-d(ii) — fold tol ruling 3.6 into the same rebuild?** R4-c's plan is a full 120-run rebuild +
  re-QC + per-alloy re-merge, which is precisely the moment the 2026-07-29 precedent §8.2 said to
  settle the reciprocity-tol policy — *"to avoid running the merge twice"* — and the deleted earlier
  draft folded the two into one rebuild for that reason. With the band now 14.3k NiCr classes,
  re-merging twice is the expensive mistake. The complication is §9.3.5: the gate itself **moves
  3.6's evidence base** (1,607 NiCr + 505 NiFe surviving classes silently lose their reciprocity
  partner), so the band must be **re-measured post-rebuild before 3.6 is decided on it**. That makes
  the two rulings *sequencing-coupled* rather than independent: one rebuild → re-measure the band →
  decide 3.6 → one merge; or accept two merges. **Recommended: fold, with the re-measure step
  explicit and 3.6 decided on post-rebuild numbers.**

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
it flagged 2/2 in the review packet as well — but on the full corpus it is a **~20× enrichment in
NiCr and ~15× in NiFe** (the table above; the "~20×" is not a joint figure), with **low recall** in
both. It is an excellent cheap prescreen and a bad substitute for the gate.

- **R5-a — adopt as a prescreen on the measured/graduation pipeline** (flag `unpaired` targets
  before spending search budget, and flag any `unpaired` class carrying a `harvested_pair` stamp
  for review). Costs one column read; would have caught both casualties at zero measurement cost.
- **R5-b — additionally surface it as a QC flag corpus-wide** (flag only, never a gate).
- **R5-c — no change**; the symmetric gate subsumes it.

**Recommendation: R5-a**, explicitly *as a prescreen and not as a gate* — the recall numbers
forbid promoting it further. R5-b is a low-cost extra if Stephen wants the corpus-wide view.

### R6 — Does the audit / review protocol gain a final-state residual column?

Not a gate question — a **protocol** question this measurement raises and that no other ruling
covers. §3.1 finds **50 NiCr `pending_research | approved` classes flip**, and §4.1's two
casualties are *both* `approved`: `approved` at audit does not imply a sound projection, because the
audit protocol **never looked at the final state**. R5 proposes a standing prescreen for a *weaker*
signal (`unpaired`: ~20× / ~15× enrichment, low recall) while the direct signal — the final-state
residual itself — is not in front of the auditor at all.

- **R6-a — display `res_P2` (mover and static maxima) in the audit / review surface**, so future
  audits can see the final state. Costs one column, given §9.1's persistence proposal, and re-opens
  nothing already audited.
- **R6-b — R6-a *plus* a re-audit of the `approved` classes the gate leaves unchanged**, against the
  new column. Larger, but the population is bounded and enumerable from the catalogue.
- **R6-c — no change**; the gate removes the unsound ones at build, so an auditor never meets them.

**Recommendation: R6-a.** The gate makes R6-c *nearly* true, but only for events the gate can see:
the 656 zero-mover events (§2) and — under R1-d — everything the frame-anchor treatment quarantines
rather than discards still reach a reviewer, and a reviewer without the final-state residual cannot
tell them apart. R6-b is not recommended *unless* R1-a or R1-f is ruled (no build-time removal), in
which case the audit surface becomes the only line of defence and R6-b is the consistent choice.

## 9. Enforcement mechanics, if R1 is adopted

### 9.1 The gate and the ledger

Pipeline order inside `project_event` is unchanged except for one added computation: project →
snap P0 **and P2** → detect movers → **mover gate on `max(res_P0, res_P2)`** (ledger) → mask
static bystanders → `compute_depth_sig` → canonicalise. `P2` and its snap `s2` are already computed
in `project_event` — `s2 = _snap(frame, P2[p])` at `event_projection.py:830`, with `:829` the `s0`
snap and `:831` `detect_movers` (the range `:829-831` was quoted loosely in an earlier form of this
line) — so the residual and the static-substrate discriminator are a few lines; no new inputs are
needed from the reference table.

Ledger reason codes, under each R1 option:

- **R1-c**: `MOVER_OFFLATTICE` (unchanged, P0 side) · `MOVER_OFFLATTICE_P2` (attributable) ·
  `FRAME_ANCHOR_P2` (non-attributable) · `FRAME_UNFIT` (unchanged).
- **R1-d**: the first two and `FRAME_UNFIT` are ledger discards; `FRAME_ANCHOR_P2` becomes a **QC
  quarantine reason** on the class instead, joining the existing sticky-quarantine vocabulary.
- **R1-b**: one code, `MOVER_OFFLATTICE`, extended to the P2 side — simplest and least
  informative.

Both `res_P0` and `res_P2` (mover and static maxima) should be persisted as additive catalogue
columns regardless of the ruling, so §2-style audits never need a re-projection again — the same
precedent as 2026-07-29 §11. **This is an author proposal carrying no ruling handle of its own**
(it is additive, read-compatible and changes no verdict); if Stephen wants it ruled explicitly, it
is the persistence half of R1-f and the prerequisite for R6-a.

### 9.2 What happens to the frame-anchor population under each ruling

- Under **R1-c** it is discarded with a truthful, distinct reason — recoverable only by re-running
  a future re-anchored build against the ledger's lineage.
- Under **R1-d** it is quarantined: excluded from every bake (`skipped_quarantined`), retained in
  the catalogue, and directly re-openable if the frame anchor is ever changed. The 14 mixed
  classes (NiCr 10 / NiFe 4) are over-quarantined by this — a class with some clean members loses
  them all. Their combined class flux is 3.40 firings (NiCr 0.00 + NiFe 3.40), i.e. negligible.
- Under **R1-b** it is swept into `MOVER_OFFLATTICE` and becomes indistinguishable from the D6
  target in every downstream audit. This is the option §3.2 argues against.
- Under **R1-a**, **R1-e** and **R1-f** it is untouched and stays bakeable.

Two dispositions that would otherwise be left to inference. (i) The **47 events visible by neither
signal** (§3.2) sit inside the non-attributable bucket, so they follow it: quarantined under R1-d,
discarded under R1-b/R1-c, untouched under R1-a/R1-e/R1-f. They get no separate treatment under any
variant. (ii) **R1-d depends on the quarantine being sticky.** §9.3.4 notes that QC re-runs on
merged member lists and that quarantine status can therefore move, so `FRAME_ANCHOR_P2` must join
the **sticky-quarantine vocabulary explicitly** — never cleared by a later QC pass that no longer
sees the dropped members. If it is not pinned, the whole 3,687-event bucket silently re-enters the
bake population at the next QC and R1-d quietly degrades into R1-e. This is a correctness condition
for R1-d, not an implementation detail.

### 9.3 Migration

1. **No `CANON_SCHEMA_VERSION` bump** under R4-b as recommended — **with the machine-readable
   `gate_policy` stamp and the `merge`/`remap` refusal implemented first, not after** (R4-b; the
   no-bump recommendation is conditional on them, and §13 gives the form). If a bump is ruled
   instead, the 2026-07-29 §8.3 lineage `remap` path applies unchanged (`pylatkmc.ingest.cli remap`
   exists and was exercised in the slice-2 migration).
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
   §14.1). Backward linkage is resolved at build time against the post-drop survivor set
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
   `models/nife_v2_scratch` (`b3df55e`) bakes the 180 graduated NiFe classes — **0 affected** (see
   below for what that does and does not mean).
   `models/nicr_v2_scratch` (tracked since `da91997`) consumes the 2026-07-29 sweep catalogue; its
   casualty check was
   **executed under verification** rather than deferred (all 29 of that sweep's runs sit inside
   the 120-run measurement): **2 of its 22 baked classes flip** — `2986630951ae…` (2/2 members,
   Ea 0.7490) and `ac2488f17a71…` (3/3, Ea 0.7789), the same two physical half-shift events as
   §4.1's casualties under their older-CANON ids — occupying **80 of its 2,400 committed procs
   (3.33 %)**.

   **What actually holds, stated without slack.** No committed proclist *changes on its own*: the
   `generated/proclist.{c,h}` files committed alongside both specs are static artifacts, and a D6
   rebuild does not touch them. What a D6 rebuild changes is what a **regeneration** would produce
   — and a regeneration after the rebuild **would** change one of them. For `nife_v2_scratch`:
   nothing, because 0 of its 180 classes are affected, so a regeneration is expected byte-identical
   (verify, don't assume — that expectation rests entirely on §4.2's 0-of-180 result; had any of the
   180 shrunk, a committed proclist would change). For `nicr_v2_scratch`: a real shrink, 2,400 → 2,320
   procs and 22 → 20 `v2_class_ids`. But note the catalogue it points at is the **2026-07-29 sweep
   catalogue**, not the 120-run /data tree that R4-c rebuilds, so the shrink only reaches it if that
   older catalogue is *also* rebuilt under the new policy — which R4-c as written does not cover.
   Whether it should is an open sub-question under R4-c. (The casualty count is nonetheless
   measurable today because all 29 of that sweep's runs sit inside the 120-run measurement.)
   `ni_example`'s v0.3 family-CSV path consumes no EventClass catalogue and must stay
   **byte-identical** (validation gate).

## 10. Costs

**The rebuild campaign** (R4-c) — a **measured rate applied to an extrapolated volume**, not an
end-to-end measured campaign, which is how it should be read. The rate, **88 ms/row**, is one
measured run (878 rows in 77.6 s, single core, the drifted `T800_2vac` tag) scaled linearly to all
120 runs = 132,840 rows ≈ **3.3 h serial, ~25 min at 8-way** under the ≤21-core budget. Per-run
artifacts ~700 M; the 732 M comparison figure is `du -sh` on the *old-policy* 2026-08-14 tree, so it
is an upper-bound analogue rather than a prediction. Merges are minutes. The 2026-07-29 precedent's
slice-2 analogue was a 53-run rebuild plus a full lineage `remap`; this one is 120 runs but, under
R4-b as recommended, **no remap** — the expensive half of the precedent's migration does not recur.

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
  **One honest caveat, because §2 partially reinterprets that precedent's own evidence.** The 0.5 Å
  P0 cut was justified there on mover residuals being sharply bimodal — "essentially 0 or ≥ 0.9,
  with a near-empty valley" — and on "60.7 % of failures have a perfectly on-lattice mover (median
  0.000 Å)". §2 shows that for the 87.49 % seed-mover majority the zero mode is an **artifact of the
  frame anchor**, not a physical fact about where movers sit. The *signature* the precedent observed
  is real and reproduces here; part of its *explanation* is structural. The author's reading is that
  this does **not** require re-justifying the P0 cut — that cut only ever fires on the
  non-degenerate population (multi-mover / non-seed), where the bimodality is not an artifact — but
  that reading is offered for **confirmation, not asserted**. If Stephen reads it otherwise,
  re-justifying the 0.5 Å P0 cut becomes its own item; this memo does not pre-empt that and adds no
  ruling for it.
- **Extending the bystander mask to P2 — author-proposed deferral, overridable, and ruleable as
  R1-g.** It is the natural sibling question, and it is the *direct fix* for the frame-anchor bucket
  — 75.9 % of the naive catch, i.e. three quarters of the population this memo is about. The author
  proposes deferring it because masking changes canonical *content* and would force the full CANON
  bump + `remap` that R4-b avoids — a **cost** argument, not a principle. The deleted earlier draft
  deferred the same question on **principle** instead: context rows are claims about the *initial*
  state, so a bystander that relaxes in the final state impugns no identity claim, and masking it
  would discard information the identity never asserts. Both arguments are on the table; neither is
  settled here, and R1-g exists so Stephen can rule it in rather than having to reopen the memo.
- **Re-anchoring the local frame** (so `res_P0` is not structurally zero for seed movers) —
  the deeper fix suggested by §2. Also an **author-proposed deferral**: it would change every
  `class_id` and is a far larger decision, and D6 is the cheap gate that makes the current anchor
  safe rather than a replacement for it. Recorded, not decided.
- **Sub-lattice subdivision** (2026-07-29 §10.1 — Stephen's own deferral) — still the eventual
  escape hatch if a discarded population ever needs *representing* rather than merely excluding;
  nothing here forecloses it, and §4.1's two casualties would be its **first concrete customers**
  (R3-e) if a re-search or re-harvest ever confirms real saddles with genuinely non-lattice final
  states.
- Parked sibling items, untouched by this memo: the 15-class review (§7 overlaps it only in the two
  named instances), D1/D2/D3/D5 of the NiFe brief, the 22 same-action double-count collision pairs,
  and the V4 ν₀-placeholder gate
  (`.scratch/phaseC/research_campaign_nife/V4_NIFE_REVERIFICATION_2026-08-15.md`, commit `09f518d`).
- **Tol ruling 3.6 is *not* independent — it is sequencing-coupled** to R4-c / R4-d(ii): the rebuild
  moves its evidence base (§9.3.5) and the re-merge should be run once, not twice. Its band, with
  the bases labelled, because these two are routinely conflated: the **whole-quarantine** basis
  (`audit_status == 'quarantined'`) is NiCr **10,699 classes / 38.30 %** of corpus flux and NiFe
  **3,603 / 44.75 %**; the **strict reciprocity** basis (`audit_reason` ⊃ "reciprocity") is NiCr
  **9,957 / 35.86 %** and NiFe **3,436 / 39.79 %**. The first pair is the one usually quoted and it
  is *not* "the reciprocity band" — `NICR_FLUX_RESTATEMENT_2026-08-15.md` §4 separates them
  explicitly. Both pairs carry that restatement's §9 caveat (i): a **±0.4 pp** treatment band from
  the dirty-run handling.

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
  (v) a **full-run `class_id`-set gate**, promoted from the weaker "unchanged-`class_id` round-trip
  for a shrunk class": rebuild **one** run under the D6 policy and assert that the new id set equals
  the old id set **minus the flipped ids**, and that every shrunk class **keeps its id**. This is
  the demonstration R4-b's premise currently lacks (the 584/584 result is same-policy determinism),
  it costs one run, and it should be run **before** implementing rather than as a regression after;
  (vi) two-seed byte-determinism of the rebuilt catalogue; (vii) `ni_example` proclist
  byte-identical; (viii) if R4-b's guard is ruled, `merge`/`remap` must **refuse** a symmetric-gate
  catalogue combined with a `P0_only` (or unstamped) one.
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
- The `gate_g3_snap_residual` docstring (`event_class.py:894-934`) and `reftable.py`'s ledger
  paragraph both need rewriting to name the snapshot, whichever way R1 goes.

## 14. Adversarial verification addenda (2026-08-15)

### 14.1 First pass — 4-lens Opus fleet

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

### 14.2 Second pass — two independent verifiers on the memo itself

The memo was then attacked again by two further independent verifiers, both returning **PARTIAL**:
every empirical number was re-derived from the raw parquets and **confirmed** — neither verifier
broke a measurement — with the defects confined to framing, labelling, argument direction and
missing options. All of the following were applied above; no number in §§2–7 changed as a result.

- **Two factual errors.** §4.1's signal 4 conflated an `action_id` with its archetype:
  `6698383570156747695` carries **45.409 %** of NiCr corpus flux, not 98.97 %; the 98.967 % belongs
  to archetype `4972478298379930765` across its two actions. And §6's "pure-Ni history" was in fact
  **NiCr Ni95Cr05** over 6 runs, measured on the *mover P0* residual — so the composition
  explanation that had been built on it was wrong and has been replaced by the real differences
  (different quantity, different corpus size).
- **One argument reversed.** R3-c had used the 1.0e12 Hz placeholder ν₀ as an argument *against*
  re-search; a re-search is precisely what would replace it. §4.1's "honest deduction" is likewise
  not a discount — at 1 of 5 members (20 %) the casualties sit at or below the 26.3 % base rate.
- **Overclaims narrowed.** §2's "algebraic identity" is an empirical result on this corpus
  (guaranteed for the seed *atom* by construction, not forced for every mover atom); the status line
  now says *no gate implementation was committed* rather than "nothing was committed" (the
  measurement **is** committed, at `5ff4bfc`); §10's costs are a **measured rate on an extrapolated
  volume**; and R4-b's 584/584 result is same-policy determinism, not policy-change id-invariance —
  now stated as a premise with a cheap pre-implementation demonstration attached (§13, test v).
- **A dropped safeguard restored.** R4-b's no-bump recommendation now carries a **mandatory**
  cross-policy `gate_policy` stamp + `merge`/`remap` refusal (B4 element-set-guard pattern, commit
  `9c18a79`). The 2026-07-29 precedent §8.1 explicitly rejected *bare* no-bump, and with unchanged
  ids a pre-D6 catalogue merged with a post-D6 one silently re-admits gate-failing members under the
  same `class_id`.
- **A third structural blind spot added** (§2): **656 zero-mover events**, on which today's gate and
  the proposed one are both vacuous, 638 of them carrying `res_P2 ≥ 0.5 Å`; mitigation named
  (`translator_v2`'s counted empty-delta skip).
- **Missing options added, briefly and neutrally:** R1-f (flag, don't drop — the option Stephen
  overrode in 2026-07-29 §6), R1-g (mask instead of gate), the recorded rejection of
  *gate-only-the-recovered-population*; R2-d (0.45 Å) and the per-alloy-threshold note; R3-d
  (re-harvest from trajectory) and R3-e (grandfather pending sub-lattice representation); R4-a's
  translator-side cost asymmetry; R4-c's NiFe-only / defer cost sketches; R4-d(ii) (fold tol 3.6
  into the one rebuild); and a new **R6** on the audit protocol.
- **Bases and labels fixed:** §11's tol band (whole-quarantine 10,699/38.30 % and 3,603/44.75 % vs
  strict-reciprocity 9,957/35.86 % and 3,436/39.79 %, with the ±0.4 pp dirty-run caveat); §5's
  73.45 %-carried vs 73.70 %-removed; §4.2's class-level vs member-level median; §3.2's hop-table
  column sums and the `< 0.4` bin's half-shift status; R1-d's events vs classes; R5's ~20× (NiCr) /
  ~15× (NiFe); §6's ~1.5×-per-step as a NiCr statement; the gate's own cite
  (`event_class.py:894-934`, not the residual array at `event_projection.py:832-835`); §9.1's
  `:829-831`; and the benign all-`False` `match_build` column (Measurement integrity).
- **Author scoping marked as such.** §11's two "out of scope" items and R4-a's rejected alternatives
  are now author-proposed deferrals for Stephen to confirm or override, not settled outcomes;
  §9.1's persistence proposal is flagged as carrying no ruling handle of its own.
- **Consequences given rulings or dispositions:** the audit-protocol question (R6), the
  `frame_anchor_tol` coupling (R2), the 47 neither-signal events and the R1-d quarantine-stickiness
  condition (§9.2).

### 14.3 The superseded sibling draft

An earlier same-night draft of this same decision — `SYMMETRIC_GATE_DECISION_2026-08-15.md`, 05:20,
single-recommendation form — sat un-withdrawn beside this memo and **recommended differently**
(its D6.1 = adopt with the *naive* gate; D6.3 = withdraw + queue for re-search). Two same-night
memos asking one reader to rule on one decision in different directions is a live hazard, so the
draft has been **deleted** and this is now the only D6 decision surface. Four things it carried that
this memo lacked are folded in above:

1. its **D6.3** *withdraw-at-rebuild + queue-for-re-search* disposition → recorded under **R3-c**;
2. its **D6.5** *refuse cross-policy merges* guard → now mandatory under **R4-b**;
3. its **§6.5** *sub-lattice-subdivision escape hatch*, naming these two casualties as its first
   concrete customers → **R3-e** and §11;
4. its **§5** recorded rejection of *gate only the recovered/token-mismatch population* → **R1**.

Its D6.6 sequencing note (fold tol 3.6 into one rebuild) is carried as **R4-d(ii)**. Where the two
drafts disagree, this memo's position is stated with the evidence that post-dates the draft: **R1-d**
over the naive gate on §3.2's 75.9 % fork, and **R3-b** over the re-search queue on §7's
shoulders-not-basins finding — with the draft's alternative preserved as an option in both cases
rather than dropped.

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
- **Reproducing the cross-tabs — what is scripted and what was ad hoc.** `gate_impact.py` produces
  `gate_impact_by_class.parquet` (90,472 rows × 39 cols: `class_id`, `alloy`, `n_members`,
  `n_fail_{0.4,0.5,0.6}`, `status_{0.4,0.5,0.6}`, `max_res_sym_A`, `min_res_sym_A`, `max_res_P0_A`,
  `max_res_P2_A`, `min_hop_over_1nn`, `n_half_shift_members`, `n_multi_mover_members`,
  `audit_status`, `audit_reason`, `nu0_pair_policy`, `pair_status`, `Ea_rep_eV`, `Ea_std_eV`,
  `n_eff`, `action_id`, `archetype`, `token_mismatch`, `backward_class`, `flux_firings`,
  `reachable`, …). Everything keyed on class status, curation stamps, `pair_status` or flux is
  reproducible from that file **alone** — §3.1's `nu0_pair_policy` × `audit_status` cross-tab, §5's
  top-100 rankings, R5's precision/recall table, §6's per-alloy bins — using `status_0.5`
  (flipped / shrunk / unchanged) joined against `pair_status`, `audit_status`, `nu0_pair_policy`,
  `token_mismatch`, `reachable` and `flux_firings`.
  **The attributability splits are not.** `mover_offlattice_P2_attributable` is a **member-level**
  column of the 120 `p2_measure/{NiCr,NiFe}/*.parquet` files, and `gate_impact.py` does not
  aggregate it — so §3.2's class-level fork table, §5's attributable columns, the 14 mixed classes
  and §6's pile-up attribution came from **ad-hoc analysis written for this memo, with no saved
  script**. The recipe, stated so it can be re-run: explode `merged_v3_{NiCr,NiFe}.parquet`'s
  `source_sim_paths` into `run_tag#idx_ref` keys, join those against the concatenated `p2_measure`
  parquets on (`run_tag`, `idx_ref`), then aggregate per `class_id` over
  `mover_offlattice_P2_attributable`, `gate_P0_fail` / `gate_P2_fail` / `gate_sym_fail`,
  `half_shift`, `hop_min_over_1nn`, `static_max_residual_P0` / `_P2`, `drift_P0_A` / `drift_P2_A`,
  `n_movers`, `n_mover_atoms` and `seed_is_mover`. Both second-pass verifiers reproduced every one
  of those figures independently by exactly this route.
- **Scope of the bit-for-bit validation**, stated exactly: `res_P0` reproduced the production
  ledger, per-run catalogue and merged catalogue with max deviation 0.0 Å on **one validated run
  per alloy** (four independent checks each); row conservation and join integrity (0 unmatched
  members, 0 duplicate keys) hold across **all 120 runs / 132,840 events**.
