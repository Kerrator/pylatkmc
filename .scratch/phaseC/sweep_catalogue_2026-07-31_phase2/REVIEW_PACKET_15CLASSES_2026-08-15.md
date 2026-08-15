# Review packet — the 15-class review list (12 token-flicker + 3 structural)

**Prepared** 2026-08-15 · **Scope** curation/evidence only — no reclassification, no catalogue was
modified, nothing was committed, `/data/…` and `production_NiCrFe/runs/` were read-only throughout.
**Every recommendation below is an agent recommendation awaiting Stephen's ruling.**

## 0. Orientation

**What this list is.** During the 2026-07-22/23 re-search campaign (`onlattice_design/RESEARCH_CAMPAIGN_PROTOCOL_DECISION_2026-07-22.md`) 81 `pending_research` classes from the `verify_fix_T500_1vac` NiCr run were re-searched from scratch — padded cluster, LAMMPS minimisation, pARTn saddle refinement, Vineyard ν₀ — to decide whether their harvested barriers could be promoted to *measured*. 66 graduated. The other 15 all **passed the barrier test** (|Ea_re-search − Ea_harvested| ≤ 11.1 meV against a 50 meV band, every saddle re-converging with exactly one imaginary mode) but **failed the identity test**: the class_id recomputed from the re-relaxed geometry did not equal the stored one. Rather than invent a rule mid-campaign, Stephen took them out for his own inspection (decision 9, the 'Q8 strict' ruling). They have sat there since, tagged 12 `saddle-token-flicker (Q8 strict)` + 3 `structural-identity-change`.

**Why they matter.** They are the *entire* remaining representable-but-unmeasured bucket of that run: 25.43 expected firings = **7.93 %** of run flux, and the gap between the campaign's post-graduation 78.8 % measured share and the 86.7 % representable ceiling. Six of them also survive into the 2026-08-14 NiCr production corpus, where they carry **39.6** reachability-corrected firings.

**What has already been ruled elsewhere, and is NOT reopened here.**

- **Decision 8 (Q7, 2026-07-22) — ACCEPTED.** A saddle-token *kind* flip alone, with the refined saddle inside `classify_saddle_site`'s own ambiguity band, is rescued by the classifier's designed `prev_kind` hysteresis. 6 classes were accepted this way during the campaign.
- **Decision 9 (Q8, 2026-07-23) — STRICT.** *coord_sig* flicker is not auto-accepted; these 15 go to review. That is the ruling this packet serves.
- **Token-mismatch track — separate.** `TOKEN_MISMATCH_VERDICT_2026-08-15.md` §3 measured **zero** overlap between this review list and the token-mismatch population (0/12 and 0/15), and showed the two cannot intersect by construction: the flicker detector is hard-gated on single-mover events (`rc_accept.py:86`), token mismatch is 100 % multi-mover. Different quantity too — token *content* here, token *count* there. **This packet does not merge the two tracks and neither should the ruling.**
- **tol = 1e-6 reciprocity quarantine** is its own standing decision; three of these classes are quarantined under it in the 2026-08-14 corpus and that is reported, not re-argued.

**Lineage caveat you should know before reading the ids.** `review_list_v3.csv` is *not* v3-keyed. Its `class_id` column still holds the CANON-v1 ids from July 22, and both appended remap columns read `UNMATCHED_NOT_IN_OLD_CATALOGUE` — `remap_review_lists.py` looked these ids up in the Phase-1 *per-run* catalogues, where they never existed (they came from the `verify_fix` impl catalogue, not the 29-run sweep). This packet re-keys them the way the 2026-07-29 memo §8.3 prescribes, **by `idx_ref` lineage** into this campaign's own `verify_fix_T500_1vac_v3_raw.parquet`: all 15 land on exactly one v3 class each, none is in the discard ledger, and the v3 ids reproduce exactly when the stored rows are re-projected with today's installed code. Both id generations are carried in every section below.

### The headline finding, up front

**The 12 / 3 split does not survive contact with the current identity layer.** Substituting the stored saddle token into the re-searched projection recovers the stored `class_id` for **15 / 15**, and a token-blind identity makes before and after equal for **15 / 15**. The three `structural` classes (idx 96, 435, 249) are *frame-gauge* artifacts: their re-search frames came out rotated by the D4h element `((0,-1,0),(1,0,0),(0,0,1))` — a +90° turn about the surface normal — which canonicalisation absorbs but which `rc_accept._token_only_diff` (a raw-offset comparison) reads as a changed delta and context. Verified exhaustively: that one op maps the before arrows *and* all 225 context rows onto the after ones, exactly. So there is **one** phenomenon in this list, not two, and the review question is singular: *is a saddle-token change of this magnitude an identity change?*

**How big is 'this magnitude'?** `_saddle_coord_sig` counts occupied sites inside a hard `1.15 × 1NN = 2.8624 Å` shell around the saddle, **with no hysteresis band** — unlike `classify_saddle_site`, which was given a ±0.12 × 1NN band precisely to stop this kind of flicker. In 13 of the 15 classes exactly one or two atoms cross that hard boundary, with margins of **0.6 – 11.7 mÅ (median 2.3 mÅ)**. For scale: the projection's own snap residuals on these clusters are 60 – 137 mÅ, and the re-relaxation moved atoms by up to 137 mÅ. The identity is being decided at ~1/50 of the noise floor of the thing it is measuring.

### Summary table — 15 rows, with agent recommendations

| # | idx_ref | class_id (v3) | mover | Ea harv. / re-search (eV) | ΔEa (meV) | flicker | margin (mÅ) | flux: verify / NiCr-0814 | status in NiCr-0814 | **recommendation** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 369 | `3bc7bdd3c73a…` | Cr | 0.643 / 0.641 | -2.1 | coord_sig | 4.0 | 8.84 / 10.11 | approved (n=2) | **keep** |
| 2 | 241 | `435efbdb931f…` | Cr | 0.620 / 0.614 | -5.7 | coord_sig | 2.0 | 5.87 / — | absent | **keep** |
| 3 | 110 | `db7b0796779c…` | Ni | 0.733 / 0.723 | -10.3 | coord_sig | 4.3 | 1.77 / 2.60 | quarantined (n=3) | **keep** |
| 4 | 96 | `c6e67890a9dc…` | Ni | 0.795 / 0.792 | -3.0 | coord_sig | 0.6 | 1.68 / — | absent | **discard** |
| 5 | 152 | `245862556318…` | Ni | 0.806 / 0.800 | -6.8 | coord_sig | 0.6 | 1.45 / — | absent | **discard** |
| 6 | 435 | `f9c65e0b55e1…` | Cr | 0.571 / 0.569 | -1.8 | kind only | n/a | 1.17 / — | absent | **keep (Q7)** |
| 7 | 201 | `6c7a17975c51…` | Ni | 0.746 / 0.735 | -11.1 | coord_sig | 10.9 | 0.97 / 4.28 | pending (n=1) | **keep** |
| 8 | 146 | `68f112cce978…` | Ni | 0.810 / 0.807 | -3.0 | coord_sig | 1.7 | 0.75 / 2.18 | quarantined (n=4) | **keep** |
| 9 | 436 | `b87a270d50e9…` | Cr | 0.599 / 0.596 | -2.6 | coord_sig | 2.9 | 0.59 / 19.80 | approved (n=2) | **keep** |
| 10 | 76 | `d01234bc1eaf…` | Ni | 0.779 / 0.781 | +1.6 | coord_sig | 0.6 | 0.51 / 0.62 | quarantined (n=2) | **keep + merge-flag** |
| 11 | 405 | `2ad57879eec7…` | Ni | 0.782 / 0.774 | -7.4 | coord_sig + kind | 11.7 | 0.51 / — | absent | **keep** |
| 12 | 249 | `69abbc958a45…` | Ni | 0.752 / 0.746 | -5.8 | kind only | n/a | 0.45 / — | absent | **keep (Q7)** |
| 13 | 118 | `920b97fdde2c…` | Ni | 0.803 / 0.797 | -5.5 | coord_sig | 2.3 | 0.42 / — | absent | **keep** |
| 14 | 345 | `bb319c6534bf…` | Ni | 0.794 / 0.789 | -4.9 | coord_sig | 0.9 | 0.34 / — | absent | **keep** |
| 15 | 321 | `3a093c0ca624…` | Ni | 0.803 / 0.798 | -5.2 | coord_sig | 5.7 | 0.11 / — | absent | **keep** |

**Recommendation tally (agent, awaiting ruling):** 11 × keep-and-graduate, 2 × keep under the *already-approved* Q7 rule (idx 435, 249 — no new policy needed), 2 × discard (idx 96, 152 — for a geometry defect that has nothing to do with tokens). Kept classes carry 22.30 of the 25.43 review firings; the two discards carry 3.13 and appear in **none** of the 60 production runs.

---

## 1. What the evidence says as a whole

**F1 — one motif, not fifteen.** Every class is a single-mover, in-plane 1NN vacancy hop on a surface (`archetype = V1NN_inplane`, archetype digest `4501caaac4464c8d`, `depth_sig = SURFACE/7`, `delta_atoms = 0`, 225-row context at r_ctx = 8.5 Å, 130-atom cluster, no truncation). 11 Ni movers, **4 Cr movers** (idx 369, 241, 435, 436). Two action ids: `5cf5705e14817baf` (Ni) and `247c6ad71f8e0c82` (Cr). A single ruling therefore covers the whole list without species or mechanism carve-outs.

**F2 — the barriers were never in dispute.** |ΔEa| ≤ 11.1 meV on all 15 (mean −4.9 meV), all in band, every re-converged saddle with exactly 1 imaginary Hessian mode, `mover_ok` and `dra_ok` true everywhere. What failed was `class_id_ok`, and only that.

**F3 — the 12/3 split is an artifact (see §0).** 15/15 recovered by token substitution; 15/15 equal token-blind; the 3 `structural` cases differ from their stored form by one exact D4h element.

**F4 — the flicker is a knife-edge on an unbanded cutoff.** 13/15 turn on 1–2 atoms crossing 2.8624 Å by 0.6–11.7 mÅ. `classify_saddle_site` has a ±0.12 × 1NN hysteresis band; `_saddle_coord_sig` (`event_projection.py:1058`) has none, yet both feed the same class digest. Worth noting for a future canon bump — **not** actionable inside this review, since changing `_saddle_coord_sig` would change every `class_id`.

**F5 — two of the fifteen are already covered by an approved rule.** idx 435 and 249 have *bit-identical* coord_sig; only `kind` flips, and the hysteresis re-classification returns the stored kind. That is decision 8 verbatim. They reached the review list only because the frame-naive gate refused to call them token-only. Note that `classify_saddle_site` sat inside its ambiguity band (`n_hard = 2`, `n_soft = 5–6`) for **all 15** — the kind label is never confidently determined for this surface-hop population.

**F6 — two of the fifteen carry a real, unrelated defect.** idx 96 and 152 have half-hop final states (1.323 Å and 1.312 Å = 0.53 × 1NN; final-state mover snap residual 1.19 Å / 1.20 Å), are the only two `unpaired` classes in the list (pyKMC found no backward event), and their re-relaxed final states sit +0.787 eV and +0.796 eV above the initial with ~5 meV reverse barriers — shoulders, not basins. G3 does not catch this because `project_event` computes snap residuals from `P0` only; that is the P0-only residual-gate item the token verdict raises in §5, and these two are a concrete instance of it.

**F7 — corpus survival.** 6/15 are present in the 2026-08-14 NiCr production corpus (`merged_v3_NiCr.parquet`, 70,179 classes): 2 `approved` + `pending_research` (idx 369, 436), 1 `pending` + `pending_research` (idx 201), 3 `quarantined` by the tol = 1e-6 reciprocity rule (idx 110, 146, 76). Their combined production flux is **39.6 firings**, dominated by idx 436 (19.80) and idx 369 (10.11). Only 1/15 (idx 146) appears in the phase-2 29-run NiCr merge. 0/15 appear in the NiFe corpus, as expected.

**F8 — one confirmed §10.3.5 double count, and only one.** idx 76's two flicker faces both exist as separate rows in the production corpus (`d01234bc1eaf…` and `06f50e0a5712…`) with byte-identical `delta`/`arrows`/`context`/depth and barriers 6.1 meV apart. That is the same-`action_id` double count the token verdict §10.3.5 flags — one physical channel split in two, rates summing at runtime if both were ever baked. A token-blind grouping of the whole NiCr corpus finds **720 classes collapsing into 354 groups** (1.0 % of the corpus); of the 174 groups where the `kind` is also identical, the median Ea spread is 15 meV but 49 exceed 50 meV and the worst is 337 meV.

**F9 — therefore: do not read this packet as 'drop tokens from identity'.** That larger change is parked in `canonical.py`'s CANON v3 docstring for a documented reason (adversarial review 2026-07-31 finding 3: the aggregate rate path averages a class's members, so merging a cheap channel with an expensive one fires the dominant channel at a fraction of its rate). The corpus tail above supports that caution. What this packet supports is far narrower — see §2.

---

## 2. The decisions this packet is asking for

**D1 — the actual Q8 question (11 classes).** Should the *acceptance gate* of a re-search campaign treat a coord_sig change as an identity change when the atoms responsible sit within a stated tolerance of the coordination cutoff? Evidence says the flicker is 0.6–11.7 mÅ against a 60–137 mÅ noise floor, and that in every case the delta, arrows, mover, context and depth are preserved exactly (modulo D4h). *Agent recommendation:* accept, i.e. graduate these 11 on their harvested pairs, with the acceptance rule stated as a threshold (e.g. token-only difference + every crossing atom within 25 mÅ of the cutoff + single mover) so it is auditable and does not silently generalise. **This changes the acceptance gate only — no class_id, no catalogue schema, no canon version.**

**D2 — the two Q7 classes (idx 435, 249).** No new policy required: decision 8 already covers them. *Agent recommendation:* apply it, and fix `rc_accept._token_only_diff` to compare canonical forms instead of raw offsets so the next campaign does not re-manufacture this. Note the same `rc_accept.py` is byte-identical in `research_campaign_nife/`, which has 7 `acceptance_failed` rows in its own 19-class review list — worth a look on that track, out of scope here.

**D3 — the two half-hop classes (idx 96, 152).** Independent of D1. *Agent recommendation:* veto with the reason recorded as an off-lattice final state, and log them against the P0-only residual-gate item (token verdict §5) as its first named instances. Cost: 3.13 firings (0.98 % of run flux) and nothing in production.

**D4 (optional, small).** Record the idx 76 pair as a merge candidate under the §10.3.5 same-action double-count item. No action needed today — both rows are quarantined and neither is stamped.

---

## 3. Per-class one-pagers

Ordered by verify-run flux, descending. Every number is measured, not carried over: barriers and ν₀ come from `verify_fix_T500_1vac_v3_raw.parquet` and the run's `reference_table.pickle`; before/after tokens and geometry from re-projecting the stored row and the campaign's own re-relaxed states (`jobs/idx<N>/{mins,sadstate}.npz`) through today's installed `project_event`; corpus status from `merged_v3_NiCr.parquet`; production flux from `class_flux_nicr.csv` (2026-08-15).

### 1. idx_ref 369 — `3bc7bdd3c73a…` — Cr in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `3bc7bdd3c73a5e2523dd9584fd9b8e51efc17efae813f287183c2ecfe6fbf518`
- **class_id on the review list (CANON v1, July 22)** `080554a1fb0500a9e2593b72…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 247c6ad71f8e0c82` · `delta_atoms 0` · orientation count 16
- **mover species** Cr · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Cr atom at the anchor site hops into the neighbouring vacancy at `[-1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(-1, -1, 0) EMPTY->CR` / `(0, 0, 0) CR->EMPTY`; `arrows`: `(0, 0, 0)->(-1, -1, 0) Cr`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.447 Å = 0.983 × 1NN** (1NN = 2.489 Å); init→saddle **1.183 Å**, re-search saddle displacement 1.134 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.120 Å** before re-relaxation, **0.102 Å** after; re-relaxation moved atoms by at most **0.120 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.042 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.6428 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **9.720e+12 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 4.114e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `fe331e020892`, dE(pair) +0.06340 eV; re-search dE **+0.0625 eV**
- re-search: Ea **0.6406 eV** (ΔEa **-2.1 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: `approved` / `pending_research`, 2 members, Ea_rep 0.6462 eV — *PENDING_RE_SEARCH: recovered by the 2026-07-22 frame fix with no previously-measured member; awaiting in-situ *

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **8.836 expected firings = 2.76 %** of run flux; 34.7 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **10.108 firings**, 9 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 8, 11, 11)
re-searched          HOLLOW_FCC(8, 8, 11, 11)
```

- coord_sig length changes 6 → 4; the multiset loses/gains ['7'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 8, 11, 11} vs after {8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(0, -2, 0)` (coordination 7) moves OUT of the 2.8624 Å shell: d/cut 0.9902 → 1.0014, i.e. it sits 4.0 mÅ from the boundary; site `(-2, 0, 0)` (coordination 7) moves OUT of the 2.8624 Å shell: d/cut 0.9909 → 1.0021, i.e. it sits 6.0 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

Highest-flux class in the review list (8.84 firings, 27.6 % of the review-list flux) and the single largest Cr-mover item. The re-search reproduced the barrier to 2.1 meV with one imaginary mode; the identity difference is two coordinating atoms crossing the 2.862 Å cutoff by 4.0 and 4.2 mÅ. Nothing about the mechanism changed — the same Cr atom made the same in-plane 1NN hop into the same vacancy, and the same 225-site context surrounds it. It also survives into the 2026-08-14 NiCr production corpus with 2 members, `approved`, and 10.1 reachability-corrected firings, so this is a live production channel that is still unmeasured. Graduating it converts the largest single block of the residual representable gap.

---

### 2. idx_ref 241 — `435efbdb931f…` — Cr in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `435efbdb931f1fc84b032f3517bd32048618cea3f4ac9db79eb9249d74822f74`
- **class_id on the review list (CANON v1, July 22)** `f15da8e82e022e4754c501ac…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 247c6ad71f8e0c82` · `delta_atoms 0` · orientation count 16
- **mover species** Cr · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Cr atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) CR->EMPTY` / `(1, 1, 0) EMPTY->CR`; `arrows`: `(0, 0, 0)->(1, 1, 0) Cr`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.463 Å = 0.990 × 1NN** (1NN = 2.489 Å); init→saddle **1.162 Å**, re-search saddle displacement 1.161 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.083 Å** before re-relaxation, **0.081 Å** after; re-relaxation moved atoms by at most **0.067 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.040 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.6195 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **8.660e+12 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 2.983e+13 Hz (inside the band)
- reciprocity: `pair_status = linked`, backward class `64b1fcf53743`, dE(pair) +0.01033 eV; re-search dE **+0.0103 eV**
- re-search: Ea **0.6137 eV** (ΔEa **-5.7 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **5.873 expected firings = 1.83 %** of run flux; 23.1 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 8, 8, 11, 11)
```

- coord_sig length changes 6 → 5; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 8, 11, 11} vs after {7, 8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(2, 0, 0)` (coordination 7) moves OUT of the 2.8624 Å shell: d/cut 0.9982 → 1.0007, i.e. it sits 2.0 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

Second-highest flux (5.87 firings) and the second Cr-mover item. One atom crosses the cutoff by 2.0 mÅ; kind is HOLLOW_FCC on both sides. Barrier agreement 5.7 meV. Absent from the 2026-08-14 corpus, so its only evidence is the verify-run trajectory — but that evidence is a clean 1NN hop with a 5.7 meV barrier confirmation, and the 2.0 mÅ flicker margin is ~40× below the projection's own snap-residual scale on this cluster (83 mÅ). Nothing here warrants a discard.

---

### 3. idx_ref 110 — `db7b0796779c…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `db7b0796779cb0282ced852a7b46ba54cbf79d623e6d69997f9462610ab688c6`
- **class_id on the review list (CANON v1, July 22)** `6e4805c19858221706ff597c…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, -1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.566 Å = 1.031 × 1NN** (1NN = 2.489 Å); init→saddle **1.155 Å**, re-search saddle displacement 1.193 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.126 Å** before re-relaxation, **0.113 Å** after; re-relaxation moved atoms by at most **0.121 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.087 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7334 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **1.666e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 7.948e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `edf9468abb9b`, dE(pair) -0.01288 eV; re-search dE **-0.0174 eV**
- re-search: Ea **0.7231 eV** (ΔEa **-10.3 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: `quarantined` / **no ν₀ policy (quarantined ⇒ unstamped)**, 3 members, Ea_rep 0.7328 eV — *QC: pair reciprocity broken (|dE_f+dE_b|=0.0001 eV) — mislink/projection artifact*

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **1.773 expected firings = 0.55 %** of run flux; 7.0 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **2.603 firings**, 1 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   OTHER(7, 8, 8, 11, 11)
re-searched          OTHER(7, 7, 8, 8, 11, 11)
```

- coord_sig length changes 5 → 6; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 8, 8, 11, 11} vs after {7, 7, 8, 8, 11, 11}
- `kind`: **unchanged (OTHER)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(2, 0, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0170 → 0.9985, i.e. it sits 4.3 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

One atom crosses inward by 4.3 mÅ (1.0170 → 0.9985 of the cutoff); the `OTHER` kind is stable on both sides, so this is a pure coordination-count flicker. Barrier agreement 10.3 meV, the second largest in the set but still 5× inside the graduation band. Survives into the 2026-08-14 corpus with 3 members and 2.60 firings, though quarantined there by the tol=1e-6 reciprocity rule — that quarantine is a separate standing ruling and does not bear on the token question.

---

### 4. idx_ref 96 — `c6e67890a9dc…` — Ni in-plane 1NN hop (structural-identity-change)

**1 · Identity**

- **class_id (CANON v3)** `c6e67890a9dcea4ac2b0b25ca6577ded42cf5252f4c29b71fb64393e77f5c178`
- **class_id on the review list (CANON v1, July 22)** `2a60b77a4ab1fe6cd8e7bd23…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[-1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(-1, -1, 0) EMPTY->NI` / `(0, 0, 0) NI->EMPTY`; `arrows`: `(0, 0, 0)->(-1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **1.323 Å = 0.532 × 1NN** (1NN = 2.489 Å); init→saddle **1.072 Å**, re-search saddle displacement 1.109 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.085 Å** before re-relaxation, **0.074 Å** after; re-relaxation moved atoms by at most **0.081 Å**; mover residual in the initial state 0.000 Å
- **ANOMALY — half-hop final state.** The mover ends only 0.53 × 1NN from its start, so its snap residual to the claimed end site is **1.190 Å** — 2.4× the 0.5 Å mover tolerance. `project_event` computes snap residuals from `P0` only, so the G3 gate cannot see it (token verdict §2e/§5).

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7946 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.775e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 3.499e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = unpaired`, backward class **none (unpaired)**, dE(pair) n/a (unpaired); re-search dE **+0.7869 eV**
- re-search: Ea **0.7916 eV** (ΔEa **-3.0 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **1.678 expected firings = 0.52 %** of run flux; 6.6 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 8, 8, 11, 11)
```

- coord_sig length changes 4 → 5; the multiset loses/gains ['7'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {8, 8, 11, 11} vs after {7, 8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(2, 0, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0002 → 0.9991, i.e. it sits 0.6 mÅ from the boundary
- projection frame: the re-search frame is rotated by the D4h element `((0,-1,0),(1,0,0),(0,0,1))` (+90° about the surface normal). That op maps the stored arrows **and all 225 context rows** exactly onto the re-searched ones — this is the entire reason the class was labelled `structural`, and it is a gauge artifact of `_token_only_diff`, not a physical change.
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): DISCARD (veto) — defective harvest, not a token question**

The token flicker here is real and knife-edge (0.6 mÅ, the tightest in the set), but it is not the reason to worry about this class. The harvested event's own geometry is broken: the mover travels 1.323 Å = 0.53 × 1NN, so the final-state atom sits mid-bond and its snap residual to the claimed end site is 1.19 Å — 2.4× the 0.5 Å mover tolerance and 14× the cluster's own worst snap residual. The G3 gate never sees this because `project_event` computes residuals from `P0` only (token verdict §2e/§5). Two independent signals agree: the class is `unpaired` (pyKMC found no backward event) and the re-relaxed final state sits +0.787 eV above the initial with a ~5 meV reverse barrier, i.e. it is a shoulder, not a basin. Recommend vetoing it rather than graduating a 0.79 eV hop whose end state does not exist; if the channel is wanted, re-harvest it from the trajectory rather than repair it.

---

### 5. idx_ref 152 — `245862556318…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `2458625563183da22191d99bb2c341abe87170402ce29158d09e731f0282a432`
- **class_id on the review list (CANON v1, July 22)** `0909b0fead0c8a39fa80d694…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, -1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **1.312 Å = 0.527 × 1NN** (1NN = 2.489 Å); init→saddle **1.071 Å**, re-search saddle displacement 1.103 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.107 Å** before re-relaxation, **0.089 Å** after; re-relaxation moved atoms by at most **0.104 Å**; mover residual in the initial state 0.000 Å
- **ANOMALY — half-hop final state.** The mover ends only 0.53 × 1NN from its start, so its snap residual to the claimed end site is **1.204 Å** — 2.4× the 0.5 Å mover tolerance. `project_event` computes snap residuals from `P0` only, so the G3 gate cannot see it (token verdict §2e/§5).

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.8064 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.994e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 4.146e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = unpaired`, backward class **none (unpaired)**, dE(pair) n/a (unpaired); re-search dE **+0.7961 eV**
- re-search: Ea **0.7997 eV** (ΔEa **-6.8 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **1.451 expected firings = 0.45 %** of run flux; 5.7 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 8, 8, 11, 11)
```

- coord_sig length changes 4 → 5; the multiset loses/gains ['7'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {8, 8, 11, 11} vs after {7, 8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(0, -2, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0042 → 0.9998, i.e. it sits 0.6 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): DISCARD (veto) — defective harvest, not a token question**

The same pathology as idx 96 and the same numbers: 1.312 Å hop = 0.53 × 1NN, final-state mover snap residual 1.204 Å, `unpaired`, re-relaxed dE = +0.796 eV with Ea_meas only 4.6 meV above it. Its coord_sig flicker (one atom at 0.6 mÅ) is incidental. These two are the only members of the review list that carry a geometry defect, they are the only two that are `unpaired`, and neither appears anywhere in the 60-run 2026-08-14 NiCr corpus — consistent with rare artifacts rather than real channels. Recommend veto with the reason recorded as off-lattice final state, and cross-reference to the P0-only residual-gate item (token verdict §5), which is the systemic fix.

---

### 6. idx_ref 435 — `f9c65e0b55e1…` — Cr in-plane 1NN hop (structural-identity-change)

**1 · Identity**

- **class_id (CANON v3)** `f9c65e0b55e1acd168b8c747ebc0e4ef6013fb8172ab462ea86bd3448128dfd8`
- **class_id on the review list (CANON v1, July 22)** `10f2625d22d9c9ab3766535a…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 247c6ad71f8e0c82` · `delta_atoms 0` · orientation count 16
- **mover species** Cr · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Cr atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) CR->EMPTY` / `(1, 1, 0) EMPTY->CR`; `arrows`: `(0, 0, 0)->(1, 1, 0) Cr`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.467 Å = 0.991 × 1NN** (1NN = 2.489 Å); init→saddle **1.343 Å**, re-search saddle displacement 1.316 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.077 Å** before re-relaxation, **0.085 Å** after; re-relaxation moved atoms by at most **0.067 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.041 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.5708 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **6.264e+12 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 1.782e+13 Hz (inside the band)
- reciprocity: `pair_status = linked`, backward class `b87a270d50e9`, dE(pair) -0.02816 eV; re-search dE **-0.0268 eV**
- re-search: Ea **0.5690 eV** (ΔEa **-1.8 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **1.173 expected firings = 0.37 %** of run flux; 4.6 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 8, 11, 11)
re-searched          OTHER(7, 7, 8, 8, 11, 11)
```

- coord_sig positions: **identical** (no position differs)
- `kind`: **HOLLOW_FCC → OTHER**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: no coordinating atom crosses the cutoff — the coordination signature is **identical** on both sides and only the categorical `kind` label flips
- projection frame: the re-search frame is rotated by the D4h element `((0,-1,0),(1,0,0),(0,0,1))` (+90° about the surface normal). That op maps the stored arrows **and all 225 context rows** exactly onto the re-searched ones — this is the entire reason the class was labelled `structural`, and it is a gauge artifact of `_token_only_diff`, not a physical change.
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — already covered by approved decision 8 (Q7 hysteresis)**

This class is NOT a Q8 case. Its coordination signature is bit-identical before and after ((7,7,8,8,11,11)); only the `kind` label flips HOLLOW_FCC → OTHER, and `classify_saddle_site` re-run with the stored `prev_kind` returns HOLLOW_FCC — exactly the condition Stephen already approved as decision 8 on 2026-07-22. It landed in the review list only because `rc_accept._token_only_diff` compares raw projection offsets, and this re-search's local frame came out rotated by the D4h element ((0,-1,0),(1,0,0),(0,0,1)) — a +90° turn about the surface normal that canonicalisation absorbs but that raw-field equality does not. Graduate it under the existing rule; no new policy needed. It is also the backward partner of idx 436, so the two should be dispositioned together to keep the pair reciprocal.

---

### 7. idx_ref 201 — `6c7a17975c51…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `6c7a17975c517d5c33c85d9087633b62c7e524bc836d7e6d6fd3fe57491e5836`
- **class_id on the review list (CANON v1, July 22)** `520aa8ac4f827ca296a3b527…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[-1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(-1, 1, 0) EMPTY->NI` / `(0, 0, 0) NI->EMPTY`; `arrows`: `(0, 0, 0)->(-1, 1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.578 Å = 1.036 × 1NN** (1NN = 2.489 Å); init→saddle **1.169 Å**, re-search saddle displacement 1.211 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.137 Å** before re-relaxation, **0.125 Å** after; re-relaxation moved atoms by at most **0.137 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.096 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7456 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **1.570e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 1.169e+15 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `89bb728c0636`, dE(pair) -0.00816 eV; re-search dE **-0.0126 eV**
- re-search: Ea **0.7345 eV** (ΔEa **-11.1 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: `pending` / `pending_research`, 1 member, Ea_rep 0.7445 eV — *PENDING_RE_SEARCH: recovered by the 2026-07-22 frame fix with no previously-measured member; awaiting in-situ *

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.972 expected firings = 0.30 %** of run flux; 3.8 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **4.277 firings**, 1 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   OTHER(7, 8, 8, 11, 11)
re-searched          OTHER(7, 7, 8, 8, 11, 11)
```

- coord_sig length changes 5 → 6; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 8, 8, 11, 11} vs after {7, 7, 8, 8, 11, 11}
- `kind`: **unchanged (OTHER)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(-2, 0, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0140 → 0.9962, i.e. it sits 10.9 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

One atom crosses inward by 10.9 mÅ; `OTHER` kind stable on both sides. Barrier agreement 11.1 meV — the largest |ΔEa| in the review list, and still 4.5× inside the band. Live in the 2026-08-14 NiCr corpus as `pending` with 4.28 firings, so graduating it removes a real production-corpus hole. Its harvested ν₀ (1.57e13 Hz) sits comfortably inside the 1e12–5e13 acceptance band even though the padded-cluster diagnostic ν₀ (1.17e15 Hz) is the worst outlier in the set — the diagnostic is not what fires, and its excursion should not be read as evidence against the class.

---

### 8. idx_ref 146 — `68f112cce978…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `68f112cce97809c952363f041a9152ab4fe07ac3f9883deb1fba2e6601a48bcc`
- **class_id on the review list (CANON v1, July 22)** `d39e02b25986f188cdc42cd9…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, -1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.562 Å = 1.029 × 1NN** (1NN = 2.489 Å); init→saddle **1.443 Å**, re-search saddle displacement 1.480 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.116 Å** before re-relaxation, **0.115 Å** after; re-relaxation moved atoms by at most **0.112 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.073 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.8096 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.069e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 5.313e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `cc0860ceb7e4`, dE(pair) -0.02029 eV; re-search dE **-0.0211 eV**
- re-search: Ea **0.8066 eV** (ΔEa **-3.0 meV**, in band), 1 imaginary mode, pARTn ladder length 11
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: `pending/pending_research`; 2026-08-14 NiCr corpus: `quarantined` / **no ν₀ policy (quarantined ⇒ unstamped)**, 4 members, Ea_rep 0.7874 eV — *QC: pair reciprocity broken (|dE_f+dE_b|=0.0001 eV) — mislink/projection artifact*

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.751 expected firings = 0.23 %** of run flux; 3.0 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **2.180 firings**, 3 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 11, 11)
```

- coord_sig length changes 5 → 4; the multiset loses/gains ['8'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 11, 11} vs after {7, 7, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(-1, -1, 0)` (coordination 8) moves OUT of the 2.8624 Å shell: d/cut 0.9994 → 1.0063, i.e. it sits 1.7 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

One atom crosses outward by 1.7 mÅ (0.9994 → 1.0063); kind stable. Barrier agreement 3.0 meV. This is the only review class that also appears in the phase-2 29-run NiCr merge (as `pending`), and it carries 4 members and 2.18 firings in the 2026-08-14 corpus, where it is quarantined by the 1e-6 reciprocity rule (|dE_f+dE_b| = 1e-4 eV). Two separate dispositions therefore apply to it: graduate the identity question here, and let the standing tol ruling decide the quarantine.

---

### 9. idx_ref 436 — `b87a270d50e9…` — Cr in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `b87a270d50e9a8223597ae8b7bed633ce9a8120b8eb5a82b3fb66d0b3d85080b`
- **class_id on the review list (CANON v1, July 22)** `4c18235a45c1b31164b7ca59…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 247c6ad71f8e0c82` · `delta_atoms 0` · orientation count 16
- **mover species** Cr · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Cr atom at the anchor site hops into the neighbouring vacancy at `[-1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(-1, -1, 0) EMPTY->CR` / `(0, 0, 0) CR->EMPTY`; `arrows`: `(0, 0, 0)->(-1, -1, 0) Cr`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.467 Å = 0.991 × 1NN** (1NN = 2.489 Å); init→saddle **1.177 Å**, re-search saddle displacement 1.176 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.086 Å** before re-relaxation, **0.076 Å** after; re-relaxation moved atoms by at most **0.086 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.043 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.5989 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **7.262e+12 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 5.534e+13 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `f9c65e0b55e1`, dE(pair) +0.02816 eV; re-search dE **+0.0250 eV**
- re-search: Ea **0.5964 eV** (ΔEa **-2.6 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: `approved` / `pending_research`, 2 members, Ea_rep 0.6032 eV — *PENDING_RE_SEARCH: recovered by the 2026-07-22 frame fix with no previously-measured member; awaiting in-situ *

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.593 expected firings = 0.18 %** of run flux; 2.3 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **19.800 firings**, 22 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 8, 8, 11, 11)
```

- coord_sig length changes 6 → 5; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 8, 11, 11} vs after {7, 8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(-2, 0, 0)` (coordination 7) moves OUT of the 2.8624 Å shell: d/cut 0.9913 → 1.0010, i.e. it sits 2.9 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

Highest production leverage of the whole review list: 19.80 reachability-corrected firings in the 2026-08-14 NiCr corpus, `approved`, 2 members — the largest single unmeasured Cr-mover channel surfaced by this list. In the verify run it is only 0.59 firings, so a flux ranking taken from the July campaign alone badly understates it. The flicker is one atom crossing outward by 2.9 mÅ; barrier agreement 2.6 meV. It is the backward partner of idx 435 (dE +0.0282 / −0.0282 eV, exactly reciprocal), so dispositioning the two together preserves detailed balance in the catalogue.

---

### 10. idx_ref 76 — `d01234bc1eaf…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `d01234bc1eaf3af5c25f2705dec2d6152da94601cbc4493d408cb2b1e1591efd`
- **class_id on the review list (CANON v1, July 22)** `8b47a4e47f3f84f467860cfe…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, -1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.510 Å = 1.009 × 1NN** (1NN = 2.489 Å); init→saddle **1.414 Å**, re-search saddle displacement 1.435 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.065 Å** before re-relaxation, **0.072 Å** after; re-relaxation moved atoms by at most **0.060 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.039 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7793 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **1.866e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 6.748e+13 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `cd36b265ecc1`, dE(pair) -0.00906 eV; re-search dE **-0.0091 eV**
- re-search: Ea **0.7809 eV** (ΔEa **+1.6 meV**, in band), 1 imaginary mode, pARTn ladder length 11
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: `quarantined` / **no ν₀ policy (quarantined ⇒ unstamped)**, 2 members, Ea_rep 0.7799 eV — *QC: pair reciprocity broken (|dE_f+dE_b|=0.0001 eV) — mislink/projection artifact*

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.511 expected firings = 0.16 %** of run flux; 2.0 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus (60 runs, reachability-corrected, `research_campaign_nicr/class_flux_nicr.csv`): **0.617 firings**, 3 selections

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 11, 11)
```

- coord_sig length changes 5 → 4; the multiset loses/gains ['8'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 11, 11} vs after {7, 7, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(-1, -1, 0)` (coordination 8) moves OUT of the 2.8624 Å shell: d/cut 0.9998 → 1.0030, i.e. it sits 0.6 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- **§10.3.5 same-action double count: YES, confirmed in production.** Both faces of this flicker exist as separate rows in `merged_v3_NiCr.parquet` — `d01234bc1eaf…` (`HOLLOW_FCC(7,7,8,11,11)`, 2 members, Ea 0.7799 eV, 0.62 firings) and `06f50e0a5712…` (`HOLLOW_FCC(7,7,11,11)`, 5 members, Ea 0.7738 eV, 10.26 firings) — with byte-identical delta, arrows, 225-row context and depth signature. One physical channel, two class rows, 6.1 meV apart; their rates would sum at runtime if both were baked.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate; ALSO flag the sibling merge (see §10.3.5 note)**

The one class in the list that demonstrates the double-count hazard with production data rather than argument. Its flicker margin is 0.6 mÅ — one atom at 0.9998 of the cutoff going to 1.0030 — and both sides of that flicker exist as separate rows in the 2026-08-14 NiCr corpus: `d01234bc1eaf…` (token …(7,7,8,11,11), 2 members, Ea 0.7799, 0.62 firings) and `06f50e0a5712…` (token …(7,7,11,11), 5 members, Ea 0.7738, 10.26 firings). Their `delta`, `arrows`, 225-row `context` and depth signature are byte-identical; the barriers differ by 6.1 meV. This is precisely the same-`action_id` double count the token-mismatch verdict flags in §10.3.5: if both were ever stamped and baked, both procs would match the same site and their rates would sum. Recommend graduating and recording the pair as a merge candidate for whatever memo carries the §10.3.5 item.

---

### 11. idx_ref 405 — `2ad57879eec7…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `2ad57879eec75f46d7c4c551b6d874c0e66101080195ad670ea452838b10fa42`
- **class_id on the review list (CANON v1, July 22)** `bbf1c0a37260601585df1170…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, 1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, 1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.571 Å = 1.033 × 1NN** (1NN = 2.489 Å); init→saddle **1.180 Å**, re-search saddle displacement 1.216 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.108 Å** before re-relaxation, **0.093 Å** after; re-relaxation moved atoms by at most **0.083 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.089 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7818 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **1.738e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 2.950e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `18ead8631382`, dE(pair) +0.01339 eV; re-search dE **+0.0118 eV**
- re-search: Ea **0.7744 eV** (ΔEa **-7.4 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.506 expected firings = 0.16 %** of run flux; 2.0 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 8, 8, 11, 11)
re-searched          OTHER(7, 7, 8, 8, 11, 11)
```

- coord_sig length changes 5 → 6; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 8, 8, 11, 11} vs after {7, 7, 8, 8, 11, 11}
- `kind`: **HOLLOW_FCC → OTHER**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(0, 2, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0101 → 0.9959, i.e. it sits 11.7 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

One atom crosses inward by 11.7 mÅ, which pushes the hard count from 4 to 5 and therefore flips the kind label HOLLOW_FCC → OTHER as a side effect — the kind change is downstream of the same single-atom crossing, not an independent mechanism change. (`classify_saddle_site` sat in its ambiguity band on both sides: n_hard = 2, n_soft = 6.) Barrier agreement 7.4 meV. Treat it with the other Q8 cases rather than as a mechanism dispute.

---

### 12. idx_ref 249 — `69abbc958a45…` — Ni in-plane 1NN hop (structural-identity-change)

**1 · Identity**

- **class_id (CANON v3)** `69abbc958a454954397bd3d046c4afa809f4b977f1addcfc87e85161409fc29f`
- **class_id on the review list (CANON v1, July 22)** `36b43f23b0c45dcf4991bdc7…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,-1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, -1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, -1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.566 Å = 1.031 × 1NN** (1NN = 2.489 Å); init→saddle **1.545 Å**, re-search saddle displacement 1.583 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.113 Å** before re-relaxation, **0.097 Å** after; re-relaxation moved atoms by at most **0.111 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.081 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7522 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.229e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 4.264e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `5b286f213156`, dE(pair) +0.01755 eV; re-search dE **+0.0185 eV**
- re-search: Ea **0.7464 eV** (ΔEa **-5.8 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.451 expected firings = 0.14 %** of run flux; 1.8 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   OTHER(7, 7, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 8, 11, 11)
```

- coord_sig positions: **identical** (no position differs)
- `kind`: **OTHER → HOLLOW_FCC**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: no coordinating atom crosses the cutoff — the coordination signature is **identical** on both sides and only the categorical `kind` label flips
- projection frame: the re-search frame is rotated by the D4h element `((0,-1,0),(1,0,0),(0,0,1))` (+90° about the surface normal). That op maps the stored arrows **and all 225 context rows** exactly onto the re-searched ones — this is the entire reason the class was labelled `structural`, and it is a gauge artifact of `_token_only_diff`, not a physical change.
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — already covered by approved decision 8 (Q7 hysteresis)**

Second Q7 case, mislabelled `structural` for the same reason as idx 435: coord_sig identical ((7,7,8,11,11) both sides), only the kind flips OTHER → HOLLOW_FCC, and the re-search frame came out rotated by the same +90° D4h element, which the raw-field diff read as a changed delta and context. The hysteresis re-classification returns the stored kind, so decision 8 applies as written. Barrier agreement 5.8 meV. Graduate under the existing rule.

---

### 13. idx_ref 118 — `920b97fdde2c…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `920b97fdde2cddfc3317cda8b87ac9a0dea556ab39961624048e3ed6231c81d5`
- **class_id on the review list (CANON v1, July 22)** `7af75647c3bd3952c5c67beb…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, 1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, 1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.550 Å = 1.025 × 1NN** (1NN = 2.489 Å); init→saddle **1.391 Å**, re-search saddle displacement 1.422 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.097 Å** before re-relaxation, **0.073 Å** after; re-relaxation moved atoms by at most **0.096 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.062 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.8030 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **1.922e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 2.760e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `7132bca2b32b`, dE(pair) -0.01199 eV; re-search dE **-0.0118 eV**
- re-search: Ea **0.7975 eV** (ΔEa **-5.5 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.416 expected firings = 0.13 %** of run flux; 1.6 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 11, 11)
```

- coord_sig length changes 6 → 4; the multiset loses/gains ['8'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 8, 11, 11} vs after {7, 7, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(-1, 1, 0)` (coordination 8) moves OUT of the 2.8624 Å shell: d/cut 0.9952 → 1.0023, i.e. it sits 6.6 mÅ from the boundary; site `(1, -1, 0)` (coordination 8) moves OUT of the 2.8624 Å shell: d/cut 0.9971 → 1.0008, i.e. it sits 2.3 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

Two symmetry-equivalent atoms cross the cutoff together (0.9952 → 1.0023 and 0.9971 → 1.0008; smallest margin 2.3 mÅ), which is why the signature loses both 8s at once. Kind stable, barrier agreement 5.5 meV. Absent from the 2026-08-14 corpus; the case rests on the verify-run evidence, which is clean.

---

### 14. idx_ref 345 — `bb319c6534bf…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `bb319c6534bfa17bc182d5a8c3aea11b4610dd7751900719ab598aa258bc0894`
- **class_id on the review list (CANON v1, July 22)** `1d2e44193abb70496ed18a31…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, 1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, 1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.562 Å = 1.029 × 1NN** (1NN = 2.489 Å); init→saddle **1.110 Å**, re-search saddle displacement 1.152 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.123 Å** before re-relaxation, **0.111 Å** after; re-relaxation moved atoms by at most **0.115 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.074 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.7941 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.366e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 5.567e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `1dbda92b3fe1`, dE(pair) -0.02070 eV; re-search dE **-0.0201 eV**
- re-search: Ea **0.7892 eV** (ΔEa **-4.9 meV**, in band), 1 imaginary mode, pARTn ladder length 1
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.337 expected firings = 0.10 %** of run flux; 1.3 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 8, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 8, 8, 11, 11)
```

- coord_sig length changes 5 → 6; the multiset loses/gains a repeated entry — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 8, 8, 11, 11} vs after {7, 7, 8, 8, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(0, 2, 0)` (coordination 7) moves INTO the 2.8624 Å shell: d/cut 1.0032 → 0.9997, i.e. it sits 0.9 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

One atom crosses inward by 0.9 mÅ — 0.03 % of the cutoff radius. Kind stable, barrier agreement 4.9 meV. Nothing distinguishes this class from the eleven others except its low flux (0.34 firings), and low flux is not a reason to discard a class whose barrier was independently confirmed; it is a reason not to spend more search budget on it.

---

### 15. idx_ref 321 — `3a093c0ca624…` — Ni in-plane 1NN hop (saddle-token-flicker)

**1 · Identity**

- **class_id (CANON v3)** `3a093c0ca624e32ddee6a6f950050b4922f9eca3b2bd00b4171c35cc05e94196`
- **class_id on the review list (CANON v1, July 22)** `527f2fdb9133bfe5d7274db5…` — re-keyed here by `idx_ref` lineage (the file's own remap columns say `UNMATCHED_NOT_IN_OLD_CATALOGUE`; see §0).
- **archetype / action** `V1NN_inplane` (digest `4501caaac4464c8d`) · `action_id 5cf5705e14817baf` · `delta_atoms 0` · orientation count 16
- **mover species** Ni · **depth** SURFACE/7 · anchor `(0,0,0)`
- **In words:** one Ni atom at the anchor site hops into the neighbouring vacancy at `[1,1,0]` — a single in-plane first-neighbour vacancy exchange in a surface layer. `delta`: `(0, 0, 0) NI->EMPTY` / `(1, 1, 0) EMPTY->NI`; `arrows`: `(0, 0, 0)->(1, 1, 0) Ni`.

**2 · Geometry**

- n_movers **1**; 130-atom cluster; 225-site context (r_ctx 8.5 Å), not truncated
- mover displacement init→final **2.541 Å = 1.021 × 1NN** (1NN = 2.489 Å); init→saddle **1.416 Å**, re-search saddle displacement 1.446 Å (agreement tolerance |Δ| ≤ 0.3 Å — passed)
- projection snap residual (max over cluster) **0.099 Å** before re-relaxation, **0.090 Å** after; re-relaxation moved atoms by at most **0.109 Å**; mover residual in the initial state 0.000 Å
- final-state mover snap residual 0.053 Å — a complete, on-lattice hop; nothing anomalous

**3 · Kinetics**

- members in the verify run: **1** (singleton) · Ea_rep **0.8032 eV** · no spread (single member, `Ea_std` undefined)
- harvested pair: ν₀_f **2.114e+13 Hz** (inside the 1e12–5e13 acceptance band) · padded-cluster diagnostic ν₀ 1.957e+14 Hz (ABOVE the band — diagnostic only, never fired)
- reciprocity: `pair_status = linked`, backward class `47dcaa870d74`, dE(pair) -0.02097 eV; re-search dE **-0.0205 eV**
- re-search: Ea **0.7980 eV** (ΔEa **-5.2 meV**, in band), 1 imaginary mode, pARTn ladder length 11
- **current status** — verify-run catalogue: `pending` / `pending_research`; phase-2 29-run merge: **absent**; 2026-08-14 NiCr corpus: **absent**

**4 · Flux / leverage**

- verify_fix_T500_1vac (the campaign corpus): **0.111 expected firings = 0.04 %** of run flux; 0.4 % of the review list's own 25.43
- 2026-08-14 NiCr production corpus: **not present** — this class did not recur in any of the 60 production runs, so the verify run is its only evidence

**5 · The review question — the flickering token, side by side**

```
stored (harvested)   HOLLOW_FCC(7, 7, 8, 11, 11)
re-searched          HOLLOW_FCC(7, 7, 11, 11)
```

- coord_sig length changes 5 → 4; the multiset loses/gains ['8'] — entries are a *sorted multiset*, so 'position' is only meaningful as the count of each coordination value: before {7, 7, 8, 11, 11} vs after {7, 7, 11, 11}
- `kind`: **unchanged (HOLLOW_FCC)**; `start_rank` 0 on both sides (single mover)
- what moved across the cutoff: site `(1, -1, 0)` (coordination 8) moves OUT of the 2.8624 Å shell: d/cut 0.9961 → 1.0020, i.e. it sits 5.7 mÅ from the boundary
- projection frame: **identical gauge** on both sides (D4h identity op), so the raw-field comparison and the canonical comparison agree
- token substitution test: replacing the re-searched token with the stored one **recovers the stored class_id**; a token-blind identity makes the two **equal**. The saddle token is therefore the sole identity-changing difference.
- §10.3.5 same-action double count: **no sibling present** — no other class in the 2026-08-14 NiCr corpus (nor in the verify-run catalogue) shares this class's delta/arrows/context/depth under a different token, so the flicker has not fragmented this channel *yet*. It is the same mechanism as the idx 76 pair; only the harvest happened to land on one face.

**6 · Recommendation (agent — awaiting Stephen's ruling): KEEP — graduate on the harvested pair**

Lowest flux in the list (0.111 firings, 0.03 % of run flux) and the least consequential either way. One atom crosses outward by 5.7 mÅ, kind stable, barrier agreement 5.2 meV. Recommend graduating it with the rest for uniformity of policy rather than carrying a 1-class exception.

---

## Appendix A — method and provenance

| what | how |
|---|---|
| re-keying v1 → v3 | `idx_ref` lineage into `sweep_catalogue_2026-07-31_phase2/verify_fix_T500_1vac_v3_raw.parquet` (2026-07-29 memo §8.3). All 15 land 1:1; none in `…_raw_discarded.parquet`. Cross-checked by re-projecting each stored row with today's `project_event` + `canonical.class_id` — the v3 ids reproduce exactly. |
| before/after projections | `project_event(coloring=FULL, rcut=8.5, d_max=3, r_ctx_min=3.6, nominal_a=3.52)` — the campaign's own constants (`rc_common.py`) — on the stored reference-table row and on the campaign's re-relaxed `R1`/`Rsad`/`R2` (`jobs/idx<N>/mins.npz`, `sadstate.npz`), truncated to `n_real`. Identical to what `rc_accept.assess` did in July. |
| cutoff margins | replicates `_saddle_coord_sig`: distance from the mover's saddle position to each occupied site's *ideal* lattice position, against `1.15 × frame.h × √2 = 2.8624 Å`. Before-rows are mapped through the aligning D4h op first, so the crossings are gauge-comparable. |
| token-only proof | `canonical.class_id(dataclasses.replace(pe_after, saddle_tokens=pe_before.saddle_tokens))` vs the stored id (15/15), and both sides with a neutral token (15/15 equal). |
| corpus status | `/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/merged_v3_NiCr.parquet` and `…/merged_v3_NiFe.parquet`, `sweep_catalogue_merged_v3.parquet` (phase 2, 29 runs), `impl/catalogue_v3_qc_veto_stamped_impl.parquet` (v1-keyed). Read-only. |
| flux | verify-run: `research_campaign/flux_restatement_post_graduation.csv` (320.61 total firings). Production: `research_campaign_nicr/class_flux_nicr.csv` (2026-08-15, 116,099.7 total firings, reachability-corrected) — the artifact built by the parallel NiCr flux track tonight. |
| token-blind corpus grouping | key = (delta, arrows, all 225 context rows, depth, delta_atoms, coloring) hashed per class; a lower bound on merges, since two token-siblings could in principle canonicalise into different frames. |

## Appendix B — the two small code observations (not decisions)

1. `rc_accept._token_only_diff` (`research_campaign/rc_accept.py:30-40`) compares raw `anchor0`/`delta`/`context`/`movers`, so a re-search whose local frame lands in a different D4h gauge is reported as a structural change. It mislabelled 3 of these 15 and, because the Q7 hysteresis rescue is gated behind it, denied 2 of them an already-approved acceptance. The byte-identical file is in use on the NiFe track.
2. `_saddle_coord_sig` (`event_projection.py:1058`) uses a hard `1.15 × 1NN` cutoff with no hysteresis, while the `kind` classifier it ships next to has an explicit ±0.12 × 1NN band for exactly this reason (`_SADDLE_COORD_BAND`, added for 'Geom-7/M1 round() boundary flicker'). Both fields land in the same class digest. Changing this is a CANON bump — noted for a future one, not proposed here.

## Appendix C — files

- this packet: `/home/kerr/pykmc/pylatkmc/.scratch/phaseC/sweep_catalogue_2026-07-31_phase2/REVIEW_PACKET_15CLASSES_2026-08-15.md`
- machine-readable companion (15 rows, 58 columns): `…/review_packet_summary.csv`
- source review list: `…/review_list_v3.csv` · campaign log: `…/phaseC/research_campaign/campaign_log.csv` · protocol + decisions 8/9: `~/pykmc/onlattice_design/RESEARCH_CAMPAIGN_PROTOCOL_DECISION_2026-07-22.md`
- separate track, do not merge: `…/phaseC/TOKEN_MISMATCH_VERDICT_2026-08-15.md` (§3 zero overlap, §5 P0-only residual gate, §10.3.5 same-action double counts)
