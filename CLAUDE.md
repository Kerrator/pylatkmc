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
   the rate laws.
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
`python -m pylatkmc.ingest.cli recover …` (one subcommand).

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

- **Diffusion hops are HARDCODED to mover species `'Ni'`.** `codegen.generate()` calls
  `translate_all()` with no `mover_species`, so every hop emits `SP_NI` regardless of
  `spec.species` (`translator.py` default `'Ni'`). Only **dissolution** is species-aware. A non-Ni
  model compiles and runs but never diffuses its real species — no error at any stage.
- **`RateConst` is typedef'd in TWO translation units** — `decision_tree.emit_rate_table` (into
  `proclist.c`) and `codegen._PROCLIST_H_TEMPLATE` (into `proclist.h`); `proclist.c` does **not**
  include `proclist.h`. `_Static_assert(sizeof==24)` guards size, **not field order**. A one-sided
  reorder passes the assert and reads garbage rates.
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
  `step time_s dt_s n_vac k_tot k_event Ea_eV proc_id site` — **no** motif/direction column.
  Full INI key list: `set_key` in `runtime/src/io/config_reader.c`.
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
