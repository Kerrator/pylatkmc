"""Unit tests for `pylatkmc.family_prefactors`.

Validates CSV schema enforcement, sanity-range filtering, bare-Vineyard
mode (κ_RPA = NaN), saddle-convergence gating, and target-T filtering.
"""

from __future__ import annotations

import csv
import warnings
from pathlib import Path

import pytest

from pylatkmc.family_prefactors import (
    FamilyPrefactor,
    load_family_prefactors,
    summarise_prefactors,
)


_REQUIRED_COLS = (
    "motif", "T_K", "n_free", "Ea_eV",
    "omega0_eV", "omega0_THz", "nu0_Hz", "nu0_THz",
    "kappa_RPA", "kappa_HF", "alpha_h", "alpha_f", "alpha_f_kT",
    "k0_assumed_Hz", "rate_correction_factor",
    "saddle_converged", "fmax_at_saddle_eV_per_A",
    "neb_n_images", "free_radius_A", "delta_q0", "dx", "notes",
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_REQUIRED_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _REQUIRED_COLS})


def _row(motif: str, **overrides) -> dict:
    """Build a representative row with sensible defaults; override per test."""
    base = dict(
        motif=motif, T_K=500.0, n_free=20, Ea_eV=0.62,
        omega0_eV=0.025, omega0_THz=6.0,
        nu0_Hz=1.0e13, nu0_THz=10.0,
        kappa_RPA=0.85, kappa_HF=0.83,
        alpha_h=0.1, alpha_f=0.05, alpha_f_kT=0.002,
        k0_assumed_Hz=1.0e13, rate_correction_factor=0.85,
        saddle_converged=True, fmax_at_saddle_eV_per_A=0.015,
        neb_n_images=7, free_radius_A=6.0, delta_q0=0.05, dx=0.01, notes="",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_load_single_family(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [_row("surface_1NN_inplane")])
    out = load_family_prefactors(csv_path)
    assert "surface_1NN_inplane" in out
    p = out["surface_1NN_inplane"]
    assert p.nu0_Hz == 1.0e13
    assert p.kappa_RPA == 0.85
    assert abs(p.k0_eff_Hz - 1.0e13 * 0.85) < 1e6
    assert p.saddle_converged is True


def test_load_multiple_families(tmp_path):
    csv_path = tmp_path / "fp.csv"
    rows = [
        _row("surface_1NN_inplane", nu0_Hz=8.0e12, kappa_RPA=0.9),
        _row("subsurface_1NN_inplane", nu0_Hz=6.0e12, kappa_RPA=0.85),
        _row("surface_2NN_diagonal", nu0_Hz=5.0e12, kappa_RPA=0.95),
    ]
    _write_csv(csv_path, rows)
    out = load_family_prefactors(csv_path)
    assert len(out) == 3
    assert {p.family_id for p in out.values()} == {
        "surface_1NN_inplane", "subsurface_1NN_inplane", "surface_2NN_diagonal",
    }


def test_target_T_K_filter(tmp_path):
    csv_path = tmp_path / "fp.csv"
    rows = [
        _row("surface_1NN_inplane", T_K=300.0),
        _row("surface_1NN_inplane", T_K=500.0, nu0_Hz=2.0e13),
        _row("surface_1NN_inplane", T_K=900.0),
    ]
    _write_csv(csv_path, rows)
    out = load_family_prefactors(csv_path, target_T_K=500.0)
    # Only the T=500 row survives → 1 entry
    assert len(out) == 1
    assert out["surface_1NN_inplane"].nu0_Hz == 2.0e13


# ---------------------------------------------------------------------------
# Bare-Vineyard mode (κ unavailable)
# ---------------------------------------------------------------------------

def test_bare_vineyard_when_kappa_nan(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [
        _row("surface_1NN_inplane", kappa_RPA="NaN", nu0_Hz=2.14e13),
    ])
    out = load_family_prefactors(csv_path, allow_bare_vineyard=True)
    p = out["surface_1NN_inplane"]
    assert p.kappa_RPA is None
    assert p.k0_eff_Hz == 2.14e13   # bare ν₀
    assert "bare-Vineyard" in p.notes


def test_bare_vineyard_disabled_drops_nan(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [
        _row("surface_1NN_inplane", kappa_RPA="NaN"),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = load_family_prefactors(csv_path, allow_bare_vineyard=False)
    assert out == {}


# ---------------------------------------------------------------------------
# Sanity-range filtering
# ---------------------------------------------------------------------------

def test_drops_unphysical_nu0(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [
        _row("crazy_1", nu0_Hz=1.0e9),    # 0.001 THz, too low
        _row("crazy_2", nu0_Hz=1.0e15),   # 1000 THz, too high
        _row("ok", nu0_Hz=8.0e12),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = load_family_prefactors(csv_path)
    assert "ok" in out
    assert "crazy_1" not in out
    assert "crazy_2" not in out


def test_drops_unphysical_kappa(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [
        _row("crazy", kappa_RPA=1.5),   # κ > 1.0001 is unphysical
        _row("ok", kappa_RPA=0.7),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = load_family_prefactors(csv_path)
    assert "ok" in out
    assert "crazy" not in out


# ---------------------------------------------------------------------------
# Saddle-convergence gating
# ---------------------------------------------------------------------------

def test_unconverged_saddle_skipped(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [
        _row("bad_saddle", saddle_converged="False"),
        _row("good_saddle", saddle_converged="True"),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = load_family_prefactors(csv_path, require_saddle_converged=True)
    assert "good_saddle" in out
    assert "bad_saddle" not in out


def test_unconverged_saddle_kept_when_relaxed(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [_row("bad_saddle", saddle_converged="False")])
    out = load_family_prefactors(csv_path, require_saddle_converged=False)
    assert "bad_saddle" in out
    assert out["bad_saddle"].saddle_converged is False


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_missing_required_column_raises(tmp_path):
    csv_path = tmp_path / "fp.csv"
    csv_path.write_text("motif,T_K,nu0_Hz\n"
                         "surface_1NN_inplane,500.0,1e13\n")
    # Missing kappa_RPA + saddle_converged → should ValueError
    with pytest.raises(ValueError, match="missing required column"):
        load_family_prefactors(csv_path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_family_prefactors(tmp_path / "doesnt_exist.csv")


def test_empty_csv_returns_empty(tmp_path):
    csv_path = tmp_path / "fp.csv"
    _write_csv(csv_path, [])
    out = load_family_prefactors(csv_path)
    assert out == {}


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

def test_summarise_empty():
    s = summarise_prefactors({})
    assert "no per-family" in s


def test_summarise_with_data():
    p = FamilyPrefactor(
        family_id="surface_1NN_inplane",
        nu0_Hz=2.14e13, kappa_RPA=None, k0_eff_Hz=2.14e13,
        T_K=500.0, saddle_converged=True, notes="bare-Vineyard",
    )
    s = summarise_prefactors({"surface_1NN_inplane": p})
    assert "surface_1NN_inplane" in s
    assert "21.40 THz" in s
    assert "NaN" in s   # κ printed as NaN since None
    assert "bare-Vineyard" in s
