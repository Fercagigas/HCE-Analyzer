-- 0004_harden_security_definer_functions.sql
-- Endurece las funciones SECURITY DEFINER restantes senaladas por el Supabase
-- security advisor (lints 0011 function_search_path_mutable, 0028/0029
-- security_definer_function_executable).
--
-- Las cuatro funciones trigger (enforce_max_sessions, update_chat_session_timestamp,
-- update_session_on_message, update_updated_at_column) las invoca el motor como
-- owner al disparar el trigger; no necesitan EXECUTE para anon/authenticated/public
-- por RPC. version() es utilitaria y no debe exponerse por la API REST.
--
-- Aplicar en el SQL Editor de Supabase (rol postgres). Idempotente.

-- Fijar search_path en la unica funcion trigger que no lo tenia.
alter function public.enforce_max_sessions() set search_path = public, pg_temp;

-- Retirar EXECUTE de la superficie REST (PostgREST expone /rpc/<fn> a estos roles).
revoke all on function public.enforce_max_sessions() from public, anon, authenticated;
revoke all on function public.update_chat_session_timestamp() from public, anon, authenticated;
revoke all on function public.update_session_on_message() from public, anon, authenticated;
revoke all on function public.update_updated_at_column() from public, anon, authenticated;
revoke all on function public.version() from public, anon, authenticated;

-- Verificacion:
--   Los triggers siguen operativos (se disparan por el motor, no por rol).
--   El security advisor ya no reporta estas funciones como ejecutables por anon/authenticated.
