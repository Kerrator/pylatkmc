# CLAUDE.md

Guidance for Claude Code when working in this repository.

> This file and `docs/` are authoritative. If an untracked local `.agents/AGENT.md`
> is present in your checkout, treat it as partially stale — it cites
> `pylatkmc-gen rate` / `provenance` subcommands and a `pylatkmc/ratebuilder.py`
> module that no longer exist (rate-building moved to `pylatkmc.ingest`; see
> `docs/INGEST_PIPELINE.md`). Prefer this file when they disagree.

## What pylatkmc is

Species-aware **on-lattice kinetic Monte Carlo**. A TOML model spec plus a curated
rate catalogue (CSV of FCC move families, produced by an upstream off-lattice pyKMC
pipeline) are translated by Python **codegen** into one specialised C file, which is
compiled against a static C+MPI runtime into **one binary per model**. The design
(spec-driven codegen, pattern-DB decision tree, O(1) avail-sites bookkeeping) is
ported from kmos.

Three layers, one direction of dependency:

1. **Python codegen** — `pylatkmc/`: `loader.py` (TOML → `ModelSpec`), `translator.py`
   (family CSV → `list[Process]`), `decision_tree.py` (Processes → nested-switch C),
   `codegen.py` (`generate()` → `proclist.{c,h}`). `processes.py` is the frozen
   pydantic Process IR; `spec.py` the spec contract.
2. **Generated C** — `models/<name>/generated/proclist.{c,h}`: model-specific,
   **committed** so users compile without regenerating.
3. **Static C runtime** — `runtime/src/{core,io,mpi}/`: model-agnostic backbone
   (lattice/coord_codes, state, avail_sites, active_filter, kmc step loop, INI/
   kmcinit/xyz I/O, per-rank MPI replicas). Never generated.

`pylatkmc/ingest/` is the optional pyKMC→pylatkmc bridge (builds the curated
catalogue + HTST ν₀ prefactors); the core never imports it. Install via
`pip install -e ".[ingest]"`.

## Commands

```bash
pip install -e ".[dev]"                                  # pydantic + pytest/ruff/mypy

pylatkmc-gen build models/<m>/<m>.kmcspec.toml           # spec + family CSV → generated/proclist.{c,h}
pylatkmc-gen processes models/<m>/<m>.kmcspec.toml       # inspect catalogue translation (read-only)
pylatkmc-gen info  <spec> | clean <spec>                 # print spec / rm -rf generated/
# (these four are the ONLY subcommands)

cmake -B build -DMODEL=<m> && cmake --build build -j4    # → build/pylatkmc_<m>  (MPI + C11 required)
# MODEL defaults to ni_fe_cr_v1 and is CACHED — re-run the configure step when switching models.
mpirun -n N build/pylatkmc_<m> input.ini                 # one KMC replica per rank

pytest tests/unit_py/ -q                                 # the test suite (testpaths default)
ruff check . && ruff format --check . && mypy pylatkmc/  # lint gates (mypy strict)
```

`input.ini` sections: `[run]` (max_steps, sample_every, base_seed), `[paths]`
(initconfig_path, output_root), `[physics]` (temperature_K, plus
overpotential_phi_eV / dissolution_prefactor_Hz / max_dissolution_events for
dissolution models), `[validation]`. Full key list: `set_key` in
`runtime/src/io/config_reader.c`. Outputs: `<output_root>/replica_NNNN/`
(`trajkmc.xyz`, `pykmc.out`, `summary.json`) + rank-0 `aggregate_summary.json`.
Build the `.kmcinit` referenced by `paths.initconfig_path` with
`tools/build_initial_config.py` (FCC slab generator) or `tools/xyz_to_kmcinit.py`
— don't hand-roll the binary format.

## Models

| Model | What | Regenerates standalone? |
|---|---|---|
| `ni_example` | self-contained pure-Ni 1-vacancy demo; **vendors** its catalogue in `data/` | **yes** — start here |
| `ni_fe_cr_v1` | production Ni-Fe-Cr model | no — `[rate_data]` resolves to `../../../apps/PyKMC_Analysis/...`, an outer workspace **outside this repo**; a standalone clone can only compile it from the committed `generated/` proclist |
| `ni_dissolution_demo` | electrochemical dissolution demo (vacancy-free slab) | hops no (same outer-workspace catalogue); the dissolution family is analytical from its local `epsilon_table.toml` |

All models still **compile** standalone from their committed `generated/` files.

## Invariants — things that break silently

- **`RateConst` is typedef'd in TWO emitters** — `decision_tree.emit_rate_table`
  (into proclist.c) and `codegen._PROCLIST_H_TEMPLATE` (into proclist.h); proclist.c
  does not include proclist.h. Keep them layout-identical. The
  `_Static_assert(sizeof(RateConst) == ...)` guards size, **not field order**.
- **Codegen must be byte-deterministic.** Never order emission by `hash()`/set/dict
  iteration — tie-breaks use stable string sorts. A regression test diffs codegen
  under two `PYTHONHASHSEED`s.
- **`generated/` is committed.** Any emitter change that alters output requires
  regenerating every model's proclist and committing it. Only `ni_example`
  regenerates without the outer-workspace catalogue — if you can't regenerate the
  others, don't commit a partially-regenerated set; flag the mismatch instead.
- **Species and neighbour codes are hand-synced with C.** Codegen emits `SP_<NAME>`
  by upper-casing the spec species — it must exist in
  `runtime/src/core/events_base.h` (errors only at C compile time). Python
  `NEIGHBOUR_CODES` (processes.py) must match the `coord_codes.h` enum **and**
  `NEIGHBOUR_CODE_DELTAS[]` in `coord_codes.c` (enum integers index `coord_table`).
- **`KB_EV_PER_K`** — single source `rate_expression.py`; mirrored into the generated
  C macro and into `dissolution_rate.py` (test-guarded). Don't introduce another kB.
- **`dissolution_rate.py` is duplicated byte-for-byte** in the companion pyKMC repo
  (the cross-check test `test_copies_agree_on_grid` asserts numeric agreement and
  skips when the sibling copy isn't present). Keep it pure-stdlib; no engine imports.
- **The Process IR is frozen pydantic** (hashable; golden-file determinism). Don't
  add mutable state. `Process.name` becomes a C identifier and must be globally
  unique — both translator and decision tree enforce this.
- **`ShellCondition` is an exact-count gate.** If its coord resolves to a missing
  site, the count var stays `-1` and the Process **silently never fires**. The
  dissolution family gates every occupied species (including count 0) so exactly
  one dissolution Process matches per surface atom.
- **Dissolution overpotential is runtime, not baked**: `rateconst_eval(rc, T, phi)`
  subtracts `phi` only for `is_electrochemical` rows, clamped at a barrierless
  floor. Each dissolution adds +1 vacancy; under-budgeting
  `physics.max_dissolution_events` silently caps dissolutions (vac list is
  fixed-size).
- **Bystanders are a stub** — `_expand_bystanders` raises `NotImplementedError`;
  today's catalogue emits none.

## Tests — practical notes

- ctypes tests compile the C-under-test with `cc -std=c11 -Werror` at collection
  (skip if no `cc`); compile-gate tests run real cmake builds (skip without
  cmake/MPI). `tests/unit_c/` is currently empty.
- The compile gates **regenerate into the working tree** — after running them with
  modified codegen, the committed `generated/` files may be dirty. That's expected;
  review and commit (or revert) deliberately.
- `tests/ingest/` needs the `[ingest]` extras; only its **data-dependent** tests
  (Hessian, trajectory recovery) skip when the upstream pyKMC workspace is
  unreachable (`$PYKMC_KMC_ROOT` or an auto-detected parent) — the pure-logic
  family/rate-table tests run regardless. A bare `pytest` collects only
  `tests/unit_py/`.
- CI (`.github/workflows/tests.yml`): pytest matrix (Linux/macOS across the
  supported Python versions), cmake smoke build from the **committed** proclist,
  Linux end-to-end mpirun check. The lint job gates on ruff; mypy is advisory
  (`continue-on-error`).

## Conventions

Python: ruff (line length 100, `E,F,W,I,UP,B,SIM`), mypy **strict** on `pylatkmc/`
— which **includes** `pylatkmc/ingest/` (`tests/` and `tools/` sit outside the
`mypy pylatkmc/` target; ingest only has narrow ruff per-file-ignores, not a mypy
exemption). C: strict ISO C11
(`-Wall -Wextra -Wpedantic`; no declarations directly after a `case` label —
block-wrap them, as the emitters do). Keep models self-contained in
`models/<name>/`. When behaviour changes, update the matching `docs/` page.

## Where to read more

`docs/PATTERN_DB.md` (primary architecture reference: CSV → IR → decision tree →
BKL → state), `docs/ARCHITECTURE.md` (three layers + runtime data structures),
`docs/HOW_IT_WORKS.md` (worked single-hop trace), `docs/CATALOGUE_SCHEMA.md`
(every CSV column), `docs/FAMILY_REGISTRY.md` (the FCC move families),
`docs/INGEST_PIPELINE.md` (catalogue-building runbook), `docs/KMOS_COMPARISON.md`,
`docs/PYKMC_INTEGRATION.md`. `models/ni_example/README.md` is the end-to-end
walkthrough for newcomers.
