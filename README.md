# ChatHCE — Capa de inteligencia clínica sobre MIMIC-IV

ChatHCE es un prototipo académico (Trabajo de Fin de Máster, VIU) de **capa de inteligencia clínica**: un chat con Claude que consulta la historia clínica de un paciente, busca en guías y protocolos indexados (RAG) y genera visualizaciones, sobre el dataset **MIMIC-IV Clinical Database Demo 2.2** (módulos hospitalario y UCI). No sustituye a la HCE; la lee.

Tras la **Fase 1 (Foundation)** del roadmap hospital-ready el sistema tiene:

- Un core `chathce/` con arquitectura de ports and adapters, independiente de Streamlit y de los SDKs (ADR 0110).
- **Scope estricto de paciente**: toda consulta clínica se ejecuta sobre el paciente activo; sin paciente, las herramientas clínicas se rechazan. No existe SQL libre; el acceso a datos es por operaciones allowlisted y agregados server-side (ADR 0050, 0090).
- Un **Model Gateway** propio sobre el SDK `anthropic` con cadena de fallback, timeouts y eventos de alto nivel (ADR 0080).
- Dos canales: **Streamlit** (UI) y **FastAPI** (`/api/v1/chat`, SSE), autenticados con Supabase Auth (ADR 0100).
- Respuestas con hechos, inferencias y evidencia trazable (`facts`, `inferences`, `evidence`, `uncertainty`).
- Suite de tests por capas verde sin credenciales y auditoría sin PHI (ADR 0120).

> Estado detallado: [docs/ESTADO_ACTUAL.md](docs/ESTADO_ACTUAL.md). Roadmap: `ROADMAP_HOSPITAL_READY/`. Índice de documentación: [docs/INDEX.md](docs/INDEX.md).

---

## Arquitectura

```
Canales
  Streamlit  main.py -> src/core/app.py -> ui/* -> chathce.streamlit_adapter
  FastAPI    python -m uvicorn chathce.api.app:app  (JWT Bearer, JSON + SSE)
  Evaluación Evaluation/* -> chathce.legacy.LegacyAgentFacade
        |
        v
  chathce.composition.build_container(get_settings())
        |
  ChatService(RequestContext)
    -> ModelGateway ----------> LLMProvider -> adapters.anthropic (AsyncAnthropic, streaming)
    -> ToolRegistry (12 tools)
         clínicas -----------> ScopeGuard -> ClinicalDataProvider -> Supabase mimiciv_hosp / mimiciv_icu (+ RPC clinical_*_v1)
         search_clinical_documents -> KnowledgeRepository -> Supabase rag_chunks (pgvector) + embeddings/reranker locales
         create_visualization -> plotly_templates (figure_json)
    -> Conversation/Analysis/UserPreferences repositories -> Supabase public.*
    -> AuditSink -> logs/audit/audit.jsonl
```

Herramientas disponibles para el modelo: `get_patient_summary`, `get_admission_details`, `get_diagnoses`, `get_labs`, `search_lab_items`, `get_medications`, `get_icu_stays`, `get_icu_observations`, `search_icd_codes`, `get_dataset_statistics` (solo modo investigación), `search_clinical_documents`, `create_visualization`.

Documentos técnicos: [docs/UNIFIED_CHAT_ARCHITECTURE.md](docs/UNIFIED_CHAT_ARCHITECTURE.md), [docs/architecture/INVENTORY.md](docs/architecture/INVENTORY.md), [docs/decisions/](docs/decisions/).

---

## Instalación

### Prerrequisitos

- Conda (entorno `HCE`, Python 3.11) o Python 3.11 con `pip`.
- Proyecto Supabase con MIMIC-IV Clinical Demo 2.2 cargado (ver `scripts/load_mimiciv.py` y [docs/MIGRACION_MIMIC_IV.md](docs/MIGRACION_MIMIC_IV.md)).
- Clave de API de Anthropic.

### Pasos

```powershell
git clone <url-del-repositorio>
cd HCE-Analyzer
conda env create -f environment.yml
conda activate HCE
copy .env.example .env      # y rellena las credenciales
```

Variables mínimas en `.env` (placeholders, nunca valores reales en Git):

```env
ANTHROPIC_API_KEY=TU_CLAVE_ANTHROPIC_AQUI
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_KEY=TU_CLAVE_SUPABASE_AQUI
# Recomendada: clave de un rol de solo lectura sobre mimiciv_hosp / mimiciv_icu
# SUPABASE_CLINICAL_KEY=TU_CLAVE_SOLO_LECTURA_AQUI
```

El resto de secciones (`LLM_*`, `CLINICAL_*`, `API_*`, `AUDIT_*`) están documentadas en `.env.example`.

### Base de datos

1. Carga o verifica MIMIC-IV: `python scripts/load_mimiciv.py --verify-only`.
2. Aplica en el SQL Editor de Supabase las migraciones de `db/migrations/` (`0001` RPC de agregados; `0002` elimina la RPC de SQL libre). Procedimiento en [db/README.md](db/README.md).
3. Indexa guías clínicas para el RAG: `python scripts/index_guias.py` (carpeta `Guías/`).

Comprobación de configuración:

```powershell
conda activate HCE ; python -c "from config.settings import get_settings; s=get_settings(); s.require_database(); s.require_anthropic(); print('ok')"
```

---

## Ejecución

```powershell
# Interfaz Streamlit (http://localhost:8501)
conda activate HCE ; streamlit run main.py

# API FastAPI (http://127.0.0.1:8000; un solo worker porque el RAG carga modelos locales)
conda activate HCE ; python -m uvicorn chathce.api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

### Uso de la interfaz

1. Regístrate o inicia sesión (Supabase Auth). La cookie solo guarda el refresh token y se revalida en cada carga.
2. En la barra lateral selecciona el **Paciente activo** (`subject_id`) y, opcionalmente, el **Episodio** (`hadm_id`).
3. Pregunta en lenguaje natural. Ejemplos:
   - "Resume el historial del paciente activo."
   - "¿Qué valores de creatinina tiene fuera de rango en este ingreso?"
   - "Lista los diagnósticos del ingreso con sus códigos ICD."
   - "¿Qué recomienda la guía indexada para el manejo de la hiperpotasemia?"
   - "Gráfica de la evolución de la glucosa durante el ingreso."
4. Los usuarios con rol `researcher` pueden activar el **Modo investigación** para estadísticas agregadas del dataset (diagnósticos y fármacos más frecuentes, distribución de tipos de ingreso).
5. Sube guías o protocolos (PDF, DOCX, TXT) desde el panel de documentos; quedan indexados para el RAG.

### API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Proceso vivo |
| GET | `/ready` | Configuración, datos clínicos y LLM comprobados (503 si algo falla) |
| POST | `/api/v1/chat` | Respuesta JSON (`ChatResponse`) |
| POST | `/api/v1/chat/stream` | Server-Sent Events: `status`, `tool_call`, `tool_result_summary`, `text_delta`, `complete`, `error` |
| GET | `/api/v1/patients/{subject_id}/summary` | Resumen del paciente sin LLM |
| GET | `/api/v1/visualizations/{viz_id}` | Figura Plotly en JSON |

Autenticación: `Authorization: Bearer <access_token de Supabase Auth>`. Errores con formato `{"error": {"code", "message", "trace_id", "request_id"}}`; códigos `AUTH_REQUIRED`, `AUTH_INVALID_TOKEN` (401), `SCOPE_VIOLATION`, `PURPOSE_NOT_ALLOWED` (403), `VALIDATION_ERROR` (422), `RATE_LIMITED` (429), `LLM_UNAVAILABLE`, `CLINICAL_DATA_UNAVAILABLE` (503).

```powershell
$body = '{"message":"Resume el ingreso","patient_id":"10001217","purpose":"clinical_care"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/chat -ContentType "application/json" -Headers @{Authorization="Bearer TU_TOKEN_AQUI"} -Body $body
curl.exe -N -H "Authorization: Bearer TU_TOKEN_AQUI" -H "Content-Type: application/json" -d $body http://127.0.0.1:8000/api/v1/chat/stream
```

---

## Tests y evaluación

```powershell
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest                 # sin credenciales ni red
conda activate HCE ; python -m pytest tests/security -q                              # controles de seguridad
conda activate HCE ; $env:HCE_RUN_INTEGRATION="1" ; python -m pytest -m integration  # live, solo lectura
conda activate HCE ; python -m Evaluation.run_all_evaluations --dry-run              # pre-flight
conda activate HCE ; python -m Evaluation.run_all_evaluations                        # RAGAS, seguridad, latencia, casos
```

Estructura y convenciones en [tests/README.md](tests/README.md). Baseline de Fase 1 en [docs/baseline/FASE1_BASELINE.md](docs/baseline/FASE1_BASELINE.md).

---

## Seguridad y privacidad

- Dataset de demostración público y desidentificado (MIMIC-IV Demo). No se procesa PHI real.
- Aislamiento por paciente en la aplicación (`ScopeGuard`), superficie del modelo sin SQL ni nombres de tabla, sin ejecución de código generado, auditoría sin contenido clínico.
- Threat model y checklist operativa de Supabase: [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md), [docs/security/SUPABASE_VERIFICATION_CHECKLIST.md](docs/security/SUPABASE_VERIFICATION_CHECKLIST.md).
- Pendientes conocidos: RLS por usuario/paciente, Evidence Engine, kill switch (ver `docs/ESTADO_ACTUAL.md`).

---

## Estructura del proyecto

```
chathce/            core (domain, ports, application, gateway), adapters, composition, api, streamlit_adapter, legacy
config/             settings.py (get_settings), constants.py, logging_config.py
services/           legacy en migración: rag/, auth/session_manager.py, unified_chat/ (fachadas), cache_manager.py
ui/                 interfaz Streamlit
src/                core/app.py, processors/document_processor.py
db/migrations/      SQL versionado (RPC de agregados, retirada de SQL libre, plantilla RAG)
Evaluation/         runners de evaluación y golden set v2
scripts/            carga MIMIC-IV, indexación RAG, fixtures, golden set
tests/              unit, contract, integration, security, evaluation, fakes, fixtures
docs/               documentación, ADRs (docs/decisions), baselines (docs/baseline)
```

---

## Licencia y aviso

Proyecto académico. El dataset MIMIC-IV Demo se usa bajo sus propios términos (PhysioNet). Este software no es un producto sanitario y no debe usarse para decisiones clínicas reales.
