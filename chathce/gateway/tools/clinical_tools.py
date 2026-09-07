"""Tools clinicas allowlisted sobre ClinicalDataProvider (ADR 0050). Sin SQL, sin nombres de tabla."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.clinical import Page, TimeRange
from chathce.domain.context import Purpose, RequestContext
from chathce.domain.evidence import EvidenceType
from chathce.domain.tools import AuditCategory, ToolContract, ToolResult
from chathce.gateway.tool_registry import Tool
from chathce.gateway.tools._evidence import evidence_from_dtos

_closed = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Inputs (visibles al modelo)
# ---------------------------------------------------------------------------
class PatientSummaryInput(BaseModel):
    model_config = _closed
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)


class AdmissionDetailsInput(BaseModel):
    model_config = _closed
    hadm_id: int = Field(description="Identificador del ingreso hospitalario (episodio)", gt=0)


class DiagnosesInput(BaseModel):
    model_config = _closed
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso concreto", gt=0)
    limit: int = Field(50, ge=1, le=100, description="Maximo de diagnosticos")


class LabsInput(BaseModel):
    model_config = _closed
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso concreto", gt=0)
    itemids: Optional[List[int]] = Field(None, description="Identificadores de prueba (itemid) concretos", max_length=20)
    label_contains: Optional[str] = Field(None, description="Texto contenido en el nombre de la prueba (p. ej. 'Hemoglobin')", max_length=80)
    start: Optional[datetime] = Field(None, description="Inicio del intervalo temporal (ISO 8601)")
    end: Optional[datetime] = Field(None, description="Fin del intervalo temporal (ISO 8601)")
    abnormal_only: bool = Field(False, description="Solo resultados marcados como anormales")
    limit: int = Field(50, ge=1, le=200, description="Maximo de resultados (mas recientes primero)")


class SearchLabItemsInput(BaseModel):
    model_config = _closed
    label_contains: str = Field(description="Texto a buscar en el nombre de la prueba de laboratorio", min_length=2, max_length=80)
    limit: int = Field(20, ge=1, le=50)


class MedicationsInput(BaseModel):
    model_config = _closed
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso concreto", gt=0)
    drug_contains: Optional[str] = Field(None, description="Texto contenido en el nombre del farmaco", max_length=80)
    include_administrations: bool = Field(False, description="Incluir registros de administracion ademas de prescripciones")
    limit: int = Field(50, ge=1, le=100)


class IcuStaysInput(BaseModel):
    model_config = _closed
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso concreto", gt=0)
    limit: int = Field(10, ge=1, le=20)


class IcuObservationsInput(BaseModel):
    model_config = _closed
    stay_id: int = Field(description="Identificador de la estancia en UCI del paciente activo", gt=0)
    itemids: Optional[List[int]] = Field(None, description="Identificadores de medicion (itemid) concretos", max_length=20)
    label_contains: Optional[str] = Field(None, description="Texto contenido en el nombre de la medicion (p. ej. 'Heart Rate')", max_length=80)
    start: Optional[datetime] = Field(None, description="Inicio del intervalo temporal (ISO 8601)")
    end: Optional[datetime] = Field(None, description="Fin del intervalo temporal (ISO 8601)")
    limit: int = Field(100, ge=1, le=200, description="Maximo de mediciones (mas recientes primero)")


class SearchIcdInput(BaseModel):
    model_config = _closed
    code_prefix: Optional[str] = Field(None, description="Prefijo del codigo ICD", max_length=10)
    title_contains: Optional[str] = Field(None, description="Texto contenido en la descripcion del codigo", max_length=80)
    icd_version: Optional[Literal[9, 10]] = Field(None, description="Version ICD")
    kind: Literal["diagnosis", "procedure"] = Field("diagnosis", description="Catalogo: diagnosticos o procedimientos")
    limit: int = Field(20, ge=1, le=50)


class DatasetStatisticsInput(BaseModel):
    model_config = _closed
    statistic: Literal["dataset_summary", "top_diagnoses", "top_drugs", "admission_type_distribution"] = Field(
        description="Estadistica fija del conjunto de datos"
    )
    limit: int = Field(20, ge=1, le=50, description="Numero de grupos (top_diagnoses, top_drugs)")
    icd_version: Optional[Literal[9, 10]] = Field(None, description="Filtrar top_diagnoses por version ICD")


class AnyOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


def _time_range(start: Optional[datetime], end: Optional[datetime]) -> Optional[TimeRange]:
    if start is None and end is None:
        return None
    return TimeRange(start=start, end=end)


def _ok(ctx: RequestContext, operation: str, data: Any, *, count: Optional[int] = None, limit: Optional[int] = None,
        truncated: bool = False, evidence=None) -> ToolResult:
    if isinstance(data, Page):
        count, limit, truncated = data.count, data.limit, data.truncated
    return ToolResult(
        tool_name="", tool_use_id="", success=True, operation=operation, scope=ctx.scope(), data=data,
        count=count if count is not None else (1 if data is not None else 0), limit=limit or 100, truncated=truncated,
        evidence=evidence or [],
    )


def build_clinical_tools(provider: Any) -> List[Tool]:
    source = getattr(provider, "source_name", "clinical")

    def ev(ctx, dtos, tool_name, kind=EvidenceType.clinical_record):
        return evidence_from_dtos(ctx, dtos, tool_name=tool_name, provider="clinical_data_provider", source_system=source, kind=kind)

    async def patient_summary(ctx: RequestContext, args: PatientSummaryInput) -> ToolResult:
        summary = await provider.get_patient_summary(ctx, args.subject_id)
        dtos = [summary.patient, *summary.admissions, *summary.conditions, *summary.recent_labs, *summary.medications, *summary.icu_stays]
        return _ok(ctx, "get_patient_summary", summary, count=1, limit=1, truncated=any(summary.truncated.values()),
                   evidence=ev(ctx, dtos, "get_patient_summary"))

    async def admission_details(ctx: RequestContext, args: AdmissionDetailsInput) -> ToolResult:
        details = await provider.get_admission_details(ctx, args.hadm_id)
        dtos = [details.admission, *details.conditions, *details.procedures, *details.transfers, *details.icu_stays]
        return _ok(ctx, "get_admission_details", details, count=1, limit=1, evidence=ev(ctx, dtos, "get_admission_details"))

    async def diagnoses(ctx: RequestContext, args: DiagnosesInput) -> ToolResult:
        page = await provider.list_conditions(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id, limit=args.limit)
        return _ok(ctx, "list_conditions", page, evidence=ev(ctx, page.items, "get_diagnoses"))

    async def labs(ctx: RequestContext, args: LabsInput) -> ToolResult:
        page = await provider.list_lab_observations(
            ctx, subject_id=args.subject_id, hadm_id=args.hadm_id, itemids=args.itemids, label_contains=args.label_contains,
            time_range=_time_range(args.start, args.end), abnormal_only=args.abnormal_only, limit=args.limit,
        )
        return _ok(ctx, "list_lab_observations", page, evidence=ev(ctx, page.items, "get_labs"))

    async def search_lab_items(ctx: RequestContext, args: SearchLabItemsInput) -> ToolResult:
        page = await provider.search_lab_items(ctx, label_contains=args.label_contains, limit=args.limit)
        return _ok(ctx, "search_lab_items", page)

    async def medications(ctx: RequestContext, args: MedicationsInput) -> ToolResult:
        page = await provider.list_medications(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id,
                                               drug_contains=args.drug_contains, include_emar=args.include_administrations, limit=args.limit)
        return _ok(ctx, "list_medications", page, evidence=ev(ctx, page.items, "get_medications"))

    async def icu_stays(ctx: RequestContext, args: IcuStaysInput) -> ToolResult:
        page = await provider.list_icu_stays(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id, limit=args.limit)
        return _ok(ctx, "list_icu_stays", page, evidence=ev(ctx, page.items, "get_icu_stays"))

    async def icu_observations(ctx: RequestContext, args: IcuObservationsInput) -> ToolResult:
        page = await provider.list_icu_observations(ctx, stay_id=args.stay_id, itemids=args.itemids, label_contains=args.label_contains,
                                                    time_range=_time_range(args.start, args.end), limit=args.limit)
        return _ok(ctx, "list_icu_observations", page, evidence=ev(ctx, page.items, "get_icu_observations"))

    async def search_icd(ctx: RequestContext, args: SearchIcdInput) -> ToolResult:
        page = await provider.search_icd_codes(ctx, code_prefix=args.code_prefix, title_contains=args.title_contains,
                                               icd_version=args.icd_version, kind=args.kind, limit=args.limit)
        return _ok(ctx, "search_icd_codes", page)

    async def dataset_statistics(ctx: RequestContext, args: DatasetStatisticsInput) -> ToolResult:
        if args.statistic == "dataset_summary":
            data = await provider.get_dataset_summary(ctx)
            return _ok(ctx, "get_dataset_summary", data, count=1, limit=1)
        if args.statistic == "top_diagnoses":
            data = await provider.top_diagnoses(ctx, limit=args.limit, icd_version=args.icd_version)
        elif args.statistic == "top_drugs":
            data = await provider.top_drugs(ctx, limit=args.limit)
        else:
            data = await provider.admission_type_distribution(ctx)
        return _ok(ctx, data.operation, data, count=len(data.buckets), limit=data.limit, truncated=data.truncated)

    clinical = dict(permissions="read_only", audit_category=AuditCategory.clinical_data)  # noqa: F841 (documental)

    return [
        Tool(ToolContract(
            name="get_patient_summary",
            description="Resumen del paciente activo: demografia, ingresos, diagnosticos con descripcion, ultimos laboratorios, medicacion y estancias en UCI.",
            input_model=PatientSummaryInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("demographics", "admissions", "diagnoses", "labs", "medications", "icu"),
            max_rows=1, timeout_s=45.0,
        ), patient_summary),
        Tool(ToolContract(
            name="get_admission_details",
            description="Detalle de un ingreso hospitalario del paciente activo: fechas, tipo, diagnosticos y procedimientos codificados, traslados, servicios y estancias en UCI.",
            input_model=AdmissionDetailsInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("admissions", "diagnoses", "procedures", "transfers", "icu"), max_rows=1,
        ), admission_details),
        Tool(ToolContract(
            name="get_diagnoses",
            description="Diagnosticos codificados (ICD-9/ICD-10) del paciente activo con su descripcion, opcionalmente limitados a un ingreso.",
            input_model=DiagnosesInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("diagnoses",), max_rows=100,
        ), diagnoses),
        Tool(ToolContract(
            name="get_labs",
            description="Resultados de laboratorio del paciente activo (nombre de la prueba, valor, unidades, rango de referencia, marca de anormal), mas recientes primero. Filtra por nombre de prueba, ingreso, intervalo temporal o solo anormales.",
            input_model=LabsInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("labs",), max_rows=200,
        ), labs),
        Tool(ToolContract(
            name="search_lab_items",
            description="Busca en el catalogo de pruebas de laboratorio por nombre para obtener identificadores (itemid) y categorias.",
            input_model=SearchLabItemsInput, output_model=AnyOutput, requires_patient_scope=False,
            audit_category=AuditCategory.clinical_data, max_rows=50,
        ), search_lab_items),
        Tool(ToolContract(
            name="get_medications",
            description="Medicacion prescrita al paciente activo (farmaco, dosis, via, inicio y fin), opcionalmente por ingreso o por nombre; puede incluir registros de administracion.",
            input_model=MedicationsInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("medications",), max_rows=100,
        ), medications),
        Tool(ToolContract(
            name="get_icu_stays",
            description="Estancias en UCI del paciente activo (unidad de entrada y salida, fechas y duracion).",
            input_model=IcuStaysInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("icu",), max_rows=20,
        ), icu_stays),
        Tool(ToolContract(
            name="get_icu_observations",
            description="Mediciones monitorizadas (constantes vitales y otros parametros) de una estancia en UCI del paciente activo, mas recientes primero; filtra por nombre de medicion o intervalo.",
            input_model=IcuObservationsInput, output_model=AnyOutput, requires_patient_scope=True,
            audit_category=AuditCategory.clinical_data, data_categories=("icu",), max_rows=200,
        ), icu_observations),
        Tool(ToolContract(
            name="search_icd_codes",
            description="Busca en el catalogo ICD de diagnosticos o procedimientos por prefijo de codigo o texto de la descripcion (no contiene datos de pacientes).",
            input_model=SearchIcdInput, output_model=AnyOutput, requires_patient_scope=False,
            audit_category=AuditCategory.clinical_data, max_rows=50,
        ), search_icd),
        Tool(ToolContract(
            name="get_dataset_statistics",
            description="Estadisticas fijas de todo el conjunto de datos (recuentos globales, diagnosticos mas frecuentes, farmacos mas prescritos, distribucion de tipos de ingreso). Solo en modo investigacion; nunca devuelve pacientes concretos.",
            input_model=DatasetStatisticsInput, output_model=AnyOutput, requires_patient_scope=False, requires_purpose=Purpose.research,
            audit_category=AuditCategory.dataset_aggregate, data_categories=("aggregate",), max_rows=50,
        ), dataset_statistics),
    ]
