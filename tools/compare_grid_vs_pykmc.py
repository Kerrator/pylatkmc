"""Phase 1 aggregator: build the long-form CSV + full-time D-ratio heatmap.

Walks the paired (T, nvac) cells produced by ``sim_discovery_dual``,
loads each engine's summary, normalises units, and emits one CSV +
one PNG.

Reconciliation rules:
  * pyKMC's ``msd_final`` is a per-vacancy list of length ``n_vacancies``
    from a single trajectory. We report ``mean_msd = mean(msd_final)``
    and ``msd_sem = std(msd_final) / sqrt(n_vac)`` (within-trajectory
    scatter across vacancies).
  * pylatkmc's ``mean_msd_A2_mean`` is the cross-vacancy mean already
    averaged across replicas. Error bar: ``mean_msd_A2_std / sqrt(n_replicas)``
    (across-replica scatter).
  * The two error bars have different physical meaning — we tag each row
    with ``error_kind`` so the writeup can be honest about it.

Usage:
    python tools/compare_grid_vs_pykmc.py \\
        --out-csv tools/comparison_output/comparison_grid.csv \\
        --out-plot tools/comparison_output/plots/D_ratio_full_time.png

Run from the pylatkmc repo root with the pykmc env active.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

# Allow ``python tools/compare_grid_vs_pykmc.py`` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_discovery_dual import (  # noqa: E402
    DualCell,
    coverage_report,
    find_dual_cells,
    load_pykmc_summary,
    load_pylat_summary,
)

# Long-form CSV column order (kept in sync with `Row` below).
CSV_COLUMNS = (
    "T_K",
    "n_vacancies",
    "engine",
    "view",
    "MSD_A2",
    "MSD_sem",
    "t_end_s",
    "D_A2_per_s",
    "n_replicas",
    "error_kind",
    "slab_id",
    "n_steps_or_frames",
    "source_path",
    "notes",
)


@dataclass(frozen=True)
class Row:
    T_K: float
    n_vacancies: int
    engine: str  # "pyKMC" | "pylatkmc"
    view: str  # "full_time" | "time_aligned" | "longtime_supplement"
    MSD_A2: float
    MSD_sem: float
    t_end_s: float
    D_A2_per_s: float  # MSD / (6t); NaN if t == 0
    n_replicas: int
    error_kind: str  # "within_traj_per_vac" | "across_replica"
    slab_id: str  # "100Ni_grid" for the main grid
    n_steps_or_frames: int
    source_path: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Loaders + normalisers
# ---------------------------------------------------------------------------


def compute_D(msd_A2: float, t_s: float) -> float:
    """3D diffusion coefficient ``D = MSD / (6t)`` in Å²/s.

    Returns NaN for ``t == 0`` (the T=300/1vac case where pyKMC fires
    zero events and ``msd_final = [0.0]``).
    """
    if t_s <= 0:
        return float("nan")
    return msd_A2 / (6.0 * t_s)


def pykmc_row(cell: DualCell, view: str = "full_time") -> Row | None:
    """Convert a pyKMC summary into a Row.

    Returns None if the summary has no MSD list at all (genuinely missing
    field). If the MSD list is present but all-zero, the row is still
    returned with a `notes` flag explaining whether it's:
      * "trajectory truncated (n_frames=1)" — the trajkmc.xyz was clipped
        (typically at 512 KB) so only the initial frame was kept;
        analysis returns msd=0 by construction. Affects the 5 1-vac cells
        T = {300, 400, 800, 900, 1200}.
      * "vacancy returned to start" — n_frames > 1 but actual zero net
        displacement (rare but physically possible at low T with few
        events).
    """
    s = load_pykmc_summary(cell)
    msd_list = s.get("msd_final") or []
    n_vac_actual = len(msd_list)
    if n_vac_actual == 0:
        return None
    arr = np.asarray(msd_list, dtype=float)
    msd_mean = float(arr.mean())
    msd_sem = (
        float(arr.std(ddof=1) / math.sqrt(n_vac_actual)) if n_vac_actual > 1 else 0.0
    )
    t_end = float(s["total_sim_time"])
    n_frames = int(s.get("n_frames") or 0)
    n_events = int(s.get("n_events") or 0)
    notes = ""
    if msd_mean == 0.0:
        if n_frames <= 1:
            notes = (
                f"trajectory under-sampled (n_frames={n_frames}); pyKMC fired "
                f"{n_events} events but trajkmc.xyz was clipped — MSD measurement undefined"
            )
        else:
            notes = f"net zero displacement after {n_events} events"
    return Row(
        T_K=cell.temperature_K,
        n_vacancies=cell.n_vacancies,
        engine="pyKMC",
        view=view,
        MSD_A2=msd_mean,
        MSD_sem=msd_sem,
        t_end_s=t_end,
        D_A2_per_s=compute_D(msd_mean, t_end),
        n_replicas=1,
        error_kind="within_traj_per_vac",
        slab_id="100Ni_grid",
        n_steps_or_frames=n_frames,
        source_path=str(cell.pykmc_summary_path),
        notes=notes,
    )


def pylat_row(cell: DualCell, view: str = "full_time") -> Row | None:
    """Convert a pylatkmc aggregate_summary into a Row."""
    s = load_pylat_summary(cell)
    msd_mean = float(s.get("mean_msd_A2_mean", 0.0))
    msd_std = float(s.get("mean_msd_A2_std", 0.0))
    n_replicas = int(s.get("n_replicas", 1))
    msd_sem = msd_std / math.sqrt(n_replicas) if n_replicas > 0 else msd_std
    t_end = float(s.get("total_time_s_mean", 0.0))
    n_steps = int(s.get("n_steps_mean") or 0)
    return Row(
        T_K=cell.temperature_K,
        n_vacancies=cell.n_vacancies,
        engine="pylatkmc",
        view=view,
        MSD_A2=msd_mean,
        MSD_sem=msd_sem,
        t_end_s=t_end,
        D_A2_per_s=compute_D(msd_mean, t_end),
        n_replicas=n_replicas,
        error_kind="across_replica",
        slab_id="100Ni_grid",
        n_steps_or_frames=n_steps,
        source_path=str(cell.pylat_summary_path),
        notes="",
    )


def build_long_form(cells: list[DualCell]) -> list[Row]:
    """One Row per (cell, engine). Skips cells with no MSD on the pyKMC
    side (they show up in the report's coverage stats instead)."""
    rows: list[Row] = []
    for c in cells:
        if not c.is_complete:
            continue
        try:
            pk = pykmc_row(c)
        except FileNotFoundError:
            pk = None
        try:
            pl = pylat_row(c)
        except FileNotFoundError:
            pl = None
        if pk is not None:
            rows.append(pk)
        if pl is not None:
            rows.append(pl)
    return rows


def time_aligned_rows(
    timealigned_root: Path = (
        Path(__file__).resolve().parent / "comparison_output" / "timealigned"
    ),
) -> list[Row]:
    """Load Phase 2 outputs (one ``output/aggregate_summary.json`` per
    re-run cell) and emit ``view='time_aligned'`` rows.

    Each Phase 2 cell already has ``max_time_s = pyKMC.t_end * 1.05``,
    so the engine's actual stopping time should be very close to
    pyKMC's. We compare MSD at the engine's actual t.
    """
    rows: list[Row] = []
    if not timealigned_root.is_dir():
        return rows
    for cell_dir in sorted(timealigned_root.glob("T*_*vac")):
        agg = cell_dir / "output" / "aggregate_summary.json"
        if not agg.is_file():
            continue
        try:
            T_str, nvac_str = cell_dir.name.split("_")
            T = float(T_str.lstrip("T"))
            nvac = int(nvac_str.rstrip("vac"))
        except ValueError:
            continue
        s = json.loads(agg.read_text())
        msd_mean = float(s.get("mean_msd_A2_mean", 0.0))
        msd_std = float(s.get("mean_msd_A2_std", 0.0))
        n_replicas = int(s.get("n_replicas", 1))
        msd_sem = msd_std / math.sqrt(n_replicas) if n_replicas > 0 else msd_std
        t_end = float(s.get("total_time_s_mean", 0.0))
        n_steps = int(s.get("n_steps_mean") or 0)
        rows.append(
            Row(
                T_K=T,
                n_vacancies=nvac,
                engine="pylatkmc",
                view="time_aligned",
                MSD_A2=msd_mean,
                MSD_sem=msd_sem,
                t_end_s=t_end,
                D_A2_per_s=compute_D(msd_mean, t_end),
                n_replicas=n_replicas,
                error_kind="across_replica",
                slab_id="100Ni_grid",
                n_steps_or_frames=n_steps,
                source_path=str(agg),
                notes=f"Phase 2 re-run with max_time_s set to pyKMC.t_end*1.05",
            )
        )
    return rows


# ---------------------------------------------------------------------------
# CSV + plot
# ---------------------------------------------------------------------------


def write_csv(rows: list[Row], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def _heatmap(
    M_disp: np.ndarray,
    Ts_disp: list[float],
    nvacs: list[int],
    title: str,
    cbar_label: str,
    out_path: Path,
) -> None:
    """Shared heatmap renderer."""
    import matplotlib.pyplot as plt

    vmax = float(np.nanmax(np.abs(M_disp))) if np.any(~np.isnan(M_disp)) else 1.0
    if not math.isfinite(vmax) or vmax == 0:
        vmax = 1.0
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(
        M_disp,
        cmap="RdBu_r",
        vmin=-vmax,
        vmax=vmax,
        aspect="auto",
        interpolation="nearest",
    )
    ax.set_xticks(range(len(nvacs)))
    ax.set_xticklabels([str(n) for n in nvacs])
    ax.set_yticks(range(len(Ts_disp)))
    ax.set_yticklabels([f"{int(t)} K" for t in Ts_disp])
    ax.set_xlabel("n_vacancies")
    ax.set_ylabel("Temperature")
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    for i, _ in enumerate(Ts_disp):
        for j, _ in enumerate(nvacs):
            v = M_disp[i, j]
            if math.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", color="grey", fontsize=9)
            else:
                ax.text(
                    j,
                    i,
                    f"{v:+.2f}",
                    ha="center",
                    va="center",
                    color="black" if abs(v) < vmax * 0.6 else "white",
                    fontsize=8,
                )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_D_ratio_heatmap(rows: list[Row], out_path: Path) -> None:
    """log10(D_pylat / D_pyKMC) on the full-time view (each engine
    reports MSD at its own end time)."""
    by_cell: dict[tuple[float, int], dict[str, float]] = {}
    for r in rows:
        if r.view != "full_time":
            continue
        by_cell.setdefault((r.T_K, r.n_vacancies), {})[r.engine] = r.D_A2_per_s

    Ts = sorted({k[0] for k in by_cell})
    nvacs = sorted({k[1] for k in by_cell})
    M = np.full((len(Ts), len(nvacs)), np.nan)
    for i, T in enumerate(Ts):
        for j, nv in enumerate(nvacs):
            d = by_cell.get((T, nv), {})
            d_pl = d.get("pylatkmc", float("nan"))
            d_pk = d.get("pyKMC", float("nan"))
            if d_pk > 0 and d_pl > 0 and not math.isnan(d_pk) and not math.isnan(d_pl):
                M[i, j] = math.log10(d_pl / d_pk)
    Ts_disp = list(reversed(Ts))
    _heatmap(
        M[::-1, :],
        Ts_disp,
        nvacs,
        title=(
            "log10(D_pylatkmc / D_pyKMC) — full-time view (each engine at its own t_end)\n"
            "Blue = pylatkmc faster than pyKMC; Red = pyKMC faster; — = pyKMC fired 0 events"
        ),
        cbar_label="log10 ratio",
        out_path=out_path,
    )


def plot_MSD_ratio_timealigned(rows: list[Row], out_path: Path) -> None:
    """log10(MSD_pylat(t*) / MSD_pyKMC(t*)) on the time-aligned view.

    Cells without a Phase 2 re-run (pyKMC ahead in time, or 0-event)
    plot as "—".
    """
    pk_by_cell: dict[tuple[float, int], float] = {}
    for r in rows:
        if r.view == "full_time" and r.engine == "pyKMC":
            pk_by_cell[(r.T_K, r.n_vacancies)] = r.MSD_A2
    pl_aligned: dict[tuple[float, int], float] = {}
    for r in rows:
        if r.view == "time_aligned" and r.engine == "pylatkmc":
            pl_aligned[(r.T_K, r.n_vacancies)] = r.MSD_A2

    keys = sorted(set(pk_by_cell) | set(pl_aligned))
    Ts = sorted({k[0] for k in keys})
    nvacs = sorted({k[1] for k in keys})
    M = np.full((len(Ts), len(nvacs)), np.nan)
    for i, T in enumerate(Ts):
        for j, nv in enumerate(nvacs):
            pk = pk_by_cell.get((T, nv))
            pl = pl_aligned.get((T, nv))
            if pk and pl and pk > 0 and pl > 0:
                M[i, j] = math.log10(pl / pk)
    Ts_disp = list(reversed(Ts))
    _heatmap(
        M[::-1, :],
        Ts_disp,
        nvacs,
        title=(
            "log10(MSD_pylatkmc(t*) / MSD_pyKMC(t*)) — time-aligned at t*=pyKMC.t_end\n"
            "Blue = pylatkmc MSD higher; Red = pyKMC MSD higher; — = no Phase 2 re-run"
        ),
        cbar_label="log10 ratio",
        out_path=out_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument(
        "--out-csv",
        default="tools/comparison_output/comparison_grid.csv",
        help="Long-form CSV path",
    )
    p.add_argument(
        "--out-plot",
        default="tools/comparison_output/plots/D_ratio_full_time.png",
        help="Heatmap PNG path (full-time D ratio)",
    )
    p.add_argument(
        "--out-plot-timealigned",
        default="tools/comparison_output/plots/MSD_ratio_time_aligned.png",
        help="Heatmap PNG path (time-aligned MSD ratio); only emitted if "
        "Phase 2 outputs are present under tools/comparison_output/timealigned/",
    )
    p.add_argument(
        "--include-time-aligned",
        action="store_true",
        default=True,
        help="Append Phase 2 (time_aligned) rows to the CSV and emit the "
        "time-aligned heatmap. On by default.",
    )
    args = p.parse_args(argv)

    cells = find_dual_cells()
    print(coverage_report(cells))
    rows = build_long_form(cells)
    if args.include_time_aligned:
        ta_rows = time_aligned_rows()
        if ta_rows:
            print(f"  + {len(ta_rows)} time_aligned rows from Phase 2")
            rows.extend(ta_rows)
    write_csv(rows, Path(args.out_csv))
    print(f"wrote {len(rows)} rows -> {args.out_csv}")
    plot_D_ratio_heatmap(rows, Path(args.out_plot))
    print(f"wrote heatmap        -> {args.out_plot}")
    if args.include_time_aligned and any(r.view == "time_aligned" for r in rows):
        plot_MSD_ratio_timealigned(rows, Path(args.out_plot_timealigned))
        print(f"wrote time-aligned   -> {args.out_plot_timealigned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
