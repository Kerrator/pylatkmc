"""TOML -> ModelSpec loader.

The spec file's relative paths (rate_data.primary, .family_table, .fallback_scalar)
are resolved against the spec file's parent directory so specs stay portable.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib  # stdlib
else:
    import tomli as tomllib  # type: ignore[no-redef]

from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell


def load(path: str | Path) -> ModelSpec:
    """Load a .kmcspec.toml file and return a validated ModelSpec."""
    spec_path = Path(path).resolve()
    if not spec_path.is_file():
        raise FileNotFoundError(f"spec file not found: {spec_path}")
    with spec_path.open("rb") as f:
        raw = tomllib.load(f)

    # Resolve rate_data paths relative to the spec file's directory.
    rd_raw: dict[str, Any] = dict(raw.get("rate_data", {}))
    for key in ("primary", "family_table", "fallback_scalar"):
        if key in rd_raw and rd_raw[key] is not None:
            rd_raw[key] = (spec_path.parent / rd_raw[key]).resolve()

    spec = ModelSpec(
        name=raw["name"],
        lattice=raw.get("lattice", "fcc"),
        species=list(raw["species"]),
        shells=[Shell(**s) for s in raw["shells"]],
        key=Key(axes=[KeyAxis(**a) for a in raw["key"]["axes"]]),
        rate_data=RateData(**rd_raw),
    )
    return spec
