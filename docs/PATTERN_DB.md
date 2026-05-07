# PATTERN_DB.md — pylatkmc v0.2 architecture

This document describes the pattern-DB pipeline that replaced the v0.1
9-axis rate cube. Read it after the [README quickstart](../README.md#quickstart)
and before [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md)'s worked example.

## Why pattern-DB instead of a rate cube

The v0.1 cube had two structural limits that made it hard to extend:

1. **Scalar counts lose spatial pattern.** The cube cell `n_vac_nn1=2`
   was the same for two vacancies at neighbouring sites and two at
   opposite corners. Real saddle barriers depend on the *arrangement*,
   and the curated FCC family catalogue already records this.

2. **Single-atom swap can't represent multi-site moves.** Cooperative
   1NN hops (2 atoms) and triple hops (3 atoms) appear in the
   catalogue with their own Ea distributions, but the cube runtime's
   `apply_event` only ever swapped one `(vac_origin, vac_dest)` pair.

The pattern-DB approach borrows kmos's idea: each kinetic mechanism
becomes a `Process` with explicit `Conditions` (species at specific
neighbour offsets) and `Actions` (atomic multi-site state changes).
The runtime maintains a per-Process `avail_sites` index of currently-
eligible anchor sites, BKL-selects from the cumulative rate, and applies
the chosen Process's actions atomically.

## End-to-end pipeline

```
                                                     ┌─────────────────────────┐
                                                     │  classified_events_with │
                                                     │  _families.csv          │
                                                     │  (curated upstream)     │
                                                     └────────────┬────────────┘
                                                                  │ aggregated by
                                                                  ▼ family + bucket
                                                     ┌─────────────────────────┐
                                                     │  rate_lookup_table_     │
                                                     │  family.csv             │
                                                     │  (rate_data.family_table│
                                                     │   in the spec)          │
                                                     └────────────┬────────────┘
                                                                  │
              ┌─── pylatkmc-gen build ────────────────────────────┘
              │
              ▼ Python
   ┌──────────────────────────────────┐    ┌──────────────────────────────────┐
   │ pylatkmc.translator              │    │ pylatkmc.processes               │
   │  load_family_rate_table          │───▶│  Process(name, family_id, Ea_eV, │
   │  translate_all                   │    │    rate_constant, conditions=…,  │
   │   per-family direction tables    │    │    actions=…, bystanders=…)      │
   │   (NeighbourCode-based)          │    │                                  │
   └──────────────────────────────────┘    └─────────────┬────────────────────┘
                                                         │ list[Process]
                                                         ▼
   ┌──────────────────────────────────┐    ┌──────────────────────────────────┐
   │ pylatkmc.codegen                 │◀───┤ pylatkmc.decision_tree           │
   │  generate(spec, out_dir)         │    │  compile_decision_tree           │
   │  → writes proclist.{c,h}         │    │  emit_process_enum               │
   │                                  │    │  emit_rate_table                 │
   │                                  │    │  emit_apply_actions              │
   └─────────────┬────────────────────┘    └──────────────────────────────────┘
                 │ generated/proclist.{c,h}
                 ▼
   ┌──────────────────────────────────┐
   │  CMake → build/pylatkmc_<n>      │
   │  (links generated proclist.c     │
   │   against runtime/src/)          │
   └─────────────┬────────────────────┘
                 │
                 ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │  C runtime: per replica, per step                                      │
   │                                                                        │
   │   active_filter_rescan(af, lat, st)                                    │
   │   avail_sites_clear(as)                                                │
   │   for s in active_filter sites:                                        │
   │       touchup_a(lat, st, as, s)        ← generated decision tree       │
   │   avail_sites_refresh_cum_rates(as)                                    │
   │   r1, r2 ← rng                                                         │
   │   dt = -log(r2) / r_tot                                                │
   │   target = r1 * r_tot                                                  │
   │   avail_sites_select(as, target, &proc, &site)                         │
   │   apply_table[proc](st, lat, site)     ← generated apply function      │
   │       └─→ state_apply_actions(st, …, SP_VACANT)  (atomic multi-site)   │
   │   update unwrapped_xyz for the moved vacancy (single-hop heuristic)    │
   └────────────────────────────────────────────────────────────────────────┘
```

## Data plane: Process IR

`pylatkmc/processes.py` defines five Pydantic models, all frozen and
hashable so golden-file tests can compare lists deterministically:

```python
class CoordOffset(BaseModel):
    """One neighbour direction relative to the anchor.

    `code` is a NeighbourCode name (e.g. "NC_NN1_PX", "NC_NN1_UP_PP",
    "NC_NN2_DIAG_PP", "NC_ANCHOR"). The runtime resolves it via
    `lattice->coord_table[site * N_NEIGHBOUR_CODES + nc]`."""
    code: str    # one of NEIGHBOUR_CODES

class Condition(BaseModel):
    """Per-coord species check (HARD gate)."""
    coord: CoordOffset
    species: str                 # "Vacant", "Ni", "Fe", "Cr"

class Action(BaseModel):
    coord: CoordOffset
    before: str                  # required pre-state
    after: str                   # post-state set when fired

class ShellCondition(BaseModel):  # NEW in v0.3
    """Bucket-key gate (HARD): the site at `coord` must have EXACTLY
    `count` sites in its `shell` whose species equals `species`.
    Threads catalogue bucketing (e.g. nv1=4_nv2=1) through to runtime
    so a Process discovered in a 4-vacant-1NN context can't fire on
    sites without that local environment."""
    coord: CoordOffset
    shell: Literal["1nn", "2nn"]
    species: str
    count: int                   # >= 0

class Bystander(BaseModel):       # SOFT rate modulator (v0.4 stub today)
    coord: CoordOffset
    allowed_species: tuple[str, ...]
    flag: str                    # e.g. "1nn", "2nn"

class Process(BaseModel):
    name: str                    # valid C identifier
    family_id: str               # provenance — back-link to catalogue family
    Ea_eV: float
    rate_constant: float | str   # scalar (baked at codegen) or expression with Bystanders
    conditions: tuple[Condition, ...]
    actions: tuple[Action, ...]
    shell_conditions: tuple[ShellCondition, ...] = ()  # v0.3
    bystanders: tuple[Bystander, ...] = ()
```

**Multi-site processes** have `len(actions) >= 2`. The runtime applies all
actions in one transactional update via
[`state_apply_actions`](#state_apply_actions).

### NeighbourCode

Why not integer `(di, dj, dk)` offsets like kmos's
`Coord(name, offset, layer)`? For an FCC (100) slab, layer 0 sites sit
at conventional cubic coordinates `(i, j, 0)` while layer 1 sites are
shifted by `(½, ½, ½)`. There's no integer basis where in-plane axial
1NN AND face-shifted cross-layer 1NN are both representable with clean
integer triples. kmos solves this with named-sites-within-cell;
pylatkmc v0.2 solves it with a flat enum:

```c
typedef enum {
    NC_ANCHOR,
    NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY,           /* axial 1NN */
    NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM,
    NC_NN1_UP_PP,   NC_NN1_UP_PM,   NC_NN1_UP_MP,   NC_NN1_UP_MM,
    NC_NN2_DIAG_PP, NC_NN2_DIAG_PM, NC_NN2_DIAG_MP, NC_NN2_DIAG_MM,
    NC_NN2_PX, NC_NN2_MX, NC_NN2_PY, NC_NN2_MY, NC_NN2_PZ, NC_NN2_MZ,
    N_NEIGHBOUR_CODES
} NeighbourCode;
```

(See [`runtime/src/core/coord_codes.h`](../runtime/src/core/coord_codes.h)
for the canonical Cartesian delta of each code, in units of `nn_d`.)

At lattice load, `lattice_build_coord_table(lat)` walks each site's
1NN/2NN CSR adjacency, computes the PBC-wrapped Cartesian delta for
each edge, and matches it against `NEIGHBOUR_CODE_DELTAS[]` within a
small tolerance. The result is a flat lookup table

```
coord_table[site * N_NEIGHBOUR_CODES + nc]
    = absolute neighbour site index, or -1 if absent
```

A surface site has `coord_table[site * N + NC_NN1_UP_*] == -1` (no
layer above); a fully-bulk site has all 12 1NN codes populated.

## Translator: catalogue → list[Process]

`pylatkmc/translator.py` reads `rate_lookup_table_family.csv` and emits
one Process per `(family, bucket, direction)` triple. Each family has
a direction table:

```python
SURFACE_1NN_INPLANE_DIRS = (NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY)
BULK_1NN_DIRS = (
    NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY,                 # in-plane
    NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM,     # cross-layer up
    NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM,  # cross-layer down
)
SURFACE_2NN_DIRS = (NC_NN2_DIAG_PP, NC_NN2_DIAG_PM, NC_NN2_DIAG_MP, NC_NN2_DIAG_MM)
BULK_2NN_DIRS   = (NC_NN2_PX, NC_NN2_MX, NC_NN2_PY, NC_NN2_MY, NC_NN2_PZ, NC_NN2_MZ)
INTERLAYER_1NN_DIRS_UP   = (NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM)
INTERLAYER_1NN_DIRS_DOWN = (NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM)
```

Production catalogue (`rate_lookup_table_family.csv`, 56 family-bucket
rows × 9 fit-barrier families) → 358 Processes for ni_fe_cr_v1 at T=500K.

## Codegen: list[Process] → proclist.c

`pylatkmc/decision_tree.py` (port of kmos's `_write_optimal_iftree`)
greedily partitions the Process set on the most-shared `CoordOffset`,
emitting nested `switch (st->species[lat->coord_table[site * N + nc]]) { case SP_NI: … }`
trees. Each leaf calls `avail_sites_add(as, P_<name>, site)`.

`emit_apply_actions` produces one C function per Process:

```c
static HopOutcome apply_actions_<name>(State *st, const Lattice *lat, int site) {
    StateAction acts[K] = {
        { .site = lat->coord_table[site * N + NC_…], .before = SP_…, .after = SP_… },
        …
    };
    state_apply_actions(st, acts, K, SP_VACANT);
    return (HopOutcome){ .v_origin = …, .v_dest = … };
}

static const ApplyFn apply_table[N_PROCS] = {
    [P_<name>] = apply_actions_<name>,
    …
};
```

`emit_rate_table` produces a `RateConst` array indexed by `P_<name>`,
with `rate` baked at codegen time as
`k0_Hz * exp(-Ea_eV / (kB * T_K))`.

`compile_decision_tree(processes, "touchup_a")` is the per-anchor entry
point. The runtime calls it once per active site per step.

### Leaf-level shell-condition gating (v0.3)

When a leaf has Processes that share Conditions but differ in their
`shell_conditions`, the codegen emits a count-loop block instead of
bare `avail_sites_add` calls. Every unique `(coord, shell, species)`
triple shared across leaf Processes gets a single CSR-walk that counts
matching neighbours of `coord`'s mover; each Process gets an
`if (n1 == k1 && n2 == k2) avail_sites_add(...)` gate.

Example for `surface_1nn_inplane / nv1=4_nv2=1` and
`nv1=0_nv2=0` Processes that both reach the same anchor leaf:

```c
case SP_NI: {  /* species at NC_NN1_PX = mover */
    /* shell-count loops for bucket-key gating */
    int nr_1nn_vacant_at_nn1_px = -1;  /* sentinel: stub-site mover → no match */
    {
        int _m = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX];
        if (_m >= 0 && _m < lat->n_sites) {
            nr_1nn_vacant_at_nn1_px = 0;
            for (int _i = lat->nn1_offsets[_m]; _i < lat->nn1_offsets[_m + 1]; ++_i) {
                if (st->species[lat->nn1_indices[_i]] == SP_VACANT)
                    nr_1nn_vacant_at_nn1_px++;
            }
        }
    }
    /* (similar block for nr_2nn_vacant_at_nn1_px) */

    if (nr_1nn_vacant_at_nn1_px == 4 && nr_2nn_vacant_at_nn1_px == 1)
        avail_sites_add(as, P_surface_1nn_inplane__nv1_4_nv2_1__nn1_px__ni, site);
    if (nr_1nn_vacant_at_nn1_px == 0 && nr_2nn_vacant_at_nn1_px == 0)
        avail_sites_add(as, P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni, site);
    /* … one if per bucket-key Process … */
    break;
}
```

This makes each Process fire ONLY when the catalogue bucket's
discovery context is actually present in the lattice. Without
ShellCondition gating, `surface_1nn_inplane / nv1=4_nv2=1` would fire
at every (vacant, atom-neighbour) pair on a 1-vacancy slab — even
though that bucket was discovered in pyKMC simulations with ≥4
vacancies in the mover's local environment.

The full bundled `proclist.c` for ni_fe_cr_v1 grows from ~5000 (v0.2)
to ~5500 (v0.3) lines from the count-loop emission; still compiles in
~5s with `-O2 -Wall -Wextra -Werror`.

## Runtime: per-step pipeline

The C step loop is in [`runtime/src/core/kmc.c:kmc_step_once`](../runtime/src/core/kmc.c).
Per step:

1. **Active-site rescan** (`active_filter_rescan`). A site is "active"
   iff vacant, has a vacant 1NN, or has `nn1_degree < 12`. Bulk atoms
   with full coordination and no nearby vacancy can never have a
   Process match — skipping them saves the touchup cost.

2. **Clear the avail_sites index** (`avail_sites_clear`). Wipes all
   `(proc, site)` enrolments from the previous step. Per-proc rate
   constants stay (they're set once at startup).

3. **Touchup at every active site.** The generated `touchup_a(lat,
   st, as, site)` walks the decision tree and calls `avail_sites_add(as,
   P_<name>, site)` for every eligible Process.

4. **Refresh cum_rates** (`avail_sites_refresh_cum_rates`). Recomputes
   `cum_rates[p] = Σ_{j≤p} rates[j] · n_sites_per_proc[j]`.

5. **BKL select**:
   ```
   r1, r2 ← RNG
   dt = -log(r2) / r_tot
   target = r1 * r_tot
   avail_sites_select(as, target, &proc, &site)
       └── binary-search for proc s.t. cum_rates[proc-1] < target ≤ cum_rates[proc]
       └── pick uniform slot k = (target - cum_rates[proc-1]) / rates[proc]
       └── return site_at[proc][k]
   ```

6. **Apply the chosen Process** (`apply_table[proc](st, lat, site)`).
   Returns `HopOutcome { v_origin, v_dest }`.

7. **MSD bookkeeping**: when both `v_origin` and `v_dest` are valid
   (single-vacancy hop pattern: exactly one V→A action and one A→V
   action), accumulate the min-image displacement into
   `unwrapped_xyz[v_idx]` at the new vacancy slot. Multi-vacancy
   concerted events leave `v_origin = v_dest = -1` and the runtime
   skips the MSD update with a one-time stderr warning.

### avail_sites — O(1) book-keeping

`avail_sites_add(as, p, s)` and `avail_sites_del(as, p, s)` are O(1)
swap-last operations on the dual-index pair:

```c
site_at [proc * n_sites + k]    // dense per-proc list, k ∈ [0, n_sites_per_proc[proc])
slot_of[proc * n_sites + site]  // reverse map: slot k or -1
```

Add: `k = n[p]++; site_at[k] = s; slot_of[s] = k;`
Del: take the entry's slot `k`, swap in the last entry, decrement.

Direct port of kmos's Fortran `avail_sites(proc, k, switch)` array.
Memory: ~12 MB for (n_procs=358, n_sites=4096); fine for v0.2.

### state_apply_actions — atomic multi-site mutation

`state_apply_actions(st, StateAction*, n, vacant_species)` validates
every action's `before` against the current `st->species[]`, rejects
duplicate sites, checks `n_vac_max` overflow, then mutates `species[]`
and updates `vac_list[]` / `vac_idx_of[]` (removals before additions to
avoid transient overflow when n_vac_max == 1). Returns 0 on success or
-EINVAL with no mutation on validation failure.

Source: [`runtime/src/core/state_actions.c`](../runtime/src/core/state_actions.c).

### active_filter — coord-based gate

`active_filter_compute_static(af, lat)` precomputes a bitmap of
geometry-derived active sites (anywhere `nn1_degree < bulk_threshold`).
`active_filter_rescan(af, lat, st)` resets the dynamic part to that
static mask, then marks every vacancy and every 1NN of vacancy.
O(n_vac × 12 + n_static_sites) per step.

For the production 8×8×3 slab with one surface vacancy, this gives
~13–20 active sites instead of all 192 — touchup cost drops by an
order of magnitude.

## Files at a glance

| Concern | Source |
|---|---|
| Process IR | `pylatkmc/processes.py` |
| Catalogue translator | `pylatkmc/translator.py` |
| Codegen entry | `pylatkmc/codegen.py:generate` |
| Decision tree | `pylatkmc/decision_tree.py` |
| Direction codes (Python) | `pylatkmc/processes.py:NEIGHBOUR_CODES` |
| Direction codes (C) | `runtime/src/core/coord_codes.h` |
| Lookup table builder | `runtime/src/core/lattice.c:lattice_build_coord_table` |
| Step loop | `runtime/src/core/kmc.c:kmc_step_once` |
| Event book-keeping | `runtime/src/core/avail_sites.{h,c}` |
| Active-site gate | `runtime/src/core/active_filter.{h,c}` |
| Multi-site apply | `runtime/src/core/state_actions.c` |
| Runtime entry / startup | `runtime/src/mpi/replica.c:replica_run` |

## Validation

Smoke run on `ni_fe_cr_v1` (8×8×3 slab, 1 surface vacancy, T=500 K,
100k steps × 2 MPI ranks):

```
mean_msd_A2 = 6.79e5 Å²    (cube baseline 7.79e5 Å² — within 13%)
n_procs = 358
total_time_s ≈ 4.0e-08
all 162 unit tests pass
```

Per-step pykmc.out columns (v0.2 schema):

```
# step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site
100  3.91e-11  1.57e-13  1  2.17e+12  1.38e+10  0.2839  101  44
…
```

`proc_id` is the integer index from the generated
`enum { P_<name>, ..., N_PROCS }` in proclist.c — cross-reference to
map back to a Process name.

## See also

- [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) — worked example: one
  `surface_1NN_inplane` Ni hop traced from CSV row to fired event.
- [`KMOS_COMPARISON.md`](KMOS_COMPARISON.md) — what we ported from
  kmos and what's still different.
- [`PYKMC_INTEGRATION.md`](PYKMC_INTEGRATION.md) — interaction with the
  curated catalogue and the upstream pyKMC pipeline.
