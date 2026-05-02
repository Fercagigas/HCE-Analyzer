# Guía de Creación de Herramientas - Chat Unificado

**Última actualización**: Febrero 2026

## Resumen

Esta guía explica cómo crear nuevas herramientas para el Sistema de Chat Unificado de ChatHCE. Las herramientas extienden las capacidades del agente proporcionando acceso a nuevas fuentes de datos, servicios o funcionalidades.

## Arquitectura de Herramientas

### Clase Base: ClaudeToolAdapter

Todas las herramientas heredan de `ClaudeToolAdapter` (`services/medical_agent/tools/claude_adapter.py`):

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

class ClaudeToolAdapter(ABC):
    """Base adapter para herramientas compatibles con Claude."""
    
    def __init__(self, tool_name: str, tool_description: str, args_schema: Type[BaseModel]):
        """
        Args:
            tool_name: Nombre único de la herramienta
            tool_description: Descripción para el agente
            args_schema: Pydantic BaseModel que define el esquema de entrada
        """
        self.tool_name = tool_name
        self.tool_description = tool_description
        self.args_schema = args_schema
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Ejecutar la herramienta. Debe ser implementado por subclases."""
        pass
    
    def get_langchain_tool(self):
        """Retorna StructuredTool compatible con LangChain bind_tools()."""
        from langchain_core.tools import StructuredTool
        return StructuredTool.from_function(
            func=self.execute,
            name=self.tool_name,
            description=self.tool_description,
            args_schema=self.args_schema,
            return_direct=False
        )
    
    def to_claude_schema(self) -> Dict[str, Any]:
        """Convierte a esquema compatible con Claude API."""
        schema = self.args_schema.model_json_schema()
        return {
            "name": self.tool_name,
            "description": self.tool_description,
            "input_schema": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", [])
            }
        }
    
    def format_input(self, input_data: Dict) -> Dict:
        """Valida input contra el schema Pydantic."""
        validated = self.args_schema(**input_data)
        return validated.model_dump()
    
    def format_output(self, output_data: Any) -> str:
        """Formatea output para consumo de Claude."""
        # Convierte dicts, listas y otros tipos a string legible
```

### Métodos Clave

| Método | Propósito |
|--------|-----------|
| `__init__(tool_name, tool_description, args_schema)` | Constructor con nombre, descripción y schema Pydantic |
| `execute(**kwargs)` | Método abstracto - lógica de la herramienta |
| `get_langchain_tool()` | Retorna `StructuredTool` para LangChain |
| `to_claude_schema()` | Genera esquema JSON para Claude API |
| `format_input(data)` | Valida entrada contra schema Pydantic |
| `format_output(data)` | Formatea salida como string legible |
| `__call__(**kwargs)` | Ejecuta flujo completo: format_input → execute → format_output |

### ClaudeToolRegistry

Registro centralizado para gestionar herramientas:

```python
class ClaudeToolRegistry:
    def register(self, tool: ClaudeToolAdapter): ...
    def get_tool(self, tool_name: str) -> ClaudeToolAdapter: ...
    def get_all_tools(self) -> List[ClaudeToolAdapter]: ...
    def get_langchain_tools(self) -> List: ...  # Para bind_tools()
    def get_claude_schemas(self) -> List[Dict]: ...
```

## Crear una Nueva Herramienta

### Paso 1: Definir el Schema de Entrada (Pydantic)

```python
# services/unified_chat/tools/my_new_tool.py
from pydantic import BaseModel, Field
from typing import Optional

class MyNewToolInput(BaseModel):
    """Schema de entrada para MyNewTool."""
    query: str = Field(..., description="Consulta principal")
    category: Optional[str] = Field(None, description="Categoría opcional de filtro")
    limit: Optional[int] = Field(10, description="Número máximo de resultados")
```

### Paso 2: Implementar la Herramienta

```python
import logging
from typing import Dict, Any, Optional
from services.medical_agent.tools.claude_adapter import ClaudeToolAdapter

logger = logging.getLogger(__name__)

class MyNewTool(ClaudeToolAdapter):
    """Herramienta para [descripción del propósito]."""
    
    def __init__(self):
        super().__init__(
            tool_name="my_new_tool",
            tool_description="""
            Descripción detallada para el agente.
            
            Usa esta herramienta cuando el usuario pregunte sobre:
            - Caso de uso 1
            - Caso de uso 2
            - Caso de uso 3
            
            NO uses esta herramienta para:
            - Lo que NO debe usarse
            
            Parámetros:
            - query (str, requerido): Consulta principal
            - category (str, opcional): Filtro por categoría
            - limit (int, opcional): Máximo de resultados (default: 10)
            """,
            args_schema=MyNewToolInput
        )
        # Inicializar servicios necesarios
        self.service = MyService()
    
    def execute(
        self,
        query: str,
        category: Optional[str] = None,
        limit: Optional[int] = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ejecutar la herramienta.
        
        Args:
            query: Consulta principal
            category: Filtro opcional
            limit: Máximo de resultados
            
        Returns:
            Dict con resultados
        """
        try:
            # 1. Validar parámetros
            if not query or not query.strip():
                return {"success": False, "error": "La consulta no puede estar vacía"}
            
            # 2. Ejecutar lógica
            results = self.service.search(query, category=category, limit=limit)
            
            # 3. Retornar resultados estructurados
            return {
                "success": True,
                "total_results": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error en MyNewTool: {e}")
            return {"success": False, "error": str(e)}
```

### Paso 3: Crear Factory Function

```python
def create_my_new_tool() -> MyNewTool:
    """Factory function para crear instancia de MyNewTool."""
    return MyNewTool()
```

### Paso 4: Registrar en el Agente

En `services/unified_chat/unified_agent.py`, añadir la herramienta en `_initialize_tools()`:

```python
from services.unified_chat.tools.my_new_tool import create_my_new_tool

class UnifiedChatAgent:
    def _initialize_tools(self) -> List:
        tools = []
        
        # Herramientas existentes
        db_tool = create_database_tool()
        tools.append(db_tool.get_langchain_tool())
        
        rag_tool = create_rag_tool()
        tools.append(rag_tool.get_langchain_tool())
        
        # Nueva herramienta
        my_tool = create_my_new_tool()
        tools.append(my_tool.get_langchain_tool())
        
        return tools
```

### Paso 5: Actualizar System Prompt

Añadir la descripción de la herramienta en `_create_system_prompt()`:

```python
# En el system prompt del agente
"""
HERRAMIENTAS DISPONIBLES:

1. query_mimic_database - Consultas a MIMIC-IV-ED
2. search_clinical_documents - Búsqueda RAG en documentos
3. request_visualization - Generación de visualizaciones
4. my_new_tool - [Descripción y cuándo usarla]

GUÍAS DE SELECCIÓN:
- Usa my_new_tool cuando [condiciones específicas]
"""
```

## Herramientas Existentes como Referencia

### DatabaseTool

```python
# services/unified_chat/tools/database_tool.py

class DatabaseToolInput(BaseModel):
    query_type: str = Field(..., description="Tipo de consulta")
    subject_id: Optional[int] = Field(None, description="ID del paciente")
    stay_id: Optional[int] = Field(None, description="ID de estancia")
    # ... más campos

class DatabaseTool(ClaudeToolAdapter):
    def __init__(self):
        super().__init__(
            tool_name="query_mimic_database",
            tool_description="...",
            args_schema=DatabaseToolInput
        )
    
    def execute(self, query_type, subject_id=None, ...):
        # Despacha según query_type:
        # patient_summary, vital_signs, diagnoses, medications, custom

def create_database_tool() -> DatabaseTool:
    return DatabaseTool()
```

### RAGTool

```python
# services/unified_chat/tools/rag_tool.py

class RAGQueryInput(BaseModel):
    query: str = Field(..., description="Consulta de búsqueda")
    specialty: Optional[str] = Field(None, description="Especialidad")
    top_k: Optional[int] = Field(None, description="Número de resultados")

class RAGTool(ClaudeToolAdapter):
    def __init__(self):
        super().__init__(
            tool_name="search_clinical_documents",
            tool_description="...",
            args_schema=RAGQueryInput
        )
        self.rag_service = ImprovedRAGService()
        self.query_augmenter = QueryAugmenter()
    
    def execute(self, query, specialty=None, top_k=None):
        # 1. Augmentar consulta con Claude Haiku
        # 2. Buscar con cada consulta augmentada
        # 3. Deduplicar y retornar top_k

def create_rag_tool() -> RAGTool:
    return RAGTool()
```

## Mejores Prácticas

### 1. Descripción Clara para el Agente

La descripción es crucial para que Claude seleccione la herramienta correcta:

```python
tool_description="""
[Resumen en una línea]

Usa esta herramienta cuando el usuario pregunte sobre:
- [Caso de uso específico con ejemplo]
- [Caso de uso específico con ejemplo]

NO uses esta herramienta para:
- [Lo que NO debe usarse]

Parámetros:
- param1 (tipo, requerido): [Descripción con ejemplo]
- param2 (tipo, opcional): [Descripción con default]

Retorna:
- [Descripción del formato de respuesta]
"""
```

### 2. Validación de Parámetros con Pydantic

Usar Pydantic BaseModel para validación automática:

```python
from pydantic import BaseModel, Field, validator

class MyToolInput(BaseModel):
    patient_id: int = Field(..., gt=0, description="ID positivo del paciente")
    query_type: str = Field(..., description="Tipo de consulta")
    
    @validator('query_type')
    def validate_query_type(cls, v):
        valid_types = ['summary', 'vitals', 'diagnoses']
        if v not in valid_types:
            raise ValueError(f"Tipo inválido. Válidos: {valid_types}")
        return v
```

### 3. Manejo de Errores

```python
def execute(self, **kwargs) -> Dict[str, Any]:
    try:
        result = self._do_work(**kwargs)
        return {"success": True, "data": result}
        
    except ConnectionError as e:
        logger.error(f"Error de conexión en {self.tool_name}: {e}")
        return {
            "success": False,
            "error": "No se pudo conectar al servicio",
            "suggestion": "Intente nuevamente en unos momentos"
        }
    except ValueError as e:
        logger.warning(f"Parámetros inválidos en {self.tool_name}: {e}")
        return {"success": False, "error": f"Parámetros inválidos: {e}"}
    except Exception as e:
        logger.error(f"Error inesperado en {self.tool_name}: {e}")
        return {"success": False, "error": f"Error inesperado: {e}"}
```

### 4. Formateo de Resultados

Sobreescribir `format_output()` para resultados legibles:

```python
def format_output(self, output_data: Any) -> str:
    if isinstance(output_data, dict):
        if not output_data.get('success'):
            return f"Error: {output_data.get('error', 'Desconocido')}"
        
        lines = [f"## Resultados ({output_data.get('total', 0)} encontrados)\n"]
        for item in output_data.get('data', []):
            lines.append(f"- **{item['name']}**: {item['value']}")
        return "\n".join(lines)
    
    return str(output_data)
```

### 5. Logging Estructurado

```python
def execute(self, **kwargs) -> Dict[str, Any]:
    logger.info(f"Ejecutando {self.tool_name}", extra={
        "tool": self.tool_name,
        "params": {k: v for k, v in kwargs.items() if k != 'api_key'}
    })
    
    result = self._do_work(**kwargs)
    
    logger.info(f"{self.tool_name} completado", extra={
        "tool": self.tool_name,
        "success": result.get('success'),
        "result_count": len(result.get('data', []))
    })
    return result
```

### 6. Caché para Operaciones Costosas

```python
from services.cache_manager import cache_manager

def execute(self, query: str, **kwargs) -> Dict[str, Any]:
    cache_key = f"{self.tool_name}:{hash(query)}"
    cached = cache_manager.get(cache_key)
    if cached:
        logger.info(f"Cache hit para {cache_key}")
        return cached
    
    result = self._do_work(query, **kwargs)
    cache_manager.set(cache_key, result, ttl=300)
    return result
```

## Testing

```python
import pytest
from services.unified_chat.tools.my_new_tool import MyNewTool, create_my_new_tool

class TestMyNewTool:
    @pytest.fixture
    def tool(self):
        return create_my_new_tool()
    
    def test_initialization(self, tool):
        assert tool.tool_name == "my_new_tool"
        assert tool.args_schema is not None
    
    def test_execute_success(self, tool):
        result = tool.execute(query="test query")
        assert result["success"] is True
    
    def test_execute_empty_query(self, tool):
        result = tool.execute(query="")
        assert result["success"] is False
    
    def test_langchain_tool(self, tool):
        lc_tool = tool.get_langchain_tool()
        assert lc_tool.name == "my_new_tool"
    
    def test_claude_schema(self, tool):
        schema = tool.to_claude_schema()
        assert schema["name"] == "my_new_tool"
        assert "input_schema" in schema
```

## Checklist de Creación

- [ ] Schema Pydantic definido con `BaseModel`
- [ ] Constructor llama a `super().__init__(tool_name, tool_description, args_schema)`
- [ ] Método `execute()` implementado (no `_execute()`)
- [ ] Factory function creada (`create_my_tool()`)
- [ ] Herramienta registrada en `_initialize_tools()` via `get_langchain_tool()`
- [ ] System prompt actualizado con descripción de la herramienta
- [ ] Validación de parámetros implementada
- [ ] Manejo de errores completo
- [ ] Logging implementado
- [ ] Tests unitarios escritos
- [ ] Documentación actualizada

---

**Versión**: 2.0
**Sistema**: ChatHCE - Chat Unificado
