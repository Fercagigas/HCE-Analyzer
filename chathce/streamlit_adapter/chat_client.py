"""StreamlitChatClient: llama a ChatService con el contexto de la sesion Streamlit y devuelve el dict legacy que renderiza la UI."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from chathce.composition.container import Container
from chathce.domain.chat import ChatOptions, ChatRequest
from chathce.domain.context import Channel, Purpose, RequestContext, build_context
from chathce.domain.errors import DomainError
from chathce.legacy.response_mapper import to_legacy_dict


class StreamlitChatClient:
    def __init__(self, container: Container):
        self._container = container

    def build_context(self, *, user_id: str, roles: Iterable[str], session_id: Optional[str], patient_id: Optional[str],
                      encounter_id: Optional[str], research_mode: bool) -> RequestContext:
        purpose = Purpose.research if research_mode else Purpose.clinical_care
        return build_context(user_id=user_id, channel=Channel.streamlit, roles=set(roles), purpose=purpose,
                             patient_id=patient_id, encounter_id=encounter_id, session_id=session_id)

    def send(self, message: str, *, user_id: str, roles: Iterable[str], session_id: Optional[str], patient_id: Optional[str],
             encounter_id: Optional[str], research_mode: bool, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            ctx = self.build_context(user_id=user_id, roles=roles, session_id=session_id, patient_id=patient_id,
                                     encounter_id=encounter_id, research_mode=research_mode)
        except DomainError as exc:
            return {"success": False, "content": f"⚠️ {exc.message}", "tools_used": [], "tool_results": [], "visualizations": [],
                    "sources": [], "metadata": {"error_type": exc.code}, "model_used": "none", "tokens_used": 0,
                    "error": exc.message, "error_type": exc.code, "suggestions": []}
        opts = ChatOptions(
            max_context_messages=int((options or {}).get("max_context_messages", 10)),
            include_sources=bool((options or {}).get("show_sources", True)),
            enable_visualizations=bool((options or {}).get("enable_visualizations", True)),
        )
        request = ChatRequest(message=message, session_id=session_id, patient_id=ctx.patient_id, encounter_id=ctx.encounter_id,
                              purpose=ctx.purpose, options=opts)
        response = self._container.run(self._container.chat_service.handle_chat(request, ctx, persist=True))
        legacy = to_legacy_dict(response, query_length=len(message))
        legacy["session_id"] = response.metadata.session_id
        return legacy

    def figure_json(self, *, user_id: str, viz_id: str) -> Optional[str]:
        ctx = RequestContext(user_id=user_id, channel=Channel.streamlit)
        artifact = self._container.run(self._container.visualizations.get(ctx, viz_id))
        return artifact.figure_json if artifact is not None else None
