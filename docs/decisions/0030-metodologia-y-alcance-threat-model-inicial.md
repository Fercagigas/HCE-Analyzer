# ADR 0030 — Metodología y alcance del threat model inicial

Estado: aceptado para el baseline de Fase 0

Fecha: 2026-09-01

## Contexto

ChatHCE cierra la Fase 0 con un modelo de amenazas de la implementación existente. El sistema observado es un monolito Streamlit que concentra identidad, estado, orquestación del LLM, tools, acceso a Supabase, RAG y ejecución de visualizaciones. La arquitectura objetivo del roadmap todavía no existe y no puede contabilizarse como control.

El método debe cubrir tanto amenazas de software distribuido —identidad, autorización, integridad, divulgación, disponibilidad y privilegios— como amenazas propias de un sistema agentic con RAG y tools: prompt injection directa e indirecta, extracción del system prompt, SQL/tool injection, exfiltración, fugas de contexto, consultas masivas, poisoning, documentos maliciosos, tool misuse, agotamiento y código generado.

El intended purpose, las exclusiones, la matriz de riesgo y las decisiones DP-01 a DP-08 ya están aprobados. El threat model no debe reabrirlos ni aceptar riesgo residual. Tampoco es una prueba ofensiva, una DPIA, una clasificación regulatoria o el risk file clínico futuro.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Aplicar solo STRIDE por componente.** Se descarta como método completo porque clasifica bien spoofing, tampering, repudiation, information disclosure, denial of service y elevation of privilege, pero no hace suficientemente visibles las cadenas propias de LLM/RAG/tools ni obliga a separar direct injection, indirect injection, poisoning y ejecución de salida del modelo.
2. **Usar solo una lista de amenazas de IA, por ejemplo OWASP para aplicaciones LLM.** Se descarta porque puede omitir fallos convencionales que aquí son dominantes, como restauración de sesión, IDOR, CSRF, secretos, auditabilidad y supply chain. Una taxonomía externa tampoco sustituye la trazabilidad al código real.
3. **Aplicar LINDDUN como método principal.** Se descarta para este baseline porque aporta profundidad de privacidad, pero no cubre por sí solo autorización de tools, integridad, ejecución de código y disponibilidad. Sus preocupaciones de privacidad se conservan en los impactos y en las amenazas de exfiltración/leakage.
4. **Aplicar PASTA o construir attack trees cuantitativos completos.** Se descarta en Fase 0 porque exige información operacional, actores, telemetría, despliegue y probabilidad cuantitativa que el repositorio no proporciona. Daria una precisión aparente y retrasaría el inventario accionable.
5. **Modelar la arquitectura objetivo del roadmap.** Se descarta porque confundiría controles planificados con implementados y ocultaría la exposición que debe reducir Fase 1 y 2.
6. **Combinar STRIDE por cada confín de confianza real con un registro explícito de amenazas de IA y valoración cualitativa conservadora.** Se elige porque cubre el sistema convencional y las cadenas agentic, mantiene trazabilidad a fichero/línea y permite mapear cada riesgo a una fase sin inventar controles o datos de despliegue.

## Decision

El threat model inicial se documenta en `docs/security/THREAT_MODEL.md` y adopta estas reglas:

1. La unidad de análisis STRIDE es cada confín de confianza observado en el código actual: navegador/Streamlit, UI/core, Supabase de producto, datos clínicos/RPC, Anthropic, ingesta/RAG, executor/host, persistencia local/scripts y Hugging Face/artefactos.
2. STRIDE se aplica a todos los confines mediante una matriz completa; cada escenario remite a un registro detallado.
3. Se mantiene un registro específico y explícito para las trece amenazas de IA requeridas: prompt injection directa, extracción del system prompt, indirect injection, SQL/tool injection, exfiltración, fugas cross-patient y cross-tenant, bulk queries, RAG poisoning, documentos maliciosos, tool misuse, resource exhaustion y ejecución de código generado.
4. Cada amenaza debe incluir activo, vector, precondiciones, impacto clínico y de privacidad, probabilidad, controles existentes, riesgo residual y documento/fase de mitigación.
5. Solo cuentan como controles existentes los verificables en esta fotografía del repositorio. RLS, TLS, WAF, secret manager, contratos de proveedor y otras defensas externas desconocidas no reducen el riesgo hasta que se documenten y prueben.
6. La valoración es cualitativa —probabilidad Alta/Media/Baja y riesgo residual Crítico/Alto/Medio/Bajo— porque no hay telemetría, despliegue canónico ni tasas históricas suficientes para una estimación cuantitativa fiable.
7. La severidad del threat model es una priorización de seguridad y no sustituye la escala de riesgo inherente por capability de `docs/product/RISK_CAPABILITY_MATRIX.md`.
8. No se ejecutan exploits ni ataques live. La evidencia procede de documentación, inspección estática del código y baseline de pruebas ya capturado.
9. El modelo describe el sistema en el commit `235f5ea`. Los controles objetivo se citan solo como mitigaciones trazadas a Fase 1, Fase 2 o posteriores.
10. El threat model no acepta riesgos ni amplía el intended purpose. Todo riesgo residual Crítico bloquea una exposición hospitalaria y permanece dentro de la prohibición vigente de DP-07.

## Motivo

STRIDE aporta cobertura sistemática de los cambios de confianza y evita concentrarse únicamente en el LLM. El catálogo de IA hace visibles las cadenas en las que texto no confiable controla retrieval, argumentos de tools o código, que son los riesgos diferenciales de ChatHCE. La valoración cualitativa conservadora permite priorizar sin fingir datos estadísticos que no existen.

Modelar el sistema actual mantiene la separación entre hechos y aspiraciones: por ejemplo, una regex SQL, un límite local o un validador AST se registran como controles parciales, mientras que `RequestContext`, RBAC/ABAC, DLP, sandbox, audit trail y kill switch siguen siendo mitigaciones futuras. Esto produce entradas accionables para Fase 1 y 2 sin reabrir decisiones de producto.

## Consecuencias

- El resultado contiene solapamientos deliberados: una misma cadena puede aparecer en STRIDE y en el registro de IA, pero conserva un único ID detallado para trazabilidad.
- Las incertidumbres externas aumentan o mantienen el riesgo; nunca se convierten en supuestos favorables.
- Un riesgo puede ser Crítico aunque v1 sea investigación/educación: la severidad expresa la exposición técnica y el gate de despliegue, no una afirmación de uso asistencial actual.
- Los controles parciales no se presentan como mitigación suficiente si dependen del modelo, de regex/denylists o de estado local sin contexto.
- La lista priorizada obliga a tratar identidad/contexto, SQL/tools, código generado, privacidad y RAG seguro como gates antes de compartir el sistema o conectarlo a datos hospitalarios.
- Cambios futuros de arquitectura o despliegue deberán actualizar el modelo y aportar evidencia para reducir el riesgo residual; no deben sobrescribir la fotografía histórica de Fase 0.

## Pendientes

1. Verificar y versionar tipo de claves, RLS/policies y contratos/autorización de RPC en el entorno Supabase utilizado.
2. Documentar topología de despliegue, TLS, red, reverse proxy, acceso administrativo y controles de secretos.
3. Convertir en Fase 1 los confines objetivo (`RequestContext`, Model Gateway, Clinical Data Gateway y repositorios) en threat boundaries verificables.
4. Convertir en Fase 2 las amenazas de IA en casos adversariales con efectos observables y gates bloqueantes, no verificadores basados solo en keywords.
5. Asignar propietarios de mitigación y fechas cuando se planifique Fase 1 y 2.
6. Recalcular el riesgo residual solo después de implementar y probar los controles; mantener cero tolerancia para acceso no autorizado, fugas entre pacientes/tenants y violaciones de políticas de tools.
7. Ampliar el análisis de privacidad a DPIA/LINDDUN y el análisis clínico a hazard log/risk file en las fases de privacidad, regulación y pilot readiness.
