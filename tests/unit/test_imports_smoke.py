"""Los modulos principales se importan sin credenciales ni red."""

import pytest

pytestmark = pytest.mark.unit


def test_config_is_importable_and_lazy():
    from config import get_settings
    from config.settings import ConfigurationError

    settings = get_settings()
    assert settings.database.supabase_url is None
    with pytest.raises(ConfigurationError) as exc:
        settings.require_database()
    assert "SUPABASE_URL" in str(exc.value)
    assert "SUPABASE_KEY" in str(exc.value)


def test_rag_components_are_importable():
    from services.rag.parent_child_chunker import ParentChildChunker
    from services.rag.reranker import Reranker
    from services.rag.supabase_vector_store import SupabaseVectorStore

    assert ParentChildChunker and Reranker and SupabaseVectorStore


def test_core_packages_are_importable():
    from chathce.adapters.visualization.plotly_templates import create_allowlisted_visualization
    from chathce.composition.container import build_container
    from chathce.gateway.tools import build_clinical_tools, build_knowledge_tool, build_visualization_tool
    from chathce.legacy.agent_facade import LegacyAgentFacade

    assert create_allowlisted_visualization and build_container and build_clinical_tools
    assert build_knowledge_tool and build_visualization_tool and LegacyAgentFacade


def test_legacy_facade_module_is_importable_without_credentials():
    from services.unified_chat.unified_agent import UnifiedChatAgent, create_unified_agent

    assert UnifiedChatAgent and create_unified_agent


def test_memory_profile_container_builds_without_credentials(monkeypatch):
    monkeypatch.setenv("CLINICAL_PROVIDER", "memory")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("AUDIT_SINK", "null")
    from config import get_settings
    from chathce.composition.container import build_container

    container = build_container(get_settings())
    assert container.profile == {"llm": "fake", "clinical": "memory", "persistence": "memory"}
    assert set(container.registry.names()) >= {"get_patient_summary", "get_labs", "search_clinical_documents", "create_visualization"}
