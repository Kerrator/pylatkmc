# Red-team review — Geometry & projection

**Lens:** periodic boundaries and the free surface; snapping tolerances vs relaxed off-lattice
positions; global drift/registration between snapshot and reference frame; degenerate/ambiguous
projections; unmappable atoms; reverse-mapping determinism; behaviour when the slab roughens.

**Target:** `FINAL_DESIGN_DRAFT.md` (the `synthesis` design), components §1 (frame/site model),
§2 (forward configuration projection), §3 (event projection), §4.1 (regime/depth), §5.2 (anchor),
§7.4 (reverse map).

**Input side actually read** (allowed by brief): `pyKMC/pykmc/event_table.py` (reference-table
schema + `_build_event_series`), `neighbors_list.py`, `point_set_registration.py`, `symmetries.py`,
`system.py`, `environments/{coordination,common_neighbor_analysis,graph_nauty,region}.py`,
`atomic_environment.py`, `utils/geometry.py`. The clean-room engine/classifier were **not** read.

The core input-contract facts I verified in source (they drive most findings):

- **Reference clusters are stored as raw, wrapped, un-recentred subset coordinates.**
  `event_table.py:653-656` stores `initial_positions = min1_positions[neighbor_list_forwward]`,
  `saddle_positions = saddle_positions[neighbor_list_forwward]`,
  `final_positions = min2_positions[neighbor_list_forwward]` — all sliced from full-system arrays
  with **no unwrap and no recentring**. `align_positions_by_neighbors` exists but is applied only to
  the *active* event table (`event_table.py:1115,1175`), never to reference rows. The three arrays
  share one atom order (the initial-state rcut neighbour list of the mover), so `P0[p]`, `Psaddle[p]`,
  `P2[p]` are the same atom — but the cluster can straddle a box face.
- **The neighbour KD-tree is periodic on all three axes**, `boxsize = [cell00, cell11, cell22]`
  (`neighbors_list.py:41-42`), i.e. z is treated as periodic even for a free-surface slab.
- **System positions are wrapped and negative coords are clamped to 0** every update
  (`system.py:189-194`: `self.positions[self.positions < 0] = 0`).
- pyKMC's *own* live-environment unwrap in PSR uses `alat = cell[0][0]` (the in-plane constant) as
  the threshold/shift for **all three axes including z** (`point_set_registration.py:102,130-142`) —
  boundary handling upstream is ad-hoc, so the design cannot assume clean clusters.
- The reference schema (`event_table.py:718-734`) carries **no absolute-atom-id column**, so a
  projected event has only subset-relative geometry — there is no cheap external key to detect a
  straddling or truncated cluster.

---

## Finding 1 — Boundary-straddling reference clusters silently corrupt the event-projection frame and surface-normal inference  **[CRITICAL]**

**Where:** §3.1 `fit_local_fcc`, §3.2 site-change detection, §3.1 "surface normal / z-sign is fixed
from the *missing* NN directions".

**Trigger (concrete):** any harvested event whose mover sits within ~`rcut` (≈5 Å ≈ 1.4 lattice
constants) of an in-plane periodic face — i.e. a large fraction of events on the first target
(10²–10³-atom) slab, where most of the in-plane area is within `rcut` of a boundary. Because the
stored cluster is raw wrapped coordinates (`event_table.py:653-656`), the mover's `−x` (or `−y`)
`⟨110⟩` neighbours at `x = x_mover − 1.76 Å < 0` are wrapped to `x ≈ Lx − 1.66 Å` and stored on the
**far side of the box**.

**Mechanism / what goes wrong:** `project_event` (§3) has **no min-image unwrap** (unlike the
forward *config* projection §2.2, which does "min-image in-plane"). `fit_local_fcc` matches nn bond
directions to the 12 ideal `⟨110⟩` directions; the across-boundary neighbours appear at ~`Lx`, not
2.49 Å, so they are silently excluded from the nn set. The design then "fixes the surface normal /
z-sign from the missing NN directions (the vacuum hemisphere has fewer than 12 neighbours)." A **bulk**
mover near an in-plane boundary now looks under-coordinated on the `−x` side → a **phantom in-plane
surface normal** is inferred, the Procrustes rotation `R_e` is fit to a lop-sided bond set, and the
event is routed to the *surface* symmetry regime instead of bulk.

**Downstream:** wrong `regime` → canonicalization under C₄ᵥ(8) instead of O_h(48) → wrong
`orientation_count`, wrong `class_id`, and a bulk vacancy hop near the boundary is catalogued as a
distinct "surface" class (silent catalogue pollution + failure of the convergence signal, since these
never stop appearing as the vacancy roams the boundary strip). The §4.7 `sym_matrix` cross-check is
itself computed by `unique_symmetries` on the *same* straddling cluster (`event_table.py:625-629`), so
it cannot catch the error. G4's round-trip only re-projects the design's *own* ideal re-expansion, not
the original straddling geometry, so it passes.

**Detection gap:** none of G1–G6 inspect for a cluster that spans > (box − rcut) in any in-plane axis.

**Fix:** before `fit_local_fcc`, min-image-unwrap every stored cluster about its `move_atom_idx` atom
using the event's own cell (the design already knows the cell); assert the unwrapped cluster diameter
< `2·rcut`. Derive the surface normal from the *decorated EMPTY hemisphere within `r_ctx`*, never from
"missing" atoms, so an in-plane boundary can never masquerade as a surface.

---

## Finding 2 — Ambiguous snap at the parity-Voronoi boundary → nondeterministic occupancy → phantom vacancies and phantom hops  **[CRITICAL]**

**Where:** §2.2 `round_to_even_parity` ("if parity is odd, flip the single coordinate with the
largest rounding error"); §2.3 `soft_surface_tol = 1.05 Å`.

**Trigger (concrete):** a surface / step-edge / under-coordinated atom that has relaxed toward a
bridge position (the normal response to a missing lateral neighbour) so its lattice-index coordinate
`u` lands near a **face of the parity-Voronoi cell**, where two of the three coordinates have nearly
equal rounding error (~0.5). `soft_surface_tol = 1.05 Å` (0.42·nn) is loose enough that such an atom
is **force-snapped** rather than flagged unmappable.

**Mechanism:** the tiebreak "flip the coordinate with the largest rounding error" is ill-conditioned
exactly on that face — a thermal-scale difference (~0.01 Å) between two otherwise-identical relaxed
minima flips which coordinate is flipped, so the atom snaps to site *A* in one cycle's snapshot and to
the adjacent site *A′* (2.49 Å away) in the next. Same physical configuration → two different
occupancy grids.

**Downstream (silent wrong physics):** the flip manufactures a **phantom vacancy at `A`** and a
**phantom atom at `A′`**. Vacancy-anchored enumeration (§5.2) immediately builds real, executable
vacancy-hop instances around the phantom vacancy; the BKL loop *executes events that do not physically
exist*, corrupting the trajectory and the SRO/composition coverage statistics that are the whole
dealloying signal. On handback, §7.4 emits the phantom atom at the wrong ideal site, so pyKMC minimises
from a wrong config and may "discover" a spurious event or waste a saddle search. If the flipped site
straddles a Ni/Cr occupancy boundary the species label is also wrong → wrong full-colour class → wrong
rate.

**Detection gap:** G4 checks `class_id` stability of a projected *event*, not the stability of the
forward *config* projection; nothing re-snaps a jittered copy of the snapshot to check determinism.
The design's "accept" verdict (§2.3, "0 unmappable, max residual < snap_tol") is satisfied by a
confidently-wrong snap.

**Fix:** treat any atom with a second-nearest-site distance within `snap_hysteresis` (~0.3 Å) of its
nearest as *ambiguous* → carry it with the previous cycle's assignment (hysteresis) or route to audit;
add a projection unit test: perturb a slab by `N(0, 0.05 Å)` 100× and assert the occupancy grid is
invariant.

---

## Finding 3 — `depth_sig` cannot be computed at ingest from a standalone cluster, so the silent subsurface/bulk merge it claims to fix is still open, and it aliases at depth ≈ rcut  **[CRITICAL]**

**Where:** §4.1 ("explicit `depth_sig` ... computed from `depth[]`") vs §3 event projection; §1.3
`Grid.depth` is a **global** BFS-from-vacuum array.

**Trigger (concrete):** a fully-coordinated subsurface event whose mover is deeper than ~`rcut` from
any free surface — its stored rcut cluster contains **no EMPTY-above/vacuum site at all**.

**Mechanism:** `depth_sig` is the design's headline closure of descriptor's "silent subsurface/bulk
merge." But it is defined in terms of `Grid.depth[]`, which is a property of the *assembled global
grid* built during forward *config* projection. Event ingest (§3, §7.1) processes an **isolated
subset cluster** from a past pyKMC row — there is no global grid, and depth is only knowable from the
cluster's *own* vacuum reach. For a mover deeper than `rcut` the cluster looks identical to bulk, so
`depth_sig` cannot distinguish `SUBSURF(d)` from `BULK`. The very merge §4.1 advertises as fixed is
therefore **still silent** for those events: a subsurface event with a genuinely different barrier is
merged into the bulk class (or vice versa) and gets the wrong Arrhenius rate.

**Second failure (aliasing):** for an event at depth ≈ `rcut/(a/2)` (≈2–3 layers), whether the
relaxed cluster's rcut ball *happens* to reach a vacuum site depends on surface relaxation and the
exact atom set — so instance 1 yields `SUBSURF(2)` and instance 2 yields `BULK`. The **same physical
event splits into two `class_id`s** → class fragmentation, split barrier statistics (defeating the
`Ea_std` gate and the trimmed-mean rate), and `new-classes-per-cycle` never reaches 0 → the loop's
convergence criterion never fires.

**Detection gap:** the "refines `(event_id, id_saddle)`" test (§4.4) does not help — pyKMC's
`event_id` is a single-atom graph/coordination certificate that *also* cannot see depth beyond its own
`rcut`, so both sides share the blind spot and the refinement check passes.

**Fix:** define `depth_sig` **operationally from the cluster** — `depth = min layers from the mover to
the nearest EMPTY-with-occupied-neighbour site inside the cluster`, and emit `BULK_OR_DEEPER` (a single
merged bucket) once the cluster is fully coordinated, explicitly accepting the merge for `d > rcut`
rather than pretending to resolve it; require `r_ctx ≥ (d_surf+1)·(a/2)` so the surface band is always
reached. Document that subsurface resolution is capped at `rcut`.

---

## Finding 4 — Reverse map with `R ≠ I` emits a non-periodic lattice → boundary defect seam poisons the next pyKMC harvest  **[MAJOR]**

**Where:** §1.1 `Cartesian(i,j,k) = origin + R·h·(i,j,k)`; §7.4 `to_atomistic` emits
`Cartesian(ijk[id], frame)` with the registered `R`; §2.1 fits `R` via `kabsch_ransac`.

**Trigger (concrete):** any cycle whose snapshot is slightly tilted or thermally sheared so RANSAC
returns `R = I + δR` with a small rotation angle θ (θ need only be ~0.1°). The design explicitly
registers `R` per cycle and only claims "`R ≈ I`", not `R = I`.

**Mechanism:** in-plane periodicity of the handed-back config requires the site image at `i + n_i` to
equal `Cartesian + Lx·x̂` (pyKMC's orthorhombic cell vector). But §7.4 emits it at
`Cartesian + R·(Lx·x̂)`, which differs by `(R − I)·Lx·x̂ ≈ θ·Lx` in the transverse direction. So a
**rotated ideal lattice does not tile the orthorhombic PBC box**: atoms on the `x = 0` face no longer
coincide with the periodic images of the `x = Lx` face. For a promoted 10⁵-site slab (L ≈ 200 Å),
θ = 0.1° gives a ~0.35 Å seam mismatch — comparable to `snap_tol`.

**Downstream:** pyKMC reads the config, wraps it, and **clamps negative coordinates to 0**
(`system.py:194`), further distorting the boundary atoms, then minimises from a strained seam →
discovers spurious boundary/edge "events" that are pure registration artifacts → catalogue pollution,
and the seam recurs every cycle θ ≠ 0. Because the reverse map is advertised as "byte-reproducible,"
this failure is invisible to provenance (the content hash is *of the wrong config*).

**Fix:** decouple the two uses of the frame — use `R` only to *read* the snapshot in §2.2, but emit
the reverse map on the **pure integer lattice with `R = I`** (`origin + h·(i,j,k)`), which tiles the
orthorhombic cell exactly. Assert `‖R − I‖` below a hard bound and abort→audit if a snapshot is too
tilted to register with `R = I`.

---

## Finding 5 — "Fall back to the last accepted snapshot" livelocks the loop in the roughening regime the mission targets  **[MAJOR]**

**Where:** §2.3 reject row: "Retry once with widened `snap_tol`; else fall back to the last accepted
snapshot and raise `PROJECTION_STRUCTURAL` audit."

**Trigger (concrete):** productive dealloying — the surface roughens / develops adatom-island +
pit texture / locally amorphises (the design's own W1). More than `n_soft = 3` surface atoms, or a
*cluster of adjacent* unmappables (explicitly a reject condition), exceed tolerance.

**Mechanism:** every fresh pyKMC snapshot in this regime is rejected, so the engine re-uses the *last
accepted* occupancy grid. But pyKMC has already evolved *past* that grid (the whole point of the
20–1000-step leg). Reverse-mapping the stale grid hands pyKMC a configuration it has already left; the
next leg re-roughens, is rejected again, and the loop **re-emits the same stale state indefinitely** —
no forward progress in configuration or time. Worse, the convergence metric is `new harvested classes
per cycle → 0`; a stalled loop that keeps re-projecting one frozen state produces zero new classes and
therefore reads as **converged** while actually being live-locked precisely where the interesting
physics (porosity onset) begins.

**Detection gap:** the coverage report tracks fallback-flux and unharvested environments, not
"snapshot rejected N cycles in a row" or "on-lattice state has not advanced." A human sees a stream of
`PROJECTION_STRUCTURAL` audits but the automated convergence gate says "done."

**Fix:** make repeated rejection a **distinct non-convergence signal** (`stalled`, not `converged`);
on reject, hand pyKMC the *rejected* (rough) snapshot to continue off-lattice rather than the stale
grid — i.e. degrade gracefully to pure pyKMC in the un-projectable region instead of freezing.

---

## Finding 6 — Column-envelope vacancy/vacuum test misclassifies porous / overhang / re-entrant geometry  **[MAJOR]**

**Where:** §2.3 and §1.3 `surface_k[i,j] = max k occupied in that column`; "an `EMPTY` below its
column's envelope is a **vacancy**, above it **vacuum**"; §5.2 anchors vacancy hops on
`species_sites[EMPTY]` filtered by this vacancy/vacuum call.

**Trigger (concrete):** the dealloying end-state itself — nanoporous ligaments, subsurface voids,
overhangs, and laterally-connected pores. A single overhanging adatom over an open pit is enough:
its column's `max k` is high, so **every open pore site beneath it is labelled "vacancy."**

**Mechanism:** the max-k column envelope assumes a monotone, single-valued surface height `z(x,y)`.
Porous / re-entrant morphology is multi-valued in z (occupied above empty above occupied...). Open
pore space that is laterally connected to the vacuum but sits *below* an overhang is misclassified as
interior **vacancy**; conversely a real vacancy under a thin ligament may be labelled vacuum if the
ligament column reads empty at its top.

**Downstream:** §5.2 enumerates vacancy-hop instances on pore/vacuum sites → the BKL list contains
**non-physical events**, and real pore-surface vacancies are missed → wrong event set and wrong flux
in exactly the regime the campaign exists to study. This is a *correctness* failure, broader than the
disclosed W9 (which frames porosity only as an `O(N)` performance degradation). The design also claims
promotion "unchanged" from the 1–2-vacancy workstation slab to production dealloying — this
assumption breaks there.

**Fix:** replace the column-envelope test with the design's own `depth[]` BFS from a *flood-fill of the
connected vacuum region*: an `EMPTY` site is "vacancy/adatom-target" iff it is **not** in the vacuum
flood-fill component *and* has ≥1 occupied neighbour. This is O(N) once per cycle (same budget as the
grid build) and is topology-correct for pores and overhangs.

---

## Finding 7 — Saddle-token quantization is fragile to frame error and to the off-lattice saddle magnitude → spurious class splits or silent merges  **[MAJOR]**

**Where:** §3.3 `tok = round_to_sublattice(2·(snap_frac(saddle_positions[p]) − midpoint(S0[p],S2[p])))`.

**Trigger (concrete):** any event whose saddle bulge (perpendicular displacement of the mover at the
transition state) has magnitude comparable to the sub-lattice quantization cell — which is the *common*
case, since a `⟨110⟩` bridge saddle sits only ~0.3–0.6 Å off the bond midpoint. The token is measured
in `frame_e`, the very frame that Finding 1 shows is fragile for near-boundary and surface events.

**Mechanism:** `2·(saddle − midpoint)` lands near a `round()` decision boundary. A small
registration error in `frame_e` (surface relaxation, straddle, RANSAC noise) or thermal variation in
the saddle position pushes it across the boundary, so two instances of the *same* physical mechanism
get **different tokens** → the SPLIT_CHECK/identity key splits one class into two (fragmentation,
defeating convergence and diluting barrier statistics). The inverse also occurs: two genuinely
distinct paths (over-bridge vs through-hollow) whose `2×` displacements round to the **same** integer
are silently merged with averaged barriers — the exact failure the token was introduced to prevent
(§4.7, "the fix to pattern's biggest identity weakness").

**Detection gap:** the design offers "SPLIT_CHECK backstop if token too coarse" for the merge
direction but nothing for the *over-split* direction, and no bound is given on the token's robustness
radius vs the frame's registration error.

**Fix:** compute the token in the *canonical class frame* after Δ-canonicalization (not the noisy
per-event `frame_e`), and only quantise the **discrete topological class** of the saddle (which hollow
/ which bridge, by counting the coordinating atoms of the saddle site) rather than a continuous
`round()` of a length comparable to the cell; carry a real-valued saddle offset in provenance for
audit rather than baking a brittle rounding into the identity key.

---

## Finding 8 — Isolated interstitial / dumbbell silently drops an atom and is *accepted*  **[MAJOR]**

**Where:** §2.2 collision handling (`if occ[id(s)] != EMPTY: collision.append(...); keep_nearer`) and
§2.3 accept rule (`≤ n_soft (3) unmappable ... accept + warn`).

**Trigger (concrete):** a single `⟨100⟩` split-interstitial / dumbbell — two atoms sharing one FCC
site's Voronoi cell. Autonomous pARTn saddle searches *discover interstitial-mediated pathways*
(that is the design's stated selling point over standard lattice catalogues), so this is not a corner
case for the discovery engine.

**Mechanism:** both dumbbell atoms snap to the same site id; `keep_nearer` keeps one and marks the
other **unmappable**. One isolated dumbbell = 1 collision + 1 unmappable, **below `n_soft = 3`**, so
the snapshot is *accepted* per §2.3 — with an atom silently deleted from the grid.

**Downstream:** the grid is non-conservative, but the I4 conservation invariant is defined over
on-lattice *cycles* (§1.3, "Σ non-EMPTY constant across a canonical cycle"), not over the projection
step, so it never fires. Composition drifts by one atom per accepted interstitial; the reverse map
hands pyKMC a config missing that atom; and a genuinely interstitial diffusion event can never be
represented, yet is *absorbed* rather than *flagged* (the opposite of G3's intent for off-lattice
pathways).

**Fix:** treat **any** collision as a hard structural signal (a rigid lattice cannot host two atoms
per site) → route to audit / hand back to pyKMC, regardless of `n_soft`; add a projection-time
conservation check (`n_occupied_sites == n_atoms − n_unmappable`) that must equal the input atom count.

---

## Finding 9 — `layer_z` is detected but never used in the snap, and KDE peak detection degrades on thin/rough slabs  **[MINOR]**

**Where:** §2.1 `layer_z = kde_peaks(X[:,2])` ("Layer detection ... is what makes surface relaxation
harmless") vs §2.2, which snaps with **uniform** `h`: `s = round_to_even_parity((1/h)·Rᵀ·(X−origin))`
and scores `d = |X − Cartesian(s)|`, `Cartesian(s) = origin + R·h·s`.

**Mechanism:** the advertised relaxation-absorption is not realised — `layer_z` is computed and stored
in `LatticeFrame` but does not enter the snap or the residual, which both use the uniform `k·h`
plane. A contracted/rumpled top layer is therefore measured against the ideal plane, inflating its
residual toward `soft_surface_tol` (feeding Finding 2's ambiguity). Separately, `kde_peaks` assumes a
cleanly layered z-histogram: on the **first target system** (10²–10³ atoms ≈ 6–10 layers, few atoms
per layer) the peak statistics are thin, and once the surface roughens, adatom/step z-values fill the
inter-layer bins so peaks merge → wrong layer count → wrong `k`/`depth` assignment.

**Downstream:** internal inconsistency (a stored quantity the design's correctness argument leans on
is dead code) plus fragile layer indexing that couples into `depth_sig` (Finding 3) and the
vacancy/vacuum height (Finding 6).

**Fix:** actually snap z to the nearest **detected** `layer_z[k]` (not `k·h`) and score residuals
against it; or drop `layer_z` and own the uniform-`h` approximation honestly. Guard `kde_peaks` with a
minimum-atoms-per-peak check and fail→audit when peaks are not separable.

---

## Finding 10 — Reverse-map determinism is undercut by per-cycle, unseeded re-registration (and an internal spec contradiction)  **[MINOR]**

**Where:** §7.4 / §1.3 claim a "byte-reproducible" / "bit-reproducible" reverse map and list "frame
`content_hash`" among the reproducibility inputs (§8.3). §2.1 **re-registers the frame every cycle**
via `kde_peaks` + Nelder–Mead phase search + `kabsch_ransac`.

**Mechanism:** `to_atomistic` is deterministic only *given a frame*. But the frame is the output of
KDE peak-picking (threshold/bandwidth-sensitive), Nelder–Mead (initialisation-sensitive), and RANSAC
(randomised, unseeded in the spec). Re-running the same cycle can yield a different `origin`/`R`/`h`
→ different ideal positions → different pyKMC minimisation start → potentially different discovered
events → a non-reproducible catalogue. §1.3 says the `LatticeFrame` is "persisted per campaign," which
**contradicts** §2.1's "refit each cycle": if it is truly refit each cycle, then "identical occupancy
⇒ byte-identical coordinates" (§7.4) holds only *within* a cycle, not across the campaign the
reproducibility claim (§8.3) covers; the stored `content_hash` then records the drift rather than
preventing it.

**Fix:** register the frame **once** at campaign start (persisted, hashed, seeded), and in later cycles
only *track* rigid drift with a bounded, deterministic refinement (or none), so `origin`/`R`/`h` are
fixed inputs; explicitly seed RANSAC and Nelder–Mead and record the seeds in provenance.

---

## Severity summary

| # | Finding | Severity | Primary component |
|---|---|---|---|
| 1 | Boundary-straddling cluster corrupts event frame + surface-normal inference | critical | §3 event projection |
| 2 | Ambiguous parity-Voronoi snap → nondeterministic occupancy → phantom vacancies/hops | critical | §2.2 forward projection |
| 3 | `depth_sig` uncomputable at ingest → silent subsurface/bulk merge persists + rcut aliasing | critical | §4.1 identity / §3 ingest |
| 4 | `R ≠ I` reverse map emits non-periodic lattice → boundary seam poisons harvest | major | §7.4 reverse map |
| 5 | Fallback-to-stale-snapshot livelocks the loop in the roughening regime | major | §2.3 cycle policy |
| 6 | Column-envelope vacancy/vacuum test wrong on porous/overhang geometry | major | §2.3 / §5.2 |
| 7 | Saddle-token `round()` fragile → spurious splits / silent merges | major | §3.3 saddle token |
| 8 | Isolated interstitial silently drops an atom and is accepted | major | §2.2 collision policy |
| 9 | `layer_z` detected but unused; KDE smears on thin/rough slabs | minor | §2.1 registration |
| 10 | Reverse-map determinism undercut by per-cycle unseeded re-registration | minor | §2.1 / §7.4 |

**Cross-cutting theme:** the design's forward *configuration* projection (§2) is min-image- and
PBC-aware, but the event *projection* (§3) and the identity machinery (§4) inherit **raw, un-recentred,
grid-less** clusters from pyKMC and quietly assume they are clean, well-centred, vacuum-reaching, and
frame-stable. Every critical finding is an instance of that inheritance gap: the boundary (1, 4), the
free surface / relaxation (2, 6, 7, 9), the missing global context at ingest (3), and the un-projectable
regimes (5, 8). The forward pipeline's guards (RANSAC, min-image, snap tolerance, unmappable report)
are not mirrored on the event/identity side, which is where the catalogue is actually built.
