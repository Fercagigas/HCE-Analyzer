
import streamlit as st
import os
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="HCE Analyzer - Análisis Clínico Inteligente",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importaciones locales
from services.auth.session_manager import SessionManager
from ui.components.components.auth_pages import show_login_page
from ui.components.components.sidebar import show_sidebar
from ui.components.components.analysis_form import show_analysis_form
from services.clinical_chat import show_clinical_chat
from ui.components.components.document_manager import show_document_manager
from ui.components.components.footer import show_footer
from config.config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON

# Inicializar estado de sesión
SessionManager.init_session()

# Estilos CSS personalizados
st.markdown("""
    <style>
        /* Ocultar elementos de formulario de Streamlit */
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }
        
        /* Estilos personalizados */
        .main-header {
            text-align: center;
            padding: 2rem;
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .feature-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        
        .welcome-container {
            text-align: center;
            padding: 3rem;
        }
        
        .user-greeting {
            text-align: right;
            padding: 1rem;
            color: #1e88e5;
            font-size: 1.1em;
            font-weight: 500;
        }
    </style>
""", unsafe_allow_html=True)

def show_welcome_screen():
    """Pantalla de bienvenida con opciones principales"""
    st.markdown(f"""
        <div class="main-header">
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style='font-size: 1.2em; opacity: 0.9;'>{APP_TAGLINE}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Opciones principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="feature-card">
                <h3>📊 Análisis de HCE</h3>
                <p>Analiza historias clínicas y reportes médicos con IA avanzada</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🆕 Nueva Sesión de Análisis", use_container_width=True, type="primary"):
            success, session = SessionManager.create_chat_session("Análisis HCE")
            if success:
                st.session_state.current_session = session
                st.session_state.current_mode = "analysis"
                st.rerun()
            else:
                st.error("Error al crear la sesión")
    
    with col2:
        st.markdown("""
            <div class="feature-card">
                <h3>💬 Consultas Clínicas</h3>
                <p>Consulta guías clínicas y protocolos hospitalarios</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 Chat Clínico", use_container_width=True, type="secondary"):
            success, session = SessionManager.create_chat_session("Consulta Clínica")
            if success:
                st.session_state.current_session = session
                st.session_state.current_mode = "clinical_chat"
                st.rerun()
            else:
                st.error("Error al crear la sesión")
    
    with col3:
        st.markdown("""
            <div class="feature-card">
                <h3>📚 Gestión de Documentos</h3>
                <p>Añade y gestiona guías clínicas y protocolos</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("📁 Añadir Contexto", use_container_width=True):
            st.session_state.current_mode = "document_manager"
            st.rerun()

def show_chat_history():
    """Muestra el historial de chat de la sesión actual"""
    if not st.session_state.get('current_session'):
        return
        
    success, messages = st.session_state.auth_service.get_session_messages(
        st.session_state.current_session['id']
    )
    
    if success and messages:
        for msg in messages:
            if msg['role'] == 'user':
                with st.chat_message("user"):
                    st.write(msg['content'])
            elif msg['role'] == 'assistant':
                with st.chat_message("assistant"):
                    st.write(msg['content'])

def show_user_greeting():
    """Muestra saludo personalizado al usuario"""
    if st.session_state.user:
        display_name = st.session_state.user.get('name') or st.session_state.user.get('email', '')
        st.markdown(f"""
            <div class="user-greeting">
                👋 Hola, {display_name}
            </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal de la aplicación"""
    SessionManager.init_session()

    # Verificar autenticación
    if not SessionManager.is_authenticated():
        show_login_page()
        show_footer()
        return

    # Mostrar saludo del usuario
    show_user_greeting()
    
    # Mostrar barra lateral
    show_sidebar()

    # Contenido principal basado en el modo actual
    current_mode = st.session_state.get('current_mode', 'welcome')
    
    if current_mode == 'welcome' or not st.session_state.get('current_session'):
        show_welcome_screen()
    
    elif current_mode == 'analysis':
        st.title(f"📊 {st.session_state.current_session['title']}")
        show_chat_history()
        show_analysis_form()
    
    elif current_mode == 'clinical_chat':
        st.title(f"💬 {st.session_state.current_session['title']}")
        show_chat_history()
        show_clinical_chat()
    
    elif current_mode == 'document_manager':
        st.title("📚 Gestión de Documentos Clínicos")
        show_document_manager()
    
    # Footer
    show_footer()

if __name__ == "__main__":
    main()

