"""Event projection: one pyKMC reference row -> a ``ProjectedEvent`` (Agent A4).

Implements contract Phase A, section 5 (``FINAL_DESIGN`` sections 3 and 4.1). Turns a
single pyKMC reference-table row -- a *local, subset-relative, raw-wrapped* cluster
(``initial_positions`` = ``rcut``-neighbours of the mover, etc.) -- into an on-lattice
event: a set of ``(site, occ_before -> occ_after)`` changes, a full ``r_ctx``-decorated
context, an ordered categorical saddle token per mover, and an operational depth
signature.

Pipeline (section 3, in order):

1. **Unwrap first (Geom-1).** Every stored cluster is min-image-unwrapped about its
   ``move_atom_idx`` atom, using the event's own PBC cell, before any fit. Without this a
   mover within ``~rcut`` of an in-plane face has its ``-x/-y`` neighbours wrapped to the
   far box side, and ``fit_local_fcc`` infers a *phantom* in-plane surface -- routing a
   bulk hop into the surface regime.
2. **Own local FCC fit.** A Procrustes fit of the seed's nearest-neighbour bond
   directions onto the ideal ``<110>`` star gives the local rotation ``R`` and the half
   spacing ``h`` -- independent of ``projection.LatticeFrame``.
3. **TRUE site-change detection (section 3.2).** Movers are the atoms whose *snapped
   site* changes between the initial and final snapshots -- ground truth, never
   ``move_atom_idx`` alone -- so a concerted event that ``move_atom_idx`` names only one
   of is caught in full.
4. **Delta + full context.** ``delta`` holds only sites whose occupancy changed;
   ``context`` decorates **every** ideal site within ``r_ctx`` of the moved-site centroid
   (``EMPTY`` included, uncovered sites flagged ``OUTSIDE`` + ``truncated``).
5. **Ordered categorical saddle token (section 3.3).** ``kind`` counts the occupied atoms
   coordinating each mover's transition-state position (top=1, bridge=2, hollow=3/4) with
   a robust geometric test + hysteresis band -- never a rounded displacement.
6. **Operational depth signature (section 4.1).** Identically defined at ingest and
   runtime: a contiguous EMPTY hemisphere with occupied backing -> SURFACE; else the
   layer distance to the nearest EMPTY-with-occupied-neighbour, capped at ``d_max``.

Load-DAG note (contract 0.2): this module imports ``lattice`` and ``event_class`` at
module level only, and never imports ``canonical`` (identity is a downstream consumer of
the ``ProjectedEvent`` this module returns). ``start_rank`` on each saddle token is left
0 here and filled by ``canonical`` in the winning ``(a*, g*)`` frame.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pylatkmc.ingest.event_class import (
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventProjReport,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
    type_to_occ,
)
from pylatkmc.ingest.lattice import (
    NN12_OFFSETS,
    Offset,
    round_to_even_parity,
)

# --------------------------------------------------------------------------- #
# Tunable geometric constants (Angstrom-relative factors, dimensionless)      #
# --------------------------------------------------------------------------- #
_SQRT2 = math.sqrt(2.0)

#: Neighbours within this factor of the shortest bond count as the 1NN shell for the
#: local frame fit. 2NN sits at ``sqrt(2) x 1NN`` (~1.414), so 1.25 is a clean gap.
_NN_SHELL_FACTOR = 1.25

#: ICP refinement rounds for the Procrustes bond-direction fit (converges in ~2 for
#: near-axis-aligned clusters; a handful is cheap and covers mild misorientation).
_FIT_ICP_ROUNDS = 6

#: Coordinating cutoff for the saddle token, as a fraction of the local 1NN spacing.
#: An atom "coordinates" the transition state when it sits within ~one bond length
#: (1.0 x 1NN) of it -- top/bridge/hollow atoms all sit at ~bond distance; the next
#: substrate shell (2NN / 3NN of the saddle) is at >= ~1.4 x 1NN, so 1.15 separates
#: them with a wide robustness margin.
_SADDLE_COORD_FACTOR = 1.15

#: Half-width of the hysteresis band around the coordinating cutoff (fraction of 1NN):
#: a saddle whose (n+1)-th atom falls inside ``[factor +/- band] x 1NN`` keeps its
#: previously-assigned ``kind`` (removes the round()-boundary flicker of Geom-7/M1).
_SADDLE_COORD_BAND = 0.12

#: A surface is declared only when at least this many of the mover's 1NN are EMPTY
#: (an isolated interior vacancy has 1) -- a hemisphere's worth on (100) is 4.
_SURFACE_MIN_EMPTY = 3

#: ...and their summed unit directions are this coherent (mean projection), i.e. the
#: empties cluster on one side (a vacuum hemisphere), not scattered vacancies.
_SURFACE_COHERENCE = 0.5


# --------------------------------------------------------------------------- #
# Local FCC frame (this module's own fit; independent of projection.py)       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LocalFrame:
    """A local, event-private FCC frame fitted from one cluster (contract 3.1).

    ``x_cartesian = origin + h * (R @ off)`` maps an integer even-parity offset to
    Cartesian; the inverse ``off ~ round_even(R.T @ (x - origin) / h)`` snaps a
    Cartesian atom to its site. ``origin`` is the seed (mover) position, so the seed
    snaps to ``(0, 0, 0)`` by construction -- this is ``anchor0`` and every delta /
    context / mover offset is expressed relative to it.
    """

    origin: tuple[float, float, float]
    h: float
    R: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    seed_idx: int


def _rmat(frame: LocalFrame) -> np.ndarray:
    """Return the frame rotation as a ``(3, 3)`` float array."""
    return np.asarray(frame.R, dtype=float)


def _origin(frame: LocalFrame) -> np.ndarray:
    """Return the frame origin as a length-3 float array."""
    return np.asarray(frame.origin, dtype=float)


def _snap(frame: LocalFrame, x: np.ndarray) -> Offset:
    """Snap one Cartesian position to its nearest even-parity site in ``frame``."""
    u = _rmat(frame).T @ (np.asarray(x, dtype=float) - _origin(frame)) / frame.h
    return round_to_even_parity(u)


def _site_cart(frame: LocalFrame, off: Offset) -> np.ndarray:
    """Return the Cartesian position of an integer offset in ``frame``."""
    x = _origin(frame) + frame.h * (_rmat(frame) @ np.asarray(off, dtype=float))
    return np.asarray(x, dtype=float)


# --------------------------------------------------------------------------- #
# 5. min_image_unwrap                                                         #
# --------------------------------------------------------------------------- #
def _cell_lengths(cell: np.ndarray | None) -> np.ndarray | None:
    """Extract orthorhombic box lengths from a cell (``(3,)`` or ``(3, 3)`` diagonal)."""
    if cell is None:
        return None
    c = np.asarray(cell, dtype=float)
    lengths = np.abs(np.diag(c)) if c.ndim == 2 else np.abs(c.reshape(-1)[:3])
    if lengths.shape[0] != 3 or not np.all(np.isfinite(lengths)) or np.any(lengths <= 0.0):
        return None
    return lengths


def min_image_unwrap(positions: np.ndarray, about: int, cell: np.ndarray | None) -> np.ndarray:
    """Unwrap a raw-wrapped subset cluster about its ``about`` atom (Geom-1).

    Uses the event's own PBC ``cell`` (orthorhombic; a ``(3, 3)`` cell is read on its
    diagonal). Every atom is shifted by the minimum-image displacement from the ``about``
    atom, so a neighbour wrapped to the far side of the box is brought back to its true
    ``~2.49 A`` position. **Must run before any fit.** With ``cell is None`` (or a
    degenerate cell) the positions are returned unchanged.
    """
    P = np.asarray(positions, dtype=float)
    lengths = _cell_lengths(cell)
    if lengths is None:
        return np.asarray(P.copy(), dtype=float)
    ref = P[about]
    d = P - ref
    d -= lengths * np.rint(d / lengths)
    return np.asarray(ref + d, dtype=float)


# --------------------------------------------------------------------------- #
# 5. fit_local_fcc                                                            #
# --------------------------------------------------------------------------- #
_NN12_UNIT = np.asarray(NN12_OFFSETS, dtype=float) / _SQRT2  # 12 ideal <110> unit dirs
_NN12_FLOAT = np.asarray(NN12_OFFSETS, dtype=float)


def _kabsch(ideal_scaled: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Best-fit rotation ``R`` with ``obs_i ~ R @ ideal_scaled_i`` (proper rotation)."""
    h = obs.T @ ideal_scaled
    u_mat, _s, vt = np.linalg.svd(h)
    d = float(np.sign(np.linalg.det(u_mat @ vt)))
    dmat = np.diag([1.0, 1.0, d])
    return np.asarray(u_mat @ dmat @ vt, dtype=float)


def fit_local_fcc(P0: np.ndarray, seed_idx: int) -> LocalFrame:
    """Fit the event's local FCC frame from the seed's 1NN bond directions (contract 3.1).

    Procrustes (iterated closest-point) of the seed's nearest-neighbour bond directions
    onto the ideal ``<110>`` star gives the local rotation ``R``; ``h`` is the mean bond
    length divided by ``sqrt(2)`` (the 1NN spacing is ``a / sqrt(2) = h * sqrt(2)``). The
    ``origin`` is the seed position, so ``snap(seed) == (0, 0, 0)``.
    """
    P = np.asarray(P0, dtype=float)
    seed = P[seed_idx]
    d = P - seed
    dist = np.linalg.norm(d, axis=1)
    order = np.argsort(dist, kind="stable")
    nz = [int(i) for i in order if dist[i] > 1e-6]
    if len(nz) < 3:
        raise ValueError(f"cluster too small to fit a local frame ({len(nz)} neighbours)")
    d_min = float(dist[nz[0]])
    nn_idx = [i for i in nz if dist[i] <= _NN_SHELL_FACTOR * d_min]
    bonds = d[nn_idx]  # (M, 3)
    blen = dist[nn_idx]  # (M,)
    h_fit = float(np.mean(blen)) / _SQRT2

    bond_units = bonds / blen[:, None]
    rmat = np.eye(3)
    for _ in range(_FIT_ICP_ROUNDS):
        predicted = (rmat @ _NN12_UNIT.T).T  # (12, 3) obs-frame ideal unit dirs
        cos = bond_units @ predicted.T  # (M, 12)
        best = np.argmax(cos, axis=1)  # nearest ideal dir per bond
        matched = _NN12_FLOAT[best]  # (M, 3) integer offsets
        rmat_new = _kabsch(h_fit * matched, bonds)
        if np.allclose(rmat_new, rmat, atol=1e-12):
            rmat = rmat_new
            break
        rmat = rmat_new

    r_tuple = (
        (float(rmat[0, 0]), float(rmat[0, 1]), float(rmat[0, 2])),
        (float(rmat[1, 0]), float(rmat[1, 1]), float(rmat[1, 2])),
        (float(rmat[2, 0]), float(rmat[2, 1]), float(rmat[2, 2])),
    )
    return LocalFrame(
        origin=(float(seed[0]), float(seed[1]), float(seed[2])),
        h=h_fit,
        R=r_tuple,
        seed_idx=int(seed_idx),
    )


# --------------------------------------------------------------------------- #
# 5. detect_movers (site-change is ground truth, section 3.2)                 #
# --------------------------------------------------------------------------- #
def detect_movers(
    P0: np.ndarray, P2: np.ndarray, frame_e: LocalFrame
) -> tuple[tuple[Offset, ...], list[Offset]]:
    """Detect the TRUE site-change set and interior empties (contract 3.2).

    Movers are the atoms whose snapped site differs between the initial (``P0``) and final
    (``P2``) snapshots -- ``movers = {snap(P0[p]) : snap(P0[p]) != snap(P2[p])}`` -- which
    is ground truth and catches a concerted event that ``move_atom_idx`` names only one
    of. Displacement magnitude is only a pre-filter and plays no role here. The second
    return value is the interior ``EMPTY`` sites (vacancies / adatom targets): even-parity
    sites strictly inside the initial cluster's bounding box that no atom occupies.

    Returns ``(mover_start_offsets, empties)``, both in the ``frame_e`` (anchor0-relative)
    lattice, sorted for determinism.
    """
    A0 = np.asarray(P0, dtype=float)
    A2 = np.asarray(P2, dtype=float)
    n = A0.shape[0]
    s0 = [_snap(frame_e, A0[p]) for p in range(n)]
    s2 = [_snap(frame_e, A2[p]) for p in range(n)]

    mover_starts = sorted({s0[p] for p in range(n) if s0[p] != s2[p]})
    occupied0 = set(s0)
    empties = sorted(_interior_empties(s0, occupied0))
    return tuple(mover_starts), list(empties)


def _interior_empties(sites: Sequence[Offset], occupied: set[Offset]) -> list[Offset]:
    """Even-parity sites strictly inside the bounding box of ``sites`` that are empty.

    A deterministic, dependency-light approximation of "EMPTY sites inside conv-hull(P0)"
    (contract 3.2): the strict bounding-box interior excludes the surrounding vacuum while
    keeping genuine internal vacancies. Used only as provenance for adatom/vacancy
    targets -- it does not affect identity.
    """
    if not sites:
        return []
    xs = [s[0] for s in sites]
    ys = [s[1] for s in sites]
    zs = [s[2] for s in sites]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    out: list[Offset] = []
    for i in range(lo[0] + 1, hi[0]):
        for j in range(lo[1] + 1, hi[1]):
            for k in range(lo[2] + 1, hi[2]):
                if (i + j + k) % 2 != 0:
                    continue
                s = (i, j, k)
                if s not in occupied:
                    out.append(s)
    return out


# --------------------------------------------------------------------------- #
# 5. classify_saddle_site (categorical, section 3.3)                          #
# --------------------------------------------------------------------------- #
def _nn_spacing(points: np.ndarray) -> float:
    """Median nearest-neighbour distance among ``points`` (the local 1NN scale)."""
    m = points.shape[0]
    if m < 2:
        return float("nan")
    nn: list[float] = []
    for i in range(m):
        d = np.linalg.norm(points - points[i], axis=1)
        d[i] = np.inf
        nn.append(float(np.min(d)))
    return float(np.median(nn))


def classify_saddle_site(
    psad: np.ndarray,
    S0: np.ndarray,
    S2: np.ndarray,
    prev_kind: SaddleKind | None,
) -> SaddleKind:
    """Categorical topological class of one mover's transition-state site (contract 3.3).

    ``kind`` is decided by **counting** the occupied atoms coordinating the transition
    state ``psad`` (top=1, bridge=2, hollow=3, ``(100)`` fourfold hollow=4), never by
    rounding a continuous displacement (Geom-7 / M1). ``S0`` / ``S2`` are the ``(M, 3)``
    Cartesian positions of the occupied substrate atoms in the initial / final snapshots
    (the hopping atom's own endpoints excluded by the caller); the coordinating cutoff is
    derived from the local 1NN spacing of ``S0``, with a hysteresis band -- a saddle
    within ``eps`` of the cutoff keeps ``prev_kind`` (removes cross-cycle flicker). ``S2``
    is accepted for interface parity and reserved for future disambiguation.

    Returns ``SaddleKind.OTHER`` when the substrate is too sparse to score.
    """
    del S2  # reserved (interface parity); the initial substrate S0 defines coordination
    sub = np.asarray(S0, dtype=float)
    if sub.ndim != 2 or sub.shape[0] < 2:
        return SaddleKind.OTHER
    r_nn = _nn_spacing(sub)
    if not math.isfinite(r_nn) or r_nn <= 0.0:
        return SaddleKind.OTHER

    p = np.asarray(psad, dtype=float)
    dist = np.linalg.norm(sub - p, axis=1)
    cut = _SADDLE_COORD_FACTOR * r_nn
    band = _SADDLE_COORD_BAND * r_nn

    n_hard = int(np.count_nonzero(dist < cut - band))
    n_soft = int(np.count_nonzero(dist < cut + band))
    if n_hard == n_soft:
        count = n_hard
    elif prev_kind is not None:
        # Ambiguous boundary: keep the previously-assigned kind (hysteresis).
        return prev_kind
    else:
        count = int(np.count_nonzero(dist < cut))

    if count == 1:
        return SaddleKind.TOP
    if count == 2:
        return SaddleKind.BRIDGE
    if count == 3:
        return _hollow_subkind(p, sub, dist, r_nn)
    if count == 4:
        return SaddleKind.HOLLOW_FCC
    return SaddleKind.OTHER


def _hollow_subkind(
    psad: np.ndarray, sub: np.ndarray, dist: np.ndarray, r_nn: float
) -> SaddleKind:
    """FCC vs HCP for a 3-fold hollow: HCP has a substrate atom directly beneath."""
    coord = sub[dist < _SADDLE_COORD_FACTOR * r_nn + _SADDLE_COORD_BAND * r_nn]
    if coord.shape[0] < 3:
        return SaddleKind.HOLLOW_FCC
    center = coord.mean(axis=0)
    in_plane = np.linalg.norm(sub[:, :2] - center[:2], axis=1)
    below = sub[:, 2] < psad[2] - 0.3 * r_nn
    near = in_plane < 0.5 * r_nn
    if np.any(below & near):
        return SaddleKind.HOLLOW_HCP
    return SaddleKind.HOLLOW_FCC


# --------------------------------------------------------------------------- #
# 5. compute_depth_sig (operational, section 4.1)                             #
# --------------------------------------------------------------------------- #
def _is_occupied_pred(pred: OccPredicate) -> bool:
    """True iff a context predicate denotes an occupied site (species / OCC_ANY)."""
    return pred.kind in ("SPECIES", "OCC_ANY")


def compute_depth_sig(
    context: Sequence[StencilSite],
    movers: Sequence[Offset],
    S0: Sequence[Offset],
    *,
    d_max: int | None = None,
) -> DepthSig:
    """Operational depth signature, identically defined at ingest and runtime (contract 4.1).

    From the decorated cluster alone (no global grid): if the mover's ``r_ctx`` context
    reaches a contiguous EMPTY hemisphere with occupied backing, return
    ``SURFACE(coordination of the mover start site)``. Otherwise ``d`` = the minimum layer
    distance (``|dk|``) from the mover to the nearest EMPTY site that has an occupied
    neighbour inside the cluster; ``d <= d_max`` -> ``SUBSURF(d)``, else the explicit merge
    ``BULK_OR_DEEPER`` (param ``-1``). ``d_max`` defaults to the cluster's resolvable depth
    (the max covered ``|dk|`` in the context).

    ``movers`` / ``S0`` are anchor0-relative offsets; the primary mover is ``(0, 0, 0)``
    when present (the seed), else the smallest mover offset.
    """
    occupied: set[Offset] = {cs.off for cs in context if _is_occupied_pred(cs.pred)}
    occupied |= set(S0)
    empty: set[Offset] = {cs.off for cs in context if cs.pred.kind == "EMPTY"}
    covered: set[Offset] = {cs.off for cs in context if cs.pred.kind != "OUTSIDE"}

    mover_set = set(movers)
    primary: Offset = (0, 0, 0) if (0, 0, 0) in mover_set else min(mover_set, default=(0, 0, 0))

    # Coordination of the mover start + its empty 1NN directions.
    empty_dirs: list[np.ndarray] = []
    coordination = 0
    for off in NN12_OFFSETS:
        nb = (primary[0] + off[0], primary[1] + off[1], primary[2] + off[2])
        if nb in occupied:
            coordination += 1
        elif nb in empty:
            v = np.asarray(off, dtype=float)
            empty_dirs.append(v / np.linalg.norm(v))

    if coordination < 12 and len(empty_dirs) >= _SURFACE_MIN_EMPTY:
        net = np.sum(np.asarray(empty_dirs), axis=0)
        if float(np.linalg.norm(net)) >= _SURFACE_COHERENCE * len(empty_dirs):
            return DepthSig(DepthKind.SURFACE, coordination)

    # Subsurface / bulk: layer distance to the nearest EMPTY-with-occupied-neighbour.
    if d_max is None:
        d_max = max(
            (abs(cs.off[2] - primary[2]) for cs in context if cs.off in covered),
            default=0,
        )

    depths: list[int] = []
    for e in empty:
        has_occ_nb = any(
            (e[0] + off[0], e[1] + off[1], e[2] + off[2]) in occupied for off in NN12_OFFSETS
        )
        if has_occ_nb:
            depths.append(abs(e[2] - primary[2]))
    if not depths:
        return DepthSig(DepthKind.BULK_OR_DEEPER, -1)
    d = min(depths)
    if d <= d_max:
        return DepthSig(DepthKind.SUBSURF, d)
    return DepthSig(DepthKind.BULK_OR_DEEPER, -1)


# --------------------------------------------------------------------------- #
# Row-field access helpers                                                    #
# --------------------------------------------------------------------------- #
def _get(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Read ``key`` from a mapping or a ``pandas.Series``-like row, else ``default``."""
    try:
        contains = key in row
    except TypeError:
        contains = False
    if contains:
        return row[key]
    getter = getattr(row, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            return default
    return default


def _resolve_nu0_hz(row: Mapping[str, Any]) -> float:
    """Resolve the forward prefactor in Hz: HTST ``nu0`` if present, else ``k_prefactor``.

    Units trap (the pyKMC k0 incident, see AGENTS.md memory): the reference
    table's ``nu0`` column is stored in **Hz**, but ``k_prefactor`` (the resolved
    pyKMC prefactor, same units as ``k``) is stored in **ps^-1**. The fallback
    must therefore be scaled by 1e12; reading it as Hz turns the k0 = 1.0 ps^-1
    default into a 1 Hz prefactor and silently kills the class's rate.
    """
    for key, scale in (("nu0", 1.0), ("k_prefactor", 1.0e12)):
        val = _get(row, key)
        if val is None:
            continue
        try:
            f = float(val)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f) and f > 0.0:
            return f * scale
    return float("nan")


def _type_to_occ(symbol: Any) -> Occ:
    """Map one pyKMC species entry (symbol str or occupancy int) to an ``Occ`` code."""
    if isinstance(symbol, str):
        return type_to_occ(symbol)
    try:
        code = int(symbol)
    except (TypeError, ValueError):
        return Occ.OCC_ANY
    try:
        occ = Occ(code)
    except ValueError:
        return Occ.OCC_ANY
    if occ in (Occ.EMPTY, Occ.OCC_ANY, Occ.OUTSIDE):
        return Occ.OCC_ANY
    return occ


def _species_list(types: Any, n: int, coloring: Coloring) -> list[Occ]:
    """Per-atom occupancy codes; grey with no types -> all ``OCC_ANY``."""
    if types is None:
        if coloring == Coloring.FULL:
            raise ValueError("FULL coloring requires initial_types")
        return [Occ.OCC_ANY] * n
    seq = list(types)
    if len(seq) != n:
        raise ValueError(f"initial_types length {len(seq)} != n_atoms {n}")
    return [_type_to_occ(t) for t in seq]


def _species_pred(occ: Occ) -> OccPredicate:
    """Occupancy code -> the context predicate stored for that site."""
    if occ == Occ.EMPTY:
        return OccPredicate(kind="EMPTY")
    if occ == Occ.OUTSIDE:
        return OccPredicate(kind="OUTSIDE")
    return OccPredicate(kind="SPECIES", species=frozenset({occ}))


def _sites_within(ctr: Offset, radius_units: float) -> list[Offset]:
    """Even-parity sites within ``radius_units`` (lattice units) of ``ctr``, sorted."""
    reach = int(math.floor(radius_units)) + 1
    r2 = radius_units * radius_units
    out: list[Offset] = []
    for di in range(-reach, reach + 1):
        for dj in range(-reach, reach + 1):
            for dk in range(-reach, reach + 1):
                if (di + dj + dk) % 2 != 0:
                    continue
                if di * di + dj * dj + dk * dk <= r2:
                    out.append((ctr[0] + di, ctr[1] + dj, ctr[2] + dk))
    out.sort()
    return out


# --------------------------------------------------------------------------- #
# 5. project_event — the full section-3 pipeline                              #
# --------------------------------------------------------------------------- #
def project_event(
    row: Mapping[str, Any],
    *,
    coloring: Coloring,
    rcut: float,
    d_max: int,
    r_ctx_min: float,
) -> ProjectedEvent:
    """Project one pyKMC reference row onto the FCC frame (contract 5, ``FINAL_DESIGN`` 3).

    Runs the full section-3 pipeline: min-image-unwrap all of
    ``initial/final/saddle_positions`` about ``move_atom_idx`` -> fit the event's own
    local FCC frame -> detect the true movers (site change is ground truth) -> build
    ``delta`` / ``delta_atoms`` and the ``r_ctx``-decorated context (``EMPTY`` included,
    uncovered sites ``OUTSIDE`` + ``truncated``) -> one categorical saddle token per mover
    -> the operational depth signature. ``anchor0`` is ``(0, 0, 0)`` (the seed's snapped
    site); every offset is relative to it. ``start_rank`` on each token is left 0 (filled
    later by ``canonical``).
    """
    P0_raw = np.asarray(_get(row, "initial_positions"), dtype=float)
    P2_raw = np.asarray(_get(row, "final_positions"), dtype=float)
    Psad_raw = np.asarray(_get(row, "saddle_positions"), dtype=float)
    move_atom_idx = int(_get(row, "move_atom_idx", 0))
    cell = _get(row, "cell")
    n = P0_raw.shape[0]

    # 1. Unwrap FIRST (Geom-1), each about the mover, in the event's own cell.
    P0 = min_image_unwrap(P0_raw, move_atom_idx, cell)
    P2 = min_image_unwrap(P2_raw, move_atom_idx, cell)
    Psad = (
        min_image_unwrap(Psad_raw, move_atom_idx, cell)
        if Psad_raw.size == P0.size
        else P0.copy()
    )

    # 2. Fit the event's own local FCC frame.
    frame = fit_local_fcc(P0, move_atom_idx)

    # 3. True site-change set (ground truth), plus per-atom snapped sites.
    s0 = [_snap(frame, P0[p]) for p in range(n)]
    s2 = [_snap(frame, P2[p]) for p in range(n)]
    mover_starts, _empties = detect_movers(P0, P2, frame)

    species = _species_list(_get(row, "initial_types"), n, coloring)
    occ0: dict[Offset, Occ] = {}
    occ2: dict[Offset, Occ] = {}
    for p in range(n):
        occ0[s0[p]] = species[p]
        occ2[s2[p]] = species[p]

    # 4a. delta = only sites whose occupancy changed; delta_atoms = net occupancy change.
    touched = sorted(set(occ0) | set(occ2))
    delta: list[DeltaSite] = []
    for s in touched:
        before = occ0.get(s, Occ.EMPTY)
        after = occ2.get(s, Occ.EMPTY)
        if before != after:
            delta.append(DeltaSite(off=s, before=before, after=after))
    delta_atoms = sum(1 for ds in delta if ds.after != Occ.EMPTY) - sum(
        1 for ds in delta if ds.before != Occ.EMPTY
    )

    # 4b. Full r_ctx-decorated context about the moved-site centroid.
    moved_sites = [ds.off for ds in delta] or list(mover_starts) or [(0, 0, 0)]
    centroid = np.mean(np.asarray(moved_sites, dtype=float), axis=0)
    ctr = round_to_even_parity(centroid)
    a_fit = 2.0 * frame.h
    r_ctx = max(a_fit, rcut, r_ctx_min, (d_max + 1) * frame.h)
    origin = _origin(frame)
    truncated = False
    context: list[StencilSite] = []
    for s in _sites_within(ctr, r_ctx / frame.h):
        if s in occ0:
            pred = _species_pred(occ0[s])
        elif float(np.linalg.norm(_site_cart(frame, s) - origin)) <= rcut + 0.25 * frame.h:
            pred = OccPredicate(kind="EMPTY")
        else:
            pred = OccPredicate(kind="OUTSIDE")
            truncated = True
        context.append(StencilSite(off=s, pred=pred))

    # 5. One categorical saddle token per mover (movers-order; start_rank filled later).
    saddle_tokens = _build_saddle_tokens(mover_starts, s0, s2, P0, Psad, frame, move_atom_idx)

    # 6. Operational depth signature.
    depth_sig = compute_depth_sig(
        tuple(context), tuple(mover_starts), tuple(occ0.keys()), d_max=d_max
    )

    # Projection report (snap residuals / diameter / mover agreement) for the gates.
    proj_report = _build_report(P0, s0, s2, frame, move_atom_idx, mover_starts)

    ea_fwd = float(_get(row, "energy_barrier", float("nan")))
    k_row = float(_get(row, "k", float("nan")))
    idx_ref = int(_get(row, "idx_ref", 0))
    return ProjectedEvent(
        anchor0=(0, 0, 0),
        delta=tuple(delta),
        delta_atoms=delta_atoms,
        context=tuple(context),
        movers=tuple(mover_starts),
        saddle_tokens=saddle_tokens,
        depth_sig=depth_sig,
        coloring=coloring,
        r_ctx_used=float(r_ctx),
        truncated=truncated,
        Ea_fwd_eV=ea_fwd,
        nu0_fwd_hz=_resolve_nu0_hz(row),
        k_row=k_row,
        id_saddle=str(_get(row, "id_saddle", "")),
        id_final=str(_get(row, "id_final", "")),
        event_id=str(_get(row, "event_id", "")),
        idx_ref=idx_ref,
        idx_backward=int(_get(row, "idx_backward", -1)),
        move_atom_idx=move_atom_idx,
        source_row=int(_get(row, "source_row", idx_ref)),
        proj_report=proj_report,
    )


def _build_saddle_tokens(
    mover_starts: Sequence[Offset],
    s0: Sequence[Offset],
    s2: Sequence[Offset],
    P0: np.ndarray,
    Psad: np.ndarray,
    frame: LocalFrame,
    move_atom_idx: int,
) -> tuple[PathToken, ...]:
    """One ``PathToken`` per mover, in movers-order (``start_rank`` left 0 for canonical)."""
    # start site -> the atom index that starts there (deterministic: first / seed wins).
    start_to_atom: dict[Offset, int] = {}
    for q in range(len(s0)):
        start_to_atom.setdefault(s0[q], q)
    if move_atom_idx < len(s0):
        start_to_atom[s0[move_atom_idx]] = move_atom_idx

    tokens: list[PathToken] = []
    for ms in mover_starts:
        p: int | None = start_to_atom.get(ms)
        if p is None or Psad.shape[0] <= p:
            tokens.append(PathToken(start_rank=0, kind=SaddleKind.OTHER, coord_sig=()))
            continue
        end_site = s2[p]
        # Substrate = occupied atoms other than this hopping atom, as Cartesian positions.
        sub0 = np.asarray([P0[q] for q in range(P0.shape[0]) if q != p], dtype=float)
        kind = classify_saddle_site(Psad[p], sub0, sub0, None)
        coord_sig = _saddle_coord_sig(Psad[p], ms, end_site, s0, frame)
        tokens.append(PathToken(start_rank=0, kind=kind, coord_sig=coord_sig))
    return tuple(tokens)


def _saddle_coord_sig(
    psad: np.ndarray,
    start: Offset,
    end: Offset,
    s0: Sequence[Offset],
    frame: LocalFrame,
) -> tuple[int, ...]:
    """Sorted coordination signature of the occupied atoms coordinating the saddle site.

    For each occupied lattice site within the coordinating cutoff of ``psad`` (excluding
    the hop's own start / end), its coordination number among the initial occupancy
    ``s0``; sorted ascending (a frame-invariant integer signature).
    """
    occupied = set(s0)
    r_nn = frame.h * _SQRT2
    cut = _SADDLE_COORD_FACTOR * r_nn
    coords: list[int] = []
    for site in sorted(occupied):
        if site in (start, end):
            continue
        if float(np.linalg.norm(_site_cart(frame, site) - np.asarray(psad, dtype=float))) < cut:
            c = sum(
                1
                for off in NN12_OFFSETS
                if (site[0] + off[0], site[1] + off[1], site[2] + off[2]) in occupied
            )
            coords.append(c)
    return tuple(sorted(coords))


def _build_report(
    P0: np.ndarray,
    s0: Sequence[Offset],
    s2: Sequence[Offset],
    frame: LocalFrame,
    move_atom_idx: int,
    mover_starts: Sequence[Offset],
) -> EventProjReport:
    """Snap residuals, cluster diameter and mover-agreement for the ingest gates."""
    n = P0.shape[0]
    residuals = np.asarray(
        [float(np.linalg.norm(P0[p] - _site_cart(frame, s0[p]))) for p in range(n)],
        dtype=float,
    )
    max_residual = float(np.max(residuals)) if n else 0.0
    mover_atoms = [p for p in range(n) if s0[p] != s2[p]]
    mover_max = float(np.max(residuals[mover_atoms])) if mover_atoms else 0.0

    if n >= 2:
        diffs = P0[:, None, :] - P0[None, :, :]
        diameter = float(np.max(np.linalg.norm(diffs, axis=2)))
    else:
        diameter = 0.0

    seed_start = s0[move_atom_idx] if move_atom_idx < n else None
    mover_agreement = seed_start in set(mover_starts)
    return EventProjReport(
        max_residual=max_residual,
        mover_max_residual=mover_max,
        diameter=diameter,
        mover_agreement=mover_agreement,
    )
