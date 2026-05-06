"""pylatkmc — compile a ModelSpec into specialised C (pattern-DB proclist.c).

Public API:

    from pylatkmc import load, ModelSpec, generate

    spec = load("models/ni_fe_cr_v1.kmcspec.toml")   # TOML -> ModelSpec
    generate(spec, out_dir=...)                       # writes proclist.c + proclist.h

In v0.2 the codegen emits a single per-model `proclist.c` (plus a
companion `proclist.h`) bundling the Process catalogue, rate table,
apply functions, and decision tree. The rate cube and .kmcrt format
that earlier versions used are retired.
"""
from __future__ import annotations

from pylatkmc.codegen import generate
from pylatkmc.loader import load
from pylatkmc.spec import KeyAxis, ModelSpec, Shell

__all__ = [
    "KeyAxis",
    "ModelSpec",
    "Shell",
    "generate",
    "load",
]
