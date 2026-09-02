# Tests de ChatHCE

## Estructura por capas (ADR 0120)

```
tests/
├── conftest.py            # sys.path, filtros de warnings, reset de get_settings()
├── fakes/                 # container_factory (contenedor con fakes), fake_supabase (alias del cliente PostgREST en memoria),
│                          # mimic_fixtures (carga de tablas grabadas), normalize
├── fixtures/
│   ├── mimic/             # tables/ (3 pacientes, 17 tablas), expected/ (salida congelada del legacy = contrato), manifest.json
│   ├── prompts/           # snapshot del system prompt
│   └── tool_observations/ # observaciones de tools grabadas
├── unit/                  # sin red (solo loopback) ni .env: domain, gateway, application, adapters en memoria, api (ASGITransport), ui, fronteras
├── contract/              # cada adapter cumple su port con fakes o fixtures: provider MIMIC, repositorios, identidad, conocimiento, mapping Anthropic, vector store
├── integration/           # HCE_RUN_INTEGRATION=1 y credenciales; solo lectura; se saltan sin ellas
├── security/              # sin exec/eval, superficie de schemas y prompt, aislamiento entre pacientes, inyección, validación de resultados, sin caché por usuario
├── characterization/      # vacío tras WP12 (conftest); expected/ conserva el baseline
└── evaluation/            # helpers de Evaluation/ (Hypothesis) y validación del golden set real
```

Marcadores (`pytest.ini`, `--strict-markers`): `unit`, `contract`, `integration`, `security`, `slow`. `asyncio_mode = auto`.

## Ejecutar (PowerShell)

```powershell
# Sin credenciales (lo que debe estar verde en cada commit)
conda activate HCE ; $env:HCE_DISABLE_DOTENV="1" ; python -m pytest

# Solo seguridad / solo fronteras
conda activate HCE ; python -m pytest tests/security -q
conda activate HCE ; python -m pytest tests/unit/test_architecture_boundaries.py -q

# Integracion (lee .env; solo lectura sobre Supabase demo; pocas llamadas a Anthropic con max_tokens minimo)
conda activate HCE ; $env:HCE_RUN_INTEGRATION="1" ; python -m pytest -m integration

# Cobertura
conda activate HCE ; python -m pytest --cov=chathce --cov=config --cov=services --cov=ui --cov=src --cov-report=term-missing
```

Tests live que requieren un usuario de pruebas (`HCE_TEST_USER_EMAIL` / `HCE_TEST_USER_PASSWORD`, fuera del repo) se saltan si no están definidos. Los tests de agregados live se saltan hasta que `db/migrations/0001` esté aplicada.

## Fakes del core

- `tests/fakes/container_factory.build_test_container(...)`: `build_container` con `FakeLLMProvider`, provider en memoria sobre las fixtures (envuelto por `ScopeGuard`), repositorios en memoria y `CollectingAuditSink` (con escáner de PHI).
- `FakeLLMProvider(ScriptedTurn...)`: guioniza texto y `tool_use` por iteración para probar el gateway sin red.
- `InMemoryPostgrestClient` + `register_clinical_aggregate_rpcs`: API fluida de PostgREST y las 4 RPC de agregados sobre las tablas grabadas.

## Fixtures MIMIC

Grabadas una vez con `scripts/record_mimic_fixtures.py --n-subjects 3` (lectura sobre Supabase). Regrabar solo si cambia el dataset; `manifest.json` registra commit, fecha, pacientes y conteos. `expected/` no se regenera: es la salida del `DatabaseService` legacy congelada antes de retirarlo y sirve de contrato para `MimicClinicalDataProvider`.

## Snapshots

`tests/fixtures/prompts/` se regenera con `UPDATE_SNAPSHOTS=1`; revisa el diff antes de commitear.

## Convenciones

- Un test nuevo va en la capa que corresponde a lo que prueba; si necesita red o `.env`, es `integration`.
- Nunca escribir en Supabase desde tests. Nunca incluir credenciales, emails reales ni PHI en fixtures.
- Si un test toca la superficie visible al modelo (descripciones, schemas, prompt), ejecuta también `tests/security/test_tool_schema_surface.py`.
