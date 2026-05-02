"""
Document Manager for Unified Chat System

Handles document upload, processing, indexing, and management for the RAG system.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from services.rag.improved_rag_service import ImprovedRAGService, get_rag_service
from src.processors.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentManager:
    """
    Manages document lifecycle for the unified chat system.
    """
    
    def __init__(self):
        """Initialize Document Manager with ImprovedRAGService and document processor"""
        try:
            # Use singleton to avoid re-loading CUDA models on every Streamlit re-run
            self.rag_service = get_rag_service()
            logger.info("RAG service initialized successfully")
            
            # Set up document processor
            self.document_processor = DocumentProcessor()
            logger.info("Document processor initialized successfully")
            
            # Configure metadata management
            self.supported_formats = ['.pdf', '.docx', '.txt']
            self.max_file_size_mb = 50
            
            logger.info("Document Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Document Manager: {e}")
            raise
    
    def upload_document(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Upload and index a document into the RAG system.
        
        Args:
            file_path: Path to the document file
            metadata: Optional metadata to attach to the document
            
        Returns:
            Dictionary with upload status and metadata
            
        Requirements: 4.2, 4.3, 4.4
        """
        try:
            logger.info(f"Starting document upload: {file_path}")
            
            # Validate file path
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    'success': False,
                    'error': f'Archivo no encontrado: {file_path}',
                    'file': file_path
                }
            
            # Validate file type (PDF, DOCX, TXT)
            file_extension = file_path_obj.suffix.lower()
            if file_extension not in self.supported_formats:
                return {
                    'success': False,
                    'error': f'Formato de archivo no soportado: {file_extension}. '
                            f'Formatos permitidos: {", ".join(self.supported_formats)}',
                    'file': file_path
                }
            
            # Validate file size
            file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return {
                    'success': False,
                    'error': f'Archivo demasiado grande: {file_size_mb:.2f}MB. '
                            f'Tamaño máximo: {self.max_file_size_mb}MB',
                    'file': file_path
                }
            
            # Prepare metadata - prioritize original_filename if provided
            original_filename = metadata.get('original_filename') if metadata else None
            display_filename = original_filename if original_filename else file_path_obj.name
            
            doc_metadata = {
                'filename': display_filename,  # Use original filename for display
                'original_filename': original_filename if original_filename else file_path_obj.name,
                'temp_file_path': str(file_path_obj),  # Keep temp path for reference
                'file_size_mb': round(file_size_mb, 2),
                'file_extension': file_extension,
                'uploaded_at': datetime.now().isoformat(),
                'document_type': 'clinical_guide'
            }
            
            # Add custom metadata if provided (but don't override filename)
            if metadata:
                for key, value in metadata.items():
                    if key not in ['filename', 'original_filename']:  # Don't override these
                        doc_metadata[key] = value
            
            # Process document with document processor
            logger.info(f"Processing document: {file_path_obj.name}")
            chunks = self.document_processor.process_document(
                str(file_path_obj),
                doc_metadata
            )
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No se pudo procesar el documento. '
                            'Verifique que el archivo contenga texto extraíble.',
                    'file': file_path
                }
            
            # Index chunks using ImprovedRAGService for proper parent-child
            # chunking and correct collection targeting
            logger.info(f"Indexing document: {len(chunks)} chunks")
            try:
                # Combine all chunk texts into full document text
                # ImprovedRAGService will re-chunk with parent-child strategy
                full_text = "\n\n".join([chunk.page_content for chunk in chunks])
                
                # Index via ImprovedRAGService (stores in Supabase pgvector)
                index_result = self.rag_service.add_text(
                    text=full_text,
                    metadata=doc_metadata
                )
                
                if index_result.get('success', False):
                    index_result['total_chunks'] = index_result.get('child_chunks', 0)
                    index_result['processed_files'] = [{'file': str(file_path_obj), 'chunks': index_result.get('child_chunks', 0)}]
                    logger.info(
                        f"Document indexed successfully: "
                        f"{index_result.get('parent_chunks', 0)} parent chunks, "
                        f"{index_result.get('child_chunks', 0)} child chunks"
                    )
                else:
                    logger.error(f"Error indexing document: {index_result.get('error', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error indexing chunks: {e}")
                index_result = {
                    'success': False,
                    'error': str(e)
                }
            
            if not index_result.get('success', False):
                return {
                    'success': False,
                    'error': f'Error al indexar documento: {index_result.get("error", "Error desconocido")}',
                    'file': file_path
                }
            
            # Registrar documento en Supabase (clinical_documents)
            self._save_to_clinical_documents(doc_metadata)

            # Return upload status and metadata
            return {
                'success': True,
                'message': f'Documento indexado exitosamente: {file_path_obj.name}',
                'file': file_path,
                'metadata': doc_metadata,
                'chunks_processed': len(chunks),
                'index_result': index_result
            }
            
        except Exception as e:
            logger.error(f"Error uploading document {file_path}: {e}")
            return {
                'success': False,
                'error': f'Error al procesar documento: {str(e)}',
                'file': file_path
            }
    
    def list_documents(self) -> Dict[str, Any]:
        """
        List all indexed documents with metadata.
        Combina datos de Supabase pgvector (RAG) con registros de clinical_documents.
        
        Returns:
            Dictionary with success status, documents list, and summary
            
        Requirements: 4.5
        """
        try:
            logger.info("Retrieving list of indexed documents")
            
            # Retrieve document metadata from RAG service
            stats = self.rag_service.get_collection_stats()
            
            if 'error' in stats:
                logger.error(f"Error retrieving collection stats: {stats['error']}")
                return {
                    'success': False,
                    'error': stats['error'],
                    'documents': [],
                    'summary': {
                        'total_documents': 0,
                        'unique_sources': 0,
                        'specialties': [],
                        'collection_name': 'unknown'
                    }
                }
            
            # Get unique sources from collection
            sources = stats.get('sources', [])
            specialties = stats.get('specialties', [])
            total_docs = stats.get('total_documents', 0)
            
            # Obtener registros de Supabase para enriquecer metadata
            supabase_docs = {}
            try:
                from services.supabase_services import ClinicalDocumentService
                doc_service = ClinicalDocumentService()
                success, db_docs = doc_service.list_documents()
                if success:
                    for doc in db_docs:
                        supabase_docs[doc.get('filename', '')] = doc
            except Exception as e:
                logger.debug(f"No se pudo obtener docs de Supabase: {e}")
            
            # Create document entries enriched with Supabase data
            documents = []
            for source in sources:
                doc_entry = {
                    'filename': source,
                    'source': source,
                    'indexed': True,
                    'collection': stats.get('collection_name', 'unknown')
                }
                # Enriquecer con datos de Supabase si existen
                if source in supabase_docs:
                    sb_doc = supabase_docs[source]
                    doc_entry.update({
                        'id': sb_doc.get('id'),
                        'title': sb_doc.get('title'),
                        'document_type': sb_doc.get('document_type'),
                        'specialty': sb_doc.get('specialty'),
                        'upload_date': sb_doc.get('upload_date'),
                        'processed': sb_doc.get('processed', False),
                        'metadata': sb_doc.get('metadata', {}),
                    })
                documents.append(doc_entry)
            
            logger.info(f"Retrieved {len(documents)} documents from collection")
            
            # Add collection summary
            summary = {
                'total_documents': total_docs,
                'unique_sources': len(sources),
                'specialties': specialties,
                'collection_name': stats.get('collection_name', 'unknown'),
                'supabase_synced': len(supabase_docs),
            }
            
            return {
                'success': True,
                'documents': documents,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {
                'success': False,
                'error': str(e),
                'documents': []
            }
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Remove a document from the RAG index.
        
        Args:
            document_id: Identifier for the document (filename or path)
            
        Returns:
            Dictionary with deletion status
            
        Requirements: 4.5
        """
        try:
            logger.info(f"Deleting document: {document_id}")
            
            # Try multiple strategies to find and delete the document
            
            # Strategy 1: Match by original_filename
            filter_dict = {'original_filename': document_id}
            delete_result = self.rag_service.delete_documents(filter_dict)
            
            if not delete_result.get('success', False) or delete_result.get('deleted_count', 0) == 0:
                # Strategy 2: Match by filename
                filter_dict = {'filename': document_id}
                delete_result = self.rag_service.delete_documents(filter_dict)
            
            if not delete_result.get('success', False) or delete_result.get('deleted_count', 0) == 0:
                # Strategy 3: Match by document_id directly
                try:
                    delete_result = self.rag_service.delete_document(document_id)
                    if delete_result.get('success'):
                        return {
                            'success': True,
                            'message': f'Documento eliminado exitosamente: {document_id}',
                            'document_id': document_id,
                            'deleted_count': delete_result.get('deleted_parent_chunks', 0)
                        }
                except Exception:
                    pass
            
            # Handle deletion errors
            if not delete_result.get('success', False):
                return {
                    'success': False,
                    'error': f'Error al eliminar documento: {delete_result.get("error", "Documento no encontrado")}',
                    'document_id': document_id
                }
            
            deleted_count = delete_result.get('deleted_count', 0)
            
            if deleted_count == 0:
                return {
                    'success': False,
                    'error': f'Documento no encontrado: {document_id}',
                    'document_id': document_id
                }
            
            # Eliminar también de clinical_documents en Supabase
            self._delete_from_clinical_documents(document_id)
            
            return {
                'success': True,
                'message': f'Documento eliminado exitosamente: {document_id}',
                'document_id': document_id,
                'deleted_count': deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                'success': False,
                'error': f'Error al eliminar documento: {str(e)}',
                'document_id': document_id
            }
    
    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific document.
        
        Args:
            document_id: Identifier for the document
            
        Returns:
            Dictionary with document information
        """
        try:
            logger.info(f"Retrieving document info: {document_id}")
            
            # Search for document in collection
            search_results = self.rag_service.search_clinical_guidelines(
                query=document_id,
                top_k=10
            )
            
            # Filter results to match document_id
            matching_docs = [
                doc for doc in search_results
                if doc.get('metadata', {}).get('filename') == document_id or
                   doc.get('source') == document_id
            ]
            
            if not matching_docs:
                return {
                    'success': False,
                    'error': f'Documento no encontrado: {document_id}'
                }
            
            # Aggregate document information
            doc_info = {
                'success': True,
                'document_id': document_id,
                'chunks_count': len(matching_docs),
                'metadata': matching_docs[0].get('metadata', {}),
                'source': matching_docs[0].get('source', 'unknown')
            }
            
            return doc_info
            
        except Exception as e:
            logger.error(f"Error retrieving document info for {document_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_document(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a document before upload.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Use document processor's validation
            validation_result = self.document_processor.validate_document(file_path)
            
            # Add additional checks
            file_path_obj = Path(file_path)
            
            if validation_result.get('valid', False):
                # Check file size against our limits
                file_size_mb = validation_result.get('file_info', {}).get('size_mb', 0)
                if file_size_mb > self.max_file_size_mb:
                    validation_result['valid'] = False
                    validation_result['errors'].append(
                        f'Archivo demasiado grande: {file_size_mb}MB. '
                        f'Máximo permitido: {self.max_file_size_mb}MB'
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating document {file_path}: {e}")
            return {
                'valid': False,
                'errors': [f'Error en validación: {str(e)}'],
                'warnings': []
            }
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported document formats.
        
        Returns:
            List of supported file extensions
        """
        return self.supported_formats
    
    def get_max_file_size(self) -> int:
        """
        Get maximum allowed file size in MB.
        
        Returns:
            Maximum file size in megabytes
        """
        return self.max_file_size_mb
    def _save_to_clinical_documents(self, doc_metadata: Dict[str, Any]) -> None:
        """
        Registra el documento en la tabla clinical_documents de Supabase.

        Args:
            doc_metadata: Metadata del documento procesado
        """
        try:
            from services.supabase_services import ClinicalDocumentService
            doc_service = ClinicalDocumentService()

            success, record = doc_service.save_document(
                filename=doc_metadata.get('original_filename', doc_metadata.get('filename', '')),
                title=doc_metadata.get('description') or doc_metadata.get('filename', ''),
                document_type=doc_metadata.get('document_type'),
                specialty=doc_metadata.get('specialty'),
                file_path=doc_metadata.get('temp_file_path'),
                metadata={
                    'file_size_mb': doc_metadata.get('file_size_mb'),
                    'file_extension': doc_metadata.get('file_extension'),
                    'uploaded_at': doc_metadata.get('uploaded_at'),
                    'chunks_info': doc_metadata.get('processing_config', {}),
                },
            )

            if success and record:
                doc_service.mark_as_processed(record['id'])
                logger.info(f"Documento registrado en clinical_documents: {record['id']}")
            else:
                logger.warning("No se pudo registrar documento en clinical_documents")
        except Exception as e:
            # No bloquear el flujo principal si falla el registro en Supabase
            logger.warning(f"Error registrando documento en Supabase: {e}")
    def _delete_from_clinical_documents(self, document_id: str) -> None:
        """
        Elimina el registro del documento de la tabla clinical_documents en Supabase.

        Args:
            document_id: Nombre del archivo o ID del documento
        """
        try:
            from services.supabase_services import ClinicalDocumentService
            doc_service = ClinicalDocumentService()
            doc_service.delete_by_filename(document_id)
            logger.info(f"Documento eliminado de clinical_documents: {document_id}")
        except Exception as e:
            logger.warning(f"Error eliminando documento de Supabase: {e}")
