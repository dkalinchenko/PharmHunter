"""Service for managing company history persistence and deduplication with Supabase."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: supabase package not installed. Run: pip install supabase")

from ..models.company_history import CompanyHistory, CompanyRecord, HuntSummary
from ..models.leads import Lead, ScoredLead
from ..utils.fuzzy_matcher import normalize_company_name, find_best_match, DEFAULT_MATCH_THRESHOLD


def get_secret(key: str, default: str = "") -> str:
    """Get a secret from st.secrets or environment variables."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


class CompanyHistoryService:
    """
    Service for managing company history with Supabase persistence.
    
    Handles:
    - Loading/saving history to Supabase PostgreSQL
    - Adding new companies from search results
    - Checking for duplicates with fuzzy matching
    - Exporting history data
    """
    
    def __init__(self, match_threshold: int = DEFAULT_MATCH_THRESHOLD):
        """
        Initialize the history service.
        
        Args:
            match_threshold: Minimum fuzzy match score to consider a duplicate (0-100)
        """
        self.match_threshold = match_threshold
        self._history: Optional[CompanyHistory] = None
        self._supabase: Optional[Client] = None
    
    @property
    def supabase(self) -> Client:
        """Get or create Supabase client."""
        if self._supabase is not None:
            return self._supabase
        
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase package not installed. Run: pip install supabase")
        
        # Get credentials from secrets or environment
        url = get_secret("SUPABASE_URL")
        key = get_secret("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError(
                "Supabase credentials not found. Please add SUPABASE_URL and SUPABASE_KEY "
                "to your .env file or Streamlit secrets."
            )
        
        self._supabase = create_client(url, key)
        return self._supabase
    
    def load_history(self) -> CompanyHistory:
        """
        Load history from Supabase.
        
        Returns:
            CompanyHistory object
        """
        if self._history is not None:
            return self._history
        
        try:
            # Load all companies
            companies_result = self.supabase.table("companies").select("*").execute()
            
            # Convert Supabase records to CompanyRecord objects
            companies = []
            for record in companies_result.data:
                companies.append(CompanyRecord(
                    company_name=record["company_name"],
                    normalized_name=record["normalized_name"],
                    website=record.get("website"),
                    first_seen=record["first_seen"],
                    last_seen=record["last_seen"],
                    times_discovered=record["times_discovered"],
                    hunt_ids=record["hunt_ids"],
                    therapeutic_areas=record["therapeutic_areas"],
                    clinical_phases=record["clinical_phases"],
                    icp_scores=record["icp_scores"],
                    best_score=record.get("best_score"),
                    was_qualified=record["was_qualified"],
                    source_urls=record["source_urls"],
                ))
            
            # Load hunt summaries
            hunts_result = self.supabase.table("hunts").select("*").execute()
            hunt_summary = {}
            for record in hunts_result.data:
                hunt_summary[record["hunt_id"]] = HuntSummary(
                    hunt_id=record["hunt_id"],
                    timestamp=record["timestamp"],
                    companies_found=record["companies_found"],
                    new_companies=record.get("new_companies", 0),
                    duplicates_filtered=record.get("duplicates_filtered", 0),
                    qualified_count=record["qualified_count"],
                    params=record["params"],
                )
            
            # Construct CompanyHistory object
            self._history = CompanyHistory(
                total_companies=len(companies),
                total_hunts=len(hunt_summary),
                companies=companies,
                hunt_summary=hunt_summary,
            )
            
            return self._history
            
        except Exception as e:
            print(f"Warning: Could not load from Supabase: {e}. Creating new history.")
            self._history = CompanyHistory()
            return self._history
    
    def save_history(self, history: Optional[CompanyHistory] = None) -> bool:
        """
        Save history to Supabase.
        
        Note: With Supabase, we typically upsert records individually.
        This method is kept for compatibility but may not be heavily used.
        
        Args:
            history: CompanyHistory to save (uses cached if not provided)
            
        Returns:
            True if successful
        """
        # With Supabase, individual upserts are preferred
        # This method is kept for interface compatibility
        return True
    
    def _upsert_company(self, company: CompanyRecord) -> bool:
        """
        Insert or update a single company in Supabase.
        
        Args:
            company: CompanyRecord to upsert
            
        Returns:
            True if successful
        """
        try:
            data = {
                "company_name": company.company_name,
                "normalized_name": company.normalized_name,
                "website": company.website,
                "first_seen": company.first_seen.isoformat(),
                "last_seen": company.last_seen.isoformat(),
                "times_discovered": company.times_discovered,
                "hunt_ids": company.hunt_ids,
                "therapeutic_areas": company.therapeutic_areas,
                "clinical_phases": company.clinical_phases,
                "icp_scores": company.icp_scores,
                "best_score": company.best_score,
                "was_qualified": company.was_qualified,
                "source_urls": company.source_urls,
            }
            
            # Upsert based on normalized_name (unique constraint)
            self.supabase.table("companies").upsert(
                data,
                on_conflict="normalized_name"
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error upserting company {company.company_name}: {e}")
            return False
    
    def is_duplicate(
        self,
        company_name: str
    ) -> Tuple[bool, Optional[CompanyRecord], int]:
        """
        Check if a company is a duplicate in history.
        
        Args:
            company_name: Name of company to check
            
        Returns:
            Tuple of (is_duplicate, matching_record, match_score)
        """
        history = self.load_history()
        
        if not history.companies:
            return False, None, 0
        
        best_match, score = find_best_match(
            company_name,
            history.companies,
            threshold=self.match_threshold
        )
        
        is_dup = best_match is not None and score >= self.match_threshold
        
        return is_dup, best_match, score
    
    def filter_duplicates(
        self,
        leads: List[Lead]
    ) -> Tuple[List[Lead], int, List[Dict[str, Any]]]:
        """
        Filter out duplicate leads from a list.
        
        Args:
            leads: List of Lead objects to filter
            
        Returns:
            Tuple of (filtered_leads, duplicate_count, duplicate_details)
        """
        history = self.load_history()
        
        filtered_leads: List[Lead] = []
        duplicates: List[Dict[str, Any]] = []
        seen_in_batch: set = set()
        
        for lead in leads:
            # Normalize for batch dedup
            normalized = normalize_company_name(lead.company_name)
            
            # Check if already seen in this batch
            if normalized in seen_in_batch:
                duplicates.append({
                    "company_name": lead.company_name,
                    "reason": "duplicate_in_batch",
                    "match_score": 100
                })
                continue
            
            # Check against history
            is_dup, existing, score = self.is_duplicate(lead.company_name)
            
            if is_dup and existing:
                duplicates.append({
                    "company_name": lead.company_name,
                    "matched_with": existing.company_name,
                    "reason": "found_in_history",
                    "match_score": score,
                    "last_seen": existing.last_seen.isoformat() if existing.last_seen else None,
                    "times_discovered": existing.times_discovered
                })
            else:
                filtered_leads.append(lead)
                seen_in_batch.add(normalized)
        
        return filtered_leads, len(duplicates), duplicates
    
    def add_companies(
        self,
        leads: List[ScoredLead],
        hunt_id: str,
        hunt_params: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add companies from scored leads to Supabase.
        
        Args:
            leads: List of ScoredLead objects
            hunt_id: ID of the hunt these leads came from
            hunt_params: Search parameters used for the hunt
            
        Returns:
            Number of new companies added
        """
        history = self.load_history()
        new_count = 0
        qualified_count = 0
        
        for lead in leads:
            normalized = normalize_company_name(lead.company_name)
            
            # Check if company already exists in loaded history
            existing = history.get_company_by_normalized_name(normalized)
            
            if existing:
                # Update existing record
                existing.update_from_lead(lead, hunt_id)
                self._upsert_company(existing)
            else:
                # Create new record
                new_record = CompanyRecord(
                    company_name=lead.company_name,
                    normalized_name=normalized,
                    website=lead.website,
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                    times_discovered=1,
                    hunt_ids=[hunt_id],
                    therapeutic_areas=[lead.therapeutic_area] if lead.therapeutic_area else [],
                    clinical_phases=[lead.clinical_phase] if lead.clinical_phase else [],
                    icp_scores=[lead.icp_score] if lead.icp_score else [],
                    best_score=lead.icp_score,
                    was_qualified=lead.is_qualified if hasattr(lead, 'is_qualified') else False,
                    source_urls=[lead.source_url] if lead.source_url else []
                )
                self._upsert_company(new_record)
                new_count += 1
            
            if hasattr(lead, 'is_qualified') and lead.is_qualified:
                qualified_count += 1
        
        # Add hunt summary to Supabase
        try:
            hunt_data = {
                "hunt_id": hunt_id,
                "timestamp": datetime.now().isoformat(),
                "companies_found": len(leads),
                "new_companies": new_count,
                "duplicates_filtered": 0,  # Will be updated by caller if needed
                "qualified_count": qualified_count,
                "params": hunt_params or {},
            }
            
            self.supabase.table("hunts").upsert(
                hunt_data,
                on_conflict="hunt_id"
            ).execute()
        except Exception as e:
            print(f"Error saving hunt summary: {e}")
        
        # Clear cache to force reload on next access
        self._history = None
        
        return new_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics from history.
        
        Returns:
            Dictionary of statistics
        """
        history = self.load_history()
        return history.get_statistics()
    
    def export_json(self) -> str:
        """
        Export history as JSON string.
        
        Returns:
            JSON string of full history
        """
        history = self.load_history()
        return json.dumps(
            history.model_dump(mode='json'),
            indent=2,
            default=str
        )
    
    def get_all_companies(self) -> List[CompanyRecord]:
        """
        Get all companies in history.
        
        Returns:
            List of CompanyRecord objects
        """
        history = self.load_history()
        return history.companies
    
    def get_company_count(self) -> int:
        """Get total number of companies in history."""
        history = self.load_history()
        return history.total_companies
    
    def get_hunt_count(self) -> int:
        """Get total number of hunts executed."""
        history = self.load_history()
        return history.total_hunts
    
    def clear_cache(self):
        """Clear the cached history (forces reload on next access)."""
        self._history = None
