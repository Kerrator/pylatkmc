"""Unit tests for ``pylatkmc.ingest.event_projection`` (Agent A4, contract 11.3).

Pure-math tests (numpy only; no ingest extras). Synthetic clusters are built on the
ideal FCC frame (``h = a/2``, ``R = I``) with optional Gaussian jitter, exercising:

* **Boundary unwrap (Geom-1):** ``min_image_unwrap`` restores the true ``~2.49 A``
  neighbour bonds of a mover near an in-plane face; without it the fit infers a phantom
  in-plane surface (a bulk hop mis-routed into the surface regime) and the cluster
  straddles the box (G7).
* **True movers (section 3.2):** a 3-site concerted crowdion whose ``move_atom_idx``
  names only one mover -> ``detect_movers`` finds all three; G4 mover-agreement holds.
* **Categorical saddle token (Geom-7 / M1):** bridge vs hollow vs top are distinct and
  stable across 100 jittered re-relaxations; a 2-mover event's tokens are bound to their
  own movers; hysteresis holds a boundary kind.
* **Operational depth signature (section 4.1):** SURFACE / SUBSURF / BULK_OR_DEEPER from
  planted clusters, capped at ``d_max``.

Plus the two core cases the task names: a 2-site hop and a 3-site concerted event.
"""

from __future__ import annotations

import math

import numpy as np

from pylatkmc.ingest.event_class import (
    Coloring,
    DepthKind,
    GateOutcome,
    GateThresholds,
    Occ,
    OccPredicate,
    SaddleKind,
    StencilSite,
    run_gates,
)
from pylatkmc.ingest.event_projection import (
    classify_saddle_site,
    compute_depth_sig,
    detect_movers,
    fit_local_fcc,
    min_image_unwrap,
    project_event,
)
from pylatkmc.ingest.lattice import NN12_OFFSETS

H = 1.76  # half spacing a/2 for a = 3.52 A
NN = H * math.sqrt(2.0)  # 1NN spacing ~ 2.489 A


# --------------------------------------------------------------------------- #
# Cluster builders                                                            #
# --------------------------------------------------------------------------- #
def _ball_sites(rad2: int) -> list[tuple[int, int, int]]:
    """Even-parity offsets within squared index radius ``rad2`` of the origin, sorted."""
    reach = int(math.isqrt(rad2)) + 1
    out = [
        (i, j, k)
        for i in range(-reach, reach + 1)
        for j in range(-reach, reach + 1)
        for k in range(-reach, reach + 1)
        if (i + j + k) % 2 == 0 and i * i + j * j + k * k <= rad2
    ]
    return sorted(out)


def _cart(off: tuple[int, int, int]) -> np.ndarray:
    """Ideal Cartesian position of an integer offset (R = I)."""
    return H * np.asarray(off, dtype=float)


def _positions(occ: dict[tuple[int, int, int], str]):
    """Return (positions, types, sorted_sites) for an occupancy dict, sorted by site."""
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    return pos, types, sites


def _row(**kw):
    """A reference-row mapping with sane defaults for the fields project_event reads."""
    base = dict(
        energy_barrier=0.6,
        k=1.0e6,
        k_prefactor=1.0e13,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        source_row=0,
        cell=None,
    )
    base.update(kw)
    return base


def _thresholds() -> GateThresholds:
    """Permissive gate thresholds so structural (not barrier) properties drive outcomes."""
    return GateThresholds(
        emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0
    )


# --------------------------------------------------------------------------- #
# min_image_unwrap / fit_local_fcc                                            #
# --------------------------------------------------------------------------- #
def test_min_image_unwrap_restores_bond_lengths():
    """A neighbour wrapped to the far box side is brought back to ~2.49 A (Geom-1)."""
    box = 20.0
    cell = np.array([box, box, box])
    # mover at the +x edge; its -x neighbour lives one box away (wrapped).
    mover = np.array([0.5, 10.0, 10.0])
    wrapped_neighbour = np.array([0.5 - NN + box, 10.0, 10.0])  # true x < 0 -> +box
    good_neighbour = np.array([0.5 + NN, 10.0, 10.0])
    raw = np.stack([mover, wrapped_neighbour, good_neighbour])
    assert np.linalg.norm(raw[1] - raw[0]) > box / 2  # raw: looks far away

    unw = min_image_unwrap(raw, about=0, cell=cell)
    assert math.isclose(float(np.linalg.norm(unw[1] - unw[0])), NN, rel_tol=1e-6)
    assert math.isclose(float(np.linalg.norm(unw[2] - unw[0])), NN, rel_tol=1e-6)


def test_min_image_unwrap_noop_without_cell():
    """With no cell the positions pass through unchanged (identity)."""
    P = np.random.default_rng(0).normal(size=(6, 3))
    out = min_image_unwrap(P, about=0, cell=None)
    assert np.allclose(out, P)


def test_fit_local_fcc_recovers_identity_frame():
    """An ideal axis-aligned cluster fits h ~ a/2 and R ~ I; the seed snaps to (0,0,0)."""
    occ = {s: "Ni" for s in _ball_sites(6)}
    pos, _types, sites = _positions(occ)
    mi = sites.index((0, 0, 0))
    frame = fit_local_fcc(pos, mi)
    assert math.isclose(frame.h, H, rel_tol=1e-6)
    assert np.allclose(np.asarray(frame.R), np.eye(3), atol=1e-6)


def test_fit_local_fcc_recovers_rotated_frame():
    """A rigidly rotated ideal cluster is recovered: snapping reproduces the sites."""
    from pylatkmc.ingest.event_projection import _snap

    occ = {s: "Ni" for s in _ball_sites(6)}
    pos, _types, sites = _positions(occ)
    theta = 0.3
    rot = np.array(
        [
            [math.cos(theta), -math.sin(theta), 0.0],
            [math.sin(theta), math.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    rpos = pos @ rot.T
    mi = sites.index((0, 0, 0))
    frame = fit_local_fcc(rpos, mi)
    snapped = [_snap(frame, rpos[p]) for p in range(len(sites))]
    assert set(snapped) == set(sites)


# --------------------------------------------------------------------------- #
# Boundary unwrap regression (Geom-1)                                         #
# --------------------------------------------------------------------------- #
def _wrap(P: np.ndarray, box: float) -> np.ndarray:
    """Wrap every coordinate into [0, box)."""
    return P % box


def test_boundary_unwrap_prevents_phantom_surface():
    """Unwrap keeps a face-adjacent bulk mover 12-coordinated; the raw cluster fakes a surface."""
    from pylatkmc.ingest.event_projection import _site_cart, _snap

    box = 20.0
    cell = np.array([box, box, box])
    shift = np.array([1.5, 10.0, 10.0])  # mover 1.5 A from the x = 0 face
    sites = _ball_sites(6)
    ss = sorted(sites)
    mi = ss.index((0, 0, 0))
    true = np.asarray([_cart(s) + shift for s in ss], dtype=float)
    raw = _wrap(true, box)

    def coordination(pos: np.ndarray) -> int:
        frame = fit_local_fcc(pos, mi)
        occ = {_snap(frame, pos[p]) for p in range(len(pos))}
        return sum(1 for off in NN12_OFFSETS if off in occ)

    # Raw (no unwrap): 4 wrapped neighbours vanish -> phantom under-coordination.
    assert coordination(raw) < 12
    # Unwrapped: the true bulk coordination is restored.
    unw = min_image_unwrap(raw, mi, cell)
    assert coordination(unw) == 12

    def depth_kind(pos: np.ndarray) -> DepthKind:
        frame = fit_local_fcc(pos, mi)
        occ = {_snap(frame, pos[p]) for p in range(len(pos))}
        origin = np.asarray(frame.origin)
        ctx: list[StencilSite] = []
        for off in _ball_sites(20):
            if off in occ:
                pred = OccPredicate(kind="SPECIES", species=frozenset({Occ.NI}))
            elif float(np.linalg.norm(_site_cart(frame, off) - origin)) <= 5.0 + 0.25 * frame.h:
                pred = OccPredicate(kind="EMPTY")
            else:
                pred = OccPredicate(kind="OUTSIDE")
            ctx.append(StencilSite(off, pred))
        return compute_depth_sig(ctx, [(0, 0, 0)], [], d_max=2).kind

    # The regression: without unwrap the bulk hop is misrouted into SURFACE.
    assert depth_kind(unw) != DepthKind.SURFACE
    assert depth_kind(raw) == DepthKind.SURFACE


def test_g7_fails_on_straddling_cluster_without_unwrap():
    """A face-straddling cluster passes G7 once unwrapped and fails when left wrapped."""
    box = 20.0
    shift = np.array([1.5, 10.0, 10.0])
    occ = {s: "Ni" for s in _ball_sites(6)}
    del occ[(1, 1, 0)]  # vacancy target for the hop
    ss = sorted(occ)
    mi = ss.index((0, 0, 0))
    P0true = np.asarray([_cart(s) + shift for s in ss], dtype=float)
    P2true = P0true.copy()
    P2true[mi] = _cart((1, 1, 0)) + shift
    Psad = P0true.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0))) + shift
    types = [occ[s] for s in ss]
    raw0, raw2, raws = _wrap(P0true, box), _wrap(P2true, box), _wrap(Psad, box)
    common = dict(
        initial_positions=raw0,
        final_positions=raw2,
        saddle_positions=raws,
        initial_types=types,
        move_atom_idx=mi,
    )
    th = _thresholds()

    pe_ok = project_event(
        _row(cell=np.array([box, box, box]), **common),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
    )
    g_ok = run_gates(pe_ok, thresholds=th)
    assert g_ok[6].gate == "G7" and g_ok[6].outcome == GateOutcome.PASS

    pe_bad = project_event(
        _row(cell=None, **common),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
    )
    g_bad = run_gates(pe_bad, thresholds=th)
    assert g_bad[6].gate == "G7" and g_bad[6].outcome == GateOutcome.FAIL


# --------------------------------------------------------------------------- #
# Core case 1: 2-site hop                                                     #
# --------------------------------------------------------------------------- #
def test_two_site_hop_delta_movers_and_gates():
    """A single Cr atom hops into a Ni-matrix vacancy: 1 mover, 2-site conserving delta."""
    occ = {s: "Ni" for s in _ball_sites(6)}
    del occ[(1, 1, 0)]  # vacancy target
    occ[(0, 0, 0)] = "Cr"  # the mover (full colour)
    pos, types, sites = _positions(occ)
    mi = sites.index((0, 0, 0))
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))

    pe = project_event(
        _row(
            initial_positions=pos,
            final_positions=P2,
            saddle_positions=Psad,
            initial_types=types,
            move_atom_idx=mi,
        ),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
    )

    assert pe.anchor0 == (0, 0, 0)
    assert pe.movers == ((0, 0, 0),)
    changed = {(ds.off, ds.before, ds.after) for ds in pe.delta}
    assert changed == {
        ((0, 0, 0), Occ.CR, Occ.EMPTY),
        ((1, 1, 0), Occ.EMPTY, Occ.CR),
    }
    assert pe.delta_atoms == 0
    assert pe.proj_report.mover_agreement is True
    assert pe.proj_report.max_residual < 1e-9

    outcomes = {g.gate: g.outcome for g in run_gates(pe, thresholds=_thresholds())}
    assert outcomes["G5"] == GateOutcome.PASS  # conserving
    # mover agreement holds -> not FAIL; the deferred ideal-site round-trip is NA.
    assert outcomes["G4"] == GateOutcome.NA
    assert outcomes["G3"] == GateOutcome.PASS  # snaps cleanly
    assert outcomes["G7"] == GateOutcome.PASS  # compact cluster


# --------------------------------------------------------------------------- #
# Core case 2 / true movers (section 3.2): 3-site concerted crowdion          #
# --------------------------------------------------------------------------- #
def _concerted_crowdion():
    """Build a [110] crowdion: A->D, B->A, C->B; move_atom_idx names only A."""
    box_sites = [
        (i, j, k)
        for i in range(-2, 4)
        for j in range(-2, 4)
        for k in range(-1, 2)
        if (i + j + k) % 2 == 0
    ]
    occ = {s: "Ni" for s in box_sites}
    a, b, c, d = (0, 0, 0), (1, 1, 0), (2, 2, 0), (-1, -1, 0)
    del occ[d]  # the vacancy the chain migrates into
    pos, types, sites = _positions(occ)
    idx = {s: sites.index(s) for s in (a, b, c)}
    P2 = pos.copy()
    P2[idx[a]] = _cart(d)  # A -> D
    P2[idx[b]] = _cart(a)  # B -> A
    P2[idx[c]] = _cart(b)  # C -> B
    Psad = pos.copy()
    Psad[idx[a]] = 0.5 * (_cart(a) + _cart(d))
    Psad[idx[b]] = 0.5 * (_cart(b) + _cart(a))
    Psad[idx[c]] = 0.5 * (_cart(c) + _cart(b))
    return occ, pos, P2, Psad, types, sites, idx[a], (a, b, c)


def test_three_site_concerted_true_movers():
    """detect_movers finds all three concerted movers even though only A is named."""
    occ, pos, P2, Psad, types, sites, mi, starts = _concerted_crowdion()
    frame = fit_local_fcc(pos, mi)
    movers, _empties = detect_movers(pos, P2, frame)
    assert set(movers) == set(starts)
    assert len(movers) == 3


def test_three_site_concerted_project_event():
    """The projected concerted event carries 3 movers and agrees with move_atom_idx (G4)."""
    occ, pos, P2, Psad, types, sites, mi, starts = _concerted_crowdion()
    pe = project_event(
        _row(
            initial_positions=pos,
            final_positions=P2,
            saddle_positions=Psad,
            initial_types=types,
            move_atom_idx=mi,
        ),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
    )
    assert len(pe.movers) == 3
    assert set(pe.movers) == set(starts)
    assert len(pe.saddle_tokens) == 3  # one per mover, movers-ordered
    assert pe.proj_report.mover_agreement is True
    # Homospecies chain: only the two chain ENDS change occupancy (D fills, C empties).
    assert pe.delta_atoms == 0
    changed_sites = {ds.off for ds in pe.delta}
    assert (-1, -1, 0) in changed_sites  # D became occupied
    assert (2, 2, 0) in changed_sites  # C became empty


# --------------------------------------------------------------------------- #
# Saddle token: categorical, stable, mover-bound (Geom-7 / M1, Sym-6)         #
# --------------------------------------------------------------------------- #
def _bridge_substrate():
    sub = np.array([[-NN / 2, 0.0, 0.0], [NN / 2, 0.0, 0.0], [10.0, 10.0, 0.0], [10.0, 10.0, NN]])
    sad = np.array([0.0, 0.0, math.sqrt(NN**2 - (NN / 2) ** 2)])
    return sub, sad


def _hollow_substrate():
    half = NN / 2
    sub = np.array(
        [[half, half, 0.0], [half, -half, 0.0], [-half, half, 0.0], [-half, -half, 0.0]]
    )
    sad = np.array([0.0, 0.0, math.sqrt(NN**2 - 2 * half**2)])
    return sub, sad


def _top_substrate():
    sub = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 0.0], [10.0, 10.0, NN]])
    sad = np.array([0.0, 0.0, NN])
    return sub, sad


def test_classify_bridge_hollow_top_distinct():
    """Counting the coordinating occupied atoms distinguishes bridge / hollow / top."""
    sub, sad = _bridge_substrate()
    assert classify_saddle_site(sad, sub, sub, None) == SaddleKind.BRIDGE
    sub, sad = _hollow_substrate()
    assert classify_saddle_site(sad, sub, sub, None) == SaddleKind.HOLLOW_FCC
    sub, sad = _top_substrate()
    assert classify_saddle_site(sad, sub, sub, None) == SaddleKind.TOP


def test_classify_stable_under_jitter():
    """The categorical kind does not flicker over 100 jittered re-relaxations (Geom-7/M1)."""
    rng = np.random.default_rng(12345)
    for builder, expected in (
        (_bridge_substrate, SaddleKind.BRIDGE),
        (_hollow_substrate, SaddleKind.HOLLOW_FCC),
        (_top_substrate, SaddleKind.TOP),
    ):
        base_sub, base_sad = builder()
        for _ in range(100):
            sub = base_sub + rng.normal(scale=0.05, size=base_sub.shape)
            sad = base_sad + rng.normal(scale=0.05, size=base_sad.shape)
            assert classify_saddle_site(sad, sub, sub, None) == expected


def test_classify_hysteresis_holds_boundary_kind():
    """A saddle within the boundary band keeps its previously-assigned kind (hysteresis)."""
    from pylatkmc.ingest.event_projection import _SADDLE_COORD_FACTOR

    # A remote 4-atom square (side = 1NN) pins the local 1NN scale to NN; two
    # coordinating atoms sit exactly at the cutoff radius, making the count ambiguous.
    ref = np.array(
        [[20.0, 20.0, 20.0], [20.0 + NN, 20.0, 20.0], [20.0, 20.0 + NN, 20.0], [20.0 + NN, 20.0 + NN, 20.0]]
    )
    r = _SADDLE_COORD_FACTOR * NN
    boundary = np.array([[r, 0.0, 0.0], [-r, 0.0, 0.0]])
    sub = np.vstack([boundary, ref])
    sad = np.array([0.0, 0.0, 0.0])
    # With a prior kind, the ambiguous boundary retains it rather than flipping.
    assert classify_saddle_site(sad, sub, sub, SaddleKind.BRIDGE) == SaddleKind.BRIDGE
    assert classify_saddle_site(sad, sub, sub, SaddleKind.TOP) == SaddleKind.TOP


def test_saddle_tokens_bound_to_own_mover():
    """Every token is derived from its OWN mover's saddle, in movers-order (Sym-6)."""
    from pylatkmc.ingest.event_projection import _build_saddle_tokens, _snap

    occ, pos, P2, Psad, types, sites, mi, starts = _concerted_crowdion()
    frame = fit_local_fcc(pos, mi)
    s0 = [_snap(frame, pos[p]) for p in range(len(pos))]
    s2 = [_snap(frame, P2[p]) for p in range(len(pos))]
    movers, _empties = detect_movers(pos, P2, frame)

    tokens = _build_saddle_tokens(movers, s0, s2, pos, Psad, frame, mi)
    assert len(tokens) == len(movers)

    # Positional binding: recompute each mover's kind independently and match by index.
    start_to_atom: dict[tuple[int, int, int], int] = {}
    for p in range(len(s0)):
        start_to_atom.setdefault(s0[p], p)
    start_to_atom[s0[mi]] = mi
    for i, ms in enumerate(movers):
        p = start_to_atom[ms]
        sub = np.asarray([pos[q] for q in range(len(pos)) if q != p], dtype=float)
        expected = classify_saddle_site(Psad[p], sub, sub, None)
        assert tokens[i].kind == expected
    # start_rank is left 0 by A4 (filled by canonical in the winning (a*, g*) frame).
    assert all(t.start_rank == 0 for t in tokens)


# --------------------------------------------------------------------------- #
# Operational depth signature (section 4.1)                                   #
# --------------------------------------------------------------------------- #
def _occ_pred() -> OccPredicate:
    return OccPredicate(kind="SPECIES", species=frozenset({Occ.NI}))


def _empty_pred() -> OccPredicate:
    return OccPredicate(kind="EMPTY")


def _slab_context(mover_k: int, k_top: int, reach: int) -> list[StencilSite]:
    """Even-parity sites within ``reach`` of the mover, occupied for k <= k_top else EMPTY."""
    ctx: list[StencilSite] = []
    for i in range(-reach, reach + 1):
        for j in range(-reach, reach + 1):
            for k in range(-reach, reach + 1):
                if (i + j + k) % 2 != 0:
                    continue
                if i * i + j * j + (k - mover_k) ** 2 > reach * reach + 1:
                    continue
                pred = _occ_pred() if k <= k_top else _empty_pred()
                ctx.append(StencilSite((i, j, k), pred))
    return ctx


def test_depth_sig_surface():
    """A mover with a coherent EMPTY +z hemisphere and occupied backing -> SURFACE(coord)."""
    ctx = [StencilSite((0, 0, 0), _occ_pred())]
    for off in NN12_OFFSETS:
        ctx.append(StencilSite(off, _empty_pred() if off[2] == 1 else _occ_pred()))
    ds = compute_depth_sig(ctx, [(0, 0, 0)], [(0, 0, 0)], d_max=3)
    assert ds.kind == DepthKind.SURFACE
    assert ds.param == 8  # (100) surface coordination: 4 in-layer + 4 below


def test_depth_sig_subsurface_and_capping():
    """One layer below a surface -> SUBSURF(d); the same event past d_max -> BULK_OR_DEEPER."""
    ctx = _slab_context(mover_k=0, k_top=1, reach=3)  # mover 1 layer below the top
    ds = compute_depth_sig(ctx, [(0, 0, 0)], [], d_max=3)
    assert ds.kind == DepthKind.SUBSURF
    assert ds.param >= 1
    capped = compute_depth_sig(ctx, [(0, 0, 0)], [], d_max=1)
    assert capped.kind == DepthKind.BULK_OR_DEEPER
    assert capped.param == -1


def test_depth_sig_bulk_or_deeper():
    """A fully coordinated cluster with no covered vacuum -> BULK_OR_DEEPER (explicit merge)."""
    ctx = _slab_context(mover_k=0, k_top=99, reach=3)  # dense: nothing empty
    ds = compute_depth_sig(ctx, [(0, 0, 0)], [], d_max=3)
    assert ds.kind == DepthKind.BULK_OR_DEEPER
    assert ds.param == -1


def test_depth_sig_surface_at_top_layer():
    """A mover on the top layer of a slab is classified SURFACE."""
    ctx = _slab_context(mover_k=2, k_top=2, reach=3)
    ds = compute_depth_sig(ctx, [(0, 0, 2)], [], d_max=3)
    assert ds.kind == DepthKind.SURFACE
