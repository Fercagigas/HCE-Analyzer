
"""
Memory-optimized document processor using Docling for extraction and segmentation
"""
import os
import gc
import logging
from typing import List, Dict, Any, Optional, Iterator, Generator
from pathlib import Path
import tempfile
from datetime import datetime
import sys

# Importaciones de Docling
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    DOCLING_AVAILABLE = True
except ImportError:
    logging.warning("Docling no disponible. Usando fallback con PyPDF2")
    DocumentConverter = None
    DOCLING_AVAILABLE = False

# Detección de GPU
def _detect_accelerator() -> str:
    """Detecta el mejor dispositivo de aceleración disponible"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logging.info(f"🚀 GPU detectada: {gpu_name} (CUDA {torch.version.cuda})")
            return "cuda"
    except ImportError:
        pass
    logging.info("⚠️ GPU no disponible, usando CPU")
    return "cpu"

# Importaciones de LangChain para segmentación
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Memory-optimized PDF document processor with Docling and intelligent segmentation"""
    
    def __init__(self, max_memory_mb: int = 500, chunk_size: int = 2400, streaming_threshold_mb: int = 10):
        self.converter = None
        self.text_splitter = None
        self.markdown_splitter = None
        self.max_memory_mb = max_memory_mb
        self.chunk_size = chunk_size
        self.streaming_threshold_mb = streaming_threshold_mb
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize processing components with GPU acceleration if available"""
        try:
            # Initialize Docling if available
            if DOCLING_AVAILABLE and DocumentConverter:
                # Detectar dispositivo de aceleración
                device_str = _detect_accelerator()
                
                # Configurar opciones de aceleración
                if device_str == "cuda":
                    accel_device = AcceleratorDevice.CUDA
                else:
                    accel_device = AcceleratorDevice.CPU
                
                accelerator_options = AcceleratorOptions(
                    device=accel_device,
                    num_threads=4
                )
                
                # Configure pipeline options for PDF
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = True
                pipeline_options.do_table_structure = True
                pipeline_options.accelerator_options = accelerator_options
                
                # Configure converter
                self.converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
                logger.info(f"Docling initialized successfully (device: {device_str})")
            else:
                logger.warning("Docling not available, using fallback")
            
            # Initialize text splitters with memory-efficient settings
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=min(200, self.chunk_size // 6),  # Adaptive overlap
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # Splitter for Markdown with headers
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
            
            logger.info("Text splitters initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def process_document(self, file_path: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Process a PDF document and return segmented chunks with memory optimization"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_path.suffix.lower() == '.pdf':
                raise ValueError("Only PDF files are supported")
            
            # Check file size for streaming decision
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Processing document: {file_path.name} ({file_size_mb:.2f}MB)")
            
            # Use streaming for large files
            if file_size_mb > self.streaming_threshold_mb:
                return self._process_document_streaming(file_path, metadata)
            else:
                return self._process_document_standard(file_path, metadata)
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return []
        finally:
            # Force garbage collection after processing
            gc.collect()
    
    def _process_document_standard(self, file_path: Path, metadata: Dict[str, Any] = None) -> List[Document]:
        """Standard processing for smaller files"""
        try:
            # Extract text from PDF
            if self.converter:
                text_content = self._extract_with_docling(file_path)
            else:
                text_content = self._extract_with_fallback(file_path)
            
            if not text_content:
                logger.warning(f"Could not extract text from: {file_path.name}")
                return []
            
            # Prepare base metadata
            base_metadata = self._prepare_base_metadata(file_path, metadata)
            
            # Segment document
            chunks = self._segment_document(text_content, base_metadata)
            
            # Clear text content from memory
            del text_content
            gc.collect()
            
            logger.info(f"Document processed: {len(chunks)} chunks generated")
            return chunks
            
        except Exception as e:
            logger.error(f"Error in standard processing: {e}")
            return []
    
    def _process_document_streaming(self, file_path: Path, metadata: Dict[str, Any] = None) -> List[Document]:
        """Streaming processing for large files"""
        try:
            logger.info(f"Using streaming processing for large file: {file_path.name}")
            
            # Process in chunks to avoid memory overflow
            chunks = []
            base_metadata = self._prepare_base_metadata(file_path, metadata)
            
            # Use page-by-page processing for large PDFs
            for page_chunks in self._extract_pages_streaming(file_path):
                if page_chunks:
                    # Process each page's chunks
                    for page_text in page_chunks:
                        if page_text.strip():
                            page_segments = self._segment_text_chunk(page_text, base_metadata)
                            chunks.extend(page_segments)
                    
                    # Periodic memory cleanup
                    if len(chunks) % 50 == 0:  # Every 50 chunks
                        gc.collect()
            
            logger.info(f"Streaming processing completed: {len(chunks)} chunks generated")
            return chunks
            
        except Exception as e:
            logger.error(f"Error in streaming processing: {e}")
            return []
    
    def _prepare_base_metadata(self, file_path: Path, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Prepare base metadata for document chunks"""
        base_metadata = {
            'filename': file_path.name,
            'file_path': str(file_path),
            'processed_at': datetime.now().isoformat(),
            'file_size': file_path.stat().st_size,
            'document_type': 'clinical_guide',
            'processing_mode': 'memory_optimized'
        }
        
        # Add custom metadata
        if metadata:
            base_metadata.update(metadata)
        
        # Add extracted metadata from filename
        filename_metadata = self.extract_metadata_from_filename(file_path.name)
        base_metadata.update(filename_metadata)
        
        return base_metadata
    
    def _extract_with_docling(self, file_path: Path) -> str:
        """Extract text using Docling with memory optimization"""
        try:
            # Convert document
            result = self.converter.convert(str(file_path))
            
            # Extract content in Markdown format
            markdown_content = result.document.export_to_markdown()
            
            # Clear converter result from memory
            del result
            gc.collect()
            
            logger.info(f"Text extracted with Docling: {len(markdown_content)} characters")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Error with Docling: {e}")
            # Fallback to alternative method
            return self._extract_with_fallback(file_path)
    
    def _extract_pages_streaming(self, file_path: Path) -> Generator[List[str], None, None]:
        """Extract PDF pages in streaming mode to minimize memory usage"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                # Process pages in batches to control memory usage
                batch_size = max(1, min(10, self.max_memory_mb // 50))  # Adaptive batch size
                
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    batch_texts = []
                    
                    for page_num in range(batch_start, batch_end):
                        try:
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            
                            if page_text and page_text.strip():
                                # Add page marker for context
                                formatted_text = f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
                                batch_texts.append(formatted_text)
                            
                        except Exception as e:
                            logger.warning(f"Error extracting page {page_num + 1}: {e}")
                            continue
                    
                    if batch_texts:
                        yield batch_texts
                    
                    # Clear batch from memory
                    del batch_texts
                    gc.collect()
                    
                    logger.debug(f"Processed pages {batch_start + 1}-{batch_end} of {total_pages}")
            
        except Exception as e:
            logger.error(f"Error in streaming extraction: {e}")
            yield []
    
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
        """Segment document into intelligent chunks"""
        try:
            chunks = []
            
            # Try Markdown header segmentation first
            if self._is_markdown_format(text):
                chunks = self._segment_markdown_text(text, base_metadata)
            else:
                # Standard character-based segmentation
                chunks = self._segment_plain_text(text, base_metadata)
            
            # Filter very small chunks
            filtered_chunks = [
                chunk for chunk in chunks 
                if len(chunk.page_content.strip()) > 50
            ]
            
            # Memory cleanup
            del chunks
            gc.collect()
            
            logger.info(f"Segmentation completed: {len(filtered_chunks)} valid chunks")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"Error in segmentation: {e}")
            return []
    
    def _segment_markdown_text(self, text: str, base_metadata: Dict[str, Any]) -> List[Document]:
        """Segment Markdown text with memory optimization"""
        chunks = []
        
        try:
            md_chunks = self.markdown_splitter.split_text(text)
            
            for i, chunk in enumerate(md_chunks):
                if chunk.page_content.strip():
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        'chunk_id': i,
                        'chunk_type': 'markdown_section',
                        'headers': chunk.metadata
                    })
                    
                    # Split large chunks
                    if len(chunk.page_content) > self.chunk_size * 1.5:
                        sub_chunks = self._split_large_chunk(chunk.page_content, chunk_metadata)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(Document(
                            page_content=chunk.page_content,
                            metadata=chunk_metadata
                        ))
                
                # Periodic memory cleanup during processing
                if i % 20 == 0 and i > 0:
                    gc.collect()
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in Markdown segmentation: {e}")
            return []
    
    def _segment_plain_text(self, text: str, base_metadata: Dict[str, Any]) -> List[Document]:
        """Segment plain text with memory optimization"""
        chunks = []
        
        try:
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
                
                # Periodic memory cleanup
                if i % 50 == 0 and i > 0:
                    gc.collect()
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in plain text segmentation: {e}")
            return []
    
    def _segment_text_chunk(self, text: str, base_metadata: Dict[str, Any]) -> List[Document]:
        """Segment a single text chunk (used in streaming mode)"""
        try:
            if not text or not text.strip():
                return []
            
            # Use smaller chunks for streaming mode to control memory
            streaming_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size // 2,  # Smaller chunks for streaming
                chunk_overlap=100,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            text_chunks = streaming_splitter.split_text(text)
            chunks = []
            
            for i, chunk in enumerate(text_chunks):
                if chunk.strip() and len(chunk.strip()) > 30:
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        'chunk_id': f"stream_{i}",
                        'chunk_type': 'streaming_section',
                        'chunk_size': len(chunk)
                    })
                    
                    chunks.append(Document(
                        page_content=chunk,
                        metadata=chunk_metadata
                    ))
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error segmenting text chunk: {e}")
            return []
    
    def _split_large_chunk(self, text: str, base_metadata: Dict[str, Any]) -> List[Document]:
        """Split large chunks into smaller ones"""
        try:
            sub_chunks = self.text_splitter.split_text(text)
            documents = []
            
            for j, sub_chunk in enumerate(sub_chunks):
                if sub_chunk.strip():
                    sub_metadata = base_metadata.copy()
                    sub_metadata['chunk_id'] = f"{base_metadata.get('chunk_id', 0)}_{j}"
                    sub_metadata['chunk_type'] = 'markdown_subsection'
                    
                    documents.append(Document(
                        page_content=sub_chunk,
                        metadata=sub_metadata
                    ))
            
            return documents
            
        except Exception as e:
            logger.error(f"Error splitting large chunk: {e}")
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
    
    def process_multiple_documents(self, file_paths: List[str], 
                                 metadata_list: List[Dict[str, Any]] = None,
                                 batch_size: int = 5) -> Iterator[List[Document]]:
        """Process multiple documents in memory-efficient batches"""
        total_files = len(file_paths)
        processed_count = 0
        
        logger.info(f"Starting batch processing of {total_files} documents with batch size {batch_size}")
        
        # Process files in batches to control memory usage
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch_files = file_paths[batch_start:batch_end]
            batch_chunks = []
            
            logger.info(f"Processing batch {batch_start // batch_size + 1}: "
                       f"files {batch_start + 1}-{batch_end} of {total_files}")
            
            for i, file_path in enumerate(batch_files):
                try:
                    global_index = batch_start + i
                    metadata = metadata_list[global_index] if metadata_list and global_index < len(metadata_list) else {}
                    
                    # Add batch information to metadata
                    metadata.update({
                        'batch_id': batch_start // batch_size,
                        'file_index_in_batch': i,
                        'global_file_index': global_index
                    })
                    
                    chunks = self.process_document(file_path, metadata)
                    batch_chunks.extend(chunks)
                    processed_count += 1
                    
                    logger.debug(f"Processed file {processed_count}/{total_files}: {Path(file_path).name}")
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    continue
            
            # Yield batch results and clean up memory
            if batch_chunks:
                yield batch_chunks
            
            # Force memory cleanup between batches
            del batch_chunks
            gc.collect()
            
            logger.info(f"Completed batch {batch_start // batch_size + 1}, "
                       f"processed {processed_count}/{total_files} files")
        
        logger.info(f"Batch processing completed: {processed_count}/{total_files} files processed")
    
    def process_multiple_documents_to_list(self, file_paths: List[str], 
                                         metadata_list: List[Dict[str, Any]] = None,
                                         batch_size: int = 5) -> List[Document]:
        """Process multiple documents and return all chunks as a list"""
        all_chunks = []
        
        for batch_chunks in self.process_multiple_documents(file_paths, metadata_list, batch_size):
            all_chunks.extend(batch_chunks)
        
        logger.info(f"Multiple document processing completed: {len(all_chunks)} total chunks")
        return all_chunks
    
    def get_memory_usage_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics for the processor"""
        import psutil
        process = psutil.Process()
        return {
            'process_memory_mb': process.memory_info().rss / (1024 * 1024),
            'max_memory_mb': self.max_memory_mb,
            'streaming_threshold_mb': self.streaming_threshold_mb,
            'chunk_size': self.chunk_size
        }
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage by cleaning up unused objects"""
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        # Force garbage collection
        collected_objects = gc.collect()
        
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_freed = initial_memory - final_memory
        
        result = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_freed_mb': memory_freed,
            'collected_objects': collected_objects
        }
        
        logger.info(f"Memory optimization completed: {memory_freed:.2f}MB freed, "
                   f"{collected_objects} objects collected")
        
        return result
    
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

