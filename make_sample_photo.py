"""Generate a small JPEG with EXIF and XMP for testing embedded metadata.

Pure standard library — no dependencies. Run:

    python make_sample_photo.py

This writes sample-photo.jpg in the current directory. Upload that file to
your Photos folder in Box, then run python process.py.
"""

from __future__ import annotations

import struct

OUTPUT = "sample-photo.jpg"

# 8x8 grayscale JPEG (public-domain generated baseline image). Pixel
# dimensions become File.ImageWidth / File.ImageHeight in Box.
_JPEG_IMAGE = bytes.fromhex(
    "ffd8"
    "ffe000104a46494600010100000100010000"
    "ffdb004300100b0c0e0c0a100e0d0e1211101318281a181616183123251d283a333d3c3933383740485c4e404457453738506d51575f626768673e4d71797064785c656763"
    "ffc0000b080008000801011100"
    "ffc4001f0000010501010101010100000000000000000102030405060708090a0b"
    "ffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"
    "ffda00080001000100003f00"
    "d2cf20"
    "ffd9"
)

TYPE_ASCII = 2
TYPE_SHORT = 3
TYPE_LONG = 4

TAG_MAKE = 0x010F
TAG_EXIF_IFD = 0x8769
TAG_ISO = 0x8827
TAG_DATETIME_ORIGINAL = 0x9003


def _pack_ifd(entries: list[tuple[int, int, int, bytes | None]], extra: list[bytes], start: int) -> bytes:
    """Build a TIFF IFD. Inline values are 4 bytes; larger values go in extra."""
    count = len(entries)
    extra_offset = start + 2 + 12 * count + 4
    body = bytearray()
    extras = bytearray()

    body += struct.pack("<H", count)
    for tag, typ, value_count, inline_or_none in entries:
        if inline_or_none is not None:
            value = inline_or_none.ljust(4, b"\x00")[:4]
        else:
            blob = extra.pop(0)
            value = struct.pack("<I", extra_offset + len(extras))
            extras += blob
            pad = (2 - (len(blob) % 2)) % 2
            extras += b"\x00" * pad
        body += struct.pack("<HHI", tag, typ, value_count) + value
    body += struct.pack("<I", 0)
    return bytes(body) + bytes(extras)


def build_exif_app1() -> bytes:
    make = b"Apple\x00"
    datetime_original = b"2024:06:15 14:30:00\x00"

    # TIFF header (8 bytes) then IFD0. Exif IFD follows IFD0 + Make string.
    tiff_header = b"II" + struct.pack("<HI", 42, 8)

    ifd0_start = 8
    # Estimate Exif IFD offset: header(8) + IFD0 count(2) + 2*12 entries + next(4) + Make(6, padded to 6)
    ifd0_without_extra = 2 + 12 * 2 + 4
    make_padded_len = len(make) + (len(make) % 2)
    exif_ifd_offset = ifd0_start + ifd0_without_extra + make_padded_len

    ifd0 = _pack_ifd(
        [
            (TAG_MAKE, TYPE_ASCII, len(make), None),
            (TAG_EXIF_IFD, TYPE_LONG, 1, struct.pack("<I", exif_ifd_offset)),
        ],
        [make],
        ifd0_start,
    )

    iso_value = struct.pack("<H", 200)
    exif_ifd = _pack_ifd(
        [
            (TAG_ISO, TYPE_SHORT, 1, iso_value),
            (TAG_DATETIME_ORIGINAL, TYPE_ASCII, len(datetime_original), None),
        ],
        [datetime_original],
        exif_ifd_offset,
    )

    tiff = tiff_header + ifd0 + exif_ifd
    payload = b"Exif\x00\x00" + tiff
    return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload


def build_xmp_app1() -> bytes:
    xmp = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:creator>
        <rdf:Seq>
          <rdf:li>Jane Photographer</rdf:li>
        </rdf:Seq>
      </dc:creator>
      <dc:rights>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">Copyright 2026 Sample</rdf:li>
        </rdf:Alt>
      </dc:rights>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode("utf-8")
    payload = b"http://ns.adobe.com/xap/1.0/\x00" + xmp
    return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload


def build_jpeg() -> bytes:
    soi = _JPEG_IMAGE[:2]
    rest = _JPEG_IMAGE[2:]
    return soi + build_exif_app1() + build_xmp_app1() + rest


if __name__ == "__main__":
    with open(OUTPUT, "wb") as f:
        f.write(build_jpeg())
    print(f"Wrote {OUTPUT}")
