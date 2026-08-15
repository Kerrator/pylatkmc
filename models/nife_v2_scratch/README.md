# `nife_v2_scratch` — NiFe measured-rates model (Phase B/C v2 path)

The first pylatkmc model whose rates come from **measured Ni-Fe kinetics**. It is the
sibling of [`nicr_v2_scratch`](../nicr_v2_scratch/): same v2 pipeline
(`[rate_data].event_class_table` → `translator_v2` → `pattern_codegen`), different
catalogue and **no surrogate model**.

## Where the rates come from

```
60 NiFe production runs (2026-08-14 full campaign, CANON v3, per-alloy split)
   → merged_v3_NiFe.parquet                      (20,293 classes, none stamped)
   → 2026-08-15 re-search graduation leg          (±0.05 eV agreement gate)
   → merged_v3_NiFe_graduated_2026-08-15.parquet  (180 classes stamped `harvested_pair`)
   → pylatkmc-gen build → generated/proclist.c    (14,976 oriented procs)
```

The spec points at the graduated parquet under
`/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/` — **read-only, outside this
repo**. Consequently, and exactly like `ni_fe_cr_v1`, **this model does not regenerate
in a bare clone**; it still *compiles* from the committed `generated/proclist.{c,h}`.

Only the 180 graduated classes are emitted. Everything else in the catalogue is
skip-counted by `translator_v2` (never silently baked):

| Translate result (2026-08-15) | |
|---|---|
| classes in catalogue | 20,293 |
| rate mode | phase-C raw-pairs |
| classes translated | **180** |
| oriented patterns (procs) | **14,976** (180 classes × 16 orientations × members) |
| member rate channels | **936** |
| skipped quarantined | 3,603 |
| skipped pending-research | 16,510 |
| all other skip counters | 0 |

Per-mover split: **Fe mover — 153 classes / 400 member channels / 6,400 procs**
(Eₐ 0.25–0.85 eV); **Ni mover — 27 classes / 536 member channels / 8,576 procs**
(Eₐ 0.37–0.86 eV). Every class is `orientation_count = 16` and single-arrow.

Rates are the **raw harvested (ν₀, Eₐ) pairs** — one `RateConst` per member, not an
aggregate. The re-searched barriers of the graduation gate enter no rate; they were a
validation gate only.

## No surrogate model — on purpose

`[rate_data].surrogate_model` is deliberately **unset**, so the Phase C surrogate rate
channel is compiled out (no `PYLATKMC_HAS_SURROGATE`, no `phasec.out`). The only
existing artifact, `esym_model_v2.json`, is **NiCr-fit with an Fe context range of
`[0,0]`**: every Fe-bearing runtime context trips `SURR_TRIG_SPECIES`, so the surrogate
could only *flag* an Fe gap, never fill one. Baking it here would add a channel that
never fires plus a misleading flag stream. It becomes appropriate only after an
Fe-bearing E_sym refit.

The practical consequence: these 180 measured classes are the **only trained Fe
kinetics** in this binary. Contexts outside them have no rate at all (they simply never
fire) — this is a scoping model for the D1 promotion decision, not a production
NiFe model.

## Spec knobs that do *not* matter here

On the v2 path `temperature_K`, `k0_Hz` and `prefactor_style` are informational only —
they appear in the `proclist.c` preamble comment and nowhere else. Rates are evaluated
at **runtime** from `physics.temperature_K` in `input.ini`
(`k = ν₀·exp(−Eₐ/k_B·T)`), so one binary runs at any temperature. The catalogue itself
is multi-temperature (`t_ref_K` ∈ {300…800 K} across the 180 classes). The
`[[key.axes]]` block is required by the loader but vestigial — it drives nothing.

## Build

```bash
# from the pylatkmc/ repo root — regeneration needs the /data catalogue present
pylatkmc-gen build models/nife_v2_scratch/nife_v2_scratch.kmcspec.toml
cmake -B build_nife -DMODEL=nife_v2_scratch && cmake --build build_nife -j4
#   → build_nife/pylatkmc_nife_v2_scratch
```

`generated/proclist.h` exports `PYLATKMC_V2_MAX_REACH_IJ 8` / `PYLATKMC_V2_MAX_REACH_K 4`
— a configuration whose vacuum gap is thinner than that on any axis is **rejected at
startup** by `replica.c` (the integer site grid wraps every axis, so a thin gap would
alias pattern rows onto the far surface).

No `examples/` are shipped: this model has no validated run configuration yet. Sizing a
slab that satisfies the reach above is the first step toward one.

## Files

| Path | Role |
|---|---|
| `nife_v2_scratch.kmcspec.toml` | the model spec (`event_class_table` → the /data graduated parquet) |
| `generated/proclist.{c,h}` | generated C (committed, so the model builds without the catalogue) |
