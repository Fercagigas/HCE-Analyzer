import streamlit as st
from typing import Dict, Any, Tuple, Optional, List
import logging
from datetime import datetime, timedelta
from services.auth.auth_service import AuthService
import extra_streamlit_components as stx

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    """Gestor centralizado de sesiones y autenticación con cookies"""
    
    COOKIE_NAME = "hce_remember_me"
    COOKIE_EXPIRY_HOURS = 1

    @staticmethod
    def get_cookie_manager():
        return st.session_state.cookie_manager

    @staticmethod
    def init_session():
        """Inicializa el estado de sesión y el gestor de cookies"""
        try:
            if 'cookie_manager' not in st.session_state:
                st.session_state.cookie_manager = stx.CookieManager(key='cookie_manager_hce')

            if 'authenticated' not in st.session_state:
                st.session_state.authenticated = False
            
            if 'user' not in st.session_state:
                st.session_state.user = None
            
            if 'auth_service' not in st.session_state:
                st.session_state.auth_service = AuthService()
            
            if 'current_session' not in st.session_state:
                st.session_state.current_session = None
            
            if 'current_mode' not in st.session_state:
                st.session_state.current_mode = 'welcome'
            
            SessionManager._check_existing_session()
            
        except Exception as e:
            logger.error(f"Error inicializando sesión: {e}")
            st.error("Error inicializando la aplicación")
    
    @staticmethod
    def _check_existing_session():
        """Verifica si existe una sesión válida en el estado o en las cookies"""
        try:
            if SessionManager.is_authenticated():
                # Don't refresh cookie on every check to avoid duplicate key errors
                return

            cookie_manager = SessionManager.get_cookie_manager()
            remember_me_cookie = cookie_manager.get(SessionManager.COOKIE_NAME)
            if remember_me_cookie:
                st.session_state.authenticated = True
                st.session_state.user = remember_me_cookie
                st.session_state.current_mode = 'welcome'
                logger.info(f"Sesión restaurada desde cookie para: {remember_me_cookie.get('email')}")
                
                # Cargar preferencias del usuario al restaurar sesión
                user_id = remember_me_cookie.get('id')
                if user_id:
                    SessionManager._load_user_preferences(user_id)
            
        except Exception as e:
            # Log at debug level to avoid cluttering logs with cookie errors
            logger.debug(f"Error verificando sesión existente: {e}")
            # Don't clear session on cookie errors, just continue without cookies

    @staticmethod
    def _refresh_cookie():
        """Refresca la cookie de sesión para extender su duración"""
        try:
            if SessionManager.is_authenticated():
                cookie_manager = SessionManager.get_cookie_manager()
                cookie_manager.set(
                    SessionManager.COOKIE_NAME,
                    st.session_state.user,
                    expires_at=datetime.now() + timedelta(hours=SessionManager.COOKIE_EXPIRY_HOURS)
                )
        except Exception as e:
            # Silently fail on cookie refresh errors to avoid breaking the app
            logger.debug(f"Error refrescando cookie: {e}")

    @staticmethod
    def _clear_session():
        """Limpia el estado de sesión y la cookie"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.current_session = None
        st.session_state.current_mode = 'welcome'
        try:
            cookie_manager = SessionManager.get_cookie_manager()
            cookie_manager.delete(SessionManager.COOKIE_NAME)
        except Exception as e:
            logger.debug(f"Error eliminando cookie: {e}")
        logger.info("Sesión limpiada")
    
    @staticmethod
    def is_authenticated() -> bool:
        """Verifica si el usuario está autenticado"""
        return st.session_state.get('authenticated', False) and st.session_state.get('user') is not None
    
    @staticmethod
    def login(email: str, password: str, remember_me: bool = False) -> Tuple[bool, str]:
        """Inicia sesión de usuario y opcionalmente guarda una cookie"""
        try:
            if not email or not password:
                return False, "Email y contraseña son requeridos"
            
            success, result = st.session_state.auth_service.login(email, password)
            
            if success:
                st.session_state.authenticated = True
                st.session_state.user = result
                st.session_state.current_mode = 'welcome'
                
                # Cargar preferencias del usuario desde Supabase
                SessionManager._load_user_preferences(result.get('id'))
                
                if remember_me:
                    SessionManager._refresh_cookie()

                logger.info(f"Login exitoso para: {email}")
                return True, "Login exitoso"
            else:
                logger.warning(f"Login fallido para: {email}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False, "Error interno en autenticación"
    
    @staticmethod
    def logout():
        """Cierra sesión del usuario y limpia la cookie"""
        try:
            user_email = st.session_state.get('user', {}).get('email', 'Usuario desconocido')
            st.session_state.auth_service.logout()
            SessionManager._clear_session()
            logger.info(f"Logout exitoso para: {user_email}")
            
        except Exception as e:
            logger.error(f"Error en logout: {e}")
            SessionManager._clear_session()

    # ... (el resto de los métodos de la clase se mantienen igual)
    @staticmethod
    def register(email: str, password: str, name: str, specialty: str = None, medical_license: str = None) -> Tuple[bool, str]:
        """Registra un nuevo usuario"""
        try:
            if not all([email, password, name]):
                return False, "Email, contraseña y nombre son requeridos"
            
            # Intentar registro
            success, result = st.session_state.auth_service.register(
                email=email,
                password=password,
                name=name,
                specialty=specialty,
                medical_license=medical_license
            )
            
            if success:
                logger.info(f"Registro exitoso para: {email}")
                return True, "Usuario registrado exitosamente"
            else:
                logger.warning(f"Registro fallido para: {email}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error en registro: {e}")
            return False, "Error interno en registro"
            
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Obtiene información del usuario actual"""
        if SessionManager.is_authenticated():
            return st.session_state.user
        return None
    
    @staticmethod
    def create_chat_session(title: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Crea una nueva sesión de chat"""
        try:
            if not SessionManager.is_authenticated():
                return False, None
            
            user_id = st.session_state.user['id']
            
            # Generar título si no se proporciona
            if not title:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                title = f"Sesión {timestamp}"
            
            # Crear sesión
            success, session = st.session_state.auth_service.create_chat_session(user_id, title)
            
            if success:
                logger.info(f"Sesión creada: {session['id']} para usuario: {user_id}")
                return True, session
            else:
                logger.error(f"Error creando sesión para usuario: {user_id}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error creando sesión de chat: {e}")
            return False, None
    
    @staticmethod
    def get_user_sessions(limit: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene las sesiones del usuario actual"""
        try:
            if not SessionManager.is_authenticated():
                return False, []
            
            user_id = st.session_state.user['id']
            
            success, sessions = st.session_state.auth_service.get_user_sessions(user_id, limit)
            
            if success:
                return True, sessions
            else:
                logger.error(f"Error obteniendo sesiones para usuario: {user_id}")
                return False, []
                
        except Exception as e:
            logger.error(f"Error obteniendo sesiones: {e}")
            return False, []
    
    @staticmethod
    def save_message(session_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Guarda un mensaje en la sesión actual
        
        Args:
            session_id: ID de la sesión
            content: Contenido del mensaje (texto)
            role: 'user' o 'assistant'
            metadata: Opcional - Dict con tools_used, sources, execution_time_ms, has_visualization
        """
        try:
            if not SessionManager.is_authenticated():
                return False
            
            success = st.session_state.auth_service.save_message(session_id, content, role, metadata)
            
            if success:
                logger.info(f"Mensaje guardado en sesión: {session_id}")
                return True
            else:
                logger.error(f"Error guardando mensaje en sesión: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error guardando mensaje: {e}")
            return False
    
    @staticmethod
    def get_session_messages(session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene los mensajes de una sesión"""
        try:
            if not SessionManager.is_authenticated():
                return False, []
            
            success, messages = st.session_state.auth_service.get_session_messages(session_id)
            
            if success:
                return True, messages
            else:
                logger.error(f"Error obteniendo mensajes de sesión: {session_id}")
                return False, []
                
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return False, []
    
    @staticmethod
    def update_user_profile(updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Actualiza el perfil del usuario"""
        try:
            if not SessionManager.is_authenticated():
                return False, "Usuario no autenticado"
            
            user_id = st.session_state.user['id']
            
            success, result = st.session_state.auth_service.update_user_profile(user_id, updates)
            
            if success:
                # Actualizar información en session_state
                st.session_state.user.update(updates)
                logger.info(f"Perfil actualizado para usuario: {user_id}")
                return True, "Perfil actualizado correctamente"
            else:
                logger.error(f"Error actualizando perfil para usuario: {user_id}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error actualizando perfil: {e}")
            return False, "Error interno actualizando perfil"
    
    @staticmethod
    def get_user_stats() -> Dict[str, Any]:
        """Obtiene estadísticas del usuario actual"""
        try:
            if not SessionManager.is_authenticated():
                return {}
            
            user_id = st.session_state.user['id']
            
            # Obtener estadísticas básicas
            success, sessions = SessionManager.get_user_sessions(limit=100)
            
            stats = {
                'total_sessions': len(sessions) if success else 0,
                'last_login': datetime.now().isoformat(),
                'analyses_today': 0,  # Se calcularía desde la base de datos
                'rag_queries_today': 0,  # Se calcularía desde la base de datos
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    @staticmethod
    def check_session_limits() -> Dict[str, Any]:
        """Verifica los límites de la sesión actual"""
        try:
            if not SessionManager.is_authenticated():
                return {'valid': False, 'reason': 'No autenticado'}
            
            # Verificar límites de tiempo, uso, etc.
            # Por ahora, retornamos que la sesión es válida
            return {
                'valid': True,
                'analyses_remaining': 15,  # Se calcularía desde la base de datos
                'rag_queries_remaining': 50,  # Se calcularía desde la base de datos
                'session_expires_at': None  # Se calcularía basado en la configuración
            }
            
        except Exception as e:
            logger.error(f"Error verificando límites de sesión: {e}")
            return {'valid': False, 'reason': 'Error interno'}    @staticmethod
    def _load_user_preferences(user_id: str) -> None:
        """
        Carga las preferencias del usuario desde Supabase y las guarda en session_state.

        Args:
            user_id: ID del usuario
        """
        try:
            from services.supabase_services import UserPreferencesService
            prefs_service = UserPreferencesService()
            success, preferences = prefs_service.get_preferences(user_id)

            if success:
                st.session_state.unified_config = preferences
                st.session_state.user_preferences_service = prefs_service
                logger.info(f"Preferencias cargadas para usuario: {user_id}")
            else:
                logger.warning("No se pudieron cargar preferencias, usando defaults")
        except Exception as e:
            logger.warning(f"Error cargando preferencias: {e}")

    @staticmethod
    def save_user_preferences(preferences: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Guarda las preferencias del usuario en Supabase.

        Args:
            preferences: Dict con las preferencias a guardar

        Returns:
            Tuple (success, mensaje)
        """
        try:
            if not SessionManager.is_authenticated():
                return False, "No autenticado"

            user_id = st.session_state.user.get('id')
            if not user_id:
                return False, "ID de usuario no disponible"

            prefs_service = st.session_state.get('user_preferences_service')
            if not prefs_service:
                from services.supabase_services import UserPreferencesService
                prefs_service = UserPreferencesService()

            return prefs_service.save_preferences(user_id, preferences)
        except Exception as e:
            logger.error(f"Error guardando preferencias: {e}")
            return False, str(e)
