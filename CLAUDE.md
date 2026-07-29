# CLAUDE.md

Guidance for Claude Code in this repository. This file + `docs/` are authoritative; verify any
claim against source. (The old `.agents/AGENT.md` was **deleted** — it documented a retired
flat-rate-cube / `ratebuilder.py` / `.kmcrt` architecture that no longer exists.)

## What pylatkmc is

Species-aware **on-lattice kinetic Monte Carlo** (FCC), v0.3, Python 3.10–3.13. A TOML model spec
plus a curated FCC family rate catalogue (CSV) are translated by Python **codegen** into one
specialised C file, compiled against a static C+MPI runtime into **one binary per model**. Design
(spec-driven codegen, pattern-DB decision tree, O(1) avail-sites/BKL) is ported from kmos.

Three layers, one direction of dependency:

1. **Python codegen** — `pylatkmc/`: `loader.py` (TOML → `ModelSpec`), `translator.py`
   (family CSV → `list[Process]`), `decision_tree.py` (Processes → nested-switch `touchup_a` +
   rate table), `codegen.py` (`generate()` → `proclist.{c,h}`). `processes.py` is the frozen
   pydantic Process IR; `spec.py` the spec contract; `rate_expression.py`/`dissolution_rate.py`
   the rate laws. **Phase B adds a second, explicitly-selected translation path**: when
   `[rate_data].event_class_table` names an EventClass Parquet catalogue (Phase A,
   `pylatkmc/ingest/`), `generate()` routes through `translator_v2.py` (catalogue →
   species-resolved, D4h-orientation-expanded `LatticePattern`s) + `pattern_codegen.py`
   (packed static pattern tables + a generic matcher emitted into `proclist.c`) instead of
   the family-CSV/nested-switch pipeline. The v2 path lazily imports `pylatkmc.ingest`
   (needs the `[ingest]` extras); the bare core stays importable without them.
2. **Generated C** — `models/<name>/generated/proclist.{c,h}`: model-specific, **committed** so
   users compile without regenerating. Codegen emits **only** these two files.
3. **Static C runtime** — `runtime/src/{core,io,mpi}/`: model-agnostic backbone (lattice/coord
   codes, state, avail_sites, active_filter, KMC step loop, INI/kmcinit/xyz I/O, per-rank MPI
   replicas). Never generated.

`pylatkmc/ingest/` is the optional pyKMC→pylatkmc bridge (builds the curated catalogue + HTST ν₀
prefactors); **the core never imports it**. Install via `pip install -e ".[ingest]"`.

## The CLI

`pylatkmc-gen` has **exactly four** subcommands (`pylatkmc/cli.py`): `build` (the only writer →
`<spec_dir>/generated/proclist.{c,h}`), `info`, `processes` (read-only; `--family-csv` optional),
`clean`. There is **no** `rate`/`provenance` subcommand. The ingest pipeline is a **separate** CLI:
`python -m pylatkmc.ingest.cli` with **five** subcommands — `recover` (per-bucket Vineyard ν₀ from
trajectories, needs LAMMPS) and four pure ones over an `EventClass` Parquet catalogue: `build`
(reference table → catalogue via the robust pinned-h frame fit; mover-keyed G3 per the 2026-07-29
over-snapping memo — `FRAME_UNFIT` / `MOVER_OFFLATTICE` rows are dropped at build into the sidecar
ledger `<out>_discarded.parquet`, counted, never silent; ≥0.5 Å static bystanders are masked to
`WILDCARD` in the context), `qc` (QC screens → schema-v2 QC'd Parquet; dE-spread now
QUARANTINES per the 2026-07-22 memo §3.5; `--measured-refs` stamps `nu0_pair_policy` =
`harvested_pair`/`pending_research` — the latter is skip-counted by `translator_v2`, never emitted
as measured procs), `graduate` (re-search agreement gate, ±0.05 eV → pending class converts to
measured; disagreements go to the review list as `CONTEXT_SUSPECT`), and `merge` (class-level union
of per-run QC'd catalogues on `class_id`; re-runs QC on merged member lists).

## Models

| Model | What | Regenerates in a bare clone? |
|---|---|---|
| `ni_example` | self-contained pure-Ni demo; **vendors** its catalogue in `data/` | **yes** — start here |
| `ni_fe_cr_v1` | production Ni-Fe-Cr | no — `[rate_data].family_table` resolves to `../../../apps/PyKMC_Analysis/…`, an outer workspace **outside this repo** |
| `ni_dissolution_demo` | electrochemical dissolution demo; reuses `ni_fe_cr_v1`'s catalogue for hops + an analytical `[dissolution]` family from a local `epsilon_table.toml` | no (same outer catalogue); the dissolution family is analytical |

All three still **compile** standalone from their committed `generated/` proclist.

## Rates are evaluated at RUNTIME, not baked (the biggest trap)

`RateConst = {prefactor_Hz, Ea_eV, is_electrochemical, _pad}` (24 B). `rateconst_eval(rc, T, φ)`
computes the rate at run time. **One binary runs at any temperature and any overpotential** — there
is no T-mismatch error path anywhere. Do **not** re-bake T into the prefactor. (Older `docs/` pages
and the deleted `.agents/AGENT.md` claim rates are baked-per-T and that a T-mismatch errors in
`state.c` — both false.)

## Invariants — things that break silently

- **Family-CSV (v0.3) diffusion hops are Ni-only — now stated, not silent.** The old
  `mover_species='Ni'` default is DEAD: `translate_all()` requires the argument
  (keyword-only) and `codegen.generate()`/`cli.py` pass `"Ni"` explicitly, because the family
  CSV carries no species information. The **species-resolved path is `translator_v2`**
  (EventClass catalogue): mover species come from each class's delta. Species bridge between
  the ingest `Occ` enum and the runtime `Species` enum is **by NAME only** — their integers
  DISAGREE (`Occ.CR=2, Occ.FE=3` vs `SP_FE=2, SP_CR=3`); mapping by integer silently swaps
  Cr and Fe.
- **`RateConst` is typedef'd in multiple translation units that must stay in lockstep** —
  `decision_tree.emit_rate_table` and `pattern_codegen.emit_v2_rate_table` (each into its
  path's `proclist.c`) and `codegen._PROCLIST_H_TEMPLATE` (into `proclist.h`); `proclist.c`
  does **not** include `proclist.h`. `_Static_assert(sizeof==24)` guards size, **not field
  order**. A one-sided reorder passes the assert and reads garbage rates.
- **Codegen must be byte-deterministic** across `PYTHONHASHSEED`. Tie-breaks use stable string
  sorts — never `hash()`/set/dict iteration order. A regression test diffs two seeds.
- **`generated/proclist.{c,h}` is committed; CI links it and never regenerates/diffs it.** Any
  emitter change that alters output requires regenerating **every** model's proclist and committing
  it. Only `ni_example` regenerates without the outer-workspace catalogue — if you can't regenerate
  the others, flag the mismatch; don't ship a partial set.
- **`ShellCondition` is an exact-count gate with a `-1` sentinel.** A coord that resolves to an
  absent/stub site leaves the count at `-1`, which matches no count (incl. 0), so the Process
  **silently never fires** — looks like "rate too low," not "gate never matched."
- **`coord_table` absent-neighbour sentinel is `n_sites`, NOT `-1`** (and `species[n_sites]=255`
  makes void reads a no-op). Three docstrings still say `-1` (`lattice.h`, `coord_codes.h`) — they
  are wrong; **don't** change the sentinel to match them (→ out-of-bounds / corruption).
- **The v2 integer site grid lives in the RUNTIME slab frame, not the crystal frame.** The
  runtime slab's in-plane axes are the crystal **[110]** directions (in-plane 1NN at
  `(±nn_d, 0, 0)`, `coord_codes.c`), so sites form the same-parity sublattice
  (`u ≡ v ≡ w mod 2`) of a **tetragonal** grid `(nn_d/2, nn_d/2, nn_d/√2)` — NOT the a/2
  cubic grid the ingest identity layer uses. `translator_v2.to_runtime_frame` bridges with
  `(u,v,w) = (i+j, j−i, k)`, and the D4h orientation transversal must be computed AFTER
  that map (coset representatives don't survive the frame change). `lattice_build_site_grid`
  rejects off-grid/off-sublattice configs with `-EINVAL` at startup. Two corollaries:
  (1) **saddle tokens bind to movers by CRYSTAL-frame rank** (Phase A `start_rank` order) —
  `to_runtime_frame` does not preserve lex order, so sorting the runtime offsets mis-binds
  tokens on concerted multi-mover classes (`_movers_in_token_order`); (2) **the grid wraps
  every axis**, so a vacuum gap thinner than the pattern reach would alias offsets onto the
  far surface — the generated proclist.h exposes `PYLATKMC_V2_MAX_REACH_{IJ,K}` and
  replica.c refuses such configs at startup (`lattice_max_empty_axis_run`).
- **v2 matcher EMPTY semantics are asymmetric by design.** A context `EMPTY` row matches
  `SP_VACANT` **or** an absent site (stub 255) — harvest-side EMPTY can't distinguish a
  vacancy from vacuum beyond the slab. A **delta** `Vacant` row is strict `SP_VACANT`: the
  site must exist to receive an atom (adatom moves onto non-sites correctly never fire).
- **v2 translation skips are counted, never silent** (`TranslationReport`): empty-delta,
  non-conserving (`delta_atoms != 0`, off by default — these would fire as spontaneous
  atom creation/deletion), token-mismatch, unsupported predicates, offset overflow. On the
  2026-07-18 production NiCr catalogue: 439 classes → 275 translated / 4392 oriented procs.
  An all-skipped (empty) catalogue emits a compilable stub proclist — the empty rate-table
  branch still carries the `RateConst` typedef the NULL public glue references (both paths).
- **Phase C is an ADDITIVE, gated third layer on the v2 path** (`pylatkmc/surrogate_codegen.py`
  + `runtime/src/core/surrogate.{c,h}`; approved in `onlattice_design/PHASEC_RATE_MODEL_DECISION.md`).
  Triggered only when the catalogue is stamped (`nu0_pair_policy=="harvested_pair"`):
  (a) **measured classes fire raw harvested pairs** — one RateConst per member (`nu0_f_list_hz[i]`,
  already Hz — do **not** ×1e12; `barriers_eV[i]`), so `n × orientation_count` procs per class
  (singletons are 1:1); **quarantined classes are excluded and counted** (`skipped_quarantined`);
  and a **machine-readable provenance** block (`v2_class_ids` + per-proc `v2_proc_{class,member,
  channel,v6_ea}`) replaces the comment-only provenance. (b) an optional `[rate_data].surrogate_model`
  (an `esym_model.json`) bakes the E_sym model + per-1NN-direction feature tables and enables a
  **runtime surrogate rate channel** for generic 1NN vacancy hops not covered by a measured proc.
  Guard rails: the whole channel + `phasec.out` + provenance consumption sit behind
  `#ifdef PYLATKMC_HAS_SURROGATE` (defined only when a model is baked) so v0.3 / schema-1 output
  stays **byte-identical** (verified on `ni_example`); the `Surrogate`/`SurrDir`/`SurrSite` struct
  layout in `surrogate.h` is in **lockstep** with what `emit_surrogate_tables` bakes into proclist.c
  (proclist.c `#include`s `surrogate.h`, so no duplicate typedef — but never edit one without the
  other); the surrogate feature reductions are an **exact port** of `pylatkmc/ingest/surrogate.py`'s
  map-level functions (the C-vs-Python `test_surrogate_parity` locks them to ≤1e-10; a drift there is
  the silent-wrong-rate trap). The KRA barrier `Ea_hat = E_sym + ½·ΔE_H` is **DB-exact by
  construction** (two-origin symmetric E_sym + midpoint-mask ΔΦ). `measured_anchored_form` (N6
  staged switch) ships **OFF** — flag only, no behaviour.
- **Dissolution under-budgeting silently caps events.** The vac list is fixed-size
  (`n_vac_initial + max(max_dissolution_events, 4)`); past the cap, `state_apply_actions` returns
  `-EINVAL` and no-ops, but the discarded return + unconditional `n_dissolution++` + advancing
  clock make the run *plateau* with no error. Default `max_dissolution_events=0` ⇒ only 4 events;
  default `overpotential_phi_eV=0` ⇒ effectively no dissolution at all.
- **`dissolution_prefactor_Hz` runtime override** silently replaces the baked prefactor for **all**
  electrochemical Processes when `> 0` (a value of exactly `0` means "use baked," not "set to 0").
- **`KB_EV_PER_K` has one source** (`rate_expression.py`), mirrored into the generated C macro and
  into `dissolution_rate.py` (test-guarded). Don't introduce a second kB. Keep `dissolution_rate.py`
  pure-stdlib — it is byte-duplicated in the sibling pyKMC repo (cross-check test).
- **`key.axes` / rate-cube machinery is validated but VESTIGIAL.** `spec.py` still enforces
  `Key/KeyAxis`, the permanent `site_class`/`direction` axes, and `n_cube_entries()`, and the
  loader **requires** a `[[key.axes]]` block — but the translator → IR → decision-tree path drives
  emission, *not* the axes. Don't present axes as the codegen driver.
- **Bystanders are a stub** — `_expand_bystanders` raises; non-scalar `rate_constant` raises.
  Today's catalogue emits none, so these hard-fail only if a future catalogue adds species-count
  axes.
- **Inert INI keys**: `summary_every` (`summary.json` is written once at end only),
  `rng_replay_path`, and `ratetable_path` are accepted but never acted on.

## Build / run / test — facts (procedures live in skills & agents)

```bash
pip install -e ".[dev]"                                  # pydantic/numpy + pytest/ruff/mypy
pylatkmc-gen build models/<m>/<m>.kmcspec.toml           # → generated/proclist.{c,h}
cmake -B build -DMODEL=<m> && cmake --build build -j4    # → build/pylatkmc_<m> (MPI + C11 required)
mpirun -n N build/pylatkmc_<m> input.ini                 # one KMC replica per rank
pytest tests/unit_py/ -q                                 # the default + only CI suite
ruff check pylatkmc/ tests/ tools/ && mypy pylatkmc/     # ruff = hard gate; mypy strict, advisory
```

- `-DMODEL` is a **CACHED** cmake var (default `ni_fe_cr_v1`) — re-run the configure step when
  switching models. `REQUIRE_GENERATED=ON` (default) hard-fails if `generated/` has no `.c`.
- Outputs: `<output_root>/replica_NNNN/` (`trajkmc.xyz`, `pykmc.out`, `summary.json`) + rank-0
  `aggregate_summary.json`. `pykmc.out` columns (space-delimited, 9):
  `step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site` — **no** motif/direction column
  (a surrogate-channel fire logs `proc_id = -1` here; its detail is in `phasec.out`).
  A **Phase C surrogate model** additionally emits `phasec.out`
  (`step k_flag_frac_inst k_flag_frac_cum n_surr_inst n_surr_fired n_meas_fired v6_absresid_mean
  v6_absresid_max`) + `flag_registry.csv` (the priority re-search list, sorted by
  `carried_flux·max(n_fired,1)`), and extra `summary.json`/`aggregate_summary.json` fields
  (`flagged_flux_fraction_cum`, `n_surrogate_fired`, `n_measured_fired`, `v6_*`, model versions).
  Full INI key list: `set_key` in `runtime/src/io/config_reader.c` (incl. the inert-safe
  `[surrogate]` block: `surrogate_enable`, `k_floor_Hz`, `leverage_gate`, `flux_threshold`,
  `flag_registry_capacity`).
- Build the `.kmcinit` referenced by `paths.initconfig_path` with `tools/build_initial_config.py`
  or `tools/xyz_to_kmcinit.py` — don't hand-roll the binary format (the `initconfig.h` docstring's
  field order is stale; `initconfig.c` is authoritative).
- `tests/unit_py/` is the only suite a bare `pytest`/CI runs. ctypes tests skip without `cc`;
  compile-gate tests skip without cmake/MPI; many tests skip on missing toolchain/data/personal
  paths — **a green run with many skips means little**. `tests/ingest/` needs `[ingest]` extras +
  `PYKMC_KMC_ROOT` and is **not** collected by default. mypy is advisory in CI (`continue-on-error`).

## Where procedures and depth live

- **Dispatched sub-agents** (`.claude/agents/`, zero trigger surface — invoke via the `Task` tool):
  `engine-codegen-runtime` (spec/codegen/runtime edits, add species/family, regenerate), 
  `curate-rate-catalogue` (build the catalogue + HTST ν₀; formerly `ingest-htst-bridge`),
  `cross-engine-validation` (MSD/diffusivity vs off-lattice pyKMC).
- **Skills** (`.claude/skills/`, auto-trigger): `build-run-model`, `verify-pylatkmc-change`.
- **Docs** (`docs/`): `PATTERN_DB.md` (primary: CSV → IR → decision tree → avail_sites → BKL →
  state), `ARCHITECTURE.md`, `HOW_IT_WORKS.md`, `CATALOGUE_SCHEMA.md`, `FAMILY_REGISTRY.md`,
  `INGEST_PIPELINE.md`, `KMOS_COMPARISON.md`, `PYKMC_INTEGRATION.md`. Several predate the
  dissolution merge and still describe the baked-rate model / stale test counts — trust code.

## Agent skills

Per-repo config for the engineering-pipeline skills (`to-prd`, `to-issues`, `triage`, …), written
by `configure-engineering-workflow` (2026-07-17):

- **Issue tracker — local markdown** (`docs/agents/issue-tracker.md`): issues/PRDs live under
  `.scratch/<feature-slug>/` (gitignored, machine-local). No GitHub Issues; PRs are not a triage
  surface.
- **Triage labels** (`docs/agents/triage-labels.md`): the five canonical roles keep their default
  strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded
  in each issue file's `Status:` line.
- **Domain docs** (`docs/agents/domain.md`): single-context — `CONTEXT.md` + `docs/adr/` at the
  repo root (neither exists yet; skills proceed silently until they do).
