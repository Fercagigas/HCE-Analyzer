"""Kill switch de generacion de IA, consultable en cada peticion.

El fichero opcional permite cambiar el estado sin reiniciar el proceso: contiene
``enabled`` o ``disabled``. Si no existe, prevalece la configuracion base.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AIGenerationStatus:
    enabled: bool
    source: str
    changed: bool = False


class AIGenerationGate:
    def __init__(self, *, enabled: bool = True, state_file: Optional[str] = None):
        self._default_enabled = enabled
        self._state_file = Path(state_file) if state_file else None
        self._last: Optional[tuple[bool, str]] = (enabled, "config")

    def status(self) -> AIGenerationStatus:
        enabled, source = self._default_enabled, "config"
        if self._state_file:
            try:
                if self._state_file.exists():
                    value = self._state_file.read_text(encoding="utf-8").strip().lower()
                    if value in {"enabled", "true", "1", "on"}:
                        enabled, source = True, "runtime_file"
                    elif value in {"disabled", "false", "0", "off"}:
                        enabled, source = False, "runtime_file"
                    else:
                        # Un valor invalido no debe reactivar IA por accidente.
                        enabled, source = False, "runtime_file_invalid"
            except OSError:
                enabled, source = False, "runtime_file_unavailable"
        current = (enabled, source)
        changed = self._last is not None and self._last != current
        self._last = current
        return AIGenerationStatus(enabled=enabled, source=source, changed=changed)
