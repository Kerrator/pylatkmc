# PYKMC_INTEGRATION.md — pylatkmc ↔ pyKMC

**Audience:** anyone who wants to take pyKMC simulation outputs and
turn them into a pylatkmc model, validate one against the other, or
author a new pylatkmc model from scratch.

**Last updated:** 2026-05-06 (v0.2.0).

---

## How they fit together

pyKMC and pylatkmc serve different niches:

- **pyKMC** is the off-lattice reference. Each event is a
  pARTn-discovered saddle-point search; reuse via IRA point-set
  registration; environment classification via CNA / graph hashing.
  Slow per step, expensive saddle searches, but flexible enough to
  handle arbitrary defects, grain boundaries, and complex
  topologies.

- **pylatkmc** is the on-lattice fast runner. Catalogue-driven; rates
  are baked at codegen time; per-step cost is O(active_sites × log
  n_procs). Specialised to FCC slabs with low defect density (~1–10
  vacancies). Good for million-step trajectories at fixed T.

The pipeline links them through the **curated FCC family catalogue**:

```
pyKMC simulations
    └── classified_events.csv (raw)
        └── classify_lattice_events: family_id + bucket
            └── classified_events_with_families.csv
                └── aggregate by (family_id, family_bucket_id):
                    └── rate_lookup_table_family.csv  ← pylatkmc consumes this
```

The aggregation lives in
`apps/PyKMC_Analysis/Analysis/lattice_event_classification/` (in the
workspace meta-repo, not in pylatkmc itself).

## Curating the catalogue

Each pyKMC event has rich provenance (saddle/min1/min2 positions,
energies, atomic environment hash). The classification pipeline:

1. **Family registry.** `apps/PyKMC_Analysis/Analysis/families.py`
   defines ~14 canonical event types (`surface_1NN_inplane`,
   `subsurface_2NN_diagonal`, `surface_subsurface_exchange_*`,
   `concerted_multisite`, etc.) with seed-rules + environment-rules
   that classify each event row deterministically.
2. **Bucketing.** Within each family, events bucket by integer keys
   like `nv1=2_nv2=0` (2 vacancies in the 1NN shell, 0 in the 2NN
   shell). The bucket structure is family-specific.
3. **Aggregation.** Per `(family, bucket)` the pipeline computes
   n_events, Ea_mean_eV, Ea_std_eV, and a small set of provenance
   columns. The output is `rate_lookup_table_family.csv`.

pylatkmc reads only the family rate table — never the raw
`classified_events.csv`. This decouples the on-lattice runner from
upstream pyKMC implementation details.

## Spec → pylatkmc model

A `.kmcspec.toml` declares which catalogue to consume, the species
list, and the physics parameters:

```toml
name = "ni_fe_cr_v1"
lattice = "fcc"
species = ["Vacant", "Ni", "Fe", "Cr"]   # first MUST be Vacant

[[shells]]
name = "nn1"
cutoff_mult = 1.05    # 1NN cutoff is 1.05 * a/√2

[[shells]]
name = "nn2"
cutoff_mult = 1.45    # 2NN cutoff is 1.45 * a/√2

[key]
axes = []             # v0.2: no rate-cube key axes; the pattern-DB has its own structure

[rate_data]
family_table = "../../../apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table_family.csv"
temperature_K = 500.0
k0_Hz = 1.0e13
```

The `family_table` path is resolved relative to the `.kmcspec.toml`
file. Pull the CSV from the upstream Analysis pipeline, point the
spec at it, and `pylatkmc-gen build <spec>` does the rest.

## Building a new alloy model from scratch

Suppose you want a new model `nife_ternary` based on the same FCC
family catalogue, but at T=900 K instead of 500 K.

```bash
# 1. Make the model directory and spec
mkdir -p models/nife_ternary
cp models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml models/nife_ternary/nife_ternary.kmcspec.toml
# Edit:
#   name = "nife_ternary"
#   temperature_K = 900.0

# 2. Build a starting configuration via tools/build_initial_config.py
#    (a 12x12x4 NiFe slab with one surface vacancy in the middle)
python tools/build_initial_config.py \
    --nx 12 --ny 12 --nz 4 \
    --species Ni Fe \
    --composition 0.95 0.05 \
    --vacancies 1 \
    --out models/nife_ternary/examples/config.kmcinit

# 3. Inspect the catalogue translation
pylatkmc-gen processes models/nife_ternary/nife_ternary.kmcspec.toml
# expect: ~360 Processes (catalogue is the same, T differs but counts don't)

# 4. Build proclist.c
pylatkmc-gen build models/nife_ternary/nife_ternary.kmcspec.toml
# → models/nife_ternary/generated/proclist.{c,h}

# 5. Compile
cmake -B build -DMODEL=nife_ternary
cmake --build build -j 4
# → build/pylatkmc_nife_ternary

# 6. Author input.ini, run
cat > models/nife_ternary/examples/input.ini <<'EOF'
[run]
max_steps      = 100000
sample_every   = 100
base_seed      = 42

[paths]
initconfig_path = config.kmcinit
output_root     = ./output

[physics]
temperature_K = 900.0
EOF

cd models/nife_ternary/examples
mpirun -n 4 ../../../build/pylatkmc_nife_ternary input.ini
cat output/aggregate_summary.json
```

That's the entire authoring path: ~10 commands, no template
plumbing. The same family CSV drives the new model; only T (and the
slab geometry) changes.

## Validation harnesses

`tools/compare_msd_vs_pykmc.py` (when present): reads a pyKMC
`pykmc.out` and a pylatkmc `aggregate_summary.json`, prints the
effective MSD-derived diffusivity at the same T. Target: **within 2×**
of the pyKMC reference.

Multi-vacancy / cooperative-event validation is a v0.3 task; the
v0.2 single-vacancy MSD agrees with the v0.1 cube baseline to within
13%, which is well inside the plan's ±30% gate.

## When NOT to use pylatkmc

- **Defect search / saddle discovery.** That's pyKMC's job. pylatkmc
  fires events from a precompiled catalogue — it can't discover new
  ones at runtime.
- **Geometries the catalogue doesn't cover.** Today the catalogue is
  curated for FCC (100) slab geometries. Other surfaces / bulk
  configurations may have catalogue gaps that the runtime can't fill.
- **Active basin acceleration.** That requires saddle searches at
  runtime; lives in pyKMC.
- **Restart from arbitrary trajectories.** Out of scope for v0.2.

## See also

- [`PATTERN_DB.md`](PATTERN_DB.md) — the pattern-DB pipeline.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — three-layer overview.
- [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) — worked-example trace from
  catalogue row to fired event.
- pyKMC: `pyKMC-develop/` in the workspace meta-repo.
- Family registry: `apps/PyKMC_Analysis/Analysis/families.py`.
- Catalogue CSV:
  `apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table_family.csv`.
