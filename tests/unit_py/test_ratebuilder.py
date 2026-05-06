"""Tests for pylatkmc.ratebuilder.

Uses a tiny synthetic CSV with only a handful of events so tier-by-tier
behavior can be verified by hand. The real curated catalogue has 80k
events and 700k cells; that's exercised in an integration run, not
here.
"""
from __future__ import annotations

import math
import struct
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pylatkmc import build_rate_table, load
from pylatkmc.kmcfmt import RATETABLE_MAGIC, read_header
from pylatkmc.ratebuilder import (
    K_B_EV_PER_K,
    _apply_cross_class_fallback,
    _apply_tier2_fallback,
    _apply_tier6_family,
    _load_family_bucket_barriers,
    _motif_of,
    _motif_lookup_table,
    _prepare_dataframe,
)
from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SPEC = REPO_ROOT / "models" / "ni_fe_cr_v1" / "ni_fe_cr_v1.kmcspec.toml"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def mini_spec(tmp_path: Path) -> ModelSpec:
    """Tiny 4-axis spec: (site_class, direction, mover_species, n_vac_nn1).
    Cube = 3 * 5 * 3 * 3 = 135 entries."""
    return ModelSpec(
        name="mini",
        lattice="fcc",
        species=["Vacant", "Ni", "Fe", "Cr"],
        shells=[Shell(name="nn1", cutoff_mult=1.05)],
        key=Key(axes=[
            KeyAxis(name="mover_species", kind="enum", max=3, skip_vacant=True),
            KeyAxis(name="n_vac_nn1", kind="count", shell="nn1", match="vac", max=3),
        ]),
        rate_data=RateData(
            primary=tmp_path / "classified.csv",
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )


def _write_synthetic_csv(path: Path, rows: list[dict]) -> None:
    """Write a CSV with all the columns _prepare_dataframe expects."""
    columns = [
        "site_class_3d", "direction_family_3d", "mover_species_ml",
        "nn1_count_Ni", "nn1_count_Fe", "nn1_count_Cr",
        "nn2_count_Ni", "nn2_count_Fe", "nn2_count_Cr",
        "n_vac_nn1_initial", "energy_barrier", "assignment_status",
    ]
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


# ------------------------------------------------------------------
# Motif lookup table
# ------------------------------------------------------------------
def test_motif_of_known_combos() -> None:
    assert _motif_of(0, 0) == 0  # surface × <110> → MF_SURFACE_1NN
    assert _motif_of(0, 1) == 1  # surface × <100> → MF_SURFACE_2NN
    assert _motif_of(1, 2) == 4  # subsurface × <111> → MF_INTERLAYER


def test_motif_lookup_table_shape() -> None:
    tbl = _motif_lookup_table()
    assert len(tbl) == 3 * 5       # SC_COUNT * DF_COUNT
    assert all(0 <= v <= 7 for v in tbl)


# ------------------------------------------------------------------
# Dataframe preparation
# ------------------------------------------------------------------
def test_prepare_dataframe_filters_rejected(mini_spec: ModelSpec, tmp_path: Path) -> None:
    csv = tmp_path / "events.csv"
    _write_synthetic_csv(csv, [
        {"site_class_3d": "surface", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Ni", "nn1_count_Ni": 10, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 1, "energy_barrier": 0.5,
         "assignment_status": "accepted"},
        {"site_class_3d": "surface", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Ni", "nn1_count_Ni": 10, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 1, "energy_barrier": 0.5,
         "assignment_status": "excluded:fit_barrier=False"},
    ])
    df = pd.read_csv(csv)
    out = _prepare_dataframe(df, mini_spec)
    assert len(out) == 1, "excluded row should be filtered out"
    assert out["_sc"].iloc[0] == 0       # surface
    assert out["_dir"].iloc[0] == 0      # <110>_inplane
    assert out["_mover"].iloc[0] == 0    # Ni
    assert out["_n_vac_nn1"].iloc[0] == 1


def test_prepare_dataframe_clips_to_axis_max(mini_spec: ModelSpec, tmp_path: Path) -> None:
    csv = tmp_path / "events.csv"
    _write_synthetic_csv(csv, [
        # n_vac_nn1 = 9, axis max = 3, so clipped to 2
        {"site_class_3d": "bulk_like", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Fe", "nn1_count_Ni": 3, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 9, "energy_barrier": 1.0,
         "assignment_status": "accepted"},
    ])
    df = pd.read_csv(csv)
    out = _prepare_dataframe(df, mini_spec)
    assert out["_n_vac_nn1"].iloc[0] == mini_spec.key.axes[1].max - 1


# ------------------------------------------------------------------
# End-to-end build: tier 1 only
# ------------------------------------------------------------------
def _arrhenius(Ea_eV: float, T_K: float, k0_Hz: float) -> float:
    return k0_Hz * math.exp(-Ea_eV / (K_B_EV_PER_K * T_K))


def test_tier1_aggregation_on_mini_spec(mini_spec: ModelSpec, tmp_path: Path) -> None:
    csv = tmp_path / "events.csv"
    _write_synthetic_csv(csv, [
        # Two events in the same cell (surface, <110>, Ni, n_vac=1): mean Ea
        {"site_class_3d": "surface", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Ni", "nn1_count_Ni": 10, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 1, "energy_barrier": 0.50,
         "assignment_status": "accepted"},
        {"site_class_3d": "surface", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Ni", "nn1_count_Ni": 10, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 1, "energy_barrier": 0.60,
         "assignment_status": "accepted"},
        # A different cell
        {"site_class_3d": "bulk_like", "direction_family_3d": "<111>_interlayer",
         "mover_species_ml": "Fe", "nn1_count_Ni": 11, "nn1_count_Fe": 1,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 0, "energy_barrier": 1.20,
         "assignment_status": "accepted"},
    ])
    out_path = tmp_path / "mini.kmcrt"
    stats = build_rate_table(mini_spec, csv, out_path, verbose=False)

    assert stats.n_cells_tier1 == 2
    assert stats.n_rows_accepted == 3

    # Read back the binary and spot-check two entries.
    rate, Ea, count = _read_cube(out_path, mini_spec.n_cube_entries())
    # Cell (surface=0, <110>=0, Ni=0, n_vac=1): mean Ea = 0.55
    idx1 = mini_spec.linear_index((0, 0, 0, 1))
    expected = _arrhenius(0.55, mini_spec.rate_data.temperature_K,
                          mini_spec.rate_data.k0_Hz)
    assert rate[idx1] == pytest.approx(expected, rel=1e-5)
    assert Ea[idx1] == pytest.approx(0.55, rel=1e-5)
    assert count[idx1] == 2

    # Cell (bulk_like=2, <111>=2, Fe=1, n_vac=0): mean Ea = 1.20
    idx2 = mini_spec.linear_index((2, 2, 1, 0))
    expected2 = _arrhenius(1.20, mini_spec.rate_data.temperature_K,
                           mini_spec.rate_data.k0_Hz)
    assert rate[idx2] == pytest.approx(expected2, rel=1e-5)
    assert count[idx2] == 1


# ------------------------------------------------------------------
# Tier 2 fallback
# ------------------------------------------------------------------
def test_tier2_fills_missing_via_element_drop() -> None:
    """A cube with n_vac_nn2 axis: tier 2 should drop n_vac_nn2 and fill cells
    that have a donor at n_vac_nn2=0."""
    spec = ModelSpec(
        name="t2",
        lattice="fcc",
        species=["Vacant", "Ni"],
        shells=[Shell(name="nn1", cutoff_mult=1.05),
                Shell(name="nn2", cutoff_mult=1.50)],
        key=Key(axes=[
            KeyAxis(name="n_vac_nn2", kind="count", shell="nn2", match="vac", max=3),
        ]),
        rate_data=RateData(
            primary=Path("/tmp/x.csv"),
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )
    axis_maxes = [m for _, m in spec.all_axes()]
    cube_rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    cube_Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # Seed one donor at n_vac_nn2=0 for (site_class=0, dir=0).
    cube_rate[0, 0, 0] = 1.5
    cube_Ea[0, 0, 0] = 0.5

    n_filled = _apply_tier2_fallback(
        cube_rate, cube_Ea, spec, drop_order=["n_vac_nn2"]
    )
    # Axis n_vac_nn2 has max 3 → the other 2 values should now be filled.
    assert n_filled == 2
    assert cube_rate[0, 0, 1] == 1.5
    assert cube_rate[0, 0, 2] == 1.5


def test_cross_class_fallback_fills_surface_from_subsurface() -> None:
    """Surface slab is empty, subsurface slab has data → surface borrows."""
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell
    spec = ModelSpec(
        name="cc",
        lattice="fcc",
        species=["Vacant", "Ni"],
        shells=[Shell(name="nn1", cutoff_mult=1.05)],
        key=Key(axes=[
            KeyAxis(name="n_vac_nn1", kind="count", shell="nn1", match="vac", max=3),
        ]),
        rate_data=RateData(
            primary=Path("/tmp/x.csv"),
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )
    axis_maxes = [m for _, m in spec.all_axes()]   # (3, 5, 3)
    rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # subsurface has data at (subsurface=1, dir=<110>=0, n_vac=1)
    rate[1, 0, 1] = 2.0
    Ea[1, 0, 1] = 0.8
    n = _apply_cross_class_fallback(rate, Ea, spec)
    # Surface (sc=0) and bulk_like (sc=2) should borrow at (dir=0, n_vac=1).
    assert rate[0, 0, 1] == 2.0
    assert rate[2, 0, 1] == 2.0
    # Cells the donor had as NaN stay NaN.
    assert np.isnan(rate[0, 0, 0])
    assert n == 2


# ------------------------------------------------------------------
# Tier 6 family-averaged barrier
# ------------------------------------------------------------------
def test_load_family_bucket_barriers_drops_empty_and_excluded(tmp_path: Path) -> None:
    csv = tmp_path / "family.csv"
    pd.DataFrame([
        {"family_id": "foo", "family_bucket_id": "nv1=0",
         "n_events": 100, "Ea_mean_eV": 0.5,
         "source_filter": "accepted; audit_excluded=False"},
        {"family_id": "foo", "family_bucket_id": "nv1=1",
         "n_events": 200, "Ea_mean_eV": 0.7,
         "source_filter": "accepted; audit_excluded=False"},
        # Empty placeholder — dropped
        {"family_id": "empty_family", "family_bucket_id": "nv1=0",
         "n_events": 0, "Ea_mean_eV": float("nan"),
         "source_filter": "accepted; audit_excluded=False"},
        # Excluded (fit_barrier=False) — dropped
        {"family_id": "excluded_family", "family_bucket_id": "*",
         "n_events": 50, "Ea_mean_eV": 1.5,
         "source_filter": "excluded:fit_barrier=False"},
    ]).to_csv(csv, index=False)
    out = _load_family_bucket_barriers(csv)
    assert set(out) == {"foo"}
    # As of May 2026, _load_family_bucket_barriers returns 2-axis (nv1, nv2)
    # tuples; for 1-axis bucket IDs like "nv1=0" the nv2 component is -1
    # ("any nv2" event-weighted fallback).
    assert set(out["foo"]) == {(0, -1), (1, -1)}
    assert out["foo"][(0, -1)] == pytest.approx(0.5)
    assert out["foo"][(1, -1)] == pytest.approx(0.7)


def test_load_family_bucket_barriers_handles_li_prefix(tmp_path: Path) -> None:
    """Buckets like 'li=1_nv1=3' should parse the nv1 part."""
    csv = tmp_path / "family.csv"
    pd.DataFrame([
        {"family_id": "foo", "family_bucket_id": "li=0_nv1=5",
         "n_events": 100, "Ea_mean_eV": 0.9,
         "source_filter": "accepted; audit_excluded=False"},
        {"family_id": "foo", "family_bucket_id": "li=1_nv1=5",
         "n_events": 100, "Ea_mean_eV": 1.1,
         "source_filter": "accepted; audit_excluded=False"},
    ]).to_csv(csv, index=False)
    out = _load_family_bucket_barriers(csv)
    # Both rows have nv1=5; event-weighted average = 1.0. 2-axis key:
    # nv2 = -1 (any-nv2 fallback for 1-axis-style bucket ID).
    assert out["foo"][(5, -1)] == pytest.approx(1.0)


def test_load_family_bucket_barriers_missing_file_returns_empty(tmp_path: Path) -> None:
    assert _load_family_bucket_barriers(tmp_path / "nope.csv") == {}


def test_tier6_respects_bucket_matching(mini_spec: ModelSpec) -> None:
    """Cube cell n_vac_nn1=V fills from family bucket nv1=V+1 (mover offset).
    Cells whose bucket is missing in the family table stay NaN."""
    axis_maxes = [m for _, m in mini_spec.all_axes()]   # (3, 5, 3, 3)
    rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # Family has buckets nv1=1, nv1=2 — cube n_vac_nn1 values 0 and 1 can fill.
    # But n_vac_nn1=2 would need bucket nv1=3 which is missing → stays NaN.
    # 2-axis key form (nv1, nv2); nv2=-1 = "any nv2" event-weighted fallback.
    family_buckets = {"surface_1NN_inplane": {(1, -1): 0.5, (2, -1): 0.6}}
    kT = K_B_EV_PER_K * mini_spec.rate_data.temperature_K
    k0 = mini_spec.rate_data.k0_Hz
    n, used = _apply_tier6_family(rate, Ea, mini_spec, family_buckets, kT, k0)
    assert used.get((0, 0)) == "surface_1NN_inplane"
    # n_vac_nn1 = 0: mover nv1 = 1, Ea = 0.5 → filled
    assert np.all(~np.isnan(rate[0, 0, :, 0])), "n_vac_nn1=0 slice should be filled"
    # n_vac_nn1 = 1: mover nv1 = 2, Ea = 0.6 → filled
    assert np.all(~np.isnan(rate[0, 0, :, 1]))
    # n_vac_nn1 = 2: mover nv1 = 3 absent → NaN
    assert np.all(np.isnan(rate[0, 0, :, 2]))


def test_tier6_skips_family_without_matching_buckets(mini_spec: ModelSpec) -> None:
    """If no cube n_vac_nn1 value maps to a present bucket, tier 6 does nothing."""
    axis_maxes = [m for _, m in mini_spec.all_axes()]
    rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # Cube n_vac_nn1 max = 3, so needs buckets at 1, 2, or 3. nv1=99 is unreachable.
    family_buckets = {"surface_1NN_inplane": {(99, -1): 0.5}}
    kT = K_B_EV_PER_K * mini_spec.rate_data.temperature_K
    n, used = _apply_tier6_family(
        rate, Ea, mini_spec, family_buckets, kT, mini_spec.rate_data.k0_Hz,
    )
    assert n == 0
    assert used == {}


def test_tier6_falls_back_to_second_family_if_primary_missing(
    mini_spec: ModelSpec,
) -> None:
    """Surface <111> has two candidates; primary missing → secondary used."""
    axis_maxes = [m for _, m in mini_spec.all_axes()]
    rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # Primary `surface_subsurface_exchange_up` absent; only secondary provided.
    family_buckets = {"surface_interlayer_hop": {(1, -1): 0.9}}
    kT = K_B_EV_PER_K * mini_spec.rate_data.temperature_K
    n, used = _apply_tier6_family(
        rate, Ea, mini_spec, family_buckets, kT, mini_spec.rate_data.k0_Hz,
    )
    assert used.get((0, 2)) == "surface_interlayer_hop"
    # n_vac_nn1=0 maps to mover nv1=1 → slice should be filled.
    assert np.all(~np.isnan(rate[0, 2, :, 0]))


def test_tier6_skips_unmapped_direction(mini_spec: ModelSpec) -> None:
    """The `unresolved` direction has no family mapping → nothing filled."""
    axis_maxes = [m for _, m in mini_spec.all_axes()]
    rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    family_buckets = {"surface_1NN_inplane": {(1, -1): 0.5, (2, -1): 0.6, (3, -1): 0.7}}
    kT = K_B_EV_PER_K * mini_spec.rate_data.temperature_K
    _apply_tier6_family(
        rate, Ea, mini_spec, family_buckets, kT, mini_spec.rate_data.k0_Hz,
    )
    # dir=<unresolved>=4 is not in _SC_DIR_TO_FAMILIES → stays NaN.
    assert np.all(np.isnan(rate[0, 4]))


def test_tier2_skips_unknown_axis_gracefully() -> None:
    spec = ModelSpec(
        name="t2b",
        lattice="fcc",
        species=["Vacant", "Ni"],
        shells=[Shell(name="nn1", cutoff_mult=1.05)],
        key=Key(axes=[
            KeyAxis(name="n_vac_nn1", kind="count", shell="nn1", match="vac", max=3),
        ]),
        rate_data=RateData(
            primary=Path("/tmp/x.csv"),
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )
    axis_maxes = [m for _, m in spec.all_axes()]
    cube_rate = np.full(axis_maxes, np.nan, dtype=np.float32)
    cube_Ea = np.full(axis_maxes, np.nan, dtype=np.float32)
    # drop_order references axes not in this spec → should be a no-op, not error.
    n = _apply_tier2_fallback(cube_rate, cube_Ea, spec,
                              drop_order=["n_Cr_nn2", "n_Fe_nn2"])
    assert n == 0


# ------------------------------------------------------------------
# Binary format roundtrip
# ------------------------------------------------------------------
def _read_cube(path: Path, n_expected: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with open(path, "rb") as fp:
        header = read_header(fp, RATETABLE_MAGIC)
        assert header["n_entries"] == n_expected
        (n,) = struct.unpack("<I", fp.read(4))
        assert n == n_expected
        rate = np.frombuffer(fp.read(4 * n), dtype="<f4")
        Ea = np.frombuffer(fp.read(4 * n), dtype="<f4")
        count = np.frombuffer(fp.read(4 * n), dtype="<u4")
    return np.array(rate), np.array(Ea), np.array(count)


def test_written_header_has_expected_fields(
    mini_spec: ModelSpec, tmp_path: Path,
) -> None:
    csv = tmp_path / "events.csv"
    _write_synthetic_csv(csv, [
        {"site_class_3d": "surface", "direction_family_3d": "<110>_inplane",
         "mover_species_ml": "Ni", "nn1_count_Ni": 10, "nn1_count_Fe": 0,
         "nn1_count_Cr": 0, "nn2_count_Ni": 6, "nn2_count_Fe": 0,
         "nn2_count_Cr": 0, "n_vac_nn1_initial": 1, "energy_barrier": 0.5,
         "assignment_status": "accepted"},
    ])
    out_path = tmp_path / "mini.kmcrt"
    build_rate_table(mini_spec, csv, out_path, verbose=False)

    with open(out_path, "rb") as fp:
        header = read_header(fp, RATETABLE_MAGIC)
    assert header["model_name"] == "mini"
    assert header["n_axes"] == len(mini_spec.all_axes())
    assert header["n_entries"] == mini_spec.n_cube_entries()
    assert header["strides"] == list(mini_spec.strides())
    assert header["axis_maxes"] == [m for _, m in mini_spec.all_axes()]
    assert header["axis_names"] == [n for n, _ in mini_spec.all_axes()]
    assert header["version"] == 3
    assert len(header["motif_of_class_dir"]) == 3 * 5
