
"""
ChatHCE - Main Application Entry Point
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging before importing other modules
from config.logging_config import setup_logging, get_logger, create_debug_session

# Initialize logging
setup_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    enable_file_logging=True,
    enable_console_logging=True,
    enable_structured_logging=True
)

logger = get_logger(__name__)

# Create debug session for this run
debug_session = create_debug_session("main_app")

import streamlit as st
import traceback
from src.core.app import main as streamlit_main

# Run the application directly (Streamlit executes this file as a script)
logger.info("🚀 Starting ChatHCE application...")

try:
    # Run Streamlit application
    streamlit_main()
except Exception as e:
    logger.critical(f"💥 Critical error in main application: {str(e)}")
    logger.critical(f"Full traceback: {traceback.format_exc()}")
    raise
