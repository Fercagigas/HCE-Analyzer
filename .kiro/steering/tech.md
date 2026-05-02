# HCE Analyzer Pro - Technical Stack

## Core Technologies

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs with Python 3.8+
- **Streamlit**: Primary web interface framework for rapid UI development
- **Python 3.8+**: Core programming language

### AI & Machine Learning
- **LangChain**: Framework for developing applications with language models
- **Claude API (Anthropic)**: Primary LLM provider with multiple model fallbacks:
  - Primary: `claude-haiku-4-5-20251001`
  - Secondary: `claude-sonnet-4-5-20250929` 
  - Tertiary: `claude-opus-4-20250514`
- **HuggingFace Transformers**: For embeddings (`sentence-transformers/all-MiniLM-L6-v2`)

### Database & Storage
- **Supabase**: Primary database and authentication service (PostgreSQL-based)
- **Supabase pgvector**: Vector store for document embeddings and similarity search (RAG)
- **Local File Storage**: For uploaded documents and temporary files

**NOTA:** El sistema accede a Supabase mediante:
- `Database Tool` (`services/unified_chat/tools/database_tool.py`) - Herramienta del agente
- `DatabaseService` (`services/medical_agent/services/database_service.py`) - Servicio de datos
- Cliente Python de Supabase (`supabase-py`)

El MCP de Supabase en `~/.kiro/settings/mcp.json` es **solo para desarrollo** (consultas del agente Kiro durante implementación), NO se usa en producción.

### Document Processing
- **Docling**: Advanced PDF processing and text extraction
- **PyPDF2**: PDF text extraction
- **python-docx**: Word document processing

### Configuration & Validation
- **Pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management

## Development Tools

### Testing
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async testing support

### Code Quality
- **black**: Code formatting
- **flake8**: Linting

### Monitoring & Logging
- **structlog**: Structured logging
- **Python logging**: Standard logging framework

## Common Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run Streamlit app (main interface)
streamlit run main.py

# Run FastAPI server (API only)
python api/main.py
# or
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Run test API
python test_api.py
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. tests/

# Run specific test file
pytest test_api.py
```

### Development
```bash
# Format code
black .

# Lint code
flake8 .

# Check configuration
python -c "from config.settings import settings; print('Config loaded successfully')"
```

## Configuration

### Environment Variables
- Required: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
- Optional: `DEBUG`, `LOG_LEVEL`
- See `.env.example` for complete list

### Key Configuration Files
- `config/settings.py`: Pydantic-based configuration management
- `config/config.py`: Legacy configuration (being phased out)
- `config/constants.py`: Application constants
- `.env`: Environment variables (not in repo)

## Architecture Patterns

### Service Layer Pattern
- Services in `services/` directory handle business logic
- Clear separation between UI, API, and business logic

### Agent Pattern
- AI agents in `src/analyzers/` for different analysis types
- Modular approach to different AI capabilities

### Repository Pattern
- Data access abstracted through service classes
- Database operations centralized in service layer