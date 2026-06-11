"""Tests for the analytical electrochemical dissolution family translator."""

from __future__ import annotations

from pathlib import Path

import pytest

from pylatkmc.decision_tree import emit_rate_table
from pylatkmc.dissolution_rate import DissolutionParams, e_bare, load_params
from pylatkmc.processes import Action, Condition, CoordOffset, Process
from pylatkmc.translator import compositions_of, translate_dissolution_family

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EPS_TABLE = _REPO_ROOT / "models/ni_dissolution_demo/epsilon_table.toml"


@pytest.fixture
def params() -> DissolutionParams:
    return load_params(_EPS_TABLE)


# --------------------------------------------------------------------------
# compositions_of
# --------------------------------------------------------------------------


def test_compositions_single_species() -> None:
    comps = compositions_of(5, ("Ni",))
    assert comps == [{"Ni": 5}]


def test_compositions_sum_to_n_and_cover_all_species() -> None:
    comps = compositions_of(3, ("Ni", "Cr"))
    for c in comps:
        assert sum(c.values()) == 3
        assert set(c) == {"Ni", "Cr"}  # every species present (incl. 0)
    # multisets of size 3 over 2 species => 4
    assert len(comps) == 4


# --------------------------------------------------------------------------
# translate_dissolution_family — structure & invariants
# --------------------------------------------------------------------------


def test_pure_ni_process_count(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni"], T_K=500.0)
    # one per coordination N in [min, max]
    assert len(procs) == params.max_coordination - params.min_coordination + 1


def test_every_process_is_one_action_to_vacant(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni", "Cr", "Fe"], T_K=500.0)
    for p in procs:
        assert len(p.actions) == 1
        a = p.actions[0]
        assert a.coord == CoordOffset(code="NC_ANCHOR")
        assert a.after == "Vacant"
        assert a.before != "Vacant"
        # the single Condition pins the anchor to the mover species
        assert p.conditions == (Condition(coord=CoordOffset(code="NC_ANCHOR"), species=a.before),)


def test_flag_and_prefactor(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni", "Cr", "Fe"], T_K=500.0)
    for p in procs:
        assert p.is_electrochemical is True
        assert p.prefactor_Hz == pytest.approx(params.nu_E_Hz)
        assert p.family_id == "dissolution"


def test_ea_equals_e_bare(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni", "Cr"], T_K=500.0)
    for p in procs:
        mover = p.actions[0].before
        hist = {sc.species: sc.count for sc in p.shell_conditions}
        assert p.Ea_eV == pytest.approx(e_bare(params, mover, hist))
    # spot check the pure-Ni N=8 anchor used by the smoke test
    ni8 = next(p for p in procs if p.name == "dissolution__ni__ni8")
    assert ni8.Ea_eV == pytest.approx(1.6)  # 8 * 0.200


def test_shell_conditions_sum_to_N_and_gate_all_species(params: DissolutionParams) -> None:
    species = ["Vacant", "Ni", "Cr", "Fe"]
    occupied = {s for s in species if s != "Vacant"}
    procs = translate_dissolution_family(params, species, T_K=500.0)
    for p in procs:
        # every occupied species is gated (incl. count 0) -> mutually exclusive buckets
        assert {sc.species for sc in p.shell_conditions} == occupied
        for sc in p.shell_conditions:
            assert sc.coord == CoordOffset(code="NC_ANCHOR")
            assert sc.shell == "1nn"
        n = sum(sc.count for sc in p.shell_conditions)
        assert params.min_coordination <= n <= params.max_coordination


def test_coordination_gate_excludes_bulk(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni", "Cr", "Fe"], T_K=500.0)
    for p in procs:
        n = sum(sc.count for sc in p.shell_conditions)
        assert n <= params.max_coordination  # never emit N > max (bulk atoms can't dissolve)
        assert n >= params.min_coordination


def test_names_unique(params: DissolutionParams) -> None:
    procs = translate_dissolution_family(params, ["Vacant", "Ni", "Cr", "Fe"], T_K=500.0)
    names = [p.name for p in procs]
    assert len(set(names)) == len(names)


# --------------------------------------------------------------------------
# emit_rate_table — the is_electrochemical flag reaches the C struct
# --------------------------------------------------------------------------


def test_rate_table_emits_electrochemical_flag(params: DissolutionParams) -> None:
    anchor = CoordOffset(code="NC_ANCHOR")
    hop = Process(
        name="hop_x",
        family_id="surface_1NN_inplane",
        Ea_eV=0.5,
        rate_constant=1.0e7,
        prefactor_Hz=1.0e13,
        conditions=(Condition(coord=anchor, species="Vacant"),),
        actions=(Action(coord=anchor, before="Vacant", after="Ni"),),
    )
    diss = translate_dissolution_family(params, ["Vacant", "Ni"], T_K=500.0)[0]
    rt = emit_rate_table([hop, diss])
    assert "int32_t is_electrochemical; int32_t _pad;" in rt
    assert "_Static_assert(sizeof(RateConst) == 24" in rt
    assert f"[P_{hop.name}]" in rt and ".is_electrochemical = 0" in rt
    assert f"[P_{diss.name}]" in rt
    # the dissolution row carries the flag set
    diss_line = next(line for line in rt.splitlines() if f"[P_{diss.name}]" in line)
    assert ".is_electrochemical = 1" in diss_line
