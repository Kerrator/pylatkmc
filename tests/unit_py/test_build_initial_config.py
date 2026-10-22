"""tools/build_initial_config.py at scale (large-system-scaling/14).

The per-site neighbour loop (9 xy image copies, one cKDTree.query_ball_point
call per site, a CSR built from Python lists) is replaced by one periodic
cKDTree pass packed with numpy. The .kmcinit must not change: each case runs
the tool and the frozen pre-change copy (_legacy_build_initial_config.py, the
tool at fe64066) with the same arguments and compares the files byte for byte,
over cell shapes (incl. two-site-wide cells, where a neighbour is reachable
through two periodic images), compositions, vacancy counts and layers, adatom
layers and vacuum. Plus the input limits: layer_index is int8 in the format
(runtime/src/io/initconfig.c), so more than 128 layers must fail loudly instead
of wrapping (NumPy 1.x) or raising an opaque OverflowError (NumPy 2.x); and a
one-site-wide cell, where every site is its own in-plane neighbour, is refused.

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


CASES = {
    "defaults_3x3x3": "--nx 3 --ny 3",
    "golden_nicr_random": (
        "--nx 10 --ny 10 --nz 10 --composition Ni90_Cr10 --n-vacancies 4 --vacuum-layers 8 --seed 7"
    ),
    "golden_nicr_8x8": (
        "--nx 8 --ny 8 --nz 10 --composition Ni90_Cr10 --n-vacancies 2 --vacuum-layers 8 --seed 7"
    ),
    "readme_6x6x4": "--nx 6 --ny 6 --nz 4 --element Ni --n-vacancies 5 --vacuum-layers 1",
    "two_site_cell": "--nx 2 --ny 2 --nz 4 --n-vacancies 0",
    "two_wide_adatoms": (
        "--nx 2 --ny 5 --nz 3 --n-adatom-layers 2 --vacuum-layers 2.5 --n-vacancies 2"
    ),
    "ternary_vacancy_layer": (
        "--nx 5 --ny 7 --nz 6 --n-adatom-layers 3 --vacancy-layer 4 --n-vacancies 3 "
        "--composition Ni0.8_Fe0.1_Cr0.1 --seed 11"
    ),
    "no_vacuum": "--nx 7 --ny 3 --nz 5 --composition Fe1_Cr1 --n-vacancies 9 --seed 3",
    "adatoms_12x9": (
        "--nx 12 --ny 9 --nz 7 --n-adatom-layers 1 --composition Ni95_Fe5 --n-vacancies 6 --seed 5"
    ),
    "max_128_layers": "--nx 3 --ny 3 --nz 125 --n-adatom-layers 3",
}


@pytest.mark.parametrize("args", CASES.values(), ids=CASES.keys())
def test_kmcinit_is_byte_identical_to_the_per_site_loop(
    tools: tuple[ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: str,
) -> None:
    new, legacy = tools
    assert _run(legacy, args, tmp_path / "legacy.kmcinit", monkeypatch) == 0
    assert _run(new, args, tmp_path / "new.kmcinit", monkeypatch) == 0
    expected = (tmp_path / "legacy.kmcinit").read_bytes()
    assert (tmp_path / "new.kmcinit").read_bytes() == expected


def _legacy_csr(legacy: ModuleType, positions, cell) -> tuple:
    """The pre-change main()'s neighbour block: two per-site searches, the 1NN
    removed from the 2NN, first image per neighbour, sorted, packed."""
    adj1 = legacy.compute_neighbors_with_pbc(positions, cell, NN_DIST, 1.1)
    adj2_raw = legacy.compute_neighbors_with_pbc(positions, cell, NN_DIST, np.sqrt(2.0) * 1.05)
    adj2 = []
    for nn1, raw in zip(adj1, adj2_raw):
        nn1_set = {j for j, _ in nn1}
        adj2.append([(j, d) for j, d in raw if j not in nn1_set])

    def classify(d):
        return legacy.classify_direction(d, NN_DIST)

    return (*legacy.adj_to_csr(adj1, classify), *legacy.adj_to_csr(adj2, classify))


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


@pytest.mark.parametrize("chunk", [1, 7, 64, 1 << 16])
def test_chunked_neighbour_search_matches_the_per_site_loop(
    tools: tuple[ModuleType, ModuleType], chunk: int
) -> None:
    """The byte-identity cases fit in one query chunk; stitch several here."""
    new, legacy = tools
    positions, _, _, cell = new.build_fcc100_slab(
        5, 4, 6, NN_DIST, vacuum_layers=1.5, n_adatom_layers=2
    )
    got = new.compute_neighbor_csr(positions, cell, NN_DIST, chunk=chunk)
    expected = _legacy_csr(legacy, positions, cell)
    assert len(got) == len(expected) == 6
    for g, e in zip(got, expected):
        assert g.dtype == e.dtype
        assert np.array_equal(g, e)


def test_build_path_has_no_per_site_loop(
    tools: tuple[ModuleType, ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() must not fall back to the per-site loop (kept only for
    xyz_to_kmcinit.py). A 1e5-site slab spans two query chunks; the CSR it
    writes must have the FCC(100) slab structure."""
    new, _ = tools

    def per_site_loop(*args: object, **kwargs: object) -> None:
        raise AssertionError("main() called the per-site neighbour loop")

    monkeypatch.setattr(new, "compute_neighbors_with_pbc", per_site_loop)
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
    assert new.DF_UNRESOLVED not in set(k["nn1_dir"]) | set(k["nn2_dir"])
    for shell in ("nn1", "nn2"):
        offsets, indices = k[f"{shell}_offsets"], k[f"{shell}_indices"]
        rows = np.repeat(np.arange(n), np.diff(offsets))
        assert np.all(np.diff(indices)[np.diff(rows) == 0] > 0), f"{shell} rows not sorted"
        fwd = rows.astype(np.int64) * n + indices
        rev = indices.astype(np.int64) * n + rows
        assert np.array_equal(np.sort(fwd), np.sort(rev)), f"{shell} adjacency not symmetric"
    assert int((k["species"] == 0).sum()) == 3


def test_more_than_128_layers_fail_loudly(
    tools: tuple[ModuleType, ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """layer_index is int8: 128 layers (indices 0..127) is the maximum."""
    new, _ = tools
    for nz, n_adatom in ((126, 3), (129, 0), (300, 0)):
        with pytest.raises(ValueError, match="at most 128 layers"):
            new.build_fcc100_slab(3, 3, nz, NN_DIST, n_adatom_layers=n_adatom)
    _, layer, site_class, _ = new.build_fcc100_slab(3, 3, 125, NN_DIST, n_adatom_layers=3)
    assert layer.dtype == np.int8 and layer.min() == 0 and layer.max() == 127
    assert set(site_class[layer == 124]) == {new.SC_SURFACE}
    assert set(site_class[layer == 123]) == {new.SC_SUBSURFACE}
    assert set(site_class[(layer < 123) | (layer > 124)]) == {new.SC_BULK_LIKE}
    out = tmp_path / "thick.kmcinit"
    with pytest.raises(SystemExit, match="layer_index as int8"):
        _run(new, "--nx 3 --ny 3 --nz 140", out, monkeypatch)
    assert not out.exists()


@pytest.mark.parametrize(("nx", "ny"), [(1, 4), (4, 1)])
def test_one_site_wide_cell_is_refused(
    tools: tuple[ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nx: int,
    ny: int,
) -> None:
    """The per-site loop wrote every site as its own in-plane neighbour here."""
    new, _ = tools
    out = tmp_path / "narrow.kmcinit"
    with pytest.raises(SystemExit, match=r"nx, ny >= 2"):
        _run(new, f"--nx {nx} --ny {ny} --nz 3", out, monkeypatch)
    assert not out.exists()
