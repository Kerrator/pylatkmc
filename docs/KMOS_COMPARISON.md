# pylatkmc vs. kmos

**Audience:** anyone trying to reason about why pylatkmc made specific architectural choices, or considering merging ideas from one into the other.
**Last updated:** 2026-04-19 (after M4 species harness).

**Source code for every claim below:** `kmos-main/` in this repo (Hoffmann's kmos, GPLv3) for kmos; `pylatkmc/` for pylatkmc. File:line references are relative to ``.

This document supersedes the earlier `docs/kmos_environment_matching.md`, which was written before pylatkmc's codegen build-out and is now positioned as a redirect.

---

## TL;DR — mental-model contrast

Both codes are **on-lattice KMC engines driven by Python-authored model specs** that compile down to specialised, per-model native code. That's the broad similarity. The differences are mostly about **where physics complexity lives**.

- **kmos** stores complexity **in code**. Each rate is a formula string attached to a *Process*. Each Process has a list of `(coord, species)` conditions. At codegen time, those conditions become a nested `select case` decision tree per affected lattice coord. At runtime, an `avail_sites` data structure tracks "for each Process, the list of sites where its conditions are currently true" — maintained incrementally, O(1) per site change.
- **pylatkmc** stores complexity **in data**. Each rate is a `f32` in a flat N-dimensional cube indexed by an integer key. There are no Processes; events are enumerated each step from the lattice topology + species, the rate cube is consulted, BKL selects one. Schema lives in a TOML model spec; codegen specialises the C inner loop to that schema so the lookup is branch-free.

Both ship Python → C/Fortran codegen with a string-template preprocessor. We literally ported kmos's `#@ ... @#` preprocessor (~50 LOC from `kmos-main/kmos/utils/__init__.py:1449`) into `pylatkmc/pylatkmc/codegen.py`. Below the preprocessor, the architectural choices diverge.

---

## How a user declares physics

### kmos

A `Process` is a 4-tuple: `(name, rate_constant, condition_list, action_list)`. Every condition and action is `(coord, species)`. From `kmos-main/examples/render_diffusion_model.py` style:

```python
pt.add_process(
    name='A_diff_right',
    rate_constant='k_diff',
    condition_list=[
        Condition(coord=c_hollow,          species='A'),
        Condition(coord=c_hollow_right_nn, species='empty'),
    ],
    action_list=[
        Action(coord=c_hollow,          species='empty'),
        Action(coord=c_hollow_right_nn, species='A'),
    ],
)
```

Defined in `kmos-main/kmos/types.py:2024–2256`.

To express a **neighbour-dependent** rate, kmos offers two paths:

1. **Pre-enumerate processes.** `kmos-main/examples/render_pairwise_interaction.py:61–81` literally loops over all 2⁴ 1NN configurations and generates 16 separate processes with rate constants that bake in the count of CO neighbours. Pro: zero runtime arithmetic. Con: `2^N` process explosion in codegen.
2. **Bystanders + OTF rate evaluation.** `kmos-main/examples/render_pairwise_interaction_otf.py:59–70`. One process carries a `bystander_list`. At runtime, generated Fortran counts matching bystanders into `nr_<sp>_<flag>` variables and the `otf_rate` expression folds them in. Pro: one process. Con: runtime arithmetic per event.

### pylatkmc

A model is one TOML file. Physics doesn't enter as Processes — it enters as **axis declarations**:

```toml
species = ["Vacant", "Ni", "Fe", "Cr"]

[[shells]]
name = "nn1"
cutoff_mult = 1.05

[[key.axes]]
name = "mover_species"
kind = "enum"
max  = 3              # Ni / Fe / Cr (Vacant excluded)

[[key.axes]]
name  = "n_vac_nn1"
kind  = "count"
shell = "nn1"
match = "vac"
max   = 5

# … six more axes for n_Fe_nn1, n_Cr_nn1, n_vac_nn2, n_Fe_nn2, n_Cr_nn2 …

[rate_data]
primary       = "../../../Analysis/.../classified_events_with_families.csv"
temperature_K = 500.0
k0_Hz         = 1.0e13
```

The user declares **what dimensions of the local environment matter** for rate selection. They never write a process. Codegen turns the spec into a `RateKey` struct, an inline `ratetable_key(...)` function, and a `scan_<shell>()` loop that builds the key from the lattice state. The rate values come from data — pre-aggregated in `pylatkmc.ratebuilder.build` at build time, mmap'd as a 4-byte float per cell.

For a neighbour-dependent rate, pylatkmc has only one path: **add an axis**. The 9-axis schema in `models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml` is what species awareness looks like. There's no `2^N` blow-up because we don't enumerate — we count.

---

## Three backends (kmos) vs. one runtime (pylatkmc)

kmos has three codegen backends, picked in `kmos-main/kmos/io/__init__.py:140–165`:

| Backend | Fortran template | Pattern matching | Rate evaluation | Sweet spot |
|---|---|---|---|---|
| `local_smart` (default) | `base.mpy` (~1380 lines) | nested `select case` on species at each stencil coord; incremental update via `touchup_*` subroutines | compile-time scalar rate per process | small stencil, few processes |
| `lat_int` | `base_lat_int.mpy` (~1380 lines) | same as `local_smart` but processes are **grouped** into lateral-interaction clusters that share a `run_proc_<group>.f90` | compile-time scalar rate per process | many processes that share a stencil (e.g. 16 pairwise variants) |
| `otf` (on-the-fly) | `base_otf.f90` (~1530 lines) | matches only on hard conditions; soft counts (`bystander`) are evaluated at call time | **runtime**: `otf_rate` expression with `nr_*` bystander counts as free variables | many-body / continuous-coverage interactions |

pylatkmc has one runtime: a static C backbone (`runtime/src/{core,io,mpi}/`) plus per-model generated `events.h`, `ratetable.{h,c}`, `avail.c`. There's no OTF tier and no incremental matcher — every step does a full rebuild of the events array. The reason it can be that simple is that the rate cube is **the** lookup mechanism; there's no decision tree to maintain.

Implementationally, pylatkmc's "one backend" sits closest to kmos's `lat_int` mental model: many "processes" (one per occupied 1NN/2NN edge of every vacancy) that share the lattice state, dispatched per step. The key difference is that pylatkmc bins them by integer key instead of pattern-matching them by Process identity.

---

## Runtime data structure

### kmos `avail_sites` (the heart of `local_smart`/`lat_int`)

For `local_smart` and `lat_int`, the entire runtime matcher is one 3D array (`kmos-main/kmos/fortran_src/base.mpy:88–147`):

```fortran
integer, allocatable :: avail_sites(:, :, :)   ! (n_proc, n_site, 2)
integer, allocatable :: nr_of_sites(:)          ! (n_proc)
```

- `avail_sites(p, k, 1)` = the `k`-th enabled site for process `p` (densely packed left).
- `avail_sites(p, s, 2)` = reverse index — where site `s` lives in the packed list for process `p`, or 0 if not enabled.

That redundancy is what makes `add_proc` and `del_proc` **O(1)** (`base.mpy:245–260`):

```
add_proc(p, s):
    nr_of_sites(p) += 1
    avail_sites(p, nr_of_sites(p), 1) = s     ! append
    avail_sites(p, s,              2) = nr_of_sites(p)

del_proc(p, s):
    k    = avail_sites(p, s, 2)
    last = avail_sites(p, nr_of_sites(p), 1)
    avail_sites(p, k,    1) = last            ! swap last into k
    avail_sites(p, last, 2) = k
    nr_of_sites(p) -= 1
```

When a `put_` or `take_` changes a site's species, generated Fortran calls `touchup_<layer>_<coord>` for every stencil coord in range. Each touchup runs the decision tree at that coord and calls `add_proc` / `del_proc`. **No full rebuild ever happens**.

### pylatkmc `AvailEvents` (full rebuild)

`runtime/src/core/avail.h`:

```c
typedef struct {
    Event    *events;       /* [n_vac_max * AVAIL_MAX_EVENTS_PER_VAC], dense */
    double   *cum_rates;    /* parallel running sum */
    int32_t   n_events;
    double    r_tot;
    int32_t   n_vac_max;
} AvailEvents;
```

The generated `avail_rebuild_all` walks every vacancy each step, scans its 1NN and 2NN shells (with per-species counters), keys the rate cube, and appends one Event per occupied edge. `avail_select(av, target, ...)` then binary-searches `cum_rates`.

`O(n_vac × 18)` per step, no incremental updates. At ≤ 100 vacancies on a 22×22×20 slab and ~100 ns/event, this is well under 100 µs/step. Incremental matching is a future M5/M6 candidate; the kmos `add_proc` / `del_proc` pattern is the natural reference implementation.

---

## Codegen: decision trees vs. flat lookup

### kmos `_write_optimal_iftree`

The core codegen function in `kmos-main/kmos/io/__init__.py:2568–2655` builds, for each affected lattice coord, a balanced decision tree across all processes that touch it:

1. Find the most-shared condition coord across processes (the coord that appears in the most process condition lists).
2. Emit `select case(get_species(that_coord))` and partition the process set by required species.
3. Recurse into each branch on the next-most-shared coord.
4. Leaves are `call add_proc(proc_id, site)` (or `del_proc`).

Per-process the codegen also emits `run_proc_<name>` (the execution body), `touchup_<coord>` (called from `put_/take_` for dirty sites), and `nli_<name>` / `nlf_<name>` (initial / final neighbour-list hooks). Site-change → `log N` decision-tree probes across all processes that could match.

### pylatkmc `ratetable_key`

The closest analogue in pylatkmc is the inline `ratetable_key` in the generated `ratetable.h`:

```c
static inline int32_t ratetable_key(const RateTable *rt, const RateKey *k) {
    return
        (int32_t)k->site_class * rt->strides[0]
      + (int32_t)k->direction * rt->strides[1]
      + (int32_t)k->mover_species * rt->strides[2]
      + (int32_t)k->n_vac_nn1 * rt->strides[3]
      // ... etc
    ;
}
```

There's no decision tree — there's an integer-arithmetic key construction and a single load from the mmap'd cube. The price you pay for this simplicity: the cube has to enumerate every possible key tuple at build time (703,125 cells for `ni_fe_cr_v1`), and most cells are filled by fallback tiers rather than direct training data.

The kmos approach scales gracefully when species/conditions multiply (the decision tree just gets deeper); pylatkmc's approach scales gracefully when training data is dense (more axes mean more bins, but lookup cost is constant).

---

## What "the environment" is

### kmos: boolean conjunction of pattern predicates

For a kmos process with

```python
conditions = [(coord=s,            species=empty),
              (coord=s+(1,0,0,_),  species=CO),
              (coord=s+(0,1,0,_),  species=O)]
```

the environment is the single predicate `species(s)==empty ∧ species(s+(1,0,0))==CO ∧ species(s+(0,1,0))==O`. Two processes with overlapping but non-identical conditions get two independent `add_proc` calls. **No bucketing by scalar count, no fallback** — if you didn't declare the process, it does not fire.

Rates live inside each process as a formula string evaluated at parameter-change time. The rate does not depend on the environment except by being attached to a process whose conditions describe that environment.

### pylatkmc: integer tuple into a flat cube

pylatkmc's environment is `(site_class, direction, mover_species, n_vac_nn1, n_Fe_nn1, n_Cr_nn1, n_vac_nn2, n_Fe_nn2, n_Cr_nn2)`. Two events with the same tuple share the same rate (by construction). Cells with no training events fall through a deterministic seven-tier fallback chain documented in [`ARCHITECTURE.md`](ARCHITECTURE.md#rate-cube-builder--seven-tier-fallback-chain).

Compared to kmos:
- Information **lost**: the spatial arrangement of neighbours, the destination site's environment (only the per-edge direction family), the precise identity of which neighbour is which.
- Information **gained** by the bucketing: better statistical pooling. Every event with `n_Cr_nn1 = 1` contributes to the same cell, regardless of which 1NN slot the Cr atom occupies.

Whether that trade-off is right depends on how strongly the rate depends on spatial arrangement. For FCC vacancy diffusion, the experimental answer (and the curated family catalogue's answer) is "scalar counts capture most of it." For surface chemistry with anisotropic adsorbate-adsorbate interactions, kmos's stencil-based view is probably more honest.

---

## Comparison table

| Aspect | kmos (`local_smart`) | kmos (`otf`) | pylatkmc |
|---|---|---|---|
| **Unit of categorization** | individual Process with explicit stencil pattern | individual Process + runtime bystander count | rate-cube cell `(sc, dir, mover, n_vac_*, n_Fe_*, n_Cr_*)` |
| **Species in the key** | yes (every `coord@species`) | yes (strict) + counts (bystander) | yes (mover + per-shell histogram) |
| **Spatial arrangement** | explicit (each offset has a species) | explicit for hard, summarized for soft | none — scalar counts only |
| **Destination-site environment** | yes (via conditions at dest coord) | yes | no (only per-edge direction family) |
| **Neighbour shell depth** | arbitrary (user's stencil) | arbitrary | 1NN + 2NN hard-coded in CSR |
| **Vacancy–vacancy correlation** | yes (multi-site patterns) | yes | no — each vacancy enumerates events independently |
| **Rate storage** | formula string per process | formula string + bystander counts | pre-exponentiated `f32` cube |
| **Runtime cost per step** | O(dirty sites × processes × log-tree) | same + per-event bystander count | O(n_vac × 18) full rebuild |
| **Rebuild frequency** | incremental on site change | incremental | full rebuild every step |
| **Code bloat with more conditions** | 2^N processes (worst case) | linear in bystander set | zero (data table grows) |
| **User-facing declaration** | XML or Python DSL with Process API | same | TOML + axis list + path to curated CSV |
| **Target language** | Fortran 90 + f2py wrapper | same | C11 + MPI, single static binary |

---

## What pylatkmc borrowed from kmos

1. **Spec-driven codegen.** Python project file → specialised native code. Same overall pattern; different schema choice (axes vs. processes).
2. **The `#@ ... @#` preprocessor.** ~50 LOC port of `kmos-main/kmos/utils/__init__.py:1449` into `pylatkmc/pylatkmc/codegen.py`. We use f-string semantics inside `#@` lines (kmos uses `.format()`, but `.format()` doesn't support method calls like `{name.upper()}`). Otherwise the line-rewriter loop is the same shape.
3. **Specialised inner loop per model.** Like kmos's `local_smart`/`lat_int`/`otf` choice baking into the generated Fortran, pylatkmc bakes the axis schema into `ratetable.{h,c}` so the C runtime has zero schema dispatch.
4. **Model-dir-per-binary convention.** `models/<name>/` mirrors kmos's project-per-directory layout. One binary per compiled model; Python codegen + native build are separate steps.

---

## What pylatkmc deliberately did NOT borrow

1. **Pattern-DB / decision-tree matcher.** kmos's `_write_optimal_iftree` (`kmos-main/kmos/io/__init__.py:2568`) is elegant for surface chemistry where the mental model IS "this process fires when this stencil pattern is satisfied." For vacancy diffusion the natural unit is "every occupied neighbour of every vacancy is a candidate hop." Encoding that as kmos Processes would mean one Process per `(direction × shell × species_combo)` — for a Ni-Fe-Cr alloy with 9 axes and `5⁶` count combinations per `(sc, dir, mover)`, that's many thousands of generated Fortran processes. The flat-cube approach handles it as one branch-free expression.
2. **`avail_sites` incremental O(1) add/del.** Big perf win on paper; not yet implemented in pylatkmc. M5/M6 candidate. The current full-rebuild path is ~100 µs/step at 100 vacancies, which is fine for the systems we care about.
3. **OTF runtime rate evaluation.** All rates are pre-exponentiated at build time. Means we can't change `T` or k0 without a rebuild, but it makes the hot path one float load. Acceptable trade since temperature sweeps already require running multiple rate cubes (one per T) for downstream analysis anyway.
4. **`actions` tuple for multi-site events.** Each pylatkmc event is a single-vacancy hop. No concerted motions, no exchanges encoded as multi-atom moves. The training data we get from pyKMC + Analysis is overwhelmingly single-vacancy 1NN hops, and modelling concerted events would require both training-data extensions and event-model extensions. Out of scope for now.
5. **XML project format.** kmos uses XML (or programmatic Python). pylatkmc uses TOML — easier to read, easier to validate via pydantic, no DTD machinery.

---

## What we could still steal later

Three concrete, independent ideas — ranked by cost/benefit if we re-prioritise:

### (a) Incremental matching — biggest perf lever

`avail_rebuild_all()` in the generated `avail.c` rebuilds every event every step. kmos's swap-based O(1) add/del on a densely-packed per-vacancy list is the exact same shape that would work for pylatkmc. The adaptation:

- Keep one packed list per vacancy (or per `(sc, dir)` slab).
- When a hop fires, only two vacancies change: the one that moved, and any vacancy whose 1NN/2NN shell touched the origin or destination.
- `touchup` each of them: recompute counts, delete old events, insert new ones with the swap-last trick.

pylatkmc already has the right data (`vac_list`, `vac_idx_of` in `runtime/src/core/state.h`) to do this. M5 was planned for cutover; M6 would be a natural place to layer this in.

### (b) Bystander-style runtime species counts — alternative path to richer alloys

Instead of widening the cube further (e.g. adding `n_Mn_*` axes for quaternary alloys), borrow kmos's bystander idea: count specific species in specific shells at runtime, fold the count into a rate expression. We'd need an OTF-style runtime rate evaluator inside pylatkmc, but it would buy us the ability to handle continuously-varying compositions without exploding the cube dimensionality.

That's a much bigger lift than (a) and probably only worth it if we genuinely need quaternary alloys or composition gradients.

### (c) Decision-tree codegen — only if we drop the cube

If we ever outgrow the scalar-count key and want multi-site patterns (e.g. "vacancy dimer dissolves differently from isolated vacancy + isolated vacancy"), kmos's `_write_optimal_iftree` is the right algorithm. But this is a **different architecture** — pattern DB at codegen, not a data cube at runtime — and should only be considered if the cube's dimensionality blows up.

---

## File:line pointers

### kmos
- `kmos-main/kmos/utils/__init__.py:1449` — `evaluate_template`, the preprocessor we ported.
- `kmos-main/kmos/io/__init__.py:140-165` — backend selection.
- `kmos-main/kmos/io/__init__.py:2411-2655` — `touchup_*` codegen + `_write_optimal_iftree`.
- `kmos-main/kmos/io/__init__.py:2657-3084` — OTF rate parser (`_parse_otf_rate`, `_otf_get_auxiliary_params`).
- `kmos-main/kmos/fortran_src/base.mpy:88-302` — `avail_sites`, `add_proc`, `del_proc`, `determine_procsite`.
- `kmos-main/kmos/fortran_src/base_otf.f90:200-400` — bystander counters and OTF rate evaluation.
- `kmos-main/kmos/types.py:2024-2256` — `Process`, `Condition`, `Action`, `Bystander`.
- `kmos-main/examples/render_pairwise_interaction.py` and `render_pairwise_interaction_otf.py` — side-by-side comparison of the two strategies on the same physics.

### pylatkmc
- `pylatkmc/pylatkmc/codegen.py` — `evaluate_template` + `generate`.
- `pylatkmc/pylatkmc/spec.py` — `ModelSpec`, `KeyAxis`, `Shell` (pydantic).
- `pylatkmc/pylatkmc/ratebuilder.py` — `build` + the seven-tier fallback chain.
- `pylatkmc/pylatkmc/templates/ratetable.h.tmpl` — the inline `ratetable_key`.
- `pylatkmc/pylatkmc/templates/avail.c.tmpl` — `scan_<shell>` + `avail_rebuild_all`.
- `pylatkmc/runtime/src/core/avail.h` — `AvailEvents` interface.
- `pylatkmc/runtime/src/core/events_base.h` — permanent enums shared across all models.
- `pylatkmc/runtime/src/mpi/replica.c` — model-agnostic ensemble aggregator.

---

## Cross-references

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — internal architecture of pylatkmc (codegen, fallback chain, runtime).
- [`PYKMC_INTEGRATION.md`](PYKMC_INTEGRATION.md) — how the data flow from pyKMC sims becomes a pylatkmc binary.
- [`../README.md`](../README.md) — top-level hub.
- `pylatkmc_m4_species_report.md` (upstream workspace doc) — M4 validation report.
- The earlier draft, `kmos_environment_matching.md` (upstream workspace doc), is now a one-paragraph stub redirecting here.
