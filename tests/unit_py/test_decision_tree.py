"""Tests for the decision-tree codegen (M-B)."""

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

ANCHOR = CoordOffset(di=0, dj=0, dk=0, sublattice="a")
PX = CoordOffset(di=1, dj=0, dk=0, sublattice="a")
MX = CoordOffset(di=-1, dj=0, dk=0, sublattice="a")
PY = CoordOffset(di=0, dj=1, dk=0, sublattice="a")


def _vac_to(direction: CoordOffset, mover: str = "Ni", name_suffix: str = "") -> Process:
    sign = lambda v: "p" if v >= 0 else "m"  # noqa: E731
    name = (f"hop_{sign(direction.di)}{abs(direction.di)}"
            f"_{sign(direction.dj)}{abs(direction.dj)}"
            f"_{sign(direction.dk)}{abs(direction.dk)}{name_suffix}")
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
    assert "P_hop_p1_p0_p0" in out
    assert "P_hop_p0_p1_p0" in out
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
    assert "static void apply_actions_hop_p1_p0_p0(int site)" in out
    assert "static void apply_actions_hop_p0_p1_p0(int site)" in out
    assert "static const ApplyFn apply_table[N_PROCS]" in out


def test_apply_actions_anchor_uses_site_directly() -> None:
    """The anchor coord (0,0,0,a) → species[site] = ..., not a coord_at call."""
    procs = [_vac_to(PX)]
    out = emit_apply_actions(procs)
    assert "species[site] = SP_NI" in out         # anchor action
    assert "coord_at(site, 1, 0, 0" in out         # +x direction action


def test_apply_actions_multi_site_emits_n_assignments() -> None:
    """A 3-action Process emits 3 species[...] = ... assignments."""
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
    # 3 lines of `species[...] = SP_...;` inside apply_actions_triple
    body_match = re.search(
        r"apply_actions_triple\(int site\) \{(.*?)\}", out, re.DOTALL
    )
    assert body_match is not None
    body = body_match.group(1)
    assert body.count("species[") == 3


# ---------------------------------------------------------------------------
# compile_decision_tree — structural tests
# ---------------------------------------------------------------------------


def test_compile_empty_returns_stub() -> None:
    out = compile_decision_tree([], "touchup_a")
    assert "void touchup_a(int site)" in out
    assert "no processes" in out


def test_compile_single_process_emits_switch() -> None:
    procs = [_vac_to(PX)]
    out = compile_decision_tree(procs, "touchup_a")
    assert "void touchup_a(int site)" in out
    assert "switch (species[site])" in out  # anchor's coord uses `site` directly
    assert "case SP_VACANT:" in out
    assert "add_proc(P_hop_p1_p0_p0, site, rate_table[P_hop_p1_p0_p0].rate);" in out


def test_compile_multiple_processes_share_anchor_branch() -> None:
    """Multiple Processes whose anchor is `Vacant @ (0,0,0,a)` should
    nest under a single `case SP_VACANT:` branch (greedy partitioning
    on the most-shared coord)."""
    procs = [_vac_to(PX), _vac_to(MX), _vac_to(PY)]
    out = compile_decision_tree(procs, "touchup_a")
    # Only one switch on the anchor's species (not 3 separate ones)
    assert out.count("switch (species[site])") == 1
    # All three Processes appear as add_proc calls
    assert out.count("add_proc(P_") == 3


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
    # Both Processes' add_proc lines present
    assert "add_proc(P_hop_p1_p0_p0" in out
    assert "add_proc(P_from_ni" in out


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

    This catches typos in the emitted C and validates that the symbols
    we reference (species[], SP_*, P_*, rate_table[], add_proc,
    coord_at) match the harness's contract.
    """
    procs = [_vac_to(PX), _vac_to(MX), _vac_to(PY)]

    # The harness: stub declarations for every symbol the codegen uses.
    harness = """
#include <stddef.h>

/* Species enum */
typedef enum { SP_VACANT = 0, SP_NI = 1, SP_FE = 2, SP_CR = 3 } Species;

/* Sublattice tags */
typedef enum { SUB_A = 0, SUB_B = 1 } Sublattice;

/* The "lattice" is just a 1024-site flat array for this test. */
static unsigned char species[1024];

/* coord_at: stub — for the test, just clamp into the array. */
int coord_at(int site, int di, int dj, int dk, int sub) {
    (void)di; (void)dj; (void)dk; (void)sub;
    return (site + 17) & 1023;   /* arbitrary but valid */
}

/* add_proc: stub. */
void add_proc(int proc, int site, double rate) {
    (void)proc; (void)site; (void)rate;
}
"""

    # Splice: enum, rate_table, apply_actions, then touchup
    program = (
        harness
        + emit_process_enum(procs)
        + emit_rate_table(procs)
        + emit_apply_actions(procs)
        + compile_decision_tree(procs, "touchup_a")
    )
    # Reference apply_table + rate_table so -Wunused-const-variable doesn't
    # flag them. In production they're called by the runtime; the test
    # harness just needs to satisfy the linter.
    program += """
int main(void) {
    apply_table[0](0);
    return (int)rate_table[0].rate;
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
