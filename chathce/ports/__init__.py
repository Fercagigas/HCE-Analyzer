"""Ports (interfaces) del core. Los adapters los implementan; el core solo depende de ellos."""

from chathce.ports.analysis_repository import AnalysisRepository
from chathce.ports.audit_sink import AuditSink
from chathce.ports.clinical_data_provider import ClinicalDataProvider
from chathce.ports.conversation_repository import ConversationRepository
from chathce.ports.identity_provider import IdentityProvider, OidcCapableIdentityProvider
from chathce.ports.knowledge_repository import KnowledgeRepository
from chathce.ports.knowledge_governance import KnowledgeApprovalAuthorizer
from chathce.ports.llm_provider import LLMProvider
from chathce.ports.user_preferences_repository import UserPreferencesRepository
from chathce.ports.visualization_repository import VisualizationRepository

__all__ = [
    "AnalysisRepository",
    "AuditSink",
    "ClinicalDataProvider",
    "ConversationRepository",
    "IdentityProvider",
    "OidcCapableIdentityProvider",
    "KnowledgeRepository",
    "KnowledgeApprovalAuthorizer",
    "LLMProvider",
    "UserPreferencesRepository",
    "VisualizationRepository",
]
