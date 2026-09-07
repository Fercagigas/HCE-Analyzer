# ADR 0160 — Minimizacion y deteccion de PHI antes del modelo

Estado: Aceptada

Fecha: 2026-09-07

## Contexto

MIMIC-IV Demo esta desidentificado, pero ChatHCE debe poder conectarse a datos hospitalarios reales sin enviar identificadores innecesarios al proveedor de modelos. Antes de esta decision, el historial y el resultado estructurado de una tool podian convertirse en contexto del modelo sin una politica por campo. `AuditEvent` ya tenia una allowlist, pero faltaba una prueba de extremo a extremo frente a PHI sintetico.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Confiar en la desidentificacion de MIMIC y no transformar datos.** Descartada: no protege el futuro adapter hospitalario ni texto libre.
2. **Redactar todo con expresiones regulares justo antes del proveedor.** Descartada: no minimiza DTOs estructurados, no define el tratamiento de fechas e identificadores y concentra logica en `ModelGateway`.
3. **Eliminar todos los identificadores y fechas.** Descartada: impide relacionar episodios y seguir una evolucion clinica en una misma conversacion.
4. **Catalogo por DTO + detector de texto en las fronteras del prompt** (elegida). El catalogo elimina texto libre, generaliza fechas a mes y pseudonimiza identificadores con HMAC estable solo durante la sesion. El detector cubre DNI/NIE, telefonos, correos y nombres marcados en notas. Los modos `observe`, `redact` y `block` son configurables con `PHI_DETECTION_MODE`; el valor seguro por defecto es `redact`.
5. **Servicio DLP externo obligatorio.** Aplazada: requiere contrato, residencia y disponibilidad operativa; la capa local deja una frontera y contratos comprobables offline.

## Decision

- `chathce/domain/phi.py` contiene el catalogo `CLINICAL_PHI_CATALOG`, las acciones `remove`, `generalize` y `pseudonymize`, y el detector de texto.
- `ChatService` inspecciona el mensaje y cada entrada del historial antes de invocar al gateway. En `block` devuelve `PHI_BLOCKED` sin enviar el texto. La persistencia conserva la version segura para que un turno posterior tampoco reinyecte PHI.
- `ToolRegistry` minimiza `ToolResult.data` y su representacion visible inmediatamente antes de que el gateway la entregue al modelo. No se modifica `ModelGateway`.
- La auditoria no recibe hallazgos ni valores detectados: los identificadores de usuario, paciente, episodio y sesion se pseudonimizan antes de `AuditEvent`, y solo se conservan metadatos permitidos. Los tests usan exclusivamente valores sinteticos y verifican ausencia de estos en el mock del proveedor y en los eventos de auditoria.

## Consecuencias

- Positivas: existe un unico catalogo reutilizable, los tokens no son reversibles sin el valor original y la correlacion minima dentro de sesion se conserva; la configuracion funciona sin `.env`.
- Negativas: la deteccion de nombres es deliberadamente conservadora para no dañar preguntas clinicas; no sustituye una solucion DLP ni una DPIA. Los tokens cambian entre sesiones y no sirven como identificadores de negocio.
- Operacion: en produccion se debe mantener `redact` o `block`; `observe` solo sirve para despliegues controlados y no registra el contenido detectado.
