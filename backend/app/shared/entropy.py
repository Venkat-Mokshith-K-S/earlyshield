"""Shannon entropy, shared by the monitor (features) and the recovery vault."""

import bz2
import lzma
import struct
import zlib
from pathlib import Path
from typing import Optional

import numpy as np

ENTROPY_SAMPLE_BYTES = 65536  # read at most 64KB per file to keep this fast


def shannon_entropy(data: bytes) -> float:
    """Bits per byte (0-8). Plain text sits around 4-5; encrypted/compressed data trends toward 8."""
    if not data:
        return 0.0
    # numpy instead of a Python byte loop: ~25x faster, which matters when
    # an attack window touches hundreds of files.
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    p = counts[counts > 0] / len(data)
    return float(-(p * np.log2(p)).sum())


def _decoded_sample(raw: bytes) -> Optional[bytes]:
    """
    If `raw` starts a well-formed gzip / bzip2 / xz stream or an unencrypted
    zip member, return the first decompressed bytes; otherwise None.

    Why: legitimately compressed files (archiving, log rotation) are as
    random as ciphertext byte-for-byte, which made routine gzip archiving look
    exactly like copy-then-delete ransomware. What matters is the entropy of
    the CONTENT, so a file that genuinely decompresses is judged on what it
    decompresses to. Ciphertext never decompresses; ciphertext wrapped in a
    valid gzip decompresses to random bytes and still scores ~8; a
    password-protected zip (as used by e.g. Qlocker) is not decoded at all.
    """
    try:
        if raw[:2] == b"\x1f\x8b":
            out = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, ENTROPY_SAMPLE_BYTES)
        elif raw[:3] == b"BZh":
            out = bz2.BZ2Decompressor().decompress(raw, ENTROPY_SAMPLE_BYTES)
        elif raw[:6] == b"\xfd7zXZ\x00":
            out = lzma.LZMADecompressor().decompress(raw, ENTROPY_SAMPLE_BYTES)
        elif raw[:4] == b"PK\x03\x04" and len(raw) >= 30:
            flags, method = struct.unpack("<HH", raw[6:10])
            if flags & 0x1:
                return None  # encrypted member: can't (and shouldn't) look inside
            name_len, extra_len = struct.unpack("<HH", raw[26:30])
            body = raw[30 + name_len + extra_len:]
            if method == 0:
                out = body
            elif method == 8:
                out = zlib.decompressobj(-zlib.MAX_WBITS).decompress(body, ENTROPY_SAMPLE_BYTES)
            else:
                return None
        else:
            return None
    except (zlib.error, OSError, EOFError, lzma.LZMAError, ValueError, struct.error):
        return None
    return out or None


def content_entropy(raw: bytes) -> float:
    decoded = _decoded_sample(raw)
    return shannon_entropy(decoded if decoded is not None else raw)


def file_entropy(path: Path) -> Optional[float]:
    try:
        with open(path, "rb") as f:
            return content_entropy(f.read(ENTROPY_SAMPLE_BYTES))
    except OSError:
        return None
