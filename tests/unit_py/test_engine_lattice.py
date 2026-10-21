# tests/unit_py/test_engine_lattice.py
import pathlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import pack_kmcinit  # noqa: E402

from pylatkmc.engine.lattice import read_kmcinit  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EXAMPLE_KMCINIT = REPO / "models/ni_fe_cr_v1/examples/config.kmcinit"


def test_read_minimal_kmcinit_roundtrips(tmp_path):
    positions = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]], dtype=np.float32
    )
    path = pack_kmcinit(
        tmp_path,
        positions=positions,
        nn1_offsets=np.array([0, 1, 3, 4], dtype=np.int32),
        nn1_indices=np.array([1, 0, 2, 1], dtype=np.int32),
        nn2_offsets=np.array([0, 0, 0, 0], dtype=np.int32),
        nn2_indices=np.array([], dtype=np.int32),
        layer_index=np.array([0, 0, 0], dtype=np.int8),
        site_class=np.array([0, 0, 0], dtype=np.uint8),
        initial_species=np.array([0, 1, 1], dtype=np.uint8),  # site0 vacant
        nn_dist=1.0,
        cell=(100.0, 100.0, 100.0),
        n_layers=1,
    )
    lat = read_kmcinit(path)
    assert lat.n_sites == 3
    assert lat.nn_dist == 1.0
    assert lat.initial_species.tolist() == [0, 1, 1]
    # coord_table was built: site0's +x neighbour is site1.
    from pylatkmc.engine.coords import CODE_INDEX
    assert lat.coord_table[0, CODE_INDEX["NC_NN1_PX"]] == 1


@pytest.mark.skipif(not EXAMPLE_KMCINIT.exists(), reason="example fixture absent")
def test_read_real_example_kmcinit():
    lat = read_kmcinit(EXAMPLE_KMCINIT)
    assert lat.n_sites > 0
    assert lat.nn_dist > 0.0
    assert lat.coord_table.shape == (lat.n_sites, 23)
    # exactly the committed example has a single vacancy (species 0).
    assert int((lat.initial_species == 0).sum()) == 1
