# pylatkmc — species-aware on-lattice KMC

Python codegen → specialised C runtime → MPI ensemble. A model is declared
by a TOML spec; `pylatkmc-gen` renders specialised C, CMake links it
against a static C+MPI runtime, and a binary rate cube baked from a
curated catalogue of pyKMC events drives the simulation.

The architectural pattern is borrowed from [kmos](https://github.com/mhoffman/kmos)
(spec-driven codegen → compiled native code), with a flat 9-axis rate cube
in place of kmos's pattern-DB decision tree. See
[`docs/KMOS_COMPARISON.md`](docs/KMOS_COMPARISON.md) for what we kept and
what we deliberately left out.

**Status:** M1–M4 shipped (scaffolding, codegen, rate builder with seven-tier
fallback, species-aware cross-composition harness). 76 unit tests passing.
Ready for first public release.

---

## Requirements

- Python ≥ 3.9
- A C compiler (gcc / clang) and CMake ≥ 3.18
- OpenMPI ≥ 4.x (or any MPI 3.1-compatible implementation)
- A curated rate-table CSV (FCC family catalogue) — produced by the upstream
  pyKMC analysis pipeline. A pre-built example `.kmcrt` is shipped in
  `models/ni_fe_cr_v1/examples/` so you can run the example without
  rebuilding the cube yourself.

## Quickstart

```bash
# 1. Set up a virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Generate C source from the model spec
pylatkmc-gen build models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml

# 3. Compile the binary
cmake -B build -DMODEL=ni_fe_cr_v1
cmake --build build -j 4
# → build/pylatkmc_ni_fe_cr_v1

# 4. (Optional) build the rate cube from a curated catalogue
#    Requires classified_events_with_families.csv (see docs/PYKMC_INTEGRATION.md).
pylatkmc-gen rate models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
# → models/ni_fe_cr_v1/examples/ni_fe_cr_v1.kmcrt

# 5. Inspect coverage of the rate cube against your spec
pylatkmc-gen provenance models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml

# 6. Run an example simulation
cd models/ni_fe_cr_v1/examples
mpirun -n 4 ../../../build/pylatkmc_ni_fe_cr_v1 input.ini
cat output/aggregate_summary.json
```

For a full walkthrough — including authoring a new `.kmcspec.toml` from
scratch — see the tutorial in
[`docs/PYKMC_INTEGRATION.md`](docs/PYKMC_INTEGRATION.md#tutorial--build-a-new-alloy-model-from-scratch).

---

## Where to read next

- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — what pylatkmc is and
  how it's structured: three-layer architecture (Python codegen, generated C,
  static C runtime + MPI), model spec, the 9-axis rate-cube key, codegen
  pipeline, the seven-tier fallback chain, runtime, MPI ensemble.
- **[`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md)** — end-to-end
  walkthrough: pyKMC saddle event → classified row → 9-axis cube cell →
  runtime hop. Includes a worked example tracing one
  `surface_1NN_inplane` Ni hop through every stage with file:line cites.
- **[`docs/PYKMC_INTEGRATION.md`](docs/PYKMC_INTEGRATION.md)** — end-to-end
  pipeline from a pyKMC simulation to a running pylatkmc binary, plus
  validation harnesses (`tools/compare_msd_vs_pykmc.py`,
  `tools/compare_species_aware.py`) and the new-model tutorial.
- **[`docs/KMOS_COMPARISON.md`](docs/KMOS_COMPARISON.md)** —
  same-and-different vs. kmos, what we borrowed, what we deliberately
  didn't.

---

## Layout

```
pylatkmc/
├── pylatkmc/         # Python: spec → C source + .kmcrt cube + family prefactor loader
├── runtime/src/      # static C backbone (kmc, lattice, state, rng, MPI, IO)
├── models/<name>/    # one subdir per compiled model (TOML spec + generated/ + examples/)
├── tests/unit_py/    # 76 pytests
├── tools/            # compare harnesses, build_initial_config
└── docs/             # ARCHITECTURE, HOW_IT_WORKS, PYKMC_INTEGRATION, KMOS_COMPARISON
```

For each top-level subdir's contents and purpose, see
[`docs/ARCHITECTURE.md#directory-layout`](docs/ARCHITECTURE.md#directory-layout).

---

## Tests

```bash
pytest tests/unit_py/ -q
# 76 passed
```

Includes a codegen-compile end-to-end test that fully rebuilds the binary
in ~1.7 s on a typical laptop.

---

## Explicitly deferred (NOT in this release)

- Multi-site / concerted events (kmos-style `actions` tuples)
- 3NN or longer-range shells
- Non-cubic lattices (HCP, BCC)
- Incremental `avail_sites` maintenance (kmos-style O(1) swap) — full
  rebuild every step is fine for typical 1–10 vacancy systems
- OTF (runtime) rate modulation — rates are pre-exponentiated at build
  time
- IRA-based reconstruction
- Restart / checkpoint resume
- Basin acceleration — that lives in pyKMC (the off-lattice reference),
  not here

See
[`docs/ARCHITECTURE.md#validation-status--known-limitations`](docs/ARCHITECTURE.md#validation-status--known-limitations)
and
[`docs/KMOS_COMPARISON.md#what-we-could-still-steal-later`](docs/KMOS_COMPARISON.md#what-we-could-still-steal-later)
for context on each.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Citing

A pre-print describing the design and validation is in preparation. For
now, please cite the GitHub repository directly. A `CITATION.cff` will be
added once the paper is available.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to set up a development
environment, run the test suite, add a new model, and submit pull
requests.

---

## Acknowledgements

- The codegen pattern (spec → specialised native code) is inspired by
  [kmos](https://github.com/mhoffman/kmos) (Hoffmann et al.). The
  `#@ ... @#` preprocessor syntax is a clean reimplementation of the
  kmos-style directive used in their `evaluate_template` machinery.
- The curated FCC family catalogue that drives `pylatkmc-gen rate` is
  produced by an off-lattice pyKMC simulation pipeline using
  [pARTn](https://gitlab.com/mammasmias/artn-plugin) for saddle search
  and [IRA](https://github.com/mammasmias/IterativeRotationsAssignments)
  for environment matching.
