# Deep-research findings — pylatkmc Phase C/D (verified)

Companion to `RESEARCH_GAPS_AUDIT_2026-07-18.md`. Five `/deep-research` passes (one per consolidated
gap-focus), each: 5–6 web-search angles → source fetch + falsifiable-claim extraction → **3-vote Opus
adversarial verification** (≥2 refutes kills a claim) → synthesis. The automated synthesis agent hit
the session usage limit on every pass, so **this report is the synthesis, written by the judge (Opus)
integrating all five verified claim-sets against the design** — a stronger merge than the per-pass
agent could do, because it cross-references the passes and the audit.

## How to read the confidence tags

- **[CONFIRMED n-m]** — survived Opus 3-vote adversarial verification (n confirm, m refute). High
  confidence the claim matches its quoted source. Verification checks claim-vs-quote + a
  contradicting-source search; it does **not** independently re-derive the DOI/venue.
- **[UNVERIFIED]** — single extraction from a **primary** source whose 3 verifier votes all *errored
  out on the session limit* before adjudicating. **Not refuted — just not stress-tested.** Plausible
  and on-topic; treat as a lead to confirm, not a settled fact.
- **[REFUTED]** — ≥2/3 Opus skeptics refuted it; listed for transparency, do not rely.

**Global caveat:** citations were located by search/fetch agents. The claim↔quote link is
adversarially checked; the exact reference string is plausible but **not hand-verified** — check any
paper before citing it in writing or committing a design to it.

---

## Bottom line per gap (the verdicts)

| Gap | What the literature settles | Confidence | Decision for pyKMC |
|---|---|---|---|
| **1+3 Continuous surrogate vs discrete catalogue + split_tol** | A continuous local surrogate hits **RMSE < 0.1 eV (often < 0.04 eV)** for FCC vacancy-migration barriers *in the Ni-Fe-Cr family itself*; low-order broken-bond/BEP sits **at or above 0.2 eV**. KRA/Kinetic-Ising is **provably insufficient** for concentrated alloys. | High | **Replace the discrete exact-class catalogue + split_tol with a continuous per-environment barrier surrogate.** It beats the planned low-order fallback *and* dissolves split_tol (no within-class averaging → no lumping tolerance). |
| **1e / percolation** | Barrier distributions are **bimodal**; transport **percolates the low-barrier tail** (confirmed in Ni-Fe-Cr and Ta-W). | High | Trimmed-mean class aggregation **does** suppress the dominant Cr channel — the audit's fear is confirmed. Do not aggregate away the low-barrier members. |
| **6 Detailed balance** | Enforce per-pair via **KRA symmetric + antisymmetric split from one energy model**; forward/backward barriers depend on **different atom sets** (weakly correlated), so ν0_f ≠ ν0_b in general. | Med (direction confirmed; exact ν0 recipe thin this pass) | Adopt the KRA endpoint-split so detailed balance holds by construction; do not assume ν0_f = ν0_b. |
| **2 Projecting relaxed events** | Mature engines (k-ART) do **not** widen a snap tolerance — they use **topological identity**, detect the "one class → many geometries" degeneracy by **reconstruction failure** (saddle disappears), split by **adjusting the graph cutoff**, and **always re-converge the reused event's barrier** (~0.01 eV). | High | Stop tuning snap_tol. Recognition = topology; rate = always re-converged. Route non-representable events back to off-lattice search. |
| **2d rate-error-budget tolerance** | **Nothing found** sets a projection tolerance from an allowable rate distortion. | — (genuine gap) | pyKMC would have to build this itself; the audit's "sparse, proceed on judgment" stands. |
| **4 Bookkeeping** | **Composition-rejection selection is exact and O(log(rmax/rmin)) for continuous rates — micro-groups unnecessary.** The binding constraint is the **propensity-update path, not selection.** The dirty-ball invalidation bound is a real correctness surface that **even Zacros only asserts, never proves.** | High | Adopt CR selection (retires the dense table + the micro-group worry). The incremental-repair radius is the actual risk — build it with an independent oracle, or benchmark an optimized full rescan first. |
| **5 Stop criteria** | **Rate-weighted "fraction of total rate found" is provably superior to count-based** (new-classes→0); its MSE vanishes. But it is **biased low (over-optimistic) when fast events are found first.** | High | Replace new-classes→0 with a rate-weighted completeness estimator — **and keep an independent probe**, because the rate-weighted metric is itself over-optimistic under exactly pyKMC's biased-trajectory condition. |
| **7 Event identity** | Canonical graph labeling (nauty/Traces) gives the **iff + label-invariance** guarantee the anchored D4h-min lacks; k-ART anchors multi-site events to the **most-displaced atom (frame-independent)**, and the automorphism group (→ symmetry number) falls out **for free**. Canonical labels **alone are insufficient** for symmetric events — must add direction of motion. | High | Re-base event identity on nauty-style canonical labeling; anchor by most-displaced atom, not lex; carry the automorphism order as the symmetry-number rate weight; add motion direction to separate symmetric variants. |
| **8 Layer-dependent barriers / porous** | Near-surface FCC(100) vacancy barriers are **layer- and species-dependent** (~0.4 eV surface vs ~0.7 eV bulk; Ni-Cr near-surface hops species-specific); dealloying KMC classifies sites by **coordination number**, not height. | Med (primary sources, votes lost to limit) | The correct catalogue symmetry is **layer-dependent**, not a global O_h/D4h choice — topology-as-identity handles this automatically. Replace the z(x,y) height labeling with coordination-based classification. |

---

## Pass 1 — Continuous barrier surrogate vs discrete catalogue (gaps 1, 3, 6)

**Verdict: the continuous surrogate wins decisively, and this collapses three audit gaps into one design move.**

Confirmed:
- Continuous one-hot occupation surrogate (PCA+ridge) predicts FCC Al-Mg-Zn vacancy barriers to **RMSE < 0.04 eV, R² ≥ 90%** — far finer than the 0.15 eV split_tol. [CONFIRMED 3-0] arXiv:2206.02879
- SVR on local-chemical-environment descriptors: **NiFeCr RMSE < 0.1 eV (R > 0.89); quinary NiFeCrCoCu < 0.07 eV (R > 0.95)** — inside 0.15 eV, in the exact alloy family. [CONFIRMED 3-0] Front. Mater. 2021 (10.3389/fmats.2021.673574)
- A single ANN on ~32,000 NEB barriers predicts Ni-Fe barriers on-the-fly per site across the full composition range, including SRO configs. [CONFIRMED 2-0 / 3-0] J. Alloys Compd. 2023 (S0925838822048484)
- Beyond-KRA transition-state cluster expansion (Ta-W): **0.12 / 0.18 eV RMSE** train/test. [CONFIRMED 3-0] arXiv:2605.23612
- Low-order models are the *worst*: on identical Pt-Ni data, broken-bond **0.281 eV**, KRA-broken-bond **0.227**, constant **0.214**, parabolic **0.204**, cluster expansion **0.127 eV**. [CONFIRMED 2-0] arXiv:2009.12474
- Kinetic-Ising / constant-KRA is **not broadly applicable to FCC alloys** — local distortion makes the kinetic term environment-dependent. [CONFIRMED 3-0] arXiv:2206.02879
- KRA is **provably insufficient** for Ta-W: barrier↔driving-force correlation only **r² = 0.21**. [CONFIRMED 3-0] arXiv:2605.23612
- Forward/backward barriers depend on **different atom sets** (initial- vs final-side), weakly correlated — bears directly on per-pair detailed balance and separate prefactors. [CONFIRMED 3-0] Sci. Adv. adr4697
- BEP is **not universal**, needs reparameterization per reaction class; on its surface-chemistry home turf the ML-generalized-BEP floor is **MAE 0.23 eV test**. [CONFIRMED 3-0] ChemCatChem 2022 (10.1002/cctc.202201108)
- **Percolation confirmed:** FCC-alloy barrier distributions are bimodal; low-barrier peaks = fast diffusion channels. [CONFIRMED 3-0] Front. Mater. 2021. Ta-W shows a dilute-trapping → percolated-transport crossover at x*≈9.8% ≈ the bcc bond-percolation threshold. [CONFIRMED 3-0] arXiv:2605.23612
- Binary-trained surrogate extrapolates to ternary/quaternary/quinary **without retraining** (but with **no** uncertainty-based OOD control). [CONFIRMED 3-0] Front. Mater. 2021

Refuted (do not rely):
- "Barrier variance comes primarily from the symmetric KRA term, not the driving force." [REFUTED 0-3] — the confirmed picture is the opposite emphasis: the spread is environment-driven and not captured by a constant-KRA/driving-force model.
- "Electronic descriptor χ·Sv gives 0.13–0.2 eV MAE for refractory HEAs." [REFUTED 1-2] — borderline; treat the ~0.2 eV low-order floor as coming from the Pt-Ni broken-bond numbers above instead.

Unverified but primary (votes lost to limit — strong leads):
- Detailed balance **enforced by construction** via the KRA split ΔE^b = ΔE^KRA + ½ΔE from one state-energy model. [UNVERIFIED] Comput. Phys. Commun. S0010465525002541 (the direct answer to gap-6 RQ-c).
- Barrier-model error **directly distorts dissolution kinetics**: in Pt3Ni KMC, Ni loss tracks each model's error; low-spread surrogates artificially accelerate the rare low-barrier events driving segregation/dissolution. [UNVERIFIED] arXiv:2009.12474 — the mechanism behind "compressing the distribution corrupts the dealloying tail."
- SOAP-GPR continuous surrogate with **predictive-variance gating**: uncertainty > 0.05 eV triggers a full NEB and adds it to the training set (self-evolving active learning). [UNVERIFIED] arXiv:2605.31144 — the established OOD-control answer (gap-1 RQ-d).

Judge's read: gaps **1 (fallback form), 3 (split_tol), and 6 (detailed balance)** all resolve to one decision — **regress the barrier on the local environment (KRA/CE or ML), don't lump into discrete classes.** A continuous surrogate is measured well inside 0.15 eV *in this alloy family*, the low-order fallback the audit worried about is the weakest option (~0.2–0.28 eV), and the KRA endpoint-split gives detailed balance for free. No confirmed evidence surfaced that **concerted/multi-atom** saddles are predictable from atom-centered descriptors — consistent with the audit's "thin, forces an on-the-fly channel."

## Pass 2 — Projecting strongly-relaxed events (gap 2)

**Verdict: the fix is not a wider snap_tol — it is topology-based identity + reconstruction-failure detection + always re-converging the reused barrier.**

Confirmed:
- k-ART detects the "one topological class → multiple relaxed geometries" degeneracy **by reconstruction failure** — the reconstructed first-order saddle *disappears* on refinement; that is the signal, not a residual threshold. [CONFIRMED 3-0] arXiv:1107.2417
- It splits the degeneracy by **locally adjusting the graph connectivity cutoff** until the conflated geometries separate into sub-topologies — not by tuning a global geometric tolerance. [CONFIRMED 3-0] arXiv:1107.2417
- Recognition is **purely topological**: 5.0 Å sphere (~40 atoms), 2.8 Å bond cutoff, NAUTY key; **no Cartesian residual threshold** is used for matching. [CONFIRMED 2-0] arXiv:0805.2158
- **Seed-then-reconverge decouples recognition from rate accuracy:** reused low-barrier events are re-relaxed to 0.1 eV/Å → **~0.01 eV barrier precision**, capturing the specific environment and long-range elastic effects; the catalogued value is never used verbatim. [CONFIRMED 3-0] arXiv:0805.2158
- Routing is **binary on topology identity**: unseen topology → fresh ART searches; known topology → reuse + re-relax. [CONFIRMED 3-0] arXiv:0805.2158

Cross-run note: the exact *initial* saddle convergence criterion is paper-dependent — 1.0 eV/Å in arXiv:0805.2158, 0.5 eV/Å in arXiv:1107.2417 (one run confirmed the 0.5 figure 2-0; an earlier run refuted a differently-worded 0.5 claim). The robust, decision-relevant fact is unaffected: **reused events are always re-converged to ~0.1 eV/Å.**

Unverified but primary (votes lost to limit):
- **SEAKMC** doesn't match stored environments at all — it flushes the per-defect catalogue each event and re-searches inside a spherical **active volume of 2.7–4.5 lattice parameters**; ~35× cheaper than k-ART on 50-vacancy Fe. [UNVERIFIED] arXiv:1409.1253
- k-ART imposes an **RMSD event threshold of 2.1 Å**; dropping it to 1.0 Å re-admits flickering motions that create super-basins — i.e. the threshold is tuned to *kinetics*, not lattice geometry. [UNVERIFIED] arXiv:1409.1253
- **EON KDB** uses loose geometric matches only as **seeds**; the suggested saddle is fully re-converged before entering the rate table, so loose matching adds **no** rate approximation (a failed match costs only compute). [UNVERIFIED] multiple (trochet19, eon/kdb docs)

Genuine gap (RQ-d): **no source** sets a projection/matching tolerance from a **rate-error budget**. pyKMC must build this itself if it wants a principled tolerance — the audit's assessment holds.

Judge's read: the 316/439 rejection is a symptom of forcing a rigid-lattice snap. The field's answer is to make identity topological and rate accuracy a *separate, always-recomputed* quantity. That is a larger redesign than raising a tolerance, but it is the load-bearing one.

## Pass 3 — Scalable bookkeeping & incremental repair (gap 4)

**Verdict: selection is a solved problem (adopt composition-rejection); the incremental-repair invalidation radius is the real, under-proven risk — and even Zacros only asserts it.**

Confirmed:
- **Composition-rejection (SSA-CR) is constant-time, independent of the number of reactions.** [CONFIRMED 3-0] Slepoy-Thompson-Plimpton, JCP 128 205101 (2008)
- **PSSA-CR is an exact SSA** combining partial-propensity + composition-rejection — CR handles arbitrary continuous rates **without quantization**. [CONFIRMED 3-0] PSSA-CR (PMID 20113014). ⇒ **the audit's "micro-group proliferation" worry is moot; rate-quantized micro-groups are unnecessary.**
- **The binding constraint is the propensity-update path, not selection:** SSA-CR wins only when *search* is expensive; when *update* dominates (the usual case) RSSA is preferred, and standard CR complexity bounds **omit the update cost**. [CONFIRMED 3-0] Springer 2018 (10.1007/s11538-018-0462-y)
- Production sparse local-update precedent: **KMCLib** re-matches only sites in the vicinity of the fired event → **O(1) in N**; **kmcos** never rescans at runtime and updates avail_sites only in the local neighborhood; **SPPARKS** exposes an explicit finite invalidation radius `h_energy` and recomputes only altered sites. [CONFIRMED 3-0 each] KMCLib; kmcos docs; SPPARKS (10.1088/1361-651X/accc4b)
- **Gibson-Bruck dependency graph** is the formal, geometry-free invalidation construct (edge iff Affects(vᵢ) ∩ DependsOn(aⱼ) ≠ ∅). [CONFIRMED 2-0] JPCA 104 1876 (2000)
- Distributed exact KMC (Zacros Time-Warp) is exact but carries **5.8–69.2× (mean ~14.7×) rollback re-simulation overhead**. [CONFIRMED 3-0] Phil. Trans. R. Soc. A 381 20220235 (2023) ⇒ deferring the dense porous/equiatomic regime to distributed KMC is expensive.

Refuted (do not rely):
- "KMCLib uses a dense per-site availability table like pyKMC." [REFUTED 0-3] — KMCLib is **sparse** match-lists.
- "BKL/CR selection is polynomial in N in the dense-active regime." [REFUTED 0-3] — CR selection **holds up**; the skeptics killed the pessimistic claim.

Unverified but primary (votes lost to limit — directly on the correctness question):
- The dependency-graph invalidation set is **proven sufficient (Theorem 1)**, not asserted — for chemistry, where dependencies are static. [UNVERIFIED] JPCA 104 1876
- Zacros uses a **fixed graph-distance (l-edge) invalidation neighborhood** analogous to pyKMC's dirty-ball. [UNVERIFIED] PMC11065322
- **Zacros ASSERTS the sufficiency of that neighborhood as "intuitive," without a formal proof.** [UNVERIFIED] PMC11065322 — i.e. **a mature production code has the same unproven-invalidation gap pyKMC is worried about.**

Judge's read: adopt CR selection and drop the dense n_procs×n_sites table — that retires most of the asserted blow-up and the micro-group worry outright. The novel risk is **not** selection or memory; it is proving the spatial invalidation radius for a *geometric pattern-matcher* (dependency graphs are proven only for static chemical dependencies). Since even Zacros doesn't prove it, the pragmatic path is: benchmark an optimized sparse full-rescan first, and only build the dirty-ball path with an **independent** oracle (not one that re-runs the same matcher).

## Pass 4 — Loop stop criteria & completeness (gap 5)

**Verdict: replace count-based new-classes→0 with a rate-weighted estimator — but keep an independent probe, because the rate-weighted metric is itself over-optimistic under a biased trajectory.**

Confirmed:
- Xu-Henkelman confidence **C = 1 − 1/Nr** (95% at Nr = 20 consecutive empty searches); Np need not be known a priori. [CONFIRMED 3-0] Xu & Henkelman, JCP 129 114104 (2008)
- Non-uniform extension **C = 1 − 1/(αNr)**; the Al/Al(100) data fit α = 0.25 for *count-based* completeness. [CONFIRMED 3-0] same
- **Empirically, rate-weighted completeness converges as the ideal α=1 while count-based lags at α=0.25** — rate-weighted is strictly faster/better. [CONFIRMED 3-0] same
- Aristoff-Chill-Simpson: **rate-weighted ("fraction of total rate found") is fundamentally superior**, and names the 2008 count-based criterion as the inferior "original"; they **prove the MSE of the rate-weighted estimators vanishes** as the run continues. [CONFIRMED 3-0] arXiv:1506.05092 / CAMCoS 11(2) 2016
- The Eyring-Kramers-based estimator **can overestimate completeness** if the assumed rate law deviates; a Monte-Carlo estimator is conservative instead. [CONFIRMED 3-0] arXiv:1506.05092
- Count-based (ART-family consecutive-empty) is **only qualitative — unquantifiable uncertainty** from frequency bias. [CONFIRMED 3-0] Trochet-Béland-Mousseau review (trochet19)
- k-ART itself has **no statistically principled termination** — searches ∝ log(topology frequency); EON uses an explicit confidence stop (default **0.99**). [CONFIRMED 3-0 / 3-0] PRE 84 046704; EON docs

Refuted (do not rely):
- "EON's confidence criterion is rate-weighted (20 kT window)." [REFUTED 0-3] — EON's confidence is the **count-based** Xu-Henkelman consecutive-search limit; the rate-weighted improvement is specifically **Chill-Henkelman (2014) / Aristoff-Chill-Simpson**.

Unverified but primary (votes lost to limit — the crucial caution):
- **MDSS-AKMC** uses a rate-weighted completeness estimator X(F) and stops at **X(F) < 0.01 (99% of total escape rate)**; the error E(F) = 1 − (1/K)Σkᵢ is the fraction of escape rate not yet found. [UNVERIFIED] JCP 140 214110 (2014)
- **That estimator is biased LOW (over-optimistic) when fast processes are found first — exact only at t→∞ or when all high-T rates are equal.** [UNVERIFIED] JCP 140 214110 — **this is pyKMC's self-referential-metric failure mode, named and sourced.**

Judge's read: adopt the rate-weighted "fraction of total rate found" estimator (Chill-Henkelman) as the leg-switch/convergence criterion — it provably dominates new-classes→0. But the same literature warns it is *over-optimistic on a rate-biased partial sample*, which is exactly pyKMC's biased-trajectory condition. So the independent probe (a short direct-pyKMC reference compared by a rate-spectrum test) is **not** optional — it is the guard against the rate-weighted metric's own known bias.

## Pass 5 — Collision-free event identity & porous morphology (gaps 7, 8)

**Verdict: canonical graph labeling is the true-canonical-form the anchored D4h-min lacks; k-ART's frame-independent anchor and the free automorphism/symmetry-number are the exact fixes for the red-team findings.**

Confirmed:
- A canonical form gives the **biconditional** G≅G' ⟺ C(G)=C(G') and is **label-invariant** (C(G^γ)=C(G) for every relabeling) — precisely the frame-independence a lexicographic anchor tie-break lacks. [CONFIRMED 3-0 ×3] arXiv:1301.1493; arXiv:0804.4881; ACM 10.1145/3356020
- All SOTA canonical labelers (nauty, Bliss, Traces) are individualization-refinement and **differ only in heuristics, not in the correctness guarantee**; automorphism-group computation is a **byproduct** of canonization — giving the **symmetry number** an anchored minimization does not expose. [CONFIRMED 2-0 / 3-0] ACM 10.1145/3356020; arXiv:0804.4881
- k-ART resolves multi-anchor ambiguity with a **frame-independent physical rule: anchor to the atom that moved most**, overriding the trial atom — not a lex tie-break. [CONFIRMED 3-0] arXiv:0805.2158 (**the direct fix for the red-team's frame-dependent anchor**)
- **Canonical labels alone are insufficient for symmetric events:** distinct events can share identical topologies, barrier, and displacement, so k-ART **adds the direction of atomic motion**; validated on symmetric Si/Fe. [CONFIRMED 3-0] arXiv:1107.2417
- The topology-key identity is valid only under an explicit precondition: the connectivity graph must map to a **unique relaxed structure** under the potential. [CONFIRMED 3-0] arXiv:0805.2158

Unverified but primary (votes lost to limit):
- **Zacros symmetry-number weighting** (RQ-b): the cluster-expansion Hamiltonian weights each figure by a **graph multiplicity GM_γ (= symmetry number)**: contribution = ECI_γ · GM_γ · N_CE_γ; and Zacros prevents k-fold over-counting **by design** — its detection returns a **single valid mapping per instance** rather than enumerating equivalents and correcting after. [UNVERIFIED] PMC11065322
- **Layer-dependent barriers** (RQ-c): FCC(100) surface-layer in-plane vacancy hop **0.42 eV (DFT) / 0.47 eV (EAM)** vs ~0.7 eV bulk; in dilute **Ni-Cr**, a vacancy migrating toward the (100) surface has **lower barriers for Cr-exchange than Ni-exchange**, and an in-plane hop is unfavorable specifically when it lands the vacancy over a subsurface Cr. [UNVERIFIED] OSTI 1784621 (Goswami lineage); arXiv:cond-mat/9704009 ⇒ **the correct catalogue symmetry is layer- and species-dependent, not a global O_h/D4h choice.**
- **Erlebacher dealloying KMC** governs both surface diffusion and dissolution by **local coordination number**, not a height function. [UNVERIFIED] J. Electrochem. Soc. 151 C614 (2004)

Judge's read: re-base identity on nauty-style canonical labeling — it *is* the guarantee the audit said was missing, and it hands you the symmetry number for free (fixing the multi-anchor over-count that G2 can't see). Two nuances the confirmed evidence adds: (1) even a true canonical form needs the **direction-of-motion** augment to separate symmetric event variants; (2) topology-as-identity **also** resolves the O_h-vs-D4h question, because the barrier difference is genuinely layer-dependent and a topological key inherits the local broken symmetry automatically.

---

## Cross-cutting decision (what the whole set says to do)

1. **The single highest-leverage move is to abandon the discrete exact-class catalogue for a continuous local barrier surrogate (KRA/CE or ML regression).** It is measured well inside the 0.15 eV split_tol *in the Ni-Fe-Cr family*, beats the low-order fallback the audit worried about, dissolves split_tol, and — via the KRA endpoint-split — gives detailed balance by construction. This one decision retires gaps 1, 3, and 6 together. Do it before building Phase C.

2. **Recognition and rate must be separated.** Every mature engine (k-ART, EON, SEAKMC) makes local-environment *identity* topological and *never* trusts a catalogued barrier verbatim — it re-converges the rate in the actual environment (~0.01 eV). pyKMC's snap_tol conflates the two; that conflation, not the tolerance value, is the Phase-B trap.

3. **Selection is solved; invalidation is not.** Adopt composition-rejection (exact, continuous-rate-friendly, retires the dense table and the micro-group worry). Then treat the dirty-ball radius as the genuine correctness risk — even Zacros only asserts it — and either prove it with an independent oracle or benchmark an optimized sparse full-rescan first.

4. **Convergence needs a rate-weighted metric *and* an independent probe.** Rate-weighted "fraction of total rate found" provably dominates new-classes→0, but is itself over-optimistic on a biased trajectory — so the direct-pyKMC spectrum probe is mandatory, not a nicety.

5. **Canonical labeling + coordination-based site classification** replace the anchored D4h identity and the z(x,y) height labeling respectively, and both handle the layer-dependent / porous regime automatically.

## What remains genuinely open (build-it-yourself, no prior art found)

- A projection/matching tolerance derived from a **rate-error budget** (gap 2, RQ-d).
- A **provably-sufficient geometric invalidation neighborhood for a spatial fingerprint/IRA matcher**, verified independently of re-running the matcher (gap 4, RQ-c) — dependency-graph proofs cover only static chemical dependencies.
- Positive evidence that **concerted/multi-atom saddle** barriers are predictable from atom-centered local descriptors (gap 1, RQ-e) — none surfaced; route these to on-the-fly search.
- The quantitative **sensitivity of equilibrium SRO/composition to aggregated-barrier imbalance** (gap 6) — needs pyKMC's own numerical check.

## Provenance

Five runs, ~2.0–2.4M subagent tokens each, Opus 3-vote verification. Session task outputs
(ephemeral): wl9icgs0d (barrier surrogate), wmin4dutd (projection), wsi522kgr (bookkeeping),
w7yfydczb (stop criteria), wcap01vr3 (identity/porous). Workflow run IDs wf_132cb1e8-2d0,
wf_dd420569-49b, wf_5434bff2-efc, wf_59e6f5a1-501, wf_211ee392-3c3.
