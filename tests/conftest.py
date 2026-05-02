"""
Pytest configuration and fixtures for ChatHCE tests
"""

import pytest
import warnings
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Suppress Pydantic deprecation warnings (external library)
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
    warnings.filterwarnings("ignore", message="Using extra keyword arguments on `Field` is deprecated")
    warnings.filterwarnings("ignore", message=".*PydanticDeprecatedSince20.*")
    
    # Suppress Supabase/Postgrest deprecation warnings (external library)
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="supabase")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="postgrest")
    warnings.filterwarnings("ignore", message=".*'timeout' parameter is deprecated.*")
    warnings.filterwarnings("ignore", message=".*'verify' parameter is deprecated.*")
    
    # Suppress pandas FutureWarnings (for compatibility)
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
    
    # Suppress pytest internal warnings
    warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)
    
    # Configure environment for testing
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("LOG_LEVEL", "ERROR")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    # Markers are now registered in pytest.ini, so we don't need to add them dynamically
    pass

@pytest.fixture(scope="session", autouse=True)
def suppress_warnings():
    """Suppress warnings for the entire test session."""
    with warnings.catch_warnings():
        # Suppress all deprecation warnings from external libraries
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)
        yield

@pytest.fixture
def mock_env_vars():
    """Provide mock environment variables for testing."""
    return {
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_supabase_key",
        "SECRET_KEY": "test_secret_key",
        "DEBUG": "false",
        "LOG_LEVEL": "ERROR"
    }

@pytest.fixture
def clean_environment(mock_env_vars):
    """Provide a clean environment for testing."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    for key, value in mock_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
