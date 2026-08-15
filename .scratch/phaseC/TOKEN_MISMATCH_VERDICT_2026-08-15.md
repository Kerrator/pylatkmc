# NiFe "token mismatch" skips — root cause + verdict

**Date:** 2026-08-15 · **Repo:** `~/pykmc/pylatkmc` @ `ingest` `da91997` (clean tree at start)
**Follow-up to:** `~/pykmc/NICRFE_INGEST_READINESS_2026-08-14.md` §5 / §7
**Scope:** `translator_v2.translate_event_classes` → `report.skipped_token_mismatch`

---

## 0. Verdict in one line

**PHYSICS, surfaced by a stale translator-side proxy — not a harvest defect, and not NiFe-specific.**
No saddle token is ever lost: `len(arrows) == len(saddle_token)` on **90,472 / 90,472** classes
across both production merges. The skip fires because `translator_v2._movers_in_token_order`
reconstructs the mover list from `cls.delta`, and `delta` stores **only sites whose occupancy
changed** — so a concerted relay in which a **same-species** atom takes over a just-vacated site
elides that site entirely. The catalogue has carried the correct datum since schema v4 / CANON v3
(`cls.arrows`); the translator simply never switched to it.

The ingest layer documented this exact hazard when `arrows` was introduced
(`pylatkmc/ingest/event_class.py:245-257`, `class Arrow`):

> A **permutation, not a displacement multiset**: *which atom went where is the datum a
> same-species concerted event's `delta` cannot reconstruct* (memo §2.3), and it costs nothing to
> capture […]

**Disposition: fix in `translator_v2` (done, uncommitted).** Not a veto — the data is sound.
Not accept-the-skip — the skip silently discards 7–11 % of every merged catalogue and reads to a
reviewer as breakage.

---

## 1. Recount at HEAD (`da91997`, pre-fix)

Two independent measurements: the real translator path (`translate_catalogue`) and a
gate-independent direct parquet scan. The scan is needed because on a **stamped** catalogue
(NiCr) the `pending_research` skip fires *before* the token check, so the translator's counter
reads 0 and hides the population entirely.

| catalogue | classes | `skipped_token_mismatch` (translator) | raw population (direct scan) | share |
|---|---|---|---|---|
| pilot `pilot_NiFe_merged_v3.parquet` (`include_unstamped=True`) | 3,264 | **285** — reproduces `9b5536d` exactly | 287 | 8.79 % |
| full `merged_v3_NiFe.parquet` (`include_unstamped=True`) | 20,293 | **2,176** | **2,253** | **11.10 %** |
| full `merged_v3_NiCr.parquet` (default path) | 70,179 | **0 — masked** | **5,014** | **7.14 %** |

- The pilot 285 **reproduces bit-for-bit at HEAD**; the v2 species basis (`8f90015`/`da91997`)
  did not touch it (it is a surrogate-side change).
- Translator-vs-scan gaps are exactly the quarantined classes skipped earlier: NiFe 2,253 − 77
  quarantined = 2,176 ✓. NiCr: 5,014 − 150 quarantined = 4,864 would hit the check the moment
  those classes are stamped `harvested_pair` by the graduation campaign.
- **This is corpus-wide, not NiFe-specific.** NiCr was masked twice over: by `pending_research`
  on the production path, and by the `include_unstamped` gate on the pilot path.

---

## 2. Bucket table

### 2a. Token count vs delta-derived mover count (full merges, raw scan)

| n_tokens | n_delta_movers | n_arrows | NiFe | NiCr | reading |
|---|---|---|---|---|---|
| 1 | 1 | 1 | 17,574 | 62,268 | single hop — always matches |
| 2 | 2 | 2 | 319 | 2,420 | 2-mover, **different** species handoff — matches |
| 3 | 3 | 3 | 105 | 51 | 3-mover, no same-species handoff — matches |
| 0 | 0 | 0 | 42 | 426 | NO_OP (empty delta, skipped earlier) |
| **2** | **1** | **2** | **1,727** | **4,405** | **MISMATCH** — 2-chain, one same-species handoff |
| **3** | **1** | **3** | **356** | **553** | **MISMATCH** — 3-chain, two same-species handoffs |
| **3** | **2** | **3** | **170** | **56** | **MISMATCH** — 3-chain, one same-species handoff |

`n_tokens − n_delta_movers` is **never negative** and never exceeds 2 (the chain length − 1).
It is exactly the count of same-species handoffs in the mover permutation.

### 2b. Single- vs multi-mover

| n_arrows | NiFe matched | NiFe mismatch | NiCr matched | NiCr mismatch |
|---|---|---|---|---|
| 0 | 42 | 0 | 426 | 0 |
| 1 | 17,574 | **0** | 62,268 | **0** |
| 2 | 319 | 1,727 | 2,420 | 4,405 |
| 3 | 105 | 526 | 51 | 609 |

**100 % of mismatches are multi-mover. 0 single-mover class has ever mismatched, in either alloy.**

### 2c. By archetype (`action.archetype_name`)

| archetype | NiFe matched | NiFe mismatch | % | NiCr matched | NiCr mismatch | % |
|---|---|---|---|---|---|---|
| `V1NN_inplane` | 9,296 | 0 | 0.0 | 31,021 | 0 | 0.0 |
| `V1NN_outofplane` | 31 | 0 | 0.0 | 775 | 0 | 0.0 |
| `HOP_2NN` | 405 | 0 | 0.0 | 1,623 | 0 | 0.0 |
| `HOP_3NN` | 7,625 | 0 | 0.0 | 28,060 | 0 | 0.0 |
| `HOP_4NN` | 104 | 0 | 0.0 | 366 | 0 | 0.0 |
| `HOP_far` | 103 | 0 | 0.0 | 383 | 0 | 0.0 |
| `NC` / `NO_OP` | 52 | 0 | 0.0 | 468 | 0 | 0.0 |
| **`C2_0deg`** | 110 | **508** | 82.2 | 184 | **931** | 83.5 |
| **`C2_60deg`** | 179 | **1,126** | 86.3 | 2,061 | **2,972** | 59.1 |
| **`C2_90deg`** | 14 | **83** | 85.6 | 78 | **447** | 85.1 |
| `C2_120deg` | — | — | — | 6 | 0 | 0.0 |
| **`C3`** | 105 | **523** | 83.3 | 51 | **600** | 92.2 |
| **`UNCLASSIFIED`** | 16 | **13** | 44.8 | 89 | **64** | 41.8 |

**Every mismatch lives in a concerted (`C2`/`C3`) or residual multi-arrow archetype; every
single-arrow archetype is clean at exactly 0.0 %.** The two alloys hit the same
species-blind `archetype` digests (16 shared), confirming a structural, species-independent
property of the taxonomy.

### 2d. By arrow species composition — the mechanism, stated directly

| arrow species | NiFe matched | NiFe mismatch | NiCr matched | NiCr mismatch |
|---|---|---|---|---|
| `Ni+Ni` | **7** | **1,727** | 7 | **4,345** |
| `Ni+Ni+Ni` | 0 | **357** | 0 | **556** |
| `Cr+Cr` / `Fe+Fe+Ni` | 2 | 2 | 0 | 60 / 10 |
| `Fe+Ni` / `Cr+Ni` | **319** | 0 | **2,413** | 0 |
| `Fe+Ni+Ni` / `Cr+Ni+Ni` | 103 | 167 | 51 | 43 |

A chain of **distinct** species never mismatches (every start site changes occupancy → every
mover appears in `delta`). A chain with a **repeated adjacent** species always does. `Fe+Ni+Ni`
appears in both columns because whether the Ni→Ni pair is *adjacent in the permutation cycle*
decides it.

### 2e. Sub-bucket: genuine chain vs off-lattice-final artifact (599-event sample, NiFe)

`project_event` computes snap residuals from **`P0` only** (`event_projection.py:831-835`), so G3
`MOVER_OFFLATTICE` and the bystander mask never look at the final state.

| bucket | n | median mover hop / 1NN | final mover residual ≥ 0.5 Å | shortest hop < 0.7 × 1NN |
|---|---|---|---|---|
| mismatch, 2 movers | 150 | 0.966 | 12 (8.0 %) | 9 (6.0 %) |
| mismatch, 3 movers | 149 | 0.963 | 17 (11.4 %) | 10 (6.7 %) |
| control: matched multi-mover | 150 | 0.981 | 4 (2.7 %) | 4 (2.7 %) |
| control: single-mover | 150 | 1.059 | 2 (1.3 %) | 0 (0.0 %) |

**≈ 93 % of mismatches are full-length real hops** (median 0.96 × 1NN, initial residuals
0.06–0.19 Å). The off-lattice-final tail (8–11 %) is a **separate, pre-existing** issue that also
shows up in the control buckets — see §5.

---

## 3. Overlap with the 12 token-flicker review classes — **ZERO, and a different mechanism**

`~/pykmc/pylatkmc/.scratch/phaseC/sweep_catalogue_2026-07-31_phase2/review_list_v3.csv` (15 rows:
12 `saddle-token-flicker (Q8 strict)` + 3 `structural-identity-change`).

- **`class_id` overlap with the mismatch sets: 0 / 12** in both merges (and 0 / 15 for the whole
  review list). Those ids are not present in *any* v3 catalogue at all — they are pre-remap ids
  carried through as `UNMATCHED_NOT_IN_OLD_CATALOGUE`.
- **Structurally disjoint.** The flicker detector is hard-gated on **single-mover** classes:
  `.scratch/phaseC/research_campaign/rc_accept.py:84-95` requires
  `len(pe_after.saddle_tokens) == 1`. Token mismatch is **100 % multi-mover** (§2b). The two
  populations cannot intersect by construction.
- **Different quantity.** Flicker is a change in one token's *content* (`coord_sig` 6→4,
  `kind` HOLLOW_FCC→OTHER) between the harvested projection and the re-search projection, which
  moves the `class_id`. Token mismatch is a *count* disagreement between the token list and a
  translator-side reconstruction of the mover list, at a fixed class.

**Do not merge these review items.** No new mechanism was invented here; they are unrelated.

---

## 4. Traced exemplars (catalogue → `source_sim_paths` → `reference_table.pickle`)

`production_NiCrFe` was read-only throughout.

### E1 — `4e945ce4a1bf128a…` — textbook clean 3-chain (the canonical case)
Sources: `NiFe_Ni95_Fe05_T400_9vac#166` (+ T500_10vac#369, T500_8vac#205, 1 more), `Ea_rep` 1.554 eV,
`n_eff` 4. Re-projected `idx_ref=166`: **3 Ni movers, displacements 2.385 / 2.440 / 2.478 Å against
a 1NN of 2.489 Å** — three complete hops. `mover_max_residual = 0.197 Å` (G3 tol 0.5 Å), frame fit
clean.

```
arrows : (0,0,0)->(0,-1,1) Ni   (0,1,1)->(0,0,0) Ni   (1,1,2)->(0,1,1) Ni
delta  : (0,-1,1) Vacant->Ni    (1,1,2) Ni->Vacant          <-- (0,0,0) and (0,1,1) ELIDED
tokens : 3   n_delta_movers: 1
```
Both handoff sites are Ni→Ni, so both vanish from `delta`. **Physics, not a defect.**

### E2 — `1768d0145885119b…` — mixed-species 3-chain, *partial* elision
Sources: `NiFe_Ni95_Fe05_T700_2vac#76` (+ 4), `Ea_rep` 1.789 eV, `n_eff` 5, quarantined.
Re-projected: 3 movers at 2.376 / 2.468 / 2.469 Å, `mover_max_residual = 0.183 Å`.

```
arrows : (0,0,0)->(0,-1,1) Fe   (0,1,1)->(0,0,0) Ni   (0,2,2)->(0,1,1) Ni
delta  : (0,-1,1) Vacant->Fe    (0,0,0) Fe->Ni    (0,2,2) Ni->Vacant   <-- (0,1,1) ELIDED
tokens : 3   n_delta_movers: 2
```
The Fe→Ni handoff **is** recorded (species changed); only the Ni→Ni one is lost. This is the
`n_tok=3 / n_mov=2` bucket and it pins the mechanism precisely: elision tracks *species equality
at the handoff*, nothing else.

### E3 — `2f5dd741e6347be7…` / `3d47227ec6af2634…` — highest-flux mismatch classes, and the tail case
Sources: `NiFe_Ni95_Fe05_T800_10vac#489` and `#492`; `Ea_rep` 0.829 / 0.818 eV — the top two
mismatch classes by measured trajectory flux (2.73 and 2.98 firings).

```
arrows : (-1,1,0)->(-2,2,0) Ni   (0,0,0)->(-1,1,0) Ni
delta  : (-2,2,0) Vacant->Ni     (0,0,0) Ni->Vacant          <-- (-1,1,0) ELIDED
tokens : 2   n_delta_movers: 1
```
Same elision mechanism. **But** this one *also* lands in the §2e tail: both atoms move only
1.34 / 1.38 Å (≈ 0.54 × 1NN) and `arrows_raw` puts the **final** positions at
`(-0.549, 0.513, 0.124)` / `(-1.528, 1.515, 0.118)` in a/2 units — i.e. roughly **half-way between
sites**. `mover_max_residual` still reads **0.069 Å** because it is computed on `P0` only. The
snapper promoted a collective half-shift into a 2-mover relay. That is a real (separate) data-quality
gap, §5.

---

## 5. Secondary finding — G3 never checks the FINAL state (not fixed here)

`project_event` builds `residuals` from the **initial** snapshot only
(`pylatkmc/ingest/event_projection.py:831-835`); both the G3 `MOVER_OFFLATTICE` gate and the §6
bystander `WILDCARD` mask key off it. A final configuration that never reached a lattice site is
therefore invisible to every build-time gate. Measured (§2e): **8–11 % of mismatch classes and
1–3 % of matched controls** have a final mover residual ≥ 0.5 Å.

This is **pre-existing, orthogonal, and out of scope for this fix.** Recommendation: raise it as its
own item (a symmetric `max(res(P0), res(P2))` for the mover-keyed G3 would be the natural form, but
it re-partitions the corpus and needs its own memo + canon decision — do **not** slip it in here).

---

## 6. Impact — what the skip was actually costing

Measured against the real pyKMC trajectories via
`.scratch/phaseC/research_campaign_nife/class_flux_nife.csv` (the same `flux_firings` measure the
NiFe re-search campaign ranked on):

| quantity | value |
|---|---|
| mismatch share of NiFe classes | 2,253 / 20,293 = **11.10 %** |
| mismatch share of **non-quarantined trajectory flux** | **0.0512 %** |
| mismatch classes ever selected in a real trajectory | **23 / 2,176** (38 of 119,931 selections) |
| median `Ea_rep` — mismatch vs matched | **1.618 eV** vs 0.952 eV |

So the population is **numerically large but kinetically almost irrelevant**: rare, high-barrier
concerted relays. NiCr's flux share is unmeasured on the widened 60-run corpus (no per-class flux
artifact exists for it yet); a naive `k × n_eff` proxy is *worthless* here — it reads 60 % for NiFe
against a true 0.05 %, because it is dominated by `n_eff=1` low-`Ea` singletons that never occur.

**The case for fixing is diagnostic, not kinetic:** a counter reading `skipped_token_mismatch=2176`
looks like breakage, is invisible on the default path, and silently drops 7–11 % of every catalogue.

---

## 7. The fix (left UNCOMMITTED in the working tree)

Two files modified; nothing committed, nothing else touched.

### `pylatkmc/translator_v2.py` — `_movers_in_token_order`

```python
    if cls.arrows:
        mover_offs_crystal = sorted(tuple(a.start) for a in cls.arrows)
    else:
        mover_offs_crystal = sorted(
            tuple(ds.off) for ds in cls.delta if _occ_name(ds.before) != VACANT
        )
    return [to_runtime_frame(off) for off in mover_offs_crystal]
```

plus an expanded docstring recording why `delta` is the wrong source, and a comment at the check
site (`translate_event_classes`) noting that on an arrow-bearing catalogue the counter is now a
genuine corruption detector. The `skipped_token_mismatch` counter, its report line and the
`include_unstamped` gate are all unchanged.

**Why `arrows` is exactly the right list, and why the change is a provable no-op where it matters:**

1. Tokens are sorted by `start_rank` = `canonical_rank_map(movers, a*, g*)` =
   lex rank of `apply_op(g*, m − a*)` (`ingest/canonical.py:179-192`).
2. `_canonical_orientation` stores arrows with `start = _transform_offset(a.start, a*, mat)`
   (`ingest/event_class.py:1128-1132`) — the **same** transform.
   ⇒ `sorted(a.start for a in cls.arrows)` **is** the token order, by construction.
3. Measured corpus-wide (90,472 classes, both merges):
   - `len(arrows) == len(saddle_token)` on **100 %** — no token is ever dropped;
   - delta-derived movers ⊆ arrow starts on **100 %**, with **equality on exactly the
     non-mismatch classes** ⇒ identical output wherever the old code produced any output;
   - `set(delta mover species) == set(arrow species)` on **100 %** ⇒ `codegen.py:469`'s
     spec-species validation is unaffected.

### `tests/unit_py/test_translator_v2.py`

- **New** `test_same_species_concerted_chain_binds_tokens_via_arrows`: builds a real
  `v ← A(Ni) ← B(Ni)` relay through the genuine Phase A `build_class_catalogue`, asserts the
  precondition (2 tokens / 2 arrows / **1** delta mover), that the class now translates with
  `skipped_token_mismatch == 0` and `orientation_mismatches == []`, and that the emitted pattern
  keeps the elided handoff site as a **context** row, never a delta row.
- **Extended** `test_multimover_tokens_bind_by_crystal_rank`: now also exercises the
  `arrows == ()` schema≤3 fallback and asserts both paths agree.

### Verification executed

| check | result |
|---|---|
| `pytest tests/unit_py/ -q` | **497 passed, 2 skipped** (both documented env skips) |
| `ruff check` + `ruff format --check` on both changed files | clean |
| `mypy pylatkmc/translator_v2.py` | 5 errors — **identical to the pre-change baseline** (verified via `git stash`); no new errors |
| `models/nicr_v2_scratch/generated/proclist.{c,h}` regenerated | **byte-identical** (22 classes / 2,400 procs, `token-mismatch: 0`) |
| `models/ni_example/generated/proclist.c` regenerated | **byte-identical** |
| NiCr production translate, default path | **unchanged: 32 patterns / 4,608 procs** |
| full NiFe, `include_unstamped=True` | `token_mismatch` 2,176 → **0**; translated 14,504 → **16,680** (+2,176 exactly); `orientation_mismatches == []` |
| pilot NiFe, `include_unstamped=True` | `token_mismatch` 285 → **0**; translated 2,767 → **3,052** (+285 exactly) |
| duplicate-proc audit: distinct `(delta, context)` images per transversal | **16,680 / 16,680 classes clean** — `n_ops == n_geo` on every class, recovered and pre-existing alike. No rate double-counting introduced. |

### One behavioural consequence to note before promotion

Enabling the recovered classes creates **106 runtime-geometry collisions** in the full NiFe
catalogue: a recovered concerted class emits the identical `(anchor, delta, context, orientation)`
pattern as a pre-existing single-hop class, so both procs match the same site and **their rates
sum**. That is physically correct — a relay and a direct long hop are parallel channels to the same
on-lattice final state — and the concerted route is frequently the *cheaper* one (e.g. 1.391 eV vs
2.611 eV for one pair). It is also **not new behaviour**: 20 such collisions already exist among the
classes that translate today. Flagging it because it is the one visible change in emitted rates.

---

## 8. Recommended disposition

1. **Take the fix** (§7). Smallest correct change; provably inert on everything that translates
   today; makes `skipped_token_mismatch` a real corruption detector (0 corpus-wide) instead of a
   false alarm. **Do not** veto and **do not** accept-the-skip.
2. **Close the readiness-report item** (`NICRFE_INGEST_READINESS_2026-08-14.md` §5/§7,
   "285 NiFe token-mismatch classes… investigation item stands") as *resolved — physics + stale
   translator proxy*, with the corrected corpus-wide numbers (NiFe 2,253 / NiCr 5,014).
3. **Keep the 12 token-flicker review classes on their own track.** Zero overlap, gated to
   single-mover events, different quantity (token content vs token count). §3.
4. **Raise the P0-only residual gate as a new item** (§5) — separate memo, separate canon call.
   Do not bundle.
5. **Sequencing.** Because the NiCr production catalogue is stamped, its 4,864 non-quarantined
   mismatch classes only become visible once the graduation campaign stamps them
   `harvested_pair`. Landing the fix now means the NiCr re-search leg never has to explain a
   suddenly-appearing 5,014-class skip.
6. **Not urgent on kinetics.** 0.05 % of measured NiFe flux; 23 of 2,176 classes ever fired.
   This does not gate the NiFe re-search campaign or the promotion decision.

---

## 9. Artifacts

- Report: `~/pykmc/TOKEN_MISMATCH_VERDICT_2026-08-15.md` (this file)
- Working-tree diff (uncommitted): `~/pykmc/pylatkmc/pylatkmc/translator_v2.py`,
  `~/pykmc/pylatkmc/tests/unit_py/test_translator_v2.py`
- Scan/sample scripts + intermediates: session scratchpad
  (`scan.py`, `recount.py`, `sample_final_resid.py`, `scan_Ni{Cr,Fe}_full.parquet`,
  `sample_final_resid_NiFe.csv`)
- Inputs (unmodified): `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_{pilot,full}/`,
  `~/pykmc/production_NiCrFe/runs/*/reference_table.pickle`
