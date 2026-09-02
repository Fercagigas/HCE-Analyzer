# Estado actual del proyecto ChatHCE

**Última actualización:** 1 de septiembre de 2026
**Rama principal:** `main`

Este documento resume, de forma precisa, en qué punto se encuentra el proyecto: qué está hecho, qué acaba de cambiar y qué queda pendiente. Sirve como punto de entrada rápido para retomar el trabajo.

---

## 1. Resumen en una frase

ChatHCE es un prototipo Streamlit de capa de inteligencia clínica (chat unificado con Claude + RAG + visualizaciones) que, tras la Fase 0 (baseline, inventario, intended purpose, threat model), acaba de **migrar su fuente de datos clínicos de MIMIC-IV-ED a MIMIC-IV Clinical Demo 2.2**. La transformación hacia arquitectura hospital-ready (FastAPI, Model Gateway, Clinical Data Gateway) sigue pendiente (Fase 1+).

---

## 2. Fase del roadmap

| Fase | Estado | Notas |
|---|---|---|
| **Fase 0 — Freeze y baseline** | ✅ Completada | Baseline de tests, inventario, mapa de acoplamiento, intended purpose, out-of-scope, matriz de riesgo, threat model. ADRs 0001/0010/0020/0030. |
| **Migración de datos MIMIC-IV** | ✅ Completada | Fuera de la secuencia estricta del roadmap; prevista por DP-03 ("MIMIC-IV-ED es adapter transitorio"). Ver §4. |
| **Mitigaciones de seguridad iniciales** | ✅ Integradas | Cierre de superficie web XSRF/CORS + bind localhost (ADR 0060), visualizaciones parametrizadas sin ejecución de código LLM (ADR 0040) con `tests/test_visualization_security.py`, checklist de verificación de Supabase (ADR 0070). |
| **Fase 1 — Foundation / P0** | ⏳ Pendiente | Separar core de Streamlit, FastAPI, Model Gateway, Clinical Data Gateway tipado, `RequestContext`, eliminación de SQL libre. |
| Fases 2–9 | ⏳ Pendientes | Seguridad completa, evidencia, frontend React, FHIR/SMART, features AI-first, piloto. |

Detalle del roadmap: `ROADMAP_HOSPITAL_READY/` y steering `.kiro/steering/roadmap.md`.

---

## 3. Arquitectura ejecutable actual

Monolito Streamlit (sin FastAPI todavía):

```
main.py -> src/core/app.py
  -> SessionManager -> AuthService ---------> Supabase Auth/public
  -> UnifiedChatInterface
       -> UnifiedChatAgent -> ClaudeLLMManager -> Anthropic
            -> DatabaseTool  -> DatabaseService -> Supabase mimiciv_hosp/mimiciv_icu
            -> RAGTool       -> ImprovedRAGService -> Supabase rag_chunks (pgvector) + HF
            -> VisualizationCollaborationTool -> DatabaseService / VisualizationAgent
```

- **LLM:** Claude Haiku 4.5 (primario) con fallback Sonnet/Opus.
- **Datos clínicos:** MIMIC-IV Clinical Demo 2.2 en Supabase.
- **RAG:** pgvector + embeddings/reranker locales (Hugging Face).
- **Auth/persistencia:** Supabase (`public.*`).

---

## 4. Migración MIMIC-IV (recién completada)

**De:** MIMIC-IV-ED (urgencias, schema `mimic_ed`, 6 tablas, 222 estancias)
**A:** MIMIC-IV Clinical Demo 2.2 (hospitalario + UCI, 100 pacientes, 18 tablas, ~1,48M filas)

### Esquemas nuevos en Supabase
- `mimiciv_hosp` (15 tablas): patients, admissions, transfers, services, diagnoses_icd (+ d_icd_diagnoses), procedures_icd (+ d_icd_procedures), labevents (+ d_labitems), microbiologyevents, omr, prescriptions, pharmacy, emar.
- `mimiciv_icu` (3 tablas): icustays, chartevents (+ d_items).
- `mimic_ed` **eliminado**.

### Cambio de modelo de datos
- Eje del episodio: `hadm_id` (admisión hospitalaria); `stay_id` pasa a ser estancia UCI.
- Diagnósticos/procedimientos guardan solo códigos ICD → título vía JOIN con diccionarios.
- Labs/chartevents guardan `itemid` → nombre vía d_labitems/d_items.

### Seguridad (mantiene la posición previa)
- RLS + política SELECT para `authenticated`; escritura revocada a `anon`/`authenticated`.
- Esquemas expuestos vía PostgREST; RPC `execute_readonly_query` con search_path a los nuevos esquemas.

### Verificación realizada
- Conteos por tabla exactos vs CSV origen; integridad referencial OK (0 huérfanos).
- Smoke test del data service + tool (patient_summary, labs, diagnoses con títulos, custom query por RPC, rechazo del esquema antiguo).

Documentación:
- Diccionario de datos (columna a columna, 18 tablas): `docs/MIMIC_IV_DATA_DICTIONARY.md`
- Contexto y cambios de la migración: `docs/MIGRACION_MIMIC_IV.md`

---

## 5. Código tocado por la migración

- `config/settings.py` — `allowed_schemas = ["mimiciv_hosp", "mimiciv_icu"]`.
- `services/medical_agent/services/database_service.py` — reescrito; mapa `TABLE_SCHEMA` y operaciones clínicas nuevas.
- `services/unified_chat/tools/database_tool.py` — nuevo contrato/esquema para el LLM y query types.
- `services/medical_agent/prompt_manager.py` — identidad/contexto/esquema/ejemplos.
- `services/medical_agent/tools/visualization_collaboration_tool.py` — fuentes de datos/agregados.
- `services/connection_pool_manager.py` — health check.
- `utils/validators/mimic_validator.py` — conteos/columnas/integridad.
- `scripts/load_mimiciv.py` — cargador idempotente (nuevo).
- Docs: README, CONFIGURACION_SUPABASE_VERIFICADA, UNIFIED_CHAT_ARCHITECTURE, PROMPT_ENGINEERING_GUIDE, UNIFIED_CHAT_COMPLETE_GUIDE, INDEX, MIGRACION_MIMIC_IV (nuevo).
- Steering: tech.md, structure.md, product.md.

---

## 6. Cómo arrancar / operar

```powershell
conda activate HCE ; python start_app.py            # arrancar app (con verificaciones)
conda activate HCE ; streamlit run main.py           # arrancar directo
conda activate HCE ; python -m pytest                # tests
conda activate HCE ; python scripts/load_mimiciv.py --verify-only   # verificar carga MIMIC-IV
```

Requiere en `.env`: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` (service_role), `SECRET_KEY`.

---

## 7. Deuda y pendientes conocidos

### De la migración
- **Golden sets de evaluación** (`Evaluation/golden_set_*.json`) siguen siendo de urgencias; hay que regenerarlos con preguntas/SQL del nuevo modelo (tarea de evaluación con diseño clínico).
- El enriquecimiento de títulos de diagnóstico hace N consultas (una por código); funciona a escala demo, optimizable con un JOIN/`in_`.
- Dataset descomprimido en `_mimic_iv_extract/` (en `.gitignore`); borrable si no se va a recargar.

### Del roadmap (Fase 1+)
- SQL libre (`custom_query`) sigue existiendo como activo de investigación; sustituir por `ClinicalDataProvider` tipado.
- No hay FastAPI, Model Gateway, `RequestContext` ni aislamiento por tenant/paciente.
- Suite de tests no está verde sin credenciales (settings exige Supabase en tiempo de importación).

### Riesgos Fase 0: estado
- ✅ **Mitigado** — CORS/XSRF desactivados en Streamlit: cerrados y bind a localhost (ADR 0060).
- ✅ **Mitigado** — Ejecución de código de visualización generado por LLM: ruta clínica limitada a templates parametrizados (ADR 0040).
- ⏳ **Vigente** — Restauración de sesión confiando en cookie sin revalidar contra Supabase.
- ⏳ **Vigente** — Config duplicada `settings.py`/`config.py`; `SECRET_KEY` ausente de `.env.example`.
- ⏳ **Vigente** — SQL libre controlable por el modelo (ver arriba).

---

## 8. Estado git

- `main` sincronizado con `origin/main`; sin PRs abiertos.
- PRs integrados en esta sesión:
  - #12 Threat model inicial (ADR 0030)
  - #13 Checklist de verificación de Supabase (ADR 0070)
  - #14 Migración MIMIC-IV-ED → MIMIC-IV Clinical Demo 2.2
  - #15 Cierre de superficie web XSRF/CORS (ADR 0060)
  - #16 Visualización: métricas en datasets pequeños
  - (previo) Visualizaciones parametrizadas sin ejecución de código (ADR 0040) + `tests/test_visualization_security.py`
- Ramas de trabajo locales ya fusionadas eliminadas.
- Artefactos de tesis (`TFM VIU Fernando Cagigas.pdf`, `figures/`) permanecen sin versionar intencionadamente.
