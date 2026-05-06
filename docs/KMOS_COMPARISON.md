# KMOS_COMPARISON.md — what we ported, what's still kmos-different

**Audience:** kmos users curious about pylatkmc, and pylatkmc readers
curious about why our IR + runtime data structures look the way they do.

**Last updated:** 2026-05-06 (v0.2.0).

---

## TL;DR

After v0.2's hard cutover to the pattern-DB pipeline, pylatkmc is
much closer to kmos in spirit than it was during v0.1. The main
differences now are:

- **Implementation language**: kmos emits Fortran, pylatkmc emits C.
- **Lattice format**: kmos uses cell-tiled `(cell_i, cell_j, cell_k,
  named_site)` indexing; pylatkmc uses a flat per-site `coord_table`
  populated from positions.
- **Catalogue source**: kmos models are hand-authored in Python
  (`Project()` + `add_process(...)`); pylatkmc translates a curated
  pyKMC FCC family CSV.
- **Bystanders / OTF rates**: kmos runs through it; pylatkmc v0.2
  bakes scalar rates at codegen time (Bystanders deferred).
- **Front-end / GUI**: kmos has a Qt-based process editor; pylatkmc
  is CLI-only.

Everything else — the Process IR, the decision-tree compiler, the
`avail_sites` data structure, the BKL selector — is a faithful port.

---

## What we ported directly from kmos

### 1. Process IR

| kmos                     | pylatkmc                           |
|---|---|
| `Process(condition_list, action_list, bystander_list, rate_constant, …)` | `Process(conditions, actions, bystanders, rate_constant, …)` |
| `ConditionAction(coord, species)` | `Condition(coord, species)` + `Action(coord, before, after)` |
| `Bystander(coord, allowed_species, flag)` | `Bystander(coord, allowed_species, flag)` |

kmos's `ConditionAction` doubles as both pre-condition and post-action;
pylatkmc splits them so the validator can check `Action.before` against
the matching `Condition.species`. Schema is otherwise 1:1.

References:
- kmos: `_archive/kmos-main/kmos/types.py:2024–2255`
- pylatkmc: [`pylatkmc/processes.py`](../pylatkmc/processes.py)

### 2. Decision-tree codegen

`pylatkmc/decision_tree.py:compile_decision_tree` is a port of kmos's
`_write_optimal_iftree` (`_archive/kmos-main/kmos/io/__init__.py:2568`).
The algorithm:

1. Find the most-frequently-shared `Coord` across all remaining
   Processes' Conditions.
2. Emit a `switch` on the species at that coord.
3. For each species value, partition the Process set into those
   expecting that species at that coord; recurse.
4. Leaf = enrol the Process via `avail_sites_add(as, P_<name>, site)`.

The output is a tree of average depth ~log(n_processes) and worst-case
depth = max condition count per process. Behaviour is identical
between kmos's Fortran emitter and pylatkmc's C emitter; only the
target language differs.

### 3. `avail_sites` data structure

kmos's Fortran array `avail_sites(proc, k, switch)`
(`_archive/kmos-main/kmos/fortran_src/base.mpy:88–302`) ports verbatim
to pylatkmc's
[`runtime/src/core/avail_sites.{h,c}`](../runtime/src/core/avail_sites.h):

| kmos (Fortran)                     | pylatkmc (C)                                        |
|---|---|
| `avail_sites(proc, k, 1)` for k=1..nr_of_sites(proc) | `site_at[proc * n_sites + k]` for k in [0, n_sites_per_proc[proc]) |
| `avail_sites(proc, site, 2)`       | `slot_of[proc * n_sites + site]`, -1 if not enrolled |
| `nr_of_sites(proc)`                | `n_sites_per_proc[proc]`                            |
| `accum_rates(proc)`                | `cum_rates[proc]`                                   |
| `add_proc(proc, site)`             | `avail_sites_add(as, proc, site)`                   |
| `del_proc(proc, site)`             | `avail_sites_del(as, proc, site)`                   |
| `determine_procsite(target)`       | `avail_sites_select(as, target, &proc, &site)`      |

Same O(1) swap-last semantics, same binary-search BKL select, same
memory layout (one big flat array per axis).

### 4. BKL selector

`avail_sites_select` is the standard BKL: binary-search `cum_rates`
for the smallest `proc` with `cum_rates[proc] > target`, then pick a
site uniformly within that proc's enrolled list. Same as kmos's
`determine_procsite`.

---

## What's pylatkmc-specific (not in kmos)

### 1. Coordinate resolution: `NeighbourCode` instead of `(name, offset, layer)`

kmos's `Coord(name, offset, layer)` carries:
- `name` — a within-cell named site (e.g. "A", "B", "hollow1")
- `offset` — integer cell offset (di, dj, dk) in unit-cell units
- `layer` — logical grouping name

The runtime indexes sites by `(cell_i, cell_j, cell_k, name_idx)`.
That requires storing per-site `(cell_i, cell_j, cell_k, name_idx)`
in the lattice format.

pylatkmc's `.kmcinit` only stores Cartesian positions + CSR
adjacency (it pre-dates the v2 redesign). Rather than retrofit
cell-coords into the lattice format, we adopt a flat enum:

```c
typedef enum {
    NC_ANCHOR,
    NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY,
    NC_NN1_DOWN_PP, …, NC_NN1_UP_MM,
    NC_NN2_DIAG_PP, …, NC_NN2_DIAG_MM,
    NC_NN2_PX, …, NC_NN2_MZ,
    N_NEIGHBOUR_CODES                                  /* = 23 */
} NeighbourCode;
```

Each code names a specific neighbour direction with a documented
canonical Cartesian delta. At lattice load,
`lattice_build_coord_table(lat)` walks each site's nn1/nn2 CSR and
matches each edge's actual position-delta against the canonical
deltas, populating a flat lookup table:

```c
coord_table[site * N_NEIGHBOUR_CODES + nc]
    = absolute neighbour site index, or -1
```

The result is **functionally equivalent** to kmos's
`(name, offset, layer)` lookup, but specialised to FCC. Generalising
to BCC/HCP means adding more codes (or refactoring to kmos-style
named-sites).

### 2. Catalogue translator

kmos models are hand-authored:

```python
project = kmos.Project()
project.add_layer(name="ruo2")
…
project.parse_and_add_process(
    "CO_adsorption_cus; empty@cus -> CO@cus; k_CO_ads_cus")
```

pylatkmc generates Processes from a curated catalogue. For each
`(family_id, family_bucket_id)` row in `rate_lookup_table_family.csv`,
the translator emits one Process per direction in the family's
`_FAMILY_DIRECTIONS` table. The pattern is intentional: catalogues
let domain experts (the pyKMC analysis pipeline) curate event types
once, and the translator deterministically produces hundreds of
Processes from that.

References:
- kmos hand-authoring: `_archive/kmos-main/examples/AB_model.py`
- pylatkmc translator: [`pylatkmc/translator.py:translate_all`](../pylatkmc/translator.py)

### 3. Active-site filter

kmos always rebuilds the avail_sites for *every* site that's been
touched by an event (and its surrounding stencil). For typical
catalysis problems with full-cell occupancy that's appropriate.

pylatkmc adds a coordination-based active filter (port of pyKMC's
`atomic_environment` threshold; see
[`runtime/src/core/active_filter.{h,c}`](../runtime/src/core/active_filter.h)).
For a single-vacancy slab where most atoms are bulk-coordinated and
no Process can fire on them, the filter cuts touchup cost from
O(n_sites) to O(active_sites) — typically 13–20 sites for our
1-vacancy ni_fe_cr_v1 system instead of 192.

This is a v0.2 specialisation for slab geometries with few defects;
kmos doesn't need it because catalysis surfaces are densely populated.

### 4. State + multi-site action validation

kmos's runtime applies actions one at a time. pylatkmc's
`state_apply_actions` validates every action's `before` against
the live state, rejects duplicate sites, checks `n_vac` overflow,
*then* mutates atomically. On any validation failure, returns
`-EINVAL` with no mutation.

The validator catches codegen bugs that kmos would silently corrupt.

### 5. Rate baking strategy

kmos supports OTF (on-the-fly) rate evaluation: rate constants are
expressions evaluated at runtime, allowing T or chemical-potential
sweeps within a single binary.

pylatkmc v0.2 bakes rates at codegen time:

```c
[P_<name>] = { .rate = k0_Hz * exp(-Ea_eV / (kB * T_K)), .Ea_eV = … },
```

To run at a different T, regenerate proclist.c. This is intentional:
the pylatkmc workflow pairs each model directory with a single (T, k0)
pair, and rebuilds are cheap (proclist.c regenerates in ~1 s, full
binary in ~10 s).

Adding OTF rates would require carrying a small expression evaluator
in the runtime — deferred.

---

## What we deliberately didn't port

### Front-end editor

kmos ships a Qt-based GUI process editor (`kmos edit`), good for
hand-authoring and visualising small models. pylatkmc is CLI-only;
visual inspection of the catalogue and emitted Processes is via
`pylatkmc-gen processes <spec>` (text summary) and the upstream
`apps/PyKMC_Analysis/Analysis/event_viewer/` Dash app for the
catalogue itself.

### XML model serialisation

kmos serialises models to XML. pylatkmc has no equivalent — the
canonical model representation is the TOML spec + the curated CSV.
Reproducibility is via git.

### Steady-state / temperature ramps

kmos's runtime supports steady-state convergence checks and
automated T-ramp protocols. pylatkmc keeps the runtime simple: run
N steps or T seconds, write the trajectory, exit. Higher-level
protocols are the user's job (typically driven from Python).

---

## Side-by-side: simple 1NN hop in both worlds

### kmos

```python
project.add_layer(name="ruo2")
project.add_site(name="cus", layer="ruo2", pos=[0.5, 0.5, 0.5])
project.add_species(name="empty")
project.add_species(name="CO")
project.add_parameter(name="T", value=600)
project.add_parameter(name="k_CO_diff", value="1e10*exp(-0.6/(kB*T))")

project.parse_and_add_process(
    "CO_diff_x; "
    "CO@cus.(0,0,0).ruo2 + empty@cus.(1,0,0).ruo2 "
    "-> empty@cus.(0,0,0).ruo2 + CO@cus.(1,0,0).ruo2; "
    "k_CO_diff")
```

### pylatkmc

```python
# (auto-generated by translator.translate_all from the catalogue)
Process(
    name="surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni",
    family_id="surface_1NN_inplane",
    Ea_eV=0.6121,
    rate_constant=1e13 * exp(-0.6121 / (kB * 500.0)),  # baked at codegen
    conditions=(
        Condition(coord=CoordOffset(code="NC_ANCHOR"), species="Vacant"),
        Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),
    ),
    actions=(
        Action(coord=CoordOffset(code="NC_ANCHOR"), before="Vacant", after="Ni"),
        Action(coord=CoordOffset(code="NC_NN1_PX"), before="Ni", after="Vacant"),
    ),
)
```

Same physics, same matching, same atomic apply. Just a different
authoring path.

---

## What we could still steal later

- **Per-arrangement Processes.** kmos lets users specify exact
  spatial arrangements; we currently average over arrangements within
  a (family, bucket). When intra-bucket Ea scatter is wide,
  per-arrangement Processes would be more faithful.
- **Bystanders / OTF rates.** Catalogue rate-modulation by Bystander
  counts is a real win for n_Fe-dependent surface_1NN rates;
  v0.2 deferred this.
- **Cell-tiled lattice indexing.** For BCC/HCP we'll likely need
  kmos's full `(name, offset, layer)` IR.
- **`kmos export_xml`-style model serialisation.** Would simplify
  reproducibility for archival models.

---

## See also

- [`PATTERN_DB.md`](PATTERN_DB.md) — pattern-DB pipeline reference.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — three-layer overview.
- [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) — worked example trace.
- kmos source: `_archive/kmos-main/` (in the workspace meta-repo).
