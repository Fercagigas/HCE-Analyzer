# Estándares de Código - ChatHCE

## Lenguaje y Versión

- **Python 3.8+** como lenguaje principal
- Usar type hints en todas las funciones
- Compatibilidad con Python 3.8, 3.9, 3.10, 3.11, 3.12

## Estilo de Código

### PEP 8
- Seguir PEP 8 estrictamente
- Líneas máximo 100 caracteres (no 79)
- 4 espacios para indentación (no tabs)
- 2 líneas en blanco entre clases y funciones top-level
- 1 línea en blanco entre métodos de clase

### Nombres
```python
# Clases: PascalCase
class UnifiedChatAgent:
    pass

# Funciones y métodos: snake_case
def process_message(query: str) -> Dict[str, Any]:
    pass

# Constantes: UPPER_SNAKE_CASE
MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.1

# Variables: snake_case
user_query = "¿Cuál es el diagnóstico?"
patient_data = fetch_patient_data()

# Privados: prefijo con _
def _internal_helper():
    pass
```

### Imports
```python
# Orden de imports:
# 1. Standard library
import os
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# 2. Third-party
import pandas as pd
import streamlit as st
from langchain_classic.agents import AgentExecutor
from anthropic import Anthropic

# 3. Local
from config.settings import settings
from services.unified_chat.unified_agent import UnifiedChatAgent
from utils.helpers import format_response
```

## Documentación

### Docstrings
Usar formato Google Style:

```python
def query_mimic_database(
    subject_id: int,
    query_type: str = "patient_summary",
    include_vitals: bool = True
) -> Dict[str, Any]:
    """
    Consulta la base de datos MIMIC-IV-ED para obtener datos de pacientes.
    
    Args:
        subject_id: ID del paciente en MIMIC-IV-ED
        query_type: Tipo de consulta ('patient_summary', 'vital_signs', etc.)
        include_vitals: Si incluir signos vitales en el resultado
        
    Returns:
        Dict con los datos del paciente y metadata de la consulta
        
    Raises:
        DatabaseConnectionError: Si no se puede conectar a Supabase
        InvalidPatientError: Si el subject_id no existe
        
    Example:
        >>> data = query_mimic_database(10014729, "patient_summary")
        >>> print(data['patient_info']['age'])
        45
    """
    pass
```

### Comentarios
```python
# Comentarios en español para lógica compleja
# Explicar el "por qué", no el "qué"

# ✅ BIEN
# Usamos Claude para el agente porque maneja mejor tool calling
llm = ChatAnthropic(model="claude-haiku-4-5-20251001")

# ❌ MAL
# Crear instancia de LLM
llm = ChatAnthropic(model="claude-haiku-4-5-20251001")
```

## Type Hints

### Siempre usar type hints
```python
from typing import Dict, List, Optional, Any, Union, Tuple

# Funciones
def process_query(query: str, context: List[Dict]) -> Dict[str, Any]:
    pass

# Métodos de clase
class ChatAgent:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
    
    def chat(self, message: str) -> str:
        return "response"

# Variables complejas
patient_data: Dict[str, Union[str, int, float]] = {}
results: List[Tuple[str, int]] = []

# Optional para valores que pueden ser None
def get_patient(id: int) -> Optional[Dict[str, Any]]:
    pass
```

## Manejo de Errores

### Excepciones Específicas
```python
# Definir excepciones personalizadas
class HCEAnalyzerError(Exception):
    """Base exception para HCE Analyzer"""
    pass

class DatabaseConnectionError(HCEAnalyzerError):
    """Error de conexión a base de datos"""
    pass

class InvalidQueryError(HCEAnalyzerError):
    """Consulta SQL inválida o insegura"""
    pass

# Usar try-except específicos
try:
    result = execute_query(sql)
except DatabaseConnectionError as e:
    logger.error(f"Error de conexión: {e}")
    return {"error": "No se pudo conectar a la base de datos"}
except InvalidQueryError as e:
    logger.warning(f"Consulta inválida: {e}")
    return {"error": "La consulta no es válida"}
```

### Logging
```python
import logging

# Usar logging en lugar de print
logger = logging.getLogger(__name__)

# Niveles apropiados
logger.debug("Detalles de debugging")
logger.info("Información general")
logger.warning("Advertencia, pero continúa")
logger.error("Error que afecta funcionalidad")
logger.critical("Error crítico del sistema")

# Incluir contexto
logger.info(
    "Consulta procesada",
    extra={
        "user_id": user_id,
        "query_type": query_type,
        "execution_time_ms": 1234
    }
)
```

## Configuración

### Usar Pydantic Settings
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class ServiceSettings(BaseSettings):
    """Configuración del servicio"""
    api_key: str = Field(..., env="API_KEY")
    max_retries: int = Field(3, env="MAX_RETRIES")
    timeout: float = Field(30.0, env="TIMEOUT")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }

# Usar settings globales
from config.settings import settings

api_key = settings.claude_agent.anthropic_api_key
```

### Variables de Entorno
```python
# Nunca hardcodear secrets
# ❌ MAL
api_key = "sk-ant-api03-..."

# ✅ BIEN
from config.settings import settings
api_key = settings.claude_agent.anthropic_api_key
```

## Estructura de Clases

### Dataclasses para Modelos
```python
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class PatientData:
    """Datos de un paciente de MIMIC-IV-ED"""
    subject_id: int
    stay_id: int
    age: int
    gender: str
    admission_time: datetime
    diagnoses: List[str] = field(default_factory=list)
    vital_signs: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """Validación después de inicialización"""
        if self.age < 0 or self.age > 120:
            raise ValueError(f"Edad inválida: {self.age}")
```

### Servicios como Clases
```python
class DatabaseService:
    """Servicio para interactuar con Supabase"""
    
    def __init__(self):
        """Inicializar conexión"""
        self.client = self._create_client()
        self.logger = logging.getLogger(__name__)
    
    def _create_client(self):
        """Método privado para crear cliente"""
        pass
    
    def query(self, sql: str) -> List[Dict]:
        """Método público para consultas"""
        pass
```

## Testing

### Estructura de Tests
```python
import pytest
from unittest.mock import Mock, patch

class TestUnifiedChatAgent:
    """Tests para UnifiedChatAgent"""
    
    @pytest.fixture
    def agent(self):
        """Fixture para crear agente"""
        return UnifiedChatAgent()
    
    def test_process_message_success(self, agent):
        """Test de procesamiento exitoso"""
        result = agent.process_message("test query", [])
        assert result["success"] is True
        assert "content" in result
    
    def test_process_message_with_database_tool(self, agent):
        """Test usando database tool"""
        with patch('services.unified_chat.tools.database_tool.DatabaseTool') as mock:
            mock.return_value.execute.return_value = {"data": "test"}
            result = agent.process_message("paciente 123", [])
            assert "tools_used" in result
```

### Nombres de Tests
- Prefijo `test_`
- Descriptivos: `test_<método>_<escenario>_<resultado_esperado>`
- Ejemplos:
  - `test_query_database_with_valid_id_returns_data`
  - `test_rag_search_with_empty_query_raises_error`
  - `test_agent_with_multiple_tools_integrates_results`

## Performance

### Optimizaciones
```python
# Usar list comprehensions
# ✅ BIEN
results = [process(item) for item in items if item.is_valid]

# ❌ MAL
results = []
for item in items:
    if item.is_valid:
        results.append(process(item))

# Usar generators para grandes datasets
def process_large_dataset(data):
    for item in data:
        yield process(item)

# Cache para operaciones costosas
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(param: str) -> str:
    # Operación costosa
    return result
```

## Seguridad

### Validación de Inputs
```python
def validate_sql_query(query: str) -> bool:
    """Validar que la consulta SQL sea segura"""
    # Prevenir SQL injection
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    query_upper = query.upper()
    
    for keyword in forbidden:
        if keyword in query_upper:
            raise InvalidQueryError(f"Keyword prohibido: {keyword}")
    
    return True

def sanitize_user_input(text: str) -> str:
    """Sanitizar input del usuario"""
    # Remover caracteres peligrosos
    return text.strip().replace(";", "").replace("--", "")
```

## Convenciones Específicas del Proyecto

### Respuestas en Español
```python
# Todas las respuestas al usuario en español
def format_error_message(error: Exception) -> str:
    """Formatear mensaje de error para el usuario"""
    return f"❌ **Error**: {str(error)}\n\nPor favor, intente nuevamente."
```

### Estructura de Respuestas
```python
# Formato estándar para respuestas del agente
@dataclass
class AgentResponse:
    success: bool
    content: str
    tools_used: List[str]
    visualizations: List[Dict]
    sources: List[Dict]
    metadata: Dict[str, Any]
    error: Optional[str] = None
```

### Logging Estructurado
```python
# Usar logging estructurado para métricas
logger.info(
    "unified_chat.query_completed",
    extra={
        "user_id": user_id,
        "session_id": session_id,
        "tools_used": ["database", "rag"],
        "execution_time_ms": 1234,
        "success": True
    }
)
```

## Herramientas de Desarrollo

### Formateo
```bash
# Black para formateo automático
black .

# isort para ordenar imports
isort .
```

### Linting
```bash
# flake8 para linting
flake8 . --max-line-length=100

# mypy para type checking
mypy . --ignore-missing-imports
```

### Pre-commit
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

## Referencias

- PEP 8: https://pep8.org/
- Type Hints: https://docs.python.org/3/library/typing.html
- Google Style Docstrings: https://google.github.io/styleguide/pyguide.html
- Pydantic: https://docs.pydantic.dev/
