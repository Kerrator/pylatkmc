"""Tests for the curated family registry + assignment pipeline."""
from __future__ import annotations

import pandas as pd
import pytest
from _paths import AUDIT_CSV, CLASSIFICATION_DIR

from pylatkmc.ingest.build_family_rate_table import build_family_table
from pylatkmc.ingest.families import (
    FAMILY_REGISTRY,
    FCCFamily,
    family_by_id,
    validate_registry,
)
from pylatkmc.ingest.family_assignment import (
    AUDIT_KEY_COLS,
    _assign_one,
    assign_events,
    build_report,
    load_audit,
)

# ── Fixtures ────────────────────────────────────────────────────────────────

def _row(**kwargs) -> pd.Series:
    """Base row with the bare-minimum columns the registry reads."""
    base = {
        "composition": "100Ni",
        "nvac": 1,
        "temp": 500.0,
        "idx_ref": 0,
        "move_type": "1NN_hop",
        "move_type_pre_zlayer": "1NN_hop",
        "motif_family_3d": "surface_1nn_translation",
        "direction_family_3d": "<110>_inplane",
        "site_class_3d": "surface",
        "surface_layer_initial": 0,
        "n_moved": 1,
        "n_vac_nn1_initial": 5,
        "energy_barrier": 0.70,
    }
    base.update(kwargs)
    return pd.Series(base)


@pytest.fixture
def mini_df() -> pd.DataFrame:
    """Small synthetic DataFrame hitting several families."""
    rows = [
        _row(idx_ref=1, motif_family_3d="surface_1nn_translation",
             direction_family_3d="<110>_inplane", site_class_3d="surface",
             n_vac_nn1_initial=5, energy_barrier=0.74),
        _row(idx_ref=2, motif_family_3d="surface_1nn_translation",
             direction_family_3d="<110>_inplane", site_class_3d="surface",
             n_vac_nn1_initial=6, energy_barrier=0.54),
        _row(idx_ref=3, motif_family_3d="interlayer_translation",
             direction_family_3d="<111>_interlayer", site_class_3d="surface",
             surface_layer_initial=0, n_vac_nn1_initial=6, energy_barrier=0.02),
        _row(idx_ref=4, motif_family_3d="surface_subsurface_exchange",
             move_type_pre_zlayer="exchange_up",
             direction_family_3d="<111>_interlayer", site_class_3d="subsurface",
             n_vac_nn1_initial=1, energy_barrier=1.02),
        _row(idx_ref=5, motif_family_3d="subsurface_exchange",
             direction_family_3d="<111>_interlayer", site_class_3d="bulk_like",
             n_vac_nn1_initial=1, energy_barrier=1.05),
        _row(idx_ref=6, motif_family_3d="concerted_3d",
             direction_family_3d="unresolved", site_class_3d="surface",
             n_moved=3, energy_barrier=0.80),
        _row(idx_ref=7, motif_family_3d="unresolved_multisite",
             direction_family_3d="unresolved", site_class_3d="subsurface",
             n_moved=2, energy_barrier=0.95),
    ]
    return pd.DataFrame(rows)


# ── Registry validity ──────────────────────────────────────────────────────

def test_registry_has_unique_ids():
    ids = [f.family_id for f in FAMILY_REGISTRY]
    assert len(ids) == len(set(ids)), "duplicate family_id"


def test_registry_no_overlap_on_mini_df(mini_df):
    rep = validate_registry(mini_df)
    assert rep["n_rows"] == len(mini_df)


def test_registry_raises_on_synthetic_overlap(mini_df):
    """Fabricate two families that both match the same row to prove the
    validator fails loudly on overlap."""
    fake_a = FCCFamily(
        family_id="__fake_a", family_name="fake A",
        movement_template="", seed_rule=lambda r: True,
        environment_rule=lambda r: "x", priority=0, fit_barrier=False,
        review_notes="",
    )
    fake_b = FCCFamily(
        family_id="__fake_b", family_name="fake B",
        movement_template="", seed_rule=lambda r: True,
        environment_rule=lambda r: "x", priority=0, fit_barrier=False,
        review_notes="",
    )
    with pytest.raises(ValueError, match="overlap"):
        validate_registry(mini_df.head(3), [fake_a, fake_b])


def test_family_by_id_roundtrip():
    assert family_by_id("surface_1NN_inplane").family_id == "surface_1NN_inplane"
    assert family_by_id("does_not_exist") is None


# ── Assignment pipeline ────────────────────────────────────────────────────

def test_assign_one_matches_surface_1NN_inplane():
    row = _row()
    out = _assign_one(row, audit={}, registry=FAMILY_REGISTRY)
    assert out["family_id"] == "surface_1NN_inplane"
    assert out["assignment_status"] == "accepted"
    assert out["audit_excluded"] is False


def test_assign_one_audit_ignore_excludes():
    row = _row(idx_ref=42)
    audit = {("100Ni", 1, 500.0, 42): {"verdict": "ignore", "override_move_type": None, "notes": None}}
    out = _assign_one(row, audit, FAMILY_REGISTRY)
    assert out["family_id"] == ""
    assert out["assignment_status"] == "excluded"
    assert out["audit_excluded"] is True
    assert out["assignment_note"] == "audit:ignore"


def test_assign_one_audit_unset_excludes():
    """unset = audited but not decided; exclude defensively."""
    row = _row(idx_ref=7)
    audit = {("100Ni", 1, 500.0, 7): {"verdict": "unset", "override_move_type": None, "notes": None}}
    out = _assign_one(row, audit, FAMILY_REGISTRY)
    assert out["assignment_status"] == "excluded"


def test_assign_one_reclassify_override():
    """An audit reclassify injects override_move_type and re-seeds."""
    row = _row(idx_ref=99, move_type="1NN_hop",
               motif_family_3d="surface_1nn_translation",
               direction_family_3d="<110>_inplane", site_class_3d="surface")
    audit = {("100Ni", 1, 500.0, 99):
             {"verdict": "reclassify", "override_move_type": "2NN_hop", "notes": "correction"}}
    out = _assign_one(row, audit, FAMILY_REGISTRY)
    # motif_family_3d still 'surface_1nn_translation' in the row (we don't
    # re-derive that); the registry's seed predicates should still land this
    # on surface_1NN_inplane. The assignment_note records the override.
    assert out["assignment_status"] == "accepted"
    assert "audit:reclassify" in out["assignment_note"]


def test_assign_events_produces_all_seven_columns(mini_df):
    out = assign_events(mini_df, audit={})
    new_cols = {"family_id", "family_name", "family_bucket_id",
                "family_bucket_name", "assignment_status",
                "assignment_note", "audit_excluded"}
    assert new_cols.issubset(out.columns)
    # No unresolved rows in the fixture.
    assert (out["assignment_status"] != "unresolved").all()


def test_unresolved_signatures_reported(mini_df):
    unknown = _row(idx_ref=999, motif_family_3d="something_new",
                   direction_family_3d="<110>_inplane", site_class_3d="surface")
    df = pd.concat([mini_df, pd.DataFrame([unknown])], ignore_index=True)
    out = assign_events(df, audit={})
    report = build_report(out, audit={}, registry=FAMILY_REGISTRY)
    assert report["n_unresolved"] == 1
    assert len(report["unresolved_signatures"]) >= 1
    assert report["unresolved_signatures"][0]["motif_family_3d"] == "something_new"


# ── Rate-table aggregation ─────────────────────────────────────────────────

def test_rate_table_excludes_audit_excluded(mini_df):
    # Mark row 1 as ignore → it must not contribute to surface_1NN_inplane stats.
    audit = {("100Ni", 1, 500.0, 1):
             {"verdict": "ignore", "override_move_type": None, "notes": None}}
    out = assign_events(mini_df, audit)
    tbl = build_family_table(out)
    surface_row = tbl[(tbl["family_id"] == "surface_1NN_inplane")
                      & (tbl["n_events"] > 0)]
    # Only row idx_ref=2 (nv1=6) remains; row 1 was excluded.
    total = int(surface_row["n_events"].sum())
    assert total == 1


def test_rate_table_has_no_event_id_columns():
    """Regression: the curated family table must not key on event indices."""
    tbl_df = pd.read_csv(CLASSIFICATION_DIR / "rate_lookup_table_family.csv")
    forbidden = {"idx_ref", "ref_event", "row_idx", "event_idx"}
    assert forbidden.isdisjoint(tbl_df.columns), (
        f"event-ID column leaked into curated table: "
        f"{forbidden & set(tbl_df.columns)}"
    )
    # representative_row_indices is a JSON-string column, not an index key.
    if "representative_row_indices" in tbl_df.columns:
        val = tbl_df["representative_row_indices"].iloc[0]
        assert isinstance(val, str) and val.startswith("[")


def test_fit_barrier_false_families_not_fit(mini_df):
    out = assign_events(mini_df, audit={})
    tbl = build_family_table(out)
    for fid in ("concerted_multisite", "unresolved_multisite"):
        rows = tbl[tbl["family_id"] == fid]
        if len(rows) == 0:
            continue
        for _, row in rows.iterrows():
            assert row["source_filter"].startswith("excluded:"), (
                f"{fid} should not be fit; got source_filter={row['source_filter']}"
            )


def test_empty_dataframe_edge_case():
    empty = pd.DataFrame(columns=[
        "composition", "nvac", "temp", "idx_ref",
        "move_type", "motif_family_3d", "direction_family_3d",
        "site_class_3d", "n_moved", "n_vac_nn1_initial",
        "energy_barrier", "move_type_pre_zlayer", "surface_layer_initial",
    ])
    out = assign_events(empty, audit={})
    assert len(out) == 0


# ── Audit log loader ───────────────────────────────────────────────────────

def test_load_audit_missing_file(tmp_path):
    assert load_audit(tmp_path / "nonexistent.csv") == {}


def test_load_audit_real_file():
    """Sanity: the real audit_log.csv loads and produces dict keys matching
    the documented (composition, nvac, temp, idx_ref) tuple."""
    audit = load_audit(AUDIT_CSV)
    assert len(audit) > 0
    # Every key should be the 4-tuple, values should have "verdict"
    for key, val in list(audit.items())[:3]:
        assert len(key) == len(AUDIT_KEY_COLS)
        assert "verdict" in val
