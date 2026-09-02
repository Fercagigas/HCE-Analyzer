"""Adapters en memoria: fakes deterministas para tests y para el perfil `memory` de desarrollo."""

from chathce.adapters.memory.audit import CollectingAuditSink, NullAuditSink
from chathce.adapters.memory.fake_llm_provider import FakeLLMProvider, ScriptedTurn
from chathce.adapters.memory.repositories import (
    InMemoryAnalysisRepository,
    InMemoryConversationRepository,
    InMemoryIdentityProvider,
    InMemoryKnowledgeRepository,
    InMemoryUserPreferencesRepository,
    InMemoryVisualizationRepository,
)

__all__ = [
    "CollectingAuditSink",
    "NullAuditSink",
    "FakeLLMProvider",
    "ScriptedTurn",
    "InMemoryAnalysisRepository",
    "InMemoryConversationRepository",
    "InMemoryIdentityProvider",
    "InMemoryKnowledgeRepository",
    "InMemoryUserPreferencesRepository",
    "InMemoryVisualizationRepository",
]
