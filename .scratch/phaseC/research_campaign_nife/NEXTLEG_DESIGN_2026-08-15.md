# NiFe re-search leg 2 — stratified candidate design (2026-08-15)

Follow-on to `NIFE_RESEARCH_CAMPAIGN_2026-08-15.md` §6 caveat 6 ("the measured set is
energetically homogeneous; a stratified per-action / Fe-in-context leg is the natural next
slice"). Design only — nothing was launched. Candidate list: `nextleg_candidates.csv`
(427 rows = **386 launch rows + 41 flagged appendix rows**); per-class diagnostics keyed by
`class_id` in `nextleg_strata.csv`.

Baselines (post-graduation, corpus = 120,291 expected firings): measured 56,073 (46.6%),
quarantined 53,834 (44.8%), **pending 10,384 (8.63%, 16,510 classes)** — the whole addressable
space for this leg.

## 1 Strata — exact predicates

Applied to the **pending** classes of `merged_v3_NiFe_graduated.parquet`
(`nu0_pair_policy == "pending_research"`; the 180 measured and the 3,603 quarantined carry other
values and are excluded by construction). `arch_name` = `pylatkmc.ingest.action.archetype_name(arrows,
delta_atoms)` recomputed from the parquet `arrows` + `delta_atoms` — **not** the mislabelled
`archetype` column of `class_flux_nife.csv`, which holds the grey u64 digest (the parquet
`archetype` column is that same digest, so the name has to be recomputed, not joined).

| stratum | predicate |
|---|---|
| `A1_fe_mover` | `arch_name == "V1NN_inplane"` and any `arrows[i].species == Occ.FE (3)` |
| `A2_fe_ctx_1nn` | `arch_name == "V1NN_inplane"`, no Fe mover, and ≥1 `context` row with `pred == 3` at integer distance² == 2 (1NN) from an arrow **start or end** |
| `B_<arch>` | `arch_name not in {V1NN_inplane, NC, NO_OP}` — one sub-stratum per archetype name |
| (`A0_no_local_fe`) | `V1NN_inplane` with no Fe mover and no path-adjacent Fe — **deliberately not selected** |

Ranking is flux-descending **within** each stratum (`class_flux_nife.csv` reachability-corrected
`flux_firings`); B ties broken by `n_instances`. Strata are disjoint; archetype wins over Fe role,
so a Fe-mover C2 lands in `B_C2_0deg`, and the `fe_role` column keeps that axis visible.

**Why not "Fe anywhere in context":** the 225-site stencil contains ≥1 Fe in **19,897 of 20,293
classes (98%)** — the literal reading of the brief selects the whole corpus. Tightening to
1NN-of-the-hop-path is what makes the stratum mean anything. Both predicates were validated
against the raw pyKMC geometry: 175/175 A1 search members really have an Fe moving atom,
125/125 A2 members a Ni mover with ≥1 Fe within 2.7 Å of the hop path (0 exceptions).

## 2 Exclusions and flags (nothing silently dropped)

* 180 measured + 3,603 quarantined — excluded by the policy filter.
* **19 failed-review classes + 1 CONTEXT_SUSPECT**: all still `pending_research`, all would rank
  into the A1/A2 heads. Kept in the file as `X_prev_failed` / `X_prev_out_of_band` **after** the
  386 launch rows, so `--top 386` never touches them. They carry **2,444.6 firings = 23.5% of all
  pending flux** — more than the entire A2 selection. Re-running them through `rc_campaign`
  unchanged is deterministic (`zseed = 1000*rung + attempt`, and the existing `jobs/<run>__idx<n>/
  mins.npz` short-circuits the min phase), so they will fail identically; they need a protocol
  change (new seeds / more rungs / different member), which is out of scope here.
* **`X_mover_mismatch` (21)**: candidates that the flux ranking *would* have picked, dropped by
  the prescreen in §3 and backfilled from deeper in the same stratum.
* **`NC` (10 classes, `delta_atoms == -1`, 0.05% of pending flux) excluded**: `translator_v2`
  skips non-conserving classes by default, so a measured rate for them has no consumer.

## 3 Prescreen: `mover_rank != 0` (validated 3/3 on leg 1)

`rc_accept.assess` identifies the mover as `argmax(|R2 - R1|)` and requires it to equal the stored
`move_atom_idx`. Computing that argmax on the **stored** initial→final geometry predicts the gate
exactly: on the 200 leg-1 jobs, all 3 `mover_ok=False` acceptance failures had stored
`mover_rank != 0`, and **0 of 197** rank-0 classes failed it (those 3 also have
`dra_stored ≈ 0.06 Å` — the recorded mover does not move to the saddle). Candidates are therefore
screened on `mover_rank == 0` before quota filling. This removes 3 A1 / 1 A2 and, crucially,
**40 of 62 `C2_0deg`, 24 of 32 `C3`, 12 of 32 `C2_60deg`** pool rows (verification pass: plus
8 of 22 `C2_90deg`, omitted from the original scan list — 84 concerted rejects in all) — the
concerted archetypes are where the stored mover key is unreliable.

## 4 Sizing

| stratum | pending pool | pool flux (% pending) | **n proposed** | selected flux | % of own stratum | % pending | % corpus | yield | exp. grad |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `A1_fe_mover` | 483 | 5515.7 (53.1%) | **175** | 2971.4 | 53.9 | 28.61 | **2.470** | 0.90 | 157.5 |
| `A2_fe_ctx_1nn` | 4262 | 2901.5 (27.9%) | **125** | 1124.9 | 38.8 | 10.83 | **0.935** | 0.90 | 112.5 |
| `B_V1NN_outofplane` | 28 | 1.4e-4 | **26** | 1.4e-4 | 99.9 | ~0 | ~0 | 0.80 | 20.8 |
| `B_HOP_3NN` | 5610 | 0.543 | **12** | 0.543 | 100.0 | 0.005 | 0.0005 | 0.80 | 9.6 |
| `B_HOP_2NN` | 358 | ~0 | **10** | ~0 | 77.7 | ~0 | ~0 | 0.80 | 8.0 |
| `B_HOP_4NN` | 97 | ~0 | **5** | ~0 | 74.6 | ~0 | ~0 | 0.80 | 4.0 |
| `B_HOP_far` | 93 | ~0 | **5** | ~0 | 53.0 | ~0 | ~0 | 0.80 | 4.0 |
| `B_C2_0deg` | 579 | 40.84 (0.39%) | **12** | 10.00 | 24.5 | 0.096 | 0.008 | 0.45 | 5.4 |
| `B_C2_60deg` | 1277 | 0.352 | **5** | 0.351 | 99.7 | 0.003 | ~0 | 0.45 | 2.25 |
| `B_C2_90deg` | 97 | 0.046 | **3** | 0.032 | 68.8 | ~0 | ~0 | 0.45 | 1.35 |
| `B_C3` | 589 | 0.689 | **5** | 1e-4 | 0.01 | ~0 | ~0 | 0.30 | 1.5 |
| `B_UNCLASSIFIED` | 29 | ~0 | **3** | ~0 | 94.0 | ~0 | ~0 | 0.30 | 0.9 |
| **total** | | | **386** | **4107.2** | | **39.55** | **3.414** | 0.85 | **≈328** |

"% of own stratum" is measured against the **full** pending stratum, which still contains the
excluded leg-1 failures. Net of those, A1's 175 rows cover **83.9%** of the 467 reachable A1
classes' flux (3542.4 firings) and A2's 125 cover 43.7% of its 4261 reachable classes (2572.3) —
A1's flux is flat after the 16 excluded heavy hitters (max selected flux 34.3 firings), which is
why 175 rows are needed to reach 84%.

Yields: 0.90 for A1/A2 = the leg-1 precedent (180/200; the July NiCr leg was 66/81) with the
mover-gate failures now prescreened out and the 12 refine + 4 class-drift failure modes still live.
0.80 for single-mover B (same harness regime, but median `Ea_rep` 1.5–2.1 eV stresses the refine
ladder — no precedent). Concerted B is capped by the argmax mover gate at roughly `1/n_movers`
(§5), hence 0.45 for C2 and 0.30 for C3/UNCLASSIFIED.

**Expected outcome at these yields:** +3,692 firings measured → measured share **46.6% → 49.7% of
corpus**, **84.4% → 89.9% of non-quarantined**; pending **8.63% → 5.56%** of corpus. Stratum A alone
delivers 3.07 of the 3.41 percentage points; stratum B is coverage, not flux.

**Job count / wall clock:** 386 jobs. Leg 1's primary pass ran 200 jobs in **8 min 13 s** on 7
workers (`jobs/` mtimes 01:24:29 → 01:32:42), so 386 ≈ **16 min**; at the 15 min/200 planning rate,
≈ **29 min**. Budget +50% on the trailing B block (a failing class burns all 15 ladder attempts).
`--workers 14` (the harness default) roughly halves it and still respects the 21-of-24-core cap.

## 5 Per-stratum caveats

1. **Singletons have no retry geometry.** A1 is 159/175 singleton, A2 54/125 (71 multi-member),
   B almost entirely singleton. `rc_retry.py` only rescues multi-member classes — 14 of leg 1's 19
   failures were singletons. Expect ~2 recoveries from a leg-2 retry round, not ~20.
2. **Multi-member classes search the member closest to `Ea_rep`** (`rc_common.load_targets`), and
   that member is resolved from `merged_v3_NiFe_stamped.parquet` **at launch time**. Regenerating
   or re-merging that parquet between now and the launch silently changes which geometry is
   searched. `nextleg_strata.csv` records the member this design resolved
   (`pred_search_run` / `pred_search_idx`) so the launch can be diffed against it.
3. **Concerted strata are structurally hostile to `rc_accept` as-is.** Every selected C2/C3
   candidate has 2 (resp. 3) atoms displaced > 1 Å with `|mover_margin| < 0.3 Å`, i.e. the two
   movers are tied to within relaxation noise, so `mover_ok = (argmax == stored move_atom_idx)` is
   a coin flip even for the rank-0 survivors. Their `n_tok` is 2/3, which also disables the
   saddle-token flicker rescue (`rc_accept` requires `len(saddle_tokens) == 1`). A real concerted
   leg needs the mover *set* compared instead of the argmax; these 25 rows are a capability probe.
4. **`B_C3`'s flux head is entirely in the prescreen appendix** — the 4 flux-bearing C3 classes all
   fail `mover_rank`, so the 5 selected carry 0.01% of the C3 stratum flux. Same effect, weaker, on
   `C2_0deg` (24.5% of stratum flux selected).
5. **Token flicker history.** All 7 leg-1 flicker rescues were single-token `HOLLOW_FCC` classes
   (7 of 62 attempted, 11.3%); no other token kind flickered. Selected: 52 `HOLLOW_FCC` in A1, 107
   in A2 — expect ~15–18 flicker-mediated graduations, which per caveat 5 of the campaign report
   agree slightly worse (18.9 vs 13.3 meV mean |ΔEa|).
6. **`B_V1NN_outofplane` is the cheapest complete-archetype win** (26 of 28 pending classes, the
   other 2 prescreened out) and doubles as Fe coverage — 21 of its 26 search members have an Fe
   mover. Its median `Ea_rep` of 1.49 eV against 0.65 eV in-plane is itself worth the measurement:
   either the out-of-plane channel really is that stiff, or these are projection artifacts.
7. **Zero-flux candidates**: 12 of the 26 out-of-plane classes and most of the `HOP_*` probes have
   `flux_firings == 0` (reachable but never applicable in a sampled state). They are selected for
   archetype coverage, and their graduation moves no flux.
8. **Quarantine is untouched.** 3,603 classes / 44.8% of corpus flux sit behind the `tol = 1e-6`
   reciprocity band; this leg cannot reach them. Ruling 3.6 remains a larger lever than the whole
   campaign, leg 1 and leg 2 combined.

## 6 Ready to launch

`rc_common.TARGETS_CSV` is a module constant hard-wired to `targets_nife.csv`, and it is read
*inside* `load_targets()`, so a one-line rebind picks up the new file with **no edit to the
harness**. Verified end-to-end without launching: `load_targets()` returns 427 rows × 34 columns,
every field `run_one` reads is present and non-null, all 386 launch rows resolve to a real
`(run_tag, idx_ref)` in the reference tables, and the only `jobs/` directory collisions are the 20
appendix rows (never selected by `--top 386`).

**Back up the leg-1 artifacts first** — `rc_graduate.py` overwrites `research_results.csv`,
`review_list.csv`, `catalogue_v3_NiFe_graduated.parquet` and `merged_v3_NiFe_graduated.parquet` in
place (the 2026-08-15 copies staged in `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/` are
the safety net, and `campaign_log.csv` is keyed by `class_id`, so leg 2 appends rather than
replaces).

```bash
cd /home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign_nife
/home/kerr/pykmc/pykmc_env/bin/python -c "
import pathlib, sys
sys.argv = ['rc_campaign', '--top', '386', '--workers', '7']
import rc_common as C
C.TARGETS_CSV = pathlib.Path.cwd() / 'nextleg_candidates.csv'
import rc_campaign; rc_campaign.main()"
```

Then, unchanged: `python rc_retry.py` (multi-member failures only) and `python rc_graduate.py`,
which rebuild the research CSV from the **cumulative** `campaign_log.csv` (leg 1 + leg 2) and
re-graduate + re-merge in one pass. Partial legs follow the file order:
`--top 175` = A1 only, `--top 300` = A1+A2 (all the flux), `--top 386` = full leg.
