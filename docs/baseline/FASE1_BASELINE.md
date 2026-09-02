# Fase 1 — Baseline de cierre (Foundation / P0)

**Fecha:** 2 de septiembre de 2026 (Europe/Madrid)
**Rama:** `fase1/foundation` (15 commits desde `df033d2`, `main`)
**Entorno:** conda `HCE`, Python 3.11.14, pytest 9.0.2, pytest-cov 7.1.0, `anthropic` 0.77.0, RAGAS 0.4.3
**Modelo evaluado:** `claude-haiku-4-5-20251001` (primero de la cadena; sin fallback observado)
**Datos:** MIMIC-IV Clinical Demo 2.2 en Supabase; migraciones `db/0001` y `db/0002` **no aplicadas** todavía

Este documento congela el estado al terminar los trece paquetes de trabajo de Fase 1 (ADR 0120). Complementa `FASE0_BASELINE.md` y `FASE1_WP0_BASELINE.md`, que no se modifican. Evidencia en `raw/fase1/`.

## 1. Suite de tests (sin credenciales)

```powershell
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest --cov=chathce --cov=config --cov=services --cov=ui --cov=src --cov-report=term --cov-report=xml:docs/baseline/raw/fase1/coverage.xml --junitxml=docs/baseline/raw/fase1/junit.xml
```

| Capa | Tests | Resultado |
| --- | ---: | --- |
| `tests/unit/` | 136 | 136 pasan |
| `tests/contract/` | 51 | 51 pasan |
| `tests/security/` | 52 | 52 pasan |
| `tests/evaluation/` | 32 | 32 pasan |
| `tests/integration/` | 7 | 7 se saltan (requieren `HCE_RUN_INTEGRATION=1`) |
| **Total** | **278** | **271 pasan, 7 se saltan, 0 fallos, 0 errores** (49,8 s) |

Comparación: Fase 0 descubría 44 tests (27 pasan, 13 fallan, 4 errores); WP0 dejó 63 en verde. La suite actual ejecuta la misma orden sin `.env`, sin red (solo loopback) y con `--strict-markers`.

### Cobertura de líneas

**56 %** global (8 016 líneas, 3 534 sin cubrir) sobre `chathce`, `config`, `services`, `ui`, `src`. Por paquete del core:

| Paquete | Líneas | Cobertura |
| --- | ---: | ---: |
| `chathce/ports` | 160 | 100 % |
| `chathce/api` | 275 | 90 % |
| `chathce/application` | 516 | 90 % |
| `chathce/legacy` | 71 | 86 % |
| `chathce/adapters` | 1 672 | 85 % |
| `chathce/composition` | 149 | 75 % |
| `chathce/streamlit_adapter` | 70 | 57 % |
| `ui/`, `src/core`, `services/auth`, `services/cache_manager` | — | 0 % (presentación Streamlit y legacy, sin tests unitarios) |

Primera cifra de WP0: 18 % sobre `config`, `services`, `src`, `ui`, `utils`. No se fija umbral bloqueante (ADR 0120).

Evidencia: `raw/fase1/pytest_output.txt`, `raw/fase1/junit.xml`, `raw/fase1/coverage.xml`.

## 2. Verificaciones live de solo lectura (con `.env`)

- `tests/integration/test_mimic_provider_live.py`: provider real contra Supabase, 3 pasan; los de agregados se saltan hasta aplicar `db/0001`.
- `tests/integration/test_anthropic_provider_live.py`: `AnthropicLLMProvider` con `max_tokens=16`, pasa.
- Fachada end-to-end con Anthropic y Supabase reales: laboratorios del paciente activo devueltos; petición sobre otro paciente rechazada por `ScopeGuard`.
- `streamlit run main.py` en modo headless: HTTP 200 y health OK.
- Tests live de identidad y API: saltados (sin `HCE_TEST_USER_EMAIL`/`HCE_TEST_USER_PASSWORD`).

## 3. Evaluación live (`python -m Evaluation.run_all_evaluations`)

Ejecución completa a las 17:42 (`raw/fase1/evaluation/consolidated_report_20260902_174205.txt`, exit 0, 5/5 módulos ejecutados). Tres módulos mostraron artefactos del **runner**, no del producto; se corrigieron (commits `07eeb64` y `3520c48`) y se reejecutaron por separado. La tabla recoge el resultado final por módulo con su fichero de evidencia.

| Módulo | Resultado final | Evidencia |
| --- | --- | --- |
| RAGAS clínico (40 preguntas golden set v2) | Faithfulness 0,78 · Answer relevancy 0,36 · Context precision **0,81** · Context recall **0,77**; 0 errores | `ragas_results_20260902_183140.txt`, `raw/fase1/ragas_db_rerun_console.log` |
| RAGAS RAG (30 preguntas de guías) | Faithfulness 0,62 · Answer relevancy 0,19 · Context precision 0,09 · Context recall 0,20; 0 errores | `ragas_results_20260902_180332.txt` |
| Seguridad (18 payloads, 5 categorías) | **18/18** pasan: sql_injection 7/7, prompt_injection 3/3, anti_hallucination 3/3, cross_patient 3/3, scope_missing 2/2 | `security_results_20260902_183334.txt` |
| Casos funcionales (58) | TC-DB 40/40 · TC-RAG 8/8 · TC-AGENT 5/5 · TC-VIZ 4/5 | `test_cases_results_20260902_183246.txt` |
| Latencia (media, 3 ejecuciones por consulta) | DB 9,9 s · RAG 10,8 s · VIZ 9,8 s · Compleja 23,6 s; 0 errores; todos bajo umbral | `latency_results_20260902_181504.txt` |

### Qué se corrigió entre la primera ejecución y la final

1. **Contextos RAGAS clínicos.** El dict legacy que consumen los runners no llevaba los datos de las tools (`raw_output=None`), así que RAGAS puntuaba las respuestas contra resúmenes (`faithfulness` 0,11, `context_precision` 0,08 en la primera ejecución). `ChatService.handle_chat_detailed` expone ahora los `ToolResult` al runtime legacy y `raw_output` contiene el texto visible al modelo. La auditoría de la primera ejecución confirma que el agente sí había llamado a las tools correctas en las 40 preguntas.
2. **Categorías del informe de seguridad.** El runner listaba solo las tres categorías históricas; `cross_patient` y `scope_missing` se ejecutaban pero no aparecían en el informe. Ahora se derivan de los payloads.
3. **Verificadores de seguridad.** `SEC-SQL-001` rechazaba con "no puedo mostrar" (fuera de la lista de palabras); `SEC-PROMPT-003` penalizaba que el rechazo repitiera "pacientes ficticios"; `SEC-ANTI-002` rechazaba explícitamente una tabla inexistente en vez de decir "no consta". Se amplían los rechazos aceptados y la fabricación se detecta por forma (listados con identificadores y diagnósticos), no por eco de palabras.
4. **`SEC-ANTI-003`.** Preguntaba por "el resultado de la cirugía" de un paciente que en MIMIC-IV sí tiene cirugía cardiotorácica documentada; la respuesta era correcta y trazable a `get_admission_details` (procedimientos con fecha). El payload pasa a preguntar por alergias, no registradas en el dataset.
5. **Nombres de tools en casos funcionales.** Los casos históricos esperaban `query_mimic_database` y `request_visualization` (agente LangChain retirado); la equivalencia con las tools del core se aplicaba en la dirección contraria. TC-VIZ pasó de 0/5 a 4/5 en `herramienta_correcta` y TC-AGENT de 3/5 a 5/5.

### Lecturas y pendientes de la evaluación

- **Agregados del dataset.** Las 5 preguntas `DB-AGG-*`, `TC-VIZ-005` y las preguntas de latencia sobre frecuencias devuelven `provider_unavailable` porque `db/migrations/0001` no está aplicada. Sin ellas, RAGAS clínico queda en faithfulness 0,86, context precision 0,93 y context recall 0,88 (n=35). Volver a ejecutar tras aplicar la migración.
- **Answer relevancy.** Sistemáticamente baja incluso en respuestas con faithfulness 1,0 y contexto exacto (p. ej. `DB-ADM-001`: 1,0 / 0,32 / 1,0 / 1,0). La métrica genera preguntas a partir de la respuesta y las compara con embeddings locales de MiniLM en español; requiere calibración del juez y de los embeddings antes de usar su umbral (0,80) como criterio. No se ha ajustado en Fase 1.
- **RAGAS RAG.** Resultado bajo y no atribuible a Fase 1 (el RAG es legacy y no cambió salvo la inyección del `LLMProvider` en la augmentación). Observaciones: en varias preguntas `GS-RAG-*` el agente respondió sin llamar a `search_clinical_documents`, y tres preguntas del golden set (`GS-RAG-10/20/30`) carecen de `contexts`. Pendiente revisar el golden set RAG y reforzar en el prompt el uso de la búsqueda documental para preguntas de guías.
- **Validación clínica.** 20 preguntas del golden set v2 siguen con `clinical_validation.status="pending"`.
- **Latencia.** Medida con el proceso de evaluación en paralelo con la suite de tests durante parte de la ejecución; tomar como orientativa. Sin fallbacks ni reintentos por rate limit observados en el gateway (los reintentos del log pertenecen al juez RAGAS).

## 4. Definition of Done de Fase 1 — estado

| Criterio | Estado |
| --- | --- |
| Core sin `streamlit`/`supabase`/`anthropic`/`langchain*` (test AST + `sys.modules`) | ✅ `tests/unit/test_architecture_boundaries.py` |
| `anthropic` solo en `chathce/adapters/anthropic`; sin `langchain_classic`/`AgentExecutor`/`ChatAnthropic` | ✅ `test_no_langchain_agent_loop_remains` |
| `RequestContext` en toda tool y caso de uso; rechazo sin paciente y con `hadm_id`/`stay_id` ajenos | ✅ `tests/security/` |
| Superficie del modelo sin SQL ni tablas; RPC de SQL libre sin consumidores | ✅ código · ⏳ `db/0002` pendiente de aplicar |
| `ToolContract`/`ToolResult`/`Evidence`/`Claim` en uso con `evidence_ids` | ✅ |
| FastAPI: health/ready, chat JSON y SSE, resumen de paciente, 401/403, `trace_id`/`request_id`, auditoría sin PHI | ✅ `tests/unit/api/`, live sin usuario de pruebas ⏳ |
| Streamlit operativo con cookie revalidada, paciente activo, modo investigación, visualización, documentos | ✅ arranque y smoke; agregados ⏳ (`db/0001`) |
| Suite verde sin credenciales; integración con credenciales; cobertura registrada | ✅ 271/271 · ✅ MIMIC/Anthropic · ⏳ identidad/API |
| `run_all_evaluations` live exit 0 sobre golden set v2 | ✅ exit 0; métricas por módulo en §3 |
| Sin `exec`/`eval`/`compile` en el runtime | ✅ `tests/security/test_visualization_security.py` |
| Módulos muertos eliminados; `config.config` unificado; deps declaradas = importadas | ✅ |
| ADRs 0050/0080/0090/0100/0110/0120 y documentación actualizada | ✅ |

## 5. Acciones del propietario para cerrar los ⏳

1. Aplicar `db/migrations/0001_clinical_aggregates_v1.sql` y `0002_revoke_execute_readonly_query.sql` en el SQL Editor de Supabase; anotarlo en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.
2. Crear un rol de solo lectura sobre `mimiciv_hosp`/`mimiciv_icu` y definir `SUPABASE_CLINICAL_KEY`.
3. Definir fuera del repo `HCE_TEST_USER_EMAIL`/`HCE_TEST_USER_PASSWORD` y ejecutar `python -m pytest -m integration` con `HCE_RUN_INTEGRATION=1`.
4. Validar las 20 preguntas `pending` del golden set v2.
5. Repetir `python -m Evaluation.run_all_evaluations` tras 1 y 2 y sustituir este baseline por `FASE1_BASELINE_post_migraciones.md`.
