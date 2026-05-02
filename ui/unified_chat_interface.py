"""
Unified Chat Interface for ChatHCE

This module provides a single, simplified chat interface that integrates access to both
the MIMIC-IV-ED database and RAG-indexed clinical documents through intelligent tool selection.
"""

import streamlit as st
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

from services.unified_chat.unified_agent import create_unified_agent
from services.unified_chat.document_manager import DocumentManager
from services.cache_manager import cache_manager

# Configure logging
logger = logging.getLogger(__name__)


class UnifiedChatInterface:
    """
    Unified chat interface that provides a single entry point for all queries.
    
    Features:
    - Single chat input for all query types
    - Automatic tool selection (database, RAG, visualization)
    - Document upload functionality
    - Conversation history management
    - Performance indicators
    - Error handling with recovery suggestions
    
    Requirements: 1.1, 2.1, 3.1, 4.1, 5.1
    """
    
    def __init__(self):
        """Initialize unified chat interface with agent and document manager"""
        logger.info("Initializing UnifiedChatInterface...")
        
        # Initialize unified chat agent (lazy)
        self._unified_agent = None
        self._agent_initialized = False
        
        # Initialize document manager (lazy)
        self._document_manager = None
        self._doc_manager_initialized = False
        
        # Set up session state management
        self._initialize_session_state()
        
        # Configure caching
        self.cache_enabled = True
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("UnifiedChatInterface initialized")
    
    def _initialize_session_state(self):
        """
        Set up session state management for conversation history and settings.
        
        Requirements: 1.1, 2.1, 3.1, 4.1, 5.1
        """
        # Initialize unified chat messages
        if "unified_messages" not in st.session_state:
            st.session_state.unified_messages = []
            logger.info("Initialized unified_messages in session state")
        
        # Initialize chat configuration
        if "unified_config" not in st.session_state:
            st.session_state.unified_config = {
                'show_tool_usage': True,
                'show_performance': True,
                'show_sources': True,
                'enable_visualizations': True,
                'max_context_messages': 10
            }
            logger.info("Initialized unified_config in session state")
        
        # Initialize document upload state
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = []
            logger.info("Initialized uploaded_documents in session state")
        
        # Initialize visualization cache — persists Plotly figures across Streamlit re-runs.
        # The VisualizationStore singleton lives in-process but Streamlit re-runs can
        # create a fresh process/module state, losing stored figures. Keeping a copy in
        # session_state guarantees they survive page re-renders.
        if "viz_cache" not in st.session_state:
            st.session_state.viz_cache = {}  # viz_id -> StoredVisualization
            logger.info("Initialized viz_cache in session state")

        # Initialize performance tracking
        if "unified_performance" not in st.session_state:
            st.session_state.unified_performance = {
                'total_queries': 0,
                'cache_hits': 0,
                'total_response_time_ms': 0
            }
            logger.info("Initialized unified_performance in session state")
    
    def _initialize_unified_agent(self):
        """
        Lazy initialization of unified chat agent.
        
        Requirements: 1.1, 2.1, 3.1, 5.1
        """
        if self._agent_initialized:
            return
        
        logger.info("🤖 Initializing Unified Chat Agent...")
        
        try:
            self._unified_agent = create_unified_agent()
            self._agent_initialized = True
            logger.info("✅ Unified Chat Agent initialized successfully")
            
        except Exception as e:
            error_msg = f"Error initializing unified agent: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Unified agent error traceback: {traceback.format_exc()}")
            st.error(f"❌ Error inicializando sistema unificado: {str(e)}")
            st.error("Verifique la configuración de Claude API y la base de datos")
    
    def _initialize_document_manager(self):
        """
        Lazy initialization of document manager.
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        if self._doc_manager_initialized:
            return
        
        logger.info("📄 Initializing Document Manager...")
        
        try:
            self._document_manager = DocumentManager()
            self._doc_manager_initialized = True
            logger.info("✅ Document Manager initialized successfully")
            
        except Exception as e:
            error_msg = f"Error initializing document manager: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Document manager error traceback: {traceback.format_exc()}")
            st.error(f"❌ Error inicializando gestor de documentos: {str(e)}")
            st.error("Verifique la configuración de RAG y Supabase")
    
    def show(self):
        """
        Main method to display the unified chat interface.
        
        This is the entry point for rendering the complete interface.
        """
        logger.info("🚀 Starting Unified Chat Interface rendering...")
        
        # Initialize components
        with st.spinner("🔄 Inicializando sistema de chat unificado..."):
            self._initialize_unified_agent()
            self._initialize_document_manager()
        
        # Check if initialization was successful
        if not self._unified_agent:
            st.error("❌ No se pudo inicializar el sistema de chat unificado")
            self._show_initialization_help()
            return
        
        # Show system status
        self._show_system_status()
        
        # Sidebar with document upload and configuration
        with st.sidebar:
            self._show_sidebar()
        
        # Load conversation history from database if needed
        if not st.session_state.unified_messages:
            self._load_conversation_history()
        
        # Show welcome message if no messages
        if not st.session_state.unified_messages:
            self._show_welcome_message()
        
        # Document Management Button (prominent)
        self._show_context_management_button()
        
        # Display conversation history
        self._display_messages()
        
        # Chat input
        self._show_chat_input()
    
    def _show_initialization_help(self):
        """Show help information when initialization fails"""
        st.info("💡 Sugerencias para resolver el problema:")
        st.markdown("""
        - Verifique que la variable `ANTHROPIC_API_KEY` esté configurada
        - Compruebe las credenciales de Supabase (`SUPABASE_URL`, `SUPABASE_KEY`)
        - Verifique la configuración de Supabase pgvector
        - Reinicie la aplicación
        - Revise los logs para más detalles
        - Contacte al administrador del sistema
        """)
    
    def _show_system_status(self):
        """
        Show system status indicator.
        
        Requirements: 1.1, 2.1, 3.1
        """
        with st.expander("🔧 Estado del Sistema", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("🤖 Agente Unificado")
                if self._unified_agent:
                    st.success("✅ Claude Agent")
                    st.success("✅ Tool Selection")
                else:
                    st.error("❌ Agent")
            
            with col2:
                st.subheader("🗄️ Fuentes de Datos")
                if self._unified_agent:
                    st.success("✅ MIMIC-IV-ED")
                    st.success("✅ RAG Documents")
                else:
                    st.warning("⚠️ Datos")
            
            with col3:
                st.subheader("📊 Herramientas")
                if self._unified_agent:
                    st.success("✅ Database Tool")
                    st.success("✅ RAG Tool")
                    st.success("✅ Visualization Tool")
                else:
                    st.error("❌ Tools")
    
    def _show_welcome_message(self):
        """
        Show welcome message for unified chat.
        
        Requirements: 1.1, 2.1, 3.1, 4.1, 5.1
        """
        st.markdown("""
        ### 🎯 Bienvenido al Chat Unificado de ChatHCE
        
        Este sistema integra **todas las capacidades** en una sola interfaz inteligente:
        
        **🏥 Consultas sobre Pacientes (MIMIC-IV-ED):**
        - Información demográfica y estancias
        - Signos vitales y tendencias
        - Diagnósticos con códigos ICD
        - Medicamentos y administración
        
        **📚 Consultas sobre Guías Clínicas (RAG):**
        - Protocolos y procedimientos
        - Guías de tratamiento
        - Mejores prácticas clínicas
        - Información sobre medicamentos
        
        **📊 Visualizaciones Automáticas:**
        - Gráficos de signos vitales
        - Tendencias y comparaciones
        - Distribuciones y correlaciones
        
        **🤖 Selección Inteligente de Herramientas:**
        El sistema decide automáticamente qué herramientas usar según tu consulta.
        
        **Ejemplos de consultas:**
        - "Muéstrame los signos vitales del paciente 10014729"
        - "¿Cuál es el protocolo para hipertensión?"
        - "Compara el tratamiento del paciente 10014729 con las guías de hipertensión"
        - "Genera un gráfico de temperatura del paciente 10014729"
        """)
        
        # Add visualization capabilities button
        with st.expander("📊 Ver Capacidades de Visualización Completas", expanded=False):
            self._show_visualization_capabilities()
    
    def _show_context_management_button(self):
        """
        Show prominent context management button and interface.
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        # Initialize session state for document manager visibility
        if 'show_document_manager' not in st.session_state:
            st.session_state.show_document_manager = False
        
        # Create a prominent button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "📁 Gestión de Documentos RAG",
                use_container_width=True,
                type="primary",
                help="Añadir, ver y eliminar documentos del contexto RAG"
            ):
                st.session_state.show_document_manager = not st.session_state.show_document_manager
        
        # Show document management interface if toggled
        if st.session_state.show_document_manager:
            st.markdown("---")
            self._show_document_management_interface()
            st.markdown("---")
    
    def _show_document_management_interface(self):
        """
        Complete document management interface with upload, list, and delete.
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        st.markdown("### 📚 Gestión de Contexto RAG")
        st.caption("Los documentos subidos se vectorizan y almacenan en Supabase pgvector para consultas RAG")
        
        # Initialize document manager if needed
        if not self._doc_manager_initialized:
            self._initialize_document_manager()
        
        if not self._document_manager:
            st.error("❌ Gestor de documentos no disponible")
            return
        
        # Create tabs for different operations
        tab1, tab2, tab3 = st.tabs(["📤 Subir Documento", "📋 Documentos Indexados", "📊 Estadísticas"])
        
        with tab1:
            self._show_upload_tab()
        
        with tab2:
            self._show_documents_list_tab()
        
        with tab3:
            self._show_statistics_tab()
    
    def _show_upload_tab(self):
        """Show document upload interface"""
        st.markdown("#### 📤 Subir Nuevo Documento")
        
        # File uploader without explicit key - let Streamlit auto-generate it
        uploaded_file = st.file_uploader(
            "Selecciona un archivo para añadir al contexto RAG",
            type=['pdf', 'docx', 'txt'],
            help="Formatos soportados: PDF, DOCX, TXT (máx. 50MB)"
        )
        
        if uploaded_file:
            # Show file info
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📄 **Archivo:** {uploaded_file.name}")
            with col2:
                st.info(f"📏 **Tamaño:** {file_size_mb:.2f} MB")
            
            # Metadata input
            st.markdown("**Metadatos del Documento**")
            
            # Especialidad fija: Urgencias
            specialty = "Urgencias"
            st.info("🏥 **Especialidad:** Urgencias y Emergencias (MIMIC-IV-ED)")
            st.caption("🔜 Próximamente: Más especialidades disponibles")
            
            # Tipo de documento
            doc_type = st.selectbox(
                "Tipo de Documento",
                ["Guía Clínica", "Protocolo", "Manual", "Procedimiento", "Algoritmo", "Otro"],
                key="doc_type"
            )
            
            description = st.text_area(
                "Descripción (opcional)",
                placeholder="Breve descripción del contenido del documento...",
                key="doc_description"
            )
            
            # Upload button
            if st.button("📥 Subir y Vectorizar", use_container_width=True, type="primary"):
                self._process_document_upload_with_metadata(
                    uploaded_file,
                    specialty=specialty,
                    doc_type=doc_type,
                    description=description
                )
    
    def _show_documents_list_tab(self):
        """Show list of indexed documents with delete functionality"""
        st.markdown("#### 📋 Documentos Indexados")
        
        try:
            # Get document list
            doc_list_result = self._document_manager.list_documents()
            
            if not doc_list_result.get('success'):
                st.warning("⚠️ No se pudo obtener la lista de documentos")
                return
            
            documents = doc_list_result.get('documents', [])
            summary = doc_list_result.get('summary', {})
            
            # Show summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Total Documentos", summary.get('total_documents', 0))
            with col2:
                st.metric("📚 Fuentes Únicas", summary.get('unique_sources', 0))
            with col3:
                specialties = summary.get('specialties', [])
                st.metric("🏥 Especialidades", len(specialties) if specialties else 0)
            
            st.markdown("---")
            
            # Show document list
            if documents:
                st.markdown("**Documentos Indexados:**")
                
                # Use a unique prefix based on where this is being called from
                # This prevents duplicate keys when the same document list is rendered multiple times
                import time
                unique_prefix = f"doclist_{int(time.time() * 1000000) % 1000000}"
                
                for idx, doc in enumerate(documents):
                    # Create truly unique key using timestamp prefix + index + filename hash
                    doc_key = f"del_{unique_prefix}_{idx}_{abs(hash(doc.get('filename', 'unknown')))}"
                    
                    with st.expander(f"📄 {doc.get('filename', 'Unknown')} - {doc.get('source', 'N/A')}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.caption(f"**Fuente:** {doc.get('source', 'N/A')}")
                            st.caption(f"**Colección:** {doc.get('collection', 'N/A')}")
                            if doc.get('indexed'):
                                st.success("✅ Indexado en Supabase")
                        
                        with col2:
                            if st.button(
                                "🗑️ Eliminar",
                                key=doc_key,
                                use_container_width=True,
                                type="secondary"
                            ):
                                self._delete_document_with_confirmation(doc.get('filename'))
            else:
                st.info("📭 No hay documentos indexados. Sube tu primer documento en la pestaña 'Subir Documento'.")
        
        except Exception as e:
            st.error(f"❌ Error al listar documentos: {str(e)}")
            logger.error(f"Error listing documents: {e}")
    
    def _show_statistics_tab(self):
        """Show RAG system statistics"""
        st.markdown("#### 📊 Estadísticas del Sistema RAG")
        
        try:
            # Get collection stats from RAG service
            from services.rag.improved_rag_service import get_rag_service
            rag_service = get_rag_service()
            
            stats = rag_service.get_collection_stats()
            
            if 'error' not in stats:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("📦 Total Chunks", stats.get('total_documents', 0))
                    st.metric("📚 Colección", stats.get('collection_name', 'N/A'))
                
                with col2:
                    sources = stats.get('sources', [])
                    st.metric("📄 Fuentes", len(sources))
                    specialties = stats.get('specialties', [])
                    st.metric("🏥 Especialidades", len(specialties))
                
                # Show sources
                if sources:
                    st.markdown("**Fuentes Indexadas:**")
                    for source in sources[:10]:
                        st.text(f"• {source}")
                
                # Show specialties
                if specialties:
                    st.markdown("**Especialidades:**")
                    for specialty in specialties:
                        st.text(f"• {specialty}")
            else:
                st.warning(f"⚠️ {stats.get('error')}")
            
            # Cache statistics
            st.markdown("---")
            st.markdown("**📊 Estadísticas de Caché:**")
            
            cache_stats = rag_service.get_cache_stats()
            if cache_stats:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    embeddings_stats = cache_stats.get('embeddings', {})
                    st.metric("🔢 Embeddings Cache", embeddings_stats.get('size', 0))
                
                with col2:
                    llm_stats = cache_stats.get('llm_responses', {})
                    st.metric("💬 LLM Responses", llm_stats.get('size', 0))
                
                with col3:
                    hit_rate = cache_stats.get('overall_hit_rate', 0)
                    st.metric("🎯 Hit Rate", f"{hit_rate:.1%}")
            
            # Clear cache button
            st.markdown("---")
            if st.button("🗑️ Limpiar Caché RAG", use_container_width=True):
                result = rag_service.clear_cache("all")
                if result.get('success'):
                    st.success("✅ Caché limpiado exitosamente")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result.get('error')}")
        
        except Exception as e:
            st.error(f"❌ Error al obtener estadísticas: {str(e)}")
            logger.error(f"Error getting statistics: {e}")
    
    def _process_document_upload_with_metadata(self, uploaded_file, specialty, doc_type, description):
        """Process document upload with metadata"""
        import tempfile
        import os
        
        try:
            with st.spinner("🔄 Procesando documento..."):
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Prepare metadata
                    metadata = {
                        'specialty': specialty.lower().replace(' ', '_'),
                        'document_type': doc_type.lower().replace(' ', '_'),
                        'description': description if description else None,
                        'original_filename': uploaded_file.name
                    }
                    
                    # Upload document
                    result = self._document_manager.upload_document(tmp_file_path, metadata)
                    
                    if result.get('success'):
                        st.success(f"✅ {result.get('message')}")
                        st.info(f"📦 Chunks procesados: {result.get('chunks_processed', 0)}")
                        
                        # Add to session state
                        st.session_state.uploaded_documents.append({
                            'filename': uploaded_file.name,
                            'uploaded_at': datetime.now().isoformat(),
                            'specialty': specialty,
                            'doc_type': doc_type
                        })
                        
                        # Clear cache to reflect new document
                        cache_manager.invalidate("rag_*", cache_type="llm_responses")
                        
                        st.balloons()
                        
                        # Rerun to refresh document list
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.get('error')}")
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
        
        except Exception as e:
            st.error(f"❌ Error procesando documento: {str(e)}")
            logger.error(f"Error processing document upload: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _delete_document_with_confirmation(self, document_id):
        """Delete document with confirmation"""
        try:
            with st.spinner(f"🗑️ Eliminando {document_id}..."):
                result = self._document_manager.delete_document(document_id)
                
                if result.get('success'):
                    st.success(f"✅ {result.get('message')}")
                    st.info(f"🗑️ Chunks eliminados: {result.get('deleted_count', 0)}")
                    
                    # Clear cache
                    cache_manager.invalidate("rag_*", cache_type="llm_responses")
                    cache_manager.invalidate("search_*", cache_type="query_results")
                    
                    # Rerun to refresh list
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('error')}")
        
        except Exception as e:
            st.error(f"❌ Error eliminando documento: {str(e)}")
            logger.error(f"Error deleting document: {e}")
    
    def _show_sidebar(self):
        """
        Show sidebar with document upload and configuration.
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        # Prominent "Añadir Contexto" button
        if st.button("📁 Añadir Contexto", use_container_width=True, type="primary", help="Gestionar documentos para RAG"):
            st.session_state.show_document_manager = not st.session_state.get('show_document_manager', False)
        
        st.divider()
        
        # Show document manager if toggled
        if st.session_state.get('show_document_manager', False):
            self._show_document_manager_panel()
        else:
            # Show compact document info
            st.subheader("📄 Documentos RAG")
            self._show_document_summary()
        
        st.divider()
        
        # Configuration section
        self._show_configuration()
        
        st.divider()
        
        # Performance indicators
        self._show_performance_sidebar()
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Limpiar Chat", use_container_width=True):
            st.session_state.unified_messages = []
            st.rerun()
    
    def _show_document_manager_panel(self):
        """
        Show comprehensive document management panel.
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        st.subheader("📚 Gestión de Documentos RAG")
        
        # Tabs for different actions
        tab1, tab2, tab3 = st.tabs(["📤 Subir", "📋 Listar", "📊 Estadísticas"])
        
        with tab1:
            self._show_upload_tab()
        
        with tab2:
            self._show_documents_list_tab()
        
        with tab3:
            self._show_statistics_tab()
    
    def _show_document_summary(self):
        """Show compact summary of indexed documents"""
        if not self._document_manager:
            st.info("Gestor no disponible")
            return
        
        try:
            doc_list_result = self._document_manager.list_documents()
            
            if doc_list_result.get('success'):
                summary = doc_list_result.get('summary', {})
                total_docs = summary.get('total_documents', 0)
                unique_sources = summary.get('unique_sources', 0)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Documentos", total_docs)
                with col2:
                    st.metric("Fuentes", unique_sources)
                
                if total_docs > 0:
                    st.success(f"✅ {total_docs} documentos indexados")
        except Exception as e:
            logger.error(f"Error showing document summary: {e}")
    
    def _show_document_upload(self):
        """
        Show document upload widget.
        
        Requirements: 4.1, 4.2, 4.4
        """
        st.markdown("**📤 Subir Documento Clínico**")
        
        uploaded_file = st.file_uploader(
            "Selecciona un archivo",
            type=['pdf', 'docx', 'txt'],
            help="Formatos soportados: PDF, DOCX, TXT (máx. 50MB)",
            key="unified_file_upload"
        )
        
        if uploaded_file:
            # Show file info
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📄 **{uploaded_file.name}** ({file_size_mb:.2f} MB)")
            
            if st.button("📥 Subir y Procesar", use_container_width=True, type="primary"):
                self._process_document_upload(uploaded_file)
    
    def _show_document_list(self):
        """
        Show list of uploaded documents.
        
        Requirements: 4.5
        """
        st.markdown("**📚 Documentos Indexados**")
        
        if not self._document_manager:
            st.info("Gestor de documentos no disponible")
            return
        
        try:
            # Get list of documents
            doc_list_result = self._document_manager.list_documents()
            
            if doc_list_result.get('success'):
                documents = doc_list_result.get('documents', [])
                summary = doc_list_result.get('summary', {})
                
                # Show summary
                st.metric("Total Documentos", summary.get('total_documents', 0))
                
                # Show document list
                if documents:
                    import time
                    unique_prefix = f"sidebar_{int(time.time() * 1000000) % 1000000}"
                    
                    for idx, doc in enumerate(documents[:10]):  # Show first 10
                        with st.expander(f"📄 {doc.get('filename', 'Unknown')}"):
                            st.caption(f"Fuente: {doc.get('source', 'N/A')}")
                            doc_key = f"del_{unique_prefix}_{idx}_{abs(hash(doc.get('filename', 'unknown')))}"
                            if st.button("🗑️ Eliminar", key=doc_key):
                                self._delete_document(doc.get('filename'))
                else:
                    st.info("No hay documentos indexados")
            else:
                st.warning("No se pudo obtener la lista de documentos")
                
        except Exception as e:
            logger.error(f"Error showing document list: {e}")
            st.error(f"Error: {str(e)}")
    
    def _show_configuration(self):
        """Show configuration options"""
        st.markdown("**⚙️ Configuración**")
        
        # Initialize config from session_state (loaded from Supabase on login)
        if 'unified_config' not in st.session_state:
            st.session_state.unified_config = {
                'show_tool_usage': True,
                'show_performance': True,
                'show_sources': True,
                'enable_visualizations': True,
                'max_context_messages': 10
            }
        
        config = st.session_state.unified_config
        
        config['show_tool_usage'] = st.checkbox(
            "Mostrar herramientas usadas",
            value=config.get('show_tool_usage', True),
            help="Indica qué herramientas se usaron en cada respuesta"
        )
        
        config['show_performance'] = st.checkbox(
            "Mostrar métricas de rendimiento",
            value=config.get('show_performance', True),
            help="Muestra tiempo de respuesta y modelo usado"
        )
        
        config['show_sources'] = st.checkbox(
            "Mostrar fuentes RAG",
            value=config.get('show_sources', True),
            help="Muestra las fuentes de documentos consultados"
        )
        
        config['enable_visualizations'] = st.checkbox(
            "Habilitar visualizaciones",
            value=config.get('enable_visualizations', True),
            help="Permite generar gráficos automáticamente"
        )

        # Botón para guardar preferencias en Supabase
        if st.button("💾 Guardar preferencias", use_container_width=True):
            from services.auth.session_manager import SessionManager
            success, msg = SessionManager.save_user_preferences(config)
            if success:
                st.success("✅ Preferencias guardadas")
            else:
                st.warning(f"⚠️ {msg}")
    
    def _show_performance_sidebar(self):
        """
        Show performance indicators in sidebar.
        
        Requirements: 1.1, 2.1, 3.1
        """
        st.markdown("**📊 Rendimiento**")
        
        if "unified_performance" not in st.session_state:
            st.session_state.unified_performance = {
                'total_queries': 0,
                'cache_hits': 0,
                'total_response_time_ms': 0
            }
        
        perf = st.session_state.unified_performance
        
        total_queries = perf.get('total_queries', 0)
        cache_hits = perf.get('cache_hits', 0)
        total_time = perf.get('total_response_time_ms', 0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Consultas", total_queries)
            if total_queries > 0:
                avg_time = total_time / total_queries
                st.metric("Tiempo Prom.", f"{avg_time:.0f}ms")
        
        with col2:
            if total_queries > 0:
                cache_rate = (cache_hits / total_queries) * 100
                st.metric("Cache Hit", f"{cache_rate:.0f}%")
            else:
                st.metric("Cache Hit", "0%")
    
    def _load_conversation_history(self):
        """
        Load conversation history from database including metadata.
        
        If the current session has no messages but the user has older sessions
        with content, load the most recently active one instead.
        
        Requirements: 1.1, 2.1, 3.1
        """
        if not st.session_state.get('current_session'):
            return

        try:
            session_id = st.session_state.current_session['id']
            success, messages = st.session_state.auth_service.get_session_messages(session_id)

            # If the current session is empty, try to find the most recent session
            # that actually has messages (avoids landing on a blank newly-created session)
            if success and not messages and st.session_state.get('user'):
                user_id = st.session_state.user['id']
                ok, sessions = st.session_state.auth_service.get_user_sessions(user_id, limit=3)
                if ok and sessions:
                    for candidate in sessions:
                        if candidate['id'] == session_id:
                            continue  # already checked
                        ok2, candidate_msgs = st.session_state.auth_service.get_session_messages(
                            candidate['id']
                        )
                        if ok2 and candidate_msgs:
                            # Switch to this session silently
                            st.session_state.current_session = candidate
                            session_id = candidate['id']
                            messages = candidate_msgs
                            logger.info(
                                f"Switched to session {session_id} which has "
                                f"{len(messages)} messages"
                            )
                            break

            if success and messages:
                for message in messages:
                    msg_content = message['content']
                    metadata = message.get('metadata', {})
                    
                    # For assistant messages, reconstruct the response structure
                    if message['role'] == 'assistant' and metadata:
                        msg_content = {
                            'success': True,
                            'content': message['content'],
                            'tools_used': metadata.get('tools_used', []),
                            'sources': metadata.get('sources', []),
                            'visualizations': [],  # Don't reload visualizations from DB
                            'metadata': {
                                'model_used': metadata.get('model_used', 'unknown')
                            }
                        }
                    
                    st.session_state.unified_messages.append({
                        "role": message['role'],
                        "content": msg_content
                    })
                logger.info(f"Loaded {len(messages)} messages from history")
                    
        except Exception as e:
            logger.warning(f"Error loading conversation history: {e}")
    
    def _display_messages(self):
        """
        Display conversation history.
        
        Requirements: 1.1, 2.1, 3.1
        """
        for message in st.session_state.unified_messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    self._render_assistant_message(message["content"])
                else:
                    st.write(message["content"])
    
    def _show_chat_input(self):
        """
        Show chat input field and handle message submission.
        
        Requirements: 1.1, 2.1, 3.1
        """
        if prompt := st.chat_input("Pregunta sobre pacientes, guías clínicas, o solicita visualizaciones..."):
            # Add user message to chat history
            st.session_state.unified_messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.write(prompt)
            
            # Process message with unified agent
            with st.chat_message("assistant"):
                self._process_user_message(prompt)
    
    def _process_user_message(self, message: str):
        """
        Process user message with unified agent and display results.
        
        Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5
        """
        logger.info(f"🤖 Processing user message: {message[:100]}...")
        
        # Show processing status
        with st.spinner("🤖 Procesando con agente unificado..."):
            try:
                # Get conversation context
                context = self._get_conversation_context()
                
                # Track performance
                start_time = datetime.now()
                
                # Process message with unified agent
                result = self._unified_agent.process_message(
                    message=message,
                    context=context,
                    session_id=st.session_state.get('current_session', {}).get('id')
                )
                
                # Calculate response time
                end_time = datetime.now()
                response_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Update performance tracking
                if "unified_performance" not in st.session_state:
                    st.session_state.unified_performance = {
                        'total_queries': 0,
                        'cache_hits': 0,
                        'total_response_time_ms': 0
                    }
                perf = st.session_state.unified_performance
                perf['total_queries'] += 1
                perf['total_response_time_ms'] += response_time_ms
                
                logger.info(f"📊 Message processed: {type(result)}")
                
                if isinstance(result, dict) and result.get('success'):
                    # Add response time to result
                    result['processing_time_ms'] = response_time_ms
                    
                    # Persist any new visualizations into session_state BEFORE the
                    # re-run that Streamlit triggers after appending to messages.
                    # This prevents "Visualization X not found in store" warnings.
                    self._persist_visualizations_to_session(result)
                    
                    # Add successful response to chat history
                    st.session_state.unified_messages.append({
                        "role": "assistant",
                        "content": result
                    })
                    
                    # Display response
                    self._render_assistant_message(result)
                    
                    # Save to database
                    self._save_to_database(message, result)
                    
                else:
                    # Handle error response
                    error_msg = result.get('error', 'Error desconocido') if isinstance(result, dict) else str(result)
                    logger.error(f"❌ Message processing failed: {error_msg}")
                    
                    error_response = {
                        'success': False,
                        'content': f"❌ **Error**\n\n{error_msg}",
                        'error': error_msg
                    }
                    
                    st.session_state.unified_messages.append({
                        "role": "assistant",
                        "content": error_response
                    })
                    
                    self._render_error_message(error_response)
                    
            except Exception as e:
                error_msg = f"Error procesando mensaje: {str(e)}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Message processing traceback: {traceback.format_exc()}")
                
                error_response = {
                    'success': False,
                    'content': f"❌ **Error de Sistema**\n\n{error_msg}",
                    'error': error_msg
                }
                
                st.session_state.unified_messages.append({
                    "role": "assistant",
                    "content": error_response
                })
                
                self._render_error_message(error_response)
    
    def _render_assistant_message(self, content):
        """
        Render assistant message with markdown, visualizations, and metadata.
        
        Handles:
        1. visualization_ids type - retrieves from visualization_store
        2. Legacy image/multiple_images types - displays directly
        
        Requirements: 1.4, 2.3, 3.3, 5.5
        """
        if isinstance(content, dict):
            # Structured response
            response_text = content.get('content', '')
            
            # Display main response with markdown
            if response_text:
                st.markdown(response_text)
            else:
                st.write(str(content))
            
            # Display inline visualizations
            if content.get('visualizations') and st.session_state.unified_config.get('enable_visualizations'):
                st.markdown("---")
                st.markdown("### 📊 Visualizaciones")
                
                for viz in content['visualizations']:
                    # NEW: Handle visualization_ids type (from visualization_store)
                    if viz.get('type') == 'visualization_ids' and viz.get('ids'):
                        self._render_visualizations_from_store(viz['ids'])
                    
                    elif viz.get('type') == 'image' and viz.get('data'):
                        # Single image (legacy)
                        if viz.get('title'):
                            st.markdown(f"**{viz['title']}**")
                        st.image(viz['data'])
                    
                    elif viz.get('type') == 'multiple_images' and viz.get('images'):
                        # Multiple images (legacy)
                        st.markdown(f"**{viz.get('count', len(viz['images']))} visualizaciones generadas:**")
                        for img in viz['images']:
                            if img.get('title'):
                                st.markdown(f"**{img['title']}**")
                            if img.get('data'):
                                st.image(img['data'])
                            st.markdown("---")
            
            # Show source citations for RAG responses with retrieved content
            if content.get('sources') and st.session_state.unified_config.get('show_sources'):
                st.markdown("---")
                st.markdown("### 📚 Fuentes Consultadas")
                for i, source in enumerate(content['sources'], 1):
                    filename = source.get('filename', '')
                    if filename:
                        # Structured source from RAG
                        label = f"📄 {filename}"
                        if source.get('page'):
                            label += f" — p. {source['page']}"
                        if source.get('specialty'):
                            label += f" — {source['specialty']}"
                        with st.expander(label):
                            if source.get('doc_type'):
                                st.caption(f"Tipo: {source['doc_type']}")
                            st.caption(f"Fuente extraída por: {source.get('tool', 'RAG')}")
                            # Show original retrieved content
                            retrieved = source.get('retrieved_content', '')
                            if retrieved:
                                st.markdown("**Texto original recuperado:**")
                                st.info(retrieved)
                    else:
                        # Fallback: plain text source
                        with st.expander(f"Fuente {i}"):
                            st.caption(source.get('content', 'N/A'))
            
            # Indicate which tools were used
            if content.get('tools_used') and st.session_state.unified_config.get('show_tool_usage'):
                with st.expander("🔧 Herramientas Utilizadas", expanded=False):
                    for tool in content['tools_used']:
                        tool_icon = self._get_tool_icon(tool)
                        st.markdown(f"{tool_icon} **{tool}**")
            
            # Display performance metadata
            if st.session_state.unified_config.get('show_performance'):
                self._render_performance_metadata(content)
        
        else:
            # Simple text response
            st.write(content)
    
    def _persist_visualizations_to_session(self, result: Dict[str, Any]) -> None:
        """
        Copy Plotly figure objects from VisualizationStore into st.session_state.viz_cache
        so they survive Streamlit re-runs within the same browser session.
        """
        visualizations = result.get('visualizations', [])
        if not visualizations:
            return

        try:
            from services.medical_agent.visualization_store import visualization_store

            if 'viz_cache' not in st.session_state:
                st.session_state.viz_cache = {}

            for viz_entry in visualizations:
                if viz_entry.get('type') == 'visualization_ids':
                    for viz_id in viz_entry.get('ids', []):
                        if viz_id not in st.session_state.viz_cache:
                            stored = visualization_store.get(viz_id)
                            if stored:
                                st.session_state.viz_cache[viz_id] = stored
                                logger.info(f"Persisted visualization {viz_id} to session_state")
                            else:
                                logger.warning(f"Could not persist {viz_id}: not in store")
        except Exception as e:
            logger.error(f"Error persisting visualizations to session: {e}")

    def _render_visualizations_from_store(self, viz_ids: list):
        """
        Render Plotly figures using st.plotly_chart() — no PNG conversion needed.

        Looks up figures in st.session_state.viz_cache first (survives re-runs),
        then falls back to the in-process VisualizationStore.
        """
        try:
            from services.medical_agent.visualization_store import visualization_store

            if 'viz_cache' not in st.session_state:
                st.session_state.viz_cache = {}

            found_any = False
            for viz_id in viz_ids:
                # 1. Try session_state cache (persists across re-runs)
                stored_viz = st.session_state.viz_cache.get(viz_id)

                # 2. Fall back to in-process store (available on first render)
                if stored_viz is None:
                    stored_viz = visualization_store.get(viz_id)
                    if stored_viz is not None:
                        st.session_state.viz_cache[viz_id] = stored_viz

                if stored_viz is None:
                    logger.warning(f"Visualization {viz_id} not found in store or cache")
                    continue

                found_any = True

                # Show title
                title = stored_viz.title or stored_viz.metric or ""
                if title:
                    st.markdown(f"**{title}**")

                # Render with plotly_chart (interactive, no kaleido needed)
                if stored_viz.figure is not None:
                    try:
                        st.plotly_chart(
                            stored_viz.figure,
                            use_container_width=True,
                            key=f"viz_{viz_id}"
                        )
                    except Exception as e:
                        logger.error(f"Error rendering plotly chart {viz_id}: {e}")
                        # Fallback: try PNG conversion
                        try:
                            import base64
                            img_bytes = stored_viz.figure.to_image(format='png', width=1200, height=600)
                            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                            st.image(f"data:image/png;base64,{img_b64}")
                        except Exception as e2:
                            st.warning(f"⚠️ No se pudo renderizar la visualización {viz_id}: {e2}")
                elif stored_viz.base64_image:
                    st.image(f"data:image/png;base64,{stored_viz.base64_image}")
                else:
                    st.warning(f"⚠️ Visualización {viz_id} sin datos de figura")

                st.markdown("---")

            if not found_any:
                st.info("ℹ️ Las visualizaciones no están disponibles (se generaron en una sesión anterior).")

        except ImportError as e:
            logger.error(f"Could not import visualization_store: {e}")
            st.error("❌ Error: No se pudo cargar el almacén de visualizaciones")
        except Exception as e:
            logger.error(f"Error rendering visualizations from store: {e}")
            st.error(f"❌ Error al renderizar visualizaciones: {str(e)}")
    
    def _render_error_message(self, error_response: Dict[str, Any]):
        """
        Show user-friendly error messages with recovery suggestions.
        
        Requirements: 1.1, 2.1, 3.1
        """
        error_msg = error_response.get('error', 'Error desconocido')
        
        st.error(f"❌ {error_msg}")
        
        # Display suggestions for error recovery
        st.markdown("**💡 Sugerencias:**")
        suggestions = error_response.get('suggestions', [
            'Intente reformular su pregunta',
            'Verifique que los IDs de paciente sean correctos',
            'Asegúrese de que hay documentos indexados para consultas RAG',
            'Intente nuevamente en unos momentos'
        ])
        
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
        
        # Add retry functionality
        if st.button("🔄 Reintentar", key=f"retry_{datetime.now().timestamp()}"):
            st.rerun()
    
    def _render_performance_metadata(self, content: Dict[str, Any]):
        """
        Render performance indicators.
        
        Requirements: 1.1, 2.1, 3.1
        """
        model_used = content.get('model_used', 'Unknown')
        processing_time = content.get('processing_time_ms')
        tokens_used = content.get('tokens_used')
        
        metadata_parts = []
        
        # Show model used
        metadata_parts.append(f"🤖 {model_used}")
        
        # Show response time
        if processing_time is not None:
            metadata_parts.append(f"⏱️ {processing_time:.0f}ms")
        
        # Indicate cache hits
        if content.get('cached'):
            metadata_parts.append("🚀 Cached")
        
        # Show tool usage count
        tools_count = len(content.get('tools_used', []))
        if tools_count > 0:
            metadata_parts.append(f"🔧 {tools_count} tools")
        
        st.caption(" | ".join(metadata_parts))
    
    def _get_tool_icon(self, tool_name: str) -> str:
        """Get icon for tool name"""
        tool_icons = {
            'query_mimic_database': '🗄️',
            'search_clinical_documents': '📚',
            'request_visualization': '📊'
        }
        return tool_icons.get(tool_name, '🔧')
    
    def _show_visualization_capabilities(self):
        """Show minimal visualization capabilities overview."""
        st.markdown("""
        El sistema genera visualizaciones con **Plotly** a partir de lenguaje natural.

        **Tipos disponibles:** timeline, comparación, distribución, scatter, heatmap, 
        box plot, violin, 3D, sunburst, treemap, waterfall, sankey, y más.

        **Ejemplos:**
        - "Muestra la evolución de temperatura del paciente 10014729"
        - "Compara presión sistólica y diastólica"
        - "Distribución de diagnósticos por categoría ICD"
        """)
        st.caption("💡 Describe cualquier visualización en tu consulta y el sistema la generará automáticamente.")
    
    def _get_conversation_context(self) -> List[Dict[str, Any]]:
        """
        Get conversation context for agent processing with tool results.
        
        This method now preserves the full message structure including tool_results
        to enable the agent to reference previous data without re-executing tools.
        
        Requirements: 1.1, 2.1, 3.1
        """
        # Get recent messages for context
        max_context = st.session_state.unified_config.get('max_context_messages', 10)
        recent_messages = st.session_state.unified_messages[-max_context:] if len(st.session_state.unified_messages) > max_context else st.session_state.unified_messages
        
        context = []
        for message in recent_messages:
            content = message["content"]
            
            # Preserve full structure for assistant messages with tool results
            if message["role"] == "assistant" and isinstance(content, dict):
                # Keep the full dict structure including tool_results
                context.append({
                    "role": message["role"],
                    "content": content  # Full dict with tool_results
                })
            else:
                # For user messages or simple text, extract text content
                if isinstance(content, dict):
                    content = content.get("content", "")
                
                context.append({
                    "role": message["role"],
                    "content": content
                })
        
        return context
    
    def _save_to_database(self, user_message: str, assistant_response: Dict[str, Any]):
        """
        Save messages to database with metadata.
        
        Requirements: 1.1, 2.1, 3.1
        """
        try:
            if not st.session_state.get('auth_service'):
                return

            # Auto-create a session if none exists (e.g. user entered chat without
            # clicking "Nuevo Chat" explicitly)
            if not st.session_state.get('current_session'):
                logger.info("No active session — auto-creating one before saving messages")
                success, session = st.session_state.auth_service.create_chat_session(
                    st.session_state.user['id'],
                    f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                if success:
                    st.session_state.current_session = session
                    logger.info(f"Auto-created session: {session['id']}")
                else:
                    logger.warning("Could not auto-create session — messages will not be saved")
                    return

            session_id = st.session_state.current_session['id']
            
            # Save user message (no metadata for user messages)
            st.session_state.auth_service.save_message(
                session_id,
                user_message,
                'user'
            )
            
            # Extract response text (handle both string and dict content)
            response_text = assistant_response.get('content', str(assistant_response))
            if isinstance(response_text, dict):
                response_text = response_text.get('content', str(response_text))
            
            # Build metadata for assistant response (no images stored)
            metadata = {
                'tools_used': assistant_response.get('tools_used', []),
                'sources': assistant_response.get('sources', []),
                'execution_time_ms': int(assistant_response.get('processing_time_ms', 0)),
                'has_visualization': bool(assistant_response.get('visualizations')),
                'model_used': assistant_response.get('metadata', {}).get('model_used', 'unknown')
            }
            
            # Save assistant response with metadata
            st.session_state.auth_service.save_message(
                session_id,
                response_text,
                'assistant',
                metadata=metadata
            )
            
            # Guardar análisis en tabla analyses
            self._save_analysis(user_message, assistant_response, metadata)
            
            logger.info(f"Messages saved to database with metadata: tools={metadata['tools_used']}")
            
        except Exception as e:
            logger.warning(f"Error saving to database: {e}")
    def _save_analysis(
        self,
        user_message: str,
        assistant_response: Dict[str, Any],
        metadata: Dict[str, Any],
    ):
        """
        Guarda el análisis en la tabla analyses de Supabase.

        Args:
            user_message: Mensaje del usuario
            assistant_response: Respuesta del agente
            metadata: Metadata de la respuesta
        """
        try:
            user = st.session_state.get('user')
            if not user or not user.get('id'):
                return

            from services.supabase_services import AnalysisService
            analysis_service = AnalysisService()

            # Determinar tipo de análisis basado en herramientas usadas
            tools_used = metadata.get('tools_used', [])
            if len(tools_used) > 1:
                analysis_type = "mixed"
            elif 'query_mimic_database' in tools_used or 'database' in str(tools_used).lower():
                analysis_type = "database_query"
            elif 'rag' in str(tools_used).lower():
                analysis_type = "rag_search"
            elif 'visualization' in str(tools_used).lower():
                analysis_type = "visualization"
            else:
                analysis_type = "general"

            # Preparar resultados
            results = {
                'tools_used': tools_used,
                'execution_time_ms': metadata.get('execution_time_ms', 0),
                'has_visualization': metadata.get('has_visualization', False),
                'model_used': metadata.get('model_used', 'unknown'),
                'sources': metadata.get('sources', []),
                'session_id': st.session_state.get('current_session', {}).get('id'),
            }

            analysis_service.save_analysis(
                user_id=user['id'],
                analysis_type=analysis_type,
                content=user_message,
                results=results,
            )
        except Exception as e:
            # No bloquear el flujo principal
            logger.warning(f"Error guardando análisis: {e}")
    
    def _process_document_upload(self, uploaded_file):
        """
        Process uploaded file for indexing.
        
        Requirements: 4.1, 4.2, 4.4
        """
        try:
            # Show upload progress indicator
            with st.spinner(f"📄 Procesando {uploaded_file.name}..."):
                # Save file temporarily
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Upload and index document
                    result = self._document_manager.upload_document(
                        file_path=tmp_file_path,
                        metadata={
                            'original_filename': uploaded_file.name,
                            'uploaded_by': st.session_state.get('user', {}).get('email', 'unknown'),
                            'upload_timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    # Show upload success/error messages
                    if result.get('success'):
                        st.success(f"✅ {result.get('message', 'Documento indexado exitosamente')}")
                        st.info(f"📊 Procesados {result.get('chunks_processed', 0)} fragmentos")
                        
                        # Add to uploaded documents list
                        st.session_state.uploaded_documents.append({
                            'filename': uploaded_file.name,
                            'uploaded_at': datetime.now().isoformat(),
                            'chunks': result.get('chunks_processed', 0)
                        })
                        
                        # Rerun to update document list
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Error al procesar documento')}")
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
                        
        except Exception as e:
            error_msg = f"Error procesando archivo: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
    
    def _delete_document(self, document_id: str):
        """
        Delete a document from the index.
        
        Requirements: 4.5
        """
        try:
            with st.spinner(f"🗑️ Eliminando {document_id}..."):
                result = self._document_manager.delete_document(document_id)
                
                if result.get('success'):
                    st.success(f"✅ {result.get('message', 'Documento eliminado')}")
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('error', 'Error al eliminar documento')}")
                    
        except Exception as e:
            error_msg = f"Error eliminando documento: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)


# Global unified chat interface instance
unified_chat_interface = UnifiedChatInterface()


def show_unified_chat():
    """Main function to show unified chat interface"""
    unified_chat_interface.show()
