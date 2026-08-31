# ADR 0020 — Baseline reproducible de tests y evaluación

## Contexto

La Fase 0 del roadmap requiere congelar el comportamiento actual antes de
refactorizar ChatHCE. La suite pytest tiene resultados mixtos y los runners de
evaluación dependen de credenciales, servicios, datos y modelos externos. El
repositorio también contiene informes históricos en `Evaluation/results/`, pero
no fijan de forma suficiente el commit, el entorno, las credenciales, el estado
de los datos ni los modelos que los produjeron.

Un baseline útil debe conservar tanto los éxitos como los fallos sin convertir
la ausencia de infraestructura externa en resultados clínicos o de seguridad.
También debe ser reproducible sin exponer secretos.

## Opciones consideradas (incluidas las descartadas y por que)

1. Considerar baseline únicamente los tests y evaluaciones que pasan. Se
   descarta porque ocultaría 13 fallos, 4 errores y todos los módulos externos
   no ejecutados; produciría una imagen artificialmente positiva.
2. Adoptar los ficheros existentes en `Evaluation/results/` como baseline de
   evaluación. Se descarta porque son históricos, no se regeneraron en la
   captura actual y carecen de procedencia suficiente para comparar ejecuciones.
   Además, un módulo puede constar como completado aunque sus métricas internas
   estén bajo threshold.
3. Instalar dependencias faltantes, introducir credenciales de prueba o cambiar
   configuración/tests para conseguir una ejecución verde. Se descarta porque
   alteraría el objeto que se quiere medir, infringiría el freeze previo al
   refactor y podría consumir o revelar servicios no autorizados.
4. Fijar el baseline como una observación versionada: commit, entorno, comandos,
   códigos de salida, tiempos, outputs crudos y clasificación explícita entre
   ejecutado, fallido, bloqueado y no medido. Esta es la opción elegida.

## Decision

El baseline de Fase 0 queda definido por:

- el commit `38b94ba856998eef5cfffa21bc8b03cde510f1c3`;
- el entorno Conda `HCE` observado con Python 3.11.14 y el inventario de paquetes
  en `docs/baseline/raw/environment-observed.txt`;
- la ejecución canónica de `pytest.ini` + `tests/`, incluido cada estado y
  duración en TXT y JUnit;
- el intento de medición de cobertura y su bloqueo por ausencia de `pytest-cov`;
- los intentos literales de los cinco scripts y los intentos funcionales con
  `python -m`, incluidos preflight y dry-runs sin credenciales;
- `docs/baseline/FASE0_BASELINE.md` como interpretación versionada de la evidencia
  cruda en `docs/baseline/raw/`.

Quedan fuera del baseline cuantitativo:

- los informes históricos de `Evaluation/results/`;
- cualquier score RAGAS, de seguridad, funcional o de latencia que no haya sido
  producido durante esta captura;
- cobertura numérica de código, porque no llegó a medirse;
- disponibilidad, rendimiento o seguridad de servicios externos no ejecutados;
- valores de secretos, tokens, claves, URLs sensibles o cadenas de conexión;
- cambios para corregir tests, código de producción, datos o configuración.

Los estados “bloqueado” o “no medido” no se reinterpretan como aprobado ni como
fallido clínico: expresan ausencia de evidencia ejecutada.

## Motivo

Esta decisión conserva una referencia honesta y auditable del sistema previo al
refactor. Permite comparar cambios futuros contra el mismo conjunto de comandos
sin atribuir resultados a componentes que no llegaron a ejecutarse, evita
contaminar el baseline arreglando sus síntomas y mantiene los secretos fuera del
repositorio.

## Consecuencias

- El baseline inicial no es verde y no constituye un gate de release ni una
  certificación de seguridad o eficacia clínica.
- Las regresiones futuras deberán comparar por separado tests locales, cobertura
  y evaluaciones live; no basta el código de salida del orquestador.
- Para repetir exactamente el entorno observado hará falta un mecanismo de lock
  adicional, porque `environment.yml` no fija todas las versiones.
- Una ejecución live posterior deberá registrar versiones de modelos, corpus y
  snapshot de datos, además de usar credenciales por un canal seguro.
- Los fallos actuales permanecen visibles como deuda y no se corrigen en esta
  decisión.

## Pendientes

- Definir y versionar un lock de dependencias compatible con Conda.
- Añadir de forma deliberada la herramienta de cobertura y acordar su alcance y
  threshold en una fase posterior.
- Desacoplar la importación de módulos de las credenciales para distinguir tests
  unitarios de integración, sin reescribir el dato histórico de este baseline.
- Corregir/documentar los entrypoints y la semántica de exit codes en una tarea
  posterior.
- Validar o corregir las 3 preguntas RAG con `contexts` vacío.
- Definir snapshots/versiones de Supabase y del corpus RAG para comparabilidad.
- Acordar umbrales bloqueantes y un informe de seguridad que no confunda
  “ejecutado” con “aprobado”.
