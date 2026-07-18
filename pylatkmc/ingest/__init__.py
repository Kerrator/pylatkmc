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

Event-representation layer (Phase A)
------------------------------------
These five flat modules form the deterministic pyKMC-event → ``EventClass`` catalogue
pipeline (identity + rate-space aggregation + gates). Their load-time import DAG is
``projection/event_projection/canonical → lattice, event_class`` and ``event_class →
(numpy, stdlib)`` only (pandas/pyarrow are imported lazily inside I/O functions), so
importing them never pulls a heavy dependency at module load.

lattice                  FCC integer embedding (parity, NN shells, coordination) + the
                         16-op D₄ₕ point group as pinned integer matrices (numpy/stdlib).
event_class              Schema spine: the integer-code enums, frozen value types,
                         ``ProjectedEvent``/``EventClass`` records, rate-space
                         aggregation (§6.1), gates G1–G7, catalogue assembly, and the
                         ``EventClass`` Parquet reader/writer.
projection               Forward off-lattice snapshot → sparse FCC ``Occupancy`` projection
                         (frame calibration, snap, flood-fill/depth) + deterministic
                         ``to_atomistic`` reverse map for round-trip tests.
event_projection         One pyKMC reference row → ``ProjectedEvent`` via its own local FCC
                         fit (min-image unwrap, mover/saddle detection, depth signature).
canonical                Class identity: the complete (translation × D₄ₕ × automorphism)
                         orbit invariant → ``canonical_form``, its TLV ``canonical_blob``,
                         and the blake2b ``class_id`` (plus ``move_shape``/``family_id``).

Dependencies
------------
This subpackage is **optional** and dependency-heavy; ``pylatkmc`` core (codegen +
runtime) does not import it. Install the extras and import submodules explicitly::

    pip install -e ".[ingest]"          # pandas, scipy, ase, pyarrow
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
