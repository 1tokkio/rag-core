# Riesgos técnicos — `rag-core`

| Riesgo | Impacto | Probabilidad | Mitigación | Señal de alerta |
|---|---|---:|---|---|
| La dimensión real de `intfloat/multilingual-e5-small` no coincide con la migración. | Alto | Media | Verificar dimensión en documentación oficial y validar configuración al iniciar. | Fallos al insertar o consultar embeddings. |
| El modelo local consume demasiada memoria o tarda demasiado. | Alto | Media | Medir temprano, documentar requisitos y mantener un adaptador de embeddings reemplazable. | Ingesta lenta o contenedor inestable. |
| El identificador `claude-haiku-5-5` no está disponible o cambia. | Alto | Media | Verificar disponibilidad y nombre exacto en documentación oficial de Anthropic antes de implementar; aislarlo detrás de `LLMProvider`. | Error de modelo inválido o cambios de API. |
| El costo de Anthropic supera el límite bajo. | Alto | Media | Limitar contexto, controlar número de consultas, imprimir tokens y usar proveedores falsos en pruebas y evaluación de desarrollo. | Aumento inesperado de tokens o consultas. |
| La búsqueda híbrida produce resultados irrelevantes. | Alto | Media | Probar cada modo por separado, medir hit rate@k y ajustar RRF con el dataset sintético. | Hit rate bajo en preguntas conocidas. |
| La búsqueda textual no funciona por configuración incorrecta de `tsvector`. | Medio | Media | Probar indexación y consultas con fixtures, revisar configuración de idioma y documentar la elección. | Resultados vacíos aunque exista coincidencia literal. |
| El índice HNSW no es compatible con la versión instalada de pgvector. | Medio | Media | Verificar sintaxis, operador y versión en documentación oficial; probar migración en contenedor PostgreSQL 16. | Error al crear índice o consulta vectorial. |
| El chunking separa contexto relevante. | Alto | Alta | Evaluar tamaños y overlap con casos sintéticos; conservar índice, offsets y página. | Citas incompletas o respuestas que requieren chunks vecinos. |
| Los PDFs no tienen texto extraíble. | Medio | Alta | No incluir OCR en MVP; detectar texto vacío y devolver error claro. | Documento aceptado sin chunks útiles. |
| El LLM inventa información. | Alto | Media | Prompt de grounding, contexto limitado, validación de citas y respuesta de desconocimiento sin evidencia. | Afirmaciones sin cita válida. |
| Las citas no corresponden al contexto recuperado. | Alto | Media | Construir metadata desde base de datos y validar cada cita antes de responder. | ID, página o chunk inexistente. |
| Tests llaman accidentalmente a proveedores reales. | Alto | Media | Interfaces, fakes deterministas, fixtures y configuración de test sin claves; bloquear red en CI si es viable. | Tests lentos, no deterministas o requieren secreto. |
| El mecanismo de migraciones se elige sin verificar compatibilidad. | Medio | Media | Decidirlo antes de Fase 2 y comprobarlo en documentación oficial y contenedor limpio. | Base local funciona pero migración falla en CI. |
| El contenedor de integración no es reproducible. | Medio | Media | Fijar imagen compatible, esperar readiness, limpiar datos entre tests y ejecutar el mismo flujo en CI. | Tests que pasan solo con una base local existente. |
| Las métricas de evaluación son poco representativas. | Medio | Alta | Usar 50 casos sintéticos variados y documentar limitaciones; separar retrieval de generación. | Métricas altas con respuestas deficientes. |
| Se filtran secretos o datos reales. | Alto | Baja | `.env.example` sin valores reales, `.gitignore`, revisión antes de commit y datos exclusivamente ficticios. | Secretos en commits, logs o fixtures. |
| Crecimiento de alcance hacia UI, autenticación o multitenancy. | Alto | Alta | Aplicar `SCOPE.md`; convertir solicitudes fuera de alcance en decisiones explícitas. | Archivos o endpoints no contemplados en las fases. |

## Riesgos prioritarios antes de Fase 2

Antes de implementar ingesta, el implementador debe confirmar:

1. La dimensión del modelo de embeddings y su impacto en el esquema.
2. El mecanismo de migraciones para PostgreSQL 16.
3. Los límites de tamaño de archivo y valores por defecto de chunking.
4. La estrategia para representar página y offsets en PDF, TXT y Markdown.

Si alguno requiere una decisión del propietario del proyecto, debe preguntar antes de escribir código.

## Verificación de herramientas

Todas las librerías, versiones, modelos, operadores de pgvector, parámetros HNSW, APIs y configuraciones de CI deben verificarse en su documentación oficial antes de incorporarse al proyecto.

