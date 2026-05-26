
"""
Páginas de autenticación para HCE Analyzer
"""
import streamlit as st
from services.auth.session_manager import SessionManager
from config.config import APP_NAME, APP_ICON, UI_MESSAGES

def show_login_page():
    """Muestra la página de inicio de sesión"""
    st.markdown(f"""
        <div style='text-align: center; padding: 3rem 0;'>
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>Sistema de Análisis Clínico Inteligente con Chat Unificado</h3>
            <p style='color: #666; font-size: 1.1em;'>
                Acceso inteligente a datos MIMIC-IV-ED y documentos clínicos en una sola interfaz
            </p>
            <p style='color: #667eea; font-size: 0.95em; margin-top: 1rem;'>
                🎯 Chat Unificado • 🗄️ Base de Datos • 📚 RAG • 📊 Visualizaciones
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Tabs para login y registro
    tab1, tab2 = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_register_form()

def show_login_form():
    """Formulario de inicio de sesión"""
    with st.form("login_form"):
        st.subheader("Iniciar Sesión")
        
        email = st.text_input(
            "📧 Correo Electrónico",
            placeholder="tu.email@hospital.com"
        )
        
        password = st.text_input(
            "🔒 Contraseña",
            type="password",
            placeholder="Tu contraseña"
        )
        
        remember_me = st.checkbox("Mantener sesión iniciada")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_button = st.form_submit_button(
                "🚀 Iniciar Sesión",
                use_container_width=True,
                type="primary"
            )
        
        if login_button:
            if not email or not password:
                st.error("❌ Por favor completa todos los campos")
                return
            
            with st.spinner("🔄 Verificando credenciales..."):
                success, message = SessionManager.login(email, password, remember_me)
                
                if success:
                    st.success("✅ ¡Bienvenido! Redirigiendo...")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # Enlace para recuperar contraseña (fuera del form)
    st.markdown("---")
    with st.expander("🔑 ¿Olvidaste tu contraseña?"):
        reset_email = st.text_input(
            "Ingresa tu correo electrónico",
            placeholder="tu.email@hospital.com",
            key="reset_email"
        )
        if st.button("📧 Enviar enlace de recuperación", use_container_width=True):
            if reset_email and '@' in reset_email:
                success, msg = st.session_state.auth_service.reset_password(reset_email)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
            else:
                st.error("❌ Ingresa un correo válido")

def show_register_form():
    """Formulario de registro"""
    with st.form("register_form"):
        st.subheader("Crear Cuenta Nueva")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                "👤 Nombre Completo",
                placeholder="Dr. Juan Pérez"
            )
            
            email = st.text_input(
                "📧 Correo Electrónico",
                placeholder="juan.perez@hospital.com"
            )
        
        with col2:
            specialty = st.selectbox(
                "🏥 Especialidad",
                [
                    "Medicina General",
                    "Urgencias",
                    "Cardiología",
                    "Neurología",
                    "Pediatría",
                    "Ginecología",
                    "Traumatología",
                    "Medicina Interna",
                    "Cirugía",
                    "Radiología",
                    "Patología",
                    "Anestesiología",
                    "Otra"
                ]
            )
            
            medical_license = st.text_input(
                "🆔 Número de Colegiatura",
                placeholder="123456-7"
            )
        
        password = st.text_input(
            "🔒 Contraseña",
            type="password",
            placeholder="Mínimo 8 caracteres"
        )
        
        confirm_password = st.text_input(
            "🔒 Confirmar Contraseña",
            type="password",
            placeholder="Repite tu contraseña"
        )
        
        # Términos y condiciones
        terms_accepted = st.checkbox(
            "Acepto los términos y condiciones de uso del sistema",
            help="Al registrarte, aceptas el uso responsable del sistema para fines médicos profesionales"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            register_button = st.form_submit_button(
                "✨ Crear Cuenta",
                use_container_width=True,
                type="primary"
            )
        
        if register_button:
            # Validaciones
            errors = []
            
            if not all([name, email, password, confirm_password, specialty]):
                errors.append("Todos los campos son obligatorios")
            
            if password != confirm_password:
                errors.append("Las contraseñas no coinciden")
            
            if len(password) < 8:
                errors.append("La contraseña debe tener al menos 8 caracteres")
            
            if not terms_accepted:
                errors.append("Debes aceptar los términos y condiciones")
            
            if "@" not in email:
                errors.append("Formato de email inválido")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return
            
            # Intentar registro
            with st.spinner("📝 Creando cuenta..."):
                success, message = SessionManager.register(
                    email=email,
                    password=password,
                    name=name,
                    specialty=specialty,
                    medical_license=medical_license
                )
                
                if success:
                    st.success("✅ ¡Cuenta creada exitosamente! Ya puedes iniciar sesión.")
                    st.balloons()
                else:
                    st.error(f"❌ {message}")

def show_logout_confirmation():
    """Muestra confirmación de cierre de sesión"""
    st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h3>¿Estás seguro que deseas cerrar sesión?</h3>
            <p>Se perderán los datos no guardados de la sesión actual.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.session_state.show_logout_confirmation = False
            st.rerun()
    
    with col3:
        if st.button("✅ Cerrar Sesión", use_container_width=True, type="primary"):
            SessionManager.logout()
            st.success("👋 Sesión cerrada correctamente")
            st.rerun()



