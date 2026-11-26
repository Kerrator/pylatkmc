"""Exercise the real emitter, CMake runtime and BKL draws on a small synthetic model."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pylatkmc import codegen, load
from pylatkmc.processes import Action, Condition, CoordOffset, Process, ShellCondition

ROOT = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).parent
EXAMPLE = ROOT / "models/ni_example"
SLAB = EXAMPLE / "examples/slab_ni_1vac.kmcinit"
MODEL = "test_replay"
BUILD_HASH = "public-replay-test"


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    source = tmp_path_factory.mktemp("source")
    shutil.copy(ROOT / "CMakeLists.txt", source)
    for name in ("runtime", "tools"):
        (source / name).symlink_to(ROOT / name, target_is_directory=True)

    # Only the Ni example's spec metadata and small slab are used. These five
    # processes exercise local hops, changes of occupancy, a nonlocal read,
    # and a first-neighbor shell around a second-neighbor center.
    anchor, px, read, center = (
        CoordOffset(code=f"NC_{name}")
        for name in ("ANCHOR", "NN1_PX", "NN2_DIAG_PP", "NN2_DIAG_MM")
    )

    def process(name, rate, conditions, actions, shells=()):
        return Process(
            name=name,
            family_id=name,
            Ea_eV=0,
            rate_constant=rate,
            prefactor_Hz=rate,
            conditions=tuple(Condition(coord=c, species=s) for c, s in conditions),
            actions=tuple(Action(coord=c, before=b, after=a) for c, b, a in actions),
            shell_conditions=shells,
        )

    shell = ShellCondition(coord=center, shell="1nn", species="Fe", count=2)
    processes = [
        process("label", 1, [(anchor, "Ni")], [(anchor, "Ni", "Fe")]),
        process("unlabel", 2, [(anchor, "Fe"), (read, "Ni")], [(anchor, "Fe", "Ni")]),
        process("remove", 0.5, [(anchor, "Fe")], [(anchor, "Fe", "Vacant")], (shell,)),
        process("insert", 0.2, [(anchor, "Vacant")], [(anchor, "Vacant", "Ni")]),
        process(
            "hop",
            1,
            [(anchor, "Vacant"), (px, "Ni")],
            [(anchor, "Vacant", "Ni"), (px, "Ni", "Vacant")],
        ),
    ]
    generated = source / "models" / MODEL / "generated"
    generated.mkdir(parents=True)
    spec = load(EXAMPLE / "ni_example.kmcspec.toml")
    (generated / "proclist.c").write_text(codegen._build_proclist_c(processes, spec))
    (generated / "proclist.h").write_text(codegen._build_proclist_h(spec))
    return source


def test_emitter_reach_and_unmodelled_reads(source, tmp_path):
    """Every shell/read dependency must enter the template or refuse the build."""
    script = ROOT / "tools/gen_reach_template.py"
    original = source / "models" / MODEL / "generated/proclist.c"
    header = tmp_path / "pt_reach_template.h"

    def generate(path):
        return subprocess.run(
            [sys.executable, str(script), str(path), str(header)], capture_output=True, text=True
        )

    result = generate(original)
    assert result.returncode == 0, result.stderr
    text = header.read_text()
    assert "PT_READ_CODES[] = { NC_NN1_PX, NC_NN2_DIAG_PP }" in text
    assert "PT_SHELL_CODES[] = { NC_NN2_DIAG_MM }" in text

    marker = "void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {"
    assert original.read_text().count(marker) == 1
    unknown = tmp_path / "unmodelled.c"
    unknown.write_text(original.read_text().replace(marker, marker + "\n    if (st->step) return;"))
    result = generate(unknown)
    assert result.returncode != 0 and "cannot model" in result.stderr
    assert not header.exists()

    result = generate(EXAMPLE / "generated/proclist.c")
    assert result.returncode != 0 and "nn2" in result.stderr
    assert not header.exists()


@pytest.fixture(scope="module")
def builds(source, tmp_path_factory):
    if not shutil.which("cmake") or not shutil.which("mpicc"):
        pytest.skip("CMake and an MPI C compiler are required")
    result = {}
    for mode in ("full", "ordered"):
        build = tmp_path_factory.mktemp(mode)
        options = []
        if mode == "ordered":
            options = [
                "-DPYLATKMC_INCREMENTAL=ON",
                "-DPYLATKMC_REPLAY_ORDER=ON",
                "-DPYLATKMC_INCREMENTAL_ORACLE=ON",
                f"-DPYLATKMC_BUILD_HASH={BUILD_HASH}",
            ]
        subprocess.run(
            ["cmake", "-S", str(source), "-B", str(build), f"-DMODEL={MODEL}", *options], check=True
        )
        subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], check=True)
        result[mode] = build
    return result


def test_seeded_outputs_and_provenance(builds, tmp_path):
    outputs = {}
    for mode, build in builds.items():
        work = tmp_path / mode
        work.mkdir()
        # Use relative input and output paths, including with spaces in tmp_path.
        (work / "slab.kmcinit").symlink_to(SLAB)
        (work / "input.ini").write_text(
            "[run]\nmax_steps=256\nsample_every=1\nbase_seed=19\n"
            "[paths]\ninitconfig_path=slab.kmcinit\noutput_root=.\n"
            "[physics]\ntemperature_K=500\nmax_dissolution_events=256\n"
        )
        binary = build / f"pylatkmc_{MODEL}"
        subprocess.run([str(binary), "input.ini"], cwd=work, check=True)
        outputs[mode] = work
        if mode == "ordered":
            manifest = (build / "BUILD-MANIFEST.txt").read_text().splitlines()
            assert f"commit: {BUILD_HASH}" in manifest
            assert "PYLATKMC_REPLAY_ORDER: ON" in manifest
            assert "PYLATKMC_INCREMENTAL_ORACLE: ON" in manifest
            assert f"binary_sha256: {hashlib.sha256(binary.read_bytes()).hexdigest()}" in manifest
        else:
            assert not (build / "BUILD-MANIFEST.txt").exists()

    for name in ("replica_0000/trajkmc.xyz", "replica_0000/pykmc.out"):
        assert (outputs["ordered"] / name).read_bytes() == (outputs["full"] / name).read_bytes()
    for name in ("replica_0000/summary.json", "aggregate_summary.json"):
        expected = json.loads((outputs["full"] / name).read_text())
        actual = json.loads((outputs["ordered"] / name).read_text())
        assert actual.pop("rebuild_mode") == "incremental_replay_order"
        assert actual.pop("build_hash") == BUILD_HASH
        if name == "replica_0000/summary.json":
            assert actual.pop("oracle_checks") == 256
            assert actual.pop("oracle_failures") == 0
        assert actual == expected
    summary = json.loads((outputs["full"] / "replica_0000/summary.json").read_text())
    assert (summary["n_steps"], summary["run_rc"]) == (256, 0)


def build_driver(source, build, name, flags):
    exe = build / name
    core = source / "runtime/src/core"
    subprocess.run(
        [
            "mpicc",
            "-std=c11",
            *flags,
            "-I",
            str(core),
            "-I",
            str(source / "runtime/src/io"),
            "-I",
            str(source / "models" / MODEL / "generated"),
            str(TESTS / f"_{name}.c"),
            str(build / "libpylatkmc_lib.a"),
            "-lm",
            "-o",
            str(exe),
        ],
        check=True,
    )
    return exe


def test_exact_draws_and_all_slots(source, builds):
    traces = {}
    for mode, build in builds.items():
        flags = (
            []
            if mode == "full"
            else [
                "-DPYLATKMC_INCREMENTAL",
                "-DPYLATKMC_REPLAY_ORDER",
                "-DPYLATKMC_INCREMENTAL_ORACLE",
            ]
        )
        driver = build_driver(source, build, "replay_draws", flags)
        traces[mode] = subprocess.check_output([str(driver), str(SLAB)]).splitlines()
        if mode == "ordered":
            slots = build_driver(source, build, "replay_slots", flags)
            subprocess.run([str(slots)], check=True)
    assert len(traces["full"]) == 800
    assert traces["ordered"] == traces["full"]
    assert len({row.split()[0] for row in traces["full"]}) == 5
