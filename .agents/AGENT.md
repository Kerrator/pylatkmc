# pylatkmc — AI Assistant Instructions

This file is the operational guide for AI coding assistants working on
the pylatkmc codebase. Human contributors should start with
[`../README.md`](../README.md) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## What pylatkmc is

A kmos-inspired species-aware on-lattice KMC engine. The pipeline:
TOML model spec → `pylatkmc-gen` Python codegen → generated C → CMake
link with the static C+MPI runtime backbone → per-model binary
`pylatkmc_<name>`. Rate cubes are pre-built from a curated FCC family
catalogue (CSV produced by an off-lattice pyKMC analysis pipeline,
external to this repo) via a deterministic seven-tier fallback chain.

pylatkmc is **independent at runtime** of any other engine — it consumes
the curated rate table and runs its own simulations. No MPI co-execution
with off-lattice tools.

## Critical: rate-cube preprocessing

Before any `pylatkmc-gen rate` build that consumes a freshly-regenerated
catalogue from the upstream analysis pipeline, the catalogue must have
**correct `n_vac_nn1_initial` columns** (true vacancy counts, not the
coordination-shortfall proxy). Otherwise the cube undershoots Ea by
~0.115 eV → 14× rate inflation at 500 K.

The upstream pipeline ships a corrector (typically called
`fix_catalogue_nvac.py`) that re-derives `n_vac_nn1`, `n_vac_nn2`, and
`family_bucket_id` from existing `coord_mover_*` and `nn2_count_*`
columns. **Always run it after a catalogue rebuild, before
`pylatkmc-gen rate`.**

The rate-table loader in `pylatkmc/ratebuilder.py:_load_family_bucket_barriers`
also accepts **2-axis (nv1, nv2)** bucket IDs (`nv1=N_nv2=M`) for
`*_1NN_inplane` families, with auto-derived 1-axis "any-nv2"
event-weighted fallback per nv1. Tier 6 (family-averaged) typically
fills cells that tier 7 (legacy scalar) would otherwise cover; a healthy
build shows **0 tier-7 cells** in `pylatkmc-gen provenance` output.

## What this codebase covers

- Author / edit a TOML model spec (`models/<name>/<name>.kmcspec.toml`).
- Run the codegen + build + rate-cube + provenance commands via
  `pylatkmc-gen`.
- Modify `pylatkmc/` — codegen, ratebuilder, spec parser, preprocessor.
- Modify the static C runtime (`runtime/src/{core,io,mpi}/*.{c,h}`):
  KMC selector, lattice neighbour list, RNG, IO, MPI replica aggregator.
- Add / extend pytest tests in `tests/unit_py/`.
- Build an initial config via `tools/build_initial_config.py`.
- Compare against an off-lattice pyKMC reference via
  `tools/compare_msd_vs_pykmc.py` and `tools/compare_species_aware.py`.
- Update design docs (`docs/ARCHITECTURE.md`, `docs/HOW_IT_WORKS.md`,
  `docs/PYKMC_INTEGRATION.md`, `docs/KMOS_COMPARISON.md`) when
  behaviour changes.
- Diagnose rate-cube coverage gaps via `pylatkmc-gen provenance`.

## What this codebase does NOT cover

- **Generating the rate-table CSV** — input only. The curated catalogue
  and the family rate table are produced by an external pyKMC analysis
  pipeline; pylatkmc consumes the result.
- **Running off-lattice pyKMC sims** — separate engine.
- **Rendering trajectories in 3D** — `trajkmc.xyz` is a standard ASE
  extended XYZ; use any compatible viewer (Ovito, ASE GUI, VMD).
- **Per-event UI** — pylatkmc has no event browser. For off-lattice
  catalogue browsing, use the upstream pyKMC analysis pipeline's tools.
- **Ingesting new pyKMC sims** into the curated catalogue — that's an
  upstream concern.

## Environment Setup

```bash
# From pylatkmc/
python -m venv .venv && source .venv/bin/activate
pip install -e .                       # installs `pylatkmc-gen` CLI

# Build dir + per-model binary
cmake -B build -DMODEL=<name>
cmake --build build -j 4               # produces build/pylatkmc_<name>

# MPI launcher (any OpenMPI ≥ 4.x or MPI 3.1-compatible implementation)
mpirun --oversubscribe -n N <binary> <input.ini>
```

`pip install -e .` registers the entry point so `pylatkmc-gen` resolves to
`pylatkmc.cli:main`. Re-run `pip install -e .` if you change
`pyproject.toml` console scripts.

**MPI gotcha (macOS):** if you have multiple MPI installations on your
system (e.g. homebrew's openmpi alongside a hand-built one), make sure
the `mpirun` you invoke and the libmpi that the binary linked against
come from the **same** install. Mixed-toolchain MPI segfaults in
`MPI_Allreduce` are very confusing.

## Top-level Layout

```
pylatkmc/
├── pylatkmc/           # Python package (~1.4 kLOC) — TOML → C + .kmcrt
│   ├── cli.py               #   `pylatkmc-gen` entry point: build|rate|info|provenance|clean
│   ├── loader.py            #   reads kmcspec.toml → ModelSpec (pydantic)
│   ├── spec.py              #   ModelSpec / Axis / Shell pydantic models
│   ├── codegen.py           #   spec → events.h, ratetable.{h,c}, avail.c, key_spec.json
│   ├── ratebuilder.py       #   curated CSV → .kmcrt (7-tier fallback)
│   └── preprocessor.py      #   `#@ ... @#` template rewriter (kmos port)
├── runtime/src/             # Static C backbone (model-agnostic)
│   ├── core/                #   KMC engine, lattice, state, RNG, format helpers
│   ├── io/                  #   config reader, XYZ writer, pykmc.out logger
│   └── mpi/                 #   replica.c — MPI ensemble aggregator
├── models/                  # One dir per model
│   └── <name>/
│       ├── <name>.kmcspec.toml
│       ├── generated/       #   codegen output (events.h, ratetable.{h,c}, avail.c)
│       └── examples/        #   input.ini, .kmcinit, .kmcrt
├── tests/unit_py/           # 62 pytest tests: spec_load, preprocessor, codegen, ratebuilder
├── tools/                   # build_initial_config.py, compare_msd_vs_pykmc.py, compare_species_aware.py
├── docs/                    # ARCHITECTURE.md, PYKMC_INTEGRATION.md, KMOS_COMPARISON.md
├── CMakeLists.txt           # builds pylatkmc_<MODEL> per -DMODEL=<name>
├── pyproject.toml           # exposes pylatkmc-gen CLI
└── build/                   # CMake output dir
```

## Workflow

For any task, walk through these steps in order:

### Step 1 — Identify the model

Every task is associated with a specific model name (e.g.
`ni_fe_cr_v1`). Confirm the spec lives at the canonical path:

```
models/<name>/<name>.kmcspec.toml
```

The binary is `pylatkmc_<spec.name>`. The CLI's `_resolve_generated_dir`
enforces this layout.

### Step 2 — Spec → Generated C

```bash
pylatkmc-gen build models/<name>/<name>.kmcspec.toml
```

Produces `models/<name>/generated/{events.h, ratetable.h, ratetable.c,
avail.c, key_spec.json}`. CMake links these against the static runtime.

If the spec changed (axis added, max increased, new species), run
`pylatkmc-gen clean` first — CMake doesn't always invalidate the build cache
when only header content changes.

### Step 3 — CMake build

```bash
cmake -B build -DMODEL=<name>
cmake --build build -j 4
```

Output: `build/pylatkmc_<name>`. CMake reads `-DMODEL` and infers
`models/<name>/generated/` as the codegen dir. The build replaces stub
.c files in `runtime/src/core/` with the generated ones via include-path
ordering. **Don't** mix a `core/foo.c` stub with a `generated/foo.c` of
the same name in the source list.

### Step 4 — Build rate cube

```bash
# Required prerequisite if the upstream catalogue was just regenerated:
cd <upstream-pyKMC-analysis>
python -m Analysis.tools.fix_catalogue_nvac \
    --input  Analysis/lattice_event_classification/classified_events_with_families.csv \
    --output Analysis/lattice_event_classification/classified_events_with_families.csv
cd Analysis
python build_family_rate_table.py \
    --input  lattice_event_classification/classified_events_with_families.csv \
    --output lattice_event_classification/rate_lookup_table_family.csv

# Then build the cube:
cd pylatkmc
pylatkmc-gen rate models/<name>/<name>.kmcspec.toml
```

Reads the curated CSV (paths declared in `[rate_data]` of the spec),
applies the fallback chain, and writes a binary `.kmcrt` file
(8-byte magic + u32 header_bytes + JSON header + u32 n_entries +
`f32[n_entries]` rate + `f32[n_entries]` Ea + `u32[n_entries]` count)
mmap'd at runtime. Cube size for `ni_fe_cr_v1`: 3 × 5 × 3 × 5⁶ ≈ 700k
entries.

**Critical file-format note.** The payload starts with `u32 n_entries`
*after* the JSON header and *before* the f32 rate array. Earlier
diagnostic decoders that skipped this 4-byte field read shifted values.
See `Analysis/tools/patch_cube_cell.py` for the corrected decoder.

**Two-axis tier 6.** Family bucket IDs may be
`nv1=N_nv2=M` (2-axis) for the three `*_1NN_inplane` families;
`ratebuilder.py:_load_family_bucket_barriers` parses both 1-axis and
2-axis IDs and synthesises a 1-axis "any-nv2" event-weighted fallback
per nv1. This means tier 6 typically fills cells that tier 7 used to
cover — `pylatkmc-gen provenance` will show 0 tier-7 cells for a healthy
build.

**The temperature is baked in at this step.** Running at a different
`temperature_K` than declared in the spec will throw an error. Build a
separate cube per T.

### Step 5 — Initial config (optional)

```bash
python tools/build_initial_config.py --nx 22 --ny 22 --nz 20 \
    --composition Ni95_Cr5 --n-vacancies 1 --seed 42 \
    -o models/<name>/examples/config.kmcinit
```

Or use one of the pre-shipped `.kmcinit` files in `models/<name>/examples/`.

### Step 6 — Run

```bash
cd models/<name>/examples
mpirun --oversubscribe -n 4 \
    pylatkmc/build/pylatkmc_<name> input.ini
```

Outputs land under `output/` per the `input.ini` config:

```
output/
├── aggregate_summary.json    # MPI-aggregated: n_replicas, mean/std D, motif/direction histograms
└── replica_NNNN/
    ├── summary.json          # per-rank: n_steps, total_time_s, mean_msd_A2
    ├── pykmc.out             # tab-delimited log (step, time, dt, n_vac, k_tot, k_event, Ea, motif, direction)
    └── trajkmc.xyz           # sampled trajectory (every `sample_every` steps)
```

### Step 7 — Validate

```bash
pytest tests/unit_py/                                # 62 tests
pylatkmc-gen provenance models/<name>/<name>.kmcspec.toml  # coverage report
python tools/compare_msd_vs_pykmc.py ...             # cross-engine MSD check
```

`pylatkmc-gen provenance` reports per-(site_class, direction) cell coverage
across the seven fallback tiers. Critical for catching missing training
data — especially for alloys (see Known Quirk #2).

## Conventions and Constants

### Spec layout (enforced)
- File: `models/<name>/<name>.kmcspec.toml` (the spec name and dir name
  must match).
- Binary: `pylatkmc_<spec.name>` in `build/`.

### Required spec fields
- `name` — string (binary suffix).
- `lattice` — only `"fcc"` is supported.
- `species` — list with `"Vacant"` first.
- `[[shells]]` — named neighbour shells, each with `name` and
  `cutoff_mult`.
- `[[key.axes]]` — user-declared key dimensions, each with `name`,
  `kind` (`enum` or `count`), and `max`. `count` axes also need `shell`
  and `match`.
- `[rate_data]` — paths to the curated CSV, family rate table, scalar
  fallback, plus `temperature_K` and `k0_Hz`.

### Implicit key axes (always first, do NOT declare)
- `site_class` — 3 values (surface / subsurface / bulk).
- `direction` — 5 values (`<110>` / `<100>` / `<111>` / `<001>` / unresolved).

### Rate cube format
- Header: magic bytes + axis info.
- Body: `f32[n_entries]` rates (Hz) + `f32[n_entries]` Ea (eV).
- Mmap'd at runtime — no allocation.

### MPI seeding
- Each rank gets `base_seed + rank` via splitmix64.
- Deterministic, no rank collisions.
- Single-replica runs (`-n 1`) use only the base seed.

### Output schema
- `pykmc.out` columns (tab-separated): `step  time_s  dt_s  n_vac
  k_tot  k_event  Ea_eV  motif  direction`.
- `aggregate_summary.json` keys: `n_replicas`, `mean_msd_A2_mean`,
  `mean_msd_A2_std`, `total_time_s_mean`, motif histogram, direction
  histogram.

### kmos heritage and divergences
**Inherited:**
- Spec-driven codegen pattern (Python project spec → specialised
  native code).
- `#@ ... @#` preprocessor (50-line port; pylatkmc uses f-string syntax
  inside `#@` lines).
- Specialised inner loop per model — schema baked at codegen time, no
  runtime dispatch.
- Model-dir-per-binary convention.

**Diverged:**
- No pattern-DB decision tree. pylatkmc uses a flat rate cube indexed
  by integer key — schema complexity lives in data, not in code.
- No incremental `avail_sites` O(1) tracker yet (M5/M6 candidate).
  Currently rebuilds events every step, O(n_vac × 18).
- All rates pre-exponentiated at build time (no OTF runtime rate
  evaluation). Changing T requires rebuilding the cube.
- TOML + pydantic, not XML or programmatic Python.
- No multi-site events (`actions` tuple) — only single-vacancy 1NN/2NN
  hops.

## Task Recipes

### Recipe 1 — First-time setup

```bash
cd pylatkmc
source ../pykmc_env/bin/activate
pip install -e .                                      # installs pylatkmc-gen
pylatkmc-gen build models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
cmake -B build -DMODEL=ni_fe_cr_v1
cmake --build build -j 4
pylatkmc-gen rate models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
cd models/ni_fe_cr_v1/examples
mpirun --oversubscribe -n 4 \
    pylatkmc/build/pylatkmc_ni_fe_cr_v1 input.ini
cat output/aggregate_summary.json
```

### Recipe 2 — Add a new species axis

1. Add the axis to `[[key.axes]]` in the TOML spec:
   ```toml
   [[key.axes]]
   name  = "n_Cu_nn1"
   kind  = "count"
   shell = "nn1"
   match = "Cu"
   max   = 5
   ```
2. Add `"Cu"` to the `species` list.
3. `pylatkmc-gen clean models/<name>/<name>.kmcspec.toml`
4. `pylatkmc-gen build ...` and `cmake --build build -j 4`.
5. `pylatkmc-gen rate ...` and check `pylatkmc-gen provenance ...` — expect
   significant tier-7 fallback if no Cu training data exists yet.

### Recipe 3 — Build at a new temperature

You need one rate cube per T because rates are pre-exponentiated.

1. Copy the spec: `cp models/<name>/<name>.kmcspec.toml
   models/<name>_T700/<name>_T700.kmcspec.toml`.
2. Edit `name = "<name>_T700"` and `temperature_K = 700.0` in
   `[rate_data]`.
3. `pylatkmc-gen build` + `cmake --build build -j 4` + `pylatkmc-gen rate`.
4. Run with `mpirun ... build/pylatkmc_<name>_T700 input.ini`.

### Recipe 4 — Diagnose a fallback-tier coverage gap

```bash
pylatkmc-gen provenance models/<name>/<name>.kmcspec.toml > /tmp/prov.txt
grep -E "tier_[5-7]" /tmp/prov.txt | head -20
```

Output rows show per-(site_class, direction) which tier filled which
cells. Tiers 5-7 are coarse fallbacks; many of them indicate missing
training data. Cross-reference against the curated CSV's
`assignment_status == 'accepted'` rows to see which families are
populated.

### Recipe 5 — Modify the C runtime

Example: add a column to `pykmc.out`.

1. Edit `runtime/src/io/log.c` — extend the format string and the per-
   step write.
2. Update the column doc in `runtime/src/io/log.h`.
3. `cmake --build build -j 4` (no codegen needed since the runtime is
   model-agnostic).
4. Add a regression test in `tests/unit_py/test_log_format.py`.
5. Update `Analysis/AGENT.md` if downstream notebooks parse `pykmc.out`.

### Recipe 6 — Cross-engine validation against pyKMC

```bash
python tools/compare_msd_vs_pykmc.py \
    --pykmc-dir ../apps/PyKMC_Analysis/Data/Research/Ni_T500_1vac_baseline \
    --latkmc-dir build/pylatkmc_ni_fe_cr_v1 \
    --temperature 500 \
    --steps 100000
```

Outputs a side-by-side MSD plot and an Arrhenius-fit comparison.
Discrepancies at the same T usually mean: (a) basin acceleration on
pyKMC side (pylatkmc has no basin), (b) fallback tiers diluting the
species-specific rates (run `provenance` to confirm), or (c) a different
initial config.

### Recipe 7 — Add a unit test

```bash
# tests/unit_py/test_<feature>.py
import pytest
from pylatkmc.loader import load
from pathlib import Path

def test_<feature>():
    spec = load(Path("models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml"))
    assert spec.species[0] == "Vacant"
    # ...

# Run:
pytest tests/unit_py/test_<feature>.py -v
```

For C-side changes, add a regression test in
`tests/unit_py/test_compile.py` that compiles the affected model and
asserts the binary runs a smoke `input.ini`.

## Verification Patterns

```bash
# Full Python suite
pytest tests/unit_py/ -v                          # 62 tests as of M4

# Coverage report (the alloy-specific gold standard)
pylatkmc-gen provenance models/<name>/<name>.kmcspec.toml

# Smoke check the rate cube binary
xxd models/<name>/examples/<name>.kmcrt | head -5  # magic + axis info

# After running input.ini, sanity-check the aggregate
python -c "
import json
d = json.load(open('output/aggregate_summary.json'))
assert d['n_replicas'] == NTASKS
assert d['mean_msd_A2_mean'] > 0
print(f\"D = {d['mean_msd_A2_mean'] / (d['total_time_s_mean'] * 1e-10):.2e} A^2/s\")
"
```

## Known Quirks

1. **Build cache invalidation.** Changing the spec doesn't always
   trigger a CMake rebuild if the generated files already exist. Run
   `pylatkmc-gen clean models/<name>/<name>.kmcspec.toml` before `pylatkmc-gen build`
   when an axis is added or `max` is increased.

2. **Tier-2 alloy fallback drops element identity.** When a cell has
   non-zero alloy axes (e.g. `n_Fe_nn1 > 0`) and no training data, the
   rate is copied from the `n_Fe_nn1 = 0` slice. This is correct only if
   the rate is **weakly dependent** on the specific alloy identity —
   acceptable for FCC diffusion but not in general. Check with
   `pylatkmc-gen provenance`.

3. **Bucket-aware tier-6 mover offset.** Family buckets index by the
   *mover's* `nv1`, not the vacancy's. For a 1NN hop,
   `mover_nv1 = vacancy_n_vac_nn1 + 1`. Cells at
   `n_vac_nn1 = 0` (isolated vacancy) correctly match family bucket
   `nv1 = 1` (mover with 1NN). See `_MOVER_NV1_OFFSET = 1` in
   `pylatkmc/ratebuilder.py:322`. The same offset applies to nv2
   for the 2-axis bucket lookup.

3a. **Two-axis tier-6 lookup (2-axis variant).** For
   `surface_1NN_inplane`, `subsurface_1NN_inplane`, `bulk_1NN_inplane`,
   `_load_family_bucket_barriers` returns
   `dict[family, dict[(nv1, nv2), Ea]]` keyed on the mover's
   (nv1, nv2). `_apply_tier6_family` looks up the exact pair first; if
   missing, it falls back to a 1-axis "any-nv2" event-weighted mean
   stored at key `(nv1, -1)`. Other families remain 1-axis. See
   `pylatkmc/ratebuilder.py:_load_family_bucket_barriers` and
   `_apply_tier6_family` for the parser + lookup logic.

4. **MPI seeding determinism.** Each rank uses `base_seed + rank` via
   splitmix64. Identical results across runs for fixed seed +
   rank-count. Single-replica runs reuse only the base seed.

5. **FCC-only.** Shells are CSR 1NN + 2NN. No 3NN, no HCP / BCC
   without code changes (would need to extend `runtime/src/core/lattice.c`
   and the codegen lattice axis enum).

6. **Temperature is baked in.** Pre-exponentiated rates in the `.kmcrt`
   cube. Running at a different `temperature_K` than the spec declared
   throws an error in `runtime/src/core/state.c`. Build a separate cube
   per T.

7. **Generated `.c` files replace stubs.** CMake's include-path
   ordering is the mechanism: `models/<name>/generated/` is prepended to
   the include path, and the stub `runtime/src/core/<file>.c` is
   removed from the source list. Don't add a generated file with the
   same name as a stub without updating `CMakeLists.txt`.

8. **No basin acceleration.** Differs from pyKMC. Direct D comparisons
   against pyKMC require off-basin pyKMC runs (`basin = False`),
   otherwise pyKMC will look "faster" by orders of magnitude.

9. **Training-data status (M4, 2026-04-19).** The curated catalogue is
   **100Ni only** (81,277 events; zero alloy events). All compositions
   produce identical D until M4b (Analysis-side ingestion of the 62
   alloy sims in `Data/Research/Ni_Slab_Alloys/`) lands. Verified via
   `tools/compare_species_aware.py`. M4b is owned by the lattice
   classification sub-agent.

10. **`n_vac_nn1` upstream-catalogue caveat.** The upstream classification
    pipeline ships with a fast-path that produces
    `n_vac_nn1_initial = max(0, 12 - coord_mover)` — a coordination-
    shortfall proxy, not a true vacancy count. Surface atoms (coord=8)
    always read `nv1=4` under that proxy. The upstream pipeline ships
    a corrector (`fix_catalogue_nvac.py`) that re-derives `nv1`, `nv2`,
    and `family_bucket_id` from existing `coord_mover_*` and `nn2_count_*`
    columns in ~30 s. **Always run it after regenerating the catalogue,
    before `pylatkmc-gen rate`.**

11. **Multi-vacancy MSD discrepancy ≠ rate-cube error.** When the
    off-lattice pyKMC reference's multi-vacancy MSD is much smaller than
    pylatkmc's, the cause is usually pyKMC's basin acceleration eating
    low-Ea flicker hops (e.g. 0.084 eV jumps in surface-vacancy clusters)
    rather than a cube-rate bias. Use pyKMC `basin = False` runs (slow)
    for an apples-to-apples comparison, or compute pyKMC's "effective" D
    after excluding basin-trap events.

12. **`#@ ... @#` preprocessor scope.** Only top-level statements
    inside `#@` lines are evaluated. Multi-line constructs (`for`, `if`)
    use the `[[ ... ]]` block form. See `pylatkmc/preprocessor.py`
    for the rewrite rules.

## References

- High-level architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- End-to-end walkthrough: [`../docs/HOW_IT_WORKS.md`](../docs/HOW_IT_WORKS.md)
- Integration with the upstream pyKMC analysis pipeline:
  [`../docs/PYKMC_INTEGRATION.md`](../docs/PYKMC_INTEGRATION.md)
- Comparison with kmos: [`../docs/KMOS_COMPARISON.md`](../docs/KMOS_COMPARISON.md)
- **Per-family rate-prefactor loader:**
  [`../pylatkmc/family_prefactors.py`](../pylatkmc/family_prefactors.py)
  — accepts a `family_prefactors.csv` produced by an external HTST
  (Vineyard ν₀ + Sharia–Henkelman RPA κ) pipeline. Loader is ready
  (14 unit tests passing); integration into `ratebuilder.py`'s tier-1
  / tier-6 / tier-7 rate-baking lines is staged but not yet wired.
- Tests: [`../tests/unit_py/`](../tests/unit_py/)
- User CLI tools: [`tools/`](tools/)
- Curated rate-table source (input):
  [`../apps/PyKMC_Analysis/Analysis/lattice_event_classification/`](../apps/PyKMC_Analysis/Analysis/lattice_event_classification/)
- Project README: [`README.md`](README.md)
