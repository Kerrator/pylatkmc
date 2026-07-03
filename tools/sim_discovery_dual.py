"""Pair each pyKMC simulation cell with its matching pylatkmc cell.

The two engines write outputs into different trees:

  * pyKMC:    ``Data/Research/100Ni/{nvac}vac/T{T}/{full,NiAlH_full}/``
  * pylatkmc: ``pylatkmc/models/ni_fe_cr_v1/examples/full_100Ni/output_T{T}_{nvac}vac/``

This module reuses the existing pyKMC walker
(``Data/Research/sim_discovery.find_simulations``) and pairs each hit
with the pylatkmc cell at the same (composition, T, nvac). Composition is
fixed at "100Ni" for this study; only the 100Ni cells are included.

The ``coloring`` subdirectory naming on the pyKMC side is inconsistent
across cells (some are ``full``, some are ``NiAlH_full``). The walker
handles both transparently — every match is returned.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Pull the pyKMC walker in via sys.path (it lives in a sibling tree).
_REPO_ROOT = Path(__file__).resolve().parents[2]  # kmc/
_RESEARCH_DIR = _REPO_ROOT / "Data" / "Research"
sys.path.insert(0, str(_RESEARCH_DIR))
from sim_discovery import SimInfo, find_simulations  # noqa: E402

PYKMC_RESEARCH_ROOT = _RESEARCH_DIR
PYLAT_GRID_ROOT = (
    _REPO_ROOT
    / "pylatkmc"
    / "models"
    / "ni_fe_cr_v1"
    / "examples"
    / "full_100Ni"
)


@dataclass(frozen=True)
class DualCell:
    """A (T, nvac) cell with both engines' artefact paths.

    ``pylat_path`` is None if the matching pylatkmc cell hasn't been run
    yet; ``pykmc_path`` is None if pyKMC's grid is missing that cell. We
    return both partial and full pairs so the caller can report coverage.
    """

    composition: str
    n_vacancies: int
    temperature_K: float
    pykmc_sim: SimInfo | None
    pylat_path: Path | None

    @property
    def pykmc_summary_path(self) -> Path | None:
        if self.pykmc_sim is None:
            return None
        return self.pykmc_sim.path / "analysis" / "summary.json"

    @property
    def pylat_summary_path(self) -> Path | None:
        if self.pylat_path is None:
            return None
        return self.pylat_path / "aggregate_summary.json"

    @property
    def is_complete(self) -> bool:
        return (
            self.pykmc_summary_path is not None
            and self.pykmc_summary_path.is_file()
            and self.pylat_summary_path is not None
            and self.pylat_summary_path.is_file()
        )


def _pylat_path_for(temp_K: float, nvac: int, root: Path = PYLAT_GRID_ROOT) -> Path:
    """Canonical pylatkmc cell path for (T, nvac) on the 100Ni grid."""
    return root / f"output_T{int(temp_K)}_{nvac}vac"


def find_dual_cells(
    composition: str = "100Ni",
    pykmc_root: Path = PYKMC_RESEARCH_ROOT,
    pylat_root: Path = PYLAT_GRID_ROOT,
) -> list[DualCell]:
    """Walk the pyKMC tree and pair each cell with its pylatkmc match.

    Returns
    -------
    list[DualCell]
        Sorted by (T, nvac). One row per (T, nvac) cell. If the pyKMC side
        has multiple coloring subdirs for the same (T, nvac), the *first*
        is used (we standardise on "NiAlH_full" if both exist, else
        whichever is found).
    """
    pykmc_sims = [
        s for s in find_simulations(pykmc_root) if s.composition == composition
    ]

    # Group by (T, nvac); prefer "NiAlH_full" coloring when both present.
    by_key: dict[tuple[int, float], SimInfo] = {}
    for s in pykmc_sims:
        key = (s.n_vacancies, s.temperature)
        if key not in by_key:
            by_key[key] = s
        else:
            # Prefer NiAlH_full over plain full
            if s.coloring == "NiAlH_full" and by_key[key].coloring != "NiAlH_full":
                by_key[key] = s

    cells: list[DualCell] = []
    for (nvac, T), pykmc_sim in by_key.items():
        pylat_path = _pylat_path_for(T, nvac, pylat_root)
        cells.append(
            DualCell(
                composition=composition,
                n_vacancies=nvac,
                temperature_K=T,
                pykmc_sim=pykmc_sim,
                pylat_path=pylat_path if pylat_path.is_dir() else None,
            )
        )

    cells.sort(key=lambda c: (c.temperature_K, c.n_vacancies))
    return cells


def coverage_report(cells: list[DualCell]) -> str:
    """Human-readable summary of which cells are populated on both sides."""
    n_total = len(cells)
    n_complete = sum(1 for c in cells if c.is_complete)
    n_pykmc_only = sum(
        1
        for c in cells
        if c.pykmc_summary_path
        and c.pykmc_summary_path.is_file()
        and not (c.pylat_summary_path and c.pylat_summary_path.is_file())
    )
    n_pylat_only = sum(
        1
        for c in cells
        if c.pylat_summary_path
        and c.pylat_summary_path.is_file()
        and not (c.pykmc_summary_path and c.pykmc_summary_path.is_file())
    )
    return (
        f"DualCell coverage: {n_complete}/{n_total} cells with both engines; "
        f"pyKMC-only: {n_pykmc_only}; pylatkmc-only: {n_pylat_only}"
    )


def load_pykmc_summary(cell: DualCell) -> dict:
    """Read the pyKMC summary.json for a cell. Raises FileNotFoundError if absent."""
    p = cell.pykmc_summary_path
    if p is None or not p.is_file():
        raise FileNotFoundError(f"pyKMC summary missing for {cell}")
    with open(p) as f:
        return json.load(f)


def load_pylat_summary(cell: DualCell) -> dict:
    """Read the pylatkmc aggregate_summary.json. Raises if absent."""
    p = cell.pylat_summary_path
    if p is None or not p.is_file():
        raise FileNotFoundError(f"pylatkmc summary missing for {cell}")
    with open(p) as f:
        return json.load(f)


__all__ = (
    "PYKMC_RESEARCH_ROOT",
    "PYLAT_GRID_ROOT",
    "DualCell",
    "find_dual_cells",
    "coverage_report",
    "load_pykmc_summary",
    "load_pylat_summary",
)
