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

Run with:
    python build_family_rate_table.py \\
        --input  lattice_event_classification/classified_events_with_families.csv \\
        --output lattice_event_classification/rate_lookup_table_family.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from .families import FAMILY_REGISTRY


def _barrier_stats(barriers: pd.Series) -> dict:
    n = len(barriers)
    if n == 0:
        return {
            "n_events": 0,
            "Ea_mean_eV": float("nan"),
            "Ea_std_eV":  float("nan"),
            "Ea_min_eV":  float("nan"),
            "Ea_max_eV":  float("nan"),
            "Ea_median_eV": float("nan"),
        }
    return {
        "n_events":     n,
        "Ea_mean_eV":   float(barriers.mean()),
        "Ea_std_eV":    float(barriers.std()) if n > 1 else 0.0,
        "Ea_min_eV":    float(barriers.min()),
        "Ea_max_eV":    float(barriers.max()),
        "Ea_median_eV": float(barriers.median()),
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


def build_family_table(assigned_df: pd.DataFrame) -> pd.DataFrame:
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
                "source_filter":     "accepted; audit_excluded=False",
                "representative_row_indices": "[]",
            })
            continue

        for bucket, grp in fam_accepted.groupby("family_bucket_id", sort=True):
            stats = _barrier_stats(grp["energy_barrier"])
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
    args = ap.parse_args()

    print(f"[build_family_rate_table] reading {args.input}")
    df = pd.read_csv(args.input)
    print(f"  {len(df)} rows; "
          f"accepted={int((df['assignment_status']=='accepted').sum())}, "
          f"excluded={int((df['assignment_status']=='excluded').sum())}, "
          f"unresolved={int((df['assignment_status']=='unresolved').sum())}")

    tbl = build_family_table(df)

    # Attach HTST nu0 (Hz) with per-bucket → per-family → k0 precedence. Buckets
    # without a recovered nu0 stay NaN and fall back to the global k0 in the
    # pylatkmc translator. nu0_source records which tier supplied each value.
    bucket_nu0 = load_bucket_nu0(args.prefactors_bucket)
    family_nu0 = load_family_nu0(args.prefactors)
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

    print("\n=== populated rows ===")
    cols = ["family_id", "family_bucket_id", "n_events", "Ea_mean_eV", "Ea_std_eV"]
    with pd.option_context("display.max_rows", None,
                           "display.width", 120,
                           "display.max_colwidth", 40):
        print(tbl[tbl["n_events"] > 0][cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
