"""Content entropy: compressed files are judged by what they decompress to."""

import bz2
import gzip
import io
import lzma
import os
import zipfile

from app.shared.entropy import content_entropy

TEXT = ("date,account,amount\n" + "\n".join(f"2026-01-{i % 28 + 1:02d},rent,{i * 13.7:.2f}" for i in range(3000))).encode()
CIPHER = os.urandom(len(TEXT))


def _zip(data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("a.csv", data)
    return buf.getvalue()


def test_legit_compression_scores_like_its_content():
    for packed in (gzip.compress(TEXT), bz2.compress(TEXT), lzma.compress(TEXT), _zip(TEXT)):
        assert abs(content_entropy(packed[:65536]) - content_entropy(TEXT)) < 0.1


def test_ciphertext_stays_high_however_it_is_wrapped():
    assert content_entropy(CIPHER) > 7.9
    assert content_entropy(gzip.compress(CIPHER)) > 7.9  # valid gzip around ciphertext
    assert content_entropy(b"\x1f\x8b" + os.urandom(5000)) > 7.9  # fake gzip header


def test_encrypted_zip_member_is_not_decoded():
    data = bytearray(_zip(TEXT))
    data[6] |= 0x1  # set the "encrypted" flag in the local file header
    assert content_entropy(bytes(data)) > 7.0
