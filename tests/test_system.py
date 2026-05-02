"""
Tests generales del sistema ChatHCE.

Verifica que los componentes principales se importan y funcionan correctamente.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestImports:
    """Verifica que todos los módulos principales se importan correctamente."""
    
    def test_config_imports(self):
        """Verifica imports de configuración."""
        from config.settings import settings
        from config.config import RAG_CONFIG
        
        assert settings is not None
        assert RAG_CONFIG is not None
    
    def test_rag_service_imports(self):
        """Verifica imports de servicios RAG."""
        from services.rag.parent_child_chunker import ParentChildChunker
        from services.rag.supabase_vector_store import SupabaseVectorStore
        from services.rag.reranker import Reranker
        
        assert ParentChildChunker is not None
        assert SupabaseVectorStore is not None
        assert Reranker is not None
    
    def test_visualization_imports(self):
        """Verifica imports de visualización."""
        from services.medical_agent.visualization_agent import VisualizationAgent
        from services.medical_agent.visualization_handler import VisualizationHandler
        
        assert VisualizationAgent is not None
        assert VisualizationHandler is not None


class TestVisualizationAgent:
    """Tests básicos para VisualizationAgent."""
    
    def test_initialization(self):
        """Verifica inicialización del agente."""
        from services.medical_agent.visualization_agent import VisualizationAgent
        
        agent = VisualizationAgent()
        assert agent is not None
        assert hasattr(agent, 'generate_visualization')
    
    def test_get_performance_stats(self):
        """Verifica estadísticas de rendimiento."""
        from services.medical_agent.visualization_agent import VisualizationAgent
        
        agent = VisualizationAgent()
        stats = agent.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert 'total_visualizations' in stats


class TestVisualizationHandler:
    """Tests básicos para VisualizationHandler."""
    
    def test_initialization(self):
        """Verifica inicialización del handler."""
        from services.medical_agent.visualization_handler import VisualizationHandler
        
        handler = VisualizationHandler()
        assert handler is not None
    
    def test_process_empty_response(self):
        """Verifica procesamiento de respuesta vacía."""
        from services.medical_agent.visualization_handler import VisualizationHandler
        
        handler = VisualizationHandler()
        result = handler.process_agent_response({'success': False})
        
        assert isinstance(result, dict)


class TestDatabaseTool:
    """Tests básicos para DatabaseTool."""
    
    def test_tool_imports(self):
        """Verifica que el tool se importa correctamente."""
        from services.unified_chat.tools.database_tool import DatabaseTool
        assert DatabaseTool is not None


class TestRAGTool:
    """Tests básicos para RAGTool."""
    
    def test_tool_imports(self):
        """Verifica que el tool se importa correctamente."""
        from services.unified_chat.tools.rag_tool import RAGTool
        assert RAGTool is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
