"""
Report formatter utilities for ChatHCE.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportFormatter:
    """Formats data into human-readable reports."""

    @staticmethod
    def format_patient_summary(data: Dict[str, Any]) -> str:
        """
        Format a patient summary dict into a readable string.

        Args:
            data: Patient data dictionary

        Returns:
            Formatted string report
        """
        lines = ["## Resumen del Paciente", ""]

        subject_id = data.get("subject_id", "N/A")
        stay_id = data.get("stay_id", "N/A")
        gender = data.get("gender", "N/A")
        race = data.get("race", "N/A")
        disposition = data.get("disposition", "N/A")

        lines.append(f"**ID Paciente**: {subject_id}")
        lines.append(f"**ID Estancia**: {stay_id}")
        lines.append(f"**Género**: {gender}")
        lines.append(f"**Raza/Etnia**: {race}")
        lines.append(f"**Disposición**: {disposition}")

        intime = data.get("intime")
        outtime = data.get("outtime")
        if intime:
            lines.append(f"**Ingreso**: {intime}")
        if outtime:
            lines.append(f"**Egreso**: {outtime}")

        return "\n".join(lines)

    @staticmethod
    def format_vital_signs(vitals: List[Dict[str, Any]]) -> str:
        """
        Format a list of vital sign records into a readable table.

        Args:
            vitals: List of vital sign dicts

        Returns:
            Formatted string
        """
        if not vitals:
            return "No se encontraron registros de signos vitales."

        lines = ["## Signos Vitales", ""]
        header = "| Hora | FC | FR | SpO2 | PAS | PAD | Temp |"
        separator = "|------|----|----|------|-----|-----|------|"
        lines.append(header)
        lines.append(separator)

        for v in vitals:
            charttime = v.get("charttime", "")
            if isinstance(charttime, str) and "T" in charttime:
                charttime = charttime.replace("T", " ")[:16]

            row = (
                f"| {charttime} "
                f"| {v.get('heartrate', '-')} "
                f"| {v.get('resprate', '-')} "
                f"| {v.get('o2sat', '-')} "
                f"| {v.get('sbp', '-')} "
                f"| {v.get('dbp', '-')} "
                f"| {v.get('temperature', '-')} |"
            )
            lines.append(row)

        return "\n".join(lines)

    @staticmethod
    def format_diagnoses(diagnoses: List[Dict[str, Any]]) -> str:
        """
        Format a list of diagnosis records.

        Args:
            diagnoses: List of diagnosis dicts

        Returns:
            Formatted string
        """
        if not diagnoses:
            return "No se encontraron diagnósticos."

        lines = ["## Diagnósticos", ""]
        for i, d in enumerate(diagnoses, 1):
            icd_code = d.get("icd_code", "N/A")
            icd_title = d.get("icd_title", "N/A")
            icd_version = d.get("icd_version", "")
            lines.append(f"{i}. **{icd_code}** (ICD-{icd_version}): {icd_title}")

        return "\n".join(lines)

    @staticmethod
    def format_medications(medications: List[Dict[str, Any]]) -> str:
        """
        Format a list of medication records.

        Args:
            medications: List of medication dicts

        Returns:
            Formatted string
        """
        if not medications:
            return "No se encontraron medicamentos."

        lines = ["## Medicamentos", ""]
        for med in medications:
            name = med.get("name", "N/A")
            charttime = med.get("charttime", "")
            source = med.get("source", "")
            category = med.get("etcdescription", "")

            entry = f"- **{name}**"
            if charttime:
                entry += f" ({charttime})"
            if source:
                entry += f" [{source}]"
            if category:
                entry += f" — {category}"
            lines.append(entry)

        return "\n".join(lines)

    @staticmethod
    def format_error(error_message: str) -> str:
        """Format an error message for display."""
        return f"❌ **Error**: {error_message}\n\nPor favor, intente nuevamente."

    @staticmethod
    def format_timestamp(dt: Optional[datetime] = None) -> str:
        """Format a datetime as a readable string."""
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%d/%m/%Y %H:%M:%S")


__all__ = ["ReportFormatter"]
