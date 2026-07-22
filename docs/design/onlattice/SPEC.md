# CLEAN-ROOM DESIGN BRIEF — Species-aware on-lattice KMC fed by autonomous off-lattice event discovery

You are designing, from first principles, the **event representation and machinery** for an
on-lattice kinetic Monte Carlo (KMC) engine whose event catalogue is not hand-written but
**harvested from an off-lattice, autonomous event-discovery KMC code (pyKMC)** through an
alternating loop. Your design is the product; implementation follows later.

## CLEAN-ROOM RULE (binding)

Workspace documents in this repository (CLAUDE.md, AGENTS.md, memory files) reference an existing
on-lattice engine and an existing event-classification pipeline built by this group. You must
**not** read those components, search for them, or let any workspace description of them shape
your design. Design from first principles and from the published lattice-KMC literature you
already know (rejection-free/BKL, pattern-based lattice codes, cluster-expansion KMC, adaptive
KMC, off-lattice/on-lattice hybrid schemes — all fair game). You MAY read the pyKMC source tree
(`/home/kerr/pykmc/pyKMC/pykmc/`) — it is the *input side* of your design, particularly
`event_table.py` and `environments/` (`common_neighbor_analysis.py`, `coordination.py`,
`graph_nauty.py`, `region.py`). Ignore anything else the workspace tells you about how this
problem "is currently done".

## Scientific mission

Dealloying of FCC Ni-Cr and Ni-Fe (later ternary Ni-Cr-Fe) slab surfaces. The off-lattice engine
(pyKMC: pARTn saddle searches + local-environment classification + event reuse via point-set
registration) autonomously discovers diffusion events, including events absent from
literature-standard lattice catalogues. The on-lattice engine must execute the harvested
catalogue **fast** (10⁶+ steps) so that configuration space and time evolve far beyond
off-lattice reach; the loop alternates the two engines so discovery keeps pace with evolution.

## The alternation loop (fixed decisions — design within these)

1. **Deliverable is staged, catalogue-first.** The loop is a catalogue-completion engine: cycles
   are file-based handoffs, each step scriptable, so a closed-loop driver can be added later
   without redesign. Convergence signal: newly harvested event classes per cycle → 0.
2. **Diffusion-only for now.** No dissolution/electrochemistry in the loop yet. The lattice is
   canonical (atom count conserved) in v1, BUT the event schema must leave room for
   occupancy-count-changing events (site → empty with atom removal) so a later dealloying
   campaign needs no re-harvest or schema break.
3. **pyKMC leg = real KMC steps with a seeded table.** Each cycle maps the lattice configuration
   back to atomistic coordinates, runs k = 20–1000 ordinary pyKMC steps with the *cumulative*
   reference event table preloaded (pyKMC's own registration-based dedup makes rediscovery
   cheap); the cycle's harvest is the new reference-table rows.
4. **Rate model = exact-class lookup + parametric fallback.** An executable event instance whose
   local environment exactly matches a harvested class uses that class's rate (Arrhenius from
   averaged barrier + prefactor). A near-miss environment gets a rate from a regression fitted to
   all harvested barriers over local-environment descriptors (bond-counting / local-composition
   style) and the site is **flagged**; flagged environments are priority targets for the next
   pyKMC exploration leg. Nothing silently contributes zero flux.
5. **Curation = auto-gates + exception audit.** Automated gates (barrier within physical bounds,
   forward/backward pair consistency, small snap residual, projection round-trip check) admit
   events immediately; failures and first instances of brand-new classes go to a human audit
   queue. Your design must define the gate checks precisely and carry per-class provenance.
6. **Switching = fixed n + coverage report.** The evolve leg runs a fixed, tunable n (~10⁶
   steps), then emits a coverage report: fraction of executed flux carried by fallback rates,
   environment classes observed-but-unharvested, composition / short-range-order drift. These
   metrics must be cheap to accumulate during the run.
7. **First target system:** small NiCr(100) slab, order 10²–10³ atoms, 1–2 vacancies, free
   surface, both engines on one Linux workstation; later promoted unchanged to production slab
   geometry (10⁵+ sites) on a cluster.

## Input contract — what pyKMC gives you

**Reference event record** (one row per discovered event; see `event_table.py`, reference-table
schema): `initial_positions`, `initial_types`, `saddle_positions`, `final_positions` — arrays for
a *local cluster* of atoms around the event (subset-relative indexing); `energy_barrier` [eV];
`k` [ps⁻¹] and `k_prefactor`; `nu0` [ps⁻¹] (harmonic-TST attempt frequency, when enabled);
`move_atom_idx` — index (subset-relative) of the *nominal primary mover*; `sym_matrix`,
`sym_perm` — the rotation + permutation found by point-set registration when the event was
deduplicated; `idx_backward` — row index of the paired reverse event; `event_id`, `id_saddle`,
`id_final` — environment hash ids; `dra` [Å] — mover initial→saddle displacement norm.

Caution: the schema names ONE mover, but `final_positions − initial_positions` may show several
atoms changing lattice sites (concerted events). Your projection must detect the true set of
site changes, not trust `move_atom_idx` alone.

**Full-cell snapshots**: positions (N×3, Å), chemical types, cell matrix, at every KMC step.
**Restart capability**: pyKMC can start from a supplied atomistic configuration and a supplied
reference table (`config.control.reference_table`).

**Lattice context**: FCC nickel, a ≈ 3.52 Å; slab with in-plane periodic boundaries and free
surfaces in ±z; site alphabet {Ni, Cr, Fe, empty}; a bulk vacancy is an interior empty site;
coordination/surface are emergent from occupied-neighbour counts. Off-lattice positions are
*relaxed* — atoms sit near, not on, ideal sites; surface atoms deviate most.

## Required design components (cover ALL — your angle determines emphasis, not scope)

1. **Forward configuration projection**: off-lattice snapshot → site occupancy on a fixed global
   FCC reference frame. Snap policy, drift/registration handling, tolerance, and the report of
   unmappable atoms (what threshold, what happens to the cycle if any exist).
2. **Event projection**: an off-lattice event record → an on-lattice event: a **set of (site,
   occupancy-before → occupancy-after) changes** (multi-site is first-class; the 2-site
   vacancy swap is the common case), plus the surrounding context needed for identity.
3. **Class identity**: when are two projected events *the same lattice event class*?
   Canonicalization under the lattice symmetry appropriate to a (100) slab (bulk site group vs
   reduced surface symmetry — handle both), species decoration, and the size/shape of the
   environment context that is part of identity. This is the heart of the design — justify it.
4. **Runtime matching**: given the occupancy grid, enumerate every executable event instance
   (all classes, all orientations, all sites) to build the KMC rate list; update it
   **incrementally** after each executed event. Complexity analysis required: target ≥10⁶ steps
   on 10³ sites in minutes and 10⁵–10⁶ sites feasible on a cluster node.
5. **Rate assignment**: exact-lookup path; the fallback regression (descriptor choice, fitting
   protocol, refit cadence as the catalogue grows); the flag mechanism; Arrhenius evaluation
   k = ν₀·exp(−Ea/kBT) with class properties (Ea, ν₀) temperature-independent.
6. **Novelty & harvest round trip**: mapping new pyKMC rows into classes; deciding
   "new class" vs "new instance of known class"; preserving forward/backward pairing
   (microscopic reversibility bookkeeping); the coverage-report metrics of loop decision 6.
7. **Provenance & curation hooks**: per-class record of source cycle(s), contributing barriers
   and their spread, gate outcomes; the audit queue interface; determinism/reproducibility of
   the reverse mapping (occupancy → ideal-site atomistic configuration handed to pyKMC, which
   will minimize it).

## Deliverable format (a design document, not code)

Concrete data schemas (structs/tables with field types), algorithms in pseudocode, worked
example (a vacancy hop AND a 3-site concerted event, projected → classified → matched →
executed), complexity analysis, failure-mode table (what breaks it, how it's detected), test
plan (unit + round-trip + statistical), and an explicit list of the design's own weaknesses.

## Evaluation rubric (how you will be judged)

- Correctness & physical fidelity — 30
- Runtime matching cost at scale — 20
- Classification robustness + novelty detection — 20
- Implementability & fit to the harvest pipeline above — 15
- Extensibility (ternary species, occupancy-count-changing events, closed-loop driver) — 15
