"""
Data validators for ChatHCE.
"""
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataValidator:
    """General-purpose data validator."""

    @staticmethod
    def is_non_empty_string(value: Any) -> bool:
        """Return True if value is a non-empty string."""
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def is_positive_int(value: Any) -> bool:
        """Return True if value is a positive integer."""
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
        """
        Validate that all required fields are present and non-None.

        Returns:
            Dict with keys: valid (bool), missing_fields (list)
        """
        missing = [field for field in required if data.get(field) is None]
        return {"valid": len(missing) == 0, "missing_fields": missing}

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Remove dangerous characters and truncate to max_length."""
        if not isinstance(text, str):
            return ""
        # Strip HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length]


class PatientDataValidator:
    """Validator for MIMIC-IV-ED patient data."""

    VALID_GENDERS = {"M", "F", "MALE", "FEMALE", "UNKNOWN"}

    @staticmethod
    def validate_subject_id(subject_id: Any) -> bool:
        """Validate that subject_id is a positive integer."""
        return DataValidator.is_positive_int(subject_id)

    @staticmethod
    def validate_stay_id(stay_id: Any) -> bool:
        """Validate that stay_id is a positive integer."""
        return DataValidator.is_positive_int(stay_id)

    @staticmethod
    def validate_vital_sign(value: Any, min_val: float, max_val: float) -> bool:
        """Validate a vital sign value is within physiological range."""
        try:
            v = float(value)
            return min_val <= v <= max_val
        except (TypeError, ValueError):
            return False

    @classmethod
    def validate_triage_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate triage data fields.

        Returns:
            Dict with keys: valid (bool), errors (list)
        """
        errors: List[str] = []

        if not cls.validate_subject_id(data.get("subject_id")):
            errors.append("Invalid subject_id")

        if data.get("heartrate") is not None:
            if not cls.validate_vital_sign(data["heartrate"], 0, 300):
                errors.append("heartrate out of range")

        if data.get("sbp") is not None:
            if not cls.validate_vital_sign(data["sbp"], 0, 300):
                errors.append("sbp out of range")

        if data.get("o2sat") is not None:
            if not cls.validate_vital_sign(data["o2sat"], 0, 100):
                errors.append("o2sat out of range")

        return {"valid": len(errors) == 0, "errors": errors}


__all__ = ["DataValidator", "PatientDataValidator"]
