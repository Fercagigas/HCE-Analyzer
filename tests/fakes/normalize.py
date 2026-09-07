"""Normalizacion de estructuras para comparar salidas grabadas con salidas actuales."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any


def _default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # pragma: no cover
            pass
    if hasattr(value, "item"):  # numpy scalars
        try:
            return value.item()
        except Exception:  # pragma: no cover
            pass
    return str(value)


def _clean(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def normalize(value: Any) -> Any:
    """JSON round-trip: fechas a ISO, NaN a None, numpy a nativos, claves ordenadas."""
    return _clean(json.loads(json.dumps(_clean(value), default=_default, sort_keys=True)))


def dump_json(value: Any) -> str:
    return json.dumps(normalize(value), ensure_ascii=False, indent=2, sort_keys=True)
