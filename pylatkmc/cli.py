"""Command-line entry point for pylatkmc.

Exposed as `pylatkmc-gen` via the pyproject.toml [project.scripts] table.

Usage:
    pylatkmc-gen build <spec.kmcspec.toml>        # render C files into generated/
    pylatkmc-gen info  <spec.kmcspec.toml>        # print axes / cube size / paths
    pylatkmc-gen clean <spec.kmcspec.toml>        # rm -rf generated/
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import struct

import numpy as np

from pylatkmc import load
from pylatkmc.codegen import generate
from pylatkmc.kmcfmt import RATETABLE_MAGIC, read_header
from pylatkmc.ratebuilder import CLASS_MAP, DIR_MAP
from pylatkmc.ratebuilder import build as build_rate_table
from pylatkmc.spec import ModelSpec


def _resolve_generated_dir(spec_path: Path) -> Path:
    """Canonical layout: <model_dir>/<model_name>.kmcspec.toml →
    <model_dir>/generated/"""
    return spec_path.parent / "generated"


def cmd_build(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    out = _resolve_generated_dir(spec_path)
    written = generate(spec, out)
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
    print(f"n_cube_entries:  {spec.n_cube_entries():,}")
    print(f"T / k0:          {spec.rate_data.temperature_K} K, {spec.rate_data.k0_Hz:.2e} Hz")
    print("axes:")
    for (name, max_bin), stride in zip(spec.all_axes(), spec.strides(), strict=True):
        print(f"  {name:20s} max={max_bin:2d}  stride={stride}")
    return 0


def cmd_rate(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    out_path = (
        Path(args.out).resolve() if args.out
        else spec_path.parent / "examples" / f"{spec.name}.kmcrt"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats = build_rate_table(
        spec,
        classified_csv=spec.rate_data.primary,
        out_path=out_path,
        scalar_csv=spec.rate_data.fallback_scalar,
        family_csv=spec.rate_data.family_table,
        verbose=True,
    )
    print(f"pylatkmc-gen: wrote {out_path}")
    print(f"  coverage: {stats.as_dict()['pct_filled']:.1f}% "
          f"(tier-1 {stats.as_dict()['pct_tier1']:.1f}%)")
    return 0


def cmd_provenance(args: argparse.Namespace) -> int:
    """Coverage report for a built .kmcrt: which (site_class, direction) slabs
    are populated, which still have zeros, and the min/mean/max rate per slab."""
    spec_path = Path(args.spec).resolve()
    spec = load(spec_path)
    kmcrt_path = (
        Path(args.kmcrt).resolve() if args.kmcrt
        else spec_path.parent / "examples" / f"{spec.name}.kmcrt"
    )
    if not kmcrt_path.is_file():
        print(f"pylatkmc-gen: no .kmcrt at {kmcrt_path} (run `pylatkmc-gen rate` first)")
        return 1

    with open(kmcrt_path, "rb") as fp:
        header = read_header(fp, RATETABLE_MAGIC)
        (n_entries,) = struct.unpack("<I", fp.read(4))
        rate = np.frombuffer(fp.read(4 * n_entries), dtype="<f4").copy()
        Ea = np.frombuffer(fp.read(4 * n_entries), dtype="<f4").copy()
        count = np.frombuffer(fp.read(4 * n_entries), dtype="<u4").copy()

    axis_maxes = header["axis_maxes"]
    rate_cube = rate.reshape(axis_maxes)
    Ea_cube = Ea.reshape(axis_maxes)
    count_cube = count.reshape(axis_maxes)

    # Names for the per-slab table.
    sc_names = {v: k for k, v in CLASS_MAP.items()}
    dir_names = {v: k for k, v in DIR_MAP.items()}

    print(f"provenance report for {kmcrt_path.name}")
    print(f"  spec: {spec.name} ({len(axis_maxes)} axes, {n_entries:,} entries)")
    print(f"  T={header['temperature_K']} K, k0={header['k0_Hz']:.2e} Hz")
    print()
    total_nonzero = int((rate_cube > 0).sum())
    total_tier1 = int((count_cube > 0).sum())
    print(f"  overall: {total_nonzero:,} / {n_entries:,} cells non-zero "
          f"({100*total_nonzero/n_entries:.1f}%)")
    print(f"  tier-1 direct: {total_tier1:,} cells ({100*total_tier1/n_entries:.2f}%)")
    print()

    header_fmt = (
        f"  {'site_class':<11} {'direction':<18} "
        f"{'coverage':>11} {'tier1':>8} "
        f"{'rate_max':>12} {'rate_mean_nz':>14} {'Ea_mean_nz':>11}"
    )
    print(header_fmt)
    print("  " + "-" * (len(header_fmt) - 2))
    for sc_i in range(axis_maxes[0]):
        for dir_i in range(axis_maxes[1]):
            slab_rate = rate_cube[sc_i, dir_i]
            slab_Ea = Ea_cube[sc_i, dir_i]
            slab_count = count_cube[sc_i, dir_i]
            nz = slab_rate > 0
            n_nz = int(nz.sum())
            n_t1 = int((slab_count > 0).sum())
            pct = 100.0 * n_nz / slab_rate.size
            rate_max = float(slab_rate.max()) if n_nz else 0.0
            rate_mean = float(slab_rate[nz].mean()) if n_nz else 0.0
            Ea_mean = float(slab_Ea[nz].mean()) if n_nz else 0.0
            print(
                f"  {sc_names.get(sc_i, '?'):<11} {dir_names.get(dir_i, '?'):<18} "
                f"{pct:>9.1f}% {n_t1:>8d} "
                f"{rate_max:>12.3e} {rate_mean:>14.3e} {Ea_mean:>11.3f}"
            )
    return 0


def cmd_processes(args: argparse.Namespace) -> int:
    """Translate a curated catalogue into pattern-DB Processes and print a summary.

    M-A.7 of the v2 redesign. Replaces `provenance` (which was tied to
    the rate-cube format). Reports per-family Process counts, total
    Process count, Ea range, and any wide-Ea-scatter or
    unknown-family warnings.

    The Processes themselves are NOT written to disk by this command
    (that's `build` in v2). This is a read-only inspection tool.
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
        print(f"pylatkmc-gen processes: family rate table not found: {family_csv}",
              file=sys.stderr)
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
    print(f"Processes per family:")
    for fid, n in sorted(fam_proc_counts.items()):
        print(f"  {fid:42s} {n:>5} Processes")

    if processes:
        ea = [p.Ea_eV for p in processes]
        print(f"\nEa_eV range: min={min(ea):.3f}  max={max(ea):.3f}")

    if unknown_families:
        print(f"\n⚠ Unknown families in catalogue (skipped):")
        for f in sorted(set(unknown_families)):
            print(f"  {f}")

    if scatter_warnings:
        print(f"\n⚠ {len(scatter_warnings)} wide-Ea-scatter buckets "
              f"(per-bucket-mean rate may be unreliable):")
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
        description="pylatkmc code generator: spec.kmcspec.toml -> C source + rate table.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Render C source files to <spec_dir>/generated/")
    p_build.add_argument("spec", help="Path to .kmcspec.toml")
    p_build.set_defaults(func=cmd_build)

    p_info = sub.add_parser("info", help="Print spec shape without generating anything")
    p_info.add_argument("spec", help="Path to .kmcspec.toml")
    p_info.set_defaults(func=cmd_info)

    p_rate = sub.add_parser("rate", help="Build the .kmcrt rate table from the curated CSV")
    p_rate.add_argument("spec", help="Path to .kmcspec.toml")
    p_rate.add_argument("-o", "--out", default=None,
                        help="Output .kmcrt path (default: <model_dir>/examples/<name>.kmcrt)")
    p_rate.set_defaults(func=cmd_rate)

    p_prov = sub.add_parser("provenance",
                            help="Per-(site_class, direction) coverage report for a built .kmcrt")
    p_prov.add_argument("spec", help="Path to .kmcspec.toml")
    p_prov.add_argument("-k", "--kmcrt", default=None,
                        help="Path to .kmcrt (default: <model_dir>/examples/<name>.kmcrt)")
    p_prov.set_defaults(func=cmd_provenance)

    p_proc = sub.add_parser(
        "processes",
        help="Translate the curated catalogue into pattern-DB Processes and print a summary",
    )
    p_proc.add_argument("spec", help="Path to .kmcspec.toml")
    p_proc.add_argument("--family-csv", default=None,
                        help="Path to rate_lookup_table_family.csv "
                             "(default: spec's rate_data.family_table)")
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
