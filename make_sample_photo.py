"""Generate a small JPEG with EXIF and XMP for testing embedded metadata.

Pure standard library — no dependencies. Run:

    python make_sample_photo.py

This writes sample-photo.jpg in the current directory. Upload that file to
your Photos folder in Box, then run python process.py.
"""

from __future__ import annotations

import math
import struct

OUTPUT = "sample-photo.jpg"
WIDTH = 320
HEIGHT = 240

TYPE_ASCII = 2
TYPE_SHORT = 3
TYPE_LONG = 4

TAG_MAKE = 0x010F
TAG_EXIF_IFD = 0x8769
TAG_ISO = 0x8827
TAG_DATETIME_ORIGINAL = 0x9003

# Zigzag visit order of 8x8 coefficients stored row-major.
_ZIGZAG = [
    0, 1, 8, 16, 9, 2, 3, 10,
    17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
]

def _scale_qt(table: list[int], quality: int) -> list[int]:
    """libjpeg-style quality scaling. quality 90 keeps gradients from blocking."""
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    return [max(1, min(255, (value * scale + 50) // 100)) for value in table]


# ITU-T T.81 Annex K quantization tables (natural 8x8 order), quality 90.
_QT_LUMA = _scale_qt(
    [
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99,
    ],
    90,
)
_QT_CHROMA = _scale_qt(
    [
        17, 18, 24, 47, 99, 99, 99, 99,
        18, 21, 26, 66, 99, 99, 99, 99,
        24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
    ],
    90,
)

# ITU-T T.81 Annex K Huffman bits/values. bits[i] = number of codes of length i+1.
_DC_LUMA_BITS = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
_DC_LUMA_VAL = list(range(12))
_DC_CHROMA_BITS = [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
_DC_CHROMA_VAL = list(range(12))
_AC_LUMA_BITS = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 125]
_AC_LUMA_VAL = [
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
    0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
    0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
    0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
    0xF9, 0xFA,
]
_AC_CHROMA_BITS = [0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 119]
_AC_CHROMA_VAL = [
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
    0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91, 0xA1, 0xB1, 0xC1, 0x09, 0x23, 0x33, 0x52, 0xF0,
    0x15, 0x62, 0x72, 0xD1, 0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18, 0x19, 0x1A, 0x26,
    0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
    0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
    0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5,
    0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3,
    0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA,
    0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
    0xF9, 0xFA,
]


def _build_huffman(bits: list[int], values: list[int]) -> dict[int, tuple[int, int]]:
    """Return symbol -> (code, bit_length) from JPEG bits/huffval tables."""
    mapping: dict[int, tuple[int, int]] = {}
    code = 0
    idx = 0
    for length in range(1, 17):
        for _ in range(bits[length - 1]):
            mapping[values[idx]] = (code, length)
            idx += 1
            code += 1
        code <<= 1
    return mapping


_DC_LUMA = _build_huffman(_DC_LUMA_BITS, _DC_LUMA_VAL)
_DC_CHROMA = _build_huffman(_DC_CHROMA_BITS, _DC_CHROMA_VAL)
_AC_LUMA = _build_huffman(_AC_LUMA_BITS, _AC_LUMA_VAL)
_AC_CHROMA = _build_huffman(_AC_CHROMA_BITS, _AC_CHROMA_VAL)


class _BitWriter:
    def __init__(self) -> None:
        self._buf = bytearray()
        self._acc = 0
        self._nbits = 0

    def write(self, code: int, length: int) -> None:
        for i in range(length - 1, -1, -1):
            self._acc = (self._acc << 1) | ((code >> i) & 1)
            self._nbits += 1
            if self._nbits == 8:
                self._buf.append(self._acc)
                if self._acc == 0xFF:
                    self._buf.append(0x00)
                self._acc = 0
                self._nbits = 0

    def flush(self) -> bytes:
        if self._nbits:
            pad = 8 - self._nbits
            self.write((1 << pad) - 1, pad)
        return bytes(self._buf)


def _category_and_bits(value: int) -> tuple[int, int, int]:
    if value == 0:
        return 0, 0, 0
    abs_val = abs(value)
    size = abs_val.bit_length()
    extra = value if value > 0 else value + (1 << size) - 1
    return size, extra, size


def _dct(block: list[float]) -> list[float]:
    out = [0.0] * 64
    for u in range(8):
        cu = math.sqrt(0.5) if u == 0 else 1.0
        for v in range(8):
            cv = math.sqrt(0.5) if v == 0 else 1.0
            total = 0.0
            for y in range(8):
                for x in range(8):
                    total += (
                        block[y * 8 + x]
                        * math.cos((2 * x + 1) * u * math.pi / 16)
                        * math.cos((2 * y + 1) * v * math.pi / 16)
                    )
            out[v * 8 + u] = 0.25 * cu * cv * total
    return out


def _quantize(coeffs: list[float], table: list[int]) -> list[int]:
    return [int(round(coeffs[i] / table[i])) for i in range(64)]


def _encode_block(
    writer: _BitWriter,
    coeffs: list[int],
    prev_dc: int,
    dc_table: dict[int, tuple[int, int]],
    ac_table: dict[int, tuple[int, int]],
) -> int:
    dc = coeffs[0]
    size, extra, extra_len = _category_and_bits(dc - prev_dc)
    code, length = dc_table[size]
    writer.write(code, length)
    if extra_len:
        writer.write(extra, extra_len)

    run = 0
    for natural in _ZIGZAG[1:]:
        value = coeffs[natural]
        if value == 0:
            run += 1
            continue
        while run >= 16:
            zrl, zlen = ac_table[0xF0]
            writer.write(zrl, zlen)
            run -= 16
        size, extra, extra_len = _category_and_bits(value)
        rs, rlen = ac_table[(run << 4) | size]
        writer.write(rs, rlen)
        writer.write(extra, extra_len)
        run = 0
    if run:
        eob, elen = ac_table[0x00]
        writer.write(eob, elen)
    return dc


def _sample_pixels(width: int, height: int) -> bytes:
    """Sky-over-ground gradient so the file is obviously a photo in a preview."""
    pixels = bytearray(width * height * 3)
    horizon = int(height * 0.62)
    blend = 24
    i = 0
    for y in range(height):
        fy_sky = y / max(horizon - 1, 1)
        fy_ground = (y - horizon) / max(height - horizon - 1, 1)
        for x in range(width):
            fx = x / (width - 1)
            sky = (
                70 + 90 * fy_sky + 40 * fx,
                130 + 70 * fy_sky,
                190 + 40 * fy_sky - 20 * fx,
            )
            ground = (
                70 + 80 * fy_ground + 30 * fx,
                110 - 20 * fy_ground,
                50 + 20 * fx,
            )
            t = 0.0 if y < horizon - blend else 1.0 if y >= horizon else (y - (horizon - blend)) / blend
            r = sky[0] * (1 - t) + ground[0] * t
            g = sky[1] * (1 - t) + ground[1] * t
            b = sky[2] * (1 - t) + ground[2] * t
            pixels[i] = max(0, min(255, int(r)))
            pixels[i + 1] = max(0, min(255, int(g)))
            pixels[i + 2] = max(0, min(255, int(b)))
            i += 3
    return bytes(pixels)


def _rgb_to_ycbcr_block(pixels: bytes, width: int, x0: int, y0: int, height: int) -> tuple[list[float], list[float], list[float]]:
    y_block = [0.0] * 64
    cb_block = [0.0] * 64
    cr_block = [0.0] * 64
    for by in range(8):
        py = min(y0 + by, height - 1)
        for bx in range(8):
            px = min(x0 + bx, width - 1)
            i = (py * width + px) * 3
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            y_block[by * 8 + bx] = 0.299 * r + 0.587 * g + 0.114 * b - 128
            cb_block[by * 8 + bx] = -0.168736 * r - 0.331264 * g + 0.5 * b
            cr_block[by * 8 + bx] = 0.5 * r - 0.418688 * g - 0.081312 * b
    return y_block, cb_block, cr_block


def _marker(kind: int, payload: bytes) -> bytes:
    return bytes([0xFF, kind]) + struct.pack(">H", len(payload) + 2) + payload


def _dqt(table_id: int, table: list[int]) -> bytes:
    payload = bytes([table_id]) + bytes(table[i] for i in _ZIGZAG)
    return _marker(0xDB, payload)


def _dht(table_class: int, table_id: int, bits: list[int], values: list[int]) -> bytes:
    payload = bytes([(table_class << 4) | table_id]) + bytes(bits) + bytes(values)
    return _marker(0xC4, payload)


def _encode_jpeg(pixels: bytes, width: int, height: int) -> bytes:
    writer = _BitWriter()
    prev_dc = [0, 0, 0]
    tables = [
        (_QT_LUMA, _DC_LUMA, _AC_LUMA),
        (_QT_CHROMA, _DC_CHROMA, _AC_CHROMA),
        (_QT_CHROMA, _DC_CHROMA, _AC_CHROMA),
    ]
    for y0 in range(0, height, 8):
        for x0 in range(0, width, 8):
            blocks = _rgb_to_ycbcr_block(pixels, width, x0, y0, height)
            for component, block in enumerate(blocks):
                qt, dc_table, ac_table = tables[component]
                coeffs = _quantize(_dct(block), qt)
                prev_dc[component] = _encode_block(
                    writer, coeffs, prev_dc[component], dc_table, ac_table
                )

    sof = struct.pack(">BHHB", 8, height, width, 3)
    sof += bytes([1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1])
    sos = bytes([3, 1, 0x00, 2, 0x11, 3, 0x11, 0, 63, 0])

    return b"".join(
        [
            b"\xff\xd8",
            _marker(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"),
            _dqt(0, _QT_LUMA),
            _dqt(1, _QT_CHROMA),
            _marker(0xC0, sof),
            _dht(0, 0, _DC_LUMA_BITS, _DC_LUMA_VAL),
            _dht(1, 0, _AC_LUMA_BITS, _AC_LUMA_VAL),
            _dht(0, 1, _DC_CHROMA_BITS, _DC_CHROMA_VAL),
            _dht(1, 1, _AC_CHROMA_BITS, _AC_CHROMA_VAL),
            _marker(0xDA, sos),
            writer.flush(),
            b"\xff\xd9",
        ]
    )


def _pack_ifd(
    entries: list[tuple[int, int, int, bytes | None]], extra: list[bytes], start: int
) -> bytes:
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

    tiff_header = b"II" + struct.pack("<HI", 42, 8)
    ifd0_start = 8
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
    exif_ifd = _pack_ifd(
        [
            (TAG_ISO, TYPE_SHORT, 1, struct.pack("<H", 200)),
            (TAG_DATETIME_ORIGINAL, TYPE_ASCII, len(datetime_original), None),
        ],
        [datetime_original],
        exif_ifd_offset,
    )
    payload = b"Exif\x00\x00" + tiff_header + ifd0 + exif_ifd
    return _marker(0xE1, payload)


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
    return _marker(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + xmp)


def _inject_app1(jpeg: bytes, segments: list[bytes]) -> bytes:
    """Insert APP1 segments after SOI and the JFIF APP0 marker."""
    if jpeg[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    offset = 2
    if jpeg[offset : offset + 2] == b"\xff\xe0":
        length = int.from_bytes(jpeg[offset + 2 : offset + 4], "big")
        offset += 2 + length
    return jpeg[:offset] + b"".join(segments) + jpeg[offset:]


def build_jpeg() -> bytes:
    jpeg = _encode_jpeg(_sample_pixels(WIDTH, HEIGHT), WIDTH, HEIGHT)
    return _inject_app1(jpeg, [build_exif_app1(), build_xmp_app1()])


if __name__ == "__main__":
    with open(OUTPUT, "wb") as f:
        f.write(build_jpeg())
    print(f"Wrote {OUTPUT}")
