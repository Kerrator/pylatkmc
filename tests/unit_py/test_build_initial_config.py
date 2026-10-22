"""tools/build_initial_config.py at scale (large-system-scaling/14).

The tool used to copy the positions into 9 xy images, run one
cKDTree.query_ball_point per site from a Python loop and pack the CSR from
per-edge Python lists: hours and tens of GB at 1e7 sites. It now does one
periodic KD-tree pair search plus numpy-only CSR packing (`neighbour_csr`) and
builds the slab without a per-site loop. Its output must stay byte-identical:

- the slab builder and `neighbour_csr` are compared, array for array, with
  verbatim copies of the routines they replaced (the oracle below), on shapes
  that include 1- and 2-site-wide cells (one neighbour reachable through
  several images; a site its own image neighbour) and 128 layers;
- whole `.kmcinit` files written by the CLI are compared with the shipped
  example slabs and with SHA-256 digests of the replaced tool's output
  (b4bad8a / fe64066) over shapes, compositions, vacancy counts, adatom layers
  and vacuum, which also pins the species and vacancy RNG draw sequence.

`layer_index` is int8 in the `.kmcinit` (`runtime/src/io/initconfig.c` reads
i8[N]). More than 128 layers (an index above 127) raised OverflowError on
NumPy 2 and wrapped silently on 1.x, corrupting the site_class and vacancy
masks; such a slab is now refused with a ValueError that names the limit.

Needs numpy and scipy (scipy is only in the [ingest] extra): skipped without.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

np = pytest.importorskip("numpy")
cKDTree = pytest.importorskip("scipy.spatial").cKDTree

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
TOOLS = REPO_ROOT / "tools"
NN_DIST = 3.524 / np.sqrt(2.0)  # Ni, as main() computes it


@pytest.fixture(scope="module")
def bic() -> ModuleType:
    """tools/build_initial_config.py, loaded by path (it imports its sibling kmcfmt)."""
    sys.path.insert(0, str(TOOLS))
    try:
        spec = importlib.util.spec_from_file_location(
            "_build_initial_config_tool", TOOLS / "build_initial_config.py"
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(TOOLS))
    return mod


# ---------------------------------------------------------------------------
# Oracle: the replaced implementation, verbatim (tools/build_initial_config.py
# @ fe64066: build_fcc100_slab's loop, compute_neighbors_with_pbc,
# classify_direction, adj_to_csr and main()'s 1NN/2NN assembly).
# ---------------------------------------------------------------------------


def _ref_build_fcc100_slab(nx, ny, nz, nn_dist, vacuum_layers=0.0, n_adatom_layers=0):
    ls = nn_dist / np.sqrt(2.0)
    nz_total = nz + n_adatom_layers
    sites = []
    for k in range(nz_total):
        dx = 0.5 * nn_dist if (k % 2 == 1) else 0.0
        dy = 0.5 * nn_dist if (k % 2 == 1) else 0.0
        for i in range(nx):
            for j in range(ny):
                x = i * nn_dist + dx
                y = j * nn_dist + dy
                z = k * ls
                sites.append((x, y, z, k))
    positions = np.array([(s[0], s[1], s[2]) for s in sites], dtype=np.float32)
    layer_index = np.array([s[3] for s in sites], dtype=np.int8)
    top = nz - 1
    site_class = np.full(len(sites), 2, dtype=np.uint8)
    site_class[layer_index == top] = 0
    site_class[layer_index == top - 1] = 1
    cell = np.array([nx * nn_dist, ny * nn_dist, (nz_total + vacuum_layers) * ls], dtype=np.float32)
    return positions, layer_index, site_class, cell


def _ref_compute_neighbors_with_pbc(positions, cell, nn_dist, cutoff_factor):
    n = len(positions)
    cell_arr = np.asarray(cell, dtype=np.float64)
    offsets = [
        (ox, oy, 0.0)
        for ox in (-cell_arr[0], 0.0, cell_arr[0])
        for oy in (-cell_arr[1], 0.0, cell_arr[1])
    ]
    images = np.vstack([positions + np.array(o, dtype=np.float64) for o in offsets])
    tree = cKDTree(images)
    cutoff = cutoff_factor * nn_dist
    out = [[] for _ in range(n)]
    eps2 = 1e-8
    for i in range(n):
        p = positions[i].astype(np.float64)
        hits = tree.query_ball_point(p, cutoff)
        for h in hits:
            disp = images[h] - p
            if disp.dot(disp) < eps2:
                continue
            j = h % n
            out[i].append((j, disp))
    return out


def _ref_classify_direction(disp, nn_dist):
    dx, dy, dz = float(disp[0]), float(disp[1]), float(disp[2])
    d_xy = np.hypot(dx, dy)
    ls = nn_dist / np.sqrt(2.0)
    tol = 0.1 * nn_dist
    if abs(dz) < tol:
        if abs(d_xy - nn_dist) < tol:
            return 0
        if abs(d_xy - np.sqrt(2.0) * nn_dist) < tol:
            return 1
        return 4
    if abs(abs(dz) - ls) < tol:
        return 2
    if abs(abs(dz) - 2 * ls) < tol and d_xy < tol:
        return 3
    return 4


def _ref_adj_to_csr(adj, classify_dir):
    n = len(adj)
    offsets = np.zeros(n + 1, dtype=np.int32)
    all_items = []
    for s, items in enumerate(adj):
        seen = {}
        for j, disp in items:
            df = classify_dir(disp)
            if j in seen:
                continue
            seen[j] = df
        sorted_neighbors = sorted(seen.items())
        offsets[s + 1] = offsets[s] + len(sorted_neighbors)
        all_items.extend(sorted_neighbors)
    indices = np.array([it[0] for it in all_items], dtype=np.int32)
    dir_family = np.array([it[1] for it in all_items], dtype=np.uint8)
    return offsets, indices, dir_family


def _ref_neighbour_csr(positions, cell, nn_dist):
    adj_1nn = _ref_compute_neighbors_with_pbc(positions, cell, nn_dist, 1.1)
    adj_2nn_raw = _ref_compute_neighbors_with_pbc(positions, cell, nn_dist, np.sqrt(2.0) * 1.05)
    adj_2nn = []
    for s in range(len(positions)):
        nn1_set = {j for j, _ in adj_1nn[s]}
        adj_2nn.append([(j, d) for j, d in adj_2nn_raw[s] if j not in nn1_set])

    def classifier(d):
        return _ref_classify_direction(d, nn_dist)

    return _ref_adj_to_csr(adj_1nn, classifier), _ref_adj_to_csr(adj_2nn, classifier)


def _assert_same_arrays(got, want, what: str) -> None:
    for g, w in zip(got, want):
        assert g.dtype == w.dtype, f"{what}: dtype {g.dtype} != {w.dtype}"
        assert g.shape == w.shape, f"{what}: shape {g.shape} != {w.shape}"
        assert g.tobytes() == w.tobytes(), f"{what}: contents differ"


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
    (8, 5, 10, 8.0, 2),
    (2, 3, 125, 0.0, 3),  # 128 layers: the int8 layer_index limit, still accepted
]


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: "x".join(map(str, s)))
def test_slab_and_neighbour_lists_match_the_replaced_search(
    bic: ModuleType, shape: tuple[int, int, int, float, int]
) -> None:
    nx, ny, nz, vacuum, adatom = shape
    slab = bic.build_fcc100_slab(nx, ny, nz, NN_DIST, vacuum_layers=vacuum, n_adatom_layers=adatom)
    ref_slab = _ref_build_fcc100_slab(
        nx, ny, nz, NN_DIST, vacuum_layers=vacuum, n_adatom_layers=adatom
    )
    _assert_same_arrays(slab, ref_slab, "slab (positions, layer_index, site_class, cell)")

    positions, _, _, cell = slab
    nn1, nn2 = bic.neighbour_csr(positions, cell, NN_DIST, 1.1, np.sqrt(2.0) * 1.05)
    ref_nn1, ref_nn2 = _ref_neighbour_csr(positions, cell, NN_DIST)
    _assert_same_arrays(nn1, ref_nn1, "1NN CSR (offsets, indices, dir_family)")
    _assert_same_arrays(nn2, ref_nn2, "2NN CSR (offsets, indices, dir_family)")


def _run_cli(bic: ModuleType, monkeypatch: pytest.MonkeyPatch, args: str, out: Path) -> bytes:
    monkeypatch.setattr(sys, "argv", ["build_initial_config.py", *args.split(), "-o", str(out)])
    assert bic.main() == 0
    return out.read_bytes()


@pytest.mark.parametrize(
    ("args", "shipped"),
    [
        (
            "--nx 6 --ny 6 --nz 4 --n-vacancies 1 --vacuum-layers 1.0 --seed 42",
            "ni_example/examples/slab_ni_1vac.kmcinit",
        ),
        (
            "--nx 6 --ny 6 --nz 4 --n-vacancies 0 --vacuum-layers 1.0 --seed 42",
            "ni_dissolution_demo/examples/slab_ni_0vac.kmcinit",
        ),
    ],
    ids=["ni_example", "ni_dissolution_demo"],
)
def test_cli_rebuilds_the_shipped_example_slabs(
    bic: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, args: str, shipped: str
) -> None:
    shipped_path = REPO_ROOT / "models" / shipped
    if not shipped_path.is_file():
        pytest.skip(f"shipped slab missing: {shipped_path}")
    assert _run_cli(bic, monkeypatch, args, tmp_path / "out.kmcinit") == shipped_path.read_bytes()


# SHA-256 of the replaced tool's output for the same arguments.
CLI_DIGESTS = [
    (
        "--nx 8 --ny 8 --nz 10 --composition Ni90_Cr10 --n-vacancies 2 --vacuum-layers 8 --seed 7",
        "66777b4bc141cfb33ebca4b2063578181708e54c163a331079dbd23cdcf2565f",
    ),
    (
        "--nx 1 --ny 5 --nz 4 --n-adatom-layers 2",
        "2a65155fce221a3d970929502ad2a9df8d5973db5c6a1f564bb2c849ec8c0a32",
    ),
    (
        "--nx 2 --ny 2 --nz 5 --n-vacancies 3 --composition Ni50_Fe50 --seed 3",
        "23ee9e2ab52ad5b03471fdfc829296bf481807649a8bb01296e58ed0af26aff7",
    ),
    (
        "--nx 3 --ny 3 --nz 6 --n-adatom-layers 3 --vacancy-layer 5 --n-vacancies 2",
        "e7c06fa651d08cad4282863b63d05bbdec979a4c178d9070bbdf5b96905f70cd",
    ),
    (
        "--nx 12 --ny 9 --nz 7 --composition Ni0.9_Fe0.05_Cr0.05 --n-vacancies 5 "
        "--n-adatom-layers 3 --vacuum-layers 6 --seed 11",
        "c0071ede023cff0b0e92d3c194e5d0740478496420657df39601349cf9b00294",
    ),
    (
        "--nx 6 --ny 5 --nz 4 --element Fe --n-vacancies 2",
        "d50ce75b279ffcb48a8c1bbf6c9127143bea1fd98495e3ddaba2dcdcb5bd9acb",
    ),
    (
        "--nx 4 --ny 4 --nz 125 --n-adatom-layers 3 --composition Ni70_Cr30 --seed 9",
        "9757dfc9ba515b45231db63d7fa3d426725c222bb05d187219e37b4907af8d08",
    ),
]


@pytest.mark.parametrize(("args", "digest"), CLI_DIGESTS, ids=range(len(CLI_DIGESTS)))
def test_cli_output_is_byte_identical_to_the_replaced_tool(
    bic: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, args: str, digest: str
) -> None:
    data = _run_cli(bic, monkeypatch, args, tmp_path / "out.kmcinit")
    assert hashlib.sha256(data).hexdigest() == digest


@pytest.mark.parametrize(("nz", "n_adatom"), [(129, 0), (126, 3), (300, 0)])
def test_more_than_128_layers_is_refused(bic: ModuleType, nz: int, n_adatom: int) -> None:
    """Layer index 128+ does not fit the int8 layer_index: refuse, don't wrap."""
    with pytest.raises(ValueError, match=r"at most 128: layer_index is stored as int8"):
        bic.build_fcc100_slab(2, 2, nz, NN_DIST, n_adatom_layers=n_adatom)


def test_cli_refuses_more_than_128_layers(
    bic: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "thick.kmcinit"
    monkeypatch.setattr(
        sys,
        "argv",
        ["build_initial_config.py", "--nx", "4", "--ny", "4", "--nz", "129", "-o", str(out)],
    )
    with pytest.raises(ValueError, match="129 layers"):
        bic.main()
    assert not out.exists()
