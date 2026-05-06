# HOW_IT_WORKS.md — pylatkmc traced end-to-end

**Audience:** readers who want to understand the v0.2 pattern-DB
pipeline by following one concrete event from catalogue row to fired
hop. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) and
[`PATTERN_DB.md`](PATTERN_DB.md) first.

**Last updated:** 2026-05-06 (v0.2.0).

---

## The example: a single Ni surface 1NN hop

We'll trace a Ni atom hopping into a vacant site at the +x in-plane
1NN of its current position on an FCC(100) surface. Catalogue family:
`surface_1NN_inplane`. Bucket: `nv1=1_nv2=2` (1 vacant 1NN of the
mover, 2 vacant 2NN). At T=500 K with k0=10¹³ Hz this corresponds to
one specific row in the family rate table.

```
Initial:                          After hop:
  layer 0:  Ni Ni Ni                 Ni Ni Ni
  layer 0:  Ni V  Ni     ─────►      Ni Ni V    (V at site +x of original)
  layer 0:  Ni Ni Ni                 Ni Ni Ni
                ^                          ^
            anchor site                hop destination
```

The anchor (vacancy site) and the +x site swap species: V → Ni at
anchor, Ni → V at +x.

---

## Stage 1 — pyKMC produces the catalogue row

Upstream (in `apps/PyKMC_Analysis/Analysis/`), pyKMC simulations
produce `classified_events_with_families.csv`. After aggregation into
`rate_lookup_table_family.csv`, the row for our event looks like:

```
family_id              ,family_bucket_id,n_events,Ea_mean_eV,Ea_std_eV,...
surface_1NN_inplane    ,nv1=1_nv2=2     ,4271    ,0.6121    ,0.0892   ,...
```

Key fields:
- **`family_id = surface_1NN_inplane`** — the family registry knows
  this is a 4-direction in-plane hop (±x, ±y).
- **`family_bucket_id = nv1=1_nv2=2`** — bucketed by (n_vacant_1NN,
  n_vacant_2NN) of the mover atom.
- **`n_events = 4271`** — pyKMC saw 4271 distinct events that landed
  in this bucket.
- **`Ea_mean_eV = 0.6121`** — bucket-mean activation energy.

Source: [`pylatkmc/translator.py:FamilyBucketRow`](../pylatkmc/translator.py).

---

## Stage 2 — translator emits Processes

`pylatkmc-gen build` calls
[`translator.translate_all`](../pylatkmc/translator.py) with the rows
above. For `surface_1NN_inplane`, the direction table is:

```python
SURFACE_1NN_INPLANE_DIRS = (
    CoordOffset(code="NC_NN1_PX"),
    CoordOffset(code="NC_NN1_MX"),
    CoordOffset(code="NC_NN1_PY"),
    CoordOffset(code="NC_NN1_MY"),
)
```

`_emit_simple_2action_hop(family_id="surface_1NN_inplane",
bucket_id="nv1=1_nv2=2", direction=NC_NN1_PX, mover_species="Ni",
Ea_eV=0.6121, rate_Hz=...)` produces:

```python
Process(
    name="surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni",
    family_id="surface_1NN_inplane",
    Ea_eV=0.6121,
    rate_constant=1.0e13 * exp(-0.6121 / (8.617e-5 * 500)) ≈ 6.32e6,
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

Three more Processes are emitted for the same bucket (`NC_NN1_MX`,
`NC_NN1_PY`, `NC_NN1_MY`); all share the same rate. For 56 buckets ×
9 fit-barrier families, ~358 total Processes are produced.

Inspect:

```bash
$ pylatkmc-gen processes models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
…
Total Processes: 358
Processes per family:
  bulk_1NN_inplane                            48 Processes
  subsurface_1NN_inplane                     192 Processes
  surface_1NN_inplane                         16 Processes
  …
Ea_eV range: min=0.001  max=1.198
```

---

## Stage 3 — codegen emits proclist.c

`generate(spec, out_dir)` (in
[`pylatkmc/codegen.py`](../pylatkmc/codegen.py)) calls four M-B
emitters and bundles their output into one `proclist.c`:

### 3.1 — `emit_process_enum`

```c
enum {
    P_bulk_1nn_inplane__nv1_0_nv2_1__nn1_px__ni,
    …
    P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni,    // ← our process
    …
    N_PROCS                                            // = 358
};
```

### 3.2 — `emit_rate_table`

```c
typedef struct { double rate; double Ea_eV; } RateConst;
static const RateConst rate_table[N_PROCS] = {
    …
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni] = {
        .rate   = 6.3204182e+06,
        .Ea_eV  = 0.612100
    },
    …
};
```

### 3.3 — `emit_apply_actions`

```c
static HopOutcome apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni(
    State *st, const Lattice *lat, int site)
{
    StateAction acts[2] = {
        { .site = site,                                        /* anchor */
          .before = SP_VACANT, .after = SP_NI },
        { .site = lat->coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX],
          .before = SP_NI,     .after = SP_VACANT },
    };
    state_apply_actions(st, acts, 2, SP_VACANT);
    return (HopOutcome){
        .v_origin = acts[0].site,    /* the V→Ni action's site */
        .v_dest   = acts[1].site,    /* the Ni→V action's site */
    };
}

…

static const ApplyFn apply_table[N_PROCS] = {
    …
    [P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni] =
        apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni,
    …
};
```

### 3.4 — `compile_decision_tree(processes, "touchup_a")`

```c
void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {
    switch (st->species[site]) {                  // most-shared coord = NC_ANCHOR
        case SP_VACANT:
            switch (st->species[lat->coord_table[site * N_NEIGHBOUR_CODES
                                                  + NC_NN1_PX]]) {
                case SP_NI:
                    /* every Process whose conditions are
                     * (NC_ANCHOR=Vacant, NC_NN1_PX=Ni, …) gets enrolled */
                    avail_sites_add(as,
                        P_surface_1nn_inplane__nv1_0_nv2_0__nn1_px__ni, site);
                    avail_sites_add(as,
                        P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni, site);
                    /* (more Processes here for other buckets) */
                    break;
                case SP_FE:
                    avail_sites_add(as,
                        P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__fe, site);
                    …
            }
            …  /* deeper switches for other coords */
            break;
        case SP_NI:
            …  /* Processes with anchor species = Ni */
            break;
    }
}
```

Final proclist.c is ~5000 lines for ni_fe_cr_v1.

---

## Stage 4 — CMake builds the binary

```bash
$ cmake -B build -DMODEL=ni_fe_cr_v1
$ cmake --build build -j 4
…
[100%] Linking C executable pylatkmc_ni_fe_cr_v1
[100%] Built target pylatkmc_ni_fe_cr_v1
```

CMake's `file(GLOB)` picks up:
- All `runtime/src/{core,io,mpi}/*.c` (the static backbone)
- `models/ni_fe_cr_v1/generated/proclist.c` (everything model-specific)
- `runtime/src/main.c`

Linked into `pylatkmc_lib.a` (static archive) + the executable.

---

## Stage 5 — runtime startup

`replica_run` in
[`runtime/src/mpi/replica.c`](../runtime/src/mpi/replica.c):

```c
initconfig_load(cfg->initconfig_path, &lat, &st);       // mmap .kmcinit
lattice_build_coord_table(&lat);                        // populate coord_table
                                                         //   (see Stage 6 below)
avail_sites_alloc(&as, pylatkmc_n_procs, lat.n_sites);
for (int p = 0; p < pylatkmc_n_procs; ++p)
    avail_sites_set_rate(as, p, pylatkmc_rate_table[p].rate);

active_filter_alloc(&af, lat.n_sites, /*bulk_threshold=*/12);
active_filter_compute_static(af, &lat);                 // mark surface/edge sites

rng_seed(&rng, cfg->base_seed, rank);

KmcContext ctx = { .lat = &lat, .st = &st, .as = as, .af = af, .rng = &rng, … };
kmc_run(&ctx);                                          // step loop
```

---

## Stage 6 — coord_table built once

`lattice_build_coord_table(lat)` (in
[`runtime/src/core/lattice.c`](../runtime/src/core/lattice.c)) walks
each site's nn1/nn2 CSR adjacency, computes the PBC-wrapped Cartesian
delta for each edge in `nn_d` units, and matches it against
`NEIGHBOUR_CODE_DELTAS[]` within `COORD_MATCH_TOL = 0.05 nn_d`.

For our anchor site `s` in the middle of a (100) surface:

| Edge → neighbour | Cartesian delta `(dx,dy,dz)/nn_d` | Matched code |
|---|---|---|
| `s+1` (in-plane +y) | `(0, 1, 0)` | `NC_NN1_PY` |
| `s-1` (in-plane -y) | `(0, -1, 0)` | `NC_NN1_MY` |
| `s+8` (in-plane +x) | `(1, 0, 0)` | `NC_NN1_PX`  ← **the +x neighbour** |
| `s-8` (in-plane -x) | `(-1, 0, 0)` | `NC_NN1_MX` |
| `s+64..s+71` (cross-layer up to layer 1) | `(±0.5, ±0.5, +0.707)` | `NC_NN1_UP_*` |
| `s+9, s+15, s+57, s+63` (in-plane diagonal 2NN) | `(±1, ±1, 0)` | `NC_NN2_DIAG_*` |
| `s+128` (axial 2NN through PBC z-wrap) | `(0, 0, +√2)` | `NC_NN2_PZ` |

Result: `lat->coord_table[s * 23 + NC_NN1_PX]` is set to the absolute
site index of the +x neighbour. Reads thereafter are O(1).

---

## Stage 7 — the per-step loop

`kmc_step_once` in
[`runtime/src/core/kmc.c`](../runtime/src/core/kmc.c):

### 7.1 — `active_filter_rescan(af, lat, st)`

The filter's static mask flagged surface and edge sites at startup.
Now we OR in: every vacancy + every 1NN of vacancy.

For our setup (1 surface vacancy at site `s`), the active set contains
~13 sites: `s` itself + 8 1NN of `s` + the 4-corner static-active sites
on the slab boundary.

### 7.2 — `avail_sites_clear(as)`

Wipes every `(proc, site)` enrolment from the previous step. O(n_procs
× active sites) but only walks the actually-enrolled entries; rates
stay.

### 7.3 — Touchup at every active site

```c
for (int i = 0; i < n_active; ++i) {
    touchup_a(lat, st, as, active_filter_site_at(af, i));
}
```

When `touchup_a` runs at our anchor site `s`:
- `st->species[s] == SP_VACANT` → enters `case SP_VACANT:` branch
- `st->species[coord_table[s * 23 + NC_NN1_PX]]` → reads species at +x
- That site is occupied by Ni → enters `case SP_NI:` branch
- Multiple Processes enrol at `s`: one per `(family, bucket, mover)`
  triple matching the conditions. Among them is our target:
  `P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni`.

After the per-site touchups complete, `as` has, for each Process, a
dense list of all sites where that Process is currently eligible.

### 7.4 — `avail_sites_refresh_cum_rates(as)`

```c
cum = 0
for p in 0..N_PROCS:
    cum += rates[p] * n_sites_per_proc[p]
    cum_rates[p] = cum
```

After this, `r_tot = avail_sites_r_tot(as)` is the total event rate
across all enrolled (proc, site) pairs.

### 7.5 — BKL select

```c
double r1, r2;
rng_next2(rng, &r1, &r2);
double dt     = -log(r2) / r_tot;
double target = r1 * r_tot;
avail_sites_select(as, target, &proc, &site);
```

`avail_sites_select` binary-searches `cum_rates` for the smallest `p`
with `cum_rates[p] > target`, then picks a slot uniformly within
proc `p`'s enrolled sites:

```c
int32_t k = (int32_t)((target - cum_rates[proc-1]) / rates[proc]);
*out_site = site_at[proc * n_sites + k];
```

For our example, suppose RNG gives `r1 = 0.234` and the cumulative
rate happens to land exactly on
`P_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni`. The site `k = 0`
inside that proc's list is our anchor `s`.

### 7.6 — `apply_event(ctx, proc, site)`

```c
HopOutcome ho = pylatkmc_apply_table[proc](st, lat, site);
```

Dispatches into
`apply_actions_surface_1nn_inplane__nv1_1_nv2_2__nn1_px__ni(st, lat, s)`,
which runs:

```c
StateAction acts[2] = {
    { .site = s,                          .before = SP_VACANT, .after = SP_NI     },
    { .site = lat->coord_table[s * 23 + NC_NN1_PX],
                                          .before = SP_NI,     .after = SP_VACANT },
};
state_apply_actions(st, acts, 2, SP_VACANT);
return (HopOutcome){ .v_origin = s, .v_dest = lat->coord_table[…] };
```

`state_apply_actions` (in
[`runtime/src/core/state_actions.c`](../runtime/src/core/state_actions.c))
does five passes:

1. **Validate** every action's `before` against `st->species[]`. For
   our example: `species[s] == SP_VACANT` ✓, `species[+x] == SP_NI` ✓.
2. **Reject duplicate sites.** Both actions reference distinct sites ✓.
3. **Check n_vac overflow.** delta = (+1 vacancy at +x) + (-1 vacancy
   at s) = 0; n_vac stays at 1, ≤ n_vac_max ✓.
4. **Mutate species.** `species[s] = SP_NI`, `species[+x] = SP_VACANT`.
5. **Update vac_list.** Remove `s` from vac_list (swap-last); add `+x`
   to vac_list. n_vac stays at 1; old slot 0 now holds `+x`.

### 7.7 — MSD bookkeeping

Back in `kmc.c:apply_event`:

```c
if (ho.v_origin >= 0 && ho.v_dest >= 0) {
    int32_t new_idx = st->vac_idx_of[ho.v_dest];
    /* Cartesian delta from origin to dest, with PBC. */
    double dx = positions[+x] - positions[s];   // ≈ +nn_d
    double dy = ...;                            // 0
    double dz = ...;                            // 0
    st->unwrapped_xyz[3 * new_idx + 0] += dx;
    /* dy, dz add 0 */
}
```

After the hop: `st->unwrapped_xyz[0:3]` accumulates `+nn_d` in x. Over
many hops this grows; the per-replica `mean_msd_A2` reported at the
end of the run integrates this displacement squared.

### 7.8 — Tick

```c
ctx->st->time_s += dt;
ctx->st->step   += 1;
```

If `step % cfg->sample_every == 0`, write the trajectory frame
(`xyz_writer`) and the per-step log row (`pykmc_out`).

---

## Stage 8 — pykmc.out logged

For our example step at step=100:

```
# step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site
100  3.911813084e-11  1.572640e-13  1  2.174612e+12  6.320418e+06  0.6121  142  44
```

- `proc_id = 142` is the integer index of our Process; cross-reference
  the generated enum in proclist.c to map back to the human-readable
  name.
- `site = 44` is the anchor site index.
- `k_event = 6.32e6` is the rate this Process contributes (one
  invocation worth).
- `Ea_eV = 0.6121` matches the bucket's mean.

---

## Stage 9 — aggregate summary

After all replicas finish, rank 0 collects per-replica `ReplicaStats`
via MPI_Gather and writes:

```json
{
  "n_replicas": 2,
  "n_success": 2,
  "n_failed": 0,
  "base_seed": 42,
  "temperature_K": 500.000,
  "n_procs": 358,
  "n_steps_mean": 100000.0,
  "total_time_s_mean": 4.039998173e-08,
  "mean_msd_A2_mean":  6.792775e+05,
  …
  "replicas": [
    {"rank": 0, "n_steps": 100000, "total_time_s": 4.04e-08, "mean_msd_A2": 4.49e+05},
    {"rank": 1, "n_steps": 100000, "total_time_s": 4.04e-08, "mean_msd_A2": 9.10e+05}
  ]
}
```

---

## What's NOT shown in this trace

- **Multi-site events.** A triple hop has `len(actions) = 3` and the
  `apply_actions_<name>` function builds a `StateAction[3]` array.
  v0.2 emits these from the catalogue but the MSD heuristic in
  `apply_event` skips them (one-time stderr warning).
- **Bystanders.** The IR supports rate-modulating soft counts but
  v0.2's translator and codegen don't use them (rates are scalar
  per Process). Adding Bystanders is a future M-A++.
- **Active-volume / spatial bounding box.** pyKMC has this but
  pylatkmc deliberately doesn't.
- **IRA-style reconstruction.** Lives in pyKMC, not here.

---

## See also

- [`PATTERN_DB.md`](PATTERN_DB.md) — full pipeline reference.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — three-layer overview.
- [`PYKMC_INTEGRATION.md`](PYKMC_INTEGRATION.md) — interaction with the
  upstream catalogue.
