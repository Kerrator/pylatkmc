"""Ctypes tests for `initconfig_load`'s header range checks (`runtime/src/io/initconfig.c`).

Site indices and CSR offsets are int32 in the runtime. A `.kmcinit` header
whose `n_sites` / `nn1_count` / `nn2_count` exceeds INT32_MAX used to be cast
straight to int32, so 2^32 + 8 sites silently became an 8-site lattice
(large-system-scaling/06). It must now be refused with -EOVERFLOW, and a
negative count that would wrap to a valid int32 with -EPROTO. The files here
are tiny: only the header claims the huge count, nothing large is allocated.

The header is written by `tools/kmcfmt.py` (the format's own writer); the
payload is a valid 8-site, edge-free lattice packed in `initconfig.c`'s
(authoritative) field order. No numpy / scipy needed, so these run in a
`.[dev]`-only install; they skip without cc.
"""

from __future__ import annotations

import ctypes
import errno
import importlib.util
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
RUNTIME = REPO_ROOT / "runtime" / "src"
SOURCES = [
    RUNTIME / "io" / "initconfig.c",
    RUNTIME / "core" / "kmcfmt.c",
    RUNTIME / "core" / "json_mini.c",
    RUNTIME / "core" / "state.c",
    RUNTIME / "core" / "lattice.c",
    RUNTIME / "core" / "coord_codes.c",
]
N_SITES = 8
INT32_MAX = 2**31 - 1


def _kmcfmt() -> ModuleType:
    """tools/kmcfmt.py (the .kmcinit header reader/writer), loaded by path."""
    spec = importlib.util.spec_from_file_location("_kmcfmt_tool", REPO_ROOT / "tools" / "kmcfmt.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def libinit(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    builddir = tmp_path_factory.mktemp("initconfig_lib")
    libpath = builddir / ("libinitconfig.dylib" if sys.platform == "darwin" else "libinitconfig.so")
    cmd = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-fPIC",
        "-shared",
        "-I",
        str(RUNTIME / "core"),
        "-I",
        str(RUNTIME / "io"),
        *map(str, SOURCES),
        "-lm",
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"initconfig.c + deps failed to compile:\n{res.stderr}")
    lib = ctypes.CDLL(str(libpath))
    lib.initconfig_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
    ]
    lib.initconfig_load.restype = ctypes.c_int
    lib.lattice_free.argtypes = [ctypes.c_void_p]
    lib.lattice_free.restype = None
    lib.state_free.argtypes = [ctypes.c_void_p]
    lib.state_free.restype = None
    return lib


def _write_kmcinit(path: Path, *, n_sites: int, nn1_count: int = 0, nn2_count: int = 0) -> Path:
    """A valid 8-site, edge-free .kmcinit whose HEADER claims the given counts."""
    kf = _kmcfmt()
    header = {
        "version": 1,
        "n_sites": n_sites,
        "n_layers": 1,
        "cell": [10.0, 10.0, 10.0],
        "nn_dist": 2.49,
        "nn1_count": nn1_count,
        "nn2_count": nn2_count,
    }
    n = N_SITES
    payload = b"".join(
        [
            struct.pack("<I", 1),  # payload version
            struct.pack(f"<{3 * n}f", *[2.49 * i for i in range(n) for _ in range(3)]),
            struct.pack(f"<{n + 1}i", *([0] * (n + 1))),  # nn1_offsets (no edges)
            struct.pack(f"<{n + 1}i", *([0] * (n + 1))),  # nn2_offsets (no edges)
            bytes(n),  # layer_index
            bytes(n),  # site_class
            bytes([0] + [1] * (n - 1)),  # initial_species: 1 vacancy + Ni
        ]
    )
    with open(path, "wb") as fp:
        kf.write_header(fp, kf.INITCONFIG_MAGIC, header)
        fp.write(payload)
    return path


def _load(lib: ctypes.CDLL, path: Path) -> tuple[int, int]:
    """initconfig_load into opaque Lattice/State buffers; returns (rc, n_sites)."""
    lat = ctypes.create_string_buffer(4096)
    st = ctypes.create_string_buffer(4096)
    rc = lib.initconfig_load(str(path).encode(), lat, st, 0)
    n_sites = ctypes.c_int32.from_buffer(lat).value  # Lattice.n_sites is the first field
    if rc == 0:
        lib.lattice_free(lat)
        lib.state_free(st)
    return rc, n_sites


def test_valid_header_loads(libinit: ctypes.CDLL, tmp_path: Path) -> None:
    rc, n = _load(libinit, _write_kmcinit(tmp_path / "ok.kmcinit", n_sites=N_SITES))
    assert (rc, n) == (0, N_SITES)


@pytest.mark.parametrize(
    ("field", "value", "expected_rc"),
    [
        # Truncates to 8 == the payload: loaded silently as an 8-site lattice before.
        ("n_sites", 2**32 + N_SITES, -errno.EOVERFLOW),
        # INT32_MAX + 1 truncates to INT32_MIN.
        ("n_sites", INT32_MAX + 1, -errno.EOVERFLOW),
        # Truncate to 0 == the CSR edge counts: loaded silently before.
        ("nn1_count", 2**32, -errno.EOVERFLOW),
        ("nn2_count", 2**32, -errno.EOVERFLOW),
        # Negative counts that narrow to valid int32 values (8 and 0): loaded
        # silently before; a malformed header now.
        ("n_sites", -(2**32) + N_SITES, -errno.EPROTO),
        ("nn1_count", -(2**32), -errno.EPROTO),
    ],
    ids=[
        "n_sites_wraps",
        "n_sites_int32_max_plus_1",
        "nn1_count_wraps",
        "nn2_count_wraps",
        "negative_n_sites_wraps",
        "negative_nn1_count_wraps",
    ],
)
def test_header_counts_outside_int32_are_refused(
    libinit: ctypes.CDLL, tmp_path: Path, field: str, value: int, expected_rc: int
) -> None:
    counts = {"n_sites": N_SITES, field: value}
    rc, _ = _load(libinit, _write_kmcinit(tmp_path / "bad.kmcinit", **counts))
    assert rc == expected_rc
