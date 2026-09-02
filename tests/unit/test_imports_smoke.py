"""Los modulos principales se importan sin credenciales ni red (sustituye a test_system.py)."""

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


def test_visualization_agent_initializes_offline():
    from services.medical_agent.visualization_agent import VisualizationAgent

    agent = VisualizationAgent()
    stats = agent.get_performance_stats()
    assert isinstance(stats, dict)
    assert "total_visualizations" in stats


def test_unified_chat_tools_are_importable():
    from services.unified_chat.tools.database_tool import DatabaseTool
    from services.unified_chat.tools.rag_tool import RAGTool

    assert DatabaseTool and RAGTool
