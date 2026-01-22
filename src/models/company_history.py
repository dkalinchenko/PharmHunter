"""Company history models for tracking discovered companies across hunts."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HuntEncounter(BaseModel):
    """Details of a single encounter with a company in a hunt."""
    
    hunt_id: str = Field(..., description="ID of the hunt where encountered")
    timestamp: datetime = Field(default_factory=datetime.now, description="When encountered")
    
    # Basic lead info (FROM LEAD MODEL)
    therapeutic_area: Optional[str] = Field(None, description="Therapeutic area from this hunt")
    clinical_phase: Optional[str] = Field(None, description="Clinical phase from this hunt")
    imaging_signal: Optional[str] = Field(None, description="Why company was picked")
    source_url: Optional[str] = Field(None, description="Source URL from this hunt")
    
    # Scoring details (FROM SCOREDLEAD MODEL)
    icp_score: Optional[int] = Field(None, description="ICP score from this hunt")
    score_breakdown: Optional[Dict[str, int]] = Field(None, description="Detailed score breakdown")
    score_explanation: Optional[str] = Field(None, description="Why this score was given")
    is_qualified: bool = Field(False, description="Whether qualified in this hunt")
    disqualification_reason: Optional[str] = Field(None, description="Why rejected if not qualified")
    buying_signal: Optional[str] = Field(None, description="The 'Why Now' trigger")
    recommended_offer: Optional[str] = Field(None, description="Best consulting offer")
    reasoning_chain: Optional[str] = Field(None, description="Full chain-of-thought analysis")
    scoring_timestamp: Optional[datetime] = Field(None, description="When scored")
    
    # Contact info (FROM DRAFTEDLEAD MODEL)
    contact_persona: Optional[str] = Field(None, description="Target persona type")
    contact_name: Optional[str] = Field(None, description="Actual contact name")
    contact_title: Optional[str] = Field(None, description="Contact job title")
    contact_linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    
    # Drafted messages (FROM DRAFTEDLEAD MODEL) - EXPANDED
    email_subject_options: Optional[List[str]] = Field(None, description="All 6 subject line variants")
    email_body_primary: Optional[str] = Field(None, description="Primary email (120-180 words)")
    email_variant_1: Optional[str] = Field(None, description="Variant 1: De-risk POC angle")
    email_variant_2: Optional[str] = Field(None, description="Variant 2: Scale-up angle")
    linkedin_message: Optional[str] = Field(None, description="LinkedIn message (350 chars)")
    follow_up_email: Optional[str] = Field(None, description="Follow-up for 5-7 days later")
    personalization_notes: Optional[str] = Field(None, description="Personalization rationale")
    
    # Provenance (FROM LEAD MODEL)
    discovery_source: Optional[str] = Field(None, description="Where discovered")
    source_priority: Optional[str] = Field(None, description="Source priority tier")
    search_round: Optional[int] = Field(None, description="Which search round")
    raw_search_rank: Optional[int] = Field(None, description="Position in search results")


class CompanyRecord(BaseModel):
    """Record of a company in history."""
    
    company_name: str = Field(..., description="Original company name")
    normalized_name: str = Field(..., description="Normalized name for matching (lowercase, no suffixes)")
    website: Optional[str] = Field(None, description="Company website URL")
    first_seen: datetime = Field(default_factory=datetime.now, description="When first discovered")
    last_seen: datetime = Field(default_factory=datetime.now, description="When last discovered")
    times_discovered: int = Field(1, description="Number of times found in searches")
    hunt_ids: List[str] = Field(default_factory=list, description="IDs of hunts where discovered")
    therapeutic_areas: List[str] = Field(default_factory=list, description="All therapeutic areas seen")
    clinical_phases: List[str] = Field(default_factory=list, description="All clinical phases seen")
    icp_scores: List[int] = Field(default_factory=list, description="All ICP scores received")
    best_score: Optional[int] = Field(None, description="Highest ICP score achieved")
    was_qualified: bool = Field(False, description="Whether ever qualified (score >= 75)")
    source_urls: List[str] = Field(default_factory=list, description="Source URLs where found")
    
    # NEW: Detailed encounter history
    encounters: List[HuntEncounter] = Field(default_factory=list, description="Detailed history of each encounter")
    
    def update_from_lead(self, lead: Any, hunt_id: str):
        """Update record with data from a new lead discovery."""
        self.last_seen = datetime.now()
        self.times_discovered += 1
        
        if hunt_id not in self.hunt_ids:
            self.hunt_ids.append(hunt_id)
        
        # Add therapeutic area if new
        if hasattr(lead, 'therapeutic_area') and lead.therapeutic_area:
            if lead.therapeutic_area not in self.therapeutic_areas:
                self.therapeutic_areas.append(lead.therapeutic_area)
        
        # Add clinical phase if new
        if hasattr(lead, 'clinical_phase') and lead.clinical_phase:
            if lead.clinical_phase not in self.clinical_phases:
                self.clinical_phases.append(lead.clinical_phase)
        
        # Add source URL if new
        if hasattr(lead, 'source_url') and lead.source_url:
            if lead.source_url not in self.source_urls:
                self.source_urls.append(lead.source_url)
        
        # Update scores if this is a ScoredLead
        if hasattr(lead, 'icp_score') and lead.icp_score is not None:
            self.icp_scores.append(lead.icp_score)
            if self.best_score is None or lead.icp_score > self.best_score:
                self.best_score = lead.icp_score
            
            if hasattr(lead, 'is_qualified') and lead.is_qualified:
                self.was_qualified = True
        
        # Update website if we have a better one
        if hasattr(lead, 'website') and lead.website and not self.website:
            self.website = lead.website
    
    def add_encounter(self, lead: Any, hunt_id: str):
        """Add a detailed encounter record from a drafted lead."""
        encounter = HuntEncounter(
            hunt_id=hunt_id,
            timestamp=datetime.now(),
        )
        
        # Basic lead info
        if hasattr(lead, 'therapeutic_area'):
            encounter.therapeutic_area = lead.therapeutic_area
        if hasattr(lead, 'clinical_phase'):
            encounter.clinical_phase = lead.clinical_phase
        if hasattr(lead, 'imaging_signal'):
            encounter.imaging_signal = lead.imaging_signal
        if hasattr(lead, 'source_url'):
            encounter.source_url = lead.source_url
        
        # Scoring details
        if hasattr(lead, 'icp_score'):
            encounter.icp_score = lead.icp_score
        if hasattr(lead, 'score_breakdown'):
            encounter.score_breakdown = lead.score_breakdown
        if hasattr(lead, 'score_explanation'):
            encounter.score_explanation = lead.score_explanation
        if hasattr(lead, 'is_qualified'):
            encounter.is_qualified = lead.is_qualified
        if hasattr(lead, 'disqualification_reason'):
            encounter.disqualification_reason = lead.disqualification_reason
        if hasattr(lead, 'buying_signal'):
            encounter.buying_signal = lead.buying_signal
        if hasattr(lead, 'recommended_offer'):
            encounter.recommended_offer = lead.recommended_offer
        if hasattr(lead, 'reasoning_chain'):
            encounter.reasoning_chain = lead.reasoning_chain
        if hasattr(lead, 'scoring_timestamp'):
            encounter.scoring_timestamp = lead.scoring_timestamp
        
        # Contact info
        if hasattr(lead, 'contact_persona'):
            encounter.contact_persona = lead.contact_persona
        if hasattr(lead, 'contact_name'):
            encounter.contact_name = lead.contact_name
        if hasattr(lead, 'contact_title'):
            encounter.contact_title = lead.contact_title
        if hasattr(lead, 'contact_linkedin'):
            encounter.contact_linkedin = lead.contact_linkedin
        
        # Drafted messages
        if hasattr(lead, 'email_subject_options'):
            encounter.email_subject_options = lead.email_subject_options
        if hasattr(lead, 'email_body_primary'):
            encounter.email_body_primary = lead.email_body_primary
        if hasattr(lead, 'email_variant_1'):
            encounter.email_variant_1 = lead.email_variant_1
        if hasattr(lead, 'email_variant_2'):
            encounter.email_variant_2 = lead.email_variant_2
        if hasattr(lead, 'linkedin_message'):
            encounter.linkedin_message = lead.linkedin_message
        if hasattr(lead, 'follow_up_email'):
            encounter.follow_up_email = lead.follow_up_email
        if hasattr(lead, 'personalization_notes'):
            encounter.personalization_notes = lead.personalization_notes
        
        # Provenance
        if hasattr(lead, 'provenance') and lead.provenance:
            encounter.discovery_source = lead.provenance.discovery_source
            encounter.source_priority = lead.provenance.source_priority
            encounter.search_round = lead.provenance.search_round
        if hasattr(lead, 'raw_search_rank'):
            encounter.raw_search_rank = lead.raw_search_rank
        
        self.encounters.append(encounter)


class HuntSummary(BaseModel):
    """Summary of a single hunt."""
    
    hunt_id: str = Field(..., description="Unique hunt identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When hunt was executed")
    companies_found: int = Field(0, description="Total companies discovered")
    new_companies: int = Field(0, description="Companies not seen before")
    duplicates_filtered: int = Field(0, description="Companies filtered as duplicates")
    qualified_count: int = Field(0, description="Companies that qualified")
    params: Dict[str, Any] = Field(default_factory=dict, description="Search parameters used")


class CompanyHistory(BaseModel):
    """Complete company history database."""
    
    version: str = Field("1.0", description="Schema version")
    created_at: datetime = Field(default_factory=datetime.now, description="When history was created")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last modification time")
    total_companies: int = Field(0, description="Total unique companies")
    total_hunts: int = Field(0, description="Total hunts executed")
    companies: List[CompanyRecord] = Field(default_factory=list, description="All company records")
    hunt_summary: Dict[str, HuntSummary] = Field(default_factory=dict, description="Summary of each hunt")
    
    def get_company_by_normalized_name(self, normalized_name: str) -> Optional[CompanyRecord]:
        """Find a company by its normalized name."""
        for company in self.companies:
            if company.normalized_name == normalized_name:
                return company
        return None
    
    def add_or_update_company(self, company_record: CompanyRecord):
        """Add a new company or update existing one."""
        existing = self.get_company_by_normalized_name(company_record.normalized_name)
        if existing:
            # Update existing record
            idx = self.companies.index(existing)
            self.companies[idx] = company_record
        else:
            # Add new company
            self.companies.append(company_record)
            self.total_companies = len(self.companies)
        
        self.last_updated = datetime.now()
    
    def add_hunt_summary(self, summary: HuntSummary):
        """Add a hunt summary."""
        self.hunt_summary[summary.hunt_id] = summary
        self.total_hunts = len(self.hunt_summary)
        self.last_updated = datetime.now()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        qualified_companies = sum(1 for c in self.companies if c.was_qualified)
        total_scores = [c.best_score for c in self.companies if c.best_score is not None]
        avg_best_score = sum(total_scores) / len(total_scores) if total_scores else 0
        
        # Get therapeutic area distribution
        area_counts: Dict[str, int] = {}
        for company in self.companies:
            for area in company.therapeutic_areas:
                area_counts[area] = area_counts.get(area, 0) + 1
        
        return {
            "total_companies": self.total_companies,
            "total_hunts": self.total_hunts,
            "qualified_companies": qualified_companies,
            "disqualified_companies": self.total_companies - qualified_companies,
            "average_best_score": round(avg_best_score, 1),
            "therapeutic_area_distribution": area_counts,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }
