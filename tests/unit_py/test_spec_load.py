"""Round-trip tests for the TOML -> ModelSpec loader and its invariants.

Scope: M1 scaffolding. Does NOT test codegen (M2) or rate building (M3).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pylatkmc import load
from pylatkmc.spec import (
    MAX_CUBE_ENTRIES,
    Key,
    KeyAxis,
    ModelSpec,
    RateData,
    Shell,
)

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
EXAMPLE_SPEC = REPO_ROOT / "models" / "ni_fe_cr_v1" / "ni_fe_cr_v1.kmcspec.toml"


# ------------------------------------------------------------------
# Loader round-trip
# ------------------------------------------------------------------
def test_example_spec_loads() -> None:
    spec = load(EXAMPLE_SPEC)
    assert spec.name == "ni_fe_cr_v1"
    assert spec.lattice == "fcc"
    assert spec.species[0] == "Vacant"
    assert {"Ni", "Fe", "Cr"}.issubset(set(spec.species))


def test_example_spec_has_expected_shells() -> None:
    spec = load(EXAMPLE_SPEC)
    names = {s.name for s in spec.shells}
    assert names == {"nn1", "nn2"}


def test_example_spec_cube_size_matches_plan() -> None:
    # Plan: 3 (site_class) * 5 (direction) * 3 (mover) * 5^6 (counts) = 703,125.
    spec = load(EXAMPLE_SPEC)
    assert spec.n_cube_entries() == 703_125


def test_example_spec_all_axes_ordered() -> None:
    spec = load(EXAMPLE_SPEC)
    axes = spec.all_axes()
    assert axes[0] == ("site_class", 3)
    assert axes[1] == ("direction", 5)
    user_names = [a[0] for a in axes[2:]]
    assert user_names == [
        "mover_species",
        "n_vac_nn1",
        "n_Fe_nn1",
        "n_Cr_nn1",
        "n_vac_nn2",
        "n_Fe_nn2",
        "n_Cr_nn2",
    ]


def test_strides_are_row_major() -> None:
    spec = load(EXAMPLE_SPEC)
    strides = spec.strides()
    axes = spec.all_axes()
    # Last stride must be 1.
    assert strides[-1] == 1
    # stride[i] = stride[i+1] * axes[i+1].max
    for i in range(len(strides) - 1):
        assert strides[i] == strides[i + 1] * axes[i + 1][1]


def test_counted_species_per_shell() -> None:
    spec = load(EXAMPLE_SPEC)
    assert spec.counted_species_in_shell("nn1") == ["Fe", "Cr"]
    assert spec.counted_species_in_shell("nn2") == ["Fe", "Cr"]


def test_paths_resolved_to_absolute() -> None:
    spec = load(EXAMPLE_SPEC)
    # primary path is required; resolves through spec dir -> must be absolute.
    assert spec.rate_data.primary.is_absolute()
    # Must point at the curated catalogue.
    assert spec.rate_data.primary.name == "classified_events_with_families.csv"


# ------------------------------------------------------------------
# Invariant tests (constructed specs, not via loader)
# ------------------------------------------------------------------
def _minimal_spec(**overrides: object) -> dict[str, object]:
    """Build kwargs for a minimal valid ModelSpec; override to break invariants."""
    base: dict[str, object] = dict(
        name="tiny",
        lattice="fcc",
        species=["Vacant", "Ni"],
        shells=[Shell(name="nn1", cutoff_mult=1.05)],
        key=Key(
            axes=[
                KeyAxis(name="n_vac_nn1", kind="count", shell="nn1", match="vac", max=3),
            ]
        ),
        rate_data=RateData(
            primary=Path("/tmp/primary.csv"),
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )
    base.update(overrides)
    return base


def test_species_must_start_with_vacant() -> None:
    with pytest.raises(ValidationError, match="start with 'Vacant'"):
        ModelSpec(**_minimal_spec(species=["Ni", "Fe"]))  # type: ignore[arg-type]


def test_reserved_axis_name_rejected() -> None:
    with pytest.raises(ValidationError, match="reserved"):
        ModelSpec(
            **_minimal_spec(
                key=Key(
                    axes=[
                        KeyAxis(name="site_class", kind="enum", max=3),
                    ]
                ),
            )
        )  # type: ignore[arg-type]


def test_count_axis_requires_shell_and_match() -> None:
    with pytest.raises(ValidationError, match="shell and match"):
        # kind='count' without shell/match
        KeyAxis(name="n_vac", kind="count", max=3)


def test_count_axis_unknown_shell_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown shell"):
        ModelSpec(
            **_minimal_spec(
                key=Key(
                    axes=[
                        KeyAxis(name="n_vac_nn9", kind="count", shell="nn9", match="vac", max=3),
                    ]
                ),
            )
        )  # type: ignore[arg-type]


def test_duplicate_axis_names_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate axis names"):
        ModelSpec(
            **_minimal_spec(
                key=Key(
                    axes=[
                        KeyAxis(name="x", kind="count", shell="nn1", match="vac", max=3),
                        KeyAxis(name="x", kind="count", shell="nn1", match="Ni", max=3),
                    ]
                ),
            )
        )  # type: ignore[arg-type]


def test_cube_size_cap_enforced() -> None:
    # 20 count axes * max=8 = 8^20 ~ 10^18 > 1e8 cap.
    with pytest.raises(ValidationError, match="MAX_CUBE_ENTRIES"):
        ModelSpec(
            **_minimal_spec(
                key=Key(
                    axes=[
                        KeyAxis(name=f"a{i}", kind="count", shell="nn1", match="vac", max=8)
                        for i in range(20)
                    ]
                ),
            )
        )  # type: ignore[arg-type]


def test_missing_spec_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load("/nonexistent/path/foo.kmcspec.toml")


# ------------------------------------------------------------------
# Helpers live-tested (so regressions show up here, not buried)
# ------------------------------------------------------------------
def test_n_cube_entries_never_exceeds_cap() -> None:
    spec = load(EXAMPLE_SPEC)
    assert spec.n_cube_entries() <= MAX_CUBE_ENTRIES


def test_has_mover_species_axis() -> None:
    spec = load(EXAMPLE_SPEC)
    assert spec.has_mover_species_axis() is True
