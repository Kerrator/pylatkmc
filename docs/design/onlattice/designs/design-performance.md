# Design "performance" — a fixed-site FCC on-lattice KMC engine fed by pyKMC off-lattice harvest

**Angle:** incremental / performance-first. Every decision below is chosen so the inner KMC loop
survives 10⁶–10⁸ steps: O(local) rate-list updates, cache-friendly integer occupancy, precomputed
neighbour tables, and correctness enforced by invariants and round-trip tests rather than by
re-deriving geometry every step.

**Intellectual anchors (published lattice-KMC):** BKL / n-fold way (Bortz–Kalos–Lebowitz 1975);
self-learning KMC (Trushin, Karim, Kara, Rahman 2005 — fixed lattice + pattern database of
saddles, the closest published analogue to this problem); kinetic ART / k-ART (El-Mellouhi,
Mousseau, Béland 2008 — off-lattice + nauty topological reuse, i.e. what pyKMC *is*); pattern-based
lattice codes (SPPARKS, kmos, KMCLib); cluster-expansion KMC for alloy barriers. My contribution is
the *executor* half: turn the harvested off-lattice catalogue into an on-lattice class table whose
runtime cost is independent of system size and dominated by the defect count, not the site count.

---

## 0. Design philosophy and the single load-bearing idea

The performance of a lattice KMC engine is decided by one question: **after I execute an event, how
much work do I do to get the next one?** If the answer scales with the number of sites *N*, the
engine dies at 10⁴ steps. If it scales with the number of *defects* (vacancies, surface kinks) it
runs to 10⁸.

Everything here is built to make that answer O(1) in *N*:

1. **Sites are fixed integers, atoms are just occupancy.** The lattice graph never changes (even
   under dealloying — a removed atom is an `EMPTY` site, not a re-indexing). All geometry is
   precomputed once.
2. **Rate is a per-class constant** (Arrhenius from class Ea, ν₀). So the BKL vector is grouped by
   class; total rate is Σ nₖ·kₖ and a step touches only the few classes whose instance counts
   changed.
3. **Enumeration is driven by the rarest species in an event's before-image** (usually the
   vacancy). We iterate over the O(#vacancies) empty sites, never over all N sites.
4. **A step only dirties a bounded neighbourhood.** Incremental rate-list maintenance re-examines
   O(1) sites, verified equal to a periodic full rebuild by an invariant test.

The rest of the document is the machinery that makes those four statements true and correct.

---

## 1. Lattice model and core data structures (the performance substrate)

### 1.1 FCC-as-simple-cubic parity encoding

An FCC lattice with conventional constant *a* is exactly the set of simple-cubic points on a grid of
spacing `h = a/2` subject to a parity rule:

> Site `(i,j,k) ∈ ℤ³` is an FCC site **iff `i+j+k` is even**. Its Cartesian position is
> `origin + (i,j,k)·h` (axis-aligned cell; a `basis` matrix generalises to rotated cells).

This encoding was chosen because it makes every geometric primitive an integer operation
(verified numerically):

| Quantity | Value in half-integer units | Cartesian |
|---|---|---|
| Nearest-neighbour "12-star" | all signed perms of `(±1,±1,0)` → **12 offsets** | `a/√2 = 2.489 Å` |
| 2nd-NN shell | signed perms of `(±2,0,0)` → 6 offsets | `a = 3.52 Å` |
| 3rd-NN shell | signed perms of `(±2,±1,±1)` → 24 offsets | `a·√(3/2)` |
| Site point group (bulk) | signed coordinate permutations = **O_h, 48 ops** | — |
| (100) layering | k even ⇒ (i,j) same parity; k odd ⇒ opposite ⇒ ABAB stack | — |

For a **(100) slab**: z = [001] is the surface normal; layers are indexed by k; in-plane periodic so
`i` wraps mod `n_i = 2·n_cells_x`, `j` wraps mod `n_j = 2·n_cells_y`; `k ∈ [0, n_k)` is
**non-periodic** (free surfaces). Each layer holds `n_i·n_j/2` sites. A bulk site has 12 NN; a
top-layer site keeps only the 8 NN with `dz ≤ 0` — **coordination 8**, exactly the physical FCC(100)
surface coordination (verified). Coordination is therefore read directly by counting occupied
entries in the 12-star, which also gives the dealloying eligibility test (coord ≤ coord_max) for
free.

### 1.2 Schemas

```
LatticeFrame                       # persisted per campaign; makes reverse-map bit-reproducible
  a            : float64  (Å)
  h            : float64  = a/2
  n_i, n_j     : int32    # in-plane half-integer moduli (PBC)
  n_k          : int32    # number of (100) layers (non-periodic)
  origin       : float64[3]
  basis        : float64[3][3]     # default I; rotated/strained cells supported
  z_layer_pos  : float64[n_k]      # per-layer z (captures surface relaxation/rumpling)
  species_enum : {0:EMPTY, 1:Ni, 2:Cr, 3:Fe, ...}   # 1 byte per site; ternary-ready

OccupancyGrid
  occ          : uint8[N_sites]              # species enum, 0 = EMPTY (vacancy or vacuum)
  ijk          : int32[N_sites][3]           # site -> (i,j,k)   (SoA, contiguous)
  lin          : hashmap or direct index (i,j,k) -> site_id
  nn12         : int32[N_sites][12]          # precomputed NN site ids; -1 = vacuum/out-of-slab
  ctx          : int32[N_sites][C]           # precomputed context ball (NN + 2NN [+3NN]) ids
  rctx_ball    : int32[N_sites][B]           # sites within R_ctx (for dirty-region expansion)
  species_sites: dict[uint8 -> DynArray[int32]]   # per-species site lists incl EMPTY
  site_pos_in_list : int32[N_sites]          # back-pointer for O(1) swap-remove
  surface_k    : int32[n_i*n_j]              # max occupied layer per (i,j) column
```

**Memory / layout choices (performance-first):**

- `occ` is a flat contiguous `uint8` array. 10⁶ sites = 1 MB (fits L2/L3); 10⁸ sites = 100 MB.
- Site ids are assigned in **layer-blocked (tiled) order**: within each layer, 8×8 in-plane tiles are
  contiguous, layers stacked. A site and its 12-star therefore span ≤3 adjacent layer-planes within
  one tile ⇒ the O(1) dirty updates touch a handful of cache lines.
- `nn12` (int32, 48 B/site) is the biggest table: 48 MB at 10⁶ sites (fine), 4.8 GB at 10⁸
  (too big). **Scale switch:** for N ≤ ~10⁷ store `nn12`; above that, drop the table and compute
  neighbours arithmetically (`(i±1,j±1,k) mod …`, ~10 int ops) — often cheaper than the cache miss
  a table lookup would cost at that scale. Both paths are behind one `neighbours(site)` accessor.
- Everything is **struct-of-arrays** so the hot loops vectorise and never chase Python objects.

### 1.3 Invariants (asserted in debug builds, sampled in production)

- **I1 parity:** every stored site has `i+j+k` even.
- **I2 NN symmetry:** `t ∈ nn12[s] ⟺ s ∈ nn12[t]` (or the vacuum sentinel).
- **I3 species-list consistency:** `s ∈ species_sites[occ[s]]` and `site_pos_in_list` inverts it.
- **I4 conservation (v1):** Σ over non-EMPTY species counts is constant across a canonical cycle.
- **I5 rate-list equivalence:** incremental rate list == full rebuild (see §4.6).

---

## 2. Component 1 — Forward configuration projection (off-lattice snapshot → occupancy)

**Input:** full-cell snapshot `positions (N×3, Å)`, `types`, `cell`. **Output:** `OccupancyGrid` +
an unmappable report. **Cost target:** O(N), no all-pairs search.

### 2.1 Frame establishment (drift/registration)

The in-plane cell is pinned by PBC, so `a = cell_xx / n_cells_x` exactly (and `= cell_yy/n_cells_y`;
disagreement > 1 % ⇒ abort, non-cubic in-plane). Only the **origin offset** (rigid drift + a z
gauge) is unknown and must be fitted:

```
fit_origin(positions, a):
    h = a/2
    # coarse: snap with origin 0, measure the modal residual offset
    frac = (positions / h)                      # O(N)
    res  = frac - round(frac)                    # in (-0.5, 0.5], per atom, per axis
    origin0 = median(res, axis=0) * h            # robust rigid shift (circular median in x,y)
    # one refinement pass captures the FCC parity gauge:
    return refine_z_layers(positions - origin0)  # per-layer median z -> z_layer_pos[]
```

Rigid drift is a single 3-vector; thermal expansion in z is absorbed by a per-layer `z_layer_pos`
table (interior layers ≈ k·h, surface layers relax inward). One median pass converges because the
map is rigid. Re-fit every projection so inter-cycle drift never accumulates.

### 2.2 Snap (O(1) per atom, no search)

```
snap_atom(pos):
    q = round((pos - origin) / h)                # nearest SC lattice point, 3 rounds
    if (q.i+q.j+q.k) is odd:                      # between FCC sites: fix parity
        axis = argmax(|((pos-origin)/h) - q|)     # coordinate that was nearest its half-point
        q[axis] += sign_towards_true(pos, q, axis)
    site = lin(q mod (n_i,n_j), q.k)             # PBC wrap in-plane
    residual = |pos - cart(q)|
    return site, residual
```

Rounding to nearest SC point then a single parity fix lands on the true nearest FCC site because the
Voronoi cell of an FCC site is the rhombic dodecahedron inscribed in the SC cube of the two
candidate parities. Total: O(N), branch-light, vectorisable.

### 2.3 Occupancy assembly, vacancies, and the unmappable report

- Each atom writes `occ[site] = enum(type)`. A **collision** (two atoms → one site) or a
  **residual > snap_tol** marks that atom *unmappable*.
- **Vacancy vs vacuum:** compute `surface_k[i,j] = max k with occ occupied in that column`. A site
  below its column's surface envelope but `EMPTY` is a **vacancy**; above it is **vacuum**. This one
  scan (O(N)) is what turns "an empty site" into physically-typed information and drives
  vacancy-anchored enumeration in §4.

```
snap_tol  default = 0.35 * (a/√2) ≈ 0.87 Å        # << NN spacing; >> thermal+relaxation wobble
```

Chosen so a genuinely migrated atom (≥ one NN step, 2.49 Å) can never masquerade as "relaxed on
site", while surface rumpling/thermal displacement (≤ ~0.4 Å) snaps cleanly.

**Cycle policy on unmappables (loop-decision-5 gate):**

| Unmappable fraction *f* | Action |
|---|---|
| f = 0 | clean projection; proceed |
| 0 < f ≤ `f_soft` (default 0.2 %, and ≥1 atom) | project the rest, pin each unmappable atom to its least-bad site, **flag the region + queue audit**; annotate those sites so events touching them are not harvested this cycle |
| f > `f_hard` (default 1 %) | **abort the cycle projection**, emit a diagnostic (likely amorphization / melt / mis-registration), requeue with a widened `snap_tol` retry once, else escalate to human |

Because snapshots handed across the loop are pyKMC **minima**, f should be 0 in the healthy regime;
any nonzero f is signal, not noise, hence it never silently drops flux.

---

## 3. Component 2 — Event projection (off-lattice event record → on-lattice event)

**Input:** one reference-table row (`initial_positions`, `saddle_positions`, `final_positions` — all
subset-relative to the mover's rcut cluster, same atom ordering across the three; `initial_types`;
`move_atom_idx`; `sym_matrix/sym_perm`; `idx_backward`; `energy_barrier`, `k`, `nu0`, `dra`).
**Output:** an on-lattice event = a **set of `(site_offset, sp_before → sp_after)` changes** plus a
context decoration.

### 3.1 Local frame (event records are NOT in a global frame)

The cumulative reference table mixes rows harvested at different cycles/steps and possibly
IRA-registered frames, so absolute coordinates are inconsistent. Event projection is therefore made
**frame-independent**: fit a *local* FCC frame from the well-coordinated peripheral atoms of the
subset (those far from the mover are near-ideal). `a` is the global constant; only a local origin is
fit, by the same median-residual trick over the peripheral atoms (RANSAC-lite over a few candidate
offsets, keep the one maximising sub-tolerance snaps). Snap `initial_positions` and
`final_positions` in this local frame.

### 3.2 Detect the true movers (do NOT trust `move_atom_idx`)

```
project_event(row):
    frame = fit_local_frame(row.initial_positions[peripheral])
    site_init[k] = snap(row.initial_positions[k], frame)   # same atom index k in init & final
    site_fin[k]  = snap(row.final_positions[k],  frame)
    movers = [k for k in atoms if site_init[k] != site_fin[k]]   # site change == real mover
    # occupancy changes, atom identity preserved (row k is one physical atom):
    changes = {}
    for k in movers:
        sp = enum(row.initial_types[k])            # species of atom k (EMPTY handled below)
        changes[site_init[k]] .after  = EMPTY       # it leaves
        changes[site_init[k]] .before = sp
        changes[site_fin[k]]  .after  = sp          # it arrives
        changes[site_fin[k]]  .before = EMPTY (or displaced species, resolved by union)
    reconcile(changes)   # a site that is both a source and a destination keeps net before/after
    assert snap_residual_max(minima only) < snap_tol   # gate G3 (saddle is off-lattice, exempt)
    return changes, context_decoration(changes, frame)
```

Movers are defined by **site change**, not displacement magnitude, so an atom that displaces far but
returns to its own site (large relaxation) is not a mover, and a genuine 2nd/3rd participant of a
concerted event *is* — satisfying the SPEC's explicit warning. `n_movers`-style thresholds from the
reconstruction config are used only as a secondary sanity floor.

### 3.3 Context decoration and the occupancy-count-changing hook

- **Context** = the `before`-image occupancy of every site within `R_ctx` of any changed site,
  expressed as `(offset, species)` relative to the anchor. `R_ctx` covers NN + 2NN of every changed
  site (≈ 1·a), matching the physical range of embedding/bond effects **and** the fallback-regression
  descriptor range (so exact key and fallback descriptor see the same neighbourhood — §5).
- **Non-conservative (dealloying) events are representable now:** a change `(off, Cr → EMPTY)` with
  no compensating arrival is simply a change-set whose before/after species multiset differ. v1 gates
  such events out (canonical, atom-conserving) but the schema and canonicaliser handle them
  unchanged, so the later dealloying campaign needs no re-harvest or schema break.

---

## 4. Component 3 + 4 — Class identity and runtime matching (the two hearts)

### 4.1 Class identity (Component 3)

Two projected events are the **same class** iff their `(stencil, context, species-decoration)`
canonicalise to the same key under the lattice symmetry appropriate to the anchor's depth.

**Applicable symmetry group (depth-aware — physically essential):**

```
G(anchor):
    if both surfaces are ≥ R_ctx layers away from every changed/context site:  return O_h  (48)
    else:                                                                        return C_4v (8)
```

`O_h` = the 48 signed coordinate permutations (they permute the 12-star among itself and preserve
parity — verified). `C_4v` = the 8 operations `(x,y,z) → (±perm(x,y), +z)` that keep the surface
normal fixed. **Using the reduced group at the surface is not optional:** canonicalising a surface
hop under full O_h would equate it with a bulk hop and assign the wrong barrier. Intermediate
sub-surface layers whose context still touches a surface use C_4v (a conservative discretisation;
its cost is listed in Weaknesses).

**Canonicalisation (cheap, exact, integer-only):**

```
canonical_key(changes, context, depth):
    G = precomputed_group(depth)                 # list of offset-permutation ops
    best = None
    for anchor in changed_sites:                 # ≤ ~5 candidates
        rel = express_offsets_relative_to(anchor, changes, context)
        for g in G:                              # ≤ 48
            t = sort(( g·off, sp_before, sp_after ) for each change)
            c = sort(( g·off, sp ) for each context entry)
            key = hash(t, c, depth, coloring_mode)
            best = min(best, (t, c, depth))       # lexicographic
    anchor_change := the change fixed at offset 0 in `best`
    enum_species  := rarest global species among anchor-change before-images  # perf, §4.3
    return hash(best), anchor_change, enum_species
```

Costs O(#changes · |G| · #changes·log) ≈ microseconds. Deterministic, translation+rotation+species
invariant. **This — not the pyKMC `event_id` — is the authoritative on-lattice class key.** The
pyKMC graph/coordination `event_id` is *carried as provenance* and used only as a fast pre-filter and
novelty accelerator (§6); it is off-lattice, drift-sensitive, and cannot encode a multi-site stencil,
so it is never the identity of record.

**Coloring mode:** `grey` collapses all occupied species to one label (matches pyKMC's grey mode);
`full` keeps Ni/Cr/Fe distinct. NiCr dealloying needs `full` (Cr and Ni barriers differ). The mode is
part of the key so a catalogue is never silently mixed.

**Precomputed per class:** the **orientation set** — the distinct images of the canonical stencil
under G (orbit size = |G| / |stabiliser|). Stored as `(offset-permutation, species-map)` so runtime
matching is table-driven.

### 4.2 The rate list is grouped by class (Component 4, structure)

Because rate is a class constant, the BKL vector factorises:

```
R_total = Σ_c  n_c · k_c      (exact-match pool, grouped)
        + Σ_j  k_j            (fallback pool, per-instance rates)

exact pool:      per class c -> DynArray[EventInstance]   (n_c = len);  k_c precomputed
fallback pool:   Fenwick/segment tree over per-instance k_j
supported_by:    int32[N_sites] -> list of instance handles reading that site   (dirty index)
```

`EventInstance = { anchor_site:int32, class:int32, orient:int8, pool:{exact,fallback}, k:float }`.

### 4.3 Enumeration is defect-driven, not site-driven

To list instances of class *c*, iterate the **anchor over the sites of `enum_species(c)`** (the
rarest species in the anchor change — the vacancy for any vacancy-mediated event), and for each
candidate anchor test every orientation:

```
enumerate_class(c):
    for a in species_sites[c.enum_species]:          # O(#vacancies), not O(N)
        for g in c.orientations:
            if matches(a, c, g): add_instance(a, c, g)

matches(a, c, g):
    for (off, sp_before, sp_after) in g·c.stencil:
        if occ[ neighbour(a, off) ] != sp_before: return False    # integer reads only
    for (off, sp) in g·c.context:
        if occ[ neighbour(a, off) ] != sp: return False
    return True
```

For 1–2 vacancies in a 10³–10⁶-site slab, `species_sites[EMPTY_in_slab]` is tiny, so the whole rate
list is built in microseconds and **its size is O(#defects × #classes × #orientations)**, independent
of N. Classes with no vacancy in their before-image (e.g. a direct Cr–Ni antisite exchange) anchor on
the least-abundant occupied species present (Cr in Ni-rich alloy) via `species_sites[Cr]`; a
50/50-abundant anchor is the only case that degrades to O(N/2) and is flagged for a spatial-index
enumeration fallback.

### 4.4 Incremental update after an executed event (the O(1)-in-N core)

```
execute(instance):
    apply g·stencil: for each change set occ[neighbour(anchor,off)] = sp_after
        -> update species_sites (swap-remove old, append new, O(1) each)
        -> update surface_k for touched columns
        -> update SRO / composition accumulators (O(#changes))
    changed = the sites whose occ changed
    affected = changed ∪ (rctx_ball around each changed site)      # bounded, O(1) in N
    for s in affected:
        for h in supported_by[s]: remove_instance(h)               # swap-remove from pool + index
    for a in affected ∩ species_sites[*any enum species*]:
        re-run enumerate for classes whose enum_species == occ-type of a
    advance clock: Δt = -ln(U(0,1]) / R_total
```

Only a bounded neighbourhood is re-examined, so **per-step work is O(1) in system size** and O(#local
classes) in catalogue size. The `supported_by` index makes instance removal O(1). Selection:

```
select():                                            # O(log C) with a Fenwick over classes
    u = U(0,1) * R_total
    if u < exact_total: pick class by prefix sum; pick instance uniformly in its DynArray  (O(1))
    else:               pick fallback instance via Fenwick over k_j                        (O(log M_fb))
```

### 4.5 Complexity summary

| Operation | Cost | Notes |
|---|---|---|
| Projection (Comp 1) | O(N) per cycle | rounding snap + 1 median pass; no search |
| Initial rate-list build | O(#defects · #classes · #orient · stencil) | not O(N) |
| **Per KMC step** | **O(1) in N**, O(#local classes) in catalogue | dirty region bounded; selection O(log C) |
| Memory | O(N) grid + O(N)·48 B NN table (or 0 with arithmetic neighbours) | tiled layout for locality |

**Targets:** 10⁶ steps on 10³ sites → dominated by ~10⁶ × (few µs) ≈ seconds–minute. 10⁵–10⁶ sites
on a cluster node → grid+tables O(N) memory, per-step still O(1); the only N-dependent cost is the
once-per-cycle projection and initial build, both O(N) and rare. 10⁸ sites → arithmetic-neighbour
mode, per-step still defect-bounded.

### 4.6 Correctness of the fast path — I5 invariant

Every `audit_rebuild_interval` steps (default 10⁴), rebuild the entire rate list from scratch (§4.3
over all classes) and assert it is **set-equal** to the incrementally-maintained list (same
instances, same R_total to 1 ULP). A mismatch is a hard failure with a dump. This makes the O(1)
optimisation trustworthy: the slow, obviously-correct method is the oracle for the fast one.

---

## 5. Component 5 — Rate assignment

### 5.1 Exact-lookup path

Class *c* aggregates all harvested instances mapped to it: `Ea_c = mean(barrier_samples)`,
`ν0_c = geo_mean(nu0 samples)` (or a default THz if HTST off). Rate is **temperature-independent in
its parameters**:

```
k_c = ν0_c · exp( − Ea_c / (k_B · T) )        # k_B = 8.6173e-5 eV/K; k in ps^-1, matching pyKMC
```

Precomputed once per (catalogue, T). A T-sweep just recomputes the `k_c` column.

### 5.2 Fallback regression (near-miss environments)

An executable instance whose `(stencil, context)` matches a known **stencil** but whose **context
decoration** is unseen (near-miss) gets a rate from a regression over local-environment descriptors:

- **Descriptors (cheap integer features from the grid, same R_ctx as identity):** per changed site,
  the count of each species in its NN and 2NN shells at the *initial* and *final* configurations;
  coordination of the mover before/after; #bonds broken and formed by species pair; a one-hot of
  `depth_class`; the stencil family id (which move topology). All O(1) from `nn12`/`ctx`.
- **Model:** start with ridge regression `Ea ≈ w·φ + b` (interpretable, refit in ms, extrapolates
  gracefully); upgrade to gradient-boosted trees once the catalogue has ≳ a few hundred rows and
  non-linearity shows in residuals. ν₀ fallback = geometric mean of harvested ν₀ for the stencil
  family (attempt frequencies vary little).
- **Fitting protocol:** fit on **all** harvested `(φ, Ea)` across all cycles; hold out 20 % for a
  cross-validated RMSE that is logged and audited; clamp predictions to `[emin_event, emax_event]`.
- **Refit cadence:** after any cycle that added a new class, or when the harvested-row count grows by
  > 10 % since the last fit (cheap — hundreds–thousands of rows). The model version is stamped into
  provenance so any fallback-served step is reproducible.

### 5.3 The flag mechanism (nothing contributes zero flux)

Every fallback-served instance sets `flagged = true` and increments a counter on its **observed
canonical key** (an observed-but-unharvested class). The fallback always returns a finite,
physically-clamped rate, so a near-miss environment carries real flux — it is never silently zero.
The set of flagged keys, ranked by (executed flux × count), is exported as the **priority target list
for the next pyKMC leg**: their representative sites are reverse-mapped to atomistic central atoms so
pyKMC searches exactly the environments the evolve leg most needs.

---

## 6. Component 6 — Novelty and harvest round trip

### 6.1 Ingest a cycle's new reference rows

```
ingest(new_rows):
    for row in new_rows:
        changes, ctx = project_event(row)                 # §3
        key, anchor, enum_sp = canonical_key(changes, ctx, depth_of(row))   # §4.1
        if key in catalogue:
            c = catalogue[key]
            c.barrier_samples.append(row.energy_barrier)   # new INSTANCE of known class
            c.nu0_samples.append(row.nu0); c.provenance.add(cycle, row.event_id)
            recompute Ea_c, ν0_c, k_c
            run_gates(c)                                    # §7.1; may move to audit
        else:
            c = new EventClass(key, changes, ctx, ...)      # NEW CLASS
            c.audit_status = pending_audit                  # first instance always audited
            enqueue_audit(c)
        link_reverse_pair(row)                              # §6.2
```

New-class vs new-instance is a pure hash lookup on the authoritative on-lattice key; the pyKMC
`event_id` accelerates it as a pre-filter (rows with an already-seen `event_id` almost always hit an
existing class, so the expensive projection can be skipped when the `event_id`→key cache is warm).

### 6.2 Forward/backward pairing (microscopic reversibility bookkeeping)

The row's `idx_backward` names its reverse. Project both, canonicalise both, set
`c.reverse_class_id = c'` and `c'.reverse_class_id = c`. **Consistency gate:** the reverse of *c*'s
stencil (swap before↔after, negate the net displacement) must canonicalise to *c'*; and the barriers
must satisfy `Ea_fwd − Ea_bwd = ΔE = E_final − E_initial`. Because both barriers come from the *same*
saddle, detailed balance `k_fwd/k_bwd = exp(−ΔE/k_BT)` then holds **by construction** — the pairing is
what guarantees the on-lattice engine cannot drift off equilibrium. A self-reverse event (`event_id
== id_final`) is stored once with `reverse = self`.

### 6.3 Coverage-report metrics (cheap streaming accumulation)

Maintained as running counters, all O(1)/step:

| Metric (loop-decision-6) | How accumulated |
|---|---|
| fraction of executed flux on fallback | `Σ k_selected·[flagged] / Σ k_selected`, plus a fallback-execution count |
| observed-but-unharvested classes | the flagged-key set with counts + representative sites |
| composition drift | per-species counts updated on every occupancy change |
| short-range-order drift | Warren–Cowley α for each pair, from incrementally-maintained NN pair counts |

**Convergence signal:** new canonical keys created per cycle → 0. The evolve leg runs a fixed,
tunable `n` (~10⁶) steps then emits this report; the driver decides whether to switch legs.

---

## 7. Component 7 — Provenance and curation

### 7.1 Gate checks (precise; loop-decision-5)

| Gate | Check | Fail action |
|---|---|---|
| **G1 barrier bounds** | `emin_event ≤ Ea ≤ emax_event`; `Ea_bwd ≥ emin` | audit |
| **G2 fwd/bwd consistency** | reverse stencil canonicalises to the paired class; `|Ea_fwd−Ea_bwd−ΔE| ≤ dE_tol` (0.05 eV) | audit |
| **G3 snap residual** | max snap residual over **initial & final minima** < snap_tol (saddle exempt) | audit |
| **G4 projection round-trip** | occupancy→atomistic→re-project reproduces the same changed sites & species; stencil→reverse-atomistic→re-project reproduces the stencil | audit |
| **G5 conservation (v1)** | before/after species multiset equal (atom-conserving) | audit (this is how a stray dealloying event is caught in a canonical run) |

Passing all gates ⇒ **auto-admitted**; any failure, and every brand-new class's first instance, ⇒
**pending_audit**.

### 7.2 Schemas

```
Provenance
  first_seen_cycle   : int
  source_cycles      : int[]
  contributions      : [ {cycle, pykmc_event_id, Ea, nu0, snap_residual} ]
  barrier_stats      : {mean, std, min, max, n}
  nu0_stats          : {mean, std, n}
  gate_outcomes      : {G1..G5 -> pass|fail(detail)}
  regression_version : int | null            # set iff any instance was fallback-served
  audit_status       : {auto_admitted, pending_audit, human_accepted, rejected, superseded}

AuditQueueEntry   (JSONL, file-based handoff)
  class_key, provenance, gate_failures[],
  representative_atomistic_snippet (ideal-site xyz of stencil+context),
  proposed_label, reverse_class_key
```

The audit queue is a plain JSONL file so the alternation loop stays scriptable (loop-decision-1); a
human marks `human_accepted`/`rejected`/`relabel`, accepted classes merge in, rejected keys are
remembered so they are not re-queued.

### 7.3 Deterministic reverse mapping (occupancy → atomistic for the next pyKMC leg)

Given `OccupancyGrid` + persisted `LatticeFrame`, the atomistic seed is a **pure function**: for each
occupied site emit one atom of its species at `origin + basis·(i,j,k)·h` (interior layers at ideal z,
surface layers optionally pre-relaxed via `z_layer_pos`). Deterministic and bit-reproducible because
the frame is persisted. pyKMC then minimises it (`config.control.initial_config` +
`reference_table`), so the on-lattice engine hands back exactly the ideal-site configuration pyKMC
expects to relax. Flagged sites (§5.3) are written first in the file and recorded as the priority
central-atom list for the search leg.

---

## 8. Worked examples (projected → classified → matched → executed)

### 8.1 Example A — single vacancy NN hop (2-site)

**State.** Bulk Ni vacancy at `V=(4,4,6)`; a Ni atom at NN site `N=(5,5,6)`, offset `δ=(+1,+1,0)`.

**pyKMC row.** `initial_positions`: atom near N, empty region near V; `final_positions`: atom near V,
empty near N; `move_atom_idx` → that atom; `energy_barrier` 0.68 eV, `nu0` 8 THz, `dra` ≈ 1.2 Å (to
saddle). Same atom index across init/final.

**Project (§3).** Fit local frame; `site_init = N`, `site_fin = V` for the atom → one mover, one site
change. Changes: `{ V: EMPTY→Ni, N: Ni→EMPTY }`. Max snap residual 0.21 Å < 0.87 (G3 pass). Context =
NN/2NN species around V and N (all Ni here).

**Classify (§4.1).** Depth ≥ R_ctx from both surfaces ⇒ `G = O_h`. Anchor on the EMPTY change
(`enum_species = EMPTY`, the rarest). Canonical stencil `{ (0,0,0): ∅→Ni, (1,1,0): Ni→∅ }`; under
O_h all 12 NN directions fall in one orbit ⇒ **12 orientations**, one class `c_A`. `k_cA = 8 ·
exp(−0.68/k_B·300) ps⁻¹`.

**Match (§4.3).** Iterate anchors over `species_sites[EMPTY_in_slab]` = {V}. For each of 12
orientations, check the NN is Ni: up to 12 instances, all sharing `k_cA`. So a lone bulk vacancy
contributes `12·k_cA` to `R_total` with 12 grouped instances.

**Execute (§4.4).** BKL picks `c_A`, then one instance uniformly, say orientation `δ=(1,1,0)`. Apply:
`occ[V]=Ni`, `occ[N]=EMPTY`; update species lists (V leaves EMPTY list, N joins it), `surface_k`
unchanged (bulk), SRO unchanged (Ni-only). Vacancy is now at N. `affected = {V,N} ∪ rctx_balls`
(~30 sites). Remove their instances, re-enumerate anchored at the new EMPTY site N → again ~12
instances. `Δt = −ln(U)/R_total`. Per-step work independent of the 10³–10⁶ site count.

### 8.2 Example B — 3-site concerted surface shuffle (species-resolved, absent from standard catalogues)

**State (NiCr(100) surface).** Surface vacancy `V=(4,4,8)` (top layer, coord ≤ 8); along a ⟨110⟩ row,
`P1=(5,5,8)` holds **Cr**, `P2=(6,6,8)` holds **Ni**. Off-lattice, the single-atom intermediate
(only Cr hops to V) is not a stable minimum because of the Cr–Ni interaction, so pyKMC finds a
**concerted** saddle where Cr and Ni move together.

**pyKMC row.** `initial`: Cr near P1, Ni near P2, empty near V. `final`: Cr near V, Ni near P1, empty
near P2. `move_atom_idx` names **only the Cr** (the SPEC's trap). `initial_types` distinguishes
Cr/Ni. Both Cr and Ni displace ≈ 2.49 Å.

**Project (§3).** Snap init/final: Cr `P1→V`, Ni `P2→P1` → **two movers** detected by *site change*
(the row named one; projection finds both). Changes:
`{ V: EMPTY→Cr, P1: Cr→Ni, P2: Ni→EMPTY }` — a genuine **3-site** change, species-resolved.
Minima snap residuals 0.3 Å (G3 pass; the concerted saddle itself is off-lattice and exempt).

**Classify (§4.1).** Surface-coupled ⇒ `G = C_4v` (8 ops) — **not** O_h; using O_h would fold this
into a bulk double-hop and mis-rate it. Anchor on EMPTY (`V`). Canonical stencil (full-colour):
`{ (0,0,0): ∅→Cr, (1,1,0): Cr→Ni, (2,2,0): Ni→∅ }`, a collinear ⟨110⟩ lead-Cr/trail-Ni double step.
Orbit under C_4v = the 4 in-plane ⟨110⟩ directions (× chirality) ⇒ a small orientation set, one class
`c_B` with its own `Ea_cB`, `ν0_cB`, reverse class `c_B'` (Ni-leads back). Detailed-balance pair
recorded (§6.2).

**Match (§4.3).** Anchor over surface EMPTY sites {V}. For each C_4v orientation, require
`occ[nn(V,δ1)]==Cr` and `occ[nn(V,2·δ)]==Ni` and the context. Here one orientation matches → one
instance of `c_B`, rate `k_cB`. (If P1/P2 were Ni/Ni it would not match `c_B`; a different harvested
class or the fallback would serve it.)

**Execute (§4.4).** Apply the 3-site stencil atomically: `occ[V]=Cr`, `occ[P1]=Ni`, `occ[P2]=EMPTY`.
Update species lists for all three, `surface_k` for the three columns, and the **SRO / composition
accumulators** (a Cr moved outward toward the vacancy — exactly the dealloying-relevant statistic the
coverage report tracks). `affected = {V,P1,P2} ∪ rctx_balls`; remove and re-enumerate; the vacancy is
now at P2 and a Cr sits at the old vacancy. `Δt = −ln(U)/R_total`.

This example exercises every hard requirement: multi-site first-class, don't-trust-`move_atom_idx`,
species resolution, reduced surface symmetry, and a dealloying-relevant statistic — all on the same
O(1) incremental machinery as the trivial vacancy hop.

---

## 9. Failure-mode table

| # | Failure | Trigger | Detection | Response |
|---|---|---|---|---|
| F1 | Frame mis-registration | whole-slab drift / thermal shift between cycles | median snap residual jumps; unmappable f rises | re-fit origin; retry once with widened tol; else audit |
| F2 | Amorphization / melt | run left validated regime | unmappable f > f_hard | abort cycle projection; flag region; escalate |
| F3 | Snap collision | two atoms → one site (near-saddle snapshot, or genuine defect) | collision check in assembly | mark both unmappable; audit |
| F4 | Concerted saddle won't map | saddle is inherently off-lattice | G3 applies to minima only | expected; no action (saddle exempt) |
| F5 | Final minimum won't map | event ends off-lattice (reconstruction) | G3 on final minimum | reject event; audit |
| F6 | Parity-tie snap ambiguity | atom ~equidistant between 2 sites | residual after parity-fix > tol | unmappable; audit |
| F7 | Class explosion | R_ctx too large ⇒ every environment unique | class-count growth per cycle monitored | shrink R_ctx; more fallback; alert |
| F8 | Fallback extrapolation | out-of-distribution environment | descriptor outside training hull; CV RMSE high | clamp to [emin,emax]; heavy flag; top audit priority |
| F9 | Detailed-balance violation | fwd/bwd barriers inconsistent | G2 | reject pair; audit |
| F10 | Rate-list desync (bug) | incremental-update defect | I5 periodic full-rebuild assert | hard fail + dump |
| F11 | Wrong symmetry group at surface cutoff | event straddles bulk/surface R_ctx boundary | depth classified per changed+context site; conservative C_4v | C_4v (never over-symmetrise); logged |
| F12 | Non-conservative event in v1 run | stray dealloying-type event harvested | G5 | reject; audit (schema still supports it when enabled) |
| F13 | 50/50 anchor species (no dilute driver) | direct exchange class in equiatomic alloy | enum_species abundance check | spatial-index enumeration fallback; flagged perf note |
| F14 | Catalogue/coloring-mode mix | grey + full rows merged | mode is part of the key | keys never collide; distinct classes |

---

## 10. Test plan

**Unit**
- Snap: known offsets → exact site; parity-fixer on odd-sum candidates; residual monotonic.
- Neighbour table: I1 parity, I2 symmetry; 12-star distances = a/√2; surface site has 8 NN.
- Canonicalisation: all 48 O_h images of a stencil → identical key; all 8 C_4v images at surface →
  identical key; an O_h-only relation across a surface event → **different** keys (guards F11).
- BKL: selection frequencies match `n_c·k_c` within sampling error; Δt distribution exponential.
- Incremental update: after a scripted event, instance set == fresh enumerate (unit-level I5).

**Round-trip**
- occupancy → atomistic → project → occupancy = identity (§7.3 / §2).
- event row → stencil → reverse-atomistic → re-project → same stencil (G4).
- forward∘backward stencil = identity; paired keys reverse-consistent (§6.2).
- class key invariant under every group op (property test over random stencils).

**Statistical / physical**
- Single-vacancy tracer diffusivity vs analytic `D = f·a²·Γ` and vs a direct pyKMC run (grey Ni).
- Detailed balance: two-state toy reaches Boltzmann occupation ratio `exp(−ΔE/k_BT)`.
- Arrhenius: measured mean hop rate vs `ν0·exp(−Ea/k_BT)` over a T-sweep (slope = Ea/k_B).
- Conservation I4 over 10⁶ steps (atom counts constant, v1).
- Coverage metrics: fallback-flux fraction → 0 as the catalogue completes on a seeded system.

**Performance / scaling**
- steps/sec vs N ∈ {10³, 10⁴, 10⁵, 10⁶}: assert per-step time flat (O(1) in N).
- Memory vs N linear; table vs arithmetic-neighbour crossover measured.
- I5 full-rebuild audit every 10⁴ steps green over a long run.

---

## 11. Extensibility (rubric item 15)

- **Ternary Ni-Cr-Fe:** species enum already `uint8`; `full` coloring and species-list enumeration
  are species-count agnostic; only the fallback descriptor grows by one composition channel. No
  structural change.
- **Occupancy-count-changing (dealloying):** the stencil is a general `before→after` change-set;
  `(Cr→EMPTY)` with no arrival is representable today, gated off by G5 in v1. Enabling dealloying =
  drop G5 for flagged classes + let `species_sites[EMPTY]` grow; because sites never re-index (unlike
  pyKMC's per-atom deletion), an EMPTY site is just occupancy — **no re-harvest, no schema break**.
  Bond-counting dissolution (Erlebacher `k = ν_d·exp((φ−n·E_b)/k_BT)`) drops in as a class whose rate
  is a coordination function, competing in the same grouped BKL vector.
- **Closed-loop driver:** every leg is a file-based handoff — projection reads a snapshot, harvest
  reads a reference table, reverse-map writes an xyz + priority list, audit is a JSONL queue,
  coverage is a JSON report. A driver script chains them with zero engine changes (loop-decision-1).

---

## 12. Self-declared weaknesses

1. **Rigid-lattice assumption.** Strongly reconstructed surfaces (missing-row, hex, large
   dislocation strain) push atoms past `snap_tol`; the design *detects* this (F1/F2/F6) but cannot
   *represent* a reconstruction on-lattice — those regions fall to audit and stall the catalogue
   there.
2. **`R_ctx` is a single hyperparameter with a sharp trade-off.** Too small ⇒ physically-distinct
   barriers collapse into one class (rate error, silent); too large ⇒ class explosion and
   fallback-dominated flux (F7). There is no principled auto-tuner here beyond monitoring class growth
   and fallback fraction.
3. **Fallback governs the early campaign.** When the catalogue is sparse the regression carries much
   of the flux; a biased extrapolation could steer evolution before the loop's next search leg
   corrects it. Clamping + heavy flagging mitigates but does not eliminate this.
4. **Depth→symmetry is a discrete approximation.** Collapsing all surface-coupled sites to C_4v (and
   everything else to O_h) mis-canonicalises events that straddle the R_ctx depth cutoff (F11). It
   errs conservatively (never over-symmetrises) but can *split* one physical class into two near the
   cutoff, diluting exact-match statistics.
5. **Subtle mover-count errors near tolerance.** A concerted event whose secondary mover snaps within
   ~`snap_tol` of *either* its source or destination site could be miscounted 2-vs-3 sites; G4
   round-trip catches gross cases, not borderline ones.
6. **Grey mode loses the Cr/Ni distinction** that dealloying physics needs; `full` mode is required
   for NiCr and multiplies class count (more search legs to converge).
7. **Finite interaction range.** Long-range elastic/electrostatic effects beyond `R_ctx` are not
   captured — inherent to any finite-range lattice KMC, but real for charged/segregating surfaces.
8. **No super-basin acceleration on the lattice.** pyKMC has basin acceleration; flickering
   low-barrier pairs (e.g. a vacancy rattling between two sites) will burn steps here. An absorbing-
   Markov super-event layer on top of the grouped BKL is the natural next addition but is out of
   scope for v1.
9. **Equiatomic direct-exchange classes (F13)** have no dilute anchor species, so their enumeration
   degrades toward O(N); the spatial-index fallback keeps it correct but not O(1).
```
