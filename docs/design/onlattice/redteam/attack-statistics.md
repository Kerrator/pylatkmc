# Red-team review — statistics and the alternation loop

**Target:** `onlattice_design/FINAL_DESIGN_DRAFT.md` (design "synthesis")
**Lens:** rate provenance & barrier aggregation, fallback-regression validity & extrapolation,
novelty false-negatives, coverage-report metrics, detailed-balance violations, alternation-loop
failure modes (harvest bias, catalogue poisoning, non-convergence).
**Grounding:** verified against the pyKMC input contract in `/home/kerr/pykmc/pyKMC/pykmc/`
(`event_table.py`, `rate_constant/rate_constant.py`, `symmetries.py`). Clean-room rule observed —
no on-lattice engine or classification-pipeline docs were read.

## Temperature arithmetic used throughout

Rate is `k = ν₀·exp(−Eₐ/k_BT)` (`rate_constant.py:45`), `k_B = 8.617e-5 eV/K`. Dealloying NiCr(100)
is studied at T ≈ 300–500 K (`k_BT` = 0.0259–0.0431 eV). A barrier *difference* ΔEₐ maps to a rate
ratio `exp(ΔEₐ/k_BT)`:

| ΔEₐ (eV) | where it appears in the design | ×rate @300 K | ×rate @500 K |
|---|---|---|---|
| 0.15 | `split_tol` — spread *tolerated inside one "exact" class* | **331×** | 32× |
| 0.25 | refinement escape clause + pyKMC `is_new_event` tol | **1.6×10⁴×** | 331× |
| 0.20 | representative fallback extrapolation error | 2.3×10³× | 104× |

These factors are the whole story: every place the design "tolerates" a barrier spread of a few
tenths of an eV, it is tolerating **2–4 orders of magnitude** of rate error inside a construct it
markets as exact.

---

## The root defect (context for the criticals)

pyKMC emits **one scalar barrier per accepted reference row** and never averages
(`event_table.py:649–668`); its only barrier tolerance (0.25 eV, `is_new_event`, line 417) is a
*saddle-dedup* tolerance applied *within a single `event_id` bucket* — i.e. within one physical
environment. The design instead (§4.4, §6.1, §7.1) builds a per-class `barriers[]` list,
`Eₐ = trimmed_mean(barriers)`, `Eₐ_std`, and a single class rate `k = ν₀·exp(−Eₐ/k_BT)` applied to
**every** matching instance. The barriers in one on-lattice class do **not** come from repeated
measurement of one event (pyKMC's dedup rejects a re-discovered event as `EVENT_NOT_NEW`); they come
from the design's own **fold-in** (§4.6): several distinct pyKMC `event_id`s — physically distinct
environments pyKMC resolved — merged under a coarser stencil. So `barriers[]` is a *population
mixture of distinct sub-environments*, and `Eₐ_std` is not measurement noise but **structural
heterogeneity the class cannot represent**. Findings 1–4 are consequences.

---

# CRITICAL FINDINGS

## C1 — Barrier-mean-then-exponentiate collapses a rate mixture into one wrong rate (Jensen)

**Component:** §6.1 exact-lookup rate; §4.4 SPLIT_CHECK / `split_tol`; §5.3 group-BKL.

**Mechanism.** For a class that folds in sub-environments with barriers `{Eₐᵢ}`, the physically
correct aggregate rate applied to a population is the occurrence-weighted mean of the *rates*,
`⟨k⟩ = ν₀·⟨exp(−Eₐᵢ/k_BT)⟩`. The design computes `k = ν₀·exp(−⟨Eₐᵢ⟩/k_BT)`. By Jensen's inequality
(exp is convex) `exp(−⟨Eₐ⟩) ≤ ⟨exp(−Eₐ)⟩`, always, and the gap is exponential in the spread. Two
independent mechanisms compound:
- **(a) Convexity:** mean-then-exp systematically **under**-estimates the mixture rate; the true
  flux is dominated by the *lowest-barrier* members.
- **(b) `trimmed_mean` removes the flux-dominant tail:** trimming as "outlier rejection" preferentially
  discards the extreme members — including the *lowest*-barrier one, which by (a) carries most of the
  physical flux. Outlier rejection is thus anti-correlated with physical importance.

**Trigger.** NiCr(100), full colour. A "1NN vacancy hop, surface" class folds in a pure-Ni neighbour
motif (Eₐ=0.65) and a Cr-adjacent motif beyond the promoted 1st shell (Eₐ=0.50) — both within
`split_tol` (0.15) so no split, both within the 0.25 refinement clause so no audit. `trimmed_mean` →
~0.65 (0.50 trimmed as low outlier). Every instance fires at `exp(−0.65/k_BT)`; the 0.50 sites should
fire **331× faster** (300 K). In rejection-free BKL this directly sets branching ratios, so the Cr-mediated
channel that *is the dealloying pathway* is suppressed by ~10²–10³×.

**Downstream.** Wrong kinetics and wrong branching ratios at the dealloying front, silently — the
class is reported as "exact-lookup," 0 fallback flux (looks healthy, F5). The one number the design
picks to summarize a class (mean barrier → exponentiate → trim the fast tail) is the worst possible
choice for a rate.

**Fix.** Store the rate mixture, not a mean barrier. Either (i) keep sub-environment resolution
(promote context far enough that a class is truly single-rate — but then `split_tol` must be ≈`k_BT`,
not 0.15 eV), or (ii) if lumping is unavoidable, assign the class rate as the **occurrence-weighted
mean of member rates** `⟨exp(−Eₐᵢ/k_BT)⟩`, not `exp(−mean Eₐᵢ)`, and drop `trimmed_mean` for a
rate-space aggregate. Set `split_tol` from a *rate* tolerance (`k_BT·ln(1+δ)`), not a fixed 0.15 eV.

## C2 — The detailed-balance gate G2 is an algebraic tautology (validates nothing)

**Component:** §7.2 / §8.2 gate G2; the "detailed balance from a single per-pair ΔE" crown-jewel graft.

**Mechanism.** G2 tests `|ln(k_f/k_b) − (ln(ν0_f/ν0_b) − dEnergy/k_BT)| < db_tol`. But the design
*defines* `k_f = ν0_f·exp(−Eₐ_f/k_BT)`, `k_b = ν0_b·exp(−Eₐ_b/k_BT)` (§6.1) **and**
`dEnergy := Eₐ_f − Eₐ_b` (§7.2, line 749). Substitute:
`ln(k_f/k_b) = ln(ν0_f/ν0_b) − (Eₐ_f−Eₐ_b)/k_BT = ln(ν0_f/ν0_b) − dEnergy/k_BT`.
The residual is **identically 0 to machine precision, for every class, always.** G2 cannot fail
because `dEnergy` is *defined* as the quantity that makes it pass. There is no independent energy
channel: pyKMC stores only per-row `energy_barrier` (`event_table.py:657,683`), so `dEnergy` can only
ever be the barrier difference.

**Trigger.** Any pair, healthy or pathological. Feed a class whose forward and backward means come
from completely unpaired sub-environment sets (C4); G2 passes with residual 0.

**Downstream.** The design's headline reversibility guarantee is fake — a `db_tol = 0.05` that can
never bind. The genuine per-site balance violation (C4) is thereby *undetectable*: the one gate that
is supposed to catch it is a no-op. This is a "curation gate that looks healthy while being wrong" in
the strongest sense: it is green by construction.

**Fix.** G2 must compare two **independently sourced** quantities. Options: (i) recover state energies
from a *linked* forward/backward pyKMC pair (same saddle: `ΔE = dE_f − dE_b` from the *same row pair*,
not from two class means) and test each *contributing pair* before averaging; (ii) test balance
against pyKMC's own stored `k`/`k_prefactor` column (an independent Arrhenius evaluation) rather than
re-deriving `k` from the same `Eₐ`/`ν0` the gate uses. As written the gate should be deleted or
relabelled "prefactor bookkeeping," never "detailed balance."

## C3 — Genuinely new events are silently absorbed as "instances," poisoning the class and faking convergence

**Component:** §7.1 new-class-vs-new-instance (exact `class_id` equality); §4.4 `promoted_shell`
starts at 1; §8.2 audit only fires for *first instance of a brand-new class*.

**Mechanism.** Identity `κ` includes context only out to `promoted_shell` (default = 1st shell); it
grows only when a barrier lands `> split_tol` from the current mean (SPLIT_CHECK). So a genuinely new
event that (a) differs from an existing class *only* beyond the 1st shell and (b) has a barrier
*within* `split_tol` of that class is: keyed identical → classified "new **instance**" → barrier
**appended** (shifting the class mean) → **not** audited (audit is only for new *classes*) → reported
as exact-class, 0 fallback flux. Three failures at once:
- **Novelty false-negative:** the new physics is never recognized as new.
- **Catalogue poisoning:** the foreign barrier contaminates `trimmed_mean`, changing the rate applied
  to the *genuine* members.
- **False convergence:** the loop's sole convergence signal is *new classes per cycle → 0* (decision 1,
  §7.3). Absorbing new events as instances drives that counter to 0 while real new classes are still
  being missed — the loop declares victory on an incomplete catalogue.

**Trigger.** Dealloying NiCr: a vacancy hop with a Cr at 2nd/3rd-neighbour distance (beyond promoted
shell 1). Barrier 0.62 vs pure-Ni class mean 0.65 → within `split_tol`. Absorbed; mean drifts to 0.64;
every pure-Ni instance now fires at the wrong rate; the Cr-decorated environment — exactly what the
campaign exists to catalogue — is invisible and never queued for exploration.

**Downstream.** The catalogue converges to a chemically blind set of classes whose rates are averages
over undetected decorations. Because the coverage report shows these as exact (F5), nothing signals
the miss.

**Fix.** Do not gate novelty on barrier agreement. Compare `κ` at *full* `r_ctx` (not `promoted_shell`)
for the new-class decision, and separate "identity resolution" (must be full-context) from "rate
granularity" (may be promoted). Audit or at least *flag* any instance whose full-`r_ctx` context is not
byte-identical to an existing member, regardless of barrier. Make the convergence signal require
*new full-context environments → 0*, not *new coarse classes → 0*.

## C4 — Class-mean forward/backward barriers form a fictitious ΔE → wrong equilibrium composition/SRO

**Component:** §7.2 `C.dEnergy = Eₐ_f − Eₐ_b` with `Eₐ_f`, `Eₐ_b` independent trimmed means;
§5.3 runtime uses class rates.

**Mechanism.** `Eₐ_f` is the trimmed mean over the *forward* class's member sub-environments; `Eₐ_b`
is the trimmed mean over the *backward* class's members. Nothing guarantees these member sets are the
pairwise reverses of each other — fold-in populates them independently, and `ν0_f`, `ν0_b` are
independent geometric means (ratio-of-means ≠ mean-of-ratios). So `dEnergy = Eₐ_f − Eₐ_b` is not the
ΔE of any physical pair, nor the mean pair-ΔE. At runtime, after a forward hop at a specific site, the
reverse fires at the *backward class mean* rate — averaged over a different population than that site.
The site-level ratio `k_f/k_b` therefore encodes a fictitious ΔE.

**Trigger.** Run any dilute-vacancy NiCr slab to steady state. The rejection-free walk relaxes toward
the Boltzmann distribution of the *effective* energies implied by `{k_f/k_b}` — which are the fictitious
class-mean ΔEs, not the true site ΔEs. The stationary composition and Warren–Cowley SRO the coverage
report tracks (§7.3) settle to the **wrong** values.

**Downstream.** The primary scientific observable (dealloying composition profile / surface SRO) is
biased systematically and composition-dependently (it is a mixture-averaging artifact, not zero-mean
noise). G2 cannot catch it (C2). W5' acknowledges "residual inconsistency can bias equilibrium" but
frames it as small drift caught by G2; in fact it is a first-order, undetectable bias.

**Fix.** Enforce balance **per contributing pair before averaging** (symmetrize each measured
forward/backward pair to a single ΔE and one `ν0_f/ν0_b`, §7.2's `enforce_balance`, as the *default*
not an option), and average in rate space (C1). If forward and backward classes cannot be shown to
have paired members, do not claim reversibility for that class — flag it.

## C5 — Harvest bias: the loop can converge to a fully-catalogued but dynamically-wrong basin, with healthy-looking metrics

**Component:** decisions 1/3/6; §7.3 coverage metrics; the whole alternation loop.

**Mechanism.** The pyKMC leg harvests events only from configurations the *on-lattice* leg reached
(each cycle maps the current lattice state back to atoms and runs k=20–1000 steps there). If the
on-lattice rates are systematically wrong (C1–C4), the 10⁶-step evolve leg visits the wrong region of
configuration space, so pyKMC harvests events for the wrong states, completing the catalogue *for a
basin the true dynamics would never occupy*. This is self-reinforcing: wrong rates → wrong trajectory
→ harvest where the trajectory went → catalogue "completes" there → new-classes-per-cycle → 0. The
coverage metrics all read healthy **because** the dynamics are wrong:
- **Fallback flux fraction → 0** is a ratio of `R_fallback/R_total` where *both* are computed from the
  (wrong) catalogue rates; it measures catalogue coverage of the *visited* states, not rate
  correctness. Every exact rate can be 100× off and this reads 0.
- **Observed-but-unharvested environments → ∅**: an environment appears only if *reached*; the truly
  important environments are precisely those the wrong rates never reach, so they never enter the list.
  Empty is not evidence of coverage.
- **Composition/SRO drift** is reported relative to *cycle start*, with no correct-trajectory reference,
  so a run drifting to the wrong state reports a finite, innocuous-looking drift.

**Trigger.** Any run where C1/C3 suppress the low-barrier dealloying channel: the vacancy stays in the
Ni-rich subsurface, pyKMC keeps re-harvesting Ni hops, `new classes → 0` by cycle ~5, loop declares
convergence; the Cr-stripping surface events are never in the catalogue and never in the unharvested
list.

**Downstream.** A converged catalogue that produces wrong physics, with no metric that flags it —
the definition of a silently poisoned deliverable. The convergence criterion validates *catalogue
self-consistency*, never *sampling correctness*.

**Fix.** Add an independent correctness probe that does not depend on the catalogue's own rates:
periodically (i) run a *short direct pyKMC trajectory* from a lattice state and compare the *event
frequency spectrum* to the on-lattice prediction (KL/χ² on which classes fire, not just barrier values);
(ii) seed exploration from *forced* off-distribution states (planted Cr-depleted surface patches), not
only from states the biased trajectory reached. Treat convergence as reached only when the direct-vs-
on-lattice event spectrum also agrees.

---

# MAJOR FINDINGS

## M1 — Saddle-token snapping has no tolerance → token flicker → non-terminating loop

**Component:** §3.3 `saddle_token = round_to_sublattice(2·(saddle − midpoint))`; convergence signal.

**Mechanism.** The saddle is intrinsically off-lattice and pyKMC's saddle is AV-relaxed pARTn output
(the source flags AV-relaxation as an explicit "drift channel," `event_table.py:637–643`). The token is
a hard `round_to_sublattice` with **no tolerance or hysteresis** (unlike atom snapping, which has
`snap_tol`/`soft_surface_tol`, §2.3). A saddle sitting near the bridge/hollow sublattice-cell boundary
snaps to *different* integer points across cycles as relaxation noise nudges it. Different token →
different `canonical_form` → different `class_id` → a **new class** for the *same physical event*.

**Trigger.** Any event whose saddle lands near a cell boundary (common for surface/concerted events
where the path is diffuse). Cycle N assigns token t₁; cycle N+2, from a slightly different live config,
assigns t₂. The class is re-born. `new classes per cycle` never reaches 0 → the loop's only stop
condition never fires → it runs forever, or a human must manually merge the flickering classes.

**Downstream.** Non-convergence; audit-queue flooding (each flicker is a first-instance NEW_CLASS →
audit); barrier lists fragmented across duplicate classes so even the (already wrong) averaging is
further degraded.

**Fix.** Give the token snap a tolerance band with hysteresis (a saddle within ε of a boundary keeps
its previously assigned token for that class), or make the token a *coarse categorical* (bridge vs
hollow vs top) decided by a robust geometric test, not a raw lattice round. Add a token-stability unit
test across re-relaxations of the same event.

## M2 — Fallback extrapolation into unseen NiCr compositions is exponential and drives the handoff config

**Component:** §6.2 per-`family_id` ridge/GP; frozen model; §6.3 clamp+flag.

**Mechanism.** Early cycles on a dilute-Cr slab harvest mostly Ni environments, so the family
regressor's φ columns for Cr-bond-counts are near-zero-variance → ridge shrinks their coefficients to
≈0 → the model predicts **Ni-like barriers for Cr environments**. When dealloying evolution later
produces Cr-enriched/-depleted local environments (outside the training hull), the fallback
extrapolates; a 0.2 eV error is ~10²–10³× in rate (table above), and it persists for the *entire*
10⁶-step leg until the next harvest. The clamp to `[emin,emax]` + `high_uncertainty` flag bounds the
absurdity but the flagged rate still *carries flux* and *steers the trajectory* for a full leg. The
GP's "principled σ" is only principled inside the training distribution; for a genuinely novel
composition the RBF kernel saturates σ at the prior — a **falsely bounded** uncertainty — so the
exploration-priority ranking *under*-weights exactly the environments most in need of harvest.

**Trigger.** First leg after the surface starts stripping Cr: local composition moves off the Ni-rich
training hull; fallback predicts Ni-like (too slow, or clamped) rates for the Cr-vacancy motifs; the
leg spends 10⁶ steps under wrong rates and hands back a config that under-represents the stripping,
which then biases the next harvest (feeds C5).

**Downstream.** W3 admits "mis-allocated between harvests, biasing the trajectory," but understates it:
the mis-allocation is exponential, monotone (frozen model, M3), and concentrated at the dealloying
front. GP σ under-ranks the very sites it should prioritize.

**Fix.** Detect out-of-hull φ (convex-hull / leverage test on the fitted design matrix) and treat it as
*hard novelty* (route to exploration immediately at a high floor rate, do not trust the extrapolant);
do not let a zero-variance species column silently yield an Ni-like prediction — require a minimum
count of *that species'* environments in the family before predicting for it, else fall to family-mean
with honest (large) σ. Use a σ that grows with extrapolation distance (leverage), not RBF-prior-saturated.

## M3 — Frozen-model refit vs in-leg composition drift: the leg's late portion is rated by the stalest model

**Component:** §6.2 "refit at cycle boundaries only … frozen model between cycles."

**Mechanism.** The fallback model is frozen at cycle-start composition for reproducibility. But a
10⁶-step dealloying leg *deliberately* drifts composition/SRO far from cycle start — that is the point.
So the model is freshest where the run has moved least and **stalest at the dealloying front at
end-of-leg**, which is exactly the config handed to the next harvest. Reproducibility (a real benefit)
is bought with a monotone, structured staleness bias that compounds M2 and feeds C5.

**Trigger.** Any leg with meaningful evolution. By step 10⁶ the local compositions the fallback is
rating bear little resemblance to the step-0 fit.

**Downstream.** The handoff config — the thing that determines the next harvest — is generated under
the most-wrong rates of the whole leg.

**Fix.** Decouple reproducibility from staleness: allow *within-leg* refits triggered by a monitored
drift metric (e.g. when mean |φ − φ_fit_centroid| exceeds a threshold), logging each refit's model
version so the run stays replayable. Or shorten `n` adaptively when drift is fast.

## M4 — SPLIT_CHECK and `trimmed_mean` are ingest-order-dependent → non-reproducible catalogue/rates

**Component:** §4.4 SPLIT_CHECK (`|Eₐ − mean(C.barriers)| ≤ split_tol`); §6.1 running trimmed mean;
§8.3 determinism claim.

**Mechanism.** Both the merge/split decision and the class mean depend on the *order* barriers are
ingested. Example: class holds [0.60, 0.62] (mean 0.61). Ingest 0.75 → |0.75−0.61|=0.14 < 0.15 →
merged, mean 0.657. Then 0.50 → |0.50−0.657|=0.157 > 0.15 → SPLIT_CHECK. Reverse the order (0.50 first):
|0.50−0.61|=0.11 < 0.15 → merged, mean 0.573; then 0.75 → |0.75−0.573|=0.177 > 0.15 → SPLIT_CHECK on a
*different* member. Different cycle order (or within-cycle row order) → different partition → different
rates. §8.3 claims full reproducibility via "audit decision-log replay," but the *automatic* SPLIT_CHECK
merges/splits are not human decisions and are not obviously captured by that log; and a barrier that was
"exact" in cycle 3 can retroactively become an outlier by cycle 8 after already rating five 10⁶-step legs.

**Trigger.** Re-run the same campaign with cycles processed in a different order (e.g. different MPI
scheduling of harvest rows) → a different catalogue and different physics.

**Downstream.** The reproducibility guarantee (a stated deliverable property, §8.3) is false; provenance
`Eₐ_std` is order-dependent; a rate a site received depends on *when* in the loop it was evaluated.

**Fix.** Make aggregation order-invariant: recompute each class's `Eₐ`/partition from the *full
accumulated barrier set* at each cycle boundary (batch clustering, e.g. 1-D split at gaps > `split_tol`),
not by incremental running-mean comparison. Record the automatic split/merge decisions in the replay log.

## M5 — Synthesized "barrier-pending" reverses break microscopic reversibility (ratchet or wrong-rate)

**Component:** §7.2 `synthesize_reverse` (`pair_status = synthesized_pending`); §7.1 new classes are
"matchable only after approval"; §6.3 never-zero.

**Mechanism.** pyKMC's `is_valid_new_event` returns the forward row *only* in several branches
(`event_table.py:341–386`: when `event_id == id_final`, or when the backward is already known), so
one-sided harvests are common. The design then synthesizes the reverse as a new, audit-pending class.
Two readings, both broken:
- **If audit-pending ⇒ not matchable** (§7.1's rule): after firing the forward, the reverse instance is
  structurally enumerated but its class is excluded from BKL → the reverse *cannot fire* → a **ratchet**:
  the vacancy hops A→B but not B→A until a later cycle measures the reverse. Irreversible, biased mass
  transport — directly corrupting dealloying dynamics.
- **If matchable with never-zero rate** (§6.3): the reverse fires at a *fallback/k_floor* rate while the
  forward has a *measured* rate → `k_f/k_b` is arbitrary → detailed balance violated for every one-sided
  pair until harvested.

**Trigger.** Any event pyKMC returns forward-only. First such vacancy hop near the surface → either a
one-way pump (ratchet) or an unbalanced pair, for as many cycles as it takes to harvest the reverse.

**Downstream.** Systematic reversibility violation across a large fraction of the catalogue; the
"pairing closure mid-harvest" the design sells is *structural* (a row exists) not *physical* (the rate
is right).

**Fix.** Do not execute a synthesized reverse until its barrier is measured; instead, if the forward is
executable, *withhold the forward too* (or rate the reverse by the balance relation from the forward's
measured ΔE and a prefactor estimate, `k_b = k_f·(ν0_b/ν0_f)·exp(ΔE/k_BT)`, so the pair is balanced by
construction pending harvest). Never let a measured-forward / guessed-reverse pair into the BKL vector.

## M6 — The "refines-`event_id`" validator rests on a frame-inconsistent pyKMC partition

**Component:** §4.4/§7.3 refinement invariant ("class partition refines `(event_id, id_saddle)`,
never a wrong merge"); §4.6 fan-out/fold-in.

**Mechanism.** Post-fix, pyKMC's *forward* `event_id` is the mover's **LIVE full-system** classifier
hash, while the *backward* `event_id` is **re-derived from AV-relaxed** min2 geometry, and `id_saddle`
is re-derived from the AV-relaxed saddle (`event_table.py:645–647, 660, 678, 686`). So the partition
the design refines against is internally frame-inconsistent: forward keys live, backward/saddle keys
relaxed. The on-lattice `κ` is computed in one consistent occupancy frame. Refining a consistent
partition against a mixed-frame one produces **both** false alarms (a forward live-hash split the
on-lattice stencil cannot represent → SPLIT_CHECK exhausts shells → IRREDUCIBLE_SPREAD audit flood)
**and** false passes (a re-derived backward hash that merges what should split). Separately, the
invariant's own barrier-gap escape ("no κ may contain two rows of different `event_id` with barrier gap
> 0.25 eV") *legitimizes* merging distinct environments up to 0.25 eV = up to 1.6×10⁴× rate at 300 K —
so the celebrated "never a wrong merge" guarantee is only "never a merge wronger than 4 orders of
magnitude in rate."

**Trigger.** A surface event whose live full-system mover environment differs beyond the AV region from
its relaxed re-derivation → forward `event_id` splits two rows the on-lattice class holds; if their
barriers differ > 0.25 eV, spurious audit; if < 0.25 eV, silent (masking a real distinction).

**Downstream.** The design's load-bearing safety check (never-wrong-merge) is unreliable in both
directions and over-sold by ~4 orders of magnitude; audit volume is unpredictable.

**Fix.** Refine against a *single-frame* pyKMC key (use `id_saddle`, which is shared and re-derived
consistently for both rows, plus re-derived `id_min1`/`id_min2` — not the live forward hash) for the
validator; state the guarantee in rate units (merge only within `k_BT`-scale barrier agreement), not
0.25 eV.

---

# MINOR FINDINGS

## m1 — `Eₐ_std = 0` for single-sample classes is reported as high confidence

**Component:** §1.3 `Eₐ_std`, `barriers[]`; §8.1 provenance; §6.2 weight "by low `Eₐ_std`."

**Mechanism.** With dilute defects and k=20–1000 harvest steps, most classes have 1–few barriers.
`trimmed_mean` is ill-defined for n≤3 (trimming removes the only data), and `Eₐ_std` = 0 for n=1. The
provenance and the fallback weighting (§6.2 "weight by … low `Eₐ_std`") then read a single, unvalidated
sample as *maximally trustworthy*, and up-weight it in the regression fit. SPLIT_CHECK against a
one-sample mean also fires on the first genuinely-consistent second sample noise.

**Trigger.** Any freshly harvested class (the common case early in a campaign).

**Downstream.** Confidence-weighted fallback fits are dominated by n=1 "zero-variance" classes;
coverage/provenance overstates catalogue maturity.

**Fix.** Report `Eₐ_std` as undefined (not 0) for n<3; use a shrinkage/Bayesian std with a prior floor;
weight fits by *effective sample count*, not by an std that is 0 for singletons.

---

## Requested angles — coverage map

- **Rate provenance & barrier aggregation across harvests:** root defect + C1, C3, M4, m1.
- **Fallback-regression validity & extrapolation into unseen compositions:** M2, M3.
- **Novelty false-negatives (new event absorbed into a class):** C3 (primary), M1 (fragmentation dual),
  M6 (barrier-gap escape).
- **Coverage-report metrics healthy-while-wrong:** C5 (primary), C2 (a gate green by construction),
  C3 (0-fallback despite absorbed physics).
- **Detailed-balance violations:** C2 (gate is a tautology), C4 (fictitious class-mean ΔE → wrong
  equilibrium), M5 (synthesized reverses).
- **Alternation-loop failure modes:** C5 (harvest bias / false convergence), M1 (token-flicker
  non-convergence), M3 (frozen-model staleness), M4 (order-dependent non-reproducibility).

## Out of scope / not pursued (clean-room + lens discipline)

- §4.7 `sym_perm` semantics: verified the draft's reading against `symmetries.py` (species-blind
  orbit-of-displacements, is_duplicated-filtered, identity prepended) — the draft is correct there;
  this is a classification-robustness concern, not a statistics/loop one.
- Runtime-matching complexity, tiled-SoA correctness, I1–I5 mechanics: performance lens, not attacked
  here except where a metric (I5) intersects the statistical claims.
