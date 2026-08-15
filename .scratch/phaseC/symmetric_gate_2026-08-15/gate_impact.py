#!/usr/bin/env python
"""Measure the impact of canon decision D6 (symmetric mover-keyed G3 gate) on both
production catalogues.

Gate: an EVENT is discarded when max(res_P0, res_P2) >= THR (default 0.5 A), where
res_* are the mover-keyed max snap residuals in the P0 frame.  A CLASS is discarded
only when ALL of its surviving members discard; otherwise it shrinks.

Today's build gate is P0-only at 0.5 A, so the catalogue member lists already exclude
every res_P0 >= 0.5 event.  The incremental population is therefore exactly the
"P2-only" failures.

Outputs: gate_impact_by_class.parquet, gate_impact_summary.md, plus JSON headline.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

WORK = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15")
CAT = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full")
P2 = WORK / "p2_measure"
FLUX = {
    "NiCr": Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign_nicr"),
    "NiFe": Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign_nife"),
}
THRESHOLDS = [0.4, 0.5, 0.6]
THR_MAIN = 0.5

EV_COLS = [
    "run_tag", "idx_ref", "n_movers", "d_1nn_A",
    "gate_P0_fail", "gate_P2_fail", "gate_sym_fail", "half_shift",
    "mover_max_residual_P0", "mover_max_residual_P2", "mover_max_residual_sym",
    "hop_min_A", "hop_min_over_1nn", "frame_unfit",
]

CAT_COLS = [
    "class_id", "source_sim_paths", "source_idx_refs", "audit_status", "audit_reason",
    "nu0_pair_policy", "pair_status", "Ea_rep_eV", "Ea_std_eV", "n_eff",
    "saddle_token", "arrows", "delta", "action_id", "archetype", "one_way",
    "move_shape", "delta_atoms", "t_ref_K", "k_rate_mean_psinv", "backward_class",
]


def load_events(alloy: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(P2 / alloy / "*.parquet")))
    files = [f for f in files if not f.endswith("_summary.csv")]
    dfs = [pq.read_table(f, columns=EV_COLS).to_pandas() for f in files]
    ev = pd.concat(dfs, ignore_index=True)
    ev["member_key"] = ev["run_tag"] + "#" + ev["idx_ref"].astype(str)
    return ev


def load_catalogue(path: Path) -> pd.DataFrame:
    return pq.read_table(path, columns=CAT_COLS).to_pandas()


def explode_members(cat: pd.DataFrame) -> pd.DataFrame:
    m = cat[["class_id", "source_sim_paths"]].explode("source_sim_paths")
    m = m.rename(columns={"source_sim_paths": "member_key"})
    return m.reset_index(drop=True)


def _len_or_zero(x) -> int:
    if x is None:
        return 0
    try:
        return len(x)
    except TypeError:
        return 0


def analyse(alloy: str, cat_path: Path, policy_cat_path: Path | None = None) -> dict:
    out: dict = {"alloy": alloy}
    ev = load_events(alloy)
    cat = load_catalogue(cat_path)
    # policy/audit source (NiFe base merge is unstamped -> use graduated file)
    pol = cat
    if policy_cat_path is not None:
        pol = load_catalogue(policy_cat_path)
        assert set(pol.class_id) == set(cat.class_id)

    members = explode_members(cat)
    n_slots = len(members)

    ev_idx = ev.set_index("member_key")
    dup = ev_idx.index.duplicated().sum()
    assert dup == 0, f"{alloy}: duplicate member keys in measurement: {dup}"

    joined = members.join(ev_idx, on="member_key", how="left")
    n_unmatched = int(joined["mover_max_residual_P0"].isna().sum())

    # --- corpus-level event stats (ALL harvested rows, incl. P0-dropped) ---
    n_rows = len(ev)
    n_P0 = int(ev.gate_P0_fail.sum())
    n_P2 = int(ev.gate_P2_fail.sum())
    n_P2only = int((ev.gate_P2_fail & ~ev.gate_P0_fail).sum())
    n_both = int((ev.gate_P2_fail & ev.gate_P0_fail).sum())
    n_sym = int(ev.gate_sym_fail.sum())
    out["events"] = {
        "n_harvested_rows": n_rows,
        "n_P0_fail_dropped_today": n_P0,
        "n_P2_fail": n_P2,
        "n_P2_only_fail": n_P2only,
        "n_fail_both": n_both,
        "n_sym_fail": n_sym,
        "n_half_shift": int(ev.half_shift.sum()),
        "n_multi_mover": int((ev.n_movers > 1).sum()),
        "n_catalogue_members": n_slots,
        "n_members_unmatched_in_measurement": n_unmatched,
        # incremental = events that pass today's P0-only gate but fail symmetric
        "n_incremental_discard": n_P2only,
        "share_of_harvested_pct": 100.0 * n_P2only / n_rows,
        "share_of_surviving_members_pct": 100.0 * n_P2only / n_slots,
        "median_res_P0_A": float(ev.mover_max_residual_P0.median()),
        "median_res_P2_A": float(ev.mover_max_residual_P2.median()),
        "median_res_P2_surviving_A": float(
            ev.loc[~ev.gate_P0_fail, "mover_max_residual_P2"].median()
        ),
    }

    # --- per-class aggregation at each threshold ---
    j = joined.copy()
    j["res_sym"] = j["mover_max_residual_sym"]
    grp = j.groupby("class_id", sort=False)
    per_class = pd.DataFrame({"n_members": grp.size()})
    for thr in THRESHOLDS:
        f = (j["res_sym"] >= thr)
        j[f"fail_{thr}"] = f
        g2 = j.groupby("class_id", sort=False)[f"fail_{thr}"].sum()
        per_class[f"n_fail_{thr}"] = g2
    per_class["n_half_shift_members"] = grp["half_shift"].sum()
    per_class["n_multi_mover_members"] = grp["n_movers"].apply(lambda s: int((s > 1).sum()))
    per_class["max_res_sym_A"] = grp["res_sym"].max()
    per_class["min_res_sym_A"] = grp["res_sym"].min()
    per_class["max_res_P0_A"] = grp["mover_max_residual_P0"].max()
    per_class["max_res_P2_A"] = grp["mover_max_residual_P2"].max()
    per_class["min_hop_over_1nn"] = grp["hop_min_over_1nn"].min()
    per_class = per_class.reset_index()

    for thr in THRESHOLDS:
        n = per_class["n_members"]
        nf = per_class[f"n_fail_{thr}"]
        per_class[f"status_{thr}"] = np.where(
            nf == 0, "unchanged", np.where(nf == n, "flipped", "shrunk")
        )

    # --- attach catalogue metadata ---
    meta = cat[[c for c in CAT_COLS if c not in ("source_sim_paths",)]].copy()
    meta["n_tokens"] = meta["saddle_token"].map(_len_or_zero)
    meta["n_arrows"] = meta["arrows"].map(_len_or_zero)
    # The verdict's predicate: n_tokens vs the DELTA-derived mover count (delta rows
    # whose `before` is not EMPTY/Occ 0).  n_tokens == n_arrows always (verdict 2a),
    # so `len(saddle_token) != len(arrows)` is identically False and is NOT the key.
    meta["n_delta_movers"] = meta["delta"].map(
        lambda d: 0 if d is None else sum(1 for r in d if int(r["before"]) != 0)
    )
    meta["token_mismatch"] = meta["n_tokens"] != meta["n_delta_movers"]
    meta["token_mismatch_arrows_def"] = meta["n_tokens"] != meta["n_arrows"]
    meta = meta.drop(columns=["saddle_token", "arrows", "delta", "source_idx_refs"])
    if policy_cat_path is not None:
        meta = meta.drop(columns=["nu0_pair_policy", "audit_status", "audit_reason"])
        meta = meta.merge(
            pol[["class_id", "nu0_pair_policy", "audit_status", "audit_reason"]],
            on="class_id", how="left",
        )
    per_class = per_class.merge(meta, on="class_id", how="left")
    per_class["alloy"] = alloy
    per_class["nu0_pair_policy_f"] = per_class["nu0_pair_policy"].fillna("unstamped")

    # --- flux ---
    flux_dir = FLUX[alloy]
    cflux = flux_dir / f"class_flux_{alloy.lower()}.csv"
    rflux = flux_dir / f"flux_by_ref_{alloy.lower()}.csv"
    flux_present = cflux.exists()
    if flux_present:
        cf = pd.read_csv(cflux, usecols=lambda c: c in ("class_id", "flux_firings", "reachable"))
        per_class = per_class.merge(cf, on="class_id", how="left")
        per_class["flux_firings"] = per_class["flux_firings"].fillna(0.0)
    else:
        per_class["flux_firings"] = np.nan
    # member-level flux for shrink accounting
    member_flux = None
    if rflux.exists():
        rf = pd.read_csv(rflux)
        rf["member_key"] = rf["run_tag"] + "#" + rf["idx_ref"].astype(str)
        member_flux = rf.set_index("member_key")["flux_firings"]
        j["member_flux"] = j["member_key"].map(member_flux).fillna(0.0)
    out["flux_source"] = str(cflux) if flux_present else "MISSING"

    per_class = per_class.sort_values("class_id").reset_index(drop=True)

    # =========== 1. event-level ==========
    # =========== 2. class flip/shrink by policy & audit ==========
    thr = THR_MAIN
    st = per_class[f"status_{thr}"]
    out["classes"] = {
        "n_classes": int(len(per_class)),
        "n_flipped": int((st == "flipped").sum()),
        "n_shrunk": int((st == "shrunk").sum()),
        "n_unchanged": int((st == "unchanged").sum()),
        "n_affected": int((st != "unchanged").sum()),
        "pct_flipped": 100.0 * (st == "flipped").sum() / len(per_class),
        "pct_affected": 100.0 * (st != "unchanged").sum() / len(per_class),
        "n_members_removed": int(per_class[f"n_fail_{thr}"].sum()),
        "n_singleton_classes_flipped": int(
            ((st == "flipped") & (per_class.n_members == 1)).sum()
        ),
        "n_flipped_multimember": int(
            ((st == "flipped") & (per_class.n_members > 1)).sum()
        ),
    }
    xt_pol = pd.crosstab(per_class["nu0_pair_policy_f"], st)
    xt_aud = pd.crosstab(per_class["audit_status"].fillna("NA"), st)
    xt_both = pd.crosstab(
        [per_class["nu0_pair_policy_f"], per_class["audit_status"].fillna("NA")], st
    )
    out["xt_policy"] = xt_pol.to_dict()
    out["xt_audit"] = xt_aud.to_dict()
    out["xt_policy_audit"] = {
        f"{idx[0]}|{idx[1]}": {k: int(v) for k, v in row.items()}
        for idx, row in zip(xt_both.index, xt_both.to_dict("records"))
    }
    # members removed per policy / audit bucket
    out["members_removed_by_policy"] = (
        per_class.groupby("nu0_pair_policy_f")[f"n_fail_{thr}"].sum().astype(int).to_dict()
    )
    out["members_by_policy"] = (
        per_class.groupby("nu0_pair_policy_f")["n_members"].sum().astype(int).to_dict()
    )

    # =========== 3. headline: measured / graduated classes ==========
    meas = per_class[per_class["nu0_pair_policy_f"] == "harvested_pair"].copy()
    meas_aff = meas[meas[f"status_{thr}"] != "unchanged"]
    out["measured"] = {
        "n_measured_classes": int(len(meas)),
        "n_flipped": int((meas[f"status_{thr}"] == "flipped").sum()),
        "n_shrunk": int((meas[f"status_{thr}"] == "shrunk").sum()),
        "n_unchanged": int((meas[f"status_{thr}"] == "unchanged").sum()),
        "max_res_sym_over_measured_A": float(meas["max_res_sym_A"].max()) if len(meas) else None,
        "max_res_P2_over_measured_A": float(meas["max_res_P2_A"].max()) if len(meas) else None,
        "margin_to_gate_A": float(THR_MAIN - meas["max_res_sym_A"].max()) if len(meas) else None,
        "n_measured_members": int(meas["n_members"].sum()),
        "affected_detail": meas_aff[
            ["class_id", "n_members", f"n_fail_{thr}", "max_res_P0_A", "max_res_P2_A",
             "max_res_sym_A", "Ea_rep_eV", "audit_status"]
        ].to_dict("records"),
    }
    # per-threshold measured impact
    out["measured"]["by_threshold"] = {
        str(t): {
            "n_flipped": int((meas[f"status_{t}"] == "flipped").sum()),
            "n_shrunk": int((meas[f"status_{t}"] == "shrunk").sum()),
        }
        for t in THRESHOLDS
    }

    # =========== 4. token-mismatch overlap ==========
    tm = per_class["token_mismatch"]
    out["token_mismatch"] = {
        "n_recovered_classes_arrows_def_task_wording": int(
            per_class["token_mismatch_arrows_def"].sum()
        ),
        "n_recovered_classes": int(tm.sum()),
        "pct_of_catalogue": 100.0 * tm.sum() / len(per_class),
        "n_recovered_flipped": int(((st == "flipped") & tm).sum()),
        "n_recovered_shrunk": int(((st == "shrunk") & tm).sum()),
        "n_recovered_affected": int(((st != "unchanged") & tm).sum()),
        "pct_of_flipped_that_are_recovered": (
            100.0 * ((st == "flipped") & tm).sum() / max(1, (st == "flipped").sum())
        ),
        "pct_of_affected_that_are_recovered": (
            100.0 * ((st != "unchanged") & tm).sum() / max(1, (st != "unchanged").sum())
        ),
        "recovered_flip_rate_pct": 100.0 * ((st == "flipped") & tm).sum() / max(1, tm.sum()),
        "matched_flip_rate_pct": 100.0 * ((st == "flipped") & ~tm).sum() / max(1, (~tm).sum()),
        "n_recovered_members": int(per_class.loc[tm, "n_members"].sum()),
        "n_recovered_members_removed": int(per_class.loc[tm, f"n_fail_{thr}"].sum()),
        "xt_recovered_by_policy": pd.crosstab(
            per_class.loc[tm, "nu0_pair_policy_f"], st[tm]
        ).to_dict(),
    }

    # --- 4b. verdict 10.3.1 replication: top-100 recovered classes by flux ---
    # The verdict's population is the TRANSLATOR-VISIBLE recovered set, i.e. recovered
    # classes minus the quarantined ones that the translator skips earlier (verdict §1:
    # NiFe 2,253 - 77 quarantined = 2,176).  Ranking the full 2,253 shifts the numbers
    # (top-10 44.9 %, 51 half-shift, 78.3 %); the 2,176 set reproduces §10.3.1 exactly.
    if flux_present:
        rec_all = per_class[tm].copy()
        rec = rec_all[rec_all["audit_status"] != "quarantined"].copy()
        rec_flux_tot = float(rec["flux_firings"].sum())
        rec = rec.sort_values("flux_firings", ascending=False)
        top100 = rec.head(100).copy()
        # half-shift at class level = ANY member has shortest mover hop < 0.7 x 1NN
        top100["is_half_shift"] = top100["min_hop_over_1nn"] < 0.7
        n_hs100 = int(top100["is_half_shift"].sum())
        hs100 = top100[top100["is_half_shift"]]
        _ra = rec_all.sort_values("flux_firings", ascending=False)
        _ratot = float(_ra["flux_firings"].sum())
        _rt = _ra.head(100)
        _rhs = _rt["min_hop_over_1nn"] < 0.7
        out["recovered_top100_all_incl_quarantined"] = {
            "n_recovered": int(len(_ra)),
            "top10_share_pct": 100.0 * _ra.head(10)["flux_firings"].sum() / max(1e-300, _ratot),
            "top100_share_pct": 100.0 * _rt["flux_firings"].sum() / max(1e-300, _ratot),
            "n_half_shift_in_top100": int(_rhs.sum()),
            "half_shift_flux_share_pct": (
                100.0 * _rt.loc[_rhs, "flux_firings"].sum() / max(1e-300, _ratot)
            ),
            "n_half_shift_removed": int((_rt.loc[_rhs, f"status_{thr}"] != "unchanged").sum()),
        }
        out["recovered_top100"] = {
            "population": "translator-visible recovered (token_mismatch & audit_status != quarantined)",
            "n_recovered_visible": int(len(rec)),
            "n_recovered_total": int(len(rec_all)),
            "n_recovered_quarantined": int(len(rec_all) - len(rec)),
            "recovered_total_flux": rec_flux_tot,
            "pct_of_catalogue_flux_recovered": (
                100.0 * rec_flux_tot / max(1e-300, per_class["flux_firings"].sum())
            ),
            "top10_share_of_recovered_flux_pct": (
                100.0 * rec.head(10)["flux_firings"].sum() / max(1e-300, rec_flux_tot)
            ),
            "top100_share_of_recovered_flux_pct": (
                100.0 * top100["flux_firings"].sum() / max(1e-300, rec_flux_tot)
            ),
            "n_half_shift_in_top100": n_hs100,
            "half_shift_share_of_recovered_flux_pct": (
                100.0 * hs100["flux_firings"].sum() / max(1e-300, rec_flux_tot)
            ),
            "n_half_shift_top100_flipped": int((hs100[f"status_{thr}"] == "flipped").sum()),
            "n_half_shift_top100_shrunk": int((hs100[f"status_{thr}"] == "shrunk").sum()),
            "n_half_shift_top100_unchanged": int(
                (hs100[f"status_{thr}"] == "unchanged").sum()
            ),
            "pct_half_shift_top100_removed": (
                100.0 * (hs100[f"status_{thr}"] != "unchanged").sum() / max(1, n_hs100)
            ),
            "half_shift_top100_flux_removed_pct_of_recovered": (
                100.0
                * hs100.loc[hs100[f"status_{thr}"] != "unchanged", "flux_firings"].sum()
                / max(1e-300, rec_flux_tot)
            ),
            "n_top100_any_flipped": int((top100[f"status_{thr}"] == "flipped").sum()),
            "n_top100_any_affected": int((top100[f"status_{thr}"] != "unchanged").sum()),
            "recovered_flux_removed_pct": (
                100.0
                * rec.loc[rec[f"status_{thr}"] == "flipped", "flux_firings"].sum()
                / max(1e-300, rec_flux_tot)
            ),
            "n_recovered_half_shift_classes_all": int((rec["min_hop_over_1nn"] < 0.7).sum()),
            "n_recovered_half_shift_removed_all": int(
                ((rec["min_hop_over_1nn"] < 0.7) & (rec[f"status_{thr}"] != "unchanged")).sum()
            ),
        }
        out["recovered_top100"]["hs_detail"] = hs100[
            ["class_id", "flux_firings", "n_members", f"n_fail_{thr}", f"status_{thr}",
             "max_res_P0_A", "max_res_P2_A", "max_res_sym_A", "min_hop_over_1nn",
             "Ea_rep_eV", "audit_status"]
        ].to_dict("records")

    # half-shift tail
    hs_cls = per_class["n_half_shift_members"] > 0
    hs_all = per_class["n_half_shift_members"] == per_class["n_members"]
    out["half_shift"] = {
        "n_classes_with_half_shift_member": int(hs_cls.sum()),
        "n_classes_all_half_shift": int(hs_all.sum()),
        "n_half_shift_recovered": int((hs_cls & tm).sum()),
        "n_half_shift_classes_flipped": int((hs_all & (st == "flipped")).sum()),
        "n_half_shift_classes_affected": int((hs_cls & (st != "unchanged")).sum()),
        "pct_half_shift_classes_caught": (
            100.0 * (hs_cls & (st != "unchanged")).sum() / max(1, hs_cls.sum())
        ),
        # event level
        "n_half_shift_events_total": int(ev.half_shift.sum()),
        "n_half_shift_events_surviving_P0": int((ev.half_shift & ~ev.gate_P0_fail).sum()),
        "n_half_shift_events_caught_by_sym": int(
            (ev.half_shift & ev.gate_P2_fail & ~ev.gate_P0_fail).sum()
        ),
        "pct_half_shift_events_caught": (
            100.0 * (ev.half_shift & ev.gate_P2_fail & ~ev.gate_P0_fail).sum()
            / max(1, int((ev.half_shift & ~ev.gate_P0_fail).sum()))
        ),
    }
    if flux_present:
        out["half_shift"]["flux_in_half_shift_classes"] = float(
            per_class.loc[hs_cls, "flux_firings"].sum()
        )
        out["half_shift"]["pct_catalogue_flux_half_shift"] = float(
            100.0 * per_class.loc[hs_cls, "flux_firings"].sum()
            / max(1e-300, per_class["flux_firings"].sum())
        )
        out["half_shift"]["pct_half_shift_flux_removed"] = float(
            100.0 * per_class.loc[hs_cls & (st != "unchanged"), "flux_firings"].sum()
            / max(1e-300, per_class.loc[hs_cls, "flux_firings"].sum())
        )

    # =========== 5. flux ==========
    if flux_present:
        tot_flux = per_class["flux_firings"].sum()
        fl_flip = per_class.loc[st == "flipped", "flux_firings"].sum()
        fl_shr = per_class.loc[st == "shrunk", "flux_firings"].sum()
        out["flux"] = {
            "total_flux_firings": float(tot_flux),
            "flux_flipped": float(fl_flip),
            "flux_shrunk_classes": float(fl_shr),
            "pct_flux_flipped": 100.0 * fl_flip / tot_flux if tot_flux else 0.0,
            "pct_flux_in_shrunk_classes": 100.0 * fl_shr / tot_flux if tot_flux else 0.0,
            "pct_flux_affected": 100.0 * (fl_flip + fl_shr) / tot_flux if tot_flux else 0.0,
        }
        if member_flux is not None:
            mf_tot = float(j["member_flux"].sum())
            mf_removed = float(j.loc[j[f"fail_{thr}"], "member_flux"].sum())
            out["flux"]["member_flux_total"] = mf_tot
            out["flux"]["member_flux_removed"] = mf_removed
            out["flux"]["pct_member_flux_removed"] = (
                100.0 * mf_removed / mf_tot if mf_tot else 0.0
            )
    else:
        out["flux"] = {"status": "PENDING"}

    # =========== 6. sensitivity ==========
    sens = {}
    for t in THRESHOLDS:
        s = per_class[f"status_{t}"]
        e = {
            "n_events_sym_fail": int((ev.mover_max_residual_sym >= t).sum()),
            "n_events_incremental": int(
                ((ev.mover_max_residual_sym >= t) & (ev.mover_max_residual_P0 < THR_MAIN)).sum()
            ),
            "n_members_removed": int(per_class[f"n_fail_{t}"].sum()),
            "n_flipped": int((s == "flipped").sum()),
            "n_shrunk": int((s == "shrunk").sum()),
            "n_affected": int((s != "unchanged").sum()),
            "pct_members_removed": 100.0 * per_class[f"n_fail_{t}"].sum() / n_slots,
        }
        if flux_present:
            e["pct_flux_flipped"] = float(
                100.0 * per_class.loc[s == "flipped", "flux_firings"].sum()
                / max(1e-300, per_class["flux_firings"].sum())
            )
        sens[str(t)] = e
    out["sensitivity"] = sens

    # residual distribution near the gate (valley test) — surviving members only
    surv = j["res_sym"].dropna().values
    bins = np.arange(0.0, 1.51, 0.05)
    hist, _ = np.histogram(surv, bins=bins)
    out["res_sym_hist_005A_bins"] = {
        "edges": [round(float(b), 3) for b in bins],
        "counts": [int(c) for c in hist],
        "n_above_1p5": int((surv >= 1.5).sum()),
    }
    # density in the 0.40-0.60 window relative to neighbours
    def frac(lo, hi):
        return float(((surv >= lo) & (surv < hi)).sum())
    out["valley"] = {
        "n_0.30_0.40": frac(0.30, 0.40),
        "n_0.40_0.45": frac(0.40, 0.45),
        "n_0.45_0.50": frac(0.45, 0.50),
        "n_0.50_0.55": frac(0.50, 0.55),
        "n_0.55_0.60": frac(0.55, 0.60),
        "n_0.60_0.70": frac(0.60, 0.70),
        "n_ge_0.70": float((surv >= 0.70).sum()),
        "n_ge_1.00": float((surv >= 1.00).sum()),
        # sharpness: density per 0.05 A just below vs just above the 0.5 A cut, and the
        # width of the minimum.  A true "valley" would show a near-zero bin at the cut.
        "density_0.45_0.50_per0.05": frac(0.45, 0.50),
        "density_0.50_0.55_per0.05": frac(0.50, 0.55),
        "ratio_above_over_below_at_0.5": frac(0.50, 0.55) / max(1.0, frac(0.45, 0.50)),
        "min_bin_edge_0.2_1.0": float(
            0.2 + 0.05 * int(np.argmin([frac(0.2 + 0.05 * i, 0.25 + 0.05 * i) for i in range(16)]))
        ),
        "min_bin_count_0.2_1.0": float(
            min(frac(0.2 + 0.05 * i, 0.25 + 0.05 * i) for i in range(16))
        ),
        "pct_members_within_0.05A_of_cut": 100.0 * frac(0.45, 0.55) / max(1, len(surv)),
        "n_members_within_0.05A_of_cut": frac(0.45, 0.55),
        # how many class verdicts are decided inside the 0.4-0.6 band
        "n_members_0.40_0.60": frac(0.40, 0.60),
    }

    return {"summary": out, "per_class": per_class, "events": ev, "joined": j,
            "member_flux": member_flux}


def main() -> None:
    res = {}
    res["NiCr"] = analyse("NiCr", CAT / "merged_v3_NiCr.parquet")
    res["NiFe"] = analyse(
        "NiFe",
        CAT / "merged_v3_NiFe.parquet",
        policy_cat_path=CAT / "merged_v3_NiFe_graduated_2026-08-15.parquet",
    )

    pc = pd.concat([res["NiCr"]["per_class"], res["NiFe"]["per_class"]], ignore_index=True)
    pc.to_parquet(WORK / "gate_impact_by_class.parquet", index=False)

    summ = {k: v["summary"] for k, v in res.items()}
    (WORK / "gate_impact_raw.json").write_text(json.dumps(summ, indent=2, default=str))
    print(json.dumps(summ, indent=2, default=str))


if __name__ == "__main__":
    main()
