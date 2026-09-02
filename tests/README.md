# Tests de ChatHCE

## Estructura por capas

```
tests/
├── conftest.py            # sys.path, filtros de warnings, reset de get_settings()
├── fakes/                 # FakeSupabaseClient (PostgREST en memoria), factorias legacy, normalize
├── fixtures/
│   ├── mimic/             # tablas grabadas de MIMIC-IV demo + salidas esperadas (manifest.json)
│   ├── prompts/           # snapshot del system prompt
│   └── tool_observations/ # observaciones de tools para caracterizar el formato de respuesta
├── unit/                  # sin red ni credenciales (autouse: HCE_DISABLE_DOTENV=1, socket bloqueado)
├── contract/              # cada adapter cumple su port usando fakes o fixtures grabadas
├── integration/           # requieren HCE_RUN_INTEGRATION=1 y credenciales; se saltan sin ellas
├── security/              # controles: no exec, superficie de schemas, scope, inyeccion
├── characterization/      # temporal (Fase 1): congela el comportamiento legacy antes de moverlo
└── evaluation/            # tests de los helpers de Evaluation/ (Hypothesis)
```

Marcadores (`pytest.ini`, `--strict-markers`): `unit`, `contract`, `integration`, `security`, `slow`.

## Ejecutar (PowerShell)

```powershell
# Sin credenciales (lo que corre en cada paquete de trabajo)
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest

# Solo seguridad
conda activate HCE ; python -m pytest tests/security -q

# Integracion (lee .env; solo lectura sobre Supabase demo; pocas llamadas a Anthropic)
conda activate HCE ; $env:HCE_RUN_INTEGRATION="1" ; python -m pytest -m integration

# Cobertura
conda activate HCE ; python -m pytest -m "not integration" --cov=config --cov=services --cov=chathce --cov-report=term-missing
```

`asyncio_mode = auto`: los tests `async def` no necesitan decorador.

## Fixtures MIMIC

Grabadas una vez con `scripts/record_mimic_fixtures.py` (lectura sobre Supabase). Regrabar
solo si cambia el dataset; `tests/fixtures/mimic/manifest.json` registra commit, fecha,
pacientes y conteos.

## Snapshots

`tests/fixtures/prompts/system_prompt_v0.txt` se regenera con `UPDATE_SNAPSHOTS=1`.
