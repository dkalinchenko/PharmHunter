"""Mission Control tab - Context and search parameters."""

import streamlit as st
from typing import Callable, Optional

from ..prompts.templates import ICP_DEFINITION, DEFAULT_VALUE_PROP


def render_mission_control(on_start_hunt: Optional[Callable] = None) -> dict:
    """
    Render the Mission Control tab with ICP context and search parameters.
    
    Args:
        on_start_hunt: Callback function when hunt is started
        
    Returns:
        dict with all search parameters
    """
    st.header("Mission Control")
    
    # Section 1: The Brain (Context)
    st.subheader("The Brain (Context)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        icp_definition = st.text_area(
            "ICP Definition",
            value=st.session_state.get("icp_definition", ICP_DEFINITION),
            height=300,
            key="icp_definition_input",
            help="Define the Ideal Customer Profile criteria for lead qualification"
        )
        st.session_state["icp_definition"] = icp_definition
    
    with col2:
        value_prop = st.text_area(
            "Value Proposition",
            value=st.session_state.get("value_prop", DEFAULT_VALUE_PROP),
            height=300,
            key="value_prop_input",
            help="Define your consulting offers and value proposition for outreach"
        )
        st.session_state["value_prop"] = value_prop
    
    st.divider()
    
    # Section 2: The Hunt (Parameters)
    st.subheader("The Hunt (Parameters)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        lead_count = st.slider(
            "Lead Count",
            min_value=5,
            max_value=50,
            value=st.session_state.get("lead_count", 20),
            step=5,
            key="lead_count_slider",
            help="Number of companies to discover"
        )
        st.session_state["lead_count"] = lead_count
        
        therapeutic_focus = st.text_input(
            "Therapeutic Focus",
            value=st.session_state.get("therapeutic_focus", "Radiopharma, Oncology"),
            key="therapeutic_focus_input",
            help="e.g., Radiopharma, Oncology, CNS, Immunotherapy"
        )
        st.session_state["therapeutic_focus"] = therapeutic_focus
    
    with col2:
        phase_options = ["Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3"]
        phase_preference = st.multiselect(
            "Phase Preference",
            options=phase_options,
            default=st.session_state.get("phase_preference", ["Phase 2", "Phase 2/3"]),
            key="phase_preference_select",
            help="Select preferred clinical trial phases"
        )
        st.session_state["phase_preference"] = phase_preference
        
        geography = st.text_input(
            "Geography",
            value=st.session_state.get("geography", "Global"),
            key="geography_input",
            help="e.g., US, US + EU, Global"
        )
        st.session_state["geography"] = geography
    
    with col3:
        exclusions = st.text_input(
            "Exclusions",
            value=st.session_state.get("exclusions", "Large Pharma, Med Device, Diagnostics-only"),
            key="exclusions_input",
            help="Companies to exclude from search"
        )
        st.session_state["exclusions"] = exclusions
    
    st.divider()
    
    # Start button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        hunt_clicked = st.button(
            "START HUNTING",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get("is_processing", False),
            key="start_hunt_button"
        )
    
    params = {
        "icp_definition": icp_definition,
        "value_prop": value_prop,
        "lead_count": lead_count,
        "therapeutic_focus": therapeutic_focus,
        "phase_preference": phase_preference,
        "geography": geography,
        "exclusions": exclusions
    }
    
    # Store params in session state when button clicked
    if hunt_clicked:
        # Debug: Write to file
        import os
        debug_file = "/tmp/pharmhunter_debug.log"
        with open(debug_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"BUTTON CLICKED\n")
            f.write(f"Setting should_start_hunt = True\n")
            f.write(f"Params: {list(params.keys())}\n")
        
        st.session_state["hunt_params"] = params
        st.session_state["should_start_hunt"] = True
        st.toast("🚀 Starting hunt...", icon="🎯")
        st.rerun()  # Trigger rerun to execute hunt
    
    return params
