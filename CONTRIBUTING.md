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
# expect: 76 passed
```

Tests cover the spec loader, the `#@ ... @#` preprocessor, codegen
(including a CMake-compile end-to-end test), the rate-table builder
(seven-tier fallback chain), and the `family_prefactors.py` loader.

## Linting

```bash
ruff check .          # style + simple bug-finding
ruff format .         # auto-format
mypy pylatkmc/        # strict type checking
```

CI gates on these — please run them before opening a PR.

## Adding a new model

1. Create `models/<name>/<name>.kmcspec.toml` (look at
   `models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml` as a template).
2. Generate C source: `pylatkmc-gen build models/<name>/<name>.kmcspec.toml`.
3. Compile: `cmake -B build -DMODEL=<name> && cmake --build build -j 4`.
4. (Optional) Build the rate cube from your curated catalogue:
   `pylatkmc-gen rate models/<name>/<name>.kmcspec.toml`.
5. Add a regression test to `tests/unit_py/test_codegen_compiles.py`
   that compiles your model.
6. Open a PR. Keep the model self-contained in `models/<name>/`.

See [`docs/PYKMC_INTEGRATION.md`](docs/PYKMC_INTEGRATION.md) for a full
walkthrough.

## Bug reports

Please include:

- pylatkmc version (`pip show pylatkmc`)
- Python version (`python --version`)
- OS + compiler (e.g. macOS 14 + Apple clang 15, or Ubuntu 22.04 + gcc 11)
- The model spec (`<name>.kmcspec.toml`) you were running, if possible
- The full command + error output

For runtime / numerical issues (a simulation that "ran" but gave
unexpected MSD or motif distributions), please also include the
`output/aggregate_summary.json` if you have one, and the input spec's
`temperature_K` and curated-catalogue source. Numerical issues are
often upstream — see the rate-cube preprocessing caveat in
[`.agents/AGENT.md`](.agents/AGENT.md).

## Code style

- **Python**: PEP 8 + ruff defaults; double quotes; full type
  annotations on public functions; no implicit `Any`.
- **C**: K&R style; 4-space indent; explicit `static` on file-local
  symbols; one declaration per line.
- **Commits**: imperative subject ("add", "fix", "rename"), under 72
  chars. Body wraps at 72.
- **Docs**: when behavior changes, update both the code and the
  matching section in `docs/`. README and `.agents/AGENT.md` are
  separate audiences (human onboarding vs AI-agent context).

## What's out of scope

See [`README.md`](README.md) § "Explicitly deferred" for the list of
features deliberately not implemented (multi-site events, 3NN shells,
non-cubic lattices, OTF rates, basin acceleration). PRs for these are
welcome but expect a longer review cycle and a design discussion first.

## License

By contributing, you agree that your contributions will be licensed
under the [MIT License](LICENSE) — same as the rest of the project.
