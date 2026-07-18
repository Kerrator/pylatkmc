"""Codegen — turn a ModelSpec into the runtime's `proclist.c`.

In v0.2 the codegen has a single responsibility: emit
`generated/proclist.c` (and a small companion `proclist.h`) for a given
model spec. The proclist bundles four pieces of generated C that the
M-B emitters produce from a list[Process]:

1. **Process enum** (`emit_process_enum`) — `enum { P_<name>, ...,
   N_PROCS };`
2. **Rate table** (`emit_rate_table`) — `static const RateConst
   rate_table[N_PROCS] = { ... };` storing per-Process `{prefactor_Hz,
   Ea_eV}`. The Arrhenius rate is computed by the runtime at startup from
   the *runtime* temperature (`physics.temperature_K`) — NOT baked at
   codegen time, so one compiled binary runs at any T.
3. **Apply functions + dispatch table** (`emit_apply_actions`) — one
   `apply_actions_<name>` per Process; `apply_table[N_PROCS]` indexed
   by P_<name>.
4. **Decision tree** (`compile_decision_tree`) — `void touchup_a(lat,
   st, as, site)` that calls `avail_sites_add` for every eligible
   Process at the given anchor site.

The pipeline:

  spec.rate_data.family_table (CSV)
    → translator.load_family_rate_table → list[FamilyBucketRow]
    → translator.translate_all           → list[Process]
    → emit_*                             → string
    → write generated/proclist.{c,h}

This replaces the M1-era cube codegen which emitted four separate
templates (events.h, ratetable.h, ratetable.c, avail.c). The cube
files and templates are scheduled for deletion in M-D.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pylatkmc.decision_tree import (
    compile_decision_tree,
    emit_apply_actions,
    emit_process_enum,
    emit_rate_table,
)
from pylatkmc.dissolution_rate import DissolutionParams, load_params
from pylatkmc.processes import Process
from pylatkmc.rate_expression import KB_EV_PER_K
from pylatkmc.spec import DissolutionSpec, ModelSpec
from pylatkmc.translator import (
    load_family_rate_table,
    translate_all,
    translate_dissolution_family,
)

# ---------------------------------------------------------------------------
# kmos-style #@-prefixed template preprocessor (kept for backwards compat;
# unused by the new generate() but referenced by some legacy tests until
# M-E cleanup).
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_PREFIX = "#@"


def evaluate_template(template: str, **context: Any) -> str:
    """kmos-style preprocessor (legacy; superseded by string-builder
    M-B emitters). See git history for the original docstring; kept
    around for tests that still reference it."""
    namespace: dict[str, Any] = dict(context)
    namespace["result"] = ""

    python_src: list[str] = []
    for raw_line in template.splitlines(keepends=True):
        lstripped = raw_line.lstrip()
        indent_len = len(raw_line) - len(lstripped)
        indent = raw_line[:indent_len]

        if lstripped.startswith(_PREFIX + " "):
            literal = lstripped[len(_PREFIX) + 1 :]
            if literal.endswith("\n"):
                literal = literal[:-1]
            emit = "f" + repr(literal)
            python_src.append(f"{indent}result += {emit}\n")
            python_src.append(f'{indent}result += "\\n"\n')
        elif lstripped.rstrip("\n") == _PREFIX:
            python_src.append(f'{indent}result += "\\n"\n')
        else:
            python_src.append(raw_line)

    compiled_src = "".join(python_src)
    try:
        exec(compile(compiled_src, "<template>", "exec"), namespace)
    except Exception as e:
        raise RuntimeError(
            f"evaluate_template failed: {e}\n\n"
            f"----- compiled Python -----\n{compiled_src}\n"
            f"---------------------------"
        ) from e
    return namespace["result"]


def render_template_file(template_name: str, spec: ModelSpec, **extra: Any) -> str:
    """Legacy: render a .tmpl file. Kept for back-compat; new pipeline
    in `generate()` doesn't use templates."""
    path = _TEMPLATES_DIR / f"{template_name}.tmpl"
    if not path.is_file():
        raise FileNotFoundError(f"template not found: {path}")
    return evaluate_template(path.read_text(), spec=spec, **extra)


# ---------------------------------------------------------------------------
# proclist.c emission
# ---------------------------------------------------------------------------


_PROCLIST_C_PREAMBLE = """\
/* proclist.c — GENERATED from {spec_name}.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build {spec_name}.kmcspec.toml`.
 *
 * This file is the heart of the pylatkmc v2 pattern-DB runtime: it
 * bundles the per-model Process catalogue (translated from the curated
 * FCC family CSV) into a single C compilation unit consumed by the
 * runtime backbone in `runtime/src/core/`.
 *
 * Contents (in order):
 *   1. enum {{ P_<name>, ..., N_PROCS }}      — Process IDs
 *   2. static const RateConst rate_table[]   — per-proc {{prefactor_Hz, Ea_eV}}.
 *      The Arrhenius rate is computed by the runtime at startup from the
 *      *runtime* temperature (physics.temperature_K), NOT baked here. The
 *      prefactor is the per-family Vineyard ν₀ (style=htst) or the global
 *      k0 = {k0_Hz:.3e} Hz fallback. Spec reference T = {temperature_K} K.
 *   3. static HopOutcome apply_actions_<name>(...)  — one per Process
 *      (calls state_apply_actions on a StateAction[] from each Process's
 *      actions list)
 *   4. static const ApplyFn apply_table[N_PROCS]    — dispatch table
 *   5. void touchup_a(lat, st, as, site)            — decision tree
 *
 * The runtime calls `touchup_a(...)` for each active site in
 * active_filter to enrol firing Processes via avail_sites_add. After
 * BKL selects (proc, site), the runtime calls apply_table[proc](st, lat,
 * site) to apply the actions atomically.
 */
#include <stdint.h>

#include "events_base.h"     /* SP_VACANT, SP_NI, SP_FE, SP_CR */
#include "coord_codes.h"     /* NeighbourCode enum, N_NEIGHBOUR_CODES */
#include "lattice.h"         /* struct Lattice */
#include "state.h"           /* struct State, StateAction, state_apply_actions */
#include "avail_sites.h"     /* AvailSites, avail_sites_add */

"""


_PROCLIST_H_TEMPLATE = """\
/* proclist.h — GENERATED from {spec_name}.kmcspec.toml.
 *
 * DO NOT EDIT. Regenerate with `pylatkmc-gen build {spec_name}.kmcspec.toml`.
 *
 * Public interface: just enough symbols for the runtime backbone
 * (kmc.c, replica.c, main.c) to call into proclist.c. Internal
 * symbols (apply_actions_<name>, the decision-tree helpers) stay
 * `static` inside proclist.c.
 *
 * The N_PROCS macro and the rate_table sizing are exposed so the
 * runtime can configure avail_sites at startup.
 */
#ifndef PYLATKMC_PROCLIST_H
#define PYLATKMC_PROCLIST_H

#include <stdint.h>
#include <math.h>

#include "lattice.h"
#include "state.h"
#include "avail_sites.h"

/* Boltzmann constant in eV/K. GENERATED from
 * pylatkmc.rate_expression.KB_EV_PER_K — the single source of truth shared
 * by the Python codegen and this C runtime, so the two cannot drift. */
#define PYLATKMC_KB_EV_PER_K {kb_ev_per_k:.10e}
{extra_defines}
/* Number of Processes in this model. Defined by the generated enum
 * in proclist.c; exposed here as a const for sizeof / loop bounds. */
extern const int32_t pylatkmc_n_procs;

/* Rate table: per-Process Arrhenius **prefactor** (Hz = s^-1) + activation
 * energy (eV). The rate k = prefactor_Hz * exp(-Ea_eV / (kB * T)) is computed
 * by the runtime at startup from the *runtime* temperature
 * (physics.temperature_K in input.ini) via rateconst_eval() below — NOT baked
 * at codegen time. One compiled binary therefore runs at any temperature.
 *
 * Declared as a pointer (not an array) so the storage in proclist.c can
 * be a `const RateConst *const` alias to a file-static array.
 *
 * NOTE: this typedef MUST stay layout-identical to the copy emitted by
 * pylatkmc.decision_tree.emit_rate_table into proclist.c (which does not
 * include this header). The _Static_assert below guards against drift. */
typedef struct {{ double prefactor_Hz; double Ea_eV; int32_t is_electrochemical; int32_t _pad; }} RateConst;
_Static_assert(sizeof(RateConst) == 24, "RateConst layout drift vs proclist.c");
extern const RateConst *const pylatkmc_rate_table;

/* Evaluate one Process's rate (Hz) at temperature T_K (Kelvin) and applied
 * overpotential phi_eV (eV). This is the single place the runtime un-bakes a
 * rate from a prefactor.
 *
 * For an electrochemical dissolution Process, the overpotential lowers the
 * baked bare barrier: k = prefactor * exp(-(Ea - phi) / (kB*T)), clamped at a
 * barrierless floor (Ea - phi >= 0). Non-electrochemical Processes ignore phi,
 * recovering the plain Arrhenius rate (so existing models are unaffected when
 * phi = 0). */
static inline double rateconst_eval(RateConst rc, double T_K, double phi_eV) {{
    double Ea = rc.Ea_eV - (rc.is_electrochemical ? phi_eV : 0.0);
    if (Ea < 0.0) Ea = 0.0;
    return rc.prefactor_Hz * exp(-Ea / (PYLATKMC_KB_EV_PER_K * T_K));
}}

/* HopOutcome: returned by every apply function. The runtime uses
 * v_origin / v_dest to update unwrapped_xyz for MSD tracking on simple
 * hops; multi-vacancy concerted events return -1 in both fields and
 * the runtime skips the MSD update. */
typedef struct {{ int v_origin; int v_dest; }} HopOutcome;

typedef HopOutcome (*ApplyFn)(struct State *st, const struct Lattice *lat, int site);
extern const ApplyFn *const pylatkmc_apply_table;

/* Decision tree: enrol every eligible Process at `site` into `as`. */
void touchup_a(const struct Lattice *lat, const struct State *st,
               struct AvailSites *as, int site);

#endif /* PYLATKMC_PROCLIST_H */
"""


def _build_proclist_c(processes: list[Process], spec: ModelSpec) -> str:
    """Bundle the M-B emitters into a single proclist.c source string."""
    rd = spec.rate_data
    preamble = _PROCLIST_C_PREAMBLE.format(
        spec_name=spec.name,
        temperature_K=rd.temperature_K,
        k0_Hz=rd.k0_Hz,
    )
    body = (
        emit_process_enum(processes)
        + "\n"
        + emit_rate_table(processes)
        + "\n"
        + emit_apply_actions(processes)
        + "\n"
        + compile_decision_tree(processes, "touchup_a")
    )
    # Expose pylatkmc_n_procs / pylatkmc_rate_table / pylatkmc_apply_table
    # as `extern`-able linkage. The internal `rate_table` / `apply_table`
    # arrays are file-static; we re-export them through public wrappers.
    n_procs = max(1, len(processes))  # avoid `[0]` arrays — C forbids
    public_glue = """

/* ---- Public linkage (mirrored in proclist.h) ----
 *
 * The internal `rate_table` / `apply_table` are file-static. The runtime
 * accesses them through these `pylatkmc_*` aliases, decoupling the
 * call site from the static-storage symbols.
 */
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""
    if not processes:
        # Empty case: rate_table isn't emitted (its RateConst typedef still
        # is); the empty apply_table stub IS emitted — alias it so it isn't
        # flagged unused.
        public_glue = """

const int32_t pylatkmc_n_procs = 0;
const RateConst *const pylatkmc_rate_table = NULL;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""
    _ = n_procs  # silence unused
    return preamble + body + public_glue


def _build_proclist_h(spec: ModelSpec, extra_defines: str = "") -> str:
    """Render proclist.h. ``extra_defines`` slots extra ``#define`` lines
    after the kB constant (v2 pattern-reach macros); the default ``""``
    renders byte-identically to the pre-slot template, so v0.3 models
    do not need regenerating."""
    return _PROCLIST_H_TEMPLATE.format(
        spec_name=spec.name, kb_ev_per_k=KB_EV_PER_K, extra_defines=extra_defines
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _resolve_family_csv(spec: ModelSpec, spec_path: Path | None) -> Path:
    """Resolve `spec.rate_data.family_table` (which may be relative to the
    spec file's parent directory)."""
    csv = spec.rate_data.family_table
    if csv is None:
        raise ValueError(
            f"Spec {spec.name!r} has no rate_data.family_table; pylatkmc v0.2 "
            f"requires the curated FCC family CSV to translate Processes."
        )
    csv = Path(csv)
    if not csv.is_absolute() and spec_path is not None:
        csv = (spec_path.parent / csv).resolve()
    return csv


def _build_dissolution_processes(
    spec: ModelSpec, diss_spec: DissolutionSpec
) -> list[Process]:
    """Load the ε table, build DissolutionParams from the spec, validate that
    every occupied species pair has a per-bond energy, and translate the
    analytical dissolution family into Processes.

    The spec fields (nu_E_Hz, min/max_coordination) are authoritative over the
    ε table's [meta]; the table is consulted only for the per-bond ε values.
    """
    table = load_params(diss_spec.epsilon_table)
    params = DissolutionParams(
        epsilon=table.epsilon,
        nu_E_Hz=diss_spec.nu_E_Hz,
        phi_eV=diss_spec.default_phi_eV,
        min_coordination=diss_spec.min_coordination,
        max_coordination=diss_spec.max_coordination,
    )
    occupied = [s for s in spec.species if s != "Vacant"]
    missing = sorted(
        {
            tuple(sorted((a, b)))
            for i, a in enumerate(occupied)
            for b in occupied[i:]
            if tuple(sorted((a, b))) not in params.epsilon
        }
    )
    if missing:
        raise ValueError(
            f"dissolution: epsilon_table {diss_spec.epsilon_table} is missing "
            f"per-bond energies for species pairs {missing} (model species: "
            f"{occupied}). Add them to the [epsilon_eV_per_bond] table."
        )
    return translate_dissolution_family(
        params,
        spec.species,
        T_K=spec.rate_data.temperature_K,
        shell=diss_spec.shell,
    )


def _resolve_event_class_table(spec: ModelSpec, spec_path: Path | None) -> Path:
    """Resolve `spec.rate_data.event_class_table` relative to the spec file."""
    ect = spec.rate_data.event_class_table
    assert ect is not None  # caller checks
    ect = Path(ect)
    if not ect.is_absolute() and spec_path is not None:
        ect = (spec_path.parent / ect).resolve()
    return ect


def _generate_v2(spec: ModelSpec, out: Path, spec_path: Path | None) -> list[Path]:
    """The Phase B path: EventClass Parquet → pattern tables → proclist.{c,h}.

    Species-resolved end to end (no mover-species default anywhere) and
    D4h-orientation-expanded at translate time. The emitted proclist.h is the
    same template as the v0.3 path, so the runtime cannot tell the strategies
    apart. Skipped classes are reported, never silent.
    """
    from pylatkmc.pattern_codegen import (
        emit_pattern_tables,
        emit_v2_enum,
        emit_v2_rate_table,
        n_procs_of,
        pattern_reach,
    )
    from pylatkmc.translator_v2 import translate_catalogue

    ect = _resolve_event_class_table(spec, spec_path)
    patterns, report = translate_catalogue(ect)

    # Every harvested species must be declared in the spec — a catalogue
    # species missing from spec.species would silently never occur in the
    # initial configuration, which is a modelling error, not a codegen one.
    harvested = sorted({sp for p in patterns for sp in p.mover_species})
    missing = [sp for sp in harvested if sp not in spec.species]
    if missing:
        raise ValueError(
            f"catalogue movers {missing} are not in spec.species "
            f"{spec.species}; declare them in the model spec"
        )

    for line in report.summary_lines():
        print(f"pylatkmc-gen [v2]: {line}")

    rd = spec.rate_data
    preamble = _PROCLIST_C_PREAMBLE.format(
        spec_name=spec.name,
        temperature_K=rd.temperature_K,
        k0_Hz=rd.k0_Hz,
    )
    n_procs = n_procs_of(patterns)
    body = (
        emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + emit_pattern_tables(patterns)
    )
    public_glue = """

/* ---- Public linkage (mirrored in proclist.h) ---- */
const int32_t pylatkmc_n_procs = (int32_t)N_PROCS;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""
    if n_procs == 0:
        # rate_table isn't emitted (RateConst typedef still is); the empty
        # apply_table stub IS emitted — alias it so it isn't flagged unused.
        public_glue = """

const int32_t pylatkmc_n_procs = 0;
const RateConst *const pylatkmc_rate_table = NULL;
const ApplyFn   *const pylatkmc_apply_table = apply_table;
"""

    # Pattern reach macros: replica.c refuses a config whose vacuum gap is
    # thinner than the reach (grid offsets wrap every axis; a too-thin gap
    # would alias pattern rows onto the far surface instead of the stub).
    reach_ij, reach_k = pattern_reach(patterns)
    extra_defines = (
        "\n/* Max v2 pattern reach in grid cells (D4h-invariant), over all\n"
        " * delta+context rows. The runtime rejects a configuration whose\n"
        " * vacuum gap is thinner than this on any axis (see replica.c). */\n"
        f"#define PYLATKMC_V2_MAX_REACH_IJ {reach_ij}\n"
        f"#define PYLATKMC_V2_MAX_REACH_K {reach_k}\n"
    )

    written: list[Path] = []
    proclist_c_path = out / "proclist.c"
    proclist_c_path.write_text(preamble + body + public_glue)
    written.append(proclist_c_path)
    proclist_h_path = out / "proclist.h"
    proclist_h_path.write_text(_build_proclist_h(spec, extra_defines=extra_defines))
    written.append(proclist_h_path)
    return written


def generate(spec: ModelSpec, out_dir: str | Path, spec_path: Path | None = None) -> list[Path]:
    """Render `proclist.c` + `proclist.h` for `spec` and write them to
    `out_dir`. Returns the list of written paths.

    Two explicit paths, selected by the spec:

    - **v2 (Phase B)** — `spec.rate_data.event_class_table` set: translate the
      EventClass Parquet catalogue via translator_v2 into data-driven pattern
      tables + a generic matcher (species-resolved, D4h-expanded).
    - **v0.3** — otherwise: the family-CSV pipeline below.

    v0.3 pipeline:
      1. Load the family-rate-table CSV (path from spec.rate_data.family_table,
         resolved relative to `spec_path` if given).
      2. translate_all → list[Process].
      3. emit_process_enum + emit_rate_table + emit_apply_actions +
         compile_decision_tree → C source string.
      4. Wrap with the proclist.c preamble + public-linkage glue.
      5. Write proclist.c and proclist.h, overwriting any existing files.

    `spec_path` is used to resolve relative paths in
    `spec.rate_data.family_table` / `.event_class_table`. Pass it from
    `pylatkmc-gen build` so relative paths stay anchored at the spec file's
    directory.
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if spec.rate_data.event_class_table is not None:
        return _generate_v2(spec, out, spec_path)

    family_csv = _resolve_family_csv(spec, spec_path)

    rows = load_family_rate_table(family_csv)
    processes = translate_all(
        rows,
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
        # The family CSV carries no species information, so this legacy path
        # can only emit Ni movers — stated EXPLICITLY here since translator
        # v2 removed the silent default (the v2 path is species-resolved).
        mover_species="Ni",
        style=spec.rate_data.prefactor_style,
        on_unknown_family=lambda f: print(f"pylatkmc-gen: skipping unknown family {f!r}"),
    )

    # Append the analytical electrochemical dissolution family (if enabled).
    if spec.dissolution is not None and spec.dissolution.enabled:
        diss = _build_dissolution_processes(spec, spec.dissolution)
        print(f"pylatkmc-gen: + {len(diss)} dissolution Processes")
        processes = processes + diss

    written: list[Path] = []

    proclist_c = _build_proclist_c(processes, spec)
    proclist_c_path = out / "proclist.c"
    proclist_c_path.write_text(proclist_c)
    written.append(proclist_c_path)

    proclist_h = _build_proclist_h(spec)
    proclist_h_path = out / "proclist.h"
    proclist_h_path.write_text(proclist_h)
    written.append(proclist_h_path)

    return written
