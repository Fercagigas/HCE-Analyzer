"""
Medical Agent Tools Module

Herramientas legacy del agente (colaboracion de visualizacion). La tool de base de
datos vive en services/unified_chat/tools/database_tool.py; la variante Claude
(database_tool_claude.py) se retiro en WP4 por ofrecer SQL libre.
"""

from .visualization_collaboration_tool import create_visualization_collaboration_tool, VisualizationCollaborationTool

__all__ = [
    "create_visualization_collaboration_tool",
    "VisualizationCollaborationTool"
]
