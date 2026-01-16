"""Sidebar component for system configuration."""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """Get a secret from st.secrets (Streamlit Cloud) or os.environ (.env file)."""
    # First try st.secrets (for Streamlit Cloud deployment)
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)


def render_sidebar() -> dict:
    """
    Render the sidebar with API configuration options.
    
    Returns:
        dict with configuration values
    """
    with st.sidebar:
        st.header("System Config")
        
        st.subheader("API Keys")
        
        # Get default values from st.secrets, .env file, or session state
        default_deepseek = get_secret("DEEPSEEK_API_KEY") or st.session_state.get("deepseek_api_key", "")
        default_tavily = get_secret("TAVILY_API_KEY") or st.session_state.get("tavily_api_key", "")
        
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            value=default_deepseek,
            key="deepseek_key_input",
            help="Required for lead scoring and outreach drafting (auto-loaded from .env if present)"
        )
        
        tavily_key = st.text_input(
            "Tavily API Key",
            type="password",
            value=default_tavily,
            key="tavily_key_input",
            help="Required for company discovery search (auto-loaded from .env if present)"
        )
        
        # Store keys in session state
        if deepseek_key:
            st.session_state["deepseek_api_key"] = deepseek_key
        if tavily_key:
            st.session_state["tavily_api_key"] = tavily_key
        
        st.divider()
        
        st.subheader("Model Selection")
        
        reasoning_model = st.selectbox(
            "Reasoning Model (Scoring)",
            options=["deepseek-reasoner", "deepseek-chat"],
            index=0,
            key="reasoning_model_select",
            help="DeepSeek R1 recommended for ICP scoring"
        )
        
        drafting_model = st.selectbox(
            "Drafting Model (Outreach)",
            options=["deepseek-chat", "deepseek-reasoner"],
            index=0,
            key="drafting_model_select",
            help="DeepSeek V3 recommended for email drafting"
        )
        
        st.session_state["reasoning_model"] = reasoning_model
        st.session_state["drafting_model"] = drafting_model
        
        st.divider()
        
        # Mode toggle
        use_mock = st.toggle(
            "Use Mock Data",
            value=st.session_state.get("use_mock", True),
            key="use_mock_toggle",
            help="Enable for UI testing without API calls"
        )
        st.session_state["use_mock"] = use_mock
        
        if use_mock:
            st.info("Mock mode: Using sample data for testing")
        else:
            # Validate API keys
            if not deepseek_key or not tavily_key:
                st.warning("Enter both API keys to use live mode")
        
        st.divider()
        
        # Reset button
        if st.button("Clear Session State", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ["deepseek_api_key", "tavily_api_key"]:
                    del st.session_state[key]
            st.rerun()
        
        return {
            "deepseek_api_key": deepseek_key,
            "tavily_api_key": tavily_key,
            "reasoning_model": reasoning_model,
            "drafting_model": drafting_model,
            "use_mock": use_mock
        }
