# Salidas crudas del baseline de Fase 0

Captura realizada el 31 de agosto de 2026 sobre el commit
`38b94ba856998eef5cfffa21bc8b03cde510f1c3`, en Windows, con el entorno Conda
`HCE` y Python 3.11.14.

Los `.txt` conservan el comando, fecha de inicio, directorio de trabajo, salida
completa, código de salida y tiempo de pared. No contienen valores de secretos.
Para los intentos de evaluación se retiraron explícitamente del proceso las
variables de credenciales indicadas por nombre en cada captura.

## Índice

- `environment-observed.txt`: plataforma, commit, intérprete y paquetes
  instalados con sus versiones.
- `pytest-full.txt`: ejecución canónica de la suite, incluido el detalle de
  fallos y duraciones.
- `pytest-junit.xml`: resultado estructurado por caso, con estado y tiempo de
  los 44 tests.
- `pytest-coverage.txt`: intento de cobertura; no comienza porque falta el
  plugin `pytest-cov` en el entorno `HCE`.
- Los ficheros sin sufijo `-module` (`evaluation-run-all.txt`,
  `evaluation-ragas.txt`, `evaluation-security.txt`, `evaluation-latency.txt`
  y `evaluation-test-cases.txt`) evidencian el fallo de importación de la forma
  `python Evaluation/<script>.py`.
- `evaluation-*-module.txt`: segundo intento mediante `python -m`, que sí carga
  el paquete y expone los bloqueos reales de configuración.
- `evaluation-*-dry-run.txt`: preflight o validación sin llamadas al agente.
- `evaluation-generated/`: logs que el propio orquestador alcanzó a generar.

La interpretación y los comandos de reproducción están en
`../FASE0_BASELINE.md`.
