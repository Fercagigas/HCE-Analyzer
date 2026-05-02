# Tests de ChatHCE

## Estructura

```
tests/
├── test_system.py         # Tests generales del sistema (imports, inicialización)
├── test_rag_components.py # Tests de componentes RAG (chunker, searcher, reranker)
├── test_database.py       # Tests de base de datos
└── conftest.py            # Fixtures compartidos
```

## Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Test específico
python -m pytest tests/test_system.py -v

# Con cobertura
python -m pytest tests/ -v --cov=services
```
