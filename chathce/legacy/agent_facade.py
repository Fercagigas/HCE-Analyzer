"""LegacyAgentFacade: conserva el contrato ``process_message(...) -> dict`` para la UI Streamlit y Evaluation.

Construye el RequestContext explicito (ADR 0010 §2), invoca ChatService y devuelve el
dict legacy. Lo usan los runners de Evaluation/ y `services.unified_chat.unified_agent`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from chathce.composition.container import Container
from chathce.domain.chat import ChatOptions, ChatRequest
from chathce.domain.context import Channel, Purpose, RequestContext, build_context
from chathce.domain.errors import PurposeNotAllowed
from chathce.legacy.response_mapper import from_legacy_history, to_legacy_dict

logger = logging.getLogger(__name__)

LEGACY_USER_ID = "legacy-runtime"


class LegacyAgentFacade:
    def __init__(self, container: Container, *, channel: Channel = Channel.evaluation, persist: bool = False):
        self._container = container
        self._channel = channel
        self._persist = persist

    # ------------------------------------------------------------------
    def build_context(self, *, session_id: Optional[str], patient_id: Optional[str], encounter_id: Optional[str],
                      purpose: Optional[str], user_id: Optional[str], roles: Optional[Iterable[str]]) -> RequestContext:
        roles_set = set(roles or ())
        requested = Purpose(purpose) if purpose else Purpose.clinical_care
        if requested == Purpose.research:
            roles_set.add("researcher")  # el runtime legacy no tiene identidad; el canal evaluation/streamlit lo autoriza
        return build_context(user_id=user_id or LEGACY_USER_ID, channel=self._channel, roles=roles_set, purpose=requested,
                             patient_id=patient_id, encounter_id=encounter_id, session_id=session_id)

    def process_message(
        self,
        message: str,
        context: Any = None,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        encounter_id: Optional[str] = None,
        purpose: Optional[str] = None,
        user_id: Optional[str] = None,
        roles: Optional[Iterable[str]] = None,
        options: Optional[ChatOptions] = None,
    ) -> Dict[str, Any]:
        try:
            ctx = self.build_context(session_id=session_id, patient_id=patient_id, encounter_id=encounter_id,
                                     purpose=purpose, user_id=user_id, roles=roles)
        except PurposeNotAllowed as exc:
            return {"success": False, "content": f"⚠️ {exc.message}", "tools_used": [], "tool_results": [], "visualizations": [],
                    "sources": [], "metadata": {"error_type": exc.code}, "model_used": "none", "tokens_used": 0,
                    "error": exc.message, "error_type": exc.code, "suggestions": []}
        request = ChatRequest(message=message, session_id=session_id, patient_id=ctx.patient_id, encounter_id=ctx.encounter_id,
                              purpose=ctx.purpose, history=from_legacy_history(context), options=options or ChatOptions())
        response = self._container.run(self._container.chat_service.handle_chat(request, ctx, persist=self._persist))
        legacy = to_legacy_dict(response, query_length=len(message))
        legacy["session_id"] = response.metadata.session_id
        return legacy

    def get_performance_stats(self) -> Dict[str, Any]:
        return {"engine": "chathce.gateway", "profile": dict(self._container.profile)}

    def reset_to_primary_model(self) -> None:
        return None
