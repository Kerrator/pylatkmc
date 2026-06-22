"""Pure-Python (no-codegen) reference KMC engine.

A second consumer of ``translator.translate_all(...) -> list[Process]``: it
interprets Process objects directly and runs a BKL loop in Python, instead of
emitting C. Validated statistically against the C+MPI engine.
"""

from __future__ import annotations
