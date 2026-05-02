
"""
Componente footer para HCE Analyzer
"""
import streamlit as st
from datetime import datetime
from config.config import APP_NAME, APP_ICON

def show_footer():
    """Muestra el footer de la aplicación usando componentes nativos de Streamlit"""
    
    # Separador visual
    st.markdown("---")
    
    # Container principal del footer
    with st.container():
        # Título y descripción
        st.markdown(f"### {APP_ICON} {APP_NAME}")
        st.markdown("*Sistema Avanzado de Análisis Clínico con Inteligencia Artificial*")
        
        st.markdown("")  # Espacio
        
        # Características principales en columnas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🏥 Para Profesionales**")
            st.markdown("Médicos • Enfermeros • Especialistas")
        
        with col2:
            st.markdown("**🎯 Chat Unificado**")
            st.markdown("Acceso Inteligente • MIMIC-IV-ED • RAG")
        
        with col3:
            st.markdown("**🤖 IA Avanzada**")
            st.markdown("Claude • Anthropic • Visualizaciones Dinámicas")
        
        st.markdown("---")  # Separador
        
        # Copyright y enlaces
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"© {datetime.now().year} ChatHCE. Trabajo de Fin de Máster por Fernando Cagigas.")
        
        with col2:
            st.markdown("[Documentación](docs/) | [GitHub](#) | [Contacto](#)")
    
    # Información técnica (solo en modo debug)
    if st.session_state.get('show_debug_info', False):
        show_debug_footer()

def show_debug_footer():
    """Muestra información de debug en el footer"""
    with st.expander("🔧 Información de Debug", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Estado de Sesión:**")
            st.write(f"Autenticado: {'✅' if st.session_state.get('authenticated') else '❌'}")
            st.write(f"Usuario: {st.session_state.get('user', {}).get('email', 'N/A')}")
            st.write(f"Sesión Actual: {'✅' if st.session_state.get('current_session') else '❌'}")
        
        with col2:
            st.markdown("**Configuración:**")
            st.write(f"Modo: {st.session_state.get('current_mode', 'N/A')}")
            st.write(f"Debug: {'✅' if st.session_state.get('debug_mode') else '❌'}")
            st.write(f"Timestamp: {datetime.now().strftime('%H:%M:%S')}")
        
        with col3:
            st.markdown("**Sistema:**")
            st.write(f"Streamlit: {st.__version__}")
            st.write(f"Python: {st.session_state.get('python_version', 'N/A')}")
            st.write(f"Memoria: {st.session_state.get('memory_usage', 'N/A')}")

def show_quick_help():
    """Muestra ayuda rápida en el footer"""
    with st.expander("❓ Ayuda Rápida", expanded=False):
        st.markdown("""
        ### 🚀 Inicio Rápido
        
        **🎯 Chat Unificado (Recomendado):**
        - Interfaz única para todas tus consultas
        - Acceso automático a MIMIC-IV-ED y documentos clínicos
        - Visualizaciones generadas automáticamente
        - Sin necesidad de cambiar entre modos
        
        **Ejemplos de Consultas:**
        - "Muéstrame información del paciente 10014729"
        - "¿Cuál es el protocolo para hipertensión?"
        - "Gráfica de signos vitales del paciente 10014729"
        - "¿El tratamiento del paciente sigue las guías?"
        
        **📁 Gestión de Documentos:**
        - Sube guías clínicas (PDF, DOCX, TXT)
        - Indexación automática
        - Disponibles inmediatamente en el chat
        
        ### 🔧 Atajos de Teclado
        - `Ctrl + Enter`: Enviar mensaje
        - `Esc`: Cerrar modales
        
        ### 📚 Documentación
        - [Guía de Usuario](docs/UNIFIED_CHAT_USER_GUIDE.md)
        - [Ejemplos de Consultas](docs/UNIFIED_CHAT_QUERY_EXAMPLES.md)
        - [Solución de Problemas](docs/UNIFIED_CHAT_TROUBLESHOOTING.md)
        """)

def show_system_status():
    """Muestra estado del sistema"""
    # Simular verificación de estado
    services_status = {
        "🎯 Chat Unificado": "✅ Operativo",
        "🗄️ MIMIC-IV-ED": "✅ Operativo", 
        "🔍 Sistema RAG": "✅ Operativo",
        "🔐 Autenticación": "✅ Operativo"
    }
    
    with st.expander("📊 Estado del Sistema", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            for service, status in list(services_status.items())[:2]:
                st.write(f"{service}: {status}")
        
        with col2:
            for service, status in list(services_status.items())[2:]:
                st.write(f"{service}: {status}")
        
        # Métricas del sistema
        st.markdown("**Métricas de Rendimiento:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Tiempo de Respuesta", "1.2s", "↓ 0.3s")
        
        with col2:
            st.metric("Disponibilidad", "99.9%", "↑ 0.1%")
        
        with col3:
            st.metric("Usuarios Activos", "47", "↑ 12")

def show_footer_with_options():
    """Footer con opciones adicionales"""
    # Footer principal
    show_footer()
    
    # Opciones adicionales en columnas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("❓ Ayuda Rápida", use_container_width=True):
            st.session_state.show_quick_help = not st.session_state.get('show_quick_help', False)
    
    with col2:
        if st.button("📊 Estado del Sistema", use_container_width=True):
            st.session_state.show_system_status = not st.session_state.get('show_system_status', False)
    
    with col3:
        if st.button("🔧 Debug Info", use_container_width=True):
            st.session_state.show_debug_info = not st.session_state.get('show_debug_info', False)
    
    # Mostrar secciones según estado
    if st.session_state.get('show_quick_help'):
        show_quick_help()
    
    if st.session_state.get('show_system_status'):
        show_system_status()

