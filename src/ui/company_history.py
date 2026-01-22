"""Company History tab - View all discovered companies across hunts."""

import streamlit as st
import pandas as pd
from typing import List, Optional
from datetime import datetime

from ..models.company_history import CompanyRecord, CompanyHistory, HuntSummary
from ..services.company_history_service import CompanyHistoryService


def render_company_history():
    """Render the Company History tab with all discovered companies."""
    st.header("Company History")
    st.caption("All companies discovered across all hunts - duplicates are automatically filtered from future searches")
    
    # Load history
    history_service = CompanyHistoryService()
    history = history_service.load_history()
    
    # Summary metrics at the top
    render_history_metrics(history)
    
    st.divider()
    
    # Check if we have any data
    if not history.companies:
        st.info("No companies in history yet. Run a hunt in Mission Control to start building your history.")
        return
    
    # Filters and sorting
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Qualified", "Disqualified"],
            key="history_status_filter"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort By",
            options=["Last Seen", "First Seen", "Best Score", "Times Discovered", "Company Name"],
            key="history_sort_by"
        )
    
    with col3:
        sort_order = st.selectbox(
            "Order",
            options=["Descending", "Ascending"],
            key="history_sort_order"
        )
    
    # Search box
    search_query = st.text_input(
        "Search companies",
        placeholder="Type to filter by company name...",
        key="history_search"
    )
    
    # Filter and sort companies
    display_companies = filter_and_sort_companies(
        history.companies,
        status_filter,
        sort_by,
        sort_order == "Ascending",
        search_query
    )
    
    st.divider()
    
    # Display count
    st.caption(f"Showing {len(display_companies)} of {len(history.companies)} companies")
    
    # Company table
    render_company_table(display_companies)
    
    # Hunt history timeline
    st.divider()
    with st.expander("Hunt History Timeline", expanded=False):
        render_hunt_timeline(history.hunt_summary)


def render_history_metrics(history: CompanyHistory):
    """Display summary metrics for the history."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Companies", history.total_companies)
    
    with col2:
        st.metric("Total Hunts", history.total_hunts)
    
    with col3:
        qualified = sum(1 for c in history.companies if c.was_qualified)
        st.metric("Qualified", qualified)
    
    with col4:
        scores = [c.best_score for c in history.companies if c.best_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        st.metric("Avg Best Score", f"{avg_score:.0f}")


def filter_and_sort_companies(
    companies: List[CompanyRecord],
    status_filter: str,
    sort_by: str,
    ascending: bool,
    search_query: str
) -> List[CompanyRecord]:
    """Filter and sort companies based on user selections."""
    filtered = companies
    
    # Apply status filter
    if status_filter == "Qualified":
        filtered = [c for c in filtered if c.was_qualified]
    elif status_filter == "Disqualified":
        filtered = [c for c in filtered if not c.was_qualified]
    
    # Apply search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [c for c in filtered if query_lower in c.company_name.lower()]
    
    # Sort
    if sort_by == "Last Seen":
        filtered = sorted(filtered, key=lambda c: c.last_seen, reverse=not ascending)
    elif sort_by == "First Seen":
        filtered = sorted(filtered, key=lambda c: c.first_seen, reverse=not ascending)
    elif sort_by == "Best Score":
        filtered = sorted(filtered, key=lambda c: c.best_score or 0, reverse=not ascending)
    elif sort_by == "Times Discovered":
        filtered = sorted(filtered, key=lambda c: c.times_discovered, reverse=not ascending)
    elif sort_by == "Company Name":
        filtered = sorted(filtered, key=lambda c: c.company_name.lower(), reverse=not ascending)
    
    return filtered


def render_company_table(companies: List[CompanyRecord]):
    """Render the company table with expandable details."""
    if not companies:
        st.info("No companies match the current filters.")
        return
    
    # Create DataFrame for table display
    table_data = []
    for company in companies:
        status = "Qualified" if company.was_qualified else "Disqualified"
        status_icon = "✅" if company.was_qualified else "❌"
        
        table_data.append({
            "Company": company.company_name,
            "Status": f"{status_icon} {status}",
            "Best Score": company.best_score or "-",
            "Times Found": company.times_discovered,
            "First Seen": company.first_seen.strftime("%Y-%m-%d") if company.first_seen else "-",
            "Last Seen": company.last_seen.strftime("%Y-%m-%d") if company.last_seen else "-",
            "Therapeutic Areas": ", ".join(set(company.therapeutic_areas))[:50] + "..." if len(", ".join(set(company.therapeutic_areas))) > 50 else ", ".join(set(company.therapeutic_areas)),
        })
    
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Best Score": st.column_config.NumberColumn("Best Score", width="small"),
            "Times Found": st.column_config.NumberColumn("Times Found", width="small"),
            "First Seen": st.column_config.TextColumn("First Seen", width="small"),
            "Last Seen": st.column_config.TextColumn("Last Seen", width="small"),
            "Therapeutic Areas": st.column_config.TextColumn("Therapeutic Areas", width="medium"),
        }
    )
    
    # Expandable detail view for each company
    st.subheader("Company Details")
    
    selected_company = st.selectbox(
        "Select a company to view details",
        options=[c.company_name for c in companies],
        key="history_company_select"
    )
    
    if selected_company:
        company = next((c for c in companies if c.company_name == selected_company), None)
        if company:
            render_company_detail(company)


def render_company_detail(company: CompanyRecord):
    """Render detailed view for a single company."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Discovery Info**")
        st.metric("Times Discovered", company.times_discovered)
        st.metric("Best ICP Score", company.best_score or "N/A")
        
        if company.website:
            st.write(f"**Website:** [{company.website}]({company.website})")
        
        st.write(f"**First Seen:** {company.first_seen.strftime('%Y-%m-%d %H:%M')}")
        st.write(f"**Last Seen:** {company.last_seen.strftime('%Y-%m-%d %H:%M')}")
    
    with col2:
        st.markdown("**Clinical Focus**")
        
        st.write("**Therapeutic Areas:**")
        for area in sorted(set(company.therapeutic_areas)):
            st.write(f"- {area}")
        
        st.write("**Clinical Phases:**")
        for phase in sorted(set(company.clinical_phases)):
            st.write(f"- {phase}")
    
    # Score history
    if company.icp_scores:
        st.markdown("**Score History**")
        scores_str = ", ".join(str(s) for s in company.icp_scores)
        st.write(f"All scores: {scores_str}")
        st.write(f"Average score: {sum(company.icp_scores) / len(company.icp_scores):.0f}")
    
    st.divider()
    
    # Encounter history - the rich details from each hunt
    if company.encounters:
        st.subheader(f"Hunt Encounters ({len(company.encounters)})")
        st.caption("Detailed records from each hunt where this company was discovered")
        
        # Sort encounters by timestamp (newest first)
        sorted_encounters = sorted(company.encounters, key=lambda e: e.timestamp, reverse=True)
        
        for i, encounter in enumerate(sorted_encounters, 1):
            with st.expander(
                f"**Encounter {i}:** {encounter.timestamp.strftime('%Y-%m-%d %H:%M')} "
                f"(Hunt: {encounter.hunt_id[:8]}...) "
                f"{'✅ Qualified' if encounter.is_qualified else '❌ Disqualified'}"
            ):
                render_encounter_detail(encounter)
    else:
        st.info("No detailed encounter data available for this company. Encounters are saved for hunts going forward.")
    
    # Source URLs
    if company.source_urls:
        with st.expander("All Source URLs"):
            for url in company.source_urls:
                st.write(f"- [{url}]({url})")


def render_encounter_detail(encounter):
    """Render detailed view of a single hunt encounter."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Scoring Details")
        
        # ICP Score
        if encounter.icp_score is not None:
            st.metric("ICP Score", encounter.icp_score)
            
            # Score breakdown
            if encounter.score_breakdown:
                st.markdown("**Score Breakdown:**")
                for criterion, score in encounter.score_breakdown.items():
                    # Visual bar
                    bar = "█" * (score // 5) + "░" * ((100 - score) // 5)
                    st.write(f"{criterion}: {score}/100")
                    st.caption(f"`{bar}`")
            
            # Scoring explanation
            if encounter.score_explanation:
                with st.expander("Why This Score?"):
                    st.write(encounter.score_explanation)
        
        # Provenance
        st.markdown("### Discovery Provenance")
        if encounter.discovery_source:
            st.write(f"**Source:** {encounter.discovery_source}")
        if encounter.source_priority:
            st.write(f"**Priority Tier:** {encounter.source_priority}")
        if encounter.search_round:
            st.write(f"**Search Round:** {encounter.search_round}")
        if encounter.source_url:
            st.write(f"**URL:** [{encounter.source_url}]({encounter.source_url})")
    
    with col2:
        st.markdown("### Clinical Details")
        
        if encounter.therapeutic_area:
            st.write(f"**Therapeutic Area:** {encounter.therapeutic_area}")
        if encounter.clinical_phase:
            st.write(f"**Clinical Phase:** {encounter.clinical_phase}")
        
        # Drafted message
        if encounter.email_subject or encounter.email_body:
            st.markdown("### Outreach Message")
            
            if encounter.email_subject:
                st.markdown("**Subject Line:**")
                st.info(encounter.email_subject)
            
            if encounter.email_body:
                st.markdown("**Email Body:**")
                with st.container():
                    st.text_area(
                        "Email Content",
                        value=encounter.email_body,
                        height=200,
                        key=f"encounter_email_{encounter.hunt_id}_{id(encounter)}",
                        label_visibility="collapsed"
                    )
            
            if encounter.personalization_notes:
                with st.expander("Personalization Notes"):
                    st.write(encounter.personalization_notes)


def render_hunt_timeline(hunt_summary: dict):
    """Render timeline of all hunts."""
    if not hunt_summary:
        st.info("No hunt history available yet.")
        return
    
    # Sort hunts by timestamp (newest first)
    sorted_hunts = sorted(
        hunt_summary.values(),
        key=lambda h: h.timestamp if hasattr(h, 'timestamp') else datetime.min,
        reverse=True
    )
    
    for hunt in sorted_hunts:
        # Handle both HuntSummary objects and dicts
        if isinstance(hunt, dict):
            hunt_id = hunt.get('hunt_id', 'Unknown')
            timestamp = hunt.get('timestamp', 'Unknown')
            companies_found = hunt.get('companies_found', 0)
            qualified_count = hunt.get('qualified_count', 0)
            new_companies = hunt.get('new_companies', 0)
            params = hunt.get('params', {})
        else:
            hunt_id = hunt.hunt_id
            timestamp = hunt.timestamp
            companies_found = hunt.companies_found
            qualified_count = hunt.qualified_count
            new_companies = hunt.new_companies
            params = hunt.params
        
        # Format timestamp
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
        elif isinstance(timestamp, str):
            time_str = timestamp[:16] if len(timestamp) > 16 else timestamp
        else:
            time_str = str(timestamp)
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**Hunt {hunt_id[:8]}...**")
                st.caption(time_str)
            
            with col2:
                st.metric("Found", companies_found, label_visibility="collapsed")
                st.caption("Companies Found")
            
            with col3:
                st.metric("New", new_companies, label_visibility="collapsed")
                st.caption("New Companies")
            
            with col4:
                st.metric("Qualified", qualified_count, label_visibility="collapsed")
                st.caption("Qualified")
            
            # Show search params
            if params:
                focus = params.get('therapeutic_focus', 'N/A')
                phases = params.get('phase_preference', [])
                if isinstance(phases, list):
                    phases = ', '.join(phases)
                st.caption(f"Focus: {focus} | Phases: {phases}")
            
            st.markdown("---")
