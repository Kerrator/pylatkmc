# Design "pattern" — a precompiled-local-pattern on-lattice KMC engine for harvested FCC dealloying catalogues

**Design name:** `pattern`
**Angle:** the precompiled-local-pattern tradition — per-site executable process lists,
lattice patterns compiled ahead of the run, incremental invalidation of the affected patterns
after every executed event.

---

## 0. Thesis and lineage

Classical on-lattice KMC codes (the n-fold-way of Bortz–Kalos–Lebowitz; compiled process-list codes
in the kmos/lattice_kmc/SPPARKS lineage; cluster-expansion KMC) get their speed from one idea: the
set of *possible* elementary moves is small, local, and known before the run, so it can be
**compiled into per-site templates** whose matches are enumerated once and then **repaired only where
the lattice actually changed**. Per step the cost is a small constant, independent of system size.

The twist here is that the process list is **not hand-written**. It is *harvested* from an
off-lattice autonomous discovery engine (pyKMC: pARTn saddle searches + graph/coordination
environment classification + IRA point-set reuse). pyKMC emits relaxed, atom-only, subset-relative
event records; this design turns each record into a **compiled lattice pattern** — a spatial stencil
of occupancy predicates plus an occupancy-change set plus a rate — pre-expanded over the slab's point
group, indexed for cheap matching, and repaired incrementally. The whole engine is a
catalogue-completion machine that alternates with pyKMC through file-based handoffs.

Everything below is organised as: the lattice/site model and data structures first (Section 1), then
the seven required components (Sections 2–8), then two fully worked examples (Section 9), consolidated
complexity (Section 10), failure modes (Section 11), test plan (Section 12), self-declared weaknesses
(Section 13), and fit/extensibility (Section 14).

The design's signature ideas, up front:

1. **Compile the catalogue to oriented patterns** (Section 5.1): each class → up to |G| oriented
   stencils, deduplicated exactly by its own symmetry (the discrete analogue of pyKMC's
   `sym_matrix`/`sym_perm`).
2. **Anchor at the rarest predicate** (Section 5.2): patterns are bound to their scarcest site
   (a vacancy/adatom/minority species), so enumeration scales with defects, not atoms.
3. **Per-site process lists + group-BKL** (Section 5.3): O(log C) selection, O(1) instance turnover.
4. **Incremental invalidation by pattern support** (Section 5.4): only anchors within the pattern
   support radius of a changed site are repaired — a fixed, size-independent ball per step.
5. **Geometry-aware identity that reconciles with pyKMC's graph hash** (Section 4): the discrete
   canonical form is *finer than the graph certificate where the surface breaks symmetry* and
   *coarser where the bulk restores it* — correctly splitting surface-anisotropic hops that share a
   graph hash and merging bulk hops that do not.
6. **Core/descriptor split with data-driven class refinement** (Section 4.4): a minimal
   *executability* stencil drives matching; a wider *descriptor* shell drives rate and is promoted
   into identity only when measured barriers demand it.

---

## 1. Lattice reference frame, site model, and core data structures

### 1.1 Integer FCC embedding

FCC with lattice constant `a ≈ 3.52 Å`. Every site is an integer triple `(i,j,k)` with
`i+j+k ≡ 0 (mod 2)`; its ideal Cartesian position in the registered frame is

```
r(i,j,k) = origin + (a/2) · R · (i, j, k)ᵀ
```

where `R` is the frame orientation (≈ identity for a cube-axis-aligned (100) slab). This is the
standard "FCC = even-parity sublattice of the simple-cubic (a/2) lattice" embedding. Verified facts
this design relies on (checked numerically):

- **12 nearest neighbours** = the 12 permutations of `(±1, ±1, 0)`; all preserve even parity;
  nn distance `= (a/2)√2 = 2.489 Å`.
- **6 second neighbours** = permutations of `(±2, 0, 0)`; distance `= a = 3.52 Å`.
- **(100) slab**, surface normal along the `k` axis (call it `z`): each integer `k` is one atomic
  layer; within a layer `i+j ≡ k (mod 2)`. A bulk atom's 12 nn split as **4 in-layer**
  (`(±1,±1,0)`) **+ 4 to k+1 + 4 to k−1**. A top-surface atom keeps 4 in-layer + 4 below =
  **coordination 8**, the correct FCC(100) surface coordination.

Neighbour access at runtime is **integer table lookup, never a KD-tree** — this is the central
speed win over the off-lattice engine.

### 1.2 Occupancy alphabet and the site domain

```
Occ = uint8 enum { EMPTY=0, Ni=1, Cr=2, Fe=3, ..., OUTSIDE=255 }
```

- `EMPTY` — a lattice site with no atom. A bulk `EMPTY` with occupied neighbours is a **vacancy**;
  an above-surface `EMPTY` with occupied neighbours is an **adatom target**; an `EMPTY` with **no**
  occupied neighbour within `rcut` is inert **vacuum**.
- `Ni/Cr/Fe/...` — an occupied site; the alphabet grows freely for ternary (extensibility).
- `OUTSIDE` — a parity-forbidden or out-of-domain slot (sentinel; never matches an occupancy
  predicate). Used to fold the free ±z boundary cleanly.

The **active domain** is the integer box `i∈[0,2Nx), j∈[0,2Ny), k∈[k_bot−m, k_top+m]` where
`k_top/k_bot` are the outermost occupied layers and `m` (≈ 3 layers) is an **adatom/vacuum margin**
so adatom hops and above-surface concerted events have target sites. In-plane axes are **periodic**
(`pbc = (True, True, False)`); `±z` is **free**. PBC is folded into the site↔id map by modular
arithmetic on `i,j`; missing `±z` neighbours are `OUTSIDE`.

### 1.3 Data structures

```python
# ---- Registered frame (re-fit each cycle; see §2) ----
@dataclass
class LatticeFrame:
    a: float                    # Å, registered
    R: float[3,3]               # cube-axis -> lab orientation (≈ I)
    origin: float[3]            # lab position of site (0,0,0)
    Nx, Ny, Nz: int             # box half-extents in integer-site units
    pbc: bool[3]                # (True, True, False)
    layer_z: float[Nz]          # detected z of each layer k (absorbs surface relaxation)
    k_top, k_bot: int           # outermost occupied layers at cycle start (depth reference)

# ---- The occupancy grid (dense, id-linear) ----
@dataclass
class Grid:
    frame: LatticeFrame
    occ:   Occ[n_sites]         # id -> occupancy
    valid: bool[n_sites]        # parity-correct AND in domain
    nbr12: int32[n_sites, 12]   # precomputed nn ids (OUTSIDE sentinel at free boundary), O(N) once
    nbr2:  int32[n_sites, 6]    # 2nd-shell ids (for descriptors / context)
    depth: int16[n_sites]       # min layers to the nearest free surface (bulk = large)
    site_of_id: (i,j,k)[n_sites] # id -> integer triple  (and inverse id_of(i,j,k))
```

`id = linear_index(i,j,k)` is a bijection over the dense box; `nbr12`/`nbr2` are built once with
integer arithmetic + in-plane wrap (cost `O(18·N)`, no geometry). `depth[s]` is computed once by a
BFS from the vacuum layer and updated locally when the surface recedes. Everything a match needs —
occupancy, neighbours, depth — is `O(1)` array access.

```python
# ---- Catalogue: an event class ----
@dataclass
class OccPredicate:
    kind: {SPECIES, EMPTY, OCC_ANY, WILDCARD}
    species: frozenset[Occ]     # for SPECIES (grey mode collapses every SPECIES -> OCC_ANY)

@dataclass
class StencilSite:  off: (int,int,int);  pred: OccPredicate
@dataclass
class DeltaSite:    off: (int,int,int);  before: Occ;  after: Occ

@dataclass
class EventClass:
    class_id:   bytes16         # blake2b of the canonical form (§4)
    regime:     {Oh, C4v}       # symmetry group used for canonicalization
    anchor_depth: DepthPred     # BULK | SUBSURF(d) | SURFACE(coord) — pins surface vs bulk
    core:       list[StencilSite]   # minimal executability pattern (drives MATCHING)
    context:    list[StencilSite]   # wider descriptor shell (identity + rate; drives SPLIT)
    delta:      list[DeltaSite]     # occupancy changes, canonical orientation
    delta_atoms: int            # net atom-count change: 0 diffusion, -1 dissolution (schema hook)
    Ea: float;  Ea_std: float;  nu0: float;  k_at_T: float
    barriers:   float[];  prefactors: float[]     # provenance: contributing values
    backward_class: bytes16|None;  dEnergy: float|None   # E_final - E_initial (detailed balance)
    source_cycles: int[];  source_rows: int[]     # idx_ref of contributing pyKMC rows
    gate_log:   list[GateResult]
    audit_status: {approved, pending, rejected}
    model_version: str|None     # set if any instance used a fallback rate
    anchor_pred: OccPredicate   # the RAREST predicate (runtime anchor; §5.2)

# ---- Compiled: an oriented pattern (one per symmetry orientation g) ----
@dataclass
class OrientedPattern:
    class_id: bytes16;  g: SymOp
    anchor_pred: OccPredicate;  anchor_depth: DepthPred
    screen_key: uint32          # anchor species + coarse first-shell signature (fast pre-screen)
    core_off:  (int,int,int)[m];  core_pred: OccPredicate[m]   # in g orientation
    delta:     DeltaSite[]                                     # in g orientation
    rate: float;  supp_radius: int                             # max |offset| over core∪delta

# ---- Runtime rate list ----
@dataclass
class Instance:  site: int;  pat: OrientedPattern;  rate: float;  pool_pos: int
proc_at:     dict[int -> list[Instance]]      # per-site process list
class_pool:  dict[bytes16 -> dynarray[Instance]]  # O(1) uniform pick + swap-remove
class_count, class_rate: dict[bytes16 -> ...]
group_fenwick: Fenwick over classes (and fallback micro-groups)   # O(log C) selection
R_total: float
```

---

## 2. Component 1 — Forward configuration projection (snapshot → occupancy)

**Goal.** Map a relaxed off-lattice full-cell snapshot `(X: N×3 Å, types, cell)` to occupancy on the
fixed global FCC frame, reporting anything unmappable.

### 2.1 Register the frame (robust, per cycle)

Relaxed positions drift: thermal expansion, rigid translation, surface interlayer relaxation. Refit
`LatticeFrame` each cycle rather than trusting a fixed grid.

```
register_frame(X, types, cell, a_nominal=3.52):
    # (a) lattice constant from the KNOWN periodic cell (exact, not fitted):
    n_cells_x = round(cell.Lx / a_nominal);   a = cell.Lx / n_cells_x       # (Ly cross-check)
    # (b) layer detection along z: 1-D kernel-density peaks of X[:,2] -> layer centers
    layer_z = kde_peaks(X[:,2]); assign integer k to each peak (spacing ~ a/2, contracted at surface)
    # (c) origin phase: minimise Σ snap_residual² over origin ∈ [0,a/2)³  (coarse grid + Nelder–Mead)
    origin = argmin_phase(X, a, layer_z)
    # (d) orientation: Kabsch on a subset of confidently-snapped INTERIOR atoms (absorbs small drift);
    #     for a cube-aligned slab R stays ≈ I but this catches a few-degree tilt.
    R = kabsch_refine(interior_atoms, ideal_sites)
    return LatticeFrame(a,R,origin,...,layer_z,k_top,k_bot)
```

Layer detection (not ideal `a/2` spacing) is what makes surface relaxation harmless: each atom snaps
to its **detected** layer plane, so a contracted top layer still maps 1:1.

### 2.2 Snap atoms to sites

```
project(X, types, frame):
    occ = EMPTY over valid domain
    residual = []; unmappable = []; collision = []
    for atom p in X:
        u  = (2/a) · Rᵀ · (X[p] - origin)              # lattice-index coordinates
        s  = round_to_even_parity(u)                    # nearest of the 2 parity-correct candidates
        d  = |X[p] - r(s)|                              # snap residual (Å), min-image in-plane
        residual.append(d)
        if d > snap_tol:            unmappable.append((p,d)); continue
        if occ[id(s)] != EMPTY:     collision.append((p, id(s))); resolve_keep_nearer(...); continue
        occ[id(s)] = type_to_occ(types[p])
    return occ, Report(residual, unmappable, collision)
```

`round_to_even_parity(u)`: round `u` to the nearest integer triple, then if the parity is odd, flip
the single coordinate with the largest rounding error — `O(1)`, exact nearest-FCC-site.

### 2.3 Tolerances, thresholds, and the cycle policy

- `snap_tol` default `= 0.9 Å` (`≈ 0.36·nn`; nn = 2.489 Å, half-nn = 1.24 Å). Below this an atom is
  unambiguously "on" its site given thermal + surface relaxation; above it the atom is genuinely
  off-lattice (interstitial, reconstruction, mid-transition snapshot).
- `soft_surface_tol = 1.05 Å` — a slightly looser bound applied **only** to top-surface atoms, which
  relax most.
- **Collision:** keep the nearer atom on the site; the displaced atom becomes unmappable.

**What happens to the cycle if unmappable atoms exist** (this is a gate, Section 8.2):

| Condition | Verdict |
|---|---|
| 0 unmappable, max residual < `snap_tol` | accept snapshot |
| ≤ `n_soft` (default 3) unmappable, all top-surface, each < `soft_surface_tol` | accept + warn to provenance |
| > `n_soft` unmappable, or any bulk atom unmappable, or a cluster of adjacent unmappables | **reject snapshot**: the FCC assumption has locally broken (dislocation/amorphisation/melt). Fall back to the last accepted snapshot for this cycle and raise a `PROJECTION_STRUCTURAL` audit item. Do **not** execute on-lattice from a broken projection. |

The report — `{max_residual, residual_histogram, n_unmappable, unmappable_ids, n_collision}` — is
written to the cycle log and drives the coverage report (Section 7.3).

**Round-trip self-check.** Re-expand `occ` to ideal positions and re-snap; occupancy must be
idempotent (it is by construction). The meaningful diagnostic is the residual histogram: a bimodal
histogram (a second peak near `nn/2`) signals systematic mis-registration → refit or reject.

---

## 3. Component 2 — Event projection (reference row → on-lattice event)

**Goal.** Turn one pyKMC reference row into an on-lattice event: a **set of
(site, occ_before → occ_after) changes** plus the surrounding context needed for identity. The row
stores a *local, subset-relative* cluster (`initial_positions = min1[nbr_rcut(mover)]`, etc.), **not**
global coordinates, so projection is **local** and self-contained.

### 3.1 Fit the event's own local FCC frame

```
project_event(row):
    P0 = row.initial_positions;  P2 = row.final_positions   # subset arrays (M×3)
    T0 = row.initial_types                                  # or None (grey)
    mover0 = row.move_atom_idx                              # NOMINAL mover row
    # (a) local frame from the mover + its first shell (nn bond directions ≈ (a/2)(110) family):
    frame_e = fit_local_fcc(P0, seed=mover0)   # least-squares R,a,origin against ideal FCC nn dirs
```

`fit_local_fcc` matches the cluster's nn bond directions to the 12 ideal `(±1,±1,0)` directions
(a small orthogonal-Procrustes problem seeded on the mover) and pins `a` from the mean bond length.
The cluster is tens of atoms, so this is milliseconds.

### 3.2 Detect the TRUE site-change set (do not trust `move_atom_idx`)

```
    S0 = { snap(P0[p], frame_e) : p in cluster }   # initial occupied sites (+ types)
    S2 = { snap(P2[p], frame_e) : p in cluster }   # final   occupied sites
    # empty lattice sites inside the cluster hull = vacancies/adatom targets:
    hull_sites = enumerate_lattice_sites_inside_convex_hull(P0, frame_e)
    empty0 = hull_sites - sites(S0);  empty2 = hull_sites - sites(S2)

    movers = { p : snap_site(P0[p]) != snap_site(P2[p]) }   # atoms that changed site — the TRUTH
    assert mover0 ∈ movers  else  flag(MOVER_DISAGREEMENT)   # gate (§8.2, spec-mandated)
```

The site-change comparison — not `move_atom_idx` — defines the movers, catching the concerted case
the schema warns about. `mover0` must be *among* the detected movers; if not, the row goes to audit.

### 3.3 Build the occupancy-change set Δ and the context

```
    touched = sites(S0 ∪ S2 ∪ empty0 ∪ empty2 that differ)
    delta = []
    for site t in touched:
        b = occ_before(t);  a = occ_after(t)         # from S0/S2, EMPTY if absent
        if b != a:  delta.append(DeltaSite(off = t - anchor, before=b, after=a))
    delta_atoms = (#occupied_after - #occupied_before)  # 0 for diffusion; hook for dissolution

    # context = occupancy of every lattice site within r_ctx of the moved-site centroid:
    ctr = lattice_round(centroid(moved sites))
    context = [ StencilSite(off = s-anchor, pred = species_pred(occ_before(s)))
                for s in lattice_sites_within(ctr, r_ctx) ]
    # surface normal for this event, inferred from the cluster's coordination deficit direction:
    normal_e = coordination_deficit_direction(S0, frame_e)   # None if fully coordinated (bulk)
```

- **Anchor** = the deterministic canonical anchor of the moved set (Section 4.2).
- **`r_ctx`** is set to match pyKMC's `rcut` environment (the range the graph classifier "saw"): the
  union of the **1st + 2nd neighbour shells** of every moved site. This ties on-lattice identity
  locality to the off-lattice classifier that produced `event_id` (Section 4.5).
- **Surface normal inferred from the cluster**, not from any global index: a surface event's cluster
  has a free side (under-coordinated atoms); the outward normal is the direction along which
  coordination drops. Fully coordinated cluster ⇒ bulk. This makes the projection self-contained and
  chooses the symmetry regime (Section 4.1) without needing the global site the event came from.

**Saddle handling.** The saddle is intrinsically off-lattice; it is **not** snapped. `dra`, the saddle
geometry, and the barrier are carried as provenance/rate inputs, but the on-lattice event identity is
defined by `initial→final` site changes plus context only.

**Output** of Section 3: `ProjectedEvent{ anchor, delta, delta_atoms, context, regime(from normal_e),
Ea_fwd, Ea_bwd, nu0, source_row }`.

---

## 4. Component 3 — Class identity (the heart)

**Question.** When are two projected events *the same lattice event class*? Answer: iff their
`(core + context + delta)` patterns are equal after **canonicalization under the site symmetry group
appropriate to a (100) slab**, with species decoration respected.

### 4.1 The symmetry group: bulk `Oh` vs surface `C4v`

- **Bulk regime — `Oh` (order 48).** A genuinely interior FCC site has full cubic point symmetry
  `m-3m`. Bulk events canonicalize under all 48 operations, maximally deduplicating symmetry-equivalent
  discoveries (the 12 nn hop directions collapse to one class).
- **Surface regime — `C4v` (order 8).** A free (100) surface breaks `Oh` down to the operations that
  fix the surface normal and map layers to layers: `E, 2C4, C2, 2σv, 2σd` about `z`. No operation
  flips `z` (that would map surface into vacuum). Surface-touching events canonicalize under `C4v`
  only, so a hop **parallel** to the surface and a hop **toward** it — which can have isomorphic
  graphs but different barriers — are correctly kept **distinct**.
- **Regime selection.** Determined by the event's context: if any context site has
  `depth ≤ d_surf` (default 2 layers) — i.e., the event "sees" the surface — use `C4v`; else `Oh`.
  At match time the class's `anchor_depth` predicate re-imposes this so a surface class can never bind
  in bulk (and vice versa). Depth is thus a *matchable predicate*, not merely a symmetry switch.

This directly answers the spec's "bulk site group vs reduced surface symmetry — handle both." The
honest caveat (subsurface sites have symmetry *between* `Oh` and `C4v`) is Weakness W4.

### 4.2 Deterministic anchor and total order

Canonicalization needs a deterministic origin and a total order on serializations.

```
anchor = argmin over moved sites m of key(m) where
    key(m) = ( occ_priority(before(m)),        # EMPTY < Ni < Cr < Fe ...   (stable species order)
               round(|r(m) - centroid|,1e-3),  # nearest the moved centroid
               lex(offset(m)) )                 # final tie-break
```

### 4.3 Canonical form and `class_id`

```
canonical_form(delta, context, regime):
    G = OhOps if regime==Oh else C4vOps
    best = None
    for g in G:                                     # ≤ 48 (Oh) or 8 (C4v)
        d = sorted( (g·off, before, after) for (off,before,after) in delta )
        c = sorted( (g·off, pred)          for (off,pred)          in context )
        s = serialize(regime, d, c)                 # bytes
        best = min(best, s)
    return best
class_id = blake2b(canonical_form(...), digest=16)
g_star   = argmin g   # winning op, stored on the instance for execution orientation
```

Small group + small stencil ⇒ this is microseconds and **exact** — the discrete analogue of a nauty
certificate, but computed with the explicit slab point group rather than a topological hash, so it is
geometry- and surface-aware. In **grey** mode every `SPECIES` predicate collapses to `OCC_ANY`
before serialization; in **full colour** species labels are part of the form. Ternary is automatic —
the alphabet just grows; **no colour-swap symmetry** is assumed (Ni≠Cr≠Fe physically).

### 4.4 Environment context size/shape — core vs descriptor, and data-driven splitting

The size of the identity context is a bias/variance knob:

- **too large** ⇒ every event unique (catalogue explodes, reuse dies, runtime pattern blow-up);
- **too small** ⇒ physically distinct-barrier events collapse into one class (wrong rates).

The design separates two shells:

- **Core** = moved sites + their **1st shell** — the sites whose occupancy is *causally required* for
  the move to be geometrically possible (the target must be `EMPTY`, the mover `OCC`, the framing
  atoms present). The **core drives runtime matching** (Section 5): it is what must hold for the event
  to be executable.
- **Descriptor/context** = out to the **2nd shell** (`r_ctx`) — captures local composition and
  vacancy arrangement that *modulate the barrier*. The descriptor is part of identity **but its
  promotion is data-driven**:

```
ingest instance with class_id C, barrier Ea:
    if C exists:
        if |Ea - mean(C.barriers)| ≤ split_tol (default 0.15 eV):  merge (append barrier)
        else:                                                       SPLIT_CHECK(C, instance)
    else: new class (audit first instance)

SPLIT_CHECK: find the smallest descriptor-shell extension that separates the outlier's context
    from the incumbent's; promote that shell into both classes' identity (re-key both). If none
    separates them (same context, different barrier) -> route to audit as a genuine ambiguity.
```

So identity **starts minimal and grows only where the harvested barriers prove it must** — classes
neither fragment gratuitously nor collapse distinct physics. This is the core signature of the
classification story and the main lever on rubric item "classification robustness".

### 4.5 Reconciliation with pyKMC's `event_id`

pyKMC's `event_id` is an orientation-invariant graph certificate; it can (a) **merge** surface hops
that this design must split (isomorphic graph, different barrier — pyKMC itself then keeps multiple
rows per `event_id` disambiguated by a 0.25 eV / PSR-saddle test), and (b) **split** bulk hops that
this design merges (two searches at symmetry-related sites yield different certificates that `Oh`
unifies). The design therefore treats `(event_id, id_final)` as a **fast screening bucket** for
ingest (Section 7) but the **discrete canonical form is authoritative**. Concretely: one pyKMC
`event_id` may fan out into several on-lattice classes (surface orientations) and several `event_id`s
may fold into one (bulk symmetry) — the canonical form gets both directions right where a graph hash
alone cannot.

---

## 5. Component 4 — Runtime matching (compile → per-site lists → incremental update)

### 5.1 Compile: classes → oriented patterns

Ahead of the run (and after each harvest), each approved `EventClass` is expanded over its group:

```
compile(class C):
    G = group(C.regime)
    seen = {}                                      # dedup self-symmetric orientations
    for g in G:
        core_g  = [(g·off, pred) for (off,pred) in C.core]
        delta_g = [(g·off, b, a) for (off,b,a)   in C.delta]
        key = frozenset(core_g) ∪ frozenset(delta_g)
        if key in seen: continue                   # event's own symmetry -> fewer than |G| orientations
        seen.add(key)
        emit OrientedPattern(class_id=C.class_id, g=g,
              anchor_pred = rarest_predicate(core_g),      # §5.2
              anchor_depth = C.anchor_depth,
              screen_key = screen(core_g),
              core_off/core_pred = reanchor(core_g to its rarest site),
              delta = delta_g, rate = C.k_at_T,
              supp_radius = max|off| over core_g ∪ delta_g)
```

The number of distinct orientations equals `|G| / |stabilizer|` — exactly the count pyKMC's
`sym_perm` encodes, giving a **cross-check** (Section 12). Patterns are indexed:

```
patterns_by_anchor[occ_pred][depth_bucket][screen_key] -> [OrientedPattern...]
r_supp_global = max over patterns of supp_radius        # global pattern support radius
```

### 5.2 Anchor at the rarest predicate

Each pattern is **re-anchored to its scarcest site** — a vacancy, adatom target, or minority species —
because enumeration cost scales with the number of candidate anchors. For dilute vacancies on a mostly-
Ni slab, anchoring a vacancy-hop at the **empty** site means only the ~1–2 vacancy sites are ever
tested, instead of every Ni. This turns initial matching from `O(N·patterns)` into
`O(#defect_sites·patterns)` for dilute systems — the practical regime of the target science
(10²–10³ atoms, 1–2 vacancies).

### 5.3 Initial match and the group-BKL rate list

```
build_rate_list(Grid, patterns):
    for each candidate anchor s (sites whose occ matches some anchor_pred, filtered by depth):
        for P in patterns_by_anchor[occ[s]][depth_bucket[s]][screen_key[s]]:
            if match(P, s):                        # all core predicates hold at s+offset
                inst = Instance(s, P, P.rate)
                proc_at[s].append(inst)
                pool = class_pool[P.class_id]; inst.pool_pos = len(pool); pool.append(inst)
                class_count[P.class_id]+=1; class_rate[P.class_id]=P.rate
    build group_fenwick over classes;  R_total = Σ class_count·class_rate

match(P, s):
    if not depth_ok(P.anchor_depth, depth[s]): return False
    for (off, pred) in zip(P.core_off, P.core_pred):
        t = resolve(s, off, Grid)                  # nbr-table walk; OUTSIDE if free-boundary
        if not pred.holds(occ[t]): return False
    return True
```

**Selection (one KMC step) — group-BKL / composite rejection:**

```
select():
    c   = group_fenwick.sample()                   # class with prob ∝ count·rate   -> O(log C)
    inst = class_pool[c].uniform_pick()            # O(1)
    dt  = -ln(U(0,1]) / R_total                    # BKL time advance
    return inst, dt
```

All instances of a class share one rate, so selection is `O(log C)` in the number of **classes**,
independent of the number of **instances**. Fallback-rated instances (Section 6) form their own
micro-groups keyed by discretised rate, keeping the same machinery.

### 5.4 Execute + incremental invalidation (the signature)

```
execute(inst):
    changed = []
    for (off, before, after) in inst.pat.delta:
        t = resolve(inst.site, off, Grid)
        assert occ[t] == before                    # consistency guard (else desync -> rebuild)
        occ[t] = after; changed.append(t)
    if delta_atoms != 0: update_domain_and_depth(changed)   # dissolution/surface recession hook

    # dirty anchors = candidate anchors within r_supp_global of any changed site:
    dirty = ∪_{t in changed} { s in ball(t, r_supp_global) : occ[s] matches some anchor_pred }
    for s in dirty:
        remove_instances(proc_at[s])               # pop from class_pool via swap-remove: O(1) each
        proc_at[s].clear()
        rematch s (as in build_rate_list)          # re-enumerate patterns at s
    update class_count/class_rate deltas; group_fenwick.update(...); R_total += Δ
    accumulate coverage metrics (§7.3), SRO deltas (§7.3)
```

`ball(t, r_supp_global)` is a fixed integer neighbourhood (precomputed offset list). Its size is
**independent of N** — it depends only on how far the largest pattern reaches (`r_supp_global`, ≈ 2nd–3rd
shell). Swap-remove keeps `class_pool` compact for `O(1)` turnover.

**Periodic self-heal.** Every `M` steps (default `10⁴`) recompute `R_total` and a class-count checksum
from scratch and compare to the incrementally maintained values; a mismatch asserts and triggers a full
rebuild (guards against any missed-dirty-site bug). Cost amortised to negligible.

### 5.5 Complexity (see Section 10 for consolidated numbers)

- **Compile:** `O(C·|G|·σ)` — seconds. **Initial match:** `O(A·κ·σ)`, `A` = candidate anchors
  (`≈ #defect_sites` for dilute, `≤ N` general) — once.
- **Per step:** `O(D·κ·σ)` re-match + `O(log C)` selection, with `D` = dirty anchors per step (a
  fixed, N-independent ball, ≈ 30–80 sites). **Per-step cost is O(1) in N** — the on-lattice invariant
  that makes 10⁶ steps on 10³ sites run in minutes and 10⁵–10⁶ sites feasible on a node (memory-bound,
  not step-bound).

---

## 6. Component 5 — Rate assignment

### 6.1 Exact-lookup path

Each class stores `Ea = mean(barriers)`, `nu0 = geo_mean(prefactors)` (HTST `nu0` when available,
else `k_prefactor`), both temperature-independent. At compile the rate is evaluated once:

```
k_class = nu0 · exp(-Ea / (kB·T))          # ps⁻¹; re-evaluated only if T changes
```

Every exact-matched instance uses `k_class`. This is the common path.

### 6.2 Fallback regression (near-miss) + flag

When runtime matching finds an **executable core** (a geometrically valid move exists — e.g. an
occupied site beside an empty target) but the **full descriptor/decoration** matches no approved class
exactly, the instance is rated by regression **and flagged**:

- **Descriptors** (cheap, permutation-invariant, physically motivated):
  1. mover coordination at initial and final site (`n_i`, `n_f`);
  2. per-species counts in the mover's 1st and 2nd shell, before and after;
  3. **generalized coordination number** GCN (Calle-Vallejo) of initial/final site — a strong,
     well-established correlate of FCC diffusion/adsorption barriers;
  4. surface depth / site type (bulk/surface/step/kink via coordination signature);
  5. a short-range-order indicator (Warren–Cowley-like 1st-shell pair fractions).
- **Model.** Start with **ridge / Bayesian linear regression** `Ea ≈ β·φ` (a Brønsted–Evans–Polanyi
  linear-barrier model — barriers correlate near-linearly with local bond-count/composition), upgrade
  to **gradient-boosted trees** or a **Gaussian process** as the catalogue grows (the GP's predictive
  variance ranks flagged sites for exploration). `nu0` fallback = geometric mean of harvested
  prefactors (prefactor spread is small on a log scale; barriers dominate rate variation).
- **Fitting protocol.** Fit on all harvested `(Ea, φ)` pairs; leave-one-class-out CV for the residual
  spread; weight by provenance confidence (gate-clean, low `Ea_std`). Refit is **seconds**.
- **Refit cadence.** After every harvest cycle (the catalogue grew) or when `>N_refit` (default 25)
  new events accrue since the last fit. The **model version** is stamped into provenance and into any
  instance it rated, so a run is reproducible.

### 6.3 The flag mechanism and never-zero guarantee

Every fallback-rated instance carries `flag=True`. The run maintains a `flag_registry` keyed by the
instance's descriptor vector: `{descriptor -> (count, carried_flux, first_step)}`. At cycle end this
is emitted, most-visited-and-highest-flux first, as the **priority exploration list** handed to pyKMC
(decision 4). **Nothing contributes zero flux**: a geometrically-possible move with neither an exact
class nor a confident regression prediction is assigned `max(regression_pred, k_floor)` (a conservative
upper bound) and top exploration priority — so it is *sampled*, hence *discovered*, rather than
silently frozen.

---

## 7. Component 6 — Novelty & harvest round trip

### 7.1 Ingest new pyKMC rows → classes

```
ingest(new_rows):
    for row in new_rows:
        pe = project_event(row)                    # §3
        run_auto_gates(pe, row)                     # §8.2; failures -> audit queue
        C  = class_id(canonical_form(pe.delta, pe.context, pe.regime))
        bucket by (row.event_id, row.id_final)      # fast screen; canonical form authoritative
        if C in catalogue:
            append row.energy_barrier to C.barriers; update C.Ea/Ea_std; record source_cycle/row
            if |row.Ea - mean(C.barriers)| > split_tol:  SPLIT_CHECK(C, pe)     # §4.4
        else:
            create EventClass(C, pe...); audit_status = pending                 # first instance audited
            enqueue_audit(C, first_instance=pe, reason=NEW_CLASS)
    recompile changed/new APPROVED classes                                       # §5.1
```

- **New class vs new instance** = existence of `class_id` in the catalogue, i.e. equality of the
  authoritative canonical form.
- **First instance of a brand-new class** is auto-queued for audit (decision 5); it becomes matchable
  only after approval.

### 7.2 Forward/backward pairing (microscopic reversibility)

pyKMC provides `idx_backward`. The reverse event's Δ is the **inverse** occupancy change on the same
sites. Ingest verifies and links:

```
pair(fwd_row, bwd_row):
    pe_f = project_event(fwd_row); pe_b = project_event(bwd_row)
    assert delta(pe_b) == invert(delta(pe_f)) under some g   # before<->after swapped
    assert context(pe_b at final) == context(pe_f at final)
    link: fwd_class.backward_class = bwd_class.class_id (and vice versa)
    dEnergy = Ea_fwd - Ea_bwd                                # = E_final - E_initial (state energy diff)
    DETAILED_BALANCE gate:  |ln(k_f/k_b) - (-dEnergy/kBT)| < db_tol   # §8.2
```

A **self-reverse** event (Δ equals its own inverse under a symmetry op — a symmetric exchange, or
pyKMC's `event_id == id_final` case) is stored as a single class with `backward_class = self`,
mirroring pyKMC's single-row handling. `dEnergy` per pair lets the engine keep detailed-balance
bookkeeping and is the input to the fwd/bwd consistency gate.

### 7.3 Coverage-report metrics (decision 6 — cheap to accumulate during the run)

All maintained incrementally (each event touches `O(1)` sites):

- **Fallback flux fraction** — `R_fallback / R_total`, where `R_fallback = Σ over fallback micro-groups
  count·rate`; both maintained by the same Fenwick updates. Also the fraction of **executed** steps
  that were fallback-rated (a running counter). This is the headline convergence signal per decision 4.
- **Observed-but-unharvested environments** — the `flag_registry` (Section 6.3): distinct local
  environments visited that no exact class covers, with visit counts and carried flux. The exploration
  frontier.
- **Composition / short-range-order drift** — running global species fractions and vacancy count
  (updated by each Δ), plus **Warren–Cowley SRO parameters** from incrementally maintained 1st-shell
  pair counts (each event updates only the pairs around `changed` sites, `O(1)`). Reported as drift
  from cycle start.

**Convergence of the loop** = *new harvested classes per cycle → 0* (decision 1): tracked as
`|catalogue_after| − |catalogue_before|` each cycle.

### 7.4 Reverse mapping — occupancy → atomistic config for pyKMC

```
to_atomistic(Grid):
    atoms = []
    for id in sorted(valid site ids):              # FIXED enumeration order -> determinism
        if occ[id] not in {EMPTY, OUTSIDE}:
            atoms.append( (occ_to_symbol(occ[id]), r_ideal(site_of_id[id], frame)) )
    return XYZ(atoms, cell = frame_cell, pbc=(True,True,False))
```

Atoms are emitted at their **ideal** site positions (not the relaxed snap source), so the handoff is
**frame-reproducible and independent of projection residuals**: identical occupancy ⇒ byte-identical
coordinates. Empty sites emit nothing (vacancy = absent atom — exactly pyKMC's atom-only convention).
pyKMC then minimises this ideal config (relaxing atoms off the sites into its off-lattice basin), runs
its `k = 20–1000` steps with the cumulative reference table preloaded, and returns new rows → back to
Section 7.1. Determinism of this map is the reproducibility anchor of the whole loop (Section 8.3).

---

## 8. Component 7 — Provenance & curation hooks

### 8.1 Per-class provenance

Carried on every `EventClass` (schema, Section 1.3): `source_cycles`, `source_rows` (contributing
`idx_ref`), `barriers[]` + `Ea/Ea_std/min/max`, `prefactors[]`, `gate_log` (per-instance gate outcomes),
`model_version` (if any rate was regression-derived), `first_seen` cycle, `audit_status`,
`backward_class`, `dEnergy`, `delta_atoms`. This makes every rate in the run traceable to the
off-lattice events that produced it.

### 8.2 Automated gates (decision 5), defined precisely

An event is auto-admitted iff **all** gates pass; any failure, plus every first-instance-of-new-class,
routes to the audit queue.

| Gate | Check | Threshold (default) |
|---|---|---|
| **G1 barrier bounds** | `emin ≤ Ea_fwd ≤ emax` and `Ea_bwd ≥ backward_emin` | reuse pyKMC's `emin_event/emax_event/backward_emin_event` |
| **G2 fwd/bwd consistency** | not pathologically asymmetric (mirror pyKMC's `energy_asymmetry` rule) **and** detailed-balance: `|ln(k_f/k_b) + dEnergy/kBT| < db_tol` | `db_tol = 0.05` (in ln-rate units) |
| **G3 snap residual** | every cluster atom (initial **and** final) snaps with residual `< snap_tol`; movers `< snap_tol` strictly | `snap_tol = 0.9 Å` |
| **G4 projection round-trip** | re-expand projected event to ideal positions → re-project → identical `class_id` (idempotence); **and** `move_atom_idx ∈ detected_movers` | exact id match; mover-membership boolean |

G3 is what keeps intrinsically off-lattice events (interstitials, reconstructions) out of the
on-lattice catalogue — they cannot be represented, so they are audited, not silently dropped or
force-fitted. G4 catches both mis-projection and the concerted-mover mislabel the spec warns about.

### 8.3 Audit queue and determinism

- **Queue interface** = a directory of records (decision 1: file-based handoffs), one JSON/parquet per
  item: `{rows, projected_pattern, canonical_form, gate_results, reason,
  suggested_action ∈ {new, split, outlier, structural}}`. A human (or a later auto-approver) writes a
  decision (`approve/reject/merge/split`) into a **decision log**; approved items compile into the
  catalogue on the next `recompile`.
- **Determinism / reproducibility.** (a) The reverse map (Section 7.4) is deterministic by fixed site
  enumeration + ideal positions. (b) Canonicalization is deterministic (fixed group op order, total
  serialization order). (c) The audit **decision log** is replayed, so re-running a cycle reproduces
  the catalogue bit-for-bit. (d) BKL RNG is seeded and logged. (e) The fallback **model version** is
  pinned per cycle. Together these make an entire alternation run reproducible from
  `{initial config, seed, decision log, model versions}`.

---

## 9. Worked examples

### 9.1 Vacancy hop — bulk Ni (projected → classified → matched → executed)

**Off-lattice row.** Cluster of ~40 atoms around the mover; `initial_positions` has the mover at a
site with an adjacent absent atom (the vacancy); `final_positions` has the mover shifted into that
gap; `move_atom_idx` = the mover; `energy_barrier ≈ 0.65 eV`, `k_prefactor`/`nu0` set.

**Project (Section 3).** Fit local frame from mover + 1st shell. Snap: mover initial site
`A=(0,0,0)`; the 12 nn enumerated; site `B=(1,1,0)` (a `⟨110⟩` nn) is `EMPTY` in the initial state
(no atom snaps there). Site-change detection: mover's initial site `(0,0,0)` ≠ final `(1,1,0)` ⇒
`movers = {mover}` (and `mover0 ∈ movers` ✓). Occupancy change:

```
delta = [ ((0,0,0): Ni→EMPTY), ((1,1,0): EMPTY→Ni) ]     # anchor at A; delta_atoms = 0
```

Context: 1st+2nd shells around `{A,B}` all `Ni` ⇒ bulk (no coordination deficit) ⇒ regime `Oh`.

**Classify (Section 4).** Anchor `= A` (occ_priority: the occupied moved site... tie-break puts the
canonical anchor deterministically; here the moved pair `{A,B}` canonicalizes with the hop vector
`(1,1,0)` reduced under `Oh` to its lexicographically minimal `⟨110⟩` representative). Context
(uniform Ni) is symmetric. `class_id = blake2b(canonical_form)` — the canonical **bulk Ni nn
vacancy-hop** class. All 12 nn directions are `Oh`-equivalent ⇒ **one class**; its stabiliser leaves
**12 distinct oriented patterns** (one per nn direction), matching the `sym_perm` count.

**Compile (Section 5.1).** 12 `OrientedPattern`s. Each is **re-anchored at the rarest predicate = the
EMPTY target**: `anchor_pred = EMPTY`, core = `{ anchor: EMPTY (the vacancy), (−1,−1,0): Ni (the
mover), framing 1st-shell Ni predicates }`, `delta = { anchor: EMPTY→Ni, (−1,−1,0): Ni→EMPTY }`,
`rate = k = nu0·exp(−0.65/kBT)`.

**Match (Section 5.3).** With one vacancy in the 10³-site slab, only that **one EMPTY anchor** is
tested (rarest-anchor payoff). Its 12 occupied Ni neighbours each satisfy one oriented pattern ⇒
**12 enabled instances**, all in the same class pool, each rate `k`. `group_fenwick`: this class has
count 12, rate `k`.

**Execute (Section 5.4).** BKL selects an instance — say the vacancy at `(6,6,4)` is filled from Ni at
`(5,5,4)`. Apply Δ: `(5,5,4) Ni→EMPTY`, `(6,6,4) EMPTY→Ni`. `changed = {(5,5,4),(6,6,4)}`. Dirty
anchors = EMPTY sites within `r_supp_global` of the changed sites = the **new** vacancy at `(5,5,4)`
(and the old one is now filled). Rematch: remove the 12 instances around the old vacancy, enumerate 12
new instances around the new vacancy. `R_total` unchanged (bulk homogeneous). `Δt = −ln(u)/R_total`.
The vacancy has taken one nn step; cost was `O(1)`.

### 9.2 Three-site concerted event — surface (projected → classified → matched → executed)

A vacancy-mediated correlated exchange at the (100) surface: atom1 (Ni) at `A` moves to `B`, atom2
(Cr) at `B` moves to `C`, and the vacancy at `C` ends at `A` — a chiral 3-site cycle. pyKMC's
`move_atom_idx` names **only atom1**; `final − initial` shows **two** atoms displaced.

**Off-lattice row.** Cluster around atom1; the free surface is on the `+z` side (top-layer atoms
under-coordinated). `energy_barrier ≈ 0.45 eV`.

**Project (Section 3).** Fit local frame. Snap initial: atom1@`A`, atom2@`B`, site `C` empty
(vacancy). Snap final: atom1@`B`, atom2@`C`, site `A` empty. **Site-change detection finds BOTH
movers** — `{atom1: A→B, atom2: B→C}` — even though `move_atom_idx` named only atom1 (`mover0 ∈ movers`
✓; the design does not trust `move_atom_idx`). Per-site occupancy:

```
delta = [ (A: Ni→EMPTY), (B: Cr→Ni), (C: EMPTY→Cr) ]     # anchor = canonical of {A,B,C}
delta_atoms = 0                                           # one EMPTY created at A, consumed at C
```

Context: the cluster shows a coordination deficit toward `+z` ⇒ surface event ⇒ regime `C4v`, axis =
inferred surface normal.

**Classify (Section 4).** Anchor = deterministic canonical of `{A,B,C}` (centroid-snapped, tie-broken).
Canonicalize `delta + context` under `C4v` (8 ops) → `class_id`. The 3-site cycle is **chiral**, so its
`C4v` orbit gives up to **8 oriented patterns** (mirror + rotation images are physically distinct hops
here). Species decoration (the specific Ni/Cr arrangement) is part of identity in full colour. This
event's graph certificate might coincide with a differently-oriented surface event's, but the `C4v`
canonical form keeps them distinct — the surface-anisotropy split (Section 4.5).

**Compile (Section 5.1).** ≤ 8 oriented patterns. Rarest-anchor = the `EMPTY` site `C` (vacancies are
scarce): `anchor_pred = EMPTY`, `anchor_depth = SURFACE(coord 8)`, core = the 3 sites + their 1st-shell
framing predicates, `delta` as above, `rate = nu0·exp(−0.45/kBT)`.

**Match (Section 5.3).** For each surface `EMPTY` anchor at the right depth, test the 3-offset stencil:
need `A` = Ni, `B` = Cr, `C` = EMPTY in the specific relative geometry at the surface. Matches only
where that Ni–Cr–vacancy surface motif exists — typically few instances. Each is one instance in the
class pool.

**Execute (Section 5.4).** BKL selects an instance; apply the 3-site Δ **atomically**:
`A: Ni→EMPTY, B: Cr→Ni, C: EMPTY→Cr`. `changed = {A,B,C}`. Dirty anchors = surface `EMPTY` sites within
`r_supp_global` of `{A,B,C}` (a slightly larger ball — 3 changed sites). Rematch those anchors: the
vacancy moved from `C` to `A`, the Cr moved to `C`; nearby hop/exchange patterns are re-enumerated,
including new events now enabled by the vacancy at `A` and the Cr at `C`. `R_total` updated by the
Fenwick deltas. Cost `O(1)`. Provenance records this as a surface class with `delta_atoms = 0`; SRO
counters update for the changed Ni–Cr pairs.

---

## 10. Consolidated complexity analysis

Symbols: `N` active sites (10³–10⁶); `C` classes (10²–10³); `|G|≤48`; `P` oriented patterns
(`≈ C·|G|/stabiliser`, deduped); `κ` patterns tested per candidate anchor after screening (1–20);
`σ` stencil size (10–30 sites); `A` candidate anchors (`≈ #defect_sites` dilute, `≤ N` general);
`D` dirty anchors per step (fixed ball, N-independent, ≈ 30–80).

| Phase | Cost | Notes |
|---|---|---|
| Build grid + `nbr12/nbr2/depth` | `O(N)` integer | once per cycle; no geometry |
| Register frame + project snapshot | `O(N log N)` (KDE/snap) | once per cycle |
| Compile catalogue | `O(C·|G|·σ)` | seconds; after each harvest |
| Initial match (rate list) | `O(A·κ·σ)` ≤ `O(N·κ·σ)` | once; dilute defects ⇒ `A≈#vacancies` |
| **Per KMC step** | **`O(D·κ·σ) + O(log C)`** | **N-independent** — the on-lattice invariant |
| 10⁶ steps | `O(10⁶ · (D·κ·σ))` | ≈ 10⁹–10¹⁰ primitive ops; seconds–minutes in a compiled kernel |
| Memory | `O(N)` grid + `O(#enabled instances)` | `#enabled ≈ O(N)` worst, `O(#defects·const)` dilute |

**At scale.** Because per-step cost is independent of `N`, 10⁶ steps on 10³ sites run in minutes, and
10⁵–10⁶ sites on a cluster node are limited by **memory and the one-time `O(N)` build**, not by the step
rate. The design deliberately pushes the only `N`-scaling work (grid build, initial match) to
once-per-cycle and keeps the inner loop constant — a compiled/vectorised kernel (the kmos-style "compile
the process list to code" heritage) closes the constant-factor gap for the tight loop; the Python
reference implementation is correct and used as the self-heal oracle.

---

## 11. Failure-mode table

| Failure | Cause | Detection | Response |
|---|---|---|---|
| Off-lattice atom | interstitial / reconstruction / mid-transition snapshot | snap residual > `snap_tol` (§2.3, G3) | flag unmappable; structural (many/large/clustered) ⇒ reject snapshot → audit; lone surface atom ⇒ accept + warn |
| Frame drift / wrong `a`,origin | thermal expansion, rigid translation, tilt | registration RMS, bimodal residual histogram | refit robustly each cycle; persistent failure ⇒ audit |
| Concerted mover mislabel | pyKMC `move_atom_idx` names one of several movers | site-change detection vs `move_atom_idx` (§3.2, G4) | use detected set; `mover0∉movers` ⇒ audit |
| Class fragmentation | context too large / over-decorated | instances-per-class ≈ 1; catalogue ~ #events | monitor reuse; shrink descriptor shell; merge by core |
| Class collapse (wrong rates) | context too small; distinct barriers merged | intra-class barrier spread > `split_tol` | SPLIT_CHECK promotes a wider shell into identity (§4.4) |
| Vacancy vs vacuum ambiguity | above-surface EMPTY vs bulk vacancy | occupied-neighbour count within `rcut`; domain bounds | vacancy = EMPTY with occupied nbrs; vacuum inert; only vacancy/adatom sites anchor events |
| Two atoms → one site | compression / near-saddle snapshot | collision detection (§2.2) | keep nearer, flag other; if frequent, snapshot is mid-transition ⇒ reject |
| Detailed-balance violation | fwd/bwd rates inconsistent | gate G2: `ln(k_f/k_b)` vs `−dEnergy/kBT` | reject pair → audit; don't compile |
| Enabled move with no rate | novel environment, regression out of range | fallback path; never-zero guard (§6.3) | `max(regression, k_floor)` + top exploration priority |
| Rate-list desync after event | missed dirty site in incremental update | periodic checksum vs full rebuild (§5.4) | assert + full rebuild; log |
| Symmetry over/under-reduction | wrong `Oh`/`C4v` regime at a subsurface site | regime from context depth; unit tests on known events | depth-based selection + `anchor_depth` predicate; documented as W4 |
| Pattern support too small | collective event exceeds `r_supp_global` | event stencil radius vs `r_supp_global` at compile | `r_supp_global = max` over catalogue; grows when a larger event is ingested |
| Fallback micro-group blow-up | many distinct near-miss rates coexist | count of fallback micro-groups | discretise fallback rates into bins; bounded groups |

---

## 12. Test plan

**Unit.**
- *Site model:* even-parity nn enumeration (exactly 12; nn = 2.489 Å), 2nd shell (6, at `a`), (100)
  layer structure (4 in-layer + 8 cross-layer bulk; 8 at surface), `depth` BFS, in-plane PBC wrap.
- *Projection:* ideal FCC slab → exact occupancy; Gaussian-perturbed slab → same occupancy;
  planted interstitial → flagged unmappable; frame registration invariant under rigid
  translation/rotation/thermal expansion.
- *Canonicalization:* bulk vacancy hop → **one** class over 12 orientations (`Oh`); surface hop →
  correct `C4v` class count; species decoration distinguishes Ni-hop-near-Cr from pure-Ni;
  surface-parallel vs surface-normal hops with isomorphic graphs → **distinct** classes.
- *Compile:* number of oriented patterns == `|G|/|stabiliser|` — **cross-checked against the row's
  `sym_perm` length** (independent oracle from pyKMC).
- *Rate:* Arrhenius evaluation; ridge/GP fallback on held-out barriers within CV spread; never-zero
  guard returns a positive rate.
- *Incremental update:* single-event dirty-set equals the brute-force set of anchors whose match
  status changed.

**Round-trip.**
- Project → reverse-map to ideal config → re-project → identical occupancy (idempotence).
- pyKMC row → project → canonical class → synthesise an instance on a grid → reverse the Δ → recovers
  the row's site changes.
- Forward/backward: ingest a fwd/bwd pair → `Δ_bwd == invert(Δ_fwd)` under a group op; G2 passes on a
  constructed consistent pair, fails on a perturbed-barrier pair.
- Execute a known event on a grid, reverse-map, and confirm a stub minimiser (or pyKMC) relaxes to the
  expected geometry.

**Statistical / validation.**
- *Single bulk vacancy in Ni:* on-lattice tracer diffusivity `D` vs the analytic correlated-vacancy
  value and vs a direct pyKMC run — agree within Monte-Carlo error.
- *Detailed balance:* small system with a known `dEnergy` model run to equilibrium — occupancy /
  composition distribution matches Boltzmann.
- *Incremental correctness:* incremental `R_total`/class-counts vs periodic full rebuild over 10⁵
  steps — zero drift (checksum).
- *Coverage metrics:* fallback-flux fraction and unharvested-environment counts trend to 0 as the
  catalogue grows on a simple system (loop convergence signal).
- *Scaling:* per-step wall-time flat across N ∈ {10³, 10⁴, 10⁵} — confirms O(1)/step.
- *Loop closure:* seed on-lattice from a pyKMC snapshot → run → reverse-map → pyKMC leg → confirm new
  classes per cycle → 0 on Ni(100) single-vacancy.

---

## 13. Self-declared weaknesses

- **W1 — Rigid-lattice assumption.** Surface reconstructions, large relaxations, and interstitial /
  off-lattice pathways cannot be represented; they are detected (G3) and audited, not executed.
  Dealloying can roughen or amorphise the surface — exactly where the science gets interesting — and
  there the engine degrades to "abort projection + hand back to pyKMC", capping acceleration in the
  regime that may matter most.
- **W2 — Context radius is tuned, not solved.** The core/descriptor split and data-driven SPLIT_CHECK
  reduce the risk, but `r_ctx` and `split_tol` are empirical. Barriers depend on longer-range strain /
  elastic fields a finite local stencil cannot capture; the BEP linear fallback is approximate.
- **W3 — Fallback quality is descriptor-bound.** Bond-counting / GCN / SRO features may miss the true
  barrier-determining physics for concerted or step/kink events; fallback rates can be systematically
  off until pyKMC harvests those classes. Flagging + never-zero keep flux non-zero, but it can be
  **mis-allocated** between harvests, biasing the trajectory the exploration then follows.
- **W4 — Binary symmetry regime.** `Oh` vs `C4v` is a two-way switch; real subsurface / step / kink /
  near-vacancy-cluster sites have site symmetries *between* the two. Forcing one can over- or
  under-deduplicate. A rigorous fix computes the actual site symmetry per event (as pyKMC's
  `unique_symmetries` does off-lattice) rather than a depth threshold — deferred.
- **W5 — Detailed balance checked, not enforced.** G2 gates fwd/bwd consistency, but rates come from
  independently averaged barriers; residual inconsistency can bias equilibrium. A stricter design would
  symmetrise each pair to satisfy `k_f/k_b = exp(−dEnergy/kBT)` exactly from a single per-pair `dEnergy`.
- **W6 — Truncated collective events.** A genuinely collective event whose movers exceed the stored
  `rcut` cluster projects to a partial Δ. pyKMC's own containment guard usually prevents storing these,
  but a borderline case could yield a wrong (partial) class; detection (round-trip G4) is only partial.
- **W7 — Catalogue-richness cost.** In full-colour ternary, distinct decorations multiply classes and
  patterns; runtime stays O(1)/step via screening, but compile time and memory grow with catalogue
  richness — fine at 10²–10³ classes, needs attention beyond.
- **W8 — Fallback micro-group proliferation.** Group-BKL assumes intra-class rate homogeneity; many
  coexisting continuous fallback rates spawn many micro-groups. Rate binning bounds this but trades a
  small rate-quantisation error for group count.

---

## 14. Fit to the harvest pipeline and extensibility

- **Catalogue-first, file-based loop (decision 1).** Every artifact is a file: occupancy grid,
  compiled catalogue, audit queue + decision log, coverage report, priority exploration list. Each leg
  is a scriptable step; a closed-loop driver just alternates the two engines and watches
  *new-classes-per-cycle → 0*. No redesign needed to close the loop.
- **pyKMC leg = real KMC with a seeded table (decision 3).** The reverse map (Section 7.4) emits an
  ideal-site atomistic config; pyKMC minimises and runs `k` steps with the cumulative reference table
  preloaded (its IRA dedup makes rediscovery cheap); the harvest is the new rows, ingested in
  Section 7.1.
- **Rate model (decision 4).** Exact-class lookup with parametric BEP/GCN fallback + flag; flagged
  environments become the next leg's exploration targets; nothing is silently zero.
- **Curation (decision 5).** Precise auto-gates G1–G4 admit clean events; failures and new-class first
  instances go to the audit queue; provenance is per-class.
- **Switching + coverage (decision 6).** Fixed tunable `n` steps, then a cheap coverage report
  (fallback flux, unharvested environments, composition/SRO drift), all accumulated `O(1)`/step.
- **Occupancy-count-changing events.** The `DeltaSite{before, after}` schema already admits
  `X → EMPTY` with `delta_atoms ≠ 0`; matching, canonicalization, and BKL are unchanged; only the
  reverse map (atom deletion) and pyKMC handoff differ — and pyKMC's dissolution path already deletes
  atoms. A later dealloying campaign needs **no re-harvest and no schema break**.
- **Ternary and beyond.** The occupancy alphabet grows; predicates, canonical form, regression
  descriptors, and SRO counters are all parameterised by the species set. No structural change.
- **Cluster promotion.** The same engine runs unchanged from a 10²–10³-atom workstation slab to a
  10⁵–10⁶-site production slab: per-step cost is N-independent; only the one-time build and memory
  scale, both within a single cluster node.
