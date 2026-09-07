# ADR 0090 — RequestContext, aislamiento de contexto, contratos de tools y schemas Evidence/Claim

Estado: Aceptada

Fecha: 2026-09-02

## Contexto

Ninguna operación clínica recibía contexto explícito: el paciente se infería del prompt y el
usuario de `st.session_state`. El roadmap (docs 05 y 07, P0.1) exige `RequestContext`
obligatorio (tenant, usuario, paciente, episodio, sesión, traza), contratos de tools con
schemas cerrados, y respuestas que separen hechos observados de inferencias del modelo con
evidencia trazable. El usuario decidió un modelo de **scope estricto**: la interfaz fija un
paciente activo y sin él las tools clínicas se rechazan.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Scope implícito: el modelo indica el `subject_id` en cada llamada y el sistema lo acepta.**
   Descartada: cualquier documento o mensaje puede inducir al modelo a cambiar de paciente;
   es la causa del riesgo cross-patient.
2. **Scope laxo: sin paciente activo se permite cualquier paciente, con paciente activo se
   restringe.** Descartada: convierte el estado por defecto en el más permisivo.
3. **Scope estricto con selector de paciente y modo investigación para agregados** (elegida).
   El `RequestContext` lleva `patient_id`; `ScopeGuard` y `ToolPolicy` rechazan operaciones sin
   paciente o fuera de él; los agregados exigen `purpose=research`, que a su vez exige el rol
   `researcher`.
4. **Evidence Engine completo (una `Claim` por frase con `evidence_ids`).** Aplazada a Fase 3:
   requiere post-procesado del texto del modelo. En Fase 1 se emite una `Claim` por resultado
   de tool exitoso (hechos) y una `Claim` `AI_INFERENCE` con el contenido.

## Decision

- `RequestContext` (`chathce/domain/context.py`): `tenant_id`, `user_id`, `patient_id`,
  `encounter_id`, `session_id`, `trace_id`, `request_id`, `purpose`, `roles`, `channel`.
  `build_context()` rechaza `purpose=research` sin rol `researcher`. Toda tool, caso de uso y
  operación del provider lo recibe como primer argumento.
- `ToolContract` y `ToolResult` (`chathce/domain/tools.py`): entrada `extra=forbid`,
  `requires_patient_scope`, `requires_purpose`, `timeout_s`, `max_rows <= 200`,
  `audit_category`; `ToolResult` con `success`, `scope`, `count/limit/truncated`, `error`,
  `evidence`, `artifacts` y texto visible al modelo.
- `Evidence` y `Claim` (`chathce/domain/evidence.py`): cada DTO clínico lleva
  `evidence_id = "mimic:<recurso>:<id>"`; la respuesta `ChatResponse` expone `facts`,
  `inferences`, `evidence`, `uncertainty`, `tool_calls`, `sources`, `visualizations`,
  `metadata` (`chathce/domain/chat.py`).
- Aislamiento: rate limit por `user_id`; sin caché de respuestas; historial resumido sin
  datos de tools; auditoría (`chathce/domain/audit.py`) con allowlist de atributos, nunca
  mensajes, resultados, emails ni tokens.
- Streamlit: selector "Paciente activo" y "Episodio" en la barra lateral; toggle de modo
  investigación solo para el rol `researcher`.

## Motivo

Un contexto explícito e inmutable por petición es la única entrada que las políticas pueden
comprobar; el scope estricto hace que el estado por defecto sea el más seguro; los contratos
cerrados impiden que el modelo introduzca parámetros no previstos; Evidence/Claim fijan el
formato que consumirá el Evidence Engine sin exigirlo ahora.

## Consecuencias

- Positivas: `tests/security/` demuestra rechazo sin paciente, con paciente ajeno y con
  `hadm_id` ajeno; la API devuelve 403 `SCOPE_VIOLATION`/`PURPOSE_NOT_ALLOWED`.
- Negativas: fricción de uso (hay que elegir paciente antes de preguntar); preguntas mixtas
  que abarcan varios pacientes ya no son posibles fuera del modo investigación.
- `tenant_id` es siempre `default` en Fase 1; el campo existe para no rediseñar en Fase 2.

## Pendientes

- Evidence Engine y citación por frase (Fase 3).
- Verificación server-side del vínculo usuario-paciente (hoy el paciente lo elige el usuario
  autenticado; RLS y política de acceso en Fase 2).
- Multi-tenant real y roles gestionados en Supabase (hoy `roles` proviene de metadatos de usuario).
