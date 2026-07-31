"""CLI for the pylatkmc ingest bridge: ``recover``, ``build``, ``qc``, ``graduate``, ``merge``, ``remap``.

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
identity scale; memo 2026-07-22 + over-snapping memo 2026-07-29): project every
row of a pyKMC ``reference_table.pickle``, enforce the mover-keyed G3 as a
build-time drop (``FRAME_UNFIT`` / ``MOVER_OFFLATTICE`` rows go to the sidecar
ledger ``<out>_discarded.parquet``, never into a class), mask ≥0.5 Å static
bystanders to ``WILDCARD``, run the gates, assemble the ``EventClass``
catalogue::

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

``remap`` — lineage stamp remap across a CANON schema bump (over-snapping memo
2026-07-29 §8.3). A bump relabels every ``class_id``, so measured/graduated
stamps, veto overlays, and review lists carry across by event lineage: rebuild
the stamp-source reference table under the new policy (an ordinary ``build``),
then transfer each old class's ``nu0_pair_policy`` onto the new classes its
members landed in. Every old class is accounted for in the report (remapped, or
unmatched with a reason — e.g. all members in the discard ledger)::

    python -m pylatkmc.ingest.cli remap \
        --old catalogue_v3_graduated.parquet \
        --new catalogue_v4_raw.parquet \
        --out catalogue_v4_stamped_remap.parquet \
        --report remap_report.csv \
        --overlay-in vetoes_migrated.toml --overlay-out vetoes_v2.toml \
        --review-in review_list.csv --review-out review_list_v2.csv \
        --note "CANON v2 migration 2026-07-29"
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
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
    b.add_argument(
        "--mover-snap-tol",
        type=float,
        default=0.5,
        help="G3 mover-keyed off-lattice threshold (Å; memo 2026-07-29 §4) — a row "
        "whose mover snap residual reaches it is dropped to the discard ledger",
    )
    b.add_argument(
        "--bystander-mask-tol",
        type=float,
        default=0.5,
        help="static-bystander context mask threshold (Å; memo 2026-07-29 §6) — a "
        "non-mover whose snap residual reaches it has its context row demoted "
        "to WILDCARD before canonicalisation",
    )
    b.add_argument(
        "--snap-tol",
        type=float,
        default=None,
        help="RETIRED (memo 2026-07-29 §4): no gate reads it. Accepted one release "
        "for script compatibility; recorded in the conditions stamp only — use "
        "--mover-snap-tol / --bystander-mask-tol instead",
    )
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
        "--review",
        default=None,
        help="STANDING action-review list CSV to APPEND linked-pair action_id "
        "mismatches to (memo 2026-07-30 ruling 9; default: <out>_action_review.csv). "
        "Flag + review only — mismatching classes keep firing on measured rates",
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
        "--review",
        default=None,
        help="STANDING action-review list CSV to APPEND linked-pair action_id "
        "mismatches to (memo 2026-07-30 ruling 9; default: <out>_action_review.csv). "
        "Corpus-level mismatches materialise HERE, not per-run: a pair's two "
        "directions can arrive from different runs",
    )
    m.add_argument(
        "--conditions",
        default="",
        help="free-text upstream conditions stamp for the output file metadata",
    )

    r2 = sub.add_parser(
        "remap",
        help="lineage stamp remap across a CANON schema bump (memo 2026-07-29 §8.3)",
    )
    r2.add_argument(
        "--old",
        dest="old_path",
        required=True,
        help="old stamped/graduated EventClass Parquet (pre-bump class_ids)",
    )
    r2.add_argument(
        "--new",
        dest="new_path",
        required=True,
        help="new-policy EventClass Parquet built from the SAME reference table "
        "(its discard ledger sidecar <new>_discarded.parquet is read too)",
    )
    r2.add_argument(
        "--out",
        dest="out_path",
        required=True,
        help="stamped copy of --new (nu0_pair_policy transferred by lineage)",
    )
    r2.add_argument(
        "--report",
        dest="report_path",
        required=True,
        help="CSV accounting for EVERY old class (remapped / unmatched + reason)",
    )
    r2.add_argument(
        "--overlay-in",
        default=None,
        help="old-id-keyed veto overlay (TOML/JSON) to remap through the same lineage",
    )
    r2.add_argument(
        "--overlay-out",
        default=None,
        help="output path for the remapped (new-id-keyed) veto overlay TOML",
    )
    r2.add_argument(
        "--review-in",
        default=None,
        help="review-list CSV with a class_id column to remap (rows kept verbatim; "
        "adds class_id_v2 + remap_outcome columns)",
    )
    r2.add_argument(
        "--review-out",
        default=None,
        help="output path for the remapped review-list CSV",
    )
    r2.add_argument(
        "--note",
        default="",
        help="short provenance note recorded in each transferred stamp",
    )
    r2.add_argument(
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
    from .action import IDENTITY_GROUP, action_census
    from .event_class import Coloring, GateThresholds, write_catalogue_parquet
    from .reftable import (
        ReftableBuildReport,
        build_catalogue_from_reference_table,
        discard_ledger_path,
        write_discard_ledger_parquet,
    )

    if args.snap_tol is not None:
        print(
            "WARNING: --snap-tol is retired (memo 2026-07-29 §4) and has no gate "
            "role; use --mover-snap-tol / --bystander-mask-tol",
            file=sys.stderr,
        )
    thresholds = GateThresholds(
        emin_event=args.emin,
        emax_event=args.emax,
        backward_emin_event=args.backward_emin,
        db_tol=args.db_tol,
        rcut=args.rcut,
        mover_snap_tol=args.mover_snap_tol,
        bystander_mask_tol=args.bystander_mask_tol,
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
        f"{args.conditions.strip()} | build: rcut={args.rcut:g} "
        f"mover_snap_tol={args.mover_snap_tol:g} "
        f"bystander_mask_tol={args.bystander_mask_tol:g} "
        f"d_max={args.d_max} r_ctx_min={args.r_ctx_min:g} T_ref={args.t_ref:g} "
        f"coloring={args.coloring} nominal_a={args.nominal_a:g} "
        f"identity_group={IDENTITY_GROUP} "
        f"emin={args.emin:g} emax={args.emax:g} "
        f"| rows={rep.n_rows} projected={rep.n_projected} "
        f"discarded={rep.n_discarded} (mover_offlattice={rep.n_mover_offlattice} "
        f"frame_unfit={rep.n_frame_unfit}) failures={len(rep.failures)} "
        f"classes={rep.catalogue.n_classes} "
        f"| mover-keyed G3 + discard ledger + bystander mask (memo 2026-07-29) "
        f"date={datetime.date.today().isoformat()}"
    ).strip(" |")
    write_catalogue_parquet(
        classes,
        args.out,
        metadata={b"pylatkmc.build.conditions": stamp.encode("utf-8")},
    )
    ledger_path = discard_ledger_path(args.out)
    write_discard_ledger_parquet(
        rep.discarded,
        ledger_path,
        metadata={b"pylatkmc.build.conditions": stamp.encode("utf-8")},
    )

    n_raised = len(rep.failures)
    print(
        f"projected {rep.n_projected}/{rep.n_rows} rows; discarded {rep.n_discarded} "
        f"({rep.n_mover_offlattice} MOVER_OFFLATTICE, {rep.n_frame_unfit} FRAME_UNFIT); "
        f"{n_raised} failures"
    )
    print(
        f"  conservation: rows={rep.n_rows} = projected={rep.n_projected} "
        f"+ raised={n_raised} + discarded={rep.n_discarded}"
        + (
            ""
            if rep.n_rows == rep.n_projected + n_raised + rep.n_discarded
            else "  ** VIOLATED — pipeline bug **"
        )
    )
    for i, msg in rep.failures:
        print(f"    row {i}: {msg}")
    print(
        f"catalogue: {rep.catalogue.n_classes} classes / "
        f"{rep.catalogue.n_events} events; g7_fail {rep.catalogue.n_g7_fail}"
    )
    print(action_census(classes).summary())
    print(
        f"  member action_id disagreement: {rep.catalogue.n_action_disagree} classes "
        "(stored arrows are the representative member's; monitor only)"
    )
    if rep.catalogue.rcut_mismatch_suspected:
        print(f"WARNING: {rep.catalogue.rcut_mismatch_message}")
    print(f"  wrote {args.out}")
    print(f"  discard ledger -> {ledger_path} ({rep.n_discarded} rows)")
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
    from .action import action_census
    from .event_class import (
        CATALOGUE_SCHEMA_VERSION,
        read_catalogue_parquet,
        write_catalogue_parquet,
    )
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
        f"| schema_version={CATALOGUE_SCHEMA_VERSION} date={datetime.date.today().isoformat()}"
    ).strip(" |")
    metadata = {b"pylatkmc.qc.conditions": stamp.encode("utf-8")}
    write_catalogue_parquet(out_classes, args.out_path, metadata=metadata)

    print(report.summary())
    if srep is not None:
        print(srep.summary())
    print(action_census(out_classes).summary())

    _append_action_review(args, report.action_review_rows)
    print(f"  wrote {args.out_path}")
    print(f"  metadata[pylatkmc.qc.conditions] = {stamp}")
    return 0


def _append_action_review(args: argparse.Namespace, rows: list[dict[str, object]]) -> None:
    """Log linked-pair action mismatches and append them to the standing review list.

    Ruling 9: a flag, a build-log line and a review row — never a quarantine, never a
    hard failure. Shared by ``qc`` and ``merge``; the merge case is the one that
    matters most, because a pair's two directions can arrive from different runs, so
    a corpus-level mismatch only ever materialises at merge time.
    """
    from .qc import append_action_review_rows

    if not rows:
        return
    review_path = args.review or str(Path(args.out_path).with_suffix("")) + "_action_review.csv"
    for row in rows:
        print(
            f"  ACTION_PAIR_MISMATCH: {str(row['class_id'])[:12]} <-> "
            f"{str(row['partner_class_id'])[:12]}  "
            f"action_id {row['action_id']} != {row['partner_action_id']}"
        )
    n_new = append_action_review_rows(review_path, rows)
    print(
        f"  review list: {len(rows)} pair(s) flagged, {n_new} new -> {review_path} "
        "(standing list, appended; duplicates skipped)"
    )


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
    from .action import action_census
    from .event_class import (
        CATALOGUE_SCHEMA_VERSION,
        read_catalogue_parquet,
        write_catalogue_parquet,
    )
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
        f"| schema_version={CATALOGUE_SCHEMA_VERSION} date={datetime.date.today().isoformat()}"
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
    print(action_census(report.classes).summary())
    _append_action_review(args, report.qc.action_review_rows)
    print(f"  wrote {args.out_path}")
    print(f"  metadata[pylatkmc.merge.conditions] = {stamp}")
    return 0


def _run_remap(args: argparse.Namespace) -> int:
    from .event_class import (
        CATALOGUE_SCHEMA_VERSION,
        read_catalogue_parquet,
        write_catalogue_parquet,
    )
    from .qc import load_overlay
    from .reftable import discard_ledger_path
    from .remap import apply_stamps, build_lineage, remap_classes, remap_payload

    old = read_catalogue_parquet(args.old_path)
    new = read_catalogue_parquet(args.new_path)
    ledger_path = discard_ledger_path(args.new_path)
    ledger_rows: list[dict] = []
    if ledger_path.is_file():
        import pyarrow.parquet as pq  # type: ignore[import-untyped]

        ledger_rows = pq.read_table(ledger_path).to_pylist()

    lineage = build_lineage(new, ledger_rows)
    report = remap_classes(old, lineage)
    stamped = apply_stamps(new, report, note=args.note)
    counts = report.counts()

    stamp = (
        f"{args.conditions.strip()} | REMAP (memo 2026-07-29 §8.3): "
        f"old={Path(args.old_path).name} new={Path(args.new_path).name} "
        + " ".join(f"{k}={v}" for k, v in counts.items())
        + f" join_conflicts={len(report.join_conflicts)}"
        f" | schema_version={CATALOGUE_SCHEMA_VERSION} date={datetime.date.today().isoformat()}"
    ).strip(" |")
    write_catalogue_parquet(
        stamped,
        args.out_path,
        metadata={b"pylatkmc.remap.conditions": stamp.encode("utf-8")},
    )

    with open(args.report_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "old_class_id",
                "old_policy",
                "old_audit_status",
                "n_members",
                "n_kept",
                "n_discarded",
                "n_missing",
                "outcome",
                "new_class_ids",
                "discard_reasons",
            ]
        )
        for cr in report.classes:
            n_disc = sum(1 for f in cr.fates if f.note and f.note != "MISSING")
            n_missing = sum(1 for f in cr.fates if f.note == "MISSING")
            w.writerow(
                [
                    cr.old_class_id,
                    cr.old_policy or "",
                    cr.old_audit_status,
                    len(cr.fates),
                    sum(1 for f in cr.fates if f.new_class_id is not None),
                    n_disc,
                    n_missing,
                    cr.outcome,
                    ";".join(cr.new_class_ids),
                    ";".join(cr.discard_reasons),
                ]
            )

    if args.overlay_in:
        if not args.overlay_out:
            print("--overlay-in requires --overlay-out", file=sys.stderr)
            return 2
        overlay = load_overlay(args.overlay_in)
        new_overlay, records = remap_payload(overlay, report, note=args.note)
        unmatched = [r for r in records if not r[2]]
        with open(args.overlay_out, "w") as fh:
            fh.write(
                "# Remapped veto overlay - CANON v2 migration (memo 2026-07-29 §8.3)\n"
                f"# Source: {args.overlay_in} ({len(overlay)} entries) -> "
                f"{len(new_overlay)} new-id entries; {len(unmatched)} unmatched "
                "(see remap report).\n"
                "# Apply via: python -m pylatkmc.ingest.cli qc/merge --overlay <this file>\n\n"
            )
            for nid, reason in sorted(new_overlay.items()):
                fh.write(f"{json.dumps(nid)} = {json.dumps(reason)}\n")
        for old_id, outcome, _ in unmatched:
            print(f"  overlay UNMATCHED: {old_id[:12]} ({outcome})")
        print(
            f"  overlay: {len(overlay)} old -> {len(new_overlay)} new entries "
            f"({len(unmatched)} unmatched) -> {args.overlay_out}"
        )

    if args.review_in:
        if not args.review_out:
            print("--review-in requires --review-out", file=sys.stderr)
            return 2
        by_old = {cr.old_class_id: cr for cr in report.classes}
        with open(args.review_in, newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        for row in rows:
            cr = by_old.get(row.get("class_id", ""))
            row["class_id_v2"] = ";".join(cr.new_class_ids) if cr else ""
            row["remap_outcome"] = cr.outcome if cr else "UNMATCHED_NOT_IN_OLD_CATALOGUE"
        with open(args.review_out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames + ["class_id_v2", "remap_outcome"])
            w.writeheader()
            w.writerows(rows)
        print(f"  review list: {len(rows)} rows -> {args.review_out}")

    print(
        "remap: "
        + " ".join(f"{k}={v}" for k, v in counts.items())
        + f" join_conflicts={len(report.join_conflicts)}"
    )
    for line in report.join_conflicts:
        print(f"  join conflict: {line}")
    unmatched_stamped = [cr for cr in report.classes if cr.old_policy and not cr.new_class_ids]
    for cr in unmatched_stamped:
        print(
            f"  stamped-class UNMATCHED: {cr.old_class_id[:12]} [{cr.old_policy}] "
            f"{cr.outcome} reasons={';'.join(cr.discard_reasons) or 'none'}"
        )
    print(f"  wrote {args.out_path}")
    print(f"  wrote {args.report_path}")
    print(f"  metadata[pylatkmc.remap.conditions] = {stamp}")
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
    if args.cmd == "remap":
        return _run_remap(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
