"""Unit tests for ``pylatkmc.ingest.lattice`` (Agent A1, contract section 11.1).

Pure-math tests: no ingest extras required (numpy only). Covers the D4h group
(closure/order-16, parity preservation, z-fixed-up-to-sign), the FCC neighbour
shells and (100) layering/coordination, and the even-parity snapping helpers.
"""

from __future__ import annotations

import numpy as np
import pytest

from pylatkmc.ingest.lattice import (
    D4H,
    D4H_OPS,
    IDENTITY,
    NN2_OFFSETS,
    NN3_OFFSETS,
    NN12_OFFSETS,
    apply_op,
    cartesian,
    compose,
    coordination,
    is_even_parity,
    matmul3,
    op_inverse,
    round_to_even_parity,
    second_nearest_even_parity,
    shell_offsets,
)

# Physical lattice constants (contract section 0.4; defined test-locally because the
# single source lives in event_class, which lattice may not import).
A_NOMINAL = 3.52
H = A_NOMINAL / 2.0


def _is_signed_permutation(m: tuple) -> bool:
    for i in range(3):
        row_nz = [m[i][j] for j in range(3) if m[i][j] != 0]
        col_nz = [m[j][i] for j in range(3) if m[j][i] != 0]
        if len(row_nz) != 1 or row_nz[0] not in (1, -1):
            return False
        if len(col_nz) != 1 or col_nz[0] not in (1, -1):
            return False
    return True


# ---------------------------------------------------------------------------
# D4h group: closure, order 16, signed permutations, inverses
# ---------------------------------------------------------------------------

def test_group_order_16_distinct() -> None:
    assert len(D4H_OPS) == 16
    assert len(set(D4H_OPS)) == 16
    assert len(D4H) == 16
    # SymOp indices match D4H_OPS positions.
    for i, op in enumerate(D4H):
        assert op.index == i
        assert op.mat == D4H_OPS[i]
    # Index 0 is the identity.
    assert D4H_OPS[0] == IDENTITY


def test_every_op_is_signed_permutation() -> None:
    for m in D4H_OPS:
        assert _is_signed_permutation(m)


def test_group_closed_under_matmul3() -> None:
    seen = set(D4H_OPS)
    for a in D4H_OPS:
        for b in D4H_OPS:
            assert matmul3(a, b) in seen


def test_inverses_present_and_consistent() -> None:
    for op in D4H:
        inv = op_inverse(op)
        assert inv.mat in set(D4H_OPS)
        # a . a^-1 == identity, both as matrix product and as composed SymOp.
        assert matmul3(op.mat, inv.mat) == IDENTITY
        assert compose(op, inv).mat == IDENTITY
        assert compose(op, inv).index == 0


def test_compose_matches_sequential_application() -> None:
    vecs = [(1, 1, 0), (2, 0, 0), (2, 1, 1), (3, -1, 2)]
    for a in D4H:
        for b in D4H:
            ab = compose(a, b)
            for v in vecs:
                # compose(a, b) applies b first, then a.
                assert apply_op(ab, v) == apply_op(a, apply_op(b, v))


def test_matmul3_identity_is_neutral() -> None:
    for m in D4H_OPS:
        assert matmul3(IDENTITY, m) == m
        assert matmul3(m, IDENTITY) == m


# ---------------------------------------------------------------------------
# D4h structural guarantees: parity preservation and z fixed up to sign
# ---------------------------------------------------------------------------

def test_parity_preserved_over_random_even_offsets() -> None:
    rng = np.random.default_rng(20240717)
    for _ in range(1000):
        v = [int(x) for x in rng.integers(-5, 6, size=3)]
        if (v[0] + v[1] + v[2]) % 2 != 0:  # force even parity
            v[0] += 1
        vt = (v[0], v[1], v[2])
        assert is_even_parity(vt)
        for op in D4H_OPS:
            w = apply_op(op, vt)
            assert (w[0] + w[1] + w[2]) % 2 == 0


def test_z_fixed_up_to_sign() -> None:
    for m in D4H_OPS:
        assert m[2] in ((0, 0, 1), (0, 0, -1))
        assert m[0][2] == 0
        assert m[1][2] == 0


# ---------------------------------------------------------------------------
# FCC neighbour shells and (100) layering
# ---------------------------------------------------------------------------

def test_shell_counts_and_membership() -> None:
    assert len(NN12_OFFSETS) == 12
    assert len(NN2_OFFSETS) == 6
    assert len(NN3_OFFSETS) == 24
    assert shell_offsets(1) == NN12_OFFSETS
    assert shell_offsets(2) == NN2_OFFSETS
    assert shell_offsets(3) == NN3_OFFSETS
    with pytest.raises(ValueError):
        shell_offsets(4)
    # 1NN = perms/signs of (1, 1, 0)
    for off in NN12_OFFSETS:
        assert sorted(abs(c) for c in off) == [0, 1, 1]
        assert is_even_parity(off)
    # 2NN = perms of (2, 0, 0)
    for off in NN2_OFFSETS:
        assert sorted(abs(c) for c in off) == [0, 0, 2]
        assert is_even_parity(off)
    # 3NN = perms/signs of (2, 1, 1)
    for off in NN3_OFFSETS:
        assert sorted(abs(c) for c in off) == [1, 1, 2]
        assert is_even_parity(off)


def test_shell_distances() -> None:
    origin = np.zeros(3)
    d1 = {float(np.linalg.norm(cartesian(o, origin, H))) for o in NN12_OFFSETS}
    d2 = {float(np.linalg.norm(cartesian(o, origin, H))) for o in NN2_OFFSETS}
    d3 = {float(np.linalg.norm(cartesian(o, origin, H))) for o in NN3_OFFSETS}
    assert len(d1) == 1 and d1.pop() == pytest.approx(2.489, abs=1e-3)
    assert len(d2) == 1 and d2.pop() == pytest.approx(3.520, abs=1e-3)
    assert len(d3) == 1 and d3.pop() == pytest.approx(4.311, abs=1e-3)


def test_100_layering_split() -> None:
    in_layer = [o for o in NN12_OFFSETS if o[2] == 0]
    cross_layer = [o for o in NN12_OFFSETS if o[2] != 0]
    up = [o for o in NN12_OFFSETS if o[2] == 1]
    down = [o for o in NN12_OFFSETS if o[2] == -1]
    assert len(in_layer) == 4  # 4 in-layer neighbours
    assert len(cross_layer) == 8  # 4 to k+1 + 4 to k-1
    assert len(up) == 4
    assert len(down) == 4


def test_coordination_bulk_and_surface() -> None:
    site = (0, 0, 0)

    # Fully embedded bulk atom: every 12-star neighbour occupied -> coordination 12.
    assert coordination(lambda _off: 1, site) == 12

    # (100) top-surface atom: the four k+1 neighbours are vacuum (OUTSIDE); the four
    # in-layer + four k-1 neighbours are occupied -> coordination 8.
    def surface_occ(off: tuple[int, int, int]) -> int:
        return 255 if off[2] > 0 else 1

    assert coordination(surface_occ, site) == 8

    # Isolated atom: all neighbours EMPTY -> coordination 0.
    assert coordination(lambda _off: 0, site) == 0


def test_coordination_ignores_empty_and_outside_only() -> None:
    # A mix of species codes (1, 2, 3) all count as occupied; 0 and 255 do not.
    site = (0, 0, 0)
    codes = {}
    for i, off in enumerate(NN12_OFFSETS):
        nb = (site[0] + off[0], site[1] + off[1], site[2] + off[2])
        codes[nb] = (0, 1, 2, 3, 255)[i % 5]
    expected = sum(1 for v in codes.values() if v not in (0, 255))
    assert coordination(lambda o: codes[o], site) == expected


# ---------------------------------------------------------------------------
# Even-parity snapping
# ---------------------------------------------------------------------------

def test_round_to_even_parity_even_round_no_flip() -> None:
    # round(u) already has even parity -> returned unchanged.
    got = round_to_even_parity(np.array([2.15, 0.10, -0.05]))
    assert got == (2, 0, 0)
    assert is_even_parity(got)


def test_round_to_even_parity_odd_round_flips_max_error() -> None:
    # round(u) = (1, 0, 0) is odd; largest error is on axis 0 -> flip toward 0.
    got = round_to_even_parity(np.array([0.90, 0.05, 0.0]))
    assert got == (0, 0, 0)
    assert is_even_parity(got)
    # It is the genuinely nearest even site (unique here).
    ranked = _nearest_even_bruteforce(np.array([0.90, 0.05, 0.0]))
    assert got == ranked[0]


def test_round_to_even_parity_is_nearest_over_random_points() -> None:
    rng = np.random.default_rng(99)
    for _ in range(500):
        u = rng.uniform(-4.0, 4.0, size=3)
        got = round_to_even_parity(u)
        assert is_even_parity(got)
        nearest = _nearest_even_bruteforce(u)[0]
        # got must be at the minimal distance (ties allowed -> compare distances).
        d_got = float(np.linalg.norm(np.array(got) - u))
        d_min = float(np.linalg.norm(np.array(nearest) - u))
        assert d_got == pytest.approx(d_min, abs=1e-9)


def test_second_nearest_reports_two_face_sites() -> None:
    # Midpoint of the 1NN bond (0,0,0)-(1,1,0): equidistant to exactly these two sites.
    u = np.array([0.5, 0.5, 0.0])
    first = round_to_even_parity(u)
    second = second_nearest_even_parity(u)
    assert first != second
    assert {first, second} == {(0, 0, 0), (1, 1, 0)}
    # Both are at the same (minimal) distance -> a true Voronoi face.
    d1 = float(np.linalg.norm(np.array(first) - u))
    d2 = float(np.linalg.norm(np.array(second) - u))
    assert d1 == pytest.approx(d2, abs=1e-12)


def test_second_nearest_is_distinct_and_farther_or_equal() -> None:
    rng = np.random.default_rng(7)
    for _ in range(300):
        u = rng.uniform(-4.0, 4.0, size=3)
        first = round_to_even_parity(u)
        second = second_nearest_even_parity(u)
        assert first != second
        assert is_even_parity(second)
        d1 = float(np.linalg.norm(np.array(first) - u))
        d2 = float(np.linalg.norm(np.array(second) - u))
        assert d2 >= d1 - 1e-9


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _nearest_even_bruteforce(u: np.ndarray) -> list[tuple[int, int, int]]:
    """Independent brute-force ranking of nearby even-parity sites (test oracle)."""
    base = np.rint(u).astype(int)
    scored: list[tuple[float, tuple[int, int, int]]] = []
    for di in range(-3, 4):
        for dj in range(-3, 4):
            for dk in range(-3, 4):
                s = (int(base[0]) + di, int(base[1]) + dj, int(base[2]) + dk)
                if (s[0] + s[1] + s[2]) % 2 != 0:
                    continue
                d2 = float((s[0] - u[0]) ** 2 + (s[1] - u[1]) ** 2 + (s[2] - u[2]) ** 2)
                scored.append((d2, s))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [s for _, s in scored]
