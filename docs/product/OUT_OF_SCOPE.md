# Fuera de alcance inicial

## Propósito de estos límites

Los límites siguientes aplican a la versión 1 y al piloto inicial. Evitan que una capa de recuperación y síntesis se convierta implícitamente en un sistema autónomo de decisión o ejecución clínica sin la evidencia, los controles y la estrategia regulatoria correspondientes.

Este documento no es asesoramiento jurídico ni fija la clasificación regulatoria de ChatHCE. Esa decisión se realizará en la Fase 7 conforme al uso real, los claims, la jurisdicción y `ROADMAP_HOSPITAL_READY/13-regulatory-quality-clinical-safety.md`.

## Capacidades clínicas excluidas

### Prescripción autónoma

ChatHCE no selecciona ni prescribe un medicamento, dosis, vía, frecuencia o duración para un paciente de forma autónoma. Tampoco renueva, suspende o modifica medicación.

**Por qué:** exige valorar información completa y contextual, puede causar daño directo y convierte una salida informativa en recomendación o acción clínica de alto riesgo. Buscar o citar un protocolo farmacológico no equivale a prescribir.

### Diagnóstico autónomo

ChatHCE no establece, confirma ni descarta un diagnóstico de forma autónoma y no se presenta como sustituto de una evaluación clínica.

**Por qué:** la HCE puede ser incompleta o contradictoria, la inferencia puede estar equivocada y la formulación de un diagnóstico altera decisiones posteriores. El producto puede organizar hechos e identificar explícitamente hipótesis solo si una capability de inferencia ha sido validada y siempre bajo revisión profesional.

### Triaje autónomo

ChatHCE no asigna prioridad asistencial, nivel de acuidad, destino ni tiempo máximo de atención, y no retrasa ni reemplaza circuitos de urgencia existentes.

**Por qué:** una omisión o clasificación errónea puede tener consecuencias inmediatas. Los campos de triaje ya registrados pueden recuperarse como hechos, pero el sistema no calcula ni cambia el triaje del paciente.

### Modificación automática de la HCE

ChatHCE no crea, edita, borra, firma ni presenta como definitivo ningún elemento de la HCE. Un borrador generado por IA no es parte del registro oficial.

**Por qué:** la escritura puede propagar errores, ocultar la autoría y romper trazabilidad. Cualquier integración futura de escritura debe ser separada, mostrar una previsualización editable y requerir autorización y aprobación humana explícitas.

### Órdenes clínicas sin aprobación

ChatHCE no solicita pruebas, procedimientos, interconsultas, medicación, ingresos, altas o traslados sin una acción consciente de un profesional autorizado.

**Por qué:** una orden tiene efecto real sobre el paciente y los sistemas hospitalarios. Ni una instrucción del usuario ni una salida del modelo pueden ampliar permisos o saltarse un flujo de aprobación.

## Exclusiones de función y posicionamiento

- ChatHCE no es una HCE, repositorio maestro, sistema de prescripción, CPOE, motor de triaje ni dispositivo de monitorización.
- No garantiza que la información consultada sea completa, actual o libre de errores.
- No sustituye la consulta de la fuente original ni las políticas y protocolos del centro.
- No ofrece una «segunda opinión» autónoma ni una recomendación individual de tratamiento.
- No realiza vigilancia continua ni promete detectar todos los cambios o deterioros.
- No comunica certeza clínica mediante un porcentaje de confianza autodeclarado por el LLM.
- No usa contenido documental no aprobado, vencido, retirado o de otro tenant como fundamento clínico.
- No expone información de un paciente fuera del contexto y propósito autorizados.

## Límites técnicos para producción hospitalaria

Las siguientes funciones presentes o posibles en el prototipo no forman parte del producto hospitalario inicial:

- SQL libre generado por el LLM contra datos clínicos de producción;
- acceso directo del modelo a credenciales o esquemas de la HCE;
- ejecución de código, shell o Python arbitrario generado por el modelo;
- visualizaciones basadas en código no parametrizado y no aislado;
- carga e indexación clínica de documentos sin validación, análisis de seguridad, metadatos, aprobación y versionado;
- búsqueda externa abierta como fuente clínica sin allowlist, procedencia y gobierno;
- reutilización de contexto conversacional tras cambiar de paciente, episodio, tenant o sesión;
- logging por defecto de prompts o respuestas clínicos completos.

El SQL `SELECT` personalizado, el dataset MIMIC-IV-ED, los documentos indexados y la generación de visualizaciones del código actual son activos de investigación y evaluación. Su existencia no amplía el intended purpose ni demuestra preparación para producción.

## Condiciones para reconsiderar una exclusión

Una capacidad excluida solo puede reconsiderarse mediante una nueva decisión de producto y arquitectura que, como mínimo:

1. actualice el intended purpose, los claims y esta frontera de alcance;
2. la clasifique en la matriz de riesgo y mantenga un hazard log específico;
3. determine la ruta regulatoria aplicable con asesoramiento competente;
4. implemente autorización, contratos de herramienta, evidencia, auditoría y aprobación humana proporcionales;
5. supere evaluación clínica, seguridad, factores humanos y gates de regresión;
6. defina despliegue gradual, monitorización, kill switch y rollback;
7. obtenga aceptación documentada del riesgo residual por los responsables designados.

Hasta cumplir esas condiciones, una petición fuera de alcance debe bloquearse de forma segura y, cuando sea útil, reconducirse a recuperación de información o evidencia sin producir la acción excluida.
