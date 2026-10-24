"""Builders for synthetic test files. All content is fictional."""


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(pages: list[str]) -> bytes:
    """Build a minimal, valid PDF with one text line per page (Helvetica, ASCII only)."""
    # Object numbers: 1 catalog, 2 pages tree, 3 font, then a (page, content) pair per page.
    objects: list[tuple[int, bytes]] = [
        (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        (3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
    ]
    kids = []
    for index, text in enumerate(pages):
        page_id = 4 + 2 * index
        content_id = page_id + 1
        kids.append(f"{page_id} 0 R")
        stream = f"BT /F1 12 Tf 72 720 Td ({_escape_pdf_text(text)}) Tj ET".encode("ascii")
        objects.append(
            (
                page_id,
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Contents {content_id} 0 R "
                    f"/Resources << /Font << /F1 3 0 R >> >> >>"
                ).encode("ascii"),
            )
        )
        objects.append(
            (
                content_id,
                b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            )
        )
    pages_tree = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>"
    objects.append((2, pages_tree.encode("ascii")))
    objects.sort(key=lambda item: item[0])

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number, body in objects:
        offsets[number] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)

    size = len(objects) + 1
    xref_position = len(out)
    out += b"xref\n0 %d\n" % size
    out += b"0000000000 65535 f \n"
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_position)
    return bytes(out)
