"""
RAG Tool for Unified Chat System

This module provides RAG (Retrieval-Augmented Generation) functionality for the unified chat system.
It allows searching clinical documents and guidelines that have been uploaded to the system.

Updated to use ImprovedRAGService with:
- Parent-Child Chunking for better context retrieval
- Hybrid Search (pgvector + tsvector) with RRF fusion
- Cross-encoder Reranking for improved relevance

Requirements: 1.2, 2.1, 3.1
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.medical_agent.tools.claude_adapter import ClaudeToolAdapter
from services.rag.improved_rag_service import ImprovedRAGService, get_rag_service
from services.rag.query_augmenter import QueryAugmenter

logger = logging.getLogger(__name__)


class RAGQueryInput(BaseModel):
    """Input schema for RAG query tool."""
    query: str = Field(
        description="The search query to find relevant clinical documents and guidelines"
    )
    specialty: Optional[str] = Field(
        None, 
        description="Optional specialty filter (e.g., 'cardiology', 'emergency', 'pediatrics')"
    )
    top_k: Optional[int] = Field(
        None,
        description="Number of documents to retrieve (default: 5)"
    )


class RAGTool(ClaudeToolAdapter):
    """
    RAG tool for searching clinical documents and guidelines.
    
    This tool provides enhanced search across uploaded clinical documents,
    protocols, and guidelines using:
    - Hybrid search (pgvector + tsvector semantic/lexical search)
    - Cross-encoder reranking for improved relevance
    - Parent-child chunking for better context retrieval
    
    Requirements: 1.2, 2.1, 3.1
    """
    
    def __init__(self):
        """Initialize the RAG tool with ImprovedRAGService and QueryAugmenter."""
        # Use singleton to avoid re-loading CUDA models on Streamlit re-runs
        self.rag_service = get_rag_service()
        
        # Initialize query augmenter for LLM-based query expansion
        self.query_augmenter = QueryAugmenter()
        
        # Initialize the adapter with tool metadata
        super().__init__(
            tool_name="search_clinical_documents",
            tool_description="""Herramienta para buscar en guías clínicas, protocolos y documentos médicos indexados.

DOCUMENTOS DISPONIBLES EN EL SISTEMA:
- Manual del Residente de Medicina Intensiva (Hospital Universitario Virgen del Rocío)
- Estándares y Recomendaciones para UCI (Ministerio de Sanidad España)
- El Libro de la UCI - Paul L. Marino, 3ª Edición

CUÁNDO USAR ESTA HERRAMIENTA (OBLIGATORIO si la pregunta no tiene subject_id/stay_id):
- Preguntas sobre UCI, cuidados críticos, medicina intensiva
- Estructura y organización de unidades médicas (camas, niveles asistenciales, ratios)
- Ratios médico-paciente y enfermera-paciente
- Formación médica especializada (residentes, rotaciones, competencias)
- Protocolos clínicos de cualquier especialidad (urgencias, UCI, cardiología, etc.)
- Guías de tratamiento para condiciones específicas
- Información sobre medicamentos (dosificación, indicaciones, contraindicaciones)
- Procedimientos médicos y técnicas clínicas
- Seguridad del paciente, indicadores de calidad, eventos adversos
- Cualquier pregunta de conocimiento médico general sin datos de paciente específico

PARÁMETROS:
- query (requerido): La pregunta o búsqueda a realizar
- specialty (opcional): Filtrar por especialidad (ej: 'medicina_intensiva')
- top_k (opcional): Número de documentos a recuperar (por defecto: 5)

EJEMPLOS:
- UCI: {"query": "ratio médico-paciente UCI nivel III"}
- Formación: {"query": "duración formación medicina intensiva rotaciones"}
- Protocolo: {"query": "protocolo sepsis shock séptico tratamiento"}
- Medicamento: {"query": "dosis noradrenalina shock séptico adultos"}
- Seguridad: {"query": "incidentes eventos adversos UCI SEMICYUC"}

IMPORTANTE:
- Esta herramienta busca en documentos SUBIDOS al sistema
- NO tiene acceso a datos de pacientes específicos (usa query_mimic_database para eso)
- Siempre cita las fuentes de los documentos encontrados""",
            args_schema=RAGQueryInput
        )
        
        logger.info("RAGTool initialized")
    
    def execute(self, query: str, specialty: Optional[str] = None, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute RAG search with query augmentation and improved hybrid search.
        
        Flow:
        1. Augment the original query using Claude Haiku (multi-query + HyDE)
        2. Search with each augmented query via ImprovedRAGService
        3. Merge and deduplicate results across all queries
        4. Return top_k best results sorted by score
        
        Args:
            query: The search query
            specialty: Optional specialty filter
            top_k: Number of documents to retrieve (default: 5)
            
        Returns:
            Dictionary with search results and sources
            
        Requirements: 1.2, 2.1, 3.1
        """
        try:
            k = top_k or 8  # Increased from 5 to improve recall for specific fragments
            
            logger.info(f"Executing augmented RAG search: query='{query[:50]}...', specialty={specialty}, top_k={k}")
            
            # Step 1: Augment query using Claude Haiku
            augmented_queries = self.query_augmenter.augment(query)
            logger.info(f"Query augmented into {len(augmented_queries)} queries")
            
            # Step 2: Search with each augmented query
            all_results = []
            seen_content_hashes = set()
            
            for i, aug_query in enumerate(augmented_queries):
                try:
                    if specialty:
                        results = self.rag_service.search_with_filter(
                            query=aug_query,
                            filter_dict={'specialty': specialty},
                            top_k=k
                        )
                    else:
                        results = self.rag_service.search(
                            query=aug_query,
                            top_k=k,
                            rerank=True
                        )
                    
                    # Deduplicate by content hash
                    for result in results:
                        content_hash = hash(result.get('content', '')[:200])
                        if content_hash not in seen_content_hashes:
                            seen_content_hashes.add(content_hash)
                            all_results.append(result)
                            
                except Exception as e:
                    logger.warning(f"Search failed for augmented query {i}: {e}")
                    continue
            
            # Step 3: Sort by score and take top_k
            all_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            final_results = all_results[:k]
            
            # Handle empty results
            if not final_results:
                return {
                    'success': True,
                    'found_documents': False,
                    'message': 'No se encontraron documentos relevantes para esta consulta.',
                    'suggestion': 'Intente reformular la pregunta o suba documentos relacionados con el tema.',
                    'documents': [],
                    'augmented_queries_used': len(augmented_queries)
                }
            
            # Format results with source citations
            formatted_results = {
                'success': True,
                'found_documents': True,
                'total_documents': len(final_results),
                'augmented_queries_used': len(augmented_queries),
                'documents': []
            }
            
            for i, doc in enumerate(final_results, 1):
                formatted_doc = {
                    'rank': i,
                    'content': doc.get('content', ''),
                    'source': self._format_source(doc.get('metadata', {})),
                    'metadata': doc.get('metadata', {}),
                    'score': doc.get('score', 0.0),
                    'child_content': doc.get('child_content', '')
                }
                formatted_results['documents'].append(formatted_doc)
            
            logger.info(
                f"Augmented RAG search completed: {len(final_results)} documents "
                f"from {len(augmented_queries)} queries"
            )
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error ejecutando búsqueda RAG aumentada: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'documents': []
            }
    
    def _format_source(self, metadata: Dict[str, Any]) -> str:
        """
        Format document source information for citation.
        
        Args:
            metadata: Document metadata
            
        Returns:
            Formatted source citation string
        """
        parts = []
        
        # Add filename
        if 'filename' in metadata:
            parts.append(f"Documento: {metadata['filename']}")
        
        # Add page number if available
        if 'page' in metadata:
            parts.append(f"Página: {metadata['page']}")
        
        # Add specialty if available
        if 'specialty' in metadata:
            parts.append(f"Especialidad: {metadata['specialty']}")
        
        # Add document type if available
        if 'document_type' in metadata:
            parts.append(f"Tipo: {metadata['document_type']}")
        
        # Add upload date if available
        if 'upload_date' in metadata:
            parts.append(f"Fecha: {metadata['upload_date']}")
        
        return " | ".join(parts) if parts else "Fuente desconocida"
    
    def get_langchain_tool(self):
        """
        Override to wrap execute + format_output so the agent sees
        well-formatted text with clear source citations instead of raw dicts.
        """
        from langchain_core.tools import StructuredTool

        def _execute_and_format(**kwargs) -> str:
            result = self.execute(**kwargs)
            return self.format_output(result)

        return StructuredTool.from_function(
            func=_execute_and_format,
            name=self.tool_name,
            description=self.tool_description,
            args_schema=self.args_schema,
            return_direct=False
        )

    def format_output(self, output_data: Any) -> str:
        """
        Format output for Claude consumption with clear source citations.
        
        Args:
            output_data: Output from tool execution
            
        Returns:
            Formatted output string with document content and source citations
        """
        if not isinstance(output_data, dict):
            return str(output_data)
        
        # Check if search was successful
        if not output_data.get('success', False):
            return f"❌ Error: {output_data.get('error', 'Error desconocido')}"
        
        # Check if documents were found
        if not output_data.get('found_documents', False):
            lines = [
                "📚 Búsqueda en Documentos Clínicos",
                "",
                output_data.get('message', 'No se encontraron documentos.'),
                "",
                f"Sugerencia: {output_data.get('suggestion', 'Intente con otra consulta.')}"
            ]
            return "\n".join(lines)
        
        documents = output_data.get('documents', [])
        
        # Format document content
        lines = [
            f"Se encontraron {len(documents)} documentos relevantes.",
            ""
        ]
        
        for doc in documents:
            source = doc.get('source', 'Fuente desconocida')
            lines.append(f"--- Documento {doc['rank']}: {source} ---")
            content = doc.get('content', '')
            if len(content) > 1500:
                content = content[:1500] + "..."
            lines.append(content)
            lines.append("")
        
        # Add explicit source citation section for Claude to reference
        lines.append("=== FUENTES CITADAS ===")
        lines.append("IMPORTANTE: Cita estas fuentes en tu respuesta al usuario.")
        lines.append("")
        for doc in documents:
            metadata = doc.get('metadata', {})
            filename = metadata.get('filename', 'Documento desconocido')
            page = metadata.get('page')
            specialty = metadata.get('specialty')
            doc_type = metadata.get('document_type')
            
            citation_parts = [f"[{doc['rank']}] 📄 {filename}"]
            if page:
                citation_parts.append(f"p. {page}")
            if specialty:
                citation_parts.append(f"Especialidad: {specialty}")
            if doc_type:
                citation_parts.append(f"Tipo: {doc_type}")
            
            lines.append(" | ".join(citation_parts))
        
        return "\n".join(lines)


def create_rag_tool() -> RAGTool:
    """
    Create a RAG tool instance.
    
    Returns:
        RAGTool instance
    """
    return RAGTool()
