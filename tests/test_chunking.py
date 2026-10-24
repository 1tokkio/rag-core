import pytest

from app.core.errors import AppError
from app.ingestion.chunking import split_text, validate_chunk_config
from app.ingestion.parsers import PageSpan

MAX_CHUNK = 4000


def test_overlap_produces_expected_windows():
    chunks = split_text("abcdefghij", chunk_size=4, chunk_overlap=2)

    assert [chunk.content for chunk in chunks] == ["abcd", "cdef", "efgh", "ghij"]


def test_zero_overlap_produces_adjacent_windows():
    chunks = split_text("abcdefghij", chunk_size=5, chunk_overlap=0)

    assert [chunk.content for chunk in chunks] == ["abcde", "fghij"]


def test_offsets_point_back_into_the_text():
    text = "Synthetic handbook. Vacation policy applies to all staff members."

    chunks = split_text(text, chunk_size=20, chunk_overlap=5)

    for chunk in chunks:
        assert text[chunk.start_offset : chunk.end_offset] == chunk.content


def test_chunks_are_ordered_non_empty_and_indexed_sequentially():
    text = "First part.\n\n   \n\nSecond part.\n\n\n\nThird part."

    chunks = split_text(text, chunk_size=12, chunk_overlap=2)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.content for chunk in chunks)
    starts = [chunk.start_offset for chunk in chunks]
    assert starts == sorted(starts)


def test_changing_chunk_size_changes_the_number_of_chunks():
    text = "Synthetic employees receive fifteen vacation days per calendar year. " * 10

    small = split_text(text, chunk_size=100, chunk_overlap=10)
    large = split_text(text, chunk_size=400, chunk_overlap=10)

    assert len(small) > len(large) > 0


def test_pages_are_assigned_from_chunk_start_offset():
    text = "Page one text.\n\nPage two text."
    pages = [PageSpan(page_number=1, start_offset=0), PageSpan(page_number=2, start_offset=16)]

    chunks = split_text(text, chunk_size=10, chunk_overlap=0, pages=pages)

    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2


def test_text_without_pages_has_no_page_numbers():
    chunks = split_text("Plain text document.", chunk_size=10, chunk_overlap=2)

    assert all(chunk.page_number is None for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (MAX_CHUNK + 1, 0), (100, 100), (100, 150), (100, -1)],
)
def test_invalid_configuration_is_rejected(chunk_size, chunk_overlap):
    with pytest.raises(AppError) as error:
        validate_chunk_config(chunk_size, chunk_overlap, MAX_CHUNK)

    assert error.value.status_code == 400
    assert error.value.code == "VALIDATION_ERROR"
