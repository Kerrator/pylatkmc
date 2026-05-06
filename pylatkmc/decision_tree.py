"""Decision-tree codegen for the pattern-DB matcher.

Given a list[Process], compile the conditions into a nested decision
tree that, for any given anchor site `s`, determines which Processes
are eligible (i.e. all their conditions hold at that anchor).

Algorithm — port of kmos's `_write_optimal_iftree`
(`_archive/kmos-main/kmos/io/__init__.py:2568–2655`):

    1. If a Process has no remaining conditions, emit
       `add_proc(P, site, rate)`.
    2. Otherwise, find the most-frequently-shared CoordOffset across
       all remaining Processes' conditions (the "bottleneck" coord).
    3. Emit `switch (species_at(site, coord))`.
    4. For each species value, partition the Process set into those
       expecting that species at that coord, and recurse on each
       partition with that condition removed.
    5. Processes whose conditions don't include the bottleneck coord
       are recursed at the same indent level (tail recursion, no extra
       nesting).

This produces a tree of average depth ~ log(n_processes) and worst-case
depth = max(condition count per process). Because the FCC catalogue
families share their anchor condition (Vacant @ (0,0,0,a)) and their
mover-direction conditions, the greedy partitioning collapses related
Processes onto shared branches.

Output is a Python string buffer of C source. The caller is responsible
for splicing it into a generated `proclist.c` template.

This module is pure (no I/O); side effects are confined to a
`_TreeBuilder` accumulator which the public `compile_tree()` returns.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .processes import Condition, CoordOffset, Process


# ---------------------------------------------------------------------------
# Internal: tree builder that accumulates C source
# ---------------------------------------------------------------------------


@dataclass
class _TreeBuilder:
    """Accumulator for emitted C lines; tracks indent depth.

    Use `with builder.indent():` context manager (or `.dedent()`) to
    track scope; `builder.emit(line)` appends a line at the current
    indent level.
    """

    lines: list[str] = field(default_factory=list)
    _indent: int = 0

    def emit(self, line: str = "") -> None:
        if line == "":
            self.lines.append("")
        else:
            self.lines.append(("    " * self._indent) + line)

    def push(self) -> None:
        self._indent += 1

    def pop(self) -> None:
        if self._indent > 0:
            self._indent -= 1

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


# ---------------------------------------------------------------------------
# Coord encoding for the species_at() / apply call in C
# ---------------------------------------------------------------------------


def _coord_macro(coord: CoordOffset) -> str:
    """C expression for resolving a CoordOffset to an absolute site index.

    The runtime maintains, per Lattice, a flat lookup table:
        lat->coord_table[site * N_NEIGHBOUR_CODES + nc]
    populated at lattice load by `lattice_build_coord_table` (see
    runtime/src/core/lattice.c). This function emits the C expression
    that performs that lookup. For the anchor (`NC_ANCHOR`) it shortcuts
    to `site` directly.
    """
    if coord.code == "NC_ANCHOR":
        return "site"
    return f"lat->coord_table[site * N_NEIGHBOUR_CODES + {coord.code}]"


def _species_at(coord: CoordOffset) -> str:
    """C expression for the species at a coord, given the anchor `site`
    and the runtime's `species` array. Reads from `st->species[]`."""
    return f"st->species[{_coord_macro(coord)}]"


# ---------------------------------------------------------------------------
# The recursion
# ---------------------------------------------------------------------------


def _most_shared_coord(
    processes_with_remaining: list[tuple[Process, list[Condition]]],
) -> Optional[CoordOffset]:
    """Return the CoordOffset that appears in the most Processes'
    remaining-conditions lists (or None if no Process has any condition
    left)."""
    counter: Counter[CoordOffset] = Counter()
    for _, remaining in processes_with_remaining:
        for c in remaining:
            counter[c.coord] += 1
    if not counter:
        return None
    # Stable: ties broken by lex order of the coord
    most = max(counter.items(), key=lambda kv: (kv[1], -hash(kv[0])))
    return most[0]


def _partition_by_species(
    processes_with_remaining: list[tuple[Process, list[Condition]]],
    coord: CoordOffset,
) -> tuple[dict[str, list[tuple[Process, list[Condition]]]],
            list[tuple[Process, list[Condition]]]]:
    """Split the Process set into:
    - per-species partitions keyed on the species each Process expects
      at `coord` (with that condition removed from `remaining`)
    - a "passthrough" list of Processes whose remaining conditions
      DON'T mention `coord` (to be recursed at the same level).
    """
    by_species: dict[str, list[tuple[Process, list[Condition]]]] = {}
    passthrough: list[tuple[Process, list[Condition]]] = []
    for p, remaining in processes_with_remaining:
        match = next((c for c in remaining if c.coord == coord), None)
        if match is None:
            passthrough.append((p, remaining))
            continue
        new_remaining = [c for c in remaining if c.coord != coord]
        by_species.setdefault(match.species, []).append((p, new_remaining))
    return by_species, passthrough


def _emit_subtree(
    builder: _TreeBuilder,
    processes_with_remaining: list[tuple[Process, list[Condition]]],
) -> None:
    """Recurse: emit a switch on the most-shared coord, then per-species
    branches. Leaf = `avail_sites_add(as, P_<name>, site)` — the rate
    is set once at startup via `avail_sites_set_rate` from rate_table[]."""

    # First: emit avail_sites_add for any Process whose remaining-conditions
    # list is empty (all conditions matched on the way down).
    for p, remaining in processes_with_remaining:
        if not remaining:
            builder.emit(f"avail_sites_add(as, P_{p.name}, site);")

    # Then: collect Processes that still have conditions.
    still_pending = [
        (p, rem) for (p, rem) in processes_with_remaining if rem
    ]
    if not still_pending:
        return

    coord = _most_shared_coord(still_pending)
    if coord is None:
        return  # unreachable given the filter above

    by_species, passthrough = _partition_by_species(still_pending, coord)
    if not by_species:
        # Nothing matched coord — recurse on passthrough at same level.
        if passthrough:
            _emit_subtree(builder, passthrough)
        return

    builder.emit(f"switch ({_species_at(coord)}) {{")
    builder.push()
    for species, partition in sorted(by_species.items()):
        builder.emit(f"case SP_{species.upper()}:")
        builder.push()
        _emit_subtree(builder, partition)
        builder.emit("break;")
        builder.pop()
    builder.emit("default: break;")
    builder.pop()
    builder.emit("}")

    # And tail-recurse on processes that didn't reference this coord.
    if passthrough:
        _emit_subtree(builder, passthrough)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compile_decision_tree(processes: list[Process], function_name: str) -> str:
    """Compile a list of Processes into a C function `<function_name>(lat,
    st, as, site)` that, given an anchor `site`, calls
    `avail_sites_add(as, P_<name>, site)` for every eligible Process at
    that site.

    Returns the full C source for the function (including the header
    line and braces).

    The generated function depends on:
    - `Lattice *lat`     — provides `coord_table` for NeighbourCode resolution
    - `State *st`        — provides `species[]` for condition checks
    - `AvailSites *as`   — the per-step event-availability index
    - `SP_<NAME>`        — species enum constants (from events_base.h)
    - `P_<name>`         — Process enum constants (from `emit_process_enum`)
    - `N_NEIGHBOUR_CODES` — sentinel from coord_codes.h
    - `NC_<name>`        — NeighbourCode enum constants
    - `avail_sites_add(as, P, site)` — runtime API to enrol a (proc, site)
    """
    if not processes:
        return (
            f"void {function_name}(const Lattice *lat, const State *st,\n"
            f"                {' ' * len(function_name)}AvailSites *as, int site)\n"
            f"{{ (void)lat; (void)st; (void)as; (void)site; /* no processes */ }}\n"
        )

    # Dedupe by name (translator already enforces uniqueness; double-check)
    seen: set[str] = set()
    unique: list[Process] = []
    for p in processes:
        if p.name in seen:
            raise ValueError(f"duplicate Process name in input: {p.name!r}")
        seen.add(p.name)
        unique.append(p)

    builder = _TreeBuilder()
    builder.emit(
        f"void {function_name}(const Lattice *lat, const State *st, "
        f"AvailSites *as, int site) {{"
    )
    builder.push()

    # Initial state: every Process has its full conditions list to match.
    initial = [(p, list(p.conditions)) for p in unique]
    _emit_subtree(builder, initial)

    builder.pop()
    builder.emit("}")
    return builder.render()


def emit_process_enum(processes: list[Process]) -> str:
    """Emit `enum { P_<name>, ... , N_PROCS };` for a process list."""
    if not processes:
        return "enum { N_PROCS = 0 };\n"
    lines = ["enum {"]
    for p in processes:
        lines.append(f"    P_{p.name},")
    lines.append("    N_PROCS")
    lines.append("};")
    return "\n".join(lines) + "\n"


def emit_rate_table(processes: list[Process]) -> str:
    """Emit `static const RateConst rate_table[N_PROCS] = { ... };`.

    For v2 (no Bystanders), each entry is just the scalar rate.
    """
    if not processes:
        return "/* no processes; rate_table omitted */\n"
    lines = ["typedef struct { double rate; double Ea_eV; } RateConst;",
             "static const RateConst rate_table[N_PROCS] = {"]
    for p in processes:
        if not isinstance(p.rate_constant, (int, float)):
            raise NotImplementedError(
                f"Process {p.name!r} has non-scalar rate_constant "
                f"{p.rate_constant!r}; Bystander expressions not yet supported"
            )
        lines.append(
            f"    [P_{p.name}] = {{ .rate = {float(p.rate_constant):.10e}, "
            f".Ea_eV = {p.Ea_eV:.6f} }},"
        )
    lines.append("};")
    return "\n".join(lines) + "\n"


def emit_apply_actions(processes: list[Process]) -> str:
    """Emit one apply function per Process plus a dispatch table.

    Each apply function builds a `StateAction[]` array from the Process's
    actions list (with NeighbourCode resolution per-action) and calls
    `state_apply_actions(st, acts, n, SP_VACANT)`. It returns a `HopOutcome`
    struct identifying the vacancy origin / dest sites for the runtime's
    MSD displacement bookkeeping.

    Generated signature:
        static HopOutcome apply_actions_<name>(State *st, const Lattice *lat, int site);

    `HopOutcome.v_origin` = the absolute site of the action with
    `before == "Vacant"` (if exactly one such action exists; -1 otherwise).
    `HopOutcome.v_dest`   = the absolute site of the action with
    `after == "Vacant"`  (if exactly one such action exists; -1 otherwise).
    For a simple 1NN/2NN hop, both are well-defined and the runtime uses
    them to update `unwrapped_xyz[v_idx]`. Multi-vacancy concerted events
    leave one or both at -1, in which case the runtime skips the MSD
    update with a one-time warning (decision (b) in the M-D plan).
    """
    if not processes:
        return (
            "/* no processes; apply_actions omitted */\n"
            "typedef struct { int v_origin; int v_dest; } HopOutcome;\n"
            "typedef HopOutcome (*ApplyFn)(State *st, const Lattice *lat, int site);\n"
            "static const ApplyFn apply_table[1] = { 0 };\n"
        )

    out: list[str] = []
    out.append("typedef struct { int v_origin; int v_dest; } HopOutcome;")
    out.append("typedef HopOutcome (*ApplyFn)(State *st, const Lattice *lat, int site);")
    out.append("")

    for p in processes:
        # Identify v_origin and v_dest by inspecting actions.
        origin_idx: int | None = None
        dest_idx: int | None = None
        for i, a in enumerate(p.actions):
            if a.before == "Vacant" and a.after != "Vacant":
                origin_idx = i if origin_idx is None else None  # ambiguous if >1
            if a.before != "Vacant" and a.after == "Vacant":
                dest_idx = i if dest_idx is None else None

        n_acts = len(p.actions)
        out.append(f"static HopOutcome apply_actions_{p.name}(State *st, const Lattice *lat, int site) {{")
        out.append(f"    (void)lat;")
        out.append(f"    StateAction acts[{n_acts}] = {{")
        for a in p.actions:
            target = _coord_macro(a.coord)
            out.append(f"        {{ .site = {target}, "
                       f".before = SP_{a.before.upper()}, "
                       f".after = SP_{a.after.upper()} }},")
        out.append(f"    }};")
        out.append(f"    (void)state_apply_actions(st, acts, {n_acts}, SP_VACANT);")

        if origin_idx is not None and dest_idx is not None:
            out.append(
                f"    return (HopOutcome){{ .v_origin = acts[{origin_idx}].site, "
                f".v_dest = acts[{dest_idx}].site }};"
            )
        else:
            out.append(f"    return (HopOutcome){{ .v_origin = -1, .v_dest = -1 }};")
        out.append("}")
        out.append("")

    # Dispatch table.
    out.append("static const ApplyFn apply_table[N_PROCS] = {")
    for p in processes:
        out.append(f"    [P_{p.name}] = apply_actions_{p.name},")
    out.append("};")
    return "\n".join(out) + "\n"


__all__ = (
    "compile_decision_tree",
    "emit_process_enum",
    "emit_rate_table",
    "emit_apply_actions",
)
