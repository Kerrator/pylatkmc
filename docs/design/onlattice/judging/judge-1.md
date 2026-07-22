# Judge 1 — scoring rationale

Panel: species-aware on-lattice KMC fed by autonomous off-lattice (pyKMC) event discovery.
Instrument: the SPEC rubric — Correctness/fidelity 30, Runtime-at-scale 20, Classification
robustness + novelty 20, Implementability/pipeline fit 15, Extensibility 15 (total 100).

I read the SPEC and all four designs, and I ground-truthed the fidelity claims against the pyKMC
input side (`event_table.py`, `environments/{graph_nauty,coordination,common_neighbor_analysis,
region}.py`, `symmetries.py`, `point_set_registration.py`, `neighbors_list.py`,
`config.py`/`eventsearch` thresholds). I judged strictly against the SPEC, not taste.

## Method notes and cross-cutting facts established from the source

- **`event_id` is classifier-mode-dependent and is *not* a re-derivable pure graph hash.** In
  `event_table.py` the forward `event_id` prefers the mover's **live** classifier id; that id is a
  pynauty certificate only in graph mode, but is merely `'crystal'/'noncrystal'` in coordination
  mode and a CNA label in CNA mode. **All four designs independently and correctly relegate
  `event_id` to provenance + a cheap pre-filter and re-derive an authoritative lattice identity.**
  That is the right architecture (a coordination-mode `event_id` is far too coarse to be a fine
  identity), so no design is penalized for it — but it is a shared strength worth recording.
- **pyKMC dedup logic** (verified): same `event_id` **and** `|ΔEa| < 0.25 eV` **and** an IRA
  saddle match ⇒ same event; `event_id == id_final` ⇒ self-reverse. All four cite the self-reverse
  rule; "pattern", "symmetry", "descriptor" cite the 0.25 eV tolerance explicitly.
- **Gate thresholds** `emin_event / emax_event / backward_emin_event / energy_asymmetry` exist as
  named config fields; the exact asymmetry rule is `(dE_f > energy_asymmetry·backward_emin) and
  (dE_b < backward_emin)`. "symmetry" reproduces this rule verbatim; the others reuse the names.
- **`unique_symmetries` returns orbit-generating representatives** (ops producing *distinct*
  displacement images; stabilizer ops are the ones filtered out). Therefore `len(sym_perm)` = orbit
  size = `|G|/|stabilizer|`. "pattern" reads this correctly (pattern-count == `sym_perm` length);
  **"symmetry" reads it backwards** (calls them "displacement-preserving … ⊆ my stabilizer").
- **Orthorhombic-cell assumption is real**: `neighbors_list.py` builds `cKDTree(..., boxsize=
  diag(cell))`. "descriptor" is the only design to cite this precisely — a credibility signal.
- Shared correctness (all four): FCC even-parity SC embedding; 12/6/24 shells at 2.489/3.520/4.311
  Å; FCC(100) surface coordination 8; true-mover detection by site-change (not `move_atom_idx`),
  each with a worked concerted example; deterministic ideal-site reverse map; file-based handoffs.

The **one substantive intellectual disagreement** is the bulk symmetry group and how the surface
reduction is obtained: explicit depth + group switch (Oh↔C4v: pattern, performance; D4h↔C4v:
symmetry) vs. a single decorated-Oh canonicalizer where vacuum `V` breaks the symmetry
automatically (descriptor). I verified descriptor's decorated-Oh *does* reproduce C4v at a (100)
surface and Oh in bulk (the vacuum-decoration-preserving subgroup of Oh for four top `V`s is exactly
C4v); it does **not** reproduce D4h, and it has no depth attribute, so a fully-coordinated
subsurface site whose stencil does not reach vacuum is merged with true bulk (reactively split only
by barrier variance). The depth-aware designs distinguish it a priori.

---

## Design "pattern" — precompiled-local-pattern engine

**Correctness & fidelity — 26/30.** Geometry, mover detection, projection, and reverse map are all
correct. The **core/descriptor split** (a minimal *executability* stencil for matching + a wider
*descriptor* shell for rate, promoted into identity only when measured barriers demand it) is a
genuine fidelity **asset**: classes cannot silently merge distinct-barrier physics beyond
`split_tol`. Its `event_id` reconciliation (finer where the surface breaks symmetry, coarser where
the bulk restores it) is accurate, and its `sym_perm`-length cross-check is the *correct* reading of
`unique_symmetries`. Honest limitations: the saddle is carried as provenance only (not tokenized),
so two events with identical endpoints but different saddle paths are merged and only split
reactively; detailed balance is checked, not enforced (W5, disclosed). Oh/C4v is a binary regime
with the subsurface-in-between gap disclosed as W4.

**Runtime at scale — 18/20.** O(1)/step in N via rarest-predicate anchoring (enumeration scales
with defects, not atoms), per-site process lists, group-BKL selection O(log C), and incremental
invalidation over a fixed pattern-support ball. The periodic self-heal checksum vs. full rebuild is
a good safety net. Slightly less data-structure/cache detail than "performance", and the fallback
micro-group binning adds moving parts, but the analysis is sound and complete.

**Classification robustness + novelty — 19/20.** The strongest classification story in the field.
The **data-driven SPLIT_CHECK** directly solves the SPEC's hardest problem — the context-radius
bias/variance tradeoff — by letting identity start minimal and grow only where harvested barriers
prove it must. Combined with the geometry-aware canonical form (finer than a graph hash at the
surface, coarser in the bulk) and the flux-ranked flag registry driving the exploration frontier,
this is the most robust and best-justified identity design. New-vs-known is exact canonical-form
equality; backward pairing and coverage metrics are complete.

**Implementability & pipeline fit — 13/15.** Full file-based loop, gates reuse pyKMC's exact
threshold names, audit = directory + replayable decision log (good determinism story). The cost is
the **largest implementation surface** of the four: a compile step producing oriented patterns,
dynamic SPLIT_CHECK re-keying (the "smallest descriptor-shell extension that separates" is
under-specified as an algorithm and could be ambiguous/expensive), and fallback rate-binning.

**Extensibility — 13/15.** `DeltaSite{before,after}` + `delta_atoms` cleanly admits site→EMPTY;
correctly assumes **no colour-swap symmetry** (Ni≠Cr≠Fe) for ternary; closed-loop is a driver over
existing files. Solid but less concrete about the dissolution rate law than "performance".

**Strongest transplantable ideas:** (1) core/descriptor split with data-driven SPLIT_CHECK; (2)
rarest-predicate anchoring; (3) the "finer at the surface / coarser in the bulk than a graph hash"
identity framing + `sym_perm`-count compile cross-check. **Fatal flaw:** none. Principal weakness:
highest implementation complexity; SPLIT_CHECK re-keying is the least-specified algorithm here.

**Total: 89/100.**

---

## Design "symmetry" — canonical-labeling-first engine

**Correctness & fidelity — 27/30 (top).** The most crystallographically rigorous design. The
canonical form is presented as a provable complete invariant (same key ⟺ same class, no hash luck;
256-bit digest only as an index). Two unique fidelity assets: (a) the **saddle mechanism token**
(quantize the saddle displacement so two events with identical endpoints but different paths —
over-bridge vs. through-hollow — get distinct keys), which no other design has and which addresses a
real barrier-splitting case a priori rather than reactively; (b) the **D4h (not Oh) bulk default**,
which is the safe, conservative choice for the thin-slab v1 target (a slab genuinely breaks Oh; the
in-plane vs. inter-layer ⟨110⟩ hop split is physically defensible). It also reproduces the
`energy_asymmetry` gate verbatim. **Two deductions:** the `sym_matrix/sym_perm` cross-check is
based on a **misreading** — those are orbit-generating reps, not "displacement-preserving …
stabilizer" ops, so that specific validation would misfire (auxiliary, not core, but a real blemish
on a design branded on rigor); and the D4h-as-"correct"/Oh-as-"physical-error" rhetoric overstates
the case for deep bulk (it is conservative, not strictly correct).

**Runtime at scale — 18/20.** O(1)/step via ActiveSites + a `LocalSig` prefilter (TrigIndex),
Fenwick RateTree, TouchIndex, and a bounded dirty region; grouped selection; honest about
`|ActiveSites|→O(N)` in the porous late-dealloying limit and the parallel-KMC extension. Comparable
to "pattern"; a notch below "performance" on data-structure specificity.

**Classification robustness + novelty — 18/20.** Very strong. The **`r_id ≥ rcut` invariant**
(never merge two events pyKMC distinguishes; my granularity is at least as fine as the harvest) is a
clean, correct guarantee, and the test plan's "my classes must *refine* pyKMC's `event_id`
groupings" is an excellent novelty-correctness check. Explicit depth signature (top-layer ≠
subsurface). Slightly behind "pattern" only because context-size is handled by a variance diagnostic
+ manual/audited `r_id` bump rather than pattern's automatic data-driven split, and the D4h default
imposes a guaranteed bulk over-split that *slows the loop's own convergence metric*.

**Implementability & pipeline fit — 13/15.** Deterministic `EMIT_ATOMISTIC` with content hash,
`config.control.reference_table` restart, precise threshold/util reuse. Implementation surface is
raised by the D4h/C4v machinery, the saddle tokenizer, and the local-Hungarian contested-site
assignment.

**Extensibility — 13/15.** `count_delta` is schema-ready and ternary is enum-driven, but the design
is honest (W10) that dissolution is **schema-ready, not loop-ready** — BKL competition, mass
balance, and Erlebacher integration are explicitly stubs. That candor is correct but it is a thinner
extensibility story than "performance".

**Strongest transplantable ideas:** (1) the saddle mechanism token; (2) the `r_id ≥ rcut` "at least
as fine as the harvest" invariant; (3) provable complete-invariant canonicalization + the
refines-`event_id` validation test. **Fatal flaw:** none. Principal weaknesses: the `sym_perm`
cross-check misreads pyKMC; the D4h default's guaranteed bulk over-split is in tension with the
loop's convergence goal.

**Total: 89/100.**

---

## Design "descriptor" — regression-first, one-descriptor-three-readouts engine

**Correctness & fidelity — 25/30.** The **always-Oh-on-decorated-stencil** mechanism is elegant and
(verified) correct for the surface reduction: with vacuum decorated as `V`, the
decoration-preserving subgroup of Oh at a (100) surface is exactly C4v, so surface-parallel and
surface-normal hops stay distinct and bulk hops merge — with no case analysis or per-site group
tables. The bond-count `φ` (Erlebacher broken-bond variables) is physically motivated. The precise
`neighbors_list.py` orthorhombic citation shows real source engagement. **Principal fidelity gap:**
there is **no explicit depth attribute**; identity is purely the decorated stencil, so a
fully-coordinated subsurface site whose `R_env` does not reach vacuum is silently merged with true
bulk (the SPEC explicitly asks to distinguish top-layer vs. subsurface). It is bounded — reactively
caught by `Ea_std` (W4) — and for a very thin v1 slab the practical impact is small, but the other
three handle it a priori. The mechanism tag (hop/swap/ring) is coarser than symmetry's saddle token,
and `φ` is a lossy readout (W1).

**Runtime at scale — 17/20.** O(1)/step with active-site set, trigger buckets, bounded dirty
region, and concrete op counts (~180 ops/step; ~2·10⁸ for 10⁶ steps). It defaults to a **flat
segment tree over all entries** (O(log E)) "for simplicity" rather than exploiting rate-is-a-class-
constant for grouped-BKL (O(log C)) as pattern/performance/symmetry do — a minor efficiency give-up
— and concedes the concentrated-alloy build is O(N·S). Fully adequate, just not the leader.

**Classification robustness + novelty — 17/20.** The **unified descriptor** — one stencil object is
the identity (canon), the invertible reverse-map coordinates, *and* the fallback feature vector, so
"near-miss = a short hop in descriptor space" — is the most coherent exact-lookup↔fallback
integration in the field and directly serves SPEC decision 4. **Per-mechanism-family regressors**
(the discrete key selects *which* regressor, continuous `φ` is its input) and **backward-pair
synthesis** (synthesize `κ_bwd` barrier-pending when only one direction is harvested, guaranteeing
pairing closure mid-harvest) are genuinely novel and well-judged. Held back only by the
subsurface-merge robustness gap and the lossy-`φ` limit on what the fallback can separate.

**Implementability & pipeline fit — 14/15 (top).** The leanest correct v1: one fixed 48-element
integer group, one fixed `φ` map, ridge/GP, a scipy KD-tree snap — "no nauty on the lattice side,
modest new deps." An explicit implementability section reuses the exact `event_table` columns and
pyKMC thresholds, writes the ASE-readable ideal config + cumulative `reference_table.pickle` into
the existing restart contract, and a mermaid diagram aids comprehension. Smallest surface area for a
correct build.

**Extensibility — 14/15.** `V` is an ordinary species, so `(Cr→V)` dissolution is representable with
zero schema change (flip the conservation assert + add a reservoir counter); ternary is enum-driven;
closed-loop is file-based. Clean, just less concrete on the dissolution rate law than "performance".

**Strongest transplantable ideas:** (1) the unified one-descriptor-three-readouts object; (2)
always-Oh-on-decorated-stencil (surface reduction falls out of `V`; provably correct, no group
tables); (3) per-mechanism-family regressors; (4) backward-pair synthesis for pairing closure.
**Fatal flaw:** none. Principal weakness: absence of an explicit depth attribute → silent
subsurface/bulk merge when `R_env` doesn't reach vacuum (the most consequential fidelity gap of the
four, though bounded and self-correcting).

**Total: 87/100.**

---

## Design "performance" — incremental / performance-first engine

**Correctness & fidelity — 26/30.** Fully correct and the most disciplined on invariants (I1 parity,
I2 NN symmetry, I3 species-list consistency, I4 conservation, I5 incremental==rebuild). **Detailed
balance is enforced by construction**: `Ea_fwd − Ea_bwd = ΔE` from the *same* saddle ⇒
`k_f/k_b = exp(−ΔE/kT)` holds structurally — the cleanest reversibility treatment in the field.
Depth-aware Oh/C4v, conservative C4v at the boundary. Best literature grounding (self-learning KMC
of Trushin/Kara/Rahman named as the closest published analogue — exactly right; plus k-ART, SPPARKS,
kmos, CE-KMC). Same one fidelity gap as "pattern": no saddle-path resolution, so same-endpoint
different-barrier events are merged and split only reactively.

**Runtime at scale — 20/20 (top).** Purpose-built and clearly the leader. Tiled/layer-blocked SoA
layout for cache locality; `species_sites` with O(1) swap-remove + back-pointer; the `nn12` table
with an explicit **scale-switch to arithmetic neighbours at ~10⁷ sites** (with the correct
cache-miss-vs-compute reasoning); worked memory budgets (1 MB at 10⁶, 100 MB at 10⁸); the I5
full-rebuild oracle. It is also the most honest about degradations (F13/W9 equiatomic direct-exchange
loses the dilute anchor → O(N/2) spatial-index fallback; porous late-dealloying → ActiveSites→O(N)).
This is the design that most credibly delivers the SPEC's stated raison d'être — execute the
harvested catalogue *fast* at 10⁶⁺ steps and scale to 10⁵–10⁶ sites on a node.

**Classification robustness + novelty — 16/20.** Solid and correct but the least distinctive: a
competent depth-aware Oh/C4v canonicalizer (pattern's approach minus the core/descriptor split), a
standard ridge→GBT fallback, hash-lookup novelty detection, and a flux×count-ranked exploration
list. The I5 oracle guarantees the fast matcher equals a brute-force rebuild — a real robustness
plus — but on the axis the SPEC calls "the heart," this design is a strong follower, not a leader.

**Implementability & pipeline fit — 13/15.** Clean schemas, a pure-function deterministic reverse
map, a JSONL audit queue, priority sites written first, and a driver-chains-files closed loop. The
tiled memory layout and dual neighbour modes add build effort but are standard engineering.

**Extensibility — 15/15 (top).** The best extensibility story. It names the actual dissolution rate
law and shows it competing directly in the grouped BKL vector (Erlebacher
`k = ν_d·exp((φ − n·E_b)/kT)` as a coordination-dependent rate class), and it articulates the key
enabling insight — **sites never re-index** (unlike pyKMC's per-atom deletion), so an EMPTY site is
just occupancy: dissolution needs no re-harvest and no schema break. Ternary is
species-count-agnostic by construction.

**Strongest transplantable ideas:** (1) the whole performance substrate — tiled SoA + O(1)
swap-remove species lists + arithmetic-neighbour scale-switch + I5 oracle invariant; (2)
detailed-balance-by-construction from a single per-pair ΔE; (3) Erlebacher-dissolution-as-a-BKL-class
with the "sites never re-index" insight. **Fatal flaw:** none. Principal weakness: the least
innovative treatment of class identity — precisely the component the SPEC calls "the heart."

**Total: 90/100.**

---

## Comparative summary and ranking

All four are correct, comprehensive, implementable designs that clearly understood the SPEC, read
the pyKMC input side, and cover all seven required components with worked vacancy-hop and concerted
examples, complexity analysis, failure tables, test plans, and self-declared weaknesses. **No design
has a fatal flaw.** The spread is genuinely narrow (90–87); the differences are real but modest.

- **performance (90)** — wins the two axes it targeted (Runtime 20, Extensibility 15) and ties the
  highest-weighted axis (Fidelity 26), trailing only on classification innovation. It most credibly
  serves the SPEC's stated primary mission (execute the catalogue *fast* at scale, correctly).
- **pattern (89)** — the strongest *identity* design (data-driven core/descriptor split — the best
  answer to the SPEC's hardest problem, context radius) with deep, accurate pyKMC fidelity and
  strong runtime. Loses to performance only on data-structure polish and dissolution concreteness.
- **symmetry (89)** — the most rigorous crystallography and the unique saddle token, tied top on
  fidelity. Docked below pattern on the tie-break because (a) its `sym_perm` cross-check misreads
  pyKMC where pattern reads it correctly, and (b) its D4h default imposes a guaranteed bulk
  over-split that works against the loop's own convergence-to-zero metric, whereas pattern's
  Oh-default + data-driven split is the better convergence-cost tradeoff.
- **descriptor (87)** — the most elegant/unified concept (one descriptor = identity + reverse-map +
  fallback features) and the best implementability, but the absence of an explicit depth attribute
  (silent subsurface/bulk merge) plus the lossy-`φ`/flat-tree give-ups place it a close fourth on
  the fidelity- and runtime-heavy rubric.

**Ranking: performance > pattern > symmetry > descriptor.**

The pattern/symmetry tie (both 89) is broken toward **pattern** for more accurate pyKMC-internals
fidelity and a better loop-convergence tradeoff. If one weighted "class identity is the heart" above
raw throughput, pattern would edge to #1 — it is within one point and arguably the better *identity*
design; performance takes #1 on a strict reading of the rubric because it dominates the 20+15 points
of Runtime+Extensibility while remaining fully correct.
