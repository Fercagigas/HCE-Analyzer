# Guía de creación de herramientas — ChatHCE

**Última actualización**: 2 de septiembre de 2026 (Fase 1)

## Modelo

Una herramienta es un par `Tool(contract, handler)` (`chathce/gateway/tool_registry.py`):

- `ToolContract` (`chathce/domain/tools.py`): lo único que el modelo ve (nombre, descripción, schema de entrada) más la política (`requires_patient_scope`, `requires_purpose`, `timeout_s`, `max_rows`, `audit_category`, `data_categories`).
- `handler(ctx: RequestContext, args: InputModel) -> ToolResult`: función `async` que usa exclusivamente ports del core (nunca `supabase`, `anthropic`, `streamlit`).

`ToolRegistry.dispatch` se encarga de validar la entrada, aplicar la política, el timeout, validar la salida, recortar filas, renderizar para el modelo y auditar. El handler solo produce datos.

## Reglas obligatorias

1. `input_model` con `model_config = ConfigDict(extra="forbid")`. El contrato falla al construirse si no es así.
2. Nombre, descripción y descripciones de campos **sin** `sql`, `select`, `custom_query`, `table_name`, nombres de esquema ni de tabla (`LLM_VISIBLE_FORBIDDEN_PATTERN`). Describe la operación en términos clínicos.
3. Si la tool lee datos de un paciente: `requires_patient_scope=True` y el handler debe pasar `ctx` al `ClinicalDataProvider` (ya envuelto por `ScopeGuard`). Nunca aceptes un `subject_id` sin comprobarlo contra `ctx.patient_id` (el guard lo hace).
4. Si la tool devuelve agregados de población: `requires_purpose=Purpose.research` y datos exclusivamente de RPC versionadas.
5. `max_rows <= 200`; devuelve `count`, `limit`, `truncated`.
6. Cada elemento devuelto lleva `evidence_id`; construye `Evidence` con `evidence_from_dtos` (`chathce/gateway/tools/_evidence.py`) o manualmente como en `knowledge_tool.py`.
7. Sin lógica de presentación ni de prompt en el handler. Texto para el usuario solo en `data.message`.

## Ejemplo mínimo

```python
# chathce/gateway/tools/procedures_tool.py
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field
from chathce.domain.context import RequestContext
from chathce.domain.tools import AuditCategory, ToolContract, ToolResult
from chathce.gateway.tool_registry import Tool
from chathce.gateway.tools._evidence import evidence_from_dtos


class ProceduresInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int = Field(description="Identificador del paciente activo", gt=0)
    hadm_id: Optional[int] = Field(None, description="Limitar a un ingreso", gt=0)
    limit: int = Field(100, ge=1, le=200)


class AnyOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


def build_procedures_tool(provider: Any) -> Tool:
    async def handler(ctx: RequestContext, args: ProceduresInput) -> ToolResult:
        page = await provider.list_procedures(ctx, subject_id=args.subject_id, hadm_id=args.hadm_id, limit=args.limit)
        return ToolResult(
            tool_name="", tool_use_id="", success=True, operation="list_procedures", scope=ctx.scope(),
            data={"items": [p.model_dump(mode="json") for p in page.items]},
            count=page.count, limit=page.limit, truncated=page.truncated,
            evidence=evidence_from_dtos(ctx, page.items, tool_name="get_procedures"),
        )

    contract = ToolContract(
        name="get_procedures",
        description="Procedimientos codificados (ICD) realizados al paciente activo, con fecha y descripcion.",
        input_model=ProceduresInput, output_model=AnyOutput,
        requires_patient_scope=True, audit_category=AuditCategory.clinical_data,
        data_categories=("procedures",), max_rows=200,
    )
    return Tool(contract, handler)
```

## Pasos

1. **Port**: si la operación no existe, añádela a `chathce/ports/clinical_data_provider.py` con `ctx` como primer argumento y DTO en `chathce/domain/clinical.py` (con `evidence_id`).
2. **Adapters**: implementa la operación en `chathce/adapters/supabase/mimic_clinical_data_provider.py` (PostgREST con `select` explícito y `.eq("subject_id", ctx.patient_id)`) y, si aplica, en el cliente en memoria para tests. Añade el método a `ScopeGuard` con la comprobación de scope correspondiente.
3. **Tool**: crea el fichero en `chathce/gateway/tools/`, expórtala en `chathce/gateway/tools/__init__.py`.
4. **Registro**: en `chathce/composition/container.py`, `registry.register(build_procedures_tool(guarded))`.
5. **Tests**: unit del handler con fakes (`tests/fakes/container_factory.build_test_container`), contract del adapter contra fixtures (`tests/contract/`), y seguridad si toca scope (`tests/security/`). Ejecuta `tests/security/test_tool_schema_surface.py`.
6. **Evaluación**: añade casos al golden set (`scripts/build_golden_set_mimiciv.py`) y a `Evaluation/golden_set.py` (`ALLOWED_OPERATIONS`) si procede.
7. **Docs**: tabla de tools en `docs/UNIFIED_CHAT_ARCHITECTURE.md`.

## Qué no hacer

- No aceptar SQL, nombres de tabla, filtros genéricos ni `params` libres.
- No llamar a `supabase`/`anthropic` desde el handler.
- No devolver más filas de las que permite el contrato ni omitir `truncated`.
- No incluir texto del usuario en descripciones ni en el prompt.
