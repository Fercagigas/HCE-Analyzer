
"""
Procesador de documentos PDF usando Docling para extracción y segmentación
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
from datetime import datetime

# Importaciones de Docling
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption
except ImportError:
    logging.warning("Docling no disponible. Usando fallback con PyPDF2")
    DocumentConverter = None

# Importaciones de LangChain para segmentación
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Procesador de documentos PDF con Docling y segmentación inteligente"""
    
    def __init__(self):
        self.converter = None
        self.text_splitter = None
        self.markdown_splitter = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa componentes de procesamiento"""
        try:
            # Inicializar Docling si está disponible
            if DocumentConverter:
                # Configurar opciones de pipeline para PDF
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = True  # Habilitar OCR
                pipeline_options.do_table_structure = True  # Extraer tablas
                
                # Configurar converter
                self.converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
                logger.info("Docling inicializado correctamente")
            else:
                logger.warning("Docling no disponible, usando fallback")
            
            # Inicializar text splitters
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # Splitter para Markdown con headers
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
            ]
            
            self.markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on,
                strip_headers=False
            )
            
            logger.info("Text splitters inicializados")
            
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
            raise
    
    def process_document(self, file_path: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Procesa un documento PDF y retorna chunks segmentados"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            
            if not file_path.suffix.lower() == '.pdf':
                raise ValueError("Solo se soportan archivos PDF")
            
            logger.info(f"Procesando documento: {file_path.name}")
            
            # Extraer texto del PDF
            if self.converter:
                text_content = self._extract_with_docling(file_path)
            else:
                text_content = self._extract_with_fallback(file_path)
            
            if not text_content:
                logger.warning(f"No se pudo extraer texto de: {file_path.name}")
                return []
            
            # Preparar metadata base
            base_metadata = {
                'filename': file_path.name,
                'file_path': str(file_path),
                'processed_at': datetime.now().isoformat(),
                'file_size': file_path.stat().st_size,
                'document_type': 'clinical_guide'
            }
            
            # Añadir metadata personalizada
            if metadata:
                base_metadata.update(metadata)
            
            # Segmentar documento
            chunks = self._segment_document(text_content, base_metadata)
            
            logger.info(f"Documento procesado: {len(chunks)} chunks generados")
            return chunks
            
        except Exception as e:
            logger.error(f"Error procesando documento {file_path}: {e}")
            return []
    
    def _extract_with_docling(self, file_path: Path) -> str:
        """Extrae texto usando Docling"""
        try:
            # Convertir documento
            result = self.converter.convert(str(file_path))
            
            # Extraer contenido en formato Markdown
            markdown_content = result.document.export_to_markdown()
            
            logger.info(f"Texto extraído con Docling: {len(markdown_content)} caracteres")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Error con Docling: {e}")
            # Fallback a método alternativo
            return self._extract_with_fallback(file_path)
    
    def _extract_with_fallback(self, file_path: Path) -> str:
        """Extrae texto usando PyPDF2 como fallback"""
        try:
            import PyPDF2
            
            text_content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n\n--- Página {page_num + 1} ---\n\n"
                            text_content += page_text
                    except Exception as e:
                        logger.warning(f"Error extrayendo página {page_num + 1}: {e}")
                        continue
            
            logger.info(f"Texto extraído con PyPDF2: {len(text_content)} caracteres")
            return text_content
            
        except ImportError:
            logger.error("PyPDF2 no disponible")
            return ""
        except Exception as e:
            logger.error(f"Error con PyPDF2: {e}")
            return ""
    
    def _segment_document(self, text: str, base_metadata: Dict[str, Any]) -> List[Document]:
        """Segmenta el documento en chunks inteligentes"""
        try:
            chunks = []
            
            # Intentar segmentación por headers de Markdown primero
            if self._is_markdown_format(text):
                md_chunks = self.markdown_splitter.split_text(text)
                
                for i, chunk in enumerate(md_chunks):
                    if chunk.page_content.strip():
                        chunk_metadata = base_metadata.copy()
                        chunk_metadata.update({
                            'chunk_id': i,
                            'chunk_type': 'markdown_section',
                            'headers': chunk.metadata
                        })
                        
                        # Dividir chunks grandes
                        if len(chunk.page_content) > 1500:
                            sub_chunks = self.text_splitter.split_text(chunk.page_content)
                            for j, sub_chunk in enumerate(sub_chunks):
                                sub_metadata = chunk_metadata.copy()
                                sub_metadata['chunk_id'] = f"{i}_{j}"
                                sub_metadata['chunk_type'] = 'markdown_subsection'
                                
                                chunks.append(Document(
                                    page_content=sub_chunk,
                                    metadata=sub_metadata
                                ))
                        else:
                            chunks.append(Document(
                                page_content=chunk.page_content,
                                metadata=chunk_metadata
                            ))
            else:
                # Segmentación estándar por caracteres
                text_chunks = self.text_splitter.split_text(text)
                
                for i, chunk in enumerate(text_chunks):
                    if chunk.strip():
                        chunk_metadata = base_metadata.copy()
                        chunk_metadata.update({
                            'chunk_id': i,
                            'chunk_type': 'text_section'
                        })
                        
                        chunks.append(Document(
                            page_content=chunk,
                            metadata=chunk_metadata
                        ))
            
            # Filtrar chunks muy pequeños
            filtered_chunks = [
                chunk for chunk in chunks 
                if len(chunk.page_content.strip()) > 50
            ]
            
            logger.info(f"Segmentación completada: {len(filtered_chunks)} chunks válidos")
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error en segmentación: {e}")
            return []
    
    def _is_markdown_format(self, text: str) -> bool:
        """Detecta si el texto está en formato Markdown"""
        markdown_indicators = ['#', '##', '###', '####', '*', '-', '**', '__']
        lines = text.split('\n')[:20]  # Revisar primeras 20 líneas
        
        markdown_count = 0
        for line in lines:
            if any(line.strip().startswith(indicator) for indicator in markdown_indicators):
                markdown_count += 1
        
        # Si más del 20% de las líneas tienen indicadores de Markdown
        return markdown_count > len(lines) * 0.2
    
    def process_multiple_documents(self, file_paths: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[Document]:
        """Procesa múltiples documentos"""
        all_chunks = []
        
        for i, file_path in enumerate(file_paths):
            try:
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                chunks = self.process_document(file_path, metadata)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Error procesando {file_path}: {e}")
                continue
        
        logger.info(f"Procesamiento múltiple completado: {len(all_chunks)} chunks totales")
        return all_chunks
    
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extrae metadata del nombre del archivo"""
        metadata = {}
        
        # Patrones comunes en nombres de archivos médicos
        filename_lower = filename.lower()
        
        # Detectar especialidad
        specialties = {
            'urgencias': ['urgencia', 'emergencia', 'emergency'],
            'cardiologia': ['cardio', 'corazon', 'cardiac'],
            'neurologia': ['neuro', 'cerebro', 'brain'],
            'pediatria': ['pediatr', 'niño', 'child'],
            'ginecologia': ['gineco', 'mujer', 'gynec'],
            'traumatologia': ['trauma', 'hueso', 'fractura'],
            'medicina_interna': ['interna', 'internal'],
            'cirugia': ['cirug', 'surgery', 'operacion']
        }
        
        for specialty, keywords in specialties.items():
            if any(keyword in filename_lower for keyword in keywords):
                metadata['specialty'] = specialty
                break
        
        # Detectar tipo de documento
        doc_types = {
            'protocolo': ['protocolo', 'protocol'],
            'guia_clinica': ['guia', 'guide', 'guideline'],
            'manual': ['manual', 'handbook'],
            'procedimiento': ['procedimiento', 'procedure'],
            'algoritmo': ['algoritmo', 'algorithm']
        }
        
        for doc_type, keywords in doc_types.items():
            if any(keyword in filename_lower for keyword in keywords):
                metadata['document_subtype'] = doc_type
                break
        
        return metadata
    
    def validate_document(self, file_path: str) -> Dict[str, Any]:
        """Valida un documento antes del procesamiento"""
        try:
            file_path = Path(file_path)
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'file_info': {}
            }
            
            # Verificar existencia
            if not file_path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append("Archivo no encontrado")
                return validation_result
            
            # Verificar extensión
            if file_path.suffix.lower() != '.pdf':
                validation_result['valid'] = False
                validation_result['errors'].append("Solo se soportan archivos PDF")
                return validation_result
            
            # Información del archivo
            stat = file_path.stat()
            validation_result['file_info'] = {
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            # Verificar tamaño
            if stat.st_size > 50 * 1024 * 1024:  # 50MB
                validation_result['warnings'].append("Archivo muy grande (>50MB)")
            
            if stat.st_size < 1024:  # 1KB
                validation_result['warnings'].append("Archivo muy pequeño (<1KB)")
            
            # Intentar abrir el PDF
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    num_pages = len(pdf_reader.pages)
                    
                    validation_result['file_info']['pages'] = num_pages
                    
                    if num_pages == 0:
                        validation_result['valid'] = False
                        validation_result['errors'].append("PDF sin páginas")
                    elif num_pages > 500:
                        validation_result['warnings'].append("PDF muy extenso (>500 páginas)")
                        
            except Exception as e:
                validation_result['warnings'].append(f"No se pudo validar estructura PDF: {e}")
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Error en validación: {e}"],
                'warnings': [],
                'file_info': {}
            }

