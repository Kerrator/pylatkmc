"""CLI for trajectory-recovery HTST: per-family Vineyard ν₀ from real events.

    python -m pylatkmc.ingest.cli recover \
        --rate-table   .../rate_lookup_table_family.csv \
        --classified   .../classified_events_with_families.csv \
        --potential    /path/to/NiAlH_jea.eam \
        --T 500 \
        --out-bucket   family_prefactors_bucket.csv \
        --out-family   family_prefactors.csv \
        --out-geometry recovery_audit.csv \
        --families surface_1NN_inplane,subsurface_1NN_inplane \
        --per-bucket 5
"""

from __future__ import annotations

import argparse
import sys

from .trajectory_recovery import resolve_targets, run_buckets, write_outputs


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pylatkmc.ingest", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("recover", help="recover per-family ν₀ from trajectories")
    r.add_argument("--rate-table", required=True, help="rate_lookup_table_family.csv")
    r.add_argument("--classified", required=True, help="classified_events_with_families.csv")
    r.add_argument("--potential", default="auto",
                   help="EAM potential path, or 'auto' (default) to resolve per-sim from input.in")
    r.add_argument("--T", type=float, default=500.0, help="temperature K (provenance only)")
    r.add_argument("--out-bucket", required=True, help="per-bucket ν₀ CSV (upserted)")
    r.add_argument("--out-family", default=None, help="rolled-up per-family ν₀ CSV (upserted)")
    r.add_argument("--out-geometry", default=None, help="per-geometry audit CSV")
    r.add_argument("--families", default=None, help="comma-separated family_ids (default: all)")
    r.add_argument("--per-bucket", type=int, default=None, help="cap representatives per bucket")
    r.add_argument("--free-radius", type=float, default=6.0, help="Hessian free-atom radius (Å)")
    r.add_argument("--dx", type=float, default=0.01, help="finite-difference step (Å)")
    r.add_argument("--no-verify", action="store_true", help="skip trajectory firing-step verification")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd != "recover":
        return 2

    families = [f.strip() for f in args.families.split(",")] if args.families else None
    targets = resolve_targets(
        args.rate_table, args.classified, families=families, per_bucket=args.per_bucket
    )
    if not targets:
        print("no targets resolved (check --families / rate table)", file=sys.stderr)
        return 1
    print(f"resolved {len(targets)} representative events across "
          f"{len({(t.family_id, t.family_bucket_id) for t in targets})} buckets")

    buckets, geoms = run_buckets(
        targets, args.potential, T_K=args.T, free_radius=args.free_radius,
        dx=args.dx, verify_trajectory=not args.no_verify,
    )
    write_outputs(buckets, geoms, args.out_bucket, args.out_family, args.out_geometry)

    n_ok = sum(g.ok for g in geoms)
    n_fam = sum(1 for b in buckets if b.n_accepted > 0)
    print(f"\ndone: {n_ok}/{len(geoms)} geometries accepted; "
          f"{n_fam}/{len(buckets)} buckets got a ν₀.")
    print(f"  per-bucket -> {args.out_bucket}")
    if args.out_family:
        print(f"  per-family -> {args.out_family}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
