# Design "descriptor": a regression-first on-lattice KMC engine for harvested FCC dealloying events

**Design name:** `descriptor`
**Angle:** the local-environment *feature vector* is the primary object. A single decorated-stencil
descriptor does triple duty — it (a) is the exact class identity, (b) is inverted to hand ideal-site
geometry back to pyKMC, and (c) supplies the feature space for the fallback rate regression. Lookup
and interpolation are therefore evaluated over **one geometry**: exact-match classes are cells of a
fine partition of descriptor space; the fallback is a smooth surface fitted over the coarse features
read off that same partition. Nothing about a "near miss" is ad hoc — it is literally a short hop in
descriptor space.

---

## 0. Orientation: what pyKMC hands us, and the one decision that drives everything

From `event_table.py` (reference-table schema) each discovered event arrives as a **local cluster**
(the mover's `rcut` neighbourhood, subset-relative indexing):

| field | meaning | we use it for |
|---|---|---|
| `initial_positions`, `final_positions`, `saddle_positions` | relaxed Å coords of the cluster (min1/min2/saddle) | projection, move-set detection, snap gate |
| `initial_types` | per-atom element symbols of the cluster (full-colour) or `None` (grey) | species decoration of the descriptor |
| `energy_barrier`, `k`, `k_prefactor`, `nu0` | forward Ea [eV], rate & prefactor [ps⁻¹], HTST ν₀ [ps⁻¹] | class rate aggregate + regression target |
| `move_atom_idx` | subset-relative index of the *nominal* mover | seed only — **not trusted** for the move-set |
| `sym_matrix`, `sym_perm` | point-group ops + perms IRA found | cross-check against our O_h orbit |
| `idx_backward` | row index of the paired reverse event | forward/backward class linking |
| `event_id`, `id_saddle`, `id_final` | pynauty graph-certificate hashes | **provenance + cheap pre-filter only** |
| `dra` | mover initial→saddle displacement norm [Å] | mover cross-check |

**The driving decision.** pyKMC identifies environments with a *one-way* pynauty graph certificate
(`environments/graph_nauty.py`) or coarse CNA/coordination labels. A hash is perfect for
"same/different" but it is (i) not invertible — you cannot rebuild coordinates from it, yet the loop
*requires* us to hand ideal-site coordinates back to pyKMC (SPEC component 7); and (ii) it has no
natural notion of "close" — yet the fallback (SPEC decision 4) needs exactly that. On a **fixed
lattice** we can do strictly better: geometric adjacency *is* the graph, so an ordered, decorated
**occupancy stencil** on the FCC integer lattice carries everything the certificate carries **plus**
positions, is trivially invertible, and embeds continuously. So this design re-derives identity from
a lattice stencil and keeps pyKMC's `event_id` only as provenance and a pre-filter bucket. Every one
of the seven components below is a consequence of that single choice.

### 0.1 The FCC integer lattice (exact, hashable backbone)

Fix a global reference frame `(a, R, t)` (Section 1). Represent every site by an **integer triple**
`m = (h,k,l) ∈ ℤ³` with the parity constraint `h+k+l ≡ 0 (mod 2)`; its ideal Cartesian position in
the frame is `x(m) = t + R · (a/2) · m`. (Verified numerically for a = 3.52 Å:)

```
shell   integer offsets                              count   distance
1NN     perms of (±1,±1,0)                             12     2.489 Å   (= a/√2)
2NN     perms of (±2,0,0)                               6     3.520 Å   (= a)
3NN     perms of (±2,±1,±1)                            24     4.311 Å   (= a√6/2)
```

The **site point group** is the octahedral group **O_h = 48** operations, represented *exactly* as
the 48 signed 3×3 permutation matrices (3! axis permutations × 2³ sign flips). Each preserves the
even-parity sublattice and permutes each shell within itself. This finite, exact group replaces
nauty for our identity work and is the engine of canonicalization.

Species alphabet `Σ = {V=0, Ni=1, Cr=2, Fe=3}` (extensible; `V` = "vacant/no atom", reserved 0).
**There is no separate "vacuum" symbol** — a site above a free surface is simply `V`. Surface vs
bulk is *emergent* from how many stencil neighbours are occupied, exactly as pyKMC treats it
("coordination/surface are emergent from occupied-neighbour counts"). This one choice makes surface
symmetry reduction fall out automatically (Section 3.2).

### 0.2 The one descriptor, three readouts

Around any site `s` define the **stencil** `𝒩 = [δ₀=(0,0,0), δ₁ … δ_S]` — a *fixed ordered* list of
integer offsets out to `R_env` (default 3 shells ⇒ `S = 42` offsets + centre = 43 slots; `R_env`
tied to pyKMC's `rcut` so we see the same neighbourhood the harvest saw).

```
STENCIL OCCUPANCY   o(s) := [ occ(s+δ₀), occ(s+δ₁), … occ(s+δ_S) ] ∈ Σ^(S+1)     ── discrete, exact
FEATURE MAP         φ(s) := Φ(o(s)) ∈ ℝ^d                                          ── coarse, continuous
CANONICAL KEY       κ(s) := canon(o(s)) under O_h                                  ── identity hash
```

`Φ` is a *fixed degree-≤2 polynomial feature map* of the one-hot encoding of `o(s)` (Section 5.2):
per-shell per-species counts (linear terms) and first-neighbour bond counts `n_XY` (bilinear terms —
the classic broken-bond variables of Erlebacher dealloying kinetics). Because `φ`, `κ`, and `o` are
all deterministic functions of the *same* stencil object, "exact class" (equal `κ`) and "near miss"
(small `‖Δφ‖`) live in one geometry. That is the thesis.

```mermaid
flowchart LR
  G["occupancy grid o:Site→Σ"] -->|read stencil| O["stencil o(s) ∈ Σ^43"]
  O -->|canon under O_h| K["κ  (exact identity)"]
  O -->|Φ  fixed feature map| F["φ ∈ ℝ^d (regression input)"]
  O -->|x(m)=t+R·a/2·m| X["ideal coords (reverse map to pyKMC)"]
  K --> L{"κ in catalog?"}
  L -->|yes| R1["exact rate  ν₀·e^(−Ea/kT)"]
  L -->|no| R2["fallback  Ea=f(φ), flag + σ"]
```

---

## 1. Forward configuration projection (off-lattice snapshot → occupancy grid)

**Input:** full-cell snapshot `(positions N×3 Å, types, cell 3×3, pbc)`.
**Output:** `OccupancyGrid` (dense `int8` array over a bounded site box) + `ProjectionReport`.

### 1.1 Establish / refresh the global FCC frame `(a, R, t)`

The frame is fitted **once** at loop start and **refreshed each cycle** (drift/thermal expansion):

```
fit_frame(positions, types, cell, prev_frame=None):
  1. anchors = atoms with coordination(rnei) ≥ Z_bulk_thr           # deep bulk, least relaxed
                and per-atom deviation small (if prev_frame known)
  2. a_hat  = median(1NN distance over anchors) · √2               # lattice constant
             (or hold a fixed from config; refresh only if |Δa|/a > tol_a)
  3. (R,t)  = robust rigid fit (Kabsch + RANSAC) mapping anchor
             relaxed coords → nearest ideal FCC sites of a_hat      # rejects surface/defect outliers
  4. in-plane origin fixed to the lattice site nearest the box origin (PBC ⇒ t defined mod lattice)
  5. return Frame(a_hat, R, t, pbc, version = hash(a_hat,R,t,cycle))
```

RANSAC is essential: surface atoms deviate most (SPEC), so a plain least-squares fit would be dragged
by them. We fit on the crystalline core and let the surface snap with a looser tolerance (1.3).
Slabs are non-periodic in `z`; `R` is pinned so the surface normal maps to the frame `+z` axis (the
`(100)` planes become `l = const`). Note the inherited orthorhombic-cell assumption from
`neighbors_list.py` (`cKDTree(..., boxsize=diag(cell))`) — we assert the cell is diagonal and warn
otherwise.

### 1.2 Snap policy

FCC Voronoi inradius `r_in = a/(2√2) ≈ 1.245 Å`. Default snap tolerance `τ_snap = 0.5·r_in ≈ 0.62 Å`,
with a **coordination-graded relaxation**: a low-coordination (surface) atom is allowed
`τ_snap^surf = 0.75·r_in ≈ 0.93 Å` because it relaxes outward more. For each atom `i`:

```
u_i  = R⁻¹ (r_i − t)                       # frame coordinates
m*   = round_to_FCC(u_i)                   # nearest even-parity integer triple (2 candidates, pick min ‖·‖)
ρ_i  = ‖u_i − (a/2)·m*‖                     # snap residual [Å]
if ρ_i < τ_snap(coord_i):  occ[m*] = type_i ;  record ρ_i
else:                      mark i UNMAPPABLE(reason="too_far", ρ_i)
```

`round_to_FCC`: round `2·u_i/a` to nearest integers, then if parity odd, flip the single coordinate
whose rounding residual is largest — gives the nearest parity-even site in O(1).

**Collisions.** If two atoms claim the same site, keep the smaller `ρ`; the loser is
`UNMAPPABLE(reason="collision")`. A collision signals a wrong frame or a genuine interstitial.

### 1.3 Unmappable report and cycle policy

```
ProjectionReport {
  cycle:int; frame_version:hash; n_atoms:int; n_mapped:int; n_unmappable:int;
  max_residual:float; mean_residual:float;
  unmappable: list[{atom_idx, type, pos[3], nearest_m[3], residual, reason}];
  accepted: bool
}
```

Threshold `f_max` on the **fraction** unmappable (default: `max(1, 0.005·N)` atoms). In v1 (10²–10³
atoms, 1–2 vacancies) the expected count is **0**; any unmappable atom is a red flag
(interstitial / amorphisation / frame drift). Policy when `n_unmappable > f_max`:

1. re-fit the frame once (drift may have shifted `t`); re-project;
2. if still failing → **reject the cycle**: the on-lattice engine does *not* advance from this
   snapshot. The driver instead (a) asks pyKMC to relax further, or (b) records the offending atoms
   as a local defect region for a future local-frame extension. Rejecting is correct: a projection we
   cannot trust must never silently drop atoms or invent flux.

`OccupancyGrid` also stores the **residual field** `ρ(m)` for occupied sites (a per-cycle quality
map, reused by the reverse map and gates).

---

## 2. Event projection (reference-table row → on-lattice event)

**Input:** one reference row. **Output:** `ProjectedEvent` (a *move-set* + *context descriptor*).

The row is in its **own local frame** (relaxed cluster coords, no absolute placement), so event
projection is about *topology*, not placement.

```
project_event(row, a):
  # 2.1 local frame from the initial cluster's crystalline atoms
  (R_loc,t_loc) = robust_rigid_fit(row.initial_positions[core], a)        # core = high-coord atoms
  m0[j] = round_to_FCC( R_loc⁻¹(row.initial_positions[j]-t_loc) )         # initial site of each cluster atom j
  ρ0[j] = snap residual

  # 2.2 SAME frame for the final cluster, pinned by the NON-movers
  #     (peripheral atoms that barely moved define the shared frame; avoids whole-cluster ambiguity)
  fixed = { j : ‖final[j]-initial[j]‖ < ½·d_1NN }
  (R_loc,t_loc) refined on `fixed` only
  m1[j] = round_to_FCC( R_loc⁻¹(row.final_positions[j]-t_loc) )

  # 2.3 TRUE move-set from per-atom site change (NOT move_atom_idx)
  move = [ (m0[j], row.initial_types[j], m1[j]) for j where m0[j] != m1[j] ]
  #   → occupancy deltas: at m0[j] the species leaves (→V unless another atom lands there);
  #     at m1[j] the species arrives. Assembled per touched site:
  Δ = assemble_site_deltas(move)      # dict: touched site → (before_species, after_species)

  # cross-check: every atom with ‖final-initial‖ > ½·d_1NN MUST appear in `move`, else audit
  assert movers_by_displacement ⊆ touched_atoms         # SPEC: detect the true set of site changes

  # 2.4 context = decorated stencil footprint over ALL touched sites
  context = { m : occ(m) for m within R_env of any touched site }   # from the cluster's snapped occ
  truncated = (cluster does not cover full R_env footprint)         # → gate-5 marker

  return ProjectedEvent(Δ, context, Ea=row.energy_barrier, nu0=row.nu0,
                        k=row.k, k_prefactor=row.k_prefactor,
                        snap_residual_max=max(ρ0∪ρ1), truncated=truncated,
                        source=Provenance(row), coloring_mode)
```

`assemble_site_deltas` handles the general (concerted) case: a site may be simultaneously vacated by
one atom and filled by another (2-site swap, ring), or vacated with no filler (dissolution hook —
Section 6.4 / 8). The move-set is a *set of site occupancy transitions*, multi-site first-class,
exactly as SPEC component 2 requires.

---

## 3. Class identity (the heart)

**Definition.** Two projected events belong to the same **lattice event class** iff their
`(move-set, context)` pairs are equal after canonicalisation under the octahedral group O_h acting on
the *decorated* stencil (occupancies, including `V`). Identity is then exact hash-equality on a
canonical key — O(1) lookup.

### 3.1 Canonicalisation algorithm

```
canon(Δ, context):               # Δ: touched sites w/ (before,after); context: {site: species}
  best = None ; best_g = None
  for g in O_h:                                   # 48 exact signed-permutation matrices
     Δg   = { g·m : (before,after) }              # apply g to positions (species are scalars)
     Cg   = { g·m : species }
     o    = min touched image under g             # translate so lex-min touched site → origin
     s    = serialize( sorted[(g·m − o, before, after) for Δ]           # move-set block
                        ++ sorted[(g·m − o, species) for Cg] )          # context block
     if best is None or s < best: best, best_g = s, g
  return key=hash(best), canonical_form=best, g_star=best_g            # g_star = canonical orientation
```

Cost: `48 · (|Δ| + |context|) ≈ 48·45 ≈ 2·10³` integer ops per event — negligible. The key is
**translation-invariant** (step "translate to lex-min") and **O_h-invariant** (min over `g`).

### 3.2 Why one group (O_h) gives the *correct* symmetry everywhere — automatically

This is the design's signature move. We always canonicalise under the *full* bulk O_h, but over a
stencil that **encodes vacancy/vacuum sites as `V`**. Consequence:

- **Bulk event:** all shells occupied; the 48 ops that map the (undecorated) geometry to itself all
  preserve the decoration ⇒ full 48-fold reduction. Correct.
- **(100) surface event:** the stencil has `V` on the vacuum side (e.g. the four 1NN offsets with
  `l=+1` above a top layer). An O_h op that rotates the vacuum side into the bulk produces a
  *different* decorated stencil (V's now point inward) ⇒ it does **not** map the event to itself and
  is automatically excluded. What survives is exactly the surface-preserving subgroup — `C₄ᵥ` (8 ops)
  for a `(100)` normal — *discovered from the data, not hand-coded*. A stepped/edge/defect site gets
  its own reduced effective group the same way.
- **`z→−z` slab mirror:** admitted only when the top- and bottom-surface decorations genuinely match
  (symmetric slab); otherwise the two decorated stencils differ and the mirror is correctly excluded.

So the "bulk site group vs reduced surface symmetry — handle both" requirement (SPEC component 3) is
met by a *single* mechanism: decorate with `V`, canonicalise under one fixed group. No case analysis,
no per-site group tables.

### 3.3 Species decoration and coloring mode

`coloring_mode ∈ {grey, full}` (mirrors pyKMC's `atom_coloring_mode`). `full` (default for
dealloying): `{Ni,Cr,Fe}` are distinct in `κ` ⇒ a Cr hop ≠ Ni hop. `grey`: collapse `{Ni,Cr,Fe}→A`,
keep `V` distinct ⇒ identity by geometry+vacancy only. Implemented as a fixed relabel of the stencil
before `canon`. The catalog can hold both keys (full for rates; grey as a coarse bucket / pre-filter).

### 3.4 Size/shape of the context is part of identity — and self-diagnosing

`R_env` (= pyKMC `rcut`, default 3 shells) is fixed and *part of the class key*. Justification: the
barrier must be a function of the stencil, i.e. atoms beyond `R_env` must not materially move the
barrier. The design **verifies this from its own data**: the spread of harvested barriers within a
class, `Ea_std`, is the direct diagnostic. `Ea_std` above tolerance ⇒ `R_env` too small for that
class ⇒ curation action "grow `R_env` and re-key" (Section 7). This is the point where identity and
regression meet: intra-class barrier variance is simultaneously an identity-resolution signal and the
irreducible noise floor of the fallback regression.

### 3.5 Why the decorated stencil beats the pynauty certificate (justification, per SPEC)

1. **Invertible.** `κ` ⇒ canonical form ⇒ ideal coords `x(m)` — required for the reverse leg
   (component 7). A certificate is one-way.
2. **Continuously embeddable.** `φ = Φ(o)` is defined on the same object ⇒ the fallback has a natural
   metric. A certificate has none.
3. **Strictly more information at no cost.** On a fixed lattice adjacency = geometry, so the stencil
   contains the certificate's graph *and* positions; two geometrically distinct environments that are
   graph-isomorphic (possible on a decorated lattice) are never conflated.
4. **Cheaper, transparent symmetry.** 48 fixed integer matrices vs a general graph-automorphism
   engine.

We still record `event_id` per contributing row (provenance) and use it as a cheap first-pass bucket
key, so we inherit pyKMC's dedup for free and only pay `canon` on survivors.

---

## 4. Runtime matching (occupancy grid → incremental KMC rate list)

**Goal:** enumerate every executable instance (all classes, orientations, sites), build the BKL rate
list, and update it **incrementally** after each event. Target ≥10⁶ steps on 10³ sites in minutes;
10⁵–10⁶ sites feasible on a node.

### 4.1 Active sites (locality)

Bulk perfect-crystal atoms host no events (no move-set precondition is met). Maintain the
**active-site set**

```
A = { s : occ(s)=V }                       # vacancies (and their R_env neighbourhoods)
  ∪ { s : coordination(s) < Z_bulk }        # surface / under-coordinated
  ∪ { s : stencil not single-species bulk }  # species heterogeneity (vacancy-FREE events, e.g. ring)
```

expanded by `R_env` (any site whose stencil overlaps the above). For v1 (1–2 vacancies, small slab)
`|A| ≈ surface + defect shells ≈ 10²–10³`. For a *concentrated* alloy the third clause can make
`|A| ≈ N` — accepted honestly: the initial build is then O(N·S) (one-time), but the **per-step** cost
stays bounded (4.4).

### 4.2 Class index (trigger buckets)

Precompute per class, at ingest time, its **oriented placements**: the orbit of `(Δ, context)` under
O_h reduced by the context stabiliser (`orbit_size ≤ 48` distinct oriented instances), each stored as

```
Placement { g:int;                                  # O_h index
            anchor_offset:int[3];                    # where the class anchor sits relative to a trigger site
            preconds: list[(offset[3], required_species)];   # context predicates to test
            move_abs: list[(offset[3], before, after)] }     # the occupancy transition, oriented
```

Index placements in a hash `trigger → [ (class_id, Placement) ]`, where `trigger` is a cheap local
signature of the anchor site — `(before-species at anchor, coordination bucket)`. At runtime a site
only tests the handful of classes sharing its trigger, not the whole catalog.

### 4.3 Build the rate list

```
build_rate_list(grid):
  for s in A:
     trig = trigger(s, grid)
     for (class_id, P) in class_index[trig]:
        if all( grid[s + off] == req for (off,req) in P.preconds ):     # context matches
           sites = [ s + off for (off,·,·) in P.move_abs ]
           k = rate(class_id, φ(s))                                     # exact lookup or fallback (§5)
           push RateListEntry{anchor=s, class_id, g=P.g, sites, k, fallback, family_id, cell_key}
```

Selection structure: a **Fenwick (BIT) / segment tree** over entries for `O(log|entries|)` cumulative
draw, **or** a 2-level BKL (per-active-site total, then within-site) — I default to the segment tree
for simplicity and exactness. `R = Σ k`.

### 4.4 Execute + incremental update (the performance core)

```
step(grid, tree):
  ξ ~ U(0,R]; e = tree.find(ξ)               # BKL select, O(log)
  apply e.move to grid                        # O(|move|) int writes
  Δt = −ln(U(0,1])/R ; t += Δt

  dirty = ∪_{s in e.sites} { s' : ‖s'−s‖ ≤ R_env }   # only stencils that changed  (bounded, ~|move|·S)
  for s' in dirty ∩ (A ∪ new_active):
     tree.remove(old entries anchored at s')          # subtract their k from R
     recompute trigger, re-match (as in build), tree.insert(new entries)   # add k to R
  update A (a filled vacancy leaves A; a new vacancy/heterogeneity enters)
```

Because `apply` touches `|move| ≤ ~4` sites and each contaminates only its `R_env` ball, `|dirty|` is
a **constant independent of N** (`≈ |move|·S ≈ 4·43 ≈ 170` site re-reads, a few dozen entry churns).

### 4.5 Complexity

Let `N` = sites, `N_a = |A|`, `S` = stencil size (43), `E` = live rate-list entries `≈ N_a·⟨orbit⟩`,
`m` = move-set size.

| operation | cost |
|---|---|
| projection (per cycle) | `O(N)` (KD-tree snap) |
| build rate list (per cycle) | `O(N_a · S)` |
| **per KMC step** | **`O(m·S + log E)`** — *independent of N* |
| memory | `O(N)` grid (`int8`, 1 byte/site) + `O(E)` rate list |

Worked targets:
- **10³ sites, 1–2 vac:** `N_a ≈ 200–300`, `E ≈ 10³`. Per step `≈ 4·43 + 10 ≈ 180` ops ⇒ 10⁶ steps
  `≈ 2·10⁸` ops ⇒ seconds–minutes in compiled/`numpy`-vectorised inner loop. ✔
- **10⁵–10⁶ sites:** grid ≈ 0.1–1 MB (`int8`); `log E ≈ 20`; per step `≈ 200` ops ⇒ 10⁶ steps
  `≈ 2·10⁸` ops ⇒ minutes on one node. ✔
- vs naïve per-step full rescan `O(N·S·C·⟨orbit⟩)`: speed-up factor `~ N/(m·log E)` — several orders
  of magnitude at 10⁵–10⁶ sites.

**Scale-out (extensibility):** for 10⁶ sites, spatial domain decomposition with a synchronous
sublattice / null-event BKL across MPI ranks; ranks exchange only boundary `R_env` shells between
independent regions. v1 stays serial; the incremental machinery is unchanged.

---

## 5. Rate assignment

`k = ν₀ · exp(−Ea/k_BT)` — **exactly** pyKMC's `rate_from_prefactor` (ps⁻¹, `k_B` in eV/K), `Ea, ν₀`
temperature-independent, `T` from config. Two paths share the descriptor.

### 5.1 Exact-lookup path

`κ(s)` present in catalog ⇒ use the class aggregate:
`Ea = Ea_mean`, `ν₀ = geomean(ν₀ samples)` (prefactors are log-normal; if `constant` style / ν₀
absent, `ν₀ = k0`). `k = ν₀·exp(−Ea/k_BT)`. Store `Ea_std, n_samples` for diagnostics.

### 5.2 The feature map `φ` (shared with identity)

`Φ(o)` — a fixed, degree-≤2 map of the one-hot stencil `onehot(o) ∈ {0,1}^{(S+1)×|Σ|}`:

```
linear   : per-shell per-species counts   n^(r)_X = Σ_{δ∈shell r} 1[occ(δ)=X]     (r=1,2,3; X∈Σ)
           coordination Z^(1) = Σ_X≠V n^(1)_X ,  surface indicator = (12 − Z^(1))
bilinear : first-neighbour bond counts    n_XY = Σ_{(i,j)∈1NN edges} 1[occ_i=X]·1[occ_j=Y]   (Erlebacher)
categorical (from Δ, not o): mover species, target occupancy, |move|, mechanism tag (hop/swap/ring)
```

`d ≈ 30–60`. The bond-count block `n_XY` is literally the broken-bond model of dealloying barriers,
so a *linear* regressor on `φ` is already a physically-motivated bond-counting barrier model.

### 5.3 Fallback regression (near-miss, flagged)

When `κ(s)` is **absent** but the site matched a class's *geometric mechanism* (same move-set family,
different decoration / outer-shell occupancy), assign a rate from a regression **fitted per
mechanism family** `family_id` (the species-blind move-set class — the discrete descriptor selects
*which* regressor; the continuous `φ` is its input; the joint design SPEC decision 4 asks for):

```
Ea_hat, σ = regressor[family_id].predict(φ(s))
ν0_hat    = regressor[family_id].predict_nu0(φ(s))        # or family geomean ν₀ (prefactors vary less)
Ea_hat    = clip(Ea_hat, emin_event, emax_event)          # never unphysical (reuse pyKMC bounds)
k         = ν0_hat·exp(−Ea_hat/k_BT) ;  entry.fallback = True
```

- **Tier 1 (default): ridge / bond-count linear model.** `Ea = w·φ + b`, closed-form ridge with
  predictive variance `σ²(φ) = φᵀ(ΦᵀΦ+λI)⁻¹φ·s²`. Robust with few points, physically interpretable,
  no heavy dependency. Requires `n_min ≈ 8` classes in the family.
- **Tier 2 (data-rich family): GP** (RBF on `φ`) — smooth, interpolates class means, principled `σ`.
  Drop-in when a family has ≳30 classes.
- **Cold family (`< n_min`): family-mean `Ea`** with large `σ`. **Never zero flux** — even a wholly
  novel context gets a finite, bounded rate and a *hard* flag.

**Consistency diagnostic (the "one surface" check).** On harvested cells we always use exact lookup,
but we *also* evaluate the regressor there and log `|Ea_hat − Ea_mean|` — the model's own QC residual.
A GP passes through the means by construction; ridge approximates, and its residual is exactly the
bond-count model error we report.

### 5.4 Flag mechanism and refit cadence

- Every fallback entry sets `entry.fallback=True` and increments a per-`(family_id, cell_key)`
  counter with the **flux it carried** (`k`, later Σ over its selections). `cell_key` = a coarse hash
  of `φ` (rounded feature bucket) so nearby near-misses aggregate.
- High-`σ` or high-flux cells are emitted as **priority exploration targets** for the next pyKMC leg
  (Section 6.5). Flux-weighting ensures we harvest what actually matters kinetically.
- **Refit** a family's model at *cycle boundaries only* (file handoff) when its class count grew
  ≥25% or a new class landed in a high-`σ` region. A refit is cheap (10–10² points). The evolve run
  uses a **frozen** model between cycles ⇒ reproducible flux. Model is stamped with the catalog
  version.

---

## 6. Novelty & harvest round trip

### 6.1 Ingesting a pyKMC row

```
ingest(row, cycle):
  pe = project_event(row)                       # §2
  gates = run_gates(pe)                          # §7.2 ; hard failures → audit, don't admit
  κ, form, g* = canon(pe.Δ, pe.context)          # §3.1
  if κ in catalog:                               # NEW INSTANCE of known class
     C = catalog[κ]
     C.append_sample(row.energy_barrier, row.nu0, Provenance(row,cycle))
     if |row.energy_barrier − C.Ea_mean| > 0.25: flag_audit(C, "intra-class-inconsistency")   # pyKMC's own tol
  else:                                          # candidate NEW CLASS
     C = EventClass.from(pe, κ, form, g*, cycle)
     catalog[κ] = C ; new_classes_this_cycle += 1
     flag_audit(C, "new-class")                  # admitted immediately; audited post-hoc (SPEC dec.5)
  link_backward(C, row)                          # §6.3
```

Our `canon` is a *stricter, different* dedup than pyKMC's IRA: two rows IRA kept distinct (slightly
different relaxed geometry) may share one `κ` ⇒ we **merge** (fewer classes — good, and the merged
barrier spread feeds §3.4). The many-to-one `event_id → class_id` map is logged for provenance.

### 6.2 New class vs new instance

Decision is precisely "`κ` absent vs present" — a hash test. No thresholds, no PSR at match time
(PSR already happened inside pyKMC). This is far cheaper and more deterministic than re-running
registration per candidate.

### 6.3 Forward/backward pairing (microscopic reversibility bookkeeping)

The backward event is the **reverse move-set** `−Δ` with context = the occupancy *after* the forward
event (`D_final`). We compute `κ_bwd = canon(reverse(Δ), D_final)` and set
`C.backward_class_id = κ_bwd`, `C.self_reverse = (κ_bwd == κ)`.

- If the row supplied `idx_backward`, we link both directions and record `idx_backward → κ_bwd`.
- If only one direction was harvested, we **synthesise** `κ_bwd` from geometry (we have `D_final` and
  `Δ`) and insert it as a **barrier-pending** class flagged for harvest, so its `Ea` gets measured
  next leg. This guarantees pairing *closure*: every class has a reverse in the catalog (or is its
  own reverse) even mid-harvest.
- **Reversibility for free at runtime:** after executing `A` the grid holds `D_final` at the anchor,
  which by construction matches `B`'s context ⇒ the reverse hop is automatically enumerated by the
  matcher. Detailed balance is a *property of a closed catalog*, not extra runtime code. Consistency
  gate: `apply(Δ) ∘ apply(−Δ) = identity` on a test grid (Section 7.2 gate 2).

### 6.4 Occupancy-count-changing hook (kept live, unused in v1)

A move-set entry may be `(m, before=Cr, after=V)` with **no** matching `(·→Cr)` — net atom removal
(dissolution). The descriptor, `canon`, matcher, and reverse map all treat `V` as an ordinary species,
so such events are representable with **zero schema change**. v1 asserts multiset(before) =
multiset(after) (canonical, atom-conserving); flipping that assert off + adding a reservoir counter is
all a later dealloying campaign needs — no re-harvest, no schema break (SPEC decision 2).

### 6.5 Coverage report (cheap running accumulators — SPEC decision 6)

Maintained as O(1)-per-event updates during the evolve leg:

```
CoverageReport {
  cycle; n_steps; total_flux; fallback_flux;                  # two running sums
  fallback_fraction = fallback_flux/total_flux;               # ← primary convergence metric
  unharvested_cells: top-K (cell_key, family_id, count, flux) # priority targets, flux-ranked
  composition: {Species: count};                              # trivial running counts
  sro: Warren-Cowley α_XY from the n_XY bond counts we already have;   # drift monitor
  new_classes_this_cycle;                                     # convergence signal → 0 (SPEC dec.1)
}
```

**Convergence of the whole loop = `new_classes_this_cycle → 0` and `fallback_fraction → 0`.**

---

## 7. Provenance & curation hooks

### 7.1 Per-class provenance (schema in §9)

Each `EventClass` carries: source cycles, contributing rows `(cycle, idx_ref, pykmc_event_id)`,
every barrier & ν₀ sample with its cycle, aggregate `(Ea_mean, Ea_std, n, ν0_geomean)`, gate history,
`backward_class_id`, `first_seen_cycle`, `audit_status`, and `fallback_stats(times_used, flux)`.
Full auditability of "where did this rate come from".

### 7.2 Auto-gates (admit on pass; failures + first-instances → audit)

| # | gate | check | on fail |
|---|---|---|---|
| 1 | barrier bounds | `emin ≤ Ea ≤ emax`, `Ea_bwd ≥ emin`, not `asymmetric` (reuse `eventsearch` thresholds) | reject → audit |
| 2 | fwd/bwd consistency | `κ_bwd` exists (or self-reverse); `apply(Δ)∘apply(−Δ)=id`; ΔE sign consistent if energies known | audit |
| 3 | snap residual | `max ρ over event cluster < 0.6·r_in` | audit ("off-lattice / interstitial") |
| 4 | **projection round-trip** | `forward_project(reverse_map(pe)) == pe` (same `κ` *and* move-set) | audit (frame/snap ambiguity) |
| 5 | context completeness | cluster covers full `R_env` footprint | admit with `truncated` marker + flag larger-`rcut` re-harvest |

Gates 1 mirror `is_valid_new_event`; we re-check because our *aggregate* can drift as instances
accumulate. Admission is **non-blocking**: the evolve leg runs on the auto-admitted catalog; audits
refine it for the *next* cycle.

### 7.3 Audit queue interface

A file-based JSONL queue (`audit_queue.jsonl`), one record per flagged item:

```
{class_id, reason:"new-class"|"gate:N"|"intra-class-inconsistency",
 projected_event, provenance, suggested_action}
```

A human (or a later auto-policy) marks `admit | reject | split | merge | grow_R_env`. Decisions apply
at the next cycle boundary and are appended to the class's `gate_history`. `split` re-keys a
multimodal class (Section 3.4); `grow_R_env` re-projects its instances at a larger stencil.

### 7.4 Reverse map (occupancy → ideal-site atomistic config) and determinism

```
reverse_map(grid, region=None, frame):
  atoms = [ (x(m)=t+R·(a/2)·m, species) for m in (region or occupied sites) if grid[m]≠V ]
  order atoms by lexicographic m                         # deterministic, byte-stable ordering
  write config(positions, types, cell=frame-consistent box, pbc)   # ASE-readable (xyz / lammps-data)
  return config + cumulative reference_table.pickle
```

Handed to pyKMC via `config.control.reference_table` + `initial_config`; pyKMC **minimises** (relaxes
ideal→relaxed) and runs `k=20–1000` steps; the harvest is the new reference rows.

**Determinism guarantees (reproducibility of the reverse mapping):**
1. `site → position` is a pure function of `(frame, m)` — no randomness;
2. atom ordering = sorted `m` ⇒ identical grid ⇒ **byte-identical** input file;
3. the frame `(a,R,t,version)` is versioned in provenance ⇒ a rerun reproduces coordinates exactly.

**Round-trip laws (tested, Section 11):**
`project(reverse_map(grid)) == grid` (grid idempotency) and
`forward_project(reverse_map(project(event))) == project(event)` (gate 4).

---

## 8. Worked examples

### 8.1 Vacancy hop on a (100) Ni surface (2-site)

**Setup.** `(100)` slab, normal `+z`. Top layer `l=0`; sites `l>0` are vacuum (`V`). A surface
vacancy at `m_V=(0,0,0)`; an in-plane 1NN Ni at `m_Ni=(1,1,0)` (same layer, since `(1,1,0)` has
`l=0`) hops into it. pyKMC row: `initial_types` all Ni, `move_atom_idx` = the Ni, `energy_barrier`
0.62 eV, `nu0` 8.5 ps⁻¹.

**Project (§2).** Fit local frame from the cluster's sub-surface bulk. Snap: `m_Ni^0=(1,1,0)`,
`m_V^0=(0,0,0)`; final `m_Ni^1=(0,0,0)`. Move-set (atom changed site): atom leaves `(1,1,0)`, arrives
`(0,0,0)`. Site deltas:
```
Δ = { (0,0,0): V→Ni ,  (1,1,0): Ni→V }
```
Context around the touched footprint, initial state — the anchor `(0,0,0)` shell-1 (12 sites):
`l=+1` offsets `{(±1,0,1),(0,±1,1)}` = **4 × V** (vacuum above); `l=−1` `{(±1,0,−1),(0,±1,−1)}` =
**4 × Ni** (sub-surface); `l=0` `{(±1,±1,0)}` = **4 × Ni** (in-plane, one is the mover). Coordination
of the vacancy `Z^(1)=8` ⇒ a *surface* vacancy (missing the 4 vacuum neighbours).

**Classify (§3).** `canon(Δ, context)` over O_h: ops that keep the vacuum on `+z` (the `C₄ᵥ` subgroup,
8 ops) preserve the decoration; the other 40 map vacuum into the bulk ⇒ excluded automatically. The
four in-plane 1NN directions `(±1,±1,0)` are one `C₄ᵥ` orbit ⇒ `orbit_size=4`. Canonical key
`κ_A = hash(canonical form)`; store class with `Ea_mean=0.62`, `ν0=8.5`, `family_id=`
"1NN-vacancy-hop, surface". `k_A = 8.5·exp(−0.62/k_BT)`.

**Match (§4).** Grid has a surface vacancy at some `v`. `v∈A`. `trigger(v)=(before=V, coord=8)` →
class bucket contains `A`. Its 4 oriented placements each require `v+g(1,1,0)` occupied by Ni and `v`
vacant. All 4 in-plane Ni neighbours satisfy it ⇒ **4 rate-list entries**, each
`k=8.5·exp(−0.62/k_BT)`, `fallback=False`.

**Execute (§4.4).** BKL picks the hop `(1,1,0)→(0,0,0)`. Apply: `occ[(0,0,0)]=Ni`, `occ[(1,1,0)]=V`.
`dirty` = `R_env` balls around both sites. Re-match: the vacancy now sits at `(1,1,0)`; new hops
enumerated around it; `A` set updated (old site left, new vacancy neighbourhood entered). `Δt =
−ln(U)/R`. Detailed balance: the reverse hop `(0,0,0)→(1,1,0)` is automatically present because the
post-move context at `(1,1,0)` matches `A`'s backward class.

### 8.2 Three-site concerted ring (vacancy-free, full-colour) — the "not in standard catalogues" case

**Setup (bulk).** Triangle of mutual 1NN (verified): `m1=(0,0,0)` Ni, `m2=(1,1,0)` Cr,
`m3=(1,0,1)` Fe. A concerted cyclic rotation `Ni(m1)→m2, Cr(m2)→m3, Fe(m3)→m1` — pARTn finds such
multi-atom saddles; a vacancy-only lattice catalogue would miss it entirely. pyKMC row's
`move_atom_idx` names **one** atom, but `final−initial` shows **three** atoms displaced ≈ `d_1NN`.

**Project (§2).** Snap initial and final in the shared (non-mover-pinned) frame. Per-atom site
changes give three touched sites; the displacement cross-check confirms all three (SPEC's "don't
trust `move_atom_idx`"). Anchor = lex-min touched site `(0,0,0)`. Site deltas:
```
Δ = { (0,0,0): Ni→Fe ,  (1,1,0): Cr→Ni ,  (1,0,1): Fe→Cr }
```
Context: all shells occupied (bulk) — no `V` ⇒ full O_h applies. `mechanism tag = ring, |move|=3`.

**Classify (§3).** `canon` over all 48 ops; the triangle's stabiliser fixes the distinct ring
orientations; full-colour keeps `(Ni,Cr,Fe)` decoration in `κ_B`. Backward class `κ_B,bwd =
canon(reverse ring, D_final)` = the `Fe→Ni→Cr` rotation; linked via `idx_backward`. Store
`Ea_mean, ν0`; `family_id=`"3-site-ring".

**Match (§4).** This event has **no vacancy** ⇒ it is caught by the *heterogeneity* clause of `A`
(sites near Cr/Fe). At an anchor whose stencil presents a Cr at `g(1,1,0)` and an Fe at `g(1,0,1)`
with the right surroundings, each O_h orientation mapping the stored ring onto a valid
`(Ni,Cr,Fe)`-decorated triple emits an entry. Precondition = the three species present in the
required arrangement. `k_B=ν0·exp(−Ea/k_BT)`.

**Execute (§4.4).** Apply the 3-site cyclic occupancy change: `(0,0,0)=Fe, (1,1,0)=Ni, (1,0,1)=Cr`.
`dirty` = union of `R_env` balls around all three; re-match; update. If instead the *matched* context
were a near-miss (say a 2nd-shell Cr differs from any harvested ring class), `κ` is absent → the
`3-site-ring` family regressor returns `(Ea_hat, σ)`, the entry is flagged, and its `cell_key` is
logged for the next harvest leg — never zero flux.

---

## 9. Data schemas (typed)

```
Frame            { a:f64; R:f64[3,3]; t:f64[3]; pbc:bool[3]; layer_ls:i32[]?; version:u64 }
Species          = enum { V=0, Ni=1, Cr=2, Fe=3, ... }         # V reserved 0; extensible
Site             = i32[3]  (invariant: sum ≡ 0 mod 2)
OccupancyGrid    { frame:Frame; dims:i32[3]; occ:int8[*]  (dense, idx(m) bijection);
                   residual:f32[*]?;  active:set<Site> }
Stencil          { R_env:f32; offsets:i32[S+1,3]; shells:i32[S+1]; id:u32 }

Descriptor       { stencil_occ:int8[S+1]; phi:f32[d]; key:u64; coloring:enum{grey,full} }
MoveSetEntry     { delta:i32[3]; before:Species; after:Species }
MoveSet          = sorted list<MoveSetEntry>

ProjectedEvent   { anchor:Site?; move_set:MoveSet; context:Descriptor;
                   Ea:f64; nu0:f64?; k:f64; k_prefactor:f64?;
                   snap_residual_max:f32; truncated:bool; coloring:enum; source:Provenance }

EventClass       { class_id:u64; canonical_key:bytes; canonical_form:str;
                   move_set_canonical:MoveSet; context_canonical:Descriptor;
                   coloring:enum; stencil_id:u32; R_env:f32;
                   Ea_mean:f64; Ea_std:f64; n_samples:i32; nu0_geomean:f64; nu0_std:f64; k0:f64;
                   backward_class_id:u64; self_reverse:bool; orbit_size:i32; family_id:u32;
                   provenance:Provenance; audit_status:enum{auto,confirmed,rejected};
                   fallback_stats:{times_used:i64, flux:f64} }

Provenance       { source_cycles:i32[]; first_seen_cycle:i32;
                   rows: list<{cycle:i32, idx_ref:i32, pykmc_event_id:str}>;
                   Ea_samples: list<{cycle:i32, Ea:f64, nu0:f64, idx_ref:i32}>;
                   gate_history: list<{gate:str, outcome:str, cycle:i32}> }

Regressor        { family_id:u32; type:enum{mean,ridge,gp}; params:blob;
                   train:list<{phi:f32[d], Ea:f64, class_id:u64}>; catalog_version:u64;
                   predict(phi)->(Ea_hat:f64, sigma:f64); predict_nu0(phi)->f64 }

RateListEntry    { anchor:idx; class_id:u64; g:i8;  sites:idx[]; k:f64;
                   fallback:bool; family_id:u32; cell_key:u64 }        # in a Fenwick/segment tree

ProjectionReport { cycle; frame_version; n_atoms; n_mapped; n_unmappable;
                   max_residual; mean_residual; unmappable:[...]; accepted:bool }
CoverageReport   { cycle; n_steps; total_flux; fallback_flux; fallback_fraction;
                   unharvested_cells:[{cell_key,family_id,count,flux}];
                   composition:{Species:i64}; sro:{pair:f64}; new_classes_this_cycle:i32 }
```

**Catalog on disk:** a Parquet/pickle table of `EventClass` rows (keyed by `class_id`) + a JSONL
`audit_queue` + per-family `Regressor` blobs, all stamped with `catalog_version`. Cycle handoffs are
file-based (SPEC decision 1): `{catalog, regressors, occupancy_grid, coverage_report,
projection_report, priority_targets}` in, `{new reference rows, new occupancy_grid}` out.

---

## 10. Failure-mode table

| # | failure | trigger | detection | response |
|---|---|---|---|---|
| 1 | frame drift / wrong `a` | thermal expansion, box relaxation | unmappable fraction ↑; mean `ρ` trend | re-fit frame; per-cycle `a` refresh; reject cycle if persistent |
| 2 | interstitial / amorphisation | pushed geometry, radiation-like defect | site collision / `ρ>τ_snap` | mark unmappable; reject cycle or local-frame defect handling |
| 3 | concerted event > `R_env` | large collective saddle | gate 5 (context truncated) | admit with marker; flag larger-`rcut` re-harvest |
| 4 | `φ`-collision (2 stencils → 1 `φ`) | lossy feature readout | intra-family regression outlier residual | exact lookup unaffected; augment `φ` w/ directional pair counts; flag |
| 5 | `R_env` too small (multimodal class) | barrier depends on shell > `R_env` | `Ea_std` > tol (§3.4) | `grow_R_env` re-key (audit action) |
| 6 | backward class missing | one-direction harvest | pairing-closure check (§6.3) | synthesise `κ_bwd`, barrier-pending, flag harvest |
| 7 | `move_atom_idx` misses movers | concerted event | displacement vs snapped move-set mismatch (§2.3) | use displacement set; audit if inconsistent |
| 8 | surface reconstruction (genuinely off-lattice) | (100) missing-row, step bunching | many high-`ρ` surface atoms | looser `τ_snap^surf`; if exceeded → unmappable → audit; consider surface sub-frame |
| 9 | rate-list desync after execution | missed a dirtied site | periodic full-rebuild assert (debug, §11) | rebuild; fix `dirty` set; the assert is a CI gate |
| 10 | vacancy-free event missed | ring/exchange far from any vacancy | coverage shows reachable high-flux unharvested cell | heterogeneity clause in `A` (§4.1); widen `A` if needed |
| 11 | GP/ridge extrapolation nonsense | `φ` far out-of-distribution | `Ea_hat` outside `[emin,emax]`, huge `σ` | clip to bounds; hard flag; family-mean fallback |
| 12 | non-orthorhombic cell | tilted box | cell-diagonal assert fails | warn / require orthorhombic (inherited pyKMC limit) |
| 13 | prefactor spread within class | ν₀ varies order-of-magnitude | `nu0_std` large | report; consider per-decoration ν₀ regression |

---

## 11. Test plan

**Unit.**
- FCC neighbour tables: assert shells `12@2.489 / 6@3.520 / 24@4.311 Å`, parity preserved.
- O_h: exactly 48 elements, group closure & inverses; each maps each shell onto itself.
- `canon` invariance: for random `g∈O_h` and random lattice translation, `canon(g·e) == canon(e)`
  (key stable) — property test over many random events.
- `round_to_FCC` correctness incl. the parity-flip branch; snap idempotency on an ideal grid.
- `Φ` determinism and the linear/bilinear count identities (`Σ_X n^(1)_X = Z^(1)`; `n_XY` symmetric).
- move-set detection on synthetic concerted displacements (2-swap, 3-ring, 4-ring).

**Round-trip (determinism).**
- `project(reverse_map(grid)) == grid` over random valid grids (bulk, surface, vacancy).
- gate-4: `forward_project(reverse_map(project(row))) == project(row)` over the harvested catalog.
- byte-stability: same grid ⇒ identical reverse-map file (hash equality).
- ingest→reverse_map→(pyKMC stub minimise+search)→re-ingest lands the **same** `class_id`.

**Statistical / physical.**
- **Diffusion validation:** vacancy MSD / tracer-diffusion coefficient from the on-lattice engine vs a
  direct pyKMC run on the same small system — agree within statistical error once the catalog is
  well-harvested.
- **Detailed balance:** on a small closed system run to equilibrium, the occupancy distribution
  matches Boltzmann for the catalog's `ΔE`s; per-class forward/backward flux balance at equilibrium.
- **Convergence:** over cycles, `new_classes_this_cycle → 0` and `fallback_fraction → 0`
  (the loop's stopping signal).
- **Conservation:** atom count constant in v1 (canonical); with the dissolution hook on, reservoir
  count balances removals.
- **Rate-list invariant:** every `M` steps, rebuild the full rate list and assert
  `Σ k_incremental == Σ k_rebuilt` (catches failure #9).
- **Performance:** assert per-step time is N-independent; 10⁶ steps on 10³ sites under a wall-clock
  budget; 10⁵-site build+evolve smoke test on a node.

---

## 12. Self-declared weaknesses

1. **`φ` is a lossy readout.** Distinct stencils can share `φ`, so the fallback cannot distinguish
   them (exact lookup can). Mitigated by directional pair-count features and by flag+harvest, but not
   eliminated — a fundamental cost of embedding a discrete identity into a smaller continuous space.
2. **Single rigid global frame.** The "always-O_h-on-decorated-stencil" elegance assumes the surface
   aligns with a lattice plane in one fixed frame. A reconstructed, heavily stepped, or plastically
   deformed slab (dislocations in later production geometry) stresses the snap and may need
   region-local frames — designed-for (defect regions in §1.3) but not implemented in v1.
3. **Concentrated-alloy active set ≈ N.** The heterogeneity clause makes the *initial build* O(N·S)
   for a concentrated NiCr; only the per-step cost is sublinear. Acceptable but not sublinear
   end-to-end for the first build.
4. **Mean-barrier per class hides multimodality.** We *detect* it (`Ea_std`) but the split/grow-`R_env`
   policy is heuristic; a genuinely bimodal environment mis-served until audited.
5. **Prefactor aggregation (geomean) is a modeling choice.** Wide within-class ν₀ spread makes the
   effective rate approximate; the ν₀ regression is weaker than the Ea regression (fewer physical
   priors).
6. **Ideal-site reverse map can pick the wrong basin.** Handing pyKMC atoms at *ideal* sites assumes
   its minimiser relaxes into the intended basin; a rare metastable neighbour could bias a harvested
   barrier. pyKMC's own reconstruction/containment checks are the backstop, but the risk is real.
7. **GP fallback scaling.** Tier-2 GP cost grows with per-family training size; needs inducing
   points/capping at production scale (deferred).
8. **`event_id` demotion is a bet.** Re-deriving identity from the lattice (not pyKMC's certificate)
   is strictly more informative *if* the projection is faithful; when projection is marginal (surface,
   high `ρ`), we have moved authority from pyKMC's validated hash to our snap. Gates 3–4 guard this,
   but a subtly wrong frame could systematically mis-key a whole surface family before the audit
   catches it.

---

## 13. Fit to the harvest pipeline (implementability)

- **Reads** `reference_table.pickle` (pandas) using the exact columns of `event_table.py`; consumes
  `initial/final/saddle_positions`, `initial_types`, `energy_barrier`, `k`, `k_prefactor`, `nu0`,
  `idx_backward`, `event_id` (provenance), `dra`/`move_atom_idx` (cross-check only).
- **Reuses pyKMC thresholds** (`emin_event`, `emax_event`, `energy_asymmetry`, `matching_score_thr`,
  `rcut`) so gate verdicts are consistent with what pyKMC already accepted.
- **Writes** an ASE-readable ideal-site config + the cumulative `reference_table.pickle`; the loop
  sets `config.control.reference_table` + `initial_config` and runs `k=20–1000` pyKMC steps — the
  restart contract already exists.
- **File-based handoffs** (catalog Parquet, regressor blobs, coverage/projection JSONL, priority
  targets) make each leg scriptable; a closed-loop driver drops in without redesign (SPEC decision 1).
- **New dependencies** are modest: a fixed 48-element integer group, a KD-tree snap (scipy, already a
  pyKMC dep), and a ridge/GP (numpy / optional scikit-learn). No nauty needed on the lattice side.
```
