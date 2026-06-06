"""Status codes and record schemas for trajectory-recovery HTST.

These are pure-logic, dependency-free (stdlib only) so they can be imported and
unit-tested without pandas / ASE / LAMMPS. ``trajectory_recovery`` populates them.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum


class RecoveryStatus(str, Enum):
    """Outcome of attempting to recover one event's ν₀ from a trajectory.

    Only ``OK`` and ``FALLBACK_CANONICAL`` contribute a usable ν₀; every other
    value is a gate that dropped the geometry (with a recorded reason).
    """

    OK = "ok"  # full-system recovery succeeded; ν₀ accepted
    FALLBACK_CANONICAL = "fallback_canonical"  # no trajectory ν₀; canonical slab used
    EVENT_NEVER_FIRED = "event_never_fired"  # idx_ref never appears in pykmc.out
    NO_FRAME = "no_frame"  # firing step has no on-cadence trajectory frame
    MOVER_NOT_FOUND = "mover_not_found"  # frame-diff found no atom above threshold
    MOVER_PSR_MISMATCH = "mover_psr_mismatch"  # recovered site fails IRA/PSR vs catalogue
    EA_MISMATCH = "ea_mismatch"  # recovered barrier disagrees with catalogue Ea
    SADDLE_NOT_FIRST_ORDER = "saddle_not_first_order"  # Hessian != exactly 1 negative mode
    NU0_OUT_OF_RANGE = "nu0_out_of_range"  # ν₀ outside the physical sanity band
    ERROR = "error"  # unexpected exception (message in `note`)


# Physical sanity band for an FCC-metal Vineyard prefactor (Hz). Values outside
# this are flagged (not silently averaged in). 1–50 THz brackets the FCC-Ni
# literature range (~5–30 THz) with margin.
NU0_MIN_HZ = 1.0e12
NU0_MAX_HZ = 5.0e13


@dataclass(frozen=True)
class GeometryRecord:
    """One recovered geometry's ν₀ attempt (one representative event)."""

    family_id: str
    family_bucket_id: str
    sim_path: str
    idx_ref: int
    status: RecoveryStatus
    nu0_Hz: float | None = None
    Ea_catalogue_eV: float | None = None
    Ea_recovered_eV: float | None = None
    n_movers: int | None = None
    n_free: int | None = None
    firing_step: int | None = None
    frame_index: int | None = None
    psr_score: float | None = None
    min1_reminimized: bool = False
    saddle_mode: str | None = None  # "embed" | "embed_refine"
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.status is RecoveryStatus.OK and self.nu0_Hz is not None

    def to_row(self) -> dict[str, object]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class BucketRecord:
    """Aggregated ν₀ for one (family_id, family_bucket_id) at a temperature."""

    family_id: str
    family_bucket_id: str
    T_K: float
    geometries: list[GeometryRecord] = field(default_factory=list)

    def _accepted_nu0(self) -> list[float]:
        return [g.nu0_Hz for g in self.geometries if g.ok and g.nu0_Hz is not None]

    @property
    def n_attempted(self) -> int:
        return len(self.geometries)

    @property
    def n_accepted(self) -> int:
        return len(self._accepted_nu0())

    def nu0_median(self) -> float | None:
        vals = sorted(self._accepted_nu0())
        if not vals:
            return None
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else 0.5 * (vals[mid - 1] + vals[mid])

    def nu0_geomean(self) -> float | None:
        vals = self._accepted_nu0()
        if not vals:
            return None
        return float(math.exp(sum(math.log(v) for v in vals) / len(vals)))

    def to_row(self) -> dict[str, object]:
        """Per-bucket summary row for family_prefactors_bucket.csv."""
        med = self.nu0_median()
        return {
            "family_id": self.family_id,
            "family_bucket_id": self.family_bucket_id,
            "T_K": self.T_K,
            "nu0_Hz": med,
            "nu0_THz": (med / 1e12) if med is not None else None,
            "nu0_geomean_Hz": self.nu0_geomean(),
            "n_geos_accepted": self.n_accepted,
            "n_geos_attempted": self.n_attempted,
            "nu0_source": "trajectory" if med is not None else "none",
        }
