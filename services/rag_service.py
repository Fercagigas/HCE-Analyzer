
"""
Servicio RAG integrado para consultas sobre guías clínicas
"""
import os
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from src.processors.document_processor import DocumentProcessor
from config.config import RAG_CONFIG, HUGGINGFACE_API_TOKEN
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    """Servicio principal para funcionalidades RAG"""
    
    def __init__(self):
        self.config = RAG_CONFIG
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self.document_processor = DocumentProcessor()
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa componentes RAG"""
        try:
            # Verificar API key de GROQ
            if not GROQ_API_KEY:
                logger.warning("GROQ_API_KEY no configurada, algunas funcionalidades estarán limitadas")
                return
            
            # Inicializar embeddings
            model_kwargs = {'device': 'cpu'}
            if HUGGINGFACE_API_TOKEN:
                model_kwargs['use_auth_token'] = HUGGINGFACE_API_TOKEN
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.config["embedding_model"],
                model_kwargs=model_kwargs,
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("Embeddings inicializados correctamente")
            
            # Inicializar ChromaDB
            self._initialize_vectorstore()
            
            # Inicializar LLM
            self.llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name=self.config["llm_model"],
                temperature=0.3,
                max_tokens=2048
            )
            logger.info("LLM inicializado correctamente")
            
            # Inicializar cadena QA
            self._initialize_qa_chain()
            
        except Exception as e:
            logger.error(f"Error inicializando componentes RAG: {e}")
            raise
    
    def _initialize_vectorstore(self):
        """Inicializa el vector store de ChromaDB"""
        try:
            persist_directory = self.config["persist_directory"]
            os.makedirs(persist_directory, exist_ok=True)
            
            # Configurar cliente ChromaDB
            client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Inicializar Chroma con LangChain
            self.vectorstore = Chroma(
                client=client,
                collection_name=self.config["collection_name"],
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            
            logger.info(f"Vector store inicializado en: {persist_directory}")
            
        except Exception as e:
            logger.error(f"Error inicializando vector store: {e}")
            raise
    
    def _initialize_qa_chain(self):
        """Inicializa la cadena de pregunta-respuesta"""
        if not self.vectorstore or not self.llm:
            logger.warning("Vector store o LLM no inicializados")
            return
        
        try:
            # Template de prompt personalizado
            prompt_template = """
Eres un especialista médico que consulta guías clínicas hospitalarias para responder preguntas médicas.

Contexto de guías clínicas:
{context}

Pregunta: {question}

Instrucciones:
1. Responde basándote únicamente en la información proporcionada en las guías clínicas
2. Si la información no está disponible, indícalo claramente
3. Proporciona respuestas estructuradas y profesionales
4. Incluye referencias a las guías consultadas cuando sea relevante
5. Mantén un enfoque clínico riguroso

Respuesta:
"""
            
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Configurar retriever
            retriever = self.vectorstore.as_retriever(
                search_type=self.config["search_type"],
                search_kwargs={
                    "k": self.config["top_k"],
                    "fetch_k": self.config["fetch_k"]
                }
            )
            
            # Crear cadena QA
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            logger.info("Cadena QA inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando cadena QA: {e}")
    
    def add_documents(self, file_paths: List[str], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Añade documentos al vector store"""
        try:
            results = {
                'success': True,
                'processed_files': [],
                'failed_files': [],
                'total_chunks': 0
            }
            
            for file_path in file_paths:
                try:
                    logger.info(f"Procesando documento: {file_path}")
                    
                    # Procesar documento
                    chunks = self.document_processor.process_document(
                        file_path, 
                        metadata or {}
                    )
                    
                    if chunks:
                        # Añadir al vector store
                        texts = [chunk.page_content for chunk in chunks]
                        metadatas = [chunk.metadata for chunk in chunks]
                        
                        self.vectorstore.add_texts(
                            texts=texts,
                            metadatas=metadatas
                        )
                        
                        results['processed_files'].append({
                            'file': file_path,
                            'chunks': len(chunks)
                        })
                        results['total_chunks'] += len(chunks)
                        
                        logger.info(f"Documento procesado: {len(chunks)} chunks")
                    else:
                        results['failed_files'].append({
                            'file': file_path,
                            'error': 'No se pudieron extraer chunks'
                        })
                        
                except Exception as e:
                    logger.error(f"Error procesando {file_path}: {e}")
                    results['failed_files'].append({
                        'file': file_path,
                        'error': str(e)
                    })
            
            # Persistir cambios
            if hasattr(self.vectorstore, 'persist'):
                self.vectorstore.persist()
            
            return results
            
        except Exception as e:
            logger.error(f"Error añadiendo documentos: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_files': [],
                'failed_files': file_paths
            }
    
    def search_clinical_guidelines(self, query: str, specialty: str = None, top_k: int = None) -> List[Dict[str, Any]]:
        """Busca en guías clínicas usando similarity search"""
        try:
            if not self.vectorstore:
                logger.error("Vector store no inicializado")
                return []
            
            # Usar top_k personalizado o por defecto
            k = top_k or self.config["top_k"]
            
            # Construir filtros si se especifica especialidad
            filter_dict = {}
            if specialty:
                filter_dict["specialty"] = specialty
            
            # Realizar búsqueda
            if filter_dict:
                docs = self.vectorstore.similarity_search(
                    query, 
                    k=k,
                    filter=filter_dict
                )
            else:
                docs = self.vectorstore.similarity_search(query, k=k)
            
            # Formatear resultados
            results = []
            for doc in docs:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'source': doc.metadata.get('filename', 'Desconocido')
                })
            
            logger.info(f"Búsqueda completada: {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []
    
    def query_with_rag(self, question: str) -> Dict[str, Any]:
        """Realiza consulta completa con RAG"""
        try:
            if not self.qa_chain:
                return {
                    'success': False,
                    'error': 'Cadena QA no inicializada'
                }
            
            # Ejecutar consulta
            result = self.qa_chain.invoke({"query": question})
            
            # Formatear respuesta
            response = {
                'success': True,
                'answer': result.get('result', ''),
                'sources': []
            }
            
            # Añadir fuentes si están disponibles
            if 'source_documents' in result:
                for doc in result['source_documents']:
                    response['sources'].append({
                        'content': doc.page_content[:200] + "...",
                        'metadata': doc.metadata,
                        'source': doc.metadata.get('filename', 'Desconocido')
                    })
            
            return response
            
        except Exception as e:
            logger.error(f"Error en consulta RAG: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la colección"""
        try:
            if not self.vectorstore:
                return {'error': 'Vector store no inicializado'}
            
            # Obtener información de la colección
            collection = self.vectorstore._collection
            count = collection.count()
            
            # Obtener algunos metadatos de muestra
            sample_docs = self.vectorstore.similarity_search("", k=5)
            
            sources = set()
            specialties = set()
            
            for doc in sample_docs:
                metadata = doc.metadata
                if 'filename' in metadata:
                    sources.add(metadata['filename'])
                if 'specialty' in metadata:
                    specialties.add(metadata['specialty'])
            
            return {
                'total_documents': count,
                'sources': list(sources),
                'specialties': list(specialties),
                'collection_name': self.config["collection_name"]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def delete_documents(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Elimina documentos basado en filtros"""
        try:
            if not self.vectorstore:
                return {
                    'success': False,
                    'error': 'Vector store no inicializado'
                }
            
            # ChromaDB delete con filtros
            collection = self.vectorstore._collection
            
            # Obtener IDs de documentos que coinciden con el filtro
            results = collection.get(where=filter_dict)
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                
                return {
                    'success': True,
                    'deleted_count': len(results['ids'])
                }
            else:
                return {
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No se encontraron documentos que coincidan con el filtro'
                }
                
        except Exception as e:
            logger.error(f"Error eliminando documentos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def rebuild_index(self) -> Dict[str, Any]:
        """Reconstruye el índice completo"""
        try:
            # Reinicializar vector store
            self._initialize_vectorstore()
            self._initialize_qa_chain()
            
            return {
                'success': True,
                'message': 'Índice reconstruido correctamente'
            }
            
        except Exception as e:
            logger.error(f"Error reconstruyendo índice: {e}")
            return {
                'success': False,
                'error': str(e)
            }

