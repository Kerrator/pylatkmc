"""Per-bucket → per-family → k0 ν₀ join in build_family_rate_table."""

from __future__ import annotations

import pandas as pd

from pylatkmc.ingest.build_family_rate_table import (
    attach_nu0,
    load_bucket_nu0,
    load_family_nu0,
)


def _tbl():
    return pd.DataFrame({
        "family_id": ["surface_1NN_inplane", "surface_1NN_inplane", "bulk_1NN_inplane"],
        "family_bucket_id": ["nv1=0_nv2=1", "nv1=4_nv2=0", "nv1=0"],
        "n_events": [10, 5, 0],
    })


def test_attach_nu0_precedence():
    bucket = {("surface_1NN_inplane", "nv1=0_nv2=1"): 1.58e13}  # per-bucket
    family = {"surface_1NN_inplane": 1.05e13}  # family fallback
    out = attach_nu0(_tbl(), bucket, family)
    # row 0: per-bucket value + provenance
    assert out.loc[0, "nu0_Hz"] == 1.58e13
    assert out.loc[0, "nu0_source"] == "trajectory_bucket"
    # row 1: no bucket entry -> family fallback
    assert out.loc[1, "nu0_Hz"] == 1.05e13
    assert out.loc[1, "nu0_source"] == "family"
    # row 2: neither -> NaN/k0
    assert pd.isna(out.loc[2, "nu0_Hz"])
    assert out.loc[2, "nu0_source"] == "k0"


def test_load_bucket_nu0(tmp_path):
    p = tmp_path / "fp_bucket.csv"
    pd.DataFrame({
        "family_id": ["surface_1NN_inplane", "subsurface_1NN_inplane"],
        "family_bucket_id": ["nv1=0_nv2=1", "nv1=0_nv2=1"],
        "T_K": [500.0, 500.0],
        "nu0_Hz": [1.58e13, float("nan")],  # NaN row dropped
    }).to_csv(p, index=False)
    m = load_bucket_nu0(p)
    assert m == {("surface_1NN_inplane", "nv1=0_nv2=1"): 1.58e13}


def test_load_bucket_nu0_missing_or_malformed(tmp_path):
    assert load_bucket_nu0(tmp_path / "nope.csv") == {}
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"motif": ["x"], "nu0_Hz": [1.0]}).to_csv(bad, index=False)  # wrong schema
    assert load_bucket_nu0(bad) == {}


def test_load_family_nu0_roundtrip(tmp_path):
    p = tmp_path / "fp.csv"
    pd.DataFrame({"motif": ["surface_1NN_inplane"], "nu0_Hz": [1.05e13]}).to_csv(p, index=False)
    assert load_family_nu0(p) == {"surface_1NN_inplane": 1.05e13}
