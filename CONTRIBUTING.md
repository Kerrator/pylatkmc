# Contributing to pylatkmc

Thanks for your interest. pylatkmc is an early-stage research code; bug
reports, model contributions, and small focused PRs are all welcome.

## Development setup

```bash
git clone <repo-url> pylatkmc
cd pylatkmc

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `[dev]` extras install `pytest`, `ruff`, and `mypy`.

## Running the test suite

```bash
pytest tests/unit_py/ -q
# expect: 162 passed
```

Tests cover:

- The pattern-DB IR (`processes.py`) — pydantic validators, hashability,
  serialisation.
- The catalogue translator (`translator.py`) — per-family direction
  tables, bucket parsing, scatter warnings, full-catalogue dispatch.
- The decision-tree codegen (`decision_tree.py`) — `emit_*` helpers
  plus a `cc -Werror` compile gate on the emitted C.
- The runtime modules (`avail_sites`, `active_filter`, `state_actions`,
  `coord_table`) — ctypes-driven against the real `Lattice` / `State`
  C struct types, exercising O(1) invariants on random workloads.
- A CMake compile gate (`test_codegen_compiles.py`) that runs
  `pylatkmc-gen build` + `cmake --build` and asserts a working binary.

## Linting

```bash
ruff check .          # style + simple bug-finding
ruff format .         # auto-format
mypy pylatkmc/        # type checking (strict)
```

CI gates on these — please run them before opening a PR.

## Adding a new model

The pylatkmc model authoring path (single command, no template
plumbing):

1. Create `models/<name>/<name>.kmcspec.toml` (use
   `models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml` as a template). At
   minimum: `name`, `species`, `shells`, `rate_data.family_table`,
   `rate_data.temperature_K`, `rate_data.k0_Hz`.
2. (Optional) Inspect what the catalogue translator produces:
   ```bash
   pylatkmc-gen processes models/<name>/<name>.kmcspec.toml
   ```
3. Build the proclist:
   ```bash
   pylatkmc-gen build models/<name>/<name>.kmcspec.toml
   # → models/<name>/generated/proclist.{c,h}
   ```
4. Compile:
   ```bash
   cmake -B build -DMODEL=<name> && cmake --build build -j 4
   # → build/pylatkmc_<name>
   ```
5. Author an `input.ini` and a `config.kmcinit` in
   `models/<name>/examples/` (use the ni_fe_cr_v1 example as a
   template; build .kmcinit via `tools/build_initial_config.py`).
6. Add a regression test to `tests/unit_py/test_codegen_compiles.py`
   that builds your model.
7. Open a PR. Keep the model self-contained in `models/<name>/`.

See [`docs/PYKMC_INTEGRATION.md`](docs/PYKMC_INTEGRATION.md) for a full
walkthrough.

## Bug reports

Please include:

- pylatkmc version (`pip show pylatkmc`) or commit hash (`git rev-parse HEAD`)
- Python version (`python --version`)
- OS + compiler (e.g. macOS 14 + Apple clang 15, or Ubuntu 22.04 + gcc 11)
- The model spec (`<name>.kmcspec.toml`) you were running, if possible
- The full command + error output

For runtime / numerical issues (a simulation that "ran" but gave
unexpected MSD or proc-id distributions):

- Include `output/aggregate_summary.json`.
- Include `output/replica_NNNN/pykmc.out` (a head/tail of the per-step
  log helps).
- Include the input spec's `temperature_K` and the path to the
  curated-catalogue CSV.
- Numerical issues are often upstream — verify the catalogue's
  Ea_mean_eV values look sensible via
  `pylatkmc-gen processes <spec>`.

## Code style

- **Python**: PEP 8 + ruff defaults; double quotes; full type
  annotations on public functions; no implicit `Any`.
- **C**: K&R style; 4-space indent; explicit `static` on file-local
  symbols; one declaration per line.
- **Commits**: imperative subject ("add", "fix", "rename"), under 72
  chars. Body wraps at 72.
- **Docs**: when behavior changes, update both the code and the
  matching section in `docs/`. The architecture reference is
  `docs/PATTERN_DB.md`; the worked-example trace is
  `docs/HOW_IT_WORKS.md`.

## What's out of scope

See [`README.md`](README.md) § "Explicitly deferred" for the list of
features deliberately not implemented (Bystanders / OTF rates,
per-arrangement Processes, multi-vacancy MSD slot identity, 3NN
shells, non-cubic lattices, IRA-based reconstruction, basin
acceleration). PRs for these are welcome but expect a longer review
cycle and a design discussion first.

## License

By contributing, you agree that your contributions will be licensed
under the [MIT License](LICENSE) — same as the rest of the project.
