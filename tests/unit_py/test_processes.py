"""Tests for the pattern-DB IR (processes.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pylatkmc.processes import (
    Action,
    Bystander,
    Condition,
    CoordOffset,
    Process,
)


# ---------------------------------------------------------------------------
# CoordOffset
# ---------------------------------------------------------------------------

def test_coord_offset_basic() -> None:
    c = CoordOffset(di=1, dj=0, dk=0, sublattice="a")
    assert c.di == 1
    assert c.sublattice == "a"
    assert str(c) == "(1,0,0,a)"


def test_coord_offset_is_frozen() -> None:
    c = CoordOffset(di=0, dj=0, dk=0, sublattice="a")
    with pytest.raises(ValidationError):
        c.di = 99


def test_coord_offset_is_hashable() -> None:
    """Used as dict keys / set members in the decision-tree compiler."""
    c1 = CoordOffset(di=1, dj=0, dk=0, sublattice="a")
    c2 = CoordOffset(di=1, dj=0, dk=0, sublattice="a")
    c3 = CoordOffset(di=0, dj=1, dk=0, sublattice="a")
    assert c1 == c2
    assert hash(c1) == hash(c2)
    assert c1 != c3
    assert {c1, c2, c3} == {c1, c3}


def test_coord_offset_invalid_sublattice() -> None:
    with pytest.raises(ValidationError):
        CoordOffset(di=0, dj=0, dk=0, sublattice="c")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------

def test_condition_basic() -> None:
    c = Condition(
        coord=CoordOffset(di=1, dj=0, dk=0, sublattice="a"),
        species="Vacant",
    )
    assert c.species == "Vacant"


def test_condition_rejects_empty_species() -> None:
    with pytest.raises(ValidationError):
        Condition(coord=CoordOffset(di=0, dj=0, dk=0, sublattice="a"), species="")


def test_condition_strips_species_whitespace() -> None:
    c = Condition(
        coord=CoordOffset(di=0, dj=0, dk=0, sublattice="a"),
        species="  Ni  ",
    )
    assert c.species == "Ni"


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

def test_action_basic() -> None:
    a = Action(
        coord=CoordOffset(di=0, dj=0, dk=0, sublattice="a"),
        before="Vacant",
        after="Ni",
    )
    assert a.before == "Vacant" and a.after == "Ni"


def test_action_rejects_no_op() -> None:
    """before == after means no actual state change — caller error."""
    with pytest.raises(ValidationError, match="before == after"):
        Action(
            coord=CoordOffset(di=0, dj=0, dk=0, sublattice="a"),
            before="Ni",
            after="Ni",
        )


# ---------------------------------------------------------------------------
# Bystander
# ---------------------------------------------------------------------------

def test_bystander_basic() -> None:
    b = Bystander(
        coord=CoordOffset(di=1, dj=0, dk=0, sublattice="a"),
        allowed_species=("Fe", "Cr"),
        flag="1nn",
    )
    assert "Fe" in b.allowed_species and "Cr" in b.allowed_species


def test_bystander_rejects_duplicate_species() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        Bystander(
            coord=CoordOffset(di=1, dj=0, dk=0, sublattice="a"),
            allowed_species=("Fe", "Fe"),
            flag="1nn",
        )


# ---------------------------------------------------------------------------
# Process — happy path
# ---------------------------------------------------------------------------

ANCHOR = CoordOffset(di=0, dj=0, dk=0, sublattice="a")
NN1_X = CoordOffset(di=1, dj=0, dk=0, sublattice="a")
NN1_Y = CoordOffset(di=0, dj=1, dk=0, sublattice="a")


def _simple_1NN_hop() -> Process:
    """Vacancy at anchor, Ni at +x → Ni hops in, leaving vacancy at +x."""
    return Process(
        name="surface_1NN_inplane__nv1_0__simple",
        family_id="surface_1NN_inplane",
        Ea_eV=0.646,
        rate_constant=1.0e13,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_X, species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=NN1_X, before="Ni", after="Vacant"),
        ),
    )


def test_process_simple_1NN_hop() -> None:
    p = _simple_1NN_hop()
    assert p.name == "surface_1NN_inplane__nv1_0__simple"
    assert len(p.conditions) == 2
    assert len(p.actions) == 2
    assert p.bystanders == ()
    assert p.Ea_eV == 0.646


def test_process_triple_hop_three_actions() -> None:
    """Row shuffle: vacancy + Ni + Ni at sites 0, +x, +2x → row shuffles."""
    nn2_x = CoordOffset(di=2, dj=0, dk=0, sublattice="a")
    p = Process(
        name="surface_1NN_inplane__nv1_0__triple",
        family_id="surface_1NN_inplane",
        Ea_eV=0.943,
        rate_constant=1.0e13,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_X, species="Ni"),
            Condition(coord=nn2_x, species="Ni"),
        ),
        actions=(
            # The vacancy "moves" two sites; intermediate atoms shuffle.
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=nn2_x,  before="Ni",     after="Vacant"),
            # Note: site +x remains "Ni" → "Ni" so it's NOT an Action.
        ),
    )
    assert len(p.actions) == 2  # the row's middle atom doesn't change species
    assert p.actions[0].coord == ANCHOR
    assert p.actions[1].coord == nn2_x


def test_process_with_bystanders() -> None:
    """Surface 1NN hop where the rate depends on n_Fe_nn1 (bystander count)."""
    p = Process(
        name="surface_1NN_inplane__nv1_0__Ni_with_Fe_neighbors",
        family_id="surface_1NN_inplane",
        Ea_eV=0.646,
        rate_constant="k0 * exp(-Ea/kT) * boost_Fe_1nn**nr_Fe_1nn",
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_X, species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=NN1_X, before="Ni", after="Vacant"),
        ),
        bystanders=(
            Bystander(coord=NN1_Y, allowed_species=("Fe",), flag="1nn"),
            Bystander(
                coord=CoordOffset(di=-1, dj=0, dk=0, sublattice="a"),
                allowed_species=("Fe",),
                flag="1nn",
            ),
        ),
    )
    assert len(p.bystanders) == 2
    assert isinstance(p.rate_constant, str)


# ---------------------------------------------------------------------------
# Process — validation rules
# ---------------------------------------------------------------------------

def test_process_rejects_empty_actions() -> None:
    with pytest.raises(ValidationError):
        Process(
            name="empty",
            family_id="x",
            Ea_eV=0.5,
            rate_constant=1e13,
            conditions=(Condition(coord=ANCHOR, species="Vacant"),),
            actions=(),  # rejected: a Process must do *something*
        )


def test_process_rejects_invalid_c_identifier_name() -> None:
    """Process names must be valid C identifiers (used as function names)."""
    with pytest.raises(ValidationError):
        Process(
            name="surface-1NN-inplane",  # dashes are illegal in C
            family_id="surface_1NN_inplane",
            Ea_eV=0.5,
            rate_constant=1e13,
            conditions=(),
            actions=(Action(coord=ANCHOR, before="Vacant", after="Ni"),),
        )


def test_process_rejects_action_before_inconsistent_with_condition() -> None:
    """An Action's `before` at a coord must match the Condition's species
    at that same coord (when one exists).
    """
    with pytest.raises(ValidationError, match="must match"):
        Process(
            name="bad",
            family_id="x",
            Ea_eV=0.5,
            rate_constant=1e13,
            conditions=(
                Condition(coord=ANCHOR, species="Vacant"),
                Condition(coord=NN1_X, species="Ni"),
            ),
            actions=(
                # Action says "before=Fe" but Condition says "Ni" at NN1_X
                Action(coord=NN1_X, before="Fe", after="Vacant"),
            ),
        )


def test_process_rejects_coord_in_both_conditions_and_bystanders() -> None:
    with pytest.raises(ValidationError, match="appears in both"):
        Process(
            name="overlap",
            family_id="x",
            Ea_eV=0.5,
            rate_constant=1e13,
            conditions=(Condition(coord=NN1_X, species="Ni"),),
            actions=(Action(coord=NN1_X, before="Ni", after="Vacant"),),
            bystanders=(
                Bystander(coord=NN1_X, allowed_species=("Fe",), flag="1nn"),
            ),
        )


def test_process_rejects_negative_Ea() -> None:
    with pytest.raises(ValidationError, match="non-negative"):
        Process(
            name="negEa",
            family_id="x",
            Ea_eV=-0.1,
            rate_constant=1e13,
            conditions=(),
            actions=(Action(coord=ANCHOR, before="Vacant", after="Ni"),),
        )


def test_process_is_frozen_and_hashable() -> None:
    """Required for golden-file diffing."""
    p1 = _simple_1NN_hop()
    p2 = _simple_1NN_hop()
    # Frozen
    with pytest.raises(ValidationError):
        p1.Ea_eV = 99.0
    # Hashable
    assert p1 == p2
    assert hash(p1) == hash(p2)
    assert {p1, p2} == {p1}


def test_process_serialises_to_json() -> None:
    """Used by `pylatkmc-gen processes` and golden-file tests."""
    p = _simple_1NN_hop()
    json_str = p.model_dump_json()
    # Round-trip
    p2 = Process.model_validate_json(json_str)
    assert p == p2
