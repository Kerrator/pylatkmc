"""Padded-cluster builder (protocol decisions 1-2).

Per event: fit the robust local frame (installed pinned-h fitter), map real atoms to
FCC sites, detect visible vacuum planes (top/bottom, lab z), then synthesize frozen
all-Ni padding on ideal sites in the shell rcut < h|off| <= rcut + EAM cutoff so every
real atom has a complete force environment. All real atoms stay free.
"""
from __future__ import annotations

import numpy as np

from pylatkmc.ingest.event_projection import fit_local_fcc, round_to_even_parity

import rc_common as C


class PrepError(RuntimeError):
    pass


def build_padded_cluster(row) -> dict:
    P0 = np.asarray(row["initial_positions"], float)
    Psad = np.asarray(row["saddle_positions"], float)
    Pfin = np.asarray(row["final_positions"], float)
    types = [str(t) for t in row["initial_types"]]
    mover = int(row["move_atom_idx"])
    n_real = len(P0)

    frame = fit_local_fcc(P0, mover, nominal_a=C.NOMINAL_A)
    R = np.asarray(frame.R, float)
    origin = np.asarray(frame.origin, float)
    h = float(frame.h)

    # --- occupancy of ideal sites by real atoms (initial state) ---
    rel = (P0 - origin) @ R / h          # R.T @ (x - origin) / h, row-wise
    occ: dict[tuple[int, int, int], int] = {}
    bad_snap = []
    for i in range(n_real):
        off = round_to_even_parity(rel[i])
        res = np.linalg.norm(rel[i] - np.asarray(off)) * h
        if res < C.SNAP_TOL:
            if off in occ:
                bad_snap.append(("collision", i, occ[off]))
            occ[off] = i
        else:
            bad_snap.append(("off_lattice", i, round(res, 3)))

    # --- candidate site enumeration (integer criterion, R-independent) ---
    nmax = int(np.floor(C.PAD_RMAX / h)) + 1
    rng = range(-nmax, nmax + 1)
    r2_ball = (C.RCUT / h) ** 2
    r2_pad = (C.PAD_RMAX / h) ** 2
    in_ball, pad_cand = [], []
    for i in rng:
        for j in rng:
            for k in rng:
                if (i + j + k) % 2:
                    continue
                r2 = i * i + j * j + k * k
                if r2 <= r2_ball:
                    in_ball.append((i, j, k))
                elif r2 <= r2_pad:
                    pad_cand.append((i, j, k))

    def site_xyz(offs):
        a = np.asarray(offs, float)
        return origin + (a @ R.T) * h

    ball_xyz = site_xyz(in_ball)
    occ_mask = np.array([o in occ for o in in_ball])
    z_ball = ball_xyz[:, 2]
    zmax_occ = z_ball[occ_mask].max()
    zmin_occ = z_ball[occ_mask].min()

    # visible vacuum: an EMPTY in-ball site at least SURF_TOL beyond the occupied extreme
    empty_z = z_ball[~occ_mask]
    top_visible = bool((empty_z > zmax_occ + C.SURF_TOL).any())
    bot_visible = bool((empty_z < zmin_occ - C.SURF_TOL).any())

    pad_xyz = site_xyz(pad_cand)
    keep = np.ones(len(pad_cand), bool)
    if top_visible:
        keep &= pad_xyz[:, 2] <= zmax_occ + C.SURF_TOL
    if bot_visible:
        keep &= pad_xyz[:, 2] >= zmin_occ - C.SURF_TOL
    pad_xyz = pad_xyz[keep]

    # safety: no pad within 2.0 A of any real atom in any state
    for P in (P0, Psad, Pfin):
        if len(pad_xyz):
            d2 = ((pad_xyz[:, None, :] - P[None, :, :]) ** 2).sum(-1)
            pad_xyz = pad_xyz[d2.min(1) > 4.0]

    n_pad = len(pad_xyz)
    if n_pad == 0:
        raise PrepError("no padding generated — inspect frame/surface detection")

    def padded(P):
        return np.vstack([P, pad_xyz])

    return {
        "n_real": n_real,
        "n_pad": n_pad,
        "mover": mover,
        "types": types + ["Ni"] * n_pad,
        "init": padded(P0),
        "sad": padded(Psad),
        "fin": padded(Pfin),
        "frame_R": R,
        "frame_origin": origin,
        "h": h,
        "surface": {
            "top_visible": top_visible,
            "bot_visible": bot_visible,
            "zmax_occ": float(zmax_occ),
            "zmin_occ": float(zmin_occ),
            "pad_unresolved_top": not top_visible,
            "pad_unresolved_bot": not bot_visible,
        },
        "bad_snap": bad_snap,
        "n_occ": int(occ_mask.sum()),
        "n_empty_in_ball": int((~occ_mask).sum()),
    }


def write_lammps_data(path, cluster) -> None:
    """atom_style atomic data file; ids 1..N in cluster order (real first, pads after)."""
    P = cluster["init"]
    types = cluster["types"]
    cell = C.CELL
    lines = [
        "padded cluster (re-search campaign)",
        "",
        f"{len(P)} atoms",
        "2 atom types",
        "",
        f"0.0 {cell[0, 0]:.10f} xlo xhi",
        f"0.0 {cell[1, 1]:.10f} ylo yhi",
        f"0.0 {cell[2, 2]:.10f} zlo zhi",
        "",
        "Masses",
        "",
        *[f"{tid} {C.MASSES[el]}" for el, tid in sorted(C.TYPE_ID.items(), key=lambda kv: kv[1])],
        "",
        "Atoms # atomic",
        "",
    ]
    for i, (t, p) in enumerate(zip(types, P), start=1):
        lines.append(f"{i} {C.TYPE_ID[t]} {p[0]:.10f} {p[1]:.10f} {p[2]:.10f}")
    path.write_text("\n".join(lines) + "\n")
