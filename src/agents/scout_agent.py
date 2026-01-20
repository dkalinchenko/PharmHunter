"""Scout Agent - Discovers potential leads matching search criteria."""

import json
import time
from datetime import datetime
from typing import List, Optional, Callable, Tuple, Dict

from ..models.leads import Lead, LeadProvenanceEmbed
from ..models.pipeline_state import SearchLedger, SourceRecord
from ..prompts.templates import SCOUT_SYSTEM_PROMPT
from ..services.source_config import (
    SourcePriority,
    get_expanded_therapeutic_areas,
    get_expanded_phases,
)
from ..services.company_history_service import CompanyHistoryService
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
                source_url="https://clinicaltrials.gov/example1",
                provenance=LeadProvenanceEmbed(
                    discovered_from_source="ClinicalTrials.gov",
                    source_url="https://clinicaltrials.gov/example1",
                    source_priority=1,
                    search_round=1,
                    search_query="Oncology radiopharma Phase 2 imaging"
                ),
                raw_search_rank=1
            ),
            Lead(
                company_name="NeuroPrecision Bio",
                website="https://neuroprecisionbio.com",
                therapeutic_area="CNS - Neurodegeneration",
                clinical_phase="Phase 2",
                imaging_signal="MRI volumetrics for Alzheimer's trial. Protocol requires central read for hippocampal atrophy.",
                source_url="https://clinicaltrials.gov/example2",
                provenance=LeadProvenanceEmbed(
                    discovered_from_source="ClinicalTrials.gov",
                    source_url="https://clinicaltrials.gov/example2",
                    source_priority=1,
                    search_round=1,
                    search_query="CNS neurodegeneration Phase 2 MRI imaging"
                ),
                raw_search_rank=2
            ),
            Lead(
                company_name="ImmunoPET Sciences",
                website="https://immunopetsciences.com",
                therapeutic_area="Oncology - Immunotherapy",
                clinical_phase="Phase 1/2",
                imaging_signal="PET-based CD8+ T-cell imaging for checkpoint inhibitor trials. First-in-human dosimetry ongoing.",
                source_url="https://clinicaltrials.gov/example3",
                provenance=LeadProvenanceEmbed(
                    discovered_from_source="FierceBiotech",
                    source_url="https://fiercebiotech.com/example3",
                    source_priority=2,
                    search_round=2,
                    search_query="immunotherapy PET imaging Phase 1"
                ),
                raw_search_rank=3
            ),
        ]
        
        self.report_progress(f"Found {len(mock_leads)} candidates")
        return mock_leads[:count]
    
    def execute_with_persistence(
        self,
        count: int = 10,
        focus: str = "Oncology",
        phase: str = "Phase 2",
        geography: str = "Global",
        exclusions: str = "Large Pharma",
        max_rounds: int = 3,
        **kwargs
    ) -> Tuple[List[Lead], SearchLedger]:
        """Mock version that returns both leads and search ledger."""
        leads = self.execute(count, focus, phase, geography, exclusions, **kwargs)
        
        # Create a mock search ledger
        search_ledger = SearchLedger(
            search_rounds=1,
            search_start_time=datetime.now(),
            search_end_time=datetime.now()
        )
        search_ledger.add_source_record(SourceRecord(
            source_name="ClinicalTrials.gov",
            source_priority=1,
            query_text=f"{focus} {phase} imaging clinical trial",
            results_count=len(leads),
            was_successful=True,
            domains_searched=["clinicaltrials.gov"]
        ))
        search_ledger.unique_results_found = len(leads)
        
        return leads, search_ledger


class ScoutAgent(BaseAgent):
    """Production Scout Agent with prioritized source searching and persistence loop."""
    
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
        """Discover leads - wrapper for backward compatibility."""
        leads, _ = self.execute_with_persistence(
            count=count,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions,
            **kwargs
        )
        return leads
    
    def execute_with_persistence(
        self,
        count: int = 10,
        focus: str = "Oncology",
        phase: str = "Phase 2",
        geography: str = "Global",
        exclusions: str = "Large Pharma",
        max_rounds: int = 3,
        **kwargs
    ) -> Tuple[List[Lead], SearchLedger]:
        """
        Execute search with persistence until quota met.
        
        Searches sources in priority order:
        - Round 1: ClinicalTrials.gov only (Priority 1)
        - Round 2: Add biotech aggregators (Priority 2)
        - Round 3: Expand parameters + optional sources (Priority 3)
        
        Returns:
            Tuple of (leads_found, search_ledger)
        """
        self.report_progress(f"Starting persistent search for {count} {focus} companies...")
        
        # Initialize search ledger
        search_ledger = SearchLedger(
            search_start_time=datetime.now()
        )
        
        all_leads: List[Lead] = []
        seen_companies: set = set()
        round_num = 1
        
        while len(all_leads) < count and round_num <= max_rounds:
            self.report_progress(f"Search Round {round_num}/{max_rounds} - Found {len(all_leads)}/{count} leads so far")
            
            # Get leads for this round based on priority
            if round_num == 1:
                round_leads = self._search_priority_1(
                    focus=focus,
                    phase=phase,
                    geography=geography,
                    exclusions=exclusions,
                    count=count,
                    search_ledger=search_ledger,
                    seen_companies=seen_companies
                )
            elif round_num == 2:
                round_leads = self._search_priority_2(
                    focus=focus,
                    phase=phase,
                    geography=geography,
                    exclusions=exclusions,
                    count=count - len(all_leads),
                    search_ledger=search_ledger,
                    seen_companies=seen_companies
                )
            else:
                round_leads = self._search_expanded(
                    focus=focus,
                    phase=phase,
                    geography=geography,
                    exclusions=exclusions,
                    count=count - len(all_leads),
                    search_ledger=search_ledger,
                    seen_companies=seen_companies
                )
            
            # Add new leads, avoiding duplicates
            for lead in round_leads:
                if lead.company_name.lower() not in seen_companies:
                    seen_companies.add(lead.company_name.lower())
                    all_leads.append(lead)
            
            search_ledger.search_rounds = round_num
            
            # Check if we hit quota
            if len(all_leads) >= count:
                self.report_progress(f"Quota reached! Found {len(all_leads)} leads in {round_num} round(s)")
                break
            
            round_num += 1
            
            # Small delay between rounds to avoid rate limiting
            if round_num <= max_rounds:
                time.sleep(1)
        
        # Finalize search ledger
        search_ledger.search_end_time = datetime.now()
        search_ledger.unique_results_found = len(all_leads)
        
        # Filter out duplicates from company history
        self.report_progress("Checking against company history for duplicates...")
        history_service = CompanyHistoryService()
        
        filtered_leads, duplicate_count, duplicate_details = history_service.filter_duplicates(all_leads)
        
        if duplicate_count > 0:
            self.report_progress(f"Filtered out {duplicate_count} companies already in history")
            for dup in duplicate_details[:3]:  # Show first 3 duplicates
                matched_with = dup.get('matched_with', 'batch duplicate')
                score = dup.get('match_score', 100)
                self.report_progress(f"  - Skipped '{dup['company_name']}' (matched '{matched_with}' at {score}%)")
            
            if duplicate_count > 3:
                self.report_progress(f"  - ... and {duplicate_count - 3} more duplicates")
        
        # Store duplicate info in search ledger for transparency
        search_ledger.unique_results_found = len(filtered_leads)
        search_ledger.duplicates_filtered = duplicate_count
        search_ledger.duplicate_details = duplicate_details
        
        self.report_progress(
            f"Search complete: {len(filtered_leads)} new leads from {search_ledger.total_queries} queries "
            f"({duplicate_count} duplicates filtered)"
        )
        
        return filtered_leads[:count], search_ledger
    
    def _search_priority_1(
        self,
        focus: str,
        phase: str,
        geography: str,
        exclusions: str,
        count: int,
        search_ledger: SearchLedger,
        seen_companies: set
    ) -> List[Lead]:
        """
        Search Priority 1 sources: ClinicalTrials.gov only.
        This is the non-negotiable primary source.
        """
        self.report_progress("Priority 1: Searching ClinicalTrials.gov...")
        
        sources = SourcePriority.PRIORITY_1_REQUIRED
        domains = SourcePriority.get_domains_for_priority(1)
        
        # Targeted queries for ClinicalTrials.gov
        queries = [
            f"site:clinicaltrials.gov {focus} {phase} imaging RECIST",
            f"site:clinicaltrials.gov {focus} {phase} PET MRI endpoints",
            f"site:clinicaltrials.gov {focus} clinical trial imaging biomarker",
            f"site:clinicaltrials.gov {focus} {phase} central imaging read",
        ]
        
        return self._execute_search_round(
            queries=queries,
            domains=domains,
            sources=sources,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions,
            count=count,
            search_round=1,
            search_ledger=search_ledger,
            seen_companies=seen_companies
        )
    
    def _search_priority_2(
        self,
        focus: str,
        phase: str,
        geography: str,
        exclusions: str,
        count: int,
        search_ledger: SearchLedger,
        seen_companies: set
    ) -> List[Lead]:
        """
        Search Priority 2 sources: Biotech aggregators and news sites.
        FierceBiotech, BioSpace, Endpoints News, etc.
        """
        self.report_progress("Priority 2: Searching biotech news aggregators...")
        
        sources = SourcePriority.PRIORITY_2_AGGREGATORS
        domains = SourcePriority.get_domains_for_priority(2)
        
        # Queries optimized for news sites
        queries = [
            f"{focus} biotech {phase} trial imaging endpoints",
            f"{focus} biopharma company initiates {phase} imaging",
            f"{focus} clinical trial imaging RECIST PET announcement",
            f"biopharma {focus} first patient dosed imaging trial",
        ]
        
        return self._execute_search_round(
            queries=queries,
            domains=domains,
            sources=sources,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions,
            count=count,
            search_round=2,
            search_ledger=search_ledger,
            seen_companies=seen_companies
        )
    
    def _search_expanded(
        self,
        focus: str,
        phase: str,
        geography: str,
        exclusions: str,
        count: int,
        search_ledger: SearchLedger,
        seen_companies: set
    ) -> List[Lead]:
        """
        Search with expanded parameters and Priority 3 sources.
        Loosen therapeutic area and phase requirements.
        """
        self.report_progress("Priority 3: Expanded search with broader criteria...")
        
        sources = SourcePriority.PRIORITY_3_OPTIONAL
        domains = SourcePriority.get_domains_for_priority(3)
        
        # Get expanded therapeutic areas
        expanded_areas = get_expanded_therapeutic_areas(focus)
        expanded_phases = get_expanded_phases(phase)
        
        queries = []
        
        # Add queries with expanded therapeutic areas
        for area in expanded_areas[:2]:  # Limit to 2 adjacent areas
            queries.append(f"{area} biotech imaging clinical trial {phase}")
        
        # Add queries with expanded phases
        for exp_phase in expanded_phases[:2]:  # Limit to 2 adjacent phases
            queries.append(f"{focus} biopharma {exp_phase} imaging endpoints")
        
        # Add funding-focused queries
        queries.extend([
            f"{focus} biotech Series B funding imaging trial",
            f"{focus} pharmaceutical company IPO clinical imaging",
        ])
        
        return self._execute_search_round(
            queries=queries,
            domains=domains,
            sources=sources,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions,
            count=count,
            search_round=3,
            search_ledger=search_ledger,
            seen_companies=seen_companies
        )
    
    def _execute_search_round(
        self,
        queries: List[str],
        domains: List[str],
        sources: List,
        focus: str,
        phase: str,
        geography: str,
        exclusions: str,
        count: int,
        search_round: int,
        search_ledger: SearchLedger,
        seen_companies: set
    ) -> List[Lead]:
        """Execute a search round and return extracted leads."""
        all_results = []
        seen_urls = set()
        
        for i, query in enumerate(queries):
            self.report_progress(f"  Query {i+1}/{len(queries)}: {query[:50]}...")
            
            # Determine source info for this query
            source_name = sources[0].name if sources else "Unknown"
            source_priority = sources[0].priority if sources else 3
            
            try:
                # Search with domain filtering
                results = self.tavily.search_with_retry(
                    query=query,
                    max_results=max(5, count),
                    max_retries=2
                )
                
                # Record in search ledger
                search_ledger.add_source_record(SourceRecord(
                    source_name=source_name,
                    source_priority=source_priority,
                    query_text=query,
                    results_count=len(results),
                    was_successful=True,
                    domains_searched=domains
                ))
                
                # Deduplicate results
                for r in results:
                    url = r.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        # Tag result with source info
                        r['_source_name'] = self._identify_source(url)
                        r['_source_priority'] = source_priority
                        r['_search_round'] = search_round
                        r['_search_query'] = query
                        r['_rank'] = len(all_results) + 1
                        all_results.append(r)
                
            except Exception as e:
                self.report_progress(f"  Search error: {e}")
                search_ledger.add_source_record(SourceRecord(
                    source_name=source_name,
                    source_priority=source_priority,
                    query_text=query,
                    results_count=0,
                    was_successful=False,
                    error_message=str(e),
                    domains_searched=domains
                ))
            
            # Small delay between queries
            time.sleep(0.5)
        
        if not all_results:
            self.report_progress(f"  No results in this round")
            return []
        
        self.report_progress(f"  Processing {len(all_results)} results with LLM...")
        
        # Use LLM to extract leads from results
        return self._extract_leads_from_results(
            results=all_results,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions,
            count=count,
            search_round=search_round,
            seen_companies=seen_companies
        )
    
    def _identify_source(self, url: str) -> str:
        """Identify which source a URL came from."""
        source_config = SourcePriority.get_source_by_domain(url)
        return source_config.name
    
    def _extract_leads_from_results(
        self,
        results: List[Dict],
        focus: str,
        phase: str,
        geography: str,
        exclusions: str,
        count: int,
        search_round: int,
        seen_companies: set
    ) -> List[Lead]:
        """Use LLM to extract structured leads from search results."""
        
        # Build context from search results
        search_context = "\n\n".join([
            f"[Result #{r.get('_rank', 'N/A')} from {r.get('_source_name', 'Unknown')}]\n"
            f"URL: {r.get('url', 'N/A')}\n"
            f"Title: {r.get('title', 'N/A')}\n"
            f"Content: {r.get('content', 'N/A')[:600]}"
            for r in results[:20]  # Limit context size
        ])
        
        # Build prompt
        prompt = SCOUT_SYSTEM_PROMPT.format(
            count=count,
            focus=focus,
            phase=phase,
            geography=geography,
            exclusions=exclusions
        )
        
        user_prompt = f"""Based on these search results, identify up to {count} biopharma companies.

IMPORTANT: For each company, include the source URL where you found it.

Search Results:
{search_context}

Return ONLY valid JSON - no markdown, no explanation."""
        
        try:
            leads_data = self.deepseek.call_v3_json(
                system_prompt=prompt,
                user_prompt=user_prompt,
                max_retries=2
            )
            
            # Handle both list and dict responses
            if isinstance(leads_data, dict):
                leads_data = leads_data.get("companies", leads_data.get("leads", [leads_data]))
            
            if not isinstance(leads_data, list):
                leads_data = [leads_data]
            
            leads = []
            for i, lead_dict in enumerate(leads_data):
                # Skip if company already seen
                company_name = lead_dict.get("company_name", "")
                if company_name.lower() in seen_companies:
                    continue
                
                try:
                    # Find the source info for this lead
                    source_url = lead_dict.get("source_url", "")
                    source_name = self._identify_source(source_url) if source_url else "Unknown"
                    
                    # Find original result to get metadata
                    source_priority = 2  # Default
                    search_query = ""
                    for r in results:
                        if source_url and source_url in r.get('url', ''):
                            source_priority = r.get('_source_priority', 2)
                            search_query = r.get('_search_query', '')
                            break
                    
                    # Create lead with provenance
                    lead = Lead(
                        company_name=company_name,
                        website=lead_dict.get("website"),
                        therapeutic_area=lead_dict.get("therapeutic_area", focus),
                        clinical_phase=lead_dict.get("clinical_phase", phase),
                        imaging_signal=lead_dict.get("imaging_signal", ""),
                        source_url=source_url,
                        provenance=LeadProvenanceEmbed(
                            discovered_from_source=source_name,
                            source_url=source_url or "unknown",
                            source_priority=source_priority,
                            search_round=search_round,
                            search_query=search_query
                        ),
                        raw_search_rank=i + 1
                    )
                    leads.append(lead)
                    
                except Exception as e:
                    self.report_progress(f"  Skipping invalid lead: {e}")
            
            return leads
            
        except Exception as e:
            self.report_progress(f"  Error extracting leads: {e}")
            return []
