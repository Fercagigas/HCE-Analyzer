# Estado actual del proyecto ChatHCE

**Última actualización:** 2 de septiembre de 2026
**Rama principal:** `main` (Fase 1 fusionada desde `fase1/foundation` el 2 de septiembre de 2026)

Este documento resume en qué punto se encuentra el proyecto: qué está hecho, qué acaba de cambiar y qué queda pendiente. Sirve como punto de entrada rápido para retomar el trabajo.

---

## 1. Resumen en una frase

ChatHCE es una capa de inteligencia clínica (chat con Claude, RAG de guías y visualizaciones) sobre MIMIC-IV Clinical Demo 2.2 que, tras completar la **Fase 1 (Foundation / P0)** del roadmap, dispone de un core `chathce/` independiente de Streamlit y de los SDKs, un Model Gateway propio sobre el SDK `anthropic`, acceso clínico allowlisted con scope estricto de paciente, una API FastAPI autenticada con JWT de Supabase y una suite de tests verde sin credenciales.

---

## 2. Fase del roadmap

| Fase | Estado | Notas |
|---|---|---|
| **Fase 0 — Freeze y baseline** | ✅ Completada | Baseline, inventario, mapa de acoplamiento, intended purpose, threat model. ADRs 0001/0010/0020/0030. |
| **Migración de datos MIMIC-IV** | ✅ Completada | MIMIC-IV-ED → MIMIC-IV Clinical Demo 2.2. Ver `docs/MIGRACION_MIMIC_IV.md`. |
| **Mitigaciones de seguridad iniciales** | ✅ Integradas | ADR 0040 (visualizaciones sin exec), ADR 0060 (XSRF/CORS), ADR 0070 (checklist Supabase). |
| **Fase 1 — Foundation / P0** | ✅ Completada (en `main`) | Core `chathce/`, `RequestContext`, ports y adapters, Model Gateway, Clinical Data Provider allowlisted, FastAPI, Streamlit como adapter, tests por capas. ADRs 0050/0080/0090/0100/0110/0120. Quedan acciones manuales del propietario (§7). |
| Fases 2–9 | ⏳ Pendientes | RLS por usuario, Evidence Engine, frontend React, FHIR/SMART, features AI-first, piloto. |

Detalle del roadmap: `ROADMAP_HOSPITAL_READY/` y `.kiro/steering/roadmap.md`.

---

## 3. Arquitectura ejecutable actual

```
Canales
  main.py -> src/core/app.py -> ui/* -----------------------.
  python -m uvicorn chathce.api.app:app (FastAPI, JWT) ------+--> chathce.composition.build_container(get_settings())
  Evaluation/* -> chathce.legacy.LegacyAgentFacade ---------'         |
                                                                       v
  chathce.application.ChatService(RequestContext)
    -> chathce.gateway.ModelGateway --------------> LLMProvider  -> adapters.anthropic (AsyncAnthropic, streaming)
    -> chathce.gateway.ToolRegistry (12 tools)
         -> ScopeGuard(ClinicalDataProvider) ----> adapters.supabase.MimicClinicalDataProvider (PostgREST + RPC clinical_*_v1)
         -> KnowledgeRepository -----------------> adapters.supabase (envuelve services/rag ImprovedRAGService, pgvector)
         -> VisualizationRepository -------------> adapters.visualization.plotly_templates (figure_json, in-memory)
    -> ConversationRepository / AnalysisRepository / IdentityProvider -> Supabase public.* / Auth
    -> AuditSink -> logs/audit/audit.jsonl (sin PHI)
```

- **LLM:** cadena `claude-haiku-4-5-20251001` → `claude-sonnet-4-5` → `claude-opus-4-0` por petición, 1 reintento por modelo, deadline total 120 s, máximo 6 iteraciones.
- **Datos clínicos:** operaciones allowlisted por paciente activo; agregados solo con `purpose=research` (rol `researcher`) vía RPC fijas. No existe SQL libre.
- **RAG:** pgvector + embeddings/reranker locales; `QueryAugmenter` usa el mismo `LLMProvider`.
- **Auth:** Supabase Auth. API con Bearer JWT; Streamlit con cookie que solo guarda el refresh token y revalida en cada carga.
- **Respuesta:** `ChatResponse` con `facts`, `inferences`, `evidence`, `uncertainty`, `tool_calls`, `sources`, `visualizations`, `metadata` (`trace_id`, `request_id`, modelo usado, `prompt_version`).

Documentos: `docs/UNIFIED_CHAT_ARCHITECTURE.md`, `docs/architecture/INVENTORY.md`, `docs/architecture/COUPLING_MAP.md`.

---

## 4. Qué cambió en Fase 1 (resumen por paquete de trabajo)

| WP | Contenido | ADR |
|---|---|---|
| 0 | `get_settings()` perezoso; suite verde sin credenciales; `pytest-cov`; baseline `FASE1_WP0_BASELINE.md` | 0120 |
| 1 | Layout `tests/{unit,contract,integration,security,evaluation}`; fixtures MIMIC grabadas (3 pacientes, 17 tablas); cliente PostgREST en memoria | 0120 |
| 2 | `chathce/domain` (RequestContext, DTOs, Evidence/Claim, ToolContract/ToolResult, AuditEvent) y `chathce/ports` (9 ports); fakes | 0090 |
| 3 | `MimicClinicalDataProvider`, `ScopeGuard`, migraciones `db/0001` (RPC agregados) y `db/0002` (retira `execute_readonly_query`) | 0050 |
| 4 | SQL libre eliminado del tool y del prompt del runtime legacy | 0050 |
| 5 | Golden set v2 sobre MIMIC-IV (40 preguntas, `ground_truth_operation`, `scope`, `clinical_validation`) y runners adaptados | 0050 |
| 6 | `LLMProvider`, `AnthropicLLMProvider`, `ModelGateway`, `ToolRegistry`, `render_for_model`, system prompt desde contratos | 0080 |
| 7 | Repositorios Supabase: identidad, conversación, análisis, preferencias, conocimiento | 0100 / 0110 |
| 8 | `ChatService`, composition root, 12 tools, fachada legacy; retiro de LangChain del bucle y de `ClaudeLLMManager` | 0080 / 0110 |
| 9 | FastAPI: `/health`, `/ready`, `POST /api/v1/chat`, `POST /api/v1/chat/stream` (SSE), `GET /api/v1/patients/{id}/summary`, `GET /api/v1/visualizations/{id}` | 0100 |
| 10 | Streamlit como adapter: cookie revalidada, selector de paciente activo/episodio, modo investigación, render de `figure_json` | 0100 / 0110 |
| 11 | Suite de seguridad: inyección, cross-patient, scope ausente, validación de resultados, sin caché por usuario | 0090 |
| 12 | Borrado de módulos muertos (`services/medical_agent/`, `auth_service`, `connection_pool_manager`, `rag_service`, `config/config.py`); deps `anthropic>=0.77,<1`, sin crewai/openai/langchain-classic | 0110 |
| 13 | ADRs 0050–0120, documentación, baseline `FASE1_BASELINE.md` | — |

---

## 5. Cómo arrancar / operar

```powershell
conda activate HCE ; streamlit run main.py                                                         # UI Streamlit
conda activate HCE ; python -m uvicorn chathce.api.app:app --host 127.0.0.1 --port 8000 --workers 1  # API
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest                                 # tests sin credenciales
conda activate HCE ; $env:HCE_RUN_INTEGRATION="1" ; python -m pytest -m integration                # integración (lee .env)
conda activate HCE ; python -m Evaluation.run_all_evaluations --dry-run                            # pre-flight de evaluación
conda activate HCE ; python scripts/load_mimiciv.py --verify-only                                  # verificar carga MIMIC-IV
```

Variables mínimas en `.env`: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`. Recomendada: `SUPABASE_CLINICAL_KEY` (rol de solo lectura). Ver `.env.example` para las secciones `CLINICAL_*`, `LLM_*`, `API_*`, `AUDIT_*`.

---

## 6. Verificación de cierre de Fase 1

- Suite: **271 tests pasan, 7 se saltan** (integración sin `HCE_RUN_INTEGRATION=1`), 0 fallos, sin credenciales. Cobertura **56 %** sobre `chathce`, `config`, `services`, `ui`, `src` (`docs/baseline/FASE1_BASELINE.md`).
- Fronteras: `tests/unit/test_architecture_boundaries.py` verifica que `chathce/{domain,ports,application,gateway}` no importan `streamlit`, `supabase`, `postgrest`, `anthropic` ni `langchain*`.
- Superficie visible al modelo sin SQL ni tablas: `tests/security/test_tool_schema_surface.py`, `tests/unit/gateway/test_prompt_has_no_schema.py`.
- Sin `exec`/`eval`/`compile` en el runtime: `tests/security/test_visualization_security.py`.
- Live (solo lectura): provider MIMIC contra Supabase, `AnthropicLLMProvider`, fachada end-to-end con paciente activo (labs devueltas; paciente ajeno rechazado), Streamlit arranca en modo headless. Evaluación live en `docs/baseline/raw/fase1/evaluation/`.

---

## 7. Acciones pendientes del propietario (no automatizables desde el repo)

1. Aplicar en el SQL Editor de Supabase `db/migrations/0001_clinical_aggregates_v1.sql` (habilita `get_dataset_statistics` y visualizaciones de frecuencias) y `db/migrations/0002_revoke_execute_readonly_query.sql` (elimina la RPC de SQL libre). Anotarlo en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.
2. Crear un rol/clave de solo lectura sobre `mimiciv_hosp`/`mimiciv_icu` y guardarla como `SUPABASE_CLINICAL_KEY` en `.env`.
3. Validar clínicamente las 20 preguntas del golden set con `clinical_validation.status="pending"` (`Evaluation/golden_set_ragas.json`).
4. Opcional: definir fuera del repo `HCE_TEST_USER_EMAIL` / `HCE_TEST_USER_PASSWORD` para los tests live de identidad y API; pegar en `db/migrations/0003` las definiciones de `hybrid_search`/`vector_search`.
5. Estado del roadmap por documento: `ROADMAP_HOSPITAL_READY/README.md` (columna Estado) y bloque «Estado a 2 de septiembre de 2026» en cada documento.

---

## 8. Deuda y pendientes conocidos (Fase 2+)

- **RLS por usuario/paciente** en Supabase; hoy el aislamiento lo aplica `ScopeGuard` en la aplicación y la clave de servicio ignora RLS (ADR 0100).
- **Evidence Engine**: una `Claim` por frase con `evidence_ids`; hoy una por tool y una `AI_INFERENCE` por respuesta (ADR 0090).
- **Un solo worker uvicorn** por los modelos locales del RAG; servicio de embeddings separado (ADR 0110).
- **Streaming en Streamlit** (solo la API emite SSE). **Kill switch** y circuit breaker por modelo (Fase 2).
- `services/rag/*`, `src/processors/document_processor.py` y gran parte de `ui/` siguen siendo legacy (cobertura 0–38 %); `ui/components/components/document_manager.py` llama directamente a `get_rag_service()`.
- Cookie de Streamlit legible desde JavaScript (limitación del componente); mitigada con refresh token rotatorio.
- Ficheros no versionados intencionadamente: `TFM VIU Fernando Cagigas.pdf`, `figures/`.

### Riesgos Fase 0: estado

- ✅ CORS/XSRF desactivados en Streamlit (ADR 0060).
- ✅ Ejecución de código de visualización generado por LLM (ADR 0040).
- ✅ SQL libre controlable por el modelo (ADR 0050; la RPC se elimina al aplicar `0002`).
- ✅ Restauración de sesión sin revalidar (ADR 0100).
- ✅ Config duplicada y `SECRET_KEY` sin consumidor (ADR 0110; `config/config.py` eliminado).
