"""Helpers building pictures holding EXIF metadata.

References:

- TIFF: "TIFF Revision 6.0" (Adobe, 1992),
  https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf
- Exif: "Exchangeable image file format for digital still cameras: Exif Version 2.32"
  (CIPA DC-X008-Translation-2019),
  https://www.cipa.jp/std/documents/e/DC-X008-Translation-2019-E.pdf
"""

import struct

_TAG_IMAGE_DATE = 0x0132
_TAG_EXIF_IFD = 0x8769
_TAG_ORIGINAL_DATE = 0x9003
_TYPE_ASCII = 2
_TYPE_LONG = 4
_IFD_HEADER_SIZE = 2
_IFD_ENTRY_SIZE = 12
_IFD_FOOTER_SIZE = 4
_TIFF_HEADER_SIZE = 8


def _build_tiff(image_date: str | None, original_date: str | None) -> bytes:
    """Builds a minimal little-endian TIFF holding EXIF dates.

    Layout is: TIFF header, main IFD (`Image DateTime` and pointer to the EXIF IFD), values of the
    main IFD, EXIF IFD (`EXIF DateTimeOriginal`) and its value. Offsets are relative to the
    beginning of the TIFF header.

    See the references of this module:

    - header and IFD structure, field types: TIFF, section 2 "TIFF Structure" (pages 13 to 16), and
      Exif, section 4.6.2 "IFD Structure";
    - `DateTime` tag (132.H): TIFF, page 31, and Exif, section 4.6.4;
    - Exif IFD pointer tag (8769.H): Exif, section 4.6.3;
    - `DateTimeOriginal` tag (9003.H): Exif, section 4.6.5.
    """
    entries_count = (image_date is not None) + (original_date is not None)
    data_offset = (
        _TIFF_HEADER_SIZE + _IFD_HEADER_SIZE + _IFD_ENTRY_SIZE * entries_count + _IFD_FOOTER_SIZE
    )
    entries = b""
    data = b""
    if image_date is not None:
        value = image_date.encode() + b"\0"
        entries += struct.pack(
            "<HHII", _TAG_IMAGE_DATE, _TYPE_ASCII, len(value), data_offset + len(data)
        )
        data += value
    if original_date is not None:
        value = original_date.encode() + b"\0"
        exif_ifd_offset = data_offset + len(data)
        value_offset = exif_ifd_offset + _IFD_HEADER_SIZE + _IFD_ENTRY_SIZE + _IFD_FOOTER_SIZE
        entries += struct.pack("<HHII", _TAG_EXIF_IFD, _TYPE_LONG, 1, exif_ifd_offset)
        data += struct.pack("<H", 1)
        data += struct.pack("<HHII", _TAG_ORIGINAL_DATE, _TYPE_ASCII, len(value), value_offset)
        data += struct.pack("<I", 0)
        data += value

    return (
        b"II*\0"
        + struct.pack("<I", _TIFF_HEADER_SIZE)
        + struct.pack("<H", entries_count)
        + entries
        + struct.pack("<I", 0)
        + data
    )


def make_exif(
    *, image_date: str | None = None, original_date: str | None = None, jpeg: bool = True
) -> bytes:
    """Builds the content of a picture holding EXIF dates.

    Dates are given as they are stored in EXIF (e.g. `2019:03:02 10:00:00`).

    :param image_date: value of the `Image DateTime` tag, which is not set if `None`.
    :param original_date: value of the `EXIF DateTimeOriginal` tag, which is not set if `None`.
    :param jpeg: whether to build a JPEG rather than a bare TIFF (as raw pictures are). The JPEG
    only holds the APP1 marker segment embedding the TIFF: see Exif, section 4.7.2
    "Interoperability Structure of APP1 in Compressed Data".
    :return: content of the picture.
    """
    tiff = _build_tiff(image_date, original_date)
    if not jpeg:
        return tiff

    segment = b"Exif\0\0" + tiff
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(segment) + 2) + segment + b"\xff\xd9"


__all__ = ["make_exif"]
