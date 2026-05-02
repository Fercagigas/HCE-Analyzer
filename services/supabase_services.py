"""
Servicios de Supabase para tablas del esquema public no conectadas.

Conecta las tablas: clinical_documents, analyses, user_preferences
con el frontend/backend de ChatHCE.
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
            from config.config import SUPABASE_URL, SUPABASE_KEY
            from supabase import create_client
            return create_client(SUPABASE_URL, SUPABASE_KEY)
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


class AnalysisService:
    """
    Servicio para gestionar análisis realizados por el agente.
    Tabla: public.analyses
    """

    def __init__(self, supabase_client=None):
        self.client = supabase_client or self._get_client()

    def _get_client(self):
        try:
            from config.config import SUPABASE_URL, SUPABASE_KEY
            from supabase import create_client
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Error creando cliente Supabase: {e}")
            return None

    def save_analysis(
        self,
        user_id: str,
        analysis_type: str,
        content: str,
        results: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Guarda un análisis realizado por el agente.

        Args:
            user_id: ID del usuario que solicitó el análisis
            analysis_type: Tipo de análisis (database_query, rag_search,
                           visualization, mixed)
            content: Contenido/pregunta del análisis
            results: Resultados del análisis (jsonb)
            document_id: ID del documento relacionado (opcional)

        Returns:
            Tuple (success, analysis_record o None)
        """
        if not self.client:
            logger.warning("Cliente Supabase no disponible para analyses")
            return False, None

        try:
            record = {
                "user_id": user_id,
                "analysis_type": analysis_type,
                "content": content,
                "results": results or {},
            }
            if document_id:
                record["document_id"] = document_id

            result = self.client.table("analyses").insert(record).execute()

            if result.data:
                logger.info(f"Análisis guardado: type={analysis_type}")
                return True, result.data[0]
            return False, None
        except Exception as e:
            logger.error(f"Error guardando análisis: {e}")
            return False, None

    def get_user_analyses(
        self,
        user_id: str,
        analysis_type: Optional[str] = None,
        limit: int = 20,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Obtiene análisis de un usuario.

        Args:
            user_id: ID del usuario
            analysis_type: Filtrar por tipo
            limit: Máximo de resultados

        Returns:
            Tuple (success, lista de análisis)
        """
        if not self.client:
            return False, []

        try:
            query = self.client.table("analyses") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit)

            if analysis_type:
                query = query.eq("analysis_type", analysis_type)

            result = query.execute()
            return True, result.data or []
        except Exception as e:
            logger.error(f"Error obteniendo análisis: {e}")
            return False, []

    def get_analysis_stats(self, user_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de análisis de un usuario."""
        if not self.client:
            return {"error": "Cliente no disponible"}

        try:
            result = self.client.table("analyses") \
                .select("analysis_type") \
                .eq("user_id", user_id) \
                .execute()

            data = result.data or []
            total = len(data)
            by_type: Dict[str, int] = {}
            for row in data:
                t = row.get("analysis_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1

            return {
                "total_analyses": total,
                "by_type": by_type,
            }
        except Exception as e:
            logger.error(f"Error obteniendo stats de análisis: {e}")
            return {"error": str(e)}


class UserPreferencesService:
    """
    Servicio para gestionar preferencias de usuario.
    Tabla: public.user_preferences
    """

    def __init__(self, supabase_client=None):
        self.client = supabase_client or self._get_client()

    def _get_client(self):
        try:
            from config.config import SUPABASE_URL, SUPABASE_KEY
            from supabase import create_client
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Error creando cliente Supabase: {e}")
            return None

    def get_preferences(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Obtiene las preferencias de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple (success, dict de preferencias)
        """
        if not self.client:
            return False, self._default_preferences()

        try:
            result = self.client.table("user_preferences") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()

            if result.data:
                prefs = result.data[0].get("preferences", {})
                # Merge con defaults para asegurar que todas las keys existan
                defaults = self._default_preferences()
                defaults.update(prefs)
                return True, defaults
            else:
                # No hay preferencias guardadas, crear con defaults
                return True, self._default_preferences()
        except Exception as e:
            logger.error(f"Error obteniendo preferencias: {e}")
            return False, self._default_preferences()

    def save_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Guarda o actualiza las preferencias de un usuario.
        Usa upsert para crear o actualizar.

        Args:
            user_id: ID del usuario
            preferences: Dict con las preferencias

        Returns:
            Tuple (success, mensaje)
        """
        if not self.client:
            return False, "Cliente Supabase no disponible"

        try:
            record = {
                "user_id": user_id,
                "preferences": preferences,
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Upsert: si existe actualiza, si no crea
            self.client.table("user_preferences") \
                .upsert(record, on_conflict="user_id") \
                .execute()

            logger.info(f"Preferencias guardadas para usuario: {user_id}")
            return True, "Preferencias guardadas"
        except Exception as e:
            logger.error(f"Error guardando preferencias: {e}")
            return False, str(e)

    @staticmethod
    def _default_preferences() -> Dict[str, Any]:
        """Preferencias por defecto."""
        return {
            "show_tool_usage": True,
            "show_performance": True,
            "show_sources": True,
            "enable_visualizations": True,
            "max_context_messages": 10,
            "theme": "default",
            "language": "es",
        }
