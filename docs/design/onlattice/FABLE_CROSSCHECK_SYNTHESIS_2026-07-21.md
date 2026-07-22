# Independent cross-check synthesis of the pylatkmc deep-research claims

**Author:** Claude Fable 5, 2026-07-21 (independent of the parent Opus judge synthesis).
**Evidence base:** `DEEP_RESEARCH_CLAIMS_2026-07-18.json` — 5 passes, 72 confirmed / 5 refuted /
48 unverified claims. Written **before** reading `DEEP_RESEARCH_FINDINGS_2026-07-18.md`; the diff
against that report is in `FABLE_CROSSCHECK_DIFF_2026-07-21.md`.

**Verification bar (stamped):** each `confirmed` claim survived a 3-voter Opus adversarial pass
(voters instructed to refute, defaulting to refuted when uncertain; ≥2 refutes kills).
`unverified` claims are single extractions whose voters **errored on a usage limit** — they are
leads, not stress-tested findings, and are labelled LEAD below. Reference strings (DOI/arXiv) were
not hand-verified. Claim IDs are `[pass :: status #n]` in the JSON's ordering.

**Independence disclosure:** the project memory index shown at session start contained the parent
synthesis's one-line headline ("replace discrete class catalogue + split_tol with a continuous
barrier surrogate"). I could not un-see it. The reasoning below is built from the claims JSON
alone, and — as the reader will notice — I land on that headline **in weaker form**, which is
itself evidence the reasoning here is not a paraphrase of the parent's.

**Confidence vocabulary:** CONFIRMED = survived adversarial verification (3-0 or 2-0-with-1-error;
2-1 noted as "with dissent"). LEAD = unverified (voters errored). Refuted claims are treated as
dead but their refutations are themselves informative and are used as such.

---

## Findings

### F1 — Continuous occupation-descriptor surrogates reach 0.04–0.1 eV RMSE for *bulk* vacancy hops in concentrated FCC alloys, including the Ni-Fe-Cr family. CONFIRMED.

- One-hot occupation + PCA + ridge, Al-Mg-Zn, 2000 train / 500 test DFT-NEB events: RMSE < 0.04 eV
  for both ΔEa and ΔE [1-barrier-surrogate :: confirmed #4].
- SVR on local-chemical-environment descriptors: RMSE < 0.1 eV in concentrated NiFeCr, < 0.07 eV
  in quinary NiFeCrCoCu [1 :: c#13] — the exact alloy family of interest.
- ANN on ~32,000 NEB barriers covering fcc Ni₁₋ₓFeₓ across the full composition range, evaluated
  on-the-fly inside KMC [1 :: c#7, c#12].
- Beyond-KRA transition-state cluster expansions: 0.18 eV test RMSE (Ta-W) [1 :: c#2];
  0.127 eV LOOCV (Pt-Ni, bulk+surface) [1 :: c#3].

**Caveats that bound this finding:** every confirmed accuracy number is for *single-atom
vacancy-exchange hops*, overwhelmingly in bulk, with training sets of 2,000–32,000 barriers.
Nothing here transfers automatically to (a) concerted/multi-atom events, (b) strongly-relaxed
near-surface or dealloying-front geometries, or (c) a data regime of a few hundred training
barriers. Sources are single unreplicated studies per system (indirectness + no replication in
GRADE terms), but the pattern is consistent across four independent groups/systems.

### F2 — Low-order bond-count / BEP / constant-KRA models carry 0.2–0.3 eV error and demonstrably break in concentrated FCC alloys. CONFIRMED.

- On identical Pt-Ni data: broken-bond 0.281 eV, KRA broken-bond 0.227 eV, constant-Ea 0.214 eV,
  Marcus parabolic 0.204 eV vs cluster expansion 0.127 eV [1 :: c#3].
- Generalized-BEP ML on its surface-chemistry home turf: 0.23 eV out-of-sample MAE [1 :: c#1];
  BEP requires re-parameterization per reaction class [1 :: c#8].
- The constant-KRA / Kinetic Ising decomposition is "not broadly applicable to FCC alloys" —
  local lattice distortion makes the kinetically-resolved term environment-dependent [1 :: c#5].
- KRA (barrier as a function of endpoint ΔE alone) fails outright for Ta-W: r² = 0.21 between
  barrier and driving force [1 :: c#9].

**Design meaning:** the FINAL_DESIGN §6 sketch of a low-order bond-count/GCN φ regressor sits in
the 0.2–0.3 eV error tier — roughly 4–8× kT at 500 K (kT ≈ 0.043 eV) in the exponent, i.e. rate
errors of 10²–10³. As the *majority* flux channel this is not a fallback, it is the simulation.

### F3 — Transport in concentrated alloys can percolate through the low-barrier tail; aggregation that compresses barrier spread corrupts exactly the channel dealloying rides on. CONFIRMED (tail hazard) + LEAD (dissolution-specific corruption).

- Ta-W: crossover to percolated low-barrier transport networks (~11–59% Ta), aligned with the BCC
  bond-percolation threshold [1 :: c#0].
- Bimodal barrier distributions in FCC Cu-based concentrated alloys, explicitly linked to
  percolating fast diffusion channels [1 :: c#6].
- LEAD: in Pt₃Ni dissolution KMC, low-spread barrier models (broken-bond, constant-Ea)
  artificially accelerate the rare low-barrier events that drive Ni segregation/dissolution
  [1 :: unverified #5].

**Design meaning:** any class-mean or trimmed-mean rate over a lumped class biases the low-barrier
tail — this is the mechanism by which `split_tol`-style lumping suppresses or inflates the fast Cr
channel. Note the important refutation here: the claim that the KRA-symmetric term (not the
driving force) *dominates* barrier variance was REFUTED [1 :: refuted #0], so the tail hazard
should be argued from the percolation evidence, not from a variance-decomposition story.

### F4 — Detailed balance: enforce it by construction via a symmetric + antisymmetric decomposition from one configurational energy model. LEAD (recipe), CONFIRMED (why a naive regressor can't).

- LEAD: ΔE_b(A→B) = ΔE_KRA(A,B) + ½ΔE(A,B), with rates in the form k = Z*₍A,B₎/Z_A (numerator
  exchange-invariant, denominator initial-state-only) ⇒ detailed balance holds by construction
  [1 :: u#2]; plain broken-bond violates DB, KRA-style symmetrization restores it [1 :: u#4].
- CONFIRMED: forward and backward barriers depend on *different* atom sets and are only weakly
  correlated [1 :: c#10] — so two independently-fitted directional regressors will not satisfy DB,
  and a single symmetric descriptor cannot recover both directions.

**Design meaning:** whatever model class Phase C picks, the DB-safe form is: one continuous
*symmetric* (endpoint-exchange-invariant) barrier component plus half the endpoint energy
difference from a single lattice energy model. This dissolves the class-mean-ΔE DB defect (audit
gap 6) structurally rather than by post-hoc correction. The recipe claim is a lead — but it is
also elementary algebra on the Metropolis/KRA form, so I rate the *practice* safe to adopt while
flagging the citation as unverified.

### F5 — Production self-learning KMC codes never consume a class-average rate where geometry has relaxed: recognition is topological, and every reused barrier is re-converged per site (or the match is only a seed for a fresh search). CONFIRMED.

- k-ART recognition is graph-topological (NAUTY canonical keys), with *no* Cartesian residual
  threshold in matching [2 :: c#1, c#3, c#8]; unseen topology → fresh ART searches, known →
  reuse [2 :: c#0].
- Two-stage decoupling of recognition from rate accuracy: generic (catalogued) saddles converged
  loosely — 1.0 eV/Å in the 2008 paper [2 :: c#5], "typically 0.5 eV/Å" in the 2011 methodology
  paper [2 :: c#2] (parameter evolution across papers, not a real contradiction) — then every
  *reuse* re-converged at 0.1 eV/Å to ~0.01 eV barrier precision [2 :: c#2, c#5].
- Topology↔geometry degeneracy is detected by *reconstruction failure* (the saddle vanishes on
  re-convergence) [2 :: c#7] and split by locally adjusting the graph connectivity cutoff
  [2 :: c#4]; uniqueness is a stated precondition of the whole scheme [2 :: c#6 (2-1), 5 :: c#9].
- LEADs, all pointing the same way: EON's kinetic database uses loose geometric match *only to
  seed* a dimer search; a mechanism enters the rate table only when an exact saddle re-converges,
  so matching tolerance adds zero rate error [2 :: u#1, u#4, u#11]; SEAKMC skips stored-environment
  matching entirely (active volumes, flush-and-resample) [2 :: u#12]; k-ART's event filter (RMSD
  2.1 Å) is tuned to kinetics (flicker suppression), not lattice geometry [2 :: u#14].

**Design meaning (the single most important structural result):** the literature's answer to "the
snap tolerance rejects 316/439 classes" is *not* a wider tolerance and *not* a static regressor —
it is: classify topologically, and recompute the rate in the actual environment when reusing
(seed-then-reconverge). No confirmed claim anywhere supports deriving a projection tolerance from
a rate-error budget; the production codes are architected so that no such tolerance touches rates.

### F6 — The bookkeeping redesign (grouped BKL + tree selection + finite-radius incremental repair) is standard production practice; dense n_procs×n_sites tables are not. CONFIRMED.

- Local-only updates after a firing: SPPARKS recomputes only altered-site propensities [3 :: c#3]
  with an explicit interaction-radius parameter h_energy defining the invalidation neighbourhood
  [3 :: c#5]; KMCLib re-matches only the interaction vicinity — O(1) in N [3 :: c#9]; kmcos never
  rescans after initialization and updates avail_sites only locally [3 :: c#11], with measured
  ~O(1) step cost to ~10⁵ sites [3 :: c#13 (2-1)].
- The claim that KMCLib keeps a pyKMC-style dense availability table was REFUTED [3 :: r#1] —
  sorted per-site match-lists, not a dense n_procs×n_sites array.
- Selection: kmcos uses two-level BKL binary search [3 :: c#18]; SPPARKS offers O(N)/O(log N)/O(1)
  solvers [3 :: c#10]; composition-rejection is exact and composable without rate quantization
  [3 :: c#0, c#4, c#7, c#16], **but** update cost, not selection-search cost, usually dominates
  [3 :: c#2, c#14] — so a Fenwick/binary-tree BKL is sufficient and CR is an optimization to
  benchmark, not a correctness need. The scare-claim that selection goes polynomial in
  dense-active regimes was REFUTED [3 :: r#0].
- Correctness construct: Gibson–Bruck's dependency graph formally determines the exact propensity
  set to update [3 :: c#12]; its sufficiency is proven in the chemical-network setting
  [3 :: u#3, LEAD]. The *spatial* analogue's sufficiency is asserted-not-proven even in Zacros
  [3 :: u#0, u#2, LEADs] — so pylatkmc's "dirty-ball is sufficient" gap is shared by mature
  production codes, and an explicit derivation (context radius vs interaction radius) would
  exceed published practice, not just match it.
- Distributed KMC in the dense-active regime is expensive: Zacros Time-Warp is exact but re-simulates
  ~14.7 KMC time units per unit advanced (range 5.8–69.2) [3 :: c#15, c#17].

### F7 — Stop criteria: rate-weighted completeness (fraction of total rate found) is the principled currency; count-based and coverage-based criteria are qualitatively useful but unquantifiable. CONFIRMED.

- Xu–Henkelman: C = 1 − 1/Nr (95% ⇒ 20 consecutive redundant searches) [4 :: c#3], derived under
  an equal-findability heuristic [4 :: c#8], with the worst-case extension C = 1 − 1/(αNr)
  [4 :: c#14].
- Count-based completeness has formally unquantifiable uncertainty because saddle discovery
  frequencies vary widely [4 :: c#12]; empirically rate-weighted completeness converges as the
  ideal α=1 curve while count-based follows α≈0.25 [4 :: c#13].
- The rate-weighted estimator lineage (Chill–Henkelman MD saddle searches, discovery probability ∝
  rate) is rigorous: consistent, MSE → 0 [4 :: c#4, c#5, c#10, c#11]; the Eyring–Kramers-based
  variant R̃ can over-report completeness when the rate law deviates, while the Monte-Carlo variant
  R̂ is conservative [4 :: c#7].
- Production practice is behind the theory: k-ART uses a log-frequency search heuristic with no
  statistical criterion [4 :: c#0, c#6, c#9]; EON exposes a confidence knob (default 0.99)
  [4 :: c#15] that remains count-based — the claim that its 20 kT window makes it rate-weighted
  was REFUTED [4 :: r#0].
- LEAD (important caution, named in the handoff): the rate-weighted estimator is biased
  *over-optimistic* early, when fast processes are found first and the sample is uncharacteristic
  [4 :: u#6]; the operational threshold used in MDSS-AKMC was X(F) < 0.01 ≈ 99% escape-rate
  confidence [4 :: u#2].

**Design meaning:** pylatkmc's planned "new-classes-per-cycle = 0 AND fallback-flux-fraction = 0"
switch is a count/coverage criterion computed from the catalogue's own biased trajectory — the
exact construction the confirmed evidence says is unquantifiable. The upgrade path exists and has
proofs: track fraction-of-total-rate-found per state class, use the conservative estimator, and
report a confidence, not a zero-count.

### F8 — Event identity: only canonical labeling of the chemistry-colored local graph gives the "equivalent ⇔ identical id" guarantee; it also emits the automorphism group needed to fix multi-anchor over-counting. CONFIRMED.

- Canonical form definition and label-invariance: isomorphic iff canonical forms identical
  [5 :: c#1, c#5, c#8, c#12]; precisely the property a frame-dependent lexicographic anchor
  tie-break violates [5 :: c#8].
- nauty/Traces (individualization-refinement) compute the automorphism group as a byproduct
  [5 :: c#2, c#6]; all production tools share the same correctness, differing only in heuristics
  [5 :: c#3, c#13 (2-0)].
- k-ART applies exactly this in production (canonical key + permutation key for reconstruction)
  [5 :: c#4, c#11], anchored frame-independently on the max-displacement atom [5 :: c#10], with
  direction-of-motion appended to split symmetric same-topology events [5 :: c#0], and validity
  conditional on graph↔geometry uniqueness [5 :: c#9].
- LEADs: Zacros weights symmetric patterns by a graph-multiplicity/symmetry number [5 :: u#2] or
  restricts detection to one mapping per instance [5 :: u#7]; graph patterns carry no positional
  data, so no orientation enumeration is needed [5 :: u#9].

### F9 — Near-surface barriers are layer- and species-resolved (Cr-sensitive), so a single global point-group/symmetry choice for the catalogue is suspect. LEAD only.

All the direct evidence here went unverified: layer-resolved NiCr(100) DFT barrier surveys
[5 :: u#0], lower vacancy–Cr exchange barriers near the surface [5 :: u#4], sub-layer Cr chemistry
gating in-plane hops [5 :: u#10], Cu(100) surface vacancy hop 0.42–0.47 eV vs ~0.7 eV bulk
[5 :: u#3, u#5], Erlebacher coordination-number site rules [5 :: u#8]. Directionally consistent
and physically expected, but nothing in this evidence base survived verification — treat as leads
requiring either verification or in-house EAM checks.

---

## What the evidence does NOT establish (silences that are design inputs)

1. **No confirmed claim shows any static atom-centered surrogate predicting concerted /
   multi-atom / strongly-relaxed saddle barriers.** The one framework closest to the need
   (SOAP-GP with uncertainty-triggered NEB fallback, [1 :: u#0, u#7]) is demonstrated only on
   single-element Ag(111) adatom diffusion [1 :: u#8] — and even that is a LEAD. The audit's "no
   published reassurance exists" stands unrefuted after a five-pass adversarially-verified sweep.
   For pylatkmc this silence is decisive, because the strongly-relaxed events are the majority
   channel (316/439 G3 fails, median snap residual 1.44 Å).
2. **No principled method to set a lattice-projection/matching tolerance from a rate-error
   budget** surfaced in any pass — production codes are structured to avoid needing one (F5).
3. **Scant confirmed accuracy evidence in the few-hundred-barrier training regime.** The headline
   surrogate results used 2,000 (Al-Mg-Zn one-hot ridge [1 :: c#4]) to ~32,000 (NiFe ANN
   [1 :: c#7]) training barriers; the NiFeCr SVR figure is quoted over only 120 data points
   [1 :: c#13], though the quote does not resolve train-vs-test size, and the Pt-Ni TS-CE used
   ~500 structures+NEBs [1 :: u#1]. With 445 heterogeneous harvested events, pylatkmc sits at the
   bottom of the published data range — expect materially worse RMSE than the headline numbers
   until the harvest loop grows the corpus. *(Corrected after first draft on re-reading c#13 — a
   self-correction from the claims, not from the parent report; see diff item D0.)*
4. **Dealloying/porous-morphology site classification** (bicontinuous, multi-valued z) has only
   unverified precedent here (coordination thresholds, Erlebacher lineage).

---

## What each pass settles for the engine

- **Pass 1 (rate model):** a continuous, occupation-based, DB-safe symmetric+antisymmetric
  surrogate is the right *form* for lattice-representable vacancy hops, with a proven accuracy
  ceiling (0.04–0.1 eV) far better than the current low-order φ sketch (0.2–0.3 eV) — but its
  demonstrated domain is bulk single-atom hops with ≫445 training barriers.
- **Pass 2 (projection):** stop trying to make the snap tolerance carry physics. Topological
  classification + per-site re-convergence (or seed-then-reconverge via the off-lattice engine) is
  the only pattern with confirmed support for the strongly-relaxed tail.
- **Pass 3 (bookkeeping):** the grouped-BKL + Fenwick + dirty-ball redesign is validated as
  production-standard; derive the repair set Gibson–Bruck-style with an explicit radius parameter;
  skip composition-rejection until profiling shows selection (not update) dominates.
- **Pass 4 (loop control):** replace the zero-count switch criteria with rate-weighted
  completeness + confidence (conservative estimator; the fast-events-first over-optimism caveat
  applies to exactly pylatkmc's planned self-referential metric).
- **Pass 5 (identity):** replace the anchored-D4h minimization with nauty-style canonical labeling
  of the colored environment graph; use the automorphism order (or one-mapping-per-instance
  detection) to kill multi-anchor over-counting exactly.

## Cross-pass verdict on the headline architecture question

Does a continuous surrogate subsume the discrete class catalogue? **On this evidence: it subsumes
the catalogue's *rate-assignment* role for lattice-representable bulk-like hops — eventually — but
it cannot subsume the catalogue's role as curated training/validation data, and it cannot cover
the strongly-relaxed majority channel at all.** Three-tier architecture is what the evidence
carries:

1. **Continuous DB-safe surrogate** (one-hot/cluster-expansion-family symmetric term + ½ΔE from a
   single lattice energy model) as the rate provider for lattice-representable hops. This
   dissolves `split_tol` lumping (gap 3) and the class-mean-ΔE detailed-balance defect (gap 6) *by
   construction*. Today it is data-starved (445 barriers vs ≥2,000 in every confirmed result);
   the harvest loop must keep feeding it before it can be trusted as primary.
2. **Exact-match catalogue** retained as the training corpus, provenance record, and regression
   test for the surrogate — not as the runtime rate authority once (1) is validated. In the
   current ~1.01-members-per-class regime, class rates *are* individual harvested barriers, so the
   lumping bias is mostly prospective; the DB defect is not, and argues for (1) regardless.
3. **On-the-fly / TS-aware channel** (route to the off-lattice engine, seed-then-reconverge, or
   uncertainty-triggered re-search) for out-of-distribution, concerted, and strongly-relaxed
   events. This is not optional: it is the only mechanism with any support — confirmed production
   practice (F5) plus the active-learning lead [1 :: u#0] — for the events that are currently the
   majority of pylatkmc's flux.

Confidence: HIGH on the three-tier shape and on rejecting a static low-order φ as the majority
channel (F1+F2+F5 are all confirmed-tier). MODERATE on the surrogate's eventual accuracy in
Ni-Cr specifically (transfers from Al-Mg-Zn/NiFeCr-bulk studies; needs the in-house fit).
LOW/undetermined on any static model for the concerted tail — the literature is silent, and the
silence survived adversarial search.
