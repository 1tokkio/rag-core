# rag-core

A retrieval-augmented generation (RAG) service: ingest documents, search them with hybrid retrieval, and answer questions with citations.

> Work in progress. Ingestion is implemented (phase 2). Retrieval, generation and evaluation are coming in later phases. The final README with results and limitations is written in phase 6.

## Quick start

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

- `GET /health` is liveness: `200` while the process is running.
- `GET /health/ready` is readiness: `200` when PostgreSQL answers, `503` when it does not.
- The API applies database migrations on startup.

## Ingest a document

```bash
curl -F "file=@notes.md" -F chunk_size=800 -F chunk_overlap=120 \
  http://localhost:8000/api/v1/documents
```

Supported files: PDF (with extractable text), TXT and Markdown. Limits: 10 MB per file, chunk sizes in characters. Uploading the same content twice returns `409` with the existing document ID.

## Local development

```bash
uv sync
docker compose up -d db
uv run pytest
uv run ruff check app tests migrations
```

Integration tests use the `rag_test` database on the Compose PostgreSQL server. They create it on first run. Tests make no calls to external services.

## License

[MIT](LICENSE)
