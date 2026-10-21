# pylatkmc/engine/io_ini.py
"""Parse the runtime's hand-rolled ``input.ini`` (mirrors runtime/src/io/config_reader.c)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunConfig:
    max_steps: int = 1_000_000
    max_time_s: float = 0.0
    sample_every: int = 1000
    summary_every: int = 0
    base_seed: int = 42
    ratetable_path: str = ""
    initconfig_path: str = ""
    output_root: str = "./output"
    temperature_K: float = 500.0
    rng_replay_path: str = ""
    initconfig_abs: Path = field(default_factory=Path)
    output_root_abs: Path = field(default_factory=Path)


def _strip_comment(value: str) -> str:
    for marker in ("#", ";"):
        i = value.find(marker)
        if i >= 0:
            value = value[:i]
    return value.strip()


def _resolve(base_dir: Path, raw: str) -> Path:
    raw = raw.strip()
    if raw.startswith("./"):
        raw = raw[2:]
    p = Path(raw)
    return p if p.is_absolute() else (base_dir / p)


def parse_input_ini(path: str | Path) -> RunConfig:
    path = Path(path)
    base_dir = path.parent
    cfg = RunConfig()
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        val = _strip_comment(raw)
        if section == "run":
            if key == "max_steps":
                cfg.max_steps = int(val)
            elif key == "max_time_s":
                cfg.max_time_s = float(val)
            elif key == "sample_every":
                cfg.sample_every = int(val)
            elif key == "summary_every":
                cfg.summary_every = int(val)
            elif key == "base_seed":
                cfg.base_seed = int(val)
        elif section == "paths":
            if key == "ratetable_path":
                cfg.ratetable_path = val
            elif key == "initconfig_path":
                cfg.initconfig_path = val
            elif key == "output_root":
                cfg.output_root = val
        elif section == "physics":
            if key == "temperature_K":
                cfg.temperature_K = float(val)
        elif section == "validation" and key == "rng_replay_path":
            cfg.rng_replay_path = val
    cfg.initconfig_abs = _resolve(base_dir, cfg.initconfig_path)
    cfg.output_root_abs = _resolve(base_dir, cfg.output_root)
    return cfg
