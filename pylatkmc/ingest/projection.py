"""Forward configuration projection: snapshot -> occupancy (Phase A, Agent A3).

Maps a relaxed off-lattice full-cell snapshot ``(X: N x 3 A, types, cell)`` to
occupancy on the fixed global FCC frame, **deterministically**, and reports
anything unmappable (contract Phase A, section 4; ``FINAL_DESIGN`` section 2). Cost
target O(N).

The frame is calibrated **once** per campaign (:func:`calibrate_frame`, the only
place RNG runs -- seeded, recorded); every later cycle only tracks bounded rigid
drift and thermal strain deterministically (:func:`register_cycle`). Working in the
aligned frame means ``R == I`` for the engine, so the reverse map
(:func:`to_atomistic`) emits axis-aligned atoms that tile the orthorhombic cell.

This module is independent of the identity pipeline: ``event_projection`` does its
own local FCC fit. ``projection`` exists for the round-trip determinism tests,
seeding, and the deterministic ``to_atomistic`` reverse map (contract section 12.4).

Load-DAG note (contract section 0.2): module-level intra-package imports are
``lattice`` and ``event_class`` only. ``scipy`` (the KDTree used once during
calibration) is imported lazily inside :func:`calibrate_frame` to keep import cheap.

Determinism (contract 0.1, hard gate)
-------------------------------------
No ``hash()``, no ``set``/``dict`` iteration order in any output-affecting path.
The occupancy dict is keyed by integer offsets; every seeded step lives in
:func:`calibrate_frame` and is recorded in ``frame.seeds``; the content hash and
the ``to_atomistic`` hash are ``blake2b`` over ``struct``-packed bytes in **sorted**
site order; flood-fill / BFS seeds iterate sorted lists.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from pylatkmc.ingest.event_class import (
    A_NOMINAL,
    EventProjReport,
    Occ,
    Offset,
    occ_to_symbol,
    type_to_occ,
)
from pylatkmc.ingest.lattice import (
    NN12_OFFSETS,
    round_to_even_parity,
    second_nearest_even_parity,
)

__all__ = [
    "DRIFT_TOL",
    "N_SOFT",
    "ROT_TOL",
    "SNAP_HYSTERESIS",
    "SNAP_TOL",
    "SOFT_SURFACE_TOL",
    "EventProjReport",
    "LatticeFrame",
    "Occupancy",
    "ProjectionAudit",
    "ProjectionReport",
    "calibrate_frame",
    "depth_bfs",
    "flood_fill_vacuum",
    "project",
    "register_cycle",
    "to_atomistic",
]


# --------------------------------------------------------------------------- #
# 4.2 / 2.3 Tolerances and thresholds (module constants)                      #
# --------------------------------------------------------------------------- #
SNAP_TOL: float = 0.9
"""Hard snap tolerance (A): a bulk atom farther than this from its site is unmappable."""

SOFT_SURFACE_TOL: float = 1.05
"""Loose tolerance (A) for top-surface atoms only (accept-with-warn band)."""

SNAP_HYSTERESIS: float = 0.3
"""Parity-Voronoi-face guard band (A): near-equidistant atoms inherit prev or audit."""

N_SOFT: int = 3
"""Max soft/ambiguous top-surface atoms tolerated under the accept-with-warn verdict."""

ROT_TOL: float = 0.05
"""Frobenius bound on ``||R_campaign - I||``; exceeded => FRAME_TILT audit."""

DRIFT_TOL: float = 0.5
"""Bound (A) on the per-cycle rigid-translation drift; exceeded => FRAME_DRIFT audit."""

_LAYER_MERGE_TOL: float = A_NOMINAL / 4.0
"""z-clustering merge tolerance (A) for KDE-lite layer detection (< half the layer gap)."""

_CELL_DIAG_TOL: float = 1.0e-6
"""Relative off-diagonal magnitude allowed before a cell is deemed non-orthorhombic."""

_A_MISMATCH_TOL: float = 0.01
"""Relative ``|a_x - a_y|`` mismatch that triggers a FRAME_TILT audit."""

_MAX_BONDS: int = 200_000
"""Cap on bond correspondences used in the seeded rotation fit (perf guard)."""


# --------------------------------------------------------------------------- #
# 4.1 Types                                                                   #
# --------------------------------------------------------------------------- #
Occupancy = dict[Offset, Occ]
"""Sparse ingest occupancy: FCC site offset -> occupancy code (NOT the runtime SoA)."""


class ProjectionAudit(Exception):
    """A hard projection abort routed to the pyKMC audit queue (contract 8.3).

    Carries a ``reason`` from the section-8.3 vocabulary (``FRAME_TILT`` /
    ``FRAME_DRIFT`` / ``COLLISION`` / ...). Raised by :func:`calibrate_frame` and
    :func:`register_cycle`; :func:`project` never raises for a rough snapshot (it
    returns an ``unprojectable`` verdict instead, contract 2.3 Geom-5).
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        """Store the audit ``reason`` and a human-readable ``detail``."""
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class LatticeFrame:
    """Calibrated FCC frame (contract 4.1); built once per campaign, drift-tracked."""

    a: float
    h: float
    origin: tuple[float, float, float]
    R_campaign: tuple[tuple[float, ...], ...]
    n_i: int
    n_j: int
    k_range: tuple[int, int]
    layer_z: tuple[float, ...]
    strain: tuple[float, float, float]
    k_top: int
    k_bot: int
    seeds: tuple[int, int]
    content_hash: str


@dataclass(frozen=True)
class ProjectionReport:
    """Per-snapshot projection outcome + residual provenance (contract 4.1)."""

    max_residual: float
    residual_histogram: tuple[tuple[float, int], ...]
    n_unmappable: int
    n_collision: int
    n_ambiguous: int
    stall_streak: int
    verdict: Literal["accept", "accept_warn", "handback_pyKMC", "unprojectable"]


# --------------------------------------------------------------------------- #
# Small deterministic geometry helpers                                        #
# --------------------------------------------------------------------------- #
def _as_matrix(m: np.ndarray) -> tuple[tuple[float, ...], ...]:
    """Freeze a 3x3 ``numpy`` matrix into a nested float tuple (hashable, frozen)."""
    return tuple(tuple(float(v) for v in row) for row in np.asarray(m, dtype=float))


def _assert_orthorhombic(cell: np.ndarray) -> None:
    """Raise FRAME_TILT unless ``cell`` is diagonal (orthorhombic) within tolerance."""
    c = np.asarray(cell, dtype=float)
    if c.shape != (3, 3):
        raise ProjectionAudit("FRAME_TILT", f"cell is not 3x3: shape={c.shape}")
    diag = np.abs(np.diag(c))
    scale = float(np.max(diag)) if float(np.max(diag)) > 0.0 else 1.0
    offdiag = c - np.diag(np.diag(c))
    if float(np.max(np.abs(offdiag))) > _CELL_DIAG_TOL * scale:
        raise ProjectionAudit(
            "FRAME_TILT", f"cell not orthorhombic (max off-diagonal={np.max(np.abs(offdiag)):.3e})"
        )


def _ideal_bond_dirs() -> np.ndarray:
    """The 12 ideal 1NN unit bond directions (``NN12_OFFSETS`` normalised)."""
    offs = np.asarray(NN12_OFFSETS, dtype=float)
    norms = np.linalg.norm(offs, axis=1, keepdims=True)
    return np.asarray(offs / norms, dtype=float)


def _estimate_rotation(
    X: np.ndarray, cell: np.ndarray, a: float, rng: np.random.Generator
) -> np.ndarray:
    """Seeded Kabsch/RANSAC rotation aligning observed 1NN bonds to the ideal FCC axes.

    Returns ``R_align`` (observed -> ideal): ``X_aligned = X @ R_align.T``. Each 1NN
    bond (both orientations) is assigned to its nearest ideal ``<110>`` direction
    and a cross-covariance is accumulated; the SVD gives the best proper rotation.
    Deterministic given ``rng`` (only used to subsample when bonds exceed the perf
    cap). ``R_campaign`` is this matrix's transpose (contract 2.1: ``Xa = R^T X``).
    """
    from scipy.spatial import cKDTree

    Lvec = np.abs(np.diag(np.asarray(cell, dtype=float)))
    Xw = np.mod(np.asarray(X, dtype=float), Lvec)
    tree = cKDTree(Xw, boxsize=Lvec)
    r_nn = (a / math.sqrt(2.0)) * 1.25
    pairs = tree.query_pairs(r_nn, output_type="ndarray")
    if pairs.shape[0] == 0:
        raise ProjectionAudit("FRAME_TILT", "no 1NN bonds available for rotation fit")
    if pairs.shape[0] > _MAX_BONDS:
        keep = rng.permutation(pairs.shape[0])[:_MAX_BONDS]
        keep.sort()
        pairs = pairs[keep]

    ideal = _ideal_bond_dirs()
    d = Xw[pairs[:, 1]] - Xw[pairs[:, 0]]
    d -= Lvec * np.round(d / Lvec)  # min-image
    nrm = np.linalg.norm(d, axis=1)
    good = nrm > 1e-6
    u = d[good] / nrm[good][:, None]
    u_both = np.vstack([u, -u])  # a bond is symmetric
    dots = u_both @ ideal.T
    nearest = np.argmax(dots, axis=1)
    m = ideal[nearest].T @ u_both  # sum_i outer(ideal_i, u_i) = 3x3 cross-covariance
    U, _s, Vt = np.linalg.svd(m)
    if np.linalg.det(U @ Vt) < 0.0:
        U[:, -1] *= -1.0
    return np.asarray(U @ Vt, dtype=float)


def _detect_layers(z: np.ndarray) -> list[float]:
    """KDE-lite (100) layer detection: cluster sorted z into layers, return mean z each.

    Adjacent z-values within ``_LAYER_MERGE_TOL`` join one layer (contract 2.1
    Geom-9). Deterministic (sorted scan). Raises FRAME_TILT if no atoms.
    """
    zs = np.sort(np.asarray(z, dtype=float))
    if zs.size == 0:
        raise ProjectionAudit("FRAME_TILT", "empty snapshot: no layers to detect")
    layers: list[float] = []
    cur: list[float] = [float(zs[0])]
    for zv in zs[1:]:
        if float(zv) - cur[-1] <= _LAYER_MERGE_TOL:
            cur.append(float(zv))
        else:
            layers.append(sum(cur) / len(cur))
            cur = [float(zv)]
    layers.append(sum(cur) / len(cur))
    return layers


def _origin_phase(coord: np.ndarray, h: float) -> float:
    """Sub-``h`` origin phase for one in-plane axis (robust median of residuals)."""
    ref = float(np.min(coord))
    idx = np.rint((coord - ref) / h)
    residual = coord - (ref + h * idx)
    return ref + float(np.median(residual))


def _frame_content_hash(
    a: float,
    h: float,
    origin: tuple[float, float, float],
    r_campaign: tuple[tuple[float, ...], ...],
    n_i: int,
    n_j: int,
    k_range: tuple[int, int],
    layer_z: tuple[float, ...],
    strain: tuple[float, float, float],
    k_top: int,
    k_bot: int,
    seeds: tuple[int, int],
) -> str:
    """Deterministic ``blake2b`` hex of the calibrated frame (contract 4.1)."""
    hasher = hashlib.blake2b(digest_size=32)

    def _f(x: float) -> None:
        hasher.update(struct.pack(">d", float(x)))

    def _i(x: int) -> None:
        hasher.update(struct.pack(">q", int(x)))

    _f(a)
    _f(h)
    for v in origin:
        _f(v)
    for row in r_campaign:
        for v in row:
            _f(v)
    _i(n_i)
    _i(n_j)
    _i(k_range[0])
    _i(k_range[1])
    _i(len(layer_z))
    for v in layer_z:
        _f(v)
    for v in strain:
        _f(v)
    _i(k_top)
    _i(k_bot)
    _i(seeds[0])
    _i(seeds[1])
    return hasher.hexdigest()


def _ideal_z(site: Offset, frame: LatticeFrame) -> float:
    """Detected (layer-aware) ideal z of ``site`` (contract 2.2 Geom-9).

    Uses ``frame.layer_z`` for a site inside the slab's ``k_range`` (absorbing
    surface relaxation); falls back to the ideal ``origin_z + h*k`` outside it.
    """
    lo, hi = frame.k_range
    k = site[2]
    if lo <= k <= hi:
        return frame.layer_z[k - lo]
    return frame.origin[2] + frame.h * k


def _residual(xa: np.ndarray, site: Offset, frame: LatticeFrame) -> float:
    """Layer-aware Euclidean snap residual (A) of aligned atom ``xa`` to ``site``."""
    dx = float(xa[0]) - (frame.origin[0] + frame.h * site[0])
    dy = float(xa[1]) - (frame.origin[1] + frame.h * site[1])
    dz = float(xa[2]) - _ideal_z(site, frame)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _is_top_surface(site: Offset, frame: LatticeFrame) -> bool:
    """True iff ``site`` sits in (or above) the detected top layer (soft tolerance)."""
    return site[2] >= frame.k_top


def _snap_tol_for(site: Offset, frame: LatticeFrame) -> float:
    """Hard tolerance for a bulk site, the soft tolerance for a top-surface site."""
    return SOFT_SURFACE_TOL if _is_top_surface(site, frame) else SNAP_TOL


def _wrap_inplane(site: Offset, frame: LatticeFrame) -> Offset:
    """Wrap an integer site into the periodic in-plane cell ``[0, 2n_i) x [0, 2n_j)``."""
    return (site[0] % (2 * frame.n_i), site[1] % (2 * frame.n_j), site[2])


def _occ_of_type(t: object) -> Occ:
    """Species symbol string (or integer code) -> occupancy code."""
    if isinstance(t, str):
        return type_to_occ(t)
    return Occ(int(t))  # type: ignore[call-overload]


# --------------------------------------------------------------------------- #
# 4.2 calibrate_frame / register_cycle                                        #
# --------------------------------------------------------------------------- #
def calibrate_frame(
    X0: np.ndarray,
    types0: Sequence[str] | np.ndarray,
    cell0: np.ndarray,
    *,
    a_nominal: float = A_NOMINAL,
    seeds: tuple[int, int],
) -> LatticeFrame:
    """Calibrate the campaign FCC frame ONCE (contract 4.2, ``FINAL_DESIGN`` 2.1).

    Asserts an orthorhombic cell; derives ``a`` exactly from the PBC cell
    (``|a_x - a_y| > 1%`` => FRAME_TILT audit); detects the z-layers (KDE-lite,
    load-bearing in the snap); runs the **seeded** Kabsch/RANSAC rotation fit and
    asserts ``||R_campaign - I|| < ROT_TOL`` else FRAME_TILT. RANSAC/Nelder-Mead run
    only here, seeded and recorded in ``frame.seeds``; two calls with the same
    ``seeds`` produce a byte-identical ``content_hash``.

    ``types0`` is accepted for signature compatibility (anchors are chosen
    geometrically by layer, so species are not needed at calibration time).
    """
    X = np.asarray(X0, dtype=float)
    cell = np.asarray(cell0, dtype=float)
    _assert_orthorhombic(cell)

    lx, ly = float(cell[0, 0]), float(cell[1, 1])
    n_i = int(round(lx / a_nominal))
    n_j = int(round(ly / a_nominal))
    if n_i < 1 or n_j < 1:
        raise ProjectionAudit("FRAME_TILT", f"degenerate cell: n_i={n_i}, n_j={n_j}")
    a_x = lx / n_i
    a_y = ly / n_j
    if abs(a_x - a_y) / a_x > _A_MISMATCH_TOL:
        raise ProjectionAudit(
            "FRAME_TILT", f"anisotropic in-plane lattice: a_x={a_x:.4f}, a_y={a_y:.4f}"
        )
    a = a_x
    h = a / 2.0

    rng = np.random.default_rng(int(seeds[0]))
    r_align = _estimate_rotation(X, cell, a, rng)
    r_campaign_mat = r_align.T
    tilt = float(np.linalg.norm(r_campaign_mat - np.eye(3)))
    if tilt >= ROT_TOL:
        raise ProjectionAudit("FRAME_TILT", f"||R_campaign - I||={tilt:.4f} >= ROT_TOL={ROT_TOL}")

    # Work in the aligned frame (R == I there).
    xa = X @ r_campaign_mat
    layer_means = _detect_layers(xa[:, 2])
    n_layers = len(layer_means)
    k_bot, k_top = 0, n_layers - 1

    origin_x = _origin_phase(xa[:, 0], h)
    origin_y = _origin_phase(xa[:, 1], h)
    origin_z = layer_means[0]
    origin = (origin_x, origin_y, origin_z)

    # Uniform thermal strain vs nominal (in-plane exact from cell; z from layer gaps).
    if n_layers >= 2:
        gaps = [layer_means[i + 1] - layer_means[i] for i in range(n_layers - 1)]
        mean_gap = sum(gaps) / len(gaps)
        strain_z = mean_gap / h - 1.0
    else:
        strain_z = 0.0
    strain = (a_x / a_nominal - 1.0, a_y / a_nominal - 1.0, strain_z)

    layer_z = tuple(layer_means)
    r_campaign = _as_matrix(r_campaign_mat)
    content_hash = _frame_content_hash(
        a, h, origin, r_campaign, n_i, n_j, (k_bot, k_top), layer_z, strain, k_top, k_bot, seeds
    )
    return LatticeFrame(
        a=a,
        h=h,
        origin=origin,
        R_campaign=r_campaign,
        n_i=n_i,
        n_j=n_j,
        k_range=(k_bot, k_top),
        layer_z=layer_z,
        strain=strain,
        k_top=k_top,
        k_bot=k_bot,
        seeds=(int(seeds[0]), int(seeds[1])),
        content_hash=content_hash,
    )


def register_cycle(
    X: np.ndarray,
    types: Sequence[str] | np.ndarray,
    cell: np.ndarray,
    frame: LatticeFrame,
) -> LatticeFrame:
    """Align each cycle's snapshot into the fixed frame, deterministically (contract 4.2).

    No RNG: rotates by the campaign ``R_campaign`` (so ``R == I`` in the working
    frame), estimates the bounded rigid-translation drift as the robust median
    offset of deep-bulk anchors, and updates ``h`` from the current cell's uniform
    thermal strain. Raises FRAME_DRIFT if ``||d_origin|| >= DRIFT_TOL``.
    ``types`` is accepted for signature symmetry (drift uses geometry only).
    """
    Xm = np.asarray(X, dtype=float)
    r_campaign_mat = np.asarray(frame.R_campaign, dtype=float)
    xa = Xm @ r_campaign_mat

    cell_m = np.asarray(cell, dtype=float)
    lx, ly = float(cell_m[0, 0]), float(cell_m[1, 1])
    a_x = lx / frame.n_i
    a_y = ly / frame.n_j
    strain_xy = 0.5 * ((a_x / frame.a - 1.0) + (a_y / frame.a - 1.0))
    h_eff = (frame.a / 2.0) * (1.0 + strain_xy)

    # Deep-bulk anchors: interior layers only (least surface relaxation).
    lo, hi = frame.k_range
    origin = np.asarray(frame.origin, dtype=float)
    offs: list[np.ndarray] = []
    for p in range(xa.shape[0]):
        u = (xa[p] - origin) / frame.h
        site = round_to_even_parity(u)
        if lo < site[2] < hi:
            ideal = origin + frame.h * np.asarray(site, dtype=float)
            offs.append(xa[p] - ideal)
    d_origin = np.median(np.vstack(offs), axis=0) if offs else np.zeros(3)
    drift = float(np.linalg.norm(d_origin))
    if drift >= DRIFT_TOL:
        raise ProjectionAudit("FRAME_DRIFT", f"||d_origin||={drift:.4f} >= DRIFT_TOL={DRIFT_TOL}")

    new_origin = (
        float(origin[0] + d_origin[0]),
        float(origin[1] + d_origin[1]),
        float(origin[2] + d_origin[2]),
    )
    new_strain = (a_x / A_NOMINAL - 1.0, a_y / A_NOMINAL - 1.0, frame.strain[2])
    content_hash = _frame_content_hash(
        frame.a,
        h_eff,
        new_origin,
        frame.R_campaign,
        frame.n_i,
        frame.n_j,
        frame.k_range,
        frame.layer_z,
        new_strain,
        frame.k_top,
        frame.k_bot,
        frame.seeds,
    )
    return LatticeFrame(
        a=frame.a,
        h=h_eff,
        origin=new_origin,
        R_campaign=frame.R_campaign,
        n_i=frame.n_i,
        n_j=frame.n_j,
        k_range=frame.k_range,
        layer_z=frame.layer_z,
        strain=new_strain,
        k_top=frame.k_top,
        k_bot=frame.k_bot,
        seeds=frame.seeds,
        content_hash=content_hash,
    )


# --------------------------------------------------------------------------- #
# 4.2 project                                                                 #
# --------------------------------------------------------------------------- #
def _residual_histogram(
    residuals: list[float], *, bin_width: float = 0.1, max_edge: float = 1.5
) -> tuple[tuple[float, int], ...]:
    """Fixed-bin residual histogram (deterministic); last bin is the overflow bin."""
    if not residuals:
        return ()
    n_bins = int(math.ceil(max_edge / bin_width))
    counts = [0] * (n_bins + 1)
    for r in residuals:
        b = int(r / bin_width)
        if b >= n_bins:
            b = n_bins
        counts[b] += 1
    return tuple(
        (round(i * bin_width, 4), counts[i]) for i in range(len(counts)) if counts[i] > 0
    )


def project(
    X: np.ndarray,
    types: Sequence[str] | np.ndarray,
    frame: LatticeFrame,
    prev_occ: Occupancy | None = None,
) -> tuple[Occupancy, ProjectionReport]:
    """Snap a snapshot onto the FCC frame, layer-aware and hysteretic (contract 4.2).

    For every atom: ``u = (Xa - origin)/h`` (aligned frame); the nearest and
    runner-up even-parity sites give a layer-aware residual pair. An atom farther
    than its (surface-relaxed) tolerance is *unmappable*; an atom whose two nearest
    sites lie within ``SNAP_HYSTERESIS`` is *ambiguous* -- it inherits its
    previous-cycle site from ``prev_occ`` (deterministic under thermal jitter) or is
    routed to audit; two atoms snapping to one site are a *collision* (a structural
    dumbbell -- hand the snapshot back to pyKMC, never silently drop). Conservation
    invariant I4 is asserted before returning.

    Never raises for a rough snapshot: the ``verdict`` field grades it
    (``accept`` / ``accept_warn`` / ``handback_pyKMC`` / ``unprojectable``) so the
    loop degrades gracefully instead of freezing (contract 2.3 Geom-5).
    """
    Xa = np.asarray(X, dtype=float) @ np.asarray(frame.R_campaign, dtype=float)
    origin = np.asarray(frame.origin, dtype=float)
    n_atoms = Xa.shape[0]

    occ: Occupancy = {}
    residuals: list[float] = []
    n_unmappable = 0
    n_collision = 0
    n_ambiguous = 0
    n_soft = 0
    all_soft_surface = True

    for p in range(n_atoms):
        xa = Xa[p]
        u = (xa - origin) / frame.h
        s1 = round_to_even_parity(u)
        s2 = second_nearest_even_parity(u)
        d1 = _residual(xa, s1, frame)
        d2 = _residual(xa, s2, frame)
        residuals.append(d1)

        hard = SNAP_TOL
        soft = _snap_tol_for(s1, frame)
        if d1 >= soft:
            n_unmappable += 1
            continue
        if d1 >= hard:
            # Between the hard and soft tolerance: only reachable on a surface site.
            n_soft += 1
            if not _is_top_surface(s1, frame):
                all_soft_surface = False

        w1 = _wrap_inplane(s1, frame)
        w2 = _wrap_inplane(s2, frame)
        if (d2 - d1) < SNAP_HYSTERESIS:
            resolved: Offset | None = None
            if prev_occ is not None:
                if w1 in prev_occ:
                    resolved = w1
                elif w2 in prev_occ:
                    resolved = w2
            if resolved is None:
                n_ambiguous += 1
                continue
            w1 = resolved

        if w1 in occ:
            n_collision += 1
            continue
        occ[w1] = _occ_of_type(types[p])

    # I4 conservation: every atom is placed, unmappable, collided, or (audited) ambiguous.
    # (The contract 4.2 formula omits n_ambiguous; including it is required so a
    # routed-to-audit atom does not falsely trip I4 -- see the returned deviation note.)
    placed = n_atoms - n_unmappable - n_collision - n_ambiguous
    assert len(occ) == placed, (
        f"I4 conservation violated: len(occ)={len(occ)} != {placed} "
        f"(N={n_atoms}, unmappable={n_unmappable}, collision={n_collision}, "
        f"ambiguous={n_ambiguous})"
    )

    max_residual = max(residuals) if residuals else 0.0
    verdict = _verdict(
        n_unmappable=n_unmappable,
        n_collision=n_collision,
        n_ambiguous=n_ambiguous,
        n_soft=n_soft,
        all_soft_surface=all_soft_surface,
        max_residual=max_residual,
    )
    report = ProjectionReport(
        max_residual=max_residual,
        residual_histogram=_residual_histogram(residuals),
        n_unmappable=n_unmappable,
        n_collision=n_collision,
        n_ambiguous=n_ambiguous,
        stall_streak=1 if verdict == "unprojectable" else 0,
        verdict=verdict,
    )
    return occ, report


def _verdict(
    *,
    n_unmappable: int,
    n_collision: int,
    n_ambiguous: int,
    n_soft: int,
    all_soft_surface: bool,
    max_residual: float,
) -> Literal["accept", "accept_warn", "handback_pyKMC", "unprojectable"]:
    """Grade a projection per the contract 2.3 cycle-policy table."""
    if n_collision > 0:
        return "handback_pyKMC"
    if (
        n_unmappable == 0
        and n_ambiguous == 0
        and n_soft == 0
        and max_residual < SNAP_TOL
    ):
        return "accept"
    if (
        n_unmappable == 0
        and all_soft_surface
        and (n_soft + n_ambiguous) <= N_SOFT
    ):
        return "accept_warn"
    return "unprojectable"


# --------------------------------------------------------------------------- #
# 4.2 flood_fill_vacuum / depth_bfs                                           #
# --------------------------------------------------------------------------- #
def _wrapped_occupied(occ: Occupancy, frame: LatticeFrame) -> set[Offset]:
    """Occupied sites wrapped into the canonical in-plane cell (membership set)."""
    return {_wrap_inplane(s, frame) for s in occ}


def _neighbours(site: Offset, frame: LatticeFrame) -> list[Offset]:
    """The 12 in-plane-wrapped 1NN neighbours of ``site`` (deterministic order)."""
    ni2, nj2 = 2 * frame.n_i, 2 * frame.n_j
    out: list[Offset] = []
    for off in NN12_OFFSETS:
        out.append(
            (
                (site[0] + off[0]) % ni2,
                (site[1] + off[1]) % nj2,
                site[2] + off[2],
            )
        )
    return out


def flood_fill_vacuum(occ: Occupancy, frame: LatticeFrame) -> set[Offset]:
    """Flood-fill the connected vacuum from the +/-z margins (contract 4.2, Geom-6).

    O(N) BFS seeded at the EMPTY sites of the two margin layers (``k_bot - 1`` and
    ``k_top + 1``), stepping through EMPTY 1NN neighbours (in-plane periodic, z
    bounded to the slab plus one margin layer on each side). An EMPTY site that is
    NOT reached but has an occupied neighbour is a vacancy / adatom-target rather
    than vacuum (that distinction is what the returned set enables). Determinism:
    seeds and the queue iterate sorted offsets; the returned set is membership-only.
    """
    occupied = _wrapped_occupied(occ, frame)
    lo, hi = frame.k_range
    k_lo, k_hi = lo - 1, hi + 1
    ni2, nj2 = 2 * frame.n_i, 2 * frame.n_j

    def _empty(site: Offset) -> bool:
        return site not in occupied

    # Seeds: every EMPTY, even-parity site on either margin layer.
    seeds: list[Offset] = []
    for k in (k_lo, k_hi):
        for i in range(ni2):
            for j in range(nj2):
                if (i + j + k) % 2 != 0:
                    continue
                site = (i, j, k)
                if _empty(site):
                    seeds.append(site)
    seeds.sort()

    vacuum: set[Offset] = set()
    queue: deque[Offset] = deque()
    for s in seeds:
        if s not in vacuum:
            vacuum.add(s)
            queue.append(s)
    while queue:
        site = queue.popleft()
        for nb in _neighbours(site, frame):
            if nb[2] < k_lo or nb[2] > k_hi:
                continue
            if nb in vacuum:
                continue
            if _empty(nb):
                vacuum.add(nb)
                queue.append(nb)
    return vacuum


def depth_bfs(
    occ: Occupancy,
    is_vacuum: set[Offset],
    frame: LatticeFrame,
    d_max: int,
) -> dict[Offset, int]:
    """Layers from each occupied site to the vacuum front, capped at ``d_max`` (contract 4.2).

    Multi-source BFS: occupied sites adjacent to a vacuum site are depth ``0``
    (surface), their occupied neighbours depth ``1`` (subsurface), and so on.
    A returned depth of ``d_max + 1`` denotes BULK_OR_DEEPER (deeper than the
    resolvable ``d_max``). Deterministic: sources and the queue iterate sorted
    offsets (the BFS shortest-path result is order-independent regardless).
    """
    occupied = _wrapped_occupied(occ, frame)
    vac = {_wrap_inplane(s, frame) for s in is_vacuum}

    sources: list[Offset] = []
    for site in occupied:
        if any(nb in vac for nb in _neighbours(site, frame)):
            sources.append(site)
    sources.sort()

    depth: dict[Offset, int] = {}
    queue: deque[Offset] = deque()
    for s in sources:
        depth[s] = 0
        queue.append(s)
    while queue:
        site = queue.popleft()
        d = depth[site]
        for nb in _neighbours(site, frame):
            if nb in occupied and nb not in depth:
                depth[nb] = d + 1
                queue.append(nb)

    cap = d_max + 1
    return {site: (dep if dep <= d_max else cap) for site, dep in depth.items()}


# --------------------------------------------------------------------------- #
# 4.2 to_atomistic (deterministic reverse map, R == I)                        #
# --------------------------------------------------------------------------- #
def to_atomistic(
    occ: Occupancy, frame: LatticeFrame
) -> tuple[list[tuple[str, tuple[float, float, float]]], str]:
    """Deterministic reverse map occupancy -> ideal atoms (contract 4.2 / 7.3, R == I).

    Emits ``(symbol, position)`` at the ideal axis-aligned site position
    ``origin + h*(i, j, k)`` in **sorted** site order; EMPTY / OUTSIDE / sentinel
    codes emit nothing. Returns the atom list and a ``blake2b`` content hash over the
    sorted ``(i, j, k, symbol)`` records, so a ``project -> to_atomistic -> project``
    round-trip reproduces the occupancy and the hash is byte-stable.
    """
    hasher = hashlib.blake2b(digest_size=32)
    atoms: list[tuple[str, tuple[float, float, float]]] = []
    for site in sorted(occ):
        code = occ[site]
        if code in (Occ.EMPTY, Occ.OUTSIDE, Occ.OCC_ANY):
            continue
        symbol = occ_to_symbol(code)
        x = frame.origin[0] + frame.h * site[0]
        y = frame.origin[1] + frame.h * site[1]
        z = frame.origin[2] + frame.h * site[2]
        atoms.append((symbol, (x, y, z)))
        hasher.update(struct.pack(">qqq", int(site[0]), int(site[1]), int(site[2])))
        hasher.update(symbol.encode("utf-8"))
        hasher.update(b"\x00")
    return atoms, hasher.hexdigest()
