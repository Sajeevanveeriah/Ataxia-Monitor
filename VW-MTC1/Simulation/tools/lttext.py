"""Text encodings emitted by LTspice (including optional byte-order marks)."""


def text_encoding(data):
    if data.startswith(b"\xff\xfe") or data[1:2] == b"\x00":
        return "utf-16-le"
    if data.startswith(b"\xfe\xff"):
        return "utf-16-be"
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "latin-1"


def decode_text(data):
    return data.decode(text_encoding(data)).lstrip("\ufeff")
