import numpy as np

from pylatkmc.engine.coords import (
    CODE_INDEX,
    NEIGHBOUR_CODE_DELTAS,
    build_coord_table,
)


def test_code_index_covers_23_codes_with_anchor_zero():
    assert len(CODE_INDEX) == 23
    assert CODE_INDEX["NC_ANCHOR"] == 0
    assert NEIGHBOUR_CODE_DELTAS.shape == (23, 3)
    # anchor delta is the origin
    assert np.allclose(NEIGHBOUR_CODE_DELTAS[0], [0.0, 0.0, 0.0])
    # +x in-plane 1NN sits at +1 nn_d on x
    assert np.allclose(NEIGHBOUR_CODE_DELTAS[CODE_INDEX["NC_NN1_PX"]], [1.0, 0.0, 0.0])


def test_build_coord_table_resolves_inplane_neighbours_and_stub():
    # Three sites in a row on x at spacing nn_dist=1.0: 0 -- 1 -- 2
    # Large cell so no PBC folding interferes.
    positions = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]], dtype=np.float32
    )
    # CSR 1NN: site0->[1], site1->[0,2], site2->[1]
    nn1_offsets = np.array([0, 1, 3, 4], dtype=np.int32)
    nn1_indices = np.array([1, 0, 2, 1], dtype=np.int32)
    # No 2NN edges.
    nn2_offsets = np.array([0, 0, 0, 0], dtype=np.int32)
    nn2_indices = np.array([], dtype=np.int32)
    table = build_coord_table(
        positions, nn1_offsets, nn1_indices, nn2_offsets, nn2_indices,
        cell=(100.0, 100.0, 100.0), nn_dist=1.0,
    )
    assert table.shape == (3, 23)
    px = CODE_INDEX["NC_NN1_PX"]
    mx = CODE_INDEX["NC_NN1_MX"]
    stub = 3  # n_sites
    # site0 has a +x neighbour (site1) but no -x neighbour (stub).
    assert table[0, CODE_INDEX["NC_ANCHOR"]] == 0
    assert table[0, px] == 1
    assert table[0, mx] == stub
    # site1 has both.
    assert table[1, px] == 2
    assert table[1, mx] == 0
    # a code with no matching edge stays stub.
    assert table[1, CODE_INDEX["NC_NN1_UP_PP"]] == stub
