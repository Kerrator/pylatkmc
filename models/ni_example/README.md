# `ni_example` — a self-contained pure-Ni example

A small, fully **self-contained** model for trying pylatkmc end to end: a single
vacancy diffusing on an FCC Ni(100) slab, with the move catalogue **learned from
real off-lattice pyKMC data** that is vendored right here in the repo.

Unlike the other models (whose specs point at the external `apps/PyKMC_Analysis`
catalogue), this one ships its training table under [`data/`](data/), so a fresh
clone of *just* pylatkmc can **regenerate** it with `pylatkmc-gen build` — no
sibling directories required.

## What "training on pyKMC data" means here

The off-lattice pyKMC pipeline discovers and classifies atomic moves, then
aggregates them into a per-`(family, bucket)` rate table:

```
pyKMC sim (pARTn saddle search)  →  classified_events_with_families.csv (per event)
        →  rate_lookup_table_family.csv  (per family+bucket: mean barrier Ea, Vineyard ν₀)
        →  data/rate_lookup_table_family.csv   ← vendored here (real, pure 100Ni)
        →  pylatkmc-gen build  →  generated/proclist.c   (one C Process per family×bucket×direction)
        →  cmake  →  pylatkmc_ni_example  →  run
```

A "family" is a **type of move**; pylatkmc expands one catalogue row into one
compiled Process per symmetry-equivalent direction, so a handful of families
becomes a few hundred Processes (350 for this catalogue). The runtime computes
each rate from the baked prefactor + barrier at the run temperature:
`k = ν₀·exp(−Eₐ/kᴮT)`.

## The move types in the catalogue

The vendored table is the curated, **pure-Ni (100Ni)** FCC family catalogue. The
fittable families (those with real events and a defined barrier) are:

| Family | Move | Eₐ range (eV) |
|---|---|---|
| `surface_1NN_inplane` | surface ⟨110⟩ in-plane 1NN hop — **the dominant surface-diffusion move** | 0.17–1.02 |
| `subsurface_1NN_inplane` | subsurface ⟨110⟩ in-plane 1NN hop | 0.24–0.84 |
| `subsurface_2NN_diagonal` | subsurface ⟨100⟩ 2NN diagonal hop | ~0.96 |
| `surface_interlayer_hop` | surface→subsurface ⟨111⟩ interlayer hop | 0.00–0.18 |
| `subsurface_interlayer_hop` | subsurface↔subsurface ⟨111⟩ interlayer hop | 1.02–1.08 |
| `surface_subsurface_exchange_up` | concerted 2-atom exchange, +z | 0.96–1.05 |
| `surface_subsurface_exchange_down` | concerted 2-atom exchange, −z | 0.00–1.01 |
| `subsurface_migration_interlayer` | subsurface vacancy migration via ⟨111⟩ displacement | 0.98–1.07 |

Visibility-only / zero-event families (`bulk_1NN_inplane`, `surface_2NN_diagonal`,
`subsurface_migration_axial`, `concerted_multisite`, `unresolved_multisite`) are
present in the CSV for provenance but carry no fittable barrier, so
`pylatkmc-gen` skips them automatically.

The vendored CSV also carries `surface_subsurface_exchange_lateral` rows (~1.00 eV)
— renamed `adatom_attachment` after the 2026-08-14 audit proved they are
single-atom adatom re-insertions, not 2-atom exchanges. They need an
above-surface adatom site the lattice does not have, so the translator skips
them (old and new id alike; see `translator._ADATOM_GATED_FAMILIES`) and they
emit no Processes.

Each row's bucket key (e.g. `nv1=1_nv2=0`) records the local vacancy environment
in which the move was observed; pylatkmc gates the compiled Process on that exact
environment.

## Quickstart

```bash
# from the pylatkmc/ repo root
pylatkmc-gen build models/ni_example/ni_example.kmcspec.toml   # regenerate (uses ONLY data/)
cmake -B build -DMODEL=ni_example && cmake --build build -j4   # → build/pylatkmc_ni_example

cd models/ni_example/examples
mpirun -n 1 ../../../build/pylatkmc_ni_example input.ini        # (or run the binary directly)
cat output/aggregate_summary.json
```

You should see `n_steps` complete with `run_rc: 0` and a non-zero
`mean_msd_A2` — the surface vacancy diffuses. `output/.../trajkmc.xyz` shows the
migration (the vacant site is omitted, so each frame has one fewer atom than the
lattice).

## What actually fires on this slab

The example slab ([`examples/slab_ni_1vac.kmcinit`](examples/slab_ni_1vac.kmcinit),
6×6×4 = 144 sites, **one surface vacancy**) mostly exercises
`surface_1NN_inplane` at low coordination (`nv1=1`) — i.e. ordinary surface
vacancy diffusion. The higher-coordination interlayer/exchange buckets in the
catalogue come from richer off-lattice environments and are compiled but rarely
activate with a single vacancy. To exercise more move types, scale up:

- **More vacancies** — regenerate the slab with `--n-vacancies N`
  (`python tools/build_initial_config.py --nx 6 --ny 6 --nz 4 --element Ni --n-vacancies 5 --vacuum-layers 1 -o ...`).
- **A different temperature / longer run** — edit `examples/input.ini`.
- **A different / multi-element catalogue** — drop a new
  `rate_lookup_table_family.csv` into `data/` (and add the species + their count
  axes to the spec) to model Ni-Fe / Ni-Cr instead.

## Files

| Path | Role |
|---|---|
| `ni_example.kmcspec.toml` | the model spec (pure Ni; `family_table` points at the local `data/`) |
| `data/rate_lookup_table_family.csv` | vendored real pure-Ni family catalogue (the training data) |
| `examples/slab_ni_1vac.kmcinit` | FCC Ni(100) slab, one surface vacancy |
| `examples/input.ini` | run config (T, steps, paths) |
| `generated/proclist.{c,h}` | generated C (committed, so the model also builds without regenerating) |
