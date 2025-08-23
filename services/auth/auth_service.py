
"""
Servicio de autenticación con Supabase para HCE Analyzer
"""
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
import hashlib
import uuid

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthService:
    """Servicio de autenticación y gestión de usuarios"""
    
    def __init__(self):
        self.supabase_client = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Inicializa el cliente de Supabase"""
        try:
            from config.config import SUPABASE_URL, SUPABASE_KEY
            
            if not SUPABASE_URL or not SUPABASE_KEY:
                logger.warning("Credenciales de Supabase no configuradas, usando modo simulado")
                self.supabase_client = None
                return
            
            # Importar y configurar Supabase
            from supabase import create_client
            
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Cliente Supabase inicializado correctamente")
            
        except ImportError:
            logger.warning("Supabase no disponible, usando modo simulado")
            self.supabase_client = None
        except Exception as e:
            logger.error(f"Error inicializando Supabase: {e}")
            self.supabase_client = None
    
    def login(self, email: str, password: str) -> Tuple[bool, Any]:
        """Autentica un usuario"""
        try:
            if self.supabase_client:
                return self._supabase_login(email, password)
            else:
                return self._simulated_login(email, password)
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False, "Error interno de autenticación"
    
    def _supabase_login(self, email: str, password: str) -> Tuple[bool, Any]:
        """Login usando Supabase"""
        try:
            # Autenticar con Supabase Auth
            response = self.supabase_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Obtener información adicional del usuario
                user_data = self.supabase_client.table('users').select('*').eq('id', response.user.id).execute()
                
                if user_data.data:
                    user_info = user_data.data[0]
                    user_info.update({
                        'id': response.user.id,
                        'email': response.user.email
                    })
                    return True, user_info
                else:
                    # Usuario autenticado pero sin datos adicionales
                    return True, {
                        'id': response.user.id,
                        'email': response.user.email,
                        'name': response.user.email.split('@')[0]
                    }
            else:
                return False, "Credenciales inválidas"
                
        except Exception as e:
            logger.error(f"Error en login Supabase: {e}")
            return False, "Error de autenticación"
    
    def _simulated_login(self, email: str, password: str) -> Tuple[bool, Any]:
        """Login simulado para desarrollo/demo"""
        # Usuarios de demo
        demo_users = {
            "demo@hospital.com": {
                "password": "demo123",
                "id": "demo-user-1",
                "name": "Dr. Demo",
                "specialty": "medicina_interna",
                "medical_license": "123456-7"
            },
            "admin@hce.com": {
                "password": "admin123",
                "id": "admin-user-1",
                "name": "Administrador",
                "specialty": "administracion",
                "medical_license": "ADMIN-001"
            }
        }
        
        if email in demo_users:
            user = demo_users[email]
            if password == user["password"]:
                user_info = user.copy()
                del user_info["password"]
                user_info["email"] = email
                return True, user_info
        
        return False, "Credenciales inválidas"
    
    def register(self, email: str, password: str, name: str, specialty: str = None, medical_license: str = None) -> Tuple[bool, str]:
        """Registra un nuevo usuario"""
        try:
            if self.supabase_client:
                return self._supabase_register(email, password, name, specialty, medical_license)
            else:
                return self._simulated_register(email, password, name, specialty, medical_license)
                
        except Exception as e:
            logger.error(f"Error en registro: {e}")
            return False, "Error interno de registro"
    
    def _supabase_register(self, email: str, password: str, name: str, specialty: str = None, medical_license: str = None) -> Tuple[bool, str]:
        """Registro usando Supabase"""
        try:
            # Registrar en Supabase Auth
            response = self.supabase_client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Crear registro en tabla de usuarios
                user_data = {
                    'id': response.user.id,
                    'email': email,
                    'name': name,
                    'specialty': specialty,
                    'medical_license': medical_license,
                    'created_at': datetime.now().isoformat()
                }
                
                result = self.supabase_client.table('users').insert(user_data).execute()
                
                if result.data:
                    return True, "Usuario registrado exitosamente"
                else:
                    return False, "Error creando perfil de usuario"
            else:
                return False, "Error en registro de autenticación"
                
        except Exception as e:
            logger.error(f"Error en registro Supabase: {e}")
            return False, "Error de registro"
    
    def _simulated_register(self, email: str, password: str, name: str, specialty: str = None, medical_license: str = None) -> Tuple[bool, str]:
        """Registro simulado para desarrollo/demo"""
        # En modo simulado, siempre permitimos el registro
        logger.info(f"Registro simulado para: {email}")
        return True, "Usuario registrado exitosamente (modo demo)"
    
    def logout(self):
        """Cierra sesión del usuario"""
        try:
            if self.supabase_client:
                self.supabase_client.auth.sign_out()
            logger.info("Logout completado")
        except Exception as e:
            logger.error(f"Error en logout: {e}")
    
    def create_chat_session(self, user_id: str, title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Crea una nueva sesión de chat"""
        try:
            if self.supabase_client:
                return self._supabase_create_session(user_id, title)
            else:
                return self._simulated_create_session(user_id, title)
                
        except Exception as e:
            logger.error(f"Error creando sesión: {e}")
            return False, None
    
    def _supabase_create_session(self, user_id: str, title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Crea sesión usando Supabase"""
        try:
            session_data = {
                'user_id': user_id,
                'title': title,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase_client.table('chat_sessions').insert(session_data).execute()
            
            if result.data:
                return True, result.data[0]
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"Error creando sesión Supabase: {e}")
            return False, None
    
    def _simulated_create_session(self, user_id: str, title: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Crea sesión simulada"""
        session = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': title,
            'created_at': datetime.now().isoformat()
        }
        return True, session
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene las sesiones de un usuario"""
        try:
            if self.supabase_client:
                return self._supabase_get_sessions(user_id, limit)
            else:
                return self._simulated_get_sessions(user_id, limit)
                
        except Exception as e:
            logger.error(f"Error obteniendo sesiones: {e}")
            return False, []
    
    def _supabase_get_sessions(self, user_id: str, limit: int) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene sesiones usando Supabase"""
        try:
            result = self.supabase_client.table('chat_sessions')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                return True, result.data
            else:
                return True, []
                
        except Exception as e:
            logger.error(f"Error obteniendo sesiones Supabase: {e}")
            return False, []
    
    def _simulated_get_sessions(self, user_id: str, limit: int) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene sesiones simuladas"""
        # Sesiones de ejemplo
        sessions = [
            {
                'id': 'session-1',
                'user_id': user_id,
                'title': 'Análisis de Hemograma',
                'created_at': datetime.now().isoformat()
            },
            {
                'id': 'session-2',
                'user_id': user_id,
                'title': 'Consulta sobre Hipertensión',
                'created_at': datetime.now().isoformat()
            }
        ]
        return True, sessions[:limit]
    
    def save_message(self, session_id: str, content: str, role: str) -> bool:
        """Guarda un mensaje en una sesión"""
        try:
            if self.supabase_client:
                return self._supabase_save_message(session_id, content, role)
            else:
                return self._simulated_save_message(session_id, content, role)
                
        except Exception as e:
            logger.error(f"Error guardando mensaje: {e}")
            return False
    
    def _supabase_save_message(self, session_id: str, content: str, role: str) -> bool:
        """Guarda mensaje usando Supabase"""
        try:
            message_data = {
                'session_id': session_id,
                'content': content,
                'role': role,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase_client.table('chat_messages').insert(message_data).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error guardando mensaje Supabase: {e}")
            return False
    
    def _simulated_save_message(self, session_id: str, content: str, role: str) -> bool:
        """Guarda mensaje simulado"""
        logger.info(f"Mensaje simulado guardado en sesión {session_id}: {role}")
        return True
    
    def get_session_messages(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene los mensajes de una sesión"""
        try:
            if self.supabase_client:
                return self._supabase_get_messages(session_id)
            else:
                return self._simulated_get_messages(session_id)
                
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return False, []
    
    def _supabase_get_messages(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene mensajes usando Supabase"""
        try:
            result = self.supabase_client.table('chat_messages')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at', desc=False)\
                .execute()
            
            if result.data:
                return True, result.data
            else:
                return True, []
                
        except Exception as e:
            logger.error(f"Error obteniendo mensajes Supabase: {e}")
            return False, []
    
    def _simulated_get_messages(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Obtiene mensajes simulados"""
        # Mensajes de ejemplo
        messages = []
        return True, messages
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Actualiza el perfil de un usuario"""
        try:
            if self.supabase_client:
                return self._supabase_update_profile(user_id, updates)
            else:
                return self._simulated_update_profile(user_id, updates)
                
        except Exception as e:
            logger.error(f"Error actualizando perfil: {e}")
            return False, "Error interno"
    
    def _supabase_update_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Actualiza perfil usando Supabase"""
        try:
            updates['updated_at'] = datetime.now().isoformat()
            
            result = self.supabase_client.table('users')\
                .update(updates)\
                .eq('id', user_id)\
                .execute()
            
            if result.data:
                return True, "Perfil actualizado correctamente"
            else:
                return False, "Error actualizando perfil"
                
        except Exception as e:
            logger.error(f"Error actualizando perfil Supabase: {e}")
            return False, "Error de base de datos"
    
    def _simulated_update_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Actualiza perfil simulado"""
        logger.info(f"Perfil simulado actualizado para usuario {user_id}")
        return True, "Perfil actualizado correctamente (modo demo)"

