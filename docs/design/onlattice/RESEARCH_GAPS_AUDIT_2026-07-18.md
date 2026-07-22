# Deep-research gap audit — pylatkmc current push (Phase C/D)

Generated 2026-07-18 by a 14-agent audit workflow (5 doc readers → gap synthesis → 8 web-searched
literature scouts, all Opus). Sources read: onlattice_design/{COMPARISON,FINAL_DESIGN,SPEC,
phaseA_contract}.md, redteam/ + judging/ + designs/, pylatkmc/docs/ + CLAUDE.md,
HANDOFF_phaseB_translator.md, runtime/src/core/{kmc,avail_sites,active_filter,lattice}.c.

**Citation caveat:** references below were located by web-searching scout agents and are
plausible but not hand-verified — check each before citing in a paper or committing a design to it.

**Verdict: 8 research gaps, all rated worth a deep-research pass. The two critical ones sit
exactly on Phase C's deliverables. A cross-cutting meta-finding: on 5 of 8 gaps the mature
adaptive-KMC lineage (k-ART, SLKMC, SEAKMC, EON, KRA/cluster-expansion, Zacros) solved the
problem by NOT doing what pylatkmc currently does — rigid-lattice snapping, discrete exact-class
catalogues with energy tolerances, hand-rolled anchored canonicalization — so the research payoff
is decision-changing, not citation-gathering.**

---

## CRITICAL — gate Phase C directly

### 1. Fallback-rate model: no evidence NiCr barriers obey the assumed BEP/bond-count/GCN law — and Phase B made it the MAJORITY channel

The φ regressor (degree-≤2 one-hot polynomial → ridge/GP) is justified by analogy to BEP and
Erlebacher bond-counting, with zero fit-quality measurement on the harvested pARTn barriers, and
it is unbuilt (phaseA_contract marks phi/fallback_stats empty). Only 275/439 production classes
translate, so fallback carries most of the flux — and it is least trustworthy exactly on the
strongly-relaxed events (median snap residual 1.44 Å) that fail projection.

Literature: **rich**, and it cuts both ways.
- One-hot occupation surrogate for FCC vacancy barriers (arXiv:2206.02879, Al-Mg-Zn): RMSE <0.04 eV
  achievable; 2-body features are the floor, 3-body materially better — but demonstrated on
  dilute, near-rigid-lattice NEB events, i.e. exactly the regime that does NOT fail projection.
- KRA + local cluster expansion (Van der Ven/Ceder/Thomas/Puchala; kMCpy): the principled,
  convergence-tested generalization of BEP the project is implicitly assuming.
- Tensorial transition-state CE beyond KRA (arXiv:2605.23612, Ta-W, 2026): endpoint-style
  descriptors are demonstrably insufficient for saddles — a φ on initial-environment features is
  expected to mis-rank the strongly-relaxed events that dominate the fallback channel.
- BEP/GCN provenance check: validated for surface adsorption/bond-breaking at ~0.1–0.15 eV floor,
  NOT bulk alloy vacancy migration — the borrowed reputation is from a different regime.
- ML-KMC in MPEAs (arXiv:2203.06503, 2409.14573; Sci. Adv. adr4697): field's own warning —
  local-descriptor extrapolation is poor and saddle geometry is ill-defined under distortion.
- Honestly thin sub-question: whether concerted/multi-atom saddles are predictable from
  atom-centered local descriptors AT ALL — no published reassurance exists (W3/W4 risk is open).

**Deep-research focus:** for strongly-relaxed, potentially concerted saddles in concentrated
NiCr/NiFe, what descriptor order and model class (one-hot/KRA vs converged TS-CE vs SOAP-GP with
variance control) reaches ~0.05 eV RMSE AND reliably flags out-of-distribution Cr-enriched
environments — or does the majority-fallback regime force a TS-aware/on-the-fly channel instead
of a static parametric φ?

### 2. Lattice-projection tolerance set from geometry, not from the empirical residual distribution — the direct cause of the Phase B step-2 trap

snap_tol (0.6–0.9 Å) and gate G3 derive from FCC geometric fractions; production data falsifies
them (median residual 1.44 Å → 316/439 G3 fails → trapped at step 2). Raising the tolerance
poisons class rate-means by collapsing distinct environments.

Literature: **moderate**, and it challenges the rigid-snap premise.
- k-ART (El-Mellouhi/Mousseau/Lewis PRB 78 153202; Béland et al. PRE 84 046704): classifies by
  graph topology, not snap distance, and explicitly detects the "one class ↔ many geometries"
  degeneracy, re-relaxing those events separately — the exact class-poisoning failure, with a
  working fix.
- Off-lattice SLKMC (Nandipati et al. JPCM 21 084213): on-lattice pattern recognition broke on
  relaxed environments; the group built an off-lattice variant — same failure, same escape hatch.
- EON/AKMC (Chill et al. MSMSE 22 055002; Xu & Henkelman JCP 129 114104): loose KDB match only
  SEEDS a re-converged saddle search — recognition tolerance decoupled from rate accuracy.
- SEAKMC active volumes (Xu/Osetsky/Stoller JPCM 24 375402): the per-defect local frame all four
  blinded designs name but never implement.
- Genuinely open (sparse): setting a projection tolerance from a rate-error budget — the
  machinery exists (Katsoulakis/Plechac/Vlachos CG-KMC error analysis; descriptor-distance-to-
  error ML work) but nobody has closed that loop. This part the project must build, not cite.

**Deep-research focus:** k-ART's degeneracy detect-and-split mechanism and the residual
magnitudes k-ART/SLKMC/SEAKMC/EON actually tolerate before refusing catalogue reuse; can
split-plus-reconverge replace a geometry-derived snap tolerance with one calibrated to allowable
rate distortion?

---

## HIGH — Phase C rate fidelity and scalability, Phase D termination

### 3. Within-class lumping tolerance suppresses the low-barrier Cr channel that IS the dealloying pathway

split_tol=0.15 eV tolerates a 331× rate spread at 300 K; trimmed_mean discards the lowest-barrier
members — the Cr-mediated moves. rcut was chosen for saddle-search locality, not as a
barrier-determining identity horizon.

Literature: **rich** — and it says the field moved past discrete class catalogues.
- KRA + TS cluster expansion (Van der Ven/Ceder lineage): barrier = continuous local function per
  environment; no within-class averaging, so split_tol becomes a non-question.
- Osetsky/Béland/Stoller/Zhang (Acta Mater. 115, 2016): transport in concentrated FCC alloys is
  percolation of the LOW-barrier tail — averaging that erodes the fast subset mis-rates the
  dominant channel, in the alloy-transport field's own terms.
- Jensen/rate-averaging: rate-space arithmetic mean is correct (already adopted — grounded); the
  open bit is the split criterion: k_BT·ln(1+δ) from a rate-error budget, not 0.15 eV. No paper
  prescribes a numeric tolerance recipe — the field sidesteps discretization entirely.

**Focus:** minimal barrier-determining context in concentrated NiCr/NiFe and whether a continuous
surrogate (KRA-CE or the regression fallback) eliminates split_tol rather than re-tuning it.

### 4. Group-BKL memory, per-step O(N) rescan, incremental-repair correctness — asserted, not benchmarked

avail_sites is ~340 MB/replica now, ~35 GB at the 1e6-site target; full per-step rescan today;
dirty-ball sufficiency asserted; its I5 oracle re-runs the same matcher so can't catch a
systematic radius error; rarest-anchor degrades to O(N) in equiatomic/porous regimes.

Literature: **rich** — mostly solved problems.
- Composition-rejection (Slepoy/Thompson/Plimpton JCP 128 205101, inside SPPARKS): bins by rate
  MAGNITUDE → O(log(rmax/rmin)) groups regardless of continuous fallback rates, exact sampling —
  defuses the micro-group-proliferation worry outright; rate-quantized buckets unnecessary.
- Gibson–Bruck dependency graph (JPCA 104 1876): the formal, provably-sufficient invalidation
  set the dirty-ball is re-deriving; prove rctx_ball ⊇ dependency graph instead of oracle-testing.
- KMCLib (CPC 185 2340) + Zacros subtraction/supersites (arXiv:1908.03526): sparse per-site
  enrolment + finite-radius local update → O(1)-in-N total-rate refresh; memory sparse, not dense.
- Parallel caution: synchronous sublattice (Shim & Amar PRB 71 125432), billion-atom sync KMC
  (Martínez/Marian/Kalos JCP 230 1359), FPKMC (Opplestrup/Bulatov PRL 97 230602) — FPKMC exploits
  SPARSITY and degrades in exactly the dense porous/equiatomic regime the design defers to it.
- Genuinely thin: a provable geometric invalidation bound for a spatial fingerprint/IRA-style
  matcher, verified independently of the matcher. That's where the correctness risk concentrates.

**Focus:** can bespoke group-BKL + dirty-ball be retired for composition-rejection + a
dependency-graph invalidation set, and what is the smallest provably-sufficient geometric
neighbourhood for the fingerprint matcher?

### 5. Loop convergence / catalogue-completeness criteria are self-referential and statistically unspecified

new-classes→0 AND fallback-flux→0, computed from the catalogue's own rates over a biased
trajectory; fixed n≈1e6 tied to no mixing time; the KL/χ² probe has no specified length/power.

Literature: **rich**, directly importable.
- Xu & Henkelman (JCP 129 114104): canonical per-state confidence limit (Nr consecutive empty
  searches → e.g. 95%) — what new-classes→0 is groping toward, with an actual confidence model.
- Aristoff/Chill/Simpson (CAMCoS 11 171, arXiv:1506.05092): rigorous estimator analysis; argues
  for rate-weighted "fraction of total rate found" over count-based criteria.
- MSM validation toolkit (Prinz et al. JCP 134 174105): Chapman–Kolmogorov self-consistency test
  + implied-timescale convergence = principled, catalogue-independent probe and leg-length basis.
- Unseen-species statistics (Good–Turing; Chao1; Orlitsky PNAS 113 13283): missing-mass estimates
  with confidence intervals for "how much undiscovered event mass remains." Importing these into
  KMC catalogues is non-standard — integration opportunity.

**Focus:** replace count-based stop criteria with a rate-weighted completeness estimator + CK-style
test vs a short direct-pyKMC reference; required trajectory length/event counts/tolerance for
statistical power in slow/trapped regimes.

---

## MEDIUM — production science; decide before the identity/thermo layers ossify

### 6. Detailed balance: G2 is tautological (dEnergy ≡ Ea_f−Ea_b → residual ≡ 0); class-mean ΔE biases equilibrium composition/SRO

Literature: **rich** — a solved problem with a canonical fix.
- KRA decomposition (Van der Ven/Ceder/Asta/Tepesch PRB 64 184307): barrier = symmetric kinetic
  part (safe to average/expand) + antisymmetric endpoint part from ONE energy model → detailed
  balance enforced per-pair by construction. CASM (arXiv:2309.11761) is the reference
  implementation; Ni-X non-dilute KMC (arXiv:1812.04989) is a direct system template.
- HTST constraint: ν0_f/ν0_b = Z_vib,i/Z_vib,f ≠ 1 (Vineyard; JCP 150 144105) — "DB by
  construction" with per-family ν0 silently violates this.
- Real diagnostic to replace G2: closed-loop affinity test (Andersen/Panosetti/Reuter,
  Front. Chem. 7:202).
- Sparse: published sensitivity of SRO/composition to systematic aggregated-barrier imbalance —
  needs the project's own numerical check.

### 7. Symmetry canonicalization not collision-free for symmetric/concerted events; O_h-vs-D4h undecided

Literature: **rich**.
- nauty/Traces canonical labeling (McKay & Piperno JSC 60): invariance over full automorphism
  group AND anchor choice — the landed lex-anchored point-group scheme is a known-incomplete
  hand reinvention; k-ART already runs a nauty-based chemistry-aware event key in production.
- Zacros graph-theoretic KMC (Stamatakis & Vlachos JCP 134 214115): explicit symmetry-number
  (1/|Aut|) weight fixes multi-anchor k× over-counting of R_total.
- O_h vs D4h: surface studies (arXiv:1707.05765; NiCr-specific Goswami et al., Scripta Mater.
  2021) show the in-plane vs inter-layer ⟨110⟩ split is real near surfaces and vanishes in the
  interior — the correct symmetry is LAYER-DEPENDENT; no global point-group arbiter exists.
  Topology-as-identity resolves this too.

### 8. Porous/roughened late-dealloying regime breaks single-valued-surface, fixed-frame, and rcut-cluster premises

Literature: **rich** — the dealloying canon already does it right.
- Erlebacher et al. Nature 410 450 (2001) + JES 151 C614 (2004): full-3D rigid lattice-gas,
  coordination + connected-vacuum classification, NO z(x,y) height envelope — reproduces
  bicontinuous porosity; the depth_sig/column-max-k design contradicts the field's base model.
- k-ART frame-free graph identity degrades gracefully in symmetry-broken ligaments.
- Interstitials/dumbbells: k-ART/SEAKMC keep them off-lattice or as oriented multi-site objects —
  never a silent atom deletion.
- Caveat: literature says WHAT, not how to retrofit into the generated-C tetragonal grid at
  acceptable catalogue/rescan cost — that last mile is engineering.

---

## Already well grounded — do NOT re-research

BKL/n-fold-way + Fenwick selection; Arrhenius ps⁻¹ rate law (validated vs pykmc to machine
precision); Vineyard HTST ν₀ recovery (cluster-vs-slab cross-check 9–16%); kmos code-port
provenance of the compiled proclist; Kabsch/Procrustes+RANSAC frame fitting; point-group/orbit
machinery as method; Warren–Cowley SRO + correlated tracer D=f·a²·Γ as observables; rate-space
(Jensen-correct) aggregation direction; SLKMC/k-ART correctly identified as the paradigm
prior-art; Erlebacher bond-counting for the DISSOLUTION law (v1-excluded).

## Suggested sequencing

1. Gaps 1+3+6 collapse into one deep-research pass: "continuous local barrier surrogate
   (KRA/TS-CE) vs discrete class catalogue for concentrated NiCr/NiFe" — it decides φ's form,
   dissolves split_tol, and fixes detailed balance in one design move. Run BEFORE building Phase C.
2. Gap 2 (projection/degeneracy-split) — second pass; decides how much of the relaxed-event
   population is on-lattice-representable at all.
3. Gap 4 — mostly an adoption memo (composition-rejection + dependency graph); the one research
   item is the matcher invalidation bound.
4. Gap 5 — needed before Phase D lands; estimators are importable.
5. Gaps 7+8 — before the identity layer ossifies further / before production dealloying runs.

Full agent-level detail: session task output (ephemeral) and workflow journal
wf_3bcd607b-260 (14 agents, ~965k tokens, all completed).
