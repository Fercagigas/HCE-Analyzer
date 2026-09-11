"""Validacion local y politica minima de la ingesta documental gobernada."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List

from chathce.domain.context import RequestContext


MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".txt"})
KNOWLEDGE_MANAGER_ROLE = "knowledge_manager"

# El analisis es deliberadamente conservador: no interpreta el contenido como
# instrucciones y deja una marca para revision humana. No sustituye AV/DLP.
INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions?\b", re.I),
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"\b(you\s+are|act\s+as)\s+(chatgpt|an?\s+assistant|the\s+system)\b", re.I),
    re.compile(r"\b(reveal|exfiltrate|send)\b.{0,80}\b(password|secret|token|prompt)\b", re.I | re.S),
)


@dataclass(frozen=True)
class GovernanceValidation:
    content_hash: str
    flags: List[str]


class ContextRoleKnowledgeApprovalAuthorizer:
    """Implementacion temporal hasta conectar el provider RBAC/ABAC de Fase 2."""

    def can_approve_documents(self, ctx: RequestContext) -> bool:
        return KNOWLEDGE_MANAGER_ROLE in ctx.roles


def validate_upload(file_path: str, metadata: Dict[str, str]) -> GovernanceValidation:
    """Valida tipo, tamano, metadata y contenido sin registrar texto ni rutas."""
    path = Path(file_path)
    if not path.is_file():
        raise ValueError("archivo_no_encontrado")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("tipo_de_archivo_no_permitido")
    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise ValueError("archivo_supera_tamano_maximo")

    required = ("title", "doc_type", "specialty", "version", "effective_from")
    missing = [key for key in required if not str(metadata.get(key, "")).strip()]
    if missing:
        raise ValueError("metadata_obligatoria_incompleta")
    try:
        date.fromisoformat(str(metadata["effective_from"]))
        if metadata.get("effective_to"):
            end = date.fromisoformat(str(metadata["effective_to"]))
            if end < date.fromisoformat(str(metadata["effective_from"])):
                raise ValueError("vigencia_invalida")
    except ValueError:
        raise ValueError("vigencia_invalida") from None

    digest = hashlib.sha256()
    sample = bytearray()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            if len(sample) < 256 * 1024:
                sample.extend(block[: 256 * 1024 - len(sample)])
    text = bytes(sample).decode("utf-8", errors="ignore")
    flags = ["possible_prompt_injection"] if any(pattern.search(text) for pattern in INJECTION_PATTERNS) else []
    return GovernanceValidation(content_hash=digest.hexdigest(), flags=flags)
