
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
            <h3>Sistema de Análisis Clínico Inteligente</h3>
            <p style='color: #666; font-size: 1.1em;'>
                Inicia sesión para acceder a las funcionalidades avanzadas de análisis médico
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
                success, message = SessionManager.login(email, password)
                
                if success:
                    st.success("✅ ¡Bienvenido! Redirigiendo...")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")

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

def show_profile_page():
    """Muestra la página de perfil del usuario"""
    if not SessionManager.is_authenticated():
        st.error("❌ Debes iniciar sesión para ver tu perfil")
        return
    
    user = st.session_state.user
    
    st.title("👤 Mi Perfil")
    
    # Información del usuario
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
            <div style='text-align: center; padding: 2rem; background: #f0f2f6; border-radius: 10px;'>
                <div style='font-size: 4rem;'>👨‍⚕️</div>
                <h3>{}</h3>
                <p style='color: #666;'>{}</p>
            </div>
        """.format(
            user.get('name', 'Usuario'),
            user.get('specialty', 'Especialidad no especificada')
        ), unsafe_allow_html=True)
    
    with col2:
        st.subheader("📋 Información Personal")
        
        with st.form("profile_form"):
            name = st.text_input("Nombre Completo", value=user.get('name', ''))
            email = st.text_input("Email", value=user.get('email', ''), disabled=True)
            specialty = st.selectbox(
                "Especialidad",
                [
                    "Medicina General", "Urgencias", "Cardiología", "Neurología",
                    "Pediatría", "Ginecología", "Traumatología", "Medicina Interna",
                    "Cirugía", "Radiología", "Patología", "Anestesiología", "Otra"
                ],
                index=0 if not user.get('specialty') else 0
            )
            medical_license = st.text_input(
                "Número de Colegiatura", 
                value=user.get('medical_license', '')
            )
            
            if st.form_submit_button("💾 Actualizar Perfil", type="primary"):
                # Aquí iría la lógica para actualizar el perfil
                st.success("✅ Perfil actualizado correctamente")
    
    st.divider()
    
    # Estadísticas de uso
    st.subheader("📊 Estadísticas de Uso")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Análisis Realizados", "47", "↗️ +3")
    
    with col2:
        st.metric("Consultas RAG", "128", "↗️ +12")
    
    with col3:
        st.metric("Documentos Subidos", "8", "→ 0")
    
    with col4:
        st.metric("Tiempo Total", "24h 30m", "↗️ +2h")
    
    # Configuraciones
    st.divider()
    st.subheader("⚙️ Configuraciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.checkbox("Notificaciones por email", value=True)
        st.checkbox("Guardar historial de análisis", value=True)
        st.selectbox("Idioma", ["Español", "English"], index=0)
    
    with col2:
        st.checkbox("Modo oscuro", value=False)
        st.checkbox("Análisis automático", value=False)
        st.selectbox("Zona horaria", ["UTC-5 (Lima)", "UTC-3 (Buenos Aires)"], index=0)

