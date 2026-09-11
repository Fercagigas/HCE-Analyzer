# Fase 2 — Baseline de cierre de la oleada 1 (Security foundation)

**Fecha:** 11 de septiembre de 2026 (Europe/Madrid)

**Referencia:** `origin/main` en `2ab1994` (PRs #23, #24, #25 y #27)

**Entorno:** conda `HCE`, Python 3.11.14, pytest 9.0.2, pytest-cov 7.1.0
**Alcance:** controles de la oleada 1: RLS por usuario y clave clínica de solo lectura (ADR 0130), kill switch y circuit breaker (ADR 0140), suite adversarial y gate CI (ADR 0150), y minimización/detección de PHI (ADR 0160).

Este documento congela el estado reproducible tras integrar la primera oleada de Fase 2. No declara completados los trabajos paralelos de RBAC/ABAC, gobierno del RAG ni SSO OIDC: están **en curso** y no forman parte de esta evidencia.

## 1. Suite completa sin credenciales

Se verificó que no existe `.env` en el worktree y se ejecutó la suite con la carga de dotenv deshabilitada:

```powershell
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest --cov=chathce --cov=config --cov=services --cov=ui --cov=src --cov-report=term --cov-report=xml:docs/baseline/raw/fase2/coverage.xml --junitxml=docs/baseline/raw/fase2/junit.xml
```

| Capa | Tests recogidos | Resultado |
| --- | ---: | --- |
| `tests/unit/` | 148 | 148 pasan |
| `tests/contract/` | 52 | 52 pasan |
| `tests/security/` | 78 | 78 pasan |
| `tests/evaluation/` | 32 | 32 pasan |
| `tests/integration/` | 7 | 7 se saltan (requieren `HCE_RUN_INTEGRATION=1`) |
| **Total** | **317** | **310 pasan, 7 se saltan, 0 fallos, 0 errores** (52,32 s) |

La suite se ejecutó sin `.env`, secretos ni llamadas live. La salida íntegra y sus artefactos están en `raw/fase2/`:

- `pytest-full.txt`
- `junit.xml`
- `coverage.xml`

### Comparación con el cierre de Fase 1

| Métrica | Fase 1 | Fase 2, oleada 1 | Variación |
| --- | ---: | ---: | ---: |
| Tests recogidos | 278 | 317 | +39 |
| Tests que pasan | 271 | 310 | +39 |
| Tests de seguridad | 52 | 78 | +26 |
| Tests saltados | 7 | 7 | 0 |
| Fallos / errores | 0 / 0 | 0 / 0 | 0 |
| Cobertura global | 56 % (8.016 líneas; 3.534 sin cubrir) | 57 % (8.310 líneas; 3.549 sin cubrir) | +1 pp |

La cobertura aumenta un punto porcentual mientras la superficie medida crece en 294 líneas. Es una señal de regresión controlada, no un umbral de calidad ni sustituto de pruebas live.

## 2. Gate de seguridad adversarial

El gate de Fase 2 es **cero violaciones críticas** en la suite adversarial. En esta ejecución:

- `tests/security/`: **78/78** pasan.
- Violaciones críticas offline: **0**.
- `.github/workflows/security-suite.yml` ejecuta `pytest tests/security` como comprobación bloqueante y publica JUnit/resumen; el resto de `pytest tests` queda como señal informativa.

Los controles cubren inyección directa e indirecta, base64, homoglifos Unicode, leetspeak, tokens fragmentados e idiomas mezclados; aislamiento de artefactos entre tenants, pestañas paralelas, exfiltración por argumentos y operaciones fuera de la allowlist. La prueba offline es determinista: no demuestra por sí sola RLS real ni el comportamiento probabilístico de un proveedor LLM.

## 3. Evaluación live de seguridad

No se ejecutó en este worktree: no hay `.env` ni se han inspeccionado ni creado secretos. El propietario, desde un entorno autorizado y de solo lectura, debe configurar `ANTHROPIC_API_KEY`, `SUPABASE_URL` y una clave de lectura de Supabase, y ejecutar:

```powershell
conda activate HCE
python -m Evaluation.run_security_tests --output Evaluation/results
```

Para incluir el caso de inyección indirecta `SEC-IND-001`, debe sembrar antes un documento de prueba inocuo y aislado del corpus productivo, y ejecutar:

```powershell
conda activate HCE
python -m Evaluation.run_security_tests --include-indirect-fixture --output Evaluation/results
```

El runner clasifica resultados como `critical`, `high` o `medium` y termina con código 1 ante cualquier fallo `critical`. Los resultados live, la evidencia de la siembra y las verificaciones de RLS deben archivarse por el propietario fuera de este baseline sin incluir secretos ni PHI.

## 4. Controles integrados y límites

| Control | Estado en repositorio | Evidencia / pendiente |
| --- | --- | --- |
| RLS de ownership, relación usuario-paciente y clave `clinical_readonly` | ✅ Implementado | Migración `0005`; el propietario debe aplicarla, emitir/rotar la clave y validar fail-closed live. |
| Kill switch y circuit breaker por `provider+model` | ✅ Implementado | ADR 0140 y tests unitarios/seguridad; el estado del breaker continúa siendo por proceso. |
| Minimización y detector PHI antes del modelo | ✅ Implementado | ADR 0160; modos `observe`/`redact`/`block`; DLP externo y política de egreso continúan pendientes. |
| Suite adversarial y CI | ✅ Implementado | ADR 0150; 78/78 offline y 0 violaciones críticas en este baseline. |
| RBAC/ABAC completo | 🔄 En curso | Fuera de la oleada 1. |
| Gobierno RAG y anti-poisoning operativo | 🔄 En curso | Fuera de la oleada 1. |
| SSO OIDC hospitalario | 🔄 En curso | Fuera de la oleada 1. |

## 5. Definition of Done de la oleada 1

| Criterio | Estado |
| --- | --- |
| Suite completa sin credenciales en verde y cobertura registrada | ✅ 310 pasan, 7 se saltan, 57 % |
| Gate adversarial con cero violaciones críticas | ✅ 78/78 offline; 0 críticas |
| RLS y credencial clínica de mínimo privilegio versionadas | ✅ código y migración; ⏳ aplicación/verificación live del propietario |
| Kill switch y degradación controlada antes de LLM/tools | ✅ ADR 0140 |
| Circuit breaker aislado por proveedor y modelo | ✅ ADR 0140 |
| PHI minimizada/detectada antes del modelo y fuera de auditoría | ✅ ADR 0160 |
| Evaluación live de seguridad | ⏳ requiere secretos y entorno autorizado del propietario |

La oleada 1 queda documentada y reproducible en local. Fase 2 no está cerrada: sus trabajos de RBAC/ABAC, gobierno RAG y SSO OIDC siguen en curso, y las acciones live/de infraestructura permanecen bajo responsabilidad del propietario.
