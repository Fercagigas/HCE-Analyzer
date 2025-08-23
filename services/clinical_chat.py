
"""
Componente de chat clínico especializado para consultas RAG
"""
import streamlit as st
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from src.analyzers.agents import ClinicalChatAgent, RAGAgent
from services.auth.session_manager import SessionManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalChatInterface:
    """Interfaz de chat clínico con capacidades RAG"""
    
    def __init__(self):
        self.chat_agent = ClinicalChatAgent()
        self.rag_agent = RAGAgent()
        self.specialties = [
            "General",
            "Urgencias",
            "Cardiología",
            "Neurología",
            "Pediatría",
            "Ginecología",
            "Traumatología",
            "Medicina Interna",
            "Cirugía"
        ]
    
    def render_chat_interface(self):
        """Renderiza la interfaz principal de chat mejorada"""
        # Inicializar el historial de chat en session_state si no existe
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        
        # Configuración de la consulta en sidebar
        with st.sidebar:
            st.subheader("⚙️ Configuración de Consulta")
            
            specialty = st.selectbox(
                "Especialidad",
                self.specialties,
                help="Filtra las guías clínicas por especialidad"
            )
            
            search_mode = st.radio(
                "Modo de Búsqueda",
                ["Automático", "Solo RAG", "Solo Chat"],
                help="Automático: detecta el tipo de consulta automáticamente"
            )
            
            st.divider()
            
            # Botón para limpiar chat
            if st.button("🗑️ Limpiar Chat", use_container_width=True):
                st.session_state.chat_messages = []
                st.rerun()
            
            # Estadísticas de la sesión
            self._show_session_stats()
        
        # Área principal de chat
        st.subheader("💬 Chat Clínico Especializado")
        
        # Cargar historial de la base de datos al iniciar
        self._load_chat_history()
        
        # Mostrar todos los mensajes del historial
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    self._render_assistant_message(message["content"])
                else:
                    st.write(message["content"])
        
        # Input de consulta (siempre visible al final)
        if prompt := st.chat_input("Escribe tu consulta clínica aquí..."):
            # Agregar mensaje del usuario al historial
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            # Mostrar mensaje del usuario inmediatamente
            with st.chat_message("user"):
                st.write(prompt)
            
            # Procesar y mostrar respuesta
            self._process_query_improved(prompt, specialty, search_mode)
        
        # Sugerencias de consultas (solo si no hay mensajes)
        if not st.session_state.chat_messages:
            self._show_query_suggestions()
    
    def _load_chat_history(self):
        """Carga el historial de chat de la base de datos"""
        if not st.session_state.get('current_session'):
            return
        
        # Solo cargar si el historial local está vacío
        if not st.session_state.chat_messages:
            try:
                success, messages = st.session_state.auth_service.get_session_messages(
                    st.session_state.current_session['id']
                )
                
                if success and messages:
                    # Convertir mensajes de BD al formato del chat
                    for message in messages:
                        st.session_state.chat_messages.append({
                            "role": message['role'],
                            "content": message['content']
                        })
            except Exception as e:
                logger.error(f"Error cargando historial: {e}")
    
    def _process_query_improved(self, query: str, specialty: str, search_mode: str):
        """Procesa una consulta del usuario con interfaz mejorada"""
        if not st.session_state.get('current_session'):
            st.error("❌ No hay sesión activa. Crea una nueva sesión.")
            return
        
        user_id = st.session_state.user['id']
        session_id = st.session_state.current_session['id']
        
        # Guardar mensaje del usuario en BD
        try:
            st.session_state.auth_service.save_message(session_id, query, 'user')
        except Exception as e:
            logger.error(f"Error guardando mensaje de usuario: {e}")
        
        # Mostrar indicador de procesamiento
        with st.chat_message("assistant"):
            with st.spinner("🔍 Procesando consulta..."):
                try:
                    # Determinar método de procesamiento
                    if search_mode == "Solo RAG":
                        result = self.rag_agent.process_clinical_query(
                            user_id, 
                            query, 
                            specialty if specialty != "General" else None
                        )
                    elif search_mode == "Solo Chat":
                        # Obtener contexto de conversación
                        context = self._get_conversation_context_from_session()
                        result = self.chat_agent._handle_general_chat(user_id, query, context)
                    else:  # Automático
                        context = self._get_conversation_context_from_session()
                        result = self.chat_agent.process_message(user_id, query, context)
                    
                    # Procesar resultado
                    if result.get('success'):
                        response = result.get('response', result.get('answer', ''))
                        
                        # Agregar respuesta al historial local
                        st.session_state.chat_messages.append({
                            "role": "assistant", 
                            "content": response
                        })
                        
                        # Renderizar respuesta
                        self._render_assistant_message(response)
                        
                        # Mostrar fuentes si están disponibles
                        if result.get('sources'):
                            self._show_sources(result['sources'])
                        
                        # Guardar respuesta en BD
                        try:
                            st.session_state.auth_service.save_message(session_id, response, 'assistant')
                        except Exception as e:
                            logger.error(f"Error guardando respuesta: {e}")
                        
                        # Mostrar información adicional
                        self._show_query_info(result)
                        
                    else:
                        error_msg = result.get('error', 'Error desconocido')
                        error_response = f"❌ Error: {error_msg}"
                        
                        # Agregar error al historial
                        st.session_state.chat_messages.append({
                            "role": "assistant", 
                            "content": error_response
                        })
                        
                        st.error(error_response)
                        
                        # Mostrar sugerencias si están disponibles
                        if result.get('suggestions'):
                            st.info("💡 Prueba con estas consultas:")
                            for suggestion in result['suggestions'][:3]:
                                st.write(f"• {suggestion}")
                
                except Exception as e:
                    logger.error(f"Error procesando consulta: {e}")
                    error_response = f"❌ Error interno: {str(e)}"
                    
                    # Agregar error al historial
                    st.session_state.chat_messages.append({
                        "role": "assistant", 
                        "content": error_response
                    })
                    
                    st.error(error_response)
    
    def _render_assistant_message(self, content: str):
        """Renderiza mensaje del asistente con formato especial"""
        try:
            # Intentar parsear si es una respuesta estructurada
            if "**Respuesta Directa**" in content or "FUENTE" in content:
                # Respuesta RAG estructurada
                self._render_rag_response(content)
            else:
                # Respuesta normal
                st.write(content)
                
        except Exception as e:
            logger.error(f"Error renderizando mensaje: {e}")
            st.write(content)
    
    def _render_rag_response(self, content: str):
        """Renderiza respuesta RAG con formato especial"""
        # Dividir contenido en secciones
        sections = content.split("**")
        
        current_section = ""
        for i, section in enumerate(sections):
            if i % 2 == 0:  # Texto normal
                if section.strip():
                    st.write(section.strip())
            else:  # Encabezado
                if section.strip():
                    st.markdown(f"**{section.strip()}**")
        
        # Mostrar fuentes si están presentes
        if "--- FUENTE" in content:
            with st.expander("📚 Ver Fuentes Consultadas"):
                sources = content.split("--- FUENTE")[1:]
                for i, source in enumerate(sources, 1):
                    st.markdown(f"**Fuente {i}:**")
                    st.text(source.split("---")[0].strip())
    

    
    def _get_conversation_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Obtiene el contexto de la conversación desde BD"""
        try:
            success, messages = st.session_state.auth_service.get_session_messages(session_id)
            if success:
                return messages[-10:]  # Últimos 10 mensajes
            return []
        except Exception as e:
            logger.error(f"Error obteniendo contexto: {e}")
            return []
    
    def _get_conversation_context_from_session(self) -> List[Dict[str, Any]]:
        """Obtiene el contexto de la conversación desde la sesión local"""
        try:
            # Usar los mensajes de la sesión local (más rápido)
            if st.session_state.chat_messages:
                # Convertir al formato esperado y tomar los últimos 10
                context = []
                for msg in st.session_state.chat_messages[-10:]:
                    context.append({
                        'role': msg['role'],
                        'content': msg['content'],
                        'created_at': datetime.now().isoformat()
                    })
                return context
            return []
        except Exception as e:
            logger.error(f"Error obteniendo contexto de sesión: {e}")
            return []
    
    def _show_sources(self, sources: List[Dict[str, Any]]):
        """Muestra las fuentes consultadas"""
        with st.expander("📚 Fuentes Consultadas", expanded=False):
            for i, source in enumerate(sources, 1):
                st.markdown(f"**Fuente {i}:** {source.get('source', 'Desconocido')}")
                
                # Mostrar preview del contenido
                content = source.get('content', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                
                st.text(content)
                
                # Mostrar metadata si está disponible
                metadata = source.get('metadata', {})
                if metadata:
                    st.json(metadata)
                
                if i < len(sources):
                    st.divider()
    
    def _show_query_info(self, result: Dict[str, Any]):
        """Muestra información adicional sobre la consulta"""
        with st.expander("ℹ️ Información de la Consulta", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Tipo de Consulta", result.get('type', 'Desconocido'))
                if 'model_used' in result:
                    st.metric("Modelo Utilizado", result['model_used'])
            
            with col2:
                if 'sources' in result:
                    st.metric("Fuentes Consultadas", len(result['sources']))
                if 'timestamp' in result:
                    timestamp = datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
                    st.metric("Procesado en", timestamp.strftime("%H:%M:%S"))
    
    def _show_session_stats(self):
        """Muestra estadísticas de la sesión"""
        if st.session_state.get('current_session'):
            st.subheader("📊 Estadísticas")
            
            # Obtener mensajes de la sesión
            success, messages = st.session_state.auth_service.get_session_messages(
                st.session_state.current_session['id']
            )
            
            if success:
                user_messages = [m for m in messages if m['role'] == 'user']
                assistant_messages = [m for m in messages if m['role'] == 'assistant']
                
                st.metric("Consultas Realizadas", len(user_messages))
                st.metric("Respuestas Generadas", len(assistant_messages))
                
                if messages:
                    last_message = messages[-1]
                    last_time = datetime.fromisoformat(last_message['created_at'].replace('Z', '+00:00'))
                    st.metric("Última Actividad", last_time.strftime("%H:%M"))
    
    def _show_query_suggestions(self):
        """Muestra sugerencias de consultas comunes"""
        st.markdown("### 💡 Consultas Sugeridas")
        st.markdown("*Haz clic en cualquier consulta para comenzar:*")
        
        suggestions = [
            "¿Cuál es el protocolo para manejo de dolor torácico en urgencias?",
            "¿Cómo se administran los antibióticos en casos de sepsis?",
            "¿Cuáles son los criterios de alta para pacientes con neumonía?",
            "¿Cuál es el manejo inicial de una crisis hipertensiva?",
            "¿Qué protocolo seguir para sedación en UCI?",
            "¿Cuáles son las indicaciones para intubación de emergencia?",
            "¿Cómo evaluar un paciente con sospecha de ACV?",
            "¿Cuál es el manejo de una arritmia en urgencias?"
        ]
        
        # Mostrar sugerencias en columnas
        col1, col2 = st.columns(2)
        
        for i, suggestion in enumerate(suggestions):
            col = col1 if i % 2 == 0 else col2
            with col:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    # Agregar la sugerencia como mensaje del usuario
                    st.session_state.chat_messages.append({"role": "user", "content": suggestion})
                    st.rerun()

def show_clinical_chat():
    """Función principal para mostrar el chat clínico"""
    try:
        # Verificar autenticación
        if not SessionManager.is_authenticated():
            st.error("❌ Debes iniciar sesión para usar el chat clínico")
            return
        
        # Inicializar interfaz de chat
        chat_interface = ClinicalChatInterface()
        
        # Renderizar interfaz
        chat_interface.render_chat_interface()
    
    except Exception as e:
        logger.error(f"Error en chat clínico: {e}")
        st.error(f"❌ Error inicializando chat clínico: {str(e)}")
        
        # Mostrar información de debug en desarrollo
        if st.checkbox("Mostrar detalles del error"):
            st.exception(e)

