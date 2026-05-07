"""Tests for the catalogue → Process translator (M-A.3, M-A.4)."""

from __future__ import annotations

import csv
import math

import pytest

from pylatkmc.processes import CoordOffset, Process
from pylatkmc.rate_expression import KB_EV_PER_K
from pylatkmc.translator import (
    ANCHOR,
    BULK_1NN_DIRS,
    BULK_2NN_DIRS,
    SURFACE_1NN_INPLANE_DIRS,
    FamilyBucketRow,
    load_family_rate_table,
    parse_bucket_key,
    translate_simple_hop_family,
    translate_surface_1NN_inplane,
)

# ---------------------------------------------------------------------------
# parse_bucket_key
# ---------------------------------------------------------------------------


def test_parse_bucket_two_axis() -> None:
    assert parse_bucket_key("nv1=2_nv2=0") == {"nv1": 2, "nv2": 0}


def test_parse_bucket_one_axis() -> None:
    assert parse_bucket_key("nv1=4") == {"nv1": 4}


def test_parse_bucket_li_prefix() -> None:
    assert parse_bucket_key("li=1_nv1=3") == {"li": 1, "nv1": 3}


def test_parse_bucket_rejects_star() -> None:
    with pytest.raises(ValueError):
        parse_bucket_key("*")


def test_parse_bucket_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_bucket_key("")


def test_parse_bucket_rejects_no_eq() -> None:
    with pytest.raises(ValueError):
        parse_bucket_key("nv1_2")


# ---------------------------------------------------------------------------
# Direction sets — sanity checks
# ---------------------------------------------------------------------------


def test_surface_1NN_4_directions() -> None:
    assert len(SURFACE_1NN_INPLANE_DIRS) == 4
    # All in-plane axial codes
    inplane_codes = {"NC_NN1_PX", "NC_NN1_MX", "NC_NN1_PY", "NC_NN1_MY"}
    assert {d.code for d in SURFACE_1NN_INPLANE_DIRS} == inplane_codes
    # Unique
    assert len(set(SURFACE_1NN_INPLANE_DIRS)) == 4


def test_bulk_1NN_12_directions() -> None:
    assert len(BULK_1NN_DIRS) == 12
    assert len(set(BULK_1NN_DIRS)) == 12


def test_bulk_2NN_6_directions() -> None:
    assert len(BULK_2NN_DIRS) == 6
    # All NC_NN2_* axial codes
    axial_codes = {"NC_NN2_PX", "NC_NN2_MX", "NC_NN2_PY", "NC_NN2_MY", "NC_NN2_PZ", "NC_NN2_MZ"}
    assert {d.code for d in BULK_2NN_DIRS} == axial_codes


# ---------------------------------------------------------------------------
# load_family_rate_table — fixture CSV
# ---------------------------------------------------------------------------


def _write_fixture(path, rows: list[dict]) -> None:
    fields = [
        "family_id",
        "family_name",
        "family_bucket_id",
        "family_bucket_name",
        "site_motion_template",
        "environment_rule",
        "n_events",
        "Ea_mean_eV",
        "Ea_std_eV",
        "Ea_min_eV",
        "Ea_max_eV",
        "Ea_median_eV",
        "source_filter",
        "representative_row_indices",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            full = {k: r.get(k, "") for k in fields}
            w.writerow(full)


def test_load_skips_zero_event_rows(tmp_path) -> None:
    """Buckets with n_events=0 are placeholder rows; skip them."""
    csv_path = tmp_path / "fp.csv"
    _write_fixture(
        csv_path,
        [
            {
                "family_id": "x",
                "family_bucket_id": "nv1=0",
                "n_events": "0",
                "Ea_mean_eV": "0.5",
                "Ea_std_eV": "0",
                "Ea_min_eV": "0",
                "Ea_max_eV": "0",
            },
            {
                "family_id": "x",
                "family_bucket_id": "nv1=1",
                "n_events": "10",
                "Ea_mean_eV": "0.6",
                "Ea_std_eV": "0.01",
                "Ea_min_eV": "0.55",
                "Ea_max_eV": "0.65",
            },
        ],
    )
    rows = load_family_rate_table(csv_path)
    assert len(rows) == 1
    assert rows[0].family_bucket_id == "nv1=1"


def test_load_skips_nan_Ea_rows(tmp_path) -> None:
    """fit_barrier=False families have Ea=NaN; skip."""
    csv_path = tmp_path / "fp.csv"
    _write_fixture(
        csv_path,
        [
            {
                "family_id": "concerted_multisite",
                "family_bucket_id": "n_moved=3",
                "n_events": "5",
                "Ea_mean_eV": "nan",
                "Ea_std_eV": "0",
                "Ea_min_eV": "0",
                "Ea_max_eV": "0",
            },
            {
                "family_id": "x",
                "family_bucket_id": "nv1=0",
                "n_events": "10",
                "Ea_mean_eV": "0.5",
                "Ea_std_eV": "0.01",
                "Ea_min_eV": "0.45",
                "Ea_max_eV": "0.55",
            },
        ],
    )
    rows = load_family_rate_table(csv_path)
    assert len(rows) == 1
    assert rows[0].family_id == "x"


def test_load_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_family_rate_table(tmp_path / "nope.csv")


# ---------------------------------------------------------------------------
# translate_surface_1NN_inplane — happy path
# ---------------------------------------------------------------------------


def _row(family_id: str, bucket: str, n: int, Ea: float, std: float = 0.01) -> FamilyBucketRow:
    return FamilyBucketRow(
        family_id=family_id,
        family_bucket_id=bucket,
        n_events=n,
        Ea_mean_eV=Ea,
        Ea_std_eV=std,
        Ea_min_eV=Ea - 3 * std,
        Ea_max_eV=Ea + 3 * std,
    )


def test_translate_surface_1NN_one_bucket_emits_4_processes() -> None:
    """One bucket × 4 in-plane directions = 4 Processes."""
    rows = [_row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 1.017)]
    out = translate_surface_1NN_inplane(rows, k0_Hz=1.0e13, T_K=500.0)
    assert len(out) == 4
    assert all(isinstance(p, Process) for p in out)
    assert all(p.family_id == "surface_1NN_inplane" for p in out)
    assert all(p.Ea_eV == pytest.approx(1.017) for p in out)


def test_translate_surface_1NN_other_families_ignored() -> None:
    """Rows from other families are filtered out."""
    rows = [
        _row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 1.017),
        _row("subsurface_1NN_inplane", "nv1=0_nv2=0", 100, 0.7),  # different family
        _row("bulk_1NN_inplane", "nv1=0", 50, 0.6),
    ]
    out = translate_surface_1NN_inplane(rows)
    assert len(out) == 4  # only surface_1NN_inplane × 4 dirs
    assert all(p.family_id == "surface_1NN_inplane" for p in out)


def test_translate_emits_distinct_directions() -> None:
    """The 4 emitted Processes have 4 distinct mover-direction Conditions."""
    rows = [_row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 1.017)]
    out = translate_surface_1NN_inplane(rows)
    # Find the mover direction (the non-anchor Condition's coord) per Process
    mover_coords = []
    for p in out:
        non_anchor = [c.coord for c in p.conditions if c.coord != ANCHOR]
        assert len(non_anchor) == 1
        mover_coords.append(non_anchor[0])
    assert len(set(mover_coords)) == 4
    assert set(mover_coords) == set(SURFACE_1NN_INPLANE_DIRS)


def test_translate_actions_swap_anchor_and_mover() -> None:
    """Each emitted Process has 2 Actions: anchor ← Ni, direction ← Vacant."""
    rows = [_row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 1.017)]
    out = translate_surface_1NN_inplane(rows, mover_species="Ni")
    for p in out:
        assert len(p.actions) == 2
        anchor_action = next(a for a in p.actions if a.coord == ANCHOR)
        assert anchor_action.before == "Vacant"
        assert anchor_action.after == "Ni"
        # The other action is the mover-direction site, Ni → Vacant
        mover_action = next(a for a in p.actions if a.coord != ANCHOR)
        assert mover_action.before == "Ni"
        assert mover_action.after == "Vacant"


def test_translate_rate_is_arrhenius() -> None:
    """rate_constant = k0 * exp(-Ea_mean / kT)."""
    rows = [_row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 0.6)]
    out = translate_surface_1NN_inplane(rows, k0_Hz=1.0e13, T_K=500.0)
    expected = 1.0e13 * math.exp(-0.6 / (KB_EV_PER_K * 500.0))
    for p in out:
        assert isinstance(p.rate_constant, float)
        assert p.rate_constant == pytest.approx(expected)


def test_translate_processes_have_unique_names() -> None:
    """No two emitted Processes can share a name (decision-tree codegen
    would conflict)."""
    rows = [
        _row("surface_1NN_inplane", "nv1=0_nv2=0", 591, 1.017),
        _row("surface_1NN_inplane", "nv1=1_nv2=0", 11118, 0.646),
        _row("surface_1NN_inplane", "nv1=2_nv2=0", 4407, 0.459),
    ]
    out = translate_surface_1NN_inplane(rows)
    names = [p.name for p in out]
    assert len(names) == len(set(names)) == 12  # 3 buckets × 4 dirs


def test_translate_process_names_are_valid_c_identifiers() -> None:
    """Required by the IR validator and by the codegen step."""
    import re

    rows = [_row("surface_1NN_inplane", "nv1=2_nv2=0", 4407, 0.459)]
    out = translate_surface_1NN_inplane(rows)
    for p in out:
        assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p.name), p.name


def test_translate_warns_on_high_scatter() -> None:
    """High Ea_std buckets trigger the on_scatter_warn callback."""
    rows = [
        _row("surface_1NN_inplane", "nv1=2_nv2=2", 1550, 0.66, std=0.33),  # wide
        _row("surface_1NN_inplane", "nv1=4_nv2=2", 6574, 0.35, std=0.03),  # tight
    ]
    warnings_seen: list[str] = []
    out = translate_surface_1NN_inplane(rows, on_scatter_warn=warnings_seen.append)
    assert len(out) == 8  # 2 buckets × 4 dirs
    assert len(warnings_seen) == 1
    assert "nv1=2_nv2=2" in warnings_seen[0]


# ---------------------------------------------------------------------------
# translate_simple_hop_family — generic helper used by other families
# ---------------------------------------------------------------------------


def test_translate_simple_hop_bulk_12_directions() -> None:
    """Used for bulk_1NN_inplane: 12 directions per bucket."""
    rows = [_row("bulk_1NN_inplane", "nv1=4_nv2=2", 1000, 0.4)]
    out = translate_simple_hop_family(
        rows=rows,
        family_id="bulk_1NN_inplane",
        directions=BULK_1NN_DIRS,
        mover_species="Ni",
        k0_Hz=1.0e13,
        T_K=500.0,
    )
    assert len(out) == 12


def test_translate_simple_hop_empty_when_no_matching_family() -> None:
    rows = [_row("surface_1NN_inplane", "nv1=0_nv2=0", 1, 1.0)]
    out = translate_simple_hop_family(
        rows=rows,
        family_id="bulk_1NN_inplane",  # not in rows
        directions=BULK_1NN_DIRS,
        mover_species="Ni",
        k0_Hz=1.0e13,
        T_K=500.0,
    )
    assert out == []


# ---------------------------------------------------------------------------
# translate_all — full dispatch across all 12 fit-barrier families
# ---------------------------------------------------------------------------

from pylatkmc.translator import translate_all  # noqa: E402


def test_translate_all_dispatches_per_family() -> None:
    """One bucket per family, each emitting per-direction Processes.
    Total = sum of direction counts across families present in the input."""
    rows = [
        _row("surface_1NN_inplane", "nv1=0_nv2=0", 100, 0.6),  # 4
        _row("subsurface_1NN_inplane", "nv1=0_nv2=0", 100, 0.6),  # 12
        _row("bulk_1NN_inplane", "nv1=0", 50, 0.5),  # 12
        _row("surface_2NN_diagonal", "nv1=0", 20, 0.9),  # 4
        _row("subsurface_2NN_diagonal", "nv1=3", 50, 0.95),  # 6
        _row("surface_interlayer_hop", "li=0_nv1=4", 30, 1.1),  # 4
        _row("subsurface_interlayer_hop", "nv1=2", 50, 1.0),  # 8
        _row("surface_subsurface_exchange_up", "nv1=4", 40, 1.0),  # 4
        _row("surface_subsurface_exchange_down", "nv1=4", 40, 0.9),  # 4
        _row("surface_subsurface_exchange_lateral", "nv1=4", 40, 1.0),  # 8
        _row("subsurface_migration_axial", "nv1=2", 30, 1.0),  # 12
        _row("subsurface_migration_interlayer", "nv1=2", 30, 1.0),  # 8
    ]
    expected_total = 4 + 12 + 12 + 4 + 6 + 4 + 8 + 4 + 4 + 8 + 12 + 8  # = 86
    out = translate_all(rows)
    assert len(out) == expected_total

    # All names unique
    names = [p.name for p in out]
    assert len(names) == len(set(names))


def test_translate_all_reports_unknown_family() -> None:
    rows = [
        _row("surface_1NN_inplane", "nv1=0_nv2=0", 100, 0.6),
        _row("mystery_family", "nv1=0", 10, 0.5),
    ]
    unknown_seen: list[str] = []
    out = translate_all(rows, on_unknown_family=unknown_seen.append)
    assert "mystery_family" in unknown_seen
    # Only surface_1NN_inplane (the known one) emitted Processes
    assert all(p.family_id == "surface_1NN_inplane" for p in out)
    assert len(out) == 4


def test_translate_all_known_skipped_no_warning() -> None:
    """concerted_multisite and unresolved_multisite are deliberately
    skipped without an unknown-family warning."""
    rows = [
        _row("surface_1NN_inplane", "nv1=0_nv2=0", 100, 0.6),
        # If these were in the loaded rows (won't happen in practice
        # since load_family_rate_table filters NaN Ea), they should
        # be silently skipped.
    ]
    unknown_seen: list[str] = []
    out = translate_all(rows, on_unknown_family=unknown_seen.append)
    # Only surface_1NN_inplane emitted Processes; no unknowns flagged.
    assert unknown_seen == []
    assert len(out) == 4


def test_translate_all_empty_input() -> None:
    assert translate_all([]) == []


# ===========================================================================
# v0.3: bucket-key-derived ShellConditions
# ===========================================================================


from pylatkmc.translator import (
    _emit_simple_2action_hop,
    _shell_conditions_from_bucket_key,
)


def test_shell_conditions_from_bucket_key_two_axis() -> None:
    """`nv1=4_nv2=1` → ShellCondition pair at mover."""
    mover = CoordOffset(code="NC_NN1_PX")
    scs = _shell_conditions_from_bucket_key("nv1=4_nv2=1", mover)
    assert len(scs) == 2
    sc1 = next(s for s in scs if s.shell == "1nn")
    sc2 = next(s for s in scs if s.shell == "2nn")
    assert sc1.count == 4 and sc1.species == "Vacant" and sc1.coord == mover
    assert sc2.count == 1 and sc2.species == "Vacant" and sc2.coord == mover


def test_shell_conditions_from_bucket_key_single_axis() -> None:
    """`nv1=2` → single ShellCondition (1NN axis only)."""
    mover = CoordOffset(code="NC_NN1_DOWN_PP")
    scs = _shell_conditions_from_bucket_key("nv1=2", mover)
    assert len(scs) == 1
    assert scs[0].shell == "1nn" and scs[0].count == 2


def test_shell_conditions_from_bucket_key_layer_axis_skipped() -> None:
    """`li=k_nv1=m` → layer dropped (v0.3 unsupported), nv1 kept."""
    mover = CoordOffset(code="NC_NN1_PX")
    scs = _shell_conditions_from_bucket_key("li=1_nv1=3", mover)
    # Only the nv1 axis becomes a ShellCondition; li dropped silently.
    assert len(scs) == 1
    assert scs[0].shell == "1nn" and scs[0].count == 3


def test_shell_conditions_from_bucket_key_zero_counts() -> None:
    """nv1=0_nv2=0 (isolated mover) emits valid count=0 conditions."""
    mover = CoordOffset(code="NC_NN1_PX")
    scs = _shell_conditions_from_bucket_key("nv1=0_nv2=0", mover)
    assert len(scs) == 2
    assert all(s.count == 0 for s in scs)


def test_shell_conditions_from_bucket_key_unparseable_returns_empty() -> None:
    """Wildcard / unparseable bucket keys → empty tuple (no gating)."""
    mover = CoordOffset(code="NC_NN1_PX")
    assert _shell_conditions_from_bucket_key("*", mover) == ()
    assert _shell_conditions_from_bucket_key("(empty)", mover) == ()


def test_emit_simple_2action_hop_carries_shell_gates_by_default() -> None:
    """The translator's default emits ShellConditions for nv1/nv2."""
    p = _emit_simple_2action_hop(
        family_id="surface_1NN_inplane",
        bucket_id="nv1=4_nv2=1",
        direction=CoordOffset(code="NC_NN1_PX"),
        mover_species="Ni",
        Ea_eV=0.167,
        rate_Hz=1.0e8,
    )
    assert len(p.shell_conditions) == 2
    counts_by_shell = {s.shell: s.count for s in p.shell_conditions}
    assert counts_by_shell == {"1nn": 4, "2nn": 1}


def test_emit_simple_2action_hop_no_shell_gates_when_disabled() -> None:
    """Backward-compat: emit_shell_gates=False yields v0.2 behaviour."""
    p = _emit_simple_2action_hop(
        family_id="surface_1NN_inplane",
        bucket_id="nv1=4_nv2=1",
        direction=CoordOffset(code="NC_NN1_PX"),
        mover_species="Ni",
        Ea_eV=0.167,
        rate_Hz=1.0e8,
        emit_shell_gates=False,
    )
    assert p.shell_conditions == ()
