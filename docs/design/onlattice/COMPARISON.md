# Unblinded comparison — FINAL_DESIGN (clean-room) vs pylatkmc (incumbent)

**Date:** 2026-07-17. **Inputs:** `FINAL_DESIGN.md` (4-designer competition → judge panel →
synthesis → 3-lens red team → repair; 12 Opus agents, 29 findings addressed, 0 rejected) vs
pylatkmc @ `ingest` branch (CLAUDE.md + PATTERN_DB.md + CATALOGUE_SCHEMA.md + FAMILY_REGISTRY.md +
source spot-checks). All incumbent claims below verified against code, not docs.

## Verdict up front

**Hybrid.** The blinded process independently converged on pylatkmc's architectural family —
compiled pattern-DB processes with multi-site Conditions/Actions, defect-anchored matching,
BKL selection, runtime-evaluated Arrhenius rates, kmos lineage. That convergence is strong
validation of the incumbent's *skeleton*. But every layer the red team scored as
catalogue-poisoning in the draft is the layer pylatkmc actually ships today: hand-curated
coarse class identity, mean-barrier rates, exact-match-only lookup, no reverse pairing. And two
incumbent limitations are mission-blocking for NiCr/NiFe dealloying regardless of design taste
(Ni-hardcoded movers; concerted ≥3 excluded).

**Recommendation: keep pylatkmc as the execution substrate and implementation vehicle; replace
its identity/catalogue layer with FINAL_DESIGN's canonical decorated-stencil identity; adopt the
design's rate-space aggregation, fallback regressor, and loop components as "ingest v2" + a new
projection/coverage toolset.** Do not greenfield the C engine; do not keep the incumbent
catalogue layer.

## 1. Convergent — the competition validated these incumbent choices

| Both agree on | Incumbent | FINAL_DESIGN |
|---|---|---|
| Compiled pattern/process DB, not env-lookup cube | Process IR + generated decision tree | oriented full-context patterns |
| Multi-site occupancy-change events | `Actions` list (2-atom exchanges live) | `DeltaSite` set, first-class ≥3 |
| Defect-anchored matching, active-site locality | `active_filter` (vacancy-adjacent) | rarest-predicate anchors |
| Runtime rate evaluation (one binary, any T, φ) | `rateconst_eval(rc, T, φ)` | Arrhenius at step time |
| Dissolution as a competing BKL class (Erlebacher) | `ni_dissolution_demo`, analytical family | §14, `X → EMPTY` via same schema |
| Audit-aware curation, per-class provenance | audit_log verdicts → assignment | gates G1–G7 + audit queue |
| Sites never re-index under dissolution | fixed lattice + `SP_VACANT` | `EMPTY` growth, no re-index |

## 2. Divergent — where FINAL_DESIGN wins (verified evidence)

1. **Class identity — the decisive difference.** Incumbent: 14 hand-curated `FCCFamily` seed
   rules over the *analysis classifier's* labels (`motif_family_3d`, `direction_family_3d`,
   `site_class_3d`) + coarse vacancy-count buckets (`nv1=2_nv2=0`). Identity is coarser than the
   harvest, depends on classifier internals, and novelty = the `unresolved` pile driving *manual*
   registry iteration. FINAL_DESIGN: automatic, order-independent, provably complete D₄ₕ
   canonical form over the full `r_ctx` decorated context; novelty = a key never seen; no
   registry to maintain. The red team's four *critical* statistics findings (Jensen fold-in,
   tautological balance gate, novelty absorbed as instance, fictitious class-mean ΔE) are all
   symptoms of identity-coarser-than-physics — i.e. **they apply to the incumbent's family+bucket
   scheme today**, not just to the draft.
2. **Species-awareness (mission-blocking).** Every diffusion hop emits mover species Ni —
   `translator.py:404-415` with the default documented at `translator.py:31` and confirmed by
   pylatkmc/CLAUDE.md ("a non-Ni model compiles and runs but never diffuses its real species —
   no error at any stage"). FINAL_DESIGN is species-resolved end to end (full-colour canonical
   keys; grey mode is an explicit catalogue flag).
3. **Concerted ≥3 events (mission-relevant).** Incumbent excludes them
   (`concerted_multisite`, `fit_barrier=False`). FINAL_DESIGN makes them first-class with a
   worked NiCr 3-site example.
4. **Rate statistics.** Incumbent aggregates `Ea_mean_eV`/`Ea_median_eV` per family+bucket
   (`build_family_rate_table.py:47-51`) → mean-then-exp Jensen error; the physical flux is
   dominated by the lowest-barrier member (a "tight" 0.05 eV spread at 300 K ≈ 6× rate error;
   family buckets are far wider than 0.05 eV). FINAL_DESIGN aggregates in rate space,
   `k = ⟨ν₀ᵢ·exp(−Eaᵢ/kBT)⟩` over sorted members (§6.1).
5. **Zero-flux protection.** Incumbent is exact-match-only; its own CLAUDE.md documents the
   failure ("`ShellCondition` … the Process **silently never fires** — looks like 'rate too
   low'"). FINAL_DESIGN: lookup + per-family BEP/GCN fallback + out-of-hull hard novelty +
   never-zero floor + flag registry feeding the next harvest leg (§6.2–6.3).
6. **Microscopic reversibility.** Incumbent families are directional with no pairing constraint
   (`…exchange_up` / `…exchange_down` are unrelated rows). FINAL_DESIGN recovers per-pair ΔE
   from linked forward/backward pyKMC rows (shared `id_saddle`), symmetrises, and synthesises
   *balanced* reverses when one side is missing (§7.2).
7. **Step-loop scaling.** Incumbent rescans and re-enrols **every active site every step**
   (`runtime/src/core/kmc.c:129-140`). Fine at 1–2 vacancies; approaches O(N)/step in the porous
   dealloyed end-state. FINAL_DESIGN repairs incrementally (dirty-ball invalidation + group-BKL
   Fenwick, §5.4). Not urgent for the ladder's first rungs; structural for production.
8. **The loop itself.** Incumbent's ingest is a one-way harvest (events → CSV → codegen).
   FINAL_DESIGN adds the components the alternation needs: forward snapshot projection with
   deterministic hysteretic snapping, reverse byte-stable ideal-site emission, coverage report,
   flag-driven exploration priorities, and the catalogue-independent physics probe (§2, §7).

## 3. Where the incumbent wins — keep all of this

- **A working, tested C+MPI runtime**: lattice/coord codes, avail_sites, replica MPI, INI/kmcinit
  I/O, CMake discipline, committed-proclist reproducibility, byte-deterministic codegen with a
  two-seed regression test. FINAL_DESIGN is paper; this is running code with hard-won invariants.
- **Dissolution already implemented** (runtime overpotential φ, `epsilon_table.toml`,
  electrochemical RateConst path) — FINAL_DESIGN only *specifies* it.
- **The HTST ν₀ recovery pipeline** (`trajectory_recovery`, canonical fallback, per-bucket
  medians + provenance audit) — FINAL_DESIGN *assumes* per-member ν₀ exists; this is the thing
  that produces it.
- **Cross-engine validation harness** (MSD/diffusivity vs pyKMC) — becomes the acceptance gate
  for the new identity layer.
- Pragmatics: pydantic IR + golden-file tests, ruff/mypy gates, model spec UX.

## 4. Integration path (staged, keeps every cycle shippable)

- **Phase A — rate fix + ingest v2 (pure Python, no C changes).**
  1. Immediate, independent win: switch `build_family_rate_table` barrier aggregation to
     rate-space (design §6.1) — correct even while the old family scheme is still in use.
  2. Implement projection (§2), event projection (§3), and canonical identity (§4) as new
     `pylatkmc.ingest` modules emitting the `EventClass` catalogue (Parquet, `class_id` keys).
     `FAMILY_REGISTRY` stays temporarily as a *reporting/cross-check view* (note:
     design's `family_id = move_shape ⊕ depth_sig` is a different, derived concept).
- **Phase B — translator v2.** Consume `EventClass` rows → Process IR. Required changes:
  species-resolved movers (delete the Ni default — parameterise per class), extend the
  `NeighbourCode`/`coord_table` vocabulary to the full `r_ctx` shells (≥3NN), orient-expand
  under D₄ₕ at translate time (systematises the incumbent's per-direction emission).
- **Phase C — runtime deltas.** (a) Incremental repair: reuse `touchup_a` but invoke it only on
  sites within pattern-support of the executed event instead of the full active set; keep the
  full rescan behind a debug flag as the design's I5 oracle. (b) A fallback-rate channel +
  per-instance flag counters + coverage accumulators.
- **Phase D — loop driver.** File-based forward/reverse mapping tools, coverage report, priority
  exploration list, physics probe cadence; then the closed-loop script (decision 1's staged
  promotion).

**Rejected alternatives.** *Greenfield C implementation of FINAL_DESIGN*: duplicates the
runtime/MPI/dissolution/build work that already exists and discards the determinism test
discipline — months of cost for no representational gain. *Pure incumbent*: the identity layer's
critical pathologies are structural (see §2 items 1, 4, 5, 6), and items 2–3 block the NiCr
mission outright.

## 5. Open engineering risks of the hybrid

1. **Decision-tree size under full-context predicates.** The nested-switch `touchup_a` may not
   scale to full-`r_ctx` patterns; may need data-driven pattern tables interpreted by a generic
   matcher instead of generated switches. This is the main open question — prototype in Phase B.
2. **NeighbourCode vocabulary growth** (3NN+ = 24 more codes/site in `coord_table`): memory ×
   sites; bounded, but check at 10⁶ sites.
3. **Catalogue richness** (design W7): full-context + full-colour multiplies classes; the
   fallback tail and compile time need monitoring from cycle 1.
4. **Per-member ν₀** — recovery currently emits per-bucket medians; the design wants per-member
   `nu0` where available (`event_table.py` carries it when HTST is on). Plumb through, else
   geometric-mean fallback (§6.1) applies.
5. **`family_id` semantic collision** between the old registry and the design's
   `move_shape ⊕ depth_sig` — rename one (suggest `family_id` → `registry_family` in reporting).
