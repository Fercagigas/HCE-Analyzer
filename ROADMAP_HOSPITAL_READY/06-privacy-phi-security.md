# 06 — Privacy, PHI y seguridad de datos

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Data flow inventory | 🟡 | `docs/architecture/INVENTORY.md` §3 (qué sale hacia Anthropic y Supabase); formalizar por campo pendiente |
| P0.2 Data minimisation gateway | ✅ | Catálogo por DTO y frontera única antes del prompt (`ADR 0160`) |
| P0.3 PHI/PII detection | ✅ | DNI/NIE, teléfonos, emails y nombres marcados; modos observe/redact/block (`ADR 0160`) |
| P0.4 Tokenización/pseudonimización | ✅ | Tokens HMAC estables por sesión para paciente, episodio y registros (`ADR 0160`) |
| P0.5 LLM data policy | ⏳ | Un único proveedor; política por modelo/región pendiente |
| P0.6 Encryption | 🟡 | TLS; secretos fuera del repo; clave clinica `clinical_readonly` y verificacion fail-closed preparadas (ADR 0130), pendientes de aplicar y rotar por el propietario |
| P0.6b Superficie de BD endurecida | ✅ | SQL libre eliminado de Supabase (`execute_readonly_query`, `exec_sql`); funciones `SECURITY DEFINER` de triggers con `EXECUTE` revocado a `anon`/`authenticated` y `search_path` fijo (`db/migrations/0002`–`0004`, 2026-09-02). Security advisor sin avisos de funciones. Ver `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md` |
| P0.7 Logging seguro | ✅ | `AuditEvent` sin mensajes, resultados, emails ni tokens; prueba PHI sintético en auditoría y prompt (`ADR 0160`) |
| P0.8 Browser security | 🟡 | XSRF/CORS activos en Streamlit (ADR 0060); CORS restrictivo y cabeceras de seguridad en la API; CSP y cookie HttpOnly pendientes (la cookie de Streamlit solo guarda el refresh token) |
| P1.1 – P1.3 | ⏳ | Fase 2/7 |

## Tareas

### P0.1 — Data flow inventory
Documentar qué datos entran/salen de navegador, backend, DB, vector store, logs y proveedores LLM.

### P0.2 — Data minimisation gateway
Antes del LLM, enviar únicamente atributos necesarios para la tarea. Eliminar nombre, dirección, teléfono, identificadores y otros campos cuando no aporten valor.

### P0.3 — PHI/PII detection
Detector para structured + free text. Clasificar datos sensibles antes de logging, retrieval o envío externo.

### P0.4 — Tokenización/pseudonimización
Usar referencias internas (`PATIENT_x`) cuando la identidad real no sea necesaria. Mapping fuera del contexto LLM.

### P0.5 — LLM data policy
Policy engine por modelo/deployment: qué clases de datos pueden salir, región, retention, training policy, contractual approval y fallback.

### P0.6 — Encryption
TLS en tránsito; cifrado at-rest; gestión segura de claves; rotación; secretos fuera del repo.

### P0.7 — Logging seguro
No registrar prompts/respuestas clínicos completos por defecto. Redacción/tokenización y niveles de logging diferenciados.

### P0.8 — Browser security
CSP estricta, secure cookies, CSRF cuando aplique, CORS restrictivo, headers de seguridad y no almacenar PHI innecesaria en localStorage.

### P1.1 — Retention/deletion
Políticas explícitas para conversaciones, evidence snapshots, audit y caches.

### P1.2 — DLP / egress controls
Detectar y bloquear intentos de extracción masiva o información no necesaria.

### P1.3 — DPIA support
Generar inventario técnico necesario para evaluación de impacto de protección de datos.

## Definition of Done
Se puede responder para cada campo clínico: dónde existe, por qué se necesita, quién puede acceder, si llega a un modelo externo, cuánto tiempo permanece y cómo se elimina.
