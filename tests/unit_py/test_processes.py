"""Tests for the pattern-DB IR (processes.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pylatkmc.processes import (
    ANCHOR_COORD,
    NEIGHBOUR_CODES,
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
    c = CoordOffset(code="NC_NN1_PX")
    assert c.code == "NC_NN1_PX"
    assert str(c) == "NC_NN1_PX"


def test_coord_offset_anchor_is_valid() -> None:
    c = CoordOffset(code="NC_ANCHOR")
    assert c.code == "NC_ANCHOR"
    assert ANCHOR_COORD == c


def test_coord_offset_is_frozen() -> None:
    c = CoordOffset(code="NC_NN1_PX")
    with pytest.raises(ValidationError):
        c.code = "NC_NN1_MX"


def test_coord_offset_is_hashable() -> None:
    """Used as dict keys / set members in the decision-tree compiler."""
    c1 = CoordOffset(code="NC_NN1_PX")
    c2 = CoordOffset(code="NC_NN1_PX")
    c3 = CoordOffset(code="NC_NN1_PY")
    assert c1 == c2
    assert hash(c1) == hash(c2)
    assert c1 != c3
    assert {c1, c2, c3} == {c1, c3}


def test_coord_offset_invalid_code() -> None:
    with pytest.raises(ValidationError, match="unknown NeighbourCode"):
        CoordOffset(code="NC_NOT_A_THING")


def test_coord_offset_all_known_codes_validate() -> None:
    """Every entry in NEIGHBOUR_CODES is constructible."""
    for code in NEIGHBOUR_CODES:
        c = CoordOffset(code=code)
        assert c.code == code


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------

def test_condition_basic() -> None:
    c = Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Vacant")
    assert c.species == "Vacant"


def test_condition_rejects_empty_species() -> None:
    with pytest.raises(ValidationError):
        Condition(coord=ANCHOR_COORD, species="")


def test_condition_strips_species_whitespace() -> None:
    c = Condition(coord=ANCHOR_COORD, species="  Ni  ")
    assert c.species == "Ni"


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

def test_action_basic() -> None:
    a = Action(coord=ANCHOR_COORD, before="Vacant", after="Ni")
    assert a.before == "Vacant" and a.after == "Ni"


def test_action_rejects_no_op() -> None:
    """before == after means no actual state change — caller error."""
    with pytest.raises(ValidationError, match="before == after"):
        Action(coord=ANCHOR_COORD, before="Ni", after="Ni")


# ---------------------------------------------------------------------------
# Bystander
# ---------------------------------------------------------------------------

def test_bystander_basic() -> None:
    b = Bystander(
        coord=CoordOffset(code="NC_NN1_PX"),
        allowed_species=("Fe", "Cr"),
        flag="1nn",
    )
    assert "Fe" in b.allowed_species and "Cr" in b.allowed_species


def test_bystander_rejects_duplicate_species() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        Bystander(
            coord=CoordOffset(code="NC_NN1_PX"),
            allowed_species=("Fe", "Fe"),
            flag="1nn",
        )


# ---------------------------------------------------------------------------
# Process — happy path
# ---------------------------------------------------------------------------

ANCHOR = ANCHOR_COORD
NN1_PX = CoordOffset(code="NC_NN1_PX")
NN1_PY = CoordOffset(code="NC_NN1_PY")
NN1_MX = CoordOffset(code="NC_NN1_MX")
NN2_PX = CoordOffset(code="NC_NN2_PX")


def _simple_1NN_hop() -> Process:
    """Vacancy at anchor, Ni at +x → Ni hops in, leaving vacancy at +x."""
    return Process(
        name="surface_1NN_inplane__nv1_0__simple",
        family_id="surface_1NN_inplane",
        Ea_eV=0.646,
        rate_constant=1.0e13,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_PX, species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=NN1_PX, before="Ni", after="Vacant"),
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
    """Row shuffle: vacancy + Ni + Ni at sites 0, +x, +2x → row shuffles.

    Note: with NeighbourCode IR, "+2x" is the axial 2NN code (NC_NN2_PX),
    distinct from NC_NN1_PX. The vacancy hops 2 sites in x; the middle
    Ni stays in place (no Action for it)."""
    p = Process(
        name="surface_1NN_inplane__nv1_0__triple",
        family_id="surface_1NN_inplane",
        Ea_eV=0.943,
        rate_constant=1.0e13,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_PX, species="Ni"),
            Condition(coord=NN2_PX, species="Ni"),
        ),
        actions=(
            # The vacancy "moves" two sites; intermediate atom stays put.
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=NN2_PX, before="Ni",     after="Vacant"),
        ),
    )
    assert len(p.actions) == 2  # the row's middle atom doesn't change species
    assert p.actions[0].coord == ANCHOR
    assert p.actions[1].coord == NN2_PX


def test_process_with_bystanders() -> None:
    """Surface 1NN hop where the rate depends on n_Fe_nn1 (bystander count)."""
    p = Process(
        name="surface_1NN_inplane__nv1_0__Ni_with_Fe_neighbors",
        family_id="surface_1NN_inplane",
        Ea_eV=0.646,
        rate_constant="k0 * exp(-Ea/kT) * boost_Fe_1nn**nr_Fe_1nn",
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=NN1_PX, species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=NN1_PX, before="Ni", after="Vacant"),
        ),
        bystanders=(
            Bystander(coord=NN1_PY, allowed_species=("Fe",), flag="1nn"),
            Bystander(coord=NN1_MX, allowed_species=("Fe",), flag="1nn"),
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
                Condition(coord=NN1_PX, species="Ni"),
            ),
            actions=(
                # Action says "before=Fe" but Condition says "Ni" at NN1_PX
                Action(coord=NN1_PX, before="Fe", after="Vacant"),
            ),
        )


def test_process_rejects_coord_in_both_conditions_and_bystanders() -> None:
    with pytest.raises(ValidationError, match="appears in both"):
        Process(
            name="overlap",
            family_id="x",
            Ea_eV=0.5,
            rate_constant=1e13,
            conditions=(Condition(coord=NN1_PX, species="Ni"),),
            actions=(Action(coord=NN1_PX, before="Ni", after="Vacant"),),
            bystanders=(
                Bystander(coord=NN1_PX, allowed_species=("Fe",), flag="1nn"),
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


# ===========================================================================
# ShellCondition (M-D-Prep-v0.3) — bucket-key-aware hard count gates
# ===========================================================================


from pylatkmc.processes import ShellCondition  # noqa: E402


def test_shell_condition_basic() -> None:
    """Construct a ShellCondition with all required fields."""
    sc = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="1nn",
        species="Vacant",
        count=4,
    )
    assert sc.coord.code == "NC_NN1_PX"
    assert sc.shell == "1nn"
    assert sc.species == "Vacant"
    assert sc.count == 4


def test_shell_condition_count_zero_is_valid() -> None:
    """nv1=0 (mover has 0 vacant 1NN) is a valid bucket key."""
    sc = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="1nn",
        species="Vacant",
        count=0,
    )
    assert sc.count == 0


def test_shell_condition_negative_count_rejected() -> None:
    """count < 0 is invalid."""
    with pytest.raises(ValidationError):
        ShellCondition(
            coord=CoordOffset(code="NC_NN1_PX"),
            shell="1nn", species="Vacant", count=-1,
        )


def test_shell_condition_unknown_shell_rejected() -> None:
    """Only '1nn' and '2nn' are supported in v0.3."""
    with pytest.raises(ValidationError):
        ShellCondition(
            coord=CoordOffset(code="NC_NN1_PX"),
            shell="3nn",  # type: ignore[arg-type]
            species="Vacant", count=4,
        )


def test_shell_condition_is_hashable() -> None:
    """Required for set-based deduplication in codegen."""
    sc1 = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="1nn", species="Vacant", count=4,
    )
    sc2 = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="1nn", species="Vacant", count=4,
    )
    assert sc1 == sc2
    assert hash(sc1) == hash(sc2)
    assert {sc1, sc2} == {sc1}


def test_process_with_shell_conditions() -> None:
    """Process can carry shell_conditions; defaults to empty."""
    p_default = _simple_1NN_hop()
    assert p_default.shell_conditions == ()

    sc = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="1nn", species="Vacant", count=4,
    )
    p_gated = Process(
        name="hop_nv1_4",
        family_id="surface_1NN_inplane",
        Ea_eV=0.167,
        rate_constant=1.0e7,
        conditions=(
            Condition(coord=ANCHOR_COORD, species="Vacant"),
            Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR_COORD, before="Vacant", after="Ni"),
            Action(coord=CoordOffset(code="NC_NN1_PX"),
                   before="Ni", after="Vacant"),
        ),
        shell_conditions=(sc,),
    )
    assert len(p_gated.shell_conditions) == 1
    assert p_gated.shell_conditions[0].count == 4


def test_process_rejects_shell_condition_overlap_with_bystander() -> None:
    """A (coord) cannot have both a ShellCondition (hard) and a
    Bystander (soft) — they make conflicting claims about the same
    site's role."""
    coord_px = CoordOffset(code="NC_NN1_PX")
    sc = ShellCondition(coord=coord_px, shell="1nn", species="Vacant", count=4)
    by = Bystander(coord=coord_px, allowed_species=("Fe",), flag="1nn")
    with pytest.raises(ValidationError):
        Process(
            name="overlap",
            family_id="x", Ea_eV=0.5, rate_constant=1.0,
            conditions=(Condition(coord=ANCHOR_COORD, species="Vacant"),),
            actions=(Action(coord=ANCHOR_COORD, before="Vacant", after="Ni"),),
            shell_conditions=(sc,),
            bystanders=(by,),
        )


def test_process_with_shell_conditions_serialises() -> None:
    """ShellConditions round-trip through JSON for golden-file tests."""
    sc = ShellCondition(
        coord=CoordOffset(code="NC_NN1_PX"),
        shell="2nn", species="Vacant", count=1,
    )
    p = Process(
        name="hop_with_sc",
        family_id="x", Ea_eV=0.5, rate_constant=1.0,
        conditions=(Condition(coord=ANCHOR_COORD, species="Vacant"),),
        actions=(Action(coord=ANCHOR_COORD, before="Vacant", after="Ni"),),
        shell_conditions=(sc,),
    )
    json_str = p.model_dump_json()
    p2 = Process.model_validate_json(json_str)
    assert p == p2
    assert p2.shell_conditions[0].count == 1
    assert p2.shell_conditions[0].shell == "2nn"
