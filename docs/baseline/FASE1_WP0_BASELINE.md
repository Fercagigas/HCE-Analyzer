# Fase 1 — WP0: baseline tras el saneamiento de configuracion

**Fecha:** 2 de septiembre de 2026 (Europe/Madrid)
**Commit de partida:** `df033d2` (`main`), rama `fase1/foundation`
**Entorno:** conda `HCE`, Python 3.11.14, pytest 9.0.2, pytest-cov 7.1.0

Este documento complementa, sin reescribir, `FASE0_BASELINE.md` (ADR 0020). Congela el
estado de la suite justo despues de WP0 y antes de mover codigo en Fase 1.

## Que cambio en WP0

- `config/settings.py`: la instancia global `settings = Settings()` se sustituye por
  `get_settings()` perezoso y cacheado. Ningun campo es obligatorio en tiempo de
  importacion; las credenciales se exigen con `Settings.require_database()` /
  `Settings.require_anthropic()` en el composition root. `HCE_DISABLE_DOTENV=1`
  impide leer `.env`. El nombre `settings` se conserva como shim (PEP 562) hasta WP12.
- `services/auth/session_manager.py`: corregido `return {...}    @staticmethod` en una
  sola linea (dejaba `_load_user_preferences` sin decorador y provocaba `TypeError`).
- Dependencias: declaradas `sse-starlette`, `pytest-cov` y (temporalmente)
  `langchain-classic`; retirados `pathlib` (backport innecesario) y el duplicado de
  `python-multipart`.
- `pytest.ini`: `--strict-markers` y marcadores `unit`, `contract`, `integration`,
  `security`, `slow`. `tests/conftest.py`: fixture autouse `reset_settings_cache`;
  eliminadas `mock_env_vars`/`clean_environment` (inutiles con settings en import).

## Resultado de la suite

Comando (con `.env` presente):

```powershell
conda activate HCE ; python -m pytest --cov=config --cov=services --cov=src --cov=ui --cov=utils --cov-report=term-missing --cov-report=xml:docs/baseline/raw/fase1-wp0/coverage.xml --junitxml=docs/baseline/raw/fase1-wp0/pytest-junit.xml
```

Comando sin credenciales (mismo resultado):

```powershell
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest
```

| Modulo | Tests | Resultado |
| --- | ---: | --- |
| `tests/evaluation/` | 24 | 24 pasan |
| `tests/test_database.py` | 3 | 3 pasan |
| `tests/test_rag_components.py` | 20 | 20 pasan (antes: 4 fallos + 4 errores) |
| `tests/test_system.py` | 9 | 9 pasan (antes: 9 fallos) |
| `tests/test_visualization_security.py` | 19 | 19 pasan |
| **Total** | **63** | **63 pasan, 0 fallos, 0 errores** |

Los 17 resultados rojos del baseline de Fase 0 tenian una unica causa
(`DatabaseSettings` exigia `SUPABASE_URL`/`SUPABASE_KEY` al importar). Desaparecen
sin tocar ningun test. `tests/test_visualization_security.py` (19 tests) no existia en
el baseline de Fase 0.

## Cobertura (primera medida)

`pytest-cov` no estaba instalado en Fase 0. Primera cifra, solo informativa:
**18 % de lineas** sobre `config`, `services`, `src`, `ui`, `utils` (8 354 lineas,
6 828 sin cubrir). No se fija umbral bloqueante todavia (ADR 0120 lo decidira).

Evidencia: `raw/fase1-wp0/pytest-output.txt`, `raw/fase1-wp0/pytest-junit.xml`,
`raw/fase1-wp0/coverage.xml`.

## Evaluacion

`python -m Evaluation.run_all_evaluations --dry-run` termina con exit 0 y
pre-flight en verde. No se ejecutaron evaluaciones online en WP0.

## Advertencias observadas

- `import services.auth.session_manager` fuera de Streamlit emite avisos
  `missing ScriptRunContext`; son inocuos y desaparecen en WP10.
- `connection_pool_manager` sigue instanciando los pools al importar (sin abrir red).
  Se elimina en WP12.
