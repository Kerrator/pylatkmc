# Changelog

All notable changes to pylatkmc are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Candidates for v0.4 (none committed):

- Bystander runtime support — implement count-tuple expansion in
  `_expand_bystanders` for catalogues that emit species-count axes
  (e.g. `n_Fe_1nn`). The codegen hook is in place; today the function
  raises `NotImplementedError` for any Process with non-empty
  `bystanders`.
- Layer-index gating — the `li=k` bucket axis is currently dropped
  silently with a translator warning. Needs `site_class`-based
  Conditions for proper layer pinning.
- Per-arrangement Processes — when intra-bucket Eₐ_std is wide, split
  bucket-aggregated Processes into per-catalogue-row Processes for
  finer fidelity.
- Adatom-region Process catalogue — re-classify upstream events to add
  `species[NC_NN1_UP_*] == Ni` Conditions distinguishing adatom-down
  vs interlayer-hop arms (forward exchange-up events).

---

## [0.3.0] — 2026-05-07

### Added

- **`ShellCondition` IR class** (`pylatkmc/processes.py`): a hard count
  gate at `(coord, shell, species)` requiring exactly `count`
  matching neighbours. Threads catalogue bucketing
  (e.g. `nv1=4_nv2=1`) through to runtime so a Process discovered at
  high vacancy density can no longer fire on configurations that
  don't match.
- **`Process.shell_conditions`** field (default `()`); cross-validator
  rejects coords that appear in both `ShellCondition` and `Bystander`.
- **`load_bucket_exclusions`** helper in `translator.py`: reads a
  user-flagged CSV (`flag` column with `K`/`S`/`?`) and returns the
  set of (family_id, bucket_id) pairs to drop from translation. Used
  for opt-in pruning of suspect catalogue entries.
- **`_shell_conditions_from_bucket_key`**: decodes bucket IDs
  (`nv1=k_nv2=m`, `li=k_nv1=m`) into ShellConditions at the mover
  coord, per the upstream `corrected_nvac_nn1` convention (counts at
  `coord_mover_initial`, expected = 8 for surface, 12 for bulk).
- **3-adatom-layer support** in `tools/build_initial_config.py` and
  `tools/xyz_to_kmcinit.py` (`--n-adatom-layers N`): adds N empty
  FCC(100) layers above the top atom layer, giving forward
  exchange-up events landing positions for adatoms.
- **`tools/xyz_to_kmcinit.py`**: convert pyKMC `initial_config.xyz`
  files directly into pylatkmc `.kmcinit` format. Reconstructs the
  full lattice grid from atom positions, identifies vacancy sites by
  cKDTree mismatch, builds 1NN/2NN CSR with PBC, writes the binary.
- **End-to-end regression test** (`test_one_vac_no_high_density.py`):
  drives the binary on a real pyKMC-converted 1-vacancy config and
  asserts no `nv1>=2` Process ever fires in `pykmc.out`. Captures
  the v0.2 → v0.3 regression directly.
- **9 new decision-tree codegen tests** (count-loop emission, dedup,
  bare/gated mix, Bystander stub, determinism, `cc -Werror` compile
  gate on a multi-bucket fixture).
- **8 new IR tests** (ShellCondition construction, validation,
  hashability, JSON round-trip, Bystander-overlap rejection).
- **7 new translator tests** (bucket-key → ShellCondition emission,
  axis dispatch, backward-compat flag).

### Changed

- `_emit_simple_2action_hop` now emits ShellConditions by default;
  pass `emit_shell_gates=False` to recover v0.2 behaviour.
- `compile_decision_tree` runs `_expand_bystanders` before the
  dedup pass (no-op for current catalogue; v0.4 hook).
- Decision-tree leaves now group Processes that share Conditions but
  differ in `shell_conditions`, deduplicating CSR-walking count loops
  on `(coord, shell, species)` and emitting one `if`-gate per Process.
- `runtime/src/core/state.c:state_alloc` now allocates `species` of
  length `n_sites + 1`, with `species[n_sites] = 255` as a sentinel
  for out-of-lattice neighbour reads.
- `runtime/src/core/lattice.c:lattice_build_coord_table` fills
  missing-neighbour entries with the stub site index `n_sites`
  instead of `-1`. Eliminates the bus-error in `touchup_a` when a
  surface site's `NC_NN1_UP_*` resolves to nothing.

### Fixed

- **Spurious high-vacancy-density Process firings on a 1-vacancy
  system** — the v0.2 root cause. Translator dropped bucket keys
  during translation; `surface_1nn_inplane / nv1=4_nv2=1` fired
  ~33 % of events on a 1-vacancy slab where nv1=4 cannot physically
  occur. v0.3 ShellConditions gate this exactly.

### Validated

End-to-end sweep on 80 configurations (10 vacancy counts × 8
temperatures, 500k steps × 4 MPI replicas):

| n_vac | v0.2 Eₐ | v0.3 Eₐ | v0.3 R² |
|---|---|---|---|
| 1 | 0.220 | **0.627** | **1.000** |
| 2 | 0.229 | **0.573** | 0.997 |
| 3 | 0.230 | 0.558 | 0.995 |
| 4 | 0.239 | 0.482 | 0.971 |
| 5–10 | 0.22–0.26 | 0.40–0.49 | 0.92–0.98 |

Mean v0.3 Eₐ = **0.485 eV** — squarely in the literature range for Ni
surface-vacancy diffusion (0.30–0.50 eV).

### Test totals

163 → **188** unit tests passing.

### Commits

- bc0957a — v0.3.0: ShellCondition gates Process firing by catalogue bucket key

---

## [0.2.0] — 2026-05-06

### Added

- **Pattern-DB pipeline** replacing the v0.1 9-axis flat rate cube
  with a kmos-style decision tree. `pylatkmc-gen build <spec>` reads
  the curated FCC family CSV and emits a single `proclist.c`
  (decision tree + apply functions + rate table). The cube codepath
  is gone.
- **C runtime** with `avail_sites` (O(1) swap-last add/del),
  `active_filter` (coordination-based active-site gate),
  `state_apply_actions` (atomic multi-site Action application), and
  `coord_table` (per-site neighbour-direction lookup).
- **Catalogue translator** (`pylatkmc/translator.py`) producing a
  list[Process] from `rate_lookup_table_family.csv`. ~358 Processes
  for the production ni_fe_cr_v1 model.
- **Decision-tree codegen** (`pylatkmc/decision_tree.py`) — port of
  kmos's `_write_optimal_iftree` to C-emission. Greedy partitioning
  on most-shared CoordOffset; nested species-switch tree; leaf =
  `avail_sites_add(as, P, site)`.
- **NeighbourCode** direction enum (FCC-shaped, 23 codes) replacing
  the integer `(di, dj, dk)` IR. `lattice_build_coord_table()` walks
  each site's CSR and matches against canonical Cartesian deltas.
- **MPI ensemble** runs one independent simulation per rank;
  `MPI_Gather`-based aggregator writes per-rank +
  `aggregate_summary.json`.
- **Documentation**: `docs/PATTERN_DB.md` (architecture reference),
  `docs/HOW_IT_WORKS.md` (worked-example trace), updated
  `KMOS_COMPARISON.md` and `PYKMC_INTEGRATION.md`.
- **GitHub Actions CI** (`.github/workflows/tests.yml`): pytest on
  Linux + macOS × Python 3.10–3.13, plus a 1000-step end-to-end
  smoke run.

### Fixed

- **Codegen non-determinism**: `_most_shared_coord` previously broke
  ties via `-hash(coord)`, which depends on `PYTHONHASHSEED`. Two
  invocations on the same input produced byte-different
  `proclist.c`. Replaced with stable `str(coord)` lex-sort key;
  added regression test.

### Test totals

156 → **162** (with the determinism regression test).

### Commits

- 70e55f5 — M-E: Docs + CI for v0.2.0 release; fix codegen non-determinism
- e9e973a — M-D-Prep + M-D: Hard cutover to kmos-style pattern-DB pipeline
- d2ea83c — M-C: Runtime data structures (avail_sites + active_filter +
  state_apply_actions)
- 8d6807f — M-B: Decision tree codegen (port of kmos _write_optimal_iftree)
- 68cd9da — M-A.5+A.6+A.7: Translate all 12 fit-barrier families + CLI
  + production smoke
- 661bdff — M-A.3+A.4: Catalogue family rate table → Process IR
- d92cec4 — M-A.2: Catalogue Ea statistics → Process rate constants
- c9f264e — M-A.1: Add pattern-DB IR (Process, Condition, Action,
  Bystander, CoordOffset)

---

## [0.1.0] — pre-2026-05-06 (deprecated)

The original 9-axis flat rate cube. Replaced wholesale by v0.2.0.
See `e9e973a` for the cutover commit and `docs/PATTERN_DB.md` for
the design rationale.

[Unreleased]: https://github.com/Kerrator/pylatkmc/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Kerrator/pylatkmc/releases/tag/v0.3.0
[0.2.0]: https://github.com/Kerrator/pylatkmc/releases/tag/v0.2.0
[0.1.0]: https://github.com/Kerrator/pylatkmc/releases/tag/v0.1.0
