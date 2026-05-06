# pylatkmc ↔ pyKMC Integration

**Audience:** anyone who wants to take pyKMC simulation outputs and turn them into a pylatkmc model that can be compared against pyKMC, or anyone authoring a new pylatkmc model from scratch.

> **Critical: rate-cube preprocessing.** The upstream classification
> pipeline can produce an `n_vac_nn1_initial` column that is a
> coordination-shortfall proxy (`max(0, 12 - coord_mover)`), not a
> true vacancy count. Surface atoms (coord=8) always read `nv1=4` in
> that case. Combined with 1-axis-only bucketing of the
> `*_1NN_inplane` families, this can cause cube cells to undershoot
> Ea by ~0.115 eV (→ ~14× rate inflation at 500 K). Fix: run the
> upstream `fix_catalogue_nvac.py` corrector after any catalogue
> rebuild, before `pylatkmc-gen rate`. The `families.py` registry
> upstream uses 2-axis `(nv1, nv2)` bucketing for `surface_1NN_inplane`,
> `subsurface_1NN_inplane`, and `bulk_1NN_inplane`;
> `pylatkmc.ratebuilder` parses both 1-axis (`nv1=N`) and 2-axis
> (`nv1=N_nv2=M`) bucket IDs and synthesises a 1-axis "any-nv2"
> event-weighted fallback per nv1. A healthy build shows **0 tier-7
> cells** filled in `pylatkmc-gen provenance`.

---

## The big picture

```
   pyKMC (off-lattice)         apps/PyKMC_Analysis/              pylatkmc/
   ──────────────────             ─────────                      ───────
   ┌──────────────┐  trajkmc.xyz  ┌──────────────────┐          ┌─────────────────┐
   │  pyKMC sim   │──────────────▶│ classify_lattice │          │ pylatkmc   │
   │  (per system)│  pykmc.out    │ _events.ipynb    │          │ .ratebuilder    │
   │              │  pykmc.log    │                  │          │                 │
   │              │  reference_   │                  │          │ + .codegen      │
   │              │  table.pickle │                  │          │                 │
   └──────────────┘  basin_*      └────────┬─────────┘          └────────┬────────┘
                     .pickle               │                             │
                                           │ classified_events_          │ generates
                                           │ _with_families.csv          │
                                           ▼                             ▼
                                  ┌──────────────────┐          ┌─────────────────┐
                                  │ rate_lookup_     │          │ models/<n>/     │
                                  │ table_family.csv │  ◀───┐   │ generated/*.[ch]│
                                  │ + classified_*   │      │   │ + <n>.kmcrt     │
                                  │ + scalar legacy  │──────┘   └────────┬────────┘
                                  └──────────────────┘ consumed by       │
                                                       ratebuilder       │ compiled
                                                                          ▼
                                                                 ┌─────────────────┐
                                                                 │ build/pylatkmc_<n>│
                                                                 └─────────────────┘
```

Three handoffs:

1. **pyKMC → Analysis.** Each completed pyKMC run dir holds the trajectory and event catalogue. The Analysis pipeline (`apps/PyKMC_Analysis/Analysis/classify_lattice_events.ipynb` + `lattice_map_events.py` + `families.py`) classifies every event into one of the 14 curated FCC families and tags it with site class, direction family, motif family, per-shell species histograms.
2. **Analysis → pylatkmc ratebuilder.** `pylatkmc.ratebuilder.build` reads `classified_events_with_families.csv` and aggregates barriers by the spec's axis tuple. Optional fallbacks consume `rate_lookup_table_family.csv` and the legacy scalar `rate_lookup_table.csv`.
3. **pylatkmc codegen + ratebuilder → binary.** `pylatkmc.codegen.generate` turns the spec into specialised C; `ratebuilder.build` produces the matching `.kmcrt`. CMake links the static runtime + the generated C → one binary per model.

---

## Stage 1 — what pyKMC produces

For one completed pyKMC run dir, e.g.

```
Data/Research/Ni_Slab_Alloys/NiCr_Ni95_Cr05_T500_1vac_full/
├── trajkmc.xyz             # ASE extended XYZ; one frame per KMC step + initial
├── pykmc.out               # step log: step, time, dt, Ea, rate, energy
├── pykmc.log               # narrative log; basin entry/exit, step-N successes
├── input.in                # pyKMC config (T, basin settings, potential)
├── initial_config.xyz      # written at startup; pylatkmc reads it for slab dims
├── reference_table.pickle  # event catalogue (pandas DataFrame)
├── basin_connectivity_*.pickle   # one per basin super-event
├── analyse_trajectory.ipynb       # filled-in template (run by Analysis pipeline)
└── analysis/
    └── summary.json        # ⚐ what pylatkmc's compare scripts read
```

The four files pylatkmc consumes downstream are:
- **`analysis/summary.json`** — for the pylatkmc comparison harnesses. Carries `temperature`, `n_vacancies`, `n_atoms`, `total_sim_time`, `msd_final[]`, `species[]`, `barrier_min/max`, basin counts, etc.
- **`trajkmc.xyz`** — frame 0 only, for inferring the slab dimensions (Lx, Ly, n_sites) when pylatkmc needs to build a matching `.kmcinit`.
- **`reference_table.pickle`** — read by the Analysis classification pipeline (not by pylatkmc directly).
- **`pykmc.out` and `basin_connectivity_*.pickle`** — read by Analysis Part 2/4 to build the per-event catalogue.

Documentation for the inputs above lives in `apps/PyKMC_Analysis/Analysis/AGENT.md`. That doc is the source of truth for "what does a pyKMC run dir look like and what do its files mean?"

---

## Stage 2 — Analysis classification

`apps/PyKMC_Analysis/Analysis/classify_lattice_events.ipynb`, driven by `apps/PyKMC_Analysis/Analysis/lattice_map_events.py`, takes a configured list of pyKMC run dirs and produces:

| File | What it carries | Consumer |
|---|---|---|
| `apps/PyKMC_Analysis/Analysis/lattice_event_classification/classified_events.csv` | one row per pyKMC event with motif/site_class/direction labels (no curated family yet) | `family_assignment.py` |
| `classified_events_with_families.csv` | adds `family_id`, `family_bucket_id`, `assignment_status` | **pylatkmc ratebuilder (primary input)** |
| `rate_lookup_table.csv` | scalar legacy table, keyed only by `n_vacant_inplane_nn`, surface `<110>` only | pylatkmc ratebuilder (tier-7 fallback) |
| `rate_lookup_table_family.csv` | event-weighted barrier per `(family_id, family_bucket_id)` | pylatkmc ratebuilder (tier-6 fallback) |
| `rate_lookup_table_3d_master.csv`, `rate_lookup_table_3d_catalogue.csv` | step-log and catalogue-aggregated 3D tables | research / future-`latkmc_3d.py`; not currently consumed by pylatkmc |

The columns in `classified_events_with_families.csv` that pylatkmc actually reads (see `pylatkmc/ratebuilder.py:_prepare_dataframe`):

| Column | Used for |
|---|---|
| `assignment_status` | filter to `"accepted"` rows only |
| `site_class_3d` | maps to integer `_sc` via `CLASS_MAP` |
| `direction_family_3d` | maps to `_dir` via `DIR_MAP` |
| `mover_species_ml` | maps to `_mover` (Ni/Fe/Cr → 0/1/2) |
| `n_vac_nn1_initial` | source for `_n_vac_nn1` axis (⚠ see caveat below) |
| `n_vac_nn2_initial` | source for `_n_vac_nn2` axis (May 2026+; previously derived as `6 − sum(nn2_count_*)`) |
| `nn1_count_Ni`, `nn1_count_Fe`, `nn1_count_Cr` | source for `_n_<elem>_nn1` axes |
| `nn2_count_Ni`, `nn2_count_Fe`, `nn2_count_Cr` | source for `_n_<elem>_nn2` axes |
| `family_id`, `family_bucket_id` | tier-6 family-bucket fallback (1-axis or 2-axis) |
| `energy_barrier` | aggregated as event-weighted mean → Arrhenius rate |

Notes on data quality (see also `pylatkmc_m4_species_report.md` (upstream workspace doc) and the May 2026 diagnosis `pylatkmc_msd_diagnosis.md` (upstream workspace doc)):

- ⚠ **`n_vac_nn1_initial` and `n_vac_nn2_initial` columns require post-processing.** The Analysis pipeline's `04b_ml_descriptors.py` runs with `COMPUTE_LATTICE_ADJACENCY = False` by default (the True path is hours per sim × tens of sims). With the flag off, `n_vac_nn1` is a coordination-shortfall proxy (`max(0, 12 − coord_mover)`) — surface atoms always read `nv1=4` regardless of true vacancy count. **You must run `Analysis/tools/fix_catalogue_nvac.py` after every catalogue rebuild, before `pylatkmc-gen rate`,** to substitute the layer-aware formula (`expected_coord = 8` surface, `12` bulk) and re-derive `family_bucket_id`. The tool runs in ~30 seconds and also generates `n_vac_nn2_initial` from `nn2_count_*` columns and the layer-aware 2NN expected count (5 surface, 6 bulk).
- The `nn2` shell size is hard-coded as 6 in `ratebuilder.py:_NN2_SHELL_SIZE`. This is the bulk-interior FCC count; surface atoms with shorter physical 2NN shells (5) are corrected by `fix_catalogue_nvac.py`'s layer-aware path.
- **Two-axis bucket IDs (May 2026+).** For `surface_1NN_inplane`, `subsurface_1NN_inplane`, `bulk_1NN_inplane` families, `family_bucket_id` is `nv1=N_nv2=M` (parsed by `_load_family_bucket_barriers` into `(int, int)` keys). Other families remain 1-axis (`nv1=N`). The ratebuilder also synthesises a 1-axis "any-nv2" event-weighted fallback per nv1 (stored at key `(nv1, -1)`) so cells with no exact 2-axis hit can fall back gracefully without going to tier 7.
- As of M4, **the catalogue contains 100Ni events only.** The 62 NiFe/NiCr sim dirs in `Data/Research/Ni_Slab_Alloys/` were not ingested. Until they are, every event has `mover_species_ml = "Ni"` and `nn1_count_{Fe,Cr} = 0`. The species axes in the cube can still be populated by tier-2/5/6 fallbacks, but tier-1 (direct aggregation) covers only `n_Fe = n_Cr = 0` cells. Plan to fix in M4b — see the M4 report.

> **Parallel experimental pipeline.** The same curated CSV is the input to a second, experimental research pipeline at `apps/PyKMC_Analysis/Analysis/kmos_export/` which translates the family catalogue into kmos OTF Process descriptors instead of a flat rate cube. Goal: unlock kmos as a third reference engine and support multi-site `actions` for concerted events that pylatkmc's cube cannot represent. Not used by pylatkmc's runtime; see `apps/PyKMC_Analysis/Analysis/AGENT.md` for the API and the research plan at `~/.claude/plans/i-am-looking-to-binary-haven.md` for status.

---

## Stage 3 — pylatkmc ratebuilder

`pylatkmc.ratebuilder.build()` is the single entry point that turns a spec + a curated CSV into a `.kmcrt` binary. The seven-tier fallback chain is documented in detail in [`ARCHITECTURE.md`](ARCHITECTURE.md#rate-cube-builder--seven-tier-fallback-chain); here we focus on the **physical interpretation** of each tier from the pyKMC side.

| Tier | Physical interpretation | Confidence |
|---|---|---|
| 1 — direct | "We have ≥ 1 pyKMC event whose key tuple matches this cell. Use the event-count-weighted mean Ea." | Highest. Real data, real environment. |
| 2 — element drop | "We have data at this `(sc, dir, mover, n_vac_nn1, n_vac_nn2)` but not at this specific alloy-element-count combination. Borrow from the no-Cr-or-Fe variant." | Good when species effects are weak. Suspect for strong solute trapping. |
| 5 — cross-class | "No data at this site_class for this `(dir, ...)` tuple, but the donor class (subsurface ↔ bulk_like) has it. Geometry's similar enough." | Good for bulk-like ↔ subsurface (both fully coordinated). Weaker for surface ↔ subsurface (different coordination). |
| 6 — family bucket | "Borrow a barrier from a curated family that fits this `(sc, dir)` and a matching mover-perspective vacancy bucket." Tries 2-axis `(mover_nv1, mover_nv2)` first, then falls back to 1-axis "any nv2" event-weighted per nv1. | Reasonable; honest about what bucket is available. Two-axis lookup separates isolated vacancy environments from clustered ones — see May 2026 fix. |
| 7 — scalar legacy | "We have a 1D barrier-vs-`n_vac` table for `<110>` surface hops. Best last-resort for that direction." | **Now usually 0 cells filled** — the May 2026 2-axis tier-6 catches what tier 7 used to cover. If `pylatkmc-gen provenance` shows tier-7 firing on `surface_1NN_inplane` cells, it's a sign that `n_vac_nn1`/`n_vac_nn2` are still the broken coordination-shortfall proxies (run `fix_catalogue_nvac.py`). |

A cell that gets through all seven tiers without being filled is set to **rate = 0** at write time. The runtime skips zero-rate edges in `avail_rebuild_all`, so an unfilled key tuple simply means "this event cannot fire here." That is sometimes physically correct (e.g. surface-subsurface exchange in a single-vacancy system at low T) and sometimes a coverage gap.

> **Healthy build sanity check (May 2026+).** `pylatkmc-gen provenance` should report **0 cells filled by tier 7** for a `ni_fe_cr_v1`-style spec when the catalogue has been processed by `fix_catalogue_nvac.py`. If tier 7 is firing for `surface_1NN_inplane` or `subsurface_1NN_inplane` cells, the catalogue's `n_vac_nn1` is still the coordination-shortfall proxy — re-run `fix_catalogue_nvac.py` and `build_family_rate_table.py`, then `pylatkmc-gen rate` again.

### Provenance

`count[i]` in the binary records the number of pyKMC events that contributed to cell `i` via tier 1. `count[i] == 0` means the cell was filled by a fallback tier or left at zero. The `pylatkmc-gen provenance <spec.toml>` CLI prints the per-`(sc, dir)` slab coverage table (see ARCHITECTURE for an example).

### What's in the binary

```
KMCRTv01 magic   (8 bytes)
JSON header      (UTF-8; carries n_axes, n_entries, axis_maxes[], strides[],
                  axis_names[], temperature_K, k0_Hz, motif_of_class_dir[],
                  model_name, version=3)
u32 n_entries
f32[n] rate                  (Arrhenius pre-exponentiated at T)
f32[n] Ea_eV                 (for logging / debug)
u32[n] count                 (provenance: 0 ⇒ tier ≥ 2 or unfilled)
```

`runtime/src/core/kmcfmt.{c,h}` (and the Python helper at `pylatkmc/kmcfmt.py`) handle the magic + header layer; the per-model `ratetable.c` template implements the body parser with shape validation against compile-time constants.

---

## Stage 4 — runtime CLI

The compiled binary `build/pylatkmc_<MODEL>` takes one argument: a path to an `input.ini`. Sample:

```ini
[run]
max_steps      = 100000
max_time_s     = 0
sample_every   = 5000
summary_every  = 0
base_seed      = 42

[paths]
ratetable_path  = /abs/path/to/<MODEL>.kmcrt
initconfig_path = /abs/path/to/config.kmcinit
output_root     = ./output

[physics]
temperature_K = 500.0
```

The runtime loads the rate table and `.kmcinit`, validates that `temperature_K` matches the rate-table header, then runs the BKL loop on each rank. Output:

```
output/
├── per_rank_0/
│   ├── pykmc.out        # space-separated step log
│   └── kmcout.xyz       # sampled trajectory frames
├── per_rank_1/...
├── per_rank_2/...
├── per_rank_3/...
└── aggregate_summary.json    # what the comparison harnesses read
```

Run with MPI:

```bash
mpirun --oversubscribe -n 4 \
    build/pylatkmc_ni_fe_cr_v1 \
    /path/to/input.ini
```

(On a cluster, replace `mpirun` with `srun` and adjust to your scheduler's launcher; on macOS make sure `mpirun` and the linked `libmpi` come from the same MPI install.)

---

## Validation harness 1: `tools/compare_msd_vs_pykmc.py`

```bash
python tools/compare_msd_vs_pykmc.py <pykmc_run_dir> --model ni_fe_cr_v1 --n-replicas 4 --steps 100000
```

What it does:

1. Loads `<pykmc_run_dir>/analysis/summary.json` — gets `T`, `n_vacancies`, `total_sim_time`, `msd_final`.
2. Reads `trajkmc.xyz` frame-0 header to infer slab dims `(nx, ny, nz)`.
3. Parses the composition from the directory name (e.g. `NiCr_Ni95_Cr05_T500_1vac_full` → `Ni95_Cr5`).
4. Generates a fresh `.kmcinit` of the matching size and composition.
5. Runs `pylatkmc_<model>` for the requested steps × replicas.
6. Computes `D = MSD / (6t)` for both pyKMC and pylatkmc; prints the ratio and an effective-barrier offset.

**Caveat — basin acceleration.** pyKMC reports `total_sim_time` as the physical time integrated across super-events. When basin acceleration is on, that time scale can be **8-12 orders of magnitude larger** than what raw kinetics would produce, because the basin solver compresses thousands of low-barrier hops into one super-event. pylatkmc has no basin detection, so a direct `D_pylatkmc / D_pyKMC` ratio is not physically meaningful for basin-accelerated pyKMC runs. The harness still prints the number, but treat it as a smoke test, not a physics gate.

For genuinely fair comparison you'd need either (a) a pyKMC run with `basin = False`, or (b) compare event rates / motif distributions instead of D. Until either is available, the in-engine cross-composition harness below is the better validation tool.

**May 2026 — multi-vacancy MSD discrepancy.** A 10-vacancy comparison after the n_vac_nn1 + 2-axis fixes still shows pylatkmc's MSD ~10–20× pyKMC's. Per-event analysis (catalogued in `docs/pylatkmc_msd_diagnosis.md`) revealed 12.7% of pylatkmc events fire at Ea=0.084 eV (descended-vacancy basin-trap flicker hops), which pyKMC's basin acceleration silently bridges into single super-events. This is **not** a rate-cube error — both engines have correct physics for the individual events; pylatkmc is exposing flicker that pyKMC hides. Fixing this end-to-end requires either (a) implementing basin acceleration in pylatkmc, (b) excluding low-Ea flicker from pylatkmc's event selector, or (c) running pyKMC with `basin = False` for the comparison set. None is trivial. See the diagnosis doc for the full per-event histogram.

**Reference Ea extraction tool.** `Analysis/tools/pykmc_ea_distribution.py` parses any pyKMC run's `pykmc.out` + `reference_table.pickle` and emits per-`(family_id, n_vac_nn1)` Ea statistics. Useful for sanity-checking which cells the runtime actually accesses and at what Ea — directly comparable to the cube cell that `pylatkmc-gen rate` filled. See `apps/PyKMC_Analysis/Analysis/tools/README.md` for usage.

---

## Validation harness 2: `tools/compare_species_aware.py`

```bash
python tools/compare_species_aware.py \
    --model ni_fe_cr_v1 \
    --compositions 100Ni 95Ni_5Cr 95Ni_5Fe 90Ni_10Cr \
    --temperatures 500 \
    --steps 100000 --n-replicas 4 \
    -o docs/m4_species_results.json
```

This runs the same binary on the same slab size at the same T across multiple compositions. The per-temperature D ratios `D(100Ni) / D(alloy)` should be > 1 once the species axes carry real signal. As of M4, with the catalogue containing only 100Ni events, all compositions return identical D — which is itself a useful diagnostic for "is the species axis populated?" (answer: tier 1 isn't populating it; tier 2 propagates 100Ni rates everywhere).

The `--temperatures` flag currently requires a single T because the rate cube has the Arrhenius prefactor baked at build time. To compare across T, rebuild the cube at each target T (`pylatkmc-gen rate ... --T 300`, ... — once a `--T` flag is added to `pylatkmc-gen rate`).

---

## Tutorial — build a new alloy model from scratch

Goal: stand up a `models/ni_only_v2/` model that uses a simpler key (drops the alloy axes, keeps n_vac_nn1 and n_vac_nn2 only) so we can sanity-check single-vacancy 100Ni dynamics.

### Step 1 — author the spec

Create `models/ni_only_v2/ni_only_v2.kmcspec.toml`:

```toml
name    = "ni_only_v2"
lattice = "fcc"
species = ["Vacant", "Ni"]

[[shells]]
name = "nn1"
cutoff_mult = 1.05

[[shells]]
name = "nn2"
cutoff_mult = 1.50

[[key.axes]]
name  = "n_vac_nn1"
kind  = "count"
shell = "nn1"
match = "vac"
max   = 5

[[key.axes]]
name  = "n_vac_nn2"
kind  = "count"
shell = "nn2"
match = "vac"
max   = 5

[rate_data]
primary         = "../../../apps/PyKMC_Analysis/Analysis/lattice_event_classification/classified_events_with_families.csv"
fallback_scalar = "../../../apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table.csv"
temperature_K   = 500.0
k0_Hz           = 1.0e13
```

This spec produces a `3 × 5 × 5 × 5 = 375`-entry cube (vs. the 703,125-entry cube of `ni_fe_cr_v1`).

### Step 2 — generate the C source

```bash
source pykmc_env/bin/activate
cd pylatkmc

pylatkmc-gen build models/ni_only_v2/ni_only_v2.kmcspec.toml
# → renders 5 files under models/ni_only_v2/generated/:
#   events.h, ratetable.h, ratetable.c, avail.c, key_spec.json
```

### Step 3 — compile

```bash
cmake -B build_ni_only_v2 -DMODEL=ni_only_v2 -DREQUIRE_GENERATED=ON
cmake --build build_ni_only_v2 -j 4
# → build_ni_only_v2/pylatkmc_ni_only_v2
```

Each model gets its own build dir so you can keep multiple binaries side by side.

### Step 4 — build the rate cube

```bash
pylatkmc-gen rate models/ni_only_v2/ni_only_v2.kmcspec.toml
# → models/ni_only_v2/examples/ni_only_v2.kmcrt
```

### Step 5 — inspect coverage

```bash
pylatkmc-gen provenance models/ni_only_v2/ni_only_v2.kmcspec.toml
```

Expected: `<110>_inplane` and `<111>_interlayer` slabs at high coverage; `<100>` and `<001>` mostly tier-7-or-zero. Confirm visually before running anything large.

### Step 6 — build an initconfig

```bash
mkdir -p models/ni_only_v2/examples
python tools/build_initial_config.py \
    --nx 22 --ny 22 --nz 20 \
    --element Ni --n-vacancies 1 --seed 42 \
    -o models/ni_only_v2/examples/config.kmcinit
```

For an alloy model you'd swap `--element Ni` for `--composition Ni95_Cr5` (or `Ni90_Fe5_Cr5` for ternary).

### Step 7 — write an input.ini and run

```bash
cat > models/ni_only_v2/examples/input.ini <<EOF
[run]
max_steps      = 100000
max_time_s     = 0
sample_every   = 5000
summary_every  = 0
base_seed      = 42

[paths]
ratetable_path  = models/ni_only_v2/examples/ni_only_v2.kmcrt
initconfig_path = models/ni_only_v2/examples/config.kmcinit
output_root     = ./output

[physics]
temperature_K = 500.0
EOF

cd models/ni_only_v2/examples
mpirun --oversubscribe -n 4 \
    build_ni_only_v2/pylatkmc_ni_only_v2 input.ini
cat output/aggregate_summary.json
```

A clean run prints:

```
latkmc 0.1.0-scaffold — 4 ranks
[rank 0] run: 9680 sites, 1 vacancies, T=500.0 K, max_steps=100000
[rank 0] wrote ./output/aggregate_summary.json  (n=4, 4 ok / 0 failed)
```

`aggregate_summary.json` has the fields documented in [`ARCHITECTURE.md`](ARCHITECTURE.md#mpi-ensemble) — `total_time_s_mean`, `mean_msd_A2_mean`, `motif_counts_sum`, etc.

### Step 8 — compare to pyKMC

```bash
python tools/compare_msd_vs_pykmc.py \
    Data/Research/100Ni/1vac/T500/NiAlH_full \
    --model ni_only_v2 --steps 100000 --n-replicas 4
```

If the rate cube is well-populated and the pyKMC reference uses raw kinetics (basin disabled), the diffusion ratio should be within ~3× and the effective-Ea offset within ~100 meV. With basin enabled in the pyKMC run, expect a much larger ratio — that's the basin-acceleration confound discussed above.

---

## Known integration gap — alloy events not in the catalogue

As of M4 (2026-04-19) the curated `classified_events_with_families.csv` contains 81,277 events, all from the 100Ni composition. The 62 NiFe / NiCr / NiFeCr sim dirs in `Data/Research/Ni_Slab_Alloys/` exist but were never fed through the classification pipeline. Until they are, the species axes in the pylatkmc rate cube have no tier-1 data, and `compare_species_aware.py` returns identical D across all compositions.

Full diagnosis and the unblock plan are in `pylatkmc_m4_species_report.md` (upstream workspace doc). The fix is **upstream of pylatkmc** and requires no pylatkmc code changes:

1. Extend the sim-dir list in `apps/PyKMC_Analysis/Analysis/classify_lattice_events.ipynb` to include `Data/Research/Ni_Slab_Alloys/{NiCr_*,NiFe_*}`.
2. Re-run the classification notebook (~30 min last time it ran).
3. Rebuild the pylatkmc rate cube with `pylatkmc-gen rate models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml`.
4. Re-run `compare_species_aware.py` — alloy effects should now show up in the cross-composition ratios.

---

## Cross-references

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — how the codegen, rate cube, and runtime work internally.
- [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) — end-to-end walkthrough.
- [`KMOS_COMPARISON.md`](KMOS_COMPARISON.md) — how this differs from kmos.

### Upstream pyKMC analysis pipeline (external to this repo)

The curated rate-table CSV consumed by `pylatkmc-gen rate` is produced
by an off-lattice pyKMC simulation pipeline that handles trajectory
classification, family assignment, and the `n_vac_nn1` post-processor.
It is maintained as a separate codebase. Key artefacts it produces:

- `classified_events_with_families.csv` — the catalogue (~80k rows for
  100Ni). The primary input to `pylatkmc-gen rate`.
- `rate_lookup_table_family.csv` — per `(family_id, family_bucket_id)`
  event-weighted barriers. Tier-6 fallback in `pylatkmc.ratebuilder`.
- `rate_lookup_table.csv` — legacy 1-axis scalar table. Tier-7
  fallback (usually 0 cells in a healthy build).
- `fix_catalogue_nvac.py` — the mandatory post-processor that
  re-derives `n_vac_nn1`, `n_vac_nn2`, and `family_bucket_id`.

If you have access to the upstream pipeline, point `[rate_data].primary`
in your `<model>.kmcspec.toml` at the catalogue. If not, you can use
the example pre-built `.kmcrt` shipped with `models/ni_fe_cr_v1/` — it
covers single-vacancy 100Ni hops and is sufficient for smoke-testing
the binary.
