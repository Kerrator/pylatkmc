# Phase C rate-model architecture — decision memo

**Status: APPROVED — 2026-07-21, by Stephen.** Sign-off via the `interview-design-decisions`
stress-test (8 branches, one question at a time); binding decisions and amendments are recorded
in **§8** and inline-marked as (§8-Nx). This is an architecture decision (audit gaps 1+3+6); it
amends FINAL_DESIGN §6 and the Phase A contract (amendments applied 2026-07-21). Phase C
implementation may start, in its own thread, against this memo as approved.

**Author:** Claude Fable 5, 2026-07-21.
**Inputs:** `RESEARCH_GAPS_AUDIT_2026-07-18.md` (gaps 1, 3, 6);
`DEEP_RESEARCH_CLAIMS_2026-07-18.json` (72 adversarially-verified claims — cited as
`[pass :: status #n]`); the independent cross-check `FABLE_CROSSCHECK_SYNTHESIS_2026-07-21.md` +
`FABLE_CROSSCHECK_DIFF_2026-07-21.md`; and a **new empirical anchor** measured for this memo
(§2, script `ridge_anchor_2026-07-21.py` in this directory — run from inside `pylatkmc/`).

**Conditions stamp (applies to every number below):** production NiCr `verify_fix_T500_1vac`
ingest, rcut 8.5 Å, Linux box; 439 classes / 445 harvested events (433 singleton classes);
T_ref = 500 K (kT = 0.0431 eV); holdout = 10-fold CV split **by class** with nested α selection.
445 events is a small sample — every RMSE here carries ~±0.02–0.05 eV sampling noise and all
conclusions are conditional on this corpus.

---

## 1. The decision

**Recommended architecture for Phase C's rate channel: (b)+(c) layered — a continuous,
detailed-balance-safe KRA-form surrogate as the rate model for lattice-representable events,
with an uncertainty-gated on-the-fly re-search channel as a first-class component, not a
fallback. Option (a) — the static per-family φ regressor of FINAL_DESIGN §6.2 as the majority
channel — is rejected on direct measurement.**

Concretely, the rate of a lattice-representable candidate move is:

```
Ea_f = E_sym(env; θ)  +  ½·ΔE_lattice(σ_before → σ_after)          # KRA form
k_f  = ν0(env) · exp(−Ea_f / kBT)
```

- **E_sym** — a continuous regression of the *symmetric* (endpoint-exchange-invariant) barrier
  component on one-hot occupation features of the local environment (start: the ≤2-body basis
  already sketched, extended with selected 3-body terms; upgrade tier: GP with leverage-growing
  variance, per FINAL_DESIGN §6.2's M2 machinery, which survives this memo).
- **ΔE_lattice** — from **one** lattice energy model H(σ) (cluster-expansion-style, fit to the
  harvested endpoint/`dE_pair` data), never from per-class means. Because the numerator is
  exchange-symmetric and ΔE comes from a single state function, **detailed balance holds by
  construction** [1 :: u#2 (lead), u#4 (lead) — and elementary algebra on the Metropolis/KRA
  form, so safe to adopt while the citation is verified].
- **ν0** — per-event-pair where harvested; the ν0_f/ν0_b ratio must be carried, not assumed 1
  (§2.4). Backward prefactor from the same pair data or the vibrational-partition-ratio
  constraint — flagged as an open validation, not settled literature (cross-check diff D4).
- **On-the-fly channel** — any instance that is out-of-hull / high-leverage, involves a species
  count the family has never seen, or carries flux above a threshold while surrogate-rated, is
  routed to the off-lattice pyKMC leg for re-search with top priority (the §6.3 flag_registry
  mechanism, upgraded from "exploration hint" to "rate authority for the flagged population").
  This is the field's only supported answer for strongly-relaxed/concerted events
  [2 :: c#0–c#8; 1 :: u#0].

**The exact-match catalogue is retained — re-scoped.** It remains the identity layer, the
training corpus, the provenance record, and a per-class QC anchor (the §6.2 consistency
diagnostic inverts: the surrogate is checked against measured classes). It stops being a
*separate rate law*: a measured class's rate is the surrogate evaluated at that environment,
validated against (not overridden by) its harvested barriers. *(Amended at sign-off, §8-N6:
at Phase C entry measured classes fire their raw harvested pairs; a V2-gated staged switch
moves them to the DB-safe anchored form `E_sym_measured + ½·ΔE_H`.)* With 433/439 classes singleton,
"class rate" and "harvested barrier" are the same number today, so this re-scoping changes no
current behaviour — it changes what *grows* as the corpus fills (no within-class averaging ever
starts, so `split_tol` never becomes load-bearing; see §4).

## 2. The empirical anchor — the audit's "ungrounded" is now a number

Fit: the audit's floor candidate — one-hot ≤2-body ridge (60 features: per-shell per-species
counts, 1nn bond counts n_XY, Erlebacher mover-local broken bonds, depth/Δ scalars) on
initial-environment occupations, class-level holdout.

| Population | n | holdout RMSE | null (σ of Ea) | median rate error @500 K |
|---|---|---|---|---|
| All events | 445 | **0.451 eV** | 0.665 | ×414 |
| Clean 2-site hops | 253 | 0.354 eV | 0.665 | ×144 |
| Multi-site / non-conservative | 192 | 0.552 eV | 0.639 | ×3891 |
| Mover includes Cr | 115 | **0.558 eV** | 0.763 | ×1121 |
| Lowest-quartile barriers | 112 | 0.491 eV | 0.335 | ×2291 |

Four findings, each decision-relevant:

1. **The static φ floor fails outright as a majority channel: 0.45 eV ≈ 10 kT.** Literature puts
   this model class at 0.2–0.3 eV on curated single-hop corpora [1 :: c#1, c#3]; our
   heterogeneous, surface-heavy, strongly-relaxed corpus is worse. In-sample RMSE is 0.38 eV —
   the representation, not just the data volume, saturates: **more data alone will not rescue a
   ≤2-body static φ on this event population.**
2. **It systematically kills the dealloying channel.** On the lowest-quartile barriers the model
   over-predicts 95% of events, mean bias **+0.377 eV** → the fast Cr-mediated tail is
   rate-suppressed by ~10³–10⁴×. This is the audit's gap-3 fear (percolation through the
   low-barrier tail [1 :: c#0, c#6]) reproduced on our own data, at the φ level rather than the
   split_tol level. Cr-mover events are the worst-fit subpopulation (0.56 eV).
3. **The KRA decomposition is the single biggest measured lever.** Adding ½·dE_pair as a feature:
   full corpus 0.451 → **0.295 eV**; clean hops 0.354 → **0.175 eV** (Spearman 0.67 → **0.89**;
   Cr movers 0.47 → 0.21). Regressing the symmetric part (Ea − ½ΔE) directly gives the same
   0.171 eV. Our own barrier↔driving-force correlation is r² = 0.51 — between Ta-W's 0.21
   [1 :: c#9] and the Kinetic-Ising ideal, so *neither* a pure driving-force model *nor* a
   symmetric-only model suffices: the sum is what works. Caveat: 0.175 eV uses the *measured*
   pair ΔE; runtime substitutes H(σ)'s prediction, whose error adds (validation V2).
4. **ν0_f = ν0_b is false in this corpus.** Median ν0_f/ν0_b = 1.0 but 60% of the 445 pairs fall
   outside [½, 2]; q10–q90 spans 0.09–11 — up to ~×11 rate error from prefactors alone.

Even the best measured configuration (0.175 eV, clean hops, KRA-informed) is **3.5× above the
~0.05 eV target**. Literature says 0.04–0.1 eV is reachable for exactly this alloy family and
model family [1 :: c#4, c#13] — but with curated corpora of 2,000–32,000 single-hop barriers.
Conclusion: **no static model reaches the accuracy floor on today's 445-event corpus**, which is
what forces (c) as a first-class channel and makes the learning-curve validation (V1) the gate
for shifting rate authority to the surrogate over time.

## 3. Rejected alternatives — and why

- **(a) Static per-family φ (FINAL_DESIGN §6.2 as written) as the majority-flux rate law.**
  Rejected on measurement (§2.1–2.2: 0.45 eV, tail suppression) and literature ([1 :: c#3, c#5,
  c#8]: the 0.2–0.3 eV tier; BEP's reputation is from surface chemistry, not bulk alloy
  migration). Additionally untrainable as specified: 214 `family_id`s over 439 classes ≈ 2
  classes/family — below any fitting threshold, including the design's own n_min ≈ 8. The M2
  out-of-hull machinery and flag_registry are *retained*; the per-family regressor grid is not.
- **(b-pure) Continuous surrogate replacing everything, no re-search channel.** Rejected:
  (i) 192/445 harvested events are multi-site or non-conservative projections, and the
  five-pass sweep found **zero** confirmed evidence that concerted/strongly-relaxed saddles are
  predictable from atom-centered static descriptors — the silence survived adversarial search
  (audit gap 1's "no published reassurance" stands); (ii) today's corpus is an order of magnitude
  smaller than every published success; (iii) the 316 G3-fail classes are not representable
  on-lattice at all, so *no* on-lattice rate law — discrete or continuous — can restore that
  flux; only re-search/projection redesign can (gap 2's domain; interaction noted, not resolved
  here).
- **Widening `split_tol` / class-mean rates as the growth path.** Rejected: Jensen +
  percolation [1 :: c#0, c#6] + the measured tail bias; production adaptive-KMC codes never
  consume a class-average where geometry relaxed — they re-converge per site or seed-and-research
  [2 :: c#2, c#5; leads u#1, u#11].
- **Per-pair detailed-balance patching (synthesize backward rates from class-mean ΔE).**
  Rejected: forward/backward barriers depend on different atom sets [1 :: c#10]; class-mean ΔE
  biases equilibrium SRO (gap 6); the KRA form makes the whole problem vanish by construction.

## 4. Impact on the audit gaps

- **Gap 3 (split_tol / lumping): dissolved, not re-tuned.** The surrogate assigns per-environment
  rates; classes are identity/provenance units. `split_tol` survives only as an *ingest QC
  screen* (two members of one class disagreeing by ≫ measurement noise still signals
  CONTEXT_UNDERRESOLVED → audit), never as a rate-averaging tolerance.
- **Gap 6 (detailed balance): dissolved by construction** via the KRA form (single H(σ) for the
  antisymmetric part). G2 (tautological) is replaced by: (i) the closed-loop affinity test the
  audit already names (Andersen/Reuter lineage) run on cycles of the generated proclist;
  (ii) a ν0-pair constraint check (V4). Class-mean ΔE never enters.
- **Gap 1 (φ form): answered.** Descriptor order: one-hot occupation, ≤2-body + selected 3-body,
  on the *symmetric* target; model class: ridge → GP tier with leverage-growing σ (M2 kept).
  OOD control: leverage/out-of-hull gate → on-the-fly channel (not a clamped extrapolation).
  The 214-family granularity is replaced by coarse move-topology tiers (vacancy hop / exchange /
  multi-site / non-conservative) until the corpus supports finer conditioning.

## 5. Required empirical validations before Phase C implementation freezes

- **V1 — Learning curve (gates rate authority).** Refit E_sym at corpus sizes N = 100…445 (and
  each future harvest cycle); extrapolate holdout RMSE vs N. Defines when surrogate-rated flux
  may stop being flagged. Acceptance to *reduce* on-the-fly routing: holdout RMSE ≤ 0.10 eV on
  clean hops AND tail bias ≤ kT (see V3).
- **V2 — ΔE channel error.** Fit H(σ) to endpoint data; measure |ΔE_H − dE_pair| distribution
  over the 445 linked pairs. The 0.175 eV result assumed this error ≈ 0; budget it explicitly.
- **V3 — Tail-fidelity gate (the dealloying guard).** On the lowest-quartile barrier holdout:
  signed mean error must be < kT (today +0.377 eV) and Spearman > 0.9 in the tail before the
  surrogate is trusted on Cr-channel flux. This is the memo's non-negotiable acceptance test —
  it is the number that decides whether dealloying physics survives the rate model.
- **V4 — Prefactor asymmetry.** Decide ν0_b policy (harvested pair value vs Z_vib-ratio) and
  validate on the 445 pairs (60% outside [½,2] today). pyKMC's HTST machinery can measure the
  Z_vib ratio directly on a sample of pairs.
- **V5 — OOD-gate calibration.** Leverage/hull distance vs realized error on held-out
  Cr-enriched environments; verify the gate actually fires on the (worse-fit) Cr subpopulation
  before production dealloying runs depend on it.
- **V6 — Runtime cross-check.** The §6.2 consistency diagnostic, inverted: log
  |Ea_surrogate − Ea_harvested| on every measured class each cycle; drift beyond V1's band
  triggers refit (M3 machinery retained).

## 6. What changes in the documents

- **FINAL_DESIGN §6.1:** rate-space aggregation stays for *reporting/QC*; the executed rate for a
  measured class follows §8-N6 (raw harvested pairs at Phase C entry; V2-gated switch to the
  anchored form — no behavioural change lands until Phase C ships). §6.2:
  replace the per-family degree-≤2 φ ridge with the KRA-form pair (H(σ) + E_sym tiers as §1
  above); keep M2 (out-of-hull), M3 (drift refit), §6.3 (flag/never-zero) with the flag upgraded
  to on-the-fly routing authority. Add §6.4: the on-the-fly channel contract (flag → priority
  re-search in the next off-lattice leg; synchronous re-search is a Phase D option).
- **phaseA_contract:** `phi` field becomes the E_sym feature vector (symmetric target); add
  `dE_model_version` and `nu0_pair_policy` fields; `fallback_stats` becomes
  (leverage, hull_flag, model_version, tier). Schema bump; Phase A parquet unchanged (fields stay
  empty until Phase C).
- **Memory (`pylatkmc-research-gap-audit`):** headline refined from "replace catalogue with
  continuous surrogate" to the layered (b)+(c) verdict of this memo. *(Applied 2026-07-21.)*

## 7. Cross-check provenance

The parent judge synthesis and my independent cross-check agree on every per-pass verdict
direction; the material differences (catalogue-replacement strength, which population a φ can
serve, CR-selection scope, ν0 inference) are enumerated in `FABLE_CROSSCHECK_DIFF_2026-07-21.md`
and are reflected in §1/§3 above. Items D1/D2 of that diff are what turn the parent's
"replace the catalogue, do it first" into this memo's "surrogate as rate *form* now, rate
*authority* gated on V1/V3, on-the-fly channel co-equal."

---

## 8. Sign-off notes — 2026-07-21 interview (binding)

Stress-test run as the memo requested (`interview-design-decisions`; 8 branches, one question at
a time, recommended answer given per question). §1 architecture and §5 gates **approved** with
the decisions below. Evidence labels follow the memo's hierarchy throughout.

- **N1 — static φ / drift detection.** Static φ dropped entirely, *including* as a drift
  detector. The drift-detection goal (know when runtime environments have departed the training
  corpus → return to pyKMC to harvest) is adopted as a first-class requirement, served by the
  per-cycle out-of-hull/leverage fraction in the M2 feature space, calibrated per V5. An
  ensemble-disagreement detector is revisited only if leverage proves insufficient at larger
  corpus size.
- **N2 — KRA form.** Adopted per §1. Detailed balance rests on the exchange-symmetric-numerator
  algebra; the CPC citation remains an unverified lead and is not load-bearing.
- **N3 — H(σ) training corpus (same-potential exclusivity).** H(σ) trains only on energies from
  the pyKMC production potential: harvested endpoints **plus direct same-potential
  lattice-configuration evaluations** (no pARTn search needed) — never DFT or literature values.
  Remedy for a failing V2 is more same-potential training data, never per-class patching. A
  potential swap retrains H(σ) from scratch under a new `dE_model_version`.
- **N4 — ν0 policy (two tiers, mirroring the energy architecture).** Harvested classes fire
  per-pair Vineyard ν0_f/ν0_b as-is — DB-safe by construction, since the saddle frequencies
  cancel in the ratio, leaving ∏ω(init)/∏ω(final), a per-state quantity. The surrogate channel
  mirrors KRA in log space: `ln ν0_f = L_sym(env) + ½·Δln Z_vib` from one per-state vibrational
  model; starting tier is L_sym = per-move-topology-tier constant with Δln Z_vib = 0, the ×11
  q10–q90 spread acknowledged as the error band. V4 validates by measuring ∏ω ratios with
  pyKMC's HTST machinery on sampled pairs. Evidence label: in-house measurement (§2.4) +
  standard harmonic TST — *not* a literature finding (cross-check items D4/D5).
- **N5 — on-the-fly channel contract.** Accepted as §1 (flag → provisional surrogate rate,
  never-zero → priority re-search in the next off-lattice leg; synchronous re-search stays
  Phase D). **Binding addition: the flagged-flux fraction per KMC cycle is a first-class
  contract output** — simultaneously the flood-control instrument, V1's production acceptance
  metric, and N1's drift trigger. Honest caveats recorded: routing volume is unmeasured today;
  provisional-rate dynamics between flag and re-search are an engineering compromise with no
  published analogue.
- **N6 — measured classes (amends §1/§6).** At Phase C entry, measured classes fire their raw
  harvested pairs (per-pair DB exact; the residual noise-scale closed-cycle affinity — measured
  energies are not a state function of σ — is accepted and documented). **Staged migration,
  gated on V2:** when V2's median |ΔE_H − dE_pair| drops below the measured pair-noise scale,
  measured classes switch to the DB-safe anchored form `Ea_f = E_sym_measured + ½·ΔE_H` with
  `E_sym_measured = (Ea_f + Ea_b)/2` from the harvested pair — global DB becomes exact while the
  measurement's symmetric content is kept exactly. The switch is one flag in rate assembly,
  stamped per `dE_model_version`; the GP tier (M2) eventually subsumes the measured/unseen
  split. §6's former "(identical numbers today for singletons)" is corrected to: no behavioural
  change lands until Phase C ships. `split_tol` survives as an ingest QC screen only; the
  catalogue's identity/training/provenance/QC roles are unchanged.
- **N7 — gates.** V1–V6 accepted **verbatim**. One amendment was offered and **rejected**,
  recorded here so the reasoning survives: a noise-ceiling clause on V3's tail-Spearman
  threshold (restricted range ~0.3 eV + ±0.02–0.05 eV barrier noise may cap achievable Spearman
  below 0.9; if V3 ever stalls at a plateau, revisit — the consequence of an unpassable gate is
  only that tail flux keeps routing on-the-fly, which is the safe outcome). New measurement for
  the record (same conditions stamp as §2; script `v3_tail_check_2026-07-21.py`, this
  directory): **KRA-informed tail signed bias +0.155 eV** (77% over-predicted), **tail Spearman
  0.709**, Cr-mover tail Spearman 0.319, full-population Spearman 0.804 (static φ: +0.377 eV /
  95% / 0.567 / 0.287 / 0.575 — memo §2 reproduced exactly). V3 fails today by ~3.6× on bias →
  at Phase C entry the low-barrier tail routes through the on-the-fly channel *by design*.
  V1's learning-curve baselines: 0.175 eV clean hops (measured ΔE), +0.155 eV tail bias. V2
  additionally serves as N6's migration gate.
- **N8 — gap 2 boundary.** Parked (own thread), with an upgraded opening deliverable: **triage
  the 316 non-representable classes** into (i) *irrelevant* — unreachable-state reverses,
  high-barrier-frozen, artifacts — dropped with recorded reason; (ii) *re-projectable* under a
  better projection/identity scheme; (iii) *genuinely relevant non-representable* — the
  on-the-fly channel's permanent load. Ranking by **reachability-corrected flux (occupancy ×
  rate)** — naive rate-weighting over-ranks fast reverses of unreachable states (Stephen's
  observation, e.g. return of an atom launched high above the surface) — auto-pre-classified,
  then human-refined via the pykmc-tools workflow (github.com/Kerrator/pykmc-tools; the proven
  auto-identify → human-refine pattern). Bucket (iii)'s flux share decides gap 2's urgency.
  **Human veto becomes a provenance field** in catalogue QC: a curator-excluded event stays
  excluded with a recorded reason; re-harvest cannot silently resurrect it.
