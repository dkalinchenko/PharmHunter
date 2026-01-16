"""War Room tab - Results display and review."""

import streamlit as st
import pandas as pd
from typing import List, Optional, Union

from ..models.leads import DraftedLead, ScoredLead
from .process_inspector import render_scoring_breakdown


def get_score_color(score: int) -> str:
    """Return color based on score value."""
    if score >= 85:
        return "🟢"
    elif score >= 75:
        return "🟡"
    else:
        return "🔴"


def render_progress_status():
    """Render enhanced progress status with expandable details."""
    status_text = st.session_state.get("processing_status", "Processing...")
    
    with st.status(status_text, expanded=True, state="running"):
        st.write("**Current Phase:**")
        
        # Show phase-specific progress
        raw_leads = st.session_state.get("raw_leads", [])
        scored_leads = st.session_state.get("scored_leads", [])
        drafted_leads = st.session_state.get("drafted_leads", [])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if raw_leads:
                st.success(f"Scout: {len(raw_leads)} found")
            else:
                st.info("Scout: Searching...")
        
        with col2:
            if scored_leads:
                qualified = sum(1 for l in scored_leads if l.is_qualified)
                st.success(f"Analyst: {qualified}/{len(scored_leads)} qualified")
            elif raw_leads:
                st.info("Analyst: Scoring...")
            else:
                st.empty()
        
        with col3:
            if drafted_leads:
                st.success(f"Scribe: {len(drafted_leads)} drafted")
            elif scored_leads:
                st.info("Scribe: Drafting...")
            else:
                st.empty()


def render_war_room(leads: Optional[List[Union[DraftedLead, ScoredLead]]] = None):
    """
    Render the War Room tab with results table and detail views.
    
    Args:
        leads: List of drafted leads to display
    """
    st.header("War Room")
    
    # Get leads from session state if not provided
    if leads is None:
        leads = st.session_state.get("drafted_leads", [])
    
    # Also get scored leads for showing non-qualified leads
    scored_leads = st.session_state.get("scored_leads", [])
    
    # Processing status
    if st.session_state.get("is_processing", False):
        render_progress_status()
        return
    
    # No results yet
    if not leads and not scored_leads:
        st.info("No leads yet. Go to Mission Control and start hunting!")
        
        # Show quick tips
        with st.expander("Quick Tips"):
            st.markdown("""
            1. **Configure API Keys** in the sidebar (or use Mock Mode for testing)
            2. **Set your ICP Definition** and **Value Proposition** in Mission Control
            3. **Adjust search parameters** (therapeutic focus, phase, geography)
            4. **Click START HUNTING** to begin the discovery pipeline
            """)
        return
    
    # If we have scored leads but no drafted leads, show the scored ones
    display_leads = leads if leads else scored_leads
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_leads = len(scored_leads) if scored_leads else len(display_leads)
    qualified_leads = [l for l in display_leads if l.is_qualified]
    avg_score = sum(l.icp_score for l in display_leads) / len(display_leads) if display_leads else 0
    
    with col1:
        st.metric("Total Leads", total_leads)
    with col2:
        st.metric("Qualified", len(qualified_leads))
    with col3:
        st.metric("Avg Score", f"{avg_score:.0f}")
    with col4:
        csv_data = generate_csv(display_leads)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="pharmhunter_leads.csv",
            mime="text/csv",
            type="secondary"
        )
    
    st.divider()
    
    # Filter controls
    col1, col2 = st.columns([3, 1])
    with col1:
        show_all = st.toggle(
            "Show all leads (including disqualified)",
            value=st.session_state.get("show_all_leads", False),
            key="show_all_toggle"
        )
        st.session_state["show_all_leads"] = show_all
    
    # Filter leads based on toggle
    if show_all:
        filtered_leads = display_leads
    else:
        filtered_leads = [l for l in display_leads if l.is_qualified]
    
    # Results table
    if filtered_leads:
        # Create DataFrame for display
        table_data = []
        for lead in filtered_leads:
            trigger_text = lead.buying_signal if lead.buying_signal else "No trigger identified"
            
            # Get provenance info if available
            source_name = "Unknown"
            source_priority = "-"
            search_round = "-"
            if hasattr(lead, 'provenance') and lead.provenance:
                source_name = lead.provenance.discovered_from_source
                source_priority = f"P{lead.provenance.source_priority}"
                search_round = lead.provenance.search_round
            
            table_data.append({
                "Company": lead.company_name,
                "Phase": lead.clinical_phase,
                "Score": f"{get_score_color(lead.icp_score)} {lead.icp_score}",
                "Source": source_name,
                "Therapeutic Area": lead.therapeutic_area,
                "Trigger": trigger_text[:80] + "..." if len(trigger_text) > 80 else trigger_text,
                "Offer": lead.recommended_offer,
                "Status": "✅ Qualified" if lead.is_qualified else "❌ Disqualified"
            })
        
        df = pd.DataFrame(table_data)
        
        # Display as data editor for row selection
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Company": st.column_config.TextColumn("Company", width="medium"),
                "Phase": st.column_config.TextColumn("Phase", width="small"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Source": st.column_config.TextColumn("Source", width="medium"),
                "Therapeutic Area": st.column_config.TextColumn("Area", width="medium"),
                "Trigger": st.column_config.TextColumn("Trigger Event", width="large"),
                "Offer": st.column_config.TextColumn("Recommended Offer", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small")
            }
        )
        
        st.divider()
        
        # Detailed view per lead
        st.subheader("Lead Details")
        
        for i, lead in enumerate(filtered_leads):
            score_indicator = get_score_color(lead.icp_score)
            status = "✅" if lead.is_qualified else "❌"
            
            with st.expander(
                f"{score_indicator} {lead.company_name} — Score: {lead.icp_score} {status} — {lead.clinical_phase}",
                expanded=False
            ):
                render_lead_detail(lead, i)
    else:
        if show_all:
            st.info("No leads found. Run a new hunt in Mission Control.")
        else:
            st.warning("No qualified leads. Toggle 'Show all leads' to see disqualified leads, or adjust your ICP criteria.")


def render_lead_detail(lead: Union[DraftedLead, ScoredLead], index: int):
    """Render detailed view for a single lead."""
    
    is_drafted = isinstance(lead, DraftedLead)
    
    # Lead provenance section (Glass Box transparency)
    if hasattr(lead, 'provenance') and lead.provenance:
        st.markdown("**Lead Provenance**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Source", lead.provenance.discovered_from_source)
        with col2:
            st.metric("Priority", f"P{lead.provenance.source_priority}")
        with col3:
            st.metric("Search Round", lead.provenance.search_round)
        with col4:
            if hasattr(lead, 'raw_search_rank') and lead.raw_search_rank:
                st.metric("Original Rank", f"#{lead.raw_search_rank}")
            else:
                st.metric("Original Rank", "-")
        
        if lead.provenance.source_url and lead.provenance.source_url != "unknown":
            st.caption(f"Source URL: [{lead.provenance.source_url}]({lead.provenance.source_url})")
        
        st.divider()
    
    # Two columns: Info and Reasoning
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Company Info**")
        st.write(f"**Name:** {lead.company_name}")
        if lead.website:
            st.write(f"**Website:** [{lead.website}]({lead.website})")
        else:
            st.write("**Website:** N/A")
        st.write(f"**Therapeutic Area:** {lead.therapeutic_area}")
        st.write(f"**Phase:** {lead.clinical_phase}")
        st.write(f"**Imaging Signal:** {lead.imaging_signal}")
        
        st.markdown("**Qualification**")
        
        # Score with color bar
        score_color = "green" if lead.icp_score >= 85 else "orange" if lead.icp_score >= 75 else "red"
        st.progress(lead.icp_score / 100, text=f"ICP Score: {lead.icp_score}/100")
        
        if lead.is_qualified:
            st.success("✅ Qualified for outreach")
        else:
            st.error(f"❌ Disqualified: {lead.disqualification_reason or 'Score below threshold'}")
        
        st.write(f"**Buying Signal:** {lead.buying_signal or 'None identified'}")
        st.write(f"**Recommended Offer:** {lead.recommended_offer}")
        
        # Score breakdown (if available)
        if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
            st.divider()
            render_scoring_breakdown(lead)
    
    with col2:
        st.markdown("**The Math (Reasoning Chain)**")
        if lead.reasoning_chain:
            st.text_area(
                "Analysis",
                value=lead.reasoning_chain,
                height=300,
                disabled=True,
                key=f"reasoning_{index}",
                label_visibility="collapsed"
            )
        else:
            st.info("No reasoning chain available")
        
        # Score explanation (if available and different from reasoning chain)
        if hasattr(lead, 'score_explanation') and lead.score_explanation:
            with st.expander("Score Explanation"):
                st.write(lead.score_explanation)
    
    # Only show draft sections for DraftedLead
    if is_drafted and lead.is_qualified:
        st.divider()
        
        # Contact info
        st.markdown("**Target Contact**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Persona:** {lead.contact_persona}")
        with col2:
            st.write(f"**Name:** {lead.contact_name or 'Not found'}")
            st.write(f"**Title:** {lead.contact_title or 'N/A'}")
        with col3:
            if lead.contact_linkedin:
                st.write(f"**LinkedIn:** [View Profile]({lead.contact_linkedin})")
            else:
                st.write("**LinkedIn:** Not found")
        
        st.divider()
        
        # Draft emails
        st.markdown("**The Draft (Outreach Package)**")
        
        # Subject lines
        if lead.email_subject_options:
            st.selectbox(
                "Subject Line Options",
                options=lead.email_subject_options,
                key=f"subject_select_{index}",
                help="Choose from 6 subject line variants"
            )
        
        # Tab layout for email variants
        email_tab1, email_tab2, email_tab3, email_tab4, email_tab5 = st.tabs([
            "📧 Primary", "🎯 De-risk", "📈 Scale-up", "💼 LinkedIn", "🔄 Follow-up"
        ])
        
        with email_tab1:
            st.text_area(
                "Primary Email Body",
                value=lead.email_body_primary,
                height=300,
                key=f"primary_email_{index}",
                help="Main email (120-180 words)"
            )
        
        with email_tab2:
            st.caption("Angle: De-risk proof-of-concept / endpoint integrity")
            st.text_area(
                "Variant 1",
                value=lead.email_variant_1,
                height=250,
                key=f"variant1_{index}"
            )
        
        with email_tab3:
            st.caption("Angle: Scale-up execution + site consistency")
            st.text_area(
                "Variant 2",
                value=lead.email_variant_2,
                height=250,
                key=f"variant2_{index}"
            )
        
        with email_tab4:
            char_count = len(lead.linkedin_message) if lead.linkedin_message else 0
            st.caption(f"Characters: {char_count}/350")
            st.text_area(
                "LinkedIn Message",
                value=lead.linkedin_message,
                height=100,
                key=f"linkedin_{index}"
            )
        
        with email_tab5:
            st.caption("For 5-7 business days later")
            st.text_area(
                "Follow-up Email",
                value=lead.follow_up_email,
                height=200,
                key=f"followup_{index}"
            )
    elif not is_drafted and lead.is_qualified:
        st.divider()
        st.warning("Draft outreach not yet generated for this lead.")


def generate_csv(leads: List[Union[DraftedLead, ScoredLead]]) -> str:
    """Generate CSV data from leads."""
    
    # Flatten leads to DataFrame
    data = []
    for lead in leads:
        # Provenance info
        source_name = ""
        source_priority = ""
        search_round = ""
        if hasattr(lead, 'provenance') and lead.provenance:
            source_name = lead.provenance.discovered_from_source
            source_priority = lead.provenance.source_priority
            search_round = lead.provenance.search_round
        
        # Score breakdown
        score_breakdown_str = ""
        if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
            parts = [f"{k}: {v}" for k, v in lead.score_breakdown.items()]
            score_breakdown_str = "; ".join(parts)
        
        # Base fields (common to ScoredLead and DraftedLead)
        row = {
            "Company Name": lead.company_name,
            "Website": lead.website or "",
            "Therapeutic Area": lead.therapeutic_area,
            "Clinical Phase": lead.clinical_phase,
            "Imaging Signal": lead.imaging_signal,
            "Source URL": getattr(lead, 'source_url', '') or "",
            "Discovery Source": source_name,
            "Source Priority": source_priority,
            "Search Round": search_round,
            "ICP Score": lead.icp_score,
            "Score Breakdown": score_breakdown_str,
            "Score Explanation": getattr(lead, 'score_explanation', '') or "",
            "Qualified": "Yes" if lead.is_qualified else "No",
            "Disqualification Reason": lead.disqualification_reason or "",
            "Buying Signal": lead.buying_signal,
            "Recommended Offer": lead.recommended_offer,
            "Reasoning Summary": lead.reasoning_chain[:500] + "..." if len(lead.reasoning_chain) > 500 else lead.reasoning_chain
        }
        
        # DraftedLead-specific fields
        if isinstance(lead, DraftedLead):
            row.update({
                "Contact Persona": lead.contact_persona,
                "Contact Name": lead.contact_name or "",
                "Contact Title": lead.contact_title or "",
                "Contact LinkedIn": lead.contact_linkedin or "",
                "Subject Line 1": lead.email_subject_options[0] if lead.email_subject_options else "",
                "Subject Line 2": lead.email_subject_options[1] if len(lead.email_subject_options) > 1 else "",
                "Subject Line 3": lead.email_subject_options[2] if len(lead.email_subject_options) > 2 else "",
                "Subject Line 4": lead.email_subject_options[3] if len(lead.email_subject_options) > 3 else "",
                "Subject Line 5": lead.email_subject_options[4] if len(lead.email_subject_options) > 4 else "",
                "Subject Line 6": lead.email_subject_options[5] if len(lead.email_subject_options) > 5 else "",
                "Primary Email": lead.email_body_primary,
                "Email Variant 1 (De-risk)": lead.email_variant_1,
                "Email Variant 2 (Scale-up)": lead.email_variant_2,
                "LinkedIn Message": lead.linkedin_message,
                "Follow-up Email": lead.follow_up_email,
            })
        
        data.append(row)
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False)
