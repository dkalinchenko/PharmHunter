"""Prioritized source configuration for lead discovery."""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class SourceConfig:
    """Configuration for a single source."""
    name: str
    domains: List[str]
    priority: int  # 1=primary, 2=secondary, 3=tertiary
    weight: float  # Relevance weight for scoring
    description: str


class SourcePriority:
    """Stack-ranked source configuration for lead discovery.
    
    Sources are searched in priority order:
    - Priority 1 (Required): Always searched first - ClinicalTrials.gov
    - Priority 2 (Aggregators): Biotech news/blog sites
    - Priority 3 (Optional): Funding/business databases
    """
    
    # Priority 1: Required - The non-negotiable primary source
    PRIORITY_1_REQUIRED = [
        SourceConfig(
            name="ClinicalTrials.gov",
            domains=["clinicaltrials.gov"],
            priority=1,
            weight=1.0,
            description="Official clinical trial registry - primary source for trial data"
        ),
    ]
    
    # Priority 2: Aggregators - Biotech news and blogs
    PRIORITY_2_AGGREGATORS = [
        SourceConfig(
            name="FierceBiotech",
            domains=["fiercebiotech.com"],
            priority=2,
            weight=0.85,
            description="Leading biotech industry news"
        ),
        SourceConfig(
            name="BioSpace",
            domains=["biospace.com"],
            priority=2,
            weight=0.80,
            description="Biotech and pharma news aggregator"
        ),
        SourceConfig(
            name="GenEngNews",
            domains=["genengnews.com"],
            priority=2,
            weight=0.75,
            description="Genetic engineering and biotech news"
        ),
        SourceConfig(
            name="BioPharma Dive",
            domains=["biopharmadive.com"],
            priority=2,
            weight=0.75,
            description="Biopharma industry news and analysis"
        ),
        SourceConfig(
            name="Endpoints News",
            domains=["endpts.com"],
            priority=2,
            weight=0.80,
            description="Biotech endpoints and trial news"
        ),
    ]
    
    # Priority 3: Optional - Business/funding databases
    PRIORITY_3_OPTIONAL = [
        SourceConfig(
            name="PitchBook",
            domains=["pitchbook.com"],
            priority=3,
            weight=0.60,
            description="Private market data and funding info"
        ),
        SourceConfig(
            name="Evaluate Pharma",
            domains=["evaluate.com"],
            priority=3,
            weight=0.60,
            description="Pharma market intelligence"
        ),
        SourceConfig(
            name="SEC Filings",
            domains=["sec.gov"],
            priority=3,
            weight=0.55,
            description="Public company filings"
        ),
        SourceConfig(
            name="BusinessWire",
            domains=["businesswire.com"],
            priority=3,
            weight=0.50,
            description="Press release distribution"
        ),
        SourceConfig(
            name="PR Newswire",
            domains=["prnewswire.com"],
            priority=3,
            weight=0.50,
            description="Press release distribution"
        ),
    ]
    
    @classmethod
    def get_all_sources(cls) -> List[SourceConfig]:
        """Get all sources in priority order."""
        return cls.PRIORITY_1_REQUIRED + cls.PRIORITY_2_AGGREGATORS + cls.PRIORITY_3_OPTIONAL
    
    @classmethod
    def get_sources_by_priority(cls, priority: int) -> List[SourceConfig]:
        """Get sources for a specific priority level."""
        if priority == 1:
            return cls.PRIORITY_1_REQUIRED
        elif priority == 2:
            return cls.PRIORITY_2_AGGREGATORS
        elif priority == 3:
            return cls.PRIORITY_3_OPTIONAL
        return []
    
    @classmethod
    def get_domains_for_priority(cls, max_priority: int) -> List[str]:
        """Get all domains up to and including the specified priority level."""
        domains = []
        for p in range(1, max_priority + 1):
            for source in cls.get_sources_by_priority(p):
                domains.extend(source.domains)
        return domains
    
    @classmethod
    def get_source_by_domain(cls, domain: str) -> SourceConfig:
        """Find a source config by domain."""
        for source in cls.get_all_sources():
            if domain in source.domains or any(d in domain for d in source.domains):
                return source
        # Return a generic source if not found
        return SourceConfig(
            name="Unknown",
            domains=[domain],
            priority=3,
            weight=0.4,
            description="Unknown source"
        )


# Therapeutic area expansion mappings for persistence loop
THERAPEUTIC_ADJACENCIES = {
    "Oncology": ["Immunotherapy", "Radiopharma", "Hematology", "Solid Tumors"],
    "Radiopharma": ["Oncology", "Nuclear Medicine", "Theranostics", "PET Imaging"],
    "CNS": ["Neurology", "Neurodegeneration", "Psychiatry", "Brain Imaging"],
    "Immunotherapy": ["Oncology", "Autoimmune", "Cell Therapy", "Biologics"],
    "Cardiology": ["Cardiovascular", "Heart Failure", "Cardiac Imaging"],
}

# Phase expansion for persistence loop
PHASE_EXPANSIONS = {
    "Phase 2": ["Phase 1/2", "Phase 2/3", "Late Phase 1"],
    "Phase 1": ["Phase 1/2", "Preclinical", "IND-enabling"],
    "Phase 3": ["Phase 2/3", "Pivotal", "Registration"],
}


def get_expanded_therapeutic_areas(focus: str) -> List[str]:
    """Get related therapeutic areas for expanded searching."""
    focus_lower = focus.lower()
    for key, adjacencies in THERAPEUTIC_ADJACENCIES.items():
        if key.lower() in focus_lower:
            return adjacencies
    return []


def get_expanded_phases(phase: str) -> List[str]:
    """Get related phases for expanded searching."""
    for key, expansions in PHASE_EXPANSIONS.items():
        if key.lower() in phase.lower():
            return expansions
    return []
