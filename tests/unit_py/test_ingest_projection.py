"""Unit tests for ``pylatkmc.ingest.projection`` (Agent A3, contract section 11.4).

Synthetic FCC (100) slabs exercise the deterministic layer-aware hysteretic snap, the
flood-fill vacuum/vacancy split, the ``R == I`` reverse-map round-trip, and
once-per-campaign frame calibration.

Most tests call :func:`calibrate_frame`, whose seeded rotation estimate uses
``scipy.spatial.cKDTree`` -- an ``[ingest]``-only dependency, not a base one. The
module-level ``importorskip("scipy")`` keeps a bare ``[dev]`` CI run (no ``[ingest]``)
green by *skipping* rather than erroring (contract 11.1 / 11.7).

Covered properties (contract 11.4):
    * Jitter determinism (Geom-2): N(0, 0.05 A) x100 leaves the grid invariant; a
      planted parity-Voronoi-face atom routes to audit, never a coin-flip snap.
    * Conservation (Geom-8): a planted split-interstitial collides -> hand-back; the
      I4 accounting holds for every verdict (no atom silently dropped).
    * Flood-fill (Geom-6): an overhang cavity is vacuum, a buried pore is a vacancy;
      depth_bfs caps at d_max.
    * Round-trip (Geom-4): project -> to_atomistic -> project reproduces occupancy;
      the content hash is byte-stable; the x=0 face coincides with the x=Lx image.
    * Frame calibration (Geom-10): identical seeds -> byte-identical content_hash; a
      tilted slab aborts to a FRAME_TILT audit.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")  # calibrate_frame -> scipy.spatial.cKDTree ([ingest]-only)

from pylatkmc.ingest.event_class import Occ  # noqa: E402
from pylatkmc.ingest.projection import (  # noqa: E402
    N_SOFT,
    SNAP_TOL,
    LatticeFrame,
    ProjectionAudit,
    calibrate_frame,
    depth_bfs,
    flood_fill_vacuum,
    project,
    register_cycle,
    to_atomistic,
)

A_NOMINAL = 3.52
H = A_NOMINAL / 2.0


# --------------------------------------------------------------------------- #
# Synthetic slab / occupancy builders                                         #
# --------------------------------------------------------------------------- #
def make_slab(
    n_i: int = 3,
    n_j: int = 3,
    n_layers: int = 5,
    a: float = A_NOMINAL,
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
    z_shift: float = 8.0,
) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Build an ideal FCC (100) slab (even-parity sublattice) with z vacuum gaps."""
    h = a / 2.0
    pos: list[tuple[float, float, float]] = []
    for k in range(n_layers):
        for i in range(2 * n_i):
            for j in range(2 * n_j):
                if (i + j + k) % 2 == 0:
                    pos.append(
                        (origin[0] + h * i, origin[1] + h * j, origin[2] + z_shift + h * k)
                    )
    X = np.asarray(pos, dtype=float)
    lx = 2 * n_i * h
    ly = 2 * n_j * h
    lz = 2 * z_shift + h * (n_layers - 1)
    cell = np.diag([lx, ly, lz])
    types = ["Ni"] * len(X)
    return X, types, cell


def synth_frame(n_i: int, n_j: int, n_layers: int, a: float = A_NOMINAL) -> LatticeFrame:
    """A minimal identity-oriented (R == I, origin 0) frame for flood/depth tests."""
    h = a / 2.0
    return LatticeFrame(
        a=a,
        h=h,
        origin=(0.0, 0.0, 0.0),
        R_campaign=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        n_i=n_i,
        n_j=n_j,
        k_range=(0, n_layers - 1),
        layer_z=tuple(h * k for k in range(n_layers)),
        strain=(0.0, 0.0, 0.0),
        k_top=n_layers - 1,
        k_bot=0,
        seeds=(0, 0),
        content_hash="",
    )


def full_slab_occ(n_i: int, n_j: int, n_layers: int) -> dict[tuple[int, int, int], Occ]:
    """Every even-parity site in ``[0,2n_i) x [0,2n_j) x [0,n_layers)`` occupied by Ni."""
    occ: dict[tuple[int, int, int], Occ] = {}
    for k in range(n_layers):
        for i in range(2 * n_i):
            for j in range(2 * n_j):
                if (i + j + k) % 2 == 0:
                    occ[(i, j, k)] = Occ.NI
    return occ


def rotate_z(X: np.ndarray, deg: float) -> np.ndarray:
    """Rotate coordinates by ``deg`` degrees about the z-axis (row-vector convention)."""
    th = np.radians(deg)
    c, s = np.cos(th), np.sin(th)
    rot = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return X @ rot.T


# --------------------------------------------------------------------------- #
# 11.4 Jitter determinism (Geom-2)                                            #
# --------------------------------------------------------------------------- #
def test_jitter_determinism_grid_invariant() -> None:
    """N(0, 0.05 A) x100 leaves the occupancy grid bit-identical (hysteresis-stable)."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    occ0, rep0 = project(X, types, frame)
    assert rep0.verdict == "accept"
    assert len(occ0) == len(X)

    rng = np.random.default_rng(12345)
    for _ in range(100):
        xj = X + rng.normal(0.0, 0.05, size=X.shape)
        occ, rep = project(xj, types, frame, prev_occ=occ0)
        assert occ == occ0
        assert rep.n_collision == 0
        # I4: no atom silently dropped.
        placed = len(xj) - rep.n_unmappable - rep.n_collision - rep.n_ambiguous
        assert len(occ) == placed


def test_voronoi_face_atom_routes_to_audit_not_coinflip() -> None:
    """A planted parity-Voronoi-face adatom is never snapped; its candidate sites stay empty."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))

    # Two empty adatom sites one layer above the top surface, 1NN apart; the planted
    # atom sits exactly on their shared parity-Voronoi face (equidistant to both).
    k_face = frame.k_top + 1
    site_a = (0, 0, k_face) if (0 + 0 + k_face) % 2 == 0 else (1, 0, k_face)
    site_b = (site_a[0] + 1, site_a[1] + 1, k_face)  # 1NN even-parity neighbour
    assert (sum(site_a)) % 2 == 0 and (sum(site_b)) % 2 == 0
    ox, oy, oz = frame.origin
    face = np.array(
        [
            ox + frame.h * (site_a[0] + 0.5),
            oy + frame.h * (site_a[1] + 0.5),
            oz + frame.h * k_face,
        ]
    )
    x_aug = np.vstack([X, face])
    types_aug = [*types, "Ni"]

    rng = np.random.default_rng(7)
    for _ in range(100):
        xj = x_aug + rng.normal(0.0, 0.05, size=x_aug.shape)
        occ, rep = project(xj, types_aug, frame)  # fresh (no prev): must route to audit
        # The planted atom is above every real site -> it is the sole unmappable atom,
        # and it is NEVER placed at either candidate site (no coin-flip snap).
        assert rep.n_unmappable >= 1
        assert site_a not in occ
        assert site_b not in occ
        # Every real slab atom is still placed deterministically.
        assert len(occ) == len(X)


# --------------------------------------------------------------------------- #
# 11.4 Conservation / collision (Geom-8)                                      #
# --------------------------------------------------------------------------- #
def test_split_interstitial_collides_and_hands_back() -> None:
    """Two atoms snapping to one site -> collision -> handback; I4 accounting holds."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))

    # A dumbbell: a second atom a fraction of a bond from an occupied bulk site.
    site = (2, 2, 2)
    ox, oy, oz = frame.origin
    twin = np.array(
        [ox + frame.h * site[0] + 0.15, oy + frame.h * site[1], oz + frame.h * site[2]]
    )
    x_aug = np.vstack([X, twin])
    types_aug = [*types, "Ni"]

    occ, rep = project(x_aug, types_aug, frame)
    assert rep.n_collision >= 1
    assert rep.verdict == "handback_pyKMC"
    # I4: the twin is accounted as a collision, not silently dropped.
    placed = len(x_aug) - rep.n_unmappable - rep.n_collision - rep.n_ambiguous
    assert len(occ) == placed
    assert occ[site] == Occ.NI  # the real atom is placed exactly once


def test_clean_slab_conserves_every_atom() -> None:
    """A pristine slab accepts with every atom placed and zero anomalies."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    occ, rep = project(X, types, frame)
    assert rep.verdict == "accept"
    assert rep.n_unmappable == 0
    assert rep.n_collision == 0
    assert rep.n_ambiguous == 0
    assert len(occ) == len(X)
    assert rep.max_residual < SNAP_TOL


# --------------------------------------------------------------------------- #
# 11.4 Flood-fill vacuum vs vacancy (Geom-6) + depth cap                       #
# --------------------------------------------------------------------------- #
def test_flood_fill_overhang_vacuum_vs_buried_pore_vacancy() -> None:
    """An overhang cavity connected to the side is vacuum; a buried pore is a vacancy."""
    n_i = n_j = 4
    n_layers = 5
    frame = synth_frame(n_i, n_j, n_layers)
    occ = full_slab_occ(n_i, n_j, n_layers)

    # Tunnel from the top surface down under an overhang (each step is a 1NN move):
    tunnel = [(4, 4, 4), (5, 4, 3), (4, 4, 2)]
    for s in tunnel:
        assert sum(s) % 2 == 0
        del occ[s]
    # A separately, fully enclosed single-site pore.
    pore = (2, 2, 2)
    del occ[pore]

    vacuum = flood_fill_vacuum(occ, frame)

    # The whole tunnel connects to the top margin -> vacuum (the deepest tunnel site
    # (4,4,2) is under occupied atoms = a genuine overhang, yet still vacuum).
    for s in tunnel:
        assert s in vacuum
    # The enclosed pore is unreachable from any margin -> a vacancy, not vacuum.
    assert pore not in vacuum
    # A margin site above the slab is vacuum.
    assert (1, 0, n_layers) in vacuum or (0, 1, n_layers) in vacuum


def test_depth_bfs_caps_at_d_max() -> None:
    """Surface atoms are depth 0; atoms deeper than d_max collapse to d_max+1 (BULK)."""
    n_i = n_j = 3
    n_layers = 5
    frame = synth_frame(n_i, n_j, n_layers)
    occ = full_slab_occ(n_i, n_j, n_layers)
    vacuum = flood_fill_vacuum(occ, frame)

    d_max = 1
    depth = depth_bfs(occ, vacuum, frame, d_max)

    # Bottom/top surface atoms touch the margin vacuum -> depth 0.
    assert depth[(2, 2, 0)] == 0
    assert depth[(2, 2, 4)] == 0
    # The central layer is two layers from either vacuum front -> capped at d_max+1.
    assert depth[(2, 2, 2)] == d_max + 1
    # First subsurface layer -> depth 1.
    assert depth[(1, 2, 1)] == 1
    assert max(depth.values()) == d_max + 1


# --------------------------------------------------------------------------- #
# 11.4 Round-trip (Geom-4)                                                     #
# --------------------------------------------------------------------------- #
def test_round_trip_project_to_atomistic_project() -> None:
    """project -> to_atomistic (R == I) -> project reproduces occupancy + byte-stable hash."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    occ, _rep = project(X, types, frame)

    atoms, hash_a = to_atomistic(occ, frame)
    # Byte-stable content hash across repeated calls.
    _atoms2, hash_a2 = to_atomistic(occ, frame)
    assert hash_a == hash_a2
    assert len(atoms) == len(occ)

    x2 = np.asarray([pos for _sym, pos in atoms], dtype=float)
    types2 = [sym for sym, _pos in atoms]
    occ2, rep2 = project(x2, types2, frame)
    assert occ2 == occ
    assert rep2.verdict == "accept"

    _atoms3, hash_b = to_atomistic(occ2, frame)
    assert hash_b == hash_a


def test_round_trip_x0_face_coincides_with_x_Lx_image() -> None:
    """The x=0 face coincides with the image of x=Lx: a +Lx in-plane shift is invariant."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    occ, _rep = project(X, types, frame)

    lx = float(cell[0, 0])
    x_shift = X.copy()
    x_shift[:, 0] += lx  # translate the whole slab by one in-plane period in x
    occ_shift, _rep2 = project(x_shift, types, frame)
    assert occ_shift == occ


# --------------------------------------------------------------------------- #
# 11.4 Frame calibration (Geom-10)                                            #
# --------------------------------------------------------------------------- #
def test_calibration_is_deterministic_across_identical_seeds() -> None:
    """Two calibrations with the same seeds produce a byte-identical frame + hash."""
    X, types, cell = make_slab()
    f1 = calibrate_frame(X, types, cell, seeds=(1, 2))
    f2 = calibrate_frame(X, types, cell, seeds=(1, 2))
    assert f1.content_hash == f2.content_hash
    assert f1 == f2
    # The recovered frame matches the constructed slab.
    assert f1.n_i == 3 and f1.n_j == 3
    assert f1.k_range == (0, 4)
    assert abs(f1.a - A_NOMINAL) < 1e-9
    assert np.allclose(np.asarray(f1.R_campaign), np.eye(3), atol=1e-6)


def test_calibration_aborts_on_tilted_slab() -> None:
    """A slab tilted past ROT_TOL raises a FRAME_TILT audit (contract 4.2)."""
    X, types, cell = make_slab(n_i=4, n_j=4, n_layers=6)
    x_tilt = rotate_z(X, 15.0)
    with pytest.raises(ProjectionAudit) as exc:
        calibrate_frame(x_tilt, types, cell, seeds=(1, 2))
    assert exc.value.reason == "FRAME_TILT"


def test_calibration_aborts_on_non_orthorhombic_cell() -> None:
    """A sheared (non-diagonal) cell aborts to a FRAME_TILT audit."""
    X, types, cell = make_slab()
    sheared = cell.copy()
    sheared[0, 1] = 2.0  # off-diagonal shear
    with pytest.raises(ProjectionAudit) as exc:
        calibrate_frame(X, types, sheared, seeds=(1, 2))
    assert exc.value.reason == "FRAME_TILT"


# --------------------------------------------------------------------------- #
# register_cycle: bounded deterministic drift tracking                        #
# --------------------------------------------------------------------------- #
def test_register_cycle_zero_drift_preserves_origin() -> None:
    """Re-registering the calibration snapshot recovers ~zero drift (deterministic)."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    reg = register_cycle(X, types, cell, frame)
    assert np.allclose(np.asarray(reg.origin), np.asarray(frame.origin), atol=1e-6)
    assert abs(reg.h - frame.h) < 1e-6
    # Deterministic: registering twice yields the same content hash.
    reg2 = register_cycle(X, types, cell, frame)
    assert reg.content_hash == reg2.content_hash


def test_register_cycle_aborts_on_excessive_drift() -> None:
    """A large rigid translation trips the FRAME_DRIFT audit."""
    X, types, cell = make_slab()
    frame = calibrate_frame(X, types, cell, seeds=(1, 2))
    x_drift = X.copy()
    x_drift[:, 0] += 0.9  # rigid shift beyond DRIFT_TOL
    with pytest.raises(ProjectionAudit) as exc:
        register_cycle(x_drift, types, cell, frame)
    assert exc.value.reason == "FRAME_DRIFT"


# --------------------------------------------------------------------------- #
# Verdict grading table (contract 2.3)                                        #
# --------------------------------------------------------------------------- #
def test_accept_warn_budget_constant() -> None:
    """The accept-with-warn budget constant matches the contract (n_soft = 3)."""
    assert N_SOFT == 3
