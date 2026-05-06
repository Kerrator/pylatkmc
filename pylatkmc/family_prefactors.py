"""Per-family Vineyard ν₀ + RPA κ prefactor lookup for the rate-cube builder.

This module is an *optional* extension to `ratebuilder.py`'s rate-baking
chain. The default behaviour (no `family_prefactors.csv` provided) is to
use the spec's single `k0_Hz` value (typically 1×10¹³ Hz, the Ni Debye
ballpark) for every cell. With a `family_prefactors.csv` available, each
family gets its own k₀_eff = ν₀ × κ_RPA from a Vineyard / RPA calculation
on a canonical-slab geometry.

See `apps/PyKMC_Analysis/Analysis/HTST.md` for the comprehensive HTST
reference (theory, file layout, output schema, May 2026 bug history,
known limitations, integration plan, troubleshooting), and
`docs/pylatkmc_msd_diagnosis.md` § "Frequency-correction track" for the
narrative form of the same material. The actual calculation lives at
`apps/PyKMC_Analysis/Analysis/htst/canonical_kappa.py`.

CSV schema (matches `_RESULT_SCHEMA` in `canonical_kappa.py`):

    motif, T_K, n_free, Ea_eV,
    omega0_eV, omega0_THz, nu0_Hz, nu0_THz,
    kappa_RPA, kappa_HF, alpha_h, alpha_f, alpha_f_kT,
    k0_assumed_Hz, rate_correction_factor,
    saddle_converged, fmax_at_saddle_eV_per_A,
    neb_n_images, free_radius_A, delta_q0, dx, notes

Only `motif`, `T_K`, `nu0_Hz`, `kappa_RPA`, `saddle_converged` are read
by this loader; the rest are provenance. A row is *usable* iff:

    saddle_converged is True AND
    1e10 < nu0_Hz < 1e14    AND      # 0.01–100 THz, broad sanity
    0 < kappa_RPA <= 1.0001 (or kappa_RPA is NaN: bare-Vineyard mode)

For κ_RPA = NaN (e.g. perturbation theory broke down), the loader can
operate in **bare-Vineyard mode**: k₀_eff = ν₀ (no κ correction). Set
`allow_bare_vineyard=True` in `load_family_prefactors`.

Integration plan (TODO, not yet wired into ratebuilder.py):

1. `pylatkmc-gen rate` accepts an optional `--family-prefactors <csv>` flag.
   If absent, behaviour is unchanged (k₀ = spec.rate_data.k0_Hz).
2. `ratebuilder.build()` calls `load_family_prefactors(...)` once.
   The result is a `dict[str, float]` mapping family_id → k₀_eff (Hz).
3. In tier 1 (direct aggregation), the rate-baking line at
   `ratebuilder.py:621` becomes:
       k0_eff = family_prefactors.get(row['family_id'], spec.rate_data.k0_Hz)
       rate[idx] = (k0_eff * np.exp(-Ea_mean / kT))
   But this requires per-row family_id which the current group-by drops;
   simplest fix is to keep `family_id` as part of the group-by key, then
   look up k0_eff per group.
4. In tier 6 (`_apply_tier6_family`), the family is known explicitly
   (it's the family being borrowed from). Replace the constant `k0` in
   the `fill_rate = k0 * np.exp(-Ea_val/kT)` line with
   `family_prefactors.get(family, k0)`.
5. In tier 7 (`_apply_tier7_scalar`), the legacy table is for
   `surface_1NN_inplane` only (per the spec); use that family's
   prefactor.
6. The `.kmcrt` header should record which families used non-default
   prefactors (add a `family_prefactors_applied` JSON list to the
   header). This is for `pylatkmc-gen provenance` to surface.
"""

from __future__ import annotations

import csv
import math
import warnings
from pathlib import Path
from typing import Dict, NamedTuple, Optional


__all__ = (
    "FamilyPrefactor",
    "load_family_prefactors",
    "summarise_prefactors",
)


# Sanity ranges. Wider than test_hessian_lammps so we admit edge motifs.
_NU0_MIN_HZ = 1.0e10    # 0.01 THz
_NU0_MAX_HZ = 1.0e14    # 100 THz
_KAPPA_MIN = 0.0        # bare lower bound; loader filters at >0
_KAPPA_MAX = 1.0001     # numerical excursion tolerance (matches kappa_rpa.py)


class FamilyPrefactor(NamedTuple):
    """One per-family entry in the loaded prefactor table."""
    family_id: str
    nu0_Hz: float           # Vineyard prefactor
    kappa_RPA: Optional[float]   # None if bare-Vineyard mode (κ unavailable)
    k0_eff_Hz: float        # ν₀ · κ (or just ν₀ if κ is None)
    T_K: float
    saddle_converged: bool
    notes: str


def load_family_prefactors(
    path: Path | str,
    *,
    target_T_K: float | None = None,
    allow_bare_vineyard: bool = True,
    require_saddle_converged: bool = True,
) -> Dict[str, FamilyPrefactor]:
    """Load `family_prefactors.csv` into a dict keyed by family_id.

    Parameters
    ----------
    path : path to the CSV.
    target_T_K : if set, only return rows whose `T_K` matches (within 1 K).
        If None, returns ALL rows; in this case the caller must ensure the
        T matches the cube being built (ratebuilder bakes Arrhenius at a
        single T).
    allow_bare_vineyard : if True, rows with `kappa_RPA = NaN` are kept
        with k₀_eff = ν₀ (no recrossing correction). If False, those
        rows are dropped and a warning is emitted.
    require_saddle_converged : if True, drop rows with
        `saddle_converged = False`. The diagnostic columns
        `fmax_at_saddle_eV_per_A` may still be inspected by the caller.

    Returns
    -------
    dict mapping family_id → FamilyPrefactor.
        Empty dict if the CSV is empty or all rows are filtered out.

    Raises
    ------
    FileNotFoundError if the CSV doesn't exist.
    ValueError if the schema doesn't match (missing required columns).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"family prefactors CSV not found: {path}")

    out: Dict[str, FamilyPrefactor] = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        required = ("motif", "T_K", "nu0_Hz", "kappa_RPA", "saddle_converged")
        for col in required:
            if col not in reader.fieldnames:
                raise ValueError(
                    f"family prefactors CSV missing required column {col!r}; "
                    f"got {reader.fieldnames}"
                )

        for row in reader:
            family_id = row["motif"].strip()
            if not family_id:
                continue
            try:
                T_K = float(row["T_K"])
                nu0_Hz = float(row["nu0_Hz"])
            except (ValueError, TypeError):
                warnings.warn(f"family_prefactors: skipping malformed row {row!r}")
                continue

            if target_T_K is not None and abs(T_K - target_T_K) > 1.0:
                continue

            kappa_str = (row.get("kappa_RPA", "") or "").strip().lower()
            if kappa_str in ("", "nan", "none"):
                kappa_RPA: Optional[float] = None
            else:
                try:
                    kappa_RPA = float(row["kappa_RPA"])
                except (ValueError, TypeError):
                    kappa_RPA = None

            sad_conv_str = (row.get("saddle_converged", "") or "").strip().lower()
            saddle_converged = sad_conv_str in ("true", "1", "yes")

            if require_saddle_converged and not saddle_converged:
                warnings.warn(
                    f"family_prefactors: family {family_id} saddle did not "
                    f"converge; skipping",
                    RuntimeWarning,
                )
                continue

            if not (_NU0_MIN_HZ < nu0_Hz < _NU0_MAX_HZ):
                warnings.warn(
                    f"family_prefactors: family {family_id} ν₀={nu0_Hz} Hz "
                    f"outside sanity range [{_NU0_MIN_HZ}, {_NU0_MAX_HZ}]; skipping"
                )
                continue

            if kappa_RPA is None or math.isnan(kappa_RPA):
                if not allow_bare_vineyard:
                    warnings.warn(
                        f"family_prefactors: family {family_id} κ_RPA missing "
                        f"and allow_bare_vineyard=False; skipping"
                    )
                    continue
                k0_eff_Hz = nu0_Hz
                kappa_RPA = None
                notes = "bare-Vineyard (κ_RPA unavailable)"
            elif _KAPPA_MIN < kappa_RPA <= _KAPPA_MAX:
                k0_eff_Hz = nu0_Hz * kappa_RPA
                notes = ""
            else:
                warnings.warn(
                    f"family_prefactors: family {family_id} κ_RPA={kappa_RPA} "
                    f"outside (0, {_KAPPA_MAX}]; skipping"
                )
                continue

            out[family_id] = FamilyPrefactor(
                family_id=family_id,
                nu0_Hz=nu0_Hz,
                kappa_RPA=kappa_RPA,
                k0_eff_Hz=k0_eff_Hz,
                T_K=T_K,
                saddle_converged=saddle_converged,
                notes=notes,
            )

    return out


def summarise_prefactors(prefactors: Dict[str, FamilyPrefactor]) -> str:
    """Pretty-print a one-line-per-family summary, suitable for pylatkmc-gen
    provenance output."""
    if not prefactors:
        return "(no per-family prefactors loaded; using spec.k0_Hz everywhere)"
    lines = [
        f"  {p.family_id:30s}  ν₀={p.nu0_Hz/1e12:6.2f} THz  "
        f"κ={p.kappa_RPA if p.kappa_RPA is not None else 'NaN':>6}  "
        f"k0_eff={p.k0_eff_Hz/1e12:6.2f} THz"
        f"{(' [' + p.notes + ']') if p.notes else ''}"
        for p in prefactors.values()
    ]
    return "Per-family prefactors loaded:\n" + "\n".join(lines)
