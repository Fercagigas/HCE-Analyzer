"""Allowlisted MIMIC-IV-ED database tool for the unified chat agent."""

import logging
from typing import Any, Dict, List, Literal, Optional, Union, get_args

from pydantic import BaseModel, ConfigDict, Field

from services.medical_agent.services.database_service import (
    DatabaseError,
    DatabaseService,
    ValidationError,
)
from services.medical_agent.tools.claude_adapter import ClaudeToolAdapter

logger = logging.getLogger(__name__)


QueryType = Literal[
    "patient_summary",
    "encounter_summary",
    "vital_signs",
    "diagnoses",
    "medications",
    "triage",
    "dataset_summary",
    "diagnosis_frequency",
    "medication_frequency",
    "acuity_distribution",
]


class DatabaseToolInput(BaseModel):
    """Allowlisted input contract exposed to the model."""

    model_config = ConfigDict(extra="forbid")

    query_type: QueryType = Field(
        description="Allowlisted clinical or MIMIC research operation"
    )
    subject_id: Optional[int] = Field(
        None,
        description="Patient identifier; required for patient-scoped operations",
    )
    stay_id: Optional[int] = Field(
        None,
        description="Encounter identifier; required for encounter-scoped operations",
    )
    icd_code: Optional[str] = Field(
        None,
        max_length=20,
        description="Optional ICD code used only to narrow a scoped diagnosis query",
    )
    icd_title: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional title used only to narrow a scoped diagnosis query",
    )
    limit: int = Field(
        100,
        ge=1,
        le=200,
        description="Maximum returned rows or aggregate groups (default 100, max 200)",
    )


class DatabaseScope(BaseModel):
    """Scope attached to every successful database result."""

    scope_type: Literal[
        "patient", "encounter", "patient_and_encounter", "dataset_aggregate"
    ]
    subject_id: Optional[int] = None
    stay_id: Optional[int] = None


class DatabaseToolOutput(BaseModel):
    """Explicit top-level output contract for database operations."""

    success: bool
    query_type: Optional[QueryType] = None
    permissions: Literal["read_only"] = "read_only"
    scope: Optional[DatabaseScope] = None
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    count: int = 0
    limit: int = 0
    timeout_seconds: int = 30
    truncated: bool = False
    error: Optional[str] = None


class DatabaseTool(ClaudeToolAdapter):
    """Read MIMIC through fixed operations with deterministic scope enforcement."""

    MAX_ROW_LIMIT = 200
    DEFAULT_ROW_LIMIT = 100
    TIMEOUT_SECONDS = 30

    PATIENT_OR_ENCOUNTER_OPERATIONS = {"diagnoses", "medications", "triage"}
    DATASET_AGGREGATE_OPERATIONS = {
        "dataset_summary",
        "diagnosis_frequency",
        "medication_frequency",
        "acuity_distribution",
    }

    def __init__(self):
        self.db_service = DatabaseService()
        super().__init__(
            tool_name="query_mimic_database",
            tool_description="""Read MIMIC-IV-ED through allowlisted operations only.

PATIENT/ENCOUNTER OPERATIONS:
- patient_summary: requires subject_id.
- encounter_summary and vital_signs: require stay_id.
- diagnoses, medications and triage: require subject_id or stay_id. Optional ICD filters only narrow diagnoses inside that scope.

CONTROLLED RESEARCH AGGREGATES:
- dataset_summary, diagnosis_frequency, medication_frequency and acuity_distribution.
- These return counts or bounded groups only; they never enumerate a cohort's patient rows.

CONTRACT:
- Permission: read_only.
- Patient/encounter scope is enforced in code, not by prompt instructions.
- Returned rows/groups: default 100, hard maximum 200.
- Provider request timeout: 30 seconds.
- Output: {success, query_type, permissions, scope, data, count, limit, timeout_seconds, truncated, error}.
- Arbitrary SQL, table names, generic filters and write operations are not accepted.""",
            args_schema=DatabaseToolInput,
        )
        logger.info("DatabaseTool initialized with allowlisted operations")

    def execute(
        self,
        query_type: QueryType,
        subject_id: Optional[int] = None,
        stay_id: Optional[int] = None,
        icd_code: Optional[str] = None,
        icd_title: Optional[str] = None,
        limit: int = DEFAULT_ROW_LIMIT,
    ) -> Dict[str, Any]:
        """Execute one allowlisted read operation."""
        try:
            validated_limit = self._get_validated_limit(limit)
            scope = self._validate_scope(query_type, subject_id, stay_id)
            logger.info(
                "Executing allowlisted database operation: type=%s scope=%s",
                query_type,
                scope.scope_type,
            )

            if query_type == "patient_summary":
                data = self.db_service.get_patient_summary(subject_id)
            elif query_type == "encounter_summary":
                data = self.db_service.get_stay_details(stay_id)
            elif query_type == "vital_signs":
                data = self.db_service.get_vital_signs(stay_id, limit=validated_limit)
            elif query_type == "diagnoses":
                data = self.db_service.get_scoped_diagnoses(
                    subject_id=subject_id,
                    stay_id=stay_id,
                    icd_code=icd_code,
                    icd_title=icd_title,
                    limit=validated_limit,
                )
            elif query_type == "medications":
                data = self.db_service.get_scoped_medications(
                    subject_id=subject_id,
                    stay_id=stay_id,
                    limit=validated_limit,
                )
            elif query_type == "triage":
                data = self.db_service.get_scoped_triage(
                    subject_id=subject_id,
                    stay_id=stay_id,
                    limit=validated_limit,
                )
            elif query_type == "dataset_summary":
                data = self.db_service.get_dataset_summary()
            elif query_type == "diagnosis_frequency":
                data = self.db_service.get_diagnosis_frequency(top_n=validated_limit)
            elif query_type == "medication_frequency":
                data = self.db_service.get_medication_frequency(top_n=validated_limit)
            elif query_type == "acuity_distribution":
                data = self.db_service.get_acuity_distribution()
            else:
                raise ValidationError(f"Operación no permitida: '{query_type}'")

            capped_data, truncated = self._cap_output(data, validated_limit)
            return DatabaseToolOutput(
                success=True,
                query_type=query_type,
                scope=scope,
                data=capped_data,
                count=self._count_output(capped_data),
                limit=validated_limit,
                timeout_seconds=self.TIMEOUT_SECONDS,
                truncated=truncated,
            ).model_dump()
        except ValidationError as exc:
            logger.warning("Database operation rejected: %s", exc)
            return self._error_output(query_type, f"Error de validación: {exc}")
        except DatabaseError as exc:
            logger.error("Database operation failed: %s", exc)
            return self._error_output(query_type, f"Error de base de datos: {exc}")
        except Exception as exc:
            logger.error("Unexpected database tool error: %s", exc, exc_info=True)
            return self._error_output(query_type, f"Error inesperado: {exc}")

    def _validate_scope(
        self,
        query_type: str,
        subject_id: Optional[int],
        stay_id: Optional[int],
    ) -> DatabaseScope:
        if subject_id is not None and (
            not isinstance(subject_id, int) or subject_id <= 0
        ):
            raise ValidationError("subject_id debe ser un entero positivo")
        if stay_id is not None and (not isinstance(stay_id, int) or stay_id <= 0):
            raise ValidationError("stay_id debe ser un entero positivo")

        if query_type == "patient_summary":
            if subject_id is None:
                raise ValidationError("subject_id es obligatorio para patient_summary")
            return DatabaseScope(scope_type="patient", subject_id=subject_id)

        if query_type in {"encounter_summary", "vital_signs"}:
            if stay_id is None:
                raise ValidationError(f"stay_id es obligatorio para {query_type}")
            return DatabaseScope(scope_type="encounter", stay_id=stay_id)

        if query_type in self.PATIENT_OR_ENCOUNTER_OPERATIONS:
            if subject_id is None and stay_id is None:
                raise ValidationError(
                    f"{query_type} requiere subject_id o stay_id; "
                    "no se permiten listados dataset-wide"
                )
            if subject_id is not None and stay_id is not None:
                return DatabaseScope(
                    scope_type="patient_and_encounter",
                    subject_id=subject_id,
                    stay_id=stay_id,
                )
            if subject_id is not None:
                return DatabaseScope(scope_type="patient", subject_id=subject_id)
            return DatabaseScope(scope_type="encounter", stay_id=stay_id)

        if query_type in self.DATASET_AGGREGATE_OPERATIONS:
            if subject_id is not None or stay_id is not None:
                raise ValidationError(
                    f"{query_type} es una agregación fija y no acepta scope de paciente"
                )
            return DatabaseScope(scope_type="dataset_aggregate")

        raise ValidationError(f"Operación no permitida: '{query_type}'")

    def _cap_output(self, data: Any, limit: int) -> tuple[Any, bool]:
        """Cap top-level rows and list fields contained in summary objects."""
        if isinstance(data, list):
            return data[:limit], len(data) > limit
        if isinstance(data, dict):
            capped: Dict[str, Any] = {}
            truncated = False
            for key, value in data.items():
                if isinstance(value, list):
                    capped[key] = value[:limit]
                    truncated = truncated or len(value) > limit
                else:
                    capped[key] = value
            return capped, truncated
        raise ValidationError("La operación devolvió un tipo de datos no permitido")

    def _get_validated_limit(self, limit: int) -> int:
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("limit debe ser un entero positivo")
        if limit > self.MAX_ROW_LIMIT:
            raise ValidationError(f"limit no puede superar {self.MAX_ROW_LIMIT}")
        return limit

    def _count_output(self, data: Any) -> int:
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict) and isinstance(data.get("groups"), list):
            return len(data["groups"])
        return 1 if data else 0

    def _error_output(self, query_type: str, error: str) -> Dict[str, Any]:
        safe_query_type = query_type if query_type in get_args(QueryType) else None
        return DatabaseToolOutput(
            success=False,
            query_type=safe_query_type,
            error=error,
            timeout_seconds=self.TIMEOUT_SECONDS,
        ).model_dump()

    def format_output(self, output_data: Any) -> str:
        """Format the validated output for the model without exposing internals."""
        if not isinstance(output_data, dict):
            return str(output_data)
        if not output_data.get("success"):
            return f"❌ {output_data.get('error', 'Error desconocido')}"

        scope = output_data.get("scope") or {}
        lines = [
            f"✅ Operación completada: {output_data.get('query_type')}",
            f"Ámbito: {scope.get('scope_type', 'desconocido')}",
            f"Registros/grupos: {output_data.get('count', 0)}",
        ]
        if scope.get("subject_id"):
            lines.append(f"Paciente: {scope['subject_id']}")
        if scope.get("stay_id"):
            lines.append(f"Estancia: {scope['stay_id']}")
        if output_data.get("truncated"):
            lines.append(f"⚠️ Resultado truncado al límite {output_data.get('limit')}")
        lines.append(f"Datos: {output_data.get('data')}")
        return "\n".join(lines)


def create_database_tool() -> DatabaseTool:
    """Create the allowlisted database tool."""
    return DatabaseTool()
