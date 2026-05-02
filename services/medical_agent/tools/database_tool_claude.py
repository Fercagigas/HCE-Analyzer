"""
Claude-Compatible Database Query Tool

This module provides database query functionality for Claude agent.
It uses the database service directly for query execution.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .claude_adapter import ClaudeToolAdapter
from ..services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class DatabaseQueryInput(BaseModel):
    """Input schema for database query tool."""
    query_type: str = Field(
        description="Type of query: patient_summary, stay_details, search_diagnoses, get_vital_signs, medication_history, custom"
    )
    subject_id: Optional[int] = Field(None, description="Patient identifier")
    stay_id: Optional[int] = Field(None, description="Stay identifier")
    icd_code: Optional[str] = Field(None, description="ICD code for diagnosis search")
    icd_title: Optional[str] = Field(None, description="ICD title search term")
    custom_query: Optional[str] = Field(None, description="Custom SQL query")
    params: Optional[Dict] = Field(None, description="Query parameters")


class ClaudeDatabaseQueryTool(ClaudeToolAdapter):
    """
    Claude-compatible database query tool.
    
    This tool provides access to the MIMIC-IV-ED database for patient data queries.
    """
    
    def __init__(self):
        """Initialize the Claude database query tool."""
        # Initialize the database service
        self.db_service = DatabaseService()
        
        # Initialize the adapter with tool metadata
        super().__init__(
            tool_name="database_query_tool",
            tool_description="""Herramienta para consultar la base de datos MIMIC-IV-ED de urgencias hospitalarias.

TIPOS DE CONSULTA:
1. patient_summary: Resumen completo del paciente (requiere subject_id)
2. stay_details: Detalles de estancia en urgencias (requiere stay_id)
3. search_diagnoses: Buscar diagnósticos (requiere icd_code O icd_title)
4. get_vital_signs: Signos vitales de una estancia (requiere stay_id)
5. medication_history: Historial de medicación (requiere subject_id)
6. custom: Consulta SQL personalizada (requiere custom_query)

EJEMPLOS:
- Resumen de paciente: {"query_type": "patient_summary", "subject_id": 10014729}
- Signos vitales: {"query_type": "get_vital_signs", "stay_id": 37887480}
- Consulta custom: {"query_type": "custom", "custom_query": "SELECT * FROM edstays LIMIT 10"}

IMPORTANTE: Siempre proporciona los parámetros requeridos para cada tipo de consulta.""",
            args_schema=DatabaseQueryInput
        )
        
        logger.info("ClaudeDatabaseQueryTool initialized")
    
    def execute(self, query_type: str = "patient_summary", 
                subject_id: Optional[int] = None,
                stay_id: Optional[int] = None,
                icd_code: Optional[str] = None,
                icd_title: Optional[str] = None,
                custom_query: Optional[str] = None,
                params: Optional[Dict] = None) -> str:
        """
        Execute database query using the database service.
        
        Args:
            query_type: Type of query to execute
            subject_id: Patient identifier
            stay_id: Stay identifier
            icd_code: ICD code for diagnosis search
            icd_title: ICD title search term
            custom_query: Custom SQL query
            params: Query parameters
            
        Returns:
            Query results as formatted string
        """
        try:
            # Route to appropriate query method based on query_type
            if query_type == "patient_summary":
                if not subject_id:
                    return "Error: subject_id es requerido para patient_summary"
                result = self.db_service.get_patient_summary(subject_id)
                
            elif query_type == "stay_details":
                if not stay_id:
                    return "Error: stay_id es requerido para stay_details"
                result = self.db_service.get_stay_details(stay_id)
                
            elif query_type == "search_diagnoses":
                if not icd_code and not icd_title:
                    return "Error: icd_code o icd_title es requerido para search_diagnoses"
                result = self.db_service.search_diagnoses(icd_code=icd_code, icd_title=icd_title)
                
            elif query_type == "get_vital_signs":
                if not stay_id:
                    return "Error: stay_id es requerido para get_vital_signs"
                result = self.db_service.get_vital_signs(stay_id)
                
            elif query_type == "medication_history":
                if not subject_id:
                    return "Error: subject_id es requerido para medication_history"
                result = self.db_service.get_medication_history(subject_id)
                
            elif query_type == "custom":
                if not custom_query:
                    return "Error: custom_query es requerido para consultas personalizadas"
                result = self.db_service.execute_custom_query(custom_query, params or {})
                
            else:
                return f"Error: Tipo de consulta no reconocido: {query_type}"
            
            # Format the result
            return self._format_result(result)
            
        except Exception as e:
            error_msg = f"Error ejecutando consulta de base de datos: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _format_result(self, result: Any) -> str:
        """
        Format query result for display.
        
        Args:
            result: Query result (dict, list, DataFrame, etc.)
            
        Returns:
            Formatted string representation
        """
        if isinstance(result, dict):
            # Format dictionary results
            lines = []
            for key, value in result.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"{key}:")
                    lines.append(f"  {value}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
            
        elif isinstance(result, list):
            # Format list results
            if not result:
                return "No se encontraron resultados"
            return "\n".join([str(item) for item in result])
            
        else:
            # Default string conversion
            return str(result)
    
    def format_output(self, output_data: Any) -> str:
        """
        Format output for Claude.
        
        Args:
            output_data: Output from tool execution
            
        Returns:
            Formatted output string
        """
        return str(output_data)


# Convenience function to create the tool
def create_claude_database_tool() -> ClaudeDatabaseQueryTool:
    """
    Create a Claude-compatible database query tool.
    
    Returns:
        ClaudeDatabaseQueryTool instance
    """
    return ClaudeDatabaseQueryTool()
