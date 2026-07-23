"""Pattern-table codegen — LatticePatterns → data-driven proclist.c (Phase B).

The v2 emission strategy (chosen after the Phase B sizing probe): the full-
context oriented patterns of the EventClass catalogue do NOT compile into the
v0.3 nested-switch ``touchup_a`` (439 classes × ~16 orientations × ~230
context predicates ≈ 1.6M switch conditions ≈ 0.5–1.9M generated lines).
Instead this module emits:

- **Packed static tables**: one canonical-frame row set per pattern
  (``V2DeltaRow`` / ``V2CtxRow``) plus the 16 D4h integer matrices; each
  oriented process is a ``(pattern, op)`` pair and the matcher rotates
  offsets on the fly, so the tables stay ~10² KB instead of ~10⁰ MB.
- **A generic matcher** (``v2_match`` + ``touchup_a``): screens on the
  anchor-site species (processes are sorted so each species' processes form
  one contiguous proc-id range), then verifies delta rows (exact before-
  state; the site must exist) and context rows (``EMPTY`` = vacant OR absent,
  ``OCC_ANY`` = any occupied) via ``lattice_site_at_ijk`` — the O(1) integer
  site grid added to the runtime for exactly this purpose. Reads through the
  stub site index ``n_sites`` are self-sentineling (``species[n_sites] ==
  255`` matches no exact species).
- **A generic apply** + one-line per-proc wrappers, because the runtime's
  ``pylatkmc_apply_table[proc](st, lat, site)`` call signature is frozen by
  committed v0.3 proclists.

The emitted ``proclist.h`` is byte-identical to the v0.3 one (same template):
``kmc.c`` / ``replica.c`` cannot tell the two strategies apart.

Determinism: patterns arrive sorted by ``class_id`` (translator contract);
processes are sorted by ``(anchor species code, pattern name, op index)``;
every table is emitted in that fixed order with fixed formatting.
"""

from __future__ import annotations

from pylatkmc.translator_v2 import LatticePattern, MemberRate, d4h_matrices

#: Predicate byte codes beyond the Species enum (events_base.h holds 0..3;
#: 255 is the stub sentinel). Values are part of the generated-C contract.
PRED_EMPTY = 250
PRED_OCC_ANY = 251

#: Per-proc channel tags (machine-readable provenance). Channel (a) measured
#: procs are always CHANNEL_MEASURED; the runtime surrogate channel (b) is
#: CHANNEL_SURROGATE and lives outside the proc table (never enrolled here).
CHANNEL_MEASURED = 0
CHANNEL_SURROGATE = 1

#: Species-name → runtime enum symbol. NAME-based on purpose: the ingest
#: ``Occ`` integers (CR=2, FE=3) disagree with the runtime ``Species``
#: integers (SP_FE=2, SP_CR=3); mapping by name is the only safe bridge.
_SP_SYMBOL = {
    "Vacant": "SP_VACANT",
    "Ni": "SP_NI",
    "Fe": "SP_FE",
    "Cr": "SP_CR",
}

#: Runtime integer code per species name (mirrors events_base.h; used only
#: for sorting processes into per-species buckets, never emitted directly).
_SP_CODE = {"Vacant": 0, "Ni": 1, "Fe": 2, "Cr": 3}


def _sp(name: str) -> str:
    """The runtime enum symbol for a species name (KeyError = unknown species)."""
    if name not in _SP_SYMBOL:
        raise ValueError(
            f"species {name!r} has no runtime enum symbol; the runtime Species "
            f"enum (events_base.h) knows {sorted(_SP_SYMBOL)} only"
        )
    return _SP_SYMBOL[name]


def _pred_symbol(kind: str, species: str | None) -> str:
    """The predicate byte for one context row, as a C expression."""
    if kind == "EMPTY":
        return "V2_PRED_EMPTY"
    if kind == "OCC_ANY":
        return "V2_PRED_OCC_ANY"
    if kind == "SPECIES":
        assert species is not None
        return _sp(species)
    raise ValueError(f"unknown context predicate kind {kind!r}")


def _chunk_lines(entries: list[str], per_line: int, indent: str = "    ") -> list[str]:
    """Join short initializer entries, ``per_line`` per emitted line."""
    return [
        indent + " ".join(entries[i : i + per_line])
        for i in range(0, len(entries), per_line)
    ]


def _vacancy_rows(pat: LatticePattern) -> tuple[int, int]:
    """(v_origin_row, v_dest_row) delta-row indices for MSD bookkeeping, or -1.

    Same semantics as the v0.3 per-process emitters: the vacancy origin is the
    unique row ``Vacant → occupied``; the destination is the unique row
    ``occupied → Vacant``. Ambiguity (multi-vacancy concerted) yields -1 and
    the runtime skips the MSD update with its one-time warning.
    """
    origin = [i for i, r in enumerate(pat.delta) if r.before == "Vacant" and r.after != "Vacant"]
    dest = [i for i, r in enumerate(pat.delta) if r.before != "Vacant" and r.after == "Vacant"]
    return (origin[0] if len(origin) == 1 else -1, dest[0] if len(dest) == 1 else -1)


def _members(pat: LatticePattern) -> tuple[MemberRate, ...]:
    """The pattern's rate channels; synthesize a single one from the scalar
    ``prefactor_Hz`` / ``Ea_eV`` if ``members`` is empty (defensive: a pattern
    built directly, not via the translator)."""
    if pat.members:
        return pat.members
    return (MemberRate(pat.prefactor_Hz, pat.Ea_eV, float("nan")),)


def n_procs_of(patterns: list[LatticePattern]) -> int:
    """Total oriented processes = Σ (orientation count × member count).

    Each ``(member, orientation)`` pair is one proc (§8-N6 raw-pairs); a
    singleton class is 1 member × its orientations, unchanged from the
    aggregate path.
    """
    return sum(len(p.orientation_ops) * len(_members(p)) for p in patterns)


def _order(patterns: list[LatticePattern]) -> list[int]:
    """Stable pattern order: (anchor species code, pattern name)."""
    return sorted(range(len(patterns)), key=lambda i: (
        _SP_CODE.get(patterns[i].anchor_species, 255),
        patterns[i].name,
    ))


def _proc_list(patterns: list[LatticePattern]) -> tuple[list[int], list[tuple[int, int, int, int]]]:
    """Deterministic (order, procs). ``procs`` entries are
    ``(table_idx, op, member_idx, pattern_idx)`` in emission order: patterns in
    ``_order``, then member-major, then orientation. Shared by the table, rate,
    and provenance emitters so all three stay index-aligned.
    """
    order = _order(patterns)
    procs: list[tuple[int, int, int, int]] = []
    for table_idx, pi in enumerate(order):
        pat = patterns[pi]
        for m in range(len(_members(pat))):
            for op in pat.orientation_ops:
                procs.append((table_idx, op, m, pi))
    return order, procs


def emit_v2_enum(patterns: list[LatticePattern]) -> str:
    """Emit ``enum { N_PROCS = <n> };`` — must precede the rate table."""
    return f"enum {{ N_PROCS = {n_procs_of(patterns)} }};\n"


def pattern_reach(patterns: list[LatticePattern]) -> tuple[int, int]:
    """Max in-plane / axial pattern reach in grid cells over all rows.

    Returns ``(reach_ij, reach_k)``: ``reach_ij`` bounds ``max(|di|, |dj|)``
    and ``reach_k`` bounds ``|dk|`` over every delta+context row of every
    pattern. Both are invariant under the D4h ops the matcher applies at
    runtime (the ops permute/negate the in-plane components and negate k),
    so they bound the *oriented* reach too. Exposed in the generated
    proclist.h so the runtime can refuse a configuration whose vacuum gap
    is thinner than the reach — the integer site grid wraps every axis, and
    a too-thin gap would alias offsets onto the far surface (silent wrong
    matches instead of the intended absent-site stub).
    """
    reach_ij = reach_k = 0
    for p in patterns:
        for r in (*p.delta, *p.context):
            reach_ij = max(reach_ij, abs(r.off[0]), abs(r.off[1]))
            reach_k = max(reach_k, abs(r.off[2]))
    return reach_ij, reach_k


def emit_pattern_tables(patterns: list[LatticePattern]) -> str:
    """Emit the packed pattern tables + generic matcher + apply machinery.

    Returns the C source fragment that replaces the v0.3 process enum /
    apply-function / decision-tree emission. The caller wraps it with the
    proclist.c preamble, the rate table, and the public-linkage glue.
    """
    if not patterns:
        return (
            "/* no patterns; v2 tables omitted */\n"
            "typedef struct { int v_origin; int v_dest; } HopOutcome;\n"
            "typedef HopOutcome (*ApplyFn)(State *st, const Lattice *lat, int site);\n"
            "static const ApplyFn apply_table[1] = { 0 };\n"
            "void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site)\n"
            "{ (void)lat; (void)st; (void)as; (void)site; }\n"
        )

    # ---- flatten rows + build the process list -------------------------
    # Processes sorted by (anchor species code, pattern name), then member-
    # major, then op, so each anchor species' processes are one contiguous
    # proc-id range (see _proc_list).
    order, procs = _proc_list(patterns)

    delta_rows: list[str] = []
    ctx_rows: list[str] = []
    pattern_defs: list[str] = []
    max_delta = 0

    for pi in order:
        pat = patterns[pi]
        d_begin, c_begin = len(delta_rows), len(ctx_rows)
        for r in pat.delta:
            delta_rows.append(
                f"{{{r.off[0]},{r.off[1]},{r.off[2]},{_sp(r.before)},{_sp(r.after)}}},"
            )
        for c in pat.context:
            ctx_rows.append(
                f"{{{c.off[0]},{c.off[1]},{c.off[2]},{_pred_symbol(c.kind, c.species)}}},"
            )
        max_delta = max(max_delta, len(pat.delta))
        v_origin, v_dest = _vacancy_rows(pat)
        pattern_defs.append(
            f"    {{{d_begin},{len(pat.delta)},{c_begin},{len(pat.context)},"
            f"{v_origin},{v_dest},{_sp(pat.anchor_species)},0}}, /* {pat.name} */"
        )

    n_procs = len(procs)

    # ---- per-species proc-id buckets -----------------------------------
    # v2_bucket_begin[sp] .. v2_bucket_begin[sp+1] is the proc-id range whose
    # anchor species code is sp. Species codes come from events_base.h.
    sp_of_proc = [
        _SP_CODE[patterns[pi].anchor_species] for (_t, _op, _m, pi) in procs
    ]
    n_sp = 4  # SP_COUNT in events_base.h
    bucket_begin = [0] * (n_sp + 1)
    for code in sp_of_proc:
        bucket_begin[code + 1] += 1
    for i in range(n_sp):
        bucket_begin[i + 1] += bucket_begin[i]

    # ---- D4h op matrices ----------------------------------------------
    mats = d4h_matrices()
    op_lines = [
        "    {" + ",".join(str(m[r][c]) for r in range(3) for c in range(3)) + "},"
        for m in mats
    ]

    _ = n_procs  # length of procs == N_PROCS; the enum is emitted by emit_v2_enum
    out: list[str] = []
    a = out.append
    a("/* ---- v2 data-driven pattern tables (EventClass catalogue) ----")
    a(" *")
    a(" * Each pattern stores its canonical-frame rows ONCE; each process is a")
    a(" * (pattern, D4h op) pair and the matcher rotates offsets on the fly.")
    a(" * Offsets are integer FCC cells (a/2 units) relative to the pattern")
    a(" * anchor, resolved through the runtime's integer site grid")
    a(" * (lattice_site_at_ijk). Absent sites resolve to the stub index")
    a(" * n_sites, where species[] holds the 255 sentinel. */")
    a(f"#define V2_PRED_EMPTY   {PRED_EMPTY}u  /* vacant OR absent site */")
    a(f"#define V2_PRED_OCC_ANY {PRED_OCC_ANY}u  /* any occupied species */")
    a(f"#define V2_MAX_DELTA    {max_delta}")
    a("")
    a("typedef struct { int8_t di, dj, dk; uint8_t before, after; } V2DeltaRow;")
    a("typedef struct { int8_t di, dj, dk; uint8_t pred; } V2CtxRow;")
    a("typedef struct {")
    a("    int32_t delta_begin, delta_n, ctx_begin, ctx_n;")
    a("    int8_t  v_origin_row, v_dest_row;   /* MSD bookkeeping; -1 = n/a */")
    a("    uint8_t anchor_sp, _pad;")
    a("} V2Pattern;")
    a("typedef struct { int32_t pat; uint8_t op; uint8_t _pad[3]; } V2Proc;")
    a("")
    a("/* The 16 D4h ops (row-major 3x3 integer matrices), in the canonical")
    a(" * index order of pylatkmc.ingest.lattice.D4H_OPS. */")
    a("static const int8_t V2_OPS[16][9] = {")
    out.extend(op_lines)
    a("};")
    a("")
    a(f"static const V2DeltaRow v2_delta_rows[{max(1, len(delta_rows))}] = {{")
    out.extend(_chunk_lines(delta_rows, 8))
    a("};")
    a("")
    a(f"static const V2CtxRow v2_ctx_rows[{max(1, len(ctx_rows))}] = {{")
    out.extend(_chunk_lines(ctx_rows, 8))
    a("};")
    a("")
    a(f"static const V2Pattern v2_patterns[{len(pattern_defs)}] = {{")
    out.extend(pattern_defs)
    a("};")
    a("")
    a("static const V2Proc v2_procs[N_PROCS] = {")
    out.extend(
        _chunk_lines([f"{{{t},{op},{{0,0,0}}}}," for (t, op, _m, _pi) in procs], 8)
    )
    a("};")
    a("")
    a("/* Proc-id ranges by anchor-site species code (procs are sorted so each")
    a(" * species' processes are contiguous): scan only the bucket matching")
    a(" * st->species[site]. */")
    a(f"static const int32_t v2_bucket_begin[{n_sp + 1}] = "
      f"{{{','.join(str(b) for b in bucket_begin)}}};")
    a("")
    a("/* ---- generic matcher ---- */")
    a("static int v2_match(const Lattice *lat, const State *st, int site,")
    a("                    const V2Proc *pr)")
    a("{")
    a("    const V2Pattern *pt = &v2_patterns[pr->pat];")
    a("    const int8_t *R = V2_OPS[pr->op];")
    a("    const int16_t *c0 = &lat->site_ijk[3 * site];")
    a("    for (int32_t r = 0; r < pt->delta_n; ++r) {")
    a("        const V2DeltaRow *dr = &v2_delta_rows[pt->delta_begin + r];")
    a("        int32_t di = R[0]*dr->di + R[1]*dr->dj + R[2]*dr->dk;")
    a("        int32_t dj = R[3]*dr->di + R[4]*dr->dj + R[5]*dr->dk;")
    a("        int32_t dk = R[6]*dr->di + R[7]*dr->dj + R[8]*dr->dk;")
    a("        int32_t rs = lattice_site_at_ijk(lat, c0[0]+di, c0[1]+dj, c0[2]+dk);")
    a("        /* Delta sites must EXIST with the exact before-state; the stub's")
    a("         * 255 sentinel never equals a real species code. */")
    a("        if (st->species[rs] != dr->before) return 0;")
    a("    }")
    a("    for (int32_t r = 0; r < pt->ctx_n; ++r) {")
    a("        const V2CtxRow *cr = &v2_ctx_rows[pt->ctx_begin + r];")
    a("        int32_t di = R[0]*cr->di + R[1]*cr->dj + R[2]*cr->dk;")
    a("        int32_t dj = R[3]*cr->di + R[4]*cr->dj + R[5]*cr->dk;")
    a("        int32_t dk = R[6]*cr->di + R[7]*cr->dj + R[8]*cr->dk;")
    a("        int32_t rs = lattice_site_at_ijk(lat, c0[0]+di, c0[1]+dj, c0[2]+dk);")
    a("        uint8_t v = st->species[rs];")
    a("        uint8_t p = cr->pred;")
    a("        if (p == V2_PRED_EMPTY) {")
    a("            /* Harvest-side EMPTY cannot distinguish a vacant lattice site")
    a("             * from vacuum beyond the slab; match either. */")
    a("            if (v != SP_VACANT && v != 255u) return 0;")
    a("        } else if (p == V2_PRED_OCC_ANY) {")
    a("            if (v == SP_VACANT || v == 255u) return 0;")
    a("        } else if (v != p) {")
    a("            return 0;")
    a("        }")
    a("    }")
    a("    return 1;")
    a("}")
    a("")
    a("void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site)")
    a("{")
    a("    if (!lat->site_grid || !lat->site_ijk) return;  /* grid not built */")
    a("    uint8_t sp = st->species[site];")
    a(f"    if (sp >= {n_sp}u) return;")
    a("    for (int32_t p = v2_bucket_begin[sp]; p < v2_bucket_begin[sp + 1]; ++p) {")
    a("        if (v2_match(lat, st, site, &v2_procs[p]))")
    a("            avail_sites_add(as, p, site);")
    a("    }")
    a("}")
    a("")
    a("/* ---- generic apply + per-proc wrappers ----")
    a(" *")
    a(" * The runtime calls pylatkmc_apply_table[proc](st, lat, site) — a")
    a(" * signature frozen by the committed v0.3 proclists — so each proc gets")
    a(" * a one-line wrapper binding its proc id into the generic apply. */")
    a("typedef struct { int v_origin; int v_dest; } HopOutcome;")
    a("typedef HopOutcome (*ApplyFn)(State *st, const Lattice *lat, int site);")
    a("")
    a("static HopOutcome v2_apply(State *st, const Lattice *lat, int32_t proc,")
    a("                           int32_t site)")
    a("{")
    a("    const V2Proc *pr = &v2_procs[proc];")
    a("    const V2Pattern *pt = &v2_patterns[pr->pat];")
    a("    const int8_t *R = V2_OPS[pr->op];")
    a("    const int16_t *c0 = &lat->site_ijk[3 * site];")
    a("    StateAction acts[V2_MAX_DELTA];")
    a("    for (int32_t r = 0; r < pt->delta_n; ++r) {")
    a("        const V2DeltaRow *dr = &v2_delta_rows[pt->delta_begin + r];")
    a("        int32_t di = R[0]*dr->di + R[1]*dr->dj + R[2]*dr->dk;")
    a("        int32_t dj = R[3]*dr->di + R[4]*dr->dj + R[5]*dr->dk;")
    a("        int32_t dk = R[6]*dr->di + R[7]*dr->dj + R[8]*dr->dk;")
    a("        acts[r].site   = lattice_site_at_ijk(lat, c0[0]+di, c0[1]+dj, c0[2]+dk);")
    a("        acts[r].before = dr->before;")
    a("        acts[r].after  = dr->after;")
    a("    }")
    a("    (void)state_apply_actions(st, acts, pt->delta_n, SP_VACANT);")
    a("    HopOutcome ho = { -1, -1 };")
    a("    if (pt->v_origin_row >= 0) ho.v_origin = acts[pt->v_origin_row].site;")
    a("    if (pt->v_dest_row   >= 0) ho.v_dest   = acts[pt->v_dest_row].site;")
    a("    return ho;")
    a("}")
    a("")
    a("#define V2W(n) static HopOutcome v2w_##n(State *st, const Lattice *lat, "
      "int site) { return v2_apply(st, lat, n, site); }")
    out.extend(_chunk_lines([f"V2W({i})" for i in range(n_procs)], 8, indent=""))
    a("#undef V2W")
    a("")
    a("static const ApplyFn apply_table[N_PROCS] = {")
    out.extend(_chunk_lines([f"v2w_{i}," for i in range(n_procs)], 8))
    a("};")
    return "\n".join(out) + "\n"


def emit_v2_rate_table(patterns: list[LatticePattern]) -> str:
    """Emit the v2 ``rate_table[N_PROCS]``: one entry per (pattern, op) proc.

    Same ``RateConst`` layout contract as the v0.3 emitter: the typedef here
    and the one in ``proclist.h`` are independent translation-unit copies and
    MUST stay field-for-field identical (the ``_Static_assert`` guards size,
    not order). Every orientation of a class carries the class rate
    (FINAL_DESIGN §5.1: ``rate = C.k_rate_mean``): ``prefactor_Hz`` is
    ``nu0_geo_psinv × 1e12`` (converted once, in the translator) and ``Ea_eV``
    is ``Ea_rep_eV``, so ``prefactor·exp(-Ea/kBT)`` reproduces the class's
    rate-space mean exactly at the catalogue's reference temperature.
    """
    if not patterns:
        # The typedef must still be emitted: the public glue references
        # RateConst (`pylatkmc_rate_table = NULL`) even when the table
        # itself is omitted, and proclist.c does not include proclist.h.
        return (
            "/* no patterns; rate_table omitted */\n"
            "typedef struct { double prefactor_Hz; double Ea_eV; "
            "int32_t is_electrochemical; int32_t _pad; } RateConst;\n"
            '_Static_assert(sizeof(RateConst) == 24, '
            '"RateConst layout drift vs proclist.h");\n'
        )
    _order_ignored, procs = _proc_list(patterns)
    lines = [
        "typedef struct { double prefactor_Hz; double Ea_eV; "
        "int32_t is_electrochemical; int32_t _pad; } RateConst;",
        '_Static_assert(sizeof(RateConst) == 24, '
        '"RateConst layout drift vs proclist.h");',
        "static const RateConst rate_table[N_PROCS] = {",
    ]
    for (_t, op, m, pi) in procs:
        pat = patterns[pi]
        mr = _members(pat)[m]
        lines.append(
            f"    {{ .prefactor_Hz = {mr.prefactor_Hz:.10e}, "
            f".Ea_eV = {mr.Ea_eV:.6f}, .is_electrochemical = 0, "
            f"._pad = 0 }}, /* {pat.name} m{m} g{op} */"
        )
    lines.append("};")
    return "\n".join(lines) + "\n"


def _c_string(s: str) -> str:
    """A C double-quoted string literal for an ASCII class-id hex digest."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _fmt_f64(x: float) -> str:
    """Full-precision C double literal (NaN → the standard NAN macro)."""
    import math

    if math.isnan(x):
        return "NAN"
    return f"{x:.17g}"


def emit_v2_provenance(patterns: list[LatticePattern]) -> str:
    """Emit machine-readable per-proc provenance (replaces comment-only).

    A ``v2_class_ids[]`` string table (sorted unique class ids) plus four
    per-proc arrays index-aligned with ``rate_table`` / ``v2_procs``:
    ``v2_proc_class`` (index into ``v2_class_ids``), ``v2_proc_member`` (the
    harvested member index), ``v2_proc_channel`` (CHANNEL_MEASURED), and
    ``v2_proc_v6_ea`` (the per-class V6 surrogate barrier in eV, NaN if no
    model baked). Guarded by ``PYLATKMC_V2_PROVENANCE`` in proclist.h.
    """
    _order_ignored, procs = _proc_list(patterns)
    class_ids = sorted({p.class_id for p in patterns})
    idx_of = {cid: i for i, cid in enumerate(class_ids)}

    out: list[str] = []
    a = out.append
    a("#include <math.h>   /* NAN for the V6 surrogate-barrier provenance */")
    a("/* ---- machine-readable provenance (per-proc; §8-N6 channel a) ---- */")
    a(f"static const char *const v2_class_ids[{max(1, len(class_ids))}] = {{")
    out.extend(_chunk_lines([f"{_c_string(c)}," for c in class_ids], 2))
    if not class_ids:
        a("    0")
    a("};")
    a(f"static const int32_t v2_n_classes = {len(class_ids)};")
    a("")
    proc_class = [idx_of[patterns[pi].class_id] for (_t, _op, _m, pi) in procs]
    proc_member = [m for (_t, _op, m, _pi) in procs]
    proc_chan = [CHANNEL_MEASURED for _ in procs]
    proc_v6 = [_members(patterns[pi])[m].v6_ea_surrogate for (_t, _op, m, pi) in procs]
    a(f"static const int32_t v2_proc_class[{max(1, len(procs))}] = {{")
    out.extend(_chunk_lines([f"{v}," for v in proc_class], 16))
    if not procs:
        a("    0")
    a("};")
    a(f"static const int32_t v2_proc_member[{max(1, len(procs))}] = {{")
    out.extend(_chunk_lines([f"{v}," for v in proc_member], 16))
    if not procs:
        a("    0")
    a("};")
    a(f"static const uint8_t v2_proc_channel[{max(1, len(procs))}] = {{")
    out.extend(_chunk_lines([f"{v}," for v in proc_chan], 16))
    if not procs:
        a("    0")
    a("};")
    a(f"static const double v2_proc_v6_ea[{max(1, len(procs))}] = {{")
    out.extend(_chunk_lines([f"{_fmt_f64(v)}," for v in proc_v6], 8))
    if not procs:
        a("    0")
    a("};")
    return "\n".join(out) + "\n"


__all__ = (
    "CHANNEL_MEASURED",
    "CHANNEL_SURROGATE",
    "PRED_EMPTY",
    "PRED_OCC_ANY",
    "emit_pattern_tables",
    "emit_v2_enum",
    "emit_v2_provenance",
    "emit_v2_rate_table",
    "n_procs_of",
    "pattern_reach",
)
