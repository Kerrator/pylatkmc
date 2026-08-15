# NiFe measured-rates line — decision brief (2026-08-15)

Everything actionable without a ruling is executed and committed; the one designed-but-unlaunched
item is D5, held pending your call. Evidence pointers, not copies:
`NIFE_RESEARCH_CAMPAIGN_2026-08-15.md` (§6 caveats, §8 = full-state arm),
`TOKEN_MISMATCH_VERDICT_2026-08-15.md` (§10 = adversarial-verification addendum), and
`pylatkmc/.scratch/phaseC/research_campaign_nife/NEXTLEG_DESIGN_2026-08-15.md`. This brief itself
survived a 3-verifier fact-check (74 claims, corrections applied).

## Decisions on your desk

**D1 — Promote `merged_v3_NiFe_graduated_2026-08-15.parquet` as the NiFe production candidate.**
*What promotion changes:* the 180 graduated classes become emittable by `translator_v2` at their
**harvested** ν₀/Ea pairs — the re-searched barriers are a validation gate only and enter no rate
(max |Ea_rep − Ea_research| = 49.5 meV among the graduated; report §6.1). It is a curation-status
change, not a rate change: verified column-by-column as a pure two-column relabel of the
2026-08-14 file (only `nu0_pair_policy` + `audit_reason` differ; that file stays untouched
beside it). *New evidence:* (a) full-state control arm — 15 of the 180 (top-10 flux + a 5-point
stratified tail, ranks 11/53/95/137/180) re-refined in their full 9,670–9,679-atom production
frames, 15/15 accepted in-band; **Ea_full − Ea_cluster mean +8.6 meV, median +7.3, max +17.2,
uniformly positive** — a small newly-measured systematic softness of the padded cluster (NiCr
T500 precedent ≤5.9 meV; both small vs the ±50 meV band). (b) Token-mismatch resolved — 0 of the
180 are mismatch classes; the candidate's stamped translate is unaffected by the fix (identical
report pre/post: 180 classes → 14,976 procs / 936 member channels; all 180 are single-arrow
classes where the fix is a provable no-op; 0 geometry collisions in the stamped output).
*What promotion unblocks and doesn't:* it releases the decision-3.4 codegen gate for NiFe, but
does **not** by itself produce a NiFe binary — B6 (no NiFe v2 model spec) and B4 (element-set
guard at merge) remain open. *Runtime context that makes D1 load-bearing:* `esym_model_v2` is
NiCr-fit with Fe context range [0,0], so **every Fe-bearing runtime context trips
`SURR_TRIG_SPECIES`** — the surrogate cannot fill an Fe gap, only flag it. Since Fe-mover
classes carry **91.8% of corpus flux**, these 180 measured classes (153 Fe-mover) are the *only*
trained Fe kinetics in any NiFe model until an Fe-bearing esym refit. *Bookkeeping:* the merged
candidate is durable only as the /data copy (the campaign-dir copy is untracked `.scratch`);
per-class graduation evidence lives in the git-tracked `catalogue_v3_NiFe_graduated*.parquet` +
`graduate_review.csv`, **not** in the merged file (§6.2) — say if promotion should also mean
tracking/archiving the merged parquet.

**D2 — CONTEXT_SUSPECT `a69b964d2946…`** (+51.4 meV, 1.4 meV over band, 3 members, 42.0
firings): review, or widen-band ruling. Note it is indistinguishable from ordinary pending
classes inside the merged parquet (§6.2) — whatever you rule needs a recording surface
(veto overlay or review list).

**D3 — The 19-class review list** (2,402.7 firings = 23.1% of remaining pending flux; adding
the D2 suspect makes the block 2,444.6 = 23.5%). Larger than stratum A2's selection (1,124.9)
though smaller than A1's (2,971.4). A plain re-run is deterministic and will reproduce the
failures; the actionable split is three-way: **12 refine_failed** — genuine saddle
escapes/EIGENVALUE LOST, need a ladder/seed protocol change; **4 re-projected-class-changed** —
need a class-drift ruling; **3 wrong-mover** — stored `mover_rank != 0` with `dra_stored ≈
0.06 Å`, i.e. the recorded mover never moves to the saddle: a harvest-side data-quality
question, unrecoverable by any search change (the new prescreen predicts them 3/3 with 0/197
false positives). Unrelated and still on its own track: the 15-class review (12 token-flicker +
3 structural) from the July projection campaign — verdict §3 measured zero overlap.

**D4 — Tol ruling 3.6 (reciprocity `tol = 1e-6`).** The NiFe quarantine band is 3,603 classes /
**44.8% of corpus flux** — the largest single *unaddressed* lever; no search leg can reach it,
only the ruling can.

**D5 — Launch the stratified next leg?** Designed, sized, committed, **not launched** (386 jobs
≈ 16–30 min on 7 workers; launch line in `NEXTLEG_DESIGN_2026-08-15.md`). Modelled outcome:
measured corpus flux **46.6% → 49.7%**, non-quarantined **84.4% → 89.9%**, pending 8.63% →
5.56%. Strata: Fe-mover V1NN tail (175), Fe-at-1NN-of-path Ni hops (125), minor-archetype
coverage probe (86 — flux-empty by construction: V1NN_inplane is 99.93% of corpus flux, so this
buys representation, not flux). Held because it creates a third candidate state while D1 is
open, and `rc_graduate` overwrites leg-1 outputs in place (/data copies are the safety net).
Notes: leg 2 excludes the D2/D3 classes by construction, so deferring D3 costs D5 nothing; the
searched member resolves from `merged_v3_NiFe_stamped.parquet` at launch time — a re-merge
before launch would silently shift targets (`nextleg_strata.csv` records the design-time
resolution for diffing). The concerted C2/C3 sub-block is small by design: the `mover_rank`
prescreen rejects most of that pool (84 rows incl. 40/62 C2_0deg, 24/32 C3), and `rc_accept`
cannot yet adjudicate concerted movers (argmax mover test ties). Expect ~15–18 of leg 2's
graduations via the documented flicker-hysteresis path (leg 1: 7/180, 0.9% of accepted flux).
*Sequencing:* the NiCr line sits at 32 measured of 70,179 classes; a NiCr graduation leg
competes for the same worker budget — order is your call (the token fix was landed now partly
so a future NiCr leg never surfaces a masked 5,014-class skip).

**D6 — P0-only projection gate (upgraded by verdict §10).** G3/projection residuals are computed
on the initial state only; a final state that never reached a lattice site is invisible to every
build-time gate. The verification pass showed this is not a rounding issue: **43 of the top-100
recovered concerted classes — 73.5% of all recovered flux — are half-shift artifacts**, so the
symmetric-residual gate is now a **prerequisite for any bake that enables the recovered
classes** (any `include_unstamped` bake or future multi-mover graduation), not an unranked
follow-up. It re-partitions the corpus ⇒ own memo + canon decision. (It does NOT gate D1: the
stamped translate contains none of the recovered classes.) Related small defect surfaced by the
same pass: **22 same-action double-count collision pairs** (saddle-token flicker splitting one
physical channel into two summing rows; 20 pre-existing + 2 new) — worth its own line item.

## Landed without needing a ruling (FYI)

- **Token-mismatch fix** (`8f49e18`) + **verification addendum + strengthened test** (`8345b6b`):
  movers derive from `arrows`, not `delta`; verdict = physics (same-species concerted relays)
  surfaced by a stale translator proxy — not a harvest defect, not NiFe-specific (NiCr 5,014
  masked). Counter now 0 corpus-wide = genuine corruption detector. On the `include_unstamped`
  path the recovered classes add 110 new geometry collisions (107 genuine relay-∥-direct-hop
  pairs, 3 recovered×recovered) and grow procs +15% / pattern reach_ij 8→10 — promotion-sizing
  facts for any future unstamped bake, none binding today. The verdict's kinetic-irrelevance
  claim is scoped by §10 to NiFe at measured conditions (0.0006%→0.106% flux share over
  T300→T800); the NiCr share is unmeasured and plausibly much larger — measure before reusing
  the claim. B2+B3 landed earlier (`8f90015`/`da91997`): Fe and WILDCARD are first-class
  surrogate categories end-to-end — necessary but not sufficient for Fe coverage (see D1's
  runtime note). The readiness-report §7 investigation item is now marked resolved in place.
- **Full-state control arm** (`e0a5264`): harness + log in the campaign dir; includes a
  min-image back-translation fix whose absence in the July NiCr arm is a latent bug (a
  boundary-straddling cluster teleports a box length and spuriously fails acceptance — the July
  targets never straddled the boundary).
- **Campaign report in git** (`d86c497`, updated `e0a5264` + `6894453` + this pass) with
  corrections: §6.6 — the measured 180 are homogeneous in barrier/action but **not** chemistry
  (153/180 Fe-mover; Fe-mover classes = 7% of classes, 91.8% of corpus flux); §8 added; §1
  stats rebased to the 180 graduated (mean |ΔEa| 13.3 / median 11.5 / max 49.5 / signed −4.0 meV).

## Consciously deferred (say the word and they run)

- **Tail deepening 200→500** (+6.7 pp of pending flux for +300 jobs) — an alternative use of the
  same worker budget as D5's 386 jobs.
- **NiFe V4 re-verification** (harvested-ν₀ vs per-state, mirroring the NiCr gate).
- **Fe-bearing esym refit** — the dependency that lifts the F:[0,0] OOD gate; natural pairing
  with D1/D5 but needs the surrogate line.

## Conditions on every number above

Measured 2026-08-15 on the Linux box unless stated. **Both** re-search arms (padded-cluster and
full-state) re-refine from the stored saddle — no independent-search control exists in either
alloy's leg; all agreement numbers measure projection/re-relaxation consistency, not independent
rediscovery of the transition. Full-state arm: n=15 of 180, delr_sad gate 2.0 Å, band ±0.05 eV
vs Ea_rep. Flux = reachability-corrected expected firings over the 60-run NiFe corpus
(T300–T800 × 1–10 vac; 120,291 total; pending-flux denominators are 10,384). Next-leg yields
are modelled (0.90 main strata, lower concerted), not measured. Rate policy and curation status
are separate axes: 111 of the 180 promoted classes still carry `audit_status='pending'` (§6.7).
NiCr full-state ≤5.9 meV is a July NiCr T500 measurement — precedent, not a NiFe fact.
