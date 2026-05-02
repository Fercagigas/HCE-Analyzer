# HCE Analyzer Pro - Project Structure

## Root Level Organization

```
hce-analyzer-pro/
├── main.py                 # Main Streamlit application entry point
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation (Spanish)
├── .env.example          # Environment variables template
└── .env                  # Environment variables (not in repo)
```

## Core Application Structure

### `/config` - Configuration Management
```
config/
├── config.py            # Compatibility layer (re-exports from constants/settings)
├── constants.py         # Application constants
├── settings.py          # Pydantic-based settings management
├── logging_config.py    # Logging configuration
└── __init__.py
```

### `/services` - Business Logic Layer
```
services/
├── unified_chat/        # Unified chat system (main interface)
│   ├── unified_agent.py # Main chat agent with Claude
│   ├── tools/           # Database, RAG, and visualization tools
│   └── config.py        # Chat configuration
├── medical_agent/       # Medical agent and visualization
├── rag/                 # RAG service components
├── rag_service.py       # RAG functionality and vector operations
├── auth/               # Authentication services
├── alerts/             # Alert system services
├── backup/             # Backup and recovery services
├── notifications/      # Notification services
├── reporting/          # Report generation services
├── cache_manager.py    # Cache management
├── connection_pool_manager.py # Connection pooling
├── llm_optimizer.py    # LLM optimization
└── __init__.py
```

### `/src` - Core Application Logic
```
src/
├── core/              # Core application components
│   └── app.py         # Main Streamlit application
├── processors/        # Document and data processors
│   ├── document_processor.py
│   └── async_document_processor.py
├── analyzers/         # (Reserved for future analyzers)
└── __init__.py
```

### `/ui` - User Interface Components
```
ui/
├── unified_chat_interface.py  # Main chat interface
├── components/
│   ├── components/
│   │   ├── auth_pages.py      # Authentication pages
│   │   ├── sidebar.py         # Sidebar navigation
│   │   ├── document_manager.py # Document management
│   │   └── footer.py          # Footer component
│   └── message_handler.py     # Message handling
└── __init__.py
```

### `/utils` - Utility Functions
```
utils/
├── formatters/        # Data formatting utilities
├── helpers/          # General helper functions
├── validators/       # Input validation utilities
└── __init__.py
```

## Data and Storage

### `/data` - Data Storage
```
data/
├── storage/          # File storage and uploads
└── __init__.py
```

## Documentation and Scripts

### `/docs` - Documentation
```
docs/
├── UNIFIED_CHAT_ARCHITECTURE.md
├── CONFIGURACION_SUPABASE_VERIFICADA.md
└── ... (other documentation)
```

### `/scripts` - Utility Scripts
```
scripts/
├── clear_rag.py              # Clear RAG vector data in Supabase
├── validate_mimic.py         # Validate MIMIC data
└── __init__.py
```

## Naming Conventions

### Files and Directories
- **Snake case** for Python files: `unified_agent.py`, `rag_service.py`
- **Lowercase** for directories: `services/`, `config/`, `utils/`
- **Descriptive names** that indicate purpose: `document_processor.py`, `session_manager.py`

### Python Code
- **Classes**: PascalCase (`UnifiedChatAgent`, `RAGService`)
- **Functions/Methods**: snake_case (`process_query`, `get_session_stats`)
- **Constants**: UPPER_SNAKE_CASE (`ANTHROPIC_API_KEY`, `RAG_CONFIG`)
- **Private methods**: Leading underscore (`_initialize_components`)

## Module Organization Patterns

### Service Layer Pattern
- Each service is self-contained in its own file/directory
- Services handle specific business domains (auth, chat, RAG, etc.)
- Clear interfaces between services

### Configuration Centralization
- All configuration in `/config` directory
- Environment-based configuration with Pydantic validation
- Separate files for different config concerns

### Utility Organization
- Utilities grouped by function (formatters, helpers, validators)
- Reusable components that don't contain business logic
- Clear separation from business services

## Import Conventions

### Relative Imports
- Use relative imports within the same package
- Absolute imports for cross-package dependencies

### Import Order
1. Standard library imports
2. Third-party imports
3. Local application imports
4. Relative imports

### Example Import Structure
```python
# Standard library
import os
import logging
from typing import Dict, List, Optional

# Third-party
import streamlit as st
from anthropic import Anthropic
from pydantic import BaseSettings

# Local application
from config.settings import settings
from services.unified_chat.unified_agent import UnifiedChatAgent

# Relative
from .auth_service import AuthService
```

## File Organization Rules

### Single Responsibility
- Each file should have a single, clear purpose
- Large files should be split into logical components
- Related functionality grouped together

### Logical Grouping
- Similar services grouped in same directory
- UI components separated from business logic
- Configuration isolated from application code

### Scalability Considerations
- Structure supports adding new services easily
- Clear boundaries between different system layers
- Modular design allows for independent development
