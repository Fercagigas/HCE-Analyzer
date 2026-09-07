-- 0003_drop_exec_sql.sql
-- Elimina la funcion public.exec_sql(text): SECURITY DEFINER que ejecutaba SQL
-- arbitrario (EXECUTE sql, no solo SELECT) y era ejecutable por anon/authenticated.
-- Segunda superficie de SQL libre en la base de datos, distinta de
-- execute_readonly_query (ADR 0050). El runtime no la invoca (0 referencias en el
-- codigo). Detectada por el Supabase security advisor.
--
-- Aplicar en el SQL Editor de Supabase (rol postgres). Idempotente.

revoke all on function public.exec_sql(text) from public, anon, authenticated, service_role;
drop function if exists public.exec_sql(text);

-- Verificacion (debe devolver 0 filas):
--   select proname from pg_proc where proname = 'exec_sql';
