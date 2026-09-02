# ADR 0120 — Estrategia de tests por capas y baseline de Fase 1

Estado: Aceptada

Fecha: 2026-09-02

Cierra los pendientes de ADR 0020 (suite no reproducible sin credenciales, sin cobertura).

## Contexto

En Fase 0 la suite descubría 44 tests con 13 fallos y 4 errores por una única causa (settings
exigía credenciales al importar) y no había cifra de cobertura. La migración de Fase 1 movía
código legacy a un core nuevo, lo que exigía una red de seguridad previa y una forma de probar
adapters sin depender de Supabase ni Anthropic.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mocks ad hoc de `supabase` y `anthropic` por test.** Descartada: frágiles frente a la API
   fluida de PostgREST y sin valor de contrato.
2. **Base de datos Postgres local con los datos demo para tests.** Descartada en Fase 1: añade
   Docker/PostgREST al entorno de desarrollo Windows y no cubre el cliente real de Supabase;
   se reconsidera para RLS (Fase 2).
3. **Fixtures grabadas de MIMIC-IV más un cliente PostgREST en memoria, tests por capas y
   tests de integración opcionales** (elegida).

## Decision

- Capas (`tests/README.md`): `unit` (sin red salvo loopback, sin `.env`), `contract`
  (adapters contra fakes o fixtures grabadas), `integration` (solo con `HCE_RUN_INTEGRATION=1`
  y credenciales; se saltan en otro caso), `security` (controles), `evaluation` (helpers de
  `Evaluation/`). Los tests de caracterización del legacy se retiraron en WP12; sus salidas
  esperadas (`tests/fixtures/mimic/expected/`) permanecen como baseline de contrato del provider.
- Fixtures: `scripts/record_mimic_fixtures.py` graba 3 pacientes y 17 tablas de la demo
  (`tests/fixtures/mimic/tables`, `manifest.json`); `InMemoryPostgrestClient` reproduce la API
  fluida y las cuatro RPC de agregados.
- Fakes del core: `FakeLLMProvider` con turnos guionizados, repositorios en memoria,
  `CollectingAuditSink` con escáner de PHI en los eventos.
- Reglas: `pytest.ini` con `--strict-markers`; `HCE_DISABLE_DOTENV=1` en unit; ningún test
  escribe en Supabase; los tests live son de solo lectura y con `max_tokens` mínimo.
- Cobertura medida en cada baseline con `pytest-cov`; sin umbral bloqueante en Fase 1 (se
  fijará cuando el legacy de `ui/` y `services/rag` se haya migrado).

## Motivo

Las fixtures grabadas dan tests deterministas que reproducen el dataset real; el cliente en
memoria permite probar el adapter de verdad (filtros, límites, RPC) y no un mock; las capas
hacen explícito qué requiere red y credenciales.

## Consecuencias

- Positivas: suite verde sin credenciales en cada paquete de trabajo; adapters verificados
  frente a la salida congelada del legacy; tests de seguridad ejecutables en CI.
- Negativas: las fixtures deben regrabarse si cambia el dataset; el cliente en memoria puede
  divergir de PostgREST en casos no cubiertos (los tests live lo detectan).
- Baseline de cierre en `docs/baseline/FASE1_BASELINE.md` y `docs/baseline/raw/fase1/`.

## Pendientes

- Tests de integración de identidad y API live con un usuario de pruebas
  (`HCE_TEST_USER_EMAIL`/`HCE_TEST_USER_PASSWORD` fuera del repositorio).
- Umbral de cobertura y ejecución en CI.
- Tests de RLS contra un Postgres local (Fase 2).
