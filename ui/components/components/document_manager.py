
"""
Gestor de documentos clínicos para el sistema RAG
"""
import streamlit as st
import tempfile
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from src.processors.document_processor import DocumentProcessor
from services.rag.improved_rag_service import ImprovedRAGService, get_rag_service
from services.auth.session_manager import SessionManager
from utils.helpers.utils import FileUtils, ValidationUtils
from config.config import MEDICAL_SPECIALTIES, DOCUMENT_TYPES, RAG_CONFIG

class DocumentManager:
    """Gestor completo de documentos clínicos"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.rag_service = get_rag_service()  # singleton — avoids CUDA re-load
        self.max_file_size_mb = RAG_CONFIG["max_file_size_mb"]
        self.supported_formats = RAG_CONFIG["supported_formats"]
    
    def render_interface(self):
        """Renderiza la interfaz principal de gestión de documentos"""
        st.subheader("📚 Gestión de Documentos Clínicos")
        
        # Tabs principales
        tab1, tab2, tab3, tab4 = st.tabs([
            "📤 Subir Documentos", 
            "📋 Documentos Existentes", 
            "📊 Estadísticas", 
            "⚙️ Configuración"
        ])
        
        with tab1:
            self._render_upload_interface()
        
        with tab2:
            self._render_document_list()
        
        with tab3:
            self._render_statistics()
        
        with tab4:
            self._render_settings()
    
    def _render_upload_interface(self):
        """Interfaz para subir nuevos documentos"""
        st.markdown("### 📤 Añadir Nuevas Guías Clínicas")
        
        # Información sobre el proceso
        with st.expander("ℹ️ Información sobre la carga de documentos", expanded=False):
            st.markdown("""
            **¿Qué documentos puedo subir?**
            - Guías clínicas hospitalarias
            - Protocolos de actuación médica
            - Manuales de procedimientos
            - Algoritmos de decisión clínica
            - Consensos de sociedades médicas
            
            **Formatos soportados:** PDF
            **Tamaño máximo:** 50 MB por archivo
            **Procesamiento:** Los documentos se procesan automáticamente y se indexan para búsquedas
            """)
        
        # Formulario de carga
        with st.form("document_upload_form"):
            # Carga de archivos múltiples
            uploaded_files = st.file_uploader(
                "Selecciona los documentos clínicos",
                type=['pdf'],
                accept_multiple_files=True,
                help=f"Puedes subir múltiples archivos PDF. Máximo {self.max_file_size_mb}MB por archivo."
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} archivo(s) seleccionado(s)")
                
                # Mostrar lista de archivos
                for file in uploaded_files:
                    file_size_mb = len(file.getvalue()) / (1024 * 1024)
                    st.write(f"📄 {file.name} ({file_size_mb:.2f} MB)")
            
            # Metadatos
            # Especialidad fija: Urgencias
            specialty = "urgencias"
            st.info("🏥 **Especialidad:** Urgencias y Emergencias (MIMIC-IV-ED)")
            st.caption("🔜 Próximamente: Más especialidades disponibles")
            
            # Tipo de documento
            document_type = st.selectbox(
                "📋 Tipo de Documento",
                [""] + list(DOCUMENT_TYPES.keys()),
                format_func=lambda x: "Seleccionar..." if x == "" else DOCUMENT_TYPES[x]["name"],
                help="Tipo de documento clínico"
            )
            
            # Descripción opcional
            description = st.text_area(
                "📝 Descripción (Opcional)",
                placeholder="Breve descripción del contenido del documento...",
                help="Descripción que ayudará en las búsquedas"
            )
            
            # Configuraciones de procesamiento
            with st.expander("⚙️ Configuraciones de Procesamiento", expanded=False):
                chunk_size = st.slider(
                    "Tamaño de segmentos",
                    min_value=500,
                    max_value=2000,
                    value=RAG_CONFIG["chunk_size"],
                    help="Tamaño de los segmentos de texto para indexación"
                )
                
                chunk_overlap = st.slider(
                    "Solapamiento entre segmentos",
                    min_value=50,
                    max_value=500,
                    value=RAG_CONFIG["chunk_overlap"],
                    help="Solapamiento entre segmentos consecutivos"
                )
                
                enable_ocr = st.checkbox(
                    "Habilitar OCR",
                    value=RAG_CONFIG["ocr_enabled"],
                    help="Extraer texto de imágenes en el PDF"
                )
            
            # Botón de procesamiento
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                process_button = st.form_submit_button(
                    "🚀 Procesar y Añadir Documentos",
                    use_container_width=True,
                    type="primary"
                )
            
            if process_button:
                if not uploaded_files:
                    st.error("❌ Selecciona al menos un archivo")
                elif not document_type:
                    st.error("❌ Selecciona un tipo de documento")
                else:
                    self._process_uploaded_files(
                        uploaded_files,
                        {
                            'specialty': specialty,
                            'document_type': document_type,
                            'description': description,
                            'chunk_size': chunk_size,
                            'chunk_overlap': chunk_overlap,
                            'enable_ocr': enable_ocr
                        }
                    )
    
    def _process_uploaded_files(self, uploaded_files: List, metadata: Dict[str, Any]):
        """Procesa los archivos subidos"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            total_files = len(uploaded_files)
            processed_files = []
            failed_files = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                # Actualizar progreso
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"📄 Procesando: {uploaded_file.name}")
                
                try:
                    # Crear archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # Validar archivo
                    validation = self.document_processor.validate_document(tmp_file_path)
                    
                    if not validation['valid']:
                        failed_files.append({
                            'file': uploaded_file.name,
                            'errors': validation['errors']
                        })
                        os.unlink(tmp_file_path)
                        continue
                    
                    # Preparar metadata completa
                    file_metadata = metadata.copy()
                    file_metadata.update({
                        'filename': uploaded_file.name,
                        'uploaded_by': st.session_state.user['id'],
                        'uploaded_at': datetime.now().isoformat(),
                        'file_size': len(uploaded_file.getvalue()),
                        'processing_config': {
                            'chunk_size': metadata['chunk_size'],
                            'chunk_overlap': metadata['chunk_overlap'],
                            'ocr_enabled': metadata['enable_ocr']
                        }
                    })
                    
                    # Procesar documento
                    chunks = self.document_processor.process_document(tmp_file_path, file_metadata)
                    
                    if chunks:
                        # Añadir al vector store via ImprovedRAGService
                        full_text = "\n\n".join([chunk.page_content for chunk in chunks])
                        result = self.rag_service.add_text(
                            text=full_text,
                            metadata=file_metadata
                        )
                        
                        if result.get('success', False):
                            processed_files.append({
                                'file': uploaded_file.name,
                                'chunks': result.get('child_chunks', len(chunks))
                            })
                        else:
                            failed_files.append({
                                'file': uploaded_file.name,
                                'errors': [result.get('error', 'Error desconocido')]
                            })
                    else:
                        failed_files.append({
                            'file': uploaded_file.name,
                            'errors': ['No se pudieron extraer chunks del documento']
                        })
                    
                    # Limpiar archivo temporal
                    os.unlink(tmp_file_path)
                    
                except Exception as e:
                    failed_files.append({
                        'file': uploaded_file.name,
                        'errors': [str(e)]
                    })
                    if 'tmp_file_path' in locals():
                        try:
                            os.unlink(tmp_file_path)
                        except:
                            pass
            
            # Mostrar resultados
            self._show_processing_results(processed_files, failed_files)
            
        except Exception as e:
            st.error(f"❌ Error general en procesamiento: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()
    
    def _show_processing_results(self, processed_files: List[Dict], failed_files: List[Dict]):
        """Muestra los resultados del procesamiento"""
        if processed_files:
            st.success(f"✅ {len(processed_files)} archivo(s) procesado(s) exitosamente")
            
            with st.expander("📋 Detalles de archivos procesados", expanded=True):
                for file_info in processed_files:
                    st.write(f"✅ **{file_info['file']}** - {file_info['chunks']} segmentos creados")
        
        if failed_files:
            st.error(f"❌ {len(failed_files)} archivo(s) fallaron en el procesamiento")
            
            with st.expander("⚠️ Detalles de errores", expanded=True):
                for file_info in failed_files:
                    st.write(f"❌ **{file_info['file']}**")
                    for error in file_info['errors']:
                        st.write(f"   • {error}")
        
        # Botón para actualizar estadísticas
        if st.button("🔄 Actualizar Vista", use_container_width=True):
            st.rerun()
    
    def _render_document_list(self):
        """Muestra lista de documentos existentes"""
        st.markdown("### 📋 Documentos en la Base de Conocimiento")
        
        try:
            # Obtener información de la colección
            collection_info = self.rag_service.get_collection_stats()
            
            if 'error' in collection_info:
                st.error(f"❌ Error obteniendo información: {collection_info['error']}")
                return
            
            total_docs = collection_info.get('total_documents', 0)
            
            if total_docs == 0:
                st.info("📭 No hay documentos en la base de conocimiento. ¡Sube algunos documentos para empezar!")
                return
            
            # Estadísticas rápidas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📄 Total Documentos", total_docs)
            
            with col2:
                specialties = collection_info.get('specialties', [])
                st.metric("🏥 Especialidades", len(specialties))
            
            with col3:
                sources = collection_info.get('sources', [])
                st.metric("📚 Fuentes", len(sources))
            
            # Filtros
            st.markdown("#### 🔍 Filtros")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                specialty_filter = st.selectbox(
                    "Especialidad",
                    ["Todas"] + specialties,
                    key="doc_list_specialty"
                )
            
            with col2:
                doc_types = collection_info.get('document_types', [])
                type_filter = st.selectbox(
                    "Tipo de Documento",
                    ["Todos"] + doc_types,
                    key="doc_list_type"
                )
            
            with col3:
                search_term = st.text_input(
                    "Buscar en documentos",
                    placeholder="Término de búsqueda...",
                    key="doc_search"
                )
            
            # Lista de documentos
            if search_term:
                self._show_search_results(search_term, specialty_filter, type_filter)
            else:
                self._show_document_sources(sources, specialty_filter, type_filter)
            
        except Exception as e:
            st.error(f"❌ Error cargando documentos: {str(e)}")
    
    def _show_search_results(self, search_term: str, specialty_filter: str, type_filter: str):
        """Muestra resultados de búsqueda en documentos"""
        try:
            # Construir filtros
            filters = {}
            if specialty_filter != "Todas":
                filters['specialty'] = specialty_filter
            if type_filter != "Todos":
                filters['document_type'] = type_filter
            
            # Realizar búsqueda
            results = self.rag_service.search_clinical_guidelines(
                query=search_term,
                top_k=20
            )
            
            if not results:
                st.info("🔍 No se encontraron resultados para la búsqueda")
                return
            
            st.markdown(f"#### 🔍 Resultados de búsqueda: '{search_term}'")
            st.caption(f"Se encontraron {len(results)} segmentos relevantes")
            
            for i, result in enumerate(results, 1):
                with st.expander(f"📄 Resultado {i} - {result['metadata'].get('filename', 'Desconocido')}", expanded=False):
                    # Metadata
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Especialidad:** {result['metadata'].get('specialty', 'No especificada')}")
                        st.write(f"**Tipo:** {result['metadata'].get('document_type', 'No especificado')}")
                    
                    with col2:
                        st.write(f"**Relevancia:** {1 - result.get('distance', 0):.2%}")
                        st.write(f"**Chunk ID:** {result['metadata'].get('chunk_id', 'N/A')}")
                    
                    # Contenido
                    st.markdown("**Contenido:**")
                    content = result['content']
                    if len(content) > 500:
                        st.text(content[:500] + "...")
                        if st.button(f"Ver completo", key=f"expand_{i}"):
                            st.text(content)
                    else:
                        st.text(content)
            
        except Exception as e:
            st.error(f"❌ Error en búsqueda: {str(e)}")
    
    def _show_document_sources(self, sources: List[str], specialty_filter: str, type_filter: str):
        """Muestra fuentes de documentos"""
        st.markdown("#### 📚 Fuentes de Documentos")
        
        # Filtrar fuentes si es necesario
        filtered_sources = sources
        
        if not filtered_sources:
            st.info("📭 No hay documentos que coincidan con los filtros seleccionados")
            return
        
        for source in filtered_sources:
            with st.expander(f"📄 {source}", expanded=False):
                # Obtener información del documento
                try:
                    # Buscar información específica del documento
                    doc_results = self.rag_service.search_clinical_guidelines(
                        query=source,
                        top_k=1
                    )
                    
                    if doc_results:
                        metadata = doc_results[0].get('metadata', {})
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Especialidad:** {metadata.get('specialty', 'No especificada')}")
                            st.write(f"**Tipo:** {metadata.get('document_type', 'No especificado')}")
                            st.write(f"**Institución:** {metadata.get('institution', 'No especificada')}")
                        
                        with col2:
                            st.write(f"**Versión:** {metadata.get('version', 'No especificada')}")
                            st.write(f"**Subido:** {metadata.get('uploaded_at', 'Fecha desconocida')}")
                            st.write(f"**Tamaño:** {metadata.get('file_size', 0) / 1024:.1f} KB")
                        
                        if metadata.get('description'):
                            st.write(f"**Descripción:** {metadata['description']}")
                        
                        # Acciones
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button(f"🔍 Buscar en documento", key=f"search_{source}"):
                                st.session_state[f"search_in_{source}"] = True
                        
                        with col2:
                            if st.button(f"📊 Ver estadísticas", key=f"stats_{source}"):
                                st.session_state[f"stats_{source}"] = True
                        
                        with col3:
                            if st.button(f"🗑️ Eliminar", key=f"delete_{source}", type="secondary"):
                                st.session_state[f"confirm_delete_{source}"] = True
                        
                        # Confirmación de eliminación
                        if st.session_state.get(f"confirm_delete_{source}"):
                            st.warning("⚠️ ¿Estás seguro de que quieres eliminar este documento?")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("✅ Confirmar", key=f"confirm_yes_{source}"):
                                    self._delete_document(source)
                                    st.session_state[f"confirm_delete_{source}"] = False
                                    st.rerun()
                            
                            with col2:
                                if st.button("❌ Cancelar", key=f"confirm_no_{source}"):
                                    st.session_state[f"confirm_delete_{source}"] = False
                                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error obteniendo información del documento: {str(e)}")
    
    def _delete_document(self, filename: str):
        """Elimina un documento de la base de conocimiento"""
        try:
            result = self.rag_service.delete_documents(
                filter_dict={'filename': filename}
            )
            
            if result.get('success'):
                st.success(f"✅ Documento '{filename}' eliminado correctamente")
            else:
                st.error(f"❌ Error eliminando documento: {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            st.error(f"❌ Error eliminando documento: {str(e)}")
    
    def _render_statistics(self):
        """Muestra estadísticas de la base de conocimiento"""
        st.markdown("### 📊 Estadísticas de la Base de Conocimiento")
        
        try:
            collection_info = self.rag_service.get_collection_stats()
            
            if 'error' in collection_info:
                st.error(f"❌ Error obteniendo estadísticas: {collection_info['error']}")
                return
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "📄 Total Documentos",
                    collection_info.get('total_documents', 0)
                )
            
            with col2:
                specialties = collection_info.get('specialties', [])
                st.metric(
                    "🏥 Especialidades",
                    len(specialties)
                )
            
            with col3:
                sources = collection_info.get('sources', [])
                st.metric(
                    "📚 Fuentes",
                    len(sources)
                )
            
            with col4:
                doc_types = collection_info.get('document_types', [])
                st.metric(
                    "📋 Tipos de Doc.",
                    len(doc_types)
                )
            
            # Gráficos de distribución
            col1, col2 = st.columns(2)
            
            with col1:
                if specialties:
                    st.markdown("#### 🏥 Distribución por Especialidades")
                    # Aquí se podría añadir un gráfico con plotly
                    for specialty in specialties:
                        st.write(f"• {MEDICAL_SPECIALTIES.get(specialty, {}).get('name', specialty)}")
            
            with col2:
                if doc_types:
                    st.markdown("#### 📋 Distribución por Tipos")
                    for doc_type in doc_types:
                        st.write(f"• {DOCUMENT_TYPES.get(doc_type, {}).get('name', doc_type)}")
            
            # Información técnica
            st.markdown("#### ⚙️ Información Técnica")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Colección:** {collection_info.get('collection_name', 'N/A')}")
                st.write(f"**Directorio:** {collection_info.get('persist_directory', 'N/A')}")
            
            with col2:
                st.write(f"**Modelo de Embeddings:** {RAG_CONFIG['embedding_model']}")
                st.write(f"**Tamaño de Chunk:** {RAG_CONFIG['chunk_size']} caracteres")
            
        except Exception as e:
            st.error(f"❌ Error cargando estadísticas: {str(e)}")
    
    def _render_settings(self):
        """Muestra configuraciones del sistema RAG"""
        st.markdown("### ⚙️ Configuración del Sistema RAG")
        
        # Configuraciones de búsqueda
        st.markdown("#### 🔍 Configuración de Búsqueda")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_type = st.selectbox(
                "Tipo de búsqueda",
                ["similarity", "mmr"],
                index=0 if RAG_CONFIG["search_type"] == "similarity" else 1,
                help="Similarity: búsqueda por similitud. MMR: máxima relevancia marginal"
            )
            
            top_k = st.slider(
                "Número de resultados",
                min_value=1,
                max_value=20,
                value=RAG_CONFIG["top_k"],
                help="Número de segmentos a recuperar en cada búsqueda"
            )
        
        with col2:
            fetch_k = st.slider(
                "Candidatos a evaluar",
                min_value=10,
                max_value=100,
                value=RAG_CONFIG["fetch_k"],
                help="Número de candidatos a evaluar antes de seleccionar los mejores"
            )
        
        # Configuraciones de procesamiento
        st.markdown("#### 📄 Configuración de Procesamiento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            chunk_size = st.slider(
                "Tamaño de segmentos",
                min_value=500,
                max_value=3000,
                value=RAG_CONFIG["chunk_size"],
                help="Tamaño en caracteres de cada segmento de texto"
            )
        
        with col2:
            chunk_overlap = st.slider(
                "Solapamiento",
                min_value=50,
                max_value=500,
                value=RAG_CONFIG["chunk_overlap"],
                help="Solapamiento entre segmentos consecutivos"
            )
        
        # Acciones de mantenimiento
        st.markdown("#### 🔧 Mantenimiento")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Reconstruir Índice", use_container_width=True):
                with st.spinner("Reconstruyendo índice..."):
                    result = self.rag_service.rebuild_index()
                    if result['success']:
                        st.success("✅ Índice reconstruido correctamente")
                    else:
                        st.error(f"❌ Error: {result['error']}")
        
        with col2:
            if st.button("📤 Exportar Colección", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = f"./data/exports/collection_export_{timestamp}.json"
                
                with st.spinner("Exportando colección..."):
                    result = self.rag_service.export_collection(export_path)
                    if result['success']:
                        st.success(f"✅ Colección exportada: {export_path}")
                    else:
                        st.error(f"❌ Error: {result['error']}")
        
        with col3:
            if st.button("🗑️ Limpiar Colección", use_container_width=True, type="secondary"):
                st.session_state.confirm_reset = True
        
        # Confirmación de limpieza
        if st.session_state.get('confirm_reset'):
            st.warning("⚠️ ¿Estás seguro de que quieres eliminar TODOS los documentos?")
            st.error("Esta acción NO se puede deshacer")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Confirmar Limpieza", type="primary"):
                    with st.spinner("Limpiando colección..."):
                        result = self.rag_service.reset_collection()
                        if result['success']:
                            st.success("✅ Colección limpiada correctamente")
                        else:
                            st.error(f"❌ Error: {result['error']}")
                    st.session_state.confirm_reset = False
                    st.rerun()
            
            with col2:
                if st.button("❌ Cancelar"):
                    st.session_state.confirm_reset = False
                    st.rerun()

def show_document_manager():
    """Función principal para mostrar el gestor de documentos"""
    try:
        # Verificar autenticación
        if not SessionManager.is_authenticated():
            st.error("❌ Debes iniciar sesión para gestionar documentos")
            return
        
        # Crear y mostrar interfaz
        manager = DocumentManager()
        manager.render_interface()
        
    except Exception as e:
        st.error(f"❌ Error inicializando gestor de documentos: {str(e)}")
        
        # Mostrar detalles en modo debug
        if st.checkbox("Mostrar detalles del error"):
            st.exception(e)

