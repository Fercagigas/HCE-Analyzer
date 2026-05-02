# Actualización del Esquema de Base de Datos - ChatHCE

## Fecha: Febrero 2026

## Estado: ✅ COMPLETADO

La base de datos Supabase está completamente configurada con:
- ✅ Autenticación integrada con Supabase Auth
- ✅ RLS (Row Level Security) habilitado en todas las tablas
- ✅ Políticas RLS para cada operación CRUD
- ✅ Triggers para límite de 3 sesiones por usuario
- ✅ Cascade delete para mensajes al eliminar sesiones

## Resumen de Cambios

Se actualizó el esquema `public` de Supabase y se integró completamente la autenticación con Supabase Auth.

## Autenticación con Supabase Auth

**Toda la autenticación se gestiona a través de Supabase Auth:**

- Login con email/password
- Registro de nuevos usuarios
- Recuperación de contraseña por email
- Tokens JWT automáticos
- Sesiones seguras

### Flujo de Autenticación

1. **Registro**: Usuario se registra → Supabase Auth crea cuenta → Se crea perfil en `public.users`
2. **Login**: Usuario inicia sesión → Supabase Auth valida → Se actualiza `last_login`
3. **Logout**: Se cierra sesión en Supabase Auth
4. **Recuperación**: Usuario solicita reset → Supabase envía email con enlace

### Configuración Requerida

Variables de entorno en `.env`:
```
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key
```

## Tablas Actualizadas

### 1. `users`
Nuevos campos:
- `auth_id` (UUID): Vincula con `auth.users` de Supabase Auth
- `last_login` (TIMESTAMPTZ): Último inicio de sesión
- `is_active` (BOOLEAN): Estado del usuario (soft delete)

### 2. `chat_sessions`
Nuevos campos:
- `updated_at` (TIMESTAMPTZ): Se actualiza automáticamente con cada mensaje

Triggers:
- `trigger_update_chat_session_timestamp`: Actualiza `updated_at` en UPDATE
- `trigger_enforce_max_sessions`: Limita a 3 sesiones por usuario (elimina la más antigua)

### 3. `chat_messages`
Nuevos campos:
- `metadata` (JSONB): Almacena información adicional del mensaje

Estructura de metadata:
```json
{
  "tools_used": ["database", "rag", "visualization"],
  "sources": [{"title": "...", "url": "..."}],
  "execution_time_ms": 1234,
  "has_visualization": true,
  "model_used": "claude-haiku-4-5-20251001"
}
```

**IMPORTANTE**: No se almacenan imágenes, solo referencias.

Triggers:
- `trigger_update_session_on_message`: Actualiza `updated_at` de la sesión al insertar mensaje

## Tablas Eliminadas

- `user_sessions`: Redundante con Supabase Auth sessions

## Límite de Conversaciones

Cada usuario puede tener **máximo 3 conversaciones**. Cuando se crea una nueva y ya existen 3, se elimina automáticamente la más antigua (junto con sus mensajes).

## Integración con el Backend

### Archivos Modificados

1. **`services/auth/auth_service.py`**
   - `save_message()` ahora acepta `metadata` opcional
   - `_supabase_login()` actualiza `last_login`
   - `_supabase_register()` incluye `auth_id` e `is_active`
   - `get_user_sessions()` ordena por `updated_at` y limita a 3
   - Nuevos métodos: `delete_chat_session()`, `get_user_stats()`, `update_session_title()`

2. **`services/auth/session_manager.py`**
   - `save_message()` actualizado para pasar metadata

3. **`ui/unified_chat_interface.py`**
   - `_save_to_database()` guarda metadata (tools_used, sources, etc.)
   - `_load_conversation_history()` carga metadata y reconstruye respuestas

4. **`ui/components/components/sidebar.py`**
   - Muestra máximo 3 conversaciones
   - Permite eliminar conversaciones
   - Muestra última actividad (updated_at)
   - Muestra estadísticas del usuario

5. **`src/core/app.py`**
   - Limpia mensajes al crear nueva sesión

## Flujo de Datos

### Crear Nueva Conversación
1. Usuario hace clic en "Nuevo Chat"
2. Se crea sesión en `chat_sessions`
3. Si ya hay 3 sesiones, trigger elimina la más antigua
4. Se limpian mensajes en memoria
5. Se muestra chat vacío

### Enviar Mensaje
1. Usuario escribe mensaje
2. Se guarda en `chat_messages` con role='user'
3. Agente procesa y responde
4. Se guarda respuesta con role='assistant' y metadata
5. Trigger actualiza `updated_at` de la sesión

### Cargar Conversación Existente
1. Usuario selecciona conversación del sidebar
2. Se cargan mensajes de `chat_messages`
3. Se reconstruye estructura con metadata
4. Se muestra historial completo

## Índices Creados

- `idx_users_auth_id`: Búsqueda por auth_id
- `idx_users_active`: Usuarios activos
- `idx_chat_sessions_user_updated`: Sesiones por usuario ordenadas por actividad
- `idx_chat_messages_session_created`: Mensajes por sesión ordenados
- `idx_chat_messages_metadata_tools`: Búsqueda por herramientas usadas

## Migraciones Aplicadas

1. `add_metadata_to_chat_messages`
2. `enhance_users_table`
3. `add_updated_at_to_chat_sessions`
4. `add_cascade_delete_to_chat_messages`
5. `create_max_sessions_enforcement`
6. `update_session_on_new_message`
7. `drop_redundant_user_sessions_table`
8. `fix_function_search_paths`
9. `add_missing_rls_policies` - Políticas RLS faltantes
10. `fix_remaining_function_search_paths` - Seguridad en funciones restantes
11. `fix_fk_to_public_users` - FK de analyses y user_preferences a public.users

## Políticas RLS Configuradas

### users
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Users can view own profile | `auth.uid() = id` |
| INSERT | Users can insert own profile | `auth.uid() = id` |
| UPDATE | Users can update own profile | `auth.uid() = id` |

### chat_sessions
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Users can view own chat sessions | `auth.uid() = user_id` |
| INSERT | Users can create own chat sessions | `auth.uid() = user_id` |
| UPDATE | Users can update own chat sessions | `auth.uid() = user_id` |
| DELETE | Users can delete own chat sessions | `auth.uid() = user_id` |

### chat_messages
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Users can view messages from own sessions | Verifica propiedad de sesión |
| INSERT | Users can create messages in own sessions | Verifica propiedad de sesión |
| DELETE | Users can delete messages from own sessions | Verifica propiedad de sesión |

### clinical_documents
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Anyone can view clinical documents | `true` |
| SELECT | Authenticated users can view | `auth.role() = 'authenticated'` |

### user_preferences
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Users can view own preferences | `auth.uid() = user_id` |
| INSERT | Users can insert own preferences | `auth.uid() = user_id` |
| UPDATE | Users can update own preferences | `auth.uid() = user_id` |

### analyses
| Operación | Política | Condición |
|-----------|----------|-----------|
| SELECT | Users can view own analyses | `auth.uid() = user_id` |
| INSERT | Users can create own analyses | `auth.uid() = user_id` |

## Uso en Backend

### Guardar mensaje con metadata
```python
auth_service.save_message(
    session_id="uuid",
    content="Respuesta del asistente",
    role="assistant",
    metadata={
        "tools_used": ["database", "rag"],
        "sources": [{"title": "Guía clínica", "url": "..."}],
        "execution_time_ms": 1500,
        "has_visualization": False
    }
)
```

### Obtener sesiones (ordenadas por última actividad)
```python
success, sessions = auth_service.get_user_sessions(user_id, limit=3)
# Retorna máximo 3 sesiones, ordenadas por updated_at DESC
```

### Eliminar sesión
```python
success, msg = auth_service.delete_chat_session(session_id, user_id)
# Los mensajes se eliminan automáticamente (CASCADE)
```

### Estadísticas del usuario
```python
stats = auth_service.get_user_stats(user_id)
# {total_sessions, total_messages, last_activity, max_sessions}
```
