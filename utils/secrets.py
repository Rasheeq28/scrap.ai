"""
Secrets Management Helper
Reads secrets from Streamlit secrets, environment variables, or .env file
Priority: st.secrets > os.environ > .env file
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file first
load_dotenv()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a secret from multiple sources in order of priority:
    1. Streamlit secrets (st.secrets) - for Streamlit Cloud
    2. Environment variables (os.environ) - for local/CLI
    3. Default value
    
    Args:
        key: Secret key name
        default: Default value if not found
    
    Returns:
        Secret value or default
    """
    # Try Streamlit secrets first (only if streamlit is available and running)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except (ImportError, RuntimeError):
        # Streamlit not available or not in streamlit context
        pass
    
    # Fall back to environment variables
    return os.getenv(key, default)
