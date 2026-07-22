# FINAL DESIGN — a precompiled-local-pattern on-lattice KMC engine with a full-context decorated-stencil identity, harvested from pyKMC off-lattice discovery

**Design name:** `synthesis` (final)
**Status:** amended to resolve all critical and major findings from the three red-team reports
(`redteam/attack-geometry.md`, `attack-symmetry.md`, `attack-statistics.md`). See **Appendix A —
Red-team changelog** for the finding-by-finding map.

**What changed structurally from the draft (read this first).** The draft's "crown jewel" was a
*core/descriptor split with barrier-driven `SPLIT_CHECK`*: coarse identity that grows only when
harvested barriers disagree. The red team showed this single decision is the root of eight of the
eleven criticals — it makes runtime matching coarser than identity (double-matching split siblings),
makes the class a *mixture* of physically distinct sub-environments (so `exp(−mean barrier)` is the
wrong rate and the detailed-balance gate is a tautology), hides genuinely new physics as "new
instances," and is ingest-order-dependent. The final design **removes `SPLIT_CHECK` entirely** and
replaces it with a strict three-way separation that the draft only gestured at:

| Concern | Final mechanism | Kills |
|---|---|---|
| **Identity** — are two events the same class? | Canonical form of the **full `r_ctx` decorated context** (never a coarse promoted shell), under the true slab point group **D₄ₕ**, minimised jointly over **anchor × group** (a genuine orbit invariant). | Sym-1, Sym-2, C3, M4 |
| **Rate** — what rate does a class fire at? | Each class is now **one physical environment**, so `barriers[]` is repeated measurement, not a mixture. Aggregate **in rate space** (`⟨exp(−Eₐ/kT)⟩`), never `exp(−⟨Eₐ⟩)`. Detailed balance from a **per-pair ΔE** recovered from linked pyKMC rows, enforced *before* averaging. | C1, C2, C4, M5, Sym-7 |
| **Matching** — which moves are executable now? | Enumerate candidate cores at the rarest anchor (cheap), then **canonicalise each candidate's full context** and hash-look-up its class; **dedup instances** by canonical touched-site set. | Sym-1, Sym-3 |

Everything else — the integer FCC embedding, the tiled struct-of-arrays substrate, rarest-predicate
anchoring, group-BKL O(log C) selection, incremental invalidation, the auto-gates, per-class
provenance, and the file-based alternation loop — is retained, but every place the geometry lens hit
(boundary unwrap, snap determinism, vacuum topology, reverse-map periodicity, frame calibration) and
every place the statistics lens hit (fallback extrapolation, staleness, convergence probe) is amended
in place.

---

## 0. Thesis, lineage, and the corrected architecture

Classical on-lattice KMC (Bortz–Kalos–Lebowitz n-fold-way; compiled process-list codes of the
kmos/SPPARKS/KMCLib lineage; self-learning KMC of Trushin–Kara–Rahman — a fixed lattice + a pattern
database of saddles; k-ART for topological event reuse; cluster-expansion KMC for alloy barriers)
gets its speed from one fact: **the set of elementary moves is small, local, and known before the
run**, so it compiles into per-site templates enumerated once and repaired only where the lattice
changed. Per step the cost is a small constant, independent of system size.

Here the process list is not hand-written: it is **harvested** from pyKMC (pARTn saddle searches +
graph/coordination environment classification + IRA point-set reuse), which emits relaxed, atom-only,
subset-relative event records. This engine turns each record into a **compiled lattice pattern** — a
spatial stencil of occupancy predicates + an occupancy-change set + a rate — pre-expanded over the
slab point group, indexed for cheap matching, repaired incrementally, and alternated with pyKMC
through file-based handoffs. Convergence is declared only when **both** (a) new harvested classes per
cycle → 0 **and** (b) an independent direct-pyKMC event-frequency probe agrees with the on-lattice
prediction (§7.5) — not on catalogue self-consistency alone.

### 0.1 The single unifying object — corrected readouts

The design is still organised around **one decorated context stencil per event**, with three
readouts — but the readouts are now cleanly separated by *purpose*, which is what the draft got wrong:

```
                 ┌── κ  = canonical_form( Δ  +  FULL r_ctx context  +  saddle_token  +  depth_sig )   → IDENTITY  (§4)
decorated        │       (D₄ₕ orbit, minimised over anchor × group — a complete invariant)
context   ───────┼── φ  = Φ(context)   (degree-≤2 one-hot polynomial: shell/bond counts, GCN, SRO)   → FALLBACK RATE only (§6)
stencil o(s)     │       (fits the UNSEEN tail; never overrides a measured class rate)
                 └── x  = origin + h·(i,j,k)   (R ≡ I on the integer lattice — tiles the PBC cell)     → REVERSE MAP (§7.4)
```

The decisive change: **`κ` uses the full `r_ctx` context, not a barrier-promoted sub-shell.** Two
events are the same class iff their *entire* `r_ctx` decoration canonicalises identically. Therefore a
class is a single physical environment; `barriers[]` is repeated measurement of it (relaxation/thermal
noise plus bounded beyond-`r_ctx` strain), and the rate is a legitimate per-class quantity — computed
in rate space. `φ` is demoted to serving **only** the fallback for *unseen* environments; it never
re-rates a measured class. `x` uses `R ≡ I` (§7.4) so the emitted lattice tiles the orthorhombic cell
exactly.

### 0.2 Where the correctness now lives (the invariants that replace `SPLIT_CHECK`)

1. **Identity completeness (Sym-2).** `κ` is the lexicographic minimum of `serialize(...)` over
   **every moved site as anchor × every g ∈ D₄ₕ**. This is the genuine orbit invariant under
   (translation × point group × internal automorphism); equal `κ ⟺ same class`, no frame dependence.
2. **Identity = full context (C3).** No coarse promoted shell participates in identity. Novelty is
   "a full-`r_ctx` context never seen," independent of barrier agreement.
3. **Single-environment rate (C1, C4).** Because a class is one environment, its rate is
   `ν₀·⟨exp(−Eₐᵢ/kT)⟩` (rate-space mean), and its ΔE comes from *linked* pyKMC row pairs, not from
   two class means.
4. **Match = enumerate core, resolve full context, dedup instance (Sym-1, Sym-3).** Exactly one
   instance per physical move, assigned to exactly one class.
5. **Never coarser than the harvest (r_id ≥ rcut).** Satisfied by construction: `r_ctx ≥ rcut` and
   identity uses all of it.
6. **Independent physics probe (C5).** Convergence requires a catalogue-*independent* check, not just
   `new-classes → 0`.

---

## 1. Lattice frame, site model, and unified data structures

### 1.1 Integer FCC embedding (common substrate — verified numerically)

FCC with `a ≈ 3.52 Å` is the even-parity sublattice of a simple-cubic grid of spacing
`h = a/2 = 1.760 Å`:

```
Site = { (i,j,k) ∈ ℤ³ : i+j+k ≡ 0 (mod 2) }
Cartesian(i,j,k) = origin + h · (i,j,k)ᵀ           # R ≡ I: the engine works in the frame-aligned lattice (§2.1, §7.4)
```

| shell | integer offsets | count | distance |
|---|---|---|---|
| 1NN "12-star" | perms/signs of `(±1,±1,0)` | 12 | `a/√2 = 2.489 Å` |
| 2NN | perms of `(±2,0,0)` | 6 | `a = 3.520 Å` |
| 3NN | perms/signs of `(±2,±1,±1)` | 24 | `a√6/2 = 4.311 Å` |

**Point groups.** The bulk FCC site group is O_h (48 signed coordinate permutations). **A (100) slab
does not have O_h symmetry** — the free surfaces in ±z break the equivalence of z with x,y. The
correct point group of the ideal (100) slab is **D₄ₕ (16)**: the subgroup of O_h that fixes the
z-axis, `{E, 2C₄(z), C₂(z), 2C₂′, 2C₂″, i, 2S₄, σ_h, 2σ_v, 2σ_d}`. **The engine canonicalises and
compiles under D₄ₕ throughout** (§4.3, §5.1). D₄ₕ is the honest slab symmetry and — critically —
**contains σ_h** (the xy-mirror relating the top and bottom free surfaces), which a C₄ᵥ surface group
would drop (Sym-4). All D₄ₕ ops preserve even parity and the (100) layering. A bulk atom's 12 NN split
4 in-layer + 4 to k+1 + 4 to k−1; a top-surface atom keeps 4 in-layer + 4 below = coordination 8
(correct FCC(100) surface). Coordination = count of occupied 12-star entries, which is also the
dealloying eligibility test (`coord ≤ coord_max`) for free. **Neighbour access at runtime is integer
table lookup, never a KD-tree** — the central speed win over the off-lattice engine.

> **Why D₄ₕ and not "O_h + split on barrier" (the draft's choice).** The draft defaulted to O_h and
> let `SPLIT_CHECK` split in-plane vs inter-layer hops when their barriers differed. That is
> order-dependent (M4), merges the top/bottom surfaces incorrectly when it reduces to C₄ᵥ (Sym-4), and
> conflates identity with rate (C3). D₄ₕ resolves all three: in-plane and inter-layer ⟨110⟩ hops are
> *distinct orbits a priori* (physically correct for a slab), both surfaces are generated by σ_h, and
> no barrier ever drives an identity decision. The only cost is that a truly bulk-like interior (where
> the real symmetry approaches O_h) keeps in-plane and inter-layer hops as two classes instead of one —
> a bounded convergence cost (≤2× on deep-bulk hop classes), never a wrong merge (disclosed W4).

### 1.2 Occupancy alphabet

```
Occ = uint8 enum { EMPTY=0, Ni=1, Cr=2, Fe=3, ..., OUTSIDE=255 }
```

`EMPTY` is the descriptor's `V` — there is **no separate vacuum symbol**; surface-vs-bulk is emergent
from occupied-neighbour counts (as in pyKMC). The distinction that matters — *vacancy* (executable
target) vs *vacuum* (inert) — is decided by a **topological flood-fill**, not a column envelope
(§1.3, §2.2; fixes Geom-6). `OUTSIDE` is a parity-forbidden / out-of-domain sentinel that never
matches an occupancy predicate; it folds the free ±z boundary cleanly. The alphabet grows freely for
ternary; **no colour-swap symmetry** is assumed (Ni≠Cr≠Fe physically).

The **active domain** is the integer box `i∈[0,2Nx), j∈[0,2Ny), k∈[k_bot−m, k_top+m]` with an
adatom/vacuum margin `m ≈ 3` layers so above-surface events have target sites. In-plane axes are
periodic (folded by modular arithmetic on `i,j`); ±z is free (missing neighbours = `OUTSIDE`).

### 1.3 Data structures — pattern semantics on a cache-aware substrate

```python
@dataclass
class LatticeFrame:                 # CALIBRATED ONCE per campaign (§2.1); makes the reverse map bit-reproducible
    a: float; h: float              # h = a/2, Å
    origin: float[3]                # calibration origin (frame-aligned; R absorbed at read — see §2.1)
    R_campaign: float[3,3]          # measured tilt at calibration; asserted ‖R_campaign − I‖ < rot_tol, then snapshots are aligned to it
    n_i, n_j: int; k_range: (int,int)  # in-plane periods (PBC), non-periodic k-range incl. pad
    pbc: bool[3]                    # (True, True, False)
    layer_z: float[Nz]              # detected z of each layer k (absorbs surface relaxation/rumpling) — USED in the snap (§2.2)
    strain: float[3]                # per-axis uniform strain absorbed into h_eff
    k_top, k_bot: int               # outermost occupied layers at calibration (depth reference)
    seeds: {ransac:int, neldermead:int}  # explicit RNG seeds recorded for reproducibility (Geom-10)
    content_hash: bytes; version: u64    # BLAKE2b of the calibrated frame

@dataclass
class Grid:                         # struct-of-arrays, tiled/layer-blocked site order
    frame: LatticeFrame
    occ:   uint8[N]                 # id -> occupancy; 1 byte/site
    ijk:   int32[N][3]              # id -> (i,j,k)
    valid: bool[N]                  # parity-correct AND in domain
    nbr12: int32[N][12]             # NN ids; OUTSIDE sentinel at free boundary  (scale-switch, §1.3 layout)
    nbr2:  int32[N][6]              # 2nd-shell ids
    rctx_ball: int32[N][B]          # sites within r_supp_global (dirty-region expansion)
    depth: int16[N]                 # min layers to the vacuum flood-fill front (BFS; capped at d_max, then BULK_OR_DEEPER)
    is_vacuum: bool[N]              # site is in the connected vacuum flood-fill component (topology-correct; Geom-6)
    species_sites: dict[Occ -> DynArray[int32]]  # per-species site lists incl EMPTY; O(1) swap-remove
    site_pos_in_list: int32[N]      # back-pointer inverting species_sites
```

**Layout (unchanged, performance-first).** Site ids are assigned in layer-blocked (tiled) order:
within each layer, 8×8 in-plane tiles are contiguous, layers stacked, so a site and its 12-star span
≤3 adjacent layer-planes in one tile and O(1) dirty updates touch a handful of cache lines. `nbr12`
(int32, 48 B/site) is 48 MB at 1e6 (fine), 4.8 GB at 1e8 (too big). **Scale switch:** for `N ≤ ~1e7`
store `nbr12`; above that, compute neighbours arithmetically (`(i±1,j±1,k) mod …`, ~10 int ops),
often cheaper than the cache miss. Both are behind one `neighbours(site)` accessor.

**Vacuum topology (replaces the column envelope; Geom-6).** After the occupancy grid is built, a
single O(N) BFS flood-fills the **connected vacuum component**: seed from the ±z margin `EMPTY` sites,
expand through `EMPTY` neighbours only. `is_vacuum[s] = True` iff `s` is reached. Then:
- an `EMPTY` site with ≥1 occupied neighbour and `is_vacuum=False` → **vacancy / adatom-target**
  (executable anchor, §5.2);
- an `EMPTY` site with `is_vacuum=True` → **inert vacuum** (never an anchor);
- `depth[s]` = BFS layer distance from the vacuum front, capped at `d_max = floor(rcut/(a/2)) − 1`;
  beyond that → the single `BULK_OR_DEEPER` bucket (§4.1, Geom-3).

This is **topology-correct for pores, overhangs, re-entrant ligaments, and subsurface voids** — a
buried pore connected laterally to vacuum is vacuum; a real vacancy under a thin ligament is a
vacancy. Same O(N) budget as the grid build.

```python
# ---- Catalogue: predicates and the unified event class ----
@dataclass
class OccPredicate:  kind:{SPECIES,EMPTY,OCC_ANY,WILDCARD}; species: frozenset[Occ]   # grey: SPECIES→OCC_ANY
@dataclass
class StencilSite:   off:(int,int,int); pred: OccPredicate
@dataclass
class DeltaSite:     off:(int,int,int); before: Occ; after: Occ
@dataclass
class PathToken:     start_rank: int; kind:{BRIDGE,HOLLOW_FCC,HOLLOW_HCP,TOP,OTHER}; coord_sig: tuple  # CATEGORICAL (§3.3)

@dataclass
class EventClass:
    # --- identity (§4) ---
    class_id:      bytes32          # BLAKE2b-256 of canonical_form — INDEX ONLY (never the identity of record)
    canonical_form: tuple          # full exact serialization — AUTHORITATIVE, tolerance-free
    depth_sig:     DepthSig         # SURFACE(coord) | SUBSURF(1..d_max) | BULK_OR_DEEPER  — operational, cluster-computable (§4.1)
    move_shape:    u32             # species-blind geometric core (moved sites + causal 1st shell) — the ENUMERATION template (§5.1)
    core:          list[StencilSite]   # geometric executability pattern — drives ENUMERATION (not identity)
    context:       list[StencilSite]   # V-decorated shell to r_ctx≥rcut — the FULL identity context + φ + reverse map
    saddle_token:  list[PathToken]  # ORDERED per-mover categorical mechanism label (§3.3, Sym-6/M1/Geom-7)
    delta:         list[DeltaSite]  # occupancy changes, canonical orientation
    delta_atoms:   int              # net occupancy-count change: 0 diffusion, -1 dissolution (schema hook)
    coloring:      {grey, full}
    family_id:     u32              # = move_shape ⊕ depth_sig — selects the fallback regressor (§6.2)
    orientation_count: int          # |D₄ₕ| / |Stab_{D₄ₕ}(decorated event)|  (§4.5)
    r_id_used:     float; anchor_pred: OccPredicate   # rarest predicate = enumeration anchor (§5.2)
    # --- rate (§6) ---   RATE-SPACE aggregation; NO trimmed mean for the rate
    barriers:      float[]; nu0_f_list: float[]; nu0_b_list: float[]   # per-member (one per contributing pyKMC row)
    dE_pair_list:  float[]          # per-member ΔE = dE_f − dE_b from the LINKED row pair (E_min2 − E_min1); independent of barriers
    k_rate_mean:   float            # ν₀·⟨exp(−Eₐᵢ/kT)⟩  — the executed rate (Jensen-exact; §6.1)
    Ea_rep:        float            # −kT·ln(⟨exp(−Eₐᵢ/kT)⟩)  — rate-equivalent barrier, for reporting
    Ea_std:        float|None       # None for n<3; shrinkage std otherwise (§6.1, m1)
    n_eff:         float            # effective sample count (fallback fit weight, m1)
    phi: float[d]                   # φ = §0.1 readout (fallback features only)
    model_version: str|None         # set iff any instance used a fallback rate
    # --- pairing / reversibility (§7) ---
    backward_class: bytes32|None; self_reverse: bool   # self_reverse is a property of κ (§7.2, Sym-5)
    dEnergy: float|None             # ⟨dE_pair_list⟩ — per-pair mean, INDEPENDENT of Ea_rep (§7.2, C2/C4)
    pair_status: {linked, synthesized_balanced, self}  # (§7.2)
    # --- provenance / curation (§8) ---
    source_cycles: int[]; source_rows: int[]; first_seen_cycle: int
    gate_log: list[GateResult]      # G1..G7
    audit_status: {approved, pending, rejected, quarantined}
    fallback_stats: {times_used: i64, flux: float}

@dataclass
class OrientedPattern:              # one per D₄ₕ orientation g (compiled; §5.1)
    class_id: bytes32; g: SymOp
    anchor_pred: OccPredicate; anchor_depth: DepthPred
    screen_key: uint32              # anchor species + coarse first-shell signature (fast pre-screen, from CORE)
    core_off:(int,int,int)[m]; core_pred: OccPredicate[m]       # enumeration stencil (geometry)
    ctx_off:(int,int,int)[q]; ctx_pred: OccPredicate[q]         # FULL promoted context predicates (verified on a screen hit; Sym-1)
    delta: DeltaSite[]; rate: float; fallback: bool; family_id: u32; supp_radius: int

@dataclass
class Instance:  site:int; g:SymOp; pat: OrientedPattern; rate:float; touched: frozenset[int]; pool_pos:int
# runtime: proc_at[site]->list[Instance]; class_pool[class_id]->DynArray[Instance];
#          instance_key = (canonical(touched), class_id)  → dedup set (Sym-3);
#          supported_by[site]->list[instance handles] (dirty index);
#          group_fenwick over classes (+ fallback micro-groups); R_total
```

`id = linear_index(i,j,k)` is a bijection over the dense box; `nbr12/nbr2/depth/is_vacuum` are built
once per cycle with integer arithmetic + in-plane wrap + one flood-fill (`O(N)`, no geometry).
Everything a match needs is O(1) array access.

**Asserted invariants (debug-full, production-sampled):** I1 parity; I2 NN symmetry
(`t∈nbr12[s] ⟺ s∈nbr12[t]` or sentinel); I3 species-list consistency; **I4 projection conservation**
(`n_occupied_sites == n_input_atoms − n_unmappable`, checked *at the projection step*, not only across
cycles — Geom-8); **I5 rate-list equivalence** (incremental list == full rebuild, §5.4); **I6 single
match** (each physical move canonicalises to exactly one `instance_key`; a second class matching the
same `instance_key` is a hard error — Sym-1/Sym-3 guard).

---

## 2. Component 1 — Forward configuration projection (snapshot → occupancy)

**Goal.** Map a relaxed off-lattice full-cell snapshot `(X: N×3 Å, types, cell)` to occupancy on the
fixed global FCC frame, reporting anything unmappable — **deterministically**. Cost target O(N).

### 2.1 Calibrate the frame ONCE, then align each snapshot (Geom-10, Geom-4)

The draft re-fit `origin/R/h` every cycle with unseeded KDE + Nelder–Mead + RANSAC, which makes the
"byte-reproducible" reverse map a fiction (a re-run yields a different frame → different ideal
positions → different discovered events). The final design **calibrates the frame once** at campaign
start and then only tracks bounded rigid drift deterministically:

```
calibrate_frame(X0, types0, cell0, a_nominal=3.52, seeds):          # ONCE, at campaign start
    assert is_diagonal(cell0)                                        # orthorhombic (pyKMC cKDTree(boxsize=diag(cell)))
    n_cells_x = round(cell0.Lx / a_nominal); a = cell0.Lx / n_cells_x   # exact from PBC cell; |a_x − a_y|>1% ⇒ abort
    layer_z  = kde_peaks(X0[:,2], min_atoms_per_peak = n_layer_floor)   # guarded KDE (Geom-9); fail→audit if peaks not separable
    anchors  = deep-bulk atoms (coordination ≥ Z_bulk_thr)              # least relaxed
    origin, R_campaign, strain = kabsch_ransac(anchors → ideal FCC, seed=seeds.ransac)
    assert ‖R_campaign − I‖ < rot_tol   else  abort→audit(FRAME_TILT)  # slab must be ~cube-aligned; standard for a (100) slab
    return LatticeFrame(a, origin, R_campaign, layer_z, strain, seeds, content_hash=blake2b(...))

register_cycle(X, types, cell, frame):                              # EACH cycle — deterministic, no RNG
    Xa = R_campaignᵀ · (X)                                          # ALIGN snapshot to the frame axes (absorbs sub-degree tilt)
    d_origin = robust_median_offset(Xa deep-bulk anchors, frame)    # bounded rigid translation only (closed form)
    h_eff    = a/2 · (1 + strain_from_cell(cell))                   # uniform thermal strain from the PBC cell (deterministic)
    assert ‖d_origin‖ < drift_tol  else  audit(FRAME_DRIFT)
    return frame with origin += d_origin, h = h_eff                 # R stays I in the aligned frame
```

Working in the **aligned frame means `R ≡ I`** for the whole engine: the snapshot is rotated into the
lattice axes at read, so the integer lattice is axis-aligned, and the reverse map (§7.4) emits
axis-aligned atoms that tile the orthorhombic cell exactly (Geom-4). RANSAC/Nelder–Mead run **once**,
seeded, recorded in `frame.seeds` — the catalogue is reproducible from `{initial config, seeds,
decision log}`. Layer detection is **used** in the snap (§2.2), not dead code (Geom-9).

### 2.2 Snap atoms to sites — deterministic, layer-aware, hysteretic (Geom-2, Geom-9, Geom-8)

```
project(X, types, frame, prev_occ=None):
    Xa = R_campaignᵀ · X
    occ = EMPTY over valid domain;  residual=[]; unmappable=[]; collision=[]; ambiguous=[]
    for atom p in Xa:
        u   = (1/h) · (Xa[p] − origin)                     # lattice-index coords (in-plane min-image)
        s1  = round_to_even_parity(u)                      # nearest parity-correct site
        s2  = second_nearest_even_parity(u)                # runner-up (for the hysteresis test)
        d1  = residual(Xa[p], s1, frame)                   # LAYER-AWARE: z scored against layer_z[k(s1)], not k·h  (Geom-9)
        d2  = residual(Xa[p], s2, frame)
        residual.append((p,d1))
        if d1 > snap_tol(depth_of(s1)):        unmappable.append((p,d1)); continue
        if (d2 − d1) < snap_hysteresis:                    # AMBIGUOUS: two sites nearly equidistant (Geom-2)
            if prev_occ is not None and prev_occ has p at s1 or s2:
                s1 = the previously-assigned site           # hysteresis: keep last cycle's grid assignment
            else:
                ambiguous.append((p, s1, s2, d2−d1)); route_to_audit; continue
        if occ[id(s1)] != EMPTY:               collision.append((p, id(s1))); continue   # DO NOT silently drop (Geom-8)
        occ[id(s1)] = type_to_occ(types[p])
    build is_vacuum (flood-fill), depth (BFS), species_sites          # §1.3
    conservation_check: assert count(occ != EMPTY) == len(X) − len(unmappable) − len(collision)   # I4 (Geom-8)
    return occ, ProjectionReport(residual, unmappable, collision, ambiguous)
```

- `round_to_even_parity(u)`: round `u`; if parity is odd, flip the coordinate with the largest
  rounding error — exact nearest-FCC-site (the Voronoi cell of an FCC site is the rhombic
  dodecahedron). **The hysteresis band `snap_hysteresis ≈ 0.3 Å`** guards the ill-conditioned
  parity-Voronoi face (Geom-2): an atom whose two nearest sites are within the band is *not*
  force-snapped by a thermal-scale tiebreak; it inherits its previous-cycle assignment or goes to
  audit. This makes the occupancy grid **deterministic under thermal jitter** (tested in §12).
- **Layer-aware residual (Geom-9):** the z-component of `d` is measured against the *detected*
  `layer_z[k]`, so a contracted/rumpled top layer maps 1:1 and its residual is not inflated toward the
  tolerance. `layer_z` is load-bearing, not stored dead code.
- **Collision = hard structural signal (Geom-8):** two atoms snapping to one site cannot be
  represented on a rigid lattice (a split-interstitial / dumbbell, exactly the off-lattice pathway the
  discovery engine is prized for finding). **Any collision routes the snapshot to audit / hand-back to
  pyKMC**, regardless of `n_soft`. An atom is never silently deleted; I4 conservation would fire if it
  were.

### 2.3 Tolerances, thresholds, cycle policy (Geom-5, Geom-8)

- `snap_tol = 0.9 Å` (`≈0.36·nn`); `soft_surface_tol = 1.05 Å` for top-surface atoms only.
- `snap_hysteresis = 0.3 Å` (§2.2).
- **Vacancy vs vacuum:** the flood-fill component `is_vacuum` (§1.3), not a column envelope (Geom-6).

| Condition | Verdict |
|---|---|
| 0 unmappable, 0 collision, 0 unresolved-ambiguous, max residual < `snap_tol` | **accept** |
| ≤ `n_soft` (3) unmappable, all top-surface, each < `soft_surface_tol`; 0 collision | **accept + warn** to provenance |
| **any collision** | **hand back to pyKMC** (structural; Geom-8) — never accept with a deleted atom |
| > `n_soft`, or any bulk atom unmappable, or a cluster of adjacent unmappables | **snapshot un-projectable** (dislocation / amorphisation / roughening) — see below |

**Un-projectable snapshots do NOT freeze the loop (Geom-5).** The draft's "fall back to the last
accepted grid" re-emits a *stale* state pyKMC has already left → the loop live-locks in exactly the
roughening regime the mission targets, and — because it produces zero new classes — falsely reads as
converged. The final policy:

1. Retry once with widened `snap_tol`.
2. If still un-projectable, **do not reverse-map a stale grid.** Hand pyKMC the **rejected (rough)
   snapshot itself** to continue *off-lattice* for this region, and mark the cycle
   `PROJECTION_STALLED`. The loop degrades gracefully to pure pyKMC where the lattice assumption is
   locally broken, rather than freezing.
3. **`PROJECTION_STALLED` is a distinct non-convergence signal** — the convergence detector (§7.5)
   treats consecutive stalls as *not converged* (never "done"), and the coverage report surfaces the
   stall streak and the un-projectable region's extent.

The report `{max_residual, residual_histogram, n_unmappable, n_collision, n_ambiguous,
stall_streak}` drives the coverage report (§7.5). A bimodal residual histogram signals systematic
mis-registration → re-calibrate or stall.

---

## 3. Component 2 — Event projection (reference row → on-lattice event)

**Goal.** Turn one pyKMC reference row into an on-lattice event: a **set of (site, occ_before →
occ_after) changes** + full context + an **ordered categorical saddle token**. The row stores a
*local, subset-relative, raw-wrapped* cluster (`initial_positions = min1[rcut-nbrs-of-mover]`, etc.;
`event_table.py:653-656`) with **no unwrap and no recentring** — so projection must unwrap first.

### 3.1 Unwrap, then fit the event's own local FCC frame (Geom-1)

```
project_event(row):
    cell = row-carried cell                                          # the event's own PBC cell
    P0 = min_image_unwrap(row.initial_positions, about=row.move_atom_idx, cell)   # UNWRAP FIRST (Geom-1)
    P2 = min_image_unwrap(row.final_positions,   about=row.move_atom_idx, cell)   # same atom order as P0
    Psad = min_image_unwrap(row.saddle_positions, about=row.move_atom_idx, cell)
    assert diameter(P0) < 2·rcut   else  gate G7 fail → audit(STRADDLING_CLUSTER)  # a straddle would exceed this
    T0 = row.initial_types                                           # or None (grey)
    frame_e = fit_local_fcc(P0, seed=row.move_atom_idx)              # Procrustes of nn bond dirs → ideal ⟨110⟩; h from mean bond length
```

**Every stored cluster is min-image-unwrapped about its `move_atom_idx` atom, using the event's own
cell, before anything else (Geom-1).** pyKMC stores raw wrapped subset coordinates and its own upstream
unwrap is ad-hoc (`point_set_registration.py:101-142` shifts by the in-plane `alat` on all three axes)
— so a mover within ~`rcut` of an in-plane face has its −x/−y ⟨110⟩ neighbours wrapped to the far side
of the box. Without the unwrap, `fit_local_fcc` sees those neighbours at ~`Lx` (not 2.49 Å), silently
drops them, and — fatally in the draft — **infers a phantom in-plane surface from the "missing"
neighbours**, routing a bulk boundary hop into the surface regime. The unwrap + diameter assertion
(gate **G7**) closes this. Because most of the in-plane area of a 10²–10³-atom slab is within `rcut` of
a boundary, this is not a corner case.

**Surface normal from the decorated EMPTY hemisphere, never from "missing" atoms (Geom-1).** The
regime is decided by whether the decorated context reaches a *vacuum-side* `EMPTY` hemisphere within
`r_ctx` (an actual under-coordination toward one face after unwrap), **not** by counting missing
neighbours (which a boundary wrap fakes). Concretely: fit the frame, enumerate the ideal `r_ctx`
lattice sites, and read which are occupied vs empty; a genuine free surface shows a *contiguous empty
hemisphere*, a boundary artifact does not (the far-side atoms are present after unwrap). See §4.1 for
how `depth_sig` is then computed operationally.

### 3.2 Detect the TRUE site-change set (do not trust `move_atom_idx`)

```
    S0 = { snap(P0[p], frame_e) : p in cluster };  S2 = { snap(P2[p], frame_e) }
    movers = { p : snap_site(P0[p]) != snap_site(P2[p]) }        # site change is GROUND TRUTH
    assert row.move_atom_idx ∈ movers  else  flag(MOVER_DISAGREEMENT)   # gate G4
    empties = lattice sites inside conv-hull(P0) that are EMPTY in S0   # vacancies / adatom targets
```

The site-change test is the truth; displacement thresholds are a pre-filter only. This catches the
concerted case the schema warns about (`move_atom_idx` names one of several).

### 3.3 Build Δ, full context, and an ORDERED categorical saddle token (Sym-6, Geom-7, M1)

```
    touched = sites(S0 ∪ S2 ∪ empties that differ)
    delta   = [ DeltaSite(off=t−anchor0, before=occ_before(t), after=occ_after(t)) for t in touched if changed ]
    delta_atoms = (#occupied_after − #occupied_before)          # 0 diffusion; hook for dissolution
    ctr     = lattice_round(centroid(moved sites))
    context = [ StencilSite(off=s−anchor0, pred=species_pred(occ_before(s)))       # V-decorated: EMPTY included
                for s in lattice_sites_within(ctr, r_ctx) ]     # r_ctx = max(1st+2nd shells, rcut, (d_surf+1)·(a/2))
    truncated = (cluster does not cover the full r_ctx footprint of every moved site)   # gate G6
    # --- saddle mechanism token: CATEGORICAL, ORDERED, computed in the class frame (§4.3) ---
    #     computed AFTER Δ-canonicalization so it lives in the canonical frame, not the noisy frame_e
    return ProjectedEvent(anchor0, delta, delta_atoms, context, movers, Psad,
                          truncated, Ea_fwd, Ea_bwd, dE_pair, nu0_f, nu0_b, row.id_saddle, source_row)
```

The saddle token is **not** a rounded continuous displacement (the draft's
`round_to_sublattice(2·(saddle − midpoint))`, which flickers across cycles as AV-relaxation noise
nudges the saddle across a cell boundary — Geom-7/M1 — and whose `role()` was undefined and canonicalised
as an unordered set — Sym-6). Instead, for each mover, in the **canonical class frame** (§4.3), the
token is the **discrete topological class of the saddle site**:

```
saddle_token[mover] = PathToken(
    start_rank = canonical_rank_of(mover.start_offset),         # invariant order key (§4.3), binds token↔mover
    kind       = classify_saddle_site(Psad[mover], S0, S2),     # BRIDGE | HOLLOW_FCC | HOLLOW_HCP | TOP | OTHER
    coord_sig  = sorted coordination signature of the saddle site's neighbouring occupied atoms )
```

- **Categorical, not rounded (Geom-7, M1):** `kind` is decided by *counting the occupied atoms
  coordinating the transition-state position* (a bridge has 2, an FCC/HCP hollow 3, a top 1) with a
  robust geometric test, plus a hysteresis band so a saddle within ε of a bridge/hollow boundary keeps
  its previously-assigned `kind` for that class. This removes the round()-boundary flicker that made
  `new-classes-per-cycle` never reach 0, and gives the token a well-defined robustness radius (the gap
  between coordination integers), not a sub-Ångström rounding threshold. The real-valued saddle offset
  is kept in **provenance** for audit, never in the identity key.
- **Ordered and mover-bound (Sym-6):** each token carries `start_rank` — the canonical rank of its
  mover's start offset under the same anchor × D₄ₕ minimisation that defines `κ` (§4.3). Canonicalisation
  keeps each mover's `(start, end, saddle-kind)` bound together, so a `g` that pairs mover-1's start
  with mover-2's saddle can no longer produce a spurious match. Two like-species movers bulging over
  different bridges stay distinct (no accidental merge), and the same concerted event in two
  orientations produces the same ordered token tuple (no fragmentation).

**Context is the full `r_ctx` decoration (C3).** All `EMPTY` sites inside the footprint are part of
identity (so the surface stabiliser falls out of the decoration and the vacancy arrangement modulating
the barrier is captured). `r_ctx = max(1st+2nd shells, rcut, (d_surf+1)·(a/2))` — the last term
(Geom-3) guarantees the cluster reaches the surface band so `depth_sig` is always resolvable up to
`d_max`.

**Output:** `ProjectedEvent{ anchor0, delta, delta_atoms, context, movers, Psad, truncated, Ea_fwd,
Ea_bwd, dE_pair, nu0_f, nu0_b, id_saddle, source_row }`.

---

## 4. Component 3 — Class identity (the heart)

**Question.** When are two projected events the same lattice event class? **Answer:** iff their
`(Δ + full r_ctx context + ordered saddle_token + depth_sig)` canonicalise to the same form under the
**(100)-slab point group D₄ₕ**, minimised **jointly over anchor choice and group element**, with
species decoration respected. This section states the *complete* invariant the draft's prose promised
but its pseudocode did not implement.

### 4.1 The group, and an operational depth signature (Sym-4, Geom-3)

- **`G = D₄ₕ (16)`, always** (§1.1). D₄ₕ is the honest (100)-slab point group, contains `σ_h`, and
  keeps z distinguished. It is used for **both** canonicalisation (§4.3) and compilation (§5.1), so an
  event harvested at the top surface **generates its bottom-surface σ_h image** and matches there
  (Sym-4). There is no C₄ᵥ group selection anywhere; the surface's *reduced stabiliser* (C₄ᵥ) falls out
  of the EMPTY/OUTSIDE decoration automatically, but the *orbit-generating group is always the full
  D₄ₕ*, which is what covers both surfaces.
- **`depth_sig` is computed operationally from the cluster (Geom-3), not from a global BFS array.**
  At ingest there is no global grid, so:

  ```
  depth_sig(cluster):
      if the decorated r_ctx reaches a contiguous EMPTY hemisphere with occupied backing:
          return SURFACE(coordination of the mover's start site)
      d = min layers from the mover to the nearest EMPTY-with-occupied-neighbour inside the cluster
      if d ≤ d_max:  return SUBSURF(d)
      else:          return BULK_OR_DEEPER          # cluster is fully coordinated to rcut — accept the merge EXPLICITLY
  ```

  This is **identically defined at ingest (from the cluster) and at runtime (from the capped global
  `depth[]`)**, so a physical event gets the same `depth_sig` both ways — closing the draft's fatal
  gap where `depth_sig` was defined from a global array unavailable at ingest, aliased `SUBSURF(2)`
  vs `BULK` across instances, and re-fragmented the class (Geom-3). **Subsurface resolution is capped
  at `d_max = floor(rcut/(a/2)) − 1`**; beyond that, `BULK_OR_DEEPER` merges everything the cluster
  cannot distinguish — an *explicit, documented* merge (the barrier difference for a mover deeper than
  `rcut` from any surface is below the harvest's own resolution), not a silent one. `depth_sig` is
  also a **matchable predicate** (`anchor_depth`), so a surface class can never bind in bulk and vice
  versa.

Regime is thus an *identity component* (a decoration + a depth bucket), never a group switch. The
residual imperfection (a subsurface site's true site symmetry lies between D₄ₕ and its surface
stabiliser) is bounded — at worst a convergence-cost over-split, never a wrong merge — and disclosed
as W4.

### 4.2 Deterministic canonical anchor set (Sym-2)

The anchor is **not** chosen by a frame-dependent tie-break. Instead, canonicalisation minimises over
*all* moved sites as candidate anchors:

```
candidate_anchors = moved sites                     # every moved site is tried as the origin
key components used only to PRUNE ties cheaply (all G-invariant):
    (occ_priority(before(m)), round(|Cartesian(m) − centroid|, 1e-3))
# NO lex(offset) tiebreak — offsets are frame-dependent and must not enter identity (Sym-2)
```

### 4.3 Canonical form and `class_id` — a genuine, complete orbit invariant (Sym-2)

```
canonical_form(delta, context, movers, saddle_raw, depth_sig):
    G = D₄ₕ (16)
    best = None
    for a in candidate_anchors:                                    # min OVER ANCHORS (translation invariance)
        for g in G:                                                # min OVER GROUP (point-group invariance)
            # re-express everything relative to anchor a, then rotate by g:
            d = sorted( (g·(off−a), before, after) for (off,before,after) in delta )
            c = sorted( (g·(off−a), pred)          for (off,pred)          in context )
            ranks = canonical_rank_map( movers, a, g )             # deterministic order of movers in THIS (a,g)
            t = tuple( token_in_frame(m, a, g, saddle_raw, ranks)  # ORDERED by start_rank; categorical kind (§3.3)
                       for m in sorted(movers by ranks) )
            best = min(best, serialize(depth_sig, d, c, t))        # strict integer lexicographic order
    return best                                                    # the FULL tuple — authoritative
class_id = blake2b(canonical_form, digest=32)                      # 256-bit — INDEX ONLY
(a*, g*) = argmin                                                  # winning anchor+op → stored on the instance for execution orientation
```

- **This is the complete invariant the draft only claimed.** The minimum is taken over
  **(anchor choice) × (group element)** = the orbit under translation × point group × internal
  automorphism. The draft minimised over the group only, about a *single* frame-dependently-chosen
  anchor, so two harvest orientations of a *symmetric* event (a divacancy concerted move where the two
  EMPTY movers tie; a minority-species ring) landed on different `class_id`s — inflating
  new-classes-per-cycle forever and splitting one event's barriers across spurious classes (Sym-2).
  Minimising over anchors removes the frame dependence: **equal canonical form ⟺ same orbit ⟺ same
  class**, with no hash luck (the 256-bit digest is an index; the full tuple is authoritative and
  tie-breaks exactly).
- **The saddle token is computed in the canonical `(a*, g*)` frame (Geom-7),** not the noisy
  per-event `frame_e`, so its `kind` classification is frame-stable. `canonical_rank_map` assigns each
  mover a deterministic order within the chosen `(a,g)`, and the token tuple is ordered by that rank —
  binding each mover's start/end/saddle together (Sym-6).
- **Cost.** `|candidate_anchors| ≤ #moved sites` (1–4 typically) × `|D₄ₕ| = 16` × `σ` compares =
  a few hundred integer ops per event — negligible at ingest, and the runtime does **not** re-run this
  over the group (the compiled oriented patterns, §5.1, pre-expand the orbit).
- **Grey vs full colour** (matches pyKMC's `atom_coloring_mode`): grey collapses `SPECIES → OCC_ANY`
  before serialization; full keeps Ni/Cr/Fe distinct (required for NiCr). The mode is part of the key
  so a catalogue is never silently mixed. Ternary is automatic.

### 4.4 Context size and the abandonment of `SPLIT_CHECK` (C3, Sym-1, M4)

**There is no barrier-driven context promotion.** Identity always uses the **full `r_ctx` context**;
`r_ctx = max(1st+2nd shells, rcut, (d_surf+1)·(a/2)) ≥ rcut`. Consequences:

- **A class is one physical environment**, not a fold-in mixture. Its `barriers[]` are repeated
  measurements of that environment (relaxation/thermal noise + bounded beyond-`r_ctx` strain), so a
  per-class rate is legitimate and is computed in rate space (§6.1). This is the root fix for C1
  (Jensen), C2 (tautological gate), C3 (new physics absorbed as an instance), and C4 (fictitious ΔE):
  all four were symptoms of identity being *coarser* than the physics.
- **Novelty is context novelty, not barrier disagreement (C3).** New-class-vs-new-instance is exact
  full-`r_ctx` canonical-form equality — a hash test on the authoritative key. A vacancy hop with a Cr
  in the 2nd/3rd shell is a **different `κ`** and is *always* recognised as a new class (audited),
  regardless of whether its barrier happens to fall within a tolerance of a pure-Ni class. The
  convergence signal is therefore honest (§7.5).
- **Order-independence (M4).** With no running-mean split decision, the catalogue partition is a pure
  function of the set of harvested rows (hash equality), independent of ingest order. Rate aggregation
  (§6.1) sums a sorted list, also order-independent. The "SPLIT_CHECK ingest-order" failure is
  structurally gone.
- **Reuse still comes from the physics, not from coarsening.** In the dilute early campaign (1–2
  vacancies, mostly Ni) the overwhelming majority of environments are pure-Ni and repeat massively →
  strong exact-match reuse. The combinatorial tail of rare decorations is served by the fallback
  regressor (§6.2), which is the honest bias/variance answer: measure the common environments exactly,
  interpolate the rare ones, and flag the interpolated ones for harvest.

**Consistency check against pyKMC's partition (M6).** The on-lattice partition must *refine* pyKMC's
saddle-keyed partition. The validator refines against a **single-frame** pyKMC key — the shared,
consistently re-derived **`id_saddle`** plus re-derived `id_min1/id_min2` — **not** the frame-inconsistent
live forward `event_id` (which is a live full-system hash while the backward/saddle keys are AV-relaxed;
`event_table.py:645-647`). The guarantee is stated in **rate units**: two pyKMC rows with different
`id_saddle` may share a `κ` only if their member rates agree within a `k_BT`-scale tolerance
(`|ΔEₐ| < δ_rate ≈ k_BT`); otherwise the shared `κ` means our context is missing a distinction the
saddle sees → **audit** (`CONTEXT_UNDERRESOLVED`). This replaces the draft's "0.25 eV barrier-gap
escape," which *legitimised* merges up to 1.6×10⁴× in rate (M6).

### 4.5 Compile count and the orientation orbit

`orientation_count = |D₄ₕ| / |Stab_{D₄ₕ}(decorated event)|` (orbit–stabilizer), computed once at
compile (§5.1) by deduplicating the 16 images of `(core ∪ delta ∪ ordered saddle_token)`. Surface
events have a smaller stabiliser (the decoration breaks the vertical-mirror/`σ_h` operations that move
the vacuum hemisphere), so more oriented patterns; bulk events have a larger stabiliser.

### 4.6 Reconciliation with pyKMC's `event_id` (fan-out/fold-in)

`event_id` is a mode-dependent single-atom graph certificate (graph = pynauty; coordination =
`crystal/noncrystal`; CNA = a label) — not a re-derivable multi-site key, and its forward/backward/saddle
components live in *inconsistent frames* (§4.4). It is therefore used **only** as a fast ingest
*screening bucket* (`bucket by row.id_saddle`), never as identity. One `event_id` may fan out into
several on-lattice classes (orientations/decorations a single-atom hash merges) and several `event_id`s
may fold into one (a bulk symmetry a hash splits); the full decorated canonical form gets both
directions right. The refines-`id_saddle` test (§4.4) makes the fan-out safe.

### 4.7 The `sym_matrix`/`sym_perm` cross-check — corrected (retained from the draft, verified)

Read against source (`symmetries.py`, verified): `unique_symmetries` runs IRA SOFI **species-blind**
(`typ = nat*[1]`) on `initial_positions`, forms `d = initial − final`, and retains one representative
per **distinct** displacement image (`is_duplicated == False`), prepending identity. Therefore
`len(sym_perm)` is an **orbit** size under the *grey, relaxed-cluster* point group — **not** the
on-lattice `orientation_count`. The cross-check is a **realizability** check, not a count equality:
each `sym_matrix` op, snapped to the lattice, must map the class's (grey) canonical delta onto one of
the engine's generated oriented patterns; a snapped op with no corresponding pattern flags a
projection/registration anomaly → audit. (All three red-team reports confirmed this reading; it is a
soft consistency signal, W11.)

---

## 5. Component 4 — Runtime matching (compile → per-site lists → incremental update)

Selection and update are O(1) in system size. The matching contract is the one the symmetry lens
demanded: **enumerate candidate moves cheaply on the core, resolve the exact class on the full
context, and admit each physical move exactly once.**

### 5.1 Compile: classes → oriented full-context patterns (Sym-1)

```
compile(class C):                                          # after each harvest and at run start
    G = D₄ₕ; seen = {}
    for g in G:
        core_g  = [(g·off, pred) for (off,pred) in C.core]          # geometric enumeration stencil
        ctx_g   = [(g·off, pred) for (off,pred) in C.context]       # FULL promoted context (Sym-1 fix)
        delta_g = [(g·off, b, a) for (off,b,a)   in C.delta]
        tok_g   = ordered_token_image(C.saddle_token, g)
        key = frozenset(core_g)∪frozenset(ctx_g)∪frozenset(delta_g)∪tuple(tok_g)
        if key in seen: continue                           # event's own symmetry ⇒ fewer than |G| orientations
        seen.add(key)
        emit OrientedPattern(C.class_id, g,
            anchor_pred  = rarest_predicate(core_g),        # §5.2
            anchor_depth = C.depth_sig,
            screen_key   = screen(core_g),                  # from CORE — fast pre-filter
            core_off/core_pred = reanchor(core_g at its rarest site),
            ctx_off/ctx_pred   = ctx_g,                     # verified on a screen hit (Sym-1)
            delta = delta_g, rate = C.k_rate_mean, fallback=False, family_id = C.family_id,
            supp_radius = max|off| over core_g ∪ ctx_g ∪ delta_g)
    C.orientation_count = len(seen)
patterns_by_anchor[occ_pred][depth_bucket][screen_key] -> [OrientedPattern...]
r_supp_global = max over patterns of supp_radius
```

The oriented pattern now carries **both** the core (for screening) and the **full context predicates**
(for exact class resolution). This is Sym-1's fix (i): the matched stencil is `core ∪ context`, so two
classes that differ only beyond the 1st shell no longer both match a site — each matches only where its
*full* context holds. The performance cost is re-stated honestly in §10 (a larger constant, still
N-independent).

### 5.2 Anchor at the rarest predicate (+ equiatomic fallback)

Each pattern is re-anchored to its scarcest **core** site (a vacancy, adatom target, or minority
species), so enumeration scales with defects, not atoms. Vacancy hops anchor at the `EMPTY` target on
`species_sites[EMPTY]` filtered to `is_vacuum=False` (Geom-6). **Vacancy-free events** (rings, antisite
exchanges — the mechanisms the mission targets) anchor on the least-abundant occupied species (Cr in a
Ni-rich alloy) via `species_sites[Cr]`, closing the silent-zero-flux gap. **Equiatomic fallback:** a
class whose anchor species is ~50/50 abundant is routed to spatial-index (cell-list) enumeration at a
bounded constant factor, flagged as a performance note (W9).

### 5.3 Initial match, instance dedup, and the group-BKL rate list (Sym-3)

```
build_rate_list(Grid, patterns):
    seen_instances = {}                                             # canonical instance dedup (Sym-3)
    for candidate anchor s in ∪_pred species_sites[pred] filtered by depth/vacancy:
        for P in patterns_by_anchor[occ[s]][depth_bucket[s]][screen_key[s]]:
            if not match(P, s): continue                            # tests CORE ∪ CONTEXT ∪ depth (§5.1)
            touched = { resolve(s, off) for off in P.delta.offsets }
            ikey = (canonical_touched(touched), P.class_id)         # canonical set → order-free identity of the move
            if ikey in seen_instances: continue                     # a symmetric multi-anchor event: admit ONCE (Sym-3)
            seen_instances.add(ikey)
            inst = Instance(s, P.g, P, P.rate, frozenset(touched))
            proc_at[s].append(inst); pool=class_pool[P.class_id]; inst.pool_pos=len(pool); pool.append(inst)
            for site in touched ∪ read_sites(P, s): supported_by[site].append(inst)
            class_count[P.class_id]+=1; class_rate[P.class_id]=P.rate
    build group_fenwick over classes;  R_total = Σ class_count·class_rate

match(P, s):
    if not depth_ok(P.anchor_depth, depth[s]): return False
    for (off, pred) in zip(P.core_off, P.core_pred):    # cheap core screen first
        if not pred.holds(occ[resolve(s, off)]): return False
    for (off, pred) in zip(P.ctx_off, P.ctx_pred):      # then FULL context (Sym-1)
        if not pred.holds(occ[resolve(s, off)]): return False
    return True

select():                                                          # one KMC step, group-BKL
    c    = group_fenwick.sample()                                  # class w.p. ∝ count·rate → O(log C)
    inst = class_pool[c].uniform_pick()                            # O(1)
    dt   = −ln(U(0,1]) / R_total                                   # BKL time advance
    return inst, dt
```

- **Instance dedup by canonical touched-site set (Sym-3).** A symmetric super-event (e.g. a divacancy
  concerted move with two equivalent `EMPTY` anchors, or a repeating-species ring) is enumerated once
  from each equivalent anchor, but all enumerations produce the **same** `instance_key`
  `(canonical_touched, class_id)` and collapse to a single `Instance`. This admits each physical move
  **exactly once**, so `R_total` is not inflated, the KMC clock is correct, and forward/backward flux
  counts `n_f`, `n_b` are the true instance counts → flux-level detailed balance holds (the draft's
  Sym-3 failure, invisible to G2, is removed). Invariant **I6** asserts no two distinct classes claim
  the same `instance_key`.
- **Same-endpoint / different-path is NOT a double-count.** If two *classes* share `Δ + context` but
  differ in `saddle_token` (over-bridge vs through-hollow), they are genuinely different competing
  mechanisms; both are enumerated as separate instances at a site — correct, not a bug.
- Rate is a per-class constant, so the BKL vector factorises (`R_total = Σ_c n_c·k_c` exact +
  `Σ_j k_j` fallback) and selection is `O(log C)` in the number of classes, independent of instance
  count. Fallback-rated instances form micro-groups keyed by discretised rate.

### 5.4 Execute + incremental invalidation + the I5 oracle

```
execute(inst):
    changed = []
    for (off, before, after) in inst.pat.delta:
        t = resolve(inst.site, off); assert occ[t] == before        # consistency guard
        occ[t] = after; update species_sites (O(1); back-pointer I3)
        update is_vacuum/depth locally for t (bounded re-flood in rctx_ball); changed.append(t)
    if delta_atoms != 0: update_domain_and_depth(changed)           # dissolution / surface recession hook
    accumulate SRO / composition deltas (§7.5)                      # O(#changed)
    affected = ∪_{t in changed} rctx_ball(t)                        # bounded, N-independent
    for s in affected:
        for h in supported_by[s]: remove_instance(h)                # swap-remove pool + index: O(1) each
        proc_at[s].clear()
    re-enumerate affected ∩ candidate anchors (with instance dedup as §5.3)
    group_fenwick.update(...); R_total += Δ
```

**I5 full-rebuild oracle.** Every `audit_rebuild_interval` steps (default 1e4), rebuild the entire rate
list from scratch and assert set-equality (same instances by `instance_key`, same `R_total` to 1 ULP).
A mismatch is a hard failure with a dump. I5 catches **incremental-update desync** (missed dirty
sites). It is *not* a physics oracle — it re-runs the same matching logic, so it cannot catch a shared
logic error; that role belongs to the catalogue-independent probe (§7.5). This division of labour is
stated explicitly (the symmetry lens correctly noted the draft over-trusted I5).

---

## 6. Component 5 — Rate assignment (AMENDED 2026-07-21: KRA-form surrogate + co-equal on-the-fly channel)

> **AMENDED 2026-07-21 — the approved `PHASEC_RATE_MODEL_DECISION.md` (with its §8 sign-off
> notes) supersedes parts of this section.** The rate channel is (b)+(c) layered: a continuous,
> detailed-balance-safe **KRA-form surrogate** `Ea_f = E_sym(env) + ½·ΔE_lattice` — with ΔE from
> **one** lattice energy model H(σ) trained exclusively on same-potential pyKMC data (memo
> §8-N3) — is the rate authority for lattice-representable events, **plus an uncertainty-gated
> on-the-fly re-search channel as a co-equal component** (new §6.4). Changes below: §6.1's
> aggregation is demoted to reporting/QC (executed rates for measured classes follow memo §8-N6);
> §6.2's per-family static φ regressor grid is **retired on direct measurement** (0.451 eV
> holdout RMSE, +0.377 eV low-barrier-tail bias — memo §2), replaced by the KRA-form pair with
> E_sym regressed on the symmetric target and coarse move-topology tiers instead of 214 families;
> M2 (out-of-hull/leverage) and M3 (drift refit) are **retained unchanged**; §6.3's flag is
> upgraded from exploration hint to on-the-fly routing authority, with the per-cycle flagged-flux
> fraction as a first-class contract output. ν0 policy: memo §8-N4 (per-pair Vineyard for
> harvested classes; log-space KRA mirror for the surrogate channel). Validation gates V1–V6:
> memo §5, accepted verbatim (§8-N7).

### 6.1 Exact-lookup path — aggregate in RATE space (C1, m1)

Because a class is one physical environment (§4.4), its `barriers[]` are repeated measurements. The
executed rate is the **occurrence-weighted mean of the member rates**, never `exp(−mean barrier)`:

```
k_rate_mean = ⟨ ν0_i · exp(−Ea_i / (kB·T)) ⟩   over sorted members     # Jensen-exact; kB = 8.6173e-5 eV/K
Ea_rep      = −kB·T · ln( k_rate_mean / ν0_geo )                        # rate-equivalent barrier, for REPORTING only
```

- **Why rate space (C1).** By Jensen's inequality `exp(−⟨Eₐ⟩) ≤ ⟨exp(−Eₐ)⟩`; the gap is exponential
  in the spread. Even a "tight" 0.05 eV measurement spread at 300 K gives a ~6× underestimate under
  mean-then-exp, and the physical flux is dominated by the *lowest*-barrier member — which
  `trimmed_mean` would preferentially discard as an "outlier." So **`trimmed_mean` is dropped for the
  rate.** (It is retained only to report a robust *representative barrier* and to *detect* an outlier
  member, which — because a class is now single-environment — signals `CONTEXT_UNDERRESOLVED` and goes
  to audit rather than being silently averaged in.) Summation is over a **sorted** member list for
  bit-reproducibility (M4).
- **Prefactors.** `ν0_i` are the per-member HTST ν₀ when available (`event_table.py:698`), else
  `k_prefactor`, else `k0`; `ν0_geo` is their geometric mean, used only to back out `Ea_rep`.
- **Uncertainty (m1).** `Ea_std = None` for `n < 3` (never 0 → never "maximally trustworthy"); for
  `n ≥ 3` a shrinkage estimate with a prior floor. `n_eff` (effective sample count) is what weights the
  fallback fit — not an `Ea_std` that is 0 for singletons.
- Re-evaluated only if `T` changes. This is the common path.
- ***(2026-07-21 amendment)*** This aggregation now serves **reporting/QC only**. The executed
  rate for a measured class follows memo §8-N6: raw harvested pair values at Phase C entry;
  once V2 passes (median |ΔE_H − dE_pair| below the measured pair-noise scale), the DB-safe
  anchored form `E_sym_measured + ½·ΔE_H`. Within-class averaging never becomes load-bearing
  (433/439 classes are singletons today; `split_tol` survives only as the §7 ingest QC screen).

### 6.2 The feature map φ and per-family fallback — with out-of-hull hard novelty (M2, M3)

> **Retired as rate law (2026-07-21 amendment).** The per-`family_id` static φ regressor grid
> below is superseded by the memo's KRA-form pair: **E_sym(env)** regressed on the *symmetric*
> target (Ea − ½ΔE) with one-hot ≤2-body + selected 3-body features, plus **½·ΔE from H(σ)**;
> conditioning by coarse move-topology tiers (vacancy hop / exchange / multi-site /
> non-conservative), not 214 families (≈2 classes/family — untrainable, below the design's own
> n_min ≈ 8). Static φ is also **not** kept as a drift detector (memo §8-N1): drift detection is
> the per-cycle out-of-hull/leverage fraction. **Retained unchanged from this subsection:** the
> M2 out-of-hull/leverage machinery (items 1–3 below, now also the canonical re-harvest drift
> detector), the leverage-growing σ, the M3 within-leg refit + `model_version` stamping, and the
> consistency diagnostic — inverted per gate V6 (the surrogate is logged against measured
> classes each cycle).

When runtime matching finds an **executable core** but no *approved class's full context* matches — a
genuine **near-miss** (an environment never harvested) — the instance is rated by regression **and
flagged**. `φ` serves *only* this tail; it never re-rates a measured class.

- **φ:** a fixed degree-≤2 polynomial of the one-hot context occupancy — per-shell per-species counts
  (linear), 1st-neighbour bond counts `n_XY` (bilinear — the Erlebacher broken-bond variables),
  generalized coordination number (GCN, a strong FCC-barrier correlate), surface depth, and a
  Warren–Cowley SRO indicator. `d ≈ 30–60`, O(shell) from the grid.
- **Per-`family_id` regressors:** `family_id = move_shape ⊕ depth_sig` selects *which* regressor; `φ`
  is its input.
  - Tier 1 (default): **ridge / Bayesian linear** `Ea ≈ β·φ` (a Brønsted–Evans–Polanyi bond-counting
    model) with closed-form predictive variance.
  - Tier 2 (≳30 classes in family): **Gaussian process** (RBF on φ).
  - Cold family (`< n_min ≈ 8`): family-mean Ea with large σ.
- **Out-of-hull is HARD novelty, not a confident extrapolation (M2).** The draft let a near-zero-variance
  Cr-bond column shrink to ≈0 and predict *Ni-like* barriers for Cr environments, and let the GP's RBF
  σ saturate at the prior (a *falsely bounded* uncertainty that under-ranked the very sites needing
  harvest). The final design:
  1. **Convex-hull / leverage test** on `φ` against the family's fitted design matrix. If `φ` is
     out-of-hull (high leverage), **do not trust the extrapolant**: assign a high **exploration floor**
     rate, flag `high_uncertainty`, and put the site at *top* exploration priority.
  2. **Require a minimum count of *that species'* environments** in the family before predicting for a
     composition involving it; else fall back to family-mean with an *honest large* σ.
  3. Use a **leverage-growing σ** (σ increases with extrapolation distance), never an RBF-prior-saturated
     σ — so exploration priority *increases* with novelty.
- **Within-leg refit on drift (M3).** The draft froze the fallback model at cycle start "for
  reproducibility," but a 10⁶-step dealloying leg deliberately drifts composition far from cycle start
  → the model is stalest exactly at the dealloying front at end-of-leg, which is the config handed to
  the next harvest. The final design **decouples reproducibility from staleness**: a within-leg refit
  is triggered when a monitored drift metric (mean `|φ − φ_fit_centroid|` over the active region, an
  O(1)/step accumulator) exceeds `drift_refit_tol`; each refit stamps a **new `model_version`** into
  the replay log, so the run stays bit-replayable while the rate model tracks the front. `n` may also
  be shortened adaptively when drift is fast.
- `nu0` fallback = family geometric mean. Predictions clamped to `[emin_event, emax_event]`; an
  out-of-bounds prediction → `high_uncertainty`, clamp, top exploration priority.
- **Consistency diagnostic:** on harvested cells the engine uses exact lookup but *also* evaluates the
  regressor and logs `|Ea_hat − Ea_rep|` — the model's own QC residual.
- **Fitting/refit.** Fit on all harvested `(φ, Ea_rep)` per family; leave-one-class-out CV for spread;
  weight by `n_eff` and gate-cleanliness (not by an `Ea_std` that is 0 for singletons, m1). The model
  version is stamped into provenance and into any instance it rated.

### 6.3 Flag mechanism and never-zero guarantee

Every fallback-rated instance carries `flag=True`; a `flag_registry` keyed by `(family_id, cell_key)`
tracks `(count, carried_flux, first_step, out_of_hull)`. At cycle end it is emitted highest
flux×count first as the **priority exploration list** for the next pyKMC leg. **Nothing contributes
zero flux:** a geometrically-possible move with neither an exact class nor a confident prediction gets
`max(regression_pred, k_floor)` and top exploration priority — sampled, hence discovered, not silently
frozen. (Unmatched moves — the Sym-4 far-surface case — cannot occur now that D₄ₕ generates both
surfaces; §7.5 additionally reports any never-matched candidate anchor as a coverage hole.)

***(2026-07-21 amendment)*** The flag is upgraded from exploration hint to **on-the-fly routing
authority** (§6.4): flagged instances fire the provisional surrogate rate (never-zero retained)
and are re-searched with top priority in the next off-lattice leg. The **per-cycle flagged-flux
fraction** is a first-class contract output — simultaneously the flood-control instrument, V1's
production acceptance metric, and the re-harvest drift trigger (memo §8-N1/N5).

### 6.4 The on-the-fly channel contract (2026-07-21 amendment — memo §1/§8-N5)

A **co-equal rate channel, not a fallback**. Trigger set: out-of-hull / high leverage (M2), a
species count the tier has never seen, or flux above threshold while surrogate-rated. Contract:
flag → provisional surrogate rate (never-zero) → **priority re-search in the next off-lattice
pyKMC leg** → harvested truth replaces the surrogate number and joins the training corpus.
Synchronous re-search (pause the lattice run and search now) is a Phase D option, deliberately
deferred. Routing volume is unmeasured today; the flagged-flux fraction (§6.3) is the instrument
that makes it visible. Rationale for co-equal status: 192/445 harvested events are
multi-site/non-conservative, and no confirmed evidence exists that concerted/strongly-relaxed
saddles are predictable from static atom-centered descriptors (five-pass research sweep + two
independent cross-checks, zero contradictions).

---

## 7. Component 6 — Novelty & harvest round trip

### 7.1 Ingest new pyKMC rows → classes (C3)

```
ingest(new_rows, cycle):
    for row in new_rows:
        pe = project_event(row)                             # §3 (unwrap, full context, ordered token)
        run_auto_gates(pe, row)                             # §8.2 (G1..G7); failures → audit
        C = class_id(canonical_form(pe.delta, pe.context, pe.movers, pe.saddle_raw, pe.depth_sig))   # FULL context
        bucket by row.id_saddle                             # fast screen; canonical form authoritative
        if C in catalogue:                                  # NEW INSTANCE of a known FULL-CONTEXT class
            append row.energy_barrier, row.nu0, row.dE_pair to C.{barriers,nu0_*,dE_pair_list}
            recompute k_rate_mean (rate space, sorted), Ea_rep, Ea_std, n_eff        # §6.1
            record source_cycle/row
            if outlier_member(row.energy_barrier, C):  flag_audit(C, CONTEXT_UNDERRESOLVED)   # not silently averaged
        else:                                               # NEW CLASS (a full-context environment never seen)
            create EventClass(C, pe...); audit_status = pending; enqueue_audit(C, NEW_CLASS)
        link_or_synthesize_backward(C, row)                 # §7.2
    assert class_partition refines id_saddle partition in RATE units          # §4.4 (M6)
    recompile changed/new APPROVED classes                                    # §5.1
```

New-class-vs-new-instance is exact **full-`r_ctx`** canonical-form equality (C3): a genuinely new
environment (e.g. a 2nd/3rd-shell Cr decoration) is *always* a new class and *always* audited — never
absorbed as an "instance" that poisons a mean and fakes convergence.

### 7.2 Forward/backward pairing + per-pair detailed balance (C2, C4, Sym-5, Sym-7, M5)

The reverse event's Δ is the inverse occupancy change with `before↔after` swapped and the ordered token
shared. **Detailed balance is sourced from a per-pair ΔE recovered from linked pyKMC rows, not from
class means.**

```
link_or_synthesize_backward(C, row):
    # self-reverse is a property of κ, never of pyKMC's mover hash (Sym-5):
    if ∃ g∈D₄ₕ mapping the FULL decorated stencil (Δ + context + ordered token) with before↔after swapped onto itself:
        C.backward_class = C.class_id; C.self_reverse = True; C.pair_status = self
    elif row.idx_backward present:                          # both directions harvested (LINKED pair, shared id_saddle)
        Cb = class_of(project_event(backward_row))
        assert delta(Cb) == invert(delta(C)) under some g  and  context(Cb@final)==context(C@final)
        C.backward_class = Cb.class_id; Cb.backward_class = C.class_id; C.pair_status = linked
        # per-pair ΔE from the SAME saddle: dE_pair = dE_f − dE_b = E_min2 − E_min1  (INDEPENDENT of class means)
    else:                                                   # only one direction harvested
        Cb = synthesize_reverse(C)                          # invert Δ, context = C's final decoration
        # BALANCED BY CONSTRUCTION from the forward's measured ΔE (Sym-7, M5): give the reverse a real rate
        Cb.k_rate_mean = C.k_rate_mean · (ν0_b/ν0_f) · exp(row.dE_pair / (kB·T))
        Cb.pair_status = synthesized_balanced; Cb.flag = True; enqueue_audit(Cb, PAIR_CLOSURE)
        C.backward_class = Cb.class_id
    C.dEnergy = mean(C.dE_pair_list)                        # per-pair ΔE mean — an INDEPENDENT channel (C2/C4)
```

- **Self-reverse from `κ`, not from `event_id == id_final` (Sym-5).** pyKMC's `event_id`/`id_final`
  are single-atom, mover-centred, grey-in-grey-mode graph hashes (`event_table.py:340-344`) that are
  neither necessary nor sufficient for true self-reversal; and a bare "Δ is its own inverse" test is
  context-blind (`Δ = {A:Ni→EMPTY, B:EMPTY→Ni}` inverts under the A↔B midpoint regardless of what
  decorates A vs B). The final test requires a `g∈D₄ₕ` to map the **full decorated stencil**
  (Δ + context + ordered token) with `before↔after` swapped onto itself. If the wider context is
  asymmetric, forward and backward are **kept distinct** and the reverse barrier is demanded from the
  next harvest — `dEnergy` is never forced to 0 (the draft's silent equilibrium bias).
- **Synthesized reverse is balanced, not fabricated-unbounded or missing (Sym-7, M5).** When only one
  direction is harvested, the reverse is given an *explicit, physically-bounded* rate from the
  forward's **measured per-pair ΔE** via `k_b = k_f·(ν0_b/ν0_f)·exp(ΔE/kT)`, so the pair is
  detailed-balance-consistent *by construction*. Its instances are `flag=True` (never-zero, top
  exploration priority). This removes both failure modes of the draft: the *ratchet* (reverse excluded
  from BKL → one-way mass transport across a 10⁶-step leg) and the *wrong-rate* (reverse at a fabricated
  `k_floor` → arbitrary `k_f/k_b`).
- **Detailed balance is now a REAL gate (G2), not a tautology (C2).** The draft *defined*
  `dEnergy := Eₐ_f − Eₐ_b` from two class means, so `|ln(k_f/k_b) − (ln(ν0_f/ν0_b) − dEnergy/kT)| ≡ 0`
  identically — green by construction. Here `dEnergy = ⟨dE_pair⟩` is recovered from **linked
  forward/backward rows sharing a saddle** (`dE_f − dE_b = E_min2 − E_min1`), an **independent** energy
  channel. G2 (§8.2) tests two independently-sourced quantities and can genuinely fail:
  1. the per-member spread of `dE_pair_list` must be within `db_tol` (if the forward and backward
     classes' members are *not* pairwise reverses — a fold-in artefact — the ΔE spread blows up →
     fail → audit; this is the C4 detector);
  2. the class rate ratio must match the *independently measured* `⟨dE_pair⟩` **and** pyKMC's own
     stored per-row `k`/`k_prefactor` column (`event_table.py:658-659`) within `db_tol`.
- **Enforce-per-pair is the DEFAULT (C4).** Each measured forward/backward pair is symmetrised to one
  ΔE and one `ν0_f/ν0_b` *before* it enters the class aggregate, so the class rate ratio cannot encode
  a fictitious ΔE. Because a class is single-environment (§4.4), its members *are* pairwise reverses of
  the backward class's members, so the symmetrisation is well-posed — the draft's C4 failure (means
  over *different* populations) cannot arise.

### 7.3 Reverse mapping — occupancy → atomistic config (deterministic, periodic, byte-stable; Geom-4)

```
to_atomistic(Grid) -> (config, content_hash):
    atoms = []
    for id in sorted(valid site ids):                       # FIXED enumeration order → determinism
        if occ[id] not in {EMPTY, OUTSIDE}:
            atoms.append( (occ_to_symbol(occ[id]), origin + h·ijk[id]) )   # R ≡ I: EXACT ideal position, axis-aligned
    cfg = XYZ(atoms, cell=frame_cell, pbc=(True,True,False))
    return cfg, blake2b(serialize(cfg))
```

Atoms are emitted at **ideal, axis-aligned** positions with **`R ≡ I`** (Geom-4): `origin + h·(i,j,k)`
tiles the orthorhombic PBC cell exactly, so the `x=0` face coincides with the periodic image of the
`x=Lx` face — no `(R−I)·Lx` transverse seam, no boundary defect for pyKMC to "discover" as a spurious
event, no interaction with pyKMC's negative-coordinate clamp (`system.py:194`). Because the frame is
calibrated once and snapshots are aligned into it (§2.1), `R` never enters the emitted coordinates.
Identical occupancy ⇒ byte-identical coordinates (asserted via the content hash). Empty sites emit
nothing (vacancy = absent atom). Flagged near-miss sites are written first as the priority central-atom
list. pyKMC then minimises this ideal config, runs `k = 20–1000` steps with the cumulative reference
table preloaded, and returns new rows → §7.1.

### 7.4 (reserved — reverse-map determinism folded into §2.1 + §7.3)

### 7.5 Coverage report, convergence, and the catalogue-independent probe (C5, Geom-5)

Cheap O(1)/step accumulators plus a periodic *external* check:

- **Fallback flux fraction** `R_fallback / R_total` and the fraction of *executed* steps that were
  fallback-rated.
- **Observed-but-unharvested environments** — the `flag_registry` (§6.3): distinct environments visited
  that no exact class covers, with visit counts, carried flux, and the `out_of_hull` marker (M2).
- **Never-matched candidate anchors** — any candidate anchor that matched *no* class (would have been
  the Sym-4 far-surface hole; reported as a coverage gap even though D₄ₕ now prevents the specific σ_h
  case).
- **Composition / SRO drift** — running species fractions + vacancy count + Warren–Cowley SRO from
  incrementally maintained 1st-shell pair counts (each event updates only pairs around `changed`, O(1)).
- **Stall streak** — consecutive `PROJECTION_STALLED` cycles (Geom-5); a nonzero streak is an explicit
  **non-convergence** flag.
- **Loop convergence** requires **all** of: (a) `new full-context classes per cycle → 0`; (b) fallback
  flux fraction below threshold; (c) `stall_streak == 0`; **and** (d) the **catalogue-independent
  physics probe** below agrees.

**The catalogue-independent probe (C5).** The three within-catalogue metrics are all self-referential:
if the on-lattice *rates* are wrong (which the §6 fixes prevent but cannot *prove* absent), the
10⁶-step leg visits the wrong region, pyKMC re-harvests that wrong region, the catalogue "completes"
there, and every metric reads healthy *because* the dynamics are wrong. So convergence additionally
requires an **external oracle**:

1. **Direct-trajectory spectrum check.** Periodically, from a current lattice state, run a *short
   direct pyKMC trajectory* (real off-lattice KMC, no on-lattice rates) and compare the **event-frequency
   spectrum** (which classes fire, and how often — a KL or χ² over the class-firing histogram) against
   the on-lattice engine's prediction from the same state. Convergence is declared only when the
   spectra agree within tolerance — not on `new-classes → 0` alone. A spectrum mismatch means the rates
   are steering the trajectory wrongly even though the catalogue looks complete.
2. **Forced off-distribution seeding.** Exploration is seeded not only from states the (possibly
   biased) trajectory reached but also from **planted off-distribution states** (e.g. Cr-depleted
   surface patches, deliberately roughened regions), so the harvest cannot miss the low-barrier
   dealloying channel merely because the biased trajectory never reached it.

This is the one check that catches a *shared* logic error in both the fast and slow on-lattice paths
(which I5 cannot, §5.4) and the harvest-bias basin trap (C5).

---

## 8. Component 7 — Provenance & curation hooks

### 8.1 Per-class provenance

Carried on every `EventClass` (§1.3): `source_cycles`, `source_rows`, `barriers[]`,
`dE_pair_list[]`, `nu0_f_list/nu0_b_list`, `k_rate_mean`, `Ea_rep`, `Ea_std` (None for n<3),
`n_eff`, `gate_log` (per-instance G1–G7), `model_version`, `first_seen_cycle`, `audit_status`,
`backward_class`, `pair_status`, `dEnergy`, `delta_atoms`, `family_id`, `fallback_stats`. Every rate
is traceable to the off-lattice rows that produced it, and every ΔE to a linked row pair.

### 8.2 Automated gates (decision 5), defined precisely

Auto-admitted iff **all** gates pass; any failure, and every first-instance-of-new-class, routes to the
audit queue.

| Gate | Check | Threshold |
|---|---|---|
| **G1 barrier bounds** | `emin_event ≤ Ea_fwd ≤ emax_event` and `Ea_bwd ≥ emin_event` | reuse pyKMC's exact fields |
| **G2 detailed balance (REAL, C2)** | per-member `dE_pair` spread `< db_tol`; **and** `\|ln(k_f/k_b) − (ln(ν0_f/ν0_b) − ⟨dE_pair⟩/kT)\| < db_tol` using the **independent** ⟨dE_pair⟩ from linked rows; **and** agreement with pyKMC's stored per-row `k` | `db_tol = 0.05` (ln-rate units) |
| **G3 snap residual** | every cluster atom (initial and final) snaps `< snap_tol`; movers strictly `< snap_tol`; saddle exempt (off-lattice) | `snap_tol = 0.9 Å` |
| **G4 projection round-trip** | re-expand projected event to ideal positions → re-project → identical `class_id`; **and** `move_atom_idx ∈ detected_movers` | exact id; boolean |
| **G5 conservation (v1)** | before/after species multiset equal (atom-conserving); **and** projection-time `I4` held | multiset equality |
| **G6 context completeness** | cluster covers the full `r_ctx` footprint of every moved site | else admit + `truncated` + flag larger-`rcut` re-harvest |
| **G7 cluster integrity (Geom-1)** | min-image-unwrapped cluster diameter `< 2·rcut` (no boundary straddle); no collision at projection | else audit(STRADDLING_CLUSTER / COLLISION) |

G2 is now a genuine, failable detailed-balance test (§7.2), not the draft's algebraic tautology. G3
keeps intrinsically off-lattice events (interstitials, reconstructions) out of the catalogue — audited,
not force-fitted. G4 catches mis-projection and the concerted-mover mislabel. G5 is the v1 guard that a
non-conservative event surfaces at audit (and is the switch flipped to *enable* dissolution, §9). G6
closes the nominal-mover-cluster-edge truncation hazard. **G7** is the new boundary-straddle/collision
guard (Geom-1, Geom-8).

### 8.3 Audit queue and determinism

- **Queue interface** = a directory of records (file-based handoffs), one JSON/parquet per item:
  `{rows, projected_pattern, canonical_form, ordered_saddle_token, gate_results,
  reason ∈ {NEW_CLASS, GATE_FAIL, OUTLIER_BARRIER, UNMAPPABLE, COLLISION, STRADDLING_CLUSTER,
  PAIR_CLOSURE, MOVER_MISMATCH, TRUNCATED, CONTEXT_UNDERRESOLVED, PROJECTION_STALLED, FRAME_DRIFT},
  representative_atomistic_snippet (ideal-site xyz), suggested_action}`. A human (or later
  auto-approver) writes `approve/reject/merge/split/grow_r_ctx` into a **decision log**; approved items
  compile on the next `recompile`. `QUARANTINED` classes are excluded from execution but still count in
  the coverage report (never silently zero — they become discovery targets).
- **Determinism / reproducibility.** (a) the frame is **calibrated once**, seeded, hashed, persisted,
  and only bounded rigid drift is tracked deterministically per cycle (Geom-10); (b) the reverse map is
  deterministic by fixed site enumeration + ideal `R ≡ I` positions + content hash (Geom-4); (c)
  canonicalisation is deterministic (fixed anchor×group order, total serialization order); (d) rate
  aggregation sums a sorted member list (M4); (e) there are **no** automatic running-mean split/merge
  decisions to replay (SPLIT_CHECK removed); the class partition is a pure function of the harvested
  row set; (f) the audit **decision log** and every within-leg fallback **`model_version`** (M3) are
  replayed; (g) BKL RNG is seeded and logged. An entire alternation run is reproducible from
  `{initial config, seeds, decision log, model versions, frame content_hash}`.

---

## 9. Worked examples

### 9.1 Vacancy hop — bulk Ni (projected → classified → matched → executed)

**Off-lattice row.** ~40-atom cluster; mover adjacent to an absent atom (the vacancy); `final` shifts
it into the gap; `energy_barrier ≈ 0.65 eV`; `nu0_f`, `nu0_b`, and the linked backward row (shared
`id_saddle`) present; `saddle_positions` over the ⟨110⟩ bridge.

**Project (§3).** **Unwrap the cluster about the mover** (Geom-1) — if the vacancy sat near an in-plane
face, its far-side ⟨110⟩ neighbours are brought back to 2.49 Å, so no phantom surface is inferred.
Diameter `< 2·rcut` (G7 ✓). Fit local frame. Snap: mover initial site `A=(0,0,0)`; the 12 NN
enumerated; `B=(1,1,0)` is `EMPTY`. Site-change: `A≠B` ⇒ `movers={mover}` (`move_atom_idx ∈ movers` ✓).

```
delta = [ ((0,0,0): Ni→EMPTY), ((1,1,0): EMPTY→Ni) ]     # anchor set = {A,B}; delta_atoms = 0
context = full r_ctx (1st+2nd shells) around {A,B}, all Ni ⇒ no coordination deficit
depth_sig = BULK_OR_DEEPER (cluster fully coordinated to rcut)          # operational (Geom-3)
saddle_token = [ PathToken(start_rank=0, kind=BRIDGE, coord_sig=(…)) ]  # categorical (Geom-7)
```

**Classify (§4).** Canonicalise `(Δ + full context + ordered token + depth_sig)` under **D₄ₕ(16)**,
minimised over **anchor∈{A,B} × g∈D₄ₕ** (Sym-2). In a slab, the in-plane and inter-layer ⟨110⟩ hops are
*distinct orbits* under D₄ₕ; this bulk-interior hop is (say) an in-plane one → one class, "bulk Ni ⟨110⟩
in-plane vacancy hop, over-bridge, BULK_OR_DEEPER." `orientation_count = |D₄ₕ|/|Stab|`. `class_id =
blake2b(canonical_form)`; the full tuple is authoritative. The realizability cross-check (§4.7) maps
each snapped `sym_matrix` op onto a generated oriented pattern (not a count equality).

**Compile (§5.1).** Oriented patterns re-anchored at the rarest predicate = the `EMPTY` target, each
carrying **core + full context predicates** (all-Ni shells) and the token, `rate = ν0_f·⟨exp(−0.65/kT)⟩`
(rate-space; here n small so ≈ single value), `family_id = "1NN in-plane vacancy hop ⊕ BULK_OR_DEEPER."`

**Match (§5.3).** One vacancy ⇒ only that one `EMPTY` anchor (on `species_sites[EMPTY]`,
`is_vacuum=False`) is tested. Its ⟨110⟩ Ni neighbours each satisfy one oriented pattern whose full
context (all-Ni) also holds ⇒ enabled instances, **deduped by canonical touched-site set** so a
symmetric configuration is not multiply counted (Sym-3). One class pool; `group_fenwick` count and rate;
`supported_by` indexes each instance.

**Execute (§5.4).** BKL selects an instance; apply Δ; `species_sites` O(1) swap-remove/append;
`is_vacuum`/`depth` unchanged (bulk). `changed`=2 sites; `affected = rctx_ball`; remove old instances
via `supported_by`, re-enumerate with dedup. `R_total` unchanged (homogeneous bulk). `Δt = −ln(u)/R_total`.
The reverse (measured, linked pair) is now enumerable in the flipped state at a balanced rate; G2 holds
against the independent `⟨dE_pair⟩` and pyKMC's stored `k`. Cost **O(1) in N**. Every 1e4 steps I5
rebuilds and asserts set-equality.

### 9.2 Three-site concerted event — NiCr surface (projected → classified → matched → executed)

A vacancy-mediated correlated exchange at the (100) surface: Ni `A→B`, Cr `B→C`, vacancy `C→A` — a
chiral 3-site cycle. `move_atom_idx` names **only the Ni**; `final − initial` shows **two** atoms
displaced.

**Off-lattice row.** Cluster around the Ni; free surface on `+z`. `energy_barrier ≈ 0.45 eV`; saddle
bulges over two bridges. Suppose only the forward is harvested this leg.

**Project (§3).** **Unwrap about the mover** (Geom-1); the surface normal is read from the **decorated
EMPTY hemisphere within `r_ctx`** (a contiguous empty region toward `+z`), *not* from missing neighbours
— so a near-boundary version is not mis-typed as surface. Site-change finds **both** movers
(`{Ni:A→B, Cr:B→C}`; `move_atom_idx=Ni ∈ movers` ✓):

```
delta = [ (A: Ni→EMPTY), (B: Cr→Ni), (C: EMPTY→Cr) ]     # anchor set = {A,B,C}; delta_atoms = 0
context = full r_ctx around {A,B,C} incl. the EMPTY vacuum sites above (coordination deficit → +z)
depth_sig = SURFACE(coord 8)                             # operational: r_ctx reaches vacuum hemisphere (Geom-3)
saddle_token = ordered [ (start_rank(Ni), BRIDGE, …), (start_rank(Cr), BRIDGE, …) ]   # mover-bound (Sym-6)
```

G6 checks the Cr (near the cluster edge) has full `r_ctx` coverage; if truncated, admit `truncated` and
flag a larger-`rcut` re-harvest.

**Classify (§4).** Canonicalise under **D₄ₕ(16)**, minimised over anchor∈{A,B,C} × g (Sym-2). The
vacuum `EMPTY`s reduce the *stabiliser* to the surface subgroup automatically, but **D₄ₕ still generates
the σ_h image**, so the identical event at the **bottom** surface will match (Sym-4). `depth_sig =
SURFACE(8)` keeps this distinct from any subsurface/bulk stencil (Geom-3). The 3-site cycle is chiral
and the Ni/Cr decoration breaks the mirrors, so `orientation_count = 8`. The reverse (Cr `C→B`, Ni
`B→A`, vacancy `A→C`) is a distinct `backward_class`; since only the forward was harvested, the reverse
is **synthesized_balanced**: `k_b = k_f·(ν0_b/ν0_f)·exp(ΔE/kT)` from the forward's measured per-pair ΔE
(Sym-7/M5) — a real, balanced reverse rate, flagged for harvest, **not** a ratchet and **not** a
fabricated `k_floor`.

**Compile (§5.1).** ≤8 oriented patterns (both surfaces via σ_h), re-anchored at the rarest predicate =
the surface `EMPTY` at `C`, carrying core + full context (the specific Ni–Cr–vacancy surface decoration),
`rate = ν0_f·⟨exp(−0.45/kT)⟩`, `family_id = "3-site ring ⊕ SURFACE(8)."`

**Match (§5.3).** For each surface `EMPTY` anchor at the right depth, the 3-offset core screens, then
the **full context** is verified — matching only where the exact Ni–Cr–vacancy surface motif exists
(Sym-1: a Ni–Ni-context sibling would *not* match here). Instances are deduped by canonical touched set
(Sym-3). If instead a Ni–Ni ring had been harvested and this is Ni–Cr, the full context does **not**
match any approved class ⇒ **near-miss**: the `"3-site ring ⊕ SURFACE(8)"` family regressor returns
`(Ea_hat, σ)` from φ; if the Cr-bond φ is **out-of-hull**, it is treated as **hard novelty** — high
exploration-floor rate, `high_uncertainty`, top exploration priority (M2) — never a confidently-wrong
Ni-like rate. Flagged, never zero.

**Execute (§5.4).** BKL selects; apply the 3-site Δ **atomically**; update `species_sites`,
`is_vacuum`, `depth`, and SRO/composition accumulators (a Cr moved outward — the dealloying statistic).
`changed={A,B,C}`; `affected = ∪ rctx_ball`; remove/re-enumerate with dedup. The balanced reverse is
enumerable in the flipped state, so transport is not ratcheted. Cost **O(1)**. This exercises every hard
requirement: multi-site first-class; don't-trust-`move_atom_idx`; species resolution; both-surface
coverage (σ_h); mover-bound ordered saddle token; full-context matching; out-of-hull hard-novelty
fallback; balanced synthesized reverse; and a dealloying statistic — all on O(1) incremental machinery.

---

## 10. Consolidated complexity analysis (re-costed for full-context matching)

Symbols: `N` active sites (1e3–1e6); `C` classes; `|G| = 16` (D₄ₕ); `P` oriented patterns
(`≈ C·|G|/stabiliser`, deduped); `κ` patterns tested per anchor after screening (1–20); `σ_core` core
size (4–10); **`σ_ctx` full-context size (30–60)** — the matched stencil is now `core ∪ context`
(Sym-1); `A` candidate anchors (`≈ #defect_sites` dilute); `D` dirty anchors per step (fixed ball,
N-independent, ≈30–80); `d` feature dim (30–60).

| Phase | Cost | Notes |
|---|---|---|
| Build grid + `nbr12/nbr2/depth/is_vacuum` + `species_sites` | `O(N)` integer + 1 flood-fill | once per cycle; no geometry; tiled SoA |
| Calibrate frame (once) / register cycle | `O(N)` snap + `O(N log N)` KDE once; O(N) align per cycle | seeded once (Geom-10) |
| Compile catalogue | `O(C·\|G\|·σ_ctx)` | seconds; after each harvest |
| Initial match (rate list) | `O(A·κ·(σ_core + hit·σ_ctx))` ≤ `O(N·κ·σ_ctx)` | screen on core; verify full context on a screen hit |
| **Per KMC step** | **`O(D·κ·σ_ctx) + O(log C)`** | **N-independent**; constant ~3–6× the draft's core-only (honest cost of Sym-1 fix) |
| Instance dedup | `O(σ_core)` per candidate (canonical touched set) | Sym-3; amortised into match |
| I5 full-rebuild audit | `O(A·κ·σ_ctx)` every 1e4 steps | incremental-correctness oracle |
| Direct-trajectory probe (C5) | one short pyKMC run every `probe_interval` cycles | amortised; the physics oracle |
| Coverage accumulate / step | `O(#changed)` | running sums + SRO deltas + drift metric (M3) |
| Fallback predict (per new sig) | `O(d)` + convex-hull/leverage test | memoised per `cell_key` (M2) |
| Reverse-map emit | `O(N_occ)` | once per handoff |
| Memory | `O(N)` grid + `O(#instances)` | `nn12` table ≤1e7 sites, arithmetic above |

**At scale.** Per-step cost is independent of `N`. The Sym-1 fix (verify full context, not core only)
raises the per-step **constant** by ~3–6× (verifying ~40 sites instead of ~8 on a screen hit) but does
not change the N-independence — 1e6 steps on 1e3 sites still run in minutes, and 1e5–1e6 sites on a
node are limited by memory and the once-per-cycle `O(N)` build. Honestly-disclosed degradations: the
equiatomic direct-exchange class (`O(N/2)` via spatial-index, W9) and the porous late-dealloying limit
(`|active| → O(N)`), both addressed by domain-decomposed parallel KMC as an extension. **Full-context
identity increases catalogue size** in concentrated alloys (more distinct decorations) — the honest
lower bound set by the physical resolution pyKMC itself uses; the fallback regressor + exploration
prioritisation carry the tail (W2/W7).

---

## 11. Failure-mode table

| Failure | Cause | Detection | Response |
|---|---|---|---|
| **Boundary-straddling cluster** | raw wrapped subset coords near an in-plane face | **G7** unwrapped diameter `< 2·rcut` | min-image-unwrap about mover first; else audit(STRADDLING) |
| **Phantom surface from wrapped neighbours** | surface normal from "missing" atoms | normal from decorated EMPTY hemisphere, not missing atoms | regime from real under-coordination only (Geom-1) |
| **Nondeterministic snap** | parity-Voronoi face tiebreak on jitter | `d2 − d1 < snap_hysteresis` | hysteresis: keep prev assignment, else audit (Geom-2) |
| **Interstitial/dumbbell drops atom** | two atoms → one site | **G7**/collision list; **I4** conservation | any collision ⇒ hand back to pyKMC (Geom-8) |
| Off-lattice atom | interstitial / reconstruction / mid-transition | snap residual > `snap_tol` (G3) | flag unmappable; structural ⇒ hand to pyKMC (Geom-5) |
| Frame drift / tilt | thermal expansion, translation, shear | bounded drift assert; `‖R−I‖` at calibration | calibrate once + deterministic drift; else audit (Geom-10) |
| **Non-periodic reverse-map seam** | emitting with `R≠I` | tiling assert (`x=0` vs `x=Lx` image) | emit with `R≡I` on integer lattice (Geom-4) |
| **Loop livelock on roughening** | reverse-map stale grid | consecutive `PROJECTION_STALLED` | hand pyKMC the rough snapshot; stall≠converged (Geom-5) |
| **Porous/overhang mis-labelled vacancy** | column-envelope z(x,y) | flood-fill `is_vacuum` component | topology-correct vacancy test (Geom-6) |
| Concerted mover mislabel | `move_atom_idx` names one of several | site-change vs `move_atom_idx` (G4) | use detected set; `mover0 ∉ movers` ⇒ audit |
| Truncated second-mover context | cluster centred on nominal mover | G6 context-completeness | admit `truncated`; flag larger-`rcut` re-harvest |
| **Split-sibling double-match** | matching coarser than identity | full-context match predicate (Sym-1) | each site matches ≤1 class; I6 guard |
| **Symmetric event fragments across orientations** | anchor tie-break frame-dependent | min over anchor×group (Sym-2) | complete orbit invariant; one class_id |
| **Symmetric multi-anchor over-count** | k equivalent anchors | canonical `instance_key` dedup (Sym-3) | admit each physical move once; I6 |
| **Opposite surface never matches** | C₄ᵥ omits σ_h | compile under D₄ₕ (contains σ_h) | both surfaces generated (Sym-4) |
| **Fictitious self-reverse (ΔE→0)** | trusting `event_id==id_final` | self-reverse from full κ (Sym-5) | keep fwd/bwd distinct if context asymmetric |
| **Saddle-token flicker / merge** | round() of continuous offset | categorical kind + hysteresis (Geom-7/M1) | topological class, frame-stable |
| **Token role undefined / unordered** | multi-mover concerted | ordered, mover-bound token (Sym-6) | start_rank binds token↔mover |
| **Ratchet / wrong-rate reverse** | synthesized reverse unbounded/missing | balanced from per-pair ΔE (Sym-7/M5) | `k_b=k_f(ν0_b/ν0_f)exp(ΔE/kT)`, flagged |
| **Rate = exp(−mean barrier)** | Jensen; trimmed tail | rate-space aggregate (C1) | `⟨exp(−Eₐ/kT)⟩`; drop trimmed_mean for rate |
| **G2 tautology** | dEnergy defined from same means | independent ⟨dE_pair⟩ + pyKMC k (C2) | G2 can genuinely fail |
| **New event absorbed as instance** | identity coarser than physics | full-`r_ctx` identity (C3) | always a new class; audited |
| **Fictitious class-mean ΔE** | fwd/bwd means over different pops | per-pair balance default (C4) | symmetrise pair before averaging |
| **Harvest-bias basin trap** | self-referential convergence | direct-trajectory spectrum probe (C5) | converge only if external spectra agree |
| Fallback extrapolation into unseen comp. | zero-variance species column | convex-hull/leverage out-of-hull (M2) | hard novelty, high floor, top priority |
| Frozen-model staleness at front | refit only at cycle start | within-leg drift-triggered refit (M3) | new model_version logged; replayable |
| Order-dependent catalogue | running-mean SPLIT_CHECK | SPLIT_CHECK removed (M4) | hash identity + sorted rate-space sum |
| Refines-`event_id` frame-inconsistent | live fwd vs relaxed bwd/saddle | refine vs shared `id_saddle`, rate units (M6) | single-frame validator; k_BT guarantee |
| Rate-list desync after event | missed dirty site | **I5** full-rebuild set-equality | hard fail + dump; rebuild |
| Single-sample overconfidence | `Ea_std=0` for n=1 | `Ea_std=None` for n<3; `n_eff` weight (m1) | shrinkage std; weight by effective count |
| Enabled move with no rate | novel environment | never-zero guard (§6.3) | `max(regression, k_floor)` + top priority |
| Non-conservative event in v1 | stray dealloying-type event | G5 conservation | reject → audit (enable for dissolution, §9) |
| Catalogue/coloring-mode mix | grey + full rows | mode is part of the key | distinct classes |
| Low-barrier flicker burns steps | vacancy rattling | step-rate vs clock monitor | disclosed W8; super-basin extension |

---

## 12. Test plan

**Unit.**
- *Site model:* even-parity NN enumeration (12; 2.489 Å), 2nd/3rd shells; (100) layering (4 in-layer +
  8 cross-layer bulk; 8 at surface); `depth`/`is_vacuum` **flood-fill** on a slab with a planted
  overhang and buried pore → correct vacancy/vacuum labels (Geom-6); in-plane PBC wrap; I1, I2, I3.
- *Projection determinism (Geom-2):* perturb a slab by `N(0, 0.05 Å)` **100×** and assert the occupancy
  grid is **invariant** (hysteresis); a planted parity-Voronoi-face atom routes to audit, not a
  coin-flip snap.
- *Projection conservation (Geom-8):* planted split-interstitial ⇒ collision ⇒ hand-back, **not**
  accept; `I4` fires if an atom would be dropped.
- *Boundary (Geom-1):* an event with its mover 1.5 Å from an in-plane face → min-image-unwrap restores
  2.49 Å neighbours; regime = BULK (not surface); G7 passes; the same event without unwrap would fail
  (regression guard).
- *Frame (Geom-4, Geom-10):* calibrate once, seeded; re-run yields **byte-identical** frame; reverse
  map with `R≡I` tiles the orthorhombic cell (assert `x=0` face == image of `x=Lx`); a `‖R−I‖ > rot_tol`
  slab aborts→audit.
- *Canonicalization (Sym-2, Sym-4):* bulk in-plane vs inter-layer ⟨110⟩ hop → **distinct D₄ₕ classes**;
  a symmetric divacancy concerted event harvested in **two orientations** → **one** `class_id` (min over
  anchor×group); a top-surface event's **σ_h image matches at the bottom surface**; `depth_sig` splits
  top/subsurface/bulk with identical stencils (Geom-3); species decoration distinguishes Ni-hop-near-Cr
  from pure-Ni; property test `canon(g·e)==canon(e)` over random `g∈D₄ₕ` **and translations and anchor
  relabelings**; two genuinely different decorated events → different keys.
- *Saddle token (Sym-6, Geom-7, M1):* over-bridge vs through-hollow → distinct `kind`; a 2-Ni-mover
  concerted event's two chiral variants stay **distinct** (ordered, mover-bound); token is **stable**
  across 100 re-relaxations of the same event (no flicker).
- *Matching (Sym-1, Sym-3):* two split-sibling classes (differ only in 2nd shell) → a site matches
  **exactly one**; a symmetric multi-anchor event → **exactly one** deduped instance; I6 holds.
- *Rate (C1, m1):* `k_rate_mean = ⟨exp(−Eₐ/kT)⟩` matches a brute-force mixture rate; `exp(−mean)` is
  shown to differ by the predicted Jensen factor; `Ea_std=None` for n<3; `n_eff` weighting.
- *Compile:* `orientation_count == |D₄ₕ|/|stabiliser|` by brute force.
- *`sym_perm` cross-check (§4.7):* each `sym_matrix` op snaps to a lattice symmetry realizing a
  generated oriented pattern; count-equality does **not** hold in the vacancy-reduced case.

**Round-trip.**
- Project → reverse-map (`R≡I`) → re-project → identical occupancy; byte-stable content hash.
- pyKMC row → project → canonical class → instance → reverse Δ → recovers the row's site changes; G4.
- Forward/backward: `Δ_bwd == invert(Δ_fwd)` under a `g∈D₄ₕ`; **self-reverse only when the full
  decorated κ is symmetric** (Sym-5) — a context-asymmetric hop is **not** collapsed and does **not** get
  `ΔE=0`; G2 passes on a constructed linked pair (with the correct `ν0_f/ν0_b` and independent ⟨dE_pair⟩),
  **fails** on a fold-in of unpaired members (C4 detector); a one-sided harvest yields a
  **synthesized_balanced** reverse whose `k_b/k_f` satisfies detailed balance (Sym-7/M5).

**Statistical / validation.**
- *Single bulk vacancy in Ni:* on-lattice tracer diffusivity `D` vs the analytic correlated-vacancy
  value and vs a direct pyKMC run — agree within Monte-Carlo error.
- *Detailed balance (real G2):* small system with a known `dEnergy` model to equilibrium —
  occupancy/composition matches Boltzmann; per-pair flux balance; **inject a fold-in of unpaired
  fwd/bwd members and confirm G2 FAILS** (proving it is not a tautology, C2).
- *Convergence honesty (C5):* run to `new-classes→0`, then the **direct-trajectory spectrum probe**;
  construct a case where rates are deliberately biased and confirm the probe flags a spectrum mismatch
  even though `new-classes→0` (harvest-bias detector); forced off-distribution seeding surfaces the
  planted Cr-stripping channel.
- *Fallback extrapolation (M2):* an out-of-hull Cr composition is flagged hard-novelty (high floor),
  **not** rated Ni-like; leverage-growing σ ranks it top.
- *Refit staleness (M3):* a drifting leg triggers a within-leg refit; the late-leg config is rated by a
  fresh model; replay reproduces the run from logged model versions.
- *Reproducibility (M4):* re-run the same campaign with rows/cycles in a **different order** → identical
  catalogue and rates (hash identity + sorted rate-space aggregation).
- *Incremental correctness (I5):* incremental `R_total`/counts vs periodic full rebuild over 1e5 steps —
  zero drift.
- *Scaling:* per-step wall-time flat across `N ∈ {1e3,1e4,1e5,1e6}`; table-vs-arithmetic neighbour
  crossover measured; I5 green over a long run.
- *Loop closure:* seed on-lattice from a pyKMC snapshot → run → reverse-map → pyKMC leg → confirm the
  **four-part convergence** (§7.5) on Ni(100) single-vacancy, then NiCr(100).

---

## 13. Self-declared weaknesses

- **W1 — Rigid-lattice assumption.** Reconstructions, large relaxations, and interstitial/off-lattice
  pathways cannot be represented; they are detected (G3, G7, collision) and **handed back to pyKMC**
  (Geom-5, Geom-8), so the loop degrades to pure off-lattice in un-projectable regions rather than
  freezing — but acceleration is capped exactly in the roughening regime that may matter most.
- **W2 — Context radius is bounded, not solved.** `r_ctx ≥ rcut` full-context identity removes the
  fold-in mixture, but barriers still depend on beyond-`r_ctx` strain/elastic fields a finite stencil
  cannot capture; the residual appears as bounded within-class spread and as fallback error. Subsurface
  resolution is explicitly capped at `d_max` (`BULK_OR_DEEPER`, Geom-3).
- **W3 — Fallback quality is descriptor-bound.** Bond-count/GCN/SRO features may miss the true
  barrier-determining physics for concerted or step/kink events; out-of-hull environments are treated as
  hard novelty (high floor + top priority, M2), so they are *discovered* rather than confidently
  mis-rated, but flux allocation between harvests can still be off in the interior of the hull.
- **W4 — D₄ₕ over-splits the deep-bulk interior.** Using the honest slab group D₄ₕ everywhere keeps
  in-plane and inter-layer ⟨110⟩ hops distinct even deep inside, where the real symmetry approaches O_h;
  this is a ≤2× convergence cost on deep-bulk hop classes, never a wrong merge, and never the σ_h
  top/bottom failure a C₄ᵥ surface group would cause (Sym-4). A rigorous fix computes the actual
  per-event site symmetry; deferred.
- **W5 — Detailed balance is per-pair-enforced but rests on single-environment classes.** With
  full-context identity, a class's members *are* pairwise reverses of the backward class, so per-pair
  symmetrisation (default) is well-posed and G2 is a real test. If a class cannot be shown to have
  paired members (G2 ΔE-spread failure), reversibility is **not claimed** — it is flagged and the
  environment is prioritised for harvest, rather than silently averaged.
- **W6 — Truncated collective events.** A genuinely collective event whose movers exceed the stored
  `rcut` cluster projects to a partial Δ; G6 flags incomplete `r_ctx` coverage for re-harvest, but a
  borderline case could yield a partial class before the larger-`rcut` leg runs.
- **W7 — Catalogue richness cost.** Full-context identity + full-colour ternary multiplies distinct
  classes/patterns; runtime stays O(1)/step via screening, but compile time, memory, and catalogue size
  grow with the number of *physically distinct visited environments* — fine at 1e2–1e3 classes, needs
  attention (and the fallback tail) beyond.
- **W8 — No super-basin acceleration on the lattice.** Flickering low-barrier pairs burn steps; an
  absorbing-Markov super-event layer over the grouped BKL is the natural next addition, out of v1 scope.
- **W9 — Equiatomic anchor degradation.** A ~50/50 direct-exchange class has no dilute anchor; the
  spatial-index fallback keeps it correct but not O(1). Acceptable for the dilute-vacancy early campaign;
  the porous end-state pushes active sites toward O(N) and needs the parallel-KMC extension.
- **W10 — Fallback micro-group proliferation.** Group-BKL assumes intra-class rate homogeneity; many
  coexisting continuous fallback rates spawn micro-groups. Rate binning bounds this at a small
  rate-quantisation cost.
- **W11 — `sym_perm` is a soft cross-check only.** It is a grey orbit under the reduced cluster
  symmetry (§4.7), so it validates realizability, not orientation count; registration errors that
  preserve realizability slip past it (caught instead by G4/G7).
- **W12 — The physics probe costs a direct pyKMC run.** The catalogue-independent convergence check
  (§7.5) periodically runs a short off-lattice trajectory; this is the price of not trusting
  self-referential coverage metrics (C5). Its cadence (`probe_interval`) is a tunable cost/confidence
  knob; too-rare a probe re-opens the harvest-bias risk.

---

## 14. Fit to the harvest pipeline and extensibility

- **Catalogue-first, file-based loop (decision 1).** Every artifact is a file: occupancy grid, compiled
  catalogue (Parquet of `EventClass` rows keyed by `class_id` + per-`family_id` regressor blobs, all
  version-stamped), audit directory + decision log + **model-version log** (M3), coverage report,
  projection report, priority exploration list. Each leg is scriptable; a closed-loop driver alternates
  the two engines and watches the **four-part convergence** (§7.5). No redesign to close the loop.
- **Reads/writes the real contract (decision 3).** Consumes the exact `event_table.py` columns
  (`initial/saddle/final_positions`, `initial_types`, `energy_barrier`, `k`, `k_prefactor`, `nu0`,
  `move_atom_idx`, `sym_matrix/sym_perm` for §4.7, `idx_backward`, `event_id/id_saddle/id_final`,
  `dra`); **min-image-unwraps every cluster** (Geom-1); reuses pyKMC thresholds (`emin_event`,
  `emax_event`, `backward_emin_event`, `energy_asymmetry`, `matching_score_thr`, `rcut`); recovers a
  **per-pair ΔE** from linked forward/backward rows (shared `id_saddle`; §7.2) and cross-checks against
  pyKMC's stored per-row `k` (G2); asserts the orthorhombic `cKDTree(boxsize=diag(cell))` constraint;
  writes an ASE-readable ideal-site (`R≡I`) config + the cumulative `reference_table.pickle` into
  `config.control.reference_table` + `initial_config`. New deps are modest: a fixed 16-element D₄ₕ
  integer group, a scipy KD-tree (already a dep), ridge/GP (numpy/optional sklearn) — **no nauty on the
  lattice side**.
- **Rate model (decision 4).** Exact-class rate-space lookup + per-`family_id` BEP/GCN fallback for the
  *unseen tail only* + out-of-hull hard-novelty + flag; flagged/out-of-hull environments become the next
  leg's exploration targets; nothing is silently zero.
- **Curation (decision 5).** Precise auto-gates G1–G7 (G2 a real detailed-balance test, G7 the
  boundary/collision guard) admit clean events; failures and new-class first instances go to audit;
  provenance is per-class and replayable; **no automatic order-dependent split/merge decisions exist**
  (M4).
- **Switching + coverage (decision 6).** Fixed tunable `n` steps (adaptively shortened on fast drift,
  M3), then a cheap coverage report + the periodic direct-trajectory spectrum probe (C5), all
  accumulated O(1)/step except the probe.
- **Occupancy-count-changing events / dealloying (decision 2).** The `DeltaSite{before,after}` +
  `delta_atoms` schema already admits `X → EMPTY`; matching, canonicalisation, dedup, and BKL are
  unchanged. Key enabling insight: **sites never re-index** — a removed atom is just an `EMPTY` site
  (unlike pyKMC's per-atom deletion) — so enabling dissolution = drop the G5 conservation gate for
  flagged classes + let `species_sites[EMPTY]` grow. The **Erlebacher bond-counting dissolution rate**
  `k = ν_d·exp((φ − n·E_b)/kBT)` drops in as a coordination-dependent class (φ from the same feature
  map, §6.2) competing in the same grouped BKL vector — no re-harvest, no schema break. The topological
  `is_vacuum` flood-fill (Geom-6) means the receding, porous surface is handled correctly from day one.
- **Ternary and beyond.** The occupancy alphabet grows; predicates, canonical form, `φ`, per-family
  regressors, and SRO counters are all parameterised by the species set (a `uint8` non-event).
- **Cluster promotion.** The same engine runs unchanged from a 1e2–1e3-atom workstation slab to a
  1e5–1e6-site production slab: per-step cost is N-independent (constant re-costed in §10); only the
  one-time build and memory scale (tiled SoA + arithmetic-neighbour scale switch); late-stage porous
  regimes take the domain-decomposed parallel-KMC extension.

---

## Appendix A — Red-team changelog

Each finding from the three reports (consolidated list), its severity, and where/how it is resolved.
"Amended" = the design was changed; "Rejected" = kept with technical justification.

### Geometry & projection (attack-geometry.md)

| # | Finding | Sev | Resolution |
|---|---|---|---|
| G-1 | Boundary-straddling clusters corrupt event frame + surface-normal inference | critical | **Amended.** §3.1: min-image-unwrap every stored cluster about its `move_atom_idx` atom using the event's own cell *before* `fit_local_fcc`; **gate G7** asserts unwrapped diameter `< 2·rcut`. §3.1/§4.1: surface normal derived from the **decorated EMPTY hemisphere within `r_ctx`**, never from "missing" neighbours, so a boundary wrap can't fake a surface. |
| G-2 | Ambiguous parity-Voronoi snap → nondeterministic occupancy → phantom vacancies/hops | critical | **Amended.** §2.2: `snap_hysteresis ≈ 0.3 Å` band — an atom whose two nearest sites are within the band inherits its previous-cycle assignment or routes to audit; never a thermal-scale coin-flip. §12 adds the 100× jitter-invariance determinism test. |
| G-3 | `depth_sig` uncomputable at ingest from a standalone cluster; aliases at ≈rcut | critical | **Amended.** §4.1: `depth_sig` redefined **operationally from the cluster** (min layers to nearest EMPTY-with-occupied-neighbour inside it), identically at ingest and runtime; capped at `d_max` with an explicit `BULK_OR_DEEPER` bucket (the deep merge is accepted, not faked); `r_ctx ≥ (d_surf+1)·(a/2)` guarantees the surface band is reached. |
| G-4 | Reverse map with `R≠I` emits a non-periodic lattice → boundary seam | major | **Amended.** §2.1 aligns each snapshot into the frame axes (absorbing tilt) so the engine works with `R≡I`; §7.3 emits `origin + h·(i,j,k)` (`R≡I`), which tiles the orthorhombic cell exactly; `‖R_campaign−I‖ < rot_tol` asserted at calibration (else audit). |
| G-5 | Fall-back-to-stale-snapshot livelocks the loop in the roughening regime | major | **Amended.** §2.3/§7.5: un-projectable snapshots are marked `PROJECTION_STALLED` and the **rough snapshot itself is handed back to pyKMC** (degrade to pure off-lattice); a stall streak is a **distinct non-convergence signal** — the loop can never read "converged" while stalled. |
| G-6 | Column-envelope vacancy/vacuum test wrong on porous/overhang geometry | major | **Amended.** §1.3/§2.2: replaced the column envelope with an O(N) **flood-fill of the connected vacuum component** (`is_vacuum`); an EMPTY site is a vacancy iff not in the vacuum component and has ≥1 occupied neighbour — topology-correct for pores/overhangs/voids. |
| G-7 | Saddle-token `round()` fragile to frame error/off-lattice magnitude | major | **Amended.** §3.3/§4.3: token is now a **categorical topological class** (BRIDGE/HOLLOW/TOP by counting coordinating atoms) computed in the **canonical class frame** with a hysteresis band, not a `round()` of a continuous offset in the noisy `frame_e`; real-valued offset kept in provenance only. |
| G-8 | Isolated interstitial/dumbbell silently drops an atom and is accepted | major | **Amended.** §2.2/§2.3: **any collision hands the snapshot back to pyKMC** regardless of `n_soft`; **I4 projection-time conservation** (`n_occupied == n_atoms − n_unmappable`) is checked at the projection step; gate G7 covers it. |
| G-9 | `layer_z` detected but never used; KDE smears on thin/rough slabs | minor | **Amended.** §2.2: the z-residual is scored against the **detected `layer_z[k]`** (layer-aware snap), so a contracted top layer maps 1:1; §2.1 guards `kde_peaks` with a min-atoms-per-peak check → audit when peaks are not separable. |
| G-10 | Reverse-map determinism undercut by per-cycle unseeded re-registration | minor | **Amended.** §2.1: the frame is **calibrated once** at campaign start (seeded RANSAC/Nelder–Mead, seeds recorded, hashed, persisted); later cycles only track bounded rigid drift deterministically (no RNG). The §1.3-vs-§2.1 "persisted vs refit" contradiction is removed. |

### Symmetry, identity & counting (attack-symmetry.md)

| # | Finding | Sev | Resolution |
|---|---|---|---|
| S-1 | Core-only matching is coarser than identity → split siblings double-match | critical | **Amended.** §5.1/§5.3: oriented patterns now carry the **full context predicates** (`core ∪ context`), and `match` verifies them after the core screen; each site matches ≤1 class. `SPLIT_CHECK` is removed entirely (identity is full-context, §4.4), so context-only splits — the source of the inconsistency — no longer exist. Invariant **I6**. |
| S-2 | Canonical form not a complete invariant (frame-dependent anchor, no min over anchors) | critical | **Amended.** §4.2/§4.3: `serialize` is minimised **jointly over (every moved site as anchor) × (every g∈D₄ₕ)**; `lex(offset)` is dropped from the anchor key. This is the genuine orbit invariant — equal canonical form ⟺ same class — so symmetric concerted/ring events no longer fragment across orientations. |
| S-3 | Symmetric multi-anchor events over-counted → inflated `R_total`, broken flux balance | critical | **Amended.** §5.3: each matched instance is keyed by its **canonical touched-site set + class_id** and **deduped**; a symmetric super-event enumerated from k equivalent anchors is admitted **once**. `n_f`, `n_b` become true instance counts → flux-level detailed balance holds. Invariant **I6**. |
| S-4 | Surface classes under C₄ᵥ omit σ_h → opposite surface never matches (silent zero flux) | major | **Amended.** §1.1/§4.1/§5.1: canonicalisation and compilation use the full slab group **D₄ₕ (16), which contains σ_h**, always; the surface's reduced stabiliser falls out of the decoration but both top and bottom surfaces are generated. No C₄ᵥ group selection exists. §7.5 also reports never-matched anchors as coverage holes. |
| S-5 | Self-reverse trusts pyKMC's mover graph-hash + context-blind Δ-inversion → forces ΔE=0 | major | **Amended.** §7.2: self-reverse requires some `g∈D₄ₕ` to map the **full decorated stencil** (Δ + context + ordered token), `before↔after` swapped, onto itself; `event_id==id_final` is never trusted. Context-asymmetric hops stay distinct and demand a measured `Ea_bwd`; `dEnergy` is never fabricated as 0. |
| S-6 | Saddle-token `role()` undefined + canonicalised as an unordered set → multi-mover fragment/merge | major | **Amended.** §3.3/§4.3: each token carries `start_rank` = the canonical rank of its mover's start offset (same anchor×group minimisation as S-2), and the token tuple is **ordered/mover-bound**, so each mover's start/end/saddle stay linked; two like-species movers over different bridges no longer merge, and orientations no longer fragment. |
| S-7 | Synthesized barrier-pending reverse has no runtime rate → ratchet or wrong-rate | major | **Amended.** §7.2: a one-sided harvest's reverse is **synthesized_balanced** with an explicit rate `k_b = k_f·(ν0_b/ν0_f)·exp(ΔE/kT)` from the forward's **measured per-pair ΔE**, so the pair is detailed-balance-consistent by construction; its instances are flagged/never-zero and top exploration priority — never excluded (ratchet) or fabricated at `k_floor`. |

### Statistics & the alternation loop (attack-statistics.md)

| # | Finding | Sev | Resolution |
|---|---|---|---|
| C1 | Exact-class rate uses `exp(−mean barrier)` over a fold-in mixture (Jensen) | critical | **Amended.** §4.4 makes each class one physical environment (no fold-in); §6.1 aggregates **in rate space** `k = ν₀·⟨exp(−Eₐᵢ/kT)⟩` (Jensen-exact) and **drops `trimmed_mean` for the rate** (it discarded the flux-dominant low-barrier member). `trimmed_mean` is retained only to *report* a representative barrier and to *flag* an outlier member as `CONTEXT_UNDERRESOLVED`. |
| C2 | Detailed-balance gate G2 is an algebraic tautology | critical | **Amended.** §7.2/§8.2: `dEnergy` is recovered from a **linked forward/backward pyKMC row pair sharing a saddle** (`dE_f − dE_b = E_min2 − E_min1`), an **independent** energy channel, not defined as the difference of two class means. G2 tests two independently-sourced quantities (incl. pyKMC's stored per-row `k`) and can genuinely fail; §12 includes a test that G2 **fails** on a fold-in of unpaired members. |
| C3 | A genuinely new event is silently absorbed as a "new instance" | critical | **Amended.** §4.4/§7.1: identity uses the **full `r_ctx` context**; new-class-vs-instance is exact full-context canonical equality. A 2nd/3rd-shell decoration is *always* a new class and *always* audited; convergence requires **new full-context classes → 0** (plus the §7.5 probe), not coarse-class count. |
| C4 | Class-mean forward/backward barriers form a fictitious ΔE → wrong equilibrium/SRO | critical | **Amended.** §7.2: per-pair balance (symmetrise each measured pair to one ΔE and one `ν0_f/ν0_b`) is the **default**; because classes are single-environment, members *are* pairwise reverses, so the class ΔE is a real per-pair mean, not a cross-population artefact. Rates aggregate in rate space (C1). |
| C5 | Harvest bias converges to a fully-catalogued but dynamically-wrong basin | critical | **Amended.** §7.5: convergence requires a **catalogue-independent physics probe** — a periodic short **direct pyKMC trajectory** whose event-frequency spectrum (KL/χ²) must agree with the on-lattice prediction — plus **forced off-distribution seeding** (planted Cr-depleted patches). `new-classes→0` alone is never sufficient. |
| M1 | Saddle-token snapping has no tolerance → flicker → non-terminating loop | major | **Amended.** Same fix as G-7: categorical token + hysteresis in the canonical frame; §12 adds a token-stability test across 100 re-relaxations. |
| M2 | Fallback regression extrapolates exponentially into unseen NiCr compositions | major | **Amended.** §6.2: a **convex-hull/leverage** test detects out-of-hull `φ`; such environments are **hard novelty** (high exploration-floor rate, `high_uncertainty`, top priority), never a confident Ni-like extrapolation; a minimum count of *that species'* environments is required before predicting for it; σ **grows with leverage**, never RBF-prior-saturated. |
| M3 | Frozen fallback model + in-leg drift → late (handoff) portion rated by the stalest model | major | **Amended.** §6.2/§8.3: reproducibility is decoupled from staleness — **within-leg refits** trigger on a monitored drift metric, each stamping a new `model_version` into the replay log; `n` may shorten adaptively on fast drift. |
| M4 | SPLIT_CHECK + running `trimmed_mean` are ingest-order-dependent | major | **Amended.** `SPLIT_CHECK` **removed**; identity is order-invariant full-context hash equality; rate is a **sorted** rate-space sum. No automatic running-mean split/merge decisions exist to replay (§4.4/§8.3). |
| M5 | Synthesized barrier-pending reverses break microscopic reversibility | major | **Amended.** Same fix as S-7: `synthesized_balanced` reverse with a per-pair-ΔE rate; never a ratchet, never a measured-forward/guessed-reverse pair in the BKL vector. |
| M6 | The refines-`event_id` validator rests on a frame-inconsistent pyKMC partition; 0.25 eV oversell | major | **Amended.** §4.4/§4.6: refine against a **single-frame** key (shared, consistently re-derived **`id_saddle`** + re-derived `id_min1/id_min2`), never the live forward `event_id`; the never-wrong-merge guarantee is stated in **rate units** (`|ΔEₐ| < k_BT`-scale), replacing the 0.25 eV (= 1.6×10⁴× rate) escape. |
| m1 | Single-sample classes report `Ea_std=0` and are read as maximally trustworthy | minor | **Amended.** §6.1: `Ea_std = None` for n<3 (never 0); shrinkage std with a prior floor for n≥3; the fallback fit weights by **effective sample count `n_eff`**, not by an std that is 0 for singletons. |

### Findings reconsidered but not separately "fixed"

- **Draft §4.7 `sym_perm` reading** — all three reports **confirmed** the draft's corrected reading
  (species-blind orbit of displacements, `is_duplicated`-filtered, identity prepended). Retained as the
  soft realizability cross-check (W11); no change beyond re-verification against `symmetries.py`.
- **Hash collisions on `class_id`** — explicitly rated SOUND by the symmetry lens (256-bit digest with
  the full tuple authoritative). The one residual (`if C in catalogue` on the hash) is made exact by
  keeping the full `canonical_form` as the tie-breaker (§4.3); not a behavioural change.

### Net structural change

The draft's barrier-driven `core/descriptor split with SPLIT_CHECK` — the source of S-1, C1, C2, C3,
C4, and M4 — is **removed** and replaced by the identity/rate/matching separation of §0.2:
full-`r_ctx`-context identity under D₄ₕ (a complete orbit invariant), rate-space aggregation with
per-pair detailed balance from linked rows, and enumerate-core/verify-context/dedup-instance matching.
Every critical and major finding is resolved by an in-place amendment; the three minors are also
amended.
