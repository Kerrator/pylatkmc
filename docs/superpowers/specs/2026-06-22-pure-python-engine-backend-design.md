# Design: pure-Python (no-codegen) reference engine backend

**Date:** 2026-06-22
**Status:** Approved design — ready for implementation plan
**Author:** Stephen Kerr

## 1. Goal & context

The simulation today runs as Python codegen → specialised C → MPI ensemble: a TOML
spec plus a curated FCC family-rate CSV is translated into a `list[Process]`
([`translator.translate_all`](../../../pylatkmc/translator.py)), which
[`codegen.py`](../../../pylatkmc/codegen.py) turns into `proclist.c`, compiled by
CMake against the C+MPI runtime into one binary per model.

We want to **develop and iterate in pure Python without the codegen→compile→mpirun
loop**, while keeping the existing C+MPI engine as the production "fast backend"
that can be tied back in at any time.

The chosen structure is an **in-repo backend split** (both backends on `main`),
*not* a long-lived branch and *not* a separate repo. Rationale:

- A long-lived parallel branch rots (never sees spec/model/catalogue changes) and
  turns "tie in later" into a painful merge of two diverged histories; it also
  prevents running both engines side-by-side in one tree.
- A separate repo forces lockstep versioning of two repos that share the spec/ABI
  contract, for single-maintainer research code — pure overhead.
- A backend split gives the "tie-in" for free: both backends sit downstream of the
  same `translate_all(...)` output and are selected at runtime. The Python engine
  additionally becomes a **reference oracle** the C engine is validated against.

The current C+MPI state is already recoverable via the `v0.3.0` git tag, so no extra
archival tag is needed.

## 2. The seam

```
spec.toml + family CSV
   │  loader.load → translator.load_family_rate_table → translator.translate_all
   ▼
list[Process]              ← the shared interface (front-end UNCHANGED)
   ├──► codegen.py → proclist.c → C+MPI binary       (fast backend, today)
   └──► pylatkmc/engine/  interprets Process objects   (NEW pure-Python backend)
```

The Python engine is a **second consumer of the identical `list[Process]`** that
`codegen.py` consumes. It calls the same pipeline
(`loader.load` → `load_family_rate_table` → `translate_all(rows, k0_Hz, T_K,
mover_species)`) and then *interprets* the Process objects rather than emitting C.
No codegen and no C are in the Python engine's path.

## 3. New subpackage: `pylatkmc/engine/`

| Module | Responsibility |
|---|---|
| `lattice.py` | Read `.kmcinit` (magic `KMCICv01`) into in-memory state: positions, CSR 1NN/2NN neighbour lists, `species` (mutable), `site_class`, `layer_index`, and a `vac_list`. Reuse `tools/kmcfmt.py` for the header/payload envelope. |
| `coords.py` | Build and resolve the per-site neighbour table `coord_table[site*23 + code_idx] → absolute site \| -1` for the 23 `NEIGHBOUR_CODES`. `NC_ANCHOR` resolves to the site itself. |
| `rng.py` | Reproducible per-replica RNG: `numpy.random.default_rng(SeedSequence(base_seed, spawn_key=(rank,)))`. Independent streams, reproducible across Python runs. **No obligation to match the C RNG** (see §5). |
| `executor.py` | The BKL / n-fold-way main loop: enroll eligible `(Process, anchor)` pairs, build cumulative rates, draw, select, apply, advance time, sample. |
| `runner.py` | Parse `input.ini`, loop over replicas (plain Python loop, **no MPI**), aggregate, write outputs. |
| `io.py` | `input.ini` parser (matching the C INI semantics & defaults) and the output writers (`summary.json`, `aggregate_summary.json`, optional `pykmc.out` / `trajkmc.xyz`). |

CLI: add a `run` subcommand — `pylatkmc-gen run --backend=python <input.ini>` —
mirroring `cmd_build` in [`cli.py`](../../../pylatkmc/cli.py). (`--backend=c` wrapper
deferred; see §6.)

## 4. Semantic-fidelity rules

These make the engine *equivalent* to the C engine, not merely "a KMC loop". Each is
grounded in the existing code.

1. **Eligibility is a pure function of lattice state**, so a full rescan each step is
   exact — the C decision tree (`decision_tree.py`) is only a performance
   optimization. A `Process` is eligible at anchor site `s` iff:
   - every `Condition` holds: `species[resolve(s, cond.coord.code)] == cond.species`
     (all conditions ANDed); and
   - every `ShellCondition` holds: the number of `species`-occupied sites in the
     `shell` (`'1nn'`/`'2nn'`) of `resolve(s, sc.coord.code)` is **exactly** `count`.
     This is an **exact-equality** gate (`== count`, **not** `>=`), and its `coord`
     is anchored at the **mover** direction, not the anchor site
     (`processes.py:186-223`, `translator.py:299-360`).

2. **Anchor = the gating species → fast.** Every v2 Process anchors on `Vacant`
   (`Condition(NC_ANCHOR, 'Vacant')`), so candidate anchors = the vacancy list. The
   engine groups processes by their anchor-condition species and scans only sites of
   that species. For `n_vac=1` that is 358 processes × 1 anchor per step — cheap
   enough for pure Python. (Implement the grouping generally; in v2 it reduces to
   `vac_list`.)

3. **BKL selection (correct formula; bit-exactness not required under §5):**
   `r_tot = Σ rate·count` over enrolled pairs; draw `u1, u2`;
   `target = u1·r_tot`; pick the first cumulative bin `> target`; the site within a
   bin is `floor((target − prev)/rate)`; `dt = -ln(u2)/r_tot`. Rates are pre-baked
   floats `k0·exp(-Ea/kT)` (`rate_expression.arrhenius_scalar`,
   `KB_EV_PER_K=8.617333e-5`); **no per-step expression evaluation** in v2.

4. **Apply atomically:** verify each `Action.before` against live state, then write
   all `after`s (removals before additions). Track per-vacancy unwrapped
   minimum-image displacement; `mean_msd_A2 = Σ|disp|² / n_vac`; downstream
   `D = MSD/(6t)`.

5. **Output compatibility:** write the same files with the same field names and
   printf precisions so existing `tools/compare_*.py` work unchanged —
   `aggregate_summary.json` (`total_time_s_mean`, `mean_msd_A2_mean`, sample std
   N−1), per-replica `summary.json`. `pykmc.out` / `trajkmc.xyz` are optional
   debug/visualization outputs gated by `sample_every`.

## 5. Determinism: statistical parity (chosen)

The Python engine uses its **own** RNG (numpy) — no bit-exact port of
`runtime/src/core/rng.c`. Consequences:

- **Acceptance gate is statistical:** run the same `input.ini` through both engines
  over a replica ensemble and assert `D = MSD/(6t)` (and the Arrhenius `Eₐ` across the
  temperature sweep) agree within a tolerance **calibrated against the observed
  replica spread**. Because both engines interpret the *same* catalogue with the
  *same* baked rates and the *same* BKL algorithm over the *same* eligible set, the
  only difference is the RNG stream — agreement should be tight once replica count is
  adequate.
- **Enrollment / touchup order is irrelevant** to correctness (the eligible set is
  order-independent; only the cumulative-sum draw matters). One less thing to match.
- **Dropped:** the `rng_replay_path` hook, any per-step trajectory diffing.
- **Internal determinism** (same seed → same Python trajectory) is kept and unit-tested
  separately; it does not depend on C parity.

## 6. Out of scope (YAGNI)

- `.kmcrt` reading/writing — build rates directly from the spec family CSV via
  `translate_all`. This also sidesteps the **missing `pylatkmc-gen rate` subcommand**
  that the compare scripts reference but `cli.py` does not define.
- Real MPI — replicas are a Python loop.
- The frequency-optimised decision tree — brute-force eligibility instead.
- Incremental `avail_sites` — full rescan each step (semantically identical).
- Bystander / expression-string rates — v2 emits none; assert `rate_constant` is a
  float and raise if a string appears.
- Non-FCC lattices — consume the stored `.kmcinit` CSR neighbour lists; do not
  recompute geometry.
- A `--backend=c` wrapper around `mpirun` — deferred; the CLI is shaped to allow it
  later.

## 7. Validation strategy

A new `tools/compare_py_vs_c.py` (fork of `compare_v02_v03.py`) runs the same
`input.ini` through both engines and **asserts** D agreement within a calibrated
tolerance — today's compare scripts assert no tolerance, so this is an upgrade. An
Arrhenius cross-check across the temperature sweep validates `Eₐ` agreement. Internal
unit tests cover: `coord_table` resolution against known FCC neighbours; eligibility
on a hand-built Process + lattice (including the exact-count ShellCondition gate);
atomic apply with `before`-mismatch rollback; BKL selection on a tiny system with a
known analytic answer; same-seed reproducibility.

## 8. Known hazards (from the subsystem map)

- **Stale `initconfig.h` doc-comment:** it lists a different `.kmcinit` payload order
  than the runtime actually reads. Trust `runtime/src/io/initconfig.c` and
  `tools/build_initial_config.py`, not the `.h` comment. Authoritative payload order
  (little-endian): `u32 payload_version`, `f32[N*3] positions`, `i32[N+1]
  nn1_offsets`, `i32[M1] nn1_indices`, `i32[N+1] nn2_offsets`, `i32[M2] nn2_indices`,
  `i8[N] layer_index`, `u8[N] site_class`, `u8[N] initial_species`, `u8[M1]
  nn1_dir_family`, `u8[M2] nn2_dir_family`.
- **Missing `pylatkmc-gen rate`:** referenced by `tools/compare_*.py` but absent from
  `cli.py`; we bypass `.kmcrt` entirely (build rates from the family CSV).
- **Stale `motif_counts_sum`:** forked compare scripts must not require it (the
  runtime no longer emits it).
- **Catalogue-fidelity traps:** `ShellCondition` is exact-count not `>=`; its coord is
  the mover not the anchor; `rate_constant` is typed `str | float` (v2 always float);
  bucket-key parsing silently drops `li`/unknown axes and returns `()` (ungated) on an
  unparseable key; `load_family_rate_table` skips `n_events==0` / NaN-Eₐ rows. A
  divergent reimplementation of any of these changes which processes fire. The engine
  must consume `translate_all`'s output directly rather than re-deriving the catalogue.
- **Hardcoded `/Users/stephenkerr/...` paths** in some validation scripts skip off the
  maintainer's machine — keep new tooling parameterised.

## 9. Milestones

- **M1 — Front-end interpretation, no loop.** `lattice.py` (`.kmcinit` reader via
  `kmcfmt`) + `coords.py` (23-code resolver) + a read-only "eligible processes at
  site" debug dump. Acceptance: for a known slab + vacancy, the engine lists the same
  eligible processes the C engine would enroll.
- **M2 — Single-replica run.** `rng.py` + `executor.py` BKL loop + single-replica run
  writing `summary.json`. Acceptance: MSD grows sensibly on the 1-vacancy slab;
  same-seed reproducibility holds.
- **M3 — Ensemble + CLI.** Replica loop + `aggregate_summary.json` +
  `pylatkmc-gen run --backend=python <input.ini>`. Acceptance: a drop-in target for
  the existing compare scripts (correct `aggregate_summary.json` schema).
- **M4 — Cross-engine gate.** `tools/compare_py_vs_c.py` with an asserted, calibrated
  tolerance + Arrhenius cross-check across the temperature sweep. Acceptance: Python
  and C engines agree on D (and `Eₐ`) within tolerance on `ni_fe_cr_v1`.

## 10. Assumptions

- Engine lives in `pylatkmc/engine/` (subpackage, not a top-level package).
- numpy is the only new runtime dependency (already a project dependency).
- v1 targets the `ni_fe_cr_v1` model; the engine is model-agnostic via the spec but is
  exercised against that model.

## Appendix — reference facts (file:line)

- Catalogue pipeline: `translator.translate_all` (`translator.py:524-598`); rows from
  `load_family_rate_table` (`translator.py:132-158`); rate bake
  `rate_expression.arrhenius_scalar` (`rate_expression.py:63-89`).
- `Process` fields (`processes.py:303-310`); `Condition` (`:141-151`); `Action`
  (`:154-183`); `ShellCondition` (`:186-223`); `CoordOffset`/`NEIGHBOUR_CODES`
  (`:66-138`).
- C apply/select semantics: `decision_tree.py:421-533` (apply), `:107-359` (tree),
  `avail_sites.c:163-216`.
- Runtime loop / RNG: `kmc.c:119-201`, `rng.c:14-47` (xoshiro256++ + splitmix64 —
  referenced only, not ported); MSD `replica.c:155-165`.
- I/O: `input.ini` keys `config_reader.c:36-49`; `.kmcinit` `initconfig.c:14-26,76-91`
  + `tools/kmcfmt.py:20-38`; `pykmc.out` `pykmc_out.c:13,31-37`; per-replica + aggregate
  JSON `replica.c:52-77,179-269`.
- Compare harness: `tools/compare_msd_vs_pykmc.py`, `tools/compare_species_aware.py`,
  `tools/compare_v02_v03.py` (`D=MSD/6t`, Arrhenius `Eₐ=-slope·kB`).
