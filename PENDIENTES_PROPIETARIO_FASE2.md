# Pendientes del propietario al cierre de Fase 2

Este documento explica, paso a paso y con el porqué de cada paso, las dos tareas que quedan abiertas tras integrar en `main` los trabajos de la Fase 2 (Security foundation). Ninguna de las dos puede hacerla un agente desde el repositorio: la primera requiere acceso de Owner al proyecto de Supabase y a su gestor de secretos; la segunda depende de que la primera esté hecha para poder afirmar en la documentación que Fase 2 está verificada y no solo implementada.

Referencias detalladas: `docs/security/SUPABASE_RUNBOOK_FASE2.md` (procedimiento completo con las consultas SQL de verificación), `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md` (registro de comprobaciones), `docs/security/SSO_OIDC_SETUP.md` (SSO), `docs/ESTADO_ACTUAL.md` §7 (lista de acciones) y las ADR 0130, 0170, 0180 y 0190 en `docs/decisions/`.

---

## Tarea 1 — Aplicar en Supabase lo que Fase 2 dejó versionado

### Qué está hecho y qué no

El código de Fase 2 está en `main` y la evidencia offline registrada para la oleada 1 es de 310 tests en verde, 7 omitidos y 0 fallos, sin credenciales. Pero tres piezas viven en la base de datos y solo se materializan cuando el Owner ejecuta las migraciones en el proyecto real de Supabase y emite una credencial nueva. Hasta entonces la aplicación se comporta así:

- El aislamiento por usuario y paciente lo aplica `ScopeGuard` en la aplicación; la base de datos todavía no refuerza las tablas de producto con las políticas RLS de `0005` ni las relaciones con tenant, servicio y vigencia de `0006`.
- El provider clínico falla cerrado: si no encuentra `SUPABASE_CLINICAL_KEY`, usa `SUPABASE_KEY` solo por compatibilidad y bloquea las consultas si `clinical_key_is_readonly_v1()` detecta permisos de escritura o no puede verificarse.
- El RAG no tiene todavía en las tablas reales las columnas de versión, estado y vigencia de `0007`.

### Paso 1. Aplicar las migraciones 0005, 0006 y 0007, en ese orden

En Supabase Dashboard, SQL Editor, pegar y ejecutar completo cada fichero de `db/migrations/`.

**0005 `rls_usuario_paciente_y_clinical_readonly`.** Hace tres cosas:

1. Crea la tabla `public.user_patient_access`: es la lista explícita de qué usuario puede ver qué paciente. Nace vacía a propósito: nadie obtiene una relación asistencial hasta que el Owner la concede.
2. Activa y fuerza RLS en las tablas de producto. En `chat_sessions`, `analyses` y `user_preferences` deja políticas de propiedad con `user_id = auth.uid()`; en `chat_messages`, la propiedad se deriva de la sesión. También restringe el corpus a lectura autenticada, que `0007` sustituye por políticas de tenant para RAG. Por eso los repositorios de producto usan `SUPABASE_ANON_KEY` (o su alias `SUPABASE_PUBLISHABLE_KEY`) junto con el Bearer JWT del usuario; sin JWT o sin clave pública, la persistencia protegida falla cerrada.
3. Crea el rol PostgreSQL `clinical_readonly` sin login y le concede `USAGE` y `SELECT` sobre los esquemas `mimiciv_hosp` y `mimiciv_icu`. Es la base de la clave clínica del paso 3.

**0006 `rbac_abac_relacion_asistencial`.** Amplía `user_patient_access` con `tenant_id`, `service_id`, `valid_from` y `valid_until`, y cambia la clave primaria para que una misma persona pueda atender a un paciente desde varios servicios o tenants con vigencias distintas. Retira a `authenticated` los permisos de escritura sobre esa tabla: las concesiones administrativas se crean desde el backend tras el control RBAC de la API. Los roles (`clinician`, `reviewer`, `admin`, `auditor`, `knowledge_manager`, `researcher`) y el tenant viven exclusivamente en `auth.users.raw_app_meta_data`, nunca en el cuerpo de una petición ni en `public.users` (ADR 0170).

**0007 `rag_governance`.** Añade a `clinical_documents` y `rag_chunks` las columnas de gobierno documental: `tenant_id`, `document_key`, `version`, `effective_from`, `effective_to`, `status` (`draft`, `approved`, `retired`), `approved_by`, `approved_at` y `content_hash`. Activa RLS por tenant comparando contra el claim del JWT mediante la función `rag_current_tenant_id()`, y cambia el contrato de `vector_search` e `hybrid_search` para que exijan tenant y fecha de consulta y solo devuelvan contenido `approved` y vigente. Todo el corpus existente queda marcado como `draft`, por lo que **el RAG dejará de devolver resultados heredados hasta que se revise y apruebe cada documento** (ADR 0180). Esto es deliberado: nunca se promociona contenido sin revisión.

Si una migración falla, hay que parar y no ejecutar las siguientes. La comprobación de que todo quedó bien es la consulta de RLS y políticas del runbook, sección 3: todas las tablas listadas deben mostrar `relrowsecurity = true`; las políticas de sesiones, análisis y preferencias deben referirse a `auth.uid()`, y las de RAG al tenant del JWT.

### Paso 2. Conceder relaciones usuario-paciente y asignar roles

Con la tabla vacía, ninguna cuenta dispone de una relación asistencial. Para cada usuario de prueba hay que insertar una fila en `user_patient_access` con su UUID de `auth.users`, el `tenant_id`, el `subject_id` de MIMIC, el `service_id`, `valid_from = now()` y `granted_by` (SQL exacto en el runbook, sección 3). Después, mediante el endpoint administrativo o el proceso de identidad aprobado, fijar en `auth.users.raw_app_meta_data` un `tenant_id` no vacío y una lista `roles` con valores permitidos.

Prueba de aceptación: con dos cuentas A y B, A crea una sesión de chat por la API y B recibe lista vacía o 404 al pedirla; y un usuario sin relación asistencial vigente recibe denegación al pedir datos de ese paciente. Estas dos pruebas se hacen con JWT de usuario, nunca con la clave de servicio.

### Paso 3. Emitir la clave clínica de solo lectura

El rol `clinical_readonly` existe en la base de datos tras 0005, pero el backend necesita una credencial que lo use. En el mecanismo de emisión de JWT del proyecto hay que crear un JWT cuyo claim `role` sea exactamente `clinical_readonly`, con expiración y rotación documentadas, y guardarlo en el gestor de secretos como `SUPABASE_CLINICAL_KEY`. No sirven `anon`, `authenticated`, `service_role` ni una clave secret.

Verificación desde el SQL Editor: la consulta de `has_table_privilege` del runbook, sección 4, debe devolver exactamente `true, true, false, false, true` (puede leer, no puede insertar ni actualizar, y puede ejecutar la RPC de autoverificación). Al arrancar, el provider clínico consulta `public.clinical_key_is_readonly_v1()`; si la respuesta indica escritura o no se puede verificar, bloquea todas las consultas clínicas.

### Paso 4. Configurar el runtime

En el `.env` local no versionado o en el gestor de secretos:

```dotenv
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_KEY=<CLAVE_AUTH_EXISTENTE_DE_BAJO_PRIVILEGIO>
SUPABASE_ANON_KEY=<CLAVE_PUBLISHABLE_O_ANON>
SUPABASE_CLINICAL_KEY=<JWT_CON_ROLE_CLINICAL_READONLY>
```

`SUPABASE_KEY` se conserva para Auth heredada. `SUPABASE_ANON_KEY` (o `SUPABASE_PUBLISHABLE_KEY`) es la que usan los repositorios de producto junto con el Bearer JWT de cada usuario. Reiniciar el backend después.

### Paso 5. Revisar y aprobar los documentos del RAG

Tras 0007 todos los documentos y chunks heredados quedan en `draft`. Para cada documento heredado hay que revisarlo y, si procede, marcarlo `approved` con `approved_by`, `approved_at`, `version`, `effective_from`, `tenant_id` y un `content_hash` SHA-256 válido. Hasta entonces las consultas de guías clínicas devolverán vacío para ese contenido. `chathce/application/knowledge_governance.py` valida para nuevas cargas el tipo, tamaño, metadatos, vigencia, hash y señales conservadoras de inyección; además expone un autorizador temporal que exige el rol `knowledge_manager`. No aprueba ni persiste documentos por sí mismo, por lo que los heredados requieren revisión manual.

### Paso 6. Verificación live

Con las claves configuradas fuera del repositorio y `ANTHROPIC_API_KEY` disponible, ejecutar:

```powershell
python -m Evaluation.run_security_tests --output Evaluation/results
```

Para el caso de inyección indirecta `SEC-IND-001`, sembrar antes un documento de prueba inocuo y aislado del corpus real y añadir `--include-indirect-fixture`. El gate de la oleada 1 exige cero violaciones `critical`. Registrar cada comprobación completada en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`, sin PHI ni secretos.

### Opcional. SSO con OIDC

El código soporta identidad federada (ADR 0190) pero por defecto sigue usando Supabase Auth (`IDENTITY_PROVIDER=supabase`). Para probarlo hace falta un IdP: en local, `docker compose -f docker-compose.oidc.yml up -d` levanta Keycloak con el realm de prueba de `deploy/keycloak/`. Después, configurar fuera del repositorio `IDENTITY_PROVIDER=oidc`, `OIDC_REDIRECT_URI` y `OIDC_ISSUERS`, una lista JSON que contiene como mínimo `issuer`, `client_id` y el mapeo de claims. `OIDC_SCOPES` y, solo para clientes confidenciales, `OIDC_CLIENT_SECRET`, también están disponibles. Los claims necesarios (tenant, roles, servicio) y la configuración para Entra ID están en `docs/security/SSO_OIDC_SETUP.md`. Los roles OIDC se administran en el IdP, no en ChatHCE.

### Avisos del dashboard de Supabase

Tres avisos de plataforma no se pueden resolver por SQL: activar Leaked Password Protection, habilitar más opciones de MFA y aplicar el upgrade pendiente de Postgres (implica downtime). Detalle en el checklist.

---

## Tarea 2 — Cierre documental de Fase 2

### Por qué queda abierta

La documentación de `main` todavía describe la oleada 2 como «en curso» y el cierre operativo de la oleada 1 como pendiente de verificación live. Marcar Fase 2 como completada con honestidad exige distinguir dos estados: **implementada y probada offline** (hecho para los controles con baseline) frente a **verificada en el entorno real** (depende de la Tarea 1).

### Qué hay que actualizar

- `ROADMAP_HOSPITAL_READY/15-implementation-phases.md`: el encabezado de Fase 2 y las líneas de SSO y RBAC/ABAC, que aún dicen que están en curso o no integrados. Debe reflejar qué está en código y qué sigue pendiente de verificación live.
- `ROADMAP_HOSPITAL_READY/README.md`, columna Estado, y los bloques Estado de los documentos 05 (identidad/autorización/multitenancy), 08 (RAG) y 14 (despliegue).
- `docs/ESTADO_ACTUAL.md`: tabla de fases y sección 7, marcando como hechas las acciones del propietario conforme se completen.
- `docs/baseline/`: un baseline final de Fase 2 con la suite tras el último PR y la evidencia cruda en `docs/baseline/raw/`. El baseline hoy versionado documenta 310 tests verdes y 7 omitidos para la oleada 1; el nuevo debe registrar su propio resultado real, no reutilizar esa cifra.
- `docs/APRENDIZAJES_FASE2.md`: completar las lecciones de la oleada 2, incluido el orden de migraciones y las decisiones operativas relevantes que hayan quedado evidenciadas.
- `docs/security/THREAT_MODEL.md`: mitigaciones aplicadas por RBAC, gobierno RAG y OIDC, diferenciándolas de los controles todavía pendientes de verificación live.
- Plan de Fase 3 (Evidence-first AI) y, si se inicia esa oleada, la ADR de arquitectura del Evidence Engine para arrancarla con la decisión tomada.

### Cuándo hacerlo

Puede hacerse ya la parte de «implementado», y volver a tocarse cuando la Tarea 1 termine para pasar a «verificado». Lo natural es que un worker haga la primera parte como primer paquete de la oleada 3 y que la segunda se cierre en el mismo PR o en uno posterior una vez el Owner registre las verificaciones en el checklist.
