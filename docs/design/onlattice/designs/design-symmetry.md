# Design "symmetry" — Canonical-labeling-first event machinery for harvest-fed on-lattice KMC

**Angle:** exact event-class identity via a *canonical form* of the decorated site-change set under
the slab-appropriate lattice symmetry group. Group-theoretic dedup, orientation enumeration by orbit
generation, and provably collision-free class keys. Everything downstream — runtime matching, rate
lookup, novelty detection, provenance — hangs off one integer-exact canonicalizer.

---

## 0. Design thesis and why canonical labeling

pyKMC hands us events as *relaxed off-lattice geometry* and classifies them with a nauty graph
certificate over the `rcut` connectivity graph. That certificate is topological: it throws away
geometry and is sensitive to the neighbour-cutoff. It is a fine *discovery-side* dedup key, but it is
the wrong identity for an on-lattice engine that must (a) execute events at exact rates, (b) enumerate
every orientation at every site, and (c) decide with certainty whether a new pyKMC row is a known
class or a genuine novelty.

My identity is built on the observation that **once atoms are snapped to ideal FCC sites, an event is
a finite combinatorial object**: a set of lattice sites whose occupancy (species or `empty`) changes,
embedded in a decorated neighbourhood. Two such objects denote the same physical event class **iff a
symmetry of the slab maps one exactly onto the other**. Because the slab lattice is integer-exact
after snapping, this "iff" is decidable with *zero floating-point tolerance* by computing a canonical
form under the symmetry group and comparing. The canonical form is a faithful, invertible encoding of
the exact decorated geometry, so:

- **Same key ⟺ same class**, provably (no hash collisions, no accidental topological merges).
- Classification is *at least as fine* as pyKMC's graph hash when `r_id ≥ rcut` (§3.5), so we never
  wrongly merge two events pyKMC distinguishes; we may be finer, which is always safe.
- Orientation enumeration is just *orbit generation* under the group — the same machinery that
  produces the canonical form produces the runtime stencils.

The whole design is one idea applied seven times. The rest of this document is the concrete
realization.

### 0.1 Table of contents
- §1 Fixed conventions: the integer FCC frame and the slab symmetry groups
- §2 Component 1 — Forward configuration projection
- §3 Component 3 — Class identity (canonical labeling) — *the heart*
- §4 Component 2 — Event projection
- §5 Component 4 — Runtime matching and incremental update
- §6 Component 5 — Rate assignment (exact lookup + fallback regression)
- §7 Component 6 — Novelty and harvest round trip
- §8 Component 7 — Provenance and curation hooks
- §9 Worked examples (vacancy hop; 3-site concerted ring)
- §10 Complexity analysis
- §11 Failure-mode table
- §12 Test plan
- §13 Self-declared weaknesses

(Components are covered in dependency order, not numeric order: identity §3 must precede the event
projection §4 and matching §5 that consume it.)

---

## 1. Fixed conventions — the integer FCC frame and the slab symmetry groups

Everything is expressed in an **integer FCC-on-cubic-grid** representation so that lattice arithmetic,
symmetry operations, and the canonical form are exact.

### 1.1 The lattice
Let `a ≈ 3.52 Å` be the conventional FCC cell and `u = a/2 = 1.76 Å` the grid unit. FCC sites are

```
Site = { (i, j, k) ∈ ℤ³ : i + j + k ≡ 0 (mod 2) }
Cartesian(i,j,k) = r0 + u · R_frame · (i, j, k)ᵀ
```

- 1st-NN star (12 vectors): all permutations/signs of `(±1,±1,0)`; length `√2·u = a/√2 = 2.49 Å`.
- 2nd-NN star (6 vectors): `(±2,0,0),(0,±2,0),(0,0,±2)`; length `2u = a = 3.52 Å`.
- The slab normal is `[001]` (the `z`/`k` axis). In-plane axes are `[100]`,`[010]`.
- **PBC:** periodic in `i` (period `2Nx`) and `j` (period `2Ny`); **non-periodic in `k`** (free
  surfaces). `k` runs over a finite layer range `[k_min, k_max]` with a few *virtual* layers of
  padding above the top and below the bottom surface so adatoms / new layers have valid sites.
- Every group operation below preserves the parity `i+j+k` (checked in §1.3), so it maps FCC sites to
  FCC sites — the representation is closed under symmetry.

`r0`, `R_frame` (a near-identity registration rotation), and the layer range are stored once per
projection in a `LatticeFrame` (§2.1).

### 1.2 Why a *layer* symmetry group, not O_h — the central physical decision
An infinite FCC crystal has point group `O_h` (48 ops). **A slab does not.** The free surfaces make
`z` a distinguished axis: any operation that tilts `z` into the plane (the body-diagonal 3-fold
rotations, `C_4x`, `C_4y`) maps a horizontal `(001)` layer onto a vertical plane and is *not* a
symmetry of a layered slab. The operations that survive form the tetragonal subgroup fixing the
`[001]` axis:

| Region | Group | Order | Elements |
|---|---|---|---|
| Surface skin (within `n_skin` layers of a free surface) | **C₄ᵥ** | 8 | `{E, C₄z, C₂z, C₄z³, σ_x, σ_y, σ_xy, σ_x̄y}` — all fix `z→z` |
| Deep interior (≥ `n_skin` from both surfaces) | **D₄ₕ** | 16 | `C₄ᵥ ∪ (C₄ᵥ ∘ σ_h)` where `σ_h : k→−k` |
| Interior, *opt-in* `bulk_isotropic=True` | **O_h** | 48 | full cubic (merges tilted orientations) |

This is exactly the SPEC's "bulk site group vs reduced surface symmetry". The default is **C₄ᵥ /
D₄ₕ** (never `O_h`) because for a *thin* slab — our mission — two events related by a body-diagonal
`O_h` rotation genuinely differ: one "reaches toward" a surface more than the other and their barriers
differ. Merging them (as `O_h` would) is a physical error. `O_h` is correct only in the
infinite-crystal limit; I expose it as an opt-in for users running thick slabs who want minimal bulk
class counts. **The default over-splits bulk classes rather than risk a wrong merge — a deliberate,
conservative bias.** (Consequence worked out in §9.1: the "vacancy hop" splits into an in-plane class
and an inter-layer class under D₄ₕ.)

Surface events additionally fix the `z` *sign* (into the bulk is `−k` for the top surface), removing
the `σ_h` degree of freedom → C₄ᵥ, order 8. Depth-from-surface is carried as an explicit class
attribute (§3.4) so a top-layer event ≠ a subsurface event.

### 1.3 The groups as integer matrices
Each op acts on `(i,j,k)`. All 16 D₄ₕ ops (C₄ᵥ = the first 8):

```
E    (i, j, k)        C4z  (-j, i, k)      C2z  (-i,-j, k)     C4z³ ( j,-i, k)
σx   (i,-j, k)        σy   (-i, j, k)       σxy ( j, i, k)      σx̄y (-j,-i, k)
--- compose each above with σh : (·,·,-k) for the remaining 8 D4h ops ---
```

Parity check (e.g. `C4z`): `(-j)+i+k = i+k−j`; since `i+j+k` even, `i+k` and `j` share parity, so
`i+k−j` is even. ✓ All ops preserve the FCC sublattice, verified once as a unit test (§12).

---

## 2. Component 1 — Forward configuration projection (snapshot → occupancy grid)

**Input:** a full-cell snapshot `{positions[N×3] Å, types[N], cell[3×3]}`.
**Output:** an `OccupancyGrid` on the fixed reference lattice + an `UnmappableReport`.

### 2.1 Schemas
```
LatticeFrame:
  a            : float            # 3.52 Å
  u            : float            # a/2
  r0           : float[3]         # frame origin (Cartesian), fixed at cycle 0
  R_frame      : float[3][3]      # registration rotation (≈ I), refit per projection
  strain       : float[3]         # per-axis uniform strain absorbed into u_eff (≈1.0)
  N_ij         : int[2]           # in-plane periods (2Nx, 2Ny) in grid units
  k_range      : (int, int)       # (k_min, k_max) incl. virtual pad layers
  n_skin       : int = 3          # surface-skin thickness (layers) for C4v/D4h choice
  content_hash : bytes            # BLAKE2b of the calibrated frame (provenance/repro)

OccupancyGrid:
  frame        : LatticeFrame
  occ          : dict[SiteId → Occ]      # sparse; only occupied + tracked-empty sites
                                         # dense int8 array for full-slab production
  Occ ∈ {EMPTY=0, Ni=1, Cr=2, Fe=3}      # extensible; species codes fixed per run
  SiteId       : (int i, int j, int k)   # i mod 2Nx, j mod 2Ny; k absolute
  layer_of     : k ↦ min(k−k_surf_top, k_surf_bot−k)   # depth from nearest free surface

UnmappableReport:
  n_atoms          : int
  n_unmapped       : int
  frac_unmapped    : float
  residual_hist    : float[]        # snap residual distribution (Å)
  offenders        : list[(atom_idx, nearest_site, residual, reason)]
  verdict          : {CLEAN, WARN, ABORT}
```

### 2.2 Registration / drift handling
Off-lattice positions drift (CoM translation, thermal expansion, surface relaxation, slab bending).
Before snapping, per projection:

1. **CoM removal.** Subtract the mean displacement of a set of *anchor atoms* — deep-bulk, fully
   coordinated atoms (coordination = 12 within `rnei`) that are confidently on-site.
2. **Affine correction (optional, cheap).** Least-squares fit a rigid rotation `R_frame` + per-axis
   uniform strain from confidently-snapped bulk anchors to their ideal sites; apply the inverse to
   all atoms. Absorbs thermal expansion and slow drift. For an in-plane-PBC slab this is dominated by
   a uniform `z` relaxation of surface layers and a tiny CoM; `R_frame ≈ I`.
3. Persist the fitted `LatticeFrame` (with `content_hash`) into the cycle provenance.

Registration is re-estimated every cycle (the loop reloads config each cycle; cost is `O(N_anchor)`,
negligible).

### 2.3 Snap policy (greedy-by-residual bipartite assignment)
```
function PROJECT(snapshot, frame):
    frac = to_integer_fractional(snapshot.positions, frame)      # exact grid coords, real-valued
    cand = round_to_nearest_FCC_site(frac)                       # nearest (i,j,k) with i+j+k even
    resid[a] = min_image_dist(pos[a], Cartesian(cand[a]), cell)  # Å
    order = argsort(resid)                                        # best fits claim sites first
    occ = {}; unmapped = []
    for a in order:
        s = cand[a]
        if resid[a] > d_snap:                       # too far from any site
            unmapped.append((a, s, resid[a], "residual>d_snap")); continue
        if s in occ:                                # site already claimed
            s2 = nearest_free_site(a, within=d_snap)
            if s2 is None:
                unmapped.append((a, s, resid[a], "site_contested")); continue
            s = s2
        occ[s] = species_code(types[a])
    return OccupancyGrid(frame, occ), build_report(unmapped, resid)
```

- **Tolerance** `d_snap = 0.6 Å` default (≈ 0.24 × NN distance; well below the half-NN ambiguity
  radius of 1.24 Å). Surface atoms deviate most (SPEC), so `d_snap` is generous but unambiguous.
  Tunable; the residual histogram is reported so the tolerance can be audited.
- Contested sites (two atoms within `d_snap` of one site) are resolved by a **local Hungarian**
  assignment on the small contested cluster; if still unresolvable → unmapped.
- An atom snapping to a *virtual* pad layer above the top surface is an **adatom** on a new lattice
  level — mappable and fine (that is why we pad the `k_range`). Only atoms near *no* ideal site are
  unmapped (true interstitials / amorphous / dumbbells).

### 2.4 Unmappable threshold and cycle policy
```
frac_unmapped = n_unmapped / n_atoms
if frac_unmapped == 0:                      verdict = CLEAN   → proceed
elif frac_unmapped ≤ ε_warn (0.5%):         verdict = WARN    → proceed, log offenders to audit queue
else (frac_unmapped > ε_fail = 1.0%):       verdict = ABORT   → do NOT run the on-lattice leg
```
On `ABORT`, the configuration has drifted off-lattice enough that on-lattice execution is unsafe;
control returns to pyKMC (the off-lattice engine remains authoritative for that region) and the
offending atoms are written to the audit queue as candidate *off-lattice motifs* (e.g., an interstitial
dumbbell that the FCC alphabet cannot represent). `WARN` proceeds but flags — a small unmappable count
often signals an *emerging* mechanism the lattice model should be extended to cover. All thresholds
and the verdict are recorded in the cycle report.

---

## 3. Component 3 — Class identity: canonical labeling (the heart)

Given a projected event (§4 produces it), decide its class. This section defines the object, the
group action, the canonical form, and the context that is part of identity.

### 3.1 The decorated event object
```
OnLatticeEvent (pre-canonical):
  involved   : list[ SiteDelta ]            # sites whose occupancy changes
  context    : list[ SiteState ]            # spectator sites within r_id, decorated
  saddle     : list[ SaddleToken ]          # coarse mechanism descriptor(s) (§3.3)
  depth_sig  : DepthSig                      # BULK sentinel, or per-involved layer-from-surface
  provenance : EventProvenance               # §8

  SiteDelta  : (site: SiteId, occ_before: Occ, occ_after: Occ)   # occ_before ≠ occ_after
  SiteState  : (site: SiteId, occ: Occ)                          # occ_before == occ_after
  Occ ∈ {EMPTY, Ni, Cr, Fe}
```

`involved ∪ context` are all lattice sites within `r_id` of the involved-site centroid, each carrying
`occ_before` (and, for involved, `occ_after`). This decorated set + `saddle` + `depth_sig` is the
complete identity payload.

### 3.2 The context radius `r_id` — size/shape justification
Identity context = **all ideal sites within `r_id` of the event's saddle region, fully decorated
(species *and* empty)**. Default `r_id` is chosen to include 1st and 2nd NN shells of every involved
site (radius ≈ `1.1·a = 3.9 Å`, covering the NN shell at `0.71a` and the 2nd shell at `a`).

Justification, and the tradeoff, stated explicitly:
- **Physical range.** In a metal the diffusion barrier is dominated by 1st-NN bond breaking/forming,
  modulated by 2nd-NN backdrop and by the local vacancy/surface geometry. Shells 1–2 capture this;
  shell-3 species contribute < ~0.02 eV in EAM Ni-alloy tests — below the barrier-averaging noise.
- **Too small** → physically-distinct barriers collapse into one class → rate error (detected: high
  intra-class barrier variance, §7/§8).
- **Too large** → every Cr/Fe permutation in the shell is a new class → catalog explosion → most
  runtime instances are near-misses → the fallback path dominates (defeats the purpose).
- **Harvest alignment (key implementability invariant):** set `r_id ≥ rcut` (pyKMC's environment
  radius). Then my exact-class granularity is at least as fine as the granularity at which pyKMC
  *discovers and dedups* events, so I never merge two events pyKMC distinguishes. Each pyKMC reference
  row projects to exactly one of my keys (a function); several rows may share a key (that is dedup —
  I average their barriers). Set `r_id = rcut` as the default; `r_id > rcut` (finer) is allowed and
  always safe.

A diagnostic (`barrier_std` per class, §8) auto-suggests increasing `r_id` or splitting when a class
shows a barrier spread above `tol_split = 0.15 eV`.

### 3.3 Saddle mechanism token
Endpoints alone do not always fix the mechanism: two events with identical `(before,after)` occupancy
can proceed via different saddle paths (over a bridge vs through a hollow) with different barriers.
For each involved atom I quantize its saddle displacement to a **path token**: `2 × (saddle_offset)`
rounded to the integer sub-lattice (bridge midpoints and hollow centers land on well-defined
half-integer points `2×` of which are integers), canonicalized under the same group `G`. The token is
appended to the identity tuple so distinct mechanisms with equal endpoints get distinct keys. Default
resolution is coarse (integer-rounded `2×` offset) — fine enough to separate bridge/hollow, coarse
enough not to fragment classes on thermal saddle wiggle. If two mechanisms alias under the coarse
token, the intra-class barrier-variance diagnostic catches it and the token resolution is raised.

### 3.4 Depth signature
```
DepthSig = BULK                                   # all involved sites deeper than n_skin
         | SURFACE( tuple(layer_from_surface for each involved site, in canonical order) )
```
For surface events the group is C₄ᵥ (z-sign fixed into the bulk) and the depth tuple is part of the
key, so a top-layer hop, a step-edge hop, and a subsurface hop are distinct classes. For bulk events
the group is D₄ₕ and depth is irrelevant by definition, so the sentinel `BULK` collapses all depths.

### 3.5 The canonical form
```
function CANONICAL_KEY(ev: OnLatticeEvent) -> ClassKey:
    G = D4h if ev.depth_sig == BULK
        else C4v            # surface: z-sign already fixed by projection (§4.1)
        # (O_h substituted for D4h iff config.bulk_isotropic and depth_sig == BULK)
    anchors = [d.site for d in ev.involved]          # only involved sites are candidate anchors
    best = None
    for a in anchors:
        for g in G:
            entries = []
            for x in ev.involved:                    # transform + translate to integer offsets
                off = g · (x.site − a)                # exact integer 3-vector
                entries.append( (off.z, off.x, off.y, INVOLVED,
                                 code(x.occ_before), code(x.occ_after)) )
            for x in ev.context:
                off = g · (x.site − a)
                entries.append( (off.z, off.x, off.y, CONTEXT,
                                 code(x.occ), code(x.occ)) )
            for s in ev.saddle:
                toff = g · s.token_offset
                entries.append( (toff.z, toff.x, toff.y, SADDLE, s.atom_role, 0) )
            entries.sort()                            # fixed total order (lexicographic)
            T = tuple(entries)
            if best is None or T < best: best = T
    return ClassKey(group_id(G), best, ev.depth_sig)
```
- **Total order** on an entry: `(dz, dx, dy, kind, occ_before_code, occ_after_code)`, all integers →
  a strict, tolerance-free lexicographic order.
- **Canonical form** = lexicographic minimum of the sorted, translated, group-transformed decorated
  tuple over every `(anchor, g)`. It is a *complete invariant*: two events have equal `ClassKey` iff
  some `g ∈ G` and translation maps one decorated site set exactly onto the other. Proof sketch: the
  min over the group orbit is by construction invariant under `G`; translation invariance comes from
  anchoring on an involved site and the min over all anchor choices; the decorated tuple is a faithful
  encoding (invertible up to `G` and translation), so equality of canonical forms ⟺ orbit equality.
- **Collision-free keys.** The `ClassKey` *is* the canonical tuple (plus group id and depth sig). For
  compact indexing I also store `digest = BLAKE2b-256(serialize(ClassKey))`; a 256-bit digest makes
  accidental collision probability negligible, and the full tuple is retained for exact tie-breaking,
  so the design never relies on hash luck.
- **Stabilizer / orientation count.** The set of `g` achieving the min for a fixed canonical anchor is
  the event's stabilizer `Stab_G(ev)`. The number of distinct oriented realizations at runtime is
  `|G| / |Stab_G(ev)|` (orbit-stabilizer). This is computed once per class and drives §5.
- **Cross-check.** pyKMC's own `sym_matrix`/`sym_perm` (the displacement-preserving symmetries it
  found) must be a subset of my `Stab_G(ev)` up to the registration rotation. A mismatch is logged as
  a projection-validation warning.

### 3.6 What is *not* part of identity
Absolute in-plane position (translation-invariant), absolute orientation (group-invariant), the
identity of spectator atoms beyond `r_id`, and thermal saddle wiggle finer than the path token. This
is the minimal identity that preserves the barrier — the justification the SPEC asks for.

---

## 4. Component 2 — Event projection (off-lattice event record → OnLatticeEvent)

**Input:** one reference row (subset-relative `initial_positions`, `saddle_positions`,
`final_positions`, `initial_types`, `move_atom_idx`, `dra`, `sym_*`, `energy_barrier`, `idx_backward`,
ids). **Output:** an `OnLatticeEvent` (§3.1), or a rejection with reason.

### 4.1 Local registration and snap
The row's arrays are a *local cluster* (the `rcut` neighborhood of the nominal mover at min1) in the
lab frame of *its own* discovery config — not necessarily the current snapshot. I register the cluster
to an ideal FCC template locally:

1. Build the mover's 1st-NN displacement star from `initial_positions`.
2. Solve for the rotation `R_loc` best aligning that star to the ideal FCC NN star (Kabsch on the
   matched NN vectors; this reuses the same geometry IRA already trusts). Record the residual.
3. **Surface normal / z-sign.** The *missing* NN directions (the vacuum hemisphere — fewer than 12
   neighbours present) fix the outward normal; orient `+z` outward, `−z` into the bulk. This is the
   step that decides C₄ᵥ (surface) vs D₄ₕ (bulk) and removes the z-sign ambiguity for surface events.
4. Snap `initial_positions` and `final_positions` to integer FCC sites under `R_loc`. Snap residual
   feeds the gate (§8).

### 4.2 True site-change detection (do NOT trust `move_atom_idx`)
The schema names one mover, but concerted events move several atoms. I detect the true set:

```
disp = per_atom_displacement(initial_positions, final_positions, cell, pbc)   # reuse pyKMC util
movers = event_movers(disp, n_movers, matching_thr)                           # reuse pyKMC util
site_init  = snap(initial_positions);  site_fin = snap(final_positions)
involved = []
for atom in cluster:
    if site_init[atom] != site_fin[atom]:                 # ground truth: ideal site changed
        involved.append(atom)
# occupancy delta over touched sites:
touched = { site_init[a] for a in involved } ∪ { site_fin[a] for a in involved }
for s in touched:
    before = species at s in initial (or EMPTY)
    after  = species at s in final   (or EMPTY)
    if before != after: emit SiteDelta(s, before, after)
```

- `event_movers` is a *pre-filter* (displacement > `matching_thr`); the **site-change test is the
  ground truth** — an atom that vibrates > `matching_thr` but keeps its ideal site is *not* a mover
  (excluded), and an atom that quietly crosses to an adjacent site *is* (included).
- Cross-check: the nominal `move_atom_idx` must be among `involved`, and `dra` must be consistent with
  its initial→saddle displacement. If not → flag `mover_mismatch` to audit (projection anomaly).
- If `involved == ∅` (pure relaxation, no site change) → reject the row (not an executable lattice
  event).
- **Occupancy-count-change hook (future dealloying):** if an atom present in `initial` is absent in
  `final` (deletion) the SiteDelta is `(s, species → EMPTY)` with a `count_delta = −1` recorded on the
  event; the schema already expresses this (§3.1) with no break.

### 4.3 Context, saddle, depth, and the round-trip gate
- **Context:** gather all ideal sites within `r_id` of the involved centroid from the *initial*
  snapped state; decorate each with its species/`EMPTY`; mark involved vs spectator.
- **Saddle token:** for each involved atom, quantize `saddle_positions[atom]` relative to its
  endpoints into the path token (§3.3).
- **Depth signature:** from `layer_of` the involved sites and `n_skin`.
- **Round-trip gate (loop decision 5):** re-embed the OnLatticeEvent to ideal atomistic coordinates
  (§8.4), re-project, and assert the canonical key is identical and the saddle token is reproduced.
  Failure → quarantine (projection non-invertible: a bug, or a genuinely non-lattice event).

Then `CANONICAL_KEY` (§3.5) assigns the class.

---

## 5. Component 4 — Runtime matching and incremental update

**Goal:** from the occupancy grid, enumerate every executable event instance (all classes × all
orientations × all sites), maintain the BKL rate list, and update it *incrementally* after each step.
Target: ≥10⁶ steps on 10³ sites in minutes; 10⁵–10⁶ sites feasible on a node.

### 5.1 Precomputed oriented stencils (orbit generation)
For each class `c`, generate its `|G|/|Stab|` oriented realizations once (the same group used to
canonicalize):

```
Stencil (one per orientation of a class):
  class_id     : int
  orient_id    : int
  trigger_off  : SiteId          # offset of the designated trigger site (canonical anchor)
  pattern      : list[(offset: SiteId, require: Occ)]      # occ_before required at each site
  result       : list[(offset: SiteId, occ_after: Occ)]   # occupancy writes on execution
  trig_sig     : LocalSig        # cheap prefilter signature at the trigger site (§5.3)
  count_delta  : int             # 0 (canonical v1); ± for dissolution (future)
```

The **trigger site** is the canonical anchor (e.g. the lexicographically-first involved site, or the
vacancy). Scanning is keyed on the trigger site so each instance is counted once.

### 5.2 Data structures
```
ClassCatalog   : class_id → { ClassKey, Ea, ν0, k, stencils[], provenance }
OccupancyGrid  : §2.1 (dict for sparse defects; dense int8[N] for full slab)
ActiveSites    : set[SiteId]   # sites adjacent to any EMPTY site or on the surface skin
                               # ONLY these can trigger a nontrivial event
EventList      : array of Instance(instance_id, class_id, orient_id, trigger_site, k)
RateTree       : Fenwick/segment tree over EventList.k   → O(log M) selection, O(log M) update
TouchIndex     : SiteId → set[instance_id]   # every instance whose pattern covers this site
TrigIndex      : LocalSig → list[(class_id, orient_id)]   # prefilter (§5.3)
```

### 5.3 The prefilter — why per-step cost is independent of N
Two facts collapse the cost:

1. **Only `ActiveSites` can trigger events.** A fully-coordinated bulk site with all-occupied
   neighbours hosts no hop (nothing to move into). `|ActiveSites| ≈ surface area + vacancy shells ≪
   N`. For 1–2 vacancies in a 10³–10⁶-site slab this is a few dozen to a few thousand sites.
2. **A cheap local signature shortlists candidate class-orientations.** At a trigger site compute
   `LocalSig = (occ_here, sorted 1st-NN occupancy multiset, surface-layer)`. `TrigIndex[LocalSig]`
   returns only the handful of stencils whose trigger pattern is compatible — not all `C·|G|`. The
   full stencil match (checking every offset) then runs on `O(1)` candidates.

### 5.4 Build and incremental update
```
function BUILD(grid):
    ActiveSites = compute_active(grid)
    for s in ActiveSites:
        for (c, o) in TrigIndex[LocalSig(grid, s)]:
            if MATCH(stencil[c,o], grid, s):                 # all offsets satisfy require
                add_instance(c, o, s, k=Catalog[c].k)
    build RateTree, TouchIndex

function STEP():
    inst = RateTree.select(rand())                            # BKL: O(log M)
    Δsites = apply_result(stencil[inst], grid)                # write occ_after; O(stencil)
    advance_clock(−ln(rand)/RateTree.total)                   # KMC time
    accumulate_coverage(inst)                                 # §7.5, O(1)
    # --- incremental rebuild of the dirty region ---
    dirty = ⋃_{s∈Δsites} sites_within(r_id + stencil_radius, s)      # O(1) sites (bounded)
    for s in dirty ∩ EventList.trigger_sites (via TouchIndex): remove_instance(s)
    update ActiveSites incrementally over Δsites
    for s in dirty ∩ ActiveSites:
        for (c,o) in TrigIndex[LocalSig(grid,s)]:
            if MATCH(stencil[c,o], grid, s): add_instance(c,o,s)
    RateTree.update(changed entries)                          # O(#changed · log M)
```

`dirty` is bounded by the event's spatial extent + `r_id` — a **constant** number of sites (a few
dozen), independent of `N`. So **per-step work is `O(|dirty| · Ĉ · s + log M)`** where `Ĉ` is the
*prefiltered* candidate count per site (`O(1)` amortized) and `s` the stencil size (~10–30). This is
the key scaling result: cost per step does not grow with system size (at fixed defect density).

### 5.5 Correctness of incrementality
An instance can only appear, disappear, or change rate if some site in its pattern changed occupancy.
All changed sites are in `Δsites`; every instance touching them is found via `TouchIndex` and any
instance that could newly appear has its trigger in `dirty ⊇ Δsites ⊕ r_id`. Hence the incremental
rescan is exhaustive over exactly the instances that can change — no stale or missed instances. A
`STRICT_CHECK` debug mode periodically rebuilds from scratch and asserts EventList equality (§12).

### 5.6 Scale
- 10³ sites, 1–2 vacancies: `M` (live instances) ~ 10²–10³; per step ~ hundreds of primitive ops +
  `O(log M)`. 10⁶ steps in tens of seconds to a couple of minutes with a compiled inner loop
  (Numba/Cython on `MATCH`/`LocalSig`); pure-Python is minutes-to-tens-of-minutes → compile the inner
  loop.
- 10⁵–10⁶ sites: dense `int8` grid (`O(N)` memory); `ActiveSites`/`M` scale with surface+defect count,
  not `N`. Feasible on one node. Late-stage dealloying (porous, high empty-fraction) degrades
  `|ActiveSites|→O(N)` — addressed by domain-decomposed/asynchronous parallel KMC as an extension
  (§13).

---

## 6. Component 5 — Rate assignment

`k [ps⁻¹] = ν₀ [ps⁻¹] · exp(−Ea / (k_B T))`, `k_B = 8.6173303e-5 eV/K`, `Ea, ν₀` temperature-
independent, `T` the run temperature. Matches pyKMC's `rate_from_prefactor` to machine precision;
units are ps⁻¹ throughout (fallback prefactor `k0 = 1.0` = 1 THz, as in pyKMC).

### 6.1 Exact-lookup path
Instance's `ClassKey` ∈ `ClassCatalog` → use the class's `Ea` and `ν₀`:
- `Ea` = provenance-robust mean of contributing pyKMC barriers (trimmed mean if `n_contrib ≥ 5`).
- `ν₀` = geometric mean of contributing prefactors, or `k0` if none (HTST disabled).
- `k` precomputed per class at run `T`; stored on the class and copied to instances.

### 6.2 Fallback regression (near-miss) — nothing silently zero
An instance whose local occupancy *admits a move* (e.g. an atom with an empty NN) but whose
`ClassKey ∉ Catalog` is a **near-miss**. It still gets a nonzero rate:

- **Descriptors** (cheap, physical, occupancy-only — bond-counting / local-composition style):
  `mover species; mover coordination (init); target-site coordination (final); per-species counts in
  mover 1st-shell (init) and target 1st-shell; #empty in 1st-shell; surface layer; Δcoordination;
  #involved sites; saddle path-token class`. Computable from the grid in `O(shell)`.
- **Model:** `Ea = f(descriptors)`. Start with **ridge regression on bond-count features**
  (interpretable, matches broken-bond barrier theory); upgrade to gradient-boosted trees once the
  catalog is large (`n_class ≳ 200`). Fit on all harvested `(class → Ea)` pairs, weighted by
  `n_contrib` and inverse `barrier_std`. `ν₀_hat` = catalog median (or a small separate regression).
- **Flag:** the instance is marked `provisional`; its descriptor signature is counted in the coverage
  report and becomes a **priority seed** for the next pyKMC leg (mapped back to atomistic coords via
  §8.4 and handed to pARTn to discover the true barrier).
- **Bounds:** clamp `Ea_hat` to `[emin_event, emax_event]` (pyKMC's own thresholds); a prediction
  outside bounds → `high_uncertainty`, clamp, prioritize hardest.
- **Refit cadence:** after every harvest cycle, or when `new_classes_this_cycle > τ_refit`. Predictions
  are memoized per descriptor signature (repeated near-misses in a run cost one prediction). Model +
  version stored in provenance for reproducibility.

### 6.3 Two-tier guarantee
Every executable instance carries a rate: exact if the class is known, regression+flag if not. The
flag guarantees the loop closes on it. No environment silently contributes zero flux (SPEC decision 4).

---

## 7. Component 6 — Novelty and harvest round trip

### 7.1 Mapping new pyKMC rows into classes
Each new reference row → §4 project → §3 canonicalize → look up in `ClassCatalog`:
- **Key present → new instance of a known class.** Append `(Ea, ν₀, source_cycle, source idx_ref)` to
  provenance; update running `barrier_mean`, `barrier_std`, `ν₀_mean`; recompute `k`. Outlier barrier
  (`|Ea − mean| > 0.25 eV`, matching pyKMC's `is_new_event` tol) → flag class for audit (under-resolved
  context — candidate `r_id` increase / split).
- **Key absent → new class.** Create it; run auto-gates (§8.2); admit if gates pass; **first instance
  of a brand-new class is copied to the audit queue** even when gates pass (SPEC decision 5). It begins
  carrying flux the next evolve leg.

### 7.2 Forward/backward pairing (microscopic reversibility)
pyKMC pairs events via `idx_backward`. The on-lattice reverse of an event is the *same site set with
`occ_before ↔ occ_after` swapped* (and the saddle token unchanged — the saddle is shared). I:
- Canonicalize the reverse independently → `reverse_key`; store the link on both classes.
- **Invariants enforced:** `key(reverse(reverse(e))) == key(e)`; the pyKMC-paired row must project to
  `reverse_key` (else `broken_pair` → audit); both `Ea_F, Ea_R` in bounds and satisfying the asymmetry
  gate (§8.2). This makes the on-lattice engine reversible: whenever a forward instance fires, its
  reverse instance is enumerable in the flipped state, so the chain can return — required for correct
  equilibrium sampling and basin escape.

### 7.3 New-class vs new-instance decision — summary
```
project(row) → key
if key in catalog:
    if |Ea_row − catalog[key].mean| ≤ 0.25:  new_instance (merge, average)
    else:                                     new_instance + OUTLIER flag → audit
else:                                         new_class → gates → (admit | quarantine) + audit(first)
```

### 7.4 Convergence signal
`new_classes_per_cycle` is the count of `key absent` events per cycle. The loop's convergence
criterion (SPEC decision 1) is `new_classes_per_cycle → 0`.

### 7.5 Coverage-report metrics (cheap O(1)-per-step accumulators, SPEC decision 6)
Accumulated during the evolve leg, emitted at its end:
- `fallback_flux_fraction` = `Σ k(provisional selected) / Σ k(selected)` — two running sums.
- `observed_unharvested_signatures` = histogram `descriptor_sig → (count, summed_flux)` — one dict
  update per near-miss.
- `composition` = running per-species occupancy counts (updated on each SiteDelta).
- `SRO_drift` = Warren-Cowley `α₁` from running like/unlike 1st-shell bond counts, updated
  incrementally as sites flip (Δ bond counts over `Δsites` only).
- `classes_observed` vs `classes_harvested`; `new_classes_per_cycle`.

All are `O(1)` or `O(|Δsites|)` per step — no full-grid sweep.

---

## 8. Component 7 — Provenance and curation hooks

### 8.1 Provenance schema
```
ClassProvenance:
  class_key         : ClassKey
  canonical_form    : tuple           # exact (collision-free)
  digest            : bytes(32)
  first_seen_cycle  : int
  contributing      : list[(cycle, source_idx_ref, Ea, ν0, snap_resid, roundtrip_resid)]
  barrier_mean      : float
  barrier_std       : float
  ν0_mean           : float
  k                 : float           # at run T
  group_used        : {C4v, D4h, Oh}
  r_id_used         : float
  orientation_count : int             # |G|/|Stab|
  reverse_key       : ClassKey
  gate_outcomes     : {bounds, pair_consistency, snap_residual, roundtrip}  # each PASS/FAIL/value
  admit_status      : {ADMITTED, PROVISIONAL, QUARANTINED}
  count_delta       : int             # 0 (v1); occupancy-count-change support
```

### 8.2 Auto-gates (precise; SPEC decision 5)
Applied to every candidate class/instance at harvest:
- **`barrier_bounds`**: `emin_event ≤ Ea ≤ emax_event`. FAIL → QUARANTINE.
- **`pair_consistency`**: `reverse_key` exists; both `Ea_F, Ea_R ∈ bounds`; asymmetry rejected exactly
  as pyKMC (`dE_f > energy_asymmetry·backward_emin AND dE_b < backward_emin` → fail). FAIL → audit.
- **`snap_residual`**: max event-cluster snap residual ≤ `d_snap_event = 0.6 Å` and local registration
  residual small. FAIL → QUARANTINE + route to `off_lattice_motif` list.
- **`roundtrip`** (§4.3): re-embed → re-project reproduces the canonical key and saddle token. FAIL →
  QUARANTINE.
Pass all → ADMITTED (carries flux immediately). Brand-new class → *also* audit-queued (human confirm)
even on full pass.

### 8.3 Audit queue interface
```
AuditItem:
  item_type   : {NEW_CLASS, GATE_FAIL, OUTLIER_BARRIER, UNMAPPABLE_ATOMS, BROKEN_PAIR, MOVER_MISMATCH}
  class_key   : ClassKey | null
  cycle       : int
  payload     : { atomistic_snippet, saddle, occupancy_before, occupancy_after }   # for visualization
  gate_results: {...}
  suggested   : str            # e.g. "raise r_id", "extend site alphabet (interstitial)"
  resolution  : {PENDING, APPROVE, REJECT, RELABEL}    # human/rule sets this
```
Append-only (parquet/CSV). The KMC engine reads only `ADMITTED`/`PROVISIONAL` classes; `QUARANTINED`
are excluded from execution (their flux would be wrong) but their descriptor signatures still count in
the coverage report — so they are never silently zero, they become high-priority discovery targets. A
CLI/notebook hook renders the atomistic event and offers approve/reject/relabel.

### 8.4 Reverse mapping (occupancy → atomistic config for pyKMC) — deterministic & reproducible
```
function EMIT_ATOMISTIC(grid, frame, region=None):
    atoms = []
    for (site, occ) in grid.occ where occ != EMPTY and (region is None or site in region):
        atoms.append( (species(occ), Cartesian(site, frame)) )   # EXACT ideal coordinate
    cfg = Atoms(atoms, cell=frame→cell, pbc=[True,True,False])
    return cfg, BLAKE2b(serialize(cfg))                          # content hash for repro
```
- Places each occupied site's species at its **exact ideal Cartesian coordinate**; empty sites → no
  atom. No randomness → **byte-reproducible**: same `(grid, frame)` ⇒ identical output (asserted via
  hash). This is handed to pyKMC's restart (`config.control.reference_table` + the atomistic config);
  pyKMC then minimizes/relaxes it — well-defined because it starts from clean ideal sites.
- For a **near-miss seed** handed to pyKMC for discovery, emit the local neighborhood centered on the
  flagged site (ideal coords) so pARTn's search starts from a reproducible minimum.
- The frame + config hash are stored in the cycle provenance, making a cycle byte-reproducible.

---

## 9. Worked examples

### 9.1 Vacancy hop (2-site) — projected → classified → matched → executed

**Setup.** Bulk region. Vacancy at `q`, a Ni atom at NN site `p` hops `p→q`. Integer coords
`p=(0,0,0)`, `q=(1,1,0)` (an in-plane ⟨110⟩ NN). Off-lattice row: `move_atom_idx` → the Ni;
`energy_barrier = 0.65 eV`, `ν₀ = 5 THz`; `final_positions` show the Ni at `q`, vacancy now at `p`.

**Projection (§4).** `disp` large only for the Ni; `event_movers`→{Ni}; site-change test: `site_init(Ni)=p
≠ site_fin(Ni)=q`. Touched sites `{p,q}`:
```
involved = [ SiteDelta(p, Ni, EMPTY), SiteDelta(q, EMPTY, Ni) ]
context  = shells 1–2 around {p,q}, all Ni (bulk)         depth_sig = BULK → G = D4h
saddle   = [ token at the p→q bridge ]
```

**Classification (§3.5).** Try anchors `{p,q}` × 16 D₄ₕ ops; take the lexicographic min. The canonical
form encodes "a Ni moves into an adjacent **in-plane** ⟨110⟩ empty NN, bulk, all-Ni surroundings".
Orbit of `(1,1,0)` under D₄ₕ = `{(1,1,0),(−1,1,0),(−1,−1,0),(1,−1,0)}` → **orientation_count = 4**.
Crucially the *inter-layer* hop `(1,0,1)` is a **different** orbit (size 8) → a **different class**
under D₄ₕ. So the naive "vacancy hop" splits into two bulk classes (in-plane vs inter-layer) — the
D₄ₕ-vs-O_h consequence from §1.2, physically correct for a thin slab. Class key `K_hop_bulk_Ni_inplane`.

**Matching (§5).** For the vacancy at `q`, the in-plane-hop stencil instantiates at each of the 4
in-plane NN of `q` that hold a Ni; the inter-layer stencil at the 8 slanted NN. Each becomes an
EventList entry with `k = 5·exp(−0.65/(k_B·T))` ps⁻¹.

**Execution (§5.4).** BKL selects one, say the `p→q` instance. Apply `{p→EMPTY, q→Ni}`;
`Δsites={p,q}`; `dirty` = shells around `p,q`. Rescan: the vacancy now at `p` offers fresh hops; old
`q`-triggered instances removed. Coverage: exact-class flux; SRO/composition updated. Clock advanced.

### 9.2 3-site concerted ring on the surface — projected → classified → matched → executed

**Setup.** Top layer (`z=0`, vacuum at `z>0`). A vacancy at `q=(0,0,0)`; a Ni atom `A` at
`p1=(1,1,0)` and a Cr atom `B` at `p2=(2,0,0)` execute a concerted cyclic shear: `A: p1→q`,
`B: p2→p1`, vacancy `q→p2`. This is a collective mechanism absent from textbook single-hop catalogs —
exactly the kind pyKMC discovers. Off-lattice row names **only `A`** in `move_atom_idx`, but
`final − initial` shows both `A` and `B` moved.

**Projection (§4.2 — why not trusting `move_atom_idx` matters).**
`event_movers`→{A,B}; site-change test confirms both change ideal site:
```
involved = [ SiteDelta(p1, Ni, Cr),      # B (Cr) lands where A (Ni) was
             SiteDelta(q,  EMPTY, Ni),    # A (Ni) fills the vacancy
             SiteDelta(p2, Cr, EMPTY) ]   # vacancy ends at p2
context  = shells 1–2 around {q,p1,p2}, incl. the EMPTY vacuum sites above (surface)
depth_sig = SURFACE( layers of q,p1,p2 = (0,0,0) )   → G = C4v (z fixed into bulk = −k)
saddle   = [ tokens for A and B (the ring bulges over the bridges) ]
```
A naive 1-mover projection would have emitted only `A`'s hop and corrupted the event (wrong site set,
wrong barrier on the clock). The site-change ground truth recovers all three deltas.

**Classification (§3.5).** Anchors `{q,p1,p2}` × 8 C₄ᵥ ops → canonical min → key
`K_ring_surf_NiCr_L0`. The stabilizer is trivial (the Ni/Cr decoration and the ring chirality break
all mirrors and rotations), so **orientation_count = 8** (4 rotations × 2 chiralities). The reverse
event (Cr `p1→p2`, Ni `q→p1`... i.e. occ swapped) canonicalizes to a distinct `reverse_key`, linked
for reversibility (§7.2). `Ea = 0.42 eV`, `ν₀ = 6 THz` from provenance.

**Matching (§5).** Scan surface `ActiveSites`. Wherever a vacancy has the `(Ni at +⟨110⟩, Cr at
+⟨200⟩)` pattern in one of the 8 orientations, instantiate with trigger = the vacancy `q`,
`k = 6·exp(−0.42/(k_B·T))`. If only an *all-Ni* ring had been harvested, a Ni-Cr ring is a **near-miss**
→ fallback regression on bond-count descriptors (mover Ni, second-mover Cr, surface layer 0,
coordinations) → `Ea_hat`, flagged `provisional`, seeded to the next pyKMC leg (§6.2, §8.4).

**Execution (§5.4).** Apply the 3-site occupancy change atomically: `{q→Ni, p1→Cr, p2→EMPTY}`.
`Δsites={q,p1,p2}`; `dirty` = union of their shells; rescan. Coverage: a Cr moved toward the surface
(dealloying-relevant) → composition/SRO accumulators updated. Because the reverse instance is now
enumerable in the flipped state, detailed balance is preserved.

---

## 10. Complexity analysis

Let `N`=sites, `D`=defect/surface active-site count, `C`=classes, `|G|`≤48 (≤16 default), `s`=stencil
size (~10–30), `M`=live instances, `Ĉ`=prefiltered candidates per site (`O(1)` amortized).

| Operation | Cost | Notes |
|---|---|---|
| Projection (snapshot) | `O(N log N)` | KDTree snap + greedy assignment; once per cycle |
| Registration | `O(N_anchor)` | anchors only; `≈O(N)` worst |
| Event projection (per row) | `O(s + |G|·|involved|)` | snap + canonicalize; harvest-time, rare |
| Canonical key (per event) | `O(|G|·|involved|·s·log s)` | min over anchors×group; harvest-time |
| Stencil generation (per class) | `O(|G|·s)` | once per class |
| Build EventList | `O(D·Ĉ·s + M log M)` | scan active sites only |
| **KMC step (matching + select)** | **`O(|dirty|·Ĉ·s + log M)`** | **independent of `N`** at fixed defect density |
| Coverage accumulate (per step) | `O(|Δsites|)` | running sums / SRO deltas |
| Fallback predict (per new sig) | `O(descriptor)` | memoized per signature |
| Reverse mapping emit | `O(N_occ)` | once per handoff |

**Headline:** per-step cost is `O(1)` in `N` (bounded `|dirty|`, prefiltered candidates, `O(log M)`
selection). 10⁶ steps on 10³ sites → tens of seconds–minutes with a compiled inner loop. Memory:
`O(N)` grid (dense) + `O(M)` list. 10⁵–10⁶ sites feasible on a node; the only scaling risk is
`|ActiveSites|→O(N)` in the porous late-dealloying limit (§13, addressed by parallel KMC extension).

---

## 11. Failure-mode table

| # | Failure | Cause | Detection | Response |
|---|---|---|---|---|
| 1 | Off-lattice drift beyond tol | thermal/CoM/strain | `frac_unmapped > ε_fail` | ABORT leg → back to pyKMC; log frame |
| 2 | Amorphization / interstitial dumbbell | non-FCC motif | clustered unmapped atoms | route to `off_lattice_motif`; extend alphabet (future) |
| 3 | Concerted event, `move_atom_idx` wrong | schema names 1 mover | detected movers ≠ {nominal} | use detected site-change set; flag `mover_mismatch` |
| 4 | Pure relaxation mis-read as event | vibration > `matching_thr` | `involved == ∅` after site test | reject row (no site change) |
| 5 | Wrong surface-normal / z-sign | ambiguous local registration | inconsistent depth signature | default to smaller group C₄ᵥ (safe over-split) |
| 6 | Class explosion | `r_id` too large / high decoration | catalog growth not converging, high fallback | reduce outer-shell to occupancy-only; diagnostic |
| 7 | Under-resolved class | `r_id` too small | `barrier_std > 0.15 eV` in a class | audit → raise `r_id` / split class |
| 8 | Key collision | — | impossible by construction | canonical tuple *is* the key; 256-bit digest backup |
| 9 | Saddle-mechanism aliasing | coarse path token | barrier variance in a class | raise token resolution |
| 10 | Fallback `Ea` out of bounds | poor regression | clamp check | clamp to `[emin,emax]` + high-priority flag |
| 11 | Detailed-balance violation | inconsistent F/B barriers | `pair_consistency` gate | audit; quarantine pair |
| 12 | `a ≠ 3.52` / sheared cell | wrong lattice spec | large registration residual | recalibrate frame; fail closed if residual persists |
| 13 | Two atoms → one site | local compression | assignment conflict | local Hungarian; unresolved → unmapped |
| 14 | Event straddles x/y PBC seam | boundary wrap | integer mod + min-image anchor | canonical offsets are local → no wrap needed |
| 15 | Occupancy-count-change (dealloying) | atom deletion | `count_delta ≠ 0` | schema supports; v1 executes via stub selection (future) |
| 16 | Incremental list desync | matching bug | periodic `STRICT_CHECK` full rebuild | assert equality; fail test |

---

## 12. Test plan

**Unit.**
- *Group correctness:* verify D₄ₕ/C₄ᵥ multiplication tables (closure, inverses), FCC-parity
  preservation for all ops, orbit sizes (in-plane ⟨110⟩ orbit = 4, slanted = 8 under D₄ₕ), and that
  `CANONICAL_KEY` returns the true lexicographic minimum (brute-force check on small events).
- *Canonicalization invariance (property test):* for a fixed event, apply every `g∈G`, random
  in-plane translations, and species relabelings that respect symmetry → identical key; two genuinely
  different decorated events → different keys.
- *Projection:* synthetic ideal configs + Gaussian thermal noise `< d_snap` → 100% correct snap; noise
  `> d_snap` → flagged; planted vacancy/adatom/step → detected at the right site/layer.
- *Mover detection:* hand-built 2-/3-/4-site concerted events with `move_atom_idx` deliberately wrong
  → correct site-change set recovered.
- *Rate:* `k = ν₀·exp(−Ea/(k_B T))` matches pyKMC `rate_from_prefactor` to machine precision; units
  ps⁻¹; `k0` fallback == 1.0.

**Round-trip.**
- Occupancy → `EMIT_ATOMISTIC` (ideal) → re-project → bitwise-identical occupancy.
- Event → embed → re-project → identical `ClassKey` and saddle token (the §8.2 gate as a test).
- `reverse(reverse(event)) == event`; pyKMC-paired row projects to `reverse_key`.
- `EMIT_ATOMISTIC` determinism: same grid ⇒ identical content hash.

**Statistical / integration.**
- *Physics match:* run the on-lattice engine on a small NiCr(100) slab with a catalog harvested from a
  short pyKMC run; compare vacancy diffusivity `D` (MSD Arrhenius slope) and residence-time
  distributions against a *direct* pyKMC run at the same `T` → agree within statistical error.
- *Detailed balance:* with no driving force, on-lattice occupancy statistics and SRO converge to the
  Boltzmann distribution of the known energy model; forward/backward event counts balance.
- *Loop convergence:* `fallback_flux_fraction` decreases and `new_classes_per_cycle → 0` across cycles.
- *Scaling:* per-step time vs `N` (10³→10⁶) at fixed defect density → confirm `O(1)`-per-step; measure
  steps/s (target ≥10⁶ steps on 10³ sites in minutes).
- *Refinement vs pyKMC:* on a shared dataset, verify my classes *refine* pyKMC's `event_id` groupings
  (each pyKMC group maps into one or more of my classes, never a wrong merge) and that barrier variance
  within my classes ≤ within pyKMC's.
- *`STRICT_CHECK`:* interleave periodic from-scratch rebuilds during a long run; assert EventList
  equality with the incremental path.

---

## 13. Self-declared weaknesses

1. **D₄ₕ over-splits bulk classes** vs the infinite-crystal `O_h` → more classes to harvest in thick
   or deep-bulk regimes. Mitigated by the opt-in `bulk_isotropic=O_h` mode and by the fact that for the
   *thin-slab* mission the split is physically *correct*. Still, a user on thick slabs pays a class-count
   tax unless they flip the flag.
2. **Only as good as the snap.** Strongly reconstructed surfaces (missing-row, herringbone,
   large rumpling) may not sit on the ideal FCC grid → those events land in the audit / off-lattice
   bucket; the on-lattice engine cannot *execute* a reconstruction. This is a hard boundary of any
   on-lattice model, made explicit rather than hidden.
3. **Saddle token is heuristic.** Two distinct mechanisms with identical endpoints and identical coarse
   token would alias into one class (rare; caught by barrier variance, but only after enough samples).
   Finer tokens risk fragmenting classes on thermal wiggle.
4. **Fallback is atom-centric.** Bond-count descriptors featurize single-atom hops well but multi-atom
   concerted *novel* events poorly → their fallback rates are the least reliable. They are always
   flagged and prioritized, so the loop self-corrects, but a run dominated by unharvested concerted
   events leans on weak estimates until the next pyKMC leg.
5. **Single global `r_id`.** Ideally per-class adaptive (some barriers need shell-3). v1 provides a
   variance diagnostic and a manual/audited `r_id` bump, not automatic per-class radius growth.
6. **Ideal-site minimum assumption.** The reverse mapping is exact, but pyKMC's subsequent minimization
   can relax an emitted ideal config into a slightly different basin than the class assumed, so a
   harvested barrier may occasionally attach to a neighbouring class. Mostly benign; caught by the
   round-trip gate, but not impossible.
7. **Runtime trusts precomputed stencils.** Canonicalization is exact, but at runtime I use orbit-
   generated stencils for speed; a bug in stencil generation would not be caught by the canonical form
   itself (only by `STRICT_CHECK` / integration tests).
8. **Orthorhombic ⟨100⟩ frame assumed.** Rotated/sheared cells or vicinal (stepped) surfaces need a
   frame and group generalization (a different layer group) not implemented in v1.
9. **`ActiveSites` degrades under high empty-fraction.** The `O(1)`-per-step guarantee assumes a modest
   defect density; the porous late-dealloying end-state pushes `|ActiveSites|→O(N)`. Acceptable for the
   early campaign; needs the domain-decomposed/asynchronous parallel-KMC extension for late stages.
10. **Occupancy-count-change is schema-ready, not loop-ready.** The class machinery, `count_delta`, and
    `EMIT_ATOMISTIC` handle deletion, but the BKL competition, mass-balance bookkeeping, and Erlebacher
    rate integration for dissolution are stubs in v1 — deliberately, since the loop is diffusion-only
    for now, but they are the first extension and the schema was designed so no re-harvest is needed.
```
