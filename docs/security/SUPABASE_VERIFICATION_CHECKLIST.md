# Checklist de verificación de Supabase y despliegue

Estado: lista operativa para convertir incertidumbres del threat model en controles o riesgos confirmados

Duración objetivo: 20 minutos por entorno

Fecha de revisión de las rutas del panel: 2026-09-01

## Reglas antes de empezar

- Ejecuta esta lista tú mismo con permisos Owner o Admin. No envíes claves, tokens, URL del proyecto, credenciales ni capturas sin redactar a nadie.
- No pegues secretos en tickets, documentos, terminales compartidos ni historial de shell. Si una pantalla muestra un secreto, registra solamente su **tipo**, ubicación y resultado (`OK` o `PROBLEMA`).
- Guarda la evidencia en el repositorio documental protegido del proyecto, no en Git. Una captura debe ocultar claves, tokens, URL/ref del proyecto, emails, IP y datos clínicos.
- Repite la lista para cada entorno desplegado. Usa un alias no sensible, por ejemplo `PRODUCCION` o `PRUEBAS`; no anotes la URL real.
- Esta es una verificación de solo lectura. Las correcciones están en [Qué hacer si sale mal](#qué-hacer-si-sale-mal).

Completa primero:

| Campo | Valor sin secretos |
|---|---|
| Entorno | `PRODUCCION / PRUEBAS / LOCAL` |
| Fecha y ejecutor | `AAAA-MM-DD / rol` |
| Alias interno del proyecto Supabase | `ALIAS_NO_SENSIBLE` |
| Despliegue de la aplicación | `proveedor o host, sin URL` |
| Clasificación aprobada de datos | `demo / anonimizados / PHI-PII` |
| Evidencia protegida | `ID_INTERNO_AQUI` |

### Escala usada

- **Crítica:** detener la exposición compartida o el uso de datos sensibles hasta contener el riesgo.
- **Alta:** corregir antes del siguiente piloto o ampliación de acceso.
- **Media:** corregir con responsable y fecha; no permite contabilizar el control mientras siga abierta.

## Pasada de 20 minutos

| Minuto | Comprobación |
|---:|---|
| 0-2 | 1. Proyecto, entorno y datos reales |
| 2-4 | 2. Tipo y exposición de la clave |
| 4-8 | 3. RLS, grants y policies |
| 8-11 | 4. RPC y `SECURITY DEFINER` |
| 11-14 | 5. Exposición pública, TLS y red |
| 14-16 | 6. Logs: acceso y retención |
| 16-17 | 7. Ubicación y región |
| 17-18 | 8. Política del proveedor Anthropic |
| 18-19 | 9. Corpus y administración documental |
| 19-20 | 10. Caché, procesos y cierre |

## 1. Proyecto, entorno y datos reales — 2 minutos

### 1.1 Correspondencia entre despliegue y proyecto

- **Qué comprobar:** que `SUPABASE_URL` y `SUPABASE_KEY` del despliegue pertenecen al mismo proyecto y al entorno esperado.
- **Dónde exactamente:** gestor de secretos del servicio desplegado, buscando solo los nombres `SUPABASE_URL` y `SUPABASE_KEY`; después Supabase Dashboard → selector de proyecto → **Settings → API Keys**. En local, las rutas de carga son `.env` y, si se usa Streamlit, `.streamlit/secrets.toml`; el inventario las traza en `docs/architecture/INVENTORY.md:171-178`.
- **Resultado correcto:** existe una pareja por entorno, el identificador visible del proyecto coincide, y producción no reutiliza el proyecto ni la clave de pruebas. El secreto está en el gestor del despliegue, no en variables de build, imagen, repositorio, frontend ni logs.
- **Resultado problemático:** proyecto desconocido o compartido entre entornos; URL y clave de proyectos distintos; una clave copiada en imagen, artefacto, historial, log o configuración visible al navegador.
- **Gravedad si sale mal:** **Crítica** si puede cruzar producción/pruebas o exponer una clave elevada; **Alta** para cualquier otra deriva de entorno.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — evidencia: alias de ambos entornos y ubicación del secreto, nunca su valor.

### 1.2 Contenido real de la instancia

- **Qué comprobar:** si la instancia contiene solo MIMIC-IV-ED demo/datos preparados o datos personales/clínicos reales.
- **Dónde exactamente:** Supabase Dashboard → **SQL Editor → New query**. Ejecuta esta consulta de metadatos; no abre filas ni devuelve contenido:

```sql
select schemaname, relname as table_name, n_live_tup as estimated_rows
from pg_stat_user_tables
where schemaname in ('public', 'mimic_ed')
order by schemaname, relname;
```

  Contrasta el alias del proyecto y los nombres de tabla con el inventario autorizado del entorno. Las tablas esperadas por el código están en `docs/architecture/INVENTORY.md:121-160`.
- **Resultado correcto:** existe un inventario aprobado que clasifica el entorno como demo, anonimizado o PHI/PII, y las tablas/volúmenes son compatibles con él. No inspecciones valores para hacer esta comprobación.
- **Resultado problemático:** nadie puede afirmar qué datos hay; aparecen tablas o volúmenes inesperados; hay PHI/PII en el prototipo actual o datos de otro entorno/tenant.
- **Gravedad si sale mal:** **Crítica** si hay o puede haber PHI/PII o mezcla de tenants; **Alta** si el inventario de datos demo es desconocido.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota solo clasificación, tablas inesperadas y responsable.

## 2. Tipo y exposición de la clave — 2 minutos

### 2.1 Privilegio efectivo de `SUPABASE_KEY`

- **Qué comprobar:** si el valor desplegado corresponde a una clave de bajo privilegio (`publishable` o legacy `anon`) o a una elevada (`secret` o legacy `service_role`). No decodifiques ni copies la clave en documentación.
- **Dónde exactamente:** Supabase Dashboard → **Settings → API Keys**; compara allí, visualmente y en una sesión privada, el valor del gestor de secretos del despliegue con la fila etiquetada. Comprueba también el indicador **Last used**. El código carga una sola `SUPABASE_KEY` para Auth, tablas `mimic_ed`, tablas de producto, RAG y RPC (`docs/architecture/INVENTORY.md:175-192`).
- **Resultado correcto:** la única `SUPABASE_KEY` del runtime actual es de bajo privilegio y RLS/grants/RPC limitan sus operaciones. Cualquier clave elevada necesaria para una tarea administrativa está separada por componente, solo en backend aislado y no usa esta variable compartida.
- **Resultado problemático:** `SUPABASE_KEY` es `secret`/`service_role`; no se puede identificar su tipo; una clave elevada está en navegador, aplicación de escritorio, variable de build o frontend; varios componentes reutilizan una clave elevada. Las claves elevadas omiten RLS.
- **Gravedad si sale mal:** **Crítica**.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — registra únicamente `bajo privilegio`, `elevada` o `desconocida`.

### 2.2 Copias y personas con acceso

- **Qué comprobar:** dónde existe cada clave y quién puede revelarla o modificarla.
- **Dónde exactamente:** gestor de secretos del despliegue → permisos/IAM e historial de cambios; Supabase Dashboard → **Organization Settings → Team**; repositorio → **Settings → Secrets and variables → Actions** si GitHub Actions despliega. En el host, confirma solo la existencia de `.env`/`.streamlit/secrets.toml`, no su contenido.
- **Resultado correcto:** mínimo número de copias; acceso nominal y de mínimo privilegio; MFA; sin cuentas compartidas; cambios auditables; ningún secreto en Git, logs, copias de chat o equipos no gestionados.
- **Resultado problemático:** acceso de personas que no operan el entorno; archivos legibles por usuarios ajenos; secreto en CI sin necesidad; copia sin propietario o sin fecha de rotación.
- **Gravedad si sale mal:** **Crítica** para una clave elevada expuesta; **Alta** para acceso o copias excesivas de una clave de bajo privilegio.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota roles y número de ubicaciones, no nombres personales ni valores.

## 3. RLS, grants y policies — 4 minutos

### 3.1 Cobertura por tabla y vista

- **Qué comprobar:** RLS activado y policies/grants explícitos en cada tabla de un schema expuesto. Incluye como mínimo:
  - `mimic_ed.diagnosis`, `edstays`, `medrecon`, `pyxis`, `triage`, `vitalsign`;
  - `public.users`, `chat_sessions`, `chat_messages`, `clinical_documents`, `analyses`, `user_preferences`, `rag_chunks`;
  - cualquier tabla o vista adicional devuelta por la consulta.
- **Dónde exactamente:** Supabase Dashboard → **Settings → Data API → Exposed schemas**; anota los schemas. Después **SQL Editor → New query** y ejecuta, añadiendo a la lista cualquier schema expuesto que no sea `public` o `mimic_ed`:

```sql
with api_objects as (
  select
    n.nspname as schema_name,
    c.relname as object_name,
    case c.relkind
      when 'r' then 'table'
      when 'p' then 'partitioned table'
      when 'v' then 'view'
      when 'm' then 'materialized view'
    end as object_type,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced,
    c.reloptions
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname in ('public', 'mimic_ed')
    and c.relkind in ('r', 'p', 'v', 'm')
), policy_counts as (
  select schemaname, tablename, count(*) as policy_count
  from pg_policies
  where schemaname in ('public', 'mimic_ed')
  group by schemaname, tablename
)
select
  o.*,
  coalesce(p.policy_count, 0) as policy_count
from api_objects o
left join policy_counts p
  on p.schemaname = o.schema_name and p.tablename = o.object_name
order by o.schema_name, o.object_name;
```

- **Resultado correcto:** toda tabla expuesta tiene `rls_enabled = true`; cada vista expuesta está justificada y usa `security_invoker=true` o no entrega datos protegidos; cada objeto no destinado a API está fuera de **Exposed schemas** o sin grants para roles API. RLS forzado es defensa adicional, no sustituto de tests.
- **Resultado problemático:** tabla expuesta con RLS desactivado; vista con permisos del creador que evita RLS; objeto inesperado; tabla sensible expuesta sin policies. `policy_count = 0` deniega por defecto con clave baja, pero confirma que la aplicación no dependa de un acceso inexistente.
- **Gravedad si sale mal:** **Crítica** para datos clínicos, identidad, conversación o RAG; **Alta** para otro objeto no sensible no inventariado.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — guarda el CSV de resultados en evidencia protegida.

### 3.2 Semántica de policies y grants

- **Qué comprobar:** quién puede hacer `SELECT`, `INSERT`, `UPDATE` y `DELETE`, y que la condición de policy imponga ownership/contexto tanto en `USING` como en `WITH CHECK`.
- **Dónde exactamente:** Supabase Dashboard → **Database → Policies**, tabla por tabla; después **SQL Editor → New query**:

```sql
select
  p.schemaname,
  p.tablename,
  p.policyname,
  p.permissive,
  p.roles,
  p.cmd,
  p.qual as using_expression,
  p.with_check,
  coalesce(string_agg(distinct g.grantee || ':' || g.privilege_type, ', '), 'NO_GRANTS') as grants
from pg_policies p
left join information_schema.role_table_grants g
  on g.table_schema = p.schemaname
 and g.table_name = p.tablename
 and g.grantee in ('anon', 'authenticated', 'service_role')
where p.schemaname in ('public', 'mimic_ed')
group by p.schemaname, p.tablename, p.policyname, p.permissive,
         p.roles, p.cmd, p.qual, p.with_check
order by p.schemaname, p.tablename, p.cmd, p.policyname;
```

  Para detectar grants incluso en tablas sin policies, ejecuta además:

```sql
select table_schema, table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema in ('public', 'mimic_ed')
  and grantee in ('anon', 'authenticated', 'service_role')
order by table_schema, table_name, grantee, privilege_type;
```

- **Resultado correcto:** `anon` no accede a datos del proyecto; `authenticated` solo tiene las operaciones necesarias. `users`, sesiones, mensajes, análisis y preferencias se limitan a `auth.uid()` y al propietario; `chat_messages` prueba ownership a través de `chat_sessions`; `INSERT`/`UPDATE` tienen `WITH CHECK`. Datos clínicos y RAG se limitan al contexto aprobado de usuario/tenant/paciente o no son accesibles por roles públicos. Hay policies separadas por operación y tests de permitir/denegar.
- **Resultado problemático:** expresiones `true`; rol `public`/`anon`; acceso global de `authenticated`; comprobación solo en `SELECT`; escritura que permite cambiar `user_id`/tenant; policy basada en metadata modificable por el usuario; RLS existente pero nunca probado. El runtime actual no transporta tenant/paciente obligatorios, por lo que una policy global no demuestra aislamiento hospitalario.
- **Gravedad si sale mal:** **Crítica** para lectura/escritura cruzada, acceso anónimo o datos clínicos/RAG globales; **Alta** si falta evidencia de tests aunque la policy parezca correcta.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota nombres de policies fallidas, nunca datos de filas.

## 4. RPC y `SECURITY DEFINER` — 3 minutos

### 4.1 Definición, propietario y permisos efectivos

- **Qué comprobar:** existencia, schema, firma, propietario, modo invoker/definer, `search_path` y permisos de `execute_readonly_query`, `hybrid_search` y `vector_search`.
- **Dónde exactamente:** Supabase Dashboard → **SQL Editor → New query**:

```sql
select
  n.nspname as schema_name,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as arguments,
  r.rolname as owner,
  case when p.prosecdef then 'DEFINER' else 'INVOKER' end as security_mode,
  p.proconfig as function_settings,
  has_function_privilege('anon', p.oid, 'EXECUTE') as anon_can_execute,
  has_function_privilege('authenticated', p.oid, 'EXECUTE') as authenticated_can_execute,
  has_function_privilege('service_role', p.oid, 'EXECUTE') as service_role_can_execute
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
join pg_roles r on r.oid = p.proowner
where p.proname in ('execute_readonly_query', 'hybrid_search', 'vector_search')
order by p.proname, arguments;
```

  Para revisar el cuerpo sin copiarlo fuera del panel:

```sql
select n.nspname as schema_name, p.proname as function_name,
       pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where p.proname in ('execute_readonly_query', 'hybrid_search', 'vector_search')
order by p.proname;
```

- **Resultado correcto:** las tres funciones tienen definición conocida y versionada; usan `SECURITY INVOKER` salvo excepción justificada. `anon` no puede ejecutarlas. Los grants son allowlist. Las búsquedas imponen dentro de SQL el tenant/colección autorizados y límites máximos. Toda excepción `SECURITY DEFINER` tiene propietario sin privilegios innecesarios, `search_path` vacío/fijo, nombres totalmente cualificados, validación estricta y tests de denegación.
- **Resultado problemático:** falta una función esperada o existen sobrecargas no inventariadas; cualquier rol la ejecuta por el grant implícito a `PUBLIC`; `SECURITY DEFINER` sin `search_path` seguro; owner privilegiado; SQL arbitrario; filtros/límites solo en Python; búsqueda RAG global.
- **Gravedad si sale mal:** **Crítica** para `execute_readonly_query`, cualquier RPC `DEFINER` insegura o ejecutable por `anon`; **Crítica** para búsqueda cruzada con datos sensibles/multitenant y **Alta** para el corpus demo controlado.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — registra firma, modo y roles; no copies el cuerpo si contiene identificadores sensibles.

## 5. Exposición pública, TLS y red — 3 minutos

### 5.1 Data API y base de datos

- **Qué comprobar:** qué interfaces de Supabase están habilitadas y desde qué redes se llega a PostgreSQL.
- **Dónde exactamente:** Supabase Dashboard → **Settings → Data API**: revisa **Enable Data API** y **Exposed schemas**. Después **Database → Settings → Network Restrictions** y **Database → Settings → SSL Configuration**.
- **Resultado correcto:** Data API deshabilitada si no se necesita; si se necesita, solo schemas mínimos, con RLS/grants verificados. Restricciones de red permiten PostgreSQL/pooler solo desde rangos de operadores/backend aprobados. **Enforce SSL on incoming connections** está activado. Las API HTTP gestionadas por Supabase usan TLS.
- **Resultado problemático:** Data API habilitada con `public`/`mimic_ed` completos sin necesidad o controles; PostgreSQL/pooler accesible desde cualquier IP; SSL de base de datos no forzado; nadie conoce los rangos autorizados.
- **Gravedad si sale mal:** **Crítica** si una interfaz pública alcanza datos/RPC sin autorización efectiva; **Alta** por DB sin restricción de red o sin SSL forzado.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota `Data API sí/no`, schemas y `SSL sí/no`, sin endpoints.

### 5.2 Aplicación, proxy y terminación TLS

- **Qué comprobar:** si la aplicación es pública, dónde termina TLS, redirección HTTP, HSTS, puertos y bypass del reverse proxy.
- **Dónde exactamente:** desde una red no corporativa y sin iniciar sesión, sustituye solo en tu terminal el placeholder:

```powershell
curl.exe -sS -o NUL -w "HTTP=%{http_code} DESTINO=%{url_effective} TLS_VERIFY=%{ssl_verify_result}`n" http://TU_HOST_AQUI
curl.exe -sS -I https://TU_HOST_AQUI
Test-NetConnection TU_HOST_AQUI -Port 443
Test-NetConnection TU_HOST_AQUI -Port 5432
Test-NetConnection TU_HOST_AQUI -Port 6543
```

  En el panel del proveedor de despliegue, abre el servicio → **Networking/Domains** y **Access/IAM**; identifica balanceador/proxy, origen y allowlist. No guardes la salida si contiene IP o hostname real.
- **Resultado correcto:** acceso limitado a usuarios/red autorizados; HTTP redirige a HTTPS; certificado válido (`TLS_VERIFY=0`); HSTS presente; solo 443 es público; origen no accesible saltándose el proxy; 5432/6543 no son alcanzables desde Internet; existe propietario del proxy/WAF.
- **Resultado problemático:** login o aplicación accesible para cualquiera; HTTP sin redirección; error de certificado; ausencia de HSTS; puertos DB públicos; IP/puerto de origen accesible; topología o propietario desconocidos.
- **Gravedad si sale mal:** **Crítica** si el prototipo actual es público o hay bypass hasta datos/servicio; **Alta** para TLS/HSTS/topología incompleta.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — dibuja solo `Internet/VPN → proxy → app → Supabase`, sin direcciones.

## 6. Logs: acceso y retención — 2 minutos

### 6.1 Cobertura y plazo

- **Qué comprobar:** fuentes registradas, primer evento todavía consultable, exportación y plazo exigido por la política interna.
- **Dónde exactamente:** Supabase Dashboard → **Logs → Logs Explorer**; abre `auth_logs`, `edge_logs`/API y `postgres_logs`, ordena por fecha y anota la fecha más antigua sin copiar mensajes. Ve a **Project Settings → Log Drains**. Para Auth, ve a **Authentication → Configuration → Audit Logs** y revisa **Write audit logs to the database**. Confirma el plan en **Organization → Billing**.
- **Resultado correcto:** Auth/API/Postgres producen eventos suficientes para investigación; la retención observada cubre la política aprobada; si no, existe Log Drain a un archivo inmutable con retención/borrado definidos. La política distingue logs operativos, audit y contenido clínico. Como referencia, la retención nativa publicada es 1/7/28/90 días para Free/Pro/Team/Enterprise, sujeta al plan vigente.
- **Resultado problemático:** no hay eventos atribuibles; el plazo real es desconocido o menor al requerido; no existe exportación; logs desaparecen antes de poder investigar; se confunde log técnico con audit trail clínico.
- **Gravedad si sale mal:** **Alta**; **Crítica** si impide investigar accesos a PHI exigidos por la política aplicable.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota fuentes, días observados y destino del drain, nunca eventos.

### 6.2 Quién puede leer logs

- **Qué comprobar:** miembros de Supabase, despliegue y destino del Log Drain que pueden leer o exportar logs.
- **Dónde exactamente:** Supabase Dashboard → **Organization Settings → Team**; proveedor de despliegue → servicio → **Access/IAM**; destino del drain → **IAM/Access**.
- **Resultado correcto:** lista nominal, mínimo privilegio, MFA y revisión periódica; acceso a logs sensibles limitado a operaciones/seguridad; exportación y borrado auditables.
- **Resultado problemático:** Developer/Owner innecesarios, cuentas compartidas, exmiembros, enlaces públicos, destino sin cifrado o acceso no revisado. El código puede registrar previews de mensajes y SQL (`docs/architecture/INVENTORY.md:164-169`).
- **Gravedad si sale mal:** **Crítica** si logs con PHI/PII son accesibles de forma amplia; **Alta** en otro caso.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — registra roles y recuento, no identidades.

## 7. Ubicación y región — 1 minuto

### 7.1 Supabase y copias

- **Qué comprobar:** región primaria, réplicas, backups y destino de logs frente a la residencia aprobada.
- **Dónde exactamente:** Supabase Dashboard → **Project Settings → Infrastructure**; revisa región primaria y read replicas. Revisa **Database → Backups** y **Project Settings → Log Drains**. Contrasta DPA/contrato y región del destino externo.
- **Resultado correcto:** región específica aprobada para la clasificación de datos; todas las réplicas, backups y logs cumplen la misma decisión o una transferencia documentada. Una región general llamada “Europe” no se toma como prueba automática de residencia UE.
- **Resultado problemático:** región desconocida/general incompatible; réplica, backup o drain fuera de jurisdicción; región distinta de lo contratado. Cambiar la región primaria exige crear/migrar a otro proyecto, no un toggle.
- **Gravedad si sale mal:** **Alta**; **Crítica** si hay PHI/PII en una ubicación contractual o legalmente prohibida.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota país/región aprobada, no endpoint.

## 8. Política del proveedor Anthropic — 1 minuto

### 8.1 Deployment, retención, training y acuerdos

- **Qué comprobar:** que la clave desplegada pertenece a la organización/API comercial aprobada; retención efectiva, uso para entrenamiento, ubicación, DPA/BAA/ZDR y features excluidas.
- **Dónde exactamente:** gestor de secretos: confirma solo que `ANTHROPIC_API_KEY` está en producción; Anthropic Console → **Organization → Members/Settings** y **Usage** para vincular el consumo al contrato correcto; repositorio contractual interno → order form, DPA, BAA y acuerdo Zero Data Retention, si aplican.
- **Resultado correcto:** propietario y organización identificados; API comercial; no participación voluntaria en entrenamiento; retención y routing documentados; DPA vigente. Para PHI, BAA/ZDR y configuración/feature set expresamente cubiertos, además de aprobación de privacidad. Para datos demo/preparados, el uso coincide con el intended purpose y la clasificación registrada.
- **Resultado problemático:** cuenta/producto de consumo o propietario desconocido; contrato/retención/región sin confirmar; opt-in a entrenamiento; asumir ZDR sin acuerdo; enviar PHI con retención estándar o sin BAA. La política pública de API indica borrado estándar dentro de 30 días con excepciones, y almacenamiento por defecto en EE. UU.; no sustituyas el contrato propio por esa página.
- **Gravedad si sale mal:** **Crítica** si sale PHI/PII sin autorización contractual; **Alta** para datos preparados cuando la política sigue sin probarse.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — evidencia: IDs internos de contrato y decisión, nunca la clave.

## 9. Corpus y administración documental — 1 minuto

### 9.1 Corpus realmente indexado

- **Qué comprobar:** cada documento, responsable, licencia, versión, vigencia y aprobación del contenido desplegado.
- **Dónde exactamente:** Supabase Dashboard → **SQL Editor → New query**:

```sql
select
  document_id,
  filename,
  count(*) as chunks,
  min(metadata ->> 'version') as version,
  min(metadata ->> 'owner') as owner,
  min(metadata ->> 'approval_status') as approval_status,
  min(metadata ->> 'review_date') as review_date
from public.rag_chunks
group by document_id, filename
order by filename, document_id;
```

  Si algún campo no existe en metadata, el resultado nulo es evidencia de que no está gobernado; no abras el texto de los chunks. Contrasta la salida con el registro documental aprobado.
- **Resultado correcto:** correspondencia uno a uno con el registro; owner, licencia, versión, fecha de revisión/vigencia y aprobación actuales; corpus segregado por tenant cuando aplique; retirada definida.
- **Resultado problemático:** documento desconocido, vencido, sin licencia/owner/aprobación, duplicado o de otro tenant; metadata insuficiente; no existe registro externo autorizado.
- **Gravedad si sale mal:** **Crítica** si el corpus es compartido, clínico o cross-tenant; **Alta** para demo controlada.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — guarda inventario protegido; no lo adjuntes al repo si los nombres son sensibles.

### 9.2 Quién administra documentos y scripts

- **Qué comprobar:** qué usuario ordinario alcanza upload/borrado y quién puede ejecutar `scripts/index_guias.py` o `scripts/clear_rag.py`.
- **Dónde exactamente:** abre el despliegue con una cuenta autenticada sin rol administrativo y navega a gestión documental, sin subir ni borrar nada. En el host/repo desplegado ejecuta uno de estos comandos de solo lectura:

```powershell
Get-Acl .\scripts\index_guias.py
Get-Acl .\scripts\clear_rag.py
```

```bash
stat scripts/index_guias.py scripts/clear_rag.py
```

- **Resultado correcto:** un usuario ordinario no ve ni puede invocar upload/borrado; solo el rol `knowledge-manager` aprobado administra corpus; scripts disponibles únicamente a operadores nominales, con MFA/audit y procedimiento de cambio.
- **Resultado problemático:** cualquier autenticado gestiona documentos; seguridad basada solo en ocultar el botón; scripts accesibles a todo operador/desarrollador o comparten clave elevada sin audit.
- **Gravedad si sale mal:** **Crítica**.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota roles, no usuarios.

## 10. Caché, procesos y cierre — 1 minuto

### 10.1 Caché e instancias por entorno

- **Qué comprobar:** si el artefacto desplegado habilita la caché de respuestas y cuántos procesos/réplicas sirven usuarios.
- **Dónde exactamente:** en la copia exacta desplegada:

```powershell
rg -n "cache|cache_ttl" services\unified_chat\unified_agent.py
$n = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'streamlit' }).Count; "procesos_streamlit=$n"
```

```bash
rg -n 'cache|cache_ttl' services/unified_chat/unified_agent.py
printf 'procesos_streamlit='; pgrep -fc streamlit
```

  Confirma además el número deseado de réplicas en el control de scaling del proveedor. No guardes líneas de comando completas.
- **Resultado correcto:** caché deshabilitada para datos sensibles/uso compartido, o claveada y probada por tenant, usuario, paciente, sesión y autorización; número de procesos conocido; almacenamiento y borrado de caché documentados.
- **Resultado problemático:** estado desconocido; caché global activa con varios usuarios; clave sin contexto completo; varias réplicas con comportamiento no documentado. El baseline observado usa caché en proceso que puede contener información clínica (`docs/architecture/INVENTORY.md:164-169`).
- **Gravedad si sale mal:** **Crítica** en entorno compartido o con PHI/PII; **Alta** en demo controlada.
- **Marca:** `[ ] OK  [ ] PROBLEMA  [ ] NO VERIFICADO` — anota `cache sí/no/desconocida` y número de procesos.

### 10.2 Dictamen

Cuenta los resultados:

| Resultado | Número |
|---|---:|
| `OK` con evidencia |  |
| `PROBLEMA` crítico |  |
| `PROBLEMA` alto |  |
| `NO VERIFICADO` |  |

- Si existe un `PROBLEMA` **Crítico**, limita inmediatamente el entorno a operador único/red privada y datos demo preparados; no lo declares apto para uso hospitalario.
- Todo `NO VERIFICADO` permanece como incertidumbre y **no** se contabiliza como control.
- Un `OK` solo descuenta riesgo cuando la evidencia está fechada, vinculada al entorno y tiene propietario.
- Abre un riesgo/remediación por cada problema con: entorno, item, gravedad, contención, responsable, fecha y evidencia de revalidación. No incluyas secretos.

## Qué hacer si sale mal

### Contención inmediata

1. No borres evidencia ni hagas cambios simultáneos sin registro. Anota hora, entorno e item afectado.
2. Si la app pública, una clave elevada, RLS/RPC o PHI están implicados, restringe el acceso desde el panel del despliegue (privado/VPN/allowlist) o detén el servicio. No necesitas cambiar código para contener.
3. Si sospechas fuga, trata la clave como comprometida aunque no haya confirmación. Revisa **Logs → Logs Explorer**, **Organization Audit Logs** y el audit del proveedor de despliegue sin copiar eventos sensibles.
4. Asigna propietario de incidente y conserva solo evidencia redactada en el repositorio protegido.

### Rotación paso a paso de `SUPABASE_KEY`

Esta es la corrección más probable. Rotar no sustituye RLS, mínimo privilegio ni la separación de componentes.

1. **Clasifica la clave afectada.** En Supabase Dashboard → **Settings → API Keys**, identifica su etiqueta: `publishable`, `anon`, `secret` o `service_role`. No copies su valor a la incidencia.
2. **Localiza consumidores.** Revisa el gestor de secretos de cada despliegue, CI/CD, jobs y hosts locales para el nombre `SUPABASE_KEY`. Incluye Auth, acceso `mimic_ed`, RAG y scripts porque hoy comparten la variable. Anota ubicaciones, no valores.
3. **Cierra la causa antes de reemitir.** Retira acceso de la persona/sistema indebido, elimina el secreto de logs/artefactos y restringe el entorno. Si el secreto llegó a Git, la rotación es obligatoria; borrar el fichero del último commit no revoca la clave ni elimina el historial.
4. **Corrige RLS/grants/RPC primero.** Una nueva clave de bajo privilegio solo es segura si los items 3 y 4 pasan. Si la aplicación depende de una clave elevada para funcionar, mantén el servicio privado/parado: la arquitectura actual de clave única no permite separar de forma segura tareas de usuario y administración sin trabajo posterior de código.
5. **Crea la sustituta.** En **Settings → API Keys → API Keys**, crea una nueva clave del tipo mínimo necesario. Para el runtime compartido actual, el objetivo es bajo privilegio. Si un backend aislado necesita elevación, crea una `secret` distinta por componente; no la reutilices como `SUPABASE_KEY` común.
6. **Migra primero un entorno no productivo.** Copia la nueva clave directamente del panel al gestor de secretos usando el canal seguro del proveedor. Nunca uses chat, email, argumento CLI ni fichero versionado. Reinicia/redeploya el servicio.
7. **Prueba permitir y denegar.** Comprueba login/logout, lectura del propio perfil/sesión, rechazo de otra sesión/usuario, consulta clínica dentro y fuera de scope, búsqueda RAG y rechazo de administración documental. Una pantalla que “funciona” no basta: debe existir al menos una denegación comprobada por cada frontera.
8. **Actualiza producción.** Sustituye `SUPABASE_KEY` en el gestor de secretos de producción, reinicia todas las réplicas/jobs y verifica salud y logs. No dejes una réplica con la clave anterior.
9. **Confirma adopción.** En **Settings → API Keys**, usa **Last used** y los logs para confirmar uso de la nueva y ausencia de uso de la antigua en todos los consumidores.
10. **Revoca la anterior.** Para una clave moderna `secret`, elimínala solo cuando todos los consumidores migraron; la eliminación es irreversible. Para legacy `service_role`, migra a una nueva `secret` y desactiva la legacy desde **Settings → API Keys**. Para legacy `anon`, migra a `publishable` y desactívala cuando **Last used** confirme el corte.
11. **No rotes a ciegas el JWT secret legacy.** `anon`, `service_role` y tokens Auth legacy están acoplados. Si el **JWT signing secret** también se comprometió, sigue Supabase Dashboard → **Authentication → Signing Keys** y el procedimiento oficial de transición; planifica invalidación de sesiones y posible downtime. Desactiva las claves legacy antes de revocar ese secret.
12. **Cierra y revalida.** Busca uso de la clave anterior, registra fecha/actor/tipo de clave y repite esta checklist. Nunca registres el valor ni una captura que lo muestre.

### Otras correcciones por resultado

| Fallo | Acción inmediata | Cierre exigido |
|---|---|---|
| RLS/policy/grant | Retirar schema de Data API o revocar acceso; mantener app privada | Migration versionada, policies por operación y tests allow/deny por rol/contexto |
| RPC insegura | Revocar `EXECUTE` a `PUBLIC`, `anon` y roles no necesarios; deshabilitar ruta que dependa de ella | Firma versionada, invoker por defecto, scope/límites internos y tests negativos |
| Data API/red/TLS | Desactivar interfaz no usada, allowlist y forzar TLS | Repetir pruebas externas y guardar topología aprobada |
| Logs | Restringir IAM; activar fuente/drain sin registrar contenido clínico innecesario | Retención, redacción, inmutabilidad, acceso y borrado aprobados |
| Región/proveedor | Suspender PHI/PII y egress | DPA/BAA/ZDR/residencia aprobados o migración completada |
| Corpus/RAG | Suspender upload/borrado/retrieval compartido | Registro aprobado, RBAC knowledge-manager, tenant scope y retirada probada |
| Caché/procesos | Limitar a demo/usuario único o desactivar el entorno compartido | Scope completo de caché, borrado y pruebas cross-user/tenant |

## Referencias

- Internas: `docs/security/THREAT_MODEL.md:259-272`, `docs/architecture/INVENTORY.md:121-192`, `ROADMAP_HOSPITAL_READY/05-identity-authorization-multitenancy.md` y `ROADMAP_HOSPITAL_READY/06-privacy-phi-security.md`.
- Supabase: [API keys](https://supabase.com/docs/guides/getting-started/api-keys), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [seguridad de Data API](https://supabase.com/docs/guides/api/securing-your-api), [funciones y permisos](https://supabase.com/docs/guides/database/functions), [SSL](https://supabase.com/docs/guides/platform/ssl-enforcement), [restricciones de red](https://supabase.com/docs/guides/platform/network-restrictions), [logs](https://supabase.com/docs/guides/monitoring-and-debugging/logs), [Log Drains](https://supabase.com/docs/guides/monitoring-and-debugging/log-drains), [regiones](https://supabase.com/docs/guides/platform/regions) y [access control](https://supabase.com/docs/guides/platform/access-control).
- Anthropic: [retención comercial/API](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data), [ubicación de procesamiento/almacenamiento](https://privacy.claude.com/en/articles/7996890-where-are-your-servers-located-do-you-host-your-models-on-eu-servers), [Zero Data Retention](https://privacy.anthropic.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) y [BAA](https://privacy.anthropic.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers).
