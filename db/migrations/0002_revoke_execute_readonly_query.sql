-- 0002_revoke_execute_readonly_query.sql
-- Retira la RPC que ejecutaba SQL libre generado por el modelo (riesgo AI-04/AI-08,
-- ADR 0050). Debe aplicarse despues de que el runtime deje de invocarla (WP4).
--
-- Aplicar en el SQL Editor de Supabase (rol postgres). Idempotente.

revoke all on function public.execute_readonly_query(text) from public, anon, authenticated, service_role;
drop function if exists public.execute_readonly_query(text);

-- Verificacion (debe devolver 0 filas):
--   select proname from pg_proc where proname = 'execute_readonly_query';
