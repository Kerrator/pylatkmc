"""Command-line entry point for pylatkmc.

Exposed as `pylatkmc-gen` via the pyproject.toml [project.scripts] table.

Usage:
    pylatkmc-gen build <spec.kmcspec.toml>      # render proclist.{c,h} into generated/
    pylatkmc-gen info  <spec.kmcspec.toml>      # print spec axes / paths
    pylatkmc-gen processes <spec.kmcspec.toml>  # translate catalogue → Processes (read-only summary)
    pylatkmc-gen clean <spec.kmcspec.toml>      # rm -rf generated/
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from pylatkmc import load
from pylatkmc.codegen import generate


def _resolve_generated_dir(spec_path: Path) -> Path:
    """Canonical layout: <model_dir>/<model_name>.kmcspec.toml →
    <model_dir>/generated/"""
    return spec_path.parent / "generated"


def cmd_build(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    out = _resolve_generated_dir(spec_path)
    written = generate(spec, out, spec_path=spec_path)
    print(f"pylatkmc-gen: rendered {len(written)} file(s) for model '{spec.name}' -> {out}")
    for p in written:
        print(f"  {p.relative_to(spec_path.parent)}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    print(f"name:            {spec.name}")
    print(f"lattice:         {spec.lattice}")
    print(f"species:         {spec.species}")
    print(f"shells:          {[s.name for s in spec.shells]}")
    print(f"T / k0:          {spec.rate_data.temperature_K} K, {spec.rate_data.k0_Hz:.2e} Hz")
    if spec.rate_data.family_table is not None:
        print(f"family_table:    {spec.rate_data.family_table}")
    return 0


def cmd_processes(args: argparse.Namespace) -> int:
    """Translate a curated catalogue into pattern-DB Processes and print a summary.

    Reports per-family Process counts, total Process count, Ea range,
    and any wide-Ea-scatter or unknown-family warnings. The Processes
    themselves are NOT written to disk by this command (that's `build`
    in v2). This is a read-only inspection tool.
    """
    from collections import Counter

    from .loader import load
    from .translator import load_family_rate_table, translate_all

    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)

    family_csv = Path(args.family_csv) if args.family_csv else Path(spec.rate_data.family_table)
    if not family_csv.is_absolute():
        # Relative to spec dir
        family_csv = (spec_path.parent / family_csv).resolve()

    if not family_csv.exists():
        print(f"pylatkmc-gen processes: family rate table not found: {family_csv}", file=sys.stderr)
        return 1

    rows = load_family_rate_table(family_csv)
    print(f"Loaded {len(rows)} family-bucket rows from {family_csv.name}")

    scatter_warnings: list[str] = []
    unknown_families: list[str] = []
    processes = translate_all(
        rows,
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
        on_scatter_warn=scatter_warnings.append,
        on_unknown_family=unknown_families.append,
    )

    fam_proc_counts = Counter(p.family_id for p in processes)
    print(f"\nTotal Processes: {len(processes)}")
    print("Processes per family:")
    for fid, n in sorted(fam_proc_counts.items()):
        print(f"  {fid:42s} {n:>5} Processes")

    if processes:
        ea = [p.Ea_eV for p in processes]
        print(f"\nEa_eV range: min={min(ea):.3f}  max={max(ea):.3f}")

    if unknown_families:
        print("\nWARNING: unknown families in catalogue (skipped):")
        for f in sorted(set(unknown_families)):
            print(f"  {f}")

    if scatter_warnings:
        print(
            f"\nWARNING: {len(scatter_warnings)} wide-Ea-scatter buckets "
            f"(per-bucket-mean rate may be unreliable):"
        )
        for w in scatter_warnings[:10]:
            print(f"  {w}")
        if len(scatter_warnings) > 10:
            print(f"  ... and {len(scatter_warnings) - 10} more")

    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    out = _resolve_generated_dir(spec_path)
    if out.is_dir():
        shutil.rmtree(out)
        print(f"pylatkmc-gen: removed {out}")
    else:
        print(f"pylatkmc-gen: nothing to clean (no {out})")
    return 0


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pylatkmc-gen",
        description="pylatkmc code generator: spec.kmcspec.toml -> generated/proclist.{c,h}.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Render proclist.{c,h} into <spec_dir>/generated/")
    p_build.add_argument("spec", help="Path to .kmcspec.toml")
    p_build.set_defaults(func=cmd_build)

    p_info = sub.add_parser("info", help="Print spec shape without generating anything")
    p_info.add_argument("spec", help="Path to .kmcspec.toml")
    p_info.set_defaults(func=cmd_info)

    p_proc = sub.add_parser(
        "processes",
        help="Translate the curated catalogue into pattern-DB Processes and print a summary",
    )
    p_proc.add_argument("spec", help="Path to .kmcspec.toml")
    p_proc.add_argument(
        "--family-csv",
        default=None,
        help="Path to rate_lookup_table_family.csv (default: spec's rate_data.family_table)",
    )
    p_proc.set_defaults(func=cmd_processes)

    p_clean = sub.add_parser("clean", help="Remove <spec_dir>/generated/")
    p_clean.add_argument("spec", help="Path to .kmcspec.toml")
    p_clean.set_defaults(func=cmd_clean)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
