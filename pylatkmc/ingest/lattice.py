"""Integer FCC embedding and the (100)-slab D4h point group (Phase A, Agent A1).

Pure integer / ``numpy`` geometry: the common substrate every identity and
projection module builds on (contract Phase A, section 3; ``FINAL_DESIGN`` sections
1.1-1.2). No pandas, no identity logic, no rates.

FCC with ``a ~ 3.52 A`` is the **even-parity sublattice** of a simple-cubic grid of
spacing ``h = a/2``::

    Site = { (i, j, k) in Z^3 : i + j + k = 0 (mod 2) }
    Cartesian(i, j, k) = origin + h * (i, j, k)          # R = I (frame-aligned)

The ideal (100) slab point group is **D4h (order 16)** -- the subgroup of O_h that
fixes the z-axis up to sign -- represented here as 16 integer 3x3 signed-permutation
matrices (8 signed xy-permutations x 2 z-signs). Every op preserves even parity and
fixes z up to sign; a closure assertion at import pins group validity.

Load-DAG note (contract section 0.2): ``lattice.py`` may import only ``numpy`` and the
standard library at module level. ``Occ`` (owned by ``event_class.py``) is referenced
only under ``TYPE_CHECKING`` for annotations; the two colour-invariant occupancy
sentinels needed by :func:`coordination` are mirrored as private ints (see
``_EMPTY_CODE`` / ``_OUTSIDE_CODE``) because event_class cannot be imported here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import permutations, product
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from pylatkmc.ingest.event_class import Occ

# ---------------------------------------------------------------------------
# Type aliases and constants
# ---------------------------------------------------------------------------

#: Integer FCC lattice offset ``(i, j, k)``. Defined locally because ``lattice.py``
#: sits at the base of the load DAG (contract section 0.2) and cannot import the
#: identical alias from ``event_class`` (contract section 2.2).
Offset = tuple[int, int, int]

#: One integer 3x3 matrix (row-major nested tuple).
IntMat3 = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]

#: The 3x3 integer identity.
IDENTITY: IntMat3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

# Colour-invariant occupancy sentinels (mirror ``Occ.EMPTY`` / ``Occ.OUTSIDE`` from
# event_class section 2.1 and FINAL_DESIGN section 1.2). Mirrored, not imported,
# because ``lattice.py`` must depend on numpy + stdlib only (contract section 0.2).
_EMPTY_CODE = 0
_OUTSIDE_CODE = 255


# ---------------------------------------------------------------------------
# Integer matrix algebra
# ---------------------------------------------------------------------------

def matmul3(A: IntMat3, B: IntMat3) -> IntMat3:
    """Return the integer matrix product ``A @ B`` for two 3x3 integer matrices."""
    r0 = (
        A[0][0] * B[0][0] + A[0][1] * B[1][0] + A[0][2] * B[2][0],
        A[0][0] * B[0][1] + A[0][1] * B[1][1] + A[0][2] * B[2][1],
        A[0][0] * B[0][2] + A[0][1] * B[1][2] + A[0][2] * B[2][2],
    )
    r1 = (
        A[1][0] * B[0][0] + A[1][1] * B[1][0] + A[1][2] * B[2][0],
        A[1][0] * B[0][1] + A[1][1] * B[1][1] + A[1][2] * B[2][1],
        A[1][0] * B[0][2] + A[1][1] * B[1][2] + A[1][2] * B[2][2],
    )
    r2 = (
        A[2][0] * B[0][0] + A[2][1] * B[1][0] + A[2][2] * B[2][0],
        A[2][0] * B[0][1] + A[2][1] * B[1][1] + A[2][2] * B[2][1],
        A[2][0] * B[0][2] + A[2][1] * B[1][2] + A[2][2] * B[2][2],
    )
    return (r0, r1, r2)


def _transpose(m: IntMat3) -> IntMat3:
    """Return the transpose of a 3x3 integer matrix (= inverse for signed perms)."""
    return (
        (m[0][0], m[1][0], m[2][0]),
        (m[0][1], m[1][1], m[2][1]),
        (m[0][2], m[1][2], m[2][2]),
    )


@dataclass(frozen=True)
class SymOp:
    """A D4h symmetry operation: its canonical index and its integer matrix."""

    index: int  # 0..15, position in D4H_OPS (the stable tie-break key)
    mat: IntMat3


def apply_op(op: SymOp | IntMat3, v: Offset) -> Offset:
    """Apply a D4h op (``SymOp`` or raw 3x3 matrix) to an integer offset ``v``."""
    m = op.mat if isinstance(op, SymOp) else op
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


# ---------------------------------------------------------------------------
# D4h group construction (16 integer 3x3 matrices, fixed order)
# ---------------------------------------------------------------------------

def _build_d4h() -> tuple[IntMat3, ...]:
    """Build the 16 D4h ops as integer signed-permutation matrices in fixed order.

    Block form: a 2x2 signed xy-permutation (the 8 symmetries of the square)
    direct-product with ``z -> +/- z``. Index 0 is the identity.
    """
    xy: list[list[list[int]]] = []
    for px, py in ((0, 1), (1, 0)):  # x-row -> col px ; y-row -> col py
        for sx in (1, -1):
            for sy in (1, -1):
                m = [[0, 0], [0, 0]]
                m[0][px] = sx
                m[1][py] = sy
                xy.append(m)  # 8 signed 2x2 perms
    ops: list[IntMat3] = []
    for m2 in xy:
        for sz in (1, -1):
            ops.append(
                (
                    (m2[0][0], m2[0][1], 0),
                    (m2[1][0], m2[1][1], 0),
                    (0, 0, sz),
                )
            )  # 8 * 2 = 16
    return tuple(ops)


#: The 16 D4h ops as integer 3x3 matrices; index 0..15 is the canonical op order.
D4H_OPS: tuple[IntMat3, ...] = _build_d4h()

#: Matrix -> canonical index, for O(1) ``compose`` / ``op_inverse`` (lookup only).
_INDEX_OF: dict[IntMat3, int] = {m: i for i, m in enumerate(D4H_OPS)}

#: ``SymOp`` wrappers around ``D4H_OPS``, index-ordered.
D4H: tuple[SymOp, ...] = tuple(SymOp(index=i, mat=m) for i, m in enumerate(D4H_OPS))


def compose(a: SymOp, b: SymOp) -> SymOp:
    """Return the composite op ``a . b`` (apply ``b`` first, then ``a``)."""
    return D4H[_INDEX_OF[matmul3(a.mat, b.mat)]]


def op_inverse(a: SymOp) -> SymOp:
    """Return the inverse of ``a`` (the transpose; signed perms are orthogonal)."""
    return D4H[_INDEX_OF[_transpose(a.mat)]]


def _is_signed_permutation(m: IntMat3) -> bool:
    """True iff ``m`` has exactly one entry of +/-1 in each row and each column."""
    for i in range(3):
        row_nz = [m[i][j] for j in range(3) if m[i][j] != 0]
        col_nz = [m[j][i] for j in range(3) if m[j][i] != 0]
        if len(row_nz) != 1 or row_nz[0] not in (1, -1):
            return False
        if len(col_nz) != 1 or col_nz[0] not in (1, -1):
            return False
    return True


def _verify_group() -> None:
    """Assert D4h validity at import (order 16, closed, signed-perm, z-fixed, inverses).

    This is the group-validity guarantee required by contract section 3.1.
    """
    seen = set(D4H_OPS)
    assert len(seen) == 16, "D4H_OPS must contain 16 distinct matrices"
    assert len(D4H) == 16
    for m in D4H_OPS:
        # signed permutation (one +/-1 per row and per column)
        assert _is_signed_permutation(m), f"not a signed permutation: {m}"
        # z fixed up to sign: last row is (0, 0, +/-1) and the z column is (0, 0, *)
        assert m[2] == (0, 0, 1) or m[2] == (0, 0, -1), f"z-row not fixed: {m}"
        assert m[0][2] == 0 and m[1][2] == 0, f"z-column not clean: {m}"
    # even-parity preservation on representative even and odd offsets
    for v in ((1, 1, 0), (2, 0, 0), (2, 1, 1), (1, 0, 0), (0, 0, 1)):
        s = (v[0] + v[1] + v[2]) % 2
        for op in D4H_OPS:
            w = apply_op(op, v)
            assert (w[0] + w[1] + w[2]) % 2 == s, "parity not preserved"
    # closed under matmul3
    for a in D4H_OPS:
        for b in D4H_OPS:
            assert matmul3(a, b) in seen, "group not closed under matmul3"
    # inverses present (transpose is the inverse and lives in the group)
    for a in D4H_OPS:
        at = _transpose(a)
        assert at in seen, "inverse missing from group"
        assert matmul3(a, at) == IDENTITY, "transpose is not the inverse"


_verify_group()


# ---------------------------------------------------------------------------
# FCC embedding: parity, neighbour shells, snapping, coordination
# ---------------------------------------------------------------------------

def is_even_parity(off: Offset) -> bool:
    """True iff ``(i + j + k)`` is even, i.e. ``off`` is an FCC (even-sublattice) site."""
    return (off[0] + off[1] + off[2]) % 2 == 0


def _gen_shell(nonzero: tuple[int, ...]) -> tuple[Offset, ...]:
    """All distinct permutations/sign-flips of a nonzero magnitude pattern.

    ``nonzero`` lists the absolute values placed on the *nonzero* axes (the
    remaining axes are 0). Returned sorted for a deterministic canonical order.
    """
    offs: set[Offset] = set()
    n_nz = len(nonzero)
    for axes in permutations(range(3), n_nz):
        for signs in product((1, -1), repeat=n_nz):
            v = [0, 0, 0]
            for a, mag, sg in zip(axes, nonzero, signs, strict=True):
                v[a] = sg * mag
            offs.add((v[0], v[1], v[2]))
    return tuple(sorted(offs))


#: 1NN "12-star": perms/signs of ``(+/-1, +/-1, 0)`` -- 12 offsets, distance ``a/sqrt(2)``.
NN12_OFFSETS: tuple[Offset, ...] = _gen_shell((1, 1))

#: 2NN: perms of ``(+/-2, 0, 0)`` -- 6 offsets, distance ``a``.
NN2_OFFSETS: tuple[Offset, ...] = _gen_shell((2,))

#: 3NN: perms/signs of ``(+/-2, +/-1, +/-1)`` -- 24 offsets, distance ``a*sqrt(6)/2``.
NN3_OFFSETS: tuple[Offset, ...] = _gen_shell((2, 1, 1))


def shell_offsets(shell: int) -> tuple[Offset, ...]:
    """Return the integer offset table for neighbour ``shell`` in ``{1, 2, 3}``."""
    if shell == 1:
        return NN12_OFFSETS
    if shell == 2:
        return NN2_OFFSETS
    if shell == 3:
        return NN3_OFFSETS
    raise ValueError(f"shell must be 1, 2, or 3; got {shell}")


def cartesian(off: Offset, origin: np.ndarray, h: float) -> np.ndarray:
    """Map an integer offset to Cartesian coordinates ``origin + h * (i, j, k)``."""
    return origin + h * np.asarray(off, dtype=float)


def round_to_even_parity(u: np.ndarray) -> Offset:
    """Return the nearest even-parity FCC site to a real lattice-unit point ``u``.

    Round ``u`` to the nearest integer site; if the parity is odd, flip the
    coordinate with the largest rounding error to its second-nearest integer (the
    minimal-cost single change that restores even parity -- the FCC Voronoi cell is
    the rhombic dodecahedron, so the nearest even site differs by at most one such
    flip; contract section 3.2).
    """
    r = np.rint(u).astype(int)
    if int(r.sum()) % 2 == 0:
        return (int(r[0]), int(r[1]), int(r[2]))
    err = np.abs(u - r)
    ax = int(np.argmax(err))
    step = 1 if float(u[ax]) - float(r[ax]) >= 0.0 else -1
    out = [int(r[0]), int(r[1]), int(r[2])]
    out[ax] += step
    return (out[0], out[1], out[2])


def _ranked_even_sites(u: np.ndarray) -> list[Offset]:
    """Even-parity sites in a +/-2 box around ``round(u)``, nearest first.

    Sorted by ``(squared_distance, offset)`` for a deterministic total order.
    """
    base = np.rint(u).astype(int)
    scored: list[tuple[float, Offset]] = []
    for di in range(-2, 3):
        for dj in range(-2, 3):
            for dk in range(-2, 3):
                s = (int(base[0]) + di, int(base[1]) + dj, int(base[2]) + dk)
                if (s[0] + s[1] + s[2]) % 2 != 0:
                    continue
                d2 = (
                    (s[0] - float(u[0])) ** 2
                    + (s[1] - float(u[1])) ** 2
                    + (s[2] - float(u[2])) ** 2
                )
                scored.append((d2, s))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [s for _, s in scored]


def second_nearest_even_parity(u: np.ndarray) -> Offset:
    """Return the runner-up even-parity site to ``u`` (for the hysteresis test).

    The second-nearest even site by Euclidean distance, distinct from
    :func:`round_to_even_parity` (contract section 3.2 / FINAL_DESIGN section 2.2).
    """
    first = round_to_even_parity(u)
    for s in _ranked_even_sites(u):
        if s != first:
            return s
    raise ValueError("no runner-up even-parity site found near u")


def coordination(occ_of: Callable[[Offset], Occ], site: Offset) -> int:
    """Count occupied entries among ``site``'s 12-star (the dealloying eligibility test).

    An entry counts as occupied when ``occ_of`` returns anything other than the two
    colour-invariant sentinels ``EMPTY`` (0) and ``OUTSIDE`` (255) -- so a bulk FCC
    site coordinates 12, a (100) surface site (4 in-layer + 4 below) coordinates 8.
    """
    total = 0
    for off in NN12_OFFSETS:
        nb = (site[0] + off[0], site[1] + off[1], site[2] + off[2])
        code = int(occ_of(nb))
        if code != _EMPTY_CODE and code != _OUTSIDE_CODE:
            total += 1
    return total
