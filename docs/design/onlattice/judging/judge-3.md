# Judge 3 — Scoring rationale

Panel: judge 3 of 3, independent. Clean-room rule observed: I did **not** read the workspace's
existing on-lattice engine or its event-classification pipeline, and no workspace description of
them shaped this evaluation. I judged strictly against `SPEC.md` and its rubric, using the published
lattice-KMC literature (BKL/n-fold-way, self-learning KMC, k-ART, SPPARKS/kmos pattern codes,
cluster-expansion KMC) as the allowed knowledge base.

## Verification method

I read the **input side** the SPEC authorises (`/home/kerr/pykmc/pyKMC/pykmc/`) and checked every
load-bearing claim the four designs make about the harvest contract against source, so scores rest
on facts, not on each document's self-description:

- **Reference-row schema** (`event_table.py` L649–694, columns L718–736): matches the SPEC exactly —
  `initial/saddle/final_positions`, `initial_types`, `energy_barrier`, `k`, `k_prefactor`, `nu0`,
  `move_atom_idx`, `sym_matrix`, `sym_perm`, `idx_backward`, `event_id`, `id_saddle`, `id_final`,
  `dra`. All four designs read it correctly.
- **The stored cluster is the `rcut` ball of the *nominal* mover** (`initial_positions =
  min1_positions[neighbor_list_forwward]`, `neighbor_list_forwward = neighbors_list["rcut"][index_move]`,
  L611, L653). This is centred on `move_atom_idx`, so a *second* mover of a concerted event sits near
  the cluster edge and its own context shell can be truncated — a real hazard the designs vary in
  handling.
- **`event_id` is a single-atom, single-state pynauty graph certificate of the mover's environment**
  (`graph(..., atom_idx=[index_move], ...)`, L592–597), optionally the mover's live classifier id
  (L645–647); coordination labels are rejected upstream (L302–323). It is **not** an event-level
  multi-site key — which correctly motivates all four designs re-deriving their own lattice identity
  and demoting `event_id` to a provenance/pre-filter bucket.
- **`sym_matrix`/`sym_perm` are the GREY geometric stabiliser** of the event: `unique_symmetries`
  runs IRA SOFI with `typ = nat*[1]` (species-blind) and keeps ops that preserve the displacement
  field (`symmetries.py` L34–68). So it encodes `|Stab(event)|`, not the orbit size — a subtlety that
  matters for the sym_perm cross-check some designs propose.
- **Rate law** `rate = prefactor * exp(-dE/(kb*T))`, prefactor & rate in **ps⁻¹**, dE in eV
  (`rate_constant.py` L45). All four state `k = ν₀·exp(−Ea/k_BT)` with ps⁻¹ correctly.
- **Validity gate** `is_valid_new_event` (L240–295): `emin ≤ dE_f ≤ emax`, `dE_b ≥ emin`, and the
  asymmetry rule `dE_f > energy_asymmetry·backward_emin AND dE_b < backward_emin` (L283–284). The
  self-reverse shortcut is `event_id == id_final` → single row (L340–344).
- **Mover detection** `event_movers` is displacement-threshold based (a pre-filter), returning the
  union of all atoms with disp > `matching_thr` and a top-`n_movers` floor (`geometry.py` L207–265).
  Every design correctly treats it as a pre-filter and uses the **site-change** test as ground truth.
- **`NeighborsList` builds `cKDTree(boxsize=diag(cell))`** (`neighbors_list.py` L41–42) — an
  orthorhombic-cell assumption that only one design (descriptor) explicitly inherits and asserts.

FCC constants checked numerically: nn = a/√2 = 2.489 Å, a/2 = 1.760 Å, 2nd shell = a = 3.52 Å,
FCC(100) surface coordination = 8. All four state these identically and correctly.

**Headline finding:** this is a strong, tightly-bunched field. All four nail the non-negotiable core
(integer FCC-on-SC parity embedding, O(1) neighbour tables, class-grouped BKL, defect-anchored
enumeration, O(1)-in-N incremental dirty-region update, site-change mover detection, the four auto
gates, deterministic ideal-site reverse map). **None has a fatal flaw.** Differentiation is entirely
in the quality of the *signature idea* and depth on the two highest-weighted axes (fidelity 30 +
classification 20 = 50% of the score).

---

## Design `pattern` — precompiled local patterns + data-driven class refinement

### Correctness & physical fidelity — 26.5 / 30
Physically the most defensively-correct of the four on the axis that matters most: **wrong barrier
from an over-merged class is the #1 fidelity risk**, and pattern is the only design with an *active*
auto-guard against it. Its core/descriptor split (§4.4) drives matching off a minimal *executability*
core but promotes the wider descriptor shell into identity **only when harvested barriers demand it**
(SPLIT_CHECK: intra-class barrier spread > `split_tol` → find the smallest shell extension that
separates the outlier, re-key both, or route to audit if none does). Identity "starts minimal and
grows only where the data proves it must" — the correct answer to the bias/variance of context
radius, and it means rates stay honest as the catalogue grows. Mover detection is by site-change with
the `mover0 ∈ movers` gate (§3.2, matches the source's ground-truth semantics). It is the **only**
design that is fully honest about detailed balance (W5: rates from independently-averaged barriers are
*checked* not *enforced*; it names the exact fix — per-pair symmetrisation). The gates (§8.2) reuse
the real `emin/emax/backward_emin/energy_asymmetry` thresholds. Deductions: it **drops the saddle from
identity** (§3, "on-lattice identity is defined by initial→final site changes plus context only"), so
two events pyKMC keeps distinct by `id_saddle` (same endpoints, different path/barrier) will merge and
must be caught *reactively* by SPLIT_CHECK → audit rather than distinguished up front; and its Oh/C4v
binary regime (W4) is a two-way switch where subsurface sites really sit between.

### Runtime matching cost at scale — 18 / 20
Correct O(1)-in-N per step, with all the right machinery: compile classes → oriented patterns
deduped by the event's own symmetry; **anchor at the rarest predicate** (vacancy/adatom/minority
species) so enumeration scales with defects not atoms; per-site process lists + group-BKL Fenwick
(O(log C) selection, O(1) instance turnover via swap-remove); incremental invalidation over a fixed
`ball(t, r_supp_global)` that grows only when a larger event is ingested; periodic self-heal checksum
as the correctness oracle. The consolidated complexity table is right. It is marginally behind
`performance` only because it says less about the low-level substrate (cache layout, SoA, memory
budgets, table-vs-arithmetic neighbour crossover) that decides real wall-clock at 10⁵–10⁸ sites.

### Classification robustness + novelty — 18 / 20
The strongest classification story in the field and the reason it wins overall. The **data-driven
SPLIT_CHECK** is the single best mechanism any design offers for the named "classification robustness"
axis — it neither fragments classes gratuitously (minimal core) nor collapses distinct physics
(auto-split on barrier evidence). The §4.5 reconciliation with pyKMC's `event_id` is precise and
correct: one graph hash can fan out into several surface-oriented lattice classes and several hashes
fold into one bulk class, and pattern gets both directions right where a topological hash cannot.
Novelty = canonical-form present/absent, first instance audited. The only ding: dropping the saddle
means same-endpoint/different-saddle degeneracies surface as barrier spread and land in audit rather
than being resolved by construction.

### Implementability & fit — 12.5 / 15
Fully file-based, scriptable, reuses the real gates, deterministic ideal-site reverse map. Slightly
behind on two counts: SPLIT_CHECK re-keying classes mid-campaign (invalidating compiled patterns and
audit provenance) is real added complexity, and the doc is less specific than `descriptor` about exact
`event_table.py` column plumbing and the `cKDTree` orthorhombic constraint. Its §9.1 cross-check
claim — "its stabiliser leaves 12 distinct oriented patterns, matching the sym_perm count" — is
imprecise: `sym_perm` encodes `|Stab|` (= 4 for a ⟨110⟩ hop), and the orbit size is `|G|/|Stab|` =
12, so the *count* it should match is 4, not 12. Minor, and confined to a worked-example remark.

### Extensibility — 13 / 15
`DeltaSite{before, after}` + `delta_atoms` admits site→EMPTY with no re-harvest or schema break;
ternary is just a larger alphabet with no colour-swap symmetry assumed; the file-based loop closes
without redesign. Concrete but a shade less vivid than `performance`'s explicit Erlebacher-into-BKL
demonstration.

**Strongest transplantable ideas:** (1) the **core/descriptor split with data-driven SPLIT_CHECK** —
the best available answer to context-radius bias/variance and the top fidelity guard; (2) explicit
**event_id fan-out/fold-in reconciliation** (finer where the surface breaks symmetry, coarser where
the bulk restores it); (3) `r_supp_global` that grows when a larger collective event is ingested.
**Fatal flaws:** none.

---

## Design `symmetry` — canonical-labeling-first, one exact canonicaliser

### Correctness & physical fidelity — 25.5 / 30
The most *physically careful* symmetry treatment and the only design that puts the **saddle mechanism
into identity**. Its central decision — default to **D₄ₕ (bulk) / C₄ᵥ (surface), not O_h** — is
argued correctly: a body-diagonal O_h rotation maps a (001) layer onto a vertical plane and is not a
symmetry of a layered slab, so O_h would merge an in-plane ⟨110⟩ hop with an inter-layer ⟨110⟩ hop
that genuinely differ in a thin slab (§1.2, §9.1). This is a deliberate conservative over-split (never
a wrong merge). The **saddle path token** (§3.3: quantised 2×saddle offset, canonicalised, appended
to the key) is the on-lattice analogue of pyKMC's own `id_saddle`/IRA saddle check (`event_table.py`
L352–358) and correctly propagates the distinction that the other three designs discard — the best
mechanism-fidelity in the field. The canonical form is a provably complete, collision-free invariant
(same key ⟺ same orbit) and is at-least-as-fine as pyKMC's hash when `r_id ≥ rcut`, so it never
wrongly merges what pyKMC distinguishes. Gates reproduce the real asymmetry rule *verbatim* (§8.2 vs
source L283–284) — the deepest read of the input contract. **Deduction:** the `ActiveSites` definition
("adjacent to any EMPTY or on the surface skin ... ONLY these can trigger a nontrivial event", §5.2)
is a genuine, *unacknowledged* correctness hole — a bulk vacancy-free concerted event (antisite
exchange/ring away from any surface) would never be enumerated. For the dealloying mission this is
low-impact (such events are high-barrier and rare, and its own worked ring is vacancy-mediated), but
it is the one silent gap, and `descriptor`/`performance` explicitly close it with a rare-species
anchor.

### Runtime matching cost at scale — 16.5 / 20
Correct O(1)-in-N with `ActiveSites` + `TrigIndex` prefilter + `TouchIndex` + Fenwick `RateTree` and a
`STRICT_CHECK` rebuild oracle; complexity table is right. Held back by the `ActiveSites` completeness
gap above (a rate list that can silently omit a class is a runtime-correctness issue, not just a
physics one) and by carrying the largest default group (D₄ₕ over-split ⇒ more classes/instances to
maintain) with less substrate-level detail than `pattern`/`performance`.

### Classification robustness + novelty — 17 / 20
Very strong. The complete-invariant guarantee plus the **saddle token** give it the best proactive
discrimination of same-endpoint/different-path events — a real robustness win the others lack. The
`Stab_G(ev)` vs pyKMC `sym_perm` cross-check (§3.5) is the right *idea*, though the stated direction
("`sym_perm` ⊆ `Stab`") holds cleanly only in grey mode: the source computes `sym_perm` species-blind,
so in full colour the geometric stabiliser is a *superset* of the colour-decorated one and the subset
claim inverts. Novelty is a clean key present/absent test. Slightly behind `pattern` because its
context radius `r_id` is a single global value refined only by a variance diagnostic + manual bump
(W5), not the automatic shell-promotion `pattern` offers.

### Implementability & fit — 12.5 / 15
Solid: reverse map to the pyKMC restart contract, threshold and `event_movers` reuse, byte-stable
determinism via content hashes. A little more abstract about exact column plumbing than `descriptor`;
the D₄ₕ default means more harvested classes to converge, a real (acknowledged) pipeline cost.

### Extensibility — 12.5 / 15
Schema-ready for ternary and for `count_delta ≠ 0` dissolution, but the most honest that the
dissolution path (BKL competition, mass balance, Erlebacher rate) is a **stub** in v1 (W10) — correct
but less demonstrated than `performance`/`descriptor`.

**Strongest transplantable ideas:** (1) the **saddle path token** in identity — the only proactive
handling of same-endpoint/different-mechanism degeneracy, and a faithful echo of pyKMC's `id_saddle`;
(2) the **D₄ₕ-not-O_h thin-slab argument** (a genuinely more correct default, worth adopting as an
opt-in even in an O_h-default engine); (3) the provably-complete, tolerance-free canonical form with a
256-bit digest kept only as an index, never as the identity of record. **Fatal flaws:** none (the
`ActiveSites` gap is a bounded, mission-secondary hole, not a disqualifier).

---

## Design `descriptor` — one decorated stencil, three readouts

### Correctness & physical fidelity — 24 / 30
Elegant and largely correct. Its signature move — **always canonicalise under full O_h over a
stencil that decorates vacancy/vacuum as `V`** — is sound: the min-over-O_h-orbit only merges events
actually in the same orbit, and because the `V` decoration breaks symmetry exactly where the physical
surface does, the surface-preserving subgroup (C₄ᵥ for (100)) *falls out of the data* with no
hand-coded per-site group table (§3.2). It correctly keeps a surface-parallel and surface-normal hop
distinct and correctly merges top/bottom-surface events via the z→−z mirror. Mover detection is
site-change based; gates reuse the real thresholds. **Deductions:** (a) always-O_h *does* merge
deep-bulk in-plane vs inter-layer ⟨110⟩ hops that `symmetry` deliberately splits — defensible (the
difference is below barrier-averaging noise for this mission) but a real physical choice, not the
"automatic correctness everywhere" the doc claims; (b) it drops the saddle from identity **and** its
only refinement lever is `grow_R_env`, which structurally *cannot* separate same-endpoint/different-
saddle events (growing the spatial shell never resolves a saddle degeneracy) — so that failure mode is
detected (Ea_std) but not fixable within the design, only flagged for re-harvest; (c) `φ` is a lossy
readout (W1, acknowledged).

### Runtime matching cost at scale — 17 / 20
Correct O(1)-in-N: active-site set, `class_index` trigger buckets, segment tree, `dirty` = R_env
balls; honest that the heterogeneity clause makes the *initial build* O(N·S) for a concentrated alloy
(W3) while per-step stays bounded. Clean and right, marginally less substrate detail than
`performance`.

### Classification robustness + novelty — 16 / 20
Strong on the **novelty/fallback** half: the "one geometry" unification (identity `κ`, feature `φ`,
and reverse-map coords are all functions of the *same* stencil, so "near miss" is literally a short
hop in `φ`-space) is the most principled fallback framing in the field, and per-`family_id` regression
on Erlebacher bond-count features is physically motivated. Weaker on the **robustness** half than
`pattern`/`symmetry`: identity uses a fixed global `R_env` with only a variance *diagnostic* and a
*manual* `grow_R_env`, and — as above — that lever can't address saddle degeneracy.

### Implementability & fit — 13.5 / 15
The best pipeline fit of the four. It cites the exact `event_table.py` columns, reuses the exact
pyKMC thresholds (`emin/emax/energy_asymmetry/matching_score_thr/rcut`), and is the **only** design to
catch and assert the real `cKDTree(boxsize=diag(cell))` orthorhombic constraint from
`neighbors_list.py`. Modest new deps (a 48-element integer group, scipy KD-tree, numpy ridge). The one
caution it names itself (W8): demoting `event_id` moves authority to its own snap, so a subtly wrong
surface frame could mis-key a whole family before audit — shared by all four but most explicit here.

### Extensibility — 13 / 15
`V` as an ordinary species means dissolution = flip one conservation assert + add a reservoir counter,
no re-harvest/schema break; ternary is trivial; file handoffs close the loop. Concrete, just behind
`performance`'s explicit dissolution-rate integration.

**Strongest transplantable ideas:** (1) the **"one descriptor, three readouts"** unification — using a
single decorated stencil as identity key, regression feature space, and invertible reverse-map source
is genuinely elegant and simplifies the whole pipeline; (2) **decorate-with-`V` + always-O_h** as a
way to get the correct reduced surface group with zero per-site case analysis; (3) `family_id`-keyed
regression (discrete class selects the regressor, continuous `φ` is its input) — a clean realisation
of the SPEC's exact-lookup-plus-parametric-fallback. **Fatal flaws:** none.

---

## Design `performance` — incremental/performance-first executor

### Correctness & physical fidelity — 22.5 / 30
Correct on all the fundamentals (geometry, ps⁻¹ Arrhenius, site-change mover detection with the
`move_atom_idx` trap called out, depth-aware O_h/C₄ᵥ, the five gates including a v1 conservation gate)
and uniquely rigorous on *implementation* correctness (the I5 invariant: every 10⁴ steps rebuild the
whole rate list from scratch and assert set-equality — the slow method as the oracle for the fast
one). But it is the weakest of the four on *physical* fidelity for two reasons. First, its
detailed-balance claim is overstated: §6.2 writes `k_fwd/k_bwd = exp(−ΔE/k_BT)` "by construction",
which silently assumes ν₀_f = ν₀_b — false under HTST, where the row carries distinct forward/backward
prefactors (`k_prefactor` per row); with class-averaged barriers and prefactors, balance is
approximate, and unlike `pattern` it doesn't flag this. Second, it drops the saddle from identity and
simply averages same-endpoint barriers, and its remedy for an over-merged class is monitoring only —
W2 concedes "no principled auto-tuner beyond monitoring class growth and fallback fraction", i.e. it
*detects* rate-collapse but cannot *correct* it, the opposite of `pattern`'s SPLIT_CHECK.

### Runtime matching cost at scale — 19 / 20
The best in the field and the reason to transplant from it. It is the only design that engages the
substrate that actually decides wall-clock: flat contiguous `uint8` occupancy (1 MB at 10⁶, 100 MB at
10⁸), struct-of-arrays hot loops, **layer-blocked/tiled site ordering so a 12-star spans ≤3 cache
lines**, O(1) swap-remove `species_sites`, a `supported_by` dirty index, and an explicit
table-vs-arithmetic-neighbour **scale switch at ~10⁷ sites** with the memory arithmetic to justify it.
Defect-driven enumeration with an honest F13 note that a 50/50 equiatomic direct-exchange class
degrades toward O(N/2) and needs a spatial-index fallback. This is production-grade thinking.

### Classification robustness + novelty — 13.5 / 20
The weakest axis and the main driver of its rank. The canonicalisation is competent and correct but
the least differentiated: depth-aware O_h/C₄ᵥ with no adaptive split, no saddle token, no feature-space
unification. Its one novelty-side contribution is a nice performance touch — an `event_id → key` cache
so a warm pre-filter skips re-projection — but that accelerates a decision the others already make
cheaply; it doesn't improve *robustness*. Given classification is a 20-point named axis, competent-
but-plain costs it materially here.

### Implementability & fit — 13 / 15
Strong and concrete: file-based JSONL/xyz handoffs, the `config.control.reference_table` +
`initial_config` restart contract, threshold reuse, and the I5 oracle makes the fast path
*trustworthy* to ship. A shade behind `descriptor` only on exact column/constraint specificity.

### Extensibility — 14 / 15
The best-demonstrated extensibility. It shows Erlebacher dissolution `k = ν_d·exp((φ−n·E_b)/k_BT)`
dropping in as a coordination-dependent class rate competing in the *same* grouped BKL vector, and
makes the sharp observation that because sites never re-index (an EMPTY site is just occupancy, unlike
pyKMC's per-atom deletion) dealloying needs no re-harvest or schema break — only dropping the G5
conservation gate. Ternary is a `uint8` non-event. It also flags (W8) the absence of a super-basin
layer for low-barrier flicker — an honest scope boundary.

**Strongest transplantable ideas:** (1) the **cache-aware substrate** — tiled/layer-blocked site
ids, SoA, arithmetic-neighbour scale switch, memory budgets — this is what turns a correct O(1)/step
design into one that actually hits 10⁶ steps in seconds and should be the physical layer under
whichever identity model wins; (2) the **I5 full-rebuild invariant** as a routine (not just debug)
oracle for the incremental path; (3) **Erlebacher-rate-as-a-BKL-class** for the dissolution extension.
**Fatal flaws:** none.

---

## Comparative summary and ranking

| Design | Fidelity /30 | Runtime /20 | Classification /20 | Implementability /15 | Extensibility /15 | **Total** |
|---|---|---|---|---|---|---|
| **pattern** | 26.5 | 18 | 18 | 12.5 | 13 | **88.0** |
| **symmetry** | 25.5 | 16.5 | 17 | 12.5 | 12.5 | **84.0** |
| **descriptor** | 24 | 17 | 16 | 13.5 | 13 | **83.5** |
| **performance** | 22.5 | 19 | 13.5 | 13 | 14 | **82.0** |

**Ranking: pattern > symmetry > descriptor > performance.**

The field is genuinely tight because all four are correct, spec-complete, and free of fatal flaws;
the ordering is decided on the two axes that carry half the rubric weight (fidelity + classification).

- **`pattern` wins** because its data-driven SPLIT_CHECK is the single mechanism that most directly
  attacks both high-weight axes at once — it keeps class rates honest as the catalogue grows (fidelity)
  and adapts context granularity from the barrier evidence itself (classification robustness) — while
  staying fully competitive on runtime, implementability, and extensibility, and it is the most honest
  about the shared detailed-balance limitation.
- **`symmetry` is second**: it invests in the highest-weighted axis exactly where the rubric rewards
  it — the saddle token and the D₄ₕ thin-slab argument are the most physically faithful choices in the
  field — but it carries one unacknowledged correctness gap (bulk vacancy-free events fall outside
  `ActiveSites`) and pays a class-count tax for its conservative default.
- **`descriptor` is third by a hair**: its "one geometry, three readouts" unification and best-in-field
  pipeline fit are real, but its strengths (implementability, extensibility) sit on the 15-point axes,
  and its identity is less adaptive than `pattern`'s with a structural gap on saddle degeneracy.
- **`performance` is fourth despite the best engineering** — its substrate and extensibility work are
  outstanding, but the rubric weights fidelity (30) and classification (20) over runtime (20) and
  extensibility (15), and performance is weakest precisely there (detailed-balance overclaim, no
  auto-split, least-novel classification). Judged on engineering polish alone it would place higher;
  judged strictly against the SPEC's weights, it places fourth.

**Cross-design synthesis for the eventual build:** the ideal engine is `performance`'s cache-aware
substrate and I5 oracle, carrying `pattern`'s core/descriptor split + SPLIT_CHECK as the identity/rate
model, extended with `symmetry`'s saddle token (and its D₄ₕ-as-opt-in) for mechanism fidelity, wired
to the pipeline via `descriptor`'s exact-column plumbing and the "one stencil, three readouts"
reverse-map/regression sharing.
