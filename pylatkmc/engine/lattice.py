# pylatkmc/engine/lattice.py
"""Read a binary ``.kmcinit`` (magic ``KMCICv01``) into an in-memory ``Lattice``.

Payload order is authoritative per ``runtime/src/io/initconfig.c`` (the doc comment
in ``initconfig.h`` is stale — do not follow it).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# tools/ is not an importable package; load kmcfmt by path.
_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
import kmcfmt  # type: ignore[import-not-found]  # noqa: E402  (path import of tools/kmcfmt.py)

from pylatkmc.engine.coords import build_coord_table  # noqa: E402


@dataclass(frozen=True)
class Lattice:
    n_sites: int
    n_layers: int
    cell: tuple[float, float, float]
    nn_dist: float
    positions: np.ndarray
    nn1_offsets: np.ndarray
    nn1_indices: np.ndarray
    nn2_offsets: np.ndarray
    nn2_indices: np.ndarray
    layer_index: np.ndarray
    site_class: np.ndarray
    initial_species: np.ndarray
    coord_table: np.ndarray


def read_kmcinit(path: str | Path) -> Lattice:
    header, fp = kmcfmt.open_for_read(path, kmcfmt.INITCONFIG_MAGIC)
    try:
        body = fp.read()
    finally:
        fp.close()

    n = int(header["n_sites"])
    m1 = int(header["nn1_count"])
    m2 = int(header["nn2_count"])
    nn_dist = float(header["nn_dist"])
    n_layers = int(header["n_layers"])
    if "cell" in header:
        cell = (float(header["cell"][0]), float(header["cell"][1]), float(header["cell"][2]))
    else:
        nx, ny = int(header["nx"]), int(header["ny"])
        cell = (nx * nn_dist, ny * nn_dist, 2.0 * nn_dist)

    off = 4  # skip u32 payload_version
    positions = np.frombuffer(body, dtype="<f4", count=n * 3, offset=off).reshape(n, 3)
    off += n * 3 * 4
    nn1_offsets = np.frombuffer(body, dtype="<i4", count=n + 1, offset=off)
    off += (n + 1) * 4
    nn1_indices = np.frombuffer(body, dtype="<i4", count=m1, offset=off)
    off += m1 * 4
    nn2_offsets = np.frombuffer(body, dtype="<i4", count=n + 1, offset=off)
    off += (n + 1) * 4
    nn2_indices = np.frombuffer(body, dtype="<i4", count=m2, offset=off)
    off += m2 * 4
    layer_index = np.frombuffer(body, dtype="<i1", count=n, offset=off)
    off += n
    site_class = np.frombuffer(body, dtype="<u1", count=n, offset=off)
    off += n
    initial_species = np.frombuffer(body, dtype="<u1", count=n, offset=off)
    off += n

    if nn1_offsets[n] != m1 or nn2_offsets[n] != m2:
        raise ValueError(
            f"CSR offset/count mismatch: nn1[N]={nn1_offsets[n]} vs M1={m1}; "
            f"nn2[N]={nn2_offsets[n]} vs M2={m2}"
        )

    coord_table = build_coord_table(
        positions, nn1_offsets, nn1_indices, nn2_offsets, nn2_indices, cell, nn_dist
    )

    return Lattice(
        n_sites=n,
        n_layers=n_layers,
        cell=cell,
        nn_dist=nn_dist,
        positions=positions,
        nn1_offsets=nn1_offsets,
        nn1_indices=nn1_indices,
        nn2_offsets=nn2_offsets,
        nn2_indices=nn2_indices,
        layer_index=layer_index,
        site_class=site_class,
        initial_species=initial_species,
        coord_table=coord_table,
    )
