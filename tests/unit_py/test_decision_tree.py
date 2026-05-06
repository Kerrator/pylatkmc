"""Tests for the decision-tree codegen (M-B + M-D-Prep updates)."""

from __future__ import annotations

import re
import subprocess

import pytest

from pylatkmc.decision_tree import (
    compile_decision_tree,
    emit_apply_actions,
    emit_process_enum,
    emit_rate_table,
)
from pylatkmc.processes import Action, Condition, CoordOffset, Process

ANCHOR = CoordOffset(code="NC_ANCHOR")
PX = CoordOffset(code="NC_NN1_PX")
MX = CoordOffset(code="NC_NN1_MX")
PY = CoordOffset(code="NC_NN1_PY")
NN2_PX = CoordOffset(code="NC_NN2_PX")


def _vac_to(direction: CoordOffset, mover: str = "Ni", name_suffix: str = "") -> Process:
    """Vacancy at anchor + mover at `direction` → swap. Process name is
    derived from the direction's NeighbourCode for stable C identifiers."""
    code = direction.code.removeprefix("NC_").lower()
    name = f"hop_{code}{name_suffix}"
    return Process(
        name=name,
        family_id="testfam",
        Ea_eV=0.6,
        rate_constant=1.0e7,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=direction, species=mover),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after=mover),
            Action(coord=direction, before=mover, after="Vacant"),
        ),
    )


# ---------------------------------------------------------------------------
# emit_process_enum
# ---------------------------------------------------------------------------


def test_enum_includes_n_procs() -> None:
    procs = [_vac_to(PX), _vac_to(PY)]
    out = emit_process_enum(procs)
    assert "P_hop_nn1_px" in out
    assert "P_hop_nn1_py" in out
    assert "N_PROCS" in out


def test_enum_empty_list() -> None:
    assert "N_PROCS = 0" in emit_process_enum([])


# ---------------------------------------------------------------------------
# emit_rate_table
# ---------------------------------------------------------------------------


def test_rate_table_has_one_entry_per_process() -> None:
    procs = [_vac_to(PX), _vac_to(PY)]
    out = emit_rate_table(procs)
    assert out.count("[P_hop") == 2
    assert ".rate = 1.0000000000e+07" in out
    assert ".Ea_eV = 0.600000" in out


def test_rate_table_rejects_string_expression() -> None:
    """Bystander-modulated rates aren't supported yet (planned: M-A++)."""
    p = Process(
        name="boost", family_id="x", Ea_eV=0.5,
        rate_constant="k0 * exp(-Ea/kT) * boost",
        conditions=(Condition(coord=ANCHOR, species="Vacant"),),
        actions=(Action(coord=ANCHOR, before="Vacant", after="Ni"),),
    )
    with pytest.raises(NotImplementedError, match="Bystander"):
        emit_rate_table([p])


# ---------------------------------------------------------------------------
# emit_apply_actions
# ---------------------------------------------------------------------------


def test_apply_actions_one_function_per_process() -> None:
    procs = [_vac_to(PX), _vac_to(PY)]
    out = emit_apply_actions(procs)
    assert "static HopOutcome apply_actions_hop_nn1_px(State *st, const Lattice *lat, int site)" in out
    assert "static HopOutcome apply_actions_hop_nn1_py(State *st, const Lattice *lat, int site)" in out
    assert "static const ApplyFn apply_table[N_PROCS]" in out


def test_apply_actions_anchor_uses_site_directly() -> None:
    """The anchor coord (NC_ANCHOR) → `site` in the StateAction.site
    field; the +x direction uses `coord_table` lookup."""
    procs = [_vac_to(PX)]
    out = emit_apply_actions(procs)
    # The anchor StateAction's .site field is `site` (not a coord_table lookup).
    assert ".site = site," in out
    # The +x StateAction's .site field uses coord_table.
    assert "coord_table[site * N_NEIGHBOUR_CODES + NC_NN1_PX]" in out


def test_apply_actions_multi_site_emits_n_assignments() -> None:
    """A 3-action Process emits a StateAction[3] array."""
    p = Process(
        name="triple",
        family_id="x",
        Ea_eV=0.9,
        rate_constant=1e10,
        conditions=(
            Condition(coord=ANCHOR, species="Vacant"),
            Condition(coord=PX, species="Ni"),
            Condition(coord=PY, species="Ni"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=PX, before="Ni", after="Vacant"),
            Action(coord=PY, before="Ni", after="Vacant"),
        ),
    )
    out = emit_apply_actions([p])
    body_match = re.search(
        r"apply_actions_triple\(State \*st, const Lattice \*lat, int site\) \{(.*?)^}",
        out, re.DOTALL | re.MULTILINE,
    )
    assert body_match is not None
    body = body_match.group(1)
    assert "StateAction acts[3]" in body
    # 3 .site = ... lines (one per action).
    assert body.count(".site = ") == 3


def test_apply_actions_returns_hop_outcome_for_simple_hop() -> None:
    """A 1-vacancy-out + 1-vacancy-in pattern should populate v_origin and v_dest."""
    procs = [_vac_to(PX)]
    out = emit_apply_actions(procs)
    assert "v_origin = acts[0].site" in out      # action 0 is V→Ni at anchor
    assert "v_dest = acts[1].site" in out         # action 1 is Ni→V at +x


def test_apply_actions_returns_neg1_for_non_hop() -> None:
    """A pure species swap (no vacancy involved) returns v_origin=-1, v_dest=-1."""
    p = Process(
        name="exchange",
        family_id="x",
        Ea_eV=0.5,
        rate_constant=1e10,
        conditions=(
            Condition(coord=ANCHOR, species="Ni"),
            Condition(coord=PX, species="Fe"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Ni", after="Fe"),
            Action(coord=PX, before="Fe", after="Ni"),
        ),
    )
    out = emit_apply_actions([p])
    assert ".v_origin = -1, .v_dest = -1" in out


# ---------------------------------------------------------------------------
# compile_decision_tree — structural tests
# ---------------------------------------------------------------------------


def test_compile_empty_returns_stub() -> None:
    out = compile_decision_tree([], "touchup_a")
    assert "void touchup_a(const Lattice *lat, const State *st," in out
    assert "no processes" in out


def test_compile_single_process_emits_switch() -> None:
    procs = [_vac_to(PX)]
    out = compile_decision_tree(procs, "touchup_a")
    assert "void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site)" in out
    assert "switch (st->species[site])" in out  # anchor uses st->species[site]
    assert "case SP_VACANT:" in out
    assert "avail_sites_add(as, P_hop_nn1_px, site);" in out


def test_compile_multiple_processes_share_anchor_branch() -> None:
    """Multiple Processes whose anchor is `Vacant @ NC_ANCHOR` should
    nest under a single `case SP_VACANT:` branch (greedy partitioning
    on the most-shared coord)."""
    procs = [_vac_to(PX), _vac_to(MX), _vac_to(PY)]
    out = compile_decision_tree(procs, "touchup_a")
    # Only one switch on the anchor's species (not 3 separate ones)
    assert out.count("switch (st->species[site])") == 1
    # All three Processes appear as avail_sites_add calls
    assert out.count("avail_sites_add(as, P_") == 3


def test_compile_rejects_duplicate_names() -> None:
    """Translator should never emit duplicates, but compile_decision_tree
    has its own check."""
    p1 = _vac_to(PX, name_suffix="_a")
    p2 = _vac_to(PX, name_suffix="_a")  # same name as p1
    with pytest.raises(ValueError, match="duplicate"):
        compile_decision_tree([p1, p2], "touchup_a")


def test_compile_disjoint_anchor_species_partitioned() -> None:
    """Two Processes with different anchor species (Vacant vs Ni) end
    up in separate case branches."""
    p_vac = _vac_to(PX)
    # Process with Ni at anchor (atomic motion driven from a Ni site)
    p_ni = Process(
        name="from_ni",
        family_id="testfam",
        Ea_eV=0.7,
        rate_constant=1.0e6,
        conditions=(
            Condition(coord=ANCHOR, species="Ni"),
            Condition(coord=PX, species="Vacant"),
        ),
        actions=(
            Action(coord=ANCHOR, before="Ni", after="Vacant"),
            Action(coord=PX, before="Vacant", after="Ni"),
        ),
    )
    out = compile_decision_tree([p_vac, p_ni], "touchup_a")
    assert "case SP_VACANT:" in out
    assert "case SP_NI:" in out
    # Both Processes' avail_sites_add lines present
    assert "avail_sites_add(as, P_hop_nn1_px" in out
    assert "avail_sites_add(as, P_from_ni" in out


# ---------------------------------------------------------------------------
# Compilability: the emitted C should compile under a stub harness
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    subprocess.run(["which", "cc"], capture_output=True).returncode != 0,
    reason="C compiler not available",
)
def test_compile_output_compiles_under_stub_harness(tmp_path) -> None:
    """End-to-end: emit C for a 4-Process tree, splice it into a stub
    harness, compile with cc -c, expect no errors.

    The stub harness provides the runtime symbols the codegen references:
    Lattice, State, AvailSites, StateAction, SP_*, NC_*, N_NEIGHBOUR_CODES,
    avail_sites_add, state_apply_actions.
    """
    procs = [_vac_to(PX), _vac_to(MX), _vac_to(PY)]

    harness = """
#include <stddef.h>
#include <stdint.h>

/* Species enum */
typedef enum { SP_VACANT = 0, SP_NI = 1, SP_FE = 2, SP_CR = 3 } Species;

/* NeighbourCode enum (mirror of coord_codes.h) */
typedef enum {
    NC_ANCHOR = 0,
    NC_NN1_PX, NC_NN1_MX, NC_NN1_PY, NC_NN1_MY,
    NC_NN1_DOWN_PP, NC_NN1_DOWN_PM, NC_NN1_DOWN_MP, NC_NN1_DOWN_MM,
    NC_NN1_UP_PP, NC_NN1_UP_PM, NC_NN1_UP_MP, NC_NN1_UP_MM,
    NC_NN2_DIAG_PP, NC_NN2_DIAG_PM, NC_NN2_DIAG_MP, NC_NN2_DIAG_MM,
    NC_NN2_PX, NC_NN2_MX, NC_NN2_PY, NC_NN2_MY, NC_NN2_PZ, NC_NN2_MZ,
    N_NEIGHBOUR_CODES
} NeighbourCode;

/* Minimal Lattice / State shims sufficient for the codegen's references. */
typedef struct Lattice {
    int32_t  *coord_table;
} Lattice;

typedef struct State {
    uint8_t  *species;
} State;

/* AvailSites is opaque to the codegen — only avail_sites_add() touches it. */
typedef struct AvailSites AvailSites;

/* StateAction matches the runtime's state.h definition. */
typedef struct StateAction {
    int32_t site;
    uint8_t before;
    uint8_t after;
} StateAction;

/* Stub APIs: signatures the codegen calls. */
void avail_sites_add(AvailSites *as, int32_t proc, int32_t site) {
    (void)as; (void)proc; (void)site;
}

int state_apply_actions(State *st, const StateAction *acts, int32_t n,
                        uint8_t vacant_sp) {
    (void)st; (void)acts; (void)n; (void)vacant_sp;
    return 0;
}
"""

    program = (
        harness
        + emit_process_enum(procs)
        + emit_rate_table(procs)
        + emit_apply_actions(procs)
        + compile_decision_tree(procs, "touchup_a")
    )
    # Reference apply_table + rate_table so -Wunused-const-variable doesn't
    # flag them.
    program += """
int main(void) {
    Lattice lat = { 0 };
    State st = { 0 };
    AvailSites *as = (AvailSites *)(uintptr_t)0;
    HopOutcome ho = apply_table[0](&st, &lat, 0);
    touchup_a(&lat, &st, as, 0);
    return (int)rate_table[0].rate + ho.v_origin + ho.v_dest;
}
"""

    src = tmp_path / "test_proclist.c"
    src.write_text(program)

    obj = tmp_path / "test_proclist.o"
    result = subprocess.run(
        ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-c",
         str(src), "-o", str(obj)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"emitted C did not compile:\n"
        f"--- stderr ---\n{result.stderr}\n"
        f"--- source ({len(program)} bytes) ---\n"
        f"{program}"
    )
    assert obj.exists()
