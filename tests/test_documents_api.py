import uuid

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from tests.factories import make_text_pdf

TXT_HANDBOOK = (
    b"# Synthetic Handbook\n\n"
    b"Synthetic employees receive fifteen vacation days per calendar year. "
    b"Requests must be sent to the synthetic people team two weeks in advance.\n"
)


def _upload(client, filename, data, **form):
    return client.post(
        "/api/v1/documents",
        files={"file": (filename, data)},
        data={key: str(value) for key, value in form.items()},
    )


def _count_documents(database_url):
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            return session.query(Document).count()
    finally:
        engine.dispose()


def test_ingesting_txt_returns_201_with_chunk_count(client):
    response = _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size=120, chunk_overlap=20)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "filename", "file_type", "status", "chunk_count", "created_at"}
    assert body["filename"] == "handbook.txt"
    assert body["file_type"] == "txt"
    assert body["status"] == "ready"
    assert body["chunk_count"] >= 2


def test_ingested_document_is_retrievable_with_its_configuration(client):
    created = _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size=120, chunk_overlap=20)
    document_id = created.json()["id"]

    response = client.get(f"/api/v1/documents/{document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["chunk_size"] == 120
    assert body["chunk_overlap"] == 20
    assert body["title"] is None  # Titles are derived only from Markdown headings.
    assert body["chunk_count"] == created.json()["chunk_count"]
    assert len(body["checksum"]) == 64


def test_chunk_offsets_are_persisted_and_match_the_text(client, clean_database):
    created = _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size=120, chunk_overlap=20)
    normalized = TXT_HANDBOOK.decode().strip()

    engine = create_engine(clean_database)
    try:
        with Session(engine) as session:
            chunks = session.scalars(
                select(Chunk)
                .where(Chunk.document_id == uuid.UUID(created.json()["id"]))
                .order_by(Chunk.chunk_index)
            ).all()
            assert len(chunks) == created.json()["chunk_count"]
            for chunk in chunks:
                assert normalized[chunk.start_offset : chunk.end_offset] == chunk.content
                assert chunk.page_number is None
    finally:
        engine.dispose()


def test_search_vector_is_generated_for_every_chunk(client, clean_database):
    _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size=120, chunk_overlap=20)

    engine = create_engine(clean_database)
    try:
        with engine.connect() as connection:
            matches = connection.scalar(
                text(
                    "SELECT count(*) FROM chunks "
                    "WHERE search_vector @@ to_tsquery('english', 'vacation')"
                )
            )
            nulls = connection.scalar(
                text("SELECT count(*) FROM chunks WHERE search_vector IS NULL")
            )
    finally:
        engine.dispose()

    assert matches >= 1
    assert nulls == 0


def test_pdf_chunks_carry_page_numbers(client, clean_database):
    pdf = make_text_pdf(["Synthetic policy page one.", "Synthetic policy page two."])

    response = _upload(client, "policy.pdf", pdf, chunk_size=30, chunk_overlap=0)

    assert response.status_code == 201
    engine = create_engine(clean_database)
    try:
        with engine.connect() as connection:
            pages = set(
                connection.scalars(
                    text("SELECT page_number FROM chunks WHERE document_id = :id"),
                    {"id": uuid.UUID(response.json()["id"])},
                ).all()
            )
    finally:
        engine.dispose()
    assert pages == {1, 2}


def test_reingesting_the_same_content_returns_409_with_existing_id(client):
    first = _upload(client, "handbook.txt", TXT_HANDBOOK)
    second = _upload(client, "copy-of-handbook.txt", TXT_HANDBOOK)

    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["code"] == "DOCUMENT_ALREADY_EXISTS"
    assert detail["fields"] == {"existing_document_id": first.json()["id"]}


def test_failed_ingestion_persists_nothing_and_checksum_stays_free(client, clean_database):
    blank_pdf = make_text_pdf([""])

    rejected = _upload(client, "blank.pdf", blank_pdf)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "NO_EXTRACTABLE_TEXT"
    assert _count_documents(clean_database) == 0

    # The same bytes can be retried once the source is fixed: no checksum was stored.
    retry = _upload(client, "blank.pdf", blank_pdf)
    assert retry.status_code == 422


def test_unsupported_extension_returns_400(client, clean_database):
    response = _upload(client, "contract.docx", b"not supported")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert _count_documents(clean_database) == 0


def test_oversized_upload_returns_413(make_client, clean_database):
    client = make_client(max_upload_bytes=50)

    response = _upload(client, "handbook.txt", TXT_HANDBOOK)

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"
    assert _count_documents(clean_database) == 0


def test_overlap_not_smaller_than_size_returns_400(client):
    response = _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size=100, chunk_overlap=100)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_missing_file_returns_400_validation_error(client):
    response = client.post("/api/v1/documents", data={"chunk_size": "100"})

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "VALIDATION_ERROR"
    assert "body.file" in body["detail"]["fields"]


def test_non_numeric_chunk_size_returns_400(client):
    response = _upload(client, "handbook.txt", TXT_HANDBOOK, chunk_size="many")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_list_supports_status_filter_and_pagination(client):
    _upload(client, "first.txt", b"Synthetic first document about travel stipends.")
    _upload(client, "second.txt", b"Synthetic second document about equipment loans.")

    response = client.get("/api/v1/documents", params={"limit": 1, "offset": 0})
    filtered = client.get("/api/v1/documents", params={"status": "failed"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["chunk_count"] >= 1
    assert filtered.json()["total"] == 0


def test_unknown_document_returns_404(client):
    response = client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"


def test_invalid_document_id_returns_400(client):
    response = client.get("/api/v1/documents/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
