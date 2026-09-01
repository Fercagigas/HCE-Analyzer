# ADR 0070 — Verificación operativa de Supabase y despliegue

Estado: Aceptada

Fecha: 2026-09-01

## Contexto

El threat model inicial identifica controles externos que no pueden verificarse desde el repositorio: tipo y privilegios de `SUPABASE_KEY`; RLS, policies, grants y definiciones de RPC; topología TLS/red; retención, región y política del proveedor; corpus desplegado y sus administradores; caché/procesos; y clase real de los datos. Por prudencia, ninguno reduce hoy el riesgo residual.

El inventario demuestra además que una única pareja `SUPABASE_URL`/`SUPABASE_KEY` alimenta Auth, tablas de producto, seis tablas clínicas `mimic_ed`, RAG y tres RPC. El código no impone si esa clave es de bajo privilegio o elevada. La infraestructura live y sus credenciales no pertenecen al repositorio y no deben entregarse a revisores ni incorporarse a Git.

Se necesita una comprobación que el propietario pueda ejecutar en aproximadamente veinte minutos por entorno, que produzca una decisión binaria y evidencia trazable sin revelar secretos. Esta decisión no autoriza uso hospitalario ni sustituye las mitigaciones de identidad, multitenancy, privacidad y PHI del roadmap.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Asumir los defaults de Supabase y del proveedor como controles existentes.** Descartada: los defaults dependen de fecha, plan, schema y configuración; una clave elevada omite RLS, y la mera disponibilidad de una función no prueba sus grants ni su cuerpo desplegado.
2. **Pedir credenciales y automatizar una auditoría live desde el equipo de desarrollo.** Descartada: amplía la exposición de secretos, crea un nuevo actor privilegiado, contradice mínimo privilegio y no es necesaria para obtener la evidencia.
3. **Inferir el estado live desde SQL/migraciones versionadas.** Descartada como única fuente: no existen definiciones versionadas de las RPC y, aunque existieran, una migración no demuestra que se aplicó al proyecto correcto ni que no hubo deriva manual.
4. **Emitir un informe narrativo libre.** Descartada: no garantiza cubrir cada incertidumbre, no cabe en una ejecución breve y dificulta distinguir control confirmado, riesgo confirmado y dato no verificado.
5. **Adoptar una checklist versionada, ejecutada por el propietario, con rutas de panel, consultas de solo lectura, criterios OK/problema y gravedad.** Elegida: mantiene los secretos bajo control del propietario, vincula evidencia al entorno real y permite repetir la verificación después de cambios.

## Decision

Se adopta `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md` como procedimiento canónico para verificar los controles externos de Supabase y del despliegue.

El propietario ejecutará la checklist por entorno con permisos Owner/Admin y conservará la evidencia en un sistema protegido fuera de Git. La evidencia versionada en el proyecto se limitará a estado, fecha, responsable, alias no sensible, gravedad y referencia interna; nunca contendrá claves, tokens, URL/ref del proyecto, credenciales, IP, emails ni datos clínicos.

Un control solo podrá marcarse confirmado cuando el resultado sea correcto, exista evidencia fechada y esté vinculado al entorno. Un resultado problemático se convierte en riesgo confirmado con la gravedad indicada. Un resultado no ejecutado, ambiguo o sin evidencia continúa como incertidumbre y no reduce el riesgo residual.

La checklist es de solo lectura. Las acciones de contención y rotación descritas en ella son un runbook posterior: no se ejecutan como parte de esta decisión ni autorizan cambios live por terceros. Una clave elevada en la variable compartida, RLS/RPC insegura, exposición pública del prototipo o PHI sin acuerdos aplicables obliga a contener el entorno antes de continuar.

## Motivo

La decisión separa dos responsabilidades: el repositorio define qué evidencia hace falta y el propietario, que ya controla el proyecto, verifica el estado real. Así se evita trasladar secretos y se obtiene una prueba repetible más fuerte que una declaración verbal o una captura aislada.

Las consultas se limitan a catálogos PostgreSQL y metadatos; no necesitan leer contenido clínico. Los criterios cubren conjuntamente grants y RLS, porque ninguno basta por separado, y tratan las funciones aparte porque RLS no controla el permiso `EXECUTE`. También incluyen las fronteras que Supabase no puede demostrar por sí solo: proxy, host, proveedor LLM, corpus, scripts y caché.

## Consecuencias

- El propietario dispone de un recorrido de veinte minutos para convertir cada incertidumbre en `OK`, `PROBLEMA` o `NO VERIFICADO`.
- No se incorporan credenciales ni evidencia sensible al repositorio y ningún revisor necesita acceso al proyecto Supabase.
- La rotación de clave queda descrita con transición, prueba, revocación y tratamiento específico de claves legacy.
- Un resultado `OK` representa una fotografía fechada, no una garantía permanente; cambios de proyecto, clave, schema, policy, función, región, proveedor, corpus o despliegue invalidan la evidencia afectada.
- La checklist puede confirmar controles externos, pero no corrige defectos del runtime ni convierte por sí sola el prototipo en hospital-ready.
- La ejecución breve prioriza gates críticos. No sustituye pentest, DPIA, revisión contractual, pruebas de aislamiento ni audit clínico continuo.

## Pendientes

- Ejecutar la checklist en cada entorno y enlazar el registro protegido de resultados al threat model.
- Asignar y cerrar cada riesgo confirmado; repetir los items afectados tras la corrección.
- Versionar en migraciones las tablas, grants, policies y definiciones de `execute_readonly_query`, `hybrid_search` y `vector_search`, con tests allow/deny.
- Separar credenciales por función y eliminar la dependencia de una única `SUPABASE_KEY` antes de cualquier exposición hospitalaria.
- Documentar la topología concreta del proveedor de despliegue, propietarios, redes y proceso de cambio.
- Establecer periodicidad de revalidación y triggers obligatorios: rotación, cambio de plan/región/proveedor, nueva réplica, schema/RPC, corpus, scaling o clasificación de datos.
- Actualizar el threat model solo cuando la evidencia confirme el control; mantener como riesgo cualquier problema o ausencia de prueba.
