"""Minimizacion y deteccion de PHI antes de entregar contexto a un modelo.

Este modulo no conserva el valor original ni emite logs.  El catalogo es el
contrato central para los DTOs clinicos; los textos libres se inspeccionan en
las fronteras de ChatService y ToolRegistry.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel


class PhiAction(str, Enum):
    remove = "remove"
    generalize = "generalize"
    pseudonymize = "pseudonymize"


class PhiDetectionMode(str, Enum):
    observe = "observe"
    redact = "redact"
    block = "block"


@dataclass(frozen=True)
class PhiFieldPolicy:
    action: PhiAction
    category: str


# Catalogo de los campos que pueden identificar a una persona en datos reales.
# Los identificadores se conservan solo como tokens estables dentro de la sesion.
CLINICAL_PHI_CATALOG: Mapping[str, Mapping[str, PhiFieldPolicy]] = {
    "Patient": {
        "subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"),
        "date_of_death": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
        "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    },
    "Admission": {
        "subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"),
        "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"),
        "admittime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
        "dischtime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
        "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    },
    "Transfer": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "transfer_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"), "intime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "outtime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "ServiceEpisode": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "transfertime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "Condition": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "Procedure": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "chartdate": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "LabObservation": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "labevent_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"), "charttime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "Medication": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "starttime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "stoptime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "event_txt": PhiFieldPolicy(PhiAction.remove, "free_text"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "IcuStay": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "stay_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"), "intime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "outtime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
    "IcuObservation": {"subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"), "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"), "stay_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"), "charttime": PhiFieldPolicy(PhiAction.generalize, "exact_date"), "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id")},
}

_GENERIC_CLINICAL_FIELD_POLICIES: Mapping[str, PhiFieldPolicy] = {
    "subject_id": PhiFieldPolicy(PhiAction.pseudonymize, "patient_id"),
    "hadm_id": PhiFieldPolicy(PhiAction.pseudonymize, "encounter_id"),
    "stay_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    "transfer_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    "labevent_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    "evidence_id": PhiFieldPolicy(PhiAction.pseudonymize, "record_id"),
    "event_txt": PhiFieldPolicy(PhiAction.remove, "free_text"),
    "admittime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "dischtime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "intime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "outtime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "charttime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "chartdate": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "starttime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
    "stoptime": PhiFieldPolicy(PhiAction.generalize, "exact_date"),
}


@dataclass(frozen=True)
class PhiFinding:
    category: str
    value: str


@dataclass(frozen=True)
class PhiTextResult:
    text: str
    findings: List[PhiFinding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.findings)


_PATTERNS = (
    ("dni", re.compile(r"(?<![A-Z0-9])\d{8}[TRWAGMYFPDXBNJZSQVHLCKE](?![A-Z0-9])", re.IGNORECASE)),
    ("nie", re.compile(r"(?<![A-Z0-9])[XYZ]\d{7}[TRWAGMYFPDXBNJZSQVHLCKE](?![A-Z0-9])", re.IGNORECASE)),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.IGNORECASE)),
    ("phone", re.compile(r"(?<!\w)(?:\+34[ .-]?)?(?:\d[ .-]?){9}(?!\w)")),
    # Solo tras un marcador clinico; evita convertir terminos del golden set en nombres.
    ("name", re.compile(r"\b(?:[Pp]aciente|[Nn]ombre|[Nn]ame|[Ss]r\.?|[Ss]ra\.?)\s*[:\-]?\s*([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){1,3})")),
)


class PhiMinimizer:
    """Politica sin estado salvo el secreto efimero de la sesion."""

    def __init__(self, *, session_id: Optional[str] = None, mode: PhiDetectionMode | str = PhiDetectionMode.redact):
        self._session_key = (session_id or "anonymous").encode("utf-8")
        self.mode = PhiDetectionMode(mode)

    def inspect_text(self, text: str) -> PhiTextResult:
        findings: List[PhiFinding] = []
        for category, pattern in _PATTERNS:
            for match in pattern.finditer(text or ""):
                value = match.group(1) if category == "name" else match.group(0)
                findings.append(PhiFinding(category, value))
        if self.mode == PhiDetectionMode.observe or not findings:
            return PhiTextResult(text=text, findings=findings)
        if self.mode == PhiDetectionMode.block:
            return PhiTextResult(text="", findings=findings)
        redacted = text
        # Reemplazar valores, no la etiqueta "Paciente", mantiene la pregunta comprensible.
        for finding in sorted(findings, key=lambda item: len(item.value), reverse=True):
            redacted = redacted.replace(finding.value, f"[PHI_{finding.category.upper()}]")
        return PhiTextResult(text=redacted, findings=findings)

    def minimize(self, value: Any) -> Any:
        return self._minimize(value, {})

    def pseudonymize(self, value: Any, category: str = "record_id") -> Optional[str]:
        """Token estable en la sesion, util tambien para metadatos de auditoria."""
        if value is None:
            return None
        return self._apply_policy(value, PhiFieldPolicy(PhiAction.pseudonymize, category))

    def _minimize(self, value: Any, policies: Mapping[str, PhiFieldPolicy]) -> Any:
        if isinstance(value, BaseModel):
            return self._minimize(value.model_dump(mode="python"), CLINICAL_PHI_CATALOG.get(value.__class__.__name__, {}))
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for key, item in value.items():
                policy = policies.get(str(key)) or _GENERIC_CLINICAL_FIELD_POLICIES.get(str(key))
                if policy is not None:
                    transformed = self._apply_policy(item, policy)
                    if transformed is not _REMOVED:
                        out[str(key)] = transformed
                else:
                    out[str(key)] = self._minimize(item, {})
            return out
        if isinstance(value, list):
            return [self._minimize(item, policies) for item in value]
        if isinstance(value, tuple):
            return [self._minimize(item, policies) for item in value]
        if isinstance(value, str):
            return self.inspect_text(value).text
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _apply_policy(self, value: Any, policy: PhiFieldPolicy) -> Any:
        if value is None:
            return None
        if policy.action == PhiAction.remove:
            return _REMOVED
        if policy.action == PhiAction.generalize:
            return str(value)[:7]  # YYYY-MM: conserva secuencia clinica, no fecha exacta.
        digest = hmac.new(self._session_key, str(value).encode("utf-8"), hashlib.sha256).hexdigest()[:10]
        prefix = {"patient_id": "PATIENT", "encounter_id": "ENCOUNTER", "record_id": "RECORD"}.get(policy.category, "TOKEN")
        return f"{prefix}_{digest}"


_REMOVED = object()
