"""PharmHunter - Automated biopharma lead discovery and qualification."""

import sys
import streamlit as st
from typing import List
from functools import partial

# Force immediate stdout flushing for print statements
print = partial(print, flush=True)

from src.models.leads import Lead, ScoredLead, DraftedLead
from src.agents import (
    MockScoutAgent,
    MockAnalystAgent,
    MockScribeAgent,
    ScoutAgent,
    AnalystAgent,
    ScribeAgent,
)
from src.ui.sidebar import render_sidebar
from src.ui.mission_control import render_mission_control
from src.ui.war_room import render_war_room


# Page configuration
st.set_page_config(
    page_title="PharmHunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .main .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    defaults = {
        "is_processing": False,
        "processing_status": "",
        "raw_leads": [],
        "scored_leads": [],
        "drafted_leads": [],
        "use_mock": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def update_progress(message: str):
    """Update processing status in session state."""
    st.session_state["processing_status"] = message


def validate_api_keys() -> tuple[bool, str]:
    """Validate that required API keys are present."""
    deepseek_key = st.session_state.get("deepseek_api_key", "")
    tavily_key = st.session_state.get("tavily_api_key", "")
    
    if not deepseek_key:
        return False, "DeepSeek API key is required. Please enter it in the sidebar."
    if not tavily_key:
        return False, "Tavily API key is required. Please enter it in the sidebar."
    
    return True, ""


def run_hunt_pipeline(params: dict):
    """Execute the full hunt pipeline: Scout -> Analyst -> Scribe."""
    st.session_state["is_processing"] = True
    st.session_state["processing_status"] = "Initializing hunt..."
    
    use_mock = st.session_state.get("use_mock", True)
    
    print(f"\n{'='*60}")
    print(f"STARTING HUNT PIPELINE - Mode: {'MOCK' if use_mock else 'LIVE'}")
    print(f"{'='*60}")
    
    # Validate API keys if not using mock
    if not use_mock:
        is_valid, error_msg = validate_api_keys()
        if not is_valid:
            print(f"ERROR: {error_msg}")
            st.error(error_msg)
            st.session_state["is_processing"] = False
            return
        print("API keys validated successfully")
    
    try:
        # Initialize services
        deepseek = None
        tavily = None
        
        if not use_mock:
            from src.services import TavilyService, DeepSeekService
            
            print("Initializing Tavily service...")
            tavily = TavilyService(st.session_state.get("tavily_api_key", ""))
            print("Tavily service initialized")
            
            print("Initializing DeepSeek service...")
            deepseek = DeepSeekService(
                api_key=st.session_state.get("deepseek_api_key", ""),
                reasoning_model=st.session_state.get("reasoning_model", "deepseek-reasoner"),
                drafting_model=st.session_state.get("drafting_model", "deepseek-chat")
            )
            print(f"DeepSeek service initialized - R1: {deepseek.reasoning_model}, V3: {deepseek.drafting_model}")
        
        # Phase 1: Scout - Discover leads
        print("\n[PHASE 1] Starting Scout Agent...")
        update_progress("Phase 1: Discovering companies...")
        
        if use_mock:
            print("Using MockScoutAgent")
            scout = MockScoutAgent(on_progress=update_progress)
        else:
            print("Using Production ScoutAgent with Tavily + DeepSeek")
            scout = ScoutAgent(tavily, deepseek, on_progress=update_progress)
        
        print(f"Executing Scout with params: count={params['lead_count']}, focus={params['therapeutic_focus']}")
        raw_leads = scout.execute(
            count=params["lead_count"],
            focus=params["therapeutic_focus"],
            phase=", ".join(params["phase_preference"]),
            geography=params["geography"],
            exclusions=params["exclusions"]
        )
        print(f"Scout completed: {len(raw_leads)} leads found")
        st.session_state["raw_leads"] = raw_leads
        
        if not raw_leads:
            print("WARNING: No leads found")
            update_progress("No leads found. Try adjusting your search criteria.")
            st.session_state["is_processing"] = False
            st.rerun()
            return
        
        # Phase 2: Analyst - Score leads
        print(f"\n[PHASE 2] Starting Analyst Agent for {len(raw_leads)} leads...")
        update_progress(f"Phase 2: Scoring {len(raw_leads)} leads...")
        
        if use_mock:
            print("Using MockAnalystAgent")
            analyst = MockAnalystAgent(on_progress=update_progress)
        else:
            print("Using Production AnalystAgent with DeepSeek R1")
            analyst = AnalystAgent(deepseek, on_progress=update_progress)
        
        print("Executing Analyst...")
        scored_leads = analyst.execute(
            leads=raw_leads,
            icp_definition=params["icp_definition"]
        )
        print(f"Analyst completed: {len(scored_leads)} leads scored")
        st.session_state["scored_leads"] = scored_leads
        
        qualified_count = sum(1 for l in scored_leads if l.is_qualified)
        print(f"Qualification results: {qualified_count}/{len(scored_leads)} qualified")
        
        if qualified_count == 0:
            print("WARNING: No leads qualified")
            update_progress(f"Scoring complete. No leads qualified (0/{len(scored_leads)} met threshold).")
            # Still save scored leads for review
            st.session_state["drafted_leads"] = []
            st.session_state["is_processing"] = False
            st.rerun()
            return
        
        # Phase 3: Scribe - Draft outreach for qualified leads
        print(f"\n[PHASE 3] Starting Scribe Agent for {qualified_count} qualified leads...")
        update_progress(f"Phase 3: Drafting outreach for {qualified_count} qualified leads...")
        
        if use_mock:
            print("Using MockScribeAgent")
            scribe = MockScribeAgent(on_progress=update_progress)
        else:
            print("Using Production ScribeAgent with DeepSeek V3")
            scribe = ScribeAgent(deepseek, on_progress=update_progress)
        
        print("Executing Scribe...")
        drafted_leads = scribe.execute(
            scored_leads=scored_leads,
            value_prop=params["value_prop"]
        )
        print(f"Scribe completed: {len(drafted_leads)} leads drafted")
        st.session_state["drafted_leads"] = drafted_leads
        
        print(f"\n{'='*60}")
        print(f"HUNT COMPLETE - {len(drafted_leads)} leads ready")
        print(f"{'='*60}\n")
        update_progress(f"Hunt complete! {len(drafted_leads)} leads ready for review.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*60}")
        print(f"ERROR IN PIPELINE:")
        print(f"{'='*60}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        print(f"{'='*60}\n")
        
        st.error(f"Hunt failed: {error_msg}")
        update_progress(f"Error: {error_msg}")
    
    finally:
        st.session_state["is_processing"] = False
        st.rerun()


def main():
    """Main application entry point."""
    # Debug: Write to file to confirm main() is running
    import os
    debug_file = "/tmp/pharmhunter_debug.log"
    
    with open(debug_file, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"main() called\n")
        f.write(f"should_start_hunt: {st.session_state.get('should_start_hunt', 'NOT SET')}\n")
    
    initialize_session_state()
    
    # Title
    st.title("🎯 PharmHunter")
    st.caption("Automated biopharma lead discovery and qualification")
    
    # Render sidebar
    config = render_sidebar()
    
    # Check if hunt should start (from session state flag)
    if st.session_state.get("should_start_hunt", False):
        with open(debug_file, "a") as f:
            f.write("HUNT FLAG DETECTED - starting pipeline\n")
        
        st.session_state["should_start_hunt"] = False
        params = st.session_state.get("hunt_params", {})
        
        with open(debug_file, "a") as f:
            f.write(f"Params: {params.keys() if params else 'NONE'}\n")
        
        if params:
            with open(debug_file, "a") as f:
                f.write("Calling run_hunt_pipeline...\n")
            run_hunt_pipeline(params)
    
    # Main content tabs
    tab1, tab2 = st.tabs(["Mission Control", "War Room"])
    
    with tab1:
        render_mission_control(on_start_hunt=None)  # Don't use callback, use session state instead
    
    with tab2:
        render_war_room()


if __name__ == "__main__":
    main()
