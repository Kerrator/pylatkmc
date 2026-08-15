#!/usr/bin/env python3
"""Symmetric mover-keyed G3: measure res(P0) AND res(P2) for every harvested event.

Measurement method for canon decision **D6** -- the symmetric projection gate

    G3_sym FAIL  iff  frame_unfit  OR  max(res_P0, res_P2) >= mover_snap_tol (0.5 A)

where ``res_Px`` is the *mover-keyed* snap residual of snapshot ``x``. The build
pipeline today gates on ``res_P0`` alone: ``project_event`` builds ``residuals``
from the INITIAL snapshot only (``event_projection.py`` step 3, the
``[norm(P0[p] - site_cart(s0[p]))]`` comprehension), and both the G3
``MOVER_OFFLATTICE`` drop and the §6 ``WILDCARD`` bystander mask key off it -- so a
final configuration that never reached a lattice site is invisible to every
build-time gate (TOKEN_MISMATCH_VERDICT_2026-08-15.md §5, §10.3.1). This script
measures the missing half.

What it computes, per reference-table row
-----------------------------------------
The **same pinned-h frame-fit machinery the build uses**, imported from
``pylatkmc.ingest.event_projection`` -- nothing is re-implemented here:

1. ``min_image_unwrap`` both snapshots about ``move_atom_idx`` in the event's own
   cell (these reference tables carry no ``cell`` column, so this is a no-op --
   exactly as in the production build, which reads the same absent field).
2. ``fit_local_fcc(P0, move_atom_idx, nominal_a)`` -- the robust all-bond
   global-orientation fit with ``h`` pinned to ``nominal_a / 2``. The frame is
   fitted on **P0 only**, and P2 is measured *in that frame*: ``delta``,
   ``context`` and ``arrows`` are all expressed in the P0 frame, so "did the final
   state reach a lattice site" is only meaningful with respect to **that** lattice.
   (Re-fitting on P2 is structurally useless as a check: ``fit_local_fcc`` pins the
   origin to the seed atom, so the seed's residual would be 0 by construction in a
   P2-anchored frame -- see ``drift_P2_A`` below for the drift diagnostic that
   replaces it.)
3. ``_snap`` / ``_site_cart`` per atom for both snapshots, then
   ``mover_pairs`` for the mover set.

``mover_max_residual_P0`` is computed with **exactly** ``_build_report``'s
definition -- max over the atoms whose snapped site changed (``s0[p] != s2[p]``),
*not* the de-duplicated ``mover_pairs`` starts -- so it reproduces the catalogue's
per-member ``mover_max_residual`` bit-for-bit (validated: 0.0 deviation).
``mover_max_residual_P2`` is the same reduction over the same atom set, against the
P2 snapshot's own snapped sites. That symmetry is the whole point of D6.

Structural note that motivates D6
---------------------------------
For a **single-mover event whose mover is the seed**, ``res_P0`` is *identically
0.0*: ``fit_local_fcc`` sets ``origin = P0[move_atom_idx]``, so the seed snaps to
``(0,0,0)`` with zero residual by construction. The P0-only gate is therefore
near-vacuous on the single-hop majority of the corpus; it can only fire on
multi-mover events (non-seed movers carry real residuals) or when the seed is not a
mover. ``res_P2`` has no such degeneracy -- in P2 the seed has left the origin.

Outputs
-------
One parquet per run under ``<outdir>/<ALLOY>/<run_tag>.parquet`` (ALLOY = the run
tag's first ``_``-field, e.g. ``NiCr``), one row per reference-table row, plus a
per-alloy ``_summary.csv`` covering **the runs of this invocation only** -- a later
single-run call rewrites it, so re-run with ``--alloy X --skip-existing`` (seconds,
it re-reads the parquets) to restore the whole-alloy summary. Every row of
the reference table is emitted -- including rows the build discarded and rows that
raise -- so ``len(parquet) == len(reference_table)`` is an exact conservation
check.

Usage
-----
    cd /home/kerr/pykmc/pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15
    source /home/kerr/pykmc/pykmc_env/bin/activate
    python measure_p2.py --alloy NiCr --workers 4

    # or an explicit list of run dirs / run tags
    python measure_p2.py NiCr_Ni95_Cr05_T300_1vac /home/kerr/pykmc/production_NiCrFe/runs/NiFe_Ni95_Fe05_T800_10vac

Read-only w.r.t. ``production_NiCrFe/runs/`` and the ``/data`` sweep catalogue.
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pylatkmc.ingest.event_projection import (  # the build's own machinery
    FrameUnfitError,
    _get,
    _resolve_nu0_hz,
    _site_cart,
    _snap,
    fit_local_fcc,
    min_image_unwrap,
    mover_pairs,
)
from pylatkmc.ingest.reftable import read_reference_table

RUNS_ROOT = Path("/home/kerr/pykmc/production_NiCrFe/runs")
OUT_ROOT = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/symmetric_gate_2026-08-15/p2_measure")

#: Production build parameters (per-run build log conditions stamp of
#: /data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full: ``nominal_a=3.52
#: mover_snap_tol=0.5``). Only ``nominal_a`` enters the residual; rcut / d_max /
#: r_ctx_min / coloring / bystander_mask_tol affect the context, never the frame
#: fit or the snap residual, so they are deliberately not parameters here.
NOMINAL_A = 3.52
MOVER_SNAP_TOL = 0.5

#: Half-shift criterion of TOKEN_MISMATCH_VERDICT_2026-08-15.md §2e: an event whose
#: SHORTEST mover hop is below this fraction of the 1NN spacing did not complete a
#: hop -- the snapper promoted a collective part-way shift into a lattice event.
HALF_SHIFT_FRAC = 0.7

#: Shared-box core budget (memory: linux-box-core-budget) -- never saturate 24 cores.
DEFAULT_WORKERS = 4

_FLOAT_COLS = (
    "mover_max_residual_P0",
    "mover_max_residual_P2",
    "mover_max_residual_sym",
    "max_residual_P0",
    "max_residual_P2",
    "hop_min_A",
    "hop_max_A",
    "hop_median_A",
    "hop_min_over_1nn",
    "d_1nn_A",
    "static_max_residual_P0",
    "static_max_residual_P2",
    "drift_P0_A",
    "drift_P2_A",
    "Ea_fwd_eV",
    "k_row",
    "nu0_hz",
)


def _f(x: Any, default: float = float("nan")) -> float:
    """``float(x)`` tolerating the reference table's nullable numeric columns."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v


def _i(x: Any, default: int = -1) -> int:
    """``int(x)`` tolerating nulls (``nu0`` / ``idx_backward`` are nullable)."""
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def measure_event(row: Any, *, nominal_a: float = NOMINAL_A) -> dict[str, Any]:
    """Mover-keyed P0 and P2 snap residuals for one reference-table row.

    Returns a flat dict (one output row). Never raises: a frame-unfit or malformed
    row comes back with ``frame_unfit`` / ``error`` set and NaN residuals, gated
    FAIL -- the ledger convention of memo 2026-07-29 §5, which treats FRAME_UNFIT
    as a G3 failure before any residual is evaluated.
    """
    idx_ref = _i(_get(row, "idx_ref", -1))
    out: dict[str, Any] = {
        "idx_ref": idx_ref,
        "event_id": str(_get(row, "event_id", "")),
        "idx_backward": _i(_get(row, "idx_backward", -1)),
        "move_atom_idx": _i(_get(row, "move_atom_idx", -1)),
        "Ea_fwd_eV": _f(_get(row, "energy_barrier")),
        "k_row": _f(_get(row, "k")),
        # the build's own resolver (HTST nu0 in Hz, else k_prefactor x 1e12) -- both
        # columns are nullable in the production reference tables.
        "nu0_hz": _resolve_nu0_hz(row),
        "n_atoms": 0,
        "n_movers": 0,
        "n_mover_atoms": 0,
        "seed_is_mover": False,
        "mover_agreement": False,
        "frame_unfit": False,
        "error": "",
        "d_1nn_A": float(nominal_a) / math.sqrt(2.0),
        # every exit path overrides these; declaring them here means no path can omit
        # a column and give the parquet a ragged schema
        "gate_P0_fail": False,
        "gate_P2_fail": False,
        "gate_sym_fail": False,
        "half_shift": False,
        "fail_reason": "",
        "mover_offlattice_P2_attributable": False,
    }
    for c in _FLOAT_COLS:
        out.setdefault(c, float("nan"))
    out["mover_atom_idx_list"] = []
    out["mover_res_P0_list"] = []
    out["mover_res_P2_list"] = []
    out["hop_A_list"] = []

    try:
        P0_raw = np.asarray(_get(row, "initial_positions"), dtype=float)
        P2_raw = np.asarray(_get(row, "final_positions"), dtype=float)
        move_atom_idx = _i(_get(row, "move_atom_idx", 0), 0)
        cell = _get(row, "cell")
        n = P0_raw.shape[0]
        out["n_atoms"] = int(n)
        if P2_raw.shape != P0_raw.shape:
            raise ValueError(f"final_positions {P2_raw.shape} != initial {P0_raw.shape}")

        # 1. unwrap first (Geom-1) -- identical call to project_event's
        P0 = min_image_unwrap(P0_raw, move_atom_idx, cell)
        P2 = min_image_unwrap(P2_raw, move_atom_idx, cell)

        # 2. the build's own pinned-h frame, fitted on P0
        try:
            frame = fit_local_fcc(P0, move_atom_idx, nominal_a=nominal_a)
        except FrameUnfitError as exc:
            out["frame_unfit"] = True
            out["error"] = f"FRAME_UNFIT: {exc}"
            out["gate_P0_fail"] = True
            out["gate_P2_fail"] = True
            out["gate_sym_fail"] = True
            out["fail_reason"] = "FRAME_UNFIT"
            out["half_shift"] = False
            return out

        out["d_1nn_A"] = float(frame.h) * math.sqrt(2.0)

        # 3. snap both snapshots in that ONE frame; residual = |x - site_cart(snap(x))|
        s0 = [_snap(frame, P0[p]) for p in range(n)]
        s2 = [_snap(frame, P2[p]) for p in range(n)]
        c0 = np.asarray([_site_cart(frame, s0[p]) for p in range(n)], dtype=float)
        c2 = np.asarray([_site_cart(frame, s2[p]) for p in range(n)], dtype=float)
        r0 = np.linalg.norm(P0 - c0, axis=1)
        r2 = np.linalg.norm(P2 - c2, axis=1)

        # mover ATOMS -- _build_report's definition, not the de-duplicated
        # mover_pairs starts, so mover_max_residual_P0 reproduces the catalogue.
        mover_atoms = [p for p in range(n) if s0[p] != s2[p]]
        pairs = mover_pairs(s0, s2)

        out["n_movers"] = len(pairs)  # == len(ProjectedEvent.movers) / len(arrows)
        out["n_mover_atoms"] = len(mover_atoms)
        out["seed_is_mover"] = bool(move_atom_idx < n and s0[move_atom_idx] != s2[move_atom_idx])
        out["mover_agreement"] = bool(
            move_atom_idx < n and s0[move_atom_idx] in {st for st, _e, _p in pairs}
        )

        res0 = float(np.max(r0[mover_atoms])) if mover_atoms else 0.0
        res2 = float(np.max(r2[mover_atoms])) if mover_atoms else 0.0
        out["mover_max_residual_P0"] = res0
        out["mover_max_residual_P2"] = res2
        out["mover_max_residual_sym"] = max(res0, res2)
        out["max_residual_P0"] = float(np.max(r0)) if n else 0.0
        out["max_residual_P2"] = float(np.max(r2)) if n else 0.0

        # hops (the half-shift criterion keys on the SHORTEST mover hop, §2e)
        hops = np.linalg.norm(P2[mover_atoms] - P0[mover_atoms], axis=1) if mover_atoms else None
        d1nn = out["d_1nn_A"]
        if hops is not None and hops.size:
            out["hop_min_A"] = float(np.min(hops))
            out["hop_max_A"] = float(np.max(hops))
            out["hop_median_A"] = float(np.median(hops))
            out["hop_min_over_1nn"] = float(np.min(hops) / d1nn)
            out["half_shift"] = bool(np.min(hops) < HALF_SHIFT_FRAC * d1nn)
            out["hop_A_list"] = [float(x) for x in hops]
        else:
            out["half_shift"] = False

        # Substrate (static-bystander) reference -- the discriminator that makes a
        # res_P2 failure attributable. `fit_local_fcc` pins the frame origin to the
        # SEED's initial position, so a seed that is itself off-lattice in P0 displaces
        # the whole registry: every atom then reads a large residual in BOTH snapshots
        # and the mover's res_P2 is anchor error, not a bad final state. Comparing the
        # mover against the static substrate separates the two:
        #   res_P2 >= tol AND static_max_residual_P2 < tol -> mover-specific: the final
        #       position genuinely never reached a lattice site (the D6 target).
        #   res_P2 >= tol AND static_max_residual_P2 >= tol -> registry/anchor problem,
        #       already visible in max_residual_P0 -- a different defect.
        # drift_* is the COHERENT part (norm of the median residual vector): a rigid
        # offset of the whole cluster, as opposed to scattered thermal noise.
        static = [p for p in range(n) if s0[p] == s2[p]]
        if static:
            out["static_max_residual_P0"] = float(np.max(r0[static]))
            out["static_max_residual_P2"] = float(np.max(r2[static]))
            out["drift_P0_A"] = float(np.linalg.norm(np.median(P0[static] - c0[static], axis=0)))
            out["drift_P2_A"] = float(np.linalg.norm(np.median(P2[static] - c2[static], axis=0)))
        else:
            out["static_max_residual_P0"] = 0.0
            out["static_max_residual_P2"] = 0.0
            out["drift_P0_A"] = 0.0
            out["drift_P2_A"] = 0.0
        out["mover_offlattice_P2_attributable"] = bool(
            res2 >= MOVER_SNAP_TOL and out["static_max_residual_P2"] < MOVER_SNAP_TOL
        )

        out["mover_atom_idx_list"] = [int(p) for p in mover_atoms]
        out["mover_res_P0_list"] = [float(x) for x in r0[mover_atoms]] if mover_atoms else []
        out["mover_res_P2_list"] = [float(x) for x in r2[mover_atoms]] if mover_atoms else []

        out["gate_P0_fail"] = bool(res0 >= MOVER_SNAP_TOL)
        out["gate_P2_fail"] = bool(res2 >= MOVER_SNAP_TOL)
        out["gate_sym_fail"] = bool(out["gate_P0_fail"] or out["gate_P2_fail"])
        out["fail_reason"] = (
            "MOVER_OFFLATTICE_P0P2"
            if out["gate_P0_fail"] and out["gate_P2_fail"]
            else "MOVER_OFFLATTICE_P0"
            if out["gate_P0_fail"]
            else "MOVER_OFFLATTICE_P2"
            if out["gate_P2_fail"]
            else ""
        )
        return out
    except Exception as exc:  # noqa: BLE001 -- recorded per row, never silent
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["gate_P0_fail"] = True
        out["gate_P2_fail"] = True
        out["gate_sym_fail"] = True
        out["fail_reason"] = "ERROR"
        out["half_shift"] = False
        return out


def measure_run(
    run_tag: str,
    *,
    runs_root: Path = RUNS_ROOT,
    nominal_a: float = NOMINAL_A,
) -> pd.DataFrame:
    """Measure every event of one run; one output row per reference-table row."""
    df = read_reference_table(runs_root / run_tag / "reference_table.pickle")
    alloy = run_tag.split("_", 1)[0]
    rows = []
    for i in range(len(df)):
        rec = measure_event(df.iloc[i], nominal_a=nominal_a)
        rec["run_tag"] = run_tag
        rec["alloy"] = alloy
        rec["source_row"] = i  # positional index, the ledger's `row` convention
        rows.append(rec)
    out = pd.DataFrame(rows)
    lead = ["run_tag", "alloy", "idx_ref", "source_row"]
    return out[lead + [c for c in out.columns if c not in lead]]


def _worker(args: tuple[str, str, float, str, bool]) -> dict[str, Any]:
    run_tag, runs_root, nominal_a, outdir, skip_existing = args
    t0 = time.time()
    out_path = Path(outdir) / run_tag.split("_", 1)[0] / f"{run_tag}.parquet"
    if skip_existing and out_path.exists():
        d = pd.read_parquet(out_path)
        return _summary(run_tag, d, out_path, 0.0, skipped=True)
    try:
        d = measure_run(run_tag, runs_root=Path(runs_root), nominal_a=nominal_a)
    except Exception as exc:  # noqa: BLE001
        return _fail_summary(run_tag, f"FAIL {type(exc).__name__}: {exc}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(d, out_path, run_tag=run_tag, runs_root=runs_root, nominal_a=nominal_a)
    return _summary(run_tag, d, out_path, time.time() - t0)


def _write_parquet(d: pd.DataFrame, path: Path, *, run_tag: str, runs_root: str, nominal_a: float) -> None:
    """Write with a build-style conditions stamp, so the file self-describes."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    cond = (
        f"symmetric mover-keyed G3 (canon D6) | run={run_tag} | "
        f"reftable={runs_root}/{run_tag}/reference_table.pickle | "
        f"nominal_a={nominal_a} h={nominal_a / 2.0} mover_snap_tol={MOVER_SNAP_TOL} "
        f"half_shift_frac={HALF_SHIFT_FRAC} | frame=fit_local_fcc(P0, move_atom_idx) pinned-h; "
        f"P2 measured IN THE P0 FRAME | rows={len(d)} | script={Path(__file__).name}"
    )
    table = pa.Table.from_pandas(d, preserve_index=False)
    table = table.replace_schema_metadata(
        {**(table.schema.metadata or {}), b"pylatkmc.p2measure.conditions": cond.encode()}
    )
    pq.write_table(table, path)


#: Every integer column the per-alloy aggregate sums; a FAILed run contributes 0s
#: rather than a short dict (a missing key used to KeyError the whole summary).
_COUNT_COLS = (
    "n_rows",
    "n_frame_unfit",
    "n_error",
    "n_P0_fail",
    "n_P2_fail",
    "n_P2_only_fail",
    "n_sym_fail",
    "n_half_shift",
    "n_multi_mover",
)


def _fail_summary(run_tag: str, status: str) -> dict[str, Any]:
    d: dict[str, Any] = {"run_tag": run_tag, "status": status, "parquet": ""}
    d.update(dict.fromkeys(_COUNT_COLS, 0))
    d["median_res_P2"] = float("nan")
    d["secs"] = 0.0
    return d


def _summary(
    run_tag: str, d: pd.DataFrame, path: Path, secs: float, skipped: bool = False
) -> dict[str, Any]:
    ok = ~d["frame_unfit"] & (d["error"] == "")
    return {
        "run_tag": run_tag,
        "status": "SKIP(existing)" if skipped else "OK",
        "parquet": str(path),
        "n_rows": int(len(d)),
        "n_frame_unfit": int(d["frame_unfit"].sum()),
        "n_error": int((d["error"] != "").sum() - d["frame_unfit"].sum()),
        "n_P0_fail": int(d["gate_P0_fail"].sum()),
        "n_P2_fail": int(d["gate_P2_fail"].sum()),
        "n_P2_only_fail": int((d["gate_P2_fail"] & ~d["gate_P0_fail"]).sum()),
        "n_sym_fail": int(d["gate_sym_fail"].sum()),
        "n_half_shift": int(d["half_shift"].sum()),
        "n_multi_mover": int((d["n_movers"] > 1).sum()),
        "median_res_P2": float(d.loc[ok, "mover_max_residual_P2"].median()),
        "secs": round(secs, 1),
    }


def resolve_runs(items: list[str], alloy: str | None, runs_root: Path) -> list[str]:
    """Run tags from explicit args (tag or dir path) and/or an ``--alloy`` prefix."""
    tags: list[str] = [Path(x.rstrip("/")).name for x in items]
    if alloy:
        tags += sorted(p.name for p in runs_root.iterdir() if p.name.startswith(alloy + "_"))
    seen: set[str] = set()
    uniq = [t for t in tags if not (t in seen or seen.add(t))]
    missing = [t for t in uniq if not (runs_root / t / "reference_table.pickle").is_file()]
    if missing:
        raise SystemExit(f"no reference_table.pickle for: {missing}")
    return uniq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*", help="run tags or run dirs under --runs-root")
    ap.add_argument("--alloy", default=None, help="also take every run whose tag starts <alloy>_ (NiCr / NiFe)")
    ap.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    ap.add_argument("--outdir", type=Path, default=OUT_ROOT)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="processes (shared box: keep <= 4)")
    ap.add_argument("--nominal-a", type=float, default=NOMINAL_A)
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args(argv)

    if a.workers > DEFAULT_WORKERS:
        print(f"WARNING: {a.workers} workers exceeds the shared-box budget of {DEFAULT_WORKERS}", file=sys.stderr)
    tags = resolve_runs(a.runs, a.alloy, a.runs_root)
    if not tags:
        raise SystemExit("no runs selected (give run tags or --alloy)")
    a.outdir.mkdir(parents=True, exist_ok=True)
    print(f"measuring {len(tags)} run(s) -> {a.outdir}  (workers={a.workers}, nominal_a={a.nominal_a})")

    # BLAS threads off: the work is many tiny 3x3 ops; oversubscription only hurts.
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(v, "1")

    payload = [(t, str(a.runs_root), a.nominal_a, str(a.outdir), a.skip_existing) for t in tags]
    t0 = time.time()
    if a.workers > 1 and len(tags) > 1:
        with mp.get_context("fork").Pool(a.workers) as pool:
            results = []
            for r in pool.imap_unordered(_worker, payload):
                results.append(r)
                print(f"  [{len(results)}/{len(tags)}] {r['run_tag']}: {r['status']} "
                      f"rows={r['n_rows']} P0fail={r.get('n_P0_fail')} P2fail={r.get('n_P2_fail')} "
                      f"P2only={r.get('n_P2_only_fail')} halfshift={r.get('n_half_shift')}", flush=True)
    else:
        results = [_worker(p) for p in payload]
        for r in results:
            print(f"  {r['run_tag']}: {r['status']} rows={r['n_rows']}", flush=True)

    summ = pd.DataFrame(results).sort_values("run_tag")
    for alloy, grp in summ.groupby(summ["run_tag"].str.split("_").str[0]):
        path = a.outdir / str(alloy) / "_summary.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        grp.to_csv(path, index=False)
        print(f"\n{alloy}: {len(grp)} runs, {int(grp['n_rows'].sum())} events -> {path}")
        tot = grp[list(_COUNT_COLS)].sum()
        print("  " + "  ".join(f"{k}={int(v)}" for k, v in tot.items()))
    bad = [r for r in results if not str(r["status"]).startswith(("OK", "SKIP"))]
    if bad:
        print(f"\n{len(bad)} run(s) FAILED: {[r['run_tag'] for r in bad]}", file=sys.stderr)
    print(f"\nelapsed {time.time() - t0:.1f}s")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
