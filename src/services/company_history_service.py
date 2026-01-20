"""Service for managing company history persistence and deduplication."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..models.company_history import CompanyHistory, CompanyRecord, HuntSummary
from ..models.leads import Lead, ScoredLead
from ..utils.fuzzy_matcher import normalize_company_name, find_best_match, DEFAULT_MATCH_THRESHOLD


class CompanyHistoryService:
    """
    Service for managing company history with file-based persistence.
    
    Handles:
    - Loading/saving history to JSON file
    - Adding new companies from search results
    - Checking for duplicates with fuzzy matching
    - Exporting history data
    """
    
    # Default storage locations
    PRIMARY_STORAGE_DIR = Path.home() / ".pharmhunter"
    FALLBACK_STORAGE_DIR = Path("./data")
    HISTORY_FILENAME = "company_history.json"
    
    def __init__(self, match_threshold: int = DEFAULT_MATCH_THRESHOLD):
        """
        Initialize the history service.
        
        Args:
            match_threshold: Minimum fuzzy match score to consider a duplicate (0-100)
        """
        self.match_threshold = match_threshold
        self._history: Optional[CompanyHistory] = None
        self._storage_path: Optional[Path] = None
    
    @property
    def storage_path(self) -> Path:
        """Get the path to the history file, creating directory if needed."""
        if self._storage_path is not None:
            return self._storage_path
        
        # Try primary location first (home directory)
        try:
            self.PRIMARY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            self._storage_path = self.PRIMARY_STORAGE_DIR / self.HISTORY_FILENAME
            return self._storage_path
        except (PermissionError, OSError):
            pass
        
        # Fall back to app directory
        try:
            self.FALLBACK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            self._storage_path = self.FALLBACK_STORAGE_DIR / self.HISTORY_FILENAME
            return self._storage_path
        except (PermissionError, OSError):
            # Last resort: current directory
            self._storage_path = Path(self.HISTORY_FILENAME)
            return self._storage_path
    
    def load_history(self) -> CompanyHistory:
        """
        Load history from disk, creating new if not exists.
        
        Returns:
            CompanyHistory object
        """
        if self._history is not None:
            return self._history
        
        path = self.storage_path
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._history = CompanyHistory.model_validate(data)
                return self._history
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Could not load history file: {e}. Creating new history.")
        
        # Create new history
        self._history = CompanyHistory()
        return self._history
    
    def save_history(self, history: Optional[CompanyHistory] = None) -> bool:
        """
        Save history to disk.
        
        Args:
            history: CompanyHistory to save (uses cached if not provided)
            
        Returns:
            True if successful
        """
        if history is not None:
            self._history = history
        
        if self._history is None:
            return False
        
        self._history.last_updated = datetime.now()
        
        try:
            path = self.storage_path
            
            # Write to temp file first, then rename (atomic operation)
            temp_path = path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self._history.model_dump(mode='json'),
                    f,
                    indent=2,
                    default=str
                )
            
            # Rename temp to final
            temp_path.replace(path)
            return True
            
        except Exception as e:
            print(f"Error saving history: {e}")
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
        Add companies from scored leads to history.
        
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
            
            # Check if company already exists
            existing = history.get_company_by_normalized_name(normalized)
            
            if existing:
                # Update existing record
                existing.update_from_lead(lead, hunt_id)
                history.add_or_update_company(existing)
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
                history.add_or_update_company(new_record)
                new_count += 1
            
            if hasattr(lead, 'is_qualified') and lead.is_qualified:
                qualified_count += 1
        
        # Add hunt summary
        hunt_summary = HuntSummary(
            hunt_id=hunt_id,
            timestamp=datetime.now(),
            companies_found=len(leads),
            new_companies=new_count,
            duplicates_filtered=0,  # Will be set by caller if needed
            qualified_count=qualified_count,
            params=hunt_params or {}
        )
        history.add_hunt_summary(hunt_summary)
        
        # Save to disk
        self.save_history(history)
        
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
