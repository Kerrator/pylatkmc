"""Binary-format helpers for .kmcrt rate tables.

Format (little-endian throughout):

    u8[8]   magic   = 'KMCRTv01'
    u32     header_bytes
    u8[H]   JSON header (UTF-8, padded to 4-byte alignment)
    u32     n_entries
    f32[n]  rate_s_inv
    f32[n]  Ea_eV
    u32[n]  count           (0 => filled by fallback)

The JSON header shape is defined by pylatkmc's generated ratetable.c; see
`pylatkmc.ratebuilder.build_header` for the field set.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, BinaryIO

RATETABLE_MAGIC = b"KMCRTv01"


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
    raw = fp.read(header_bytes).rstrip(b"\x00")
    return json.loads(raw.decode("utf-8"))


def open_for_read(
    path: str | Path, expected_magic: bytes = RATETABLE_MAGIC
) -> tuple[dict[str, Any], BinaryIO]:
    fp = open(Path(path), "rb")
    return read_header(fp, expected_magic), fp
