# Design "synthesis" — a precompiled-local-pattern on-lattice KMC engine with a unified decorated-stencil identity, harvested from pyKMC off-lattice discovery

**Design name:** `synthesis`
**Backbone:** `pattern` (precompiled per-site process lists, oriented-pattern compilation, rarest-predicate
anchoring, incremental invalidation, and — the crown jewel — the **core/descriptor split with data-driven
SPLIT_CHECK**).
**Grafts (each chosen where a judge panel found it beats the backbone for one of the seven required
components):**

- from **symmetry** → the **saddle mechanism token** in identity, an explicit **depth signature**, the
  **provably-complete / collision-free canonical form** (full tuple authoritative, digest as index only),
  and the **`r_id ≥ rcut` "never coarser than the harvest" invariant** with the *refines-`event_id`* test;
- from **descriptor** → the **"one decorated stencil, three readouts"** unification (identity `κ`,
  fallback feature `φ`, invertible reverse coordinates from one object), **decorate-vacuum-as-`EMPTY`
  so the surface subgroup falls out of the data**, **per-`family_id` regressors**, **backward-pair
  synthesis**, and the exact `event_table.py` column / orthorhombic-`cKDTree` plumbing;
- from **performance** → the entire **cache-aware substrate** (tiled struct-of-arrays, O(1) swap-remove
  species lists, `nn12`-table↔arithmetic-neighbour scale switch, `supported_by` dirty index), the
  **I1–I5 invariants** including the **I5 full-rebuild oracle**, the **equiatomic spatial-index anchor
  fallback**, **detailed-balance from a single per-pair ΔE**, and **Erlebacher-dissolution-as-a-BKL-class**
  with the *sites-never-re-index* insight.

Every graft below is reconciled into one schema set and one control flow; there are no orphaned
mechanisms. Two of the parents' load-bearing claims about pyKMC's `sym_perm` were mutually contradictory
in the judge reports; §4.7 resolves them against the source (`symmetries.py`) and states the *correct*,
weaker cross-check — a synthesis-only correction that neither parent got right.

---

## 0. Thesis, lineage, and the graft map

Classical on-lattice KMC (Bortz–Kalos–Lebowitz n-fold-way; compiled process-list codes of the
kmos/SPPARKS/KMCLib lineage; self-learning KMC of Trushin–Kara–Rahman — the closest published analogue,
a fixed lattice + a pattern database of saddles; k-ART for the off-lattice/topological-reuse half;
cluster-expansion KMC for alloy barriers) gets its speed from one fact: **the set of possible elementary
moves is small, local, and known before the run**, so it can be compiled into per-site templates whose
matches are enumerated once and **repaired only where the lattice changed**. Per step the cost is a small
constant, independent of system size.

The twist is that the process list is not hand-written: it is **harvested** from pyKMC (pARTn saddle
searches + graph/coordination environment classification + IRA point-set reuse), which emits relaxed,
atom-only, subset-relative event records. This engine turns each record into a **compiled lattice
pattern** — a spatial stencil of occupancy predicates + an occupancy-change set + a rate — pre-expanded
over the slab point group, indexed for cheap matching, repaired incrementally, and alternated with pyKMC
through file-based handoffs. The convergence signal is *new harvested event classes per cycle → 0*.

### 0.1 The single unifying object

The design is organised around **one decorated context stencil per event**, from which three readouts are
computed (descriptor's thesis, adopted as the spine that ties the grafts together):

```
                 ┌── κ  = canonical_form(core-Δ + promoted context + saddle_token + depth_sig)   → IDENTITY  (§4)
decorated        │
context   ───────┼── φ  = Φ(context)   (degree-≤2 one-hot polynomial: shell counts + bond counts)  → FALLBACK RATE (§6)
stencil o(s)     │
                 └── x  = origin + R·h·(i,j,k)                                                      → REVERSE MAP (§7)
```

Because `κ`, `φ`, and `x` are deterministic functions of the *same* stencil, "exact class" (equal `κ`)
and "near miss" (small `‖Δφ‖`, same `family_id`) live in one geometry — and the reverse-map coordinates
handed back to pyKMC are read off that same object. Pattern's **core/descriptor split** is expressed
inside this stencil: the **core** sub-stencil (moved sites + 1st shell) drives runtime *matching*; the
wider **context** (out to `r_ctx ≥ rcut`) is stored in full for `φ` and the reverse map but is *promoted
into `κ`* only as far as the harvested barriers demand (SPLIT_CHECK).

### 0.2 Graft map — what came from where, and why it beats the backbone

| Component | Backbone (`pattern`) | Graft (source) | Why it wins (judge finding) | Reconciliation |
|---|---|---|---|---|
| **1 Forward projection** | KDE layer detect + Kabsch refit + parity snap + accept/warn/reject | exact-column plumbing + **orthorhombic `cKDTree` assert** + RANSAC frame fit (**descriptor**); **tiled SoA grid** + `species_sites` + scale-switch neighbours (**performance**) | descriptor = best pipeline fit / source fidelity; performance = best runtime substrate (J1/J2/J3) | grid built by §1 uses performance's SoA layout; frame fit adds RANSAC + orthorhombic guard |
| **2 Event projection** | site-change mover detection (not `move_atom_idx`) | **saddle-token extraction** (**symmetry**); explicit **context-truncation gate** (**descriptor**, closing Judge-3's nominal-mover-cluster-edge hazard) | saddle token = only proactive same-endpoint/different-path handling (J1/J2/J3) | token computed here, consumed by `κ` in §4; truncation → gate G6 |
| **3 Class identity (the heart)** | **core/descriptor split + data-driven SPLIT_CHECK**; `event_id` fan-out/fold-in reconciliation | **decorate-`EMPTY` → surface subgroup falls out** (**descriptor**); explicit **depth_sig** + **saddle_token** + **complete-invariant / collision-free** key + **`r_id ≥ rcut`** & refines-`event_id` (**symmetry**); **D4h opt-in** | descriptor's automatic group is elegant/correct but *silently merges subsurface* — symmetry's depth_sig closes it; pattern drops saddle — symmetry's token fixes it (J1/J2/J3) | one key carries group **and** depth_sig **and** saddle_token; SPLIT_CHECK *enforces* the `r_id≥rcut`/refines invariant |
| **4 Runtime matching** | compile→oriented patterns, rarest-anchor, group-BKL O(log C), incremental invalidation | **cache-aware substrate + I5 oracle + I1–I5** (**performance**); **equiatomic spatial-index fallback** (**performance** F13) | performance = runtime leader 19–20/20 (J1/J2/J3) | pattern's compile/anchor/BKL run *on* performance's SoA substrate; I5 replaces the self-heal checksum |
| **5 Rate assignment** | exact-lookup + ridge/GP fallback + flag + never-zero | **one-descriptor-three-readouts** + **per-`family_id` regressors** + consistency diagnostic (**descriptor**) | descriptor = cleanest exact↔fallback integration serving decision 4 (J1/J2/J3) | `φ` is the §0.1 readout; `family_id` = species-blind move-set class; keep pattern's GP-variance exploration ranking |
| **6 Novelty & round trip** | ingest→classes, pairing, coverage metrics, reverse map | **backward-pair synthesis** (**descriptor**); **per-pair ΔE detailed balance** (**performance**, corrected for HTST prefactors); **refines-`event_id` test** (**symmetry**) | closure mid-harvest (descriptor); cleanest reversibility (performance) — but overclaimed; symmetry's never-wrong-merge check (J1/J2/J3) | per-pair ΔE + distinct fwd/bwd ν₀ (source-verified) → *enforceable* balance where prefactors allow, flagged where not — fixes pattern's W5 **and** performance's overclaim |
| **7 Provenance & curation** | per-class provenance, gates G1–G4, audit dir + decision log, determinism | **G5 conservation gate** + **Erlebacher-dissolution class** + *sites-never-re-index* + **I1–I5** (**performance**); **content-hash byte-stability** (**symmetry/descriptor**) | performance = best extensibility 14–15/15 (J1/J2/J3) | G5 added; dissolution is the extensibility payoff of `delta_atoms`; content hash added to reverse map |

Everything else (the FCC-on-SC parity embedding, defect-anchored enumeration, deterministic ideal-site
reverse map, the four auto-gates, ps⁻¹ Arrhenius) is common to all four parents and carried unchanged.

---

## 1. Lattice frame, site model, and unified data structures

### 1.1 Integer FCC embedding (common substrate — verified numerically)

FCC with `a ≈ 3.52 Å` is the even-parity sublattice of a simple-cubic grid of spacing `h = a/2 = 1.760 Å`:

```
Site = { (i,j,k) ∈ ℤ³ : i+j+k ≡ 0 (mod 2) }
Cartesian(i,j,k) = origin + R · h · (i,j,k)ᵀ            # R ≈ I for a cube-aligned (100) slab
```

| shell | integer offsets | count | distance |
|---|---|---|---|
| 1NN "12-star" | perms/signs of `(±1,±1,0)` | 12 | `a/√2 = 2.489 Å` |
| 2NN | perms of `(±2,0,0)` | 6 | `a = 3.520 Å` |
| 3NN | perms/signs of `(±2,±1,±1)` | 24 | `a√6/2 = 4.311 Å` |

Bulk site point group = the **48 signed coordinate permutations (O_h)**; all preserve even parity and
permute each shell within itself. **(100) slab:** surface normal along `k` (=`z`); a bulk atom's 12 NN
split **4 in-layer + 4 to k+1 + 4 to k−1**; a top-surface atom keeps 4 in-layer + 4 below = **coordination
8** (correct FCC(100) surface). Coordination = count of occupied 12-star entries — which is also the
dealloying eligibility test (`coord ≤ coord_max`) for free. **Neighbour access at runtime is integer
table lookup, never a KD-tree** — the central speed win over the off-lattice engine.

### 1.2 Occupancy alphabet

```
Occ = uint8 enum { EMPTY=0, Ni=1, Cr=2, Fe=3, ..., OUTSIDE=255 }
```

`EMPTY` is descriptor's `V` — there is **no separate vacuum symbol**; surface-vs-bulk is emergent from
occupied-neighbour counts (as in pyKMC). A bulk `EMPTY` with occupied neighbours is a **vacancy**; an
above-surface `EMPTY` with occupied neighbours is an **adatom target**; an `EMPTY` with no occupied
neighbour within `rcut` is inert **vacuum**. `OUTSIDE` is a parity-forbidden / out-of-domain sentinel
that never matches an occupancy predicate — it folds the free ±z boundary cleanly. The alphabet grows
freely for ternary (extensibility); **no colour-swap symmetry** is assumed (Ni≠Cr≠Fe physically).

The **active domain** is the integer box `i∈[0,2Nx), j∈[0,2Ny), k∈[k_bot−m, k_top+m]` with an
adatom/vacuum margin `m ≈ 3` layers so above-surface events have target sites. In-plane axes are periodic
(folded by modular arithmetic on `i,j`); ±z is free (missing neighbours = `OUTSIDE`).

### 1.3 Data structures — pattern semantics on performance's cache-aware substrate

```python
@dataclass
class LatticeFrame:                 # persisted per campaign; makes the reverse map bit-reproducible
    a: float; h: float              # h = a/2, Å
    R: float[3,3]; origin: float[3] # registration; R ≈ I
    basis: float[3,3]               # default I; supports rotated/strained cells  (performance)
    n_i, n_j: int; k_range: (int,int)  # in-plane periods (PBC), non-periodic k-range incl. pad
    pbc: bool[3]                    # (True, True, False)
    layer_z: float[Nz]              # detected z of each layer k (absorbs surface relaxation/rumpling)
    strain: float[3]                # per-axis uniform strain absorbed into h_eff  (descriptor/symmetry)
    k_top, k_bot: int               # outermost occupied layers at cycle start (depth reference)
    content_hash: bytes; version: u64  # BLAKE2b of the calibrated frame (repro; symmetry/descriptor)

@dataclass
class Grid:                         # struct-of-arrays, tiled/layer-blocked site order  (performance)
    frame: LatticeFrame
    occ:   uint8[N]                 # id -> occupancy; 1 byte/site (1 MB at 1e6, 100 MB at 1e8)
    ijk:   int32[N][3]              # id -> (i,j,k)
    valid: bool[N]                  # parity-correct AND in domain
    nbr12: int32[N][12]             # NN ids; OUTSIDE sentinel at free boundary        (see scale-switch)
    nbr2:  int32[N][6]              # 2nd-shell ids
    rctx_ball: int32[N][B]          # sites within r_supp_global (dirty-region expansion)  (performance)
    depth: int16[N]                 # min layers to nearest free surface (BFS; bulk = large)
    species_sites: dict[Occ -> DynArray[int32]]  # per-species site lists incl EMPTY; O(1) swap-remove
    site_pos_in_list: int32[N]      # back-pointer inverting species_sites  (performance, I3)
    surface_k: int32[n_i*n_j]       # max occupied layer per (i,j) column (vacancy vs vacuum)
```

**Layout choices (performance-first, adopted verbatim):** site ids are assigned in **layer-blocked
(tiled)** order — within each layer, 8×8 in-plane tiles are contiguous, layers stacked — so a site and its
12-star span ≤3 adjacent layer-planes in one tile and O(1) dirty updates touch a handful of cache lines.
`nn12` (int32, 48 B/site) is the largest table: 48 MB at 1e6 (fine), 4.8 GB at 1e8 (too big). **Scale
switch:** for `N ≤ ~1e7` store `nbr12`; above that, drop the table and compute neighbours arithmetically
(`(i±1,j±1,k) mod …`, ~10 int ops) — often cheaper than the cache miss a lookup would cost at that scale.
Both are behind one `neighbours(site)` accessor.

```python
# ---- Catalogue: predicates and the unified event class ----
@dataclass
class OccPredicate:  kind:{SPECIES,EMPTY,OCC_ANY,WILDCARD}; species: frozenset[Occ]   # grey: SPECIES→OCC_ANY
@dataclass
class StencilSite:   off:(int,int,int); pred: OccPredicate
@dataclass
class DeltaSite:     off:(int,int,int); before: Occ; after: Occ
@dataclass
class PathToken:     off:(int,int,int); atom_role: int    # 2×(saddle offset) snapped to sub-lattice (symmetry)

@dataclass
class EventClass:
    # --- identity (§4) ---
    class_id:      bytes32          # BLAKE2b-256 of canonical_form — INDEX ONLY (symmetry: never the identity of record)
    canonical_form: tuple          # full exact serialization — AUTHORITATIVE, tolerance-free (symmetry)
    regime:        {Oh, D4h, C4v}   # decoration-preserving group actually used (§4.1)
    group_used:    {Oh, D4h, C4v}
    depth_sig:     DepthSig         # BULK | SUBSURF(d) | SURFACE(coord, layer-tuple)  — explicit (symmetry)
    core:          list[StencilSite]   # minimal executability pattern — drives MATCHING (pattern)
    context:       list[StencilSite]   # V-decorated shell to r_ctx≥rcut — identity + φ + reverse map
    promoted_shell: int             # how far context is folded into κ (SPLIT_CHECK cursor; pattern)
    saddle_token:  list[PathToken]  # into canonical_form — same-endpoint/different-path split (symmetry)
    delta:         list[DeltaSite]  # occupancy changes, canonical orientation
    delta_atoms:   int              # net occupancy-count change: 0 diffusion, -1 dissolution (schema hook)
    coloring:      {grey, full}
    family_id:     u32              # species-blind move-set class — selects fallback regressor (descriptor)
    orientation_count: int          # |G| / |Stab_G(decorated event)|  (compile count; §4.5)
    r_id_used:     float; anchor_pred: OccPredicate   # rarest predicate = runtime anchor (§5.2)
    # --- rate (§6) ---
    Ea: float; Ea_std: float; barriers: float[]
    nu0_f: float; nu0_b: float; prefactors: float[]   # DISTINCT fwd/bwd prefactors (HTST; source-verified)
    k_at_T: float; phi: float[d]                      # φ = §0.1 readout (descriptor)
    model_version: str|None                           # set iff any instance used a fallback rate
    # --- pairing / reversibility (§7) ---
    backward_class: bytes32|None; self_reverse: bool
    dEnergy: float|None                               # E_final − E_initial, per-pair  (performance)
    pair_status: {linked, synthesized_pending, self}  # backward-pair synthesis (descriptor)
    # --- provenance / curation (§8) ---
    source_cycles: int[]; source_rows: int[]; first_seen_cycle: int
    gate_log: list[GateResult]                        # G1..G6
    audit_status: {approved, pending, rejected, quarantined}
    fallback_stats: {times_used: i64, flux: float}    # descriptor

@dataclass
class OrientedPattern:              # one per symmetry orientation g (compiled; §5.1)
    class_id: bytes32; g: SymOp
    anchor_pred: OccPredicate; anchor_depth: DepthPred
    screen_key: uint32              # anchor species + coarse first-shell signature (fast pre-screen)
    core_off:(int,int,int)[m]; core_pred: OccPredicate[m]   # in g orientation, re-anchored at rarest site
    delta: DeltaSite[]; rate: float; fallback: bool; family_id: u32; supp_radius: int

@dataclass
class Instance:  site:int; pat: OrientedPattern; rate:float; pool_pos:int   # in a class pool
# runtime: proc_at[site]->list[Instance]; class_pool[class_id]->DynArray[Instance];
#          supported_by[site]->list[instance handles] (dirty index, performance);
#          group_fenwick over classes (+ fallback micro-groups); R_total
```

`id = linear_index(i,j,k)` is a bijection over the dense box; `nbr12/nbr2/depth` are built once with
integer arithmetic + in-plane wrap (`O(N)`, no geometry). Everything a match needs — occupancy,
neighbours, depth — is O(1) array access.

**Asserted invariants (performance's I1–I5; debug-full, production-sampled):** I1 parity (every site
`i+j+k` even); I2 NN symmetry (`t∈nbr12[s] ⟺ s∈nbr12[t]` or sentinel); I3 species-list consistency
(`s∈species_sites[occ[s]]`, inverted by `site_pos_in_list`); I4 conservation (Σ non-EMPTY constant across a
canonical cycle); **I5 rate-list equivalence** (incremental list == full rebuild; §5.4).

---

## 2. Component 1 — Forward configuration projection (snapshot → occupancy)

**Goal.** Map a relaxed off-lattice full-cell snapshot `(X: N×3 Å, types, cell)` to occupancy on the fixed
global FCC frame, reporting anything unmappable. Cost target O(N), no all-pairs search.

### 2.1 Register the frame (robust, per cycle) — pattern + descriptor's RANSAC + orthorhombic guard

Relaxed positions drift (thermal expansion, rigid translation, surface interlayer relaxation). Refit each
cycle rather than trusting a fixed grid:

```
register_frame(X, types, cell, a_nominal=3.52, prev_frame=None):
    assert is_diagonal(cell)              # orthorhombic: pyKMC's NeighborsList uses cKDTree(boxsize=diag(cell))
    n_cells_x = round(cell.Lx / a_nominal);  a = cell.Lx / n_cells_x       # exact from PBC cell (Ly cross-check; |Δ|>1% ⇒ abort)
    layer_z  = kde_peaks(X[:,2])          # 1-D KDE peaks → per-layer z centres (spacing ≈ a/2, contracted at surface)
    anchors  = atoms with coordination(rnei) ≥ Z_bulk_thr and small deviation (if prev_frame)   # deep bulk, least relaxed
    origin   = argmin_phase(X, a, layer_z)                 # coarse grid + Nelder–Mead over origin ∈ [0,a/2)³
    (R, strain) = kabsch_ransac(anchors → ideal FCC sites) # RANSAC rejects surface/defect outliers (descriptor)
    return LatticeFrame(a, R, origin, ..., layer_z, strain, k_top, k_bot, content_hash=blake2b(...))
```

Layer detection (not ideal `a/2` spacing) is what makes surface relaxation harmless: each atom snaps to
its **detected** layer plane, so a contracted top layer still maps 1:1. RANSAC (graft from descriptor) is
essential because surface atoms deviate most and would drag a plain least-squares fit.

### 2.2 Snap atoms to sites (O(1) per atom, no search)

```
project(X, types, frame):
    occ = EMPTY over valid domain;  residual=[]; unmappable=[]; collision=[]
    for atom p in X:
        u = (1/h) · Rᵀ · (X[p] − origin)                # lattice-index coordinates
        s = round_to_even_parity(u)                     # nearest of the 2 parity-correct candidates
        d = |X[p] − Cartesian(s)|                       # snap residual (Å), min-image in-plane
        residual.append((p,d))
        if d > snap_tol(coord_of_layer(s)):  unmappable.append((p,d)); continue
        if occ[id(s)] != EMPTY:              collision.append((p,id(s))); keep_nearer(...); continue
        occ[id(s)] = type_to_occ(types[p])
    build surface_k, species_sites, depth (BFS from vacuum)
    return occ, ProjectionReport(residual, unmappable, collision)
```

`round_to_even_parity(u)`: round `u`, and if the parity is odd, flip the single coordinate with the
largest rounding error — O(1), exact nearest-FCC-site (the Voronoi cell of an FCC site is the rhombic
dodecahedron inscribed in the SC cube of the two candidate parities).

### 2.3 Tolerances, thresholds, cycle policy

- `snap_tol = 0.9 Å` (`≈0.36·nn`; half-nn = 1.24 Å) — below this an atom is unambiguously "on" its site
  given thermal + surface relaxation; above it it is genuinely off-lattice.
- `soft_surface_tol = 1.05 Å` applied only to top-surface atoms (which relax most).
- **Collision:** keep the nearer atom; the displaced atom becomes unmappable.
- **Vacancy vs vacuum:** `surface_k[i,j] = max k occupied in that column`; an `EMPTY` below its column's
  envelope is a **vacancy**, above it **vacuum** (one O(N) scan; drives vacancy-anchored enumeration, §5).

| Condition | Verdict |
|---|---|
| 0 unmappable, max residual < `snap_tol` | **accept** |
| ≤ `n_soft` (3) unmappable, all top-surface, each < `soft_surface_tol` | **accept + warn** to provenance |
| > `n_soft`, or any bulk atom unmappable, or a cluster of adjacent unmappables | **reject snapshot**: FCC assumption locally broken (dislocation/amorphisation/melt). Retry once with widened `snap_tol`; else fall back to the last accepted snapshot and raise `PROJECTION_STRUCTURAL` audit. Do **not** execute on-lattice from a broken projection. |

Because snapshots are pyKMC minima, `f` should be 0 in the healthy regime; any nonzero `f` is signal, not
noise, so flux is never silently dropped. The report `{max_residual, residual_histogram, n_unmappable,
unmappable_ids, n_collision}` is written to the cycle log and drives the coverage report (§7.3). A bimodal
residual histogram (a second peak near `nn/2`) signals systematic mis-registration → refit or reject.

---

## 3. Component 2 — Event projection (reference row → on-lattice event)

**Goal.** Turn one pyKMC reference row into an on-lattice event: a **set of (site, occ_before → occ_after)
changes** plus context, plus the **saddle token**. The row stores a *local, subset-relative* cluster
(`initial_positions = min1[rcut-nbrs-of-mover]`, etc.), so projection is local and self-contained.

### 3.1 Fit the event's own local FCC frame

```
project_event(row):
    P0,P2 = row.initial_positions, row.final_positions   # subset arrays (M×3)
    T0    = row.initial_types                            # or None (grey)
    frame_e = fit_local_fcc(P0, seed=row.move_atom_idx)  # orthogonal-Procrustes of nn bond dirs to ideal (±1,±1,0); a from mean bond length
```

`fit_local_fcc` matches the cluster's nn bond directions to the 12 ideal `⟨110⟩` directions (a small
Procrustes problem seeded on the mover) and pins `h` from the mean bond length; the cluster is tens of
atoms, so this is milliseconds. The **surface normal / z-sign** is fixed from the *missing* NN directions
(the vacuum hemisphere has fewer than 12 neighbours) so `+z` points outward — this decides the symmetry
regime (§4.1) without needing the global site the event came from.

### 3.2 Detect the TRUE site-change set (do not trust `move_atom_idx`)

```
    S0 = { snap(P0[p], frame_e) : p in cluster };  S2 = { snap(P2[p], frame_e) }
    movers = { p : snap_site(P0[p]) != snap_site(P2[p]) }        # site change is GROUND TRUTH
    assert row.move_atom_idx ∈ movers  else  flag(MOVER_DISAGREEMENT)   # gate G4 (§8.2)
    hull_sites = enumerate_lattice_sites_inside_convex_hull(P0, frame_e)   # empties = vacancies/adatom targets
```

`event_movers`-style displacement thresholds are a *pre-filter only*; the **site-change test is the
truth** — an atom vibrating past `matching_thr` but keeping its ideal site is not a mover; a quiet
cross-site atom is. This catches the concerted case the schema warns about (`move_atom_idx` names one of
several).

### 3.3 Build Δ, context, and the saddle token

```
    touched = sites(S0 ∪ S2 ∪ empties that differ)
    delta   = [ DeltaSite(off=t−anchor, before=occ_before(t), after=occ_after(t)) for t in touched if changed ]
    delta_atoms = (#occupied_after − #occupied_before)          # 0 diffusion; hook for dissolution
    ctr     = lattice_round(centroid(moved sites))
    context = [ StencilSite(off=s−anchor, pred=species_pred(occ_before(s)))       # V-decorated: EMPTY sites included
                for s in lattice_sites_within(ctr, r_ctx) ]     # r_ctx = union of 1st+2nd NN shells, ≥ rcut  (§4.4)
    truncated = (cluster does not cover the full r_ctx footprint of every moved site)   # gate G6 (descriptor)
    # --- saddle mechanism token (graft: symmetry) ---
    for p in movers:
        tok = round_to_sublattice( 2 · (snap_frac(row.saddle_positions[p]) − midpoint(S0[p], S2[p])) )
        saddle_token.append(PathToken(off=tok, atom_role=role(p)))     # bridge vs hollow lands on distinct integer points
    return ProjectedEvent(anchor, delta, delta_atoms, context, saddle_token, regime_hint(normal_e),
                          truncated, Ea_fwd, Ea_bwd, nu0_f, nu0_b, source_row)
```

- **Context is decorated with `EMPTY`** (descriptor's `V`): the empty sites *inside* the local footprint
  are part of identity, so the surface subgroup can fall out of the decoration automatically (§4.1) and the
  vacancy arrangement modulating the barrier is captured.
- **`r_ctx`** is the union of the 1st + 2nd NN shells of every moved site, and is held **`≥ rcut`**
  (symmetry's invariant, §4.4) so the engine never has *less* environment than pyKMC saw.
- **Saddle token** (graft, symmetry): the saddle is intrinsically off-lattice and is **not snapped to a
  site**; instead its displacement relative to the endpoint midpoint is quantised to the integer
  sub-lattice (bridge midpoints and hollow centres land on distinct half-integer points, `2×` of which are
  integers) and canonicalised with the same group as the rest of the key. This makes two events with
  identical endpoints but different saddle paths (over-bridge vs through-hollow) get **distinct keys a
  priori** — the on-lattice analogue of pyKMC's own `id_saddle` / IRA saddle check, and the fix to
  pattern's biggest identity weakness.
- **Truncation gate** (graft, descriptor): because the stored cluster is centred on the *nominal* mover,
  a *second* mover of a concerted event can sit near the cluster edge with a truncated `r_ctx` shell
  (Judge 3's hazard). If any moved site's `r_ctx` footprint is not fully covered by the cluster, the event
  is admitted with a `truncated` marker and flagged for a larger-`rcut` re-harvest (gate G6, §8.2).

**Output:** `ProjectedEvent{ anchor, delta, delta_atoms, context, saddle_token, regime, truncated,
Ea_fwd, Ea_bwd, nu0_f, nu0_b, source_row }`.

---

## 4. Component 3 — Class identity (the heart)

**Question.** When are two projected events the *same lattice event class*? **Answer:** iff their
`(core + promoted context + delta + saddle_token + depth_sig)` canonicalise to the same form under the
**decoration-preserving lattice group appropriate to a (100) slab**, with species decoration respected.
This section fuses pattern's split/SPLIT_CHECK backbone with descriptor's decorated-group mechanism and
symmetry's depth signature, saddle token, complete-invariant guarantee, and `r_id ≥ rcut` invariant.

### 4.1 The symmetry group — descriptor's decorated group + symmetry's explicit depth signature

The engine canonicalises under a slab group `G` and lets **the `EMPTY`/`OUTSIDE` decoration reduce it
automatically**:

- **Default `G = O_h` (48)** over the **`EMPTY`-decorated** stencil. An O_h op that rotates the vacuum
  hemisphere (the `EMPTY`/`OUTSIDE` sites above a top layer) into the bulk produces a *different decorated
  stencil* and therefore does **not** map a surface event onto itself; only the surface-preserving
  subgroup does. For a (100) surface that surviving subgroup is exactly **C₄ᵥ (8)** — recovered *from the
  data*, with no hand-coded per-site group table (verified by the panel: the decoration-preserving
  subgroup of O_h for four top `EMPTY`s is C₄ᵥ). Bulk (fully occupied stencil) keeps the full O_h.
- **Explicit `depth_sig` in the key (graft: symmetry)** closes descriptor's one real gap: a
  fully-coordinated *subsurface* site whose `r_ctx` does not reach vacuum would otherwise be silently
  merged with true bulk. The key carries `depth_sig ∈ { BULK | SUBSURF(d) | SURFACE(coord, layer-tuple) }`
  computed from `depth[]`, so top-layer, subsurface-at-depth-d, and bulk events are **distinct classes a
  priori** even when their decorated stencils coincide — exactly the top-layer-vs-subsurface distinction
  the SPEC demands. `depth_sig` is also a **matchable predicate** (`anchor_depth`), so a surface class can
  never bind in bulk (and vice versa).
- **`D₄ₕ` bulk default is offered as a principled opt-in (graft: symmetry).** Under O_h the in-plane and
  inter-layer `⟨110⟩` hops merge into one bulk class; under D₄ₕ they split (a slab genuinely breaks O_h).
  Rather than pay symmetry's blanket over-split (which Judge 1 flagged as working against the loop's
  convergence metric), the default is **O_h + let SPLIT_CHECK (§4.4) split the two hops precisely when
  their harvested barriers differ by `> split_tol`** — so we obtain D₄ₕ's physical correctness *exactly
  where the data warrant it* and nowhere else. `config.bulk_group = D4h` forces the a-priori split for
  users on thick slabs who prefer it. This is a strictly better convergence/fidelity trade-off than either
  parent's fixed choice.

Regime selection is by context depth: if any context site has `depth ≤ d_surf` (default 2 layers) the
event "sees" the surface → use the surface-decorated group; else bulk. The residual imperfection (a
subsurface site's *true* site symmetry sits between O_h and C₄ᵥ) is bounded — at worst a convergence-cost
over-split, never a wrong merge — and is disclosed as W4.

### 4.2 Deterministic anchor and total order

```
anchor = argmin over moved sites m of key(m):
    key(m) = ( occ_priority(before(m)),         # EMPTY < Ni < Cr < Fe … (stable species order)
               round(|Cartesian(m) − centroid|, 1e-3),
               lex(offset(m)) )                 # final tie-break
```

### 4.3 Canonical form and `class_id` — symmetry's complete, collision-free invariant

```
canonical_form(delta, context_promoted, saddle_token, regime, depth_sig):
    G = group(regime)                                       # O_h(48) | D4h(16) | C4v(8)
    best = None
    for g in G:                                             # ≤ 48
        d = sorted( (g·off, before, after) for (off,before,after) in delta )
        c = sorted( (g·off, pred)          for (off,pred)          in context_promoted )
        t = sorted( (g·off, role)          for (off,role)          in saddle_token )
        best = min(best, serialize(regime, depth_sig, d, c, t))    # strict integer lexicographic order
    return best                                             # the FULL tuple — authoritative
class_id = blake2b(canonical_form, digest=32)               # 256-bit — INDEX ONLY (never the identity of record)
g_star   = argmin g                                         # winning op → stored on the instance for execution orientation
```

- The canonical form is a **provably complete invariant** (symmetry): the min over the group orbit is
  invariant under `G` by construction; anchoring on a moved site plus the min over anchors gives
  translation invariance; the decorated tuple is a faithful (invertible up to `G` and translation)
  encoding — so **equal canonical form ⟺ same orbit ⟺ same class**, with **no hash luck**. The 256-bit
  digest is kept only as a compact index; the full tuple is retained for exact tie-breaking, so identity
  never rests on a hash collision (a real hardening over pattern's 16-byte `class_id`).
- **Grey vs full colour** (matches pyKMC's `atom_coloring_mode`): grey collapses every `SPECIES` predicate
  to `OCC_ANY` before serialization (geometry + vacancy only); full colour keeps Ni/Cr/Fe distinct
  (`full` is required for NiCr — Cr and Ni barriers differ). The mode is part of the key so a catalogue is
  never silently mixed. Ternary is automatic (the alphabet grows).

### 4.4 Context size — pattern's core/descriptor split, governed by symmetry's `r_id ≥ rcut` invariant

The identity-context size is the central bias/variance knob (too large ⇒ every event unique, reuse dies;
too small ⇒ distinct-barrier events collapse, wrong rates). The design uses **two shells and grows
identity from the data**, under a hard floor:

- **Core** = moved sites + their 1st shell — the sites *causally required* for the move (target `EMPTY`,
  mover `OCC`, framing atoms present). **The core drives runtime matching** (§5).
- **Context** = out to `r_ctx = max(1st+2nd shells, rcut)` — stored in full for `φ` (§6) and the reverse
  map (§7). **Invariant (graft: symmetry): `r_ctx ≥ rcut`**, so exact-class granularity is *at least as
  fine as the granularity at which pyKMC discovered and deduped events* — the engine can never merge two
  events pyKMC distinguished.
- **Promotion into identity is data-driven (pattern's SPLIT_CHECK):** `κ` starts with core + 1st shell
  (`promoted_shell = 1`) and grows toward `r_ctx` only when barriers demand it:

```
ingest instance with class_id C, barrier Ea:
    if C exists:
        if |Ea − mean(C.barriers)| ≤ split_tol (0.15 eV):  merge (append barrier)
        else:                                              SPLIT_CHECK(C, instance)
    else: new class (audit first instance)

SPLIT_CHECK(C, outlier):
    # 1. promote the smallest context extension that separates outlier from incumbent, re-key both;
    ext = smallest_separating_shell(C.context, outlier.context)         # search 2nd→r_ctx shells, then species refinement
    if ext exists:  C.promoted_shell = ext; re-key(C); re-key(outlier); recompile
    # 2. if geometry can't separate them, raise saddle_token resolution (mechanism aliasing);
    elif saddle_tokens_differ_at_finer_resolution: raise_token_res(C); re-key
    # 3. genuinely same (context, token), different barrier → audit ambiguity.
    else: route_to_audit(C, outlier, reason=IRREDUCIBLE_SPREAD)
```

**The two invariants reinforce each other (the synthesis):** symmetry's `r_id ≥ rcut` says *what* must
hold (never coarser than the harvest); pattern's SPLIT_CHECK is the *mechanism* that enforces it — plus a
continuously-checked **refinement guarantee**: the class partition must *refine* pyKMC's
`(event_id, id_saddle)` partition (no `κ` may contain two rows pyKMC assigned different `event_id`/`id_saddle`
with a barrier gap > 0.25 eV). A violation forces SPLIT_CHECK to promote context or raise token resolution
until refinement holds. Symmetry alone left this to a manual `r_id` bump; pattern alone left the invariant
implicit — together they give an automatic, guaranteed never-wrong-merge.

### 4.5 Compile count and the orientation orbit

The number of distinct oriented realizations of a class is `orientation_count = |G| / |Stab_G(decorated
event)|` (orbit–stabilizer), computed once at compile (§5.1) by deduplicating the |G| images of
`(core ∪ delta ∪ saddle_token)`. This is the count of `OrientedPattern`s the runtime uses.

### 4.6 Reconciliation with pyKMC's `event_id` (pattern's fan-out/fold-in, kept)

`event_id` is a mode-dependent single-atom graph certificate (graph mode = pynauty; coordination mode =
`crystal/noncrystal`; CNA mode = a CNA label) — **not** a re-derivable multi-site key, which is why the
authoritative identity is the canonical form and `(event_id, id_final)` is used only as a **fast ingest
screening bucket**. One `event_id` may **fan out** into several on-lattice classes (surface orientations a
graph hash merges) and several `event_id`s may **fold into** one (bulk symmetry a hash splits); the
decorated canonical form gets both directions right where a topological hash cannot. The refines-`event_id`
test (§4.4, §7) makes the fan-out safe.

### 4.7 The `sym_matrix`/`sym_perm` cross-check — corrected (synthesis-only)

The judge panel disagreed on what `sym_perm` encodes; both `pattern` and `symmetry` built cross-checks on
mutually incompatible readings. Read against source (`symmetries.py`): `unique_symmetries` runs IRA SOFI
**species-blind** (`typ = nat*[1]`) on `initial_positions`, forms `d = initial − final`, and retains one
representative per **distinct** displacement image (`is_duplicated == False`), prepending identity.
Therefore:

- **`len(sym_perm)` is an ORBIT size, not a stabilizer** — the number of *distinct oriented images* of the
  event's displacement under the point symmetry of the relaxed cluster. (Judge 1 / Judge 2 read the code
  correctly; Judge 3's "keeps ops that preserve the displacement" is inverted — preserving ops reproduce
  the identity's image and are the ones filtered out.)
- **…but it is the orbit under the *grey symmetry of the relaxed cluster***, which already contains the
  vacancy/surface hole and is generally **reduced below the ideal lattice site group** — and, being grey,
  can also be *larger* than the full-colour on-lattice orbit for a chemically-decorated but geometrically
  symmetric cluster. So `len(sym_perm)` is **not** numerically equal to the on-lattice `orientation_count`
  under the ideal decorated group. **Pattern's "12 oriented patterns == sym_perm count" is wrong** (a bulk
  vacancy hop's cluster symmetry, with the vacancy fixing the ⟨110⟩ axis, preserves the displacement, so
  `len(sym_perm) ≈ 1`, not 12); **symmetry's "sym_perm ⊆ my stabilizer" is also wrong** (they are orbit
  reps, and the subset direction inverts in full colour).
- **Correct cross-check (adopted):** each `sym_matrix` operation, snapped to the lattice, must be
  realizable as a lattice symmetry that maps the class's (grey) canonical delta onto **one of the engine's
  generated oriented patterns** — a *containment / realizability* check, not a count-equality assertion. A
  snapped `sym_matrix` op with no corresponding oriented pattern flags a projection/registration anomaly
  and is routed to audit. Count equality holds only in the special case where the cluster's grey symmetry
  equals the ideal decorated lattice group; in general this is a soft consistency signal, used as one.

---

## 5. Component 4 — Runtime matching (compile → per-site lists → incremental update)

Pattern's matching machinery runs on performance's cache-aware substrate (§1.3). Selection and update are
O(1) in system size.

### 5.1 Compile: classes → oriented patterns

```
compile(class C):                                          # after each harvest and at run start
    G = group(C.regime); seen = {}
    for g in G:
        core_g  = [(g·off, pred) for (off,pred) in C.core]
        delta_g = [(g·off, b, a) for (off,b,a)   in C.delta]
        tok_g   = [(g·off, role) for (off,role)  in C.saddle_token]
        key = frozenset(core_g) ∪ frozenset(delta_g) ∪ frozenset(tok_g)
        if key in seen: continue                           # event's own symmetry ⇒ fewer than |G| orientations
        seen.add(key)
        emit OrientedPattern(C.class_id, g,
            anchor_pred = rarest_predicate(core_g),        # §5.2
            anchor_depth = C.depth_sig,
            screen_key = screen(core_g),
            core_off/core_pred = reanchor(core_g at its rarest site),
            delta = delta_g, rate = C.k_at_T, fallback=False, family_id = C.family_id,
            supp_radius = max|off| over core_g ∪ delta_g)
    C.orientation_count = len(seen)                        # = |G|/|Stab| (§4.5)
patterns_by_anchor[occ_pred][depth_bucket][screen_key] -> [OrientedPattern...]
r_supp_global = max over patterns of supp_radius          # global pattern support radius (grows when a larger event is ingested)
```

### 5.2 Anchor at the rarest predicate (+ equiatomic fallback)

Each pattern is **re-anchored to its scarcest site** (a vacancy, adatom target, or minority species), so
enumeration scales with defects, not atoms. For dilute vacancies on a mostly-Ni slab, anchoring a
vacancy-hop at the `EMPTY` site tests only the ~1–2 vacancy sites, not every Ni — turning initial matching
from `O(N·patterns)` into `O(#defect_sites·patterns)`. **Vacancy-free events** (rings, antisite
exchanges — the "absent from standard catalogues" mechanisms the mission targets) anchor on the
least-abundant **occupied** species present (Cr in a Ni-rich alloy) via `species_sites[Cr]`, closing the
silent-zero-flux gap symmetry's ActiveSites definition had.

**Equiatomic fallback (graft: performance F13):** a class whose anchor species is ~50/50 abundant has no
dilute anchor and degrades toward `O(N/2)`. Detected by an abundance check at compile; such classes are
routed to a **spatial-index (cell-list) enumeration** that keeps correctness at a bounded constant factor,
and are flagged as a performance note. This is the one honestly-disclosed departure from O(defects).

### 5.3 Initial match and the group-BKL rate list

```
build_rate_list(Grid, patterns):
    for candidate anchor s in ∪_pred species_sites[pred] filtered by depth:
        for P in patterns_by_anchor[occ[s]][depth_bucket[s]][screen_key[s]]:
            if match(P, s):
                inst = Instance(s, P, P.rate); proc_at[s].append(inst)
                pool = class_pool[P.class_id]; inst.pool_pos = len(pool); pool.append(inst)
                for site in touched_by(P, s): supported_by[site].append(inst)     # dirty index (performance)
                class_count[P.class_id]+=1; class_rate[P.class_id]=P.rate
    build group_fenwick over classes;  R_total = Σ class_count·class_rate

match(P, s):
    if not depth_ok(P.anchor_depth, depth[s]): return False
    for (off, pred) in zip(P.core_off, P.core_pred):
        if not pred.holds(occ[ resolve(s, off, Grid) ]): return False    # nbr-table walk; OUTSIDE if free-boundary
    return True

select():                                                  # one KMC step, group-BKL
    c    = group_fenwick.sample()                          # class w.p. ∝ count·rate → O(log C)
    inst = class_pool[c].uniform_pick()                    # O(1)
    dt   = −ln(U(0,1]) / R_total                           # BKL time advance
    return inst, dt
```

Rate is a per-class constant, so the BKL vector factorises (`R_total = Σ_c n_c·k_c` for the exact pool +
`Σ_j k_j` for the fallback pool) and selection is `O(log C)` in the number of **classes**, independent of
instance count. Fallback-rated instances form their own micro-groups keyed by discretised rate.

### 5.4 Execute + incremental invalidation (the signature) + I5 oracle

```
execute(inst):
    changed = []
    for (off, before, after) in inst.pat.delta:
        t = resolve(inst.site, off, Grid); assert occ[t] == before      # consistency guard
        occ[t] = after; update species_sites (swap-remove old, append new — O(1); back-pointer I3)
        update surface_k for t's column; changed.append(t)
    if delta_atoms != 0: update_domain_and_depth(changed)               # dissolution / surface recession hook
    accumulate SRO / composition deltas (§7.3)                          # O(#changed)
    affected = ∪_{t in changed} rctx_ball(t)                            # bounded, N-independent (performance)
    for s in affected:
        for h in supported_by[s]: remove_instance(h)                    # swap-remove pool + index: O(1) each
        proc_at[s].clear()
    for s in affected ∩ candidate anchors: rematch s (as in build_rate_list)
    group_fenwick.update(...); R_total += Δ
```

`rctx_ball(t)` is a precomputed integer neighbourhood whose size depends only on `r_supp_global`
(≈2nd–3rd shell), **independent of N**. `supported_by` (graft: performance) makes instance removal O(1)
without scanning.

**I5 full-rebuild oracle (graft: performance, replacing pattern's checksum).** Every
`audit_rebuild_interval` steps (default 1e4), rebuild the entire rate list from scratch and assert it is
**set-equal** to the incrementally-maintained list (same instances, same `R_total` to 1 ULP). A mismatch is
a hard failure with a dump. The slow, obviously-correct method is the routine oracle for the fast one —
strictly stronger than a checksum, and the reason the O(1) optimisation is trustworthy to ship.

### 5.5 Complexity (consolidated in §10)

- **Compile** `O(C·|G|·σ)` — seconds. **Initial match** `O(A·κ·σ)`, `A ≈ #defect_sites` (dilute) — once.
- **Per step** `O(D·κ·σ) + O(log C)`, `D` = dirty anchors (fixed N-independent ball, ≈30–80). **Per-step
  cost is O(1) in N** — the on-lattice invariant that makes 1e6 steps on 1e3 sites run in minutes and
  1e5–1e6 sites feasible on a node (memory-bound, not step-bound).

---

## 6. Component 5 — Rate assignment (one descriptor, three readouts)

### 6.1 Exact-lookup path

Each class stores `Ea = trimmed_mean(barriers)`, distinct `nu0_f, nu0_b = geo_mean(prefactors)` (HTST ν₀
when available, else `k_prefactor`, else `k0`), all temperature-independent. At compile:

```
k_class = nu0_f · exp(−Ea / (kB·T))          # ps⁻¹; kB = 8.6173e-5 eV/K; matches pyKMC rate_from_prefactor
```

re-evaluated only if `T` changes. This is the common path.

### 6.2 The feature map φ and per-family fallback (graft: descriptor)

When runtime matching finds an **executable core** (a geometrically valid move) but the full
descriptor/decoration matches no approved class exactly — a **near-miss** — the instance is rated by
regression **and flagged**. This is descriptor's "one geometry" unification: the *same* context stencil
that defines `κ` supplies the fallback features `φ`, so a near-miss is literally a short hop in `φ`-space
within the same object.

- **φ (§0.1 readout):** a fixed degree-≤2 polynomial of the one-hot context occupancy — per-shell
  per-species counts (linear), first-neighbour bond counts `n_XY` (bilinear — the Erlebacher broken-bond
  variables of dealloying kinetics), coordination / GCN (Calle-Vallejo generalized coordination number, a
  strong FCC-barrier correlate), surface depth, and a Warren–Cowley SRO indicator. `d ≈ 30–60`, O(shell)
  from the grid.
- **Per-`family_id` regressors (graft: descriptor):** the **discrete** move-set family (species-blind
  class — e.g. "1NN vacancy hop, surface"; "3-site ring") selects *which* regressor; the **continuous** φ
  is its input. This is the clean realization of the SPEC's exact-lookup-plus-parametric-fallback.
  - Tier 1 (default): **ridge / Bayesian linear** `Ea ≈ β·φ` (a Brønsted–Evans–Polanyi linear-barrier
    model — physically a bond-counting barrier model), with closed-form predictive variance
    `σ²(φ) = φᵀ(ΦᵀΦ+λI)⁻¹φ·s²`. Needs `n_min ≈ 8` classes in the family.
  - Tier 2 (data-rich family, ≳30 classes): **Gaussian process** (RBF on φ) — smooth, interpolates class
    means, principled σ that ranks flagged sites for exploration (pattern's GP-variance idea, kept).
  - Cold family (`< n_min`): family-mean Ea with large σ. **Never zero flux.**
- `nu0` fallback = family geometric mean (prefactor spread is small on a log scale; barriers dominate).
  Predictions are clamped to `[emin_event, emax_event]`; an out-of-bounds prediction → `high_uncertainty`,
  clamp, top exploration priority.
- **Consistency diagnostic (graft: descriptor):** on harvested cells the engine uses exact lookup but
  *also* evaluates the regressor and logs `|Ea_hat − Ea_mean|` — the model's own QC residual (a GP passes
  through the means; ridge's residual is exactly the reported bond-count model error).
- **Fitting / refit.** Fit on all harvested `(φ, Ea)` per family; leave-one-class-out CV for residual
  spread; weight by gate-cleanliness and low `Ea_std`. Refit at **cycle boundaries only** (frozen model
  between cycles ⇒ reproducible flux) when a family's class count grew ≥25% or a new class landed in a
  high-σ region. The **model version** is stamped into provenance and into any instance it rated.

### 6.3 Flag mechanism and never-zero guarantee

Every fallback-rated instance carries `flag=True`; a `flag_registry` keyed by `(family_id, cell_key)`
(a coarse φ-bucket) tracks `(count, carried_flux, first_step)`. At cycle end it is emitted, highest
flux×count first, as the **priority exploration list** for the next pyKMC leg (decision 4). **Nothing
contributes zero flux:** a geometrically-possible move with neither an exact class nor a confident
prediction gets `max(regression_pred, k_floor)` and top exploration priority — sampled, hence discovered,
rather than silently frozen.

---

## 7. Component 6 — Novelty & harvest round trip

### 7.1 Ingest new pyKMC rows → classes

```
ingest(new_rows, cycle):
    for row in new_rows:
        pe = project_event(row)                             # §3
        run_auto_gates(pe, row)                             # §8.2 (G1..G6); failures → audit
        C = class_id(canonical_form(pe.core, pe.context[:promoted], pe.saddle_token, pe.regime, pe.depth_sig))
        bucket by (row.event_id, row.id_final)              # fast screen; canonical form authoritative
        if C in catalogue:                                  # NEW INSTANCE of a known class
            append row.energy_barrier to C.barriers; append row.nu0 to prefactors; update Ea/Ea_std
            record source_cycle/row
            if |row.Ea − mean(C.barriers)| > split_tol:  SPLIT_CHECK(C, pe)         # §4.4
            if |row.Ea − mean(C.barriers)| > 0.25:       flag_audit(C, INTRA_CLASS_INCONSISTENCY)  # pyKMC's own tol
        else:                                               # NEW CLASS
            create EventClass(C, pe...); audit_status = pending; enqueue_audit(C, NEW_CLASS)   # first instance audited
        link_or_synthesize_backward(C, row)                 # §7.2
    assert class_partition refines (event_id,id_saddle) partition                    # §4.4 guarantee
    recompile changed/new APPROVED classes                                           # §5.1
```

New-class-vs-new-instance is exact canonical-form equality (a hash test on the authoritative key). First
instance of a brand-new class is auto-queued for audit and becomes matchable only after approval.

### 7.2 Forward/backward pairing + backward-pair synthesis + per-pair detailed balance

The reverse event's Δ is the inverse occupancy change on the same sites with `before ↔ after` swapped and
the saddle token shared. Pairing fuses three grafts:

```
link_or_synthesize_backward(C, row):
    if row.idx_backward present:                            # both directions harvested
        Cb = class_of(project_event(backward_row))
        assert delta(Cb) == invert(delta(C)) under some g   and   context(Cb@final)==context(C@final)
        C.backward_class = Cb.class_id; Cb.backward_class = C.class_id; C.pair_status = linked
    elif C.self_reverse (event_id == id_final, or Δ = its own inverse under g):
        C.backward_class = C.class_id; C.pair_status = self
    else:                                                   # only one direction harvested (graft: descriptor)
        Cb = synthesize_reverse(C)                          # invert Δ, context = C's D_final; barrier-PENDING
        Cb.pair_status = synthesized_pending; enqueue_audit(Cb, PAIR_CLOSURE); C.backward_class = Cb.class_id
    # --- detailed balance, per-pair ΔE (graft: performance, corrected for HTST prefactors) ---
    C.dEnergy = Ea_fwd − Ea_bwd                             # = E_final − E_initial (state energy difference)
    DETAILED_BALANCE gate (G2):  | ln(k_f/k_b) − ( ln(nu0_f/nu0_b) − dEnergy/kBT ) | < db_tol   # db_tol = 0.05
```

- **Backward-pair synthesis (graft: descriptor)** guarantees **pairing closure mid-harvest**: every class
  has a reverse in the catalogue (or is its own reverse) even before its reverse barrier is measured —
  the synthesized reverse is barrier-pending and prioritised for the next leg. Reversibility is then a
  property of the closed catalogue, not extra runtime code: after firing forward, the grid holds the
  reverse's context, so the matcher automatically enumerates the reverse instance.
- **Detailed balance is enforced/checked per-pair from a single ΔE (graft: performance) — but correctly.**
  Performance claimed `k_f/k_b = exp(−ΔE/kBT)` "by construction"; the source shows HTST produces **distinct
  forward and backward prefactors** (`nu0_f ≠ nu0_b`; `rate_constant` `ok_backward`, `nu0_b`), so the true
  relation is `k_f/k_b = (nu0_f/nu0_b)·exp(−ΔE/kBT)`. The gate G2 uses that full relation. This is
  simultaneously the fix to **pattern's W5** (balance is now *enforceable* per-pair rather than only
  checked) **and** to **performance's overclaim** (the prefactor ratio is not silently assumed unity). An
  optional `enforce_balance` mode symmetrises each pair to satisfy the relation exactly from one ΔE and one
  measured `nu0_f/nu0_b`; otherwise class-mean averaging leaves it approximate and G2 catches drift — the
  honest position, disclosed as W5'.

### 7.3 Coverage-report metrics (decision 6 — cheap O(1)/step accumulators)

- **Fallback flux fraction** `R_fallback / R_total` (both maintained by the same Fenwick updates), plus
  the fraction of **executed** steps that were fallback-rated — the headline convergence signal (decision
  4).
- **Observed-but-unharvested environments** — the `flag_registry` (§6.3): distinct local environments
  visited that no exact class covers, with visit counts and carried flux (the exploration frontier).
- **Composition / SRO drift** — running species fractions + vacancy count (each Δ), and **Warren–Cowley
  SRO** from incrementally maintained 1st-shell pair counts (each event updates only the pairs around
  `changed`, O(1)). Reported as drift from cycle start.
- **Loop convergence** = *new harvested classes per cycle → 0* = `|catalogue_after| − |catalogue_before|`.
- **Refines-`event_id` validation (graft: symmetry)** — the test that the class partition refines pyKMC's
  `(event_id, id_saddle)` groupings (never a wrong merge) is asserted each ingest (§7.1) and reported.

### 7.4 Reverse mapping — occupancy → atomistic config for pyKMC (deterministic, byte-stable)

```
to_atomistic(Grid) -> (config, content_hash):
    atoms = []
    for id in sorted(valid site ids):                       # FIXED enumeration order → determinism
        if occ[id] not in {EMPTY, OUTSIDE}:
            atoms.append( (occ_to_symbol(occ[id]), Cartesian(ijk[id], frame)) )   # EXACT ideal position
    cfg = XYZ(atoms, cell=frame_cell, pbc=(True,True,False))
    return cfg, blake2b(serialize(cfg))                      # content hash → byte-reproducibility (symmetry/descriptor)
```

Atoms are emitted at **ideal** site positions (not the relaxed snap source), so the handoff is
frame-reproducible and independent of projection residuals: identical occupancy ⇒ byte-identical
coordinates (asserted via the content hash). Empty sites emit nothing (vacancy = absent atom — pyKMC's
atom-only convention). Flagged near-miss sites are written first and recorded as the priority central-atom
list. pyKMC then minimises this ideal config, runs `k = 20–1000` steps with the cumulative reference table
preloaded (IRA dedup makes rediscovery cheap), and returns new rows → §7.1.

---

## 8. Component 7 — Provenance & curation hooks

### 8.1 Per-class provenance

Carried on every `EventClass` (§1.3): `source_cycles`, `source_rows`, `barriers[]` + `Ea/Ea_std/min/max`,
`prefactors[]` (fwd + bwd), `gate_log` (per-instance G1–G6 outcomes), `model_version` (if any rate was
regression-derived), `first_seen_cycle`, `audit_status`, `backward_class`, `pair_status`, `dEnergy`,
`delta_atoms`, `family_id`, `fallback_stats`. Every rate in the run is traceable to the off-lattice events
that produced it.

### 8.2 Automated gates (decision 5), defined precisely

Auto-admitted iff **all** gates pass; any failure, and every first-instance-of-new-class, routes to the
audit queue.

| Gate | Check | Threshold |
|---|---|---|
| **G1 barrier bounds** | `emin_event ≤ Ea_fwd ≤ emax_event` and `Ea_bwd ≥ emin_event` | reuse pyKMC's exact fields |
| **G2 fwd/bwd consistency** | asymmetry rule `(dE_f > energy_asymmetry·backward_emin) AND (dE_b < backward_emin)` ⇒ fail; **and** detailed balance `\|ln(k_f/k_b) − (ln(nu0_f/nu0_b) − dEnergy/kBT)\| < db_tol` | `db_tol = 0.05` (ln-rate units) |
| **G3 snap residual** | every cluster atom (initial **and** final) snaps `< snap_tol`; movers strictly `< snap_tol`; saddle exempt (off-lattice) | `snap_tol = 0.9 Å` |
| **G4 projection round-trip** | re-expand projected event to ideal positions → re-project → identical `class_id`; **and** `move_atom_idx ∈ detected_movers` | exact id; boolean |
| **G5 conservation (v1)** | before/after species multiset equal (atom-conserving) — catches a stray dealloying event in a canonical run *(graft: performance)* | multiset equality |
| **G6 context completeness** | cluster covers the full `r_ctx` footprint of every moved site *(graft: descriptor)* | else admit + `truncated` marker + flag larger-`rcut` re-harvest |

G3 keeps intrinsically off-lattice events (interstitials, reconstructions) out of the on-lattice catalogue
— they cannot be represented, so they are audited, not force-fitted. G4 catches mis-projection and the
concerted-mover mislabel. G5 (graft) is the v1 guard that a non-conservative event surfaces at audit
(and is the switch flipped to *enable* dissolution, §9). G6 (graft) closes the nominal-mover-cluster-edge
truncation hazard.

### 8.3 Audit queue and determinism

- **Queue interface** = a directory of records (decision 1: file-based handoffs), one JSON/parquet per
  item: `{rows, projected_pattern, canonical_form, saddle_token, gate_results, reason ∈ {NEW_CLASS,
  GATE_FAIL, OUTLIER_BARRIER, UNMAPPABLE, PAIR_CLOSURE, MOVER_MISMATCH, TRUNCATED, IRREDUCIBLE_SPREAD},
  representative_atomistic_snippet (ideal-site xyz), suggested_action}`. A human (or a later auto-approver)
  writes `approve/reject/merge/split/grow_r_ctx` into a **decision log**; approved items compile on the
  next `recompile`. `QUARANTINED` classes are excluded from execution but their descriptor signatures still
  count in the coverage report (never silently zero — they become discovery targets).
- **Determinism / reproducibility.** (a) the reverse map is deterministic by fixed site enumeration +
  ideal positions + content hash; (b) canonicalization is deterministic (fixed group-op order, total
  serialization order); (c) the audit **decision log** is replayed, so re-running a cycle reproduces the
  catalogue bit-for-bit; (d) BKL RNG is seeded and logged; (e) the fallback **model version** is pinned per
  cycle. An entire alternation run is reproducible from `{initial config, seed, decision log, model
  versions, frame content_hash}`.

---

## 9. Worked examples

### 9.1 Vacancy hop — bulk Ni (projected → classified → matched → executed)

**Off-lattice row.** ~40-atom cluster; `initial_positions` has the mover at a site with an adjacent absent
atom (the vacancy); `final_positions` has it shifted into the gap; `move_atom_idx` = the mover;
`energy_barrier ≈ 0.65 eV`; `nu0_f`, `nu0_b` set; `saddle_positions` over the ⟨110⟩ bridge.

**Project (§3).** Fit local frame. Snap: mover initial site `A=(0,0,0)`; the 12 NN enumerated; site
`B=(1,1,0)` (a ⟨110⟩ NN) is `EMPTY`. Site-change: `A ≠ B` ⇒ `movers = {mover}` (`move_atom_idx ∈ movers`
✓). Δ and context:

```
delta = [ ((0,0,0): Ni→EMPTY), ((1,1,0): EMPTY→Ni) ]     # anchor A; delta_atoms = 0
context = 1st+2nd shells around {A,B}, all Ni ⇒ no coordination deficit ⇒ regime O_h; depth_sig = BULK
saddle_token = [ PathToken over the A→B bridge midpoint ]
```

**Classify (§4).** Anchor = canonical of `{A,B}`. Canonicalize `(core-Δ + context + saddle_token +
depth_sig)` under the `EMPTY`-decorated O_h; all 12 NN directions are one O_h orbit ⇒ **one class** =
"bulk Ni ⟨110⟩ vacancy hop, over-bridge, BULK". `class_id = blake2b(canonical_form)`; the full tuple is
retained. Its stabilizer leaves `orientation_count = |O_h|/|Stab| = 48/4 = 12` oriented patterns. **Note
(§4.7): this 12 is the on-lattice orbit under the ideal decorated O_h — it is *not* `len(sym_perm)`**, which
for this cluster (the vacancy fixes the ⟨110⟩ axis, so the grey cluster symmetry preserves the
displacement) is ≈ 1; the engine cross-checks by *realizability* (each `sym_matrix` op snaps to a lattice
symmetry mapping Δ onto one of the 12 patterns), not by count equality. If a later surface event's barrier
turned out to differ for an inter-layer vs in-plane hop, SPLIT_CHECK would split this class along the
D₄ₕ line — but with uniform bulk Ni the barriers match, so O_h's single class is correct and convergence
is not taxed.

**Compile (§5.1).** 12 `OrientedPattern`s, each **re-anchored at the rarest predicate = the `EMPTY`
target**: `anchor_pred = EMPTY`, core = `{ anchor: EMPTY, (−1,−1,0): Ni, framing 1st-shell Ni }`,
`delta = { anchor: EMPTY→Ni, (−1,−1,0): Ni→EMPTY }`, `rate = nu0_f·exp(−0.65/kBT)`,
`family_id = "1NN vacancy hop, bulk"`.

**Match (§5.3).** With one vacancy in the 1e3-site slab, only that **one `EMPTY` anchor** is tested
(rarest-anchor payoff, on `species_sites[EMPTY]`). Its 12 occupied Ni neighbours each satisfy one oriented
pattern ⇒ **12 enabled instances**, one class pool, each rate `k`; `group_fenwick`: count 12, rate `k`;
`supported_by` indexes each instance under the sites it reads.

**Execute (§5.4).** BKL selects an instance — say the vacancy at `(6,6,4)` filled from Ni at `(5,5,4)`.
Apply Δ: `(5,5,4) Ni→EMPTY`, `(6,6,4) EMPTY→Ni`; `species_sites` swap-removes/appends (O(1)); `surface_k`
unchanged (bulk). `changed = {(5,5,4),(6,6,4)}`; `affected = rctx_ball` around them. Via `supported_by`,
remove the 12 old instances (O(1) each); re-enumerate 12 new instances around the new vacancy at
`(5,5,4)`. `R_total` unchanged (bulk homogeneous). `Δt = −ln(u)/R_total`. The vacancy took one NN step;
cost was **O(1) in N**. Every 1e4 steps, I5 rebuilds and asserts set-equality.

### 9.2 Three-site concerted event — NiCr surface (projected → classified → matched → executed)

A vacancy-mediated correlated exchange at the (100) surface: Ni at `A` → `B`, Cr at `B` → `C`, vacancy at
`C` → `A` — a chiral 3-site cycle. pyKMC's `move_atom_idx` names **only the Ni**; `final − initial` shows
**two** atoms displaced.

**Off-lattice row.** Cluster around the Ni (nominal mover); the free surface is on `+z` (top-layer atoms
under-coordinated). `energy_barrier ≈ 0.45 eV`; `saddle_positions` bulge over two bridges.

**Project (§3).** Fit local frame; the missing `+z` neighbours fix the outward normal. Snap initial:
Ni@`A`, Cr@`B`, `C` empty; final: Ni@`B`, Cr@`C`, `A` empty. **Site-change finds BOTH movers**
(`{Ni: A→B, Cr: B→C}`; `move_atom_idx = Ni ∈ movers` ✓ — the design does not trust `move_atom_idx`):

```
delta = [ (A: Ni→EMPTY), (B: Cr→Ni), (C: EMPTY→Cr) ]     # anchor = canonical of {A,B,C}; delta_atoms = 0
context = 1st+2nd shells around {A,B,C} incl. the EMPTY vacuum sites above ⇒ coordination deficit toward +z
          ⇒ surface event; depth_sig = SURFACE(coord 8, layer-tuple (0,0,0))
saddle_token = [ tokens for Ni and Cr (the ring bulges over its bridges) ]
```

Because the second mover (Cr) sits toward the cluster edge, G6 checks its `r_ctx` footprint is covered; if
the stored `rcut` cluster truncates it, the event is admitted `truncated` and flagged for larger-`rcut`
re-harvest (graft: descriptor).

**Classify (§4).** Anchor = canonical of `{A,B,C}`. Under the `EMPTY`-decorated O_h, the vacuum `EMPTY`s on
`+z` are preserved only by the **C₄ᵥ** subgroup — so the effective group *falls out of the decoration*
(descriptor's mechanism), and `depth_sig = SURFACE(...)` keeps this distinct from any subsurface/bulk event
with the same stencil (graft: symmetry, closing the silent-merge gap). The 3-site cycle is **chiral** and
the Ni/Cr decoration breaks all mirrors, so `orientation_count = 8` (4 rotations × 2 chiralities). The
**saddle token** distinguishes this over-bridge ring from any through-hollow ring with the same endpoints
(graft: symmetry). `class_id`, full canonical tuple retained. Reverse (Cr `C→B`, Ni `B→A`, vacancy `A→C`)
canonicalizes to a distinct `backward_class`, linked; if only the forward was harvested, it is
**synthesized barrier-pending** (graft: descriptor).

**Compile (§5.1).** ≤ 8 oriented patterns, re-anchored at the rarest predicate = the surface `EMPTY` at
`C`: `anchor_pred = EMPTY`, `anchor_depth = SURFACE(coord 8)`, core = the 3 sites + 1st-shell framing,
`delta` as above, `rate = nu0_f·exp(−0.45/kBT)`, `family_id = "3-site ring, surface"`.

**Match (§5.3).** For each surface `EMPTY` anchor at the right depth, test the 3-offset stencil: need
`A=Ni, B=Cr, C=EMPTY` in the specific relative surface geometry — matches only where that Ni–Cr–vacancy
surface motif exists (typically few instances). If instead a Ni–Ni ring had been harvested, a Ni–Cr ring
is a **near-miss** ⇒ the `"3-site ring, surface"` **family regressor** returns `(Ea_hat, σ)` from φ
(bond-count features: mover Ni, second-mover Cr, surface layer, coordinations), the instance is flagged
`provisional`, and its `cell_key` seeds the next pyKMC leg (§6.2) — **never zero flux**.

**Execute (§5.4).** BKL selects an instance; apply the 3-site Δ **atomically**: `A: Ni→EMPTY, B: Cr→Ni,
C: EMPTY→Cr`. `species_sites` and `surface_k` updated for all three columns; **SRO/composition accumulators
update** (a Cr moved outward toward the vacancy — the dealloying-relevant statistic the coverage report
tracks). `changed = {A,B,C}`; `affected = ∪ rctx_ball`; via `supported_by`, remove and re-enumerate. The
vacancy moved `C → A`, the Cr to `C`; nearby hop/exchange patterns re-enumerate, including events newly
enabled by the vacancy at `A`. `R_total` updated by Fenwick deltas; `Δt = −ln(u)/R_total`. Cost **O(1)**.
Because the reverse instance is now enumerable in the flipped state, detailed balance is preserved
(G2, §7.2). This example exercises every hard requirement: multi-site first-class,
don't-trust-`move_atom_idx`, species resolution, reduced surface symmetry (from decoration), saddle-token
mechanism fidelity, near-miss fallback, and a dealloying-relevant statistic — all on the same O(1)
incremental machinery as the trivial vacancy hop.

---

## 10. Consolidated complexity analysis

Symbols: `N` active sites (1e3–1e6); `C` classes (1e2–1e3); `|G| ≤ 48`; `P` oriented patterns
(`≈ C·|G|/stabiliser`, deduped); `κ` patterns tested per anchor after screening (1–20); `σ` stencil size
(10–30 sites); `A` candidate anchors (`≈ #defect_sites` dilute, `≤ N` general); `D` dirty anchors per step
(fixed ball, N-independent, ≈ 30–80); `d` feature dim (30–60).

| Phase | Cost | Notes |
|---|---|---|
| Build grid + `nbr12/nbr2/depth` + `species_sites` | `O(N)` integer | once per cycle; no geometry; tiled SoA |
| Register frame + project snapshot | `O(N)` snap + `O(N log N)` KDE | once per cycle |
| Compile catalogue | `O(C·\|G\|·σ)` | seconds; after each harvest |
| Initial match (rate list) | `O(A·κ·σ)` ≤ `O(N·κ·σ)` | once; dilute defects ⇒ `A ≈ #vacancies` |
| **Per KMC step** | **`O(D·κ·σ) + O(log C)`** | **N-independent** — the on-lattice invariant |
| I5 full-rebuild audit | `O(A·κ·σ)` every 1e4 steps | amortised negligible; the correctness oracle |
| Coverage accumulate / step | `O(#changed)` | running sums + SRO deltas |
| Fallback predict (per new sig) | `O(d)` | memoised per `cell_key` |
| Reverse-map emit | `O(N_occ)` | once per handoff |
| Memory | `O(N)` grid (1 MB @1e6, 100 MB @1e8) + `O(#instances)` | `nn12` table ≤1e7 sites, arithmetic above |

**At scale.** Per-step cost is independent of `N`, so 1e6 steps on 1e3 sites run in minutes, and 1e5–1e6
sites on a cluster node are limited by memory and the once-per-cycle `O(N)` build, not by the step rate.
Performance's tiled-SoA substrate + arithmetic-neighbour scale-switch closes the constant-factor gap for
the tight loop; the Python reference is correct and used as the I5 oracle. The one honestly-disclosed
degradation is the equiatomic direct-exchange class (`O(N/2)` via the spatial-index fallback, §5.2) and the
porous late-dealloying limit (`|active| → O(N)`), addressed by domain-decomposed parallel KMC as an
extension.

---

## 11. Failure-mode table

| Failure | Cause | Detection | Response |
|---|---|---|---|
| Off-lattice atom | interstitial / reconstruction / mid-transition | snap residual > `snap_tol` (§2.3, G3) | flag unmappable; structural ⇒ reject snapshot → audit; lone surface atom ⇒ accept + warn |
| Frame drift / wrong a,origin | thermal expansion, translation, tilt | registration RMS, bimodal residual histogram | RANSAC refit each cycle; orthorhombic-cell assert; persistent ⇒ audit |
| Concerted mover mislabel | `move_atom_idx` names one of several | site-change vs `move_atom_idx` (§3.2, G4) | use detected set; `mover0 ∉ movers` ⇒ audit |
| **Truncated second-mover context** | cluster centred on nominal mover | G6 context-completeness | admit `truncated`; flag larger-`rcut` re-harvest |
| Class fragmentation | context too large / over-decorated | instances-per-class ≈ 1; catalogue ~ #events | monitor reuse; core drives match; SPLIT_CHECK only grows on evidence |
| Class collapse (wrong rates) | context too small; distinct barriers merged | intra-class barrier spread > `split_tol` | SPLIT_CHECK promotes a wider shell / raises saddle-token res (§4.4) |
| **Same-endpoint, different saddle** | over-bridge vs through-hollow path | saddle_token distinguishes a priori (§3.3) | distinct keys; SPLIT_CHECK backstop if token too coarse |
| **Silent subsurface/bulk merge** | fully-coordinated subsurface stencil | explicit `depth_sig` in key (§4.1) | distinct classes a priori |
| Vacancy vs vacuum ambiguity | above-surface EMPTY vs bulk vacancy | `surface_k` column envelope | vacancy = EMPTY below envelope; vacuum inert |
| Two atoms → one site | compression / near-saddle snapshot | collision detection (§2.2) | keep nearer, flag other; frequent ⇒ reject snapshot |
| Detailed-balance violation | fwd/bwd rates/prefactors inconsistent | G2 with `ln(nu0_f/nu0_b) − dEnergy/kBT` | reject pair → audit; optional per-pair symmetrise |
| **Bulk vacancy-free event never matched** | ring/antisite away from any vacancy | rarest **occupied**-species anchor (§5.2) | anchored on minority species; equiatomic ⇒ spatial-index |
| Enabled move with no rate | novel environment, regression out of range | fallback path; never-zero guard (§6.3) | `max(regression, k_floor)` + top exploration priority |
| Rate-list desync after event | missed dirty site in incremental update | **I5** full-rebuild set-equality (§5.4) | hard fail + dump; rebuild |
| Symmetry over/under-reduction | subsurface between O_h and C₄ᵥ | regime from context depth; unit tests | conservative surface group + `depth_sig`; W4 |
| Pattern support too small | collective event exceeds `r_supp_global` | event stencil radius vs `r_supp_global` at compile | `r_supp_global = max` over catalogue; grows on ingest |
| Fallback micro-group blow-up | many distinct near-miss rates | count of fallback micro-groups | discretise fallback rates into bins |
| Non-conservative event in v1 | stray dealloying-type event harvested | G5 conservation | reject → audit (schema supports it when enabled) |
| Catalogue/coloring-mode mix | grey + full rows merged | mode is part of the key | keys never collide; distinct classes |
| Low-barrier flicker burns steps | vacancy rattling between two sites | step-rate vs clock-advance monitor | disclosed W8; super-basin layer is the extension |

---

## 12. Test plan

**Unit.**
- *Site model:* even-parity NN enumeration (exactly 12; nn = 2.489 Å), 2nd/3rd shells (6 at a; 24 at
  4.311 Å), (100) layering (4 in-layer + 8 cross-layer bulk; 8 at surface), `depth` BFS, in-plane PBC wrap;
  invariants I1 (parity), I2 (NN symmetry), I3 (species-list consistency).
- *Projection:* ideal FCC slab → exact occupancy; Gaussian-perturbed slab → same occupancy; planted
  interstitial → flagged unmappable; frame registration invariant under rigid translation/rotation/thermal
  expansion; orthorhombic-cell assertion fires on a sheared box.
- *Canonicalization:* bulk vacancy hop → **one** class over 12 orientations (O_h); surface hop → correct
  C₄ᵥ count from decoration; **depth_sig splits top-layer vs subsurface** with identical stencils;
  **saddle_token splits over-bridge vs through-hollow** with identical endpoints; species decoration
  distinguishes Ni-hop-near-Cr from pure-Ni; surface-parallel vs surface-normal hops with isomorphic
  graphs → distinct classes; canonical form is the true lexicographic min (brute-force on small events);
  **property test:** `canon(g·e) == canon(e)` over random `g∈G` and translations; two genuinely different
  decorated events → different keys.
- *`sym_perm` cross-check (§4.7):* on synthetic events, assert each `sym_matrix` op snaps to a lattice
  symmetry realizing one generated oriented pattern (realizability), and assert the count-equality does
  **not** hold in the vacancy-reduced case — guarding against re-introducing the parents' error.
- *Compile:* `orientation_count == |G|/|stabiliser|` by brute force.
- *Rate:* `k = ν₀·exp(−Ea/kBT)` matches `rate_from_prefactor` to machine precision, ps⁻¹, `k0` fallback;
  ridge/GP fallback within LOCO-CV spread; never-zero guard returns a positive rate.
- *Incremental update:* single-event dirty-set equals the brute-force set of anchors whose match status
  changed (unit-level I5); `supported_by` removal is exhaustive.

**Round-trip.**
- Project → reverse-map to ideal config → re-project → identical occupancy (idempotence); byte-stable
  reverse map (identical content hash).
- pyKMC row → project → canonical class → synthesise an instance → reverse the Δ → recovers the row's site
  changes; `forward_project(reverse_map(project(row))) == project(row)` (G4).
- Forward/backward: `Δ_bwd == invert(Δ_fwd)` under a group op; `reverse(reverse(e)) == e`; G2 passes on a
  constructed consistent pair (including the `nu0_f/nu0_b` ratio), fails on a perturbed-barrier pair;
  **backward-pair synthesis** produces a valid barrier-pending reverse when only one direction is supplied.
- Execute a known event, reverse-map, confirm pyKMC (or a stub minimiser) relaxes to the expected geometry.

**Statistical / validation.**
- *Single bulk vacancy in Ni:* on-lattice tracer diffusivity `D` vs the analytic correlated-vacancy value
  and vs a direct pyKMC run — agree within Monte-Carlo error.
- *Detailed balance:* small system with a known `dEnergy` model to equilibrium — occupancy/composition
  matches Boltzmann; per-class forward/backward flux balance.
- *Refinement vs pyKMC:* on a shared dataset, verify classes **refine** pyKMC's `(event_id, id_saddle)`
  groupings (never a wrong merge) and that intra-class barrier variance ≤ pyKMC's.
- *Incremental correctness:* incremental `R_total`/class-counts vs periodic full rebuild over 1e5 steps —
  zero drift (I5).
- *Coverage metrics:* fallback-flux fraction and unharvested-environment counts trend to 0 as the
  catalogue grows on a simple system.
- *Scaling:* per-step wall-time flat across `N ∈ {1e3,1e4,1e5,1e6}` (O(1)/step); table-vs-arithmetic
  neighbour crossover measured; I5 audit green over a long run.
- *Loop closure:* seed on-lattice from a pyKMC snapshot → run → reverse-map → pyKMC leg → confirm new
  classes per cycle → 0 on Ni(100) single-vacancy, then NiCr(100).

---

## 13. Self-declared weaknesses

- **W1 — Rigid-lattice assumption.** Surface reconstructions, large relaxations, and interstitial /
  off-lattice pathways cannot be represented; they are detected (G3) and audited, not executed. Dealloying
  can roughen or amorphise the surface — exactly where the science gets interesting — and there the engine
  degrades to "abort projection + hand back to pyKMC", capping acceleration in the regime that may matter
  most.
- **W2 — Context radius is bounded, not solved.** `r_ctx ≥ rcut` + core/descriptor split + SPLIT_CHECK +
  saddle_token reduce the risk, but `r_ctx`, `split_tol`, and the token resolution are empirical. Barriers
  depend on longer-range strain / elastic fields a finite local stencil cannot capture; the BEP linear
  fallback is approximate.
- **W3 — Fallback quality is descriptor-bound.** Bond-count / GCN / SRO features may miss the true
  barrier-determining physics for concerted or step/kink events; fallback rates can be systematically off
  until pyKMC harvests those classes. Flagging + never-zero keep flux non-zero, but it can be
  *mis-allocated* between harvests, biasing the trajectory the exploration then follows.
- **W4 — Regime is a two/three-way switch.** The decoration-preserving group + `depth_sig` fixes the
  silent-merge and top-layer-vs-subsurface cases, but a subsurface site's *true* site symmetry sits between
  O_h and C₄ᵥ; forcing the surface group there can over-split (a convergence cost, never a wrong merge). A
  rigorous fix computes the actual per-event site symmetry (as pyKMC's `unique_symmetries` does
  off-lattice) rather than a depth threshold — deferred.
- **W5' — Detailed balance is enforceable per-pair but approximate under class-mean averaging.** With the
  corrected `k_f/k_b = (nu0_f/nu0_b)·exp(−ΔE/kBT)` and the optional per-pair symmetrisation, balance can be
  enforced exactly per pair; but rates otherwise come from independently-averaged barriers and prefactors,
  so residual inconsistency can bias equilibrium — G2 catches drift but does not remove it. (This both
  fixes pattern's W5 and corrects performance's "by-construction" overclaim, which silently assumed
  `nu0_f = nu0_b`.)
- **W6 — Truncated collective events.** A genuinely collective event whose movers exceed the stored `rcut`
  cluster projects to a partial Δ. G6 detects incomplete `r_ctx` coverage and flags for re-harvest, but a
  borderline case could still yield a partial class before the larger-`rcut` leg runs.
- **W7 — Catalogue-richness cost.** In full-colour ternary, distinct decorations multiply classes and
  patterns; runtime stays O(1)/step via screening, but compile time and memory grow with catalogue
  richness — fine at 1e2–1e3 classes, needs attention beyond.
- **W8 — No super-basin acceleration on the lattice.** Flickering low-barrier pairs (a vacancy rattling
  between two sites) burn steps; an absorbing-Markov super-event layer over the grouped BKL is the natural
  next addition but is out of v1 scope (disclosed by performance; honest boundary).
- **W9 — Equiatomic anchor degradation.** A ~50/50 direct-exchange class has no dilute anchor; the
  spatial-index fallback keeps it correct but not O(1). Acceptable for the dilute-vacancy early campaign;
  the porous late-dealloying end-state pushes active sites toward O(N) and needs the parallel-KMC
  extension.
- **W10 — Fallback micro-group proliferation.** Group-BKL assumes intra-class rate homogeneity; many
  coexisting continuous fallback rates spawn many micro-groups. Rate binning bounds this at the cost of a
  small rate-quantisation error.
- **W11 — `sym_perm` is a soft cross-check only.** Because it is a grey orbit under the reduced cluster
  symmetry (§4.7), it validates realizability, not orientation count — a weaker consistency signal than the
  parents claimed. Registration errors that happen to preserve realizability would slip past it (caught
  instead by G4 round-trip).

---

## 14. Fit to the harvest pipeline and extensibility

- **Catalogue-first, file-based loop (decision 1).** Every artifact is a file: occupancy grid, compiled
  catalogue (Parquet of `EventClass` rows keyed by `class_id` + per-`family_id` regressor blobs, all
  stamped with a catalogue version), audit directory + decision log, coverage report, projection report,
  priority exploration list. Each leg is a scriptable step; a closed-loop driver alternates the two engines
  and watches *new-classes-per-cycle → 0*. No redesign needed to close the loop.
- **Reads / writes the real contract (decision 3, graft: descriptor plumbing).** Consumes the exact
  `event_table.py` columns (`initial/saddle/final_positions`, `initial_types`, `energy_barrier`, `k`,
  `k_prefactor`, `nu0`, `move_atom_idx`, `sym_matrix/sym_perm` for the §4.7 cross-check, `idx_backward`,
  `event_id/id_saddle/id_final`, `dra`); reuses pyKMC thresholds (`emin_event`, `emax_event`,
  `backward_emin_event`, `energy_asymmetry`, `matching_score_thr`, `rcut`) so gate verdicts match what
  pyKMC accepted; asserts the orthorhombic `cKDTree(boxsize=diag(cell))` constraint; writes an ASE-readable
  ideal-site config + the cumulative `reference_table.pickle` into the existing `config.control.
  reference_table` + `initial_config` restart contract. New deps are modest: a fixed 48-element integer
  group, a scipy KD-tree (already a pyKMC dep), ridge/GP (numpy / optional sklearn) — **no nauty on the
  lattice side**.
- **Rate model (decision 4).** Exact-class lookup + per-`family_id` BEP/GCN fallback + flag; flagged
  environments become the next leg's exploration targets; nothing is silently zero.
- **Curation (decision 5).** Precise auto-gates G1–G6 admit clean events; failures and new-class first
  instances go to the audit queue; provenance is per-class and replayable.
- **Switching + coverage (decision 6).** Fixed tunable `n` steps, then a cheap coverage report (fallback
  flux, unharvested environments, composition/SRO drift, refines-`event_id`), all accumulated O(1)/step.
- **Occupancy-count-changing events / dealloying (decision 2, graft: performance).** The
  `DeltaSite{before, after}` + `delta_atoms` schema already admits `X → EMPTY`; matching, canonicalization,
  and BKL are unchanged. The key enabling insight (graft: performance): **sites never re-index** — a removed
  atom is just an `EMPTY` site, not a re-indexing (unlike pyKMC's per-atom deletion) — so enabling
  dissolution = **drop the G5 conservation gate** for flagged classes + let `species_sites[EMPTY]` grow.
  The **Erlebacher bond-counting dissolution rate** `k = ν_d·exp((φ − n·E_b)/kBT)` drops in as a
  coordination-dependent class (φ from the same feature map, §6.2) **competing in the same grouped BKL
  vector** — no re-harvest, no schema break. This is the concrete extensibility payoff the panel rated
  highest.
- **Ternary and beyond.** The occupancy alphabet grows; predicates, canonical form, `φ`, per-family
  regressors, and SRO counters are all parameterised by the species set (a `uint8` non-event). No
  structural change.
- **Cluster promotion.** The same engine runs unchanged from a 1e2–1e3-atom workstation slab to a
  1e5–1e6-site production slab: per-step cost is N-independent; only the one-time build and memory scale
  (tiled SoA + arithmetic-neighbour scale switch), both within a single cluster node; late-stage porous
  regimes take the domain-decomposed parallel-KMC extension.
