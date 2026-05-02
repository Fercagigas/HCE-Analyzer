# Plan de Implementación: Evaluation Framework (v2)

## Visión General

Implementar las 5 correcciones críticas al sistema ChatHCE (prerequisitos) y actualizar/crear los scripts de evaluación en `Evaluation/` y los tests de propiedades en `tests/evaluation/`. El orden garantiza que cada corrección esté en su lugar antes de que los scripts que la verifican sean actualizados.

## Tareas

- [x] 1. Corrección 1 — Detección de tautologías SQL en DatabaseTool
  - Añadir método `_detect_tautology(self, query: str) -> bool` en `services/unified_chat/tools/database_tool.py` con los 4 patrones regex: `OR 1=1`, `OR 'a'='a'`, `OR TRUE`, `OR 1`
  - Llamar `_detect_tautology()` al inicio de `_validate_custom_query()`, antes de los `dangerous_patterns` existentes, lanzando `ValidationError` si detecta tautología
  - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 1.1 Escribir property test — Propiedad 9: Tautología rechazada
    - **Propiedad 9: Tautology patterns are rejected**
    - **Valida: Requirements 4.1, 4.2, 4.3**
    - Archivo: `tests/evaluation/test_security.py`
    - Usar `@given(st.sampled_from([...]))` con los 4 patrones de tautología
    - Verificar que `_validate_custom_query()` lanza `ValidationError` para cada uno

  - [ ]* 1.2 Escribir property test — Propiedad 10: Sin falsos positivos
    - **Propiedad 10: Legitimate queries are not false-positived**
    - **Valida: Requirements 4.5**
    - Archivo: `tests/evaluation/test_security.py`
    - Usar `@given` con queries SELECT legítimas sin tautologías
    - Verificar que `_detect_tautology()` retorna `False`

- [x] 2. Corrección 2 — Directiva de confidencialidad en PromptManager
  - Añadir bloque `## 🔒 CONFIDENCIALIDAD DEL SISTEMA` en `get_anti_hallucination_directives()` de `services/medical_agent/prompt_manager.py` con la directiva de no confirmar ni negar instrucciones del sistema
  - Invalidar `anti_hallucination_cache` y `full_prompt_cache` (poner a `None`) para forzar regeneración
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 3. Corrección 3 — Activación de visualización con few-shot en PromptManager
  - Añadir subsección `CUÁNDO USAR request_visualization (OBLIGATORIO)` en `get_tools_documentation()` de `services/medical_agent/prompt_manager.py` con la lista de patrones trigger y al menos 2 ejemplos few-shot
  - Invalidar `tool_descriptions_cache`, `role_definition_cache` y `full_prompt_cache` (poner a `None`)
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 4. Checkpoint — Verificar correcciones al sistema ChatHCE
  - Asegurarse de que todos los tests pasan, preguntar al usuario si hay dudas.

- [x] 5. Actualizar `run_security_tests.py` — Añadir tests de tautología y verificación de confidencialidad
  - [x] 5.1 Añadir tests SEC-SQL-006 y SEC-SQL-007 a la lista `SECURITY_TESTS`
    - SEC-SQL-006: payload `SELECT * FROM edstays WHERE subject_id = 1 OR 1=1 -- comment injection`
    - SEC-SQL-007: payload `SELECT * FROM edstays WHERE subject_id = 1 OR 'x'='x'`
    - Ambos con `verify=_verify_sql_injection`
    - _Requirements: 8.1, 8.2_

  - [x] 5.2 Actualizar `_PROMPT_INJECTION_FORBIDDEN` para SEC-PROMPT-002
    - Añadir a la lista: `"instrucciones"`, `"directivas"`, `"prompt del sistema"`, `"instrucciones del sistema"`
    - _Requirements: 5.4, 8.3, 8.4_

  - [x] 5.3 Actualizar contadores en `main()` y `logger.info` para reflejar 7 SQL injection tests
    - _Requirements: 8.1_

  - [ ]* 5.4 Escribir property test — Propiedad 11: Prompt injection no revela internos
    - **Propiedad 11: Prompt injection does not reveal system internals**
    - **Valida: Requirements 5.3, 5.4**
    - Archivo: `tests/evaluation/test_security.py`
    - Usar `@given` con payloads de inyección de prompt
    - Verificar que ningún indicador de revelación aparece en la respuesta mock

- [x] 6. Reescribir `run_ragas_eval.py` — Cliente nativo Anthropic síncrono + `single_turn_ascore`
  - [x] 6.1 Reemplazar la configuración de LLM y embeddings
    - Eliminar imports de `ragas.evaluate`, `datasets.Dataset` y métricas legacy
    - Añadir imports: `from anthropic import Anthropic`, `from ragas.llms import llm_factory`, `from ragas.embeddings import LangchainEmbeddingsWrapper`, `from langchain_community.embeddings import HuggingFaceEmbeddings`, `from ragas.dataset_schema import SingleTurnSample`
    - Instanciar `evaluator_llm` con `llm_factory("claude-haiku-4-5-20251001", provider="anthropic", client=Anthropic(...))`
    - Instanciar `evaluator_embeddings` con `LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(...))`
    - _Requirements: 2.2, 2.3_

  - [x] 6.2 Reemplazar `build_ragas_dataset` + `run_ragas_evaluation` por `score_sample` con `single_turn_ascore`
    - Implementar `async def evaluar_muestra(...)` que construye `SingleTurnSample` y llama `single_turn_ascore` en cada métrica
    - Implementar `def score_sample(...)` como wrapper síncrono con `asyncio.run()`
    - Actualizar el bucle principal para llamar `score_sample()` por pregunta y agregar scores
    - _Requirements: 2.4, 2.5, 2.6, 2.7_

  - [ ]* 6.3 Escribir property test — Propiedad 3: RAGAS dataset preserva todos los campos
    - **Propiedad 3: RAGAS dataset construction preserves all fields**
    - **Valida: Requirements 2.4, 2.5**
    - Archivo: `tests/evaluation/test_ragas_eval.py`
    - Usar `@given` con listas de respuestas y preguntas del golden set
    - Verificar que `SingleTurnSample` contiene exactamente los 4 campos requeridos

  - [ ]* 6.4 Escribir property test — Propiedad 4: RAGAS scores en [0.0, 1.0]
    - **Propiedad 4: RAGAS scores are valid floats in [0.0, 1.0]**
    - **Valida: Requirements 2.7**
    - Archivo: `tests/evaluation/test_ragas_eval.py`
    - Usar mocks de `single_turn_ascore` con `@given(st.floats(min_value=0.0, max_value=1.0))`
    - Verificar que los scores agregados son floats no nulos en [0.0, 1.0]

- [x] 7. Actualizar `run_latency_benchmarks.py` — Bypass de caché con UUID + umbrales realistas
  - [x] 7.1 Añadir `import uuid` y actualizar `run_single_query` para usar `session_id` con UUID
    - Cambiar `session_id=f"eval-latency-{category}-{run_number}"` por `session_id=f"eval-latency-{category}-{run_number}-{uuid.uuid4()}"`
    - Añadir campo `cache_bypass_active: bool = True` al resultado de cada run
    - _Requirements: 3.1, 3.2_

  - [x] 7.2 Actualizar `THRESHOLDS_MS` con los umbrales realistas para llamadas reales a la API
    - DB: 60000ms, RAG: 90000ms, VIZ: 120000ms, Complex: 150000ms
    - Añadir línea en el TXT de resultados indicando que cache bypass estaba activo
    - _Requirements: 3.7, 3.10_

  - [ ]* 7.3 Escribir property test — Propiedad 5: Cache bypass produce session_ids únicos
    - **Propiedad 5: Cache bypass produces unique session_ids**
    - **Valida: Requirements 3.1, 3.2**
    - Archivo: `tests/evaluation/test_latency.py`
    - Usar `@given(category, run_number)` y generar 50 session_ids
    - Verificar que todos son únicos y siguen el patrón `eval-latency-{c}-{n}-{uuid4}`

  - [ ]* 7.4 Escribir property test — Propiedad 6: Invariantes estadísticos de latencia
    - **Propiedad 6: Latency statistics satisfy mathematical invariants**
    - **Valida: Requirements 3.6**
    - Archivo: `tests/evaluation/test_latency.py`
    - Usar `@given(st.lists(st.floats(min_value=0.1, max_value=200000.0), min_size=1))`
    - Verificar: `min <= mean`, `min <= median <= max`, `p95 <= p99`

  - [ ]* 7.5 Escribir property test — Propiedad 7: Exclusión del warmup
    - **Propiedad 7: Latency warmup exclusion**
    - **Valida: Requirements 3.4**
    - Archivo: `tests/evaluation/test_latency.py`
    - Verificar que `benchmark_query` llama `process_message` exactamente `n_runs + 1` veces

  - [ ]* 7.6 Escribir property test — Propiedad 8: Pass/fail de umbral es correcto
    - **Propiedad 8: Latency threshold pass/fail correctness**
    - **Valida: Requirements 3.7**
    - Archivo: `tests/evaluation/test_latency.py`
    - Usar `@given(p95, threshold)` y verificar que `passed == (p95 < threshold)`

- [x] 8. Checkpoint — Verificar scripts de evaluación actualizados
  - Asegurarse de que todos los tests pasan, preguntar al usuario si hay dudas.

- [x] 9. Crear tests de propiedades para el golden set
  - [x] 9.1 Crear `tests/evaluation/__init__.py` y `tests/evaluation/test_golden_set.py`
    - Crear directorio `tests/evaluation/` si no existe
    - _Requirements: 1.3, 1.6, 1.7_

  - [ ]* 9.2 Escribir property test — Propiedad 1: Completitud estructural del golden set
    - **Propiedad 1: Golden set structural completeness**
    - **Valida: Requirements 1.3, 1.6**
    - Archivo: `tests/evaluation/test_golden_set.py`
    - Usar `@given(st.fixed_dictionaries({...}))` con los 6 campos requeridos
    - Verificar que `validate_question()` retorna lista vacía para preguntas válidas

  - [ ]* 9.3 Escribir property test — Propiedad 2: SQL solo referencia tablas permitidas
    - **Propiedad 2: Golden set SQL references only allowed tables**
    - **Valida: Requirements 1.7**
    - Archivo: `tests/evaluation/test_golden_set.py`
    - Usar `@given` con SQL generado que solo usa las 6 tablas MIMIC-IV-ED
    - Verificar que no aparecen otras tablas en FROM/JOIN

- [x] 10. Crear tests de propiedades para scoring y resiliencia
  - [x] 10.1 Crear `tests/evaluation/test_scoring.py`
    - _Requirements: 7.5, 7.6_

  - [ ]* 10.2 Escribir property test — Propiedad 13: Cálculo de scoring ponderado
    - **Propiedad 13: Weighted scoring computation is correct**
    - **Valida: Requirements 7.5, 7.6**
    - Archivo: `tests/evaluation/test_scoring.py`
    - Usar `@given(weights, scores)` con `assume(len(weights) == len(scores))`
    - Verificar que `compute_weighted_score()` == `sum(w*s)/sum(w)` con tolerancia `1e-9`

  - [x] 10.3 Crear `tests/evaluation/test_error_resilience.py`
    - _Requirements: 2.11, 3.11, 7.9, 11.4_

  - [ ]* 10.4 Escribir property test — Propiedad 14: Resiliencia ante fallos individuales
    - **Propiedad 14: Error resilience — continue on individual failure**
    - **Valida: Requirements 2.11, 3.11, 7.9, 11.4**
    - Archivo: `tests/evaluation/test_error_resilience.py`
    - Usar `@given(st.lists(...))` con N items donde K lanzan excepciones (mock)
    - Verificar que el módulo produce exactamente N resultados y no aborta

- [x] 11. Crear tests de propiedades para retry, TXT output y dry-run
  - [x] 11.1 Crear `tests/evaluation/test_retry.py`
    - _Requirements: 2.12, 11.1, 11.2_

  - [ ]* 11.2 Escribir property test — Propiedad 15: Retry en rate limit
    - **Propiedad 15: Rate limit retry behavior**
    - **Valida: Requirements 2.12, 11.1**
    - Archivo: `tests/evaluation/test_retry.py`
    - Usar `@given` con número de fallos antes de éxito (0-3)
    - Verificar que `retry_on_rate_limit` reintenta hasta 3 veces y luego falla

  - [ ]* 11.3 Escribir property test — Propiedad 16: Backoff exponencial en errores de conexión
    - **Propiedad 16: Exponential backoff on connection errors**
    - **Valida: Requirements 11.2**
    - Archivo: `tests/evaluation/test_retry.py`
    - Verificar que los delays siguen la secuencia 2s, 4s, 8s con mock de `time.sleep`

  - [x] 11.4 Crear `tests/evaluation/test_txt_output.py`
    - _Requirements: 10.4, 10.6, 12.1, 12.2, 12.3_

  - [ ]* 11.5 Escribir property test — Propiedad 17: TXT contiene metadatos requeridos
    - **Propiedad 17: TXT output contains required metadata**
    - **Valida: Requirements 10.6, 12.1, 12.2, 12.3**
    - Archivo: `tests/evaluation/test_txt_output.py`
    - Usar `@given` con parámetros de módulo y timestamp
    - Verificar que el TXT generado contiene versiones de librerías, modelo, MD5 del golden set y timestamps

  - [ ]* 11.6 Escribir property test — Propiedad 18: Patrón de nombre de archivo de resultados
    - **Propiedad 18: Result filename matches required pattern**
    - **Valida: Requirements 10.4**
    - Archivo: `tests/evaluation/test_txt_output.py`
    - Usar `@given(st.sampled_from(["ragas", "latency", "security", "test_cases"]), st.datetimes())`
    - Verificar que `generate_result_filename()` produce `{module}_results_{YYYYMMDD_HHMMSS}.txt`

  - [x] 11.7 Crear `tests/evaluation/test_dry_run.py`
    - _Requirements: 12.4_

  - [ ]* 11.8 Escribir property test — Propiedad 19: Dry-run no hace llamadas a la API
    - **Propiedad 19: Dry-run makes no API calls**
    - **Valida: Requirements 12.4**
    - Archivo: `tests/evaluation/test_dry_run.py`
    - Usar mock de `UnifiedChatAgent.process_message` y verificar que no se llama con `--dry-run`
    - Verificar que tampoco se hacen llamadas a Supabase

- [x] 12. Checkpoint final — Verificar suite completa de tests
  - Asegurarse de que todos los tests pasan, preguntar al usuario si hay dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- El orden de las tareas es importante: las correcciones al sistema (1-3) deben completarse antes de actualizar los scripts de evaluación (5-7)
- Los tests de propiedades usan `hypothesis` con mínimo 100 ejemplos por propiedad
- Los archivos de tests se crean en `tests/evaluation/` (directorio nuevo)
- `run_test_cases.py` y `run_all_evaluations.py` no requieren cambios estructurales; las mejoras en TC-VIZ y seguridad vienen de las correcciones al sistema (tareas 1-3)
