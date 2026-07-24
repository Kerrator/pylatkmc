"""CLI for the pylatkmc ingest bridge: ``recover``, ``build``, ``qc``, ``graduate``, ``merge``.

``recover`` — trajectory-recovery HTST: per-family Vineyard ν₀ from real events::

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

``build`` — the installed reference-table pipeline (robust frame fit, pinned
identity scale; memo 2026-07-22): project every row of a pyKMC
``reference_table.pickle``, run the gates, assemble the ``EventClass`` catalogue::

    python -m pylatkmc.ingest.cli build \
        --reftable .../reference_table.pickle \
        --out      catalogue_raw.parquet \
        --rcut 8.5 --t-ref 500 --coloring full \
        --conditions "production NiCr verify_fix_T500_1vac, rcut 8.5 A"

``qc`` — ingest quality-control screens over an ``EventClass`` Parquet catalogue
(reciprocity, delta-less, within-class dE-spread quarantine, human-veto overlay),
re-emitting a schema-v2 QC'd catalogue. With ``--measured-refs`` it additionally
stamps each surviving class's ν₀ rate policy (memo §3.2–3.3): classes carrying a
previously-measured member fire harvested pairs; recovered classes are stamped
``pending_research`` (excluded from measured procs until graduation)::

    python -m pylatkmc.ingest.cli qc \
        --in  catalogue_raw.parquet \
        --out catalogue_qc.parquet \
        --tol 1e-6 --spread-tol 0.1 \
        --overlay vetoes.toml \
        --measured-refs measured_refs.csv \
        --conditions "production NiCr verify_fix_T500_1vac ingest, rcut 8.5 A"

``graduate`` — the re-search agreement gate (memo §3.4): fold in-situ re-search
barriers back onto ``pending_research`` classes; within the band the class
graduates to measured (harvested pairs fire), above it the class is marked
context-suspect and written to the review list::

    python -m pylatkmc.ingest.cli graduate \
        --in catalogue_qc.parquet \
        --research research_results.csv \
        --out catalogue_graduated.parquet \
        --review graduation_review.csv \
        --band 0.05

``merge`` — class-level union of many per-run QC'd catalogues into one catalogue,
keyed on the content-based ``class_id`` (portable across runs). Never concatenate raw
reference tables (``idx_ref`` is run-local); merge unions **built + QC'd** per-run
catalogues, re-runs the QC screens on the merged member lists (statuses are re-decided,
not unioned), applies the class_id-keyed veto overlay, and stamps the measured ν0
policy from a reference catalogue's ``harvested_pair`` class_id set::

    python -m pylatkmc.ingest.cli merge \
        --in NiCr_T300_1vac=T300_1vac_qc.parquet \
        --in NiCr_T500_10vac=T500_10vac_qc.parquet \
        --out sweep_catalogue.parquet \
        --tol 1e-6 --spread-tol 0.1 \
        --overlay vetoes_migrated.toml \
        --measured-catalogue catalogue_v3_graduated.parquet \
        --measured-catalogue catalogue_v3_qc_veto_stamped.parquet \
        --conditions "NiCr sweep 29 runs"
"""

from __future__ import annotations

import argparse
import csv
import datetime
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pylatkmc.ingest", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("recover", help="recover per-family ν₀ from trajectories")
    r.add_argument("--rate-table", required=True, help="rate_lookup_table_family.csv")
    r.add_argument("--classified", required=True, help="classified_events_with_families.csv")
    r.add_argument(
        "--potential",
        default="auto",
        help="EAM potential path, or 'auto' (default) to resolve per-sim from input.in",
    )
    r.add_argument("--T", type=float, default=500.0, help="temperature K (provenance only)")
    r.add_argument("--out-bucket", required=True, help="per-bucket ν₀ CSV (upserted)")
    r.add_argument("--out-family", default=None, help="rolled-up per-family ν₀ CSV (upserted)")
    r.add_argument("--out-geometry", default=None, help="per-geometry audit CSV")
    r.add_argument("--families", default=None, help="comma-separated family_ids (default: all)")
    r.add_argument("--per-bucket", type=int, default=None, help="cap representatives per bucket")
    r.add_argument("--free-radius", type=float, default=6.0, help="Hessian free-atom radius (Å)")
    r.add_argument("--dx", type=float, default=0.01, help="finite-difference step (Å)")
    r.add_argument(
        "--no-verify", action="store_true", help="skip trajectory firing-step verification"
    )

    b = sub.add_parser("build", help="build an EventClass catalogue from a reference table")
    b.add_argument("--reftable", required=True, help="pyKMC reference_table.pickle")
    b.add_argument("--out", required=True, help="output EventClass Parquet catalogue")
    b.add_argument(
        "--rcut",
        type=float,
        required=True,
        help="the pyKMC run's rcut (Å); also sets the G7 gate — a smaller "
        "value fails G7 wholesale (see GateThresholds.rcut)",
    )
    b.add_argument(
        "--coloring",
        choices=("full", "grey"),
        default="full",
        help="species coloring (default full)",
    )
    b.add_argument("--t-ref", type=float, default=500.0, help="reference temperature K")
    b.add_argument("--snap-tol", type=float, default=0.9, help="G3 snap tolerance (Å)")
    b.add_argument("--d-max", type=int, default=3, help="depth-signature cap (layers)")
    b.add_argument("--r-ctx-min", type=float, default=3.6, help="minimum context radius (Å)")
    b.add_argument(
        "--nominal-a",
        type=float,
        default=3.52,
        help="model lattice constant (Å); the identity scale h is pinned "
        "to nominal_a/2 (memo 2026-07-22 §3.1)",
    )
    b.add_argument("--emin", type=float, default=0.0, help="G1 lower barrier bound (eV)")
    b.add_argument("--emax", type=float, default=10.0, help="G1 upper barrier bound (eV)")
    b.add_argument(
        "--backward-emin",
        type=float,
        default=0.0,
        help="G1 lower bound for the backward barrier (eV)",
    )
    b.add_argument("--db-tol", type=float, default=0.05, help="G2 detailed-balance tol")
    b.add_argument(
        "--nu0-fallback-hz",
        type=float,
        default=1.0e12,
        help="prefactor fallback (Hz) for members without a usable ν₀",
    )
    b.add_argument(
        "--conditions",
        default="",
        help="free-text upstream conditions stamp for the output file metadata",
    )

    q = sub.add_parser("qc", help="run ingest QC screens over an EventClass Parquet catalogue")
    q.add_argument("--in", dest="in_path", required=True, help="input EventClass Parquet catalogue")
    q.add_argument("--out", dest="out_path", required=True, help="output QC'd (schema-v2) Parquet")
    q.add_argument("--tol", type=float, default=1e-6, help="reciprocity |dE_f+dE_b| tol (eV)")
    q.add_argument(
        "--spread-tol",
        type=float,
        default=0.1,
        help="within-class dE_pair spread quarantine tol (eV; memo §3.5)",
    )
    q.add_argument(
        "--overlay", default=None, help="human-veto overlay file (TOML/JSON: class_id -> reason)"
    )
    q.add_argument(
        "--measured-refs",
        default=None,
        help="CSV of previously-measured event idx_refs (column 'idx_ref'); "
        "enables the §3.2–3.3 rate-policy stamp (measured -> "
        "harvested_pair, recovered -> pending_research)",
    )
    q.add_argument(
        "--pending-note",
        default="",
        help="extra provenance appended to each pending_research audit_reason",
    )
    q.add_argument(
        "--conditions",
        default="",
        help="free-text upstream conditions stamp for the output file metadata",
    )

    g = sub.add_parser("graduate", help="apply the re-search agreement gate (memo §3.4)")
    g.add_argument(
        "--in", dest="in_path", required=True, help="input stamped EventClass Parquet catalogue"
    )
    g.add_argument("--out", dest="out_path", required=True, help="output Parquet catalogue")
    g.add_argument(
        "--research", required=True, help="re-search results CSV (columns: class_id, Ea_eV)"
    )
    g.add_argument(
        "--band",
        type=float,
        default=0.05,
        help="agreement band |Ea_research - Ea_harvested| (eV, default 0.05)",
    )
    g.add_argument(
        "--review", default=None, help="context-suspect review-list CSV (default: alongside --out)"
    )

    m = sub.add_parser(
        "merge",
        help="class-level union of per-run QC'd catalogues (+ overlay + class_id stamp)",
    )
    m.add_argument(
        "--in",
        dest="inputs",
        action="append",
        default=[],
        metavar="RUN_TAG=PATH",
        help="a per-run QC'd Parquet catalogue tagged with its run id "
        "(repeatable; RUN_TAG=/path/to/qc.parquet). NEVER concatenate raw reference "
        "tables — idx_ref is run-local; merge unions built+QC'd catalogues on class_id",
    )
    m.add_argument(
        "--manifest",
        default=None,
        help="alternative to repeated --in: a CSV with columns run_tag,parquet",
    )
    m.add_argument("--out", dest="out_path", required=True, help="merged EventClass Parquet")
    m.add_argument("--tol", type=float, default=1e-6, help="reciprocity |dE_f+dE_b| tol (eV)")
    m.add_argument(
        "--spread-tol", type=float, default=0.1, help="within-class dE_pair spread quarantine (eV)"
    )
    m.add_argument("--overlay", default=None, help="class_id-keyed human-veto overlay (TOML/JSON)")
    m.add_argument(
        "--measured-catalogue",
        dest="measured_catalogues",
        action="append",
        default=[],
        metavar="PATH",
        help="stamped/graduated reference catalogue Parquet; the measured class_id set "
        "is its nu0_pair_policy=='harvested_pair' classes. Repeatable: the FIRST "
        "readable path is used (graduated first, stamped as fallback)",
    )
    m.add_argument(
        "--pending-note",
        default="",
        help="extra provenance appended to each pending_research audit_reason",
    )
    m.add_argument(
        "--conditions",
        default="",
        help="free-text upstream conditions stamp for the output file metadata",
    )
    return p


def _run_recover(args: argparse.Namespace) -> int:
    from .trajectory_recovery import resolve_targets, run_buckets, write_outputs

    families = [f.strip() for f in args.families.split(",")] if args.families else None
    targets = resolve_targets(
        args.rate_table, args.classified, families=families, per_bucket=args.per_bucket
    )
    if not targets:
        print("no targets resolved (check --families / rate table)", file=sys.stderr)
        return 1
    print(
        f"resolved {len(targets)} representative events across "
        f"{len({(t.family_id, t.family_bucket_id) for t in targets})} buckets"
    )

    buckets, geoms = run_buckets(
        targets,
        args.potential,
        T_K=args.T,
        free_radius=args.free_radius,
        dx=args.dx,
        verify_trajectory=not args.no_verify,
    )
    write_outputs(buckets, geoms, args.out_bucket, args.out_family, args.out_geometry)

    n_ok = sum(g.ok for g in geoms)
    n_fam = sum(1 for b in buckets if b.n_accepted > 0)
    print(
        f"\ndone: {n_ok}/{len(geoms)} geometries accepted; {n_fam}/{len(buckets)} buckets got a ν₀."
    )
    print(f"  per-bucket -> {args.out_bucket}")
    if args.out_family:
        print(f"  per-family -> {args.out_family}")
    return 0


def _run_build(args: argparse.Namespace) -> int:
    from .event_class import Coloring, GateThresholds, write_catalogue_parquet
    from .reftable import ReftableBuildReport, build_catalogue_from_reference_table

    thresholds = GateThresholds(
        emin_event=args.emin,
        emax_event=args.emax,
        backward_emin_event=args.backward_emin,
        snap_tol=args.snap_tol,
        db_tol=args.db_tol,
        rcut=args.rcut,
    )
    rep = ReftableBuildReport()
    classes = build_catalogue_from_reference_table(
        args.reftable,
        coloring=Coloring.FULL if args.coloring == "full" else Coloring.GREY,
        rcut=args.rcut,
        thresholds=thresholds,
        t_ref_K=args.t_ref,
        d_max=args.d_max,
        r_ctx_min=args.r_ctx_min,
        nominal_a=args.nominal_a,
        nu0_fallback_hz=args.nu0_fallback_hz,
        report=rep,
    )

    stamp = (
        f"{args.conditions.strip()} | build: rcut={args.rcut:g} snap_tol={args.snap_tol:g} "
        f"d_max={args.d_max} r_ctx_min={args.r_ctx_min:g} T_ref={args.t_ref:g} "
        f"coloring={args.coloring} nominal_a={args.nominal_a:g} "
        f"emin={args.emin:g} emax={args.emax:g} "
        f"| rows={rep.n_rows} projected={rep.n_projected} "
        f"frame_unfit={rep.n_frame_unfit} failures={len(rep.failures)} "
        f"classes={rep.catalogue.n_classes} "
        f"| robust-frame-fit pinned-h (memo 2026-07-22) "
        f"date={datetime.date.today().isoformat()}"
    ).strip(" |")
    write_catalogue_parquet(
        classes,
        args.out,
        metadata={b"pylatkmc.build.conditions": stamp.encode("utf-8")},
    )

    print(
        f"projected {rep.n_projected}/{rep.n_rows} rows "
        f"({rep.n_frame_unfit} FRAME_UNFIT, {len(rep.failures)} failures)"
    )
    for i, msg in rep.failures:
        print(f"    row {i}: {msg}")
    print(
        f"catalogue: {rep.catalogue.n_classes} classes / "
        f"{rep.catalogue.n_events} events; g7_fail {rep.catalogue.n_g7_fail}"
    )
    if rep.catalogue.rcut_mismatch_suspected:
        print(f"WARNING: {rep.catalogue.rcut_mismatch_message}")
    print(f"  wrote {args.out}")
    print(f"  metadata[pylatkmc.build.conditions] = {stamp}")
    return 1 if rep.failures else 0


def _read_measured_refs(path: str) -> frozenset[int]:
    """Read the previously-measured event idx_refs (column ``idx_ref``)."""
    refs: set[int] = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "idx_ref" not in reader.fieldnames:
            raise ValueError(f"--measured-refs {path}: need a CSV with an 'idx_ref' column")
        for row in reader:
            cell = (row.get("idx_ref") or "").strip()
            if cell:
                refs.add(int(float(cell)))
    return frozenset(refs)


def _run_qc(args: argparse.Namespace) -> int:
    from .event_class import read_catalogue_parquet, write_catalogue_parquet
    from .qc import apply_qc, load_overlay, stamp_rate_policy

    overlay = load_overlay(args.overlay) if args.overlay else None
    classes = read_catalogue_parquet(args.in_path)
    report = apply_qc(classes, tol=args.tol, spread_tol=args.spread_tol, overlay=overlay)
    out_classes = report.classes

    srep = None
    stamp_note = ""
    if args.measured_refs:
        srep = stamp_rate_policy(
            out_classes,
            measured_idx_refs=_read_measured_refs(args.measured_refs),
            pending_note=args.pending_note,
        )
        out_classes = srep.classes
        stamp_note = (
            f" | stamp: measured={srep.n_measured} pending={srep.n_pending_research} "
            f"nonrepresentable={srep.n_unstamped_nonrepresentable}"
        )

    stamp = (
        f"{args.conditions.strip()} | QC: tol={args.tol:g} spread_tol={args.spread_tol:g} "
        f"overlay={args.overlay or 'none'} | classes_in={report.n_input} "
        f"quarantined={report.total_quarantined} events={report.total_quarantined_events}"
        f"{stamp_note} "
        f"| schema_version=2 date={datetime.date.today().isoformat()}"
    ).strip(" |")
    metadata = {b"pylatkmc.qc.conditions": stamp.encode("utf-8")}
    write_catalogue_parquet(out_classes, args.out_path, metadata=metadata)

    print(report.summary())
    if srep is not None:
        print(srep.summary())
    print(f"  wrote {args.out_path}")
    print(f"  metadata[pylatkmc.qc.conditions] = {stamp}")
    return 0


def _read_research_csv(path: str) -> dict[str, float]:
    """Read re-search results: ``class_id -> Ea_eV`` (strict two-column contract)."""
    out: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames or []
        if "class_id" not in names or "Ea_eV" not in names:
            raise ValueError(
                f"--research {path}: need CSV columns 'class_id' and 'Ea_eV', got {names}"
            )
        for row in reader:
            cid = (row.get("class_id") or "").strip()
            cell = (row.get("Ea_eV") or "").strip()
            if cid and cell:
                out[cid] = float(cell)
    return out


def _run_graduate(args: argparse.Namespace) -> int:
    from .event_class import read_catalogue_parquet, write_catalogue_parquet
    from .qc import graduate_classes

    research = _read_research_csv(args.research)
    classes = read_catalogue_parquet(args.in_path)
    report = graduate_classes(classes, research_ea_by_class=research, band_eV=args.band)

    stamp = (
        f"graduate: research={Path(args.research).name} band={args.band:g} eV "
        f"| pending_in={report.n_pending_in} graduated={report.n_graduated} "
        f"context_suspect={report.n_context_suspect} unresolved={report.n_unresolved} "
        f"| memo 2026-07-22 §3.4 date={datetime.date.today().isoformat()}"
    )
    write_catalogue_parquet(
        report.classes,
        args.out_path,
        metadata={b"pylatkmc.graduate.conditions": stamp.encode("utf-8")},
    )

    review_path = args.review or str(Path(args.out_path).with_suffix("")) + "_review.csv"
    fields = ["class_id", "Ea_research_eV", "Ea_harvested_eV", "abs_dev_eV", "band_eV", "n_events"]
    with open(review_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in report.review_rows:
            writer.writerow(row)

    print(report.summary())
    print(f"  wrote {args.out_path}")
    print(f"  review list -> {review_path} ({len(report.review_rows)} rows)")
    print(f"  metadata[pylatkmc.graduate.conditions] = {stamp}")
    return 0


def _read_merge_inputs(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Resolve ``(run_tag, parquet_path)`` pairs from ``--in`` and/or ``--manifest``."""
    pairs: list[tuple[str, str]] = []
    for spec in args.inputs:
        if "=" not in spec:
            raise ValueError(f"--in expects RUN_TAG=PATH, got {spec!r}")
        tag, path = spec.split("=", 1)
        tag, path = tag.strip(), path.strip()
        if not tag or not path:
            raise ValueError(f"--in expects a non-empty RUN_TAG=PATH, got {spec!r}")
        pairs.append((tag, path))
    if args.manifest:
        with open(args.manifest, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            names = reader.fieldnames or []
            if "run_tag" not in names or "parquet" not in names:
                raise ValueError(
                    f"--manifest {args.manifest}: need columns 'run_tag' and 'parquet', got {names}"
                )
            for row in reader:
                tag = (row.get("run_tag") or "").strip()
                path = (row.get("parquet") or "").strip()
                if tag and path:
                    pairs.append((tag, path))
    if not pairs:
        raise ValueError("merge needs at least one input (--in RUN_TAG=PATH or --manifest CSV)")
    return pairs


def _resolve_measured_class_ids(paths: list[str]) -> tuple[frozenset[str], str | None]:
    """Measured (``harvested_pair``) class_ids from the first readable reference catalogue."""
    from .event_class import read_catalogue_parquet
    from .merge import measured_class_ids_from_catalogue

    for path in paths:
        if not Path(path).exists():
            continue
        classes = read_catalogue_parquet(path)
        return measured_class_ids_from_catalogue(classes), path
    return frozenset(), None


def _run_merge(args: argparse.Namespace) -> int:
    from .event_class import read_catalogue_parquet, write_catalogue_parquet
    from .merge import merge_qcd_catalogues
    from .qc import load_overlay

    pairs = _read_merge_inputs(args)
    overlay = load_overlay(args.overlay) if args.overlay else None
    measured, measured_src = _resolve_measured_class_ids(args.measured_catalogues)

    per_run: list[tuple[str, list]] = []
    for tag, path in sorted(pairs):
        per_run.append((tag, read_catalogue_parquet(path)))
        print(f"  loaded {tag}: {len(per_run[-1][1])} classes  <- {path}")

    report = merge_qcd_catalogues(
        per_run,
        tol=args.tol,
        spread_tol=args.spread_tol,
        overlay=overlay,
        measured_class_ids=measured,
        pending_note=args.pending_note,
    )

    stamp_note = ""
    if report.stamp is not None:
        stamp_note = (
            f" | stamp(class_id): measured={report.stamp.n_measured} "
            f"pending={report.stamp.n_pending_research} "
            f"nonrepresentable={report.stamp.n_unstamped_nonrepresentable} "
            f"measured_src={Path(measured_src).name if measured_src else 'none'}"
        )
    stamp = (
        f"{args.conditions.strip()} | MERGE: runs={report.n_runs} "
        f"instances={report.n_input_class_instances} classes={report.n_merged_classes} "
        f"tol={args.tol:g} spread_tol={args.spread_tol:g} overlay={args.overlay or 'none'} "
        f"quarantined={report.qc.total_quarantined} "
        f"status_conflicts={report.status_conflict_count} "
        f"nonconserving_surviving={report.nonconserving_surviving}"
        f"{stamp_note} "
        f"| schema_version=2 date={datetime.date.today().isoformat()}"
    ).strip(" |")
    write_catalogue_parquet(
        report.classes,
        args.out_path,
        metadata={b"pylatkmc.merge.conditions": stamp.encode("utf-8")},
    )

    print(report.summary())
    print(report.qc.summary())
    if report.stamp is not None:
        print(report.stamp.summary())
    print(f"  wrote {args.out_path}")
    print(f"  metadata[pylatkmc.merge.conditions] = {stamp}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "recover":
        return _run_recover(args)
    if args.cmd == "build":
        return _run_build(args)
    if args.cmd == "qc":
        return _run_qc(args)
    if args.cmd == "graduate":
        return _run_graduate(args)
    if args.cmd == "merge":
        return _run_merge(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
