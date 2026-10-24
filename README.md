# rag-core

A retrieval-augmented generation (RAG) service: ingest documents, search them with hybrid retrieval, and answer questions with citations.

> Work in progress. This README is a placeholder until phase 6 (architecture, usage, evaluation results, and limitations).

## Quick start

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

`/health` returns `200` when the API can reach PostgreSQL and `503` when it cannot.

## Local development

```bash
uv sync
uv run pytest
uv run ruff check app tests
```

## License

[MIT](LICENSE)
