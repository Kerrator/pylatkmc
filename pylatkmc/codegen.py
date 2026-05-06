"""Codegen — turn a ModelSpec into the runtime's `proclist.c`.

In v0.2 the codegen has a single responsibility: emit
`generated/proclist.c` (and a small companion `proclist.h`) for a given
model spec. The proclist bundles four pieces of generated C that the
M-B emitters produce from a list[Process]:

1. **Process enum** (`emit_process_enum`) — `enum { P_<name>, ...,
   N_PROCS };`
2. **Rate table** (`emit_rate_table`) — `static const RateConst
   rate_table[N_PROCS] = { ... };` baked at codegen time from each
   Process's Arrhenius rate at the spec's T.
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
from pylatkmc.processes import Process
from pylatkmc.spec import ModelSpec
from pylatkmc.translator import load_family_rate_table, translate_all


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
            literal = lstripped[len(_PREFIX) + 1:]
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


def render_template_file(
    template_name: str, spec: ModelSpec, **extra: Any
) -> str:
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
 *   2. static const RateConst rate_table[]   — per-proc Arrhenius rate
 *      baked at T = {temperature_K} K, k0 = {k0_Hz:.3e} Hz
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

#include "lattice.h"
#include "state.h"
#include "avail_sites.h"

/* Number of Processes in this model. Defined by the generated enum
 * in proclist.c; exposed here as a const for sizeof / loop bounds. */
extern const int32_t pylatkmc_n_procs;

/* Rate table: per-Process Arrhenius rate (s^-1) baked at codegen time.
 * Read by replica.c at startup to seed avail_sites_set_rate.
 *
 * Declared as a pointer (not an array) so the storage in proclist.c can
 * be a `const RateConst *const` alias to a file-static array. */
typedef struct {{ double rate; double Ea_eV; }} RateConst;
extern const RateConst *const pylatkmc_rate_table;

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
    n_procs = max(1, len(processes))   # avoid `[0]` arrays — C forbids
    public_glue = f"""

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
        # Empty case: rate_table / apply_table aren't emitted, fall back to NULL.
        public_glue = """

const int32_t pylatkmc_n_procs = 0;
const RateConst *const pylatkmc_rate_table = NULL;
const ApplyFn   *const pylatkmc_apply_table = NULL;
"""
    _ = n_procs   # silence unused
    return preamble + body + public_glue


def _build_proclist_h(spec: ModelSpec) -> str:
    return _PROCLIST_H_TEMPLATE.format(spec_name=spec.name)


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


def generate(spec: ModelSpec, out_dir: str | Path,
             spec_path: Path | None = None) -> list[Path]:
    """Render `proclist.c` + `proclist.h` for `spec` and write them to
    `out_dir`. Returns the list of written paths.

    Pipeline:
      1. Load the family-rate-table CSV (path from spec.rate_data.family_table,
         resolved relative to `spec_path` if given).
      2. translate_all → list[Process].
      3. emit_process_enum + emit_rate_table + emit_apply_actions +
         compile_decision_tree → C source string.
      4. Wrap with the proclist.c preamble + public-linkage glue.
      5. Write proclist.c and proclist.h, overwriting any existing files.

    `spec_path` is used to resolve relative paths in
    `spec.rate_data.family_table`. Pass it from `pylatkmc-gen build` so
    relative CSV paths stay anchored at the spec file's directory.
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    family_csv = _resolve_family_csv(spec, spec_path)

    rows = load_family_rate_table(family_csv)
    processes = translate_all(
        rows,
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
        on_unknown_family=lambda f: print(
            f"pylatkmc-gen: skipping unknown family {f!r}"
        ),
    )

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
