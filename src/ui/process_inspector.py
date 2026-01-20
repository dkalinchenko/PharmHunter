"""Process Inspector tab - Glass Box transparency for the pipeline."""

import streamlit as st
import pandas as pd
from typing import List, Optional
from datetime import datetime

from ..models.pipeline_state import SearchLedger, SourceRecord, PipelineState, StageData
from ..models.leads import Lead, ScoredLead


def render_process_inspector():
    """Render the Process Inspector tab with full pipeline transparency."""
    st.header("Process Inspector")
    st.caption("The Glass Box - Complete visibility into the lead discovery pipeline")
    
    # Check if we have any data
    pipeline_state: Optional[PipelineState] = st.session_state.get("pipeline_state")
    
    if not pipeline_state:
        st.info("No hunt has been executed yet. Start a hunt in Mission Control to see process details.")
        return
    
    # Summary metrics at the top
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Hunt ID", pipeline_state.hunt_id[:8] + "...")
    with col2:
        st.metric("Total Queries", pipeline_state.search_ledger.total_queries if pipeline_state.search_ledger else 0)
    with col3:
        st.metric("New Companies", pipeline_state.new_companies_found)
    with col4:
        st.metric("Duplicates Filtered", pipeline_state.duplicates_filtered)
    with col5:
        st.metric("Qualified", pipeline_state.qualified_count)
    
    st.divider()
    
    # Tabbed view for different inspection areas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Search Ledger",
        "Top of Funnel",
        "Duplicates Filtered",
        "Pipeline Timeline",
        "Errors"
    ])
    
    with tab1:
        render_search_ledger(pipeline_state.search_ledger)
    
    with tab2:
        render_top_of_funnel(pipeline_state)
    
    with tab3:
        render_duplicates_filtered(pipeline_state)
    
    with tab4:
        render_pipeline_timeline(pipeline_state)
    
    with tab5:
        render_errors(pipeline_state)


def render_search_ledger(search_ledger: Optional[SearchLedger]):
    """Display all queries executed during the hunt."""
    st.subheader("Search Ledger")
    st.caption("Every query executed during lead discovery")
    
    if not search_ledger or not search_ledger.sources_queried:
        st.info("No search queries recorded yet.")
        return
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Queries", search_ledger.total_queries)
    with col2:
        st.metric("Total Results", search_ledger.total_results_found)
    with col3:
        st.metric("Unique Results", search_ledger.unique_results_found)
    with col4:
        duration = search_ledger.duration_seconds
        st.metric("Duration", f"{duration:.1f}s" if duration else "N/A")
    
    st.divider()
    
    # Group by priority
    priority_groups = {1: [], 2: [], 3: []}
    for record in search_ledger.sources_queried:
        priority_groups[record.source_priority].append(record)
    
    priority_labels = {
        1: "Priority 1: Primary Sources (ClinicalTrials.gov)",
        2: "Priority 2: Biotech Aggregators",
        3: "Priority 3: Optional Sources"
    }
    
    for priority in [1, 2, 3]:
        records = priority_groups[priority]
        if records:
            with st.expander(f"{priority_labels[priority]} ({len(records)} queries)", expanded=(priority == 1)):
                for i, record in enumerate(records):
                    render_source_record(record, i)


def render_source_record(record: SourceRecord, index: int):
    """Render a single source record."""
    status_icon = "✅" if record.was_successful else "❌"
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"**{record.source_name}** {status_icon}")
    with col2:
        st.markdown(f"Results: **{record.results_count}**")
    with col3:
        st.markdown(f"`{record.query_timestamp.strftime('%H:%M:%S')}`")
    
    # Query details
    st.code(record.query_text, language=None)
    
    if record.domains_searched:
        st.caption(f"Domains: {', '.join(record.domains_searched)}")
    
    if not record.was_successful and record.error_message:
        st.error(f"Error: {record.error_message}")
    
    st.markdown("---")


def render_top_of_funnel(pipeline_state: PipelineState):
    """Show all companies identified before filtering."""
    st.subheader(f"Top of Funnel ({pipeline_state.top_of_funnel_count} companies)")
    st.caption("All companies identified before ICP scoring")
    
    # Get raw leads from session state
    raw_leads: List[Lead] = st.session_state.get("raw_leads", [])
    
    if not raw_leads:
        if pipeline_state.top_of_funnel_companies:
            # Show just company names if leads not available
            st.write("Companies discovered:")
            for i, company in enumerate(pipeline_state.top_of_funnel_companies, 1):
                st.write(f"{i}. {company}")
        else:
            st.info("No leads discovered yet.")
        return
    
    # Build dataframe with provenance
    data = []
    for i, lead in enumerate(raw_leads, 1):
        row = {
            "#": i,
            "Company": lead.company_name,
            "Therapeutic Area": lead.therapeutic_area,
            "Phase": lead.clinical_phase,
            "Imaging Signal": lead.imaging_signal[:100] + "..." if len(lead.imaging_signal) > 100 else lead.imaging_signal,
        }
        
        # Add provenance if available
        if lead.provenance:
            row["Source"] = lead.provenance.discovered_from_source
            row["Priority"] = f"P{lead.provenance.source_priority}"
            row["Round"] = lead.provenance.search_round
        else:
            row["Source"] = "Unknown"
            row["Priority"] = "-"
            row["Round"] = "-"
        
        if lead.raw_search_rank:
            row["Rank"] = lead.raw_search_rank
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.multiselect(
            "Filter by Source",
            options=df["Source"].unique().tolist(),
            default=[]
        )
    with col2:
        round_filter = st.multiselect(
            "Filter by Round",
            options=sorted([r for r in df["Round"].unique() if r != "-"]),
            default=[]
        )
    
    # Apply filters
    if source_filter:
        df = df[df["Source"].isin(source_filter)]
    if round_filter:
        df = df[df["Round"].isin(round_filter)]
    
    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Company": st.column_config.TextColumn(width="medium"),
            "Phase": st.column_config.TextColumn(width="small"),
            "Priority": st.column_config.TextColumn(width="small"),
            "Round": st.column_config.NumberColumn(width="small"),
        }
    )
    
    # Expandable detail view for each lead
    with st.expander("View Lead Details"):
        selected_company = st.selectbox(
            "Select a company",
            options=[l.company_name for l in raw_leads]
        )
        
        if selected_company:
            lead = next((l for l in raw_leads if l.company_name == selected_company), None)
            if lead:
                st.json(lead.model_dump(exclude_none=True, mode="json"))


def render_duplicates_filtered(pipeline_state: PipelineState):
    """Display companies that were filtered as duplicates."""
    st.subheader("Duplicates Filtered")
    st.caption("Companies skipped because they were already in history")
    
    duplicates = pipeline_state.duplicate_details
    
    if not duplicates:
        st.success("No duplicates were filtered in this hunt.")
        st.info("This means all discovered companies were new to your history.")
        return
    
    st.info(f"{len(duplicates)} companies were filtered as duplicates")
    
    # Build table
    table_data = []
    for dup in duplicates:
        table_data.append({
            "Company": dup.get("company_name", "Unknown"),
            "Matched With": dup.get("matched_with", "batch duplicate"),
            "Match Score": f"{dup.get('match_score', 0)}%",
            "Reason": dup.get("reason", "unknown"),
            "Times Seen Before": dup.get("times_discovered", "-"),
            "Last Seen": dup.get("last_seen", "-")[:10] if dup.get("last_seen") else "-"
        })
    
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Matched With": st.column_config.TextColumn("Matched With", width="medium"),
            "Match Score": st.column_config.TextColumn("Score", width="small"),
            "Reason": st.column_config.TextColumn("Reason", width="small"),
            "Times Seen Before": st.column_config.TextColumn("Times Seen", width="small"),
            "Last Seen": st.column_config.TextColumn("Last Seen", width="small"),
        }
    )
    
    # Explanation
    with st.expander("About Duplicate Detection"):
        st.markdown("""
        **How duplicates are detected:**
        
        - **Exact Match**: Company names that match exactly (case-insensitive)
        - **Fuzzy Match**: Company names that are similar (≥85% similarity)
        - **Batch Duplicate**: Same company appearing multiple times in search results
        
        **Normalization Rules:**
        - Company suffixes (Inc, LLC, Ltd, Corp) are removed
        - Punctuation and extra whitespace are removed
        - Comparison is case-insensitive
        
        **Example:** "Radiant Therapeutics, Inc." matches "Radiant Therapeutics"
        """)


def render_pipeline_timeline(pipeline_state: PipelineState):
    """Timeline view of pipeline execution with expandable stage data."""
    st.subheader("Pipeline Timeline")
    st.caption("Stage-by-stage execution history")
    
    if not pipeline_state.stage_timestamps:
        st.info("No stage data recorded yet.")
        return
    
    # Define stages in order
    stage_order = [
        ("search", "Search Started"),
        ("discovery", "Discovery Complete"),
        ("scoring", "Scoring Complete"),
        ("drafting", "Drafting Complete"),
    ]
    
    # Create timeline
    for stage_key, stage_label in stage_order:
        start_key = f"{stage_key}_start"
        complete_key = f"{stage_key}_complete"
        
        start_time = pipeline_state.stage_timestamps.get(start_key)
        complete_time = pipeline_state.stage_timestamps.get(complete_key)
        
        if start_time or complete_time:
            # Find stage data
            stage_data = next(
                (s for s in pipeline_state.stage_data if s.stage_name == stage_key),
                None
            )
            
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if complete_time:
                        st.markdown(f"**✅ {stage_label}**")
                    elif start_time:
                        st.markdown(f"**⏳ {stage_label}** (in progress)")
                    
                with col2:
                    if complete_time:
                        st.caption(complete_time.strftime("%H:%M:%S"))
                    elif start_time:
                        st.caption(start_time.strftime("%H:%M:%S"))
                
                with col3:
                    if stage_data and stage_data.duration_seconds:
                        st.caption(f"{stage_data.duration_seconds:.1f}s")
                
                # Expandable stage details
                if stage_data and stage_data.details:
                    with st.expander(f"View {stage_key} details"):
                        st.write(f"**Input:** {stage_data.input_count} items")
                        st.write(f"**Output:** {stage_data.output_count} items")
                        st.json(stage_data.details)
                
                st.markdown("---")


def render_errors(pipeline_state: PipelineState):
    """Display any errors that occurred during the pipeline."""
    st.subheader("Errors & Warnings")
    
    if not pipeline_state.errors:
        st.success("No errors recorded during this hunt.")
        return
    
    for error in pipeline_state.errors:
        st.error(error)


def render_scoring_breakdown(lead: ScoredLead):
    """Visual breakdown of score calculation with bar chart."""
    st.markdown("**Score Breakdown**")
    
    if not lead.score_breakdown:
        st.info("No detailed breakdown available")
        return
    
    breakdown = lead.score_breakdown
    
    # Define max values for each component
    max_values = {
        "base_company_fit": 40,
        "phase_match": 20,
        "imaging_materiality": 20,
        "why_now_trigger": 15,
        "complexity_bonus": 5,
    }
    
    # Create visual breakdown
    for component, points in breakdown.items():
        max_val = max_values.get(component, 100)
        label = component.replace("_", " ").title()
        
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            st.markdown(f"**{label}**")
        with col2:
            progress = points / max_val if max_val > 0 else 0
            st.progress(progress)
        with col3:
            st.markdown(f"`{points}/{max_val}`")
    
    # Total
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**TOTAL SCORE**")
    with col2:
        score_color = "green" if lead.icp_score >= 85 else ("orange" if lead.icp_score >= 75 else "red")
        st.markdown(f"<span style='color: {score_color}; font-weight: bold; font-size: 1.2em;'>{lead.icp_score}/100</span>", unsafe_allow_html=True)
    
    # Explanation
    if lead.score_explanation:
        with st.expander("Score Explanation"):
            st.write(lead.score_explanation)
