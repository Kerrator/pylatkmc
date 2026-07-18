"""Rate-space columns in build_family_rate_table (Agent A2, contract 11.6).

A self-contained synthetic case (always runs) plus a real-data case gated on the
apps/PyKMC_Analysis curated CSV being resolvable (skips otherwise — never fails).
``tests/ingest`` is not collected by the default suite and needs the ``[ingest]``
extras (pandas).
"""

from __future__ import annotations

import math

import pandas as pd
from _paths import CLASSIFICATION_DIR

from pylatkmc.ingest.build_family_rate_table import DEFAULT_K0_HZ, build_family_table
from pylatkmc.rate_expression import KB_EV_PER_K

_RATE_COLS = ("k_rate_mean_psinv", "Ea_rep_eV", "nu0_geo_psinv", "T_ref_K")


def _synthetic_accepted() -> pd.DataFrame:
    """Four accepted surface_1NN_inplane events in one bucket (spread barriers)."""
    base = dict(
        assignment_status="accepted",
        family_id="surface_1NN_inplane",
        family_bucket_id="nv1=0_nv2=0",
    )
    barriers = [0.45, 0.55, 0.60, 0.72]
    return pd.DataFrame([{**base, "energy_barrier": b} for b in barriers])


def _assert_rate_space_properties(tbl: pd.DataFrame, t_ref_K: float) -> None:
    """The invariants the rate-space columns must satisfy on every populated row."""
    for col in _RATE_COLS:
        assert col in tbl.columns, f"missing rate-space column {col}"
    kt = KB_EV_PER_K * t_ref_K
    populated = tbl[tbl["n_events"] > 0]
    assert len(populated) > 0
    for _, row in populated.iterrows():
        k_mean = float(row["k_rate_mean_psinv"])
        ea_rep = float(row["Ea_rep_eV"])
        nu0_geo = float(row["nu0_geo_psinv"])
        assert row["T_ref_K"] == t_ref_K
        # ps^-1 scaling: a positive, finite rate in ps^-1 (Hz would be ~1e13).
        assert math.isfinite(k_mean) and k_mean > 0.0
        assert k_mean < 1.0e6  # ps^-1, not Hz
        # reproduce k_rate_mean exactly at T_ref
        repro = nu0_geo * math.exp(-ea_rep / kt)
        assert math.isclose(repro, k_mean, rel_tol=1e-9)
        # rate-space >= mean-then-exp (Jensen), and Ea_rep >= Ea_min (uniform nu0)
        mean_then_exp = nu0_geo * math.exp(-float(row["Ea_mean_eV"]) / kt)
        assert k_mean >= mean_then_exp * (1.0 - 1e-9)
        assert ea_rep >= float(row["Ea_min_eV"]) - 1e-9
        assert ea_rep <= float(row["Ea_mean_eV"]) + 1e-9


def test_rate_space_columns_synthetic() -> None:
    """build_family_table stamps consistent ps^-1 rate-space columns (self-contained)."""
    t_ref = 500.0
    bucket_nu0 = {("surface_1NN_inplane", "nv1=0_nv2=0"): 1.58e13}
    tbl = build_family_table(
        _synthetic_accepted(), t_ref_K=t_ref, bucket_nu0=bucket_nu0, family_nu0={}
    )
    _assert_rate_space_properties(tbl, t_ref)
    hit = tbl[
        (tbl["family_id"] == "surface_1NN_inplane")
        & (tbl["family_bucket_id"] == "nv1=0_nv2=0")
    ]
    assert not hit.empty
    # per-bucket nu0 was used: nu0_geo_psinv == 1.58e13 / 1e12
    assert math.isclose(float(hit.iloc[0]["nu0_geo_psinv"]), 1.58e13 / 1.0e12, rel_tol=1e-9)


def test_rate_space_k0_fallback_when_no_nu0() -> None:
    """With no nu0 maps, the rate-space nu0 falls back to the on-lattice k0 (1 ps^-1)."""
    t_ref = 500.0
    tbl = build_family_table(_synthetic_accepted(), t_ref_K=t_ref)
    _assert_rate_space_properties(tbl, t_ref)
    hit = tbl[tbl["family_id"] == "surface_1NN_inplane"]
    hit = hit[hit["n_events"] > 0]
    assert math.isclose(
        float(hit.iloc[0]["nu0_geo_psinv"]), DEFAULT_K0_HZ / 1.0e12, rel_tol=1e-9
    )


def test_rate_space_columns_real_classified_csv() -> None:
    """Run build_family_table on the real classified CSV when present; skip otherwise."""
    import pytest

    csv = CLASSIFICATION_DIR / "classified_events_with_families.csv"
    if not csv.is_file():
        pytest.skip(
            "apps/PyKMC_Analysis classified_events_with_families.csv not found; "
            "set PYKMC_KMC_ROOT to run the real-data rate-space check."
        )
    t_ref = 500.0
    df = pd.read_csv(csv)
    if "assignment_status" not in df.columns:
        pytest.skip("classified CSV lacks assignment_status; not an assigned frame")
    tbl = build_family_table(df, t_ref_K=t_ref)
    _assert_rate_space_properties(tbl, t_ref)
