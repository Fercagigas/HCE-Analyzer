
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



