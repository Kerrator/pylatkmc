# How pylatkmc actually works — end-to-end walkthrough

A pyKMC saddle-search event becomes a row in a CSV becomes a cell in an mmap'd binary cube becomes one `O(1)` lookup per vacancy per step inside a compiled C binary. This doc traces that pipeline with a worked example and pins every load-bearing claim to a file:line reference in the live code (verified 2026-05-01).

For *what* pylatkmc is and how it's structured, see [`ARCHITECTURE.md`](ARCHITECTURE.md). This doc is about *how the data moves through it.*

---

## The big picture

The whole pipeline is **one CSV column-set holding the contract** between two halves: `apps/PyKMC_Analysis/Analysis/lattice_event_classification/classified_events_with_families.csv`. Everything upstream produces those columns; everything downstream consumes them.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          UPSTREAM (Analysis-side)                                │
│                                                                                  │
│  pyKMC sim ──▶ classify_lattice_events ──▶ families.py + family_assignment.py    │
│   (saddles)        (geometry → labels)           (labels → registry buckets)     │
│      │                   │                                  │                    │
│      ▼                   ▼                                  ▼                    │
│  trajkmc.xyz       classified_events.csv      classified_events_with_families   │
│  pykmc.out         (motif/dir/site_class)      .csv (family_id, bucket_id, ...) │
│  reference_table                                                                 │
│  .pickle                                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼  (the curated CSV is the handoff)
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       DOWNSTREAM (pylatkmc-side)                                  │
│                                                                                  │
│  ratebuilder.build() ──▶ 9-axis rate cube ──▶ .kmcrt binary                     │
│  (CSV → cube cells)      (703,125 entries)    (mmap'd at runtime)               │
│       │                                              │                           │
│       │ 7-tier fallback chain                        │                           │
│       │ fills empty cells                            ▼                           │
│       │                                  pylatkmc_<model>  ──▶ KMC steps         │
│       └──▶ tier-1 = direct events        (compiled binary)    avail_rebuild_all │
│            tier-2 = element-drops                              ratetable_key    │
│            tier-5 = cross-class borrow                         BKL pick + hop   │
│            tier-6 = family-bucket                                                │
│            tier-7 = scalar legacy                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

The "missing" tiers 3 and 4 in the fallback chain are intentional — they were planned but deferred (see `ratebuilder.py` module docstring at `pylatkmc/pylatkmc/ratebuilder.py:3-12`).

---

## Stage A — pyKMC produces a saddle event

A single pyKMC run dir (e.g. `Data/Research/100Ni/1vac/T500/NiAlH_full/`) writes:

| File | Contents |
|---|---|
| `trajkmc.xyz` | One frame per fired KMC step (ASE extended XYZ; `apps/PyKMC_Analysis/Analysis/AGENT.md:33`) |
| `pykmc.out` | Step log (10 columns, see below) — written by `pyKMC-develop/pykmc/log.py:443` |
| `reference_table.pickle` | pandas DataFrame of unique saddle events (15 columns, see below) |
| `pykmc.log` (optional) | Simulation log; needed for basin analysis |
| `basin_connectivity_*.pickle` (optional) | Basin connectivity tables when basin acceleration is enabled |

The actual columns in `pykmc.out`, written by [`pyKMC-develop/pykmc/log.py:443`](../../pyKMC-develop/pykmc/log.py):

```
Step  dT(s)  T(s)  Ref event  Ea(eV)  k_evt(ps-1)  k_tot(ps-1)  E(eV)  Cpu time(s)  Wall time(s)
```

(Note: `apps/PyKMC_Analysis/Analysis/AGENT.md:32` lists only the first 8 columns; the timing columns aren't documented there.)

The `Ref event` integer indexes into `reference_table.pickle`, a pandas DataFrame with 15 columns:

| Column | Role |
|---|---|
| `event_id`, `idx_ref` | Identity / cross-references |
| `initial_positions`, `saddle_positions`, `final_positions` | N×3 partial-cluster Cartesian coords |
| `initial_types` | Per-atom species labels |
| `move_atom_idx` | Index of the primary moving atom |
| `Ea`, `k` | Activation barrier and rate constant |
| `idx_backward` | Index of the reverse event |
| `dra` | Displacement / reconstruction residual |
| `id_final`, `id_saddle` | State identifiers |
| `sym_matrix`, `sym_perm` | Symmetry tracking for IRA-mapped events |

**The fundamental physics unit at this point**: a 3-frame snapshot (initial / saddle / final) of an atom moving into a vacancy, plus barrier + symmetry. None of these have a *category* yet.

---

## Stage B — geometry classification

`apps/PyKMC_Analysis/Analysis/lattice_map_events.py` (driven by `classify_lattice_events.ipynb`) walks each fired event, extracts the mover atom + neighbours, and assigns three orthogonal labels.

```
                 raw event
                 (init → saddle → final)
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  B1. mover identification           │
        │  (atom with largest displacement)   │
        └────────────────┬────────────────────┘
                         │  mover_pos_initial, mover_pos_final
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │  B2. site_class_3d                                     │
        │   surface_layer_initial → SURFACE / SUBSURFACE / BULK  │
        │   apps/.../lattice_3d.py:98-117 (assign_3d_site_classes)│
        └────────────────┬───────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │  B3. direction_family_3d                               │
        │   classify Cartesian displacement vector:              │
        │     <110>_inplane / <100>_inplane / <111>_interlayer / │
        │     <001>_exchange / unresolved                        │
        │   apps/.../lattice_3d.py:288-319 (classify_direction_xyz)│
        └────────────────┬───────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │  B4. motif_family_3d (8 values, see _MOTIF_TABLE)      │
        │   apps/.../lattice_3d.py:125-141 + 144-167             │
        └────────────────┬───────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │  B5. z-layer reclassifier (post-hoc fix-up)            │
        │   apps/.../classify_lattice_events_parts/07_reclassify │
        │   .py:59-97 (reclassify_by_zlayer)                     │
        └────────────────┬───────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │  B6. environment counts                                │
        │   n_vac_nn1_initial, nn1_count_{Ni,Fe,Cr},             │
        │   nn2_count_{Ni,Fe,Cr}                                 │
        └────────────────────────────────────────────────────────┘
```

### Motif family values (the actual 8 from `_MOTIF_TABLE`)

The full set, defined at `apps/PyKMC_Analysis/Analysis/lattice_3d.py:125-141`:

```
surface_1nn_translation       — surface 1NN in-plane hop
surface_2nn_translation       — surface 2NN diagonal hop
subsurface_1nn_translation    — subsurface 1NN hop
interlayer_translation        — atom moves to a different layer (not exchange)
surface_subsurface_exchange   — atom from layer-1 swaps with vacancy on top
subsurface_exchange           — analogous for deeper layers
concerted_3d                  — multi-atom motion, no clear single mover
unresolved_multisite          — falls outside the geometric classifiers
```

(Older notes sometimes used short forms like `"1NN_hop"` — those are not the live values.)

### Site-class derivation

`apps/PyKMC_Analysis/Analysis/lattice_3d.py:98-117`: `surface_layer_initial == 0` → `surface`; `== 1` → `subsurface`; else → `bulk_like`. (The "top layer" convention is `0`, not `nz-1`.)

### Direction-family derivation

`apps/PyKMC_Analysis/Analysis/lattice_3d.py:288-319`: tolerance-based matching of the Cartesian displacement vector against the expected magnitudes for each Miller-index family. Catch-all is `unresolved`.

### Output

`classified_events.csv` — about 50 columns, one row per fired KMC event. Then Stage C adds 7 more.

---

## Stage C — family registry + assignment

This is "fingerprinting" in the strict sense: each event gets one of 14 declared family identities + a bucket within that family.

`apps/PyKMC_Analysis/Analysis/families.py` declares `FAMILY_REGISTRY` of 14 `FCCFamily` entries (lines 118-312). Each has 8 fields (`families.py:36-45`):

| Field | Role |
|---|---|
| `family_id` | Stable identifier (e.g. `surface_1NN_inplane`) |
| `family_name` | Human-readable name |
| `movement_template` | Documentation string |
| `seed_rule` | Predicate `row → bool` matching geometry labels |
| `environment_rule` | Function `row → bucket_id_str` (e.g. `"nv1=5"`) |
| `priority` | First-match-wins ordering |
| `fit_barrier: bool` | Whether events feed into rate fitting |
| `review_notes` | Audit / curation notes |

The 14 family ids:

```
surface_1NN_inplane                    surface_subsurface_exchange_up
subsurface_1NN_inplane                 surface_subsurface_exchange_down
bulk_1NN_inplane                       surface_subsurface_exchange_lateral
surface_2NN_diagonal                   subsurface_migration_axial
subsurface_2NN_diagonal                subsurface_migration_interlayer
surface_interlayer_hop                 concerted_multisite        (fit_barrier=False)
subsurface_interlayer_hop              unresolved_multisite       (fit_barrier=False)
```

### Example: `surface_1NN_inplane`

`families.py:123-128`:

- `seed_rule` matches:
  - `motif_family_3d == "surface_1nn_translation"`
  - `direction_family_3d == "<110>_inplane"`
  - `site_class_3d == "surface"`
- `environment_rule = _bucket_by_n_vac_nn1` (lines 64-69) — returns `f"nv1={n_vac_nn1_initial}"`, e.g. `"nv1=5"`.

### Assignment logic

`apps/PyKMC_Analysis/Analysis/family_assignment.py` walks each row:

```
1. Audit override (manual reclassification — keyed by AUDIT_KEY_COLS at line 48:
                    ["composition", "nvac", "temp", "idx_ref"]):
     verdict ∈ {"ignore", "unset", "bad"}      → assignment_status = "excluded"
     verdict == "reclassify"                    → inject override_family_id, skip seed rules
     verdict == "confirm"                       → use seed rules (default)
     no audit row at all (line 169-181)         → use seed rules (implicit pass-through)

2. Seed-rule pass (priority order):
     for family in FAMILY_REGISTRY:
         if family.seed_rule(row):
             family_id = family.family_id
             family_bucket_id = family.environment_rule(row)
             assignment_status = "accepted" if family.fit_barrier else
                                 "excluded:fit_barrier=False"
             break
     else:
         family_id = "unresolved_multisite"
```

### Output: 7 new columns added to `classified_events_with_families.csv`

```
family_id            family_name              family_bucket_id
family_bucket_name   assignment_status        assignment_note
audit_excluded
```

This file (81,322 rows × 63 columns) is the contract. Both downstream consumers (pylatkmc and `apps/.../kmos_export/`) read it.

---

## Stage D — pylatkmc ratebuilder turns CSV rows into a 9-axis rate cube

[`pylatkmc/pylatkmc/ratebuilder.py`](../pylatkmc/ratebuilder.py) reads the CSV and projects each row into a 9-axis integer key.

### CSV column → cube axis (verified at `ratebuilder.py:186-230`, `_prepare_dataframe`)

| CSV column | Cube axis (max) | Position |
|---|---|---|
| `site_class_3d` (via `CLASS_MAP`) | `site_class` (3) | 0 |
| `direction_family_3d` (via `DIR_MAP`) | `direction` (5) | 1 |
| `mover_species_ml` (Ni→0, Fe→1, Cr→2) | `mover_species` (3) | 2 |
| `n_vac_nn1_initial` | `n_vac_nn1` (5) | 3 |
| `nn1_count_Fe` | `n_Fe_nn1` (5) | 4 |
| `nn1_count_Cr` | `n_Cr_nn1` (5) | 5 |
| **derived: `_NN2_SHELL_SIZE − Σ(nn2_count_*)`** | `n_vac_nn2` (5) | 6 |
| `nn2_count_Fe` | `n_Fe_nn2` (5) | 7 |
| `nn2_count_Cr` | `n_Cr_nn2` (5) | 8 |
| `energy_barrier` | (aggregated → Arrhenius rate) | — |

`_NN2_SHELL_SIZE = 6` ([`ratebuilder.py:73`](../pylatkmc/ratebuilder.py)) — the bulk-FCC 2NN coordination. Surface atoms with shorter 2NN shells over-count vacancies by 1-2; fallback tiers fix the impact.

Cube size: 3·5·3·5·5·5·5·5·5 = **703,125 entries**. ([`generated/events.h:41`](../models/ni_fe_cr_v1/generated/events.h): `#define PYLATKMC_CUBE_SIZE 703125`.)

### Aggregation (tier 1)

`df.groupby(<9 axes>)` → event-weighted mean `Ea`, count of events. Each populated cell:

```
rate[idx]  = k0 · exp(-Ea / kT)        # f32, pre-exponentiated
Ea_eV[idx] = Ea                          # f32, for logging
count[idx] = n_events                    # u32, provenance
```

### Fallback chain (tiers 2, 5, 6, 7 — no tiers 3 or 4)

The numbering gap is intentional. The module docstring at `ratebuilder.py:3-12` notes that tiers 3 and 4 (mover-collapse and other variants) were planned but deferred during M3b.

| Tier | Function | Rule |
|---|---|---|
| 2 | `_apply_tier2_fallback` | Drop element counts (`n_Fe`, `n_Cr` → 0), look up; copy that rate into the original cell |
| 5 | `_apply_cross_class_fallback` | Borrow from another `site_class` slab via `_CROSS_CLASS_DONORS` (surface ↔ subsurface ↔ bulk_like) |
| 6 | `_apply_tier6_family` | Look up the family's bucket using **`mover_nv1 = vacancy_n_vac_nn1 + 1`** (the offset is `_MOVER_NV1_OFFSET = 1` at `ratebuilder.py:322`) |
| 7 | `_apply_tier7_scalar` | Scalar legacy `rate_lookup_table.csv`; `<110>_inplane` only |

### `_SC_DIR_TO_FAMILIES` (tier-6 mapping)

[`ratebuilder.py:133-150`](../pylatkmc/ratebuilder.py):

```python
{
    (0, 0): ["surface_1NN_inplane"],
    (0, 1): ["surface_1NN_inplane"],
    (0, 2): ["surface_subsurface_exchange_up", "surface_interlayer_hop"],
    (0, 3): ["surface_subsurface_exchange_down",
             "surface_subsurface_exchange_up"],
    (1, 0): ["subsurface_1NN_inplane"],
    (1, 1): ["subsurface_2NN_diagonal"],
    (1, 2): ["subsurface_interlayer_hop", "subsurface_migration_interlayer"],
    (1, 3): ["subsurface_migration_interlayer"],
    (2, 0): ["subsurface_1NN_inplane"],
    (2, 1): ["subsurface_2NN_diagonal"],
    (2, 2): ["subsurface_interlayer_hop", "subsurface_migration_interlayer"],
    (2, 3): ["subsurface_migration_interlayer"],
}
```

The ordered list is tried in sequence; first family with data wins.

### Mover offset is the single most non-obvious thing

The family bucket `nv1=N` is the *moving atom's* vacant 1NN count. The cube axis `n_vac_nn1` is the *vacancy's* vacant 1NN count. For a 1NN hop, the mover sees one extra vacancy (the one it's hopping into) plus all the vacancies the vacancy site sees. So:

```
mover_nv1 = vacancy_n_vac_nn1 + 1
```

Tier 6 applies the offset (`ratebuilder.py:308-322`). Get this wrong and the vacancy dives into the bulk in step 1 (this was the M3b debugging story).

### `.kmcrt` binary layout

Verified at [`pylatkmc/pylatkmc/kmcfmt.py:3-11`](../pylatkmc/kmcfmt.py):

```
u8[8]   magic           = "KMCRTv01"
u32     header_bytes
u8[H]   JSON header     (axis_maxes, strides, temperature_K, k0_Hz,
                         motif_of_class_dir, …)
u32     n_entries
f32[n]  rate_s_inv      (pre-exponentiated)
f32[n]  Ea_eV
u32[n]  count           (0 ⇒ filled by fallback ≥ tier 2)
```

`MAX_COUNT_CAP = 8` (per-axis bin cap) and `MAX_CUBE_ENTRIES = 100_000_000` (~1.2 GB hard stop) at [`spec.py:25-26`](../pylatkmc/spec.py).

---

## Stage E — codegen specialises the C runtime to the model's axis schema

`pylatkmc-gen build` reads the spec, renders four templates into `models/<name>/generated/`. The four templates ([`pylatkmc/codegen.py:110`](../pylatkmc/codegen.py)):

```
events.h.tmpl       — RateKey struct + constants
ratetable.h.tmpl    — RateTable struct + inline ratetable_key()
ratetable.c.tmpl    — ratetable_load() (mmap + JSON header validation)
avail.c.tmpl        — scan_nn1, scan_nn2, avail_rebuild_all
```

### Preprocessor convention

`#@ <text>` lines are *literal output* (with `{name}` f-string substitution); unprefixed lines are Python control flow (`pylatkmc/codegen.py:41-88`). This is the inverse of most templating engines; ported from kmos's `kmos-main/kmos/utils/__init__.py:1449`.

### The generated `RateKey` struct

[`models/ni_fe_cr_v1/generated/events.h:17-27`](../models/ni_fe_cr_v1/generated/events.h):

```c
typedef struct RateKey {
    uint8_t site_class;
    uint8_t direction;
    uint8_t mover_species;
    uint8_t n_vac_nn1;
    uint8_t n_Fe_nn1;
    uint8_t n_Cr_nn1;
    uint8_t n_vac_nn2;
    uint8_t n_Fe_nn2;
    uint8_t n_Cr_nn2;
} RateKey;
```

### The generated `ratetable_key()`

[`models/ni_fe_cr_v1/generated/ratetable.h:64-76`](../models/ni_fe_cr_v1/generated/ratetable.h):

```c
static inline int32_t ratetable_key(const RateTable *rt, const RateKey *k) {
    return
        (int32_t)k->site_class    * rt->strides[0]
      + (int32_t)k->direction     * rt->strides[1]
      + (int32_t)k->mover_species * rt->strides[2]
      + (int32_t)k->n_vac_nn1     * rt->strides[3]
      + (int32_t)k->n_Fe_nn1      * rt->strides[4]
      + (int32_t)k->n_Cr_nn1      * rt->strides[5]
      + (int32_t)k->n_vac_nn2     * rt->strides[6]
      + (int32_t)k->n_Fe_nn2      * rt->strides[7]
      + (int32_t)k->n_Cr_nn2      * rt->strides[8]
    ;
}
```

Inline, branch-free, 9-term multiply-add. Strides come from the loaded `RateTable`. The runtime never branches on the schema because the schema is hard-coded into the function body at codegen time.

CMake links the four generated files against the static `runtime/src/` backbone (kmc, lattice, state, rng, kmcfmt, json_mini, mpi/replica, io/*, main) → one binary per model: `pylatkmc_<name>`.

---

## Stage F — runtime

```
main (runtime/src/main.c:56)
  │
  └──▶ replica_run (runtime/src/mpi/replica.c:105-141)
         │
         ├── initconfig_load()      → State, Lattice
         ├── ratetable_load()       → RateTable (mmap'd .kmcrt)
         ├── avail_alloc()          → AvailEvents
         │
         └── step loop (kmc.c::kmc_step_once at lines 42-72)
              │
              ├─▶ avail_rebuild_all(av, lat, st, rt)        (generated avail.c)
              │     for each vacancy v ∈ st.vac_list:
              │       scan_nn1(lat, st, v, &nn1)            (n_vac, n_Fe, n_Cr,
              │       scan_nn2(lat, st, v, &nn2)             occ_edges)
              │       for each occupied 1NN edge (target, dir):
              │         RateKey k = {…axes…}
              │         idx  = ratetable_key(rt, &k)
              │         rate = rt->rate[idx]                 (pre-exponentiated)
              │         av.events[n] = Event{...key, rate, Ea}
              │         av.cum_rates[n] = av.cum_rates[n-1] + rate
              │       (same loop for occupied 2NN edges)
              │
              ├─▶ U  ∈ [0, av.r_tot)                        (rng.c)
              │   avail_select binary-searches cum_rates    → picks Event ev
              │
              ├─▶ apply_event(ev) → state_swap_vacancy        (kmc.c:35; state.c)
              │   unwrapped_xyz updated for MSD               (kmc.c:37-39)
              │
              ├─▶ dt = -log(U2) / r_tot                      (kmc.c:54)
              │   st.time_s += dt                             (kmc.c:64)
              │
              └─▶ pykmc_out_write_row(...)
                  if sample step: dump XYZ
```

At sim end, [`replica.c:76-182`](../runtime/src/mpi/replica.c) emits `aggregate_summary.json` via `MPI_Gather` of per-rank `ReplicaStats` structs. The output JSON has at least:

```
n_steps_mean / _std / _min / _max
total_time_s_mean / _std / …
mean_msd_A2_mean / _std / …
motif_counts_sum     (per-motif fire counts across replicas)
direction_counts_sum (per-direction fire counts)
```

### Runtime invariants

- `avail_rebuild_all` is GENERATED (`models/<name>/generated/avail.c`), not static. This is what specialises the inner loop to the spec's axis schema.
- Per-step cost is `O(n_vac × 18)` for FCC 1NN+2NN — independent of cube size.
- Rates are read directly from mmap'd memory; no allocation in the hot path.

---

## Worked example — one event end-to-end

**Pick**: 100Ni / T = 500 K / 1 vacancy. The vacancy is on the FCC(100) surface and an in-plane Ni neighbour hops into it. The mover's environment has 5 of its 8 surface 1NN sites vacant (a high-vacancy density region — common in pyKMC training because basin code likes to cluster vacancies).

### Row in `classified_events.csv` (after Stage B)

```
composition          = "100Ni"
temp                 = 500
sim_label            = "T500_NiAlH_full"
idx_ref              = 17442
energy_barrier       = 0.7203 eV
mover_species_ml     = "Ni"
move_dist            = 2.49      # ≈ a/√2 — characteristic 1NN distance
move_dz              = 0.01      # essentially in-plane
motif_family_3d      = "surface_1nn_translation"
site_class_3d        = "surface"
direction_family_3d  = "<110>_inplane"
n_vac_nn1_initial    = 5         # mover's nv1 (NOT vacancy's!)
nn1_count_Ni         = 3
nn1_count_Fe         = 0
nn1_count_Cr         = 0
nn2_count_Ni         = 5
nn2_count_Fe         = 0
nn2_count_Cr         = 0
... ~30 more columns ...
```

### Row in `classified_events_with_families.csv` (after Stage C)

7 columns added; the relevant ones:

```
family_id          = "surface_1NN_inplane"
family_name        = "Surface 1NN in-plane hop"
family_bucket_id   = "nv1=5"        # = "{n_vac_nn1_initial}"
family_bucket_name = "nv1=5"
assignment_status  = "accepted"
assignment_note    = ""
audit_excluded     = False
```

Why `surface_1NN_inplane`? `family_assignment.py` walks the registry; the predicate `motif_family_3d == "surface_1nn_translation" AND site_class_3d == "surface" AND direction_family_3d == "<110>_inplane"` matches first. The bucket comes from `_bucket_by_n_vac_nn1(row)` → `"nv1=5"`.

### Cube cell (after Stage D)

The vacancy itself sees only **4** vacant 1NN at the moment it's about to hop (one fewer than the mover sees; the mover's "extra" was the destination vacancy itself). So the cube key is:

```
(site_class=surface=0, direction=<110>=0, mover=Ni=0,
 n_vac_nn1=4, n_Fe_nn1=0, n_Cr_nn1=0,
 n_vac_nn2=1, n_Fe_nn2=0, n_Cr_nn2=0)
```

Strides for ni_fe_cr_v1 (computed row-major from axis maxes `[3, 5, 3, 5, 5, 5, 5, 5, 5]`):

```
stride[8] = 1
stride[7] = 5
stride[6] = 25
stride[5] = 125
stride[4] = 625
stride[3] = 3125
stride[2] = 15625
stride[1] = 46875
stride[0] = 234375
```

Index:

```
idx = 0·234375 + 0·46875 + 0·15625
    + 4·3125
    + 0·625 + 0·125
    + 1·25
    + 0·5 + 0·1
    = 12500 + 25
    = 12,525
```

What lives at `cube[12525]`? Tier 1 (direct aggregation) finds N events that all key here; computes their event-weighted mean Ea (≈ 0.74 eV for this bucket), then writes:

```
rate[12525]  = 1e13 · exp(−0.74 / 0.0431) ≈ 4.5 × 10⁵  s⁻¹
Ea_eV[12525] = 0.74
count[12525] = N        (e.g. 850 events)
```

Other cells like `(0, 0, 0, 4, 0, 0, 3, 0, 0)` (different `n_vac_nn2`) might have no direct events. Tier 2 fills them by dropping `n_vac_nn2` differences. Tier 5 might have already filled them from a similar surface ↔ subsurface borrow.

### At runtime

The vacancy starts at site `s_v = 17442` on the surface. `avail_rebuild_all` runs:

1. `scan_nn1(s_v)` walks the 8 1NN of `s_v` (surface coordination), counts `n_vac=4`, `n_Fe=0`, `n_Cr=0`, stashes 4 occupied edge indices.
2. `scan_nn2(s_v)` walks the 4 2NN: `n_vac=1`, `n_Fe=0`, `n_Cr=0`.
3. For each of the 4 occupied 1NN edges (i.e. each direction the vacancy could hop), build the `RateKey`. They're all `(0, 0, 0, 4, 0, 0, 1, 0, 0)` because Ni mover, same site_class, same direction (all in-plane), same shell counts. They all hit `idx = 12525` and read the same rate `4.5 × 10⁵`.
4. `av.events` ends up with 4 entries, each with `rate_s_inv = 4.5 × 10⁵`, `cum_rates = [4.5e5, 9.0e5, 1.35e6, 1.8e6]`. `r_tot = 1.8 × 10⁶`.
5. RNG `U ∈ [0, 1.8e6)` → binary search picks one of the four events.
6. `state_swap_vacancy` atomically swaps species at `(s_v, target)`. Vacancy moves.
7. `kmc_time += -log(U2) / 1.8e6  ≈  4 × 10⁻⁷ s` per step on average.
8. Loop.

That's the full life of a single event: from a saddle-point search in pyKMC, through three classification stages, into a 9-axis cube cell, to a rate value the runtime reads in `O(1)` per vacancy per step.

---

## Five invariants worth burning into your head

1. **Mover's nv1 ≠ vacancy's nv1.** Family bucket `nv1=N` is the *mover's* count; cube axis `n_vac_nn1` is the *vacancy's* count; for 1NN hops they differ by exactly 1. Tier 6 fallback applies the offset (`ratebuilder.py:308-322`); tier 1 doesn't need to (it's already grouped by the cube's axis).

2. **The cube is row-major over `(site_class, direction, mover, …shell counts…)`.** Cube size grows multiplicatively; the spec caps individual axes at 8 (`MAX_COUNT_CAP`) and total entries at 100M (`MAX_CUBE_ENTRIES`).

3. **Pre-exponentiated rates are baked at build time.** A `.kmcrt` is for a specific `T` and `k0`. Changing temperature requires a fresh `pylatkmc-gen rate ...` — re-running the runtime at a different T fails an explicit shape-check at load.

4. **The runtime never branches on the schema.** Codegen specialises `ratetable_key()` to the exact axis order; no enums, no tables, just `stride[i]` constants compiled in. That's why pylatkmc is fast despite having 9 axes.

5. **The catalogue has no alloy events yet** (M4 finding). All 81,277 accepted rows have `mover_species_ml="Ni"` and `nn1_count_{Fe,Cr}=0`. The species axes work; tier-2 fills alloy cells with Ni rates. M4b unblocks this.

---

## What this doc deliberately doesn't cover

- **Basin acceleration**: pyKMC has it, pylatkmc doesn't. Time scales differ by ~10¹² when comparing. See `pylatkmc_m4_species_report.md` (upstream workspace doc).
- **Multi-site events** (`concerted_multisite`): defined in the registry, zero events tagged. R4 of the kmos research plan addresses upstream attribution.
- **`unresolved` direction**: ~1.6 % of cube cells; tier-1 has very few events here, the rest stays NaN/zero (rare events the runtime skips at `rate ≤ 0`).
- **Incremental matching**: still on full-rebuild every step. M5/M6 candidate, kmos-style `avail_sites` swap.
- **MPI ensemble plumbing**: `replica.c` aggregator + `MPI_Gather` of `ReplicaStats` structs. Mostly model-agnostic; covered by [`ARCHITECTURE.md`](ARCHITECTURE.md#mpi-ensemble).

---

## Verification

This doc was assembled from a parallel two-agent audit (upstream + downstream halves of the pipeline) on 2026-05-01. Each load-bearing claim has a `path/to/file.py:NNN` cite immediately above. The audits verified 28 downstream claims (all OK) and 19 upstream claims (12 OK, 7 corrections folded in here, principally: motif-name format, the full 8-field `FCCFamily` dataclass, the verdict set, and the 7 columns added by `family_assignment.py`).

If any cite drifts, regenerate by re-running the audit; the agent prompts that produced it are in the session transcript.
