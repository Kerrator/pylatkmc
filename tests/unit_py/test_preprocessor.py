"""Unit tests for pylatkmc.codegen.evaluate_template.

Semantics (mirrors kmos-main/kmos/utils/__init__.py:1449):

    '#@ <text>\\n'   → literal output line (text), with {name} substitution
    '#@\\n'          → single blank line of output
    anything else    → Python source (executed verbatim)

Python control flow is expressed as bare Python lines (no prefix); the literal
'#@ ...' lines are emitted inside whatever block contains them.
"""
from __future__ import annotations

import textwrap

import pytest

from pylatkmc.codegen import evaluate_template


def _dedent(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n")


# ------------------------------------------------------------------
# Basic cases
# ------------------------------------------------------------------
def test_empty_template_returns_empty() -> None:
    assert evaluate_template("") == ""


def test_literal_only_line() -> None:
    out = evaluate_template("#@ hello world\n")
    assert out == "hello world\n"


def test_bare_hash_at_emits_newline() -> None:
    out = evaluate_template("#@ before\n#@\n#@ after\n")
    assert out == "before\n\nafter\n"


def test_variable_substitution() -> None:
    out = evaluate_template("#@ hello {name}\n", name="Stephen")
    assert out == "hello Stephen\n"


def test_expression_substitution() -> None:
    out = evaluate_template("#@ upper: {name.upper()}\n", name="fe")
    assert out == "upper: FE\n"


# ------------------------------------------------------------------
# Python control flow
# ------------------------------------------------------------------
def test_for_loop() -> None:
    tmpl = _dedent("""
        for elem in elements:
            #@ #define SP_{elem.upper()}
    """)
    out = evaluate_template(tmpl, elements=["ni", "fe", "cr"])
    assert out == "#define SP_NI\n#define SP_FE\n#define SP_CR\n"


def test_if_true_branch() -> None:
    tmpl = _dedent("""
        if flag:
            #@ yes
        else:
            #@ no
    """)
    out = evaluate_template(tmpl, flag=True)
    assert out == "yes\n"


def test_if_false_branch() -> None:
    tmpl = _dedent("""
        if flag:
            #@ yes
        else:
            #@ no
    """)
    out = evaluate_template(tmpl, flag=False)
    assert out == "no\n"


def test_nested_for_and_if() -> None:
    tmpl = _dedent("""
        for n in values:
            if n > 0:
                #@ pos {n}
            else:
                #@ neg {n}
    """)
    out = evaluate_template(tmpl, values=[1, -2, 3])
    assert out == "pos 1\nneg -2\npos 3\n"


def test_python_can_set_vars_used_by_literal() -> None:
    tmpl = _dedent("""
        x = 42
        #@ the answer is {x}
    """)
    out = evaluate_template(tmpl)
    assert out == "the answer is 42\n"


# ------------------------------------------------------------------
# Literal-line escaping
# ------------------------------------------------------------------
def test_braces_must_be_doubled_for_literal_output() -> None:
    """C-style '{ }' in output requires the .format() convention '{{ }}'."""
    out = evaluate_template("#@ struct {{ int x; }};\n")
    assert out == "struct { int x; };\n"


def test_mixed_literal_braces_and_substitution() -> None:
    out = evaluate_template(
        "#@ if (sp == SP_{elem}) {{ n_{elem}++; }}\n", elem="FE"
    )
    assert out == "if (sp == SP_FE) { n_FE++; }\n"


def test_backslash_n_in_literal_is_preserved() -> None:
    """Literal backslash-n (two chars) in a '#@' line must appear verbatim
    in the output, not be interpreted as a newline."""
    template = '#@ printf("\\n");\n'      # template has one line
    expected = 'printf("\\n");\n'
    assert evaluate_template(template) == expected


# ------------------------------------------------------------------
# Fully featured: a mini C snippet
# ------------------------------------------------------------------
def test_generates_valid_c_snippet() -> None:
    tmpl = _dedent("""
        #@ typedef enum {{
        for i, name in enumerate(species):
            #@     SP_{name.upper()} = {i},
        #@     SP_COUNT
        #@ }} Species;
    """)
    out = evaluate_template(tmpl, species=["vacant", "ni", "fe"])
    expected = _dedent("""
        typedef enum {
            SP_VACANT = 0,
            SP_NI = 1,
            SP_FE = 2,
            SP_COUNT
        } Species;
    """)
    assert out == expected


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------
def test_template_python_error_is_surfaced() -> None:
    with pytest.raises(RuntimeError, match="compiled Python"):
        evaluate_template("for x in undefined_name:\n    #@ x\n")


def test_unknown_substitution_variable_raises() -> None:
    # str.format raises KeyError when the name isn't in locals().
    with pytest.raises(RuntimeError, match="compiled Python"):
        evaluate_template("#@ hello {nope}\n")
