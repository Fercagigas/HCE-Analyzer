# ADR 0060 — Cerrar superficie web con XSRF y CORS

Estado: aceptado

Fecha: 2026-09-01

## Contexto

El threat model identifica como riesgo crítico C-02 que Streamlit se ejecuta con `server.enableCORS = false` y `server.enableXsrfProtection = false`. Esta combinación permite conexiones desde orígenes ajenos y elimina la defensa de Streamlit frente a peticiones cross-site en la frontera navegador-servidor. El roadmap exige en P0.8 CSRF cuando aplique y CORS restrictivo, además de otros controles de navegador que no forman parte de este cambio.

El historial de `.streamlit/config.toml` se revisó con `git log --follow`, `git log -S` y `git blame`. Las dos desactivaciones fueron introducidas en el commit inicial `3b4f011` del 23 de agosto de 2025, cuyo mensaje es únicamente `first commit`, y no han cambiado desde entonces. No existe una incidencia, comentario, script de arranque ni configuración de proxy o túnel que documente por qué se desactivaron. Por tanto, la causa histórica verificable es una sobreescritura explícita de los valores seguros por defecto desde la creación del repositorio; su motivación concreta es desconocida. No hay evidencia para afirmar que respondiera a un fallo de uploads, red o proxy.

La documentación de arranque solo indica `streamlit run main.py` y acceso por `http://localhost:8501`. El usuario confirmó el 1 de septiembre de 2026 que el sistema se usa actualmente solo desde `localhost`, en el mismo equipo. La búsqueda en `.streamlit/`, `config/`, scripts y documentación no encontró otra configuración de bind, CORS, XSRF, proxy, túnel, cabeceras o servidor que altere esta topología. Streamlit 1.53.1 declara `enableCORS` y `enableXsrfProtection` activados por defecto, pero el repositorio los desactiva explícitamente; además, `server.address` no estaba fijado.

Este ADR solo trata la superficie web de Streamlit. No cambia la cookie de identidad de ChatHCE ni la revalidación de sesión contra Supabase, que pertenecen al riesgo de suplantación de sesión y quedan fuera de alcance.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mantener CORS y XSRF desactivados.** Se descarta porque conserva íntegramente C-02 y no existe una necesidad actual de acceso cross-origin que compense el riesgo.
2. **Eliminar ambas claves y confiar en los valores por defecto de Streamlit.** Se descarta porque, aunque la versión observada usa valores seguros por defecto, una decisión de seguridad debe quedar explícita y ser comprobable sin depender de cambios de versión o del conocimiento implícito del framework.
3. **Activar CORS y mantener XSRF desactivado.** Se descarta porque limita orígenes, pero deja sin protección específica las peticiones que reutilicen el contexto del navegador de la víctima.
4. **Activar XSRF y mantener CORS desactivado.** Se descarta porque Streamlit 1.53.1 considera incompatible esa combinación y fuerza CORS a `true`; expresar una configuración contradictoria produciría advertencias y ocultaría la política efectiva.
5. **Activar ambas protecciones y añadir orígenes permitidos para red, túnel o proxy.** Se descarta porque ampliaría la superficie sin un caso de uso actual. No se han confirmado dominios externos ni una capa que preserve de forma fiable host y esquema.
6. **Activar ambas protecciones y limitar el bind a `127.0.0.1`, sin orígenes adicionales.** Se elige porque implementa una política explícita de mismo origen y restringe la escucha al equipo local, que es la topología confirmada.

## Decision

Configurar el servidor Streamlit de esta forma en `.streamlit/config.toml`:

```toml
[server]
headless = false
address = "127.0.0.1"
enableCORS = true
enableXsrfProtection = true
```

No se define `server.corsAllowedOrigins`: el flujo normal usa el mismo origen local y no necesita excepciones. Se conserva `headless = false` porque no debilita estas protecciones y mantiene el comportamiento de arranque existente.

La decisión exige comprobar la configuración efectiva, el arranque del proceso, la conexión del navegador en loopback y el envío de un fichero al endpoint de upload de Streamlit. No autoriza cambios en autenticación, cookies de identidad, servicios, UI ni integración con Supabase.

## Motivo

Una página servida por ChatHCE en `localhost` es same-origin respecto a sus endpoints HTTP y WebSocket. CORS puede rechazar orígenes ajenos sin bloquear esa comunicación. XSRF añade un token ligado al navegador legítimo y Streamlit lo valida en las conexiones y operaciones protegidas, incluida la ruta de carga de ficheros. Ambas defensas son complementarias y el propio framework las habilita juntas por defecto.

Fijar `127.0.0.1` evita que el proceso escuche de forma implícita en interfaces de red cuando el único uso autorizado es local. Esta restricción reduce la exposición antes incluso de que se evalúe el origen en el navegador.

No se preserva una compatibilidad hipotética con proxy, túnel o acceso LAN porque el historial no demuestra que fuera la causa de la desactivación y el usuario ha confirmado que esos modos no se usan. Si la topología cambia, debe diseñarse una configuración explícita para ella en vez de volver a desactivar globalmente los controles.

## Consecuencias

- Se recuperan las defensas integradas de Streamlit frente a orígenes no permitidos y peticiones cross-site.
- El servidor queda accesible únicamente mediante el loopback del equipo local.
- El uso normal en `localhost`, incluida la conexión WebSocket y la selección/subida de documentos, debe continuar funcionando con el token XSRF gestionado por Streamlit.
- El acceso directo desde otro equipo de la red deja de funcionar deliberadamente.
- Un túnel, dominio alternativo o proxy inverso no configurado puede fallar por el bind local, la comprobación de origen o el tratamiento de host/esquema. Esto es una pérdida aceptada para la topología actual.
- No se añaden excepciones CORS, lo que evita convertir una futura necesidad de despliegue en una autorización implícita y permanente.
- Este cambio reduce C-02, pero no completa por sí solo todo P0.8: CSP, cabeceras de seguridad, TLS y atributos de cookies requieren una capa de despliegue o decisiones adicionales.
- La suplantación mediante la cookie de aplicación y la revalidación contra Supabase permanecen sin cambios y fuera del alcance de este ADR.
- La verificación manual del 1 de septiembre de 2026 cargó la configuración efectiva con CORS y XSRF activos, confirmó que el proceso escuchaba solo en `127.0.0.1`, obtuvo `200` del healthcheck y abrió en navegador la pantalla de inicio de sesión mediante una sesión WebSocket funcional.
- Sobre ese mismo servidor se abrió una sesión de prueba y se ejercitó el endpoint real de upload: un WebSocket con origen ajeno fue rechazado, una subida sin token XSRF devolvió `403` y la misma subida local con el token emitido por Streamlit fue aceptada con `204`. Se usaron valores inertes de configuración y un fichero de prueba; no se emplearon secretos reales, no se contactaron proveedores y no se procesó ni indexó contenido.

## Pendientes

1. Si se necesita acceso LAN, túnel o proxy, documentar primero la topología, los orígenes exactos, la terminación TLS y la preservación de host/esquema; después crear configuración por entorno y repetir las pruebas de WebSocket y upload.
2. Definir CSP, cabeceras HTTP de seguridad y TLS en la capa de despliegue que corresponda, sin desactivar CORS o XSRF como atajo de compatibilidad.
3. Incorporar una comprobación automatizada que impida volver a establecer `enableCORS = false`, `enableXsrfProtection = false` o un bind no local en la configuración destinada a uso local.
4. Reevaluar el riesgo residual C-02 con evidencia de despliegue y pruebas adversariales antes de exponer el sistema fuera del equipo local.
5. Abordar la cookie de identidad y la revalidación de sesión contra Supabase en la fase y el riesgo asignados, sin mezclarlos con esta mitigación.
