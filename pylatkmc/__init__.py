"""pylatkmc — compile a ModelSpec into specialised C + binary rate table.

Public API:

    from pylatkmc import load, ModelSpec, generate, build_rate_table

    spec = load("models/ni_fe_cr_v1.kmcspec.toml")   # TOML -> ModelSpec
    generate(spec, out_dir=...)                       # C source files
    build_rate_table(spec, classified_csv=..., out_path=...)  # .kmcrt binary
"""
from __future__ import annotations

from pylatkmc.codegen import generate
from pylatkmc.loader import load
from pylatkmc.ratebuilder import build as build_rate_table
from pylatkmc.spec import KeyAxis, ModelSpec, Shell

__all__ = [
    "KeyAxis",
    "ModelSpec",
    "Shell",
    "build_rate_table",
    "generate",
    "load",
]
