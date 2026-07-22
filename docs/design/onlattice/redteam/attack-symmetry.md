# Red-team: correctness of identity and counting

**Lens:** canonicalization completeness & hash collisions; orientation multiplicity double/under-counting
in the rate list; mirror/chirality; reduced surface-vs-bulk symmetry; forward/backward pairing &
microscopic reversibility; concerted multi-site event identity.

**Target:** `FINAL_DESIGN_DRAFT.md` (the `synthesis` design). **Input side read for grounding:**
`pyKMC/pykmc/event_table.py`, `symmetries.py`, `environments/{graph_nauty,coordination,common_neighbor_analysis,region}.py`,
`neighbors_list.py`, `point_set_registration.py`.

The design leans hard on a single "provably complete / collision-free" identity key and on an
orbit–stabiliser argument for orientation counting. Both claims are load-bearing for physical fidelity,
and both have concrete holes. Three of the failures below are silent (wrong `R_total`, wrong branching,
wrong equilibrium with no gate firing); the rest break a loop leg or need manual rescue.

---

## What I checked and found SOUND (calibration)

To keep the findings honest, these attacks did **not** land:

- **Hash collisions are adequately defended.** `class_id` is a BLAKE2b-256 digest but §4.3 keeps the
  full `canonical_form` tuple as authoritative. At ~10²–10³ classes a 256-bit collision is ~10⁻⁷⁰. The
  *one* residual inconsistency (the ingest membership test §7.1 does `if C in catalogue` on the **hash**,
  not the tuple) is real but practically irrelevant. Not raised as a finding. (The identity danger is
  incompleteness of the canonical form itself — Finding 2 — not digest collisions.)
- **§4.7's `sym_perm` re-reading is correct against source.** `symmetries.unique_symmetries` runs SOFI
  species-blind (`typ = nat*[1]`) on `initial_positions`, forms `d = initial − final`, and keeps one
  representative per **distinct** displacement image (prepending identity). So `len(sym_perm)` is the
  **orbit** size of the displacement under the *grey, relaxed-cluster* point group — exactly as §4.7
  states, and *not* equal to the on-lattice `orientation_count`. The design correctly downgrades this to
  a soft realizability check (W11). No finding.
- **The bulk single-vacancy hop is counted correctly.** §9.1's `orientation_count = 48/4 = 12` is right
  (the C₂ᵥ stabiliser of a ⟨110⟩ vector is order 4), and its anchor is unique (§4.2 picks `EMPTY` over
  `Ni` by `occ_priority`, no tie), so neither Finding 2 nor Finding 3 fires on it. Simple hops are fine;
  the bugs are specifically in the *symmetric / concerted / multi-defect* regime the mission actually
  targets.
- **Forward/backward are not double-counted for simple hops** — they live in different grid states, so
  only one is ever in the rate list at a time.

---

## Finding 1 [CRITICAL] — Runtime matching keys on the *core* only, which is coarser than identity, so every context-refined (`SPLIT_CHECK`'d) class duplicates its own instances with summed/ambiguous rates

**Where.** §0.1 ("the **core** sub-stencil (moved sites + 1st shell) drives runtime *matching*; the wider
**context** … is *promoted into `κ`* only as far as the harvested barriers demand"); §5.1 `compile`
builds `OrientedPattern.core_off/core_pred = reanchor(core_g …)` from `C.core`; §5.3 `match(P,s)` checks
**only** `P.core_off/P.core_pred` (+ depth); §4.4 `SPLIT_CHECK` grows `C.promoted_shell` / `κ` from
context and "re-key(C); re-key(outlier); recompile" — it never grows `C.core`.

**Mechanism.** `SPLIT_CHECK` exists precisely to separate two events with the *same move* but *different
surrounding context* and *different barriers* (§4.4, "Class collapse (wrong rates)"). After a split you
have sibling classes `C1` (context X, rate k₁) and `C2` (context Y, rate k₂) with **identical `core` and
identical `delta`** (the move and its first shell are the same; only the promoted context differs). Both
compile to `OrientedPattern`s whose `core_off/core_pred` are byte-identical, and both land in the same
`patterns_by_anchor[occ][depth][screen_key]` bucket (`screen_key` = "anchor species + coarse first-shell
signature" = a function of the core, so it is also identical). At runtime `match` tests both and **both
pass at every site**, because `match` never looks at the context that distinguishes them.

**Concrete trigger.** Harvest two surface vacancy-hops with the same core (`EMPTY`←`Ni` over a ⟨110⟩
bridge) but a Cr sitting in the 2nd shell on one of them, giving barriers 0.45 eV vs 0.62 eV.
`SPLIT_CHECK` promotes the 2nd shell into `κ` and makes `C1`, `C2`. Now take a grid site whose actual 2nd
shell has **no** Cr (physically `C1`, rate k₁). `match` enumerates *both* `C1` and `C2` there → two
`Instance`s for the one physical hop, with rates k₁ **and** k₂.

**Downstream.** (a) `R_total = Σ class_count·k` is inflated by the extra instance. (b) The move is
over-selected; when the "wrong" sibling is chosen, `execute` applies the (identical) core `delta` anyway,
so the *state* change is right but it fired at rate k₂ instead of k₁ — the branching ratio against
competing moves is wrong. (c) The entire purpose of the crown-jewel `SPLIT_CHECK` is defeated at runtime:
the catalogue distinguishes X from Y, but the executor cannot, so both rates are always live. This is
silent — no gate checks "did more than one class match this site?", and I5 (rate-list rebuild) reproduces
the same double-match, so it agrees with itself.

**Fix.** Matching must test the **promoted-context predicates**, not just the core — i.e. the matching
stencil for a class must be `core ∪ (context promoted into κ)`. That is correct but it dissolves the
"core is small, matching is cheap" performance premise for any split class; the design needs to either
(i) fold promoted context into the matched stencil and re-cost §5/§10, or (ii) forbid context-only splits
and instead always grow the *core* under `SPLIT_CHECK`. As written the two mechanisms are mutually
inconsistent.

---

## Finding 2 [CRITICAL] — The canonical form is not a complete invariant: the anchor is fixed by a frame-dependent tie-break and the form is minimised over the point group about that *single* anchor, not over the anchor choice — so symmetric concerted events fragment across harvest orientations

**Where.** §4.2 `anchor = argmin_m key(m)`, `key(m) = (occ_priority(before(m)),
round(|Cartesian(m)−centroid|,1e-3), lex(offset(m)))`. §4.3 `canonical_form` does `for g in G: … min(...)`
— it minimises over the group **only**; the offsets are already expressed relative to the §4.2 anchor.
The §4.3 completeness bullet even claims "anchoring on a moved site **plus the min over anchors** gives
translation invariance" — but the pseudocode performs **no** min over anchors.

**Mechanism.** `key(m)` is `G`-invariant in its first two components (occupancy and distance-to-centroid
are preserved by rotations) but its tie-break `lex(offset(m))` is **not** — offsets are in the arbitrary
projection frame, so `lex` order changes under rotation. Whenever the first two components tie, the anchor
is chosen frame-dependently. `canonical_form` then rotates only *about that anchor*; it cannot reach the
representative that a different anchor choice would produce (that differs by a **translation**, which is
not in `G`). Two projections of the *same* event in two orientations therefore land on two different
canonical tuples → two `class_id`s.

**When the tie fires — exactly the targeted mechanisms.** The first two `key` components tie whenever
≥2 moved sites share `before`-occupancy and are equidistant from the moved-set centroid:
- **Any symmetric divacancy / multi-vacancy concerted event** (SPEC scope: "1–2 vacancies"): the two
  moved `EMPTY` sites tie on `occ_priority(EMPTY)` and on centroid distance → tie → `lex`-broken →
  frame-dependent anchor.
- **Any symmetric ring / exchange with ≥2 like-species movers** (the "rings, antisite exchanges … absent
  from standard catalogues" the mission is built to discover).

**Downstream.** (a) **The loop's convergence detector is defeated.** The convergence signal is
"new harvested classes per cycle → 0" (SPEC decision 1/6; §7.3). A symmetric event re-discovered in a new
orientation canonicalises to a *new* `class_id` and is counted as a brand-new class — so
"new-classes-per-cycle" never decays for these events and the catalogue keeps "growing" on re-orientations
of things it already has. (b) One physical event's barriers are split across up to (number of tied movers)
spurious classes, each with fewer samples → noisier `Ea`, weaker per-`family_id` fallback fits.
(c) Forward and backward fragments can land in different `class_id`s, mis-linking the pair (feeds
Finding 5/7). (d) The headline "provably complete / collision-free canonical form" claim is false as
implemented.

**Fix.** Implement the min the prose already promises: minimise `serialize(...)` over
**(every moved site as anchor) × (every g ∈ G)** jointly, and drop `lex(offset)` from `key`. That is a
genuine complete invariant (orbit under translation × point group × internal automorphism); the current
"pick-one-anchor-then-min-G" is not.

---

## Finding 3 [CRITICAL] — Symmetric multi-anchor events are over-counted in the rate list: one physical move matches once from each symmetry-equivalent anchor site, inflating `R_total` and breaking flux-level detailed balance asymmetrically

**Where.** §5.2 re-anchors each pattern "at its rarest site" and (for vacancy-free events) "on the
least-abundant occupied species"; §5.3 `build_rate_list` loops over **every** candidate anchor and
appends an `Instance` per matching `(anchor, pattern)`. There is no instance-level canonicalisation/dedup
anywhere in §5.

**Mechanism.** Correctness of the count requires *each physical elementary move to correspond to exactly
one matching `(anchor, pattern)` pair*. That holds only when the rarest core predicate is **unique inside
the event**. When the rarest predicate occupies **k symmetry-equivalent core sites**, the same physical
move is matched once from each of those k anchors (the compile-time orbit dedup in §5.1 collapses only
rotations *about the class anchor*; the internal symmetry relating the k anchor sites is a rotation *about
the event's centre* = rotation+translation, which is not collapsed). Result: the move is entered **k
times**.

**Concrete triggers (all in scope).**
- **Symmetric divacancy migration** (2 vacancies, SPEC scope). Core has two `EMPTY` sites related by the
  event's own symmetry; `rarest = EMPTY` matches from both → **2× count** of that super-event.
- **A minority-species ring where the anchor species repeats** — e.g. a 3-Cr-involving ring in Ni whose
  rarest predicate `Cr` sits at two of the moved sites → 2× (or 3×) count.
- **Grey-mode vacancy-free events**: with all species collapsed to `OCC_ANY`, *every* occupied core site
  is an equally-rare anchor candidate, so the multiplicity equals the number of occupied core sites — the
  worst case.

**Downstream.** (a) `R_total` is inflated by the multiplicity for those classes → `Δt = −ln(u)/R_total`
is too small (KMC clock runs slow) and the over-counted class is over-selected relative to its true rate.
(b) **Detailed balance breaks at the flux level and G2 cannot see it.** Microscopic reversibility needs
`n_f·k_f = n_b·k_b` per pair; the over-count factor is *state-dependent* (a forward event may have a
unique vacancy anchor while its reverse, in the flipped state, has two symmetry-equivalent vacancy
anchors), so `n_f` and `n_b` are inflated by *different* factors. G2 (§7.2) checks the **rates**
`k_f/k_b` against `(ν0_f/ν0_b)·exp(−ΔE/kT)` — it never inspects instance multiplicities — so a
multiplicity-induced flux imbalance passes every gate. Equilibrium composition / surface segregation (the
whole dealloying observable) drifts silently.

**Fix.** After matching, canonicalise each `Instance` to a representative (e.g. the set of absolute
touched sites + `class_id`) and dedup; or require `match` to accept a hit only when the runtime anchor is
the *canonical representative* of the found motif (the lexicographically-minimal equivalent anchor site),
so each physical move is admitted exactly once regardless of internal symmetry.

---

## Finding 4 [MAJOR] — Surface classes are compiled under C₄ᵥ, which omits the horizontal mirror σ_h, so an event harvested at one free surface is never matched at the opposite surface of the slab (silent zero-flux there)

**Where.** Internal contradiction. §4.1 headline: "Default `G = O_h (48)` over the `EMPTY`-decorated
stencil … the surviving subgroup is exactly **C₄ᵥ (8)** — recovered *from the data*". But §4.3
`canonical_form` and §5.1 `compile` both call `G = group(regime)` which returns **C₄ᵥ (8)** for the
surface regime, and iterate *only those 8 ops*. The field table (§1.3) lists surface `regime = C4v`, bulk
opt-in `D4h`.

**Mechanism.** C₄ᵥ about the surface normal = {E, 2C₄, C₂, 2σ_v, 2σ_d} — four rotations about `+z` and
four **vertical** mirror planes. It does **not** contain σ_h (reflection through the `xy` plane), the very
operation that relates the top free surface to the bottom free surface of a slab. (Ironically the *bulk*
`D4h` opt-in *does* contain σ_h; the surface, where you need it, uses the smaller group.) So compiling a
**top**-surface event under C₄ᵥ generates only top-oriented `OrientedPattern`s (the `EMPTY`/vacuum
decoration points `+z`). The σ_h image — the physically identical event at the **bottom** surface, vacuum
pointing `−z` — is never emitted.

**Concrete trigger.** SPEC geometry is a slab with "free surfaces in ±z" and 1–2 vacancies. A vacancy
introduced near the top is explored by pyKMC → top-surface events harvested. The same vacancy later random-
walks to the **bottom** surface. There, `depth_sig` is also `SURFACE` (depth 0), but every compiled
surface pattern expects vacuum above; none matches a vacuum-below site, and the bulk hop patterns need an
occupied below-neighbour that a bottom-surface site lacks (`OUTSIDE`). No pattern matches the bottom-
surface hop.

**Downstream.** The bottom-surface hop carries **zero flux and is not even flagged**: the "never-zero"
guard (§6.3) only rescues moves that are *geometrically matched but unrated*; here nothing matches, so
nothing is counted, flagged, or reported. The vacancy is silently frozen / biased at the far surface, and
because the unmatched move never appears in the coverage report (it is neither exact nor fallback), the
loop's convergence detector reports "converged" while a whole surface is inert. This escalates toward
critical whenever harvest is one-sided; it is "major" because a symmetric slab may eventually harvest both
surfaces and self-heal (manual rescue = seed a bottom-surface vacancy, or add σ_h).

**Fix.** Either (i) take §4.1 literally and *always* canonicalise/compile under the full `O_h` (48),
letting the decoration+`depth_sig` reduce the *stabiliser* automatically (this keeps σ_h and covers both
surfaces), or (ii) use the slab group `D₄ₕ` (which contains σ_h) for the surface regime rather than C₄ᵥ.
The current `group(regime)=C4v` is the one choice that drops the top↔bottom relation.

---

## Finding 5 [MAJOR] — Self-reverse detection trusts pyKMC's mover-local grey graph-hash equality (`event_id == id_final`) and a context-blind Δ-inversion test, wrongly collapsing forward/backward pairs whose surrounding context is asymmetric — forcing ΔE = 0

**Where.** §7.2 `elif C.self_reverse (event_id == id_final, or Δ = its own inverse under g): C.backward_class
= C.class_id; C.pair_status = self`, and then `C.dEnergy = Ea_fwd − Ea_bwd`. Source: `event_table.py`
lines 340–344 — pyKMC returns *only the forward row* and sets it as its own backward when
`dfevent_forward["event_id"] == dfevent_forward["id_final"]`; `event_id`/`id_final` are single-atom,
mover-centred graph certificates (`graph_nauty.graph(..., atom_idx=[index_move])`), species-blind in grey
mode.

**Mechanism.** `id_min1 == id_min2` means only that the **mover's own rcut graph** is isomorphic before
and after — it is neither necessary nor sufficient for the event to be its own reverse. Two distinct
end-sites can be graph-isomorphic to the mover yet sit in different *wider* contexts (asymmetric 2nd/3rd
shell, or — in grey mode — different species entirely). pyKMC then discards the backward barrier, and the
design's `self_reverse` disjunct **inherits that verdict** (the `or` short-circuits before the geometric
check). Worse, even the geometric disjunct "Δ = its own inverse under g" only inspects the **move**: Δ =
{A: Ni→EMPTY, B: EMPTY→Ni} is its own inverse under the A↔B midpoint inversion regardless of what
decorates A vs B, so a context-asymmetric hop is declared self-reverse and gets `Ea_bwd := Ea_fwd`,
`dEnergy := 0`.

**Concrete trigger.** A near-surface vacancy hop whose initial site is fully-coordinated subsurface and
whose final site is a step edge — same mover grey graph, genuinely different real barrier and a real
`ΔE ≠ 0`. Or an alloy hop with a Cr in the 2nd shell on one side only (outside the mover's rcut graph but
inside the design's identity context).

**Downstream.** The pair is recorded with `dEnergy = 0` ⇒ `k_f/k_b = ν0_f/ν0_b ≈ 1`. G2 cannot catch it:
there is no independent `Ea_bwd` to test against, so the detailed-balance gate is trivially satisfied by
the fabricated symmetry. Equilibrium occupancy / segregation is biased silently — again the primary
dealloying observable.

**Fix.** Never trust `event_id == id_final` for self-reversal; require that some `g ∈ G` maps the **full
decorated stencil** (delta **and** promoted context **and** saddle token), with `before↔after` swapped,
onto itself — i.e. self-reverse must be a property of `κ`, not of Δ alone or of pyKMC's mover hash. If the
context is asymmetric, treat forward and backward as distinct classes and demand the reverse barrier from
the next harvest leg.

---

## Finding 6 [MAJOR] — The saddle token's `role()` is never defined invariantly and the token is canonicalised as an *unordered* set, so multi-mover concerted events either fragment or merge distinct concerted paths — defeating the token's own purpose for the case it matters most

**Where.** §3.3 builds `saddle_token = [PathToken(off=tok, atom_role=role(p)) for p in movers]`; §4.3
canonicalises it as `t = sorted((g·off, role) for (off,role) in saddle_token)`. `role(p)` is never
defined. §4.4/§9.2 rely on the token to split "over-bridge vs through-hollow" *a priori*.

**Mechanism.** The token participates in the identity key, so `role` must be a canonical, frame-invariant
label — but neither plausible definition works for multi-mover events:
- If `role` = the mover's **subset-relative index** (à la `move_atom_idx`, the only per-mover handle
  pyKMC hands over), it is harvest/orientation-dependent → the same concerted event in two orientations
  gets two different token multisets → **fragmentation** (compounds Finding 2).
- If `role` = the mover's **species** (or `OCC_ANY` in grey), then two movers with equal role are
  interchangeable in the *unordered* `sorted` token set. A `g` that pairs mover-1's *start* with mover-2's
  *saddle displacement* produces a matching sorted set, so "mover-1 bulges toward bridge X, mover-2 toward
  bridge Y" and its swapped counterpart canonicalise identically — **merging two genuinely different
  concerted paths** with different barriers.

**Concrete trigger.** The §9.2 3-site surface ring has two movers (Ni and Cr) each with a saddle bulge
"over its bridge." In full colour the roles differ so the unordered set is safe *here*; but a
**2-Ni-mover** concerted event (two like-species movers, each bulging over a different bridge) is exactly
the interchangeable case — its two distinct chiral/path variants collapse to one class, and their
barriers get averaged.

**Downstream.** Same-endpoint/different-path aliasing that the token was introduced to prevent, but for
multi-mover events; either catalogue bloat (fragmentation) or wrong averaged rates (merge). Because the
token feeds `κ`, `SPLIT_CHECK`'s "raise token resolution" backstop (§4.4) cannot recover a *pairing* that
was destroyed by discarding mover↔token correspondence.

**Fix.** Define `role` from an invariant (e.g. the canonical rank of the mover's *start offset* under the
same anchor×G minimisation as Finding 2), and canonicalise the token as an **ordered** structure tied to
each mover's start site, not an unordered set — so mover-i's start, end, and saddle displacement stay
bound together through canonicalisation.

---

## Finding 7 [MAJOR] — Synthesized barrier-pending reverse classes have no measured rate, so between harvest cycles the just-executed forward move is either mis-rated on reverse or has no reverse instance at all — a ratchet that breaks microscopic reversibility

**Where.** §7.2 `else: Cb = synthesize_reverse(C); Cb.pair_status = synthesized_pending;
enqueue_audit(Cb, PAIR_CLOSURE); C.backward_class = Cb.class_id`, described as guaranteeing "pairing
closure mid-harvest … reversibility is then a property of the closed catalogue". §8.3 says `QUARANTINED`
classes "are excluded from execution".

**Mechanism.** When only one direction is harvested, the reverse `Cb` is created with **no barrier** and
sits in the audit queue (`pending`). The design never resolves what rate `Cb` carries at runtime before
its barrier is measured:
- If `Cb` is compiled and matchable with a placeholder rate, then after firing `C` forward the grid holds
  `Cb`'s context, the matcher enumerates the reverse instance (as §7.2 intends) — but at a **fabricated
  rate**, injecting wrong reverse flux and a wrong `ΔE`, defeating the very balance §7.2 claims to close.
- If `Cb` is *not* compiled until approved/measured (consistent with §8.3 excluding `pending`/
  `QUARANTINED` from execution), then the reverse move is **absent from the rate list**: the system can
  go `C` but cannot come back until the next pyKMC leg supplies `Ea_bwd`. That is a directional ratchet —
  microscopic reversibility is violated across the whole evolve leg (up to ~10⁶ steps, SPEC decision 6),
  which for a diffusion catalogue systematically biases transport and equilibrium.

**Concrete trigger.** Any asymmetric-barrier event where pyKMC's short (`k = 20–1000`) leg happens to
sample only the downhill direction — common, because the uphill reverse is rarer to trigger in the off-
lattice run. Its reverse is synthesized pending and stays pending through the long evolve leg.

**Downstream.** Either biased reverse flux (placeholder rate) or a one-way ratchet (uncompiled) for every
one-direction-harvested class — precisely the classes for which the loop has *no* reverse barrier yet, so
the error persists exactly where it is hardest to notice.

**Fix.** Give a synthesized reverse an *explicit, physically-bounded* provisional rate derived from
`Ea_bwd = Ea_fwd − dEnergy` using the fallback `ΔE` estimate (so the pair is at least detailed-balance-
consistent by construction), mark every instance it rates as flagged/never-zero, and route the
environment to top exploration priority — rather than leaving the reverse either fabricated-unbounded or
missing.

---

## Cross-cutting note: three of these are invisible to the design's own safety nets

- **I5 (full-rebuild rate-list oracle, §5.4)** re-runs the *same* matching logic, so it reproduces the
  Finding 1 and Finding 3 over/duplicate-counts and asserts self-consistency — it validates the fast path
  against a slow path that shares the bug.
- **G2 (detailed balance, §7.2)** checks *rates*, never *instance multiplicities* or *pairing
  correctness*, so it is blind to Findings 3, 5, and 7.
- **The coverage/convergence report (§7.3)** counts exact vs fallback flux among *matched* instances;
  Finding 4's unmatched far-surface moves and Finding 2's re-fragmented classes both corrupt the
  "new-classes-per-cycle → 0" signal without ever showing up as fallback flux.

The common root is a single architectural decision: **identity is defined on a richer object
(core + promoted context + saddle token + depth_sig, canonicalised) than the objects used for matching
(core only) and for counting (per-anchor, no instance dedup), and the anchor that ties them together is
not a group invariant.** Findings 1–3 are three faces of that mismatch; 4–7 are where the specific group
choice and the pairing bookkeeping inherit it.
