"""One-pass curated-catalogue orchestrator (assign + rate-table build + ν₀ join)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pylatkmc.ingest.build_curated_catalogue import build_curated_catalogue, main


def _mini_events() -> pd.DataFrame:
    """A minimal classifier-output frame the assigner can seed into families.

    Two surface 1NN in-plane hops (the highest-priority family) + the columns the
    seed rules read. Kept tiny; we only assert the orchestrator wiring, not the
    classifier physics (covered by test_families.py).
    """
    base = dict(
        composition="100Ni", nvac=1, temp=500.0, sim_label="s", sim_path="/x",
        move_type="1NN_hop", move_type_pre_zlayer="1NN_hop",
        motif_family_3d="surface_1nn_translation", direction_family_3d="<110>_inplane",
        site_class_3d="surface", surface_layer_initial=0, n_moved=1,
        n_vac_nn1_initial=0, n_vac_nn2_initial=0, energy_barrier=0.6, k=1.0,
    )
    return pd.DataFrame([{**base, "idx_ref": 0}, {**base, "idx_ref": 1}])


def test_orchestrator_runs_and_writes_both_outputs(tmp_path):
    ev = tmp_path / "classified_events.csv"
    _mini_events().to_csv(ev, index=False)
    audit = tmp_path / "no_audit.csv"  # missing file -> load_audit returns {} (all rows seed)

    bucket = tmp_path / "fp_bucket.csv"
    pd.DataFrame({
        "family_id": ["surface_1NN_inplane"], "family_bucket_id": ["nv1=0_nv2=0"],
        "T_K": [500.0], "nu0_Hz": [1.58e13],
    }).to_csv(bucket, index=False)
    family = tmp_path / "fp.csv"
    pd.DataFrame({"motif": ["surface_1NN_inplane"], "nu0_Hz": [1.05e13]}).to_csv(family, index=False)

    out_events = tmp_path / "with_families.csv"
    out_rate = tmp_path / "rate.csv"
    report = tmp_path / "report.json"

    assigned, tbl = build_curated_catalogue(
        ev, audit, out_events, out_rate, bucket, family, report,
    )

    # both outputs written
    assert out_events.is_file() and out_rate.is_file() and report.is_file()
    # assignment added the family columns
    assert {"family_id", "family_bucket_id", "assignment_status"}.issubset(assigned.columns)
    # the two events seeded into surface_1NN_inplane and were accepted
    acc = assigned[assigned["assignment_status"] == "accepted"]
    assert (acc["family_id"] == "surface_1NN_inplane").all()
    # rate table carries nu0_Hz + nu0_source; the populated bucket used per-bucket ν₀
    assert "nu0_Hz" in tbl.columns and "nu0_source" in tbl.columns
    hit = tbl[(tbl.family_id == "surface_1NN_inplane") & (tbl.family_bucket_id == "nv1=0_nv2=0")]
    assert not hit.empty
    assert hit["nu0_source"].iloc[0] == "trajectory_bucket"
    assert hit["nu0_Hz"].iloc[0] == 1.58e13
    # report is valid JSON
    json.loads(report.read_text())


def _cli_args(tmp_path):
    """Minimal on-disk inputs for the CLI; returns the shared argv prefix."""
    ev = tmp_path / "classified_events.csv"
    _mini_events().to_csv(ev, index=False)
    bucket = tmp_path / "fp_bucket.csv"
    pd.DataFrame(columns=["family_id", "family_bucket_id", "T_K", "nu0_Hz"]).to_csv(
        bucket, index=False)
    family = tmp_path / "fp.csv"
    pd.DataFrame(columns=["motif", "nu0_Hz"]).to_csv(family, index=False)
    return [
        "--events", str(ev),
        "--out-events", str(tmp_path / "with_families.csv"),
        "--out-rate", str(tmp_path / "rate.csv"),
        "--report", str(tmp_path / "report.json"),
        "--prefactors-bucket", str(bucket),
        "--prefactors", str(family),
    ]


def test_cli_requires_an_audit_choice(tmp_path):
    """No silent default audit log: --audit PATH or --no-audit is mandatory."""
    with pytest.raises(SystemExit) as exc:
        main(_cli_args(tmp_path))
    assert exc.value.code == 2


def test_cli_rejects_missing_audit_file(tmp_path):
    """A named audit file that doesn't exist is an error, not 'no verdicts'."""
    with pytest.raises(SystemExit) as exc:
        main([*_cli_args(tmp_path), "--audit", str(tmp_path / "missing.csv")])
    assert exc.value.code == 2


def test_cli_no_audit_builds_both_outputs(tmp_path):
    assert main([*_cli_args(tmp_path), "--no-audit"]) == 0
    assigned = pd.read_csv(tmp_path / "with_families.csv")
    assert (assigned["assignment_status"] == "accepted").all()
    assert (tmp_path / "rate.csv").is_file()
