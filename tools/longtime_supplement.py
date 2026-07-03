"""Phase 3: 1M-step archive cells alongside the matching production cell.

Tests the user's hypothesis that "at least for 1 vacancy [pyKMC and
pylatkmc] might line up" by extending pylatkmc to longer simulated time
on a 1-vacancy system. Important caveat: the archive runs are on
**different slab geometries** from the 100Ni production grid, so direct
D-comparison only makes sense WITHIN the same slab.

Cells included:

| Slab | Engine | Steps | T (K) | nvac |
|---|---|---|---|---|
| 22×22×20 100Ni grid (production) | pyKMC | n/a (event-budget) | 500 | 1 |
| 22×22×20 100Ni grid (production) | pylatkmc | 500k | 500 | 1 |
| 10×10×6 surfvac (archive) | pylatkmc | 1M | 500 | 1 |
| 22×22×20 bulkvac (archive) | pylatkmc | 1M | 500 | 1 (bulk) |
| 8×8×3 surfvac (archive) | pylatkmc | 100k | 500 | 1 |

(``Ni_6x6x5_multivac`` is excluded — its aggregate JSON is empty.)

Output: a grouped bar plot of D = MSD / (6t) per (slab, engine), so
the eye can compare same-slab pairs and within-engine slab variation.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_discovery_dual import load_pykmc_summary  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]  # kmc/
ARCHIVE_DIR = REPO_ROOT / "_archive" / "latkmc" / "examples"
PYLAT_GRID = (
    REPO_ROOT
    / "pylatkmc"
    / "models"
    / "ni_fe_cr_v1"
    / "examples"
    / "full_100Ni"
    / "output_T500_1vac"
)
PYKMC_GRID_PARENT = REPO_ROOT / "Data" / "Research" / "100Ni" / "1vac" / "T500"
OUT_PLOT = (
    REPO_ROOT
    / "pylatkmc"
    / "tools"
    / "comparison_output"
    / "plots"
    / "D_vs_engine_T500_1vac.png"
)
OUT_CSV = (
    REPO_ROOT
    / "pylatkmc"
    / "tools"
    / "comparison_output"
    / "longtime_supplement.csv"
)


@dataclass(frozen=True)
class Bar:
    slab_id: str
    engine: str
    n_steps_or_frames: int
    t_end_s: float
    msd_A2: float
    msd_sem: float
    D_A2_per_s: float
    notes: str


def _load_pylat_aggregate(path: Path, slab_id: str, notes: str) -> Bar | None:
    if not path.is_file():
        return None
    try:
        s = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    msd = float(s.get("mean_msd_A2_mean") or 0.0)
    msd_std = float(s.get("mean_msd_A2_std") or 0.0)
    n_rep = int(s.get("n_replicas") or 1)
    msd_sem = msd_std / (n_rep**0.5) if n_rep > 0 else msd_std
    t = float(s.get("total_time_s_mean") or 0.0)
    n_steps = int(s.get("n_steps_mean") or 0)
    D = msd / (6.0 * t) if t > 0 else float("nan")
    return Bar(
        slab_id=slab_id,
        engine="pylatkmc",
        n_steps_or_frames=n_steps,
        t_end_s=t,
        msd_A2=msd,
        msd_sem=msd_sem,
        D_A2_per_s=D,
        notes=notes,
    )


def _load_pykmc_grid_cell() -> Bar | None:
    # The coloring subdir name varies (NiAlH, NiAlH_full, full); pick the
    # first child dir whose analysis/summary.json is readable.
    if not PYKMC_GRID_PARENT.is_dir():
        return None
    summary: Path | None = None
    for child in sorted(PYKMC_GRID_PARENT.iterdir()):
        candidate = child / "analysis" / "summary.json"
        if candidate.is_file():
            summary = candidate
            break
    if summary is None:
        return None
    s = json.loads(summary.read_text())
    msd_list = s.get("msd_final") or []
    if not msd_list:
        return None
    import statistics

    msd_mean = statistics.mean(msd_list)
    msd_sem = (
        statistics.stdev(msd_list) / (len(msd_list) ** 0.5) if len(msd_list) > 1 else 0.0
    )
    t = float(s["total_sim_time"])
    D = msd_mean / (6.0 * t) if t > 0 else float("nan")
    return Bar(
        slab_id="22x22x20 100Ni grid (surface)",
        engine="pyKMC",
        n_steps_or_frames=int(s.get("n_frames") or 0),
        t_end_s=t,
        msd_A2=msd_mean,
        msd_sem=msd_sem,
        D_A2_per_s=D,
        notes=f"n_events={s.get('n_events')}; reference",
    )


def collect_bars() -> list[Bar]:
    bars: list[Bar] = []
    pk = _load_pykmc_grid_cell()
    if pk is not None:
        bars.append(pk)
    pl_grid = _load_pylat_aggregate(
        PYLAT_GRID / "aggregate_summary.json",
        slab_id="22x22x20 100Ni grid (surface)",
        notes="500k steps, 4 replicas (production)",
    )
    if pl_grid is not None:
        bars.append(pl_grid)

    archive_cells = [
        (
            "Ni_22x22x20_bulkvac",
            "22x22x20 bulkvac (archive)",
            "1M steps, BULK 1vac (different physics regime)",
        ),
        (
            "Ni_10x10x6_surfvac",
            "10x10x6 surfvac (archive)",
            "1M steps, smaller slab",
        ),
        (
            "Ni_8x8x3_surfvac",
            "8x8x3 surfvac (archive)",
            "100k steps, smallest slab",
        ),
    ]
    for dirname, slab_id, notes in archive_cells:
        b = _load_pylat_aggregate(
            ARCHIVE_DIR / dirname / "output" / "aggregate_summary.json",
            slab_id=slab_id,
            notes=notes,
        )
        if b is not None:
            bars.append(b)
    return bars


def plot_bars(bars: list[Bar], out_path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    # Group by slab; separate pyKMC vs pylatkmc bars side-by-side.
    slabs = []
    for b in bars:
        if b.slab_id not in slabs:
            slabs.append(b.slab_id)

    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.35
    x = np.arange(len(slabs))
    # color by engine
    colors = {"pyKMC": "#3b75af", "pylatkmc": "#e1812c"}
    for engine_idx, eng in enumerate(("pyKMC", "pylatkmc")):
        ds = []
        sems = []
        for slab in slabs:
            match = [b for b in bars if b.slab_id == slab and b.engine == eng]
            if match:
                # if multiple pylatkmc bars for one slab, take the longest-time one
                m = max(match, key=lambda b: b.t_end_s)
                ds.append(m.D_A2_per_s)
                # crude SEM band — use msd_sem/(6*t)
                sems.append(m.msd_sem / (6.0 * m.t_end_s) if m.t_end_s > 0 else 0)
            else:
                ds.append(float("nan"))
                sems.append(0)
        ax.bar(
            x + (engine_idx - 0.5) * width,
            ds,
            width,
            yerr=sems,
            label=eng,
            color=colors[eng],
            edgecolor="black",
            capsize=3,
        )

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(slabs, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("D = MSD / (6t)   [Å²/s]")
    ax.set_title(
        "T=500 K, 1 vacancy: D per slab and engine\n"
        "Same-slab pyKMC vs pylatkmc bars test the user's "
        "\"1-vac line-up\" hypothesis"
    )
    ax.legend()
    ax.grid(True, axis="y", which="both", alpha=0.3)

    # Annotate with t_end on each bar so the long-time provenance is visible.
    for engine_idx, eng in enumerate(("pyKMC", "pylatkmc")):
        for slab_idx, slab in enumerate(slabs):
            match = [b for b in bars if b.slab_id == slab and b.engine == eng]
            if not match:
                continue
            m = max(match, key=lambda b: b.t_end_s)
            xpos = slab_idx + (engine_idx - 0.5) * width
            ax.annotate(
                f"t={m.t_end_s:.1e}s\nN={m.n_steps_or_frames:.0e}",
                (xpos, m.D_A2_per_s),
                ha="center",
                va="bottom",
                fontsize=7,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_csv(bars: list[Bar], out_path: Path) -> None:
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            (
                "slab_id",
                "engine",
                "n_steps_or_frames",
                "t_end_s",
                "MSD_A2",
                "MSD_sem",
                "D_A2_per_s",
                "notes",
            )
        )
        for b in bars:
            w.writerow(
                (
                    b.slab_id,
                    b.engine,
                    b.n_steps_or_frames,
                    b.t_end_s,
                    b.msd_A2,
                    b.msd_sem,
                    b.D_A2_per_s,
                    b.notes,
                )
            )


def main() -> int:
    bars = collect_bars()
    print(f"loaded {len(bars)} bars across {len({b.slab_id for b in bars})} slabs")
    for b in bars:
        print(
            f"  {b.engine:9s} {b.slab_id:35s} t={b.t_end_s:.2e}s "
            f"MSD={b.msd_A2:.2e} D={b.D_A2_per_s:.2e}"
        )
    write_csv(bars, OUT_CSV)
    print(f"wrote csv -> {OUT_CSV}")
    plot_bars(bars, OUT_PLOT)
    print(f"wrote plot -> {OUT_PLOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
