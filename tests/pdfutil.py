"""Minimal text PDF so e-fatura tests do not need a binary fixture."""

from __future__ import annotations


def text_pdf(lines: list[str]) -> bytes:
    escaped = []
    for line in lines:
        raw = line.encode("latin-1", "replace").decode("latin-1")
        raw = raw.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        escaped.append(raw)
    ops = ["BT", "/F1 11 Tf", "40 760 Td", "13 TL"]
    for index, line in enumerate(escaped):
        if index:
            ops.append("T*")
        ops.append(f"({line}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        4: b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number in range(1, 6):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii")
        out += objects[number]
        out += b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n"
    out += b"0000000000 65535 f \n"
    for number in range(1, 6):
        out += f"{offsets[number]:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)
