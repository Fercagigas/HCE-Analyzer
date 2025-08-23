
"""
Componente de barra lateral para HCE Analyzer
"""
import streamlit as st
from datetime import datetime
from services.auth.session_manager import SessionManager
from config.config import APP_NAME, APP_ICON, MEDICAL_SPECIALTIES

def show_sidebar():
    """Muestra la barra lateral con navegación y opciones"""
    with st.sidebar:
        # Header de la barra lateral
        st.markdown(f"""
            <div style='text-align: center; padding: 1rem 0; border-bottom: 1px solid #e0e0e0; margin-bottom: 1rem;'>
                <h2>{APP_ICON} {APP_NAME}</h2>
                <p style='color: #666; font-size: 0.9em;'>Análisis Clínico Inteligente</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Información del usuario
        show_user_info()
        
        st.divider()
        
        # Navegación principal
        show_navigation()
        
        st.divider()
        
        # Sesiones recientes
        show_recent_sessions()
        
        st.divider()
        
        # Estadísticas rápidas
        show_quick_stats()
        
        st.divider()
        
        # Configuraciones y ayuda
        show_settings_and_help()

def show_user_info():
    """Muestra información del usuario autenticado"""
    if not SessionManager.is_authenticated():
        return
    
    user = st.session_state.user
    display_name = user.get('name', user.get('email', 'Usuario'))
    specialty = user.get('specialty', 'General')
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
            <div style='text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>👨‍⚕️</div>
                <h4 style='margin: 0; color: white;'>{display_name}</h4>
                <p style='margin: 0; opacity: 0.8; font-size: 0.9em;'>{specialty}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón de perfil
    if st.button("👤 Ver Perfil", use_container_width=True):
        st.session_state.current_mode = "profile"
        st.rerun()

def show_navigation():
    """Muestra opciones de navegación principal"""
    st.subheader("🧭 Navegación")
    
    # Botón de inicio
    if st.button("🏠 Inicio", use_container_width=True):
        st.session_state.current_mode = "welcome"
        if 'current_session' in st.session_state:
            del st.session_state.current_session
        st.rerun()
    
    # Análisis de HCE
    if st.button("📊 Análisis de HCE", use_container_width=True):
        success, session = SessionManager.create_chat_session("Análisis HCE")
        if success:
            st.session_state.current_session = session
            st.session_state.current_mode = "analysis"
            st.rerun()
    
    # Chat Clínico
    if st.button("💬 Chat Clínico", use_container_width=True):
        success, session = SessionManager.create_chat_session("Consulta Clínica")
        if success:
            st.session_state.current_session = session
            st.session_state.current_mode = "clinical_chat"
            st.rerun()
    
    # Gestión de Documentos
    if st.button("📚 Añadir Contexto", use_container_width=True):
        st.session_state.current_mode = "document_manager"
        st.rerun()

def show_recent_sessions():
    """Muestra sesiones recientes del usuario"""
    st.subheader("🕒 Sesiones Recientes")
    
    if not SessionManager.is_authenticated():
        st.info("Inicia sesión para ver tus sesiones")
        return
    
    try:
        # Obtener sesiones recientes
        success, sessions = st.session_state.auth_service.get_user_sessions(
            st.session_state.user['id'],
            limit=5
        )
        
        if success and sessions:
            for session in sessions:
                # Formatear fecha
                created_at = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                time_ago = _get_time_ago(created_at)
                
                # Botón de sesión
                session_title = session['title'][:25] + "..." if len(session['title']) > 25 else session['title']
                
                if st.button(
                    f"📝 {session_title}",
                    help=f"Creada {time_ago}",
                    use_container_width=True,
                    key=f"session_{session['id']}"
                ):
                    st.session_state.current_session = session
                    # Determinar modo basado en el título
                    if "Análisis" in session['title']:
                        st.session_state.current_mode = "analysis"
                    elif "Consulta" in session['title'] or "Chat" in session['title']:
                        st.session_state.current_mode = "clinical_chat"
                    else:
                        st.session_state.current_mode = "analysis"
                    st.rerun()
        else:
            st.info("No hay sesiones recientes")
            
    except Exception as e:
        st.error("Error cargando sesiones")

def show_quick_stats():
    """Muestra estadísticas rápidas del usuario"""
    st.subheader("📈 Estadísticas")
    
    if not SessionManager.is_authenticated():
        return
    
    # Estadísticas simuladas (en producción vendrían de la base de datos)
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Análisis", "47", "↗️ +3")
        st.metric("Documentos", "8", "→ 0")
    
    with col2:
        st.metric("Consultas", "128", "↗️ +12")
        st.metric("Tiempo", "24h", "↗️ +2h")
    
    # Progreso del día
    st.markdown("**Uso Diario**")
    progress_value = 0.6  # 60% del límite diario usado
    st.progress(progress_value)
    st.caption(f"9/15 análisis diarios utilizados")

def show_settings_and_help():
    """Muestra configuraciones y ayuda"""
    st.subheader("⚙️ Configuración")
    
    # Configuraciones rápidas
    if st.checkbox("🌙 Modo Oscuro", key="dark_mode"):
        # Implementar cambio de tema
        pass
    
    if st.checkbox("🔔 Notificaciones", value=True, key="notifications"):
        # Implementar configuración de notificaciones
        pass
    
    # Especialidad actual
    current_specialty = st.selectbox(
        "🏥 Especialidad",
        list(MEDICAL_SPECIALTIES.keys()),
        format_func=lambda x: MEDICAL_SPECIALTIES[x]["name"],
        key="user_specialty"
    )
    
    st.divider()
    
    # Ayuda y soporte
    st.subheader("❓ Ayuda")
    
    if st.button("📖 Guía de Uso", use_container_width=True):
        st.session_state.show_help = True
        st.rerun()
    
    if st.button("🐛 Reportar Error", use_container_width=True):
        st.session_state.show_bug_report = True
        st.rerun()
    
    if st.button("💬 Contacto", use_container_width=True):
        st.session_state.show_contact = True
        st.rerun()
    
    st.divider()
    
    # Cerrar sesión
    if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        st.session_state.show_logout_confirmation = True
        st.rerun()

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

def show_help_modal():
    """Muestra modal de ayuda"""
    if st.session_state.get('show_help'):
        st.markdown("""
            ### 📖 Guía de Uso - HCE Analyzer
            
            **🏠 Inicio**
            - Desde aquí puedes acceder a todas las funcionalidades
            - Crea nuevas sesiones de análisis o consulta
            
            **📊 Análisis de HCE**
            - Sube archivos PDF de historias clínicas
            - Obtén análisis detallados con IA
            - Guarda y revisa análisis anteriores
            
            **💬 Chat Clínico**
            - Consulta guías clínicas del hospital
            - Haz preguntas sobre protocolos médicos
            - Obtén respuestas basadas en evidencia
            
            **📚 Añadir Contexto**
            - Sube guías clínicas y protocolos
            - Organiza documentos por especialidad
            - Mejora las respuestas del sistema
            
            **⚙️ Configuración**
            - Personaliza tu experiencia
            - Configura notificaciones
            - Actualiza tu perfil profesional
        """)
        
        if st.button("✅ Entendido"):
            st.session_state.show_help = False
            st.rerun()

def show_bug_report_modal():
    """Muestra modal para reportar errores"""
    if st.session_state.get('show_bug_report'):
        st.markdown("### 🐛 Reportar Error")
        
        with st.form("bug_report_form"):
            error_type = st.selectbox(
                "Tipo de Error",
                ["Error de Funcionalidad", "Error de Interfaz", "Error de Rendimiento", "Otro"]
            )
            
            description = st.text_area(
                "Descripción del Error",
                placeholder="Describe detalladamente el error que encontraste..."
            )
            
            steps = st.text_area(
                "Pasos para Reproducir",
                placeholder="1. Hice clic en...\n2. Luego...\n3. El error ocurrió cuando..."
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("📤 Enviar Reporte"):
                    st.success("✅ Reporte enviado. ¡Gracias por tu ayuda!")
                    st.session_state.show_bug_report = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state.show_bug_report = False
                    st.rerun()

def show_contact_modal():
    """Muestra modal de contacto"""
    if st.session_state.get('show_contact'):
        st.markdown("""
            ### 💬 Contacto y Soporte
            
            **📧 Email de Soporte**
            soporte@hce-analyzer.com
            
            **📞 Teléfono**
            +1 (555) 123-4567
            
            **🕒 Horario de Atención**
            Lunes a Viernes: 8:00 AM - 6:00 PM
            Sábados: 9:00 AM - 2:00 PM
            
            **🌐 Recursos Adicionales**
            - [Documentación Técnica](https://docs.hce-analyzer.com)
            - [Videos Tutoriales](https://tutorials.hce-analyzer.com)
            - [FAQ](https://faq.hce-analyzer.com)
            
            **🚨 Emergencias Técnicas**
            Para problemas críticos que afecten la atención médica,
            contacta inmediatamente al: +1 (555) 911-TECH
        """)
        
        if st.button("✅ Cerrar"):
            st.session_state.show_contact = False
            st.rerun()

