# pylatkmc — species-aware on-lattice KMC

Python codegen → specialised C runtime → MPI ensemble. A model is declared
by a TOML spec; `pylatkmc-gen build` translates a curated FCC family
catalogue into a per-model **pattern-DB Process catalogue** and emits a
single `proclist.c` (the decision tree, rate table, and apply
functions). CMake links it against a static C+MPI runtime, producing one
binary per model.

The architectural pattern is borrowed from
[kmos](https://github.com/mhoffman/kmos): spec-driven codegen → compiled
native code, pattern-DB matching with a frequency-optimised decision
tree, O(1) `avail_sites` book-keeping. See
[`docs/KMOS_COMPARISON.md`](docs/KMOS_COMPARISON.md) for what we kept and
what we deliberately left out.

**Status — v0.2.0 (2026-05-06).** Pattern-DB pipeline shipped.
Single-vacancy MSD on the reference 8×8×3 ni_fe_cr_v1 slab agrees with
the cube baseline within 13%. 162 unit tests passing.

---

## Requirements

- Python ≥ 3.10
- A C compiler (gcc / clang) and CMake ≥ 3.20
- OpenMPI ≥ 4.x (or any MPI 3.1-compatible implementation)
- A curated rate-table CSV (FCC family catalogue) — produced by the
  upstream pyKMC analysis pipeline, e.g.
  `apps/PyKMC_Analysis/Analysis/lattice_event_classification/rate_lookup_table_family.csv`
  in the workspace meta-repo.

## Quickstart

```bash
# 1. Set up a virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Generate proclist.c from the model spec.
#    Reads the family rate table from spec.rate_data.family_table,
#    translates each (family, bucket) into one Process per direction,
#    emits the per-process apply functions + decision tree + rate table.
pylatkmc-gen build models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
# → models/ni_fe_cr_v1/generated/proclist.c (5k+ lines)
# → models/ni_fe_cr_v1/generated/proclist.h

# 3. Compile the binary
cmake -B build -DMODEL=ni_fe_cr_v1
cmake --build build -j 4
# → build/pylatkmc_ni_fe_cr_v1

# 4. Run an example simulation
cd models/ni_fe_cr_v1/examples
mpirun -n 4 ../../../build/pylatkmc_ni_fe_cr_v1 input.ini
cat output/aggregate_summary.json
```

To inspect the catalogue translation without compiling:

```bash
pylatkmc-gen processes models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
# → 358 Processes across 9 families, Ea_eV range, scatter warnings
```

For the full architectural walkthrough see
[`docs/PATTERN_DB.md`](docs/PATTERN_DB.md).

---

## Where to read next

- **[`docs/PATTERN_DB.md`](docs/PATTERN_DB.md)** — *new in v0.2.* The
  pattern-DB pipeline: catalogue CSV → Process IR → decision tree →
  `avail_sites` → BKL select → `state_apply_actions`. Covers the
  NeighbourCode coordinate-resolution scheme and the `lattice_build_coord_table`
  startup routine.
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — three-layer
  architecture (Python codegen, generated C, static C runtime + MPI),
  model-spec schema, runtime data structures, MPI ensemble.
- **[`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md)** — end-to-end
  walkthrough with a worked example tracing one
  `surface_1NN_inplane` Ni hop from catalogue row to fired event with
  file:line cites.
- **[`docs/PYKMC_INTEGRATION.md`](docs/PYKMC_INTEGRATION.md)** —
  interaction with the upstream pyKMC analysis pipeline and the
  curated FCC family catalogue.
- **[`docs/KMOS_COMPARISON.md`](docs/KMOS_COMPARISON.md)** — what we
  borrowed, what's still kmos-different.

---

## Layout

```
pylatkmc/
├── pylatkmc/         # Python: spec → proclist.c (catalogue translator + decision-tree codegen)
│   ├── processes.py     # Process / Condition / Action / Bystander pydantic IR
│   ├── translator.py    # family CSV → list[Process]
│   ├── decision_tree.py # list[Process] → C source (M-B emitters)
│   ├── codegen.py       # spec.toml + family CSV → generated/proclist.{c,h}
│   ├── rate_expression.py # arrhenius_scalar, BoostFit, scatter warnings
│   └── cli.py           # pylatkmc-gen entry point
├── runtime/src/       # static C backbone
│   ├── core/
│   │   ├── lattice.{h,c}     # immutable lattice + per-site coord_table
│   │   ├── coord_codes.{h,c} # NeighbourCode enum + canonical deltas
│   │   ├── state.{h,c}       # mutable per-replica species + vac_list
│   │   ├── state_actions.c   # state_apply_actions (atomic multi-site)
│   │   ├── avail_sites.{h,c} # O(1) swap-last add/del + BKL select
│   │   ├── active_filter.{h,c} # coord-based active-site gate
│   │   ├── kmc.{h,c}         # main step loop
│   │   └── rng.{h,c}         # splitmix64 RNG
│   ├── io/                # initconfig (.kmcinit), xyz writer, pykmc.out
│   └── mpi/               # per-replica context + MPI_Gather aggregator
├── models/<name>/     # one subdir per compiled model (TOML spec + generated/ + examples/)
├── tests/unit_py/     # 162 pytests (ctypes-driven for the C side)
├── tools/             # build_initial_config, compare harnesses
└── docs/              # PATTERN_DB, ARCHITECTURE, HOW_IT_WORKS, PYKMC_INTEGRATION, KMOS_COMPARISON
```

---

## Tests

```bash
pytest tests/unit_py/ -q
# 162 passed
```

Includes:
- A codegen-compile end-to-end test that fully rebuilds the binary in
  ~3 s.
- Ctypes-driven tests for `avail_sites`, `active_filter`, `state_apply_actions`,
  `coord_table` against the real C struct types.
- Decision-tree golden-file tests + a `cc -Werror` compile gate on the
  generated C.

---

## Explicitly deferred (NOT in this release)

- **3NN or longer-range shells.** The catalogue + lattice builder
  cover 1NN and 2NN.
- **Non-cubic lattices** (HCP, BCC). The `NeighbourCode` enum is
  FCC-shaped today.
- **OTF (runtime) rate modulation** with Bystander counts — rates are
  pre-exponentiated at codegen time.
- **Per-arrangement Processes**: each (family, bucket) currently emits
  one Process per symmetry direction with a shared bucket-mean rate.
  Per-arrangement splitting is a v0.3 candidate if intra-bucket Ea
  scatter justifies it.
- **Multi-vacancy MSD slot identity.** The single-vacancy hop heuristic
  preserves slot identity through state mutations; multi-vacancy
  concerted events emit a one-time warning and skip MSD updates.
- **Incremental `avail_sites` maintenance.** Full per-step rebuild is
  fine for typical 1–10 vacancy systems.
- **IRA-based reconstruction.** That lives in pyKMC.
- **Restart / checkpoint resume.**
- **Basin acceleration** — that lives in pyKMC.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Citing

A pre-print describing the design and validation is in preparation. For
now, please cite the GitHub repository directly. A `CITATION.cff` will
be added once the paper is available.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to set up a development
environment, run the test suite, add a new model, and submit pull
requests.

---

## Acknowledgements

- The codegen pattern (spec → specialised native code) and the
  decision-tree compiler are direct ports of ideas from
  [kmos](https://github.com/mhoffman/kmos) (Hoffmann et al.). The
  `_write_optimal_iftree` algorithm in `decision_tree.py` is a C-emission
  port of kmos's Fortran implementation. The `avail_sites` dual-index
  data structure is ported from kmos's Fortran `avail_sites(proc, k,
  switch)` array.
- The curated FCC family catalogue is produced by an off-lattice pyKMC
  simulation pipeline using
  [pARTn](https://gitlab.com/mammasmias/artn-plugin) for saddle search
  and [IRA](https://github.com/mammasmias/IterativeRotationsAssignments)
  for environment matching.
- The coordination-based active-site filter is ported from pyKMC's
  `atomic_environment` module.
