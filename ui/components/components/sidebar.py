"""
Componente de barra lateral para ChatHCE
Versión simplificada - Solo funcionalidades esenciales
"""
import streamlit as st
from datetime import datetime
from services.auth.session_manager import SessionManager


def show_sidebar():
    """Muestra la barra lateral simplificada"""
    with st.sidebar:
        # Información del usuario
        show_user_info()
        
        st.divider()
        
        # Navegación principal
        show_navigation()
        
        st.divider()
        
        # Sesiones recientes (solo si ya está en modo chat)
        if st.session_state.get('current_mode') == 'unified_chat':
            show_recent_sessions()
            st.divider()
        
        # Cerrar sesión
        if SessionManager.is_authenticated():
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                st.session_state.show_logout_confirmation = True
                st.rerun()


def show_user_info():
    """Muestra información del usuario autenticado"""
    if not SessionManager.is_authenticated():
        return
    
    user = st.session_state.get('user')
    if not user or not isinstance(user, dict):
        return
    
    display_name = user.get('name', user.get('email', 'Usuario'))
    specialty = user.get('specialty', 'Urgencias')
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1rem; border-radius: 10px;'>
            <div style='text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>👨‍⚕️</div>
                <h4 style='margin: 0; color: white;'>{display_name}</h4>
                <p style='margin: 0; opacity: 0.8; font-size: 0.9em;'>{specialty}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Mostrar estadísticas del usuario
    try:
        auth_service = st.session_state.get('auth_service')
        if auth_service and user.get('id'):
            stats = auth_service.get_user_stats(user['id'])
            if stats and not stats.get('error'):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💬", f"{stats.get('total_sessions', 0)}/3", help="Conversaciones")
                with col2:
                    st.metric("📝", stats.get('total_messages', 0), help="Mensajes totales")

            # Mostrar estadísticas de análisis
            try:
                from services.supabase_services import AnalysisService
                analysis_service = AnalysisService()
                analysis_stats = analysis_service.get_analysis_stats(user['id'])
                if not analysis_stats.get('error'):
                    total_analyses = analysis_stats.get('total_analyses', 0)
                    if total_analyses > 0:
                        st.metric("🔬", total_analyses, help="Análisis realizados")
            except Exception:
                pass  # Silently fail on analysis stats error
    except Exception:
        pass  # Silently fail on stats error


def show_navigation():
    """Muestra opciones de navegación principal"""
    st.subheader("🧭 Navegación")
    
    # Chat Unificado - Nuevo chat
    if st.button("💬 Nuevo Chat", use_container_width=True, type="primary"):
        success, session = SessionManager.create_chat_session("Chat Unificado")
        if success:
            # Limpiar mensajes anteriores
            st.session_state.unified_messages = []
            st.session_state.current_session = session
            st.session_state.current_mode = "unified_chat"
            st.rerun()
        else:
            st.error("Error al crear nueva conversación")
    
    st.caption("Chat con acceso a MIMIC-IV-ED y documentos")


def show_recent_sessions():
    """Muestra sesiones recientes del usuario (máximo 3)"""
    st.subheader("🕒 Mis Conversaciones")
    st.caption("Máximo 3 conversaciones guardadas")
    
    if not SessionManager.is_authenticated():
        st.info("Inicia sesión para ver tus sesiones")
        return
    
    user = st.session_state.get('user')
    if not user or not isinstance(user, dict) or 'id' not in user:
        st.info("Inicia sesión para ver tus sesiones")
        return
    
    try:
        auth_service = st.session_state.get('auth_service')
        if not auth_service:
            st.warning("Servicio de autenticación no disponible")
            return
        
        success, sessions = auth_service.get_user_sessions(
            user['id'],
            limit=3  # Máximo 3 sesiones
        )
        
        if success and sessions:
            for session in sessions:
                # Usar updated_at si existe, sino created_at
                timestamp_str = session.get('updated_at') or session.get('created_at')
                if timestamp_str:
                    last_activity = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    time_ago = _get_time_ago(last_activity)
                else:
                    time_ago = "fecha desconocida"
                
                session_title = session['title'][:20] + "..." if len(session['title']) > 20 else session['title']
                
                # Verificar si es la sesión actual
                is_current = st.session_state.get('current_session', {}).get('id') == session['id']
                
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    button_type = "primary" if is_current else "secondary"
                    if st.button(
                        f"{'▶️' if is_current else '📝'} {session_title}",
                        help=f"Última actividad: {time_ago}",
                        use_container_width=True,
                        key=f"session_{session['id']}",
                        type=button_type
                    ):
                        # Limpiar mensajes actuales y cargar la sesión seleccionada
                        st.session_state.unified_messages = []
                        st.session_state.current_session = session
                        st.session_state.current_mode = "unified_chat"
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{session['id']}", help="Eliminar conversación"):
                        _delete_session(session['id'])
                
            # Mostrar contador
            st.caption(f"📊 {len(sessions)}/3 conversaciones")
        else:
            st.info("No hay conversaciones guardadas")
            st.caption("Inicia un nuevo chat para comenzar")
            
    except Exception as e:
        st.error(f"Error cargando sesiones: {str(e)}")


def _delete_session(session_id: str):
    """Elimina una sesión de chat"""
    try:
        if not SessionManager.is_authenticated():
            return
        
        user_id = st.session_state.user['id']
        success, msg = st.session_state.auth_service.delete_chat_session(session_id, user_id)
        
        if success:
            # Si era la sesión actual, limpiar
            if st.session_state.get('current_session', {}).get('id') == session_id:
                st.session_state.current_session = None
                st.session_state.unified_messages = []
                st.session_state.current_mode = 'welcome'
            st.success("Conversación eliminada")
            st.rerun()
        else:
            st.error(msg)
    except Exception as e:
        st.error(f"Error: {str(e)}")


def _get_time_ago(dt: datetime) -> str:
    """Calcula tiempo transcurrido desde una fecha"""
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    
    if diff.days > 0:
        return f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"hace {hours} hora{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        return "hace unos momentos"
