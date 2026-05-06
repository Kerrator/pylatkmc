"""Tests for the codegen pipeline: rendered files parse and match the spec.

Scope: M2 codegen. Does NOT invoke the C compiler (that's
test_codegen_compiles.py). Does NOT test the rate-data builder (M3).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pylatkmc import load
from pylatkmc.codegen import evaluate_template, generate, render_template_file
from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SPEC = REPO_ROOT / "models" / "ni_fe_cr_v1" / "ni_fe_cr_v1.kmcspec.toml"


@pytest.fixture(scope="module")
def spec() -> ModelSpec:
    return load(EXAMPLE_SPEC)


@pytest.fixture
def gen_dir(spec: ModelSpec, tmp_path: Path) -> Path:
    out = tmp_path / "generated"
    generate(spec, out)
    return out


# ------------------------------------------------------------------
# generate() writes the expected set of files
# ------------------------------------------------------------------
def test_generate_writes_five_files(gen_dir: Path) -> None:
    expected = {"events.h", "ratetable.h", "ratetable.c", "avail.c", "key_spec.json"}
    assert {p.name for p in gen_dir.iterdir()} == expected


def test_key_spec_json_matches_spec(gen_dir: Path, spec: ModelSpec) -> None:
    ks = json.loads((gen_dir / "key_spec.json").read_text())
    assert ks["name"] == spec.name
    assert ks["n_cube_entries"] == spec.n_cube_entries()
    assert len(ks["axes"]) == len(spec.all_axes())
    # Axis names, maxes, strides must round-trip.
    for got, (name, max_bin), stride in zip(
        ks["axes"], spec.all_axes(), spec.strides(), strict=True
    ):
        assert got["name"] == name
        assert got["max"] == max_bin
        assert got["stride"] == stride


# ------------------------------------------------------------------
# events.h has the right RateKey fields in the right order
# ------------------------------------------------------------------
def test_events_h_defines_ratekey_with_axis_order(gen_dir: Path, spec: ModelSpec) -> None:
    events_h = (gen_dir / "events.h").read_text()
    # Find the RateKey struct block.
    m = re.search(r"typedef struct RateKey \{([^}]*)\} RateKey;", events_h, re.DOTALL)
    assert m, "RateKey struct not found in generated events.h"
    block = m.group(1)
    # Extract uint8_t field names in declaration order.
    fields = re.findall(r"uint8_t\s+(\w+);", block)
    expected_names = [name for name, _ in spec.all_axes()]
    assert fields == expected_names


def test_events_h_has_model_constants(gen_dir: Path, spec: ModelSpec) -> None:
    events_h = (gen_dir / "events.h").read_text()
    assert f'"{spec.name}"' in events_h
    assert f"PYLATKMC_N_AXES     {len(spec.all_axes())}" in events_h
    assert f"PYLATKMC_CUBE_SIZE  {spec.n_cube_entries()}" in events_h


# ------------------------------------------------------------------
# ratetable.h: key function uses the right strides
# ------------------------------------------------------------------
def test_ratetable_h_has_strides_array_size(gen_dir: Path, spec: ModelSpec) -> None:
    r_h = (gen_dir / "ratetable.h").read_text()
    n_axes = len(spec.all_axes())
    assert f"int32_t  strides[{n_axes}];" in r_h
    assert f"int32_t  axis_maxes[{n_axes}];" in r_h


def test_ratetable_h_key_function_references_all_axes(
    gen_dir: Path, spec: ModelSpec
) -> None:
    r_h = (gen_dir / "ratetable.h").read_text()
    for name, _ in spec.all_axes():
        assert f"k->{name}" in r_h, f"ratetable_key body missing axis '{name}'"


# ------------------------------------------------------------------
# ratetable.c: expected shape constants
# ------------------------------------------------------------------
def test_ratetable_c_has_axis_maxes_and_entries(gen_dir: Path, spec: ModelSpec) -> None:
    r_c = (gen_dir / "ratetable.c").read_text()
    for _, max_bin in spec.all_axes():
        # Each max shows up at least once in the EXPECTED_AXIS_MAXES initializer.
        assert str(max_bin) in r_c
    assert f"EXPECTED_N_ENTRIES = {spec.n_cube_entries()}" in r_c


# ------------------------------------------------------------------
# avail.c: species counters emitted for each shell
# ------------------------------------------------------------------
def test_avail_c_has_per_shell_counters(gen_dir: Path, spec: ModelSpec) -> None:
    a_c = (gen_dir / "avail.c").read_text()
    for shell in ("nn1", "nn2"):
        assert f"scan_{shell}" in a_c
        for elem in spec.counted_species_in_shell(shell):
            assert f"n_{elem}" in a_c, f"avail.c missing counter n_{elem} for {shell}"


def test_avail_c_references_mover_species_map(gen_dir: Path, spec: ModelSpec) -> None:
    a_c = (gen_dir / "avail.c").read_text()
    assert "MOVER_SP_IDX" in a_c
    # Non-vacant species all should appear in the initializer.
    for i, sp_name in enumerate(spec.species[1:]):
        token = f"[SP_{sp_name.upper()}] = {i},"
        assert token in a_c, f"MOVER_SP_IDX missing {token}"


# ------------------------------------------------------------------
# render_template_file() exposes per-file rendering for debugging
# ------------------------------------------------------------------
def test_render_single_template(spec: ModelSpec) -> None:
    out = render_template_file("events.h", spec)
    assert "typedef struct RateKey" in out
    assert "PYLATKMC_EVENTS_H" in out


# ------------------------------------------------------------------
# evaluate_template used directly with simple contexts (sanity)
# ------------------------------------------------------------------
def test_evaluate_template_integrates_with_spec(spec: ModelSpec) -> None:
    tmpl = (
        "for name, max_bin in spec.all_axes():\n"
        "    #@ axis {name} max {max_bin}\n"
    )
    out = evaluate_template(tmpl, spec=spec)
    assert "axis site_class max 3\n" in out
    assert "axis direction max 5\n" in out
    # The last axis in the example spec is n_Cr_nn2 with max 5.
    assert out.rstrip().endswith("axis n_Cr_nn2 max 5")


# ------------------------------------------------------------------
# Alternative shaped specs render cleanly too
# ------------------------------------------------------------------
def _minimal_spec() -> ModelSpec:
    return ModelSpec(
        name="tiny",
        lattice="fcc",
        species=["Vacant", "Ni"],
        shells=[Shell(name="nn1", cutoff_mult=1.05)],
        key=Key(axes=[
            KeyAxis(name="n_vac_nn1", kind="count", shell="nn1", match="vac", max=3),
        ]),
        rate_data=RateData(
            primary=Path("/tmp/primary.csv"),
            temperature_K=500.0,
            k0_Hz=1e13,
        ),
    )


def test_minimal_spec_generates_single_axis_key(tmp_path: Path) -> None:
    spec = _minimal_spec()
    out = tmp_path / "gen"
    generate(spec, out)
    events_h = (out / "events.h").read_text()
    # RateKey has permanent two axes + the one user-axis.
    m = re.search(r"typedef struct RateKey \{([^}]*)\} RateKey;", events_h, re.DOTALL)
    assert m
    fields = re.findall(r"uint8_t\s+(\w+);", m.group(1))
    assert fields == ["site_class", "direction", "n_vac_nn1"]
