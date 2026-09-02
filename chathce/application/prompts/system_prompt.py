"""build_system_prompt: plantilla estatica + herramientas desde ToolContract + contexto por peticion.

Orden pensado para prompt caching: la parte estable primero, el bloque de contexto al final.
`prompt_version` identifica plantilla y contratos usados (viaja en metadata y auditoria).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from chathce.domain.chat import ChatOptions
from chathce.domain.context import Purpose, RequestContext
from chathce.domain.tools import ToolContract, assert_no_schema_leak

TEMPLATE_VERSION = "1"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "chat_system.es.md"


def _load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8").strip()


def _describe_field(name: str, spec: Dict[str, Any], required: bool) -> str:
    kind = spec.get("type")
    if kind is None and "anyOf" in spec:
        kinds = [o.get("type") for o in spec["anyOf"] if o.get("type") and o.get("type") != "null"]
        kind = kinds[0] if kinds else "valor"
    if "enum" in spec:
        kind = "uno de: " + ", ".join(str(v) for v in spec["enum"])
    desc = spec.get("description", "")
    req = "obligatorio" if required else "opcional"
    default = spec.get("default")
    default_txt = f", por defecto {default}" if default not in (None, "") and not required else ""
    return f"    - {name} ({kind}, {req}{default_txt}){': ' + desc if desc else ''}"


def render_tools_section(contracts: Iterable[ToolContract]) -> str:
    lines: List[str] = ["# HERRAMIENTAS DISPONIBLES", "",
                        "Usa la herramienta más específica para cada pregunta. Los argumentos deben respetar el esquema; no inventes identificadores.", ""]
    for contract in contracts:
        schema = contract.input_schema()
        required = set(schema.get("required", []))
        props: Dict[str, Any] = schema.get("properties", {})
        lines.append(f"- **{contract.name}**: {contract.description}")
        if props:
            lines.append("  Argumentos:")
            for name, spec in props.items():
                lines.append(_describe_field(name, spec, name in required))
        if contract.requires_patient_scope:
            lines.append("  Requiere paciente activo en el contexto.")
        if contract.requires_purpose is not None:
            lines.append(f"  Solo disponible con propósito '{contract.requires_purpose.value}'.")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_context_block(ctx: RequestContext, options: Optional[ChatOptions] = None) -> str:
    patient = ctx.patient_id or "ninguno (pide al usuario que seleccione un paciente antes de consultar datos clínicos)"
    encounter = ctx.encounter_id or "cualquiera del paciente activo"
    lines = [
        "# CONTEXTO AUTORIZADO DE ESTA PETICIÓN",
        "",
        f"- Paciente activo: {patient}",
        f"- Episodio activo: {encounter}",
        f"- Propósito: {ctx.purpose.value}",
    ]
    if ctx.purpose != Purpose.research:
        lines.append("- Las estadísticas del conjunto de datos NO están disponibles en este modo.")
    if options is not None and not options.enable_visualizations:
        lines.append("- Las visualizaciones están desactivadas en esta sesión.")
    lines.append("- Si el usuario menciona otro paciente, no lo consultes: indícale que cambie el paciente activo.")
    return "\n".join(lines)


def build_system_prompt(
    contracts: Iterable[ToolContract],
    ctx: RequestContext,
    options: Optional[ChatOptions] = None,
) -> Tuple[str, str]:
    """(system_prompt, prompt_version)."""
    contracts = list(contracts)
    static_part = _load_template() + "\n\n" + render_tools_section(contracts)
    assert_no_schema_leak(static_part, where="El system prompt")
    digest = hashlib.sha256(static_part.encode("utf-8")).hexdigest()[:8]
    prompt_version = f"chat-system/{TEMPLATE_VERSION}+{digest}"
    prompt = static_part + "\n\n" + render_context_block(ctx, options)
    return prompt, prompt_version
