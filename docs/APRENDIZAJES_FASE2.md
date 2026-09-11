# Aprendizajes de la Fase 2 (Security foundation), oleada 1

**Fecha:** 11 de septiembre de 2026
**Alcance:** RLS y clave clínica readonly, contención operativa de IA, minimización/detección de PHI y evaluación adversarial/CI (ADRs 0130, 0140, 0150 y 0160). Complementa `docs/baseline/FASE2_BASELINE.md`: este documento explica decisiones, razones y lecciones; el baseline conserva la evidencia.

---

## 1. El punto de partida: seguridad de aplicación no equivale a defensa en profundidad

Fase 1 ya obligaba a transportar un `RequestContext`, rechazaba el paciente equivocado con `ScopeGuard`, eliminaba SQL libre y auditaba sin PHI. Era una base necesaria, pero aún dejaba cuatro huecos: la base de datos no imponía ownership por usuario, una clave clínica podía no ser realmente de solo lectura, el proveedor LLM no podía detenerse de forma central y el texto enviado al modelo no tenía una política de mínimo necesario.

La primera lección es que los límites clínicos relevantes deben repetirse en capas distintas. Un filtro de aplicación reduce errores de flujo; RLS y una clave con privilegios verificables limitan qué puede ocurrir si ese filtro se omite. Ninguna capa sustituye a la otra.

## 2. Decisiones de seguridad y su razonamiento

### 2.1 Ownership en la base y clave clínica verificable (ADR 0130)

La decisión fue reenviar el JWT de usuario con una clave publishable para conversaciones, análisis y preferencias, y aplicar RLS por ownership. Para datos MIMIC se separó una credencial `clinical_readonly` que debe superar una RPC de verificación; si no puede demostrar que no escribe, el provider falla cerrado.

No se aceptó una `service_role` por comodidad ni filtros de `user_id` solo en adapters: ambas opciones convierten un fallo futuro de código o configuración en una posible elusión de la frontera de datos. La relación `user_patient_access` prepara la concesión explícita, pero no inventa aún una relación asistencial completa.

**Lección:** la frase “solo lectura” debe ser una propiedad comprobable del privilegio, no una convención de nombres ni un comentario en configuración.

### 2.2 Degradar con honestidad cuando la IA no es segura o no está disponible (ADR 0140)

El kill switch se consulta antes de historial, prompt, gateway y tools; un fichero runtime permite cambiar el estado sin redeploy y un valor inválido falla cerrado. El circuit breaker se mantiene por par `provider+model`, no por proveedor global, para que un modelo degradado no prive del fallback a uno aprobado.

Se descartó depender únicamente de una variable leída al arrancar y almacenar el flag en Supabase. La primera obliga a reiniciar; la segunda convierte la contención en dependiente de un plano de datos que también puede fallar.

**Lección:** la degradación segura es una funcionalidad de producto. Debe ser visible en `/ready`, coherente en JSON/SSE/UI y dejar una huella de auditoría sin arrastrar texto clínico.

### 2.3 Mínimo necesario antes, no después, del proveedor (ADR 0160)

La minimización se diseñó como catálogo por DTO: elimina texto libre, generaliza fechas y pseudonimiza identificadores de forma estable solo dentro de la sesión. El detector se aplica al mensaje, historial y resultados de tools en las fronteras del prompt; `redact` es el valor por defecto y `block` evita por completo la llamada al modelo.

No se eligió una única expresión regular al final del gateway: llega demasiado tarde para estructurados y no define qué significa conservar contexto clínico útil. Tampoco se eliminan todos los identificadores y fechas, porque rompería la continuidad de episodios.

**Lección:** privacidad útil no consiste en borrar ciegamente; consiste en declarar campo por campo qué se elimina, generaliza o pseudonimiza, y probar que ni el proveedor ni la auditoría ven el original.

### 2.4 La suite adversarial es un gate, no una demostración puntual (ADR 0150)

La suite offline determinista se convirtió en requisito bloqueante de CI porque los controles críticos no pueden depender de secretos, red, coste de proveedor ni disponibilidad de un entorno externo. Se amplió a codificaciones, homoglifos, leetspeak, tokens partidos, mezcla de idiomas, artefactos cross-tenant, pestañas paralelas, exfiltración y allowlist.

El runner live sigue siendo manual y de solo lectura. Es el lugar correcto para comportamiento probabilístico, datos reales autorizados y el caso indirecto con documento sembrado, pero no debe ejecutarse en cada pull request ni exponerse a forks.

**Lección:** la seguridad de IA necesita dos instrumentos: un gate offline rápido y reproducible, y una evaluación live deliberada que conserve severidad, contexto y autorización.

## 3. Cómo interpretar la evidencia

El cierre de oleada 1 ejecutó 317 tests: 310 pasan y 7 de integración se saltan sin credenciales; la cobertura es 57 %. La suite adversarial suma 78 controles offline y registró **cero violaciones críticas**. Frente a Fase 1, son 39 tests verdes más y un punto de cobertura adicional.

Estas cifras acreditan contratos y fakes bajo condiciones reproducibles. No acreditan por sí solas que Supabase tenga aplicada `0005`, que la clave desplegada sea realmente `clinical_readonly`, ni que un modelo real rechace toda inyección. Esas afirmaciones requieren las verificaciones live del runbook y el runner de seguridad con secretos autorizados.

## 4. Coordinación: lecciones que también son controles

### 4.1 Las migraciones necesitan un dueño de numeración

Durante la oleada hubo una colisión de numeración alrededor de `0004`: la migración de RLS se renumeró a `0005` para preservar `0004_harden_security_definer_functions.sql`. El árbol final tiene una secuencia ejecutable clara `0001`, `0002`, `0003_drop_exec_sql`, `0004`, `0005`; el fichero `0003_rag_search_functions_snapshot.sql` es un snapshot heredado, no ejecutable, y no se aplica.

**Lección:** reservar el número antes de abrir trabajo paralelo y comprobar la secuencia al integrar evita que una migración correcta se vuelva peligrosa por orden ambiguo. El runbook debe decir qué se ejecuta y qué es solo evidencia, no delegarlo al nombre del fichero.

### 4.2 El token puede bloquear el flujo aunque el código esté listo

El alcance del token de workflow impidió completar acciones remotas del flujo de seguridad. El cambio se resolvió manteniendo CI con una suite offline sin secretos y dejando las operaciones que exigen credenciales —incluida la evaluación live— como pasos explícitos del propietario.

**Lección:** permisos de automatización son parte del diseño de entrega. Validarlos al inicio evita confundir un bloqueo de plataforma con una falta de implementación o relajar un gate crítico para “hacerlo pasar”.

### 4.3 Los documentos compartidos requieren propiedad de secciones

`docs/ESTADO_ACTUAL.md` y el roadmap `06-privacy-phi-security.md` sufrieron conflictos repetidos porque varias oleadas actualizaban el mismo resumen. La resolución correcta no es reescribir el estado ajeno: es integrar sobre `main` actualizado, aplicar cambios mínimos y expresar con precisión qué está integrado, qué es pendiente y qué está en curso.

**Lección:** los documentos de estado son artefactos de integración. Mantener una fuente de verdad, una fecha de corte y una frase explícita para trabajo paralelo reduce conflictos técnicos y de expectativas.

## 5. Qué permanece abierto

1. El propietario debe aplicar `0005`, crear/rotar `SUPABASE_CLINICAL_KEY`, conceder accesos de paciente y comprobar RLS/fail-closed en un entorno autorizado.
2. El runner `Evaluation.run_security_tests.py` debe ejecutarse con secretos fuera del repositorio, incluyendo `SEC-IND-001` solo con un documento de prueba aislado.
3. RBAC/ABAC completo, gobierno del RAG y SSO OIDC están en curso en oleadas paralelas; no se atribuyen a este cierre.
4. DLP externo, política de egreso por proveedor, relación asistencial completa, persistencia distribuida del circuit breaker y pruebas RLS/multi-tenant efímeras siguen siendo trabajo posterior.

## 6. Lo transferible

1. Defender el acceso sensible en aplicación, base de datos y credenciales separadas.
2. Diseñar el apagado de IA antes de necesitarlo y ensayarlo sin generar ni procesar datos.
3. Minimizar en las fronteras de datos con una política comprobable por campo.
4. Hacer que el gate crítico sea offline, determinista y bloqueante; reservar live para evidencia autorizada.
5. Tratar numeración de migraciones, permisos de tokens y ownership documental como parte de la seguridad operacional.
6. Escribir los límites y los pendientes con la misma claridad que los controles terminados.
