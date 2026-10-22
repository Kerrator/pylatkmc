"""tools/build_initial_config.py at scale (large-system-scaling/14).

The tool used to copy the positions into 9 xy images, run one
cKDTree.query_ball_point per site from a Python loop and pack the CSR from
per-edge Python lists: hours and tens of GB at 1e7 sites. It now builds the
slab with numpy and gets both neighbour shells from one periodic KD-tree pair
search, packed with numpy (`neighbour_csr`). Its output must not change. The
oracle is a frozen copy of the replaced tool (_legacy_build_initial_config.py =
tools/build_initial_config.py at fe64066), run under the same numpy, so these
checks do not depend on numpy's random stream:

- whole .kmcinit files and stdout of main(), over cell shapes (including 1- and
  2-site-wide cells, where a site is its own image neighbour or a neighbour is
  reachable through two images), compositions, vacancy counts and layers,
  adatom layers, vacuum, --element and 128 layers;
- the slab arrays and both CSRs, array for array (dtypes included), also with
  the pair search cut into many small batches;
- the per-site API that scripts importing the tool still call
  (compute_neighbors_with_pbc, classify_direction, adj_to_csr), which main()
  no longer uses;
- main() at 1e5 sites with that per-site API disabled: the written CSR has the
  FCC(100) structure, read in runtime/src/io/initconfig.c's layout.

layer_index is int8 in the .kmcinit (initconfig.c reads i8[N]). More than 128
layers raised OverflowError on NumPy 2 and wrapped silently on 1.x, corrupting
the site_class and vacancy masks. Such a slab is now refused: build_fcc100_slab
raises ValueError and the CLI exits with a one-line error. The existing nz /
vacuum / adatom argument errors are unchanged.

Needs numpy and scipy (scipy is only in the [ingest] extra): skipped without.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
TOOLS = REPO_ROOT / "tools"
LEGACY = Path(__file__).resolve().parent / "_legacy_build_initial_config.py"
NN_DIST = 3.524 / np.sqrt(2.0)  # A_LATTICE["Ni"] / sqrt(2), as main() computes it
R2_FACTOR = np.sqrt(2.0) * 1.05  # main()'s 2NN cutoff factor (1NN: 1.1)


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tools() -> tuple[ModuleType, ModuleType]:
    """(the tool, its frozen pre-change copy); both import kmcfmt from tools/."""
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(TOOLS))
        return _load(TOOLS / "build_initial_config.py", "bic_new"), _load(LEGACY, "bic_legacy")


def _run(module: ModuleType, args: str, out: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "argv", ["build_initial_config.py", *args.split(), "-o", str(out)])
    return module.main()


def _same_arrays(got: tuple, want: tuple, what: str) -> None:
    assert len(got) == len(want), what
    for g, w in zip(got, want):
        assert g.dtype == w.dtype, f"{what}: dtype {g.dtype} != {w.dtype}"
        assert g.shape == w.shape, f"{what}: shape {g.shape} != {w.shape}"
        assert g.tobytes() == w.tobytes(), f"{what}: contents differ"


def _legacy_csr(legacy: ModuleType, positions, cell) -> tuple:
    """The replaced main()'s neighbour block: two per-site searches, the 1NN
    removed from the 2NN, first image per neighbour, sorted, packed."""
    adj1 = legacy.compute_neighbors_with_pbc(positions, cell, NN_DIST, 1.1)
    adj2_raw = legacy.compute_neighbors_with_pbc(positions, cell, NN_DIST, R2_FACTOR)
    adj2 = []
    for nn1, raw in zip(adj1, adj2_raw):
        nn1_set = {j for j, _ in nn1}
        adj2.append([(j, d) for j, d in raw if j not in nn1_set])

    def classify(d):
        return legacy.classify_direction(d, NN_DIST)

    return legacy.adj_to_csr(adj1, classify), legacy.adj_to_csr(adj2, classify)


# ---------------------------------------------------------------------------
# Byte identity of the CLI
# ---------------------------------------------------------------------------

CLI_CASES = {
    "defaults_3x3x3": "--nx 3 --ny 3",
    # compare_golden.sh's three recorded build commands
    "golden_bases_30x30x12": "--nx 30 --ny 30 --nz 12 --n-vacancies 0 --vacuum-layers 8 --seed 1",
    "golden_nicr_8x8_periodic": (
        "--nx 8 --ny 8 --nz 10 --composition Ni90_Cr10 --n-vacancies 2 --vacuum-layers 8 --seed 7"
    ),
    "golden_nicr_random": (
        "--nx 10 --ny 10 --nz 10 --composition Ni90_Cr10 --n-vacancies 4 --vacuum-layers 8 --seed 7"
    ),
    # models/ni_example/README.md and the two shipped 6x6x4 example slabs
    "readme_6x6x4": "--nx 6 --ny 6 --nz 4 --element Ni --n-vacancies 5 --vacuum-layers 1",
    "ni_example_slab": "--nx 6 --ny 6 --nz 4 --n-vacancies 1 --vacuum-layers 1.0 --seed 42",
    "ni_dissolution_demo_slab": "--nx 6 --ny 6 --nz 4 --n-vacancies 0 --vacuum-layers 1.0",
    # every in-plane neighbour is the site itself
    "one_site_cell_1x1": "--nx 1 --ny 1 --nz 3 --n-vacancies 0",
    "one_wide_1x5_adatoms": "--nx 1 --ny 5 --nz 4 --n-adatom-layers 2",
    "one_wide_4x1_vacuum": "--nx 4 --ny 1 --nz 5 --vacuum-layers 2.5 --n-vacancies 2",
    # each in-plane neighbour reachable through two images
    "two_site_cell_2x2": "--nx 2 --ny 2 --nz 5 --n-vacancies 3 --composition Ni50_Fe50 --seed 3",
    "two_wide_2x5_adatoms": (
        "--nx 2 --ny 5 --nz 3 --n-adatom-layers 3 --vacuum-layers 8 --n-vacancies 2"
    ),
    "vacancy_layer_3x3": "--nx 3 --ny 3 --nz 6 --n-adatom-layers 3 --vacancy-layer 5 --n-vacancies 2",
    "ternary_vacancy_layer": (
        "--nx 5 --ny 7 --nz 6 --n-adatom-layers 3 --vacancy-layer 4 --n-vacancies 3 "
        "--composition Ni0.8_Fe0.1_Cr0.1 --seed 11"
    ),
    "ternary_12x9_adatoms_vacuum": (
        "--nx 12 --ny 9 --nz 7 --composition Ni0.9_Fe0.05_Cr0.05 --n-vacancies 5 "
        "--n-adatom-layers 3 --vacuum-layers 6 --seed 11"
    ),
    "element_fe": "--nx 6 --ny 5 --nz 4 --element Fe --n-vacancies 2",
    "no_vacuum_binary": "--nx 7 --ny 3 --nz 5 --composition Fe1_Cr1 --n-vacancies 9 --seed 3",
    "fractional_vacuum": "--nx 4 --ny 6 --nz 5 --vacuum-layers 0.37 --n-vacancies 4 --seed 5",
    # 128 layers: layer_index 0..127, the int8 limit, still accepted
    "max_128_layers_adatoms": (
        "--nx 4 --ny 4 --nz 125 --n-adatom-layers 3 --composition Ni70_Cr30 --seed 9"
    ),
    "max_128_layers_2x3": "--nx 2 --ny 3 --nz 128",
}


@pytest.mark.parametrize("args", CLI_CASES.values(), ids=CLI_CASES.keys())
def test_kmcinit_and_stdout_are_byte_identical_to_the_replaced_tool(
    tools: tuple[ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: str,
) -> None:
    new, legacy = tools
    out = tmp_path / "slab.kmcinit"  # the same path for both: stdout names it
    capsys.readouterr()
    assert _run(legacy, args, out, monkeypatch) == 0
    want_bytes, want_stdout = out.read_bytes(), capsys.readouterr().out
    out.unlink()
    assert _run(new, args, out, monkeypatch) == 0
    assert out.read_bytes() == want_bytes
    assert capsys.readouterr().out == want_stdout


# ---------------------------------------------------------------------------
# Array-level identity: slab builder and neighbour_csr
# ---------------------------------------------------------------------------

# (nx, ny, nz, vacuum_layers, n_adatom_layers)
SHAPES = [
    (1, 1, 3, 0.0, 0),  # every in-plane neighbour is the site itself
    (1, 4, 3, 0.0, 2),
    (4, 1, 5, 2.5, 0),
    (2, 2, 4, 0.0, 1),  # each in-plane neighbour reachable through 2 images
    (2, 5, 3, 8.0, 3),
    (3, 3, 3, 0.0, 0),
    (3, 7, 6, 1.0, 3),
    (6, 6, 4, 1.0, 0),  # the shipped ni_example / ni_dissolution_demo slabs
    (8, 5, 10, 0.37, 2),
    (2, 3, 125, 0.0, 3),  # 128 layers
]


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: "x".join(map(str, s)))
def test_slab_and_neighbour_csr_match_the_replaced_search(
    tools: tuple[ModuleType, ModuleType], shape: tuple[int, int, int, float, int]
) -> None:
    new, legacy = tools
    nx, ny, nz, vacuum, adatom = shape
    slab = new.build_fcc100_slab(nx, ny, nz, NN_DIST, vacuum_layers=vacuum, n_adatom_layers=adatom)
    want = legacy.build_fcc100_slab(
        nx, ny, nz, NN_DIST, vacuum_layers=vacuum, n_adatom_layers=adatom
    )
    _same_arrays(slab, want, "slab (positions, layer_index, site_class, cell)")

    positions, _, _, cell = slab
    nn1, nn2 = new.neighbour_csr(positions, cell, NN_DIST, 1.1, R2_FACTOR)
    want_nn1, want_nn2 = _legacy_csr(legacy, positions, cell)
    _same_arrays(nn1, want_nn1, "1NN CSR (offsets, indices, dir_family)")
    _same_arrays(nn2, want_nn2, "2NN CSR (offsets, indices, dir_family)")


@pytest.mark.parametrize("batch", [1, 7, 64])
@pytest.mark.parametrize("shape", [(5, 4, 6, 1.5, 2), (1, 4, 3, 0.0, 2)], ids=["5x4", "1x4"])
def test_neighbour_csr_stitches_pair_batches(
    tools: tuple[ModuleType, ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    batch: int,
    shape: tuple[int, int, int, float, int],
) -> None:
    """Every slab above fits one 4M-pair batch; cut the pair list into many."""
    new, legacy = tools
    monkeypatch.setattr(new, "_PAIR_BATCH", batch)
    nx, ny, nz, vacuum, adatom = shape
    positions, _, _, cell = new.build_fcc100_slab(
        nx, ny, nz, NN_DIST, vacuum_layers=vacuum, n_adatom_layers=adatom
    )
    nn1, nn2 = new.neighbour_csr(positions, cell, NN_DIST, 1.1, R2_FACTOR)
    want_nn1, want_nn2 = _legacy_csr(legacy, positions, cell)
    _same_arrays(nn1, want_nn1, f"1NN CSR, batch {batch}")
    _same_arrays(nn2, want_nn2, f"2NN CSR, batch {batch}")


# ---------------------------------------------------------------------------
# The per-site API scripts import (main() no longer uses it)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "shape", [(3, 4, 4, 1), (2, 2, 3, 0), (1, 3, 3, 2)], ids=lambda s: "x".join(map(str, s))
)
def test_per_site_api_for_importers_is_unchanged(
    tools: tuple[ModuleType, ModuleType], shape: tuple[int, int, int, int]
) -> None:
    """Scripts load the tool with importlib and rebuild the CSR from the
    per-site lists, passing the slab arguments positionally and calling
        adj_to_csr(adj, lambda d: classify_direction(d, nn_dist))
    Same arrays as the replaced tool, and as neighbour_csr."""
    nx, ny, nz, adatom = shape
    per_site = []
    for module in tools:
        pos, _, _, cell = module.build_fcc100_slab(nx, ny, nz, NN_DIST, 0.0, adatom)
        a1 = module.compute_neighbors_with_pbc(pos, cell, NN_DIST, 1.1)
        a2r = module.compute_neighbors_with_pbc(pos, cell, NN_DIST, R2_FACTOR)
        a2 = [
            [(j, d) for j, d in a2r[s] if j not in {x for x, _ in a1[s]}] for s in range(len(pos))
        ]
        csr: tuple = ()
        for adj in (a1, a2):
            csr += module.adj_to_csr(adj, lambda d, m=module: m.classify_direction(d, NN_DIST))
        per_site.append(csr)
    new_csr, legacy_csr = per_site
    _same_arrays(new_csr, legacy_csr, "adj_to_csr over compute_neighbors_with_pbc")
    new, _ = tools
    pos, _, _, cell = new.build_fcc100_slab(nx, ny, nz, NN_DIST, 0.0, adatom)
    nn1, nn2 = new.neighbour_csr(pos, cell, NN_DIST, 1.1, R2_FACTOR)
    _same_arrays(nn1 + nn2, new_csr, "neighbour_csr vs the per-site path")


def test_classify_direction_is_the_scalar_form_of_classify_directions(
    tools: tuple[ModuleType, ModuleType],
) -> None:
    """One displacement in, a Python int out, equal to the replaced function
    on every lattice edge vector and on off-lattice vectors hitting each rule."""
    new, legacy = tools
    pos, _, _, cell = legacy.build_fcc100_slab(3, 3, 5, NN_DIST, 0.0, 1)
    lattice = [
        d
        for factor in (1.1, R2_FACTOR)
        for site in legacy.compute_neighbors_with_pbc(pos, cell, NN_DIST, factor)
        for _, d in site
    ]
    rng = np.random.default_rng(14)
    ls = NN_DIST / np.sqrt(2.0)
    grid = [
        np.array([dx * NN_DIST, dy * NN_DIST, dz * ls])
        for dx in (-1.5, -1.0, -0.5, 0.0, 0.05, 0.5, 1.0, 1.2)
        for dy in (-1.0, 0.0, 0.5, 1.0)
        for dz in (-2.0, -1.0, 0.0, 0.08, 0.5, 1.0, 2.0, 3.0)
    ]
    noisy = list(rng.normal(0.0, 1.5 * NN_DIST, size=(500, 3)))
    displacements = lattice + grid + noisy + [[0.0, NN_DIST, 0.0], (NN_DIST, NN_DIST, 0.0)]
    got = [new.classify_direction(d, NN_DIST) for d in displacements]
    assert all(type(df) is int for df in got)
    assert got == [legacy.classify_direction(d, NN_DIST) for d in displacements]
    stacked = np.array([np.asarray(d, dtype=np.float64) for d in displacements])
    assert new.classify_directions(stacked, NN_DIST).tolist() == got
    assert set(got) == {
        new.DF_110_INPLANE,
        new.DF_100_INPLANE,
        new.DF_111_INTERLAYER,
        new.DF_001_EXCHANGE,
        new.DF_UNRESOLVED,
    }


# ---------------------------------------------------------------------------
# main() at scale, without the per-site path
# ---------------------------------------------------------------------------


def _read_kmcinit(path: Path) -> dict:
    """Header + payload arrays, in runtime/src/io/initconfig.c's layout."""
    data = path.read_bytes()
    assert data[:8] == b"KMCICv01"
    header_bytes = int.from_bytes(data[8:12], "little")
    header = json.loads(data[12 : 12 + header_bytes].rstrip(b"\0"))
    n, m1, m2 = header["n_sites"], header["nn1_count"], header["nn2_count"]
    fields = [
        ("payload_version", "<u4", 1),
        ("positions", "<f4", 3 * n),
        ("nn1_offsets", "<i4", n + 1),
        ("nn1_indices", "<i4", m1),
        ("nn2_offsets", "<i4", n + 1),
        ("nn2_indices", "<i4", m2),
        ("layer_index", "i1", n),
        ("site_class", "u1", n),
        ("species", "u1", n),
        ("nn1_dir", "u1", m1),
        ("nn2_dir", "u1", m2),
    ]
    out: dict = {"header": header}
    off = 12 + header_bytes
    for name, dtype, count in fields:
        out[name] = np.frombuffer(data, dtype=dtype, count=count, offset=off)
        off += out[name].nbytes
    assert off == len(data), "payload size differs from what initconfig.c reads"
    return out


def test_main_builds_1e5_sites_without_the_per_site_path(
    tools: tuple[ModuleType, ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() must not fall back to the per-site search (kept only for
    importers and tools/xyz_to_kmcinit.py). The CSR it writes for a 1e5-site
    slab must have the FCC(100) slab structure."""
    new, _ = tools

    def per_site(*args: object, **kwargs: object) -> None:
        raise AssertionError("main() called the per-site neighbour path")

    for name in ("compute_neighbors_with_pbc", "adj_to_csr", "classify_direction"):
        monkeypatch.setattr(new, name, per_site)
    nx, ny, nz = 50, 50, 40
    out = tmp_path / "big.kmcinit"
    assert _run(new, f"--nx {nx} --ny {ny} --nz {nz} --n-vacancies 3", out, monkeypatch) == 0

    k = _read_kmcinit(out)
    n = k["header"]["n_sites"]
    assert n == nx * ny * nz
    layer = k["layer_index"]
    n1, n2 = np.diff(k["nn1_offsets"]), np.diff(k["nn2_offsets"])
    # 1NN: 4 in-plane + 4 per adjacent layer; 2NN: 4 in-plane + 1 per layer two away.
    assert set(n1[(layer > 0) & (layer < nz - 1)]) == {12}
    assert set(n1[(layer == 0) | (layer == nz - 1)]) == {8}
    assert set(n2[(layer > 1) & (layer < nz - 2)]) == {6}
    assert set(n2[(layer <= 1) | (layer >= nz - 2)]) == {5}
    assert set(k["nn1_dir"]) == {new.DF_110_INPLANE, new.DF_111_INTERLAYER}
    assert set(k["nn2_dir"]) == {new.DF_100_INPLANE, new.DF_001_EXCHANGE}
    for shell in ("nn1", "nn2"):
        offsets, indices = k[f"{shell}_offsets"], k[f"{shell}_indices"]
        rows = np.repeat(np.arange(n), np.diff(offsets))
        assert np.all(np.diff(indices)[np.diff(rows) == 0] > 0), f"{shell} rows not sorted"
        fwd = rows.astype(np.int64) * n + indices
        rev = indices.astype(np.int64) * n + rows
        assert np.array_equal(np.sort(fwd), np.sort(rev)), f"{shell} adjacency not symmetric"
    assert int((k["species"] == 0).sum()) == 3


# ---------------------------------------------------------------------------
# Layer limit (int8 layer_index) and the argument errors around it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("nz", "n_adatom"), [(129, 0), (126, 3), (300, 0)])
def test_more_than_128_layers_is_refused(
    tools: tuple[ModuleType, ModuleType], nz: int, n_adatom: int
) -> None:
    """Layer index 128+ does not fit the int8 layer_index: refuse, don't wrap."""
    new, _ = tools
    with pytest.raises(ValueError, match=r"at most 128: layer_index is stored as int8"):
        new.build_fcc100_slab(2, 2, nz, NN_DIST, n_adatom_layers=n_adatom)


def test_128_layers_is_the_maximum(tools: tuple[ModuleType, ModuleType]) -> None:
    new, _ = tools
    _, layer, site_class, _ = new.build_fcc100_slab(3, 3, 125, NN_DIST, n_adatom_layers=3)
    assert layer.dtype == np.int8 and layer.min() == 0 and layer.max() == 127
    assert set(site_class[layer == 124]) == {new.SC_SURFACE}
    assert set(site_class[layer == 123]) == {new.SC_SUBSURFACE}
    assert set(site_class[(layer < 123) | (layer > 124)]) == {new.SC_BULK_LIKE}


@pytest.mark.parametrize(
    "args", ["--nx 4 --ny 4 --nz 129", "--nx 3 --ny 3 --nz 125 --n-adatom-layers 4"]
)
def test_cli_refuses_more_than_128_layers_with_one_line(
    tools: tuple[ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: str,
) -> None:
    new, _ = tools
    out = tmp_path / "thick.kmcinit"
    with pytest.raises(SystemExit) as exc:
        _run(new, args, out, monkeypatch)
    message = str(exc.value.code)
    assert message.startswith("error: nz + n_adatom_layers = ")
    assert "129 layers, but a .kmcinit holds at most 128: layer_index is stored as int8" in message
    assert "\n" not in message
    assert not out.exists()


@pytest.mark.parametrize(
    "args",
    [
        "--nx 3 --ny 3 --nz 2",
        "--nx 3 --ny 3 --vacuum-layers -1",
        "--nx 3 --ny 3 --n-adatom-layers -1",
        # also when the slab would have more than 128 layers as well
        "--nx 3 --ny 3 --nz 2 --n-adatom-layers 200",
        "--nx 3 --ny 3 --nz 200 --vacuum-layers -1",
        "--nx 3 --ny 3 --nz 200 --n-adatom-layers -1",
    ],
)
def test_cli_argument_errors_are_unchanged(
    tools: tuple[ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: str,
) -> None:
    """The pre-existing nz / vacuum / adatom checks still raise the same
    ValueError (not the new one-line exit), before anything is written."""
    out = tmp_path / "bad.kmcinit"
    messages = []
    for module in tools:
        with pytest.raises(ValueError) as exc:
            _run(module, args, out, monkeypatch)
        messages.append(str(exc.value))
        assert not out.exists()
    assert messages[0] == messages[1]
