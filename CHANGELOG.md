# Changelog

All notable changes to pylatkmc are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Electrochemical dissolution events (Erlebacher/MESOSIM).** A new analytical,
  non-conservative event type: a surface atom leaves the lattice (its site
  becomes `Vacant`) with the coordination- and potential-dependent rate
  `k = nu_E * exp(-(E_bare - Phi)/(kB*T))`, where
  `E_bare = sum_j eps(mover, neighbour_j)` over occupied 1NN neighbours.
  - Shared `pylatkmc/dissolution_rate.py` (duplicated byte-identically in
    `pyKMC-develop/pykmc/`) + canonical `epsilon_table.toml` anchored to DFT
    (Ke & Taylor 2020: ~9-coordinated Ni terrace `E_bare ~ 1.8 eV`).
  - `translator.translate_dissolution_family` emits one 1-action Process per
    (mover, occupied-neighbour histogram) for coordinations in `[min, max]`,
    gated by exact occupied-species `ShellCondition`s at the anchor's 1NN shell
    (mutually exclusive buckets; high-coordination bulk atoms can't dissolve).
  - `Process.is_electrochemical` flag flows into the C `RateConst`
    (`{prefactor_Hz, Ea_eV, is_electrochemical, _pad}`, guarded by a
    `_Static_assert`); `rateconst_eval(rc, T, phi)` subtracts the runtime
    overpotential for electrochemical Processes only (clamped at a barrierless
    floor), so **one compiled binary runs at any Phi**.
  - New `[dissolution]` spec block (`DissolutionSpec`); new `input.ini` keys
    `physics.overpotential_phi_eV`, `physics.dissolution_prefactor_Hz`,
    `physics.max_dissolution_events`; `n_vac_max` sizing now budgets dissolution
    events; per-rank and aggregate summaries report `n_dissolution`.
  - New `ni_dissolution_demo` model + a vacancy-free pure-Ni example slab.
  - Tests: `test_dissolution_rate.py`, `test_dissolution_translate.py`, and a
    build+run `test_dissolution_smoke.py` (verifies a dissolution fires, a
    vacancy is created, and the first-event rate scales as `exp(Phi/kT)`).

### Changed

- **`pykmc.out` column 5 (`k_tot`) on Phase C surrogate builds** now logs the
  total rate the step's `dt` was drawn from and its event selected against
  (measured + surrogate channel). It used to log the measured channel only
  (`0.0` on surrogate-only steps), so `k_tot != 1/<dt>` there. Builds without
  the surrogate channel (`PYLATKMC_HAS_SURROGATE` undefined: every v0.3 model
  and `nife_v2_scratch`) and `surrogate_enable = 0` runs log exactly the same
  bytes as before. Analyses that rebuild rates or residence times from this
  column on surrogate-build output must expect the new (correct) total.
  Downstream readers checked read-only on 2026-10-22, none of which reads
  surrogate-build output today: the pub3 drivers that parse column 5
  (`P6prep-rebuild-eval` `toy12/verify_toy12.py` and `v2test/v2cmp_analyze.py`,
  whose v2 builds do not define `PYLATKMC_HAS_SURROGATE`; `P5-tier1`
  `connectivity_metrics.py`, v0.3 runs); PyKMC_Analysis
  `hybrid_actions/kmc_adapter_run_diagnostics.py` (reads the archived legacy
  `latkmc` log); `lattice_map_events.py` and
  `hybrid_actions/executed_event_site_map_export.py` parse off-lattice pyKMC's
  own `pykmc.out` (`k_tot` = field 7), not this file; pub3 `ktot_shares.py`,
  `tier2_generate.py` and the P4 scripts compute `k_tot` themselves.
  (large-system-scaling/04)
- **Process exit status.** The binary exits 1 on every rank when any rank's
  replica failed setup (bad/missing `.kmcinit`, `avail_sites` ENOMEM, a refused
  geometry, ...) or its run failed; a replica that completed or trapped
  (`run_rc = -ENODATA`, no event left) still exits 0. Sweeps and job queues can
  now see failures; the aggregate's `n_success` / `n_failed` semantics are
  unchanged (a trapped replica was and is counted in `n_failed`). On stderr,
  `[rank N] replica_run failed: <rc>` is now printed for real failures only
  (a trap is reported by `kmc_run: trapped at step N`, as before), and rank 0
  adds `K of M replicas failed (setup or run error); exit status 1`.
  (large-system-scaling/01)

### Fixed

- A replica whose setup failed (any early return in `replica_run` before
  `kmc_run`) was counted in `n_success` with `run_rc = 0`; it now records the
  setup error in `run_rc` and counts as failed. (large-system-scaling/01)
- One rank failing `input_config_load` / `replica_init` left the other ranks
  blocked in MPI collectives until walltime. All ranks now agree on the
  startup status (`MPI_Allreduce`) before any replica runs and exit 1
  together; each failing rank prints its own error and rank 0 adds
  `startup failed on K of M ranks; no replica was run`. `replica_init` also
  rejects an `output_root` that would truncate the replica directory path in
  its 512-byte buffer (`-ENAMETOOLONG`) and an existing non-directory where a
  directory must go (`-ENOTDIR`; it used to pass as an existing directory and
  the run failed later at its first file open). (large-system-scaling/02)
- `dt = -log(r2)/r_tot` became `+inf` when the RNG drew `r2 = 0` exactly
  (p = 2^-53 per step): an infinite clock and a non-JSON `inf` in the
  summaries. `rng_next2` now redraws an exact zero (`r2` in (0, 1)); no draw
  is remapped, so every fixed-seed trajectory that never drew 0 is bitwise
  unchanged. (large-system-scaling/03)

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
