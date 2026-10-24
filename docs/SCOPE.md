# Alcance del proyecto — `rag-core`

## Objetivo

`rag-core` es una API REST en FastAPI que ingiere documentos PDF, TXT y Markdown, los divide en chunks configurables, genera embeddings locales, los almacena en PostgreSQL con pgvector y responde preguntas mediante búsqueda híbrida. Las respuestas deben incluir citas trazables a documento, página o chunk.

El proyecto también incluye un módulo de evaluación reproducible para medir la calidad y latencia del pipeline RAG.

## Incluido

- Python 3.12.
- FastAPI y Pydantic v2.
- PostgreSQL 16 con pgvector.
- Embeddings locales mediante `sentence-transformers` y `intfloat/multilingual-e5-small`.
- Generación mediante la API de Anthropic usando `claude-haiku-5-5`.
- Clave de generación exclusivamente desde `ANTHROPIC_API_KEY`.
- Interfaz `LLMProvider` o equivalente para sustituir Anthropic por un proveedor falso en pruebas.
- Ingesta de PDF, TXT y Markdown.
- Chunking configurable por tamaño y overlap.
- Búsqueda vectorial con índice HNSW.
- Búsqueda por palabras clave mediante `tsvector`.
- Fusión híbrida mediante Reciprocal Rank Fusion (RRF).
- Citas de documento, página o chunk.
- Evaluación con dataset sintético de 50 preguntas en `evals/dataset.jsonl`.
- Métricas hit rate@k, precisión de citas, latencia p50 y p95.
- Reporte JSON en `evals/results/`.
- Docker Compose, Dockerfile, `.env.example` y CI en GitHub Actions.
- Healthchecks separados para liveness y readiness.
- Pruebas sin llamadas a APIs externas.
- Pruebas de integración con PostgreSQL real en contenedor de test durante la fase de calidad.
- Código, documentación y datos de ejemplo en inglés.

## Excluido

- Autenticación, autorización, usuarios, roles o API keys gestionadas por la aplicación.
- Interfaz gráfica o frontend.
- Multi-tenancy.
- Memoria conversacional o sesiones persistentes.
- Streaming de respuestas.
- OCR para PDFs escaneados o sin texto extraíble.
- Formatos distintos de PDF, TXT y Markdown.
- Sincronización con servicios externos o almacenamiento cloud.
- Fine-tuning o entrenamiento de modelos.
- Despliegue productivo, autoscaling y observabilidad avanzada.
- Datos reales de clientes o información personal identificable.

## Reglas de implementación

- Antes de escribir código, el implementador debe presentar un plan con pasos, archivos y decisiones, y esperar aprobación.
- El trabajo debe ejecutarse por fases.
- Cada fase debe terminar con pruebas y un commit separado usando Conventional Commits.
- Ningún test puede llamar a un proveedor real de embeddings o generación.
- La variable `ANTHROPIC_API_KEY` nunca debe aparecer en código, commits, fixtures o logs.
- Los datos de ejemplo deben ser sintéticos.
- Cualquier funcionalidad fuera de este alcance requiere aprobación previa.
- El proyecto se atribuye únicamente a 1tokkio. No debe mencionarse ni atribuirse la autoría a Claude, Claude Code ni a ninguna otra IA en commits, código, comentarios, documentación ni metadatos. Los identificadores de modelos que el MVP usa como funcionalidad (embeddings y generación) no cuentan como atribución.
- Los mensajes de commit de este proyecto usan el formato `<tipo>: version X.Y.Z : <descripción>`, por ejemplo `fix: version 4.3.1 : mejora de fase 2`. No se añaden trailers de coautoría.

## Criterios globales de terminado

- `docker compose up` levanta la aplicación y PostgreSQL.
- `GET /health` responde `200` cuando el servicio está disponible.
- `GET /health/ready` refleja la disponibilidad de PostgreSQL.
- `pytest` pasa localmente y en CI sin claves de proveedores externos.
- `python -m app.evaluation.runner` genera un reporte JSON.
- El README documenta arquitectura, ejecución, resultados de evaluación y limitaciones honestas.

## Verificación de dependencias

Los nombres, versiones, modelos, parámetros y APIs concretas deben verificarse en la documentación oficial de Python, FastAPI, Pydantic, PostgreSQL, pgvector, sentence-transformers, Anthropic, Docker Compose y GitHub Actions antes de implementarse. El stack definido aquí es el objetivo del proyecto, no sustituye esa verificación.

