"""Tests for the shared Erlebacher dissolution-rate module.

Covers the anchored ε table, the rate formula, the overpotential term, and the
cross-package byte/numeric agreement between the two duplicated copies.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

from pylatkmc import dissolution_rate as dr
from pylatkmc.rate_expression import KB_EV_PER_K as KB_RATE_EXPR

# kmc/pylatkmc/tests/unit_py/ -> parents[2] == pylatkmc/ , parents[3] == kmc/
_REPO_ROOT = Path(__file__).resolve().parents[2]
_KMC_ROOT = Path(__file__).resolve().parents[3]
# Vendored copy inside the repo so the test stands alone in a standalone clone.
_EPS_TABLE = _REPO_ROOT / "models/ni_dissolution_demo/epsilon_table.toml"
_PYKMC_COPY = _KMC_ROOT / "pyKMC-develop/pykmc/dissolution_rate.py"


def _inline_params() -> dr.DissolutionParams:
    """Hermetic params (independent of any table retuning)."""
    return dr.DissolutionParams(
        epsilon={
            ("Ni", "Ni"): 0.20,
            ("Cr", "Ni"): 0.25,
            ("Cr", "Cr"): 0.30,
            ("Fe", "Ni"): 0.18,
        },
        nu_E_Hz=1.0e4,
        phi_eV=0.0,
        max_coordination=9,
        min_coordination=3,
    )


# --------------------------------------------------------------------------
# Constant + table provenance
# --------------------------------------------------------------------------


def test_kb_matches_rate_expression() -> None:
    """The duplicated kB must equal pylatkmc's single source of truth."""
    assert dr.KB_EV_PER_K == KB_RATE_EXPR


def test_canonical_table_anchor() -> None:
    """The shipped ε table is anchored to E_bare(9-coord Ni) ~ 1.8 eV."""
    p = dr.load_params(_EPS_TABLE)
    assert dr.e_bare(p, "Ni", {"Ni": 9}) == pytest.approx(1.8, abs=1e-9)
    assert p.nu_E_Hz == pytest.approx(1.0e4)
    assert p.max_coordination == 9
    assert p.min_coordination == 3


def test_canonical_table_rate() -> None:
    p = dr.load_params(_EPS_TABLE)
    k = dr.dissolution_rate(p, "Ni", {"Ni": 9}, T_K=500.0, phi_eV=0.0)
    assert k == pytest.approx(1.0e4 * math.exp(-1.8 / (dr.KB_EV_PER_K * 500.0)))


# --------------------------------------------------------------------------
# e_bare / eps
# --------------------------------------------------------------------------


def test_eps_symmetric() -> None:
    p = _inline_params()
    assert dr.eps(p, "Cr", "Ni") == dr.eps(p, "Ni", "Cr")


def test_eps_unknown_pair_raises() -> None:
    p = _inline_params()
    with pytest.raises(KeyError):
        dr.eps(p, "Ni", "Au")


def test_e_bare_composition_mix() -> None:
    p = _inline_params()
    # 6 Ni + 3 Cr neighbours of a Ni mover
    assert dr.e_bare(p, "Ni", {"Ni": 6, "Cr": 3}) == pytest.approx(6 * 0.20 + 3 * 0.25)


def test_e_bare_ignores_vacant() -> None:
    p = _inline_params()
    assert dr.e_bare(p, "Ni", {"Ni": 9, "Vacant": 3}) == dr.e_bare(p, "Ni", {"Ni": 9})


# --------------------------------------------------------------------------
# Overpotential term
# --------------------------------------------------------------------------


def test_phi_lowers_barrier() -> None:
    p = _inline_params()
    k0 = dr.dissolution_rate(p, "Ni", {"Ni": 9}, T_K=500.0, phi_eV=0.0)
    k1 = dr.dissolution_rate(p, "Ni", {"Ni": 9}, T_K=500.0, phi_eV=0.5)
    assert k1 > k0
    assert k1 == pytest.approx(1.0e4 * math.exp(-(1.8 - 0.5) / (dr.KB_EV_PER_K * 500.0)))


def test_phi_clamps_barrierless() -> None:
    """Φ above E_bare gives a barrierless (clamped) rate equal to ν_E."""
    p = _inline_params()
    k = dr.dissolution_rate(p, "Ni", {"Ni": 9}, T_K=500.0, phi_eV=5.0)
    assert k == pytest.approx(1.0e4)


# --------------------------------------------------------------------------
# rate_law = "tafel_ceiling": k = min(ceiling, nu_E * exp((phi - E_bare)/kT))
# Pub-3 Tier-1 w9 numbers (T 623 K, phi 3.30, eps Fe-Fe 0.33388 / Fe-Ni
# 0.36357, nu_E 1e4, ceiling 1e13).
# --------------------------------------------------------------------------


def _tier1_params(rate_law: str = "tafel_ceiling") -> dr.DissolutionParams:
    return dr.DissolutionParams(
        epsilon={("Fe", "Fe"): 0.33388, ("Fe", "Ni"): 0.36357, ("Ni", "Ni"): 0.36357},
        nu_E_Hz=1.0e4,
        min_coordination=1,
        max_coordination=9,
        rate_law=rate_law,
        ceiling_Hz=1.0e13 if rate_law == "tafel_ceiling" else None,
    )


def test_tafel_ceiling_n5_all_fe_at_ceiling() -> None:
    k = dr.dissolution_rate(_tier1_params(), "Fe", {"Fe": 5}, T_K=623.0, phi_eV=3.30)
    assert k == 1.0e13  # unclamped Tafel would be ~1.55e17


def test_tafel_ceiling_n8_all_ni() -> None:
    k = dr.dissolution_rate(_tier1_params(), "Fe", {"Ni": 8}, T_K=623.0, phi_eV=3.30)
    assert k == pytest.approx(1.4675e7, rel=1e-3)  # numbers-sheet "1.47e7"
    assert k == pytest.approx(
        1.0e4 * math.exp((3.30 - 8 * 0.36357) / (dr.KB_EV_PER_K * 623.0)), rel=1e-12
    )


def test_tafel_ceiling_n9_all_ni() -> None:
    k = dr.dissolution_rate(_tier1_params(), "Fe", {"Ni": 9}, T_K=623.0, phi_eV=3.30)
    assert k == pytest.approx(1.6806e4, rel=1e-3)  # numbers-sheet "1.68e4"
    assert k == pytest.approx(
        1.0e4 * math.exp((3.30 - 9 * 0.36357) / (dr.KB_EV_PER_K * 623.0)), rel=1e-12
    )


def test_clamped_tier1_window_is_flat_at_nu_e() -> None:
    """Default law at phi 3.30: every n <= 9 Fe sits at exactly nu_E (the w9 clamp)."""
    p = _tier1_params("clamped")
    for hist in ({"Fe": 5}, {"Ni": 8}, {"Ni": 9}, {"Fe": 9}):
        assert dr.dissolution_rate(p, "Fe", hist, T_K=623.0, phi_eV=3.30) == 1.0e4


def test_tafel_ceiling_equals_clamped_below_barrier() -> None:
    """Where E_bare > phi the two laws coincide (the floor never binds)."""
    pt, pc = _tier1_params(), _tier1_params("clamped")
    for hist in ({"Ni": 8}, {"Fe": 9}, {"Fe": 3, "Ni": 6}):
        kt = dr.dissolution_rate(pt, "Fe", hist, T_K=623.0, phi_eV=2.50)
        kc = dr.dissolution_rate(pc, "Fe", hist, T_K=623.0, phi_eV=2.50)
        if dr.e_bare(pt, "Fe", hist) >= 2.50:
            assert kt == kc


def test_tafel_ceiling_overflow_caps() -> None:
    """A huge phi overflows exp(); the law must return the ceiling, not raise."""
    k = dr.dissolution_rate(_tier1_params(), "Fe", {"Fe": 1}, T_K=10.0, phi_eV=100.0)
    assert k == 1.0e13


def test_tafel_ceiling_requires_ceiling() -> None:
    p = dr.DissolutionParams(epsilon={("Fe", "Fe"): 0.3}, rate_law="tafel_ceiling")
    with pytest.raises(ValueError):
        dr.dissolution_rate(p, "Fe", {"Fe": 3}, T_K=623.0, phi_eV=1.0)


def test_unknown_rate_law_raises() -> None:
    p = dr.DissolutionParams(epsilon={("Fe", "Fe"): 0.3}, rate_law="tafel")
    with pytest.raises(ValueError):
        dr.dissolution_rate(p, "Fe", {"Fe": 3}, T_K=623.0, phi_eV=1.0)


def test_bad_temperature_raises() -> None:
    p = _inline_params()
    with pytest.raises(ValueError):
        dr.dissolution_rate(p, "Ni", {"Ni": 9}, T_K=0.0)


# --------------------------------------------------------------------------
# Cross-package agreement (the two copies must be identical)
# --------------------------------------------------------------------------


def test_copies_agree_on_grid() -> None:
    """The pyKMC copy must produce identical numbers on a fixed grid."""
    if not _PYKMC_COPY.is_file():
        pytest.skip(f"sibling copy not found at {_PYKMC_COPY}")
    spec = importlib.util.spec_from_file_location("_pykmc_dr", _PYKMC_COPY)
    assert spec and spec.loader
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other  # needed for dataclass annotation resolution
    spec.loader.exec_module(other)

    assert other.KB_EV_PER_K == dr.KB_EV_PER_K
    p_here = _inline_params()
    p_there = other.DissolutionParams(
        epsilon=dict(p_here.epsilon), nu_E_Hz=p_here.nu_E_Hz
    )
    grid = [
        ("Ni", {"Ni": 9}, 500.0, 0.0),
        ("Ni", {"Ni": 6, "Cr": 3}, 500.0, 0.3),
        ("Cr", {"Ni": 8, "Cr": 1}, 700.0, 0.0),
        ("Ni", {"Ni": 9}, 500.0, 5.0),  # clamp branch
    ]
    for mover, hist, T, phi in grid:
        assert dr.dissolution_rate(p_here, mover, hist, T, phi) == pytest.approx(
            other.dissolution_rate(p_there, mover, hist, T, phi), rel=1e-12
        )
