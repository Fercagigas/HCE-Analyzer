# HCE Analyzer Pro - Project Structure

## Root Level Organization

```
hce-analyzer-pro/
├── main.py                 # Main Streamlit application entry point
├── test_api.py            # Simple API test endpoint
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation (Spanish)
├── .env.example          # Environment variables template
└── .env                  # Environment variables (not in repo)
```

## Core Application Structure

### `/api` - FastAPI Backend
```
api/
├── main.py               # FastAPI application entry point
├── middleware/           # Custom middleware (rate limiting, auth)
├── routes/              # API route handlers
└── __init__.py
```

### `/config` - Configuration Management
```
config/
├── config.py            # Legacy configuration (being phased out)
├── constants.py         # Application constants
├── settings.py          # Pydantic-based settings management
└── __init__.py
```

### `/services` - Business Logic Layer
```
services/
├── clinical_chat.py     # Clinical chat interface and logic
├── rag_service.py       # RAG functionality and vector operations
├── alerts/              # Alert system services
├── auth/               # Authentication services
├── backup/             # Backup and recovery services
├── notifications/      # Notification services
├── reporting/          # Report generation services
└── __init__.py
```

### `/src` - Core Application Logic
```
src/
├── analyzers/          # AI agents and analysis logic
├── core/              # Core application components
├── processors/        # Document and data processors
└── __init__.py
```

### `/models` - Data Models
```
models/
├── schemas/           # Pydantic schemas and data models
└── __init__.py
```

### `/ui` - User Interface Components
```
ui/
├── components/        # Reusable UI components
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
└── README.md         # Additional documentation
```

### `/scripts` - Utility Scripts
```
scripts/
├── start_services.py # Service startup scripts
└── __init__.py
```

## Naming Conventions

### Files and Directories
- **Snake case** for Python files: `clinical_chat.py`, `rag_service.py`
- **Lowercase** for directories: `services/`, `config/`, `utils/`
- **Descriptive names** that indicate purpose: `document_processor.py`, `session_manager.py`

### Python Code
- **Classes**: PascalCase (`ClinicalChatInterface`, `RAGService`)
- **Functions/Methods**: snake_case (`process_query`, `get_session_stats`)
- **Constants**: UPPER_SNAKE_CASE (`GROQ_API_KEY`, `RAG_CONFIG`)
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
from langchain_groq import ChatGroq
from pydantic import BaseSettings

# Local application
from config.settings import settings
from services.rag_service import RAGService

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