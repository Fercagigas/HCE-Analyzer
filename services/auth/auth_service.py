
"""
Servicio de autenticación con Supabase para HCE Analyzer
Toda la autenticación se gestiona a través de Supabase Auth
"""
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
import uuid
from services.connection_pool_manager import connection_pool_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthService:
    """
    Servicio de autenticación y gestión de usuarios con Supabase.
    
    Toda la autenticación se realiza a través de Supabase Auth.
    Los datos de usuario se almacenan en la tabla 'users' del esquema public.
    """
    
    def __init__(self):
        self.supabase_client = None
        self._use_connection_pool = True
        self._is_initialized = False
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Inicializa el cliente de Supabase para autenticación"""
        try:
            from config.config import SUPABASE_URL, SUPABASE_KEY
            
            if not SUPABASE_URL or not SUPABASE_KEY:
                logger.error("❌ Credenciales de Supabase no configuradas")
                logger.error("Configure SUPABASE_URL y SUPABASE_KEY en el archivo .env")
                self._is_initialized = False
                return
            
            # Crear cliente directo para autenticación (Auth no funciona con pool)
            from supabase import create_client
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Verificar conexión
            try:
                # Test simple query
                self.supabase_client.table('users').select('id').limit(1).execute()
                self._is_initialized = True
                logger.info("✅ AuthService inicializado con Supabase Auth")
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a Supabase: {conn_error}")
                self._is_initialized = False
            
        except ImportError as e:
            logger.error(f"❌ Supabase no instalado: {e}")
            logger.error("Ejecute: pip install supabase")
            self._is_initialized = False
        except Exception as e:
            logger.error(f"❌ Error inicializando Supabase: {e}")
            self._is_initialized = False
    
    def is_available(self) -> bool:
        """Verifica si el servicio de autenticación está disponible"""
        return self._is_initialized and self.supabase_client is not None
    
    def login(self, email: str, password: str) -> Tuple[bool, Any]:
        """
        Autentica un usuario con Supabase Auth
        
        Args:
            email: Correo electrónico del usuario
            password: Contraseña
            
        Returns:
            Tuple (success, user_info o mensaje de error)
        """
        if not self.is_available():
            return False, "Servicio de autenticación no disponible. Verifique la configuración de Supabase."
        
        try:
            # Autenticar con Supabase Auth
            response = self.supabase_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Obtener información adicional del usuario desde tabla users
                user_data = self.supabase_client.table('users')\
                    .select('*')\
                    .eq('id', response.user.id)\
                    .execute()
                
                if user_data.data:
                    user_info = user_data.data[0]
                    user_info.update({
                        'id': response.user.id,
                        'email': response.user.email,
                        'auth_token': response.session.access_token if response.session else None
                    })
                else:
                    # Usuario autenticado pero sin perfil - crear perfil básico
                    user_info = self._create_user_profile(response.user)
                
                # Actualizar last_login
                self._update_last_login(response.user.id)
                
                logger.info(f"✅ Login exitoso para: {email}")
                return True, user_info
            else:
                logger.warning(f"❌ Login fallido para: {email}")
                return False, "Credenciales inválidas"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error en login: {error_msg}")
            
            # Mensajes de error más amigables
            if "Invalid login credentials" in error_msg:
                return False, "Correo o contraseña incorrectos"
            elif "Email not confirmed" in error_msg:
                return False, "Por favor confirma tu correo electrónico antes de iniciar sesión"
            elif "Too many requests" in error_msg:
                return False, "Demasiados intentos. Espera unos minutos e intenta de nuevo"
            else:
                return False, "Error de autenticación. Intenta de nuevo más tarde"
    
    def _create_user_profile(self, auth_user) -> Dict[str, Any]:
        """Crea un perfil de usuario si no existe"""
        try:
            user_data = {
                'id': auth_user.id,
                'auth_id': auth_user.id,
                'email': auth_user.email,
                'name': auth_user.email.split('@')[0],
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase_client.table('users').insert(user_data).execute()
            
            if result.data:
                logger.info(f"✅ Perfil creado para usuario: {auth_user.email}")
                return result.data[0]
            else:
                return user_data
                
        except Exception as e:
            logger.warning(f"No se pudo crear perfil automático: {e}")
            return {
                'id': auth_user.id,
                'email': auth_user.email,
                'name': auth_user.email.split('@')[0]
            }
    
    def _update_last_login(self, user_id: str) -> None:
        """Actualiza el timestamp de último login del usuario"""
        try:
            self.supabase_client.table('users')\
                .update({'last_login': datetime.now().isoformat()})\
                .eq('id', user_id)\
                .execute()
            logger.debug(f"Last login actualizado para usuario {user_id}")
        except Exception as e:
            logger.warning(f"No se pudo actualizar last_login: {e}")
    
    def register(self, email: str, password: str, name: str, specialty: str = None, medical_license: str = None) -> Tuple[bool, str]:
        """
        Registra un nuevo usuario con Supabase Auth
        
        Args:
            email: Correo electrónico
            password: Contraseña (mínimo 6 caracteres)
            name: Nombre completo
            specialty: Especialidad médica (opcional)
            medical_license: Número de colegiatura (opcional)
            
        Returns:
            Tuple (success, mensaje)
        """
        if not self.is_available():
            return False, "Servicio de autenticación no disponible. Verifique la configuración de Supabase."
        
        try:
            # Validaciones básicas
            if len(password) < 6:
                return False, "La contraseña debe tener al menos 6 caracteres"
            
            if not email or '@' not in email:
                return False, "Correo electrónico inválido"
            
            # Registrar en Supabase Auth
            response = self.supabase_client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "specialty": specialty
                    }
                }
            })
            
            if response.user:
                # Crear registro en tabla de usuarios
                user_data = {
                    'id': response.user.id,
                    'auth_id': response.user.id,
                    'email': email,
                    'name': name,
                    'specialty': specialty,
                    'medical_license': medical_license,
                    'is_active': True,
                    'created_at': datetime.now().isoformat()
                }
                
                result = self.supabase_client.table('users').insert(user_data).execute()
                
                if result.data:
                    logger.info(f"✅ Usuario registrado: {email}")
                    
                    # Verificar si requiere confirmación de email
                    if response.user.confirmed_at is None:
                        return True, "Usuario registrado. Por favor revisa tu correo para confirmar tu cuenta."
                    else:
                        return True, "Usuario registrado exitosamente. Ya puedes iniciar sesión."
                else:
                    logger.warning(f"Usuario auth creado pero sin perfil: {email}")
                    return True, "Usuario registrado. Por favor revisa tu correo para confirmar tu cuenta."
            else:
                return False, "Error en el registro. Intenta de nuevo."
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error en registro: {error_msg}")
            
            # Mensajes de error más amigables
            if "User already registered" in error_msg:
                return False, "Este correo ya está registrado. Intenta iniciar sesión."
            elif "Password should be at least" in error_msg:
                return False, "La contraseña debe tener al menos 6 caracteres"
            elif "Unable to validate email" in error_msg:
                return False, "Correo electrónico inválido"
            else:
                return False, "Error en el registro. Intenta de nuevo más tarde."
    
    def logout(self):
        """Cierra sesión del usuario en Supabase Auth"""
        try:
            if self.supabase_client:
                self.supabase_client.auth.sign_out()
                logger.info("✅ Logout completado")
        except Exception as e:
            logger.error(f"Error en logout: {e}")
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Obtiene el usuario actualmente autenticado"""
        try:
            if not self.supabase_client:
                return None
            
            user = self.supabase_client.auth.get_user()
            if user and user.user:
                return {
                    'id': user.user.id,
                    'email': user.user.email
                }
            return None
        except Exception as e:
            logger.debug(f"No hay usuario autenticado: {e}")
            return None
    
    def refresh_session(self) -> bool:
        """Refresca la sesión del usuario si está por expirar"""
        try:
            if not self.supabase_client:
                return False
            
            session = self.supabase_client.auth.get_session()
            if session:
                self.supabase_client.auth.refresh_session()
                return True
            return False
        except Exception as e:
            logger.debug(f"No se pudo refrescar sesión: {e}")
            return False
    
    def reset_password(self, email: str) -> Tuple[bool, str]:
        """
        Envía un correo para restablecer la contraseña
        
        Args:
            email: Correo electrónico del usuario
            
        Returns:
            Tuple (success, mensaje)
        """
        if not self.is_available():
            return False, "Servicio no disponible"
        
        try:
            self.supabase_client.auth.reset_password_email(email)
            logger.info(f"✅ Email de recuperación enviado a: {email}")
            return True, "Se ha enviado un correo con instrucciones para restablecer tu contraseña"
        except Exception as e:
            logger.error(f"Error enviando email de recuperación: {e}")
            return False, "Error enviando el correo. Verifica que el email sea correcto."
    
    def create_chat_session(self, user_id: str, title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Crea una nueva sesión de chat en Supabase
        
        Args:
            user_id: ID del usuario
            title: Título de la sesión
            
        Returns:
            Tuple (success, session_data)
        """
        if not self.is_available():
            logger.error("Supabase no disponible para crear sesión")
            return False, None
        
        try:
            session_data = {
                'user_id': user_id,
                'title': title,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # El trigger enforce_max_sessions eliminará la sesión más antigua si hay 3+
            result = self.supabase_client.table('chat_sessions').insert(session_data).execute()
            
            if result.data:
                logger.info(f"✅ Sesión creada: {result.data[0]['id']}")
                return True, result.data[0]
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Error creando sesión: {e}")
            return False, None
    
    def get_user_sessions(self, user_id: str, limit: int = 3) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Obtiene las sesiones del usuario ordenadas por última actividad
        
        Args:
            user_id: ID del usuario
            limit: Máximo de sesiones (default 3)
            
        Returns:
            Tuple (success, lista de sesiones)
        """
        if not self.is_available():
            return False, []
        
        try:
            # Máximo 3 sesiones por usuario
            effective_limit = min(limit, 3)
            
            result = self.supabase_client.table('chat_sessions')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('updated_at', desc=True)\
                .limit(effective_limit)\
                .execute()
            
            return True, result.data if result.data else []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo sesiones: {e}")
            return False, []
    
    def save_message(self, session_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Guarda un mensaje en una sesión de Supabase
        
        Args:
            session_id: ID de la sesión
            content: Contenido del mensaje (texto, sin imágenes)
            role: 'user' o 'assistant'
            metadata: Opcional - Dict con tools_used, sources, execution_time_ms, has_visualization
            
        Returns:
            True si se guardó correctamente
        """
        if not self.is_available():
            logger.warning("Supabase no disponible para guardar mensaje")
            return False
        
        try:
            # Preparar metadata (sin imágenes)
            safe_metadata = {}
            if metadata:
                allowed_keys = ['tools_used', 'sources', 'execution_time_ms', 'has_visualization', 'model_used']
                for key in allowed_keys:
                    if key in metadata:
                        safe_metadata[key] = metadata[key]
            
            message_data = {
                'session_id': session_id,
                'content': content,
                'role': role,
                'metadata': safe_metadata,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase_client.table('chat_messages').insert(message_data).execute()
            
            # El trigger actualizará automáticamente updated_at en chat_sessions
            if result.data:
                logger.debug(f"Mensaje guardado en sesión {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error guardando mensaje: {e}")
            return False
    
    def get_session_messages(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Obtiene los mensajes de una sesión incluyendo metadata
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Tuple (success, lista de mensajes)
        """
        if not self.is_available():
            return False, []
        
        try:
            result = self.supabase_client.table('chat_messages')\
                .select('id, session_id, content, role, metadata, created_at')\
                .eq('session_id', session_id)\
                .order('created_at', desc=False)\
                .execute()
            
            return True, result.data if result.data else []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes: {e}")
            return False, []
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Actualiza el perfil de un usuario en Supabase
        
        Args:
            user_id: ID del usuario
            updates: Campos a actualizar
            
        Returns:
            Tuple (success, mensaje)
        """
        if not self.is_available():
            return False, "Servicio no disponible"
        
        try:
            updates['updated_at'] = datetime.now().isoformat()
            
            result = self.supabase_client.table('users')\
                .update(updates)\
                .eq('id', user_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Perfil actualizado para usuario {user_id}")
                return True, "Perfil actualizado correctamente"
            else:
                return False, "Error actualizando perfil"
                
        except Exception as e:
            logger.error(f"❌ Error actualizando perfil: {e}")
            return False, "Error de base de datos"


    def delete_chat_session(self, session_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Elimina una sesión de chat y todos sus mensajes
        
        Args:
            session_id: ID de la sesión a eliminar
            user_id: ID del usuario (para verificación de propiedad)
            
        Returns:
            Tuple (success, message)
        """
        if not self.is_available():
            return False, "Servicio no disponible"
        
        try:
            # Verificar que la sesión pertenece al usuario
            check = self.supabase_client.table('chat_sessions')\
                .select('id')\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not check.data:
                return False, "Sesión no encontrada o no autorizado"
            
            # Eliminar sesión (mensajes se eliminan en cascada por FK)
            result = self.supabase_client.table('chat_sessions')\
                .delete()\
                .eq('id', session_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Sesión {session_id} eliminada")
                return True, "Sesión eliminada correctamente"
            else:
                return False, "Error al eliminar sesión"
                
        except Exception as e:
            logger.error(f"❌ Error eliminando sesión: {e}")
            return False, "Error de base de datos"
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas del usuario desde Supabase
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con estadísticas: total_sessions, total_messages, last_activity
        """
        if not self.is_available():
            return {'total_sessions': 0, 'total_messages': 0, 'last_activity': None, 'error': 'Servicio no disponible'}
        
        try:
            # Contar sesiones
            sessions = self.supabase_client.table('chat_sessions')\
                .select('id, updated_at')\
                .eq('user_id', user_id)\
                .execute()
            
            total_sessions = len(sessions.data) if sessions.data else 0
            
            # Obtener última actividad
            last_activity = None
            if sessions.data:
                timestamps = [s.get('updated_at') for s in sessions.data if s.get('updated_at')]
                if timestamps:
                    last_activity = max(timestamps)
            
            # Contar mensajes totales
            total_messages = 0
            if sessions.data:
                for session in sessions.data:
                    msgs = self.supabase_client.table('chat_messages')\
                        .select('id', count='exact')\
                        .eq('session_id', session['id'])\
                        .execute()
                    total_messages += msgs.count if hasattr(msgs, 'count') and msgs.count else len(msgs.data or [])
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'last_activity': last_activity,
                'max_sessions': 3
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'total_sessions': 0, 'total_messages': 0, 'last_activity': None, 'error': str(e)}
    
    def update_session_title(self, session_id: str, user_id: str, new_title: str) -> Tuple[bool, str]:
        """
        Actualiza el título de una sesión de chat
        
        Args:
            session_id: ID de la sesión
            user_id: ID del usuario (para verificación)
            new_title: Nuevo título
            
        Returns:
            Tuple (success, message)
        """
        if not self.is_available():
            return False, "Servicio no disponible"
        
        try:
            result = self.supabase_client.table('chat_sessions')\
                .update({'title': new_title, 'updated_at': datetime.now().isoformat()})\
                .eq('id', session_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if result.data:
                return True, "Título actualizado correctamente"
            else:
                return False, "Sesión no encontrada o no autorizado"
                
        except Exception as e:
            logger.error(f"❌ Error actualizando título: {e}")
            return False, "Error de base de datos"
