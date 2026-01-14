"""Scout Agent - Discovers potential leads matching search criteria."""

import json
from typing import List, Optional, Callable

from ..models.leads import Lead
from ..prompts.templates import SCOUT_SYSTEM_PROMPT
from .base_agent import BaseAgent


class MockScoutAgent(BaseAgent):
    """Mock Scout Agent for UI testing without API calls."""
    
    def execute(
        self,
        count: int = 10,
        focus: str = "Oncology",
        phase: str = "Phase 2",
        geography: str = "Global",
        exclusions: str = "Large Pharma",
        **kwargs
    ) -> List[Lead]:
        """Return hardcoded mock leads for testing."""
        self.report_progress(f"Scouting for {count} companies...")
        
        mock_leads = [
            Lead(
                company_name="Radiant Therapeutics",
                website="https://radianttherapeutics.com",
                therapeutic_area="Oncology - Radiopharma",
                clinical_phase="Phase 2",
                imaging_signal="PET dosimetry for Lu-177 targeted therapy. Recently initiated Phase 2 with RECIST 1.1 endpoints.",
                source_url="https://clinicaltrials.gov/example1"
            ),
            Lead(
                company_name="NeuroPrecision Bio",
                website="https://neuroprecisionbio.com",
                therapeutic_area="CNS - Neurodegeneration",
                clinical_phase="Phase 2",
                imaging_signal="MRI volumetrics for Alzheimer's trial. Protocol requires central read for hippocampal atrophy.",
                source_url="https://clinicaltrials.gov/example2"
            ),
            Lead(
                company_name="ImmunoPET Sciences",
                website="https://immunopetsciences.com",
                therapeutic_area="Oncology - Immunotherapy",
                clinical_phase="Phase 1/2",
                imaging_signal="PET-based CD8+ T-cell imaging for checkpoint inhibitor trials. First-in-human dosimetry ongoing.",
                source_url="https://clinicaltrials.gov/example3"
            ),
        ]
        
        self.report_progress(f"Found {len(mock_leads)} candidates")
        return mock_leads[:count]


class ScoutAgent(BaseAgent):
    """Production Scout Agent using Tavily search and DeepSeek."""
    
    def __init__(
        self,
        tavily_service,
        deepseek_service,
        on_progress: Optional[Callable[[str], None]] = None
    ):
        super().__init__(on_progress)
        self.tavily = tavily_service
        self.deepseek = deepseek_service
    
    def execute(
        self,
        count: int = 10,
        focus: str = "Oncology",
        phase: str = "Phase 2",
        geography: str = "Global",
        exclusions: str = "Large Pharma",
        **kwargs
    ) -> List[Lead]:
        """Discover leads using Tavily search and LLM processing."""
        self.report_progress(f"Searching for {count} {focus} companies...")
        
        # Build search queries optimized for biopharma discovery
        queries = [
            f"{focus} biopharma {phase} clinical trial imaging endpoints RECIST PET",
            f"{focus} biotech company {phase} trial first patient dosed imaging",
            f"biopharma {focus} Series B funding clinical imaging {phase}",
            f"{focus} clinical trial {phase} imaging biomarker radiopharma",
        ]
        
        # Collect search results with retry
        all_results = []
        seen_urls = set()
        
        for i, query in enumerate(queries):
            self.report_progress(f"Search query {i+1}/{len(queries)}: {query[:40]}...")
            try:
                results = self.tavily.search_with_retry(
                    query=query,
                    max_results=max(5, count // 2),
                    max_retries=2
                )
                for r in results:
                    url = r.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
            except Exception as e:
                self.report_progress(f"Search error (continuing): {e}")
        
        if not all_results:
            self.report_progress("No search results found. Try broader criteria.")
            return []
        
        self.report_progress(f"Processing {len(all_results)} unique search results...")
        
        # Use LLM to extract and structure leads
        prompt = SCOUT_SYSTEM_PROMPT.format(
            count=count,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions
        )
        
        # Build context from search results
        search_context = "\n\n".join([
            f"Source: {r.get('url', 'N/A')}\nTitle: {r.get('title', 'N/A')}\nContent: {r.get('content', 'N/A')[:500]}"
            for r in all_results[:15]  # Limit context size
        ])
        
        user_prompt = f"Based on these search results, identify up to {count} companies:\n\n{search_context}"
        
        # Call LLM with JSON parsing and retry
        try:
            leads_data = self.deepseek.call_v3_json(
                system_prompt=prompt,
                user_prompt=user_prompt,
                max_retries=2
            )
            
            # Handle both list and dict responses
            if isinstance(leads_data, dict):
                leads_data = leads_data.get("companies", [leads_data])
            
            leads = []
            for lead_dict in leads_data:
                try:
                    leads.append(Lead(**lead_dict))
                except Exception as e:
                    self.report_progress(f"Skipping invalid lead: {e}")
            
            self.report_progress(f"Found {len(leads)} qualified candidates")
            return leads[:count]
            
        except Exception as e:
            self.report_progress(f"Error processing results: {e}")
            return []
