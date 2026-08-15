"""Acceptance layer (protocol decision 4) + memo-§8 residual collection.

Geometric sanity: mover identity + saddle displacement (dra) tolerance.
Definitive: re-projected class_id of the re-relaxed event == the pending class_id.
Also emits before/after-relaxation projection max_residual (memo §8).
"""
from __future__ import annotations

import numpy as np

import dataclasses

from pylatkmc.ingest import canonical
from pylatkmc.ingest.event_class import Coloring
from pylatkmc.ingest.event_projection import classify_saddle_site, project_event

import rc_common as C

DRA_TOL = 0.3          # A, implementation constant (memo: constants, not policy)


def _project(row_like):
    pe = project_event(
        row_like, coloring=Coloring.FULL, rcut=C.RCUT, d_max=C.D_MAX,
        r_ctx_min=C.R_CTX_MIN, nominal_a=C.NOMINAL_A,
    )
    return pe, canonical.class_id(pe), float(pe.proj_report.max_residual)


def _token_only_diff(pe_a, pe_b) -> bool:
    """True iff the two projections differ ONLY in saddle-token kind."""
    if (pe_a.anchor0 != pe_b.anchor0 or pe_a.delta != pe_b.delta
            or pe_a.context != pe_b.context or pe_a.movers != pe_b.movers
            or pe_a.depth_sig != pe_b.depth_sig
            or len(pe_a.saddle_tokens) != len(pe_b.saddle_tokens)):
        return False
    pairs = list(zip(pe_a.saddle_tokens, pe_b.saddle_tokens))
    return (all(a.coord_sig == b.coord_sig and a.start_rank == b.start_rank
                for a, b in pairs)
            and any(a.kind != b.kind for a, b in pairs))


def assess(row, n_real: int, states, target_class_id: str) -> dict:
    """row = stored reference-table row; states = driver states.npz (padded coords)."""
    P0 = np.asarray(row["initial_positions"], float)
    Psad = np.asarray(row["saddle_positions"], float)
    mover = int(row["move_atom_idx"])
    R1 = np.asarray(states["R1"], float)[:n_real]
    Rsad = np.asarray(states["Rsad"], float)[:n_real]
    R2 = np.asarray(states["R2"], float)[:n_real]

    out: dict = {}
    # --- geometric sanity ---
    disp_if = np.linalg.norm(R2 - R1, axis=1)
    out["mover_meas"] = int(disp_if.argmax())
    out["mover_ok"] = out["mover_meas"] == mover
    dra_stored = float(np.linalg.norm(Psad[mover] - P0[mover]))
    dra_meas = float(np.linalg.norm(Rsad[mover] - R1[mover]))
    out["dra_stored"] = dra_stored
    out["dra_meas"] = dra_meas
    out["dra_ok"] = abs(dra_meas - dra_stored) <= DRA_TOL
    out["relax_shift_max"] = float(np.linalg.norm(R1 - P0, axis=1).max())

    # --- §8 residuals: stored cluster before vs after re-relaxation ---
    row_before = dict(row)
    pe_before, cid_before, res_before = _project(row_before)
    row_after = dict(row)
    row_after["initial_positions"] = R1
    row_after["saddle_positions"] = Rsad
    row_after["final_positions"] = R2
    pe_after, cid_after, res_after = _project(row_after)
    out["class_id_before"] = cid_before
    out["class_id_after"] = cid_after
    out["max_residual_before"] = res_before
    out["max_residual_after"] = res_after
    out["class_id_stored_matches"] = cid_before == target_class_id
    out["class_id_ok"] = cid_after == target_class_id

    # --- saddle-token hysteresis (interview Q7, 2026-07-22) ---
    # A kind flip alone, with the refined saddle inside the classifier's own
    # ambiguity band, is cross-representation flicker: apply the classifier's
    # designed prev_kind hysteresis. Clear-kind changes still fail.
    out["saddle_token_flicker"] = False
    if (not out["class_id_ok"] and cid_before == target_class_id
            and _token_only_diff(pe_after, pe_before)
            and len(pe_after.saddle_tokens) == 1):
        sub0 = np.delete(R1, mover, axis=0)
        stored_kind = pe_before.saddle_tokens[0].kind
        hyst_kind = classify_saddle_site(Rsad[mover], sub0, sub0, stored_kind)
        if hyst_kind == stored_kind:
            pe_h = dataclasses.replace(
                pe_after, saddle_tokens=pe_before.saddle_tokens)
            if canonical.class_id(pe_h) == target_class_id:
                out["class_id_ok"] = True
                out["saddle_token_flicker"] = True

    out["accepted"] = bool(out["mover_ok"] and out["dra_ok"] and out["class_id_ok"])
    return out
