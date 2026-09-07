# ADR 0130 - RLS por usuario y clave clinica readonly

Estado: Aceptada

Fecha: 2026-09-07

## Contexto

Fase 1 comprobaba el scope de paciente en `ScopeGuard`, pero la persistencia de producto usaba una clave compartida y una clave elevada puede ignorar RLS. Las conversaciones, analisis y preferencias contienen datos sensibles. El acceso MIMIC necesita una credencial separada y sin escritura.

## Opciones consideradas

1. Mantener filtros de `user_id` solo en adapters. Descartada: un fallo, endpoint futuro o clave elevada puede omitirlos.
2. Usar una `service_role` para producto y confiar en `ScopeGuard`. Descartada: evita RLS por definicion.
3. Reenviar JWT de usuario con clave publishable y RLS por ownership; asignar paciente explicitamente; rol clinico `clinical_readonly` (elegida).
4. RLS clinico por usuario directamente sobre las tablas MIMIC. Descartada ahora: el provider clinico dedicado no lleva identidad asistencial y el modelo de relaciones usuario-paciente aun no esta integrado en todos los flujos. `user_patient_access` deja el punto de control preparado.
5. Clave clinica `service_role` marcada como solo lectura por convencion. Descartada: no evita escrituras ni permite verificar privilegios.

## Decision

La migracion 0004 fuerza RLS y reemplaza policies permisivas en datos de producto. Los adapters de conversaciones, analisis y preferencias resuelven un cliente por `RequestContext` con su Bearer JWT; no existe fallback a `service_key`. La migracion crea `user_patient_access` para concesiones explícitas. El provider MIMIC usa `SUPABASE_CLINICAL_KEY` y ejecuta `clinical_key_is_readonly_v1`; si no verifica solo lectura, falla cerrado.

## Consecuencias

Mejora el aislamiento en base de datos y limita el impacto de un bug de aplicación. El owner debe aplicar la migracion, emitir/rotar una credencial con rol `clinical_readonly`, conceder pacientes y proporcionar `SUPABASE_ANON_KEY`. El corpus RAG queda legible solo por usuarios autenticados; su ownership por tenant y el rol `knowledge-manager` siguen siendo trabajo posterior. Las rutas legacy que no pasan por los adapters Fase 1 no adquieren esta garantia.
