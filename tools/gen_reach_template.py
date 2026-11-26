#!/usr/bin/env python3
"""Derive the reach template of a generated touchup_a() for incremental builds.

CMake runs this at configure and at every build when PYLATKMC_INCREMENTAL is ON. It reads a model's generated
proclist.c and writes pt_reach_template.h with two code lists:

  READ   every NeighbourCode X whose species touchup_a reads, as
         st->species[lat->coord_table[site * N_NEIGHBOUR_CODES + X]]
  SHELL  every centre of a shell-count loop (NC_ANCHOR for `int _m = site;`);
         the loop reads the species of nn1(centre)

From them the runtime builds the static reach of an anchor a:

  {a} + nn1(a) + {coord(a, X) for X in READ} + nn1(coord(a, X)) for X in SHELL

(nn1(a) is there because the active filter reads it.) A site outside that
reach cannot change what is enrolled at a. That holds only if touchup_a reads
nothing else, so every line of it must be one of the forms the decision-tree
emitter writes (pylatkmc/decision_tree.py), in the block structure it writes
them in: species, coord_table and nn1 reads, and enrolments at `site`. Any
other line is an error that names the line. There is no fallback to a smaller
reach.

The tool reads the code as the compiler does: with comments blanked, over the
whole file. What would make those two views differ is an error (line splices,
trigraphs, a byte-order mark, control characters, non-ASCII outside comments
and literals, an unclosed comment, any preprocessor line but the generated
includes), and so is a second touchup_a. The body ends where its
braces balance. What it does assume: the generated names (SP_*, P_*, NC_*)
mean what the generated headers and enum say. It guards against emitter
changes and hand edits, not against C written to defeat it.

Second-neighbour (nn2) shells are rejected: the reach covers nn1 shells only,
so models that count nn2 shells cannot use the incremental build.

Ported from the incremental-package prototype's gen_reach_template.py, whose
pattern searches are replaced by the line-by-line check.

Usage: gen_reach_template.py <proclist.c> <out.h>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# NeighbourCode, in enum order (runtime/src/core/coord_codes.h).
CODES = (
    "NC_ANCHOR",
    "NC_NN1_PX",
    "NC_NN1_MX",
    "NC_NN1_PY",
    "NC_NN1_MY",
    "NC_NN1_DOWN_PP",
    "NC_NN1_DOWN_PM",
    "NC_NN1_DOWN_MP",
    "NC_NN1_DOWN_MM",
    "NC_NN1_UP_PP",
    "NC_NN1_UP_PM",
    "NC_NN1_UP_MP",
    "NC_NN1_UP_MM",
    "NC_NN2_DIAG_PP",
    "NC_NN2_DIAG_PM",
    "NC_NN2_DIAG_MP",
    "NC_NN2_DIAG_MM",
    "NC_NN2_PX",
    "NC_NN2_MX",
    "NC_NN2_PY",
    "NC_NN2_MY",
    "NC_NN2_PZ",
    "NC_NN2_MZ",
)

SIGNATURE = "void touchup_a(const Lattice *lat, const State *st, AvailSites *as, int site) {"

_COORD = r"lat->coord_table\[site \* N_NEIGHBOUR_CODES \+ (?P<code>NC_\w+)\]"
_NEIGHBOUR_SPECIES = r"st->species\[lat->nn1_indices\[_i\]\]"
_COUNTER = r"nr_\w+"
_SPECIES = r"SP_(?:VACANT|NI|FE|CR)"  # events_base.h
_TEST = rf"{_COUNTER} (?:==|>=) \d+"
_GATE = rf"{_TEST}(?: && {_TEST})*"
_ADD = r"avail_sites_add\(as, P_\w+, site\);"

# Where a line may stand: the kind of block it is directly inside.
_PLAIN = ("body", "block", "switch")
_SWITCH = ("switch",)
_BLOCK = ("block",)
_SHELL = ("shell",)  # if (_m >= 0 && _m < lat->n_sites) {
_LOOP = ("loop",)  # for over nn1(_m)
_AFTER_CENTRE = ("centre",)  # the line straight after `int _m = ...;`

# (form, pattern, where it may stand, the kind of block it opens)
FORMS = tuple(
    (form, re.compile(pattern), where, opens)
    for form, pattern, where, opens in (
        ("switch", r"switch \(st->species\[site\]\) \{", _PLAIN, "switch"),
        ("read", rf"switch \(st->species\[{_COORD}\]\) \{{", _PLAIN, "switch"),
        ("case", rf"case {_SPECIES}:", _SWITCH, None),
        ("break", r"break;", _SWITCH, None),
        ("default", r"default: break;", _SWITCH, None),
        ("block", r"\{", _PLAIN, "block"),
        ("guard", rf"if \({_GATE}\) \{{", _PLAIN, "block"),
        ("add", rf"(?:if \({_GATE}\) )?{_ADD}", _PLAIN, None),
        (
            "declare",
            rf"int (?P<counter>{_COUNTER}) = -1;",
            _BLOCK,
            None,
        ),
        ("anchor_centre", r"int _m = site;", _BLOCK, None),
        ("centre", rf"int _m = {_COORD};", _BLOCK, None),
        ("stub_guard", r"if \(_m >= 0 && _m < lat->n_sites\) \{", _AFTER_CENTRE, "shell"),
        ("zero", rf"{_COUNTER} = 0;", _SHELL, None),
        (
            "loop",
            r"for \(int _i = lat->nn1_offsets\[_m\]; _i < lat->nn1_offsets\[_m \+ 1\]; \+\+_i\) \{",
            _SHELL,
            "loop",
        ),
        ("neighbour", rf"const int _sp = {_NEIGHBOUR_SPECIES};", _LOOP, None),
        ("count", rf"if \(_sp != SP_VACANT && _sp < SP_COUNT\) {_COUNTER}\+\+;", _LOOP, None),
        ("count", rf"if \({_NEIGHBOUR_SPECIES} == {_SPECIES}\) {_COUNTER}\+\+;", _LOOP, None),
    )
)

# Literals first, so that a comment mark inside one is not a comment.
LEXEME = re.compile(
    r'(?P<literal>"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')'
    r"|(?P<comment>/\*.*?\*/|//[^\n]*)"
    r"|(?P<unclosed>/\*)",
    re.S,
)
GENERATED_INCLUDE = re.compile(
    r'#include (?:<stdint\.h>|"(?:events_base|coord_codes|lattice|state|avail_sites)\.h")'
)


class TemplateError(Exception):
    """touchup_a has a form the reach cannot model."""


def _rejected(where: str, text: str, reason: str) -> TemplateError:
    return TemplateError(f"{where}: {reason}\n    {text}")


def _code_lines(source: str, name: str) -> list[str]:
    """`source` as the compiler reads it, comments blanked, line numbers unchanged."""

    def error_at(pos: int, reason: str) -> TemplateError:
        lineno = source.count("\n", 0, pos) + 1
        text = source.split("\n")[lineno - 1].strip()
        return _rejected(f"{name}:{lineno}", text, reason)

    if source.startswith("\ufeff"):
        raise error_at(0, "byte-order mark")
    if m := re.search(r"[\x00-\x08\x0b-\x1f\x7f]", source):
        raise error_at(m.start(), "control character")
    if m := re.search(r"\\[^\S\n]*\n", source):
        raise error_at(m.start(), "line splice")
    if m := re.search(r"\?\?[=/'()!<>-]", source):
        raise error_at(m.start(), "trigraph")

    def blank(m: re.Match[str]) -> str:
        if m["unclosed"]:
            raise error_at(m.start(), "unclosed comment")
        return m["literal"] or " " + "\n" * m.group().count("\n")

    code = LEXEME.sub(blank, source).split("\n")
    # Compilers and Python disagree on which of these characters are blank.
    bare = LEXEME.sub(lambda m: " " + "\n" * m.group().count("\n"), source).split("\n")
    for i, line in enumerate(bare):
        if not line.isascii():
            shown = source.split("\n")[i].strip()
            raise _rejected(f"{name}:{i + 1}", shown, "non-ASCII outside comments and literals")
    return code


def _function_start(code: list[str], written: list[str], name: str) -> int:
    """0-based line of the file's one touchup_a."""
    for i, line in enumerate(code):
        text = line.strip()
        if text.startswith(("#", "%:")) and not GENERATED_INCLUDE.fullmatch(text):
            raise _rejected(
                f"{name}:{i + 1}",
                written[i].strip(),
                "preprocessor line that a generated proclist does not have",
            )
    starts = [i for i, line in enumerate(code) if line.rstrip() == SIGNATURE]
    if len(starts) != 1 or sum(len(re.findall(r"\btouchup_a\b", line)) for line in code) != 1:
        raise TemplateError(
            f"{name}: expected exactly one `{SIGNATURE}`, and no other touchup_a; "
            "cannot read touchup_a"
        )
    return starts[0]


def derive(source: str, name: str) -> tuple[list[str], list[str]]:
    """(READ, SHELL) of the touchup_a in `source`, each in enum order."""
    code = _code_lines(source, name)
    written = source.split("\n")
    start = _function_start(code, written, name)

    read: set[str] = set()
    shell: set[str] = set()
    n_adds = 0
    blocks = ["body"]  # kinds of the open blocks, innermost last
    counters: list[set[str]] = [set()]  # and the counters each of them declares
    after_centre = False

    for lineno, line in enumerate(code[start + 1 :], start=start + 2):
        text = line.strip()
        shown = written[lineno - 1].strip()
        where = f"{name}:{lineno}"
        if not text:
            continue

        if text == "}":
            if after_centre:
                raise _rejected(where, shown, "shell centre without its stub-site guard")
            blocks.pop()
            counters.pop()
            # Only the function's own brace is unindented. Elsewhere one would
            # have ended a plain text scan early, with a smaller reach.
            if (line.rstrip() == "}") != (not blocks):
                raise _rejected(where, shown, "brace indentation does not match the block depth")
            if not blocks:
                break
            continue

        found = next(((f, m) for f in FORMS if (m := f[1].fullmatch(text))), None)
        if found is None:
            if "nn2_offsets" in text or "nn2_indices" in text:
                raise _rejected(
                    where,
                    shown,
                    "second-neighbour (nn2) shells are not modelled: the reach covers nn1 "
                    "shells only, so this model cannot be built with PYLATKMC_INCREMENTAL",
                )
            raise _rejected(
                where, shown, "touchup_a line of a form the reach template cannot model"
            )

        (form, _, allowed, opens), match = found
        here = "centre" if after_centre else blocks[-1]
        if here not in allowed:
            raise _rejected(where, shown, f"`{form}` line out of place (inside: {here})")
        after_centre = form in ("anchor_centre", "centre")

        if form in ("read", "centre"):
            nc = match["code"]
            if nc not in CODES:
                raise _rejected(where, shown, f"unknown neighbour code {nc}")
            (read if form == "read" else shell).add(nc)
        elif form == "anchor_centre":
            shell.add("NC_ANCHOR")
        elif form == "declare":
            counters[-1].add(match["counter"])
        elif form == "add":
            n_adds += 1

        # A counter that no open block declared would be some outside variable.
        used = re.findall(rf"\b{_COUNTER}", text)  # P_* names cannot match: \b
        if not set(used) <= set().union(*counters):
            raise _rejected(where, shown, "count variable that touchup_a does not declare")
        if opens:
            blocks.append(opens)
            counters.append(set())
    else:
        raise TemplateError(f"{name}: could not find the end of touchup_a")

    if not n_adds:
        raise TemplateError(f"{name}: touchup_a enrols nothing; cannot derive a reach")
    return [c for c in CODES if c in read], [c for c in CODES if c in shell]


def render(read: list[str], shell: list[str], name: str) -> str:
    out = [
        f"/* GENERATED by tools/gen_reach_template.py from {name}. DO NOT EDIT. */",
        "#ifndef PT_REACH_TEMPLATE_H",
        "#define PT_REACH_TEMPLATE_H",
    ]
    for label, codes in (("READ", read), ("SHELL", shell)):
        # ISO C has no empty initialiser list; the count is what the runtime loops over.
        listed = ", ".join(codes) or "0"
        out.append(f"static const int PT_{label}_CODES[] = {{ {listed} }};")
        out.append(f"static const int PT_N_{label} = {len(codes)};")
    out.append("#endif")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: gen_reach_template.py <proclist.c> <out.h>", file=sys.stderr)
        return 2
    src, out = Path(argv[1]), Path(argv[2])
    try:
        read, shell = derive(src.read_text(encoding="utf-8"), str(src))
    except (TemplateError, OSError, UnicodeDecodeError) as exc:
        out.unlink(missing_ok=True)  # never leave an earlier template to build from
        print(f"gen_reach_template.py: {exc}", file=sys.stderr)
        return 1

    header = render(read, shell, str(src))
    if not out.is_file() or out.read_text(encoding="utf-8") != header:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(header, encoding="utf-8")
    print(f"reach template: READ {len(read)}, SHELL {len(shell)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
