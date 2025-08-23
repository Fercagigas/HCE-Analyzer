
"""
HCE Analyzer Pro - Main Application Entry Point
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import streamlit as st
from src.core.app import main as streamlit_main

if __name__ == "__main__":
    # Run Streamlit application
    streamlit_main()
