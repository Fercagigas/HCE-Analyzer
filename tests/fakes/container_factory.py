"""Contenedor de pruebas: fixtures MIMIC en memoria + FakeLLMProvider + repositorios en memoria."""

from __future__ import annotations

from typing import Optional, Sequence, Union

from chathce.adapters.memory import (
    CollectingAuditSink,
    FakeLLMProvider,
    InMemoryAnalysisRepository,
    InMemoryConversationRepository,
    InMemoryIdentityProvider,
    InMemoryKnowledgeRepository,
    InMemoryUserPreferencesRepository,
    InMemoryVisualizationRepository,
    ScriptedTurn,
)
from chathce.application.chat_service import ChatService, ChatServiceConfig
from chathce.application.conversation_service import ConversationService
from chathce.application.knowledge_service import KnowledgeService
from chathce.application.patient_summary_service import PatientSummaryService
from chathce.application.rate_limit import RateLimitConfig, RateLimiter
from chathce.application.scope_guard import ScopeGuard
from chathce.composition.container import Container
from chathce.gateway.model_gateway import GatewayConfig, ModelGateway
from chathce.gateway.tool_registry import ToolRegistry
from chathce.gateway.tools import build_clinical_tools, build_knowledge_tool, build_visualization_tool
from tests.fakes.mimic_fixtures import make_memory_client, make_provider


async def _no_sleep(_: float) -> None:
    return None


def build_test_container(
    turns: Optional[Sequence[Union[ScriptedTurn, BaseException]]] = None,
    *,
    knowledge: Optional[InMemoryKnowledgeRepository] = None,
    rate_limit: bool = False,
    max_iterations: int = 4,
) -> Container:
    audit = CollectingAuditSink()
    llm = FakeLLMProvider(list(turns or []))
    guarded = ScopeGuard(make_provider(make_memory_client()), audit=audit)
    knowledge_repo = knowledge or InMemoryKnowledgeRepository()
    visualizations = InMemoryVisualizationRepository()

    registry = ToolRegistry(audit=audit, max_visible_chars=4000)
    for tool in build_clinical_tools(guarded):
        registry.register(tool)
    registry.register(build_knowledge_tool(knowledge_repo))
    registry.register(build_visualization_tool(guarded, visualizations))

    gateway = ModelGateway(llm, registry, GatewayConfig(model_chain=["fake-primary", "fake-secondary"], max_iterations=max_iterations),
                           audit=audit, sleep=_no_sleep)
    conversations = InMemoryConversationRepository()
    analyses = InMemoryAnalysisRepository()
    conversation_service = ConversationService(conversations, analyses)
    limiter = RateLimiter(RateLimitConfig(per_minute=3, burst=2, burst_window_s=1000.0, lockout_s=60.0))
    chat_service = ChatService(gateway, registry, conversation_service, visualizations, rate_limiter=limiter, audit=audit,
                               config=ChatServiceConfig(rate_limit_enabled=rate_limit))
    return Container(
        settings=None, audit=audit, llm_provider=llm, clinical_provider=guarded, identity=InMemoryIdentityProvider(),
        conversations=conversations, analyses=analyses, preferences=InMemoryUserPreferencesRepository(), knowledge=knowledge_repo,
        visualizations=visualizations, registry=registry, gateway=gateway, chat_service=chat_service,
        conversation_service=conversation_service, patient_summary_service=PatientSummaryService(guarded),
        knowledge_service=KnowledgeService(knowledge_repo, audit), rate_limiter=limiter, profile={"llm": "fake", "clinical": "memory"},
    )
