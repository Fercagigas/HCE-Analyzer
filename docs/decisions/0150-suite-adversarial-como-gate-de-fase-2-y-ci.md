# ADR 0150 - Suite adversarial como gate de Fase 2 y CI

Estado: Aceptada

Fecha: 2026-09-07

## Contexto

Fase 1 cerró con 52 controles offline y 18 payloads live, pero no cubría variantes codificadas, aislamiento de tenant, concurrencia por sesión, exfiltración mediante argumentos ni escalada a operaciones no allowlisted. Además, las evaluaciones no bloqueaban cambios en CI. Para Fase 2, una fuga de paciente o tenant, una tool no autorizada o una exfiltración es una violación crítica y no puede promocionarse.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mantener solo el runner live manual.** Descartada: depende de secretos, es costosa y no ofrece feedback determinista por PR.
2. **Ejecutar el runner live con secretos en cada PR.** Descartada: expone capacidad de acceso a forks/entornos no autorizados, consume el proveedor y hace el gate dependiente de red y de datos cambiantes.
3. **Marcar las pruebas adversariales como informativas.** Descartada: no cumpliría la tolerancia cero para violaciones críticas.
4. **Suite offline determinista en cada PR/push, runner live manual con severidad y documento indirecto sembrado** (elegida).

## Decision

- `tests/security/` ejecuta sin `.env` vectores adversariales de usuario y de datos de tools: codificación base64, homoglifos, leetspeak, tokens partidos, idiomas mezclados, cross-tenant, pestañas paralelas, exfiltración por argumentos y operaciones fuera de allowlist.
- Cada aserción de acceso no autorizado explica la violación concreta; si el runtime descubre una vulnerabilidad real, se deja como `xfail` con motivo y se registra en el baseline, sin corregir el runtime en este paquete.
- `.github/workflows/security-suite.yml` ejecuta `pytest tests` con `HCE_DISABLE_DOTENV=1` en PR y push a `main`, publica un resumen y artefactos, y falla ante la menor violación crítica.
- `Evaluation/run_security_tests.py` conserva la ejecución live manual, registra severidad `critical`/`high`/`medium` y devuelve error para cualquier fallo crítico. `SEC-IND-001` solo se habilita con `--include-indirect-fixture` tras sembrar un documento de prueba aislado.

## Consecuencias

- Positivas: el gate es reproducible, no requiere secretos y cubre evasiones que los prompts simples no detectan; las ejecuciones live tienen criterios y severidad comunes.
- Negativas: el gate offline prueba contratos y fakes, no RLS real ni el comportamiento probabilístico del modelo; la comprobación indirecta live exige preparación manual y un entorno autorizado.
- Seguimiento: añadir pruebas RLS/multi-tenant contra infraestructura efímera cuando exista el diseño de tenant de Fase 2, y revisar periódicamente payloads y severidades con red team multidisciplinar.
