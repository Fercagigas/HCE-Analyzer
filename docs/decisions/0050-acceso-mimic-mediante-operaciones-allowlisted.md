# ADR 0050 — Acceso MIMIC mediante operaciones allowlisted

Estado: aceptada

Fecha: 2026-09-01

## Contexto

ChatHCE v1 se limita a investigación y educación con MIMIC-IV-ED y no está autorizada para producción clínica ni para influir en decisiones asistenciales reales. El roadmap prohíbe que el LLM disponga de SQL libre contra datos clínicos de producción, aunque permitía decidir si conservar esa capacidad en el entorno de investigación MIMIC.

El runtime anterior exponía al modelo `query_type="custom"`, el parámetro `custom_query`, el esquema físico y ejemplos SQL dataset-wide. `DatabaseService.execute_custom_query()` enviaba el texto completo a la RPC `execute_readonly_query`. El límite de filas se aplicaba al resultado Python solo cuando el modelo proporcionaba `limit`, después de ejecutar la RPC; no había scope obligatorio de paciente o encuentro ni un timeout efectivo de transporte para esa ruta.

La capacidad se usaba realmente. El golden set contiene 7 preguntas dataset-wide de 40 y también depende de SQL para agregaciones, triaje y joins que las cuatro operaciones antiguas no representaban. Por ello, retirar SQL sin sustitución habría eliminado tareas habituales de investigación.

La decisión debía equilibrar la mitigación de AI-04 y AI-08 con el intended purpose aprobado. El usuario confirmó explícitamente la opción A: eliminar el SQL libre por completo, también en investigación MIMIC.

## Opciones consideradas

1. Eliminar SQL libre completamente y sustituir sus usos conocidos por operaciones tipadas. Es la opción elegida. Reduce la superficie a funciones concretas, permite imponer scope y conserva estadísticas frecuentes mediante agregaciones fijas.
2. Mantener `custom` detrás de un flag explícito de investigación, con solo lectura, allowlist, límite y timeout. Se descartó porque al activar el flag el modelo seguiría construyendo un lenguaje de consulta general y podría formular lecturas dataset-wide no previstas. Los validadores sintácticos no equivalen a una política clínica ni garantizan el mínimo necesario.
3. Usar operaciones acotadas por defecto y conservar SQL como fallback de investigación bajo flag. Se descartó porque mantiene una ruta privilegiada alternativa, aumenta la superficie que debe auditarse y contradice la decisión de eliminar completamente la capacidad arbitraria.
4. Conservar el diseño anterior reforzando únicamente el prompt. Se descartó porque el modelo no es un punto de enforcement confiable y un prompt malicioso puede alterar argumentos de herramientas.
5. Conservar SQL y reforzar únicamente regex de validación. Se descartó porque las regex no representan de forma completa la gramática, el plan de ejecución, el scope clínico ni el coste de una consulta.

## Decision

Se elimina del contrato del modelo `custom`, `custom_query`, `params`, `table_name` y los filtros genéricos. También se elimina `DatabaseService.execute_custom_query()` y, por tanto, la llamada a la RPC `execute_readonly_query`. No existe flag para reactivar SQL libre.

`query_mimic_database` expone únicamente estas operaciones allowlisted:

- `patient_summary`, con `subject_id` obligatorio;
- `encounter_summary` y `vital_signs`, con `stay_id` obligatorio;
- `diagnoses`, `medications` y `triage`, con `subject_id` o `stay_id` obligatorio;
- `dataset_summary`, `diagnosis_frequency`, `medication_frequency` y `acuity_distribution`, como agregaciones fijas de investigación que devuelven conteos o grupos acotados y no enumeran pacientes de una cohorte.

El input usa un schema Pydantic cerrado y rechaza campos adicionales. El output declara `success`, operación, permiso `read_only`, scope aplicado, datos, conteo, límite, timeout, truncamiento y error. El máximo visible al modelo es de 200 filas o grupos, 100 por defecto. Las peticiones PostgREST reciben un timeout de transporte de 30 segundos, incluidas las conexiones procedentes del pool. Las agregaciones leen como máximo 1.000 filas fuente y señalan `source_truncated` cuando alcanzan ese límite.

La política se aplica en código antes de acceder al servicio. Las instrucciones del prompt describen el contrato, pero no conceden permisos ni sustituyen la validación determinista.

## Motivo

La opción elimina el lenguaje de consulta arbitrario del límite de confianza controlado por el modelo. Las operaciones clínicas expresan intención y scope, por lo que un argumento adversarial no puede transformarse en otra tabla, un join imprevisto, una escritura o una enumeración dataset-wide.

Las cuatro agregaciones fijas conservan los usos recurrentes de investigación —resumen del dataset y distribuciones de diagnósticos, medicamentos y acuidad— con minimización de salida. La pérdida de exploración ad hoc es deliberada y fue aceptada por el usuario como consecuencia de elegir la opción A.

## Consecuencias

- El modelo ya no puede ejecutar SQL, ni siquiera `SELECT`, ni conocer el esquema físico a través del contrato del tool.
- Las consultas clínicas sin paciente o encuentro quedan bloqueadas antes de acceder a la base.
- Las consultas dataset-wide solo pueden usar cuatro agregaciones predeterminadas y no pueden devolver listas de pacientes o estancias.
- Se conservan resumen de paciente, resumen de encuentro, signos vitales, diagnósticos, medicación, triaje y estadísticas MIMIC frecuentes.
- Se pierden joins, cohortes, filtros y cálculos ad hoc que no tengan una operación tipada. Recuperarlos requerirá añadir una operación concreta con contrato y pruebas.
- Parte del golden set que esperaba enumeración de cohortes o SQL arbitrario deberá reclasificarse o migrarse a operaciones aprobadas. Los resultados de agregaciones indican cuando el scan acotado puede ser parcial.
- La mitigación es apropiada para la v1 de investigación, pero no convierte el prototipo en un sistema apto para producción hospitalaria: siguen pendientes identidad, autorización, multitenancy, audit y el Clinical Data Gateway.

## Pendientes

- Migrar en Fase 1 estas operaciones al `ClinicalDataGateway` y al adapter MIMIC, manteniendo el mismo contrato sin acoplar el agente a tablas.
- Incorporar `RequestContext` con tenant, usuario, propósito y contexto de paciente/encuentro autorizado; los identificadores actuales expresan scope de consulta, no acreditan autorización.
- Implementar audit metadata y trazabilidad uniforme por invocación.
- Revisar el golden set y los casos de visualización que dependían de cohortes o joins arbitrarios.
- Añadir nuevas estadísticas únicamente como operaciones allowlisted con owner, campos, scope, límite, timeout y criterios de aceptación propios.
- Verificar en el proveedor los límites y permisos efectivos de la clave y retirar o restringir la RPC `execute_readonly_query` en Supabase, ya que su definición e invocabilidad externa no están versionadas en este repositorio.
