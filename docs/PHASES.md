# Fases de desarrollo — `rag-core`

## Reglas de ejecución

Antes de escribir código en cada fase, el implementador debe presentar un plan con pasos concretos, archivos que creará o modificará, decisiones técnicas y verificaciones previstas. Debe esperar aprobación antes de implementar. Cada fase termina con pruebas y un commit separado con mensaje Conventional Commits. No se debe iniciar la siguiente fase si los criterios de aceptación de la actual no están comprobados.

## Fase 1 — Base

### Alcance

- Estructura inicial del proyecto.
- Docker Compose con PostgreSQL 16 y pgvector.
- Dockerfile.
- Configuración con Pydantic Settings.
- Logging base.
- Healthcheck.
- Liveness en `GET /health` y readiness de base de datos en `GET /health/ready`.
- `.env.example`.
- CI inicial si es necesario para validar la base.

### Archivos esperados

- `app/api/`
- `app/core/`
- `app/db/`
- `tests/`
- `docker-compose.yml`
- `Dockerfile`
- `.env.example`
- `.github/workflows/ci.yml`

### Aceptación

- `docker compose up` inicia la aplicación y PostgreSQL.
- `GET /health` responde `200`.
- `GET /health/ready` responde `200` cuando PostgreSQL está disponible y `503` cuando no lo está.
- La configuración se carga desde variables de entorno.
- No hay claves reales en el repositorio.
- Las pruebas base pasan sin APIs externas.

## Fase 2 — Ingesta

### Alcance

- Lectura de PDF, TXT y Markdown.
- Chunking configurable por tamaño y overlap.
- Migraciones para `documents` y `chunks`.
- Endpoint `POST /api/v1/documents`.
- Endpoints `GET /api/v1/documents` y `GET /api/v1/documents/{document_id}` para verificar la ingesta.
- Pruebas unitarias de parsing y chunking.
- Pruebas de persistencia contra el PostgreSQL de Compose usando la base `rag_test`.

### Archivos esperados

- `app/ingestion/`
- `app/api/` para la ruta de documentos.
- `app/db/` para modelos, sesión y migraciones.
- `tests/` para parsers, chunking y contrato del endpoint.

### Lectura de PDF

Se propone usar `pypdf` por su licencia BSD, en lugar de PyMuPDF, cuya licencia AGPL requiere una revisión adicional para un proyecto MIT. La librería y la versión concreta deben verificarse en la documentación oficial antes de fijarlas.

### Decisión previa obligatoria

Definir y verificar el mecanismo de migraciones antes de escribirlas. No se debe introducir una herramienta de migraciones sin documentar su elección y verificar su compatibilidad oficial con PostgreSQL 16.

### Aceptación

- Los tres formatos soportados producen texto extraíble o un error claro.
- Los chunks respetan tamaño, overlap y orden configurados.
- Se guardan metadata de documento, offsets y página cuando esté disponible.
- El endpoint devuelve el documento creado y cantidad de chunks.
- La respuesta `201` usa `status: ready` para indicar que los chunks fueron persistidos; no implica que existan embeddings.
- Un checksum duplicado responde `409 Conflict` e incluye el ID existente.
- Los errores de tipo, tamaño o extracción no persisten datos.
- Las pruebas de chunking son deterministas y no usan APIs externas.
- Las pruebas de persistencia de esta fase usan `rag_test`; la integración con un contenedor de test aislado queda para la Fase 6.

## Fase 3 — Recuperación

### Alcance

- Embeddings locales con `sentence-transformers` y `intfloat/multilingual-e5-small`.
- Índice HNSW en pgvector.
- Búsqueda vectorial.
- Búsqueda por palabras clave con `tsvector`.
- Fusión híbrida con Reciprocal Rank Fusion.
- Pruebas aisladas de cada modo de búsqueda.

### Archivos esperados

- `app/retrieval/`
- Adaptador de embeddings local.
- Cambios en `app/db/` para embedding, `tsvector` e índices.
- `tests/` para búsqueda vectorial, textual y RRF.

### Aceptación

- Cada modo de búsqueda devuelve resultados ordenados.
- RRF combina ambas listas sin perder metadata de cita.
- La dimensión del vector coincide con el modelo verificado.
- Las pruebas pueden usar embeddings falsos deterministas.
- Los parámetros de pgvector y HNSW están documentados desde fuentes oficiales.

## Fase 4 — Generación

### Alcance

- Endpoint `POST /api/v1/query`.
- Interfaz `LLMProvider`.
- Integración real con Anthropic fuera de pruebas.
- Prompt con contexto y reglas de grounding.
- Respuesta con citas.
- Respuesta explícita de desconocimiento cuando no hay contexto suficiente.

### Archivos esperados

- `app/generation/`
- `app/api/` para la ruta de consulta.
- `tests/` con proveedor falso o mock.

### Aceptación

- La consulta usa retrieval híbrido antes de llamar al LLM.
- La respuesta incluye citas verificables contra chunks recuperados.
- Sin contexto suficiente, el sistema no inventa una respuesta.
- Ningún test llama a Anthropic ni a otro proveedor externo.
- `ANTHROPIC_API_KEY` solo se lee desde el entorno.

## Fase 5 — Evaluación

### Alcance

- `evals/dataset.jsonl` con 50 preguntas, respuesta y fuente esperada.
- Runner ejecutable con `python -m app.evaluation.runner`.
- Métricas hit rate@k, precisión de citas, latencia p50 y p95.
- Impresión de consultas realizadas y tokens usados al finalizar.
- Reporte JSON en `evals/results/`.

### Archivos esperados

- `app/evaluation/`
- `evals/dataset.jsonl`
- `evals/results/`
- `tests/` para métricas y runner.

### Aceptación

- El runner procesa los 50 casos sintéticos.
- El reporte contiene todas las métricas requeridas.
- La salida de consola informa consultas y tokens usados.
- Las métricas se pueden reproducir con la misma configuración.
- El runner puede ejecutarse usando proveedores falsos en pruebas.

## Fase 6 — Calidad y entrega

### Alcance

- Pruebas de integración con PostgreSQL real en contenedor de test.
- CI en GitHub Actions para lint, tests y build de Docker.
- README con arquitectura, ejecución, resultados y limitaciones.
- Revisión final de secretos y datos ficticios.

### Aceptación

- La integración con PostgreSQL pasa en local y CI.
- CI ejecuta lint, tests y build de Docker sin claves externas.
- README incluye tabla de resultados de evaluación.
- README incluye limitaciones honestas, incluyendo PDF sin OCR y dependencia de Anthropic para generación real.
- El repositorio no contiene secretos ni datos de clientes.

## Commits

Usar un commit por fase con mensajes claros, por ejemplo:

- `feat: establish application foundation`
- `feat: add document ingestion`
- `feat: add hybrid retrieval`
- `feat: add grounded query generation`
- `feat: add evaluation runner`
- `test: complete integration and delivery quality`

