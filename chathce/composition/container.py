"""Composition root: construye adapters y servicios a partir de Settings (unico lugar que valida credenciales).

Perfiles:
- ``clinical.provider``: ``supabase_mimic`` (por defecto) | ``memory``
- ``llm.provider``: ``anthropic`` (por defecto) | ``fake``
- persistencia/identidad: Supabase si hay credenciales; en memoria si no (o en perfil memory).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from chathce.adapters.logging.audit_sink import build_audit_sink
from chathce.adapters.memory import (
    FakeLLMProvider,
    InMemoryAnalysisRepository,
    InMemoryConversationRepository,
    InMemoryIdentityProvider,
    InMemoryKnowledgeRepository,
    InMemoryUserPreferencesRepository,
    InMemoryVisualizationRepository,
)
from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient, register_clinical_aggregate_rpcs
from chathce.application.chat_service import ChatService, ChatServiceConfig
from chathce.application.conversation_service import ConversationService
from chathce.application.knowledge_service import KnowledgeService
from chathce.application.patient_summary_service import PatientSummaryService
from chathce.application.rate_limit import RateLimitConfig, RateLimiter
from chathce.application.scope_guard import ScopeGuard
from chathce.composition.async_runner import AsyncRunner
from chathce.gateway.model_gateway import GatewayConfig, ModelGateway
from chathce.gateway.policy import ToolPolicy
from chathce.gateway.tool_registry import ToolRegistry
from chathce.gateway.tools import build_clinical_tools, build_knowledge_tool, build_visualization_tool


@dataclass
class Container:
    settings: Any
    audit: Any
    llm_provider: Any
    clinical_provider: Any          # ya envuelto por ScopeGuard
    identity: Any
    conversations: Any
    analyses: Any
    preferences: Any
    knowledge: Any
    visualizations: Any
    registry: ToolRegistry
    gateway: ModelGateway
    chat_service: ChatService
    conversation_service: ConversationService
    patient_summary_service: PatientSummaryService
    knowledge_service: KnowledgeService
    rate_limiter: RateLimiter
    runner: AsyncRunner = field(default_factory=AsyncRunner)
    profile: dict = field(default_factory=dict)

    def run(self, coro, *, timeout: Optional[float] = 180.0):
        return self.runner.run(coro, timeout=timeout)


def _has_supabase(settings: Any) -> bool:
    db = settings.database
    return bool(db.supabase_url and db.supabase_key)


def build_container(settings: Any, *, llm_provider: Any = None, clinical_provider: Any = None,
                    knowledge: Any = None, persist: Optional[bool] = None) -> Container:
    audit = build_audit_sink(settings)
    profile: dict = {}

    # ---- LLM ------------------------------------------------------------
    if llm_provider is None:
        if settings.llm.provider == "fake":
            llm_provider = FakeLLMProvider()
            profile["llm"] = "fake"
        else:
            from chathce.adapters.anthropic.provider import AnthropicLLMProvider

            llm_provider = AnthropicLLMProvider(settings.require_anthropic(), default_timeout_s=settings.llm.request_timeout_s)
            profile["llm"] = "anthropic"

    # ---- datos clinicos ---------------------------------------------------
    clinical = settings.clinical
    supabase_clients = None
    if clinical_provider is None:
        from chathce.adapters.supabase.mimic_clinical_data_provider import MimicClinicalDataProvider

        if clinical.provider == "memory" or not _has_supabase(settings):
            client = register_clinical_aggregate_rpcs(InMemoryPostgrestClient())
            profile["clinical"] = "memory"
        else:
            from chathce.adapters.supabase.client_factory import SupabaseClients

            db = settings.require_database()
            supabase_clients = SupabaseClients(url=db.supabase_url, service_key=db.supabase_key,
                                               clinical_key=clinical.supabase_clinical_key, postgrest_timeout_s=clinical.timeout_s)
            client = supabase_clients.clinical_client()
            profile["clinical"] = "supabase_mimic" + (" (clave dedicada)" if supabase_clients.uses_dedicated_clinical_key else "")
        clinical_provider = MimicClinicalDataProvider(
            client, source_name=clinical.source_name, default_limit=clinical.default_limit, max_limit=clinical.max_limit,
            aggregate_limit=clinical.aggregate_limit, timeout_s=clinical.timeout_s,
        )
    guarded = clinical_provider if isinstance(clinical_provider, ScopeGuard) else ScopeGuard(clinical_provider, audit=audit)

    # ---- persistencia, identidad, conocimiento ----------------------------
    use_supabase_product = _has_supabase(settings) and clinical.provider != "memory"
    if use_supabase_product:
        from chathce.adapters.supabase.analysis_repository import SupabaseAnalysisRepository
        from chathce.adapters.supabase.client_factory import SupabaseClients
        from chathce.adapters.supabase.conversation_repository import SupabaseConversationRepository
        from chathce.adapters.supabase.identity_provider import SupabaseIdentityProvider
        from chathce.adapters.supabase.knowledge_repository import SupabaseKnowledgeRepository
        from chathce.adapters.supabase.user_preferences_repository import SupabaseUserPreferencesRepository

        if supabase_clients is None:
            db = settings.require_database()
            supabase_clients = SupabaseClients(url=db.supabase_url, service_key=db.supabase_key,
                                               clinical_key=clinical.supabase_clinical_key, postgrest_timeout_s=clinical.timeout_s)
        product = supabase_clients.product_client()
        identity = SupabaseIdentityProvider(product)
        conversations = SupabaseConversationRepository(product)
        analyses = SupabaseAnalysisRepository(product)
        preferences = SupabaseUserPreferencesRepository(product)
        knowledge = knowledge or SupabaseKnowledgeRepository()
        profile["persistence"] = "supabase"
    else:
        identity = InMemoryIdentityProvider()
        conversations = InMemoryConversationRepository()
        analyses = InMemoryAnalysisRepository()
        preferences = InMemoryUserPreferencesRepository()
        knowledge = knowledge or InMemoryKnowledgeRepository()
        profile["persistence"] = "memory"
    visualizations = InMemoryVisualizationRepository()

    # ---- gateway y servicios ---------------------------------------------
    registry = ToolRegistry(policy=ToolPolicy(), audit=audit, max_visible_chars=settings.llm.max_tool_visible_chars)
    for tool in build_clinical_tools(guarded):
        registry.register(tool)
    registry.register(build_knowledge_tool(knowledge))
    registry.register(build_visualization_tool(guarded, visualizations))

    gateway = ModelGateway(llm_provider, registry, GatewayConfig(
        model_chain=list(settings.llm.model_chain), max_tokens=settings.llm.max_tokens, temperature=settings.llm.temperature,
        request_timeout_s=settings.llm.request_timeout_s, total_timeout_s=settings.llm.total_timeout_s,
        max_retries_per_model=settings.llm.max_retries_per_model, max_iterations=settings.llm.max_iterations,
    ), audit=audit)

    security = settings.security
    rate_limiter = RateLimiter(RateLimitConfig(
        per_minute=security.rate_limit_per_minute, per_hour=security.rate_limit_per_hour, burst=security.burst_limit,
        burst_window_s=security.burst_window_seconds, max_message_length=security.max_message_length,
        lockout_s=float(security.lockout_duration_seconds),
    ))
    conversation_service = ConversationService(conversations if (persist is not False) else None, analyses)
    chat_service = ChatService(gateway, registry, conversation_service, visualizations, rate_limiter=rate_limiter, audit=audit,
                               config=ChatServiceConfig(max_message_length=security.max_message_length))

    return Container(
        settings=settings, audit=audit, llm_provider=llm_provider, clinical_provider=guarded, identity=identity,
        conversations=conversations, analyses=analyses, preferences=preferences, knowledge=knowledge,
        visualizations=visualizations, registry=registry, gateway=gateway, chat_service=chat_service,
        conversation_service=conversation_service, patient_summary_service=PatientSummaryService(guarded),
        knowledge_service=KnowledgeService(knowledge, audit), rate_limiter=rate_limiter, profile=profile,
    )
