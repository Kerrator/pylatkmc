# pylatkmc Architecture

**Audience:** new readers of the pylatkmc codebase, future-self after a context drift, anyone making non-trivial changes.
**Last updated:** 2026-05-06 (v0.2.0 — pattern-DB cutover).

---

## TL;DR — three layers

```
                  ┌─ pylatkmc/ ─────────────────────────────────┐
                  │ Python: ModelSpec + family CSV → proclist.c │
                  │   spec.py         TOML schema + validators  │
                  │   loader.py       .toml → ModelSpec         │
                  │   processes.py    Process / Condition /     │
                  │                   Action / Bystander IR     │
                  │   translator.py   family CSV → list[Process]│
                  │   decision_tree.py list[Process] → C source │
                  │   codegen.py      generate() entry point    │
                  └────────────┬────────────────────────────────┘
                               │ generates
                               ▼
                  ┌─ models/<name>/generated/ ──────────────────┐
                  │ proclist.c                                  │
                  │ proclist.h                                  │
                  └────────────┬────────────────────────────────┘
                               │ compiled with
                               ▼
                  ┌─ runtime/ (static, model-agnostic) ─────────┐
                  │ src/core/                                   │
                  │   lattice / coord_codes      (geometry)     │
                  │   state / state_actions      (mutation)     │
                  │   avail_sites                (BKL index)    │
                  │   active_filter              (active gate)  │
                  │   kmc                        (step loop)    │
                  │   rng                        (splitmix64)   │
                  │ src/io/      initconfig, xyz, pykmc.out     │
                  │ src/mpi/     replica.c (MPI_Gather)         │
                  │ src/main.c                                  │
                  └────────────┬────────────────────────────────┘
                               │ CMake links to
                               ▼
                  build/pylatkmc_<MODEL>     ← per-model binary
```

Three layers, one direction of dependency:

1. **Python codegen** (`pylatkmc/`) — translates the curated FCC family
   catalogue into a list of `Process` descriptors, then emits a single
   per-model `proclist.c` (decision tree + apply functions + rate
   table). Run once per (model, T) pair.
2. **Generated C** (`models/<name>/generated/proclist.{c,h}`) — bundles
   everything model-specific into one compilation unit.
3. **Static C runtime** (`runtime/`) — backbone shared across every
   model. Never regenerated.

Everything model-specific is **baked at codegen time** (Process names,
rate constants, action specifics). The runtime hot loop is a tight
sequence of `active_filter_rescan` → `avail_sites_clear` → per-site
`touchup_a` → `avail_sites_select` → `apply_table[proc]`.

---

## Directory layout

```
pylatkmc/
├── CMakeLists.txt              # ingests one model dir; -DMODEL=<name>
├── README.md                   # hub: quickstart + pointers to this docs/ dir
├── pyproject.toml              # installable pylatkmc Python package
├── pylatkmc/                   # Python codegen package
│   ├── __init__.py             # public API: load, ModelSpec, generate
│   ├── spec.py                 # pydantic ModelSpec
│   ├── loader.py               # TOML → ModelSpec
│   ├── processes.py            # Process / Condition / Action / Bystander
│   ├── translator.py           # family CSV → list[Process]
│   ├── decision_tree.py        # list[Process] → C (M-B emitters)
│   ├── rate_expression.py      # arrhenius_scalar, BoostFit
│   ├── codegen.py              # generate(spec, out_dir) — emits proclist.{c,h}
│   └── cli.py                  # `pylatkmc-gen build / info / processes / clean`
├── runtime/src/                # Static C runtime (model-agnostic)
│   ├── core/                   # the heart of the runtime
│   │   ├── lattice.{h,c}       # immutable lattice + coord_table
│   │   ├── coord_codes.{h,c}   # NeighbourCode enum + canonical deltas
│   │   ├── state.{h,c}         # mutable per-replica species + vac_list
│   │   ├── state_actions.c     # state_apply_actions
│   │   ├── avail_sites.{h,c}   # O(1) swap-last add/del + BKL select
│   │   ├── active_filter.{h,c} # coord-based active-site gate
│   │   ├── kmc.{h,c}           # per-step main loop
│   │   ├── rng.{h,c}           # splitmix64 RNG
│   │   ├── events_base.h       # SP_VACANT, SP_NI, …
│   │   ├── kmcfmt.{h,c}        # mmap-and-validate-magic helper for .kmcinit
│   │   └── json_mini.{h,c}     # tiny JSON header parser
│   ├── io/                     # I/O modules
│   │   ├── config_reader.{h,c} # input.ini parser
│   │   ├── initconfig.{h,c}    # .kmcinit lattice loader
│   │   ├── xyz_writer.{h,c}    # trajectory writer
│   │   └── pykmc_out.{h,c}     # per-step log
│   ├── mpi/
│   │   └── replica.{h,c}       # per-replica context + MPI_Gather aggregator
│   └── main.c                  # binary entry point
├── models/<name>/              # one subdir per compiled model
│   ├── <name>.kmcspec.toml     # the spec
│   ├── generated/              # output of `pylatkmc-gen build`
│   │   ├── proclist.c          # ~5k lines for production
│   │   └── proclist.h          # public symbol declarations
│   └── examples/               # input.ini, .kmcinit fixtures
├── tests/unit_py/              # 162 pytests
├── tools/                      # build_initial_config, compare harnesses
└── docs/                       # this directory
```

---

## The data plane: Process IR

`pylatkmc/processes.py` defines the IR. See
[`PATTERN_DB.md`](PATTERN_DB.md#data-plane-process-ir) for the full
schema. Highlights:

- **`CoordOffset(code: NeighbourCode)`** — names a specific neighbour
  direction relative to the anchor. The runtime resolves it via
  `lat->coord_table[site * N + nc]`.
- **`Process`** — `name + family_id + Ea_eV + rate_constant + conditions
  + actions + bystanders`. Frozen + hashable for golden-file tests.
- **Multi-site events** = `len(actions) >= 2`. The runtime applies them
  atomically.

The IR is consumed by the catalogue translator (`translator.py`),
the decision-tree codegen (`decision_tree.py`), and the build entry
point (`codegen.py:generate`).

---

## The matching plane: decision tree

`pylatkmc/decision_tree.py` is a port of kmos's
[`_write_optimal_iftree`](../../kmos-main/kmos/io/__init__.py#L2568) to
C-emission. Given a list[Process], it greedily finds the most-shared
`CoordOffset` across remaining Conditions, emits a `switch` on that
coord's species, and recurses into per-species branches:

```c
void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {
    switch (st->species[site]) {                      // most-shared coord = NC_ANCHOR
        case SP_VACANT:
            switch (st->species[lat->coord_table[site * N + NC_NN1_PX]]) {
                case SP_NI:
                    avail_sites_add(as, P_surface_1NN_inplane__nv1_0__nn1_px__ni, site);
                    break;
                case SP_FE:
                    avail_sites_add(as, P_surface_1NN_inplane__nv1_0__nn1_px__fe, site);
                    break;
                …
            }
            …
    }
}
```

For ni_fe_cr_v1's 358 Processes, the tree depth is ~7 levels and
`touchup_a` is ~5000 lines.

---

## The execution plane: runtime per-step loop

`runtime/src/core/kmc.c:kmc_step_once`:

```c
int kmc_step_once(KmcContext *ctx,
                  int32_t *out_proc, int32_t *out_site, double *out_dt)
{
    active_filter_rescan(ctx->af, ctx->lat, ctx->st);
    avail_sites_clear(ctx->as);
    int32_t n_active = active_filter_n_active(ctx->af);
    for (int32_t i = 0; i < n_active; ++i) {
        touchup_a(ctx->lat, ctx->st, ctx->as,
                  active_filter_site_at(ctx->af, i));
    }
    avail_sites_refresh_cum_rates(ctx->as);
    double r_tot = avail_sites_r_tot(ctx->as);
    if (r_tot <= 0.0) return -ENODATA;

    double r1, r2;
    rng_next2(ctx->rng, &r1, &r2);
    double dt = -log(r2) / r_tot;
    int32_t proc, site;
    avail_sites_select(ctx->as, r1 * r_tot, &proc, &site);
    apply_event(ctx, proc, site);                // dispatches via apply_table[proc]

    ctx->st->time_s += dt;
    ctx->st->step   += 1;
    /* … out params … */
    return 0;
}
```

### Runtime data structures

- **`Lattice`** — immutable per-model geometry. Loaded from .kmcinit.
  Carries `positions`, `nn1`/`nn2` CSR adjacency, and the per-site
  `coord_table` (built once at startup by `lattice_build_coord_table`).
- **`State`** — mutable per-replica state. Triple: `species[]`,
  `vac_list[]`, `vac_idx_of[]`. Plus `unwrapped_xyz[]` for MSD.
- **`AvailSites`** — per-step event-availability index. Dual-index
  `site_at[proc][k]` + `slot_of[proc][site]` for O(1) add/del. Plus
  `rates[proc]` (set once at startup) and `cum_rates[proc]` (refreshed
  per step).
- **`ActiveFilter`** — bitmap + packed list of "sites worth running
  touchup at". Static mask (geometry-derived) + dynamic mask (vacancies
  and their 1NN).
- **`Rng`** — splitmix64; seeded per-replica from `(base_seed, rank)`.

### MPI ensemble

`runtime/src/mpi/replica.c` runs one independent simulation per MPI
rank. After `kmc_run` returns, rank 0 collects each replica's
`ReplicaStats` via `MPI_Gather` and writes `aggregate_summary.json`
to `output_root/`.

---

## Model spec (TOML)

A `.kmcspec.toml` declares:

- `name`, `lattice = "fcc"`
- `species = ["Vacant", "Ni", "Fe", "Cr"]` — first MUST be Vacant
- `[shells]` — neighbour shells (1NN, 2NN, …) by cutoff multiplier
- `[rate_data]` — paths to the catalogue CSVs and physics parameters
  (T, k0)

Example: [`models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml`](../models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml).

The TOML schema is enforced by Pydantic in `pylatkmc/spec.py`.

---

## Build

```bash
pylatkmc-gen build models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
# Pipeline:
#   ModelSpec → load_family_rate_table → translate_all → list[Process]
#                                                          │
#   compile_decision_tree                                  │
#   emit_process_enum                                      │
#   emit_rate_table                                        ▼
#   emit_apply_actions                              proclist.{c,h}

cmake -B build -DMODEL=ni_fe_cr_v1
cmake --build build -j 4
# → build/pylatkmc_ni_fe_cr_v1
```

CMake `file(GLOB)` picks up:
- All `runtime/src/{core,io,mpi}/*.c` (the static backbone)
- `models/<MODEL>/generated/*.c` (proclist.c)
- Compiles them into `pylatkmc_lib` (static archive)
- Links `runtime/src/main.c` against it → final binary

---

## Run

```bash
cd models/ni_fe_cr_v1/examples
mpirun -n 4 ../../../build/pylatkmc_ni_fe_cr_v1 input.ini
cat output/aggregate_summary.json
```

`input.ini` declares step caps, the .kmcinit path, the output root,
T, and the RNG seed. See
[`runtime/src/io/config_reader.h`](../runtime/src/io/config_reader.h)
for the field set.

---

## Validation status & known limitations

- ✅ **End-to-end pattern-DB pipeline.** Smoke run on ni_fe_cr_v1
  (8×8×3 slab, 1 surface vacancy, T=500 K, 100k steps × 2 ranks):
  `mean_msd_A2 = 6.79e5 Å²` vs cube baseline `7.79e5 Å²` — within 13%.
- ✅ **162 unit tests passing**, including ctypes tests against the
  real `Lattice` / `State` / `AvailSites` types and a `cc -Werror`
  compile gate on the generated proclist.
- ⚠️ **Single-vacancy MSD only.** Multi-vacancy concerted events
  emit a one-time stderr warning and skip MSD updates (slot identity
  is approximate when more than one vacancy is involved). Per-vacancy
  ID-based unwrapped_xyz is a v0.3 candidate.
- ⚠️ **Per-bucket rate aggregation.** Each `(family, bucket)` emits one
  Process per direction with a shared bucket-mean rate. If intra-bucket
  Ea scatter is wide (>0.05 eV with ≥10 events), `pylatkmc-gen
  processes` emits a warning. Per-arrangement Processes (one per
  catalogue row instead of per bucket) are a v0.3 candidate.
- ⚠️ **PBC-aliased `±z` 2NN codes.** In thin slabs, `NC_NN2_PZ` and
  `NC_NN2_MZ` may resolve to the same neighbour through the z PBC.
  The runtime accepts this; the same physical event may be
  enumerated under two Process IDs. Not corrected in v0.2.

---

## Where to read next

- [`PATTERN_DB.md`](PATTERN_DB.md) — full architectural reference.
- [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) — worked example.
- [`KMOS_COMPARISON.md`](KMOS_COMPARISON.md) — what we ported, what's
  still kmos-different.
- [`PYKMC_INTEGRATION.md`](PYKMC_INTEGRATION.md) — interaction with the
  upstream pyKMC pipeline.
