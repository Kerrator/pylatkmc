# Judge 2 — Scoring rationale (species-aware on-lattice KMC, clean-room design competition)

Panel role: judge 2 of 3. Scored strictly against SPEC.md; the rubric weights are
correctness/fidelity 30, runtime 20, classification+novelty 20, implementability/pipeline-fit 15,
extensibility 15 (total 100). I read the pyKMC input side (`event_table.py`, `symmetries.py`,
`environments/*`, `neighbors_list.py`) to ground fidelity claims. I did **not** read the workspace's
existing on-lattice engine or classification pipeline (clean-room rule honoured).

## Ground-truth facts I verified from the pyKMC source (used to judge fidelity)

- `move_atom_idx` is **subset-relative** (`np.where(neighbor_list == index_move)[0][0]`). All four
  designs read this correctly and all four correctly refuse to trust it for the mover set.
- `initial_positions = min1_positions[rcut-neighbours-of-mover]` — the row is a **local cluster**,
  subset-relative. All four correctly treat event projection as local/topological, not global.
- `sym_matrix`/`sym_perm` (from `unique_symmetries`) = **identity + operations whose applied
  displacement pattern is *distinct*** — i.e. orbit representatives / distinct orientations — computed
  by SOFI on the *relaxed local cluster*, which already carries the vacancy/surface-broken symmetry.
  It is **not** the stabilizer, and **not** the ideal-lattice point-group orbit. This matters for the
  cross-check claims (below).
- `event_id`/`id_saddle`/`id_final` are pynauty graph certificates keyed on the mover; full-colour
  adds element vertex-colouring, grey passes `types=None`. All four correctly demote `event_id` to
  provenance/pre-filter and re-derive their own lattice identity (exactly what the SPEC asks).
- `NeighborsList` builds `cKDTree(positions, boxsize=[cell00,cell11,cell22])` — an **orthorhombic-cell
  assumption** is already baked into pyKMC. Only `descriptor` explicitly cites this from the source.
- Dedup (`is_new_event`) = bucket by `event_id`, then 0.25 eV energy tolerance, then IRA/PSR saddle
  match with `matching_score_thr`. `k` is ps⁻¹ via `rate_from_prefactor`, `k0` default. All four use
  ps⁻¹ and reuse `emin_event`/`emax_event`/`energy_asymmetry` — good fidelity across the board.

The FCC integer embedding (even-parity SC sublattice, 12 nn = perms(±1,±1,0) at a/√2 = 2.489 Å,
6 2nd-nn at a, 24 3rd-nn = perms(±2,±1,±1) at a√6/2, (100) surface coordination 8) is **correct in all
four**. This substrate is not a differentiator.

---

## Design "descriptor"

### Correctness & fidelity — 26/30
Strongest fidelity of the field. It is the only design that read the pyKMC source closely enough to
cite the orthorhombic `cKDTree(boxsize=diag(cell))` assumption, the exact `event_table.py` columns,
the 0.25 eV `is_new_event` tolerance, `rate_from_prefactor`, and to reuse `emin_event`/`emax_event`.
Its signature symmetry decision is the most correct treatment of the SPEC's explicitly-named "heart":
**encode vacuum as an ordinary species `V`, always canonicalize under the full O_h (48), and let the
surface subgroup fall out of the decoration automatically.** I checked this on its own surface-vacancy
example: at a top-layer vacancy the four upward nn are `V`, so exactly the 8 O_h ops that keep the
`+z` hemisphere as `+z` preserve the decoration → C₄ᵥ emerges with zero hand-coding, and the
subsurface *continuum* of depths is handled automatically (no binary depth switch, no "site symmetry
is between O_h and C₄ᵥ" caveat that pattern/performance must carry). Critically, for a genuinely
bulk-like fully-occupied stencil it merges the in-plane and inter-layer ⟨110⟩ hops — which is
**correct** for barrier fidelity (identical local environment ⇒ identical barrier), and is precisely
where `symmetry`'s D₄ₕ default over-splits. Mover detection is by site-change (not `move_atom_idx`);
the vacancy-free 3-site ring example (m1=(0,0,0), m2=(1,1,0), m3=(1,0,1) — I verified these are mutual
1NN) is a harder and more honest example than the others' vacancy-mediated rings. Minor deductions:
the φ feature map is lossy (self-disclosed); the "V above surface" decoration trick depends on the
site box enumerating above-surface sites as `V`, which the doc implies but does not nail down as
crisply as performance/symmetry's explicit pad layers.

### Runtime matching cost — 17/20
Solid and credible: O(m·S + log E) per step, worked op-counts (~180 ops/step → ~2·10⁸ for 10⁶ steps →
seconds–minutes), int8 grid (0.1–1 MB at 10⁵–10⁶ sites), Fenwick/segment-tree selection, incremental
dirty-ball update, and an MPI domain-decomposition scale-out sketch. Honestly flags that the
heterogeneity clause makes the *initial build* O(N·S) for a concentrated alloy. It does not reach
performance's cache-layout depth (no tiled ordering, no nn-table-vs-arithmetic crossover analysis),
hence 17 not 19.

### Classification robustness + novelty — 18/20
Tied for best. The "one descriptor, three readouts" thesis genuinely unifies the exact identity (κ),
the fallback feature space (φ), and the invertible reverse geometry into one object, so "near miss" is
literally a short hop in the same descriptor space the identity lives in — the cleanest answer in the
field to SPEC decision 4. Novelty detection is a clean hash test (κ present/absent) with the
many-to-one `event_id → class_id` map logged. Family-based fallback (discrete move-set family selects
the regressor, continuous φ is its input) is well-posed. `Ea_std` doubles as the identity-resolution
diagnostic. Only shortfall vs `pattern`: the R_env growth is diagnostic/audited, not automatic.

### Implementability & pipeline fit — 13/15
Best in field. Names the exact reference-table columns, reuses pyKMC thresholds so gate verdicts match
what pyKMC already accepted, uses the `config.control.reference_table` + `initial_config` restart
contract, and keeps new dependencies modest (a fixed 48-element integer group, a scipy KD-tree already
in pyKMC, optional sklearn ridge/GP; no nauty on the lattice side).

### Extensibility — 13/15
`V`-as-species makes dissolution representable with zero schema change (drop the conservation assert,
add a reservoir counter); ternary is a trivial alphabet extension; file-based handoffs make the
closed-loop driver drop-in. Slightly behind performance only because performance spells out the
Erlebacher dissolution-rate class more concretely.

**Total: 87/100.**

---

## Design "performance"

### Correctness & fidelity — 25/30
Very strong. Correct substrate and correct mover-by-site-change detection. Its detailed-balance
treatment is the most physically grounded: because forward and backward barriers come from the *same
saddle*, `Ea_fwd − Ea_bwd = ΔE`, so `k_f/k_b = exp(−ΔE/kBT)` follows from the pairing — a cleaner
argument than the others'. (One caveat it under-states: under *class-mean* barrier averaging this holds
only approximately, which is exactly what its G2 gate `|Ea_fwd − Ea_bwd − ΔE| ≤ dE_tol` is there to
catch; `pattern`'s W5 is more honest that averaged barriers can drift equilibrium.) Handles
vacancy-free events (F13: anchor on least-abundant occupied species; equiatomic degrades to O(N/2) with
a spatial-index fallback, honestly flagged). Symmetry is the binary depth-based O_h/C₄ᵥ switch — correct
and conservatively biased to C₄ᵥ near the surface, but less principled than descriptor's automatic
decoration (self-disclosed W4/F11).

### Runtime matching cost — 19/20
Best in field — this is the design's whole thesis and it is executed most concretely. Struct-of-arrays
uint8 occupancy (1 MB at 10⁶, 100 MB at 10⁸), layer-blocked/tiled site ordering so a site + its 12-star
touch a handful of cache lines, an explicit nn12-table-vs-arithmetic-neighbour scale switch at ~10⁷
sites (48 MB vs 4.8 GB reasoning is correct), O(1) swap-remove via `site_pos_in_list` back-pointers, a
`supported_by` dirty index, grouped BKL with a per-class-constant rate so the rate vector factorizes,
and an I5 periodic full-rebuild oracle. It is also the only design to name the KMC-efficiency risk of
low-barrier flicker (no super-basin acceleration, W8) — a real limitation the others ignore.

### Classification robustness + novelty — 16/20
Correct and complete but the least innovative on this axis (it is runtime-first). Canonical key under
depth-appropriate O_h/C₄ᵥ, coloring mode folded into the key, novelty by authoritative-key lookup with
`event_id` as a warm-cache pre-filter. Its example B (Cr-leads/Ni-trails concerted surface double-step,
C₄ᵥ, detailed-balance pair) exercises every hard requirement correctly. Deduction: fixed R_ctx with only
class-growth *monitoring* — no automatic granularity adaptation (pattern) and no automatic
symmetry-from-decoration (descriptor).

### Implementability & pipeline fit — 12/15
Strong: reuses `emin_event`/`emax_event`, the restart contract, JSONL audit queue, file handoffs;
concrete typed schemas. A hair behind descriptor only because it is slightly less source-specific about
which pyKMC columns/thresholds it consumes.

### Extensibility — 14/15
Best dealloying story: sites never re-index (an EMPTY site is just occupancy, unlike pyKMC's per-atom
deletion), so enabling dissolution = drop G5 + grow `species_sites[EMPTY]`, and the Erlebacher
bond-counting rate `k = ν_d·exp((φ − n·E_b)/kBT)` drops in as a coordination-dependent class competing
in the same grouped BKL vector. Ternary trivial; closed-loop file-based.

**Total: 86/100.**

---

## Design "pattern"

### Correctness & fidelity — 24/30
Strong. Correct substrate and mover-by-site-change detection; thorough on failure modes, provenance
and gates. Its distinctive fidelity asset is the **core/descriptor split with data-driven SPLIT_CHECK**:
identity starts minimal (moved sites + 1st shell) and a wider descriptor shell is promoted into identity
**only when the measured intra-class barrier spread demands it** — the best-automated answer to the
context-size bias/variance problem that every design names as central. Two deductions. (1) The symmetry
regime is the binary depth-based O_h/C₄ᵥ (honest W4), less principled than descriptor's decoration.
(2) A genuine fidelity over-claim: it asserts the bulk vacancy hop compiles to "12 distinct oriented
patterns... matching the sym_perm count." I checked `unique_symmetries` — `sym_perm` is computed by
SOFI on the *relaxed local cluster that already contains the vacancy*, whose symmetry is far below
lattice O_h, so its orbit count is small, **not** 12. The idea that sym_perm cross-checks orientation
count is roughly right; the specific numeric identity is wrong.

### Runtime matching cost — 17/20
Strong and complete: rarest-predicate anchoring (enumeration scales with defects), per-site process
lists, group-BKL O(log C) selection with O(1) instance turnover, incremental invalidation over a fixed
pattern-support ball, a `screen_key` pre-screen, and a periodic self-heal checksum. Complexity table is
sound and N-independent per step. Less concrete than performance on memory layout/cache; the
fallback-micro-group proliferation (W8) is a self-noted runtime risk.

### Classification robustness + novelty — 18/20
Tied for best. The auto-split is the single most valuable robustness mechanism in the competition:
classes neither fragment gratuitously nor collapse distinct physics, and the split is driven by the
harvested barriers themselves. The reconciliation story with pyKMC's graph hash (finer where the
surface breaks symmetry, coarser where the bulk restores it) is exactly right. GP-variance ranking of
flagged sites for exploration is a nice touch. Deduction: SPLIT_CHECK is under-specified — "smallest
descriptor-shell extension that separates the outlier" leaves the search, tie-breaking, and class_id
stability under repeated re-keying unaddressed, so it carries real implementation risk.

### Implementability & pipeline fit — 12/15
Strong: reuses `emin_event`/`emax_event`/`backward_emin_event`, mirrors `energy_asymmetry`, file-based
audit directory + decision log, deterministic reverse map. Comparable to performance; behind descriptor
on source-specificity.

### Extensibility — 13/15
`DeltaSite{before,after}` + `delta_atoms` hook admits `X→EMPTY`; matching/canonicalization/BKL unchanged
for dissolution; ternary via alphabet growth; closed-loop via file artifacts. Solid, on par with
descriptor.

**Total: 84/100.**

---

## Design "symmetry"

### Correctness & fidelity — 22/30
Rigorous and the most physically careful *argument* in the field, but with two real structural gaps.
Strengths: it is the only design to derive *why* a slab's group is reduced — body-diagonal C₃ and
C₄x/C₄y rotations map a (001) layer onto a vertical plane and are therefore not slab symmetries — and it
correctly separates surface C₄ᵥ (z-sign fixed into the bulk) from interior D₄ₕ, with a provably
collision-free canonical key (proof sketch included) and an `r_id ≥ rcut` invariant guaranteeing it is
never coarser than pyKMC's own dedup (never a wrong merge). Deductions. (1) **D₄ₕ as the bulk default
over-splits genuinely-bulk-like sites**: for a fully-occupied stencil that does not reach a surface, the
in-plane and inter-layer ⟨110⟩ hops have identical local environments and identical barriers, so
splitting them (self-admitted "conservative bias") wastes harvest and dilutes statistics — descriptor's
decorated-O_h gets this case right automatically. (2) A more serious gap: **ActiveSites = "adjacent to
any EMPTY site or on the surface skin"** with the explicit claim that "a fully-coordinated bulk site
with all-occupied neighbours hosts no hop." That is false for vacancy-free concerted events (ring
rotations, direct antisite exchange) — exactly the "absent from standard catalogues" mechanisms the
SPEC's mission targets. Such a harvested class would be created but never matched → silent zero flux,
violating SPEC decision 4. descriptor (heterogeneity clause) and performance (least-abundant anchor)
both cover this case explicitly; symmetry does not. Also a fidelity slip: it calls `sym_matrix/sym_perm`
"the displacement-preserving symmetries" that "must be a subset of my Stab_G(ev)" — but
`unique_symmetries` returns displacement-*distinct* operations (orbit representatives), so the
relationship is inverted.

### Runtime matching cost — 17/20
Strong: a `TrigIndex` LocalSig prefilter shortlists candidate class-orientations so per-step work is
N-independent, `TouchIndex` for O(1) instance removal, Fenwick selection, bounded dirty region, a
`STRICT_CHECK` rebuild oracle, and an honest note that `|ActiveSites| → O(N)` in the porous
late-dealloying limit. Comparable to pattern; behind performance on concreteness. (The ActiveSites
definition that helps runtime is the same one that creates the correctness gap above.)

### Classification robustness + novelty — 17/20
Strong. Provably collision-free keys, the `r_id ≥ rcut` never-wrong-merge invariant, a depth signature
that keeps top-layer/step/subsurface events distinct, and — uniquely in the field — a **saddle
mechanism token** that separates two events with identical endpoints but different paths (bridge vs
hollow), with the fragmentation risk controlled by coarse quantization + a barrier-variance escalation.
That token is a genuine novelty addressing a real physics subtlety. Held back by the fixed global `r_id`
(diagnostic-only growth, no auto-split like pattern) and the D₄ₕ over-split.

### Implementability & pipeline fit — 11/15
Good — reuses pyKMC utilities (`event_movers`, `matching_thr`, `rate_from_prefactor`) and the restart
contract, file-based audit. Pulled down because the ActiveSites gap is a *fit* problem for the dealloying
mission (it can silently drop harvested vacancy-free classes), and dissolution is explicitly "schema-
ready, not loop-ready."

### Extensibility — 12/15
`count_delta` schema hook is present and the canonical machinery handles deletion, but it is the most
explicit that the dissolution loop (BKL competition, mass balance, Erlebacher rates) is stubbed (W10).
Ternary and closed-loop are fine. Slightly behind the others on the dissolution concreteness the SPEC
foregrounds.

**Total: 79/100.**

---

## Cross-cutting notes

**Strongest transplantable ideas (regardless of who wins):**
- `descriptor`: vacuum-as-species `V` + always-O_h decoration (surface subgroup and subsurface
  continuum emerge automatically, no depth parameter); the single stencil object serving as exact
  identity, continuous fallback feature, and invertible reverse geometry.
- `pattern`: data-driven SPLIT_CHECK (promote a wider identity shell only when harvested barriers prove
  it must) — the best automated answer to the context-size problem; core/descriptor split.
- `symmetry`: the slab-symmetry derivation (D₄ₕ/C₄ᵥ, why body-diagonal ops are excluded); the saddle
  mechanism token; the `r_id ≥ rcut` never-wrong-merge invariant.
- `performance`: cache-aware SoA/tiled layout with the nn-table-vs-arithmetic scale switch; grouped BKL
  with per-class-constant rates; the concrete Erlebacher dissolution-as-a-class dealloying extension.

**No design has a truly fatal flaw.** The most significant concerns are: symmetry's ActiveSites gap
(silent zero flux for bulk vacancy-free concerted events) and its D₄ₕ over-split; pattern's
under-specified SPLIT_CHECK and the sym_perm=12 over-claim; descriptor's lossy φ (fallback only) and the
lightly-specified above-surface `V` enumeration; performance's slightly overstated
detailed-balance-"by-construction" under class-mean averaging and its comparatively conventional
classification story.

**Ranking:** descriptor (87) > performance (86) > pattern (84) > symmetry (79). The top three are within
three points — descriptor leads the physics-side axes (fidelity + the SPEC's "heart", class identity),
performance leads the engineering-side axes (runtime + extensibility), and pattern owns the single best
classification mechanism. symmetry is a clear notch back on two real correctness concerns despite being
the most rigorous in its symmetry analysis.
