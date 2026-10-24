# Esquema de base de datos — `rag-core`

## Alcance del esquema

El esquema cubre documentos, chunks, embeddings, búsqueda textual y resultados de evaluación. No incluye usuarios, sesiones, conversaciones ni tenants.

## Tabla `documents`

| Columna | Tipo PostgreSQL | Restricciones | Descripción |
|---|---|---|---|
| `id` | `UUID` | PK | Identificador del documento. |
| `filename` | `TEXT` | NOT NULL | Nombre original. |
| `file_type` | `TEXT` | NOT NULL | `pdf`, `txt` o `md`. |
| `mime_type` | `TEXT` | NOT NULL | Tipo MIME validado. |
| `title` | `TEXT` | NULL | Título opcional. |
| `checksum` | `TEXT` | NOT NULL, UNIQUE | Hash del archivo para detectar duplicados. |
| `chunk_size` | `INTEGER` | NOT NULL | Tamaño utilizado para chunking. |
| `chunk_overlap` | `INTEGER` | NOT NULL | Overlap utilizado. |
| `status` | `TEXT` | NOT NULL | `processing`, `ready` o `failed`. En la Fase 2, `ready` significa chunks persistidos; la disponibilidad para consultas se revisa en la Fase 3. |
| `error_message` | `TEXT` | NULL | Error de procesamiento, si aplica. |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Fecha de creación. |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Última actualización. |

## Tabla `chunks`

| Columna | Tipo PostgreSQL | Restricciones | Descripción |
|---|---|---|---|
| `id` | `UUID` | PK | Identificador del chunk. |
| `document_id` | `UUID` | FK, NOT NULL | Referencia a `documents.id`. |
| `chunk_index` | `INTEGER` | NOT NULL | Orden dentro del documento. |
| `content` | `TEXT` | NOT NULL | Texto del chunk. |
| `content_hash` | `TEXT` | NOT NULL | Hash del contenido. |
| `start_offset` | `INTEGER` | NULL | Offset inicial en texto normalizado. |
| `end_offset` | `INTEGER` | NULL | Offset final en texto normalizado. |
| `page_number` | `INTEGER` | NULL | Página de origen si está disponible. |
| `embedding` | `VECTOR(<EMBEDDING_DIM>)` | NULL hasta la Fase 3 | Vector de `intfloat/multilingual-e5-small`; la Fase 2 persiste chunks sin embedding. |
| `search_vector` | `TSVECTOR` | NOT NULL | Columna generada `to_tsvector('english', content)`, creada en la Fase 2 para que los chunks sean buscables por palabras clave en la Fase 3. |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Fecha de creación. |

`<EMBEDDING_DIM>` debe reemplazarse por la dimensión verificada en la documentación oficial del modelo antes de crear la migración.

Restricción recomendada: `UNIQUE(document_id, chunk_index)`.

Índices previstos:

- FK/index en `chunks.document_id`.
- HNSW sobre `embedding` después de la Fase 3, con operador y distancia verificados en la documentación oficial de pgvector.
- GIN sobre `search_vector`, con sintaxis verificada en la documentación oficial de PostgreSQL.

## Tabla `evaluation_runs`

| Columna | Tipo PostgreSQL | Restricciones | Descripción |
|---|---|---|---|
| `id` | `UUID` | PK | Identificador de ejecución. |
| `name` | `TEXT` | NOT NULL | Nombre de la ejecución. |
| `dataset_path` | `TEXT` | NOT NULL | Ruta lógica del dataset usado. |
| `dataset_version` | `TEXT` | NOT NULL | Versión del dataset. |
| `config` | `JSONB` | NOT NULL | `k`, configuración de retrieval y límites. |
| `total_cases` | `INTEGER` | NOT NULL | Casos ejecutados. |
| `queries_count` | `INTEGER` | NOT NULL | Consultas realizadas. |
| `input_tokens` | `INTEGER` | NULL | Tokens de entrada reportados, si están disponibles. |
| `output_tokens` | `INTEGER` | NULL | Tokens de salida reportados, si están disponibles. |
| `hit_rate_at_k` | `DOUBLE PRECISION` | NULL | Hit rate@k. |
| `citation_precision` | `DOUBLE PRECISION` | NULL | Precisión agregada de citas. |
| `latency_p50_ms` | `DOUBLE PRECISION` | NULL | Latencia p50. |
| `latency_p95_ms` | `DOUBLE PRECISION` | NULL | Latencia p95. |
| `status` | `TEXT` | NOT NULL | `running`, `completed` o `failed`. |
| `error_message` | `TEXT` | NULL | Error de ejecución. |
| `started_at` | `TIMESTAMPTZ` | NOT NULL | Inicio. |
| `completed_at` | `TIMESTAMPTZ` | NULL | Finalización. |

## Tabla `evaluation_results`

| Columna | Tipo PostgreSQL | Restricciones | Descripción |
|---|---|---|---|
| `id` | `UUID` | PK | Identificador del resultado. |
| `run_id` | `UUID` | FK, NOT NULL | Referencia a `evaluation_runs.id`. |
| `case_index` | `INTEGER` | NOT NULL | Índice del caso en el JSONL. |
| `question` | `TEXT` | NOT NULL | Pregunta evaluada. |
| `expected_answer` | `TEXT` | NOT NULL | Respuesta esperada del dataset sintético. |
| `expected_source` | `JSONB` | NOT NULL | Fuente esperada: documento, página o chunk. |
| `retrieved_chunk_ids` | `JSONB` | NOT NULL | Chunks recuperados. |
| `cited_sources` | `JSONB` | NOT NULL | Fuentes citadas. |
| `hit` | `BOOLEAN` | NOT NULL | Si hubo recuperación relevante. |
| `citation_precision` | `DOUBLE PRECISION` | NOT NULL | Precisión del caso. |
| `latency_ms` | `DOUBLE PRECISION` | NOT NULL | Latencia del caso. |
| `input_tokens` | `INTEGER` | NULL | Tokens de entrada del caso. |
| `output_tokens` | `INTEGER` | NULL | Tokens de salida del caso. |
| `error_message` | `TEXT` | NULL | Error individual. |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Fecha del resultado. |

## Relaciones

```text
documents 1 ──── N chunks
evaluation_runs 1 ──── N evaluation_results
```

La evaluación debe guardar siempre un archivo JSON en `evals/results/`, aunque la persistencia de sus métricas en estas tablas se implemente como parte del módulo de evaluación.

## Invariantes de ingesta

- Un fallo de validación, tipo, tamaño o extracción no debe dejar un documento persistido ni bloquear su checksum para un reintento.
- Un checksum ya persistido debe tratarse como duplicado y no crear otro documento.
- Las consultas vectoriales deben excluir chunks cuyo `embedding` todavía sea `NULL`.

