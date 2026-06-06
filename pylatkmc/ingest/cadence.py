"""Trajectory cadence helpers — map KMC step ↔ trajectory frame.

pyKMC writes ``trajkmc.xyz`` once per *sampled* step. Frame index = step //
sample_every (frame 0 = the initial minimised config). Most production runs are
1:1 (sample_every = 1). This module resolves the cadence and the
frame-just-before-a-firing-step needed to recover the event's min1.

Pure-logic / stdlib-only so it is unit-testable without ASE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def count_xyz_frames(traj_path: str | Path) -> int:
    """Count frames in an extxyz/xyz file by reading the per-frame natom header.

    Each frame starts with a line containing just the atom count. We seek by
    reading that integer and skipping ``natoms + 1`` lines per frame, so cost is
    O(frames) line-reads of the header, not O(atoms).
    """
    path = Path(traj_path)
    n_frames = 0
    with open(path) as f:
        while True:
            header = f.readline()
            if not header:
                break
            header = header.strip()
            if header == "":
                continue
            try:
                natoms = int(header)
            except ValueError as exc:  # malformed; stop counting defensively
                raise ValueError(
                    f"{path}: expected an atom-count header, got {header!r}"
                ) from exc
            # skip the comment line + natoms coordinate lines
            for _ in range(natoms + 1):
                if not f.readline():
                    return n_frames  # truncated final frame
            n_frames += 1
    return n_frames


def parse_sample_every(input_in_path: str | Path, default: int = 1) -> int:
    """Read ``sample_every`` (or legacy ``dump``/``n_dump``) from a pyKMC input.in.

    Returns ``default`` (1) when the key is absent — the common case for the
    existing production runs, which dump every step.
    """
    path = Path(input_in_path)
    if not path.is_file():
        return default
    pat = re.compile(r"^\s*(sample_every|n_dump|dump_every)\s*=\s*(\d+)", re.IGNORECASE)
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if m:
                v = int(m.group(2))
                return v if v > 0 else default
    return default


@dataclass(frozen=True)
class Cadence:
    """Resolved step↔frame mapping for one simulation."""

    sample_every: int
    n_frames: int
    max_step: int

    def step_on_cadence(self, step: int) -> bool:
        """True if the pre-firing config for ``step`` is an exactly-stored frame."""
        return step % self.sample_every == 0

    def frame_for_step(self, step: int) -> int | None:
        """Frame index holding the configuration *entering* ``step`` (i.e. its
        min1). Returns None when that frame is off-cadence or out of range.

        Frame index == step // sample_every. Frame N is the state after N
        sampled steps == the state the event at step N+1... actually the state
        *before* step (N+1)*sample_every fires. For 1:1 cadence, frame N is the
        config min1 of the event selected at step N+1 — but we key on the event
        that fired AT ``step`` having min1 = frame (step-1)//... To keep this
        unambiguous we return the frame whose index == step // sample_every,
        which for 1:1 is the post-step config; callers use ``frame_before_step``
        for the pre-firing min1.
        """
        idx = step // self.sample_every
        if not self.step_on_cadence(step):
            return None
        if idx < 0 or idx >= self.n_frames:
            return None
        return idx

    def frame_before_step(self, step: int) -> int | None:
        """Frame index of the min1 (config entering ``step``).

        pyKMC writes frame 0 = initial config, then appends one frame *after*
        each sampled step. So the configuration that the event at ``step`` acts
        on is frame ``step - 1`` for 1:1 cadence (frame index = (step-1)//
        sample_every, valid only when (step-1) is on cadence). Returns None if
        unavailable.
        """
        prev = step - 1
        if prev < 0:
            return None
        if prev % self.sample_every != 0:
            return None
        idx = prev // self.sample_every
        if idx < 0 or idx >= self.n_frames:
            return None
        return idx
