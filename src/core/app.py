
import streamlit as st
import os
from pathlib import Path
import traceback

# Import logging configuration
from config.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Importaciones locales (lazy imports moved to functions to avoid circular imports)
def _get_imports():
    """Lazy imports to avoid issues when module is imported"""
    from services.auth.session_manager import SessionManager
    from ui.components.components.auth_pages import show_login_page, show_logout_confirmation
    from ui.components.components.sidebar import show_sidebar
    from ui.components.components.document_manager import show_document_manager
    from ui.components.components.footer import show_footer
    from ui.unified_chat_interface import show_unified_chat
    from config.config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
    return {
        'SessionManager': SessionManager,
        'show_login_page': show_login_page,
        'show_logout_confirmation': show_logout_confirmation,
        'show_sidebar': show_sidebar,
        'show_document_manager': show_document_manager,
        'show_footer': show_footer,
        'show_unified_chat': show_unified_chat,
        'APP_NAME': APP_NAME,
        'APP_TAGLINE': APP_TAGLINE,
        'APP_DESCRIPTION': APP_DESCRIPTION,
        'APP_ICON': APP_ICON
    }

# Estilos CSS personalizados
_CUSTOM_CSS = """
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
"""

def show_welcome_screen(imports):
    """Pantalla de bienvenida con Chat Unificado como opción principal"""
    APP_ICON = imports['APP_ICON']
    APP_NAME = imports['APP_NAME']
    APP_DESCRIPTION = imports['APP_DESCRIPTION']
    APP_TAGLINE = imports['APP_TAGLINE']
    SessionManager = imports['SessionManager']
    
    st.markdown(f"""
        <div class="main-header">
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style='font-size: 1.2em; opacity: 0.9;'>{APP_TAGLINE}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Destacar Chat Unificado como opción principal
    st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 15px; margin: 2rem 0; text-align: center;'>
            <h2 style='color: white; margin: 0;'>🎯 Chat Unificado</h2>
            <p style='color: white; font-size: 1.1em; margin: 1rem 0;'>
                Interfaz inteligente con acceso automático a datos MIMIC-IV-ED y documentos clínicos
            </p>
            <p style='color: rgba(255,255,255,0.9); font-size: 0.95em;'>
                ✨ Sin cambio de modos • 🤖 Selección automática de herramientas • 📊 Visualizaciones dinámicas
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón principal para Chat Unificado
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button("🚀 Iniciar Chat Unificado", use_container_width=True, type="primary", key="main_unified"):
            success, session = SessionManager.create_chat_session("Chat Unificado")
            if success:
                # Limpiar mensajes anteriores
                st.session_state.unified_messages = []
                st.session_state.current_session = session
                st.session_state.current_mode = "unified_chat"
                st.rerun()
            else:
                st.error("Error al crear la sesión")



def _show_user_greeting():
    """Muestra saludo personalizado al usuario"""
    if st.session_state.user:
        display_name = st.session_state.user.get('name') or st.session_state.user.get('email', '')
        st.markdown(f"""
            <div class="user-greeting">
                👋 Hola, {display_name}
            </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal de la aplicación con logging detallado"""
    logger.info("🎯 Starting main application function")
    
    # Configuración de la página - DEBE ser lo primero
    st.set_page_config(
        page_title="HCE Analyzer - Análisis Clínico Inteligente",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    logger.info("🖥️ Streamlit page configuration set")
    
    # Aplicar estilos CSS
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    
    try:
        # Lazy imports
        logger.info("📦 Loading imports...")
        imports = _get_imports()
        SessionManager = imports['SessionManager']
        show_login_page = imports['show_login_page']
        show_logout_confirmation = imports['show_logout_confirmation']
        show_sidebar = imports['show_sidebar']
        show_document_manager = imports['show_document_manager']
        show_footer = imports['show_footer']
        show_unified_chat = imports['show_unified_chat']
        logger.info("✅ Imports loaded successfully")
        
        # Initialize session
        logger.info("🔧 Initializing session manager...")
        SessionManager.init_session()
        logger.info("✅ Session manager initialized")

        # Verificar autenticación
        if not SessionManager.is_authenticated():
            logger.info("🔐 User not authenticated, showing login page")
            show_login_page()
            show_footer()
            return

        logger.info("✅ User authenticated successfully")
        
        # Verificar si se debe mostrar confirmación de logout
        if st.session_state.get('show_logout_confirmation', False):
            logger.info("🚪 Showing logout confirmation")
            show_logout_confirmation()
            return

        # Mostrar saludo del usuario
        _show_user_greeting()
        
        # Mostrar barra lateral
        logger.info("📋 Rendering sidebar...")
        show_sidebar()

        # Contenido principal basado en el modo actual
        current_mode = st.session_state.get('current_mode', 'welcome')
        logger.info(f"🎨 Rendering content for mode: {current_mode}")
        
        if current_mode == 'welcome' or not st.session_state.get('current_session'):
            logger.info("🏠 Showing welcome screen")
            show_welcome_screen(imports)
        
        elif current_mode == 'unified_chat':
            logger.info("🎯 Showing Unified Chat interface")
            st.title(f"🎯 {st.session_state.current_session['title']}")
            try:
                show_unified_chat()
                logger.info("✅ Unified Chat interface rendered successfully")
            except Exception as e:
                logger.error(f"❌ Error rendering Unified Chat: {str(e)}")
                logger.error(f"Unified Chat error traceback: {traceback.format_exc()}")
                st.error(f"Error cargando Chat Unificado: {str(e)}")
                st.info("💡 Intente recargar la página o contacte al soporte técnico")

        elif current_mode == 'document_manager':
            logger.info("📚 Showing document manager")
            st.title("📚 Gestión de Documentos Clínicos")
            show_document_manager()
        
        # Footer
        show_footer()
        
        logger.info("✅ Main application function completed successfully")
        
    except Exception as e:
        logger.critical(f"💥 Critical error in main function: {str(e)}")
        logger.critical(f"Main function traceback: {traceback.format_exc()}")
        
        # Show user-friendly error message
        st.error("❌ Error crítico en la aplicación")
        st.error(f"Detalle técnico: {str(e)}")
        
        with st.expander("🔧 Información de depuración", expanded=False):
            st.code(traceback.format_exc())
            st.info("💡 Sugerencias:")
            st.markdown("""
            - Recargue la página (F5)
            - Verifique su conexión a internet
            - Contacte al soporte técnico si el problema persiste
            - Revise los logs del sistema para más detalles
            """)
        
        # Re-raise the exception for proper error handling
        raise

if __name__ == "__main__":
    main()

