"""Codegen — turn a ModelSpec into specialised C source files.

This module has two responsibilities:

1. `evaluate_template(template_str, **context) -> str` — the kmos-style
   preprocessor. Ports the inverted-convention of
   `kmos-main/kmos/utils/__init__.py:1449` so our templates look exactly
   like kmos's .mpy files:

       Python line (unprefixed)   →  executed as Python
       '#@ <text>'                →  literal output, evaluated as an
                                     **f-string** against the exec's
                                     local namespace (supports method
                                     calls: {name.upper()}, arithmetic,
                                     attribute access, indexing)
       '#@' (bare)                →  blank line
       Other blank lines          →  passed through verbatim

   Convention for literal `{` and `}` in C output: **double them** as
   `{{` and `}}` (f-string convention). The templates in this package
   already follow that rule.

2. `generate(spec, out_dir)` — render the four templates
   (events.h, ratetable.h, ratetable.c, avail.c) and write them to
   `out_dir/`. Also writes `key_spec.json` for human inspection and
   debugging.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pylatkmc.spec import ModelSpec

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_PREFIX = "#@"


def evaluate_template(template: str, **context: Any) -> str:
    """kmos-style preprocessor.

    See module docstring for syntax. Returns the fully rendered text.
    """
    namespace: dict[str, Any] = dict(context)
    namespace["result"] = ""

    python_src: list[str] = []
    for raw_line in template.splitlines(keepends=True):
        # Preserve the original line's leading whitespace so emitted Python
        # control flow (bare Python lines) nest correctly.
        lstripped = raw_line.lstrip()
        indent_len = len(raw_line) - len(lstripped)
        indent = raw_line[:indent_len]

        if lstripped.startswith(_PREFIX + " "):
            # '#@ <text>' — literal line. Strip the three-char prefix, drop
            # the trailing newline (we'll re-add it ourselves), and emit as
            # an f-string so method calls / arithmetic in {...} work.
            literal = lstripped[len(_PREFIX) + 1:]
            if literal.endswith("\n"):
                literal = literal[:-1]
            # repr() gives us a safely quoted + escaped string literal with
            # correct handling of backslashes, quotes, and special chars.
            # Prepend 'f' to turn it into an f-string evaluated in scope.
            emit = "f" + repr(literal)
            python_src.append(f"{indent}result += {emit}\n")
            python_src.append(f'{indent}result += "\\n"\n')
        elif lstripped.rstrip("\n") == _PREFIX:
            # Bare '#@' — emit a single newline.
            python_src.append(f'{indent}result += "\\n"\n')
        else:
            # Unprefixed line — treat as Python. This includes blank lines,
            # which just pass through and don't affect output.
            python_src.append(raw_line)

    compiled_src = "".join(python_src)
    try:
        exec(compile(compiled_src, "<template>", "exec"), namespace)
    except Exception as e:
        # Surface the compiled Python so template errors are debuggable.
        raise RuntimeError(
            f"evaluate_template failed: {e}\n\n"
            f"----- compiled Python -----\n{compiled_src}\n"
            f"---------------------------"
        ) from e
    return namespace["result"]


def render_template_file(
    template_name: str, spec: ModelSpec, **extra: Any
) -> str:
    """Load a .tmpl file by name and render it against the given spec."""
    path = _TEMPLATES_DIR / f"{template_name}.tmpl"
    if not path.is_file():
        raise FileNotFoundError(f"template not found: {path}")
    return evaluate_template(path.read_text(), spec=spec, **extra)


def generate(spec: ModelSpec, out_dir: str | Path) -> list[Path]:
    """Render all per-model C files and write them to `out_dir`.

    Returns the list of written paths. Overwrites existing files.
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for tmpl_name in ("events.h", "ratetable.h", "ratetable.c", "avail.c"):
        rendered = render_template_file(tmpl_name, spec)
        path = out / tmpl_name
        path.write_text(rendered)
        written.append(path)

    # Human-readable key spec alongside the generated C. Useful for debugging
    # rate-cube keying and for the dump tool in M3b.
    key_spec = {
        "name": spec.name,
        "lattice": spec.lattice,
        "species": spec.species,
        "shells": [{"name": s.name, "cutoff_mult": s.cutoff_mult} for s in spec.shells],
        "axes": [
            {"name": name, "max": max_bin, "stride": stride}
            for (name, max_bin), stride in zip(
                spec.all_axes(), spec.strides(), strict=True
            )
        ],
        "n_cube_entries": spec.n_cube_entries(),
        "temperature_K": spec.rate_data.temperature_K,
        "k0_Hz": spec.rate_data.k0_Hz,
    }
    key_spec_path = out / "key_spec.json"
    key_spec_path.write_text(json.dumps(key_spec, indent=2, default=str) + "\n")
    written.append(key_spec_path)

    return written
