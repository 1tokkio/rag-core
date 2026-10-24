# API — `rag-core`

## Convenciones

- Base path sugerido: `/api/v1`.
- `GET /health` queda fuera del base path para healthchecks simples.
- JSON para solicitudes y respuestas, excepto carga de archivos.
- UUID en formato string.
- Los errores usan una forma consistente:

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable explanation",
    "fields": {}
  }
}
```

Los modelos, status codes y comportamiento concretos deben verificarse en la documentación oficial de FastAPI y Pydantic v2 antes de implementarse.

Los errores de validación de entrada deben mapearse a `400 Bad Request` con código `VALIDATION_ERROR`, en lugar de exponer el `422` predeterminado del framework.

## `GET /health`

### Entrada

Sin cuerpo ni parámetros.

### Salida `200 OK`

```json
{
  "status": "ok"
}
```

Este endpoint es exclusivamente liveness: responde `200` mientras el proceso HTTP esté vivo. No debe depender de PostgreSQL.

## `GET /health/ready`

Comprueba si la aplicación está lista para operar con PostgreSQL.

### Entrada

Sin cuerpo ni parámetros.

### Salida `200 OK`

```json
{
  "status": "ready",
  "database": "ok"
}
```

### Salida `503 Service Unavailable`

```json
{
  "detail": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "Database is not ready",
    "fields": {}
  }
}
```

El healthcheck de readiness de Docker Compose debe usar este endpoint. Las rutas liveness y readiness deben mantenerse separadas.

## `POST /api/v1/documents`

Ingiere un documento y crea chunks. En la Fase 2, el estado `ready` significa que los chunks fueron persistidos; los embeddings y la disponibilidad para búsqueda se incorporan en la Fase 3.

### Entrada

`multipart/form-data`:

- `file`: PDF, TXT o Markdown.
- `chunk_size`: entero opcional.
- `chunk_overlap`: entero opcional.
- `title`: string opcional.

### Salida `201 Created`

```json
{
  "id": "uuid",
  "filename": "synthetic-handbook.pdf",
  "file_type": "pdf",
  "status": "ready",
  "chunk_count": 12,
  "created_at": "2026-10-24T12:00:00Z"
}
```

### Errores

- `400`: extensión, configuración, MIME type o archivo inválido; también errores de validación de entrada. Usar código `VALIDATION_ERROR`.
- `409`: checksum duplicado. La respuesta debe incluir el documento existente en `fields`, incluyendo su `id`.
- `413`: archivo demasiado grande.
- `422`: contenido válido como archivo, pero sin texto extraíble.
- `500`: error de persistencia o procesamiento.

Si la validación falla por tipo, tamaño o extracción, no debe persistirse ningún documento, chunk ni checksum. El cliente debe poder corregir el archivo y reintentarlo.

Ejemplo de respuesta para checksum duplicado:

```json
{
  "detail": {
    "code": "DOCUMENT_ALREADY_EXISTS",
    "message": "A document with this checksum already exists",
    "fields": {
      "existing_document_id": "uuid"
    }
  }
}
```

## `GET /api/v1/documents`

Lista documentos ingeridos.

### Entrada

Query parameters opcionales: `status`, `limit` y `offset`.

### Salida `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "synthetic-handbook.pdf",
      "file_type": "pdf",
      "status": "ready",
      "chunk_count": 12,
      "created_at": "2026-10-24T12:00:00Z"
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

## `GET /api/v1/documents/{document_id}`

### Entrada

Path parameter `document_id`.

### Salida `200 OK`

Devuelve metadata, checksum, configuración de chunking, estado y cantidad de chunks.

### Errores

- `404`: documento inexistente.

Estos endpoints forman parte de la Fase 2 y sirven para verificar la ingesta antes de incorporar embeddings.

## `POST /api/v1/query`

Responde una pregunta usando búsqueda vectorial, búsqueda por palabras clave, RRF y generación fundamentada.

### Entrada

```json
{
  "question": "What is the synthetic vacation policy?",
  "top_k": 5,
  "document_ids": ["uuid"]
}
```

`top_k` y `document_ids` son opcionales. No se acepta historial conversacional.

### Salida `200 OK`

```json
{
  "answer": "According to the available documents, ...",
  "citations": [
    {
      "document_id": "uuid",
      "document_name": "synthetic-handbook.pdf",
      "chunk_id": "uuid",
      "chunk_index": 4,
      "page_number": 7,
      "excerpt": "Synthetic employees receive ..."
    }
  ],
  "latency_ms": 842
}
```

Si no hay contexto suficiente, `answer` debe indicar que no es posible responder con la información disponible y `citations` debe ser una lista vacía.

### Errores

- `400`: pregunta vacía o parámetros inválidos.
- `404`: no hay documentos listos o no existen resultados relevantes.
- `502`: proveedor de generación no disponible.
- `503`: base de datos o embeddings no disponibles.

## `GET /api/v1/evaluations/{evaluation_id}`

Obtiene el resumen de una evaluación y sus resultados individuales. La ejecución se inicia mediante el runner de Python, no se requiere un endpoint de creación para cumplir el MVP.

### Salida `200 OK`

Debe incluir consultas realizadas, tokens usados cuando estén disponibles, hit rate@k, precisión de citas, p50, p95 y resultados por caso.

## Fuera del contrato MVP

No se definen endpoints para login, usuarios, conversaciones, tenants, streaming, sincronización externa, actualización o eliminación de documentos.

