#!/usr/bin/env python3
"""Sets a custom icon on a .dmg file (and optionally on a volume staging dir).

macOS stores a file's custom icon in an `ICN?` resource inside the file's
resource fork (xattr `com.apple.ResourceFork`). This script builds that
resource fork by hand (no external dependencies) and applies it.

Usage:
    set_dmg_icon.py <path-to-dmg> <path-to-icns> [icn?|icns]
"""
import ctypes
import os
import struct
import sys


def setxattr(path: str, name: bytes, data: bytes) -> None:
    if hasattr(os, "setxattr"):
        os.setxattr(path, name, data)
        return
    buf = ctypes.create_string_buffer(data, len(data))
    rc = ctypes.CDLL(None).setxattr(
        os.fsencode(path), name, buf, len(data), 0, 0)
    if rc != 0:
        raise OSError(f"setxattr({name!r}) failed")

RF_DATA_OFFSET = 0x100
SECTION_LEN = 50


def build_resource_fork(data: bytes, rtype: bytes, rid: int) -> bytes:
    """Resource fork holding one unnamed resource of type `rtype` (4 chars)
    with id `rid` (0..65535).

    Layout as written by macOS on APFS (16-byte header, zero pad to 0x100,
    u32-prefixed data, then a 50-byte section of 25 big-endian u16s):

        0x00  u32  data area offset (0x100)
        0x04  u32  logical end of data area (0x104 + len)
        0x08  u32  data length incl. 4-byte prefix
        0x0C  u32  section length (50)
        ...   zero pad to 0x100
        0x100 u32  data length
        0x104 data
        ...   section: 0, 256, 0, data end, 0, data len, 0, 50, 0, 0,
                       0x0A00, 0, 28, 50, 0, t1, t2, 0, 10, id,
                       0xFFFF, 0, 0, 256, 0
    """
    n = len(data)
    data_end = RF_DATA_OFFSET + 4 + n
    total = data_end + SECTION_LEN
    fork = bytearray(total)
    struct.pack_into(">IIII", fork, 0,
                     RF_DATA_OFFSET, data_end, 4 + n, SECTION_LEN)
    struct.pack_into(">I", fork, RF_DATA_OFFSET, n)
    fork[RF_DATA_OFFSET + 4:RF_DATA_OFFSET + 4 + n] = data
    u16s = (0, 0x100, 0, data_end, 0, 4 + n, 0, SECTION_LEN, 0, 0,
            0x0A00, 0, 28, SECTION_LEN, 0,
            int.from_bytes(rtype[:2], "big"), int.from_bytes(rtype[2:], "big"),
            0, 10, rid & 0xFFFF, 0xFFFF, 0, 0, 0x100, 0)
    fork[data_end:data_end + SECTION_LEN] = struct.pack(">25H", *u16s)
    return bytes(fork)


PRESETS = {"icn?": (b"ICN?", 1), "icns": (b"icns", -16455)}


def set_file_icon(dmg: str, icns: str, preset: str = "icn?") -> None:
    rtype, rid = PRESETS[preset]
    with open(icns, "rb") as f:
        icns_data = f.read()
    setxattr(dmg, b"com.apple.ResourceFork",
             build_resource_fork(icns_data, rtype, rid))
    print(f"set {rtype.decode()} resource on {dmg}")


def main() -> None:
    if len(sys.argv) not in (3, 4) or (
            len(sys.argv) == 4 and sys.argv[3] not in PRESETS):
        sys.exit(__doc__)
    set_file_icon(sys.argv[1], sys.argv[2],
                  sys.argv[3] if len(sys.argv) == 4 else "icn?")


if __name__ == "__main__":
    main()
