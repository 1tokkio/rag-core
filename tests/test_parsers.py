import pytest

from app.core.errors import AppError
from app.ingestion.parsers import parse_document
from tests.factories import make_text_pdf


def test_txt_is_normalized_and_bom_is_removed():
    data = "﻿First line\r\nSecond line\r\n".encode()

    parsed = parse_document("notes.txt", data)

    assert parsed.file_type == "txt"
    assert parsed.mime_type == "text/plain"
    assert parsed.text == "First line\nSecond line"
    assert parsed.title is None
    assert parsed.pages == []


def test_markdown_title_comes_from_first_h1():
    data = b"Intro text\n\n# Synthetic Handbook\n\n## Section\nBody\n"

    parsed = parse_document("handbook.md", data)

    assert parsed.file_type == "md"
    assert parsed.mime_type == "text/markdown"
    assert parsed.title == "Synthetic Handbook"


def test_markdown_without_h1_has_no_title():
    parsed = parse_document("plain.md", b"## Only a subheading\nText\n")

    assert parsed.title is None


def test_pdf_pages_are_extracted_with_page_spans():
    data = make_text_pdf(["Synthetic policy page one.", "Synthetic policy page two."])

    parsed = parse_document("policy.pdf", data)

    assert parsed.file_type == "pdf"
    assert parsed.mime_type == "application/pdf"
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert parsed.pages[0].start_offset == 0
    first_page_text = "Synthetic policy page one."
    assert parsed.text.startswith(first_page_text)
    second = parsed.pages[1]
    assert parsed.text[second.start_offset :].startswith("Synthetic policy page two.")


def test_unsupported_extension_is_rejected():
    with pytest.raises(AppError) as error:
        parse_document("contract.docx", b"anything")

    assert error.value.status_code == 400
    assert error.value.code == "UNSUPPORTED_FILE_TYPE"


def test_invalid_utf8_text_is_rejected():
    with pytest.raises(AppError) as error:
        parse_document("broken.txt", b"\xff\xfe\x00bad")

    assert error.value.status_code == 400
    assert error.value.code == "INVALID_FILE"


def test_file_named_pdf_without_pdf_signature_is_rejected():
    with pytest.raises(AppError) as error:
        parse_document("fake.pdf", b"plain text, not a pdf")

    assert error.value.status_code == 400
    assert error.value.code == "INVALID_FILE"


def test_empty_text_file_has_no_extractable_text():
    with pytest.raises(AppError) as error:
        parse_document("empty.txt", b"   \n\n  ")

    assert error.value.status_code == 422
    assert error.value.code == "NO_EXTRACTABLE_TEXT"


def test_pdf_without_text_has_no_extractable_text():
    with pytest.raises(AppError) as error:
        parse_document("blank.pdf", make_text_pdf([""]))

    assert error.value.status_code == 422
    assert error.value.code == "NO_EXTRACTABLE_TEXT"
