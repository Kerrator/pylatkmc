# Pure-Python (no-codegen) reference engine backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure-Python KMC engine under `pylatkmc/engine/` that interprets the
existing `list[Process]` catalogue directly (no codegen, no C) so the model can be run
and iterated on from Python, and cross-validated statistically against the C+MPI engine.

**Architecture:** A second consumer of `translator.translate_all(...) → list[Process]`.
It reads the same `.kmcinit` lattice, builds the same per-site neighbour `coord_table`,
interprets each `Process`'s conditions / shell-conditions / actions, runs a BKL
(n-fold-way) loop with its own numpy RNG, and writes the same output JSON the C runtime
writes (so existing `tools/compare_*.py` work against it). Validation is **statistical**
(D = MSD/6t and Arrhenius Eₐ within a calibrated tolerance), not bit-exact.

**Tech Stack:** Python ≥ 3.10, numpy (already a dependency), pydantic v2 (already a
dependency), pytest. No new runtime dependencies. Reuses `tools/kmcfmt.py`,
`pylatkmc.loader`, `pylatkmc.translator`, `pylatkmc.processes`.

**Design spec:** `docs/superpowers/specs/2026-06-22-pure-python-engine-backend-design.md`

## Global Constraints

- **Python:** `>=3.10,<3.14`. Target `py310` (no 3.11+-only syntax).
- **No new runtime dependencies.** numpy + pydantic only (both already in `pyproject.toml`).
- **No AI attribution in git artifacts** (per repo policy): no `Co-Authored-By` trailer,
  no "Generated with" footer in commits.
- **Lint/format:** `ruff` with `line-length = 100`, rules `E,F,W,I,UP,B,SIM`,
  `ignore = ["E501"]`. New package code under `pylatkmc/engine/` is **not** in the
  `tools/**` or `tests/**` per-file-ignore lists — it must pass the full ruleset.
- **Typing:** `mypy` runs `strict = true` on the package. New `pylatkmc/engine/` code
  must type-check under strict mypy.
- **Tests:** pytest, `testpaths = ["tests/unit_py"]`, files named `test_*.py`. Add new
  Python tests under `tests/unit_py/`.
- **Determinism contract:** the engine matches the C engine **statistically only**. It
  uses numpy RNG; it does NOT reproduce `runtime/src/core/rng.c`.
- **Species index convention (from `.kmcinit` / spec):** `0=Vacant, 1=Ni, 2=Fe, 3=Cr`
  — i.e. the index of a species name is its position in `spec.species` (which always
  starts with `"Vacant"`). The stub/sentinel species value is `255`.
- **NeighbourCode contract:** 23 codes, order and Cartesian deltas defined in
  `runtime/src/core/coord_codes.{h,c}`; the name tuple is
  `pylatkmc.processes.NEIGHBOUR_CODES`. Match tolerance `0.05` (nn_d units). A missing
  neighbour resolves to the stub index `n_sites`.

---

## File Structure

| File | Responsibility |
|---|---|
| `pylatkmc/engine/__init__.py` | Package marker + public re-exports (`read_kmcinit`, `load_catalogue`, `run`). |
| `pylatkmc/engine/coords.py` | `NEIGHBOUR_CODE_DELTAS`, `CODE_INDEX`, `build_coord_table(...)`. |
| `pylatkmc/engine/lattice.py` | `Lattice` dataclass + `read_kmcinit(path)`. |
| `pylatkmc/engine/catalogue.py` | `load_catalogue(...)`, `export_catalogue(...)`, `CompiledProcess`, `compile_catalogue(...)`. |
| `pylatkmc/engine/state.py` | `State` (mutable species, vacancy bookkeeping, MSD accumulators) + `state_from_lattice(...)`. |
| `pylatkmc/engine/executor.py` | Eligibility, event enumeration, BKL `step_once`, `run_replica`. |
| `pylatkmc/engine/rng.py` | `make_rng(base_seed, rank)` numpy Generator factory. |
| `pylatkmc/engine/io_ini.py` | `RunConfig` + `parse_input_ini(path)`. |
| `pylatkmc/engine/io_out.py` | output writers (`summary.json`, `aggregate_summary.json`, `pykmc.out`, `trajkmc.xyz`). |
| `pylatkmc/engine/runner.py` | `run(input_ini, n_replicas)` orchestration. |
| `pylatkmc/cli.py` | (modify) add `run` and `export-catalogue` subcommands. |
| `tools/compare_py_vs_c.py` | (new) statistical cross-engine gate. |
| `tests/unit_py/_engine_fixtures.py` | shared test helpers (`pack_kmcinit`, `mini_lattice`, `px_hop_gated`, `SPECIES`). |
| `tests/unit_py/test_engine_*.py` | unit + integration tests. |

---

## Test conventions

Engine test modules **must not import from one another** (pytest's import modes make
`from tests.unit_py.X import ...` fragile). Shared helpers live in
`tests/unit_py/_engine_fixtures.py` and are imported via a 2-line preamble that puts the
test directory on `sys.path`:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import mini_lattice, px_hop_gated, pack_kmcinit, SPECIES  # noqa: E402
```

Create `tests/unit_py/_engine_fixtures.py` once (committed with Task 2):

```python
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
```

---

## Task 1: `coords.py` — neighbour-code deltas and `build_coord_table`

**Files:**
- Create: `pylatkmc/engine/__init__.py`
- Create: `pylatkmc/engine/coords.py`
- Test: `tests/unit_py/test_engine_coords.py`

**Interfaces:**
- Consumes: `pylatkmc.processes.NEIGHBOUR_CODES` (the 23-name tuple, order-significant here).
- Produces:
  - `NEIGHBOUR_CODE_DELTAS: np.ndarray` shape `(23, 3)` float32, indexed by code index.
  - `CODE_INDEX: dict[str, int]` mapping code name → index `0..22`.
  - `COORD_MATCH_TOL: float = 0.05`.
  - `build_coord_table(positions, nn1_offsets, nn1_indices, nn2_offsets, nn2_indices, cell, nn_dist) -> np.ndarray` shape `(n_sites, 23)` int32, where entry `[s, nc]` is the neighbour site index, `s` itself for `NC_ANCHOR`, or the stub `n_sites` if `s` has no such neighbour. `cell` is a length-3 float sequence; `nn_dist` a float.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_coords.py
import numpy as np
import pytest

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_coords.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine'`.

- [ ] **Step 3: Create the package marker**

```python
# pylatkmc/engine/__init__.py
"""Pure-Python (no-codegen) reference KMC engine.

A second consumer of ``translator.translate_all(...) -> list[Process]``: it
interprets Process objects directly and runs a BKL loop in Python, instead of
emitting C. Validated statistically against the C+MPI engine.
"""

from __future__ import annotations
```

- [ ] **Step 4: Write `coords.py`**

```python
# pylatkmc/engine/coords.py
"""Neighbour-code geometry: the 23 canonical FCC deltas and the per-site
``coord_table`` builder.

This is the Python port of ``runtime/src/core/coord_codes.{h,c}`` and
``lattice_build_coord_table`` in ``runtime/src/core/lattice.c``. The deltas and the
0.05 match tolerance ARE the contract — they must match the C constants exactly.
"""

from __future__ import annotations

import numpy as np

from pylatkmc.processes import NEIGHBOUR_CODES

COORD_MATCH_TOL: float = 0.05

CODE_INDEX: dict[str, int] = {name: i for i, name in enumerate(NEIGHBOUR_CODES)}

# 1/sqrt(2) and sqrt(2), matching coord_codes.c (INVS2, S2). z uses 1/√2 for
# cross-layer 1NN, √2 for axial 2NN, in nn_d units.
_INVS2 = 0.70710678
_S2 = 1.41421356

# Index order MUST match pylatkmc.processes.NEIGHBOUR_CODES (== the C enum order).
NEIGHBOUR_CODE_DELTAS: np.ndarray = np.array(
    [
        [0.0, 0.0, 0.0],          # NC_ANCHOR
        [+1.0, 0.0, 0.0],         # NC_NN1_PX
        [-1.0, 0.0, 0.0],         # NC_NN1_MX
        [0.0, +1.0, 0.0],         # NC_NN1_PY
        [0.0, -1.0, 0.0],         # NC_NN1_MY
        [+0.5, +0.5, -_INVS2],    # NC_NN1_DOWN_PP
        [+0.5, -0.5, -_INVS2],    # NC_NN1_DOWN_PM
        [-0.5, +0.5, -_INVS2],    # NC_NN1_DOWN_MP
        [-0.5, -0.5, -_INVS2],    # NC_NN1_DOWN_MM
        [+0.5, +0.5, +_INVS2],    # NC_NN1_UP_PP
        [+0.5, -0.5, +_INVS2],    # NC_NN1_UP_PM
        [-0.5, +0.5, +_INVS2],    # NC_NN1_UP_MP
        [-0.5, -0.5, +_INVS2],    # NC_NN1_UP_MM
        [+1.0, +1.0, 0.0],        # NC_NN2_DIAG_PP
        [+1.0, -1.0, 0.0],        # NC_NN2_DIAG_PM
        [-1.0, +1.0, 0.0],        # NC_NN2_DIAG_MP
        [-1.0, -1.0, 0.0],        # NC_NN2_DIAG_MM
        [+2.0, 0.0, 0.0],         # NC_NN2_PX
        [-2.0, 0.0, 0.0],         # NC_NN2_MX
        [0.0, +2.0, 0.0],         # NC_NN2_PY
        [0.0, -2.0, 0.0],         # NC_NN2_MY
        [0.0, 0.0, +_S2],         # NC_NN2_PZ
        [0.0, 0.0, -_S2],         # NC_NN2_MZ
    ],
    dtype=np.float32,
)


def _min_image1(d: float, length: float) -> float:
    """Fold a one-axis displacement into [-L/2, L/2] (matches min_image1 in lattice.c)."""
    if d > 0.5 * length:
        return d - length
    if d < -0.5 * length:
        return d + length
    return d


def _match_code(dx_n: float, dy_n: float, dz_n: float) -> int:
    """Return the NeighbourCode index whose delta matches (dx, dy, dz) in nn_d units,
    or -1 if none within COORD_MATCH_TOL. NC_ANCHOR (index 0) is never matched here."""
    for nc in range(1, len(NEIGHBOUR_CODES)):
        cd = NEIGHBOUR_CODE_DELTAS[nc]
        if (
            abs(dx_n - cd[0]) < COORD_MATCH_TOL
            and abs(dy_n - cd[1]) < COORD_MATCH_TOL
            and abs(dz_n - cd[2]) < COORD_MATCH_TOL
        ):
            return nc
    return -1


def build_coord_table(
    positions: np.ndarray,
    nn1_offsets: np.ndarray,
    nn1_indices: np.ndarray,
    nn2_offsets: np.ndarray,
    nn2_indices: np.ndarray,
    cell: tuple[float, float, float],
    nn_dist: float,
) -> np.ndarray:
    """Build ``coord_table[n_sites, 23]`` of neighbour site indices.

    Entry ``[s, 0]`` (NC_ANCHOR) is ``s``. Every other entry is the matched
    neighbour site index, or the stub value ``n_sites`` when ``s`` has no such
    neighbour. First match wins on PBC alias (matches lattice.c). Mirrors
    ``lattice_build_coord_table``.
    """
    n_sites = int(positions.shape[0])
    n_codes = len(NEIGHBOUR_CODES)
    stub = n_sites
    table = np.full((n_sites, n_codes), stub, dtype=np.int32)
    inv_nn = 1.0 / nn_dist
    lx, ly, lz = float(cell[0]), float(cell[1]), float(cell[2])

    for s in range(n_sites):
        table[s, 0] = s
        sx, sy, sz = (
            float(positions[s, 0]),
            float(positions[s, 1]),
            float(positions[s, 2]),
        )
        for offsets, indices in (
            (nn1_offsets, nn1_indices),
            (nn2_offsets, nn2_indices),
        ):
            for i in range(int(offsets[s]), int(offsets[s + 1])):
                n = int(indices[i])
                dx = _min_image1(float(positions[n, 0]) - sx, lx) * inv_nn
                dy = _min_image1(float(positions[n, 1]) - sy, ly) * inv_nn
                dz = _min_image1(float(positions[n, 2]) - sz, lz) * inv_nn
                nc = _match_code(dx, dy, dz)
                if nc < 0:
                    continue
                if table[s, nc] == stub:
                    table[s, nc] = n
    return table
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_coords.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Lint and type-check the new files**

Run: `ruff check pylatkmc/engine/coords.py pylatkmc/engine/__init__.py && mypy pylatkmc/engine/coords.py`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add pylatkmc/engine/__init__.py pylatkmc/engine/coords.py tests/unit_py/test_engine_coords.py
git commit -m "feat(engine): neighbour-code deltas and coord_table builder"
```

---

## Task 2: `lattice.py` — read `.kmcinit` into an in-memory `Lattice`

**Files:**
- Create: `pylatkmc/engine/lattice.py`
- Test: `tests/unit_py/test_engine_lattice.py`

**Interfaces:**
- Consumes: `tools/kmcfmt.py` `read_header`, `INITCONFIG_MAGIC`; `coords.build_coord_table`.
- Produces:
  - `@dataclass(frozen=True) Lattice` with fields: `n_sites: int`, `n_layers: int`,
    `cell: tuple[float, float, float]`, `nn_dist: float`, `positions: np.ndarray (N,3) f32`,
    `nn1_offsets: np.ndarray (N+1,) i32`, `nn1_indices: np.ndarray (M1,) i32`,
    `nn2_offsets: np.ndarray (N+1,) i32`, `nn2_indices: np.ndarray (M2,) i32`,
    `layer_index: np.ndarray (N,) i8`, `site_class: np.ndarray (N,) u8`,
    `initial_species: np.ndarray (N,) u8`, `coord_table: np.ndarray (N,23) i32`.
  - `read_kmcinit(path: str | Path) -> Lattice`.

The `.kmcinit` payload order is authoritative per `runtime/src/io/initconfig.c:14-91`
(NOT the stale `initconfig.h` comment): `u32 payload_version`, `f32[N*3] positions`,
`i32[N+1] nn1_offsets`, `i32[M1] nn1_indices`, `i32[N+1] nn2_offsets`, `i32[M2] nn2_indices`,
`i8[N] layer_index`, `u8[N] site_class`, `u8[N] initial_species`, `u8[M1] nn1_dir_family`,
`u8[M2] nn2_dir_family`. Header JSON keys: `version, n_sites, n_layers, nn1_count, nn2_count,
nn_dist, cell` (cell falls back to `[nx*nn_dist, ny*nn_dist, 2*nn_dist]`).

- [ ] **Step 1: Create `_engine_fixtures.py` (see *Test conventions*) and write the failing test**

First create `tests/unit_py/_engine_fixtures.py` with the full content shown in the
*Test conventions* section above. Then write this test, which packs a minimal valid
`.kmcinit` (hermetic — no scipy, no real file) via the shared `pack_kmcinit` helper,
asserts the reader round-trips it, then reads the real committed example fixture.

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_lattice.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.lattice'`.

- [ ] **Step 3: Write `lattice.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_lattice.py -v`
Expected: PASS (the real-fixture test runs since `config.kmcinit` is committed).

- [ ] **Step 5: Lint and type-check**

Run: `ruff check pylatkmc/engine/lattice.py && mypy pylatkmc/engine/lattice.py`
Expected: no errors. mypy cannot resolve the path-based `import kmcfmt`, so add
`# type: ignore[import-not-found]` on that import line only (the `# noqa: E402` for
ruff stays).

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/engine/lattice.py tests/unit_py/_engine_fixtures.py tests/unit_py/test_engine_lattice.py
git commit -m "feat(engine): .kmcinit reader producing in-memory Lattice"
```

---

## Task 3: `catalogue.py` — load, compile, and export the Process catalogue

**Files:**
- Create: `pylatkmc/engine/catalogue.py`
- Test: `tests/unit_py/test_engine_catalogue.py`

**Interfaces:**
- Consumes: `pylatkmc.loader.load`, `pylatkmc.translator.load_family_rate_table`,
  `pylatkmc.translator.translate_all`, `pylatkmc.processes.Process`,
  `coords.CODE_INDEX`.
- Produces:
  - `load_catalogue(spec_path, family_csv=None) -> list[Process]` — source priority:
    explicit `family_csv` → `spec.rate_data.family_table` if it resolves → committed
    `<spec_dir>/generated/catalogue.json`. Raises `FileNotFoundError` with a clear
    message if none available.
  - `export_catalogue(spec_path, out_path=None, family_csv=None) -> Path` — write the
    `list[Process]` as JSON (`<spec_dir>/generated/catalogue.json` by default).
  - `@dataclass(frozen=True) CompiledProcess` with: `name: str`, `family_id: str`,
    `Ea_eV: float`, `rate: float`, `anchor_species: int`,
    `conds: tuple[tuple[int, int], ...]` (code_idx, species_idx),
    `shells: tuple[tuple[int, int, int, int], ...]` (code_idx, shell_kind 0=1nn/1=2nn, species_idx, count),
    `actions: tuple[tuple[int, int, int], ...]` (code_idx, before_idx, after_idx),
    `v_from_code: int` (anchor action's code_idx, where Vacant→mover; the vacancy's
    origin), `v_to_code: int` (action where mover→Vacant; the vacancy's destination).
  - `compile_catalogue(processes, species) -> list[CompiledProcess]` where
    `species: list[str]` is `spec.species` (index = species id; `"Vacant"` is 0).
  - `SPECIES_STUB: int = 255`.

- [ ] **Step 1: Write the failing test (synthetic catalogue — no CSV needed)**

```python
# tests/unit_py/test_engine_catalogue.py
from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.processes import (
    Action,
    Condition,
    CoordOffset,
    Process,
    ShellCondition,
)

SPECIES = ["Vacant", "Ni", "Fe", "Cr"]


def _hop_process() -> Process:
    """A Ni hop from +x into the anchor vacancy, gated by exactly 1 vacant 1NN
    around the mover."""
    return Process(
        name="demo_hop",
        family_id="surface_1NN_inplane",
        Ea_eV=0.5,
        rate_constant=1.0e9,
        conditions=(
            Condition(coord=CoordOffset(code="NC_ANCHOR"), species="Vacant"),
            Condition(coord=CoordOffset(code="NC_NN1_PX"), species="Ni"),
        ),
        actions=(
            Action(coord=CoordOffset(code="NC_ANCHOR"), before="Vacant", after="Ni"),
            Action(coord=CoordOffset(code="NC_NN1_PX"), before="Ni", after="Vacant"),
        ),
        shell_conditions=(
            ShellCondition(
                coord=CoordOffset(code="NC_NN1_PX"), shell="1nn", species="Vacant", count=1
            ),
        ),
    )


def test_compile_catalogue_indexes_species_and_codes():
    from pylatkmc.engine.coords import CODE_INDEX

    compiled = compile_catalogue([_hop_process()], SPECIES)
    assert len(compiled) == 1
    cp = compiled[0]
    assert cp.name == "demo_hop"
    assert cp.rate == 1.0e9
    assert cp.anchor_species == 0  # Vacant
    # anchor condition (Vacant at NC_ANCHOR) + Ni at NC_NN1_PX
    assert (CODE_INDEX["NC_ANCHOR"], 0) in cp.conds
    assert (CODE_INDEX["NC_NN1_PX"], 1) in cp.conds
    # shell: (code, kind 0=1nn, species 0=Vacant, count 1)
    assert cp.shells == ((CODE_INDEX["NC_NN1_PX"], 0, 0, 1),)
    # vacancy moves from anchor (Vacant->Ni) to NC_NN1_PX (Ni->Vacant)
    assert cp.v_from_code == CODE_INDEX["NC_ANCHOR"]
    assert cp.v_to_code == CODE_INDEX["NC_NN1_PX"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_catalogue.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.catalogue'`.

- [ ] **Step 3: Write `catalogue.py`**

```python
# pylatkmc/engine/catalogue.py
"""Load, compile, and export the Process catalogue for the Python engine.

The catalogue is the SAME ``list[Process]`` the C codegen consumes. Source priority:
explicit ``--family-csv`` → the spec's ``family_table`` (off-repo on most machines) →
the committed ``generated/catalogue.json``. ``compile_catalogue`` turns Process objects
into an index-based form (species/code integers) for fast eligibility checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pylatkmc.engine.coords import CODE_INDEX
from pylatkmc.loader import load
from pylatkmc.processes import Process
from pylatkmc.translator import load_family_rate_table, translate_all

SPECIES_STUB: int = 255
_SHELL_KIND = {"1nn": 0, "2nn": 1}


def _generated_dir(spec_path: Path) -> Path:
    return spec_path.parent / "generated"


def _resolve_family_csv(spec_path: Path, family_csv: str | Path | None) -> Path | None:
    spec = load(spec_path)
    if family_csv is not None:
        cand = Path(family_csv)
        if not cand.is_absolute():
            cand = (spec_path.parent / cand).resolve()
        return cand if cand.exists() else None
    ft = spec.rate_data.family_table
    if ft is None:
        return None
    cand = Path(ft)
    if not cand.is_absolute():
        cand = (spec_path.parent / cand).resolve()
    return cand if cand.exists() else None


def _translate_from_csv(spec_path: Path, family_csv: Path) -> list[Process]:
    spec = load(spec_path)
    rows = load_family_rate_table(family_csv)
    return translate_all(
        rows,
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
    )


def load_catalogue(
    spec_path: str | Path, family_csv: str | Path | None = None
) -> list[Process]:
    spec_path = Path(spec_path).resolve()
    csv = _resolve_family_csv(spec_path, family_csv)
    if csv is not None:
        return _translate_from_csv(spec_path, csv)
    cat_json = _generated_dir(spec_path) / "catalogue.json"
    if cat_json.exists():
        raw = cat_json.read_text(encoding="utf-8")
        import json

        return [Process.model_validate(obj) for obj in json.loads(raw)]
    raise FileNotFoundError(
        "No catalogue source: family CSV did not resolve and "
        f"{cat_json} is absent. Run `pylatkmc-gen export-catalogue {spec_path}` "
        "on a checkout where the family CSV resolves, and commit the JSON."
    )


def export_catalogue(
    spec_path: str | Path,
    out_path: str | Path | None = None,
    family_csv: str | Path | None = None,
) -> Path:
    import json

    spec_path = Path(spec_path).resolve()
    csv = _resolve_family_csv(spec_path, family_csv)
    if csv is None:
        raise FileNotFoundError(
            "export-catalogue requires the family CSV to resolve "
            "(spec.rate_data.family_table or --family-csv)."
        )
    processes = _translate_from_csv(spec_path, csv)
    out = Path(out_path) if out_path else _generated_dir(spec_path) / "catalogue.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [p.model_dump(mode="json") for p in processes]
    out.write_text(json.dumps(payload, indent=0), encoding="utf-8")
    return out


@dataclass(frozen=True)
class CompiledProcess:
    name: str
    family_id: str
    Ea_eV: float
    rate: float
    anchor_species: int
    conds: tuple[tuple[int, int], ...]
    shells: tuple[tuple[int, int, int, int], ...]
    actions: tuple[tuple[int, int, int], ...]
    v_from_code: int
    v_to_code: int


def compile_catalogue(processes: list[Process], species: list[str]) -> list[CompiledProcess]:
    sidx = {name: i for i, name in enumerate(species)}
    out: list[CompiledProcess] = []
    for p in processes:
        if not isinstance(p.rate_constant, (int, float)):
            raise ValueError(
                f"Process {p.name!r} has a non-scalar rate_constant "
                f"({p.rate_constant!r}); the Python engine only supports v2 float rates."
            )
        conds = tuple((CODE_INDEX[c.coord.code], sidx[c.species]) for c in p.conditions)
        shells = tuple(
            (CODE_INDEX[s.coord.code], _SHELL_KIND[s.shell], sidx[s.species], s.count)
            for s in p.shell_conditions
        )
        actions = tuple(
            (CODE_INDEX[a.coord.code], sidx[a.before], sidx[a.after]) for a in p.actions
        )
        anchor_species = next(
            (sidx[c.species] for c in p.conditions if c.coord.code == "NC_ANCHOR"),
            SPECIES_STUB,
        )
        vacant = sidx["Vacant"]
        v_from = next(
            (CODE_INDEX[a.coord.code] for a in p.actions if sidx[a.before] == vacant),
            CODE_INDEX["NC_ANCHOR"],
        )
        v_to = next(
            (CODE_INDEX[a.coord.code] for a in p.actions if sidx[a.after] == vacant),
            CODE_INDEX["NC_ANCHOR"],
        )
        out.append(
            CompiledProcess(
                name=p.name,
                family_id=p.family_id,
                Ea_eV=p.Ea_eV,
                rate=float(p.rate_constant),
                anchor_species=anchor_species,
                conds=conds,
                shells=shells,
                actions=actions,
                v_from_code=v_from,
                v_to_code=v_to,
            )
        )
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_catalogue.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and type-check**

Run: `ruff check pylatkmc/engine/catalogue.py && mypy pylatkmc/engine/catalogue.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/engine/catalogue.py tests/unit_py/test_engine_catalogue.py
git commit -m "feat(engine): catalogue load/compile/export (JSON-backed, CSV-optional)"
```

---

## Task 4: `state.py` — mutable simulation state

**Files:**
- Create: `pylatkmc/engine/state.py`
- Test: `tests/unit_py/test_engine_state.py`

**Interfaces:**
- Consumes: `lattice.Lattice`, `catalogue.SPECIES_STUB`.
- Produces:
  - `class State` with: `species: np.ndarray (N+1,) uint8` (`species[N] = SPECIES_STUB`),
    `n_sites: int`, `vac_list: list[int]`, `vac_idx_of: dict[int,int]`, `n_vac: int`,
    `time_s: float`, `step: int`, `disp: np.ndarray (n_vac0, 3) float64` (per-initial-vacancy
    unwrapped displacement), `vac_origin: dict[int,int]` (current site → initial-vacancy slot).
  - `state_from_lattice(lat: Lattice) -> State`.
  - `State.mean_msd_A2() -> float` = mean over tracked vacancies of `|disp|²`.

Single-vacancy MSD tracking (the only case the C engine tracks cleanly per
`kmc.c`): when a vacancy moves from site `a` to site `b`, add the min-image displacement
`pos[b]-pos[a]` to that vacancy's accumulated `disp`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_state.py
import pathlib
import sys

from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import mini_lattice as _mini_lattice  # noqa: E402


def test_state_init_and_msd_tracking():
    st = state_from_lattice(_mini_lattice())
    assert st.n_vac == 1
    assert st.vac_list == [0]
    # stub sentinel present
    assert st.species[3] == 255
    assert st.mean_msd_A2() == 0.0
    # move the vacancy from site 0 to site 1: record displacement (1,0,0)
    st.move_vacancy(_mini_lattice(), src=0, dst=1)
    assert st.mean_msd_A2() == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.state'`.

- [ ] **Step 3: Write `state.py`**

```python
# pylatkmc/engine/state.py
"""Mutable per-replica simulation state: species array, vacancy bookkeeping, and
per-vacancy unwrapped displacement for MSD."""

from __future__ import annotations

import numpy as np

from pylatkmc.engine.catalogue import SPECIES_STUB
from pylatkmc.engine.lattice import Lattice


def _min_image(d: np.ndarray, cell: tuple[float, float, float]) -> np.ndarray:
    out = d.astype(np.float64).copy()
    for k in range(3):
        L = cell[k]
        if out[k] > 0.5 * L:
            out[k] -= L
        elif out[k] < -0.5 * L:
            out[k] += L
    return out


class State:
    def __init__(self, lat: Lattice) -> None:
        n = lat.n_sites
        self.n_sites = n
        # species padded with one stub slot at index n.
        self.species = np.empty(n + 1, dtype=np.uint8)
        self.species[:n] = lat.initial_species
        self.species[n] = SPECIES_STUB
        self.vac_list: list[int] = [int(s) for s in np.flatnonzero(lat.initial_species == 0)]
        self.vac_idx_of: dict[int, int] = {s: i for i, s in enumerate(self.vac_list)}
        self.n_vac = len(self.vac_list)
        self.time_s = 0.0
        self.step = 0
        # per-initial-vacancy unwrapped displacement; slot = initial vacancy order.
        self.disp = np.zeros((max(self.n_vac, 1), 3), dtype=np.float64)
        # current vacancy site -> displacement slot.
        self.vac_slot: dict[int, int] = {s: i for i, s in enumerate(self.vac_list)}

    def mean_msd_A2(self) -> float:
        if self.n_vac == 0:
            return 0.0
        sq = (self.disp[: self.n_vac] ** 2).sum(axis=1)
        return float(sq.mean())

    def move_vacancy(self, lat: Lattice, src: int, dst: int) -> None:
        """Move a vacancy from site ``src`` to site ``dst`` and accumulate its
        unwrapped displacement. Caller has already updated ``self.species``."""
        slot = self.vac_slot.pop(src)
        self.vac_slot[dst] = slot
        d = lat.positions[dst].astype(np.float64) - lat.positions[src].astype(np.float64)
        self.disp[slot] += _min_image(d, lat.cell)
        # keep vac_list / vac_idx_of consistent
        i = self.vac_idx_of.pop(src)
        self.vac_list[i] = dst
        self.vac_idx_of[dst] = i


def state_from_lattice(lat: Lattice) -> State:
    return State(lat)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_state.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and type-check**

Run: `ruff check pylatkmc/engine/state.py && mypy pylatkmc/engine/state.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/engine/state.py tests/unit_py/test_engine_state.py
git commit -m "feat(engine): mutable State with vacancy + MSD bookkeeping"
```

---

## Task 5: `executor.py` — eligibility and event enumeration (read-only)

**Files:**
- Create: `pylatkmc/engine/executor.py`
- Test: `tests/unit_py/test_engine_eligibility.py`

**Interfaces:**
- Consumes: `lattice.Lattice`, `state.State`, `catalogue.CompiledProcess`,
  `catalogue.SPECIES_STUB`.
- Produces:
  - `is_eligible(lat, st, cp, anchor) -> bool`.
  - `count_in_shell(lat, st, site, shell_kind, species_idx) -> int` — counts sites in
    `site`'s CSR shell (`nn1` for kind 0, `nn2` for kind 1) whose species == `species_idx`.
  - `enumerate_events(lat, st, compiled) -> tuple[list[tuple[int,int]], np.ndarray, float]`
    returning `(pairs, rates, r_tot)` where `pairs[i] = (proc_id, anchor_site)` and
    `rates[i]` is that pair's rate; `r_tot = rates.sum()`. Anchors scanned are
    `st.vac_list` grouped by each process's `anchor_species` (v2: all Vacant).

A neighbour that resolves to the stub (`coord_table[s, code] == n_sites`) has species
`SPECIES_STUB`, which never equals a real species index, so its condition fails — this
reproduces the C "stub site" behaviour without a special case.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_eligibility.py
import pathlib
import sys

import numpy as np

from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.engine.executor import enumerate_events, is_eligible
from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import (  # noqa: E402
    SPECIES,
    mini_lattice as _mini_lattice,
    px_hop_gated as _px_hop_gated,
)


def test_eligibility_respects_conditions_and_exact_shell_count():
    lat = _mini_lattice()  # sites 0(vac)-1(Ni)-2(Ni); site0 only has +x neighbour
    st = state_from_lattice(lat)
    # mover = site1 (NC_NN1_PX of anchor 0). Its 1NN shell = {0, 2}; vacant count = 1 (site0).
    compiled_ok = compile_catalogue([_px_hop_gated(1)], SPECIES)
    assert is_eligible(lat, st, compiled_ok[0], anchor=0) is True
    # exact-count gate: count=0 must NOT fire (there IS 1 vacant 1NN).
    compiled_no = compile_catalogue([_px_hop_gated(0)], SPECIES)
    assert is_eligible(lat, st, compiled_no[0], anchor=0) is False


def test_enumerate_events_only_at_vacancy_anchors():
    lat = _mini_lattice()
    st = state_from_lattice(lat)
    compiled = compile_catalogue([_px_hop_gated(1)], SPECIES)
    pairs, rates, r_tot = enumerate_events(lat, st, compiled)
    assert pairs == [(0, 0)]  # proc 0 at anchor site 0 only
    assert r_tot == 2.0
    assert np.allclose(rates, [2.0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_eligibility.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.executor'`.

- [ ] **Step 3: Write the eligibility core of `executor.py`**

```python
# pylatkmc/engine/executor.py
"""The BKL/n-fold-way executor: eligibility, event enumeration, and (Task 7) the
step loop. Eligibility is a pure function of lattice state, so a full rescan each
step is exact — the C decision tree is only a perf optimization."""

from __future__ import annotations

import numpy as np

from pylatkmc.engine.catalogue import CompiledProcess
from pylatkmc.engine.lattice import Lattice
from pylatkmc.engine.state import State


def count_in_shell(
    lat: Lattice, st: State, site: int, shell_kind: int, species_idx: int
) -> int:
    if site >= lat.n_sites:  # stub site has no shell
        return 0
    if shell_kind == 0:
        b, e = int(lat.nn1_offsets[site]), int(lat.nn1_offsets[site + 1])
        nbrs = lat.nn1_indices[b:e]
    else:
        b, e = int(lat.nn2_offsets[site]), int(lat.nn2_offsets[site + 1])
        nbrs = lat.nn2_indices[b:e]
    return int(np.count_nonzero(st.species[nbrs] == species_idx))


def is_eligible(lat: Lattice, st: State, cp: CompiledProcess, anchor: int) -> bool:
    ct = lat.coord_table[anchor]
    for code_idx, sp in cp.conds:
        if st.species[ct[code_idx]] != sp:
            return False
    for code_idx, kind, sp, count in cp.shells:
        site = int(ct[code_idx])
        if count_in_shell(lat, st, site, kind, sp) != count:
            return False
    return True


def enumerate_events(
    lat: Lattice, st: State, compiled: list[CompiledProcess]
) -> tuple[list[tuple[int, int]], np.ndarray, float]:
    """Return (pairs, rates, r_tot). Anchors are scanned by each process's
    anchor_species; in v2 every process anchors on Vacant, so the scan set is the
    vacancy list."""
    # Group anchor candidates by species value present in the state.
    pairs: list[tuple[int, int]] = []
    rate_list: list[float] = []
    # vacancy sites are the only anchor candidates for Vacant-anchored processes.
    vac_sites = st.vac_list
    for proc_id, cp in enumerate(compiled):
        if cp.anchor_species == 0:  # Vacant
            candidates = vac_sites
        else:
            candidates = [
                s for s in range(lat.n_sites) if st.species[s] == cp.anchor_species
            ]
        for s in candidates:
            if is_eligible(lat, st, cp, s):
                pairs.append((proc_id, s))
                rate_list.append(cp.rate)
    rates = np.asarray(rate_list, dtype=np.float64)
    return pairs, rates, float(rates.sum())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_eligibility.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and type-check**

Run: `ruff check pylatkmc/engine/executor.py && mypy pylatkmc/engine/executor.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/engine/executor.py tests/unit_py/test_engine_eligibility.py
git commit -m "feat(engine): eligibility + event enumeration (Vacant-anchored scan)"
```

---

## Task 6: `cli.py` — `export-catalogue` + read-only `eligible` debug command (M1 close-out)

**Files:**
- Modify: `pylatkmc/cli.py` (add two subparsers + handlers; update module docstring)
- Test: `tests/unit_py/test_engine_cli_eligible.py`

**Interfaces:**
- Consumes: `engine.catalogue.export_catalogue`, `engine.lattice.read_kmcinit`,
  `engine.catalogue.load_catalogue` + `compile_catalogue`, `engine.state.state_from_lattice`,
  `engine.executor.is_eligible`, `pylatkmc.loader.load`.
- Produces (CLI): `pylatkmc-gen export-catalogue <spec> [--family-csv X] [-o OUT]` and
  `pylatkmc-gen eligible <spec> --kmcinit <file> --site <n> [--family-csv X]` which prints
  the names of processes eligible at the given anchor site.

- [ ] **Step 1: Write the failing test (drives `eligible` via a synthetic catalogue JSON)**

```python
# tests/unit_py/test_engine_cli_eligible.py
import json
from pathlib import Path

import numpy as np

from pylatkmc.cli import main


def test_eligible_command_lists_processes(tmp_path, capsys, monkeypatch):
    # Build a tiny spec dir with a committed catalogue.json and a packed .kmcinit,
    # then drive `pylatkmc-gen eligible`.
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from _engine_fixtures import pack_kmcinit as _pack_kmcinit

    spec_dir = tmp_path / "m"
    (spec_dir / "generated").mkdir(parents=True)
    spec = spec_dir / "m.kmcspec.toml"
    spec.write_text(
        'name = "m"\n'
        'lattice = "fcc"\n'
        'species = ["Vacant", "Ni", "Fe", "Cr"]\n'
        '[[shells]]\nname = "nn1"\ncutoff_mult = 1.05\n'
        '[[key.axes]]\nname = "mover_species"\nkind = "enum"\nmax = 3\nskip_vacant = true\n'
        "[rate_data]\n"
        'primary = "p.csv"\n'
        'temperature_K = 500.0\n'
        "k0_Hz = 1.0e13\n",
        encoding="utf-8",
    )
    catalogue = [
        {
            "name": "demo_hop",
            "family_id": "surface_1NN_inplane",
            "Ea_eV": 0.5,
            "rate_constant": 1.0e9,
            "conditions": [
                {"coord": {"code": "NC_ANCHOR"}, "species": "Vacant"},
                {"coord": {"code": "NC_NN1_PX"}, "species": "Ni"},
            ],
            "actions": [
                {"coord": {"code": "NC_ANCHOR"}, "before": "Vacant", "after": "Ni"},
                {"coord": {"code": "NC_NN1_PX"}, "before": "Ni", "after": "Vacant"},
            ],
            "shell_conditions": [],
            "bystanders": [],
        }
    ]
    (spec_dir / "generated" / "catalogue.json").write_text(json.dumps(catalogue))
    kmcinit = _pack_kmcinit(
        spec_dir,
        positions=np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]], np.float32),
        nn1_offsets=np.array([0, 1, 3, 4], np.int32),
        nn1_indices=np.array([1, 0, 2, 1], np.int32),
        nn2_offsets=np.array([0, 0, 0, 0], np.int32),
        nn2_indices=np.array([], np.int32),
        layer_index=np.zeros(3, np.int8),
        site_class=np.zeros(3, np.uint8),
        initial_species=np.array([0, 1, 1], np.uint8),
        nn_dist=1.0, cell=(100.0, 100.0, 100.0), n_layers=1,
    )
    rc = main(["eligible", str(spec), "--kmcinit", str(kmcinit), "--site", "0"])
    assert rc == 0
    assert "demo_hop" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_cli_eligible.py -v`
Expected: FAIL — argparse error: invalid choice `eligible`.

- [ ] **Step 3: Add the two subcommands to `cli.py`**

Add these handlers (place after `cmd_clean`):

```python
def cmd_export_catalogue(args: argparse.Namespace) -> int:
    from .engine.catalogue import export_catalogue

    spec_path = Path(args.spec).resolve()
    out = export_catalogue(spec_path, out_path=args.output, family_csv=args.family_csv)
    print(f"pylatkmc-gen: wrote catalogue -> {out}")
    return 0


def cmd_eligible(args: argparse.Namespace) -> int:
    from .engine.catalogue import compile_catalogue, load_catalogue
    from .engine.executor import is_eligible
    from .engine.lattice import read_kmcinit
    from .engine.state import state_from_lattice
    from .loader import load

    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    processes = load_catalogue(spec_path, family_csv=args.family_csv)
    compiled = compile_catalogue(processes, list(spec.species))
    lat = read_kmcinit(args.kmcinit)
    st = state_from_lattice(lat)
    eligible = [cp.name for cp in compiled if is_eligible(lat, st, cp, args.site)]
    print(f"{len(eligible)} eligible process(es) at site {args.site}:")
    for name in eligible:
        print(f"  {name}")
    return 0
```

Then register them in `_make_parser` (after `p_clean`):

```python
    p_export = sub.add_parser(
        "export-catalogue",
        help="Serialise translate_all(...) to generated/catalogue.json",
    )
    p_export.add_argument("spec", help="Path to .kmcspec.toml")
    p_export.add_argument("--family-csv", default=None, help="Override the family CSV path")
    p_export.add_argument("-o", "--output", default=None, help="Output JSON path")
    p_export.set_defaults(func=cmd_export_catalogue)

    p_elig = sub.add_parser(
        "eligible",
        help="List processes eligible at one anchor site (read-only debug)",
    )
    p_elig.add_argument("spec", help="Path to .kmcspec.toml")
    p_elig.add_argument("--kmcinit", required=True, help="Path to a .kmcinit lattice")
    p_elig.add_argument("--site", type=int, required=True, help="Anchor site index")
    p_elig.add_argument("--family-csv", default=None, help="Override the family CSV path")
    p_elig.set_defaults(func=cmd_eligible)
```

Also update the module docstring usage block to mention `export-catalogue` and `eligible`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_cli_eligible.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite + lint (no regressions to existing CLI tests)**

Run: `python -m pytest tests/unit_py -q && ruff check pylatkmc/cli.py`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/cli.py tests/unit_py/test_engine_cli_eligible.py
git commit -m "feat(cli): export-catalogue + eligible debug command (M1 complete)"
```

---

## Task 7: `rng.py` — reproducible per-replica RNG

**Files:**
- Create: `pylatkmc/engine/rng.py`
- Test: `tests/unit_py/test_engine_rng.py`

**Interfaces:**
- Produces: `make_rng(base_seed: int, rank: int) -> np.random.Generator` — independent,
  reproducible streams per `(base_seed, rank)` using `np.random.default_rng` over a
  `SeedSequence(entropy=base_seed, spawn_key=(rank,))`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_rng.py
from pylatkmc.engine.rng import make_rng


def test_rng_reproducible_and_rank_independent():
    a1 = make_rng(42, 0).random(5).tolist()
    a2 = make_rng(42, 0).random(5).tolist()
    b = make_rng(42, 1).random(5).tolist()
    assert a1 == a2          # same (seed, rank) -> identical stream
    assert a1 != b           # different rank -> different stream
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_rng.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.rng'`.

- [ ] **Step 3: Write `rng.py`**

```python
# pylatkmc/engine/rng.py
"""Reproducible per-replica RNG. Statistical parity only — this does NOT reproduce
the C runtime's xoshiro256++ stream (see the design spec, determinism section)."""

from __future__ import annotations

import numpy as np


def make_rng(base_seed: int, rank: int) -> np.random.Generator:
    """Independent, reproducible stream per (base_seed, rank)."""
    seq = np.random.SeedSequence(entropy=base_seed, spawn_key=(rank,))
    return np.random.default_rng(seq)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_rng.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pylatkmc/engine/rng.py tests/unit_py/test_engine_rng.py
git commit -m "feat(engine): reproducible per-replica numpy RNG"
```

---

## Task 8: `executor.py` — BKL `step_once`

**Files:**
- Modify: `pylatkmc/engine/executor.py` (add `EventOutcome` + `step_once`)
- Test: `tests/unit_py/test_engine_step.py`

**Interfaces:**
- Consumes: `enumerate_events` (Task 5), `state.State.move_vacancy`, an RNG Generator.
- Produces:
  - `@dataclass EventOutcome` with: `proc_id: int`, `site: int`, `dt: float`,
    `r_tot: float`, `k_event: float`, `Ea_eV: float`.
  - `step_once(lat, st, compiled, rng) -> EventOutcome | None` — returns `None` when no
    events (terminal). Applies the selected process atomically, advances `st.time_s` and
    `st.step`, updates vacancy bookkeeping/MSD.

BKL: `r_tot = Σ rate`; `u1, u2 = rng.random(2)`; `target = u1 * r_tot`; select first
index where `cumsum(rates) > target`; `dt = -ln(u2) / r_tot`. Apply: for each action,
assert `st.species[resolve] == before` then set `= after`; then call
`st.move_vacancy(lat, src=resolve(v_from_code), dst=resolve(v_to_code))`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_step.py
import pathlib
import sys

from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.engine.executor import step_once
from pylatkmc.engine.rng import make_rng
from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import (  # noqa: E402
    SPECIES,
    mini_lattice as _mini_lattice,
    px_hop_gated as _px_hop_gated,
)


def test_step_once_applies_hop_and_advances_time():
    lat = _mini_lattice()  # 0(vac)-1(Ni)-2(Ni)
    st = state_from_lattice(lat)
    compiled = compile_catalogue([_px_hop_gated(1)], SPECIES)
    rng = make_rng(7, 0)
    out = step_once(lat, st, compiled, rng)
    assert out is not None
    assert out.proc_id == 0 and out.site == 0
    assert out.dt > 0.0
    # vacancy moved from site 0 to site 1; species swapped.
    assert st.species[0] == 1  # Ni now at site 0
    assert st.species[1] == 0  # vacancy now at site 1
    assert st.vac_list == [1]
    assert st.time_s == out.dt
    assert st.step == 1
    assert st.mean_msd_A2() == 1.0


def test_step_once_returns_none_when_no_events():
    lat = _mini_lattice()
    st = state_from_lattice(lat)
    # empty catalogue -> no events -> step_once returns None.
    compiled = compile_catalogue([], SPECIES)
    assert step_once(lat, st, compiled, make_rng(1, 0)) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_step.py -v`
Expected: FAIL — `ImportError: cannot import name 'step_once'`.

- [ ] **Step 3: Add `EventOutcome` + `step_once` to `executor.py`**

```python
# append to pylatkmc/engine/executor.py
import math
from dataclasses import dataclass


@dataclass
class EventOutcome:
    proc_id: int
    site: int
    dt: float
    r_tot: float
    k_event: float
    Ea_eV: float


def step_once(
    lat: Lattice,
    st: State,
    compiled: list[CompiledProcess],
    rng: "np.random.Generator",
) -> EventOutcome | None:
    pairs, rates, r_tot = enumerate_events(lat, st, compiled)
    if not pairs or r_tot <= 0.0:
        return None
    u1, u2 = rng.random(), rng.random()
    target = u1 * r_tot
    cum = np.cumsum(rates)
    idx = int(np.searchsorted(cum, target, side="right"))
    if idx >= len(pairs):
        idx = len(pairs) - 1
    proc_id, site = pairs[idx]
    cp = compiled[proc_id]
    dt = -math.log(u2) / r_tot if u2 > 0.0 else 0.0

    ct = lat.coord_table[site]
    # verify + apply atomically
    targets = [(int(ct[code]), before, after) for code, before, after in cp.actions]
    for resolved, before, _after in targets:
        if int(st.species[resolved]) != before:
            raise RuntimeError(
                f"apply precondition failed for {cp.name!r} at site {site}: "
                f"site {resolved} is {int(st.species[resolved])}, expected {before}"
            )
    for resolved, _before, after in targets:
        st.species[resolved] = after

    src = int(ct[cp.v_from_code])
    dst = int(ct[cp.v_to_code])
    if src != dst:
        st.move_vacancy(lat, src=src, dst=dst)

    st.time_s += dt
    st.step += 1
    return EventOutcome(
        proc_id=proc_id, site=site, dt=dt, r_tot=r_tot, k_event=cp.rate, Ea_eV=cp.Ea_eV
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_step.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and type-check**

Run: `ruff check pylatkmc/engine/executor.py && mypy pylatkmc/engine/executor.py`
Expected: no errors. (Move the `import math` / `from dataclasses import dataclass`
to the top of the file if ruff's `E402` complains.)

- [ ] **Step 6: Commit**

```bash
git add pylatkmc/engine/executor.py tests/unit_py/test_engine_step.py
git commit -m "feat(engine): BKL step_once (select, apply, advance time, MSD)"
```

---

## Task 9: `io_ini.py` — parse `input.ini`

**Files:**
- Create: `pylatkmc/engine/io_ini.py`
- Test: `tests/unit_py/test_engine_io_ini.py`

**Interfaces:**
- Produces:
  - `@dataclass RunConfig`: `max_steps:int=1000000`, `max_time_s:float=0.0`,
    `sample_every:int=1000`, `summary_every:int=0`, `base_seed:int=42`,
    `ratetable_path:str=""`, `initconfig_path:str=""`, `output_root:str="./output"`,
    `temperature_K:float=500.0`, `rng_replay_path:str=""`, plus resolved absolute
    `Path` fields `initconfig_abs` and `output_root_abs`.
  - `parse_input_ini(path) -> RunConfig`.

INI semantics mirror `config_reader.c`: `[section]` headers, `key = value`, `#`/`;`
inline comments stripped, unknown keys ignored, relative `initconfig_path` /
`output_root` / `rng_replay_path` resolved against the INI file's directory (leading
`./` stripped); absolute paths untouched. `summary_every` is parsed but unused.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_io_ini.py
from pathlib import Path

from pylatkmc.engine.io_ini import parse_input_ini

REPO = Path(__file__).resolve().parents[2]
EXAMPLE_INI = REPO / "models/ni_fe_cr_v1/examples/input.ini"


def test_parse_example_input_ini():
    cfg = parse_input_ini(EXAMPLE_INI)
    assert cfg.max_steps == 100000
    assert cfg.sample_every == 100
    assert cfg.base_seed == 42
    assert cfg.temperature_K == 500.0
    assert cfg.initconfig_path == "config.kmcinit"
    # resolved relative to the INI directory
    assert cfg.initconfig_abs == (EXAMPLE_INI.parent / "config.kmcinit")
    assert cfg.output_root_abs == (EXAMPLE_INI.parent / "output")


def test_defaults_and_comment_stripping(tmp_path):
    ini = tmp_path / "x.ini"
    ini.write_text(
        "[run]\nbase_seed = 7  # the seed\n[physics]\ntemperature_K = 300\n",
        encoding="utf-8",
    )
    cfg = parse_input_ini(ini)
    assert cfg.base_seed == 7
    assert cfg.max_steps == 1000000  # default
    assert cfg.temperature_K == 300.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_io_ini.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.io_ini'`.

- [ ] **Step 3: Write `io_ini.py`**

```python
# pylatkmc/engine/io_ini.py
"""Parse the runtime's hand-rolled ``input.ini`` (mirrors runtime/src/io/config_reader.c)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunConfig:
    max_steps: int = 1_000_000
    max_time_s: float = 0.0
    sample_every: int = 1000
    summary_every: int = 0
    base_seed: int = 42
    ratetable_path: str = ""
    initconfig_path: str = ""
    output_root: str = "./output"
    temperature_K: float = 500.0
    rng_replay_path: str = ""
    initconfig_abs: Path = field(default_factory=Path)
    output_root_abs: Path = field(default_factory=Path)


def _strip_comment(value: str) -> str:
    for marker in ("#", ";"):
        i = value.find(marker)
        if i >= 0:
            value = value[:i]
    return value.strip()


def _resolve(base_dir: Path, raw: str) -> Path:
    raw = raw.strip()
    if raw.startswith("./"):
        raw = raw[2:]
    p = Path(raw)
    return p if p.is_absolute() else (base_dir / p)


def parse_input_ini(path: str | Path) -> RunConfig:
    path = Path(path)
    base_dir = path.parent
    cfg = RunConfig()
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        val = _strip_comment(raw)
        if section == "run":
            if key == "max_steps":
                cfg.max_steps = int(val)
            elif key == "max_time_s":
                cfg.max_time_s = float(val)
            elif key == "sample_every":
                cfg.sample_every = int(val)
            elif key == "summary_every":
                cfg.summary_every = int(val)
            elif key == "base_seed":
                cfg.base_seed = int(val)
        elif section == "paths":
            if key == "ratetable_path":
                cfg.ratetable_path = val
            elif key == "initconfig_path":
                cfg.initconfig_path = val
            elif key == "output_root":
                cfg.output_root = val
        elif section == "physics":
            if key == "temperature_K":
                cfg.temperature_K = float(val)
        elif section == "validation":
            if key == "rng_replay_path":
                cfg.rng_replay_path = val
    cfg.initconfig_abs = _resolve(base_dir, cfg.initconfig_path)
    cfg.output_root_abs = _resolve(base_dir, cfg.output_root)
    return cfg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_io_ini.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and type-check; commit**

```bash
ruff check pylatkmc/engine/io_ini.py && mypy pylatkmc/engine/io_ini.py
git add pylatkmc/engine/io_ini.py tests/unit_py/test_engine_io_ini.py
git commit -m "feat(engine): input.ini parser matching config_reader.c semantics"
```

---

## Task 10: `io_out.py` — output writers (C-compatible)

**Files:**
- Create: `pylatkmc/engine/io_out.py`
- Test: `tests/unit_py/test_engine_io_out.py`

**Interfaces:**
- Produces:
  - `write_summary_json(path, *, rank, n_sites, n_vac, temperature_K, base_seed, n_steps, total_time_s, mean_msd_A2, run_rc, n_procs) -> None`.
  - `aggregate_stats(per_replica: list[dict]) -> dict` — compute the aggregate fields
    (means + **sample** std, N−1; 0 if N≤1) from a list of per-replica stat dicts.
  - `write_aggregate_summary_json(path, agg) -> None`.

Field names/precisions per `runtime/src/mpi/replica.c`: per-replica `summary.json`
fields `rank, n_sites, n_vac, temperature_K(%.3f), base_seed, n_steps,
total_time_s(%.9e), mean_msd_A2(%.6e), run_rc, n_procs`. Aggregate fields
`n_replicas, n_success, n_failed, base_seed, temperature_K, n_procs, n_steps_mean(%.1f),
n_steps_std(%.1f), total_time_s_mean(%.9e), total_time_s_std(%.9e),
mean_msd_A2_mean(%.6e), mean_msd_A2_std(%.6e), replicas:[{rank, run_rc, n_steps,
total_time_s, mean_msd_A2}]`. (`json` numeric formatting need not be byte-identical to
C; the compare scripts read values, not bytes — but keep the same keys and types.)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit_py/test_engine_io_out.py
import json

from pylatkmc.engine.io_out import (
    aggregate_stats,
    write_aggregate_summary_json,
    write_summary_json,
)


def test_summary_json_has_expected_fields(tmp_path):
    p = tmp_path / "summary.json"
    write_summary_json(
        p, rank=0, n_sites=192, n_vac=1, temperature_K=500.0, base_seed=42,
        n_steps=100, total_time_s=1.23e-6, mean_msd_A2=4.5e0, run_rc=0, n_procs=358,
    )
    d = json.loads(p.read_text())
    assert d["rank"] == 0 and d["n_procs"] == 358
    assert d["mean_msd_A2"] == 4.5
    assert set(d) == {
        "rank", "n_sites", "n_vac", "temperature_K", "base_seed", "n_steps",
        "total_time_s", "mean_msd_A2", "run_rc", "n_procs",
    }


def test_aggregate_sample_std_and_keys(tmp_path):
    per = [
        {"rank": 0, "run_rc": 0, "n_steps": 100, "total_time_s": 1.0, "mean_msd_A2": 2.0},
        {"rank": 1, "run_rc": 0, "n_steps": 200, "total_time_s": 3.0, "mean_msd_A2": 4.0},
    ]
    agg = aggregate_stats(per)
    assert agg["n_replicas"] == 2 and agg["n_success"] == 2 and agg["n_failed"] == 0
    assert agg["mean_msd_A2_mean"] == 3.0
    # sample std (N-1) of [2,4] = sqrt(2) ~ 1.4142
    assert abs(agg["mean_msd_A2_std"] - 1.4142135623730951) < 1e-9
    p = tmp_path / "aggregate_summary.json"
    write_aggregate_summary_json(p, agg)
    back = json.loads(p.read_text())
    assert len(back["replicas"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_io_out.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pylatkmc.engine.io_out'`.

- [ ] **Step 3: Write `io_out.py`**

```python
# pylatkmc/engine/io_out.py
"""Output writers compatible with the C runtime's summary / aggregate JSON
(runtime/src/mpi/replica.c), so existing tools/compare_*.py work unchanged."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def write_summary_json(
    path: str | Path,
    *,
    rank: int,
    n_sites: int,
    n_vac: int,
    temperature_K: float,
    base_seed: int,
    n_steps: int,
    total_time_s: float,
    mean_msd_A2: float,
    run_rc: int,
    n_procs: int,
) -> None:
    d = {
        "rank": rank,
        "n_sites": n_sites,
        "n_vac": n_vac,
        "temperature_K": temperature_K,
        "base_seed": base_seed,
        "n_steps": n_steps,
        "total_time_s": total_time_s,
        "mean_msd_A2": mean_msd_A2,
        "run_rc": run_rc,
        "n_procs": n_procs,
    }
    Path(path).write_text(json.dumps(d, indent=2), encoding="utf-8")


def _mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean = sum(xs) / n
    if n <= 1:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)  # sample std (N-1)
    return mean, math.sqrt(var)


def aggregate_stats(per_replica: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(per_replica)
    n_success = sum(1 for r in per_replica if r["run_rc"] == 0)
    steps_mean, steps_std = _mean_std([float(r["n_steps"]) for r in per_replica])
    t_mean, t_std = _mean_std([float(r["total_time_s"]) for r in per_replica])
    m_mean, m_std = _mean_std([float(r["mean_msd_A2"]) for r in per_replica])
    return {
        "n_replicas": n,
        "n_success": n_success,
        "n_failed": n - n_success,
        "base_seed": per_replica[0]["base_seed"] if per_replica else 0,
        "temperature_K": per_replica[0]["temperature_K"] if per_replica else 0.0,
        "n_procs": per_replica[0]["n_procs"] if per_replica else 0,
        "n_steps_mean": steps_mean,
        "n_steps_std": steps_std,
        "total_time_s_mean": t_mean,
        "total_time_s_std": t_std,
        "mean_msd_A2_mean": m_mean,
        "mean_msd_A2_std": m_std,
        "replicas": [
            {
                "rank": r["rank"],
                "run_rc": r["run_rc"],
                "n_steps": r["n_steps"],
                "total_time_s": r["total_time_s"],
                "mean_msd_A2": r["mean_msd_A2"],
            }
            for r in per_replica
        ],
    }


def write_aggregate_summary_json(path: str | Path, agg: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(agg, indent=2), encoding="utf-8")
```

Note: `aggregate_stats` reads `base_seed`/`temperature_K`/`n_procs` from each per-replica
dict; the runner (Task 11) must include those keys in the dicts it passes (in addition to
the five keys echoed into `replicas`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_engine_io_out.py -v`
Expected: PASS.

- [ ] **Step 5: Lint, type-check, commit**

```bash
ruff check pylatkmc/engine/io_out.py && mypy pylatkmc/engine/io_out.py
git add pylatkmc/engine/io_out.py tests/unit_py/test_engine_io_out.py
git commit -m "feat(engine): C-compatible summary + aggregate JSON writers"
```

---

## Task 11: `runner.py` + CLI `run` — single + ensemble run (M2/M3)

**Files:**
- Create: `pylatkmc/engine/runner.py`
- Modify: `pylatkmc/cli.py` (add `run` subcommand)
- Modify: `pylatkmc/engine/__init__.py` (re-export `run`, `read_kmcinit`, `load_catalogue`)
- Test: `tests/unit_py/test_engine_run.py`

**Interfaces:**
- Consumes: `io_ini.parse_input_ini`, `lattice.read_kmcinit`, `catalogue.load_catalogue`
  + `compile_catalogue`, `state.state_from_lattice`, `executor.step_once`,
  `rng.make_rng`, `io_out.write_summary_json` + `aggregate_stats` +
  `write_aggregate_summary_json`, `loader.load`.
- Produces:
  - `run_replica(lat, compiled, cfg, rank, n_procs, out_dir) -> dict` — run one replica
    to termination, write `replica_<rank:04d>/summary.json`, return the per-replica stat
    dict (including `base_seed`, `temperature_K`, `n_procs`).
  - `run(spec_path, input_ini, n_replicas=1, family_csv=None) -> Path` — orchestrate all
    replicas, write `aggregate_summary.json`, return its path.

Termination mirrors `kmc.c`: stop when `step >= max_steps`, or `max_time_s > 0 and
time_s >= max_time_s`, or `step_once` returns `None`.

- [ ] **Step 1: Write the failing test (end-to-end on the committed example)**

```python
# tests/unit_py/test_engine_run.py
import json
from pathlib import Path

import pytest

from pylatkmc.engine.runner import run

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml"
CATALOGUE = SPEC.parent / "generated" / "catalogue.json"
KMCINIT = REPO / "models/ni_fe_cr_v1/examples/config.kmcinit"

pytestmark = pytest.mark.skipif(
    not CATALOGUE.exists(),
    reason="needs committed generated/catalogue.json (run export-catalogue once)",
)


def test_run_two_replicas_produces_aggregate(tmp_path):
    ini = tmp_path / "input.ini"
    ini.write_text(
        "[run]\nmax_steps = 200\nsample_every = 0\nbase_seed = 42\n"
        "[paths]\n"
        f"initconfig_path = {KMCINIT}\n"
        f"output_root = {tmp_path / 'output'}\n"
        "[physics]\ntemperature_K = 500.0\n",
        encoding="utf-8",
    )
    agg_path = run(SPEC, ini, n_replicas=2)
    agg = json.loads(Path(agg_path).read_text())
    assert agg["n_replicas"] == 2
    assert agg["n_success"] == 2
    assert "mean_msd_A2_mean" in agg and "total_time_s_mean" in agg
    assert agg["total_time_s_mean"] > 0.0
    # determinism: same call → identical aggregate MSD
    agg2 = json.loads(Path(run(SPEC, ini, n_replicas=2)).read_text())
    assert agg2["mean_msd_A2_mean"] == agg["mean_msd_A2_mean"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_engine_run.py -v`
Expected: either SKIP (if `catalogue.json` not yet generated) or FAIL —
`ModuleNotFoundError: No module named 'pylatkmc.engine.runner'`. If it SKIPs, first
generate the catalogue on a checkout where the CSV resolves:
`pylatkmc-gen export-catalogue models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml` and commit
`models/ni_fe_cr_v1/generated/catalogue.json`, then re-run.

- [ ] **Step 3: Write `runner.py`**

```python
# pylatkmc/engine/runner.py
"""Orchestrate a Python-engine run: load model + lattice, loop replicas, write outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pylatkmc.engine.catalogue import CompiledProcess, compile_catalogue, load_catalogue
from pylatkmc.engine.executor import step_once
from pylatkmc.engine.io_ini import RunConfig, parse_input_ini
from pylatkmc.engine.io_out import (
    aggregate_stats,
    write_aggregate_summary_json,
    write_summary_json,
)
from pylatkmc.engine.lattice import Lattice, read_kmcinit
from pylatkmc.engine.rng import make_rng
from pylatkmc.engine.state import state_from_lattice
from pylatkmc.loader import load


def run_replica(
    lat: Lattice,
    compiled: list[CompiledProcess],
    cfg: RunConfig,
    rank: int,
    n_procs: int,
    out_dir: Path,
) -> dict[str, Any]:
    st = state_from_lattice(lat)
    rng = make_rng(cfg.base_seed, rank)
    run_rc = 0
    while st.step < cfg.max_steps:
        if cfg.max_time_s > 0.0 and st.time_s >= cfg.max_time_s:
            break
        if step_once(lat, st, compiled, rng) is None:
            break  # no events (trapped)
    rep_dir = out_dir / f"replica_{rank:04d}"
    rep_dir.mkdir(parents=True, exist_ok=True)
    write_summary_json(
        rep_dir / "summary.json",
        rank=rank, n_sites=lat.n_sites, n_vac=st.n_vac,
        temperature_K=cfg.temperature_K, base_seed=cfg.base_seed,
        n_steps=st.step, total_time_s=st.time_s, mean_msd_A2=st.mean_msd_A2(),
        run_rc=run_rc, n_procs=n_procs,
    )
    return {
        "rank": rank, "run_rc": run_rc, "n_steps": st.step,
        "total_time_s": st.time_s, "mean_msd_A2": st.mean_msd_A2(),
        "base_seed": cfg.base_seed, "temperature_K": cfg.temperature_K,
        "n_procs": n_procs,
    }


def run(
    spec_path: str | Path,
    input_ini: str | Path,
    n_replicas: int = 1,
    family_csv: str | Path | None = None,
) -> Path:
    spec_path = Path(spec_path).resolve()
    spec = load(spec_path)
    cfg = parse_input_ini(input_ini)
    lat = read_kmcinit(cfg.initconfig_abs)
    processes = load_catalogue(spec_path, family_csv=family_csv)
    compiled = compile_catalogue(processes, list(spec.species))
    n_procs = len(compiled)
    out_dir = cfg.output_root_abs
    out_dir.mkdir(parents=True, exist_ok=True)
    per = [
        run_replica(lat, compiled, cfg, rank, n_procs, out_dir)
        for rank in range(n_replicas)
    ]
    agg = aggregate_stats(per)
    agg_path = out_dir / "aggregate_summary.json"
    write_aggregate_summary_json(agg_path, agg)
    return agg_path
```

- [ ] **Step 4: Re-export from `__init__.py` and add the CLI `run` subcommand**

In `pylatkmc/engine/__init__.py`, after the docstring:

```python
from pylatkmc.engine.catalogue import load_catalogue  # noqa: E402,F401
from pylatkmc.engine.lattice import read_kmcinit  # noqa: E402,F401
from pylatkmc.engine.runner import run  # noqa: E402,F401

__all__ = ["load_catalogue", "read_kmcinit", "run"]
```

In `pylatkmc/cli.py`, add the handler:

```python
def cmd_run(args: argparse.Namespace) -> int:
    if args.backend != "python":
        print(
            f"pylatkmc-gen run: backend {args.backend!r} not supported "
            "(only 'python'; use mpirun for the C backend)",
            file=sys.stderr,
        )
        return 2
    from .engine.runner import run

    spec_path = Path(args.spec).resolve()
    agg = run(spec_path, args.input, n_replicas=args.replicas, family_csv=args.family_csv)
    print(f"pylatkmc-gen run: wrote {agg}")
    return 0
```

and register it in `_make_parser`:

```python
    p_run = sub.add_parser("run", help="Run a model with the pure-Python engine")
    p_run.add_argument("spec", help="Path to .kmcspec.toml")
    p_run.add_argument("input", help="Path to input.ini")
    p_run.add_argument("--backend", default="python", choices=["python"])
    p_run.add_argument("--replicas", type=int, default=1, help="Number of replicas")
    p_run.add_argument("--family-csv", default=None, help="Override the family CSV path")
    p_run.set_defaults(func=cmd_run)
```

- [ ] **Step 5: Run the test (now non-skipped if catalogue committed) + full suite**

Run: `python -m pytest tests/unit_py/test_engine_run.py -v && python -m pytest tests/unit_py -q`
Expected: PASS (or documented SKIP if `catalogue.json` is intentionally not committed yet).

- [ ] **Step 6: Lint, type-check, commit**

```bash
ruff check pylatkmc/engine/runner.py pylatkmc/cli.py pylatkmc/engine/__init__.py
mypy pylatkmc/engine/runner.py
git add pylatkmc/engine/runner.py pylatkmc/cli.py pylatkmc/engine/__init__.py tests/unit_py/test_engine_run.py
git commit -m "feat(engine): replica runner + pylatkmc-gen run (M3 complete)"
```

---

## Task 12: `tools/compare_py_vs_c.py` — statistical cross-engine gate (M4)

**Files:**
- Create: `tools/compare_py_vs_c.py`
- Test: `tests/unit_py/test_compare_py_vs_c.py` (unit-tests the comparison math only)

**Interfaces:**
- Produces:
  - `diffusivity(mean_msd_A2: float, total_time_s: float) -> float` = `MSD / (6 * t)`
    (`0.0` if `t<=0`).
  - `relative_diff(a: float, b: float) -> float` = `abs(a-b)/max(abs(a),abs(b),eps)`.
  - `compare(py_agg: dict, c_agg: dict, tol: float) -> tuple[bool, str]` — compare D from
    two `aggregate_summary.json` dicts; pass iff `relative_diff <= tol`.
  - A `main()` that runs the Python engine and (if a built binary + mpirun exist) the C
    engine on the same `input.ini`, then asserts agreement. When the binary or MPI is
    absent it **skips with a clear message** (mirrors the existing maintainer-only
    cross-engine scripts), it does not fail.

The script must NOT require `motif_counts_sum` (stale) and must NOT hardcode
`/Users/...` paths — take paths as CLI args.

- [ ] **Step 1: Write the failing test (math only — no binary needed)**

```python
# tests/unit_py/test_compare_py_vs_c.py
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
import compare_py_vs_c as cmp  # noqa: E402


def test_diffusivity_and_relative_diff():
    assert cmp.diffusivity(6.0, 1.0) == 1.0
    assert cmp.diffusivity(1.0, 0.0) == 0.0
    assert cmp.relative_diff(1.0, 1.0) == 0.0
    assert abs(cmp.relative_diff(1.0, 1.1) - 0.0909090909) < 1e-6


def test_compare_passes_within_tol_fails_outside():
    py = {"mean_msd_A2_mean": 6.0, "total_time_s_mean": 1.0}
    c_ok = {"mean_msd_A2_mean": 6.3, "total_time_s_mean": 1.0}
    c_bad = {"mean_msd_A2_mean": 12.0, "total_time_s_mean": 1.0}
    ok, _ = cmp.compare(py, c_ok, tol=0.10)
    assert ok is True
    bad, _ = cmp.compare(py, c_bad, tol=0.10)
    assert bad is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_py/test_compare_py_vs_c.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compare_py_vs_c'`.

- [ ] **Step 3: Write `tools/compare_py_vs_c.py`**

```python
# tools/compare_py_vs_c.py
"""Statistical cross-engine gate: run the same input.ini through the pure-Python
engine and (when available) the compiled C+MPI binary, then assert D = MSD/(6t)
agrees within a relative tolerance.

Skips cleanly (rc 0, message) when the C binary or mpirun is unavailable — this is a
maintainer-machine check, mirroring the existing cross-engine validation scripts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_EPS = 1e-300


def diffusivity(mean_msd_A2: float, total_time_s: float) -> float:
    if total_time_s <= 0.0:
        return 0.0
    return mean_msd_A2 / (6.0 * total_time_s)


def relative_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), _EPS)


def compare(py_agg: dict, c_agg: dict, tol: float) -> tuple[bool, str]:
    d_py = diffusivity(py_agg["mean_msd_A2_mean"], py_agg["total_time_s_mean"])
    d_c = diffusivity(c_agg["mean_msd_A2_mean"], c_agg["total_time_s_mean"])
    rd = relative_diff(d_py, d_c)
    msg = f"D_py={d_py:.6e}  D_c={d_c:.6e}  rel_diff={rd:.4f}  tol={tol:.4f}"
    return rd <= tol, msg


def _run_python_engine(spec: Path, input_ini: Path, replicas: int) -> dict:
    # import the package run() to avoid a subprocess round-trip.
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from pylatkmc.engine.runner import run

    agg_path = run(spec, input_ini, n_replicas=replicas)
    return json.loads(Path(agg_path).read_text())


def _run_c_engine(binary: Path, input_ini: Path, replicas: int) -> dict | None:
    mpirun = shutil.which("mpirun")
    if mpirun is None or not binary.exists():
        return None
    out_root = input_ini.parent / "output"
    subprocess.run(
        [mpirun, "--oversubscribe", "-n", str(replicas), str(binary), str(input_ini)],
        cwd=input_ini.parent, check=True,
    )
    return json.loads((out_root / "aggregate_summary.json").read_text())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Python-vs-C statistical cross-engine gate")
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--input", required=True, type=Path, help="input.ini")
    ap.add_argument("--binary", type=Path, default=None, help="compiled C binary")
    ap.add_argument("--replicas", type=int, default=4)
    ap.add_argument("--tol", type=float, default=0.15, help="relative-D tolerance")
    args = ap.parse_args(argv)

    py_agg = _run_python_engine(args.spec, args.input, args.replicas)
    c_agg = _run_c_engine(args.binary, args.input, args.replicas) if args.binary else None
    if c_agg is None:
        print("SKIP: C binary or mpirun unavailable; ran Python engine only.")
        print(f"  D_py={diffusivity(py_agg['mean_msd_A2_mean'], py_agg['total_time_s_mean']):.6e}")
        return 0
    ok, msg = compare(py_agg, c_agg, args.tol)
    print(("PASS: " if ok else "FAIL: ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_py/test_compare_py_vs_c.py -v`
Expected: PASS.

- [ ] **Step 5: (maintainer machine, optional) run the real cross-engine gate**

Run:
```bash
pylatkmc-gen build models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml
cmake -B build -DMODEL=ni_fe_cr_v1 && cmake --build build -j 4
python tools/compare_py_vs_c.py \
  --spec models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml \
  --input models/ni_fe_cr_v1/examples/input.ini \
  --binary build/pylatkmc_ni_fe_cr_v1 --replicas 4 --tol 0.15
```
Expected: `PASS: D_py=...  D_c=...  rel_diff=...`. Calibrate `--tol` to the observed
replica spread (raise replicas / steps to tighten).

- [ ] **Step 6: Commit**

```bash
git add tools/compare_py_vs_c.py tests/unit_py/test_compare_py_vs_c.py
git commit -m "feat(tools): statistical Python-vs-C cross-engine gate (M4)"
```

---

## Final verification

- [ ] **Run the whole Python suite:** `python -m pytest tests/unit_py -q` — all pass
  (engine tests + no regressions in existing C-binding tests).
- [ ] **Lint + type-check the package:** `ruff check pylatkmc/ && mypy pylatkmc/engine/`
  — clean.
- [ ] **Smoke-run the engine** on the committed example (if `catalogue.json` committed):
  `pylatkmc-gen run models/ni_fe_cr_v1/ni_fe_cr_v1.kmcspec.toml models/ni_fe_cr_v1/examples/input.ini --replicas 2`
  then inspect `models/ni_fe_cr_v1/examples/output/aggregate_summary.json`.
- [ ] **Update `README.md`** with a short "Pure-Python engine" section (how to
  `export-catalogue` once, then `run --backend=python`), and note it is a
  statistically-validated reference backend.

## Self-review notes (coverage map spec → tasks)

- Spec §3 modules → Tasks 1–11 (coords, lattice, catalogue, state, executor, rng,
  io_ini, io_out, runner, cli).
- Spec §4 fidelity rules → Task 5 (eligibility, exact-count shell, stub) + Task 8 (BKL
  formula, atomic apply, MSD).
- Spec §5 statistical parity → Task 7 (numpy RNG) + Task 12 (tolerance gate).
- Spec §3 catalogue sourcing / §6 YAGNI → Task 3 + Task 6 (`export-catalogue`,
  JSON fallback; no `.kmcrt`, no Bystanders → `compile_catalogue` raises on non-float).
- Spec §8 hazards → Task 2 (payload order from `.c`, not `.h`), Task 3 (CSV-optional),
  Task 12 (no `motif_counts_sum`, no hardcoded paths).
- Spec §9 milestones → M1 (Tasks 1–6), M2 (Tasks 7–8), M3 (Tasks 9–11), M4 (Task 12).
