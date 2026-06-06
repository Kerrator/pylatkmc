"""pylatkmc.ingest — the pyKMC → pylatkmc bridge.

This subpackage turns pyKMC analysis outputs into the curated FCC family rate
table that ``pylatkmc.translator`` consumes, and produces the per-family
Vineyard prefactors (ν₀) that drive ``style = "htst"`` rates.

Submodules
----------
families                 Curated FCC movement-family registry (FCCFamily, FAMILY_REGISTRY).
family_assignment        Assign each classified event to a family + bucket (audit-aware).
build_family_rate_table  Aggregate barriers per family/bucket → rate_lookup_table_family.csv.
htst.kappa_rpa           Pure-NumPy Vineyard ν₀ + RPA κ (LAMMPS-free).
htst.hessian_lammps      LAMMPS/ASE mass-weighted Hessian.
htst.canonical_kappa     Canonical-slab ν₀ driver (fallback geometry source).
trajectory_recovery      Recover full-system geometries from pyKMC trajectories → real per-geo ν₀.

Dependencies
------------
This subpackage is **optional** and dependency-heavy; ``pylatkmc`` core (codegen +
runtime) does not import it. Install the extras and import submodules explicitly::

    pip install -e ".[ingest]"          # pandas, scipy, ase
    from pylatkmc.ingest.families import FAMILY_REGISTRY
    from pylatkmc.ingest.build_family_rate_table import build_family_table

The HTST producers and ``trajectory_recovery`` additionally require LAMMPS (Python
bindings), pARTn, IRA, and pyKMC to be importable in the environment — these are local
builds, not pip dependencies (see docs/INGEST_PIPELINE.md). Submodule imports raise a
plain ``ModuleNotFoundError`` naming the missing package when an extra is absent.

Nothing is imported at package import time, so ``import pylatkmc.ingest`` is cheap and
never pulls pandas/ASE/LAMMPS until you import a specific submodule.
"""

from __future__ import annotations

__all__: list[str] = []
