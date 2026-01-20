"""Pipeline state tracking models for transparency and debugging."""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


class SourceRecord(BaseModel):
    """Tracks which source was queried and results."""
    
    source_name: str = Field(..., description="Name of source (e.g., 'ClinicalTrials.gov')")
    source_priority: int = Field(..., ge=1, le=3, description="Priority level: 1=primary, 2=secondary, 3=tertiary")
    query_text: str = Field(..., description="The actual search query used")
    query_url: Optional[str] = Field(None, description="URL queried if applicable")
    query_timestamp: datetime = Field(default_factory=datetime.now)
    results_count: int = Field(0, description="Number of results returned")
    was_successful: bool = Field(True, description="Whether the query succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    domains_searched: List[str] = Field(default_factory=list, description="Domains included in search")


class SearchLedger(BaseModel):
    """Complete record of all searches performed during a hunt."""
    
    search_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sources_queried: List[SourceRecord] = Field(default_factory=list)
    total_queries: int = Field(0, description="Total number of queries executed")
    total_results_found: int = Field(0, description="Total raw results before deduplication")
    unique_results_found: int = Field(0, description="Results after deduplication")
    search_rounds: int = Field(0, description="How many persistence loop iterations")
    search_start_time: Optional[datetime] = Field(None)
    search_end_time: Optional[datetime] = Field(None)
    
    # Duplicate tracking from Company History
    duplicates_filtered: int = Field(0, description="Companies filtered as already in history")
    duplicate_details: List[Dict] = Field(default_factory=list, description="Details of each filtered duplicate")
    
    def add_source_record(self, record: SourceRecord):
        """Add a source record and update totals."""
        self.sources_queried.append(record)
        self.total_queries += 1
        self.total_results_found += record.results_count
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate search duration in seconds."""
        if self.search_start_time and self.search_end_time:
            return (self.search_end_time - self.search_start_time).total_seconds()
        return None


class LeadProvenance(BaseModel):
    """Tracks exactly where a lead came from."""
    
    discovered_from_source: str = Field(..., description="Which source found this lead")
    source_url: str = Field(..., description="Specific URL where lead was found")
    source_priority: int = Field(1, description="Priority level of the source")
    discovery_timestamp: datetime = Field(default_factory=datetime.now)
    search_round: int = Field(1, description="Which iteration of persistence loop")
    search_query: Optional[str] = Field(None, description="The query that found this lead")


class StageData(BaseModel):
    """Data payload for a single pipeline stage."""
    
    stage_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    input_count: int = Field(0)
    output_count: int = Field(0)
    duration_seconds: Optional[float] = None
    details: Dict = Field(default_factory=dict)


class PipelineState(BaseModel):
    """Tracks complete pipeline execution state for Glass Box transparency."""
    
    hunt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hunt_params: Dict = Field(default_factory=dict, description="Original search parameters")
    
    # Search tracking
    search_ledger: Optional[SearchLedger] = None
    
    # Top of funnel (before filtering)
    top_of_funnel_count: int = Field(0)
    top_of_funnel_companies: List[str] = Field(default_factory=list)
    
    # Duplicate tracking (Company History integration)
    duplicates_filtered: int = Field(0, description="Companies filtered as duplicates from history")
    new_companies_found: int = Field(0, description="Companies not previously in history")
    duplicate_details: List[Dict] = Field(default_factory=list, description="Details of filtered duplicates")
    
    # Post-scoring
    scored_count: int = Field(0)
    qualified_count: int = Field(0)
    disqualified_count: int = Field(0)
    
    # Final output
    drafted_count: int = Field(0)
    
    # Stage timestamps
    stage_timestamps: Dict[str, datetime] = Field(default_factory=dict)
    stage_data: List[StageData] = Field(default_factory=list)
    
    # Errors
    errors: List[str] = Field(default_factory=list)
    
    def record_stage_start(self, stage_name: str):
        """Record when a stage starts."""
        self.stage_timestamps[f"{stage_name}_start"] = datetime.now()
    
    def record_stage_complete(self, stage_name: str, input_count: int = 0, output_count: int = 0, details: Dict = None):
        """Record when a stage completes with data."""
        end_time = datetime.now()
        self.stage_timestamps[f"{stage_name}_complete"] = end_time
        
        start_time = self.stage_timestamps.get(f"{stage_name}_start")
        duration = (end_time - start_time).total_seconds() if start_time else None
        
        self.stage_data.append(StageData(
            stage_name=stage_name,
            timestamp=end_time,
            input_count=input_count,
            output_count=output_count,
            duration_seconds=duration,
            details=details or {}
        ))
    
    def add_error(self, error_message: str):
        """Record an error."""
        self.errors.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_message}")
