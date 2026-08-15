"""Surrogate-channel codegen (Phase C channel b): bake E_sym model + per-1NN
feature tables into proclist.c, and provide the byte-parity Python reference.

The runtime surrogate channel rates *generic* 1NN vacancy-exchange candidates
(vacancy ``v`` + occupied 1NN ``n``: atom ``n → v``) that no measured proc
already covers. Its barrier is the KRA form ``Ea_hat = E_sym + ½·ΔE_H`` and its
rate ``k = tier0_nu0 · exp(−Ea_hat/kT)`` (floored), computed from the local
occupation via the exact ports of ``pylatkmc.ingest.surrogate``'s map-level
feature functions.

Everything geometric is *bakeable*: for each of the 12 crystal 1NN hop
directions codegen precomputes the context ball around the hop midpoint —
runtime-frame integer offsets, per-end crystal shell indices, per-end + midpoint
OUTSIDE("U") flags, the 1NN bond-pair list, per-site NN1/NN2 ball-adjacency
(for triangles / exposure / ΔΦ), the two mover-neighbour lists, and the affected
set. The runtime resolves sites via ``lattice_site_at_ijk``, categorises by
species (SP_VACANT/absent→"E", Ni→"N", Cr→"C", Fe→"F" — by NAME), then runs the
same reductions as :mod:`pylatkmc.ingest.surrogate`.

Species (v2 basis, 2026-08-15): the harvest-side ``"W"`` category
(WILDCARD/OCC_ANY) can never arise on this side — every live lattice site has a
definite species — but the C reductions mirror its handling term-for-term so the
two ports stay in lockstep. Fe is a first-class category (``"F"`` / ``CAT_F``),
and the pooled ridge's mover-species dummies ``mover_n_C``/``mover_n_F`` are set
from the hopping atom's species (1.0 for Cr / Fe respectively, else 0.0) in both
directional vectors.

DB-exactness (contract): E_sym is the average of the two directional feature
vectors (origin at the atom end, origin at the vacancy end), so E_sym is
invariant under n↔v swap; ΔΦ uses the n↔v-symmetric *midpoint* U-mask, so
``dphi2`` is exactly antisymmetric under the swap. Hence ``Ea_f − Ea_b = ΔE_H``
and ``k_f/k_b = exp(−ΔE_H/kT)`` to float precision.

Determinism: directions in fixed crystal-NN1 order; every ball is
``_sites_within``-sorted (offset lex == ball index order, which the ΔΦ ``j<i``
dedup relies on); all floats emitted ``%.17g``; no ``hash()``/set iteration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pylatkmc.ingest.surrogate import (
    ESYM_FEATURE_KEYS,
    H2FEATS,
    NN1,
    NN2,
    EsymModel,
    dphi2_from_maps,
    shell_of,
    state_features,
)
from pylatkmc.translator_v2 import to_runtime_frame

Offset = tuple[int, int, int]

# --------------------------------------------------------------------------- #
# Baked geometric constants (nominal crystal frame; a = 3.52 Å, h = a/2)       #
# --------------------------------------------------------------------------- #
A_NOMINAL: float = 3.52
H: float = A_NOMINAL / 2.0
R_CTX_A: float = 8.5          # context-ball radius (r_ctx_used in the catalogue)
RCUT_A: float = 8.5           # truncation radius; empty site beyond rcut+0.25h → "U"
DMAX: int = 2                 # depth resolution cap (SUBSURF d<=DMAX else BULK)

R_CTX_UNITS: float = R_CTX_A / H
TRUNC_UNITS: float = RCUT_A / H + 0.25            # rcut+0.25h in h-units
_R2_BALL: float = R_CTX_UNITS * R_CTX_UNITS
_R2_TRUNC: float = TRUNC_UNITS * TRUNC_UNITS

#: The 12 crystal 1NN hop directions (|off|² == 2), in fixed sorted order.
DIRECTIONS: tuple[Offset, ...] = tuple(sorted(NN1))

_NN1_SET = set(NN1)
_NN2_SET = set(NN2)


def _sites_within_midpoint(d: Offset, radius_units: float) -> list[Offset]:
    """Even-parity sites within ``radius_units`` of the half-integer midpoint
    ``d/2``, sorted. Centering on the true midpoint (not a snapped lattice site,
    as the ingest does) makes the ball exactly symmetric under the n↔v swap
    ``s ↔ d - s`` — the prerequisite for DB-exact forward/backward E_sym."""
    reach = int(math.floor(radius_units)) + 2
    r2x4 = 4.0 * radius_units * radius_units
    out: list[Offset] = []
    for si in range(-reach, reach + 1):
        for sj in range(-reach, reach + 1):
            for sk in range(-reach, reach + 1):
                if (si + sj + sk) % 2 != 0:
                    continue
                # |2s - d|^2 <= (2 * radius_units)^2
                a, b, c = 2 * si - d[0], 2 * sj - d[1], 2 * sk - d[2]
                if a * a + b * b + c * c <= r2x4:
                    out.append((si, sj, sk))
    out.sort()
    return out


def _sub(a: Offset, b: Offset) -> Offset:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _n2(a: Offset) -> int:
    return a[0] * a[0] + a[1] * a[1] + a[2] * a[2]


# --------------------------------------------------------------------------- #
# Per-direction geometry                                                       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DirGeom:
    """Baked context-ball geometry for one crystal 1NN hop direction.

    Vacancy is at crystal offset ``(0,0,0)`` (ball index ``vac_idx``); the atom
    is at ``dir`` (ball index ``atom_idx``). All index lists reference the sorted
    ``offs`` ball (index order == crystal-offset lex order).
    """

    dir: Offset
    runtime_dir: Offset                    # runtime-frame offset of the atom from vac
    offs: tuple[Offset, ...]               # crystal offsets, vacancy-relative, sorted
    runtime_offs: tuple[Offset, ...]       # per-site runtime offsets from the vacancy
    shell_n: tuple[int, ...]               # crystal shell from the atom end
    shell_v: tuple[int, ...]               # crystal shell from the vacancy end
    ck: tuple[int, ...]                    # crystal k-component (for depth layers)
    near_n: tuple[int, ...]                # within rcut+0.25h of the atom end
    near_v: tuple[int, ...]                # within rcut+0.25h of the vacancy end
    near_mid: tuple[int, ...]              # within rcut+0.25h of the midpoint
    vac_idx: int
    atom_idx: int
    nn1_adj: tuple[tuple[int, ...], ...]   # per site: 12 NN1 ball indices (-1 outside)
    nn2_adj: tuple[tuple[int, ...], ...]   # per site: 6 NN2 ball indices (-1 outside)
    bond_pairs: tuple[tuple[int, int], ...]  # NN1 pairs (i<j) among ball sites
    # mover neighbour lists: (ball_index, crystal_offset o from the mover)
    vac_nbrs: tuple[tuple[int, Offset], ...]
    atom_nbrs: tuple[tuple[int, Offset], ...]
    vac_tris: tuple[tuple[int, int], ...]  # NN1 pairs among vac_nbrs (ball indices)
    atom_tris: tuple[tuple[int, int], ...]
    affected: tuple[int, ...]              # NN1 of {vac,atom} not in {vac,atom}


def bake_direction(d: Offset) -> DirGeom:
    """Bake the ball geometry for hop direction ``d`` (vacancy at 0, atom at d)."""
    offs = _sites_within_midpoint(d, R_CTX_UNITS)
    idx_of = {o: i for i, o in enumerate(offs)}
    vac_idx = idx_of[(0, 0, 0)]
    atom_idx = idx_of[d]

    runtime_offs = tuple(to_runtime_frame(o) for o in offs)
    shell_n = tuple(shell_of(_sub(o, d)) for o in offs)
    shell_v = tuple(shell_of(o) for o in offs)
    ck = tuple(o[2] for o in offs)

    def near(o: Offset, seed: Offset) -> int:
        return 1 if _n2(_sub(o, seed)) <= _R2_TRUNC else 0

    near_n = tuple(near(o, d) for o in offs)
    near_v = tuple(near(o, (0, 0, 0)) for o in offs)
    # midpoint distance²: |o - d/2|² = |2o - d|² / 4
    near_mid = tuple(
        1 if _n2((2 * o[0] - d[0], 2 * o[1] - d[1], 2 * o[2] - d[2])) <= 4.0 * _R2_TRUNC else 0
        for o in offs
    )

    nn1_adj = tuple(
        tuple(idx_of.get((o[0] + a, o[1] + b, o[2] + c), -1) for (a, b, c) in NN1)
        for o in offs
    )
    nn2_adj = tuple(
        tuple(idx_of.get((o[0] + a, o[1] + b, o[2] + c), -1) for (a, b, c) in NN2)
        for o in offs
    )

    bond_pairs: list[tuple[int, int]] = []
    n = len(offs)
    for i in range(n):
        for j in range(i + 1, n):
            if _n2(_sub(offs[i], offs[j])) == 2:
                bond_pairs.append((i, j))

    def mover_nbrs(mover: Offset) -> list[tuple[int, Offset]]:
        out: list[tuple[int, Offset]] = []
        for o in NN1:
            nb = (mover[0] + o[0], mover[1] + o[1], mover[2] + o[2])
            if nb in idx_of:
                out.append((idx_of[nb], o))
        return out

    vac_nbrs = mover_nbrs((0, 0, 0))
    atom_nbrs = mover_nbrs(d)

    def tris(nbrs: list[tuple[int, Offset]]) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for a in range(len(nbrs)):
            for b in range(a + 1, len(nbrs)):
                if _n2(_sub(offs[nbrs[a][0]], offs[nbrs[b][0]])) == 2:
                    out.append((nbrs[a][0], nbrs[b][0]))
        return out

    vac_tris = tris(vac_nbrs)
    atom_tris = tris(atom_nbrs)

    dset = {(0, 0, 0), d}
    aff: set[Offset] = set()
    for dd in sorted(dset):
        for o in NN1:
            nb = (dd[0] + o[0], dd[1] + o[1], dd[2] + o[2])
            if nb not in dset and nb in idx_of:
                aff.add(nb)
    affected = tuple(sorted(idx_of[a] for a in aff))

    return DirGeom(
        dir=d,
        runtime_dir=to_runtime_frame(d),
        offs=tuple(offs),
        runtime_offs=runtime_offs,
        shell_n=shell_n,
        shell_v=shell_v,
        ck=ck,
        near_n=near_n,
        near_v=near_v,
        near_mid=near_mid,
        vac_idx=vac_idx,
        atom_idx=atom_idx,
        nn1_adj=nn1_adj,
        nn2_adj=nn2_adj,
        bond_pairs=tuple(bond_pairs),
        vac_nbrs=tuple(vac_nbrs),
        atom_nbrs=tuple(atom_nbrs),
        vac_tris=tuple(vac_tris),
        atom_tris=tuple(atom_tris),
        affected=affected,
    )


def bake_directions() -> list[DirGeom]:
    """Bake all 12 hop directions in fixed order."""
    return [bake_direction(d) for d in DIRECTIONS]


def surrogate_ball_reach(model: EsymModel) -> tuple[int, int]:
    """(reach_ij, reach_k) of the surrogate feature ball in runtime grid cells.

    The runtime resolves the ball offsets through the wrapping site grid, so the
    replica-startup vacuum guard must cover them too (like the pattern reach).
    """
    reach_ij = reach_k = 0
    for g in bake_directions():
        for (u, v, w) in g.runtime_offs:
            reach_ij = max(reach_ij, abs(u), abs(v))
            reach_k = max(reach_k, abs(w))
    return reach_ij, reach_k


# --------------------------------------------------------------------------- #
# Python reference evaluation (the C-parity oracle)                            #
# --------------------------------------------------------------------------- #
#: Runtime species NAME -> E_sym category. By NAME only — the ingest ``Occ`` and
#: runtime ``Species`` integers disagree on Cr/Fe (``Occ.CR=2, Occ.FE=3`` vs
#: ``SP_FE=2, SP_CR=3``), so an integer bridge would silently swap them.
_NAME_CAT: dict[str, str] = {"Ni": "N", "Cr": "C", "Fe": "F"}


def _build_map(
    g: DirGeom,
    species_at: dict[Offset, str],
    *,
    atom_species: str,
    atom_at_vac: bool,
    near: tuple[int, ...],
    anchor: Offset,
) -> dict[Offset, str]:
    """Category map keyed by ``anchor``-relative offsets (anchor ∈ {(0,0,0),dir}).

    ``species_at`` maps the CURRENT crystal ball offset (vacancy-relative) →
    species NAME ("Vacant"/"Ni"/"Cr"/"Fe") or ``"absent"``. The two mover sites
    are overridden per config: ``atom_at_vac`` False → atom at ``dir`` / vac at 0;
    True → atom at 0 / vac at ``dir``. Occupied sites are never "U"; an
    empty/absent site beyond the ``near`` mask → "U". The harvest-side "W"
    category never arises here (a live site always has a definite species).
    """
    m: dict[Offset, str] = {}
    for i, off in enumerate(g.offs):
        if off == (0, 0, 0):
            sp = atom_species if atom_at_vac else "Vacant"
        elif off == g.dir:
            sp = "Vacant" if atom_at_vac else atom_species
        else:
            sp = species_at[off]
        key = (off[0] - anchor[0], off[1] - anchor[1], off[2] - anchor[2])
        cat = _NAME_CAT.get(sp)
        if cat is not None:
            m[key] = cat
        else:  # vacant or absent
            m[key] = "E" if near[i] else "U"
    return m


def _depth(g: DirGeom, m: dict[Offset, str], *, seed: Offset) -> tuple[int, int]:
    """(depth_surface, depth_param) — faithful port of ingest compute_depth_sig.

    ``m`` is keyed in the same frame as ``seed`` (the primary mover). U sites
    are excluded from ``empty``; every named species (N/C/F) counts as occupied.
    """
    occupied = {off for off, c in m.items() if c in ("N", "C", "F")}
    empty = {off for off, c in m.items() if c == "E"}

    empty_dirs: list[np.ndarray] = []
    coordination = 0
    for o in NN1:
        nb = (seed[0] + o[0], seed[1] + o[1], seed[2] + o[2])
        if nb in occupied:
            coordination += 1
        elif nb in empty:
            v = np.asarray(o, dtype=float)
            empty_dirs.append(v / np.linalg.norm(v))
    if coordination < 12 and len(empty_dirs) >= 3:
        net = np.sum(np.asarray(empty_dirs), axis=0)
        if float(np.linalg.norm(net)) >= 0.5 * len(empty_dirs):
            return 1, coordination

    depths: list[int] = []
    for e in empty:
        if any((e[0] + o[0], e[1] + o[1], e[2] + o[2]) in occupied for o in NN1):
            depths.append(abs(e[2] - seed[2]))
    if not depths:
        return 0, -1  # BULK_OR_DEEPER
    dmin = min(depths)
    if dmin <= DMAX:
        return 0, dmin  # SUBSURF
    return 0, -1  # BULK_OR_DEEPER


def eval_candidate(
    model: EsymModel, g: DirGeom, species_at: dict[Offset, str], atom_species: str
) -> dict[str, float]:
    """Python oracle: E_sym / dphi2 / Ea_hat / leverage for one candidate hop.

    ``species_at`` gives the CURRENT species (atom at ``g.dir``, vacancy at 0)
    at each crystal ball offset. Two-origin E_sym average (each directional
    anchored at its own end → per-end shells) + n↔v-symmetric midpoint-mask ΔΦ.
    """
    from pylatkmc.ingest.surrogate import leverage, predict_dE, predict_esym

    def directional(near: tuple[int, ...], anchor: Offset) -> np.ndarray:
        # before = the config with the atom AT this anchor end; after = swapped.
        atom_here = anchor == g.dir  # anchor is the atom end?
        b = _build_map(g, species_at, atom_species=atom_species,
                       atom_at_vac=(anchor == (0, 0, 0)), near=near, anchor=anchor)
        a_ = _build_map(g, species_at, atom_species=atom_species,
                        atom_at_vac=(anchor == g.dir), near=near, anchor=anchor)
        _ = atom_here
        seed = (0, 0, 0)  # anchor is the seed (mover start) in anchored coords
        mvr = {
            (-anchor[0], -anchor[1], -anchor[2]),               # vacancy end
            (g.dir[0] - anchor[0], g.dir[1] - anchor[1], g.dir[2] - anchor[2]),  # atom end
        }
        fb = state_features(b, mvr)
        fa = state_features(a_, mvr)
        keys = set(fb) | set(fa)
        f: dict[str, float] = {k: 0.5 * (fb.get(k, 0.0) + fa.get(k, 0.0)) for k in keys}
        ds, dp = _depth(g, b, seed=seed)
        f["n_delta"] = 2.0
        f["abs_delta_atoms"] = 0.0
        f["depth_surface"] = float(ds)
        f["depth_param"] = float(dp)
        # mover-species dummies: the single hopping atom (same in both directional
        # vectors, so the n<->v average is unchanged and DB-exactness is preserved).
        f["mover_n_C"] = 1.0 if atom_species == "Cr" else 0.0
        f["mover_n_F"] = 1.0 if atom_species == "Fe" else 0.0
        return np.array([float(f.get(k, 0.0)) for k in ESYM_FEATURE_KEYS], dtype=np.float64)

    phi_n = directional(g.near_n, g.dir)          # atom-end anchor
    phi_v = directional(g.near_v, (0, 0, 0))      # vacancy-end anchor
    phi = 0.5 * (phi_n + phi_v)
    e_sym = predict_esym(model, phi)
    lev = leverage(model, phi)

    # ΔΦ (midpoint mask, vacancy-anchored): forward = atom n→v.
    before_mid = _build_map(g, species_at, atom_species=atom_species,
                            atom_at_vac=False, near=g.near_mid, anchor=(0, 0, 0))
    after_mid = _build_map(g, species_at, atom_species=atom_species,
                           atom_at_vac=True, near=g.near_mid, anchor=(0, 0, 0))
    dv = dphi2_from_maps(before_mid, after_mid, [(0, 0, 0), g.dir])
    d_e = predict_dE(model, dv)
    ea_hat = e_sym + 0.5 * d_e
    return {"e_sym": e_sym, "dE_H": d_e, "ea_hat": ea_hat, "leverage": lev, "phi": phi}


# --------------------------------------------------------------------------- #
# C emission                                                                   #
# --------------------------------------------------------------------------- #
def _f(x: float) -> str:
    if math.isnan(x):
        return "NAN"
    return f"{x:.17g}"


def _flat_doubles(name: str, arr: np.ndarray) -> str:
    vals = [_f(float(x)) + "," for x in np.asarray(arr, dtype=np.float64).ravel()]
    body = "\n".join(
        "    " + " ".join(vals[i : i + 6]) for i in range(0, len(vals), 6)
    )
    return f"static const double {name}[{len(vals)}] = {{\n{body}\n}};"


def _int_array(name: str, ctype: str, vals: list[int]) -> str:
    if not vals:
        return f"static const {ctype} {name}[1] = {{0}};"
    body = "\n".join(
        "    " + " ".join(f"{v}," for v in vals[i : i + 16])
        for i in range(0, len(vals), 16)
    )
    return f"static const {ctype} {name}[{len(vals)}] = {{\n{body}\n}};"


def emit_surrogate_tables(model: EsymModel) -> str:
    """Emit the surrogate model params + per-direction feature tables + the
    ``g_surrogate`` container. The struct layout lives in the runtime header
    ``surrogate.h`` (included here so proclist.c and the runtime agree — no
    duplicate typedef). Guarded at include-time by PYLATKMC_HAS_SURROGATE.
    """
    dirs = bake_directions()
    out: list[str] = []
    a = out.append
    a('#include <math.h>       /* NAN */')
    a('#include "surrogate.h"  /* SurrSite / SurrDir / Surrogate layout */')
    a("/* ================= Phase C surrogate channel (b) tables ================= */")
    a("/* Model: E_sym = ((phi-mu)/sd).w + ym ; dE_H = dphi2.h2_theta ;")
    a(" * leverage = z.Ainv.z with z=(phi-mu)/sd. Ea_hat = E_sym + 0.5*dE_H. */")
    assert len(model.mu) == len(ESYM_FEATURE_KEYS), (
        f"phi basis / model mu mismatch: model has {len(model.mu)} features, the "
        f"pinned ESYM_FEATURE_KEYS basis has {len(ESYM_FEATURE_KEYS)}. A pre-v2 "
        f"(68-key, no F/W categories, no mover dummies) esym_model.json cannot be "
        f"baked against the v2 basis — refit the model "
        f"(.scratch/phaseC/refit_esym_v2_*.py) and regenerate this proclist."
    )
    assert len(model.h2_theta) == len(H2FEATS), "H2 basis / theta mismatch"
    a("")
    # --- model vectors/matrices ---
    a(_flat_doubles("surr_mu", model.mu))
    a(_flat_doubles("surr_sd", model.sd))
    a(_flat_doubles("surr_w", model.w))
    a(_flat_doubles("surr_ainv", model.ainv))
    a(_flat_doubles("surr_h2_theta", model.h2_theta))
    a("")
    for di, g in enumerate(dirs):
        a(_emit_dir_tables(di, g))
    a("")
    a(f"static const SurrDir surr_dirs[{len(dirs)}] = {{")
    for di, g in enumerate(dirs):
        u, v, w = g.runtime_dir
        a(f"  {{ {len(g.offs)}, surr_sites_{di}, surr_nn1_{di}, surr_nn2_{di},")
        a(f"    {len(g.bond_pairs)}, surr_bi_{di}, surr_bj_{di}, {g.vac_idx}, {g.atom_idx},")
        a(f"    {u},{v},{w},")
        a(f"    {len(g.vac_nbrs)}, surr_vn_{di}, surr_vno_{di},")
        a(f"    {len(g.atom_nbrs)}, surr_an_{di}, surr_ano_{di},")
        a(f"    {len(g.vac_tris)}, surr_vt_{di}, {len(g.atom_tris)}, surr_at_{di},")
        a(f"    {len(g.affected)}, surr_aff_{di} }},")
    a("};")
    a("")
    rng = model.context_count_ranges
    n_lo, n_hi = rng.get("N", (0, 0))
    c_lo, c_hi = rng.get("C", (0, 0))
    e_lo, e_hi = rng.get("E", (0, 0))
    # An all-NiCr-trained model has no "F" range → (0, 0), so ANY runtime context
    # containing an Fe atom trips SURR_TRIG_SPECIES and lands on the flag registry.
    # That is the intended behaviour: ΔE_H has no Fe terms, so an Fe candidate is
    # extrapolation until an Fe-bearing corpus is fit.
    f_lo, f_hi = rng.get("F", (0, 0))
    # NOTE: field order below MUST match `struct Surrogate` in runtime/src/core/
    # surrogate.h exactly (positional initialisation; a one-sided reorder compiles
    # clean and reads garbage).
    a("static const Surrogate g_surrogate = {")
    a(f"    {len(ESYM_FEATURE_KEYS)}, {len(H2FEATS)}, {len(dirs)},")
    a("    surr_mu, surr_sd, surr_w, surr_ainv, surr_h2_theta,")
    a(f"    {_f(model.ym)}, {_f(model.tier0_nu0_hz)}, {_f(model.lev_q75)}, "
      f"{_f(model.ea_clamp[0])}, {_f(model.ea_clamp[1])},")
    a(f"    {int(n_lo)}, {int(n_hi)}, {int(c_lo)}, {int(c_hi)}, "
      f"{int(e_lo)}, {int(e_hi)}, {int(f_lo)}, {int(f_hi)}, surr_dirs,")
    a("};")
    a("")
    a(f'const char *const pylatkmc_surrogate_model_version = {_c_str(model.model_version)};')
    a(f'const char *const pylatkmc_dE_model_version = {_c_str(model.dE_model_version)};')
    a('const char *const pylatkmc_nu0_pair_policy = "harvested_pair";')
    a("")
    a(_MEASURED_COVERS_C)
    return "\n".join(out) + "\n"


def _c_str(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


#: The measured-channel de-dup helper (surrogate.c calls it). Emitted into
#: proclist.c AFTER the pattern tables so it can read v2_patterns / V2_OPS /
#: v2_procs / v2_delta_rows and avail_sites_is_enrolled directly.
_MEASURED_COVERS_C = r"""/* Does any enrolled MEASURED proc already do the vacancy move vac_site→neigh_site
 * (v_origin at vac_site, v_dest at neigh_site)? Used to de-dup the surrogate
 * channel against channel (a). O(N_PROCS) per call (fine for the smoke). */
static int32_t surr_proc_vsite(const Lattice *lat, int32_t anchor, int32_t proc, int row)
{
    if (row < 0) return -1;
    const V2Proc *pr = &v2_procs[proc];
    const V2Pattern *pt = &v2_patterns[pr->pat];
    const int8_t *R = V2_OPS[pr->op];
    const V2DeltaRow *dr = &v2_delta_rows[pt->delta_begin + row];
    const int16_t *c0 = &lat->site_ijk[3 * anchor];
    int32_t di = R[0]*dr->di + R[1]*dr->dj + R[2]*dr->dk;
    int32_t dj = R[3]*dr->di + R[4]*dr->dj + R[5]*dr->dk;
    int32_t dk = R[6]*dr->di + R[7]*dr->dj + R[8]*dr->dk;
    return lattice_site_at_ijk(lat, c0[0]+di, c0[1]+dj, c0[2]+dk);
}
int pylatkmc_measured_covers_hop(const Lattice *lat, const State *st,
                                 const AvailSites *as,
                                 int32_t vac_site, int32_t neigh_site)
{
    (void)st;
    for (int32_t p = 0; p < N_PROCS; ++p) {
        if (avail_sites_is_enrolled(as, p, vac_site) != 1) continue;
        const V2Pattern *pt = &v2_patterns[v2_procs[p].pat];
        int32_t vo = surr_proc_vsite(lat, vac_site, p, pt->v_origin_row);
        int32_t vd = surr_proc_vsite(lat, vac_site, p, pt->v_dest_row);
        if (vo == vac_site && vd == neigh_site) return 1;
    }
    return 0;
}
"""


def _emit_dir_tables(di: int, g: DirGeom) -> str:
    out: list[str] = []
    a = out.append
    # sites
    rows = []
    for i in range(len(g.offs)):
        u, v, w = g.runtime_offs[i]
        rows.append(
            f"{{{u},{v},{w},{g.shell_n[i]},{g.shell_v[i]},{g.ck[i]},"
            f"{g.near_n[i]},{g.near_v[i]},{g.near_mid[i]}}},"
        )
    body = "\n".join("  " + " ".join(rows[i : i + 4]) for i in range(0, len(rows), 4))
    a(f"static const SurrSite surr_sites_{di}[{len(rows)}] = {{\n{body}\n}};")
    # adjacency
    nn1 = [x for row in g.nn1_adj for x in row]
    nn2 = [x for row in g.nn2_adj for x in row]
    a(_int_array(f"surr_nn1_{di}", "int16_t", nn1))
    a(_int_array(f"surr_nn2_{di}", "int16_t", nn2))
    a(_int_array(f"surr_bi_{di}", "int16_t", [p[0] for p in g.bond_pairs]))
    a(_int_array(f"surr_bj_{di}", "int16_t", [p[1] for p in g.bond_pairs]))
    a(_int_array(f"surr_vn_{di}", "int16_t", [p[0] for p in g.vac_nbrs]))
    a(_int_array(f"surr_vno_{di}", "int8_t", [c for p in g.vac_nbrs for c in p[1]]))
    a(_int_array(f"surr_an_{di}", "int16_t", [p[0] for p in g.atom_nbrs]))
    a(_int_array(f"surr_ano_{di}", "int8_t", [c for p in g.atom_nbrs for c in p[1]]))
    a(_int_array(f"surr_vt_{di}", "int16_t", [x for p in g.vac_tris for x in p]))
    a(_int_array(f"surr_at_{di}", "int16_t", [x for p in g.atom_tris for x in p]))
    a(_int_array(f"surr_aff_{di}", "int16_t", list(g.affected)))
    return "\n".join(out)


def emit_surrogate_externs(model: EsymModel) -> str:
    """The proclist.h externs + PYLATKMC_HAS_SURROGATE guard for the channel.

    Includes the runtime ``surrogate.h`` (same struct layout proclist.c bakes)
    so ``pylatkmc_surrogate`` has a complete type at every runtime call site.
    """
    from pylatkmc.translator_v2 import MEASURED_ANCHORED_FORM

    return (
        '\n/* ---- Phase C surrogate channel (b) ---- */\n'
        '#include "surrogate.h"\n'
        "#define PYLATKMC_HAS_SURROGATE 1\n"
        "/* N6 staged-migration switch (memo §8-N6); ships OFF — measured classes\n"
        " * fire raw harvested pairs. ON would fire E_sym_measured + 0.5*dE_H,\n"
        f" * stamped per dE_model_version = {model.dE_model_version!r}. */\n"
        f"#define PYLATKMC_MEASURED_ANCHORED_FORM {int(MEASURED_ANCHORED_FORM)}\n"
        "extern const Surrogate *const pylatkmc_surrogate;\n"
        "extern const char *const pylatkmc_surrogate_model_version;\n"
        "extern const char *const pylatkmc_dE_model_version;\n"
        "extern const char *const pylatkmc_nu0_pair_policy;\n"
        "/* measured-channel de-dup helper (defined in proclist.c) */\n"
        "int pylatkmc_measured_covers_hop(const struct Lattice *lat,\n"
        "        const struct State *st, const struct AvailSites *as,\n"
        "        int32_t vac_site, int32_t neigh_site);\n"
    )


__all__ = (
    "DIRECTIONS",
    "DirGeom",
    "R_CTX_A",
    "bake_direction",
    "bake_directions",
    "emit_surrogate_externs",
    "emit_surrogate_tables",
    "eval_candidate",
    "surrogate_ball_reach",
)
