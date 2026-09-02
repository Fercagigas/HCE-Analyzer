# ADR 0050 — Acceso a datos clínicos MIMIC mediante operaciones allowlisted y agregados server-side

Estado: Aceptada

Fecha: 2026-09-02

Sustituye al borrador del mismo número elaborado sobre el modelo MIMIC-IV-ED (worktree
`hce-analyzer-9`, nunca fusionado). Se reconstruye aquí sobre MIMIC-IV Clinical Demo 2.2.

## Contexto

Hasta Fase 0 el modelo podía emitir SQL libre a través del tipo de consulta `custom_query`
del tool de base de datos, que terminaba en la RPC `public.execute_readonly_query(text)`
(`SECURITY DEFINER`, `search_path` sobre los esquemas clínicos). El threat model (ADR 0030)
lo clasificaba como riesgo Crítico: inyección indirecta a través de documentos o resultados,
acceso a cualquier paciente sin relación con el contexto de la petición y una superficie de
prompt que exponía DDL, nombres de tabla y reglas SQL al modelo. Además, el enriquecimiento de
diagnósticos hacía una consulta por código (N+1) y las descripciones de tools incluían el
esquema completo.

El roadmap (doc 04 Clinical Data Gateway y 07 Agent Orchestration P0.1) exige un port clínico
read-only con operaciones tipadas, DTOs canónicos y scope obligatorio, y que ningún texto
visible al modelo contenga SQL ni nombres de tabla.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mantener SQL libre solo para investigación** (validado con lista negra de palabras y
   límite de filas). Descartada: la validación léxica no impide leer cualquier paciente ni
   detecta tautologías nuevas; el propósito `research` no elimina que el LLM sea quien redacta
   la consulta; obligaba a exponer el esquema al modelo.
2. **Generar SQL en el core (no en el LLM) a partir de parámetros estructurados.** Descartada
   para Fase 1: sigue requiriendo una RPC de ejecución de texto, cuya sola existencia es el
   riesgo; el conjunto de consultas realmente usado por el producto es pequeño y estable.
3. **Operaciones allowlisted vía PostgREST más agregados por RPC fijas versionadas**
   (elegida). Las consultas por paciente se expresan con filtros PostgREST y `select`
   explícito; los cuatro agregados de dataset que usaba el producto se convierten en funciones
   SQL fijas `clinical_*_v1` con `SECURITY INVOKER`, `search_path` fijo, `statement_timeout`
   y límite acotado.
4. **Vistas materializadas para agregados.** Descartada por ahora: añade un job de refresco y
   permisos adicionales sin ventaja sobre cuatro funciones `STABLE` en un dataset de demo.

## Decision

- Se crea el port `ClinicalDataProvider` (`chathce/ports/clinical_data_provider.py`) con
  operaciones asíncronas allowlisted que reciben `RequestContext` como primer argumento:
  paciente, resumen, admisiones y detalle, diagnósticos, laboratorio (con búsqueda en el
  diccionario), medicación (prescripciones y administraciones), estancias y observaciones de
  UCI, búsqueda de códigos ICD y cuatro agregados de dataset. No existe operación genérica por
  tabla ni parámetro que acepte SQL.
- `MimicClinicalDataProvider` (`chathce/adapters/supabase/`) implementa el port sobre
  PostgREST con `select` explícito, `.eq("subject_id", ctx.patient_id)` siempre presente como
  defensa en profundidad, `limit+1` para señalar truncamiento y diccionarios
  (`d_labitems`, `d_items`, `d_icd_*`) cacheados en memoria, lo que elimina el N+1.
- Los agregados se sirven exclusivamente con las RPC de `db/migrations/0001_clinical_aggregates_v1.sql`.
  `db/migrations/0002_revoke_execute_readonly_query.sql` elimina la RPC de SQL libre. Ambos
  scripts se aplican manualmente en el SQL Editor; el provider degrada a `ToolResult.success=False`
  si una RPC no existe.
- `ScopeGuard` (`chathce/application/scope_guard.py`) envuelve cualquier implementación del
  port, también las de test, y rechaza operaciones sin paciente, con paciente distinto al del
  contexto, con `hadm_id`/`stay_id` que no pertenecen al paciente o agregados sin `purpose=research`.
- El contrato de cada tool prohíbe términos SQL y nombres de tabla en nombre, descripción y
  schema (`LLM_VISIBLE_FORBIDDEN_PATTERN` en `chathce/domain/tools.py`).

## Motivo

La única forma de garantizar que el modelo no lea datos fuera del paciente autorizado es que
no exista ninguna ruta por la que pueda formular la consulta. Las operaciones allowlisted
mantienen la funcionalidad clínica del producto, los agregados fijos mantienen el caso de uso
de investigación, y la RPC eliminada cierra el riesgo en la base de datos y no solo en el código.

## Consecuencias

- Positivas: aislamiento entre pacientes verificable con tests (`tests/security/test_cross_patient_isolation.py`,
  `tests/contract/test_mimic_clinical_data_provider.py`); prompt sin esquema; menos consultas
  por turno; los mismos DTOs sirven a FastAPI, Streamlit y evaluación.
- Negativas: preguntas ad hoc sobre el dataset que antes se resolvían con SQL ahora requieren
  añadir una operación o una RPC versionada; los agregados no funcionan hasta que el
  propietario aplique la migración 0001.
- El golden set de evaluación se regenera con `ground_truth_operation` en lugar de SQL
  (`Evaluation/golden_set_ragas.json`, `scripts/build_golden_set_mimiciv.py`).

## Pendientes

- Aplicar `0001` y `0002` en Supabase y anotarlo en `docs/security/SUPABASE_VERIFICATION_CHECKLIST.md`.
- Crear la clave de solo lectura `SUPABASE_CLINICAL_KEY` para el provider (ADR 0100).
- RLS por usuario/paciente en Supabase (Fase 2); hoy el aislamiento se aplica en la aplicación.
- Ampliar operaciones (microbiología, OMR, procedimientos) cuando un caso de uso lo exija.
