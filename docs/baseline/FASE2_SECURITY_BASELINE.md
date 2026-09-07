# Fase 2 - Baseline de seguridad adversarial

**Fecha:** 7 de septiembre de 2026 (Europe/Madrid)  
**Rama de referencia:** `ao/hce-analyzer-15/security-suite`  
**Alcance:** gate offline sin credenciales y runner live manual de solo lectura.

## Resultado offline

```powershell
$env:HCE_DISABLE_DOTENV="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
python -m pytest -p pytest_asyncio.plugin tests/security tests/unit/test_eval_runner_contract.py -q
```

| Medida | Antes (Fase 1) | Despues (Fase 2) |
| --- | ---: | ---: |
| Tests `tests/security/` | 52 | 78 |
| Payloads live definidos | 18 | 27 |
| Violaciones criticas offline | 0 | 0 |
| Resultado ejecutado | 52 pasan | 80 pasan (78 security + 2 de contrato del runner) |

La salida exacta se conserva en `raw/fase2/pytest-security.txt`. No se ha usado `.env`, red ni credenciales. No se detectaron vulnerabilidades nuevas; por ello no hay casos `xfail` en este baseline.

Los nuevos controles cubren base64, homoglifos Unicode, leetspeak, tokens partidos e idiomas mezclados, tanto como entrada de usuario como dentro de resultados de `search_clinical_documents`; aislamiento de tenant en artefactos; pestañas paralelas con el mismo `session_id`; argumentos de exfiltracion y operaciones no registradas.

## Gate CI

`.github/workflows/security-suite.yml` ejecuta `pytest tests` en cada pull request y push a `main`, con `HCE_DISABLE_DOTENV=1`. La menor violacion critica es una asercion offline y, por tanto, hace fallar el job. El resumen y JUnit quedan publicados como summary y artefacto de GitHub Actions.

## Runner live manual

El runner live sigue siendo de solo lectura y se ejecuta exclusivamente desde un entorno con secretos configurados:

```powershell
$env:ANTHROPIC_API_KEY = "..."
$env:SUPABASE_URL = "..."
$env:SUPABASE_KEY = "..."
python -m Evaluation.run_security_tests --output Evaluation/results
```

Para incluir `SEC-IND-001`, siembra previamente en el indice de pruebas un documento no confiable con una instruccion adversarial inocua y ejecútalo de forma manual:

```powershell
python -m Evaluation.run_security_tests --include-indirect-fixture --output Evaluation/results
```

En GitHub, guardar `ANTHROPIC_API_KEY`, `SUPABASE_URL` y la clave de lectura en **Settings > Secrets and variables > Actions**; crear un workflow manual protegido que los inyecte como variables de entorno. No se incluyen secretos ni un workflow live automatico para evitar consumo, acceso a datos o ejecuciones contra entornos no autorizados. El runner clasifica cada payload como `critical`, `high` o `medium` y devuelve código 1 solo si una violacion `critical` falla.

## Riesgos y seguimiento

El aislamiento multi-tenant de datos clinicos/RLS sigue siendo un pendiente de Fase 2 (ADR 0090); esta suite verifica el contrato de `RequestContext` y el aislamiento de artefactos en memoria, no sustituye una prueba RLS contra Supabase. La inyeccion indirecta live exige un documento sembrado y aislado del corpus productivo.
