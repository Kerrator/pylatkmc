# NiFe re-search campaign — first measured NiFe classes (2026-08-15)

Executes decision **3.4** of `NICRFE_INGEST_READINESS_2026-08-14.md`: an in-situ pARTn re-search
leg over the merged 60-run NiFe corpus, mirroring the 2026-07-23 NiCr leg
(`pylatkmc/.scratch/phaseC/research_campaign/`). Campaign dir:
`pylatkmc/.scratch/phaseC/research_campaign_nife/`. All numbers below were adversarially
verified by four independent audits (graduation ledger, re-merge integrity, flux arithmetic,
physics sanity) — every count reproduced; caveats they surfaced are in §6.

## 1 Headline

| | before | after |
|---|---|---|
| measured (`harvested_pair`) NiFe classes | **0** (unstamped by design) | **180** |
| measured share of corpus flux | 0% | **46.6%** of total · **84.4%** of non-quarantined |
| pending-research flux share | 55.25% | **8.63%** |
| agreement (180 graduated) | — | mean \|ΔEa\| **13.4 meV**, median **11.5**, max **49.5** |

Signed mean ΔEa = −3.6 meV (re-searched barriers run marginally below harvested; no systematic
bias of concern). The NiCr precedent (66/81 at ≤23 meV) transferred: NiFe graduated 180/200 at
≤49.5 meV, 90% under 30 meV.

## 2 What ran

1. **Stamp** — `ingest.cli qc` over `merged_v3_NiFe.parquet` with an **empty** measured-refs set:
   all 16,690 representable classes → `pending_research` (quarantine reproduced identically:
   3,603 classes; stamp: measured=0, nonrepresentable=0).
2. **Flux ranking** (`nife_flux.py`) — reachability-corrected expected firings (Σ k·Δt over
   applicable steps, the gap-2 framing) parsed from all 60 runs' `pykmc.events` + `pykmc.out`,
   mapped to merged classes via `source_sim_paths` (`run#idx_ref`). Corpus total 120,291 expected
   firings; per-run totals ≈ 2,000 = n_steps (all within 5% — the Σk·Δt ≈ 1/step identity holds).
   Audit re-derived the per-ref flux from raw logs with an independent parser: matched to 1e-11.
3. **Candidate list** — top **200** pending classes by corpus flux = 88.1% of pending-class flux
   (48.65% of total). All 200 are the in-plane 1NN vacancy-hop action, drawn from 39 of 60 runs;
   Ea_rep mostly 0.58–0.68 eV.
4. **Search leg** (`rc_campaign.py`, top-200, 7 workers) — padded-cluster prep (frozen all-Ni pad
   shell, rcut 8.5 + EAM 5.6 Å), per-phase serial LAMMPS+pARTn driver (min → 3-rung refine ladder,
   TMPDIR isolated per job), acceptance = mover + dra + **re-projected class_id** identity.
   Multi-member classes searched the member whose barrier is closest to Ea_rep_eV.
   First pass: 179 in-band / 1 out-of-band / 12 refine_failed / 8 acceptance_failed.
5. **Alternate-member retry** (`rc_retry.py`) — for failed classes with ≥2 members, re-searched
   the next-closest member: 6 eligible, 1 recovered (in-band). 14 of the 19 remaining failures
   are singletons with no alternate geometry.
6. **Graduate** — `ingest.cli graduate`, ±0.05 eV band: **180 graduated**, **1 CONTEXT_SUSPECT**
   (+51.4 meV, just over band), 16,509 still pending.
7. **Re-merge** — full 60-run merge with `--measured-catalogue` = the graduated set:
   `merged_v3_NiFe_graduated.parquet` (stamp: measured=180, pending=16,510, quarantined 3,603
   unchanged, status_conflicts=0). Audit: vs the 2026-08-14 candidate this is a **pure two-column
   relabel** (`nu0_pair_policy`, `audit_reason`); all 47 other columns bit-identical, class set
   and order identical, quarantine reasons untouched, old file untouched on disk.

## 3 Campaign accounting (200 attempted)

| outcome | n | note |
|---|---|---|
| measured_in_band → graduated | 180 | max \|ΔEa\| 49.5 meV |
| measured_out_of_band → CONTEXT_SUSPECT | 1 | `a69b964d2946…` +51.4 meV (band 50); review |
| refine_failed | 12 | genuine search failures: saddle escapes to 5.8–6.5 Å delr_sad, or "EIGENVALUE LOST"; all 15 ladder attempts exhausted |
| acceptance_failed | 7 | 3× wrong mover, 4× re-projected class changed (not token flicker) |

Review list (`review_list.csv`, 19 rows) carries the 12+7; both attempts of every retried class
are preserved on disk (`campaign_log_primary_failures.csv`, `retry_log.csv`).

## 4 Flux restatement (post-graduation, corpus = 120,291 expected firings)

| policy | classes | flux | % total |
|---|---|---|---|
| harvested_pair (measured) | 180 | 56,073 | **46.6** |
| quarantined (unstamped) | 3,603 | 53,834 | **44.8** |
| pending_research | 16,510 | 10,384 | 8.6 |

**Tol-ruling leverage, now quantified for NiFe:** the reciprocity-quarantine band alone holds
44.8% of NiFe corpus flux. Whatever ruling 3.6 decides about `tol = 1e-6` moves nearly half the
corpus in one stroke — it is now the single largest lever on NiFe model fidelity, bigger than
this entire campaign.

## 5 Artifacts

Campaign dir (`pylatkmc/.scratch/phaseC/research_campaign_nife/`): harness (`rc_*.py`,
`nife_flux.py`), `targets_nife.csv`, `campaign_log.csv`, `research_results.csv`,
`review_list.csv`, `graduate_review.csv`, `flux_restatement_post_graduation.csv`,
`catalogue_v3_NiFe_graduated.parquet`, `merged_v3_NiFe_graduated.parquet`, per-job state under
`jobs/`. Staged beside the production candidates in
`/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/`:
`merged_v3_NiFe_graduated_2026-08-15.parquet`, `catalogue_v3_NiFe_graduated_2026-08-15.parquet`,
`merge_NiFe_graduated_2026-08-15.log`. **The 2026-08-14 `merged_v3_NiFe.parquet` is untouched;
promotion of the graduated candidate is your call.**

## 6 Caveats the audits surfaced (all by-design or documented, none blocking)

1. **Graduation verifies, it does not replace.** `harvested_pair` means the harvested per-member
   ν₀/Ea pairs fire; the re-search Ea appears nowhere in the rate data (max
   \|Ea_rep − Ea_research\| among graduated = 49.5 meV). Memo §3.4 semantics — but a consumer
   must not read "measured" as "Ea equals the re-searched value".
2. **Provenance thins in the merged candidate.** The re-merge regenerates `audit_reason`, so
   per-class graduation evidence and the CONTEXT_SUSPECT annotation live only in
   `catalogue_v3_NiFe_graduated*.parquet` + `graduate_review.csv`, not in the merged file (same
   behaviour as the NiCr production merge). The suspect class is indistinguishable from ordinary
   pending classes if you read only the merged parquet.
3. **Re-refinement, not independent search.** The driver starts pARTn from the stored saddle
   (as in the NiCr leg), so ΔEa measures padded-cluster/projection/re-relaxation consistency —
   the campaign's stated purpose — not an independent rediscovery of the transition. No
   independent-search control arm exists in either leg.
4. **delr_sad gate is 2.0 Å vs pyKMC's 0.4** (deliberate, inherited from the July driver): 51% of
   accepted wins drift >0.4 Å, but drift correlates 0.95 with whole-cluster relaxation and −0.21
   with \|ΔEa\| — it tracks the padded cluster settling, not saddle misidentification.
5. **7 of 180 graduated via the saddle-token flicker hysteresis** (documented Q7 2026-07-22 path;
   0.9% of accepted flux; mean \|ΔEa\| 18.9 meV vs 13.3 for the rest).
6. **The measured set is energetically homogeneous**: 52% of accepted barriers in [0.63, 0.65] eV
   — the Ni-matrix workhorse hop. Fe-specific contexts and minor archetypes (C2/C3, HOP_2NN…)
   remain unmeasured; a stratified (per-action / Fe-in-context) leg is the natural next slice.
7. **Rate-policy vs curation status are separate axes**: 111/180 graduated classes still carry
   `audit_status='pending'` (unchanged from before — graduation touches `nu0_pair_policy` only).
8. Minor: 384 flux-bearing `run#idx` refs (0.22% of flux, 69 selections) map to no merged class —
   the build-time discard ledger population; 4 accepted jobs log `ladder_len=0` (resumption
   artifact — measurement itself verified sound); harness hole where a `refine_min_fallback`
   could have leaked into the research CSV is **fixed** (never fired: min Ea_meas 0.243 eV).

## 7 Open items for Stephen

1. **Promote** `merged_v3_NiFe_graduated_2026-08-15.parquet` as the NiFe production candidate
   (replaces the unstamped 2026-08-14 file; codegen was gated on this leg per decision 3.4).
2. **CONTEXT_SUSPECT** `a69b964d2946…` (+51.4 meV, 3 members) — review or widen-band call.
3. **19-class review list** (12 refine + 7 acceptance failures; 14 singletons).
4. **Tol ruling 3.6** — now worth 44.8% of NiFe corpus flux (§4).
5. Next legs: stratified archetype/Fe-context searches; B2 (WILDCARD crash) and B3 (Fe surrogate
   categories) remain separate prerequisites for the surrogate channel, not for these measured rates.
