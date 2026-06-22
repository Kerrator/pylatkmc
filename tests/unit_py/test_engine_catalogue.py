from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.processes import (
    Action,
    Condition,
    CoordOffset,
    Process,
    ShellCondition,
)

SPECIES = ["Vacant", "Ni", "Fe", "Cr"]


def _hop_process() -> Process:
    """A Ni hop from +x into the anchor vacancy, gated by exactly 1 vacant 1NN
    around the mover."""
    return Process(
        name="demo_hop",
        family_id="surface_1NN_inplane",
        Ea_eV=0.5,
        rate_constant=1.0e9,
        conditions=(
            Condition(coord=CoordOffset(code="NC_ANCHOR"), species="Vacant"),
            Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),
        ),
        actions=(
            Action(coord=CoordOffset(code="NC_ANCHOR"), before="Vacant", after="Ni"),
            Action(coord=CoordOffset(code="NC_NN1_PX"), before="Ni", after="Vacant"),
        ),
        shell_conditions=(
            ShellCondition(
                coord=CoordOffset(code="NC_NN1_PX"), shell="1nn", species="Vacant", count=1
            ),
        ),
    )


def test_compile_catalogue_indexes_species_and_codes():
    from pylatkmc.engine.coords import CODE_INDEX

    compiled = compile_catalogue([_hop_process()], SPECIES)
    assert len(compiled) == 1
    cp = compiled[0]
    assert cp.name == "demo_hop"
    assert cp.rate == 1.0e9
    assert cp.anchor_species == 0  # Vacant
    # anchor condition (Vacant at NC_ANCHOR) + Ni at NC_NN1_PX
    assert (CODE_INDEX["NC_ANCHOR"], 0) in cp.conds
    assert (CODE_INDEX["NC_NN1_PX"], 1) in cp.conds
    # shell: (code, kind 0=1nn, species 0=Vacant, count 1)
    assert cp.shells == ((CODE_INDEX["NC_NN1_PX"], 0, 0, 1),)
    # vacancy moves from anchor (Vacant->Ni) to NC_NN1_PX (Ni->Vacant)
    assert cp.v_from_code == CODE_INDEX["NC_ANCHOR"]
    assert cp.v_to_code == CODE_INDEX["NC_NN1_PX"]
