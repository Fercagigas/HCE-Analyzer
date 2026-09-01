# Fase 0 — Baseline de tests y evaluación

## Resumen ejecutivo

Este documento congela el estado observado antes de cualquier refactor sobre el
commit `38b94ba856998eef5cfffa21bc8b03cde510f1c3` (`origin/main` al iniciar la
tarea), el 31 de agosto de 2026, zona horaria Europe/Madrid.

La suite configurada por `pytest.ini` descubre 44 tests. El resultado actual es
27 pasados, 13 fallidos, 4 errores y 0 saltados. Pytest informa 5,102 s; el
tiempo de pared, incluido `conda run`, es 9,844 s. La suite no está verde.

Ninguna evaluación online produjo métricas nuevas. Los runners no llegan a
ejecutar casos reales sin un agente inicializable y servicios externos. El
orquestador aborta en preflight por falta de `ANTHROPIC_API_KEY`,
`SUPABASE_URL` y `SUPABASE_KEY`. Los valores de esas variables no se buscaron,
copiaron ni documentaron.

No existe una cifra de cobertura de código válida para este baseline. El
intento instrumentado termina con código 4 porque `pytest-cov` no está instalado
en `HCE`, aunque `tests/README.md` recomienda `--cov`. El porcentaje de tests
pasados (61,4 %) no debe confundirse con cobertura de líneas o ramas.

## Identidad del baseline

| Dato | Valor observado |
| --- | --- |
| Commit | `38b94ba856998eef5cfffa21bc8b03cde510f1c3` |
| Rama de captura | `ao/hce-analyzer-3/fase0-baseline` |
| Sistema | Windows 10.0.26200 (Windows 11 reportado por la plataforma host) |
| Conda | 25.11.1 |
| Entorno | `HCE` |
| Python declarado | 3.11 (`environment.yml`) |
| Python observado | 3.11.14 |
| Pytest observado | 9.0.2 |
| Configuración | `pytest.ini`, `testpaths = tests`, `addopts = -v --tb=short` |
| Evidencia del entorno | `raw/environment-observed.txt` |

`environment.yml` fija únicamente la versión mayor/menor de Python y deja la
mayoría de paquetes sin versión exacta (algunos solo tienen mínimos). Por ello,
crear hoy un entorno nuevo desde el YAML reproduce la intención del entorno,
pero no garantiza las mismas versiones. `raw/environment-observed.txt` registra
los nombres y versiones efectivamente presentes, sin valores de entorno.

## Suite pytest

### Comando canónico ejecutado

Desde la raíz del repositorio:

```powershell
conda run -n HCE python -m pytest --durations=0 --junitxml=docs/baseline/raw/pytest-junit.xml
```

Resultado: código de salida 1.

| Área | Total | Pasan | Fallan | Error | Saltados |
| --- | ---: | ---: | ---: | ---: | ---: |
| `tests/evaluation/` | 24 | 24 | 0 | 0 | 0 |
| `tests/test_database.py` | 3 | 3 | 0 | 0 | 0 |
| `tests/test_rag_components.py` | 8 | 0 | 4 | 4 | 0 |
| `tests/test_system.py` | 9 | 0 | 9 | 0 | 0 |
| **Total** | **44** | **27** | **13** | **4** | **0** |

Las duraciones de todos los casos, incluidos los inferiores a 5 ms que pytest
oculta en su tabla textual, están en `raw/pytest-junit.xml`. La suma del tiempo
atribuido a casos es 2,596 s; la diferencia respecto a los 5,102 s de sesión es
colección, carga de plugins y demás overhead.

### Fallos y errores observados

Los 17 resultados no satisfactorios comparten el mismo bloqueo inicial:
importar `services` carga `config.settings`; `DatabaseSettings()` exige
`SUPABASE_URL` y `SUPABASE_KEY` en tiempo de importación y Pydantic lanza dos
errores de campo requerido.

| Grupo | Casos afectados | Estado |
| --- | ---: | --- |
| `ParentChildChunker` | 2 | Fallo |
| `SupabaseVectorStore` | 4 | Error de fixture antes del cuerpo del test |
| `Reranker` | 2 | Fallo |
| Imports de configuración/RAG/visualización | 3 | Fallo |
| `VisualizationAgent` | 2 | Fallo |
| `VisualizationHandler` | 2 | Fallo |
| Imports de `DatabaseTool` y `RAGTool` | 2 | Fallo |

No se ejecutó la lógica que esos casos pretendían verificar. En especial, los
mocks de `SupabaseVectorStore` no llegan a instalarse porque resolver el target
de `patch()` importa antes el paquete `services`.

No se modificó ningún test ni código de producción para alterar este resultado.

### Cobertura real conocida

La segunda ejecución solicitó cobertura sobre `config`, `services`, `src`,
`ui`, `utils` y `main`:

```powershell
conda run -n HCE python -m pytest `
  --cov=config --cov=services --cov=src --cov=ui --cov=utils --cov=main `
  --cov-report=term-missing `
  --cov-report=xml:docs/baseline/raw/coverage.xml
```

Pytest rechazó los argumentos `--cov` (código 4): `pytest-cov` no figura en
`environment.yml` ni está instalado en el entorno observado. No se generó
`coverage.xml` y no se declara una cifra numérica.

Lo que sí puede afirmarse por inspección de la ejecución es:

- pasan 24 tests unitarios/de propiedades de helpers de evaluación (validación
  de golden sets, reintentos, scoring, salidas TXT, resiliencia y dry-run);
- pasan 3 tests de base de datos construidos solo con `Mock` y comprobaciones de
  cadenas; no importan ni ejercitan el servicio de base de datos de producción;
- no completa ningún test de componentes RAG ni de sistema;
- no se contacta una base de datos, un LLM, un índice vectorial ni otro servicio
  externo durante pytest;
- no hay medida de cobertura de líneas, ramas o funciones ni un umbral de
  cobertura configurado.

## Evaluaciones

### Problema de invocación

Las cabeceras de los runners muestran la forma
`python Evaluation/<script>.py`. Ejecutada desde la raíz, esa forma termina con
`ModuleNotFoundError: No module named 'Evaluation'`, porque Python añade
`Evaluation/`, y no la raíz, a `sys.path` mientras el script usa imports
absolutos `from Evaluation...`.

Se conservaron estos intentos literales y después se repitieron mediante
`python -m Evaluation.<módulo>`, que sí permite llegar al preflight o a la
instanciación del agente.

### Resultado por runner

| Runner | Invocación funcional | Código | Trabajo realmente ejecutado | Bloqueo |
| --- | --- | ---: | --- | --- |
| `run_all_evaluations.py` | `python -m Evaluation.run_all_evaluations` | 1 | Preflight: golden sets y directorio OK; ningún módulo ejecutado | Falta `ANTHROPIC_API_KEY`; `SUPABASE_URL` y `SUPABASE_KEY` impiden cargar settings/conectar |
| `run_ragas_eval.py` (live) | `python -m Evaluation.run_ragas_eval ...` | 1 | Import parcial; 0 preguntas procesadas | Inicialización RAGAS queda no disponible sin la clave del evaluador; el mensaje afirma incorrectamente que RAGAS no está instalado |
| `run_ragas_eval.py` (dry, DB) | Igual con `--dry-run` | 0 | 40 preguntas leídas, 40 filtradas, 0 inválidas, sin llamadas al agente | `RAGAS_AVAILABLE=False`; el dry-run aun así informa “Ready” |
| `run_ragas_eval.py` (dry, RAG) | Igual con golden set RAG | 0 | 30 preguntas leídas, 30 filtradas, 3 inválidas, sin llamadas al agente | `GS-RAG-10`, `GS-RAG-20` y `GS-RAG-30` tienen `contexts` vacío; `RAGAS_AVAILABLE=False` |
| `run_security_tests.py` | `python -m Evaluation.run_security_tests` | 1 | Descubre 13 definiciones; ejecuta 0 | `UnifiedChatAgent` no se instancia sin settings de Supabase |
| `run_latency_benchmarks.py` | `python -m Evaluation.run_latency_benchmarks --n-runs 3` | 1 | Descubre 17 consultas; ejecuta 0 warmups y 0 medidas | Mismo fallo al instanciar el agente |
| `run_test_cases.py` | `python -m Evaluation.run_test_cases` | 1 | Descubre 28 casos; ejecuta 0 | Mismo fallo al instanciar el agente |

El dry-run del orquestador también termina con código 1. Estima 0,18 USD para
una ejecución completa, pero etiqueta seguridad como “~11 tests” mientras el
runner contiene y anuncia 13.

### Qué hace falta para una ejecución live

Los siguientes son nombres, nunca valores:

| Variable | Dónde se espera | Necesidad para estos runners |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | `.env`, entorno del proceso, `Evaluation/run_all_evaluations.py`, `Evaluation/run_ragas_eval.py`, `config/settings.py` | Obligatoria para el preflight, el agente y el LLM evaluador de RAGAS |
| `SUPABASE_URL` | `.env`, entorno del proceso, `config/settings.py` | Obligatoria; el orquestador hace un ping REST y el agente accede a datos/RAG |
| `SUPABASE_KEY` | `.env`, entorno del proceso, `config/settings.py` | Obligatoria; necesita permisos compatibles con las consultas y RPC usadas |
| `HUGGINFACEHUB_API_TOKEN` | `.env.example`, `config/settings.py` | Condicional; el evaluador carga `sentence-transformers/all-MiniLM-L6-v2`, que debe estar en caché o poder descargarse |
| `OPENAI_API_KEY` | `config/settings.py` | Opcional en la configuración actual; los runners inspeccionados usan Anthropic, no OpenAI |

Además se necesita:

- acceso de red a la API de Anthropic y, si no está cacheado, al modelo de
  embeddings de Hugging Face;
- un proyecto Supabase alcanzable con el esquema/tablas MIMIC y los RPC de
  búsqueda esperados por las herramientas;
- el corpus RAG compatible con `Evaluation/golden_set_ragas_rag.json`;
- permisos de solo lectura o mínimos suficientes para las evaluaciones;
- presupuesto/cuota para las llamadas externas y un entorno de datos autorizado.

No se verificó la existencia ni el valor de credenciales fuera del worktree. En
las capturas de evaluación se eliminaron explícitamente del proceso las cinco
variables anteriores para evitar consumo accidental.

### Resultados históricos excluidos

`Evaluation/results/` contiene informes fechados el 28 de abril de 2026. No se
consideran resultados actuales: no se regeneraron en esta captura y sus
credenciales, datos, versiones y commit de origen no están fijados en los
propios informes.

También revelan un riesgo del diseño del runner: el consolidado marca un módulo
como pasado si su `main()` devuelve 0, aunque el informe interno contenga
métricas o casos fallidos. Los `main()` actuales de RAGAS, seguridad, latencia y
casos funcionales devuelven 0 tras completar la ejecución sin convertir el
incumplimiento de thresholds en un código no cero. Por tanto, “módulo ejecutado”
no equivale a “evaluación aprobada”.

## Reproducción

### 1. Crear el entorno declarado

Con Anaconda o Miniconda, siguiendo `SETUP_CONDA.md`:

```powershell
conda env create -f environment.yml
conda activate HCE
python --version
python -m pip list --format=freeze
```

Si `HCE` ya existe, el repositorio documenta:

```powershell
conda env update -f environment.yml --prune
conda activate HCE
```

Para reproducir las versiones observadas, comparar la salida con
`docs/baseline/raw/environment-observed.txt`. El YAML por sí solo no es un lock
file.

### 2. Reproducir el baseline sin credenciales

Usar una shell desechable y retirar por nombre las variables de integración:

```powershell
$env:ANTHROPIC_API_KEY = $null
$env:SUPABASE_URL = $null
$env:SUPABASE_KEY = $null
$env:OPENAI_API_KEY = $null
$env:HUGGINFACEHUB_API_TOKEN = $null
```

Ejecutar pytest:

```powershell
conda run -n HCE python -m pytest --durations=0 --junitxml=docs/baseline/raw/pytest-junit.xml
```

Ejecutar los entrypoints funcionales, escribiendo artefactos fuera de
`Evaluation/results/`:

```powershell
conda run -n HCE python -m Evaluation.run_all_evaluations --dry-run --output-dir docs/baseline/raw/evaluation-generated/run-all-module-dry-run
conda run -n HCE python -m Evaluation.run_all_evaluations --output-dir docs/baseline/raw/evaluation-generated/run-all-module

conda run -n HCE python -m Evaluation.run_ragas_eval --dry-run --golden-set Evaluation/golden_set_ragas.json --subset all --output docs/baseline/raw/evaluation-generated/ragas-module-dry-run
conda run -n HCE python -m Evaluation.run_ragas_eval --dry-run --golden-set Evaluation/golden_set_ragas_rag.json --subset rag --output docs/baseline/raw/evaluation-generated/ragas-rag-module-dry-run
conda run -n HCE python -m Evaluation.run_ragas_eval --golden-set Evaluation/golden_set_ragas.json --subset all --output docs/baseline/raw/evaluation-generated/ragas-module

conda run -n HCE python -m Evaluation.run_security_tests --output docs/baseline/raw/evaluation-generated/security-module
conda run -n HCE python -m Evaluation.run_latency_benchmarks --n-runs 3 --output docs/baseline/raw/evaluation-generated/latency-module
conda run -n HCE python -m Evaluation.run_test_cases --output docs/baseline/raw/evaluation-generated/test-cases-module
```

Para reproducir el fallo de los comandos documentados en los propios scripts:

```powershell
conda run -n HCE python Evaluation/run_all_evaluations.py --output-dir docs/baseline/raw/evaluation-generated/run-all
conda run -n HCE python Evaluation/run_ragas_eval.py --golden-set Evaluation/golden_set_ragas.json --subset all --output docs/baseline/raw/evaluation-generated/ragas
conda run -n HCE python Evaluation/run_security_tests.py --output docs/baseline/raw/evaluation-generated/security
conda run -n HCE python Evaluation/run_latency_benchmarks.py --n-runs 3 --output docs/baseline/raw/evaluation-generated/latency
conda run -n HCE python Evaluation/run_test_cases.py --output docs/baseline/raw/evaluation-generated/test-cases
```

### 3. Ejecutar live cuando exista un entorno autorizado

Configurar por un mecanismo seguro `ANTHROPIC_API_KEY`, `SUPABASE_URL` y
`SUPABASE_KEY`; asegurar la disponibilidad del modelo de embeddings y los datos;
y repetir los comandos `python -m` sin retirar las variables. No guardar `.env`,
tokens, cabeceras, URLs sensibles ni cadenas de conexión en Git o en los logs.

## Riesgos y preguntas abiertas

1. La inicialización global de settings convierte ausencia de credenciales en
   fallos de importación y bloquea tests que pretenden ser unitarios.
2. Los 27 tests pasados sobrestiman el alcance útil: 3 solo prueban mocks y 24
   validan infraestructura de evaluación; el core RAG/sistema no completa tests.
3. No hay cobertura instrumentada ni threshold de cobertura reproducible.
4. `environment.yml` no bloquea versiones y no incluye `pytest-cov`; recrear el
   entorno más adelante puede cambiar el resultado.
5. La forma CLI documentada para los cinco scripts no es ejecutable desde la
   raíz; la forma módulo no está documentada.
6. RAGAS oculta la causa real de inicialización mediante un `except` amplio y
   reporta “no instalado” aun con `ragas==0.4.3` presente.
7. Los dry-runs RAGAS devuelven 0 con `RAGAS_AVAILABLE=False`; el set RAG además
   tiene 3/30 preguntas inválidas.
8. Los exit codes de los módulos expresan finalización técnica, no cumplimiento
   de thresholds. El consolidado puede mostrar módulos “PASSED” mientras sus
   métricas internas fallan.
9. El estimador del orquestador cuenta 11 pruebas de seguridad, frente a las 13
   definidas y anunciadas por el runner.
10. Las evaluaciones dependen de servicios y datos mutables; sin fijar versión
    de corpus, snapshot de base, modelos y configuración, dos ejecuciones live
    no son directamente comparables.
11. Falta decidir qué artefactos/versiones de datos y qué umbrales serán gates
    bloqueantes en CI. Este baseline describe el presente; no certifica seguridad
    ni preparación clínica.

## Evidencia

Todas las salidas crudas están indexadas en `docs/baseline/raw/README.md`. El
ADR `docs/decisions/0020-baseline-reproducible-tests-evaluation.md` formaliza qué
se incluye y qué queda fuera de este baseline.
