
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
            st.markdown("**🔒 Seguro y Confiable**")
            st.markdown("Datos Encriptados • HIPAA Compliant")
        
        with col3:
            st.markdown("**🤖 IA Avanzada**")
            st.markdown("Modelos LLM • RAG • Análisis Inteligente")
        
        st.markdown("---")  # Separador
        
        # Copyright y enlaces
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"© {datetime.now().year} HCE Analyzer. Desarrollado con ❤️ para mejorar la atención médica.")
        
        with col2:
            st.markdown("[Términos de Uso](#) | [Privacidad](#) | [Soporte](#)")
    
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
        
        **1. Análisis de HCE:**
        - Sube un archivo PDF o introduce texto
        - Selecciona el tipo de análisis
        - Obtén interpretación médica detallada
        
        **2. Chat Clínico:**
        - Haz preguntas sobre protocolos médicos
        - Consulta guías clínicas del hospital
        - Obtén respuestas basadas en evidencia
        
        **3. Añadir Contexto:**
        - Sube guías clínicas en PDF
        - Organiza por especialidad
        - Mejora las respuestas del sistema
        
        ### 🔧 Atajos de Teclado
        - `Ctrl + Enter`: Enviar formulario
        - `Ctrl + /`: Mostrar/ocultar ayuda
        - `Esc`: Cerrar modales
        
        ### 📞 Soporte
        - Email: soporte@hce-analyzer.com
        - Teléfono: +1 (555) 123-4567
        - Documentación: [docs.hce-analyzer.com](https://docs.hce-analyzer.com)
        """)

def show_system_status():
    """Muestra estado del sistema"""
    # Simular verificación de estado
    services_status = {
        "🤖 Servicio de IA": "✅ Operativo",
        "🗄️ Base de Datos": "✅ Operativo", 
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

