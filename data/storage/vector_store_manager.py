
"""
Gestor de ChromaDB y embeddings para el sistema RAG
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np
from datetime import datetime
import json

# Importaciones de LangChain
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# Importar configuración
from config.config import HUGGINGFACE_API_TOKEN

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Gestor completo del vector store con ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "clinical_guidelines"):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embeddings = None
        self.langchain_vectorstore = None
        self._initialize()
    
    def _initialize(self):
        """Inicializa el vector store y componentes"""
        try:
            # Crear directorio si no existe
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # Inicializar embeddings
            model_kwargs = {'device': 'cpu'}
            if HUGGINGFACE_API_TOKEN:
                model_kwargs['use_auth_token'] = HUGGINGFACE_API_TOKEN
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs=model_kwargs,
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Inicializar cliente ChromaDB
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Configurar función de embeddings para ChromaDB
            embedding_function_kwargs = {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2"
            }
            if HUGGINGFACE_API_TOKEN:
                embedding_function_kwargs["token"] = HUGGINGFACE_API_TOKEN
            
            # Obtener o crear colección
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        **embedding_function_kwargs
                    )
                )
                logger.info(f"Colección existente cargada: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        **embedding_function_kwargs
                    )
                )
                logger.info(f"Nueva colección creada: {self.collection_name}")
            
            # Inicializar LangChain vector store
            self.langchain_vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            
            logger.info("Vector store inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando vector store: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """Añade documentos al vector store"""
        try:
            if not documents:
                return {
                    'success': False,
                    'error': 'No hay documentos para añadir'
                }
            
            # Preparar datos para ChromaDB
            texts = []
            metadatas = []
            ids = []
            
            for i, doc in enumerate(documents):
                # Generar ID único
                doc_id = f"{doc.metadata.get('filename', 'unknown')}_{i}_{datetime.now().timestamp()}"
                ids.append(doc_id)
                texts.append(doc.page_content)
                
                # Preparar metadata (ChromaDB requiere tipos específicos)
                metadata = {}
                for key, value in doc.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    else:
                        metadata[key] = str(value)
                
                metadatas.append(metadata)
            
            # Añadir a ChromaDB
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Añadidos {len(documents)} documentos al vector store")
            
            return {
                'success': True,
                'added_count': len(documents),
                'collection_size': self.collection.count()
            }
            
        except Exception as e:
            logger.error(f"Error añadiendo documentos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_similar(self, query: str, n_results: int = 5, where: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Busca documentos similares usando ChromaDB directamente"""
        try:
            # Realizar búsqueda
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # Formatear resultados
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'id': results['ids'][0][i] if results['ids'] else None
                    })
            
            logger.info(f"Búsqueda completada: {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []
    
    def search_with_langchain(self, query: str, k: int = 5, filter: Dict[str, Any] = None) -> List[Document]:
        """Busca usando la interfaz de LangChain"""
        try:
            if filter:
                docs = self.langchain_vectorstore.similarity_search(
                    query, 
                    k=k,
                    filter=filter
                )
            else:
                docs = self.langchain_vectorstore.similarity_search(query, k=k)
            
            logger.info(f"Búsqueda LangChain completada: {len(docs)} resultados")
            return docs
            
        except Exception as e:
            logger.error(f"Error en búsqueda LangChain: {e}")
            return []
    
    def get_retriever(self, search_type: str = "similarity", search_kwargs: Dict[str, Any] = None):
        """Obtiene un retriever de LangChain"""
        try:
            search_kwargs = search_kwargs or {"k": 5}
            
            retriever = self.langchain_vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs
            )
            
            return retriever
            
        except Exception as e:
            logger.error(f"Error creando retriever: {e}")
            return None
    
    def delete_documents(self, where: Dict[str, Any] = None, ids: List[str] = None) -> Dict[str, Any]:
        """Elimina documentos del vector store"""
        try:
            if ids:
                # Eliminar por IDs específicos
                self.collection.delete(ids=ids)
                deleted_count = len(ids)
            elif where:
                # Eliminar por filtros
                # Primero obtener los IDs que coinciden
                results = self.collection.get(where=where)
                if results['ids']:
                    self.collection.delete(ids=results['ids'])
                    deleted_count = len(results['ids'])
                else:
                    deleted_count = 0
            else:
                return {
                    'success': False,
                    'error': 'Debe especificar IDs o filtros para eliminar'
                }
            
            logger.info(f"Eliminados {deleted_count} documentos")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'collection_size': self.collection.count()
            }
            
        except Exception as e:
            logger.error(f"Error eliminando documentos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Obtiene información de la colección"""
        try:
            count = self.collection.count()
            
            # Obtener muestra de documentos para estadísticas
            sample_size = min(100, count)
            if sample_size > 0:
                sample = self.collection.get(limit=sample_size)
                
                # Analizar metadatos
                specialties = set()
                document_types = set()
                sources = set()
                
                for metadata in sample['metadatas']:
                    if 'specialty' in metadata:
                        specialties.add(metadata['specialty'])
                    if 'document_type' in metadata:
                        document_types.add(metadata['document_type'])
                    if 'filename' in metadata:
                        sources.add(metadata['filename'])
                
                return {
                    'collection_name': self.collection_name,
                    'total_documents': count,
                    'specialties': list(specialties),
                    'document_types': list(document_types),
                    'sources': list(sources),
                    'persist_directory': str(self.persist_directory)
                }
            else:
                return {
                    'collection_name': self.collection_name,
                    'total_documents': 0,
                    'specialties': [],
                    'document_types': [],
                    'sources': [],
                    'persist_directory': str(self.persist_directory)
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo información de colección: {e}")
            return {
                'error': str(e)
            }
    
    def update_document_metadata(self, document_id: str, new_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza metadata de un documento específico"""
        try:
            # ChromaDB no soporta actualización directa, necesitamos eliminar y re-añadir
            # Primero obtener el documento actual
            result = self.collection.get(ids=[document_id])
            
            if not result['ids']:
                return {
                    'success': False,
                    'error': 'Documento no encontrado'
                }
            
            # Obtener datos actuales
            current_text = result['documents'][0]
            current_metadata = result['metadatas'][0]
            
            # Actualizar metadata
            updated_metadata = current_metadata.copy()
            updated_metadata.update(new_metadata)
            
            # Eliminar documento actual
            self.collection.delete(ids=[document_id])
            
            # Re-añadir con nueva metadata
            self.collection.add(
                documents=[current_text],
                metadatas=[updated_metadata],
                ids=[document_id]
            )
            
            logger.info(f"Metadata actualizada para documento: {document_id}")
            
            return {
                'success': True,
                'updated_metadata': updated_metadata
            }
            
        except Exception as e:
            logger.error(f"Error actualizando metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_collection(self, output_path: str) -> Dict[str, Any]:
        """Exporta la colección completa a un archivo JSON"""
        try:
            # Obtener todos los documentos
            all_data = self.collection.get()
            
            export_data = {
                'collection_name': self.collection_name,
                'export_timestamp': datetime.now().isoformat(),
                'total_documents': len(all_data['ids']),
                'documents': []
            }
            
            # Formatear datos para exportación
            for i in range(len(all_data['ids'])):
                doc_data = {
                    'id': all_data['ids'][i],
                    'content': all_data['documents'][i],
                    'metadata': all_data['metadatas'][i]
                }
                export_data['documents'].append(doc_data)
            
            # Guardar a archivo
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Colección exportada a: {output_path}")
            
            return {
                'success': True,
                'exported_documents': len(all_data['ids']),
                'output_path': output_path
            }
            
        except Exception as e:
            logger.error(f"Error exportando colección: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_collection(self, input_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Importa una colección desde un archivo JSON"""
        try:
            # Leer archivo de importación
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if overwrite:
                # Limpiar colección existente
                self.collection.delete(where={})
                logger.info("Colección existente limpiada")
            
            # Preparar datos para importación
            ids = []
            documents = []
            metadatas = []
            
            for doc_data in import_data['documents']:
                ids.append(doc_data['id'])
                documents.append(doc_data['content'])
                metadatas.append(doc_data['metadata'])
            
            # Añadir documentos en lotes
            batch_size = 100
            imported_count = 0
            
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas
                )
                
                imported_count += len(batch_ids)
                logger.info(f"Importados {imported_count}/{len(ids)} documentos")
            
            return {
                'success': True,
                'imported_documents': imported_count,
                'collection_size': self.collection.count()
            }
            
        except Exception as e:
            logger.error(f"Error importando colección: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reset_collection(self) -> Dict[str, Any]:
        """Resetea completamente la colección"""
        try:
            # Eliminar colección actual
            self.client.delete_collection(self.collection_name)
            
            # Configurar función de embeddings para ChromaDB
            embedding_function_kwargs = {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2"
            }
            if HUGGINGFACE_API_TOKEN:
                embedding_function_kwargs["token"] = HUGGINGFACE_API_TOKEN
            
            # Recrear colección
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    **embedding_function_kwargs
                )
            )
            
            # Reinicializar LangChain vector store
            self.langchain_vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            
            logger.info("Colección reseteada correctamente")
            
            return {
                'success': True,
                'message': 'Colección reseteada correctamente'
            }
            
        except Exception as e:
            logger.error(f"Error reseteando colección: {e}")
            return {
                'success': False,
                'error': str(e)
            }

