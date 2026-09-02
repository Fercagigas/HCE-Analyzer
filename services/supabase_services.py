"""
Servicio legacy de Supabase para `public.clinical_documents` (usado por DocumentManager).

AnalysisService y UserPreferencesService se sustituyeron por los repositorios del core
(`chathce.adapters.supabase.*`).
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ClinicalDocumentService:
    """
    Servicio para gestionar documentos clínicos en Supabase.
    Tabla: public.clinical_documents
    """

    def __init__(self, supabase_client=None):
        self.client = supabase_client or self._get_client()

    def _get_client(self):
        try:
            from config.settings import get_settings
            from supabase import create_client

            db = get_settings().require_database()
            return create_client(db.supabase_url, db.supabase_key)
        except Exception as e:
            logger.error(f"Error creando cliente Supabase: {e}")
            return None

    def save_document(
        self,
        filename: str,
        title: Optional[str] = None,
        document_type: Optional[str] = None,
        specialty: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Registra un documento clínico en Supabase.

        Args:
            filename: Nombre del archivo
            title: Título del documento
            document_type: Tipo de documento (guía, protocolo, etc.)
            specialty: Especialidad médica
            file_path: Ruta del archivo
            metadata: Metadata adicional (jsonb)

        Returns:
            Tuple (success, document_record o None)
        """
        if not self.client:
            logger.warning("Cliente Supabase no disponible para clinical_documents")
            return False, None

        try:
            record = {
                "filename": filename,
                "title": title or filename,
                "document_type": document_type,
                "specialty": specialty,
                "file_path": file_path,
                "metadata": metadata or {},
                "processed": False,
            }

            result = self.client.table("clinical_documents").insert(record).execute()

            if result.data:
                logger.info(f"Documento registrado en Supabase: {filename}")
                return True, result.data[0]
            return False, None
        except Exception as e:
            logger.error(f"Error guardando documento en Supabase: {e}")
            return False, None

    def mark_as_processed(self, document_id: str) -> bool:
        """Marca un documento como procesado (indexado en Supabase pgvector)."""
        if not self.client:
            return False
        try:
            self.client.table("clinical_documents") \
                .update({"processed": True}) \
                .eq("id", document_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error actualizando documento: {e}")
            return False

    def list_documents(
        self,
        specialty: Optional[str] = None,
        document_type: Optional[str] = None,
        processed_only: bool = False,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Lista documentos clínicos desde Supabase.

        Args:
            specialty: Filtrar por especialidad
            document_type: Filtrar por tipo
            processed_only: Solo documentos procesados

        Returns:
            Tuple (success, lista de documentos)
        """
        if not self.client:
            return False, []

        try:
            query = self.client.table("clinical_documents") \
                .select("*") \
                .order("upload_date", desc=True)

            if specialty:
                query = query.eq("specialty", specialty)
            if document_type:
                query = query.eq("document_type", document_type)
            if processed_only:
                query = query.eq("processed", True)

            result = query.execute()
            return True, result.data or []
        except Exception as e:
            logger.error(f"Error listando documentos: {e}")
            return False, []

    def get_document(self, document_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Obtiene un documento por ID."""
        if not self.client:
            return False, None
        try:
            result = self.client.table("clinical_documents") \
                .select("*") \
                .eq("id", document_id) \
                .single() \
                .execute()
            return True, result.data
        except Exception as e:
            logger.error(f"Error obteniendo documento: {e}")
            return False, None

    def find_by_filename(self, filename: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Busca un documento por nombre de archivo."""
        if not self.client:
            return False, None
        try:
            result = self.client.table("clinical_documents") \
                .select("*") \
                .eq("filename", filename) \
                .execute()
            if result.data:
                return True, result.data[0]
            return True, None
        except Exception as e:
            logger.error(f"Error buscando documento: {e}")
            return False, None

    def delete_document(self, document_id: str) -> Tuple[bool, str]:
        """Elimina un documento de Supabase."""
        if not self.client:
            return False, "Cliente Supabase no disponible"
        try:
            self.client.table("clinical_documents") \
                .delete() \
                .eq("id", document_id) \
                .execute()
            logger.info(f"Documento eliminado de Supabase: {document_id}")
            return True, "Documento eliminado"
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False, str(e)

    def delete_by_filename(self, filename: str) -> Tuple[bool, str]:
        """Elimina un documento por nombre de archivo."""
        if not self.client:
            return False, "Cliente Supabase no disponible"
        try:
            self.client.table("clinical_documents") \
                .delete() \
                .eq("filename", filename) \
                .execute()
            logger.info(f"Documento eliminado por filename: {filename}")
            return True, "Documento eliminado"
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False, str(e)
