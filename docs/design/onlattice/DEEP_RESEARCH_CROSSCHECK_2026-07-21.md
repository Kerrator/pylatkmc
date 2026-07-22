# Deep-research cross-check — independent Fable synthesis + diff vs judge report

Companion to `DEEP_RESEARCH_FINDINGS_2026-07-18.md` and `DEEP_RESEARCH_CLAIMS_2026-07-18.json`.
Produced 2026-07-21 by a fresh session (Fable) as an anchoring-free cross-check: Part 1 was
written from the claims JSON **alone, before reading the judge report**; Part 2 diffs the two.
Bottom line: all headline verdicts agree; the diff finds confidence-management defects at the
summary layer, five silently-dropped empty research questions, and two substantive additions
(lattice projection has no prior art; the rate-weighted stop criterion needs a pARTn sampling
caveat).

**Sibling cross-check:** a separate session independently executed the same handoff earlier the
same day (`FABLE_CROSSCHECK_SYNTHESIS_2026-07-21.md` / `FABLE_CROSSCHECK_DIFF_2026-07-21.md`,
feeding the draft `PHASEC_RATE_MODEL_DECISION.md`). This report was written without knowledge of
those files. The two diffs **converge with no contradictions** on every shared item (CR selection
optional not required; ν0_f ≠ ν0_b is inference not literature; percolation confirmed for Cu-based
FCC + BCC Ta-W, inferred for Ni-Cr; verdict-table confidence laundering). Unique to the sibling:
the data-regime caveat (445 harvested events ≈ 1.01 members/class — surrogate accuracy unproven at
that corpus size) and the representable-vs-non-representable population split that motivates its
headline refinement. Unique here: the pARTn discovery-sampling caveat on the rate-weighted stop
criterion (D3), the five silently-dropped empty research questions (4c/4d/4e/2e/5e), and the
no-prior-art-for-lattice-projection framing (D2) — which independently supports the sibling's
headline refinement.

---

# Part 1 — Independent synthesis of the 2026-07-18 deep-research claims (written blind)

Written from `DEEP_RESEARCH_CLAIMS_2026-07-18.json` **only**, before reading the parent's
`DEEP_RESEARCH_FINDINGS_2026-07-18.md` (cross-check discipline per handoff).

**Evidence bar.** "Confirmed" = survived 3-vote Opus adversarial refutation (voters instructed to
refute, default-refuted when uncertain, ≥2 refutes kills). "Unverified" = voters errored on the
session limit — single extractions, plausible, *not* stress-tested; used below only as flagged
**Leads**. Citations (DOI/arXiv strings) are plausible but not hand-verified. Confidence tiers used
below: **High** = multiple independent sources and clean 3-0 votes; **Moderate** = single source, or
2-0/2-1 votes; **Lead** = unverified.

---

## F1 — Barrier model: a continuous per-environment surrogate dominates the discrete class catalogue *and* its planned bond-count fallback (High)

The accuracy ladder assembled across confirmed claims:

| Model family | Error (eV) | System | Vote |
|---|---|---|---|
| Broken-bond | 0.281 RMSE (LOOCV) | Pt-Ni FCC | 2-0 |
| KRA broken-bond | 0.227 | Pt-Ni | 2-0 |
| Constant Ea | 0.214 | Pt-Ni | 2-0 |
| Parabolic (Marcus-like) | 0.204 | Pt-Ni | 2-0 |
| Generalized-BEP ML (home turf: surfaces) | 0.23 MAE held-out | metal surfaces | 3-0 |
| Transition-state cluster expansion | 0.127 (Pt-Ni) / 0.18 test (Ta-W) | FCC / BCC | 2-0 / 3-0 |
| SVR on local-environment descriptors | <0.1 (NiFeCr), <0.07 (quinary) | **the alloy family of interest** | 3-0 |
| One-hot occupation + PCA/ridge | <0.04 (ΔEa and ΔE) | Al-Mg-Zn FCC | 3-0 |
| ANN on ~32k NEB barriers, on-the-fly in KMC | full Ni₁₋ₓFeₓ range | FCC | 3-0 + 2-0 |

Two conclusions follow directly:

1. **The planned low-order bond-count/GCN regression fallback is not fit for purpose.** Every
   bond-count-class model sits at ~0.20–0.28 eV RMSE — *worse than the 0.15 eV split_tol it is
   meant to backstop*. BEP-family models additionally are not universal (must be re-parameterized
   per reaction class, 3-0) and carry a ~0.23 eV out-of-sample floor even on their surface home
   turf. (The Pt-Ni ladder is a single source at 2-0 — Moderate on exact numbers, High on the
   qualitative ordering because the Ta-W and BEP sources agree independently.)
2. **Cheap continuous surrogates beat split_tol with margin on exactly this alloy family.** SVR at
   <0.1 eV on NiFeCr and one-hot ridge at <0.04 eV on an FCC ternary are both well inside the
   0.15 eV lumping tolerance, and the Ni-Fe ANN demonstrates full-composition on-the-fly use inside
   KMC. A continuous surrogate therefore does not merely tighten the class catalogue — it removes
   the need for a within-class lumping tolerance altogether.

**Required structural properties of the surrogate** (all confirmed):

- Endpoint-energy-difference-only models fail: KRA/driving-force form is insufficient for Ta-W
  (barrier vs ΔE correlation r² = 0.21, 3-0), and the constant-KRA "kinetic Ising" decomposition is
  explicitly not applicable to FCC alloys because local lattice distortion makes the symmetric term
  environment-dependent (3-0).
- Forward and backward barriers depend on *different* atom sets and are only weakly correlated
  (3-0) — the descriptor must see both endpoint environments; a single symmetric descriptor cannot
  recover both directions.
- Detailed balance must therefore be engineered, not assumed. The concrete by-construction recipe —
  ΔE^b = ΔE^KRA + ½ΔE with rates k = Z̄*(A,B)/Z_A from one configurational energy model — is a
  **Lead** (voters errored), as is the claim that the plain broken-bond model violates detailed
  balance outright. The *need* is confirmed; the *recipe* is not.

**Guardrails from refuted claims:** do not assert that the symmetric (KRA) term dominates the
~1 eV barrier spread in concentrated FCC alloys generally (0-3 refuted — the source statement is
Al-alloy/size-effect-specific), and do not cite the χ*Sv electronic-descriptor 0.13–0.2 eV MAE
figure as a parametric-model benchmark (1-2 refuted).

## F2 — Transport rides the low-barrier tail; class-averaged (trimmed-mean) rates suppress the channel that matters (Moderate-to-High)

- Ta-W shows a confirmed crossover from solute trapping to percolated low-barrier transport near
  the bond-percolation threshold (3-0) — but that system is **BCC**.
- For FCC, the confirmed evidence is a bimodal barrier distribution in concentrated Cu-based FCC
  alloys with the low-barrier peak explicitly interpreted as a percolating fast channel (3-0).
- The most design-relevant version — KMC of Pt₃Ni dissolution where low-spread barrier models
  artificially accelerate the rare low-barrier events that drive segregation/dissolution — is a
  **Lead** only (voters errored).

Direction confirmed, FCC-Ni-Cr-specific quantification absent. Design consequence: per-class
trimmed-mean rate aggregation is precisely a tail-suppressor; per-instance surrogate evaluation
(F1) avoids the failure mode by construction. For a dealloying engine, whose physics *is* the rare
low-barrier dissolution channel, this is a first-order concern, not a refinement.

## F3 — Out-of-distribution control at the dealloying front: direction plausible, method unproven (Lead-dominated)

- Confirmed only: one ML model trained solely on binary-alloy data extrapolated compositionally to
  ternary/quaternary/quinary FCC without retraining — and that paper used **no** uncertainty-based
  OOD detection (3-0, single source).
- The active-learning pattern the design wants (GPR predictive uncertainty > 0.05 eV triggers a
  fresh NEB, result appended to training set) is a **Lead**, and the framework carrying it is
  demonstrated only on Ag/Ag(111) surface diffusion (also a Lead).
- **Concerted/multi-atom events:** the corpus contains *no confirmed evidence in either direction*
  that concerted saddles are predictable from atom-centered local descriptors. The on-the-fly
  off-lattice search channel cannot be retired on this evidence.

## F4 — Event identity: canonical graph labeling is the correct construct; the anchored-D4h minimization is formally deficient (High — the strongest cluster in the corpus)

Multiple independent 3-0 confirmations establish exactly the guarantee the red-team review found
missing:

- A canonical form satisfies iso ⇔ *identical* key (biconditional) and label-invariance
  C(G^γ) = C(G) under **all** input relabelings — not just a hand-chosen subgroup about one anchor.
  A frame-dependent lexicographic tie-break violates label-invariance by definition.
- Individualization-refinement (nauty/Traces) yields the **automorphism group as a byproduct** of
  canonization — supplying for free the symmetry number needed to correct multi-anchor
  over-counting. All major tools (nauty, Bliss, Traces) share the same correctness guarantee and
  differ only in heuristics (2-0).
- Production precedent: k-ART keys chemistry-colored local environments with nauty and gets back
  both the canonical index and the permutation key for geometric reconstruction (3-0, two sources).

Three confirmed supplements matter for the implementation:

1. **Precondition:** the topology key is a valid identity only if graph ⇒ unique relaxed structure
   (one-topology-one-geometry, 3-0). On a rigid lattice with fixed connectivity semantics this is
   easier to guarantee than off-lattice, but it must be stated and checked, not assumed.
2. **Canonical topology alone is insufficient for *event* identity:** in symmetric configurations,
   distinct events can share initial/saddle/final topologies, barrier, and displacement magnitude;
   k-ART additionally encodes the *direction of motion* (3-0). An on-lattice analogue (e.g. the
   displacement vector in the canonical frame) is required, or symmetric divacancy/ring events will
   collide the other way — merging genuinely distinct events.
3. **Multi-anchor resolution:** k-ART anchors each event to the atom with the largest displacement —
   a frame-independent physical rule (3-0) — not a lexicographic site choice.

What is *not* settled: the precise Zacros rate-side weighting rule for symmetric patterns. The
GM_γ graph-multiplicity factor is confirmed nowhere (Lead), and it applies to the cluster-expansion
*Hamiltonian*, not to process rates; the rate-side answer ("detection returns one valid mapping per
pattern instance by construction") is likewise a Lead. The safe route is the confirmed one: take
the automorphism order from the canonizer and derive the multiplicity correction yourself.

## F5 — Lattice projection: the field's answer to "what snap tolerance?" is *no snap tolerance* (High for the mechanism; open for the rigid-lattice transfer)

Confirmed k-ART mechanism, assembled:

- Recognition/routing is **binary on topological identity** (unseen topology → fresh searches;
  known → catalogued reuse), with no Cartesian displacement/residual threshold anywhere in matching
  (3-0 + 2-0; Si parameters: 5.0 Å environment sphere, 2.8 Å bond cutoff).
- The one-topology-many-geometries degeneracy is *detected operationally* — reconstruction onto a
  mismatched geometry systematically destroys the first-order saddle (3-0) — and *resolved
  structurally* by locally adjusting the connectivity cutoff until the conflated geometries split
  into distinct classes (3-0). Not by widening or tightening a geometric tolerance.
- Rate accuracy is decoupled from recognition by **per-instance re-convergence**: generic events
  converged loosely (0.5 eV/Å per the 2011 paper; 1.0 eV/Å per the 2008 paper — an era/system
  difference between confirmed claims, not a live dispute; flagged in the handoff), then every
  low-barrier reuse re-relaxed at 0.1 eV/Å to ~0.01 eV barrier precision (3-0).

Questions the corpus does **not** answer with confirmed evidence: every EON/KDB and SEAKMC
tolerance detail (all Leads — including the attractive "matching introduces no additional rate
approximation" seed-then-reconverge claims), any principled rate-error-budget-derived projection
tolerance (nothing found), and the typical fraction of off-lattice events non-representable on the
ideal lattice (nothing found).

**Design implication (mine, from the cross-pass structure):** the 0.9 Å snap-and-reject tolerance
has no literature analogue and no principled setting; the field instead classifies topologically
and buys rate accuracy per-instance. But k-ART's decoupling *depends on having a force engine at
reuse time*, which a rigid-lattice replay engine lacks. The on-lattice substitute for per-instance
re-convergence is per-instance **surrogate evaluation** (F1). Passes 1 and 2 independently converge
on the same architectural point: *evaluate rates per instance; do not average per class.*

## F6 — Bookkeeping: sparse enrolment + finite-radius local repair is the universal production pattern; the dense table has no precedent; selection choice is second-order (High)

- Every production code surveyed does incremental local updates after a firing, never a full
  rescan: SPPARKS (recompute altered sites only, 3-0; explicit invalidation radius `h_energy`,
  3-0), kmcos (no rescan after init; local avail_sites updates; empirically O(1)/step to ~10⁵
  sites until RAM, 3-0/2-1), KMCLib (re-match only the interaction vicinity, O(1) in N, 3-0).
- The claim that KMCLib keeps a pyKMC-style dense n_procs × n_sites availability table was
  **refuted 0-3** — there is no production precedent for the dense-table design.
- Selection: SPPARKS ships O(N)/O(log N)/O(1) solvers (3-0); composition-rejection is exact and
  composes with propensity factorization **without rate quantization** (PSSA-CR, 3-0) — so
  continuous per-site regression rates need no rate-binned micro-groups. But the complexity
  guarantees are conditional (bounded dependency degree + bounded propensity sum, 3-0/2-1), and —
  the practically decisive confirmed result — **the propensity-update path, not selection search,
  usually dominates runtime** (3-0, twice). The scary "polynomial scaling in the dense-active
  regime" claim was **refuted 0-3**; do not carry it forward.
- Formal correctness construct: the Gibson-Bruck dependency graph (edge iff Affects ∩ DependsOn ≠ ∅,
  2-0). Its extension to *spatial pattern matching* with a proven sufficiency bound does not exist
  in the confirmed corpus: Zacros's l-edge invalidation neighborhood and the observation that its
  sufficiency is asserted-not-proven are both Leads.
- Parallel dense-active: the only confirmed quantification is Time-Warp rollback overhead —
  ~14.7 re-simulated KMC time units per unit of global-virtual-time advance, range 5.8–69.2 (3-0).
  Shim-Amar / Martínez / first-passage accuracy costs: no claims at all.

**Design implication:** replace the dense table with per-site sparse enrolment plus a
dependency-graph-derived local repair keyed to an explicit interaction radius (the `h_energy`
pattern). Grouped-BKL-with-Fenwick vs composition-rejection is a second-order choice; both are
defensible, and effort is better spent on the update path. The dirty-ball sufficiency proof the
design asserts would *exceed* published field practice (mature codes assert it); formalizing it as
a specialization of the dependency graph ("every process whose DependsOn set intersects the
Affects ball lies within radius r") is novel but well-posed — and worth doing for a generated-C
matcher whose pattern radii are known at codegen time.

## F7 — Stop criteria: switch to rate-weighted completeness — but the rigorous version does not transfer unmodified to ART-style discovery (High for the criterion; the transfer caveat is load-bearing)

Confirmed core:

- Xu-Henkelman: C = 1 − 1/N_r (95% ⇒ 20 consecutive searches finding only redundant saddles), with
  full derivation, and the non-uniform extension C = 1 − 1/(αN_r) where α is the relative
  find-probability of the hardest saddle (all 3-0).
- Count-based completeness converges empirically like α ≈ 0.25 (4× slower than ideal) because
  low-barrier saddles are found preferentially (3-0), and the field's own assessment is that
  count-based confidence is qualitatively "unquantifiable" (Henkelman-Jónsson lineage, 3-0).
- Rate-weighted estimators ("fraction of total rate found") are the fundamentally correct object
  (Aristoff-Chill-Simpson, 3-0); their MSEs provably vanish (3-0 + 2-0); the Eyring-Kramers-based
  variant R̃ can *over*-report completeness when the assumed rate law deviates, while the
  Monte-Carlo variant R̂ is conservative (3-0).
- k-ART, by contrast, has no statistical stopping rule at all — a log-frequency search heuristic
  (20–50 searches per decade of topology recurrence, 2-0/3-0). EON exposes confidence as a tunable
  (default 0.99, 3-0), but the refuted claim (0-3) establishes that its thermal 20-kT window does
  **not** make that confidence rate-weighted — EON's stock criterion remains count-based.

**The transfer caveat.** The rate-weighted estimator is well-defined *because* MD/thermal saddle
sampling discovers events with probability proportional to their rate (3-0). ART-family
minimum-mode searches (pARTn) do not sample proportionally to rate — that is exactly why the
count-based α is ~0.25 for dimer searches. So for a pARTn-fed catalogue, the rigorous rate-weighted
machinery does not apply as-is; the honest rigorous statement available is the α-corrected
count bound with α unknown. Supporting Leads (flag, don't lean): the MDSS-AKMC X(F) < 0.01
stopping rule, and the caution that the estimator is *biased over-optimistic early* because fast
processes are found first.

**Verdict on the current design:** "new-classes-per-cycle = 0 AND fallback-flux-fraction = 0" is
(i) a count-based criterion — the form the confirmed literature explicitly grades as the weak,
unquantifiable one — and (ii) evaluated over states visited by the catalogue's own possibly-biased
trajectory, a self-referential loop no confirmed claim addresses. Minimum defensible upgrade:
replace the class-count leg with a rate-fraction estimator (conservative R̂-style, not R̃-style),
report it with an explicit α caveat for pARTn discovery, and treat fallback-flux-fraction as a
complementary *rate-weighted* signal (it is one — it measures flux, not counts — which is a point
in the current design's favor worth keeping).

## F8 — Explicit evidence-gap register (questions the research did not close)

Confirmed-evidence silence — these remain design decisions without literature cover either way:

1. **Concerted/multi-atom barrier predictability from local descriptors** (pass 1e): nothing.
   Keep the off-lattice channel.
2. **Rate-error-budget-derived projection/matching tolerance** (pass 2d): nothing. No one sets
   tolerances from an eV budget.
3. **Fraction of off-lattice events non-representable on-lattice** (pass 2e): nothing.
4. **MSM validation probes (Chapman-Kolmogorov, implied timescales, Bayesian error bars) and the
   trajectory length needed for power in trapped regimes** (pass 4c): nothing confirmed.
5. **Unseen-species / missing-mass statistics (Good-Turing, Chao1) applied to event catalogues**
   (pass 4d): nothing.
6. **Principled evolve-leg length** (pass 4e): nothing.
7. **Layer-dependent catalogue symmetry for FCC(100) Ni-Cr** (pass 5c): Leads only — the OSTI
   Ni-Cr claims (layer-resolved paths; Cr-exchange systematically easier near the surface; in-plane
   hop cost depending on sub-layer Cr) and Cu(100) surface-vacancy barriers (0.42–0.47 eV vs ~0.7
   bulk) all errored out. Plausible and design-relevant; unverified.
8. **Porous/bicontinuous site classification** (pass 5d): even the Erlebacher
   coordination-dependent-rules claim is a Lead; no flood-fill or threshold parameters surfaced.
9. **Mass-conservative interstitial/dumbbell mapping onto a rigid lattice** (pass 5e): nothing.

## Headline (my merge)

The confirmed corpus converges from three independent directions on one architectural verdict:
**keep discrete classes only as identity/provenance keys — computed by true canonical graph
labeling — and stop using them as rate bins.** Rates should come from a continuous per-instance
surrogate over both endpoint environments (0.04–0.13 eV RMSE demonstrated, inside split_tol, on the
right alloy family), which simultaneously retires the split_tol lumping tolerance, the bond-count
fallback (confirmed worse than the tolerance it backstops), the trimmed-mean tail-suppression risk,
and the unprincipled 0.9 Å snap-reject (the on-lattice substitute for the field's
per-instance re-convergence). Bookkeeping should move to sparse enrolment + dependency-graph local
repair with an explicit radius; selection algorithm choice is second-order. The stop criterion
should become rate-weighted — with the honest caveat that pARTn discovery breaks the
rate-proportional-sampling assumption underlying the rigorous guarantees, so the estimator must be
the conservative variant and reported with an α caveat. Detailed balance by construction, OOD
detection, concerted events, porous site classification, and leg length all remain **open**: the
first two have Lead-grade recipes worth verifying next; the last three have essentially nothing.

---

# Part 2 — Diff against the judge report

Compared: Part 1 above (written blind, claims-JSON only) against
`DEEP_RESEARCH_FINDINGS_2026-07-18.md`. Items are ranked: disagreements first,
then omissions, then places the parent is better than my blind merge, then nits.

## Agreement (the short version)

The two syntheses agree on every headline move: (1) continuous per-environment surrogate replaces
discrete catalogue + split_tol + bond-count fallback; (2) canonical graph labeling (nauty-style)
replaces the anchored-D4h identity, with the max-displacement anchor, direction-of-motion augment,
and automorphism group as byproduct; (3) sparse enrolment + local repair replaces the dense table,
selection is not the bottleneck, the dirty-ball radius is the real correctness surface; (4)
rate-weighted completeness replaces new-classes→0, with an independent probe. Both flag the same
refuted claims, both note the 0.5/1.0 eV/Å cross-run detail, both list rate-error-budget tolerance
and concerted events as genuinely open. **No headline verdict changes.** The memory entry
(`pylatkmc-research-gap-audit`) can stand; two optional refinements are flagged at the end.

## Disagreements and over-statements

### D1. The verdict table launders [UNVERIFIED] leads into High-confidence "settled" cells

The per-pass sections tag evidence honestly; the bottom-line table — the part most likely to be
read alone — does not always inherit the tags:

- **Row "1e / percolation", High:** "transport percolates the low-barrier tail (confirmed in
  Ni-Fe-Cr and Ta-W)" — wrong attribution. The confirmed FCC bimodality/percolation quote is about
  **Cu-based alloys** ("the presence of two distinct peaks in Cu-based alloys indicates that
  percolation effect could be expected"); the Frontiers paper covers the NiFeCr family, but the
  percolation statement specifically does not. Ta-W is BCC. And the decision cell "Trimmed-mean
  class aggregation **does** suppress the dominant Cr channel — the audit's fear is confirmed"
  states as confirmed what the corpus supports only directionally: no confirmed claim mentions Cr
  channels or aggregation; the direct mechanism evidence (Pt3Ni low-spread models accelerating
  dissolution-driving rare events) is a Lead. Right design call, one grade too confident.
- **Row "4 Bookkeeping", High:** "the dirty-ball invalidation bound … **even Zacros only asserts,
  never proves**" — both Zacros claims (l-edge neighborhood; sufficiency-asserted-not-proven) are
  [UNVERIFIED], correctly tagged in the pass section, then presented as settled in the table.
- **Row "5 Stop criteria", High:** "it is **biased low (over-optimistic) when fast events are found
  first**" — that is the [UNVERIFIED] MDSS-AKMC claim. A *confirmed* claim carries most of the same
  weight (R̃, the Eyring-Kramers-based estimator, can over-report completeness when the rate law
  deviates, 3-0) — the caution should be grounded there, with the fast-first bias as a supporting
  lead. Same issue in cross-cutting #4, where "mandatory, not a nicety" rests on the unverified
  version.

### D2. Gap 2 is framed as "the field's answer"; the honest answer is "the field avoids the problem" (my strongest emphasis disagreement)

The parent's verdict — topology identity, reconstruction-failure detection, always-re-converge —
is a faithful summary of the confirmed k-ART claims. But research questions 2c (published schemes
for *projecting* strongly-relaxed environments onto a lattice) and 2e (fraction non-representable;
how hybrid codes route them) returned **zero confirmed claims**. k-ART never projects onto an
ideal lattice; it stays off-lattice. So the k-ART pattern is an *analogy*, not prior art for the
harvest→replay projection step: **nobody has published what pylatkmc's projection step does, and
the report should say so.** Two downstream corrections:

- The decision cell "Route non-representable events back to off-lattice search" is a sensible
  design inference, not something the literature settles (2e was empty).
- "Rate = always re-converged" is not implementable in the on-lattice replay engine — there is no
  force engine at reuse time in the generated C runtime. The parent's cross-cutting #1 and #2 sit
  adjacent but never connect: the on-lattice substitute for per-instance re-convergence **is** the
  continuous surrogate of #1, evaluated per instance. Passes 1 and 2 converge on "per-instance
  rates, never class averages" from independent directions; the report leaves that link implicit.

### D3. Stop-criterion recommendation omits the discovery-sampling condition

The rigorous rate-weighted machinery (Chill-Henkelman estimator; Aristoff-Chill-Simpson MSE proof)
is built on MD saddle sampling, where discovery probability ∝ rate — that proportionality is
itself a confirmed claim in the corpus ("one can calculate a well-defined estimator … the
probability of finding any event using MD is proportional to its rate"), and it is what makes the
unfound-rate-fraction estimable. pARTn is an ART-family minimum-mode search, which does **not**
sample proportionally to rate. The parent recommends the estimator for pyKMC's loop without
addressing which discovery engine feeds it. Nuance that softens (but does not remove) the caveat:
the confirmed Al/Al(100) result shows rate-weighted coverage converging at the ideal α=1 **under
dimer (min-mode) searches** in that system — so empirically the metric can still behave well under
pARTn-like discovery; what is lost is the *a-priori guarantee*, leaving the α-corrected count bound
(α unknown) as the only rigorous statement. Recommended fix: state the condition, cite the α=1
empirical result as the reason to proceed anyway, and (optionally) note that adding short
high-T MD sampling to the discovery leg would restore the rigorous estimator.

### D4. "Adopt CR selection" is presented as what the literature says; the corpus is more equivocal

The confirmed Springer 2018 claim says SSA-CR wins only when *search* is expensive, and when the
*update* path dominates — "often the case in practice" — **RSSA should be the choice**. The
report's own binding-constraint finding (update path dominates) therefore points away from
plain SSA-CR by its own cited source. The defensible statement: selection is second-order
(grouped-BKL/Fenwick, CR, or two-level BKL à la kmcos all have production precedent); pick on
implementation simplicity; spend the effort on the update path. Choosing CR is fine; calling it
the literature's verdict is not.

### D5. ν0_f ≠ ν0_b is not in evidence

Gap-6 row: "forward/backward barriers depend on different atom sets …, so **ν0_f ≠ ν0_b in
general**." The confirmed Sci. Adv. claim is about *barriers* (E_b), not prefactors; no claim in
the corpus addresses prefactors, vibrational partition functions, or the ν0_f/ν0_b = Z_vib ratio
constraint from the original research question. The conclusion is physically reasonable (harmonic
TST), but it is imported physics, not a research finding — it should not sit in the "what the
literature settles" column.

### D6. "Every mature engine (k-ART, EON, SEAKMC) makes identity topological" (cross-cutting #2) misdescribes even the leads

Only k-ART is confirmed. The EON/KDB leads describe **geometric** (fuzzy match-score) matching,
not topological; the SEAKMC lead describes **no matching at all** (flush the catalogue, re-search
the active volume every event). The correct generalization from the corpus: mature engines
*separate identity/recognition from rate accuracy* — by three different mechanisms, only one of
them topological, and two of the three unverified.

### D7. The symmetry-number weighting rule is presented as decided; the precise rule did not survive verification

"Carry the automorphism order as the symmetry-number rate weight" — the confirmed claims establish
that the automorphism group is *available* from the canonizer; the *precise weighting rule* is not
settled: the Zacros GM_γ claim is unverified **and** applies to the cluster-expansion Hamiltonian,
not process rates; the rate-side lead says Zacros avoids over-counting by returning a single
mapping per instance (also unverified). The multiplicity correction must be derived and validated
in-house (e.g. against brute-force enumeration on symmetric test events) — a small but real work
item the table's phrasing hides.

### D8. Gap-8: coordination-dependent *rates* ≠ coordination-based *site classification*

The unverified Erlebacher claim says diffusion and dissolution rates are governed by local
coordination number. It does not describe how sites are *classified* (surface/bulk/pore-vacuum) on
a bicontinuous morphology, and nothing about connected-vacuum flood fill or standard parameter
choices surfaced in any claim. "Replace z(x,y) with coordination-based classification" is the
right direction, but the report's "dealloying KMC classifies sites by coordination number" reads
more answered than it is — the classification scheme and its parameters are still to be designed,
not looked up.

### D9. Detailed-balance recipe: the hedge disappears between the table and the conclusion

The gap-6 row is honestly tagged Med, but cross-cutting #1 says the KRA endpoint-split "gives
detailed balance by construction … retires gaps 1, 3, and 6 together." The recipe
(ΔE^b = ΔE^KRA + ½ΔE with k = Z̄*/Z_A from one energy model) is a Lead whose three voters all
errored — verify that one source (Comput. Phys. Commun., S0010465525002541) before the Phase C
detailed-balance layer commits to it. One added clarity note the report should carry: the
confirmed "KRA is insufficient for Ta-W" result condemns KRA-as-*barrier-model* (constant or
driving-force-only symmetric term); it does not condemn KRA-as-*detailed-balance-decomposition*
with an environment-dependent symmetric term. Readers will otherwise see the report recommending
what it elsewhere calls provably insufficient.

## Omissions (silently dropped research questions)

The report's "what remains genuinely open" list has four entries; the corpus actually left **nine**
questions without confirmed evidence. Missing from the open list:

1. **4c — MSM validation probes** (Chapman-Kolmogorov, implied timescales, Bayesian error bars,
   power/trajectory-length requirements): zero claims. This matters because the report's own
   remedy for the stop-criterion bias is "the independent probe is mandatory" — while the research
   into how to *build and power* such a probe came back empty. The probe is mandated and
   unsupported in the same report.
2. **4e — evolve-leg length**: zero claims. The design under review keeps a fixed step count per
   leg; the report never mentions that this question found no literature basis either way.
3. **4d — Good-Turing/Chao1 unseen-species statistics**: zero claims; not mentioned.
4. **2e — fraction of non-representable events / routing**: zero claims (see D2).
5. **5e — mass-conservative interstitial/dumbbell mapping**: zero claims; not mentioned.

Also worth one line each: **5d** porous-classification parameters are Leads only (see D8), and the
corpus's only scaling benchmark for sparse-local-update codes is kmcos at ~10⁵ sites (2-1) — i.e.
no confirmed precedent at the 10⁶-site target; the report omits the benchmark entirely.

## Where the parent is better than my blind merge

- **"Topology-as-identity resolves the O_h-vs-D4h question automatically"** (gap-8 decision): a
  genuine insight my synthesis missed — a local-environment-keyed identity inherits broken surface
  symmetry with no global group choice. It follows from confirmed canonical-labeling machinery
  even though the layer-dependence evidence itself is Leads.
- **Sequencing** ("do it before building Phase C") and carrying the audit's **SRO-sensitivity
  numerical check** forward — useful context the claims JSON alone doesn't contain.
- My synthesis under-used the confirmed α=1-under-dimer empirical result when stating the F7
  transfer caveat (I presented the caveat harder than the evidence requires; corrected in D3 —
  self-correction, noted for honesty).

## Nits

- "RMSE < 0.1 eV (**often** < 0.04 eV)": the <0.04 figure is a single study (Al-Mg-Zn); "often"
  overstates. Similarly "R² ≥ 90%" tightens the claim's "near/above 90%".
- "CR … is exact and **O(log(rmax/rmin))**": the complexity figure comes from the research
  question, not from any confirmed claim (the confirmed claims say "constant-time" and
  "O(log log N) average-case" for a different CR variant).
- "dependency-graph proofs cover only static chemical dependencies" — the Gibson-Bruck
  Theorem-1-proof claim is itself a Lead (1 valid vote); textbook-true, but by the corpus's own
  rules it should carry the tag.

## Bottom line

The two merges agree on all five gap verdicts and all four cross-cutting decisions; nothing in the
parent's report is *wrong at the decision level*. The systematic defect is **confidence
management at the summary layer**: the verdict table and cross-cutting section repeatedly present
unverified leads, imported physics, or design inferences with the same authority as 3-0-confirmed
findings (D1, D5, D7, D9), and five researched-and-empty questions vanish rather than being
reported as empty. Two substantive additions from the cross-check: the gap-2 reframing (no prior
art exists for lattice projection — the step is novel, and the surrogate is the on-lattice
substitute for re-convergence, D2) and the stop-criterion sampling condition (D3).

**Memory flag** (per handoff: flag, don't edit): `pylatkmc-research-gap-audit`'s headline verdict
stands unchanged. If the parent updates it, the two refinements worth one line each are: (i)
lattice projection has no published prior art — Phase C's projection step is novel, not adapted;
(ii) the rate-weighted stop criterion needs an explicit caveat that pARTn discovery voids its
a-priori guarantee (empirical α=1-under-dimer is the fallback justification).
