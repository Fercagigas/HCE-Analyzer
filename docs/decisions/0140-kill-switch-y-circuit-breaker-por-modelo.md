# ADR 0140 — Kill switch de IA y circuit breaker por modelo

Estado: Aceptada

Fecha: 2026-09-07

## Contexto

El Model Gateway de Fase 1 tiene timeout, reintentos y fallback, pero una incidencia
operativa podia seguir intentando un modelo degradado y no habia una forma central de
detener la generacion sin publicar una nueva version. En un entorno clinico, la API y
la interfaz deben declarar la degradacion sin inventar una respuesta ni ejecutar tools
que impliquen inferencia.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Desactivar solo el adapter Anthropic.** Descartada: deja caminos de inferencia
   alternativos y no cubre la respuesta controlada de los canales.
2. **Variable de entorno leida solo al arrancar.** Descartada como mecanismo operativo
   unico: requiere reiniciar el proceso para cambiar el estado.
3. **Flag persistido en Supabase.** Descartada en esta fase: convertir el plano de datos
   en dependencia para una medida de contencion introduce un nuevo punto de fallo y
   requiere migraciones y RLS de administracion.
4. **Flag de configuracion y fichero runtime local, consultado por peticion** (elegida).
   `HCE_AI_ENABLED` establece el valor base y `HCE_AI_KILL_SWITCH_FILE`, si existe,
   contiene `enabled` o `disabled` y prevalece inmediatamente.
5. **Un circuit breaker global para todo el proveedor.** Descartada: un modelo fallido
   no debe bloquear modelos aprobados que aun pueden atender la peticion.
6. **Circuit breaker por proveedor+modelo en el gateway** (elegida).

## Decision

- `AIGenerationGate` se consulta al inicio de `ChatService`, antes de historial,
  prompt, gateway o tools. Con IA deshabilitada devuelve `AI_DISABLED` y una respuesta
  controlada tanto para JSON como SSE; Streamlit consume el mismo servicio.
- El fichero runtime es opcional y se puede modificar por el procedimiento operativo
  del despliegue sin redeploy. Un valor invalido falla cerrado. `/ready` publica el
  componente `ai_generation` y no prueba el LLM cuando esta deshabilitado.
- Se auditan, sin texto de usuario ni resultados clinicos, los cambios detectados y
  cada rechazo del kill switch.
- `ModelCircuitBreaker` mantiene estados `closed`, `open` y `half_open` por
  `provider+model`. Los fallos configurables (`LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD`)
  abren el circuito; tras `LLM_CIRCUIT_BREAKER_RECOVERY_S` se permite una prueba
  half-open. Exito lo cierra, fallo lo reabre. Un circuito abierto salta directamente
  al fallback existente. Las transiciones se auditan.

## Consecuencias

- Positivas: contencion inmediata, degradacion honesta y menor carga sobre modelos
  fallidos; las decisiones se pueden reconstruir con el audit trail.
- Negativas: el estado del breaker es por proceso y se reinicia al reiniciar; en una
  futura topologia multi-worker debera compartirse en un store de resiliencia.
- El fichero runtime requiere permisos y procedimiento operacional restringidos. No
  contiene PHI ni secretos, pero una modificacion no autorizada afecta disponibilidad.
