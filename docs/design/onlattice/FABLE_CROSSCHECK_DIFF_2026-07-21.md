# Diff — Fable cross-check vs the parent judge synthesis

**Compares:** `FABLE_CROSSCHECK_SYNTHESIS_2026-07-21.md` (written blind to the parent report,
except that the memory index had exposed the parent's one-line headline) against
`DEEP_RESEARCH_FINDINGS_2026-07-18.md`. Claim IDs are `[pass :: status #n]` in the claims JSON.

**Overall:** the two syntheses agree on the direction of every per-pass verdict. The differences
are: two table-row confidence inflations (unverified leads presented under "High"), one
evidence-scope overstatement (bimodality "in Ni-Fe-Cr"), one recommendation the evidence does not
carry as stated ("adopt CR selection"), one extrapolation beyond the cited claim (ν₀_f ≠ ν₀_b),
and one architectural distinction the parent blurs that materially affects the Phase C memo
(which fallback population the surrogate can actually serve). None of these reverses a verdict;
several change how strongly a decision should be stated.

---

## D0 — Self-correction (disclosed)

My first draft said all confirmed surrogate results used ≥2,000 training barriers. Re-reading
[1 :: c#13], the NiFeCr SVR number is quoted over 120 data points. Corrected in the synthesis.
The parent report does not discuss training-set sizes at all — see D6.

## Agreements (no diff)

- **Accuracy ladder** (continuous 0.04–0.1 eV vs low-order 0.2–0.3 eV; KRA/Kinetic-Ising breaks
  in concentrated FCC): identical readings, same claims.
- **Pass 2 verdict** — topology identity + reconstruction-failure detection + always-re-converge;
  snap_tol is the wrong knob; rate-error-budget tolerance is a genuine gap. Identical, including
  the 1.0 vs 0.5 eV/Å note being paper-evolution rather than contradiction.
- **Pass 4 verdict** — rate-weighted completeness dominates count-based; the over-optimism-on-
  biased-sample caution is the key caveat and is unverified; independent probe mandatory. Identical.
- **Pass 5 verdict** — canonical labeling is the missing guarantee; max-displacement anchor;
  automorphism/symmetry number for free; direction-of-motion augment needed; graph↔geometry
  uniqueness precondition. Identical.
- **Refuted-claim handling** — same five, same consequences drawn.
- **Concerted-saddle silence** — both flag that no confirmed evidence supports static
  atom-centered surrogates for concerted/multi-atom saddles, and that this forces an on-the-fly
  channel.

## Disagreements / re-statements

### D1 — Headline: "replace the catalogue" is stronger than the evidence carries *as a Phase C entry move* (strength, not direction)

Parent (gap-table row 1+3 and cross-cutting #1): "Replace the discrete exact-class catalogue +
split_tol with a continuous per-environment barrier surrogate… retires gaps 1, 3, and 6 together.
Do it before building Phase C."

I agree the surrogate should become the **rate authority for lattice-representable hops**, and
that the DB-safe KRA-form decomposition dissolves gaps 3 and 6 by construction. Two things the
headline under-weights:

1. **Data regime.** Every confirmed accuracy figure comes from a curated, homogeneous NEB corpus
   (120?–32,000 barriers of single-vacancy exchanges). pylatkmc has 445 heterogeneous harvested
   events (~1.01 members/class). Nothing in the evidence base demonstrates headline accuracy at
   that corpus size; the surrogate is the right *architecture* with an *unproven current
   operating point* — the in-house fit (audit's "cheap empirical anchor") is load-bearing for
   the decision, not a nicety.
2. **The catalogue's residual role.** "Replace/abandon" elides that the harvested catalogue is
   the surrogate's only training corpus and its natural regression test. The catalogue's
   *runtime rate-lookup* role is what gets replaced; the harvest loop and the curated event set
   remain first-class. (Also worth stating: at ~1.01 members/class, split_tol lumping is
   currently almost inactive — the lumping bias is prospective as classes fill, while the
   class-mean-ΔE detailed-balance defect is live now. The urgency ordering is DB first, lumping
   second.)

### D2 — The parent blurs which fallback population a surrogate can serve (architectural, affects the memo)

The 316/439 G3-fail classes are events that **failed projection onto the rigid lattice** — they
never became on-lattice processes at all. A φ/surrogate assigns rates to *lattice-representable*
processes in unseen environments; it cannot restore event channels that have no lattice
representation. So the "majority channel" splits into two distinct populations:

- (i) representable hops in unseen/unmatched environments → the continuous surrogate is exactly
  the right tool (F1/F2);
- (ii) non-representable (strongly-relaxed, concerted) event classes → **no on-lattice rate
  model, discrete or continuous, can fire these**; only topological re-identification (which may
  recover some as representable) or an off-lattice/on-the-fly channel addresses them (F5).

The parent's pass-2 verdict ("route non-representable events back to off-lattice search") shows
it understands this, but its headline ("the single highest-leverage move is [the surrogate]")
assigns leverage inconsistently with its own pass-2 finding: if the 316 rejected classes are the
majority flux concern, the surrogate — which only serves population (i) — is not the single
highest-leverage move; the identity/representability redesign plus the on-the-fly channel is at
least co-equal. My synthesis states these as a three-tier architecture with tier 3 non-optional.

### D3 — "Adopt composition-rejection selection" is not what the pass's own evidence recommends (recommendation vs evidence)

Parent (row 4, cross-cutting #3): "Adopt CR selection (retires the dense table + the micro-group
worry)."

The same pass confirmed: CR wins only when *search* cost dominates, and update cost dominates
"often … in practice" [3 :: c#2, c#14]; the closest production analogue to pylatkmc
(kmcos, generated-code lattice KMC) uses two-level BKL binary search [3 :: c#18]; SPPARKS treats
solver choice as interchangeable O(N)/O(log N)/O(1) [3 :: c#10]. What the evidence *settles* is
narrower: CR is exact for continuous rates without micro-group quantization [3 :: c#0, c#4, c#7]
— so the micro-group worry is moot — and selection is not the binding constraint. Two category
errors in the parent's row: (a) CR does not "retire the dense table" — the dense n_procs×n_sites
*enrolment* structure is retired by sparse per-site lists ([3 :: r#1] shows KMCLib is sparse),
which is orthogonal to the selection algorithm; (b) "adopt CR" reads as a requirement where the
evidence supports "tree/Fenwick BKL is production-standard and sufficient; CR is an available
exact optimization if profiling ever shows selection dominating." The planned grouped-BKL +
Fenwick design needs no change on this evidence.

### D4 — ν₀_f ≠ ν₀_b is an extrapolation beyond the cited claim (evidence hygiene)

Parent (row 6): "forward/backward barriers depend on different atom sets (weakly correlated), so
ν0_f ≠ ν0_b in general … do not assume ν0_f = ν0_b." The confirmed claim [1 :: c#10] is about
**barriers**, not prefactors — the quote never mentions vibrational prefactors. The conclusion is
physically plausible (Vineyard ν₀ depends on initial-state curvatures, which differ between
directions) but it is *inferred*, not sourced; the correct prefactor constraint
(ν₀_f/ν₀_b = Z_vib-ratio) was part of the research question and came back with **no confirmed
claim**. The parent's "Med" confidence partially covers this, but the table states the ν₀
conclusion as if it were the literature's. It should be labelled an inference + open item.

### D5 — Scope inflation on percolation/bimodality (evidence-scope)

Parent (row 1e): "Barrier distributions are bimodal; transport percolates the low-barrier tail
(**confirmed in Ni-Fe-Cr and Ta-W**)"; pass-1 body: "FCC-alloy barrier distributions are bimodal
[CONFIRMED 3-0]." The confirmed quote attributes the two-peak/percolation observation to
**Cu-based** alloys specifically [1 :: c#6] (the source paper spans Ni- and Cu-based systems);
the Ta-W result is BCC. Percolation-through-the-tail is thus confirmed as a *phenomenon in
concentrated transition-metal alloys* (Cu-based FCC + Ta-W BCC), and remains an inference —
reasonable, but an inference — for Ni-Cr specifically. Direction unchanged; the "in the exact
family" strength is not supported.

### D6 — Table-row confidence tags blend confirmed findings with unverified leads (presentation, matters for sign-off)

Rows 4 and 5 carry "High" confidence on sentences whose decisive clause is an unverified lead:
row 4's "even Zacros only asserts, never proves" is [3 :: u#2] (votes errored); row 5's "biased
low (over-optimistic) when fast events are found first" is [4 :: u#6] (votes errored). The body
text labels both correctly; the summary table — the part a reader signs off from — does not. Same
pattern, milder, in row 8 (marked Med, appropriately). Since the sign-off decision reads the
table, the two rows should carry a split tag (e.g. "High (direction) / lead (cited clause)").

### D7 — Minor wording

- "KRA is **provably** insufficient for Ta-W" — it is *empirically* insufficient (r² = 0.21)
  [1 :: c#9]; nothing is proven.
- Pass-1 refuted note: the parent glosses refuted r#0 as "the confirmed picture is the opposite
  emphasis." Nothing confirmed establishes an opposite variance decomposition; the accurate
  statement is just that the variance-attribution claim did not survive. (My synthesis instead
  says: argue the tail hazard from percolation, not from variance decomposition.)

## Decisions I think the evidence does not (yet) carry

1. "Do it before building Phase C" as *replace-catalogue-first* sequencing (D1) — the in-house
   fit on the 445 barriers should gate how much rate authority the surrogate gets at Phase C
   entry; the DB-safe *form* can be adopted immediately regardless.
2. "Adopt CR selection" as a design requirement (D3) — profiling-gated optimization, not a
   requirement; keep grouped BKL + Fenwick.
3. The ν₀_f ≠ ν₀_b directive as literature-settled (D4) — adopt it as a conservative modeling
   choice, but it needs the HTST ν₀ recipe validated in-house (pyKMC's own htst machinery can
   measure it on harvested pairs).

## Memory-entry impact

`pylatkmc-research-gap-audit` currently records the headline as "replace discrete class
catalogue+split_tol with a continuous barrier surrogate." Per D1/D2 this should be refined to:
continuous DB-safe surrogate as rate authority **for lattice-representable hops** (catalogue
retained as training corpus/regression set), **co-equal** with topological identity + an
on-the-fly channel for the non-representable majority tail — pending the sign-off on
`PHASEC_RATE_MODEL_DECISION.md`. Flagged here rather than edited blind.
