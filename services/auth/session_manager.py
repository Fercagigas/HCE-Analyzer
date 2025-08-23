
"""
Gestor de sesiones y autenticación para HCE Analyzer
"""
import streamlit as st
from typing import Dict, Any, Tuple, Optional, List
import logging
from datetime import datetime
from services.auth.auth_service import AuthService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    """Gestor centralizado de sesiones y autenticación"""
    
    @staticmethod
    def init_session():
        """Inicializa el estado de sesión"""
        try:
            # Inicializar variables de sesión si no existen
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
            
            # Verificar sesión existente
            SessionManager._check_existing_session()
            
        except Exception as e:
            logger.error(f"Error inicializando sesión: {e}")
            st.error("Error inicializando la aplicación")
    
    @staticmethod
    def _check_existing_session():
        """Verifica si existe una sesión válida"""
        try:
            # Verificar si hay datos de usuario en session_state
            if st.session_state.get('user') and st.session_state.get('authenticated'):
                # Verificar que la sesión sigue siendo válida
                if SessionManager._validate_session():
                    logger.info(f"Sesión válida para usuario: {st.session_state.user.get('email')}")
                else:
                    SessionManager._clear_session()
            
        except Exception as e:
            logger.error(f"Error verificando sesión existente: {e}")
            SessionManager._clear_session()
    
    @staticmethod
    def _validate_session() -> bool:
        """Valida que la sesión actual sigue siendo válida"""
        try:
            # Aquí se podría verificar con Supabase si la sesión sigue activa
            # Por ahora, asumimos que es válida si existe
            return st.session_state.get('user') is not None
        except Exception as e:
            logger.error(f"Error validando sesión: {e}")
            return False
    
    @staticmethod
    def _clear_session():
        """Limpia el estado de sesión"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.current_session = None
        st.session_state.current_mode = 'welcome'
        logger.info("Sesión limpiada")
    
    @staticmethod
    def is_authenticated() -> bool:
        """Verifica si el usuario está autenticado"""
        return st.session_state.get('authenticated', False) and st.session_state.get('user') is not None
    
    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str]:
        """Inicia sesión de usuario"""
        try:
            if not email or not password:
                return False, "Email y contraseña son requeridos"
            
            # Intentar autenticación
            success, result = st.session_state.auth_service.login(email, password)
            
            if success:
                # Configurar estado de sesión
                st.session_state.authenticated = True
                st.session_state.user = result
                st.session_state.current_mode = 'welcome'
                
                logger.info(f"Login exitoso para: {email}")
                return True, "Login exitoso"
            else:
                logger.warning(f"Login fallido para: {email}")
                return False, result
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False, "Error interno en autenticación"
    
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
    def logout():
        """Cierra sesión del usuario"""
        try:
            user_email = st.session_state.get('user', {}).get('email', 'Usuario desconocido')
            
            # Cerrar sesión en el servicio de auth
            st.session_state.auth_service.logout()
            
            # Limpiar estado de sesión
            SessionManager._clear_session()
            
            logger.info(f"Logout exitoso para: {user_email}")
            
        except Exception as e:
            logger.error(f"Error en logout: {e}")
            # Limpiar sesión de todas formas
            SessionManager._clear_session()
    
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
    def save_message(session_id: str, content: str, role: str) -> bool:
        """Guarda un mensaje en la sesión actual"""
        try:
            if not SessionManager.is_authenticated():
                return False
            
            success = st.session_state.auth_service.save_message(session_id, content, role)
            
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
            return {'valid': False, 'reason': 'Error interno'}

