"""Shared binary-format helpers for .kmcrt (rate table) and .kmcinit (initial config).

Both formats share a simple layout:

    u8[8]   magic
    u32     header_bytes (little-endian)
    u8[H]   JSON header (UTF-8), padded to 4-byte alignment after the JSON
    <payload follows, little-endian packed arrays>

The payload schema is format-specific and declared by the header.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, BinaryIO

RATETABLE_MAGIC = b"KMCRTv01"
INITCONFIG_MAGIC = b"KMCICv01"


def _pad4(n: int) -> int:
    return (4 - (n % 4)) % 4


def write_header(fp: BinaryIO, magic: bytes, header: dict[str, Any]) -> None:
    """Write magic + u32 header_bytes + JSON header, pad to 4-byte alignment."""
    if len(magic) != 8:
        raise ValueError(f"magic must be exactly 8 bytes, got {len(magic)}")
    payload = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    pad = _pad4(len(payload))
    fp.write(magic)
    fp.write(struct.pack("<I", len(payload) + pad))
    fp.write(payload)
    if pad:
        fp.write(b"\x00" * pad)


def read_header(fp: BinaryIO, expected_magic: bytes) -> dict[str, Any]:
    """Read and validate magic + JSON header."""
    magic = fp.read(8)
    if magic != expected_magic:
        raise ValueError(f"bad magic: got {magic!r}, expected {expected_magic!r}")
    (header_bytes,) = struct.unpack("<I", fp.read(4))
    raw = fp.read(header_bytes)
    # strip trailing nulls from padding
    raw = raw.rstrip(b"\x00")
    return json.loads(raw.decode("utf-8"))


def open_for_read(path: str | Path, expected_magic: bytes) -> tuple[dict[str, Any], BinaryIO]:
    fp = open(path, "rb")
    header = read_header(fp, expected_magic)
    return header, fp
