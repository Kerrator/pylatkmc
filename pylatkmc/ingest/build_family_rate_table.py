"""Build the curated family rate table.

Reads `classified_events_with_families.csv` (emitted by `family_assignment.py`),
aggregates `energy_barrier` statistics over accepted rows grouped by
(family_id, family_bucket_id), and writes `rate_lookup_table_family.csv`.

Barrier aggregation uses only rows with:
  * assignment_status == "accepted"
  * the family's `fit_barrier == True`  (multisite families are visible but
    not fit)

For each registered family, all declared-but-empty buckets are emitted as
placeholder rows with `n_events = 0` so downstream reviewers can see gaps
rather than silently missing bins.

Barrier aggregation is done in **rate space** (contract 6.1 / FINAL_DESIGN 6.1):
per (family, bucket) the executed rate is the occurrence-weighted mean of member
rates ``mean_i(nu0_i * exp(-Ea_i / kT_ref))`` — Jensen-exact (``<exp(-Ea/kT)>``,
never ``exp(-<Ea>/kT)``). The added columns are:

  * ``k_rate_mean_psinv`` — the executed rate (ps^-1 = Hz / 1e12).
  * ``nu0_geo_psinv``     — geometric-mean prefactor (== ``nu0_eff``): the runtime
    prefactor that, with ``Ea_rep_eV``, reproduces ``k_rate_mean_psinv`` **exactly**
    at ``T_ref`` and approximates it within +/-100 K.
  * ``Ea_rep_eV``         — rate-equivalent barrier, ``-kB*T_ref*ln(k_rate_mean/nu0_geo)``
    (reporting; unit-invariant — the 1e12 cancels).
  * ``T_ref_K``           — the stamped reference temperature.

The runtime path should consume ``nu0_geo_psinv`` + ``Ea_rep_eV``, not
``Ea_mean_eV``. The legacy reporting columns (``Ea_mean_eV``, ``Ea_median_eV``,
``Ea_min_eV``, ``Ea_max_eV``, ``Ea_std_eV``, ``n_events``) are retained unchanged.
Units are **ps^-1** (a known clock-freeze trap; project note
``pykmc-k0-units-clock-freeze``).

Run with:
    python build_family_rate_table.py \\
        --input  lattice_event_classification/classified_events_with_families.csv \\
        --output lattice_event_classification/rate_lookup_table_family.csv \\
        --t-ref  500
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from .event_class import aggregate_rate_space
from .families import FAMILY_REGISTRY

# The campaign reference temperature (K). ``--t-ref`` is required on the CLI; this
# default is only the library fallback for programmatic callers.
DEFAULT_T_REF_K = 500.0
# On-lattice k0 fallback in Hz (== 1.0 ps^-1, the [RateConstant] k0 default). Used
# for the rate-space columns when a bucket has no recovered HTST nu0 — matching
# attach_nu0's "NaN -> k0" tier (project note pykmc-k0-units-clock-freeze).
DEFAULT_K0_HZ = 1.0e12


def _resolve_bucket_nu0(
    family_id: str,
    bucket_id: str,
    bucket_nu0: dict[tuple[str, str], float],
    family_nu0: dict[str, float],
) -> float:
    """Per-bucket -> per-family -> NaN nu0 (Hz), the same precedence as attach_nu0."""
    key = (str(family_id), str(bucket_id))
    if key in bucket_nu0:
        return bucket_nu0[key]
    if str(family_id) in family_nu0:
        return family_nu0[str(family_id)]
    return float("nan")


# The rate-space columns added to every emitted row (NaN for empty/visible-only rows).
_RATE_SPACE_NAN = {
    "k_rate_mean_psinv": float("nan"),
    "Ea_rep_eV":         float("nan"),
    "nu0_geo_psinv":     float("nan"),
}


def _barrier_stats(
    barriers: pd.Series,
    *,
    nu0_hz: float,
    t_ref_K: float,
    nu0_fallback_hz: float,
) -> dict:
    """Reporting barrier stats + rate-space aggregation (contract 6.1).

    The rate-space columns delegate to ``event_class.aggregate_rate_space`` over
    the bucket's accepted barriers with a single resolved ``nu0_hz`` (per-bucket ->
    per-family -> k0). The legacy reporting columns are unchanged.
    """
    n = len(barriers)
    if n == 0:
        return {
            "n_events": 0,
            "Ea_mean_eV": float("nan"),
            "Ea_std_eV":  float("nan"),
            "Ea_min_eV":  float("nan"),
            "Ea_max_eV":  float("nan"),
            "Ea_median_eV": float("nan"),
            **_RATE_SPACE_NAN,
            "T_ref_K": t_ref_K,
        }
    agg = aggregate_rate_space(
        [float(b) for b in barriers],
        [nu0_hz] * n,
        t_ref_K,
        nu0_fallback_hz=nu0_fallback_hz,
    )
    return {
        "n_events":     n,
        "Ea_mean_eV":   float(barriers.mean()),
        "Ea_std_eV":    float(barriers.std()) if n > 1 else 0.0,
        "Ea_min_eV":    float(barriers.min()),
        "Ea_max_eV":    float(barriers.max()),
        "Ea_median_eV": float(barriers.median()),
        "k_rate_mean_psinv": agg.k_rate_mean_psinv,
        "Ea_rep_eV":         agg.Ea_rep_eV,
        "nu0_geo_psinv":     agg.nu0_geo_psinv,
        "T_ref_K":      t_ref_K,
    }


def load_family_nu0(path: Path) -> dict[str, float]:
    """Map family_id -> HTST Vineyard nu0 (Hz) from ``family_prefactors.csv``.

    The prefactor CSV keys families by its ``motif`` column (== family_id).
    Families with no computed nu0 are simply absent here, so they end up NaN in
    the rate table and the pylatkmc translator falls back to the global k0.
    """
    if not path.exists():
        return {}
    pf = pd.read_csv(path)
    if "motif" not in pf.columns or "nu0_Hz" not in pf.columns:
        return {}
    return {
        str(m): float(v)
        for m, v in zip(pf["motif"], pf["nu0_Hz"], strict=False)
        if pd.notna(v)
    }


def load_bucket_nu0(path: Path) -> dict[tuple[str, str], float]:
    """Map (family_id, family_bucket_id) -> HTST nu0 (Hz) from a per-bucket CSV.

    ``family_prefactors_bucket.csv`` (produced by trajectory_recovery) keys on
    ``family_id`` + ``family_bucket_id``. ν₀ varies strongly across buckets
    within a family (vacancy-count dependent), so this per-bucket prefactor is
    the most faithful source; the family-level map is the fallback.
    """
    if not path.exists():
        return {}
    pf = pd.read_csv(path)
    need = {"family_id", "family_bucket_id", "nu0_Hz"}
    if not need.issubset(pf.columns):
        return {}
    return {
        (str(f), str(b)): float(v)
        for f, b, v in zip(pf["family_id"], pf["family_bucket_id"], pf["nu0_Hz"], strict=False)
        if pd.notna(v)
    }


def attach_nu0(
    tbl: pd.DataFrame,
    bucket_nu0: dict[tuple[str, str], float],
    family_nu0: dict[str, float],
) -> pd.DataFrame:
    """Attach ``nu0_Hz`` + ``nu0_source`` with a per-bucket → per-family → k0
    precedence (trajectory per-bucket is most faithful; family-level is the
    fallback; missing → NaN, so the translator uses the global k0)."""

    def _resolve(row: pd.Series) -> tuple[float, str]:
        key = (str(row["family_id"]), str(row["family_bucket_id"]))
        if key in bucket_nu0:
            return bucket_nu0[key], "trajectory_bucket"
        if str(row["family_id"]) in family_nu0:
            return family_nu0[str(row["family_id"])], "family"
        return float("nan"), "k0"

    resolved = tbl.apply(lambda r: _resolve(r), axis=1, result_type="expand")
    tbl = tbl.copy()
    tbl["nu0_Hz"] = resolved[0].astype(float)
    tbl["nu0_source"] = resolved[1]
    return tbl


def build_family_table(
    assigned_df: pd.DataFrame,
    *,
    t_ref_K: float = DEFAULT_T_REF_K,
    bucket_nu0: dict[tuple[str, str], float] | None = None,
    family_nu0: dict[str, float] | None = None,
    nu0_fallback_hz: float = DEFAULT_K0_HZ,
) -> pd.DataFrame:
    """Aggregate accepted-row barriers per (family, bucket) into the rate table.

    Rate-space columns (``k_rate_mean_psinv``, ``Ea_rep_eV``, ``nu0_geo_psinv``,
    ``T_ref_K``) are computed at ``t_ref_K`` using each bucket's nu0 resolved with
    the same per-bucket -> per-family -> k0 precedence as ``attach_nu0``. Passing
    the ``bucket_nu0`` / ``family_nu0`` maps keeps the rate-space nu0 consistent
    with the ``nu0_Hz`` column ``attach_nu0`` writes; without them the k0 fallback
    is used. Backward-compatible: callers using only ``assigned_df`` still work.
    """
    bucket_nu0 = bucket_nu0 or {}
    family_nu0 = family_nu0 or {}
    accepted = assigned_df[assigned_df["assignment_status"] == "accepted"]
    rows = []
    for family in FAMILY_REGISTRY:
        fam_accepted = accepted[accepted["family_id"] == family.family_id]
        if not family.fit_barrier:
            rows.append({
                "family_id":         family.family_id,
                "family_name":       family.family_name,
                "family_bucket_id":  "*",
                "family_bucket_name": "*",
                "site_motion_template": family.movement_template,
                "environment_rule":  family.environment_rule.__name__,
                "n_events":          int(len(fam_accepted)),
                "Ea_mean_eV":        float("nan"),
                "Ea_std_eV":         float("nan"),
                "Ea_min_eV":         float("nan"),
                "Ea_max_eV":         float("nan"),
                "Ea_median_eV":      float("nan"),
                **_RATE_SPACE_NAN,
                "T_ref_K":           t_ref_K,
                "source_filter":     "excluded:fit_barrier=False",
                "representative_row_indices": "[]",
            })
            continue

        if len(fam_accepted) == 0:
            rows.append({
                "family_id":         family.family_id,
                "family_name":       family.family_name,
                "family_bucket_id":  "(empty)",
                "family_bucket_name": "(no sampled events)",
                "site_motion_template": family.movement_template,
                "environment_rule":  family.environment_rule.__name__,
                "n_events":          0,
                "Ea_mean_eV":        float("nan"),
                "Ea_std_eV":         float("nan"),
                "Ea_min_eV":         float("nan"),
                "Ea_max_eV":         float("nan"),
                "Ea_median_eV":      float("nan"),
                **_RATE_SPACE_NAN,
                "T_ref_K":           t_ref_K,
                "source_filter":     "accepted; audit_excluded=False",
                "representative_row_indices": "[]",
            })
            continue

        for bucket, grp in fam_accepted.groupby("family_bucket_id", sort=True):
            nu0_hz = _resolve_bucket_nu0(family.family_id, bucket, bucket_nu0, family_nu0)
            stats = _barrier_stats(
                grp["energy_barrier"],
                nu0_hz=nu0_hz,
                t_ref_K=t_ref_K,
                nu0_fallback_hz=nu0_fallback_hz,
            )
            rep_idx = grp.index[:5].tolist()
            rows.append({
                "family_id":         family.family_id,
                "family_name":       family.family_name,
                "family_bucket_id":  bucket,
                "family_bucket_name": bucket,  # same until a namer function lands
                "site_motion_template": family.movement_template,
                "environment_rule":  family.environment_rule.__name__,
                **stats,
                "source_filter":     "accepted; audit_excluded=False",
                "representative_row_indices": json.dumps(list(map(int, rep_idx))),
            })
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",  type=Path,
                    default=Path("lattice_event_classification/classified_events_with_families.csv"))
    ap.add_argument("--output", type=Path,
                    default=Path("lattice_event_classification/rate_lookup_table_family.csv"))
    ap.add_argument("--prefactors", type=Path,
                    default=Path("lattice_event_classification/family_prefactors.csv"),
                    help="per-FAMILY HTST nu0 (motif,nu0_Hz); fallback tier of the nu0_Hz join")
    ap.add_argument("--prefactors-bucket", type=Path,
                    default=Path("lattice_event_classification/family_prefactors_bucket.csv"),
                    help="per-BUCKET HTST nu0 (family_id,family_bucket_id,nu0_Hz); primary tier")
    ap.add_argument("--t-ref", type=float, required=True,
                    help="reference temperature (K) for the rate-space columns (campaign: 500)")
    args = ap.parse_args()

    print(f"[build_family_rate_table] reading {args.input}  (T_ref={args.t_ref} K)")
    df = pd.read_csv(args.input)
    print(f"  {len(df)} rows; "
          f"accepted={int((df['assignment_status']=='accepted').sum())}, "
          f"excluded={int((df['assignment_status']=='excluded').sum())}, "
          f"unresolved={int((df['assignment_status']=='unresolved').sum())}")

    # Resolve HTST nu0 (Hz) with per-bucket → per-family → k0 precedence BEFORE the
    # table build so the rate-space columns and the nu0_Hz column share the same nu0.
    bucket_nu0 = load_bucket_nu0(args.prefactors_bucket)
    family_nu0 = load_family_nu0(args.prefactors)

    tbl = build_family_table(df, t_ref_K=args.t_ref, bucket_nu0=bucket_nu0, family_nu0=family_nu0)

    # Attach the nu0_Hz + nu0_source provenance columns (same precedence). Buckets
    # without a recovered nu0 stay NaN and fall back to the global k0.
    tbl = attach_nu0(tbl, bucket_nu0, family_nu0)
    src = tbl["nu0_source"].value_counts().to_dict()
    print(f"[build_family_rate_table] HTST nu0: {len(bucket_nu0)} per-bucket + "
          f"{len(family_nu0)} per-family sources; row provenance {src}")

    # Sort: fit_barrier families first (populated), then empty, then visible-only.
    tbl["_sort_group"] = 0
    tbl.loc[tbl["source_filter"].str.startswith("excluded"), "_sort_group"] = 2
    tbl.loc[tbl["n_events"] == 0, "_sort_group"] = 1
    tbl = tbl.sort_values(["_sort_group", "family_id", "family_bucket_id"]).drop(columns="_sort_group")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(args.output, index=False)
    print(f"[build_family_rate_table] wrote {args.output}")
    print(f"  {len(tbl)} rows total:")
    n_populated = int((tbl["n_events"] > 0).sum())
    n_empty     = int(((tbl["n_events"] == 0)
                       & tbl["source_filter"].str.startswith("accepted")).sum())
    n_visible_only = int(tbl["source_filter"].str.startswith("excluded").sum())
    print(f"    {n_populated} populated buckets")
    print(f"    {n_empty} declared-but-empty buckets")
    print(f"    {n_visible_only} visible-only families (fit_barrier=False)")

    print(f"\n=== populated rows (T_ref={args.t_ref} K; rates in ps^-1) ===")
    cols = ["family_id", "family_bucket_id", "n_events",
            "Ea_mean_eV", "Ea_rep_eV", "k_rate_mean_psinv", "nu0_geo_psinv"]
    with pd.option_context("display.max_rows", None,
                           "display.width", 120,
                           "display.max_colwidth", 40):
        print(tbl[tbl["n_events"] > 0][cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
