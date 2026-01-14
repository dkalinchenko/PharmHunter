"""Pydantic models for lead data structures."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Lead(BaseModel):
    """Raw lead discovered by the Scout agent."""
    
    company_name: str = Field(..., description="Name of the biopharma company")
    website: Optional[str] = Field(None, description="Company website URL")
    therapeutic_area: str = Field(..., description="Primary therapeutic focus area")
    clinical_phase: str = Field(..., description="Current clinical trial phase")
    imaging_signal: str = Field(
        ..., 
        description="Why they were picked (e.g., 'PET dosimetry mentioned')"
    )
    source_url: Optional[str] = Field(None, description="Source URL for this lead")


class ScoredLead(Lead):
    """Lead after ICP scoring by the Analyst agent."""
    
    icp_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="ICP fit score from 0-100"
    )
    is_qualified: bool = Field(
        ..., 
        description="Whether lead meets qualification threshold (score >= 75)"
    )
    disqualification_reason: Optional[str] = Field(
        None, 
        description="Reason for disqualification if score < 75"
    )
    buying_signal: str = Field(
        ..., 
        description="The specific 'Why Now' trigger for outreach"
    )
    recommended_offer: str = Field(
        ..., 
        description="Best consulting offer to pitch"
    )
    reasoning_chain: str = Field(
        default="", 
        description="Chain-of-thought reasoning from the Analyst"
    )


class DraftedLead(ScoredLead):
    """Fully processed lead with draft outreach from the Scribe agent."""
    
    contact_persona: str = Field(
        ..., 
        description="Target persona type (e.g., 'VP of Clinical Ops')"
    )
    contact_name: Optional[str] = Field(
        None, 
        description="Actual contact name if found"
    )
    contact_title: Optional[str] = Field(
        None, 
        description="Contact's job title"
    )
    contact_linkedin: Optional[str] = Field(
        None, 
        description="LinkedIn profile URL"
    )
    email_subject_options: List[str] = Field(
        default_factory=list, 
        description="6 subject line options"
    )
    email_body_primary: str = Field(
        ..., 
        description="Primary email body (120-180 words)"
    )
    email_variant_1: str = Field(
        default="", 
        description="Variant 1: De-risk proof-of-concept angle"
    )
    email_variant_2: str = Field(
        default="", 
        description="Variant 2: Scale-up execution angle"
    )
    linkedin_message: str = Field(
        ..., 
        description="Short LinkedIn message (max 350 chars)"
    )
    follow_up_email: str = Field(
        default="", 
        description="Follow-up email for 5-7 days later"
    )
