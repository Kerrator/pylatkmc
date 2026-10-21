# tests/unit_py/_engine_fixtures.py
"""Shared helpers for the pure-Python engine tests. Import via the sys.path preamble
above so resolution is independent of pytest's import mode."""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

from pylatkmc.engine.coords import build_coord_table
from pylatkmc.engine.lattice import Lattice
from pylatkmc.processes import Action, Condition, CoordOffset, Process, ShellCondition

SPECIES = ["Vacant", "Ni", "Fe", "Cr"]


def pack_kmcinit(
    tmp_path, positions, nn1_offsets, nn1_indices, nn2_offsets, nn2_indices,
    layer_index, site_class, initial_species, nn_dist, cell, n_layers,
) -> Path:
    n = positions.shape[0]
    m1 = nn1_indices.shape[0]
    m2 = nn2_indices.shape[0]
    header = {
        "version": 1, "n_sites": n, "n_layers": n_layers, "nn1_count": m1,
        "nn2_count": m2, "nn_dist": nn_dist, "cell": list(cell),
    }
    hjson = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    pad = (4 - (len(hjson) % 4)) % 4
    payload = b"".join([
        struct.pack("<I", 1),
        positions.astype("<f4").tobytes(),
        nn1_offsets.astype("<i4").tobytes(),
        nn1_indices.astype("<i4").tobytes(),
        nn2_offsets.astype("<i4").tobytes(),
        nn2_indices.astype("<i4").tobytes(),
        layer_index.astype("<i1").tobytes(),
        site_class.astype("<u1").tobytes(),
        initial_species.astype("<u1").tobytes(),
        np.zeros(m1, dtype=np.uint8).tobytes(),
        np.zeros(m2, dtype=np.uint8).tobytes(),
    ])
    out = Path(tmp_path) / "mini.kmcinit"
    with open(out, "wb") as fp:
        fp.write(b"KMCICv01")
        fp.write(struct.pack("<I", len(hjson) + pad))
        fp.write(hjson)
        fp.write(b"\x00" * pad)
        fp.write(payload)
    return out


def mini_lattice() -> Lattice:
    """3 sites on x at spacing 1.0: site0 vacant, sites 1 and 2 are Ni."""
    positions = np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]], dtype=np.float32)
    nn1_offsets = np.array([0, 1, 3, 4], dtype=np.int32)
    nn1_indices = np.array([1, 0, 2, 1], dtype=np.int32)
    nn2_offsets = np.array([0, 0, 0, 0], dtype=np.int32)
    nn2_indices = np.array([], dtype=np.int32)
    cell = (100.0, 100.0, 100.0)
    coord_table = build_coord_table(
        positions, nn1_offsets, nn1_indices, nn2_offsets, nn2_indices, cell, 1.0
    )
    return Lattice(
        n_sites=3, n_layers=1, cell=cell, nn_dist=1.0, positions=positions,
        nn1_offsets=nn1_offsets, nn1_indices=nn1_indices,
        nn2_offsets=nn2_offsets, nn2_indices=nn2_indices,
        layer_index=np.zeros(3, np.int8), site_class=np.zeros(3, np.uint8),
        initial_species=np.array([0, 1, 1], np.uint8), coord_table=coord_table,
    )


def px_hop_gated(count: int) -> Process:
    """Ni hop from +x into the anchor vacancy, gated by exactly `count` vacant 1NN
    around the mover. rate_constant = 2.0."""
    return Process(
        name=f"px_hop_n{count}", family_id="surface_1NN_inplane", Ea_eV=0.4,
        rate_constant=2.0,
        conditions=(
            Condition(coord=CoordOffset(code="NC_ANCHOR"), species="Vacant"),
            Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),
        ),
        actions=(
            Action(coord=CoordOffset(code="NC_ANCHOR"), before="Vacant", after="Ni"),
            Action(coord=CoordOffset(code="NC_NN1_PX"), before="Ni", after="Vacant"),
        ),
        shell_conditions=(
            ShellCondition(coord=CoordOffset(code="NC_NN1_PX"), shell="1nn",
                           species="Vacant", count=count),
        ),
    )
