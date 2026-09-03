# 07 — Agent Safety, Tooling y ejecución segura

## Estado a 2 de septiembre de 2026 (cierre de Fase 1)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Tarea | Estado | Evidencia / nota |
|---|---|---|
| P0.1 Tool contracts explícitos | ✅ | `ToolContract` (input/output schema, permisos, scope, propósito, timeout, max_rows, audit_category) — ADR 0090 |
| P0.2 Least privilege tools | ✅ | 12 tools allowlisted; ninguna acepta SQL, tabla ni filtros libres (ADR 0050) |
| P0.3 Policy enforcement fuera del prompt | ✅ | `ScopeGuard` y `ToolPolicy` en código; el prompt solo informa |
| P0.4 Prompt injection defenses | 🟡 | Payloads directos, extracción de prompt y cambio de rol en verde (live 18/18). Encoded/obfuscated pendientes |
| P0.5 Indirect prompt injection | ✅ | Resultados como `<tool_data trust="untrusted_data">`; directiva en el prompt; test offline con documentos maliciosos sembrados |
| P0.6 Tool result validation | ✅ | Validación de `output_model`, recorte de filas, scope y tipos en `ToolRegistry.dispatch` |
| P0.7 No arbitrary code execution | ✅ | ADR 0040; test AST sin `exec`/`eval`/`compile` |
| P0.8 Sandbox | — | No hay código generado que ejecutar |
| P0.9 Model Gateway | ✅ | `LLMProvider` + `ModelGateway` (ADR 0080) |
| P0.10 Human approval | — | Sistema read-only; sin acciones que aprobar |
| P1.1 Kill switch | ⏳ | Fase 2 (perfil `LLM_PROVIDER=fake` existe solo para tests) |
| P1.2 Safe degraded modes | 🟡 | Fallback entre modelos y errores controlados; retrieval sin LLM pendiente |

## Tareas

### P0.1 — Tool contracts explícitos
Cada tool define input schema, output schema, permissions, patient scope, timeout, max rows/data y audit metadata.

### P0.2 — Least privilege tools
Preferir `get_latest_labs(patient)` frente a `execute_sql(query)`.

### P0.3 — Policy enforcement fuera del prompt
No confiar en "no hagas X" dentro del system prompt. Los límites críticos deben ser código determinista.

### P0.4 — Prompt injection defenses
Cubrir direct injection, system prompt extraction, tool manipulation, role override y encoded/obfuscated attacks.

### P0.5 — Indirect prompt injection
Notas clínicas y documentos recuperados son **untrusted data**, nunca instrucciones. Delimitar contenido y evitar que modifique políticas/tools.

### P0.6 — Tool result validation
Validar tipos, tamaño, tenant/patient scope, timestamps, unidades y campos permitidos antes de volver al modelo.

### P0.7 — No arbitrary code execution
Eliminar `exec`/shell/code arbitrario generado por modelo. Para visualizaciones usar funciones parametrizadas (`plot_timeseries`, `plot_histogram`, etc.).

### P0.8 — Sandbox si el código es imprescindible
Sin red, filesystem restringido, proceso aislado, allowlist de imports, CPU/RAM/time limits y datos read-only.

### P0.9 — Model Gateway
Abstraer Anthropic/otros proveedores mediante interfaz. Policies por modelo y capacidad de fallback.

### P0.10 — Human approval
Cualquier futura acción que modifique sistemas clínicos requiere revisión explícita y registro del profesional.

### P1.1 — Kill switch
Desactivar generación/inferencia manteniendo retrieval determinista y búsqueda documental cuando sea seguro.

### P1.2 — Safe degraded modes
Definir comportamiento ante LLM outage, RAG outage, FHIR outage y partial data.

## Definition of Done
Un prompt malicioso no puede ampliar permisos, consultar otro paciente, ejecutar SQL/código arbitrario ni convertir contenido recuperado en instrucciones privilegiadas.
