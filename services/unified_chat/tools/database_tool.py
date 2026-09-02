"""
Database Tool (legacy runtime) for the unified chat.

WP4 (ADR 0050): el contrato visible al modelo ya no admite SQL, nombres de tabla ni
filtros libres. Solo operaciones clinicas allowlisted y agregados fijos del dataset.
Las operaciones por paciente siguen delegando en `DatabaseService`; los agregados se
sirven por RPC a traves del `ClinicalDataProvider` nuevo (chathce). Este modulo se
retira en WP8 cuando el ChatService y el ToolRegistry sustituyan al bucle legacy.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from services.medical_agent.tools.claude_adapter import ClaudeToolAdapter
from services.medical_agent.services.database_service import DatabaseService, DatabaseError, ValidationError

logger = logging.getLogger(__name__)

QueryType = Literal[
    "patient_summary",
    "admission_details",
    "diagnoses",
    "medications",
    "labs",
    "icu_vitals",
    "dataset_summary",
    "diagnosis_frequency",
    "medication_frequency",
    "admission_type_distribution",
]

PATIENT_OPERATIONS = {"patient_summary", "admission_details", "diagnoses", "medications", "labs", "icu_vitals"}
AGGREGATE_OPERATIONS = {"dataset_summary", "diagnosis_frequency", "medication_frequency", "admission_type_distribution"}

TOOL_DESCRIPTION = """Consulta datos clinicos hospitalarios del conjunto de datos de demostracion (100 pacientes desidentificados) mediante operaciones predefinidas de solo lectura.

Operaciones por paciente (requieren identificadores):
- patient_summary: resumen del paciente (demografia, ingresos, diagnosticos, ultimos laboratorios, medicacion). Requiere subject_id.
- admission_details: detalle de un ingreso hospitalario (diagnosticos, traslados, servicios). Requiere hadm_id.
- diagnoses: diagnosticos codificados con su descripcion. Por paciente (subject_id), por ingreso (hadm_id) o busqueda en el catalogo por icd_code / icd_title.
- medications: medicacion prescrita y administrada. Requiere subject_id o hadm_id.
- labs: resultados de laboratorio con nombre de la prueba, valor y unidades. Requiere subject_id; hadm_id opcional.
- icu_vitals: constantes y mediciones monitorizadas durante una estancia en UCI. Requiere stay_id; itemid opcional.

Estadisticas del conjunto de datos (no requieren identificadores):
- dataset_summary: recuentos globales (pacientes, ingresos, estancias UCI, diagnosticos, laboratorios, prescripciones).
- diagnosis_frequency: diagnosticos mas frecuentes (top_n, maximo 50).
- medication_frequency: farmacos mas prescritos (top_n, maximo 50).
- admission_type_distribution: distribucion de tipos de ingreso.

Identificadores: subject_id = paciente; hadm_id = ingreso hospitalario (episodio); stay_id = estancia en UCI.
No es posible ejecutar consultas libres ni acceder a informacion fuera de estas operaciones."""


class DatabaseToolInput(BaseModel):
    """Contrato cerrado visible al modelo: solo operaciones predefinidas."""

    model_config = ConfigDict(extra="forbid")

    query_type: QueryType = Field(description="Operacion predefinida a ejecutar")
    subject_id: Optional[int] = Field(None, description="Identificador del paciente", gt=0)
    hadm_id: Optional[int] = Field(None, description="Identificador del ingreso hospitalario", gt=0)
    stay_id: Optional[int] = Field(None, description="Identificador de la estancia en UCI", gt=0)
    itemid: Optional[int] = Field(None, description="Identificador de la medicion (solo icu_vitals)", gt=0)
    icd_code: Optional[str] = Field(None, description="Codigo ICD para buscar en el catalogo de diagnosticos", max_length=10)
    icd_title: Optional[str] = Field(None, description="Texto a buscar en la descripcion del catalogo de diagnosticos", max_length=100)
    top_n: Optional[int] = Field(None, description="Numero de grupos en las estadisticas (1-50)", ge=1, le=50)
    limit: Optional[int] = Field(None, description="Maximo de registros a devolver (1-200)", ge=1, le=200)


class DatabaseTool(ClaudeToolAdapter):
    """Acceso clinico allowlisted para el bucle legacy."""

    DEFAULT_ROW_LIMIT = 100
    MAX_ROW_LIMIT = 200
    DEFAULT_TOP_N = 10

    def __init__(self):
        try:
            self.db_service = DatabaseService()
            logger.info("DatabaseService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseService: {e}")
            raise
        super().__init__(
            tool_name="query_mimic_database",
            tool_description=TOOL_DESCRIPTION,
            args_schema=DatabaseToolInput,
        )
        logger.info("DatabaseTool initialized (allowlisted operations only)")

    # ------------------------------------------------------------------
    def execute(
        self,
        query_type: str,
        subject_id: Optional[int] = None,
        hadm_id: Optional[int] = None,
        stay_id: Optional[int] = None,
        itemid: Optional[int] = None,
        icd_code: Optional[str] = None,
        icd_title: Optional[str] = None,
        top_n: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"Executing database operation: {query_type}")
            if query_type == "patient_summary":
                return self._execute_patient_summary(subject_id)
            if query_type == "admission_details":
                return self._execute_admission_details(hadm_id)
            if query_type == "diagnoses":
                return self._execute_diagnoses(icd_code, icd_title, subject_id, hadm_id, limit)
            if query_type == "medications":
                return self._execute_medications(subject_id, hadm_id, limit)
            if query_type == "labs":
                return self._execute_labs(subject_id, hadm_id, limit)
            if query_type == "icu_vitals":
                return self._execute_icu_vitals(stay_id, itemid, limit)
            if query_type in AGGREGATE_OPERATIONS:
                return self._execute_aggregate(query_type, top_n)
            return {
                "success": False,
                "error": (
                    f"Operacion no permitida: '{query_type}'. Operaciones validas: "
                    + ", ".join(sorted(PATIENT_OPERATIONS | AGGREGATE_OPERATIONS))
                ),
                "data": None,
            }
        except ValidationError as e:
            logger.warning(f"Validation error in database operation: {e}")
            return {"success": False, "error": f"Error de validación: {str(e)}", "data": None}
        except DatabaseError as e:
            logger.error(f"Database error in operation execution: {e}")
            return {"success": False, "error": f"Error de base de datos: {str(e)}", "data": None}
        except Exception as e:
            logger.error(f"Unexpected error in database operation: {e}", exc_info=True)
            return {"success": False, "error": f"Error inesperado: {str(e)}", "data": None}

    # ------------------------------------------------------------------
    @staticmethod
    def _require_positive(value: Optional[int], name: str, operation: str) -> int:
        if not value:
            raise ValidationError(f"{name} es requerido para {operation}")
        if not isinstance(value, int) or value <= 0:
            raise ValidationError(f"{name} debe ser un entero positivo, recibido: {value}")
        return value

    def _limit(self, limit: Optional[int]) -> int:
        if limit is None or not isinstance(limit, int) or limit <= 0:
            return self.DEFAULT_ROW_LIMIT
        return min(limit, self.MAX_ROW_LIMIT)

    def _envelope(self, query_type: str, data: Any, parameters: Dict[str, Any], limit: Optional[int] = None) -> Dict[str, Any]:
        truncated = False
        if isinstance(data, list) and limit is not None and len(data) > limit:
            data = data[:limit]
            truncated = True
        result = {
            "success": True,
            "data": data,
            "query_type": query_type,
            "permissions": "read_only",
            "parameters": parameters,
        }
        if isinstance(data, list):
            result["count"] = len(data)
            result["truncated"] = truncated
        return result

    def _execute_patient_summary(self, subject_id: Optional[int]) -> Dict[str, Any]:
        sid = self._require_positive(subject_id, "subject_id", "patient_summary")
        return self._envelope("patient_summary", self.db_service.get_patient_summary(sid), {"subject_id": sid})

    def _execute_admission_details(self, hadm_id: Optional[int]) -> Dict[str, Any]:
        hadm = self._require_positive(hadm_id, "hadm_id", "admission_details")
        return self._envelope("admission_details", self.db_service.get_admission_details(hadm), {"hadm_id": hadm})

    def _execute_icu_vitals(self, stay_id: Optional[int], itemid: Optional[int], limit: Optional[int]) -> Dict[str, Any]:
        stay = self._require_positive(stay_id, "stay_id", "icu_vitals")
        result = self.db_service.get_icu_chartevents(stay, itemid)
        return self._envelope("icu_vitals", result, {"stay_id": stay, "itemid": itemid}, self._limit(limit))

    def _execute_labs(self, subject_id: Optional[int], hadm_id: Optional[int], limit: Optional[int]) -> Dict[str, Any]:
        sid = self._require_positive(subject_id, "subject_id", "labs")
        result = self.db_service.get_lab_results(sid, hadm_id)
        # mas recientes primero para que el recorte conserve lo relevante
        if isinstance(result, list):
            result = list(reversed(result))
        return self._envelope("labs", result, {"subject_id": sid, "hadm_id": hadm_id}, self._limit(limit))

    def _execute_diagnoses(self, icd_code: Optional[str], icd_title: Optional[str], subject_id: Optional[int],
                           hadm_id: Optional[int], limit: Optional[int]) -> Dict[str, Any]:
        if not icd_code and not icd_title and not subject_id and not hadm_id:
            raise ValidationError("Se requiere al menos un criterio: icd_code, icd_title, subject_id o hadm_id")
        if icd_code or icd_title:
            result = self.db_service.search_diagnoses(icd_code=icd_code, icd_title=icd_title)
        elif hadm_id:
            result = self.db_service.get_admission_diagnoses(self._require_positive(hadm_id, "hadm_id", "diagnoses"))
        else:
            result = self.db_service.get_patient_diagnoses(self._require_positive(subject_id, "subject_id", "diagnoses"))
        return self._envelope(
            "diagnoses", result,
            {"icd_code": icd_code, "icd_title": icd_title, "subject_id": subject_id, "hadm_id": hadm_id},
            self._limit(limit),
        )

    def _execute_medications(self, subject_id: Optional[int], hadm_id: Optional[int], limit: Optional[int]) -> Dict[str, Any]:
        if not subject_id and not hadm_id:
            raise ValidationError("subject_id o hadm_id es requerido para medications")
        if hadm_id:
            result = self.db_service.get_medications_by_admission(self._require_positive(hadm_id, "hadm_id", "medications"))
        else:
            result = self.db_service.get_medication_history(self._require_positive(subject_id, "subject_id", "medications"))
        return self._envelope("medications", result, {"subject_id": subject_id, "hadm_id": hadm_id}, self._limit(limit))

    # ------------------------------------------------------------------
    def _execute_aggregate(self, query_type: str, top_n: Optional[int]) -> Dict[str, Any]:
        """Agregados fijos del dataset via RPC (ClinicalDataProvider). Nunca SQL."""
        from chathce.composition.async_runner import run_sync
        from chathce.domain.errors import DomainError
        from chathce.legacy.clinical_bridge import get_legacy_clinical_provider, legacy_research_context

        n = top_n if isinstance(top_n, int) and 1 <= top_n <= 50 else self.DEFAULT_TOP_N
        provider = get_legacy_clinical_provider()
        ctx = legacy_research_context()
        try:
            if query_type == "dataset_summary":
                summary = run_sync(provider.get_dataset_summary(ctx))
                return self._envelope("dataset_summary", summary.model_dump(mode="json"), {})
            if query_type == "diagnosis_frequency":
                freq = run_sync(provider.top_diagnoses(ctx, limit=n))
            elif query_type == "medication_frequency":
                freq = run_sync(provider.top_drugs(ctx, limit=n))
            else:
                freq = run_sync(provider.admission_type_distribution(ctx))
        except DomainError as exc:
            return {"success": False, "error": exc.message, "data": None, "query_type": query_type}
        rows: List[Dict[str, Any]] = [
            {"categoria": b.label or b.key, "codigo": b.key, "frecuencia": b.count} for b in freq.buckets
        ]
        result = self._envelope(query_type, rows, {"top_n": n})
        result["truncated"] = freq.truncated
        result["scope"] = {"scope_type": "dataset_aggregate", "source": freq.source}
        return result

    # ------------------------------------------------------------------
    def format_output(self, output_data: Any) -> str:
        if isinstance(output_data, dict) and not output_data.get("success", False):
            return f"❌ Error: {output_data.get('error', 'Unknown error')}"
        return str(output_data)


def create_database_tool() -> DatabaseTool:
    return DatabaseTool()
