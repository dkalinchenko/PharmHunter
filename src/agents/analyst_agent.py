"""Analyst Agent - Scores and qualifies leads against ICP criteria."""

import json
import time
from datetime import datetime
from typing import List, Optional, Callable, Dict

from ..models.leads import Lead, ScoredLead
from ..prompts.templates import ANALYST_SYSTEM_PROMPT
from .base_agent import BaseAgent


# Enhanced prompt for scoring with breakdown
ANALYST_SCORING_PROMPT = """You are a critical deal qualifier analyzing biopharma companies for ICP fit.

COMPANY TO ANALYZE:
- Name: {company_name}
- Website: {website}
- Therapeutic Area: {therapeutic_area}
- Clinical Phase: {clinical_phase}
- Imaging Signal: {imaging_signal}

ICP CRITERIA:
{icp_definition}

YOUR TASK:
1. Verify 'Must-Have' criteria (Biopharma, Phase 2+, Imaging Materiality)
2. Find a specific 'Why Now' trigger (Trial timeline, Funding, Org change)
3. Calculate a detailed score breakdown
4. Provide clear reasoning for each score component

SCORING FRAMEWORK:
- base_company_fit: 0-40 points (Is it a biopharma? Right therapeutic area?)
- phase_match: 0-20 points (Phase 2/3 gets full points, Phase 1 gets partial)
- imaging_materiality: 0-20 points (How critical is imaging to their trial?)
- why_now_trigger: 0-15 points (Is there a clear timing signal?)
- complexity_bonus: 0-5 points (Multi-site, multi-region, specialty imaging)

RETURN JSON FORMAT (ONLY JSON, no markdown):
{{
    "icp_score": <total 0-100>,
    "score_breakdown": {{
        "base_company_fit": <0-40>,
        "phase_match": <0-20>,
        "imaging_materiality": <0-20>,
        "why_now_trigger": <0-15>,
        "complexity_bonus": <0-5>
    }},
    "score_explanation": "<One sentence per score component explaining points given>",
    "is_qualified": <true if score >= 75>,
    "disqualification_reason": "<If not qualified, explain why>",
    "buying_signal": "<The specific Why Now trigger for outreach>",
    "recommended_offer": "<Best offer: 'Imaging Readiness Sprint', 'Imaging Charter Fast-Track', or 'End-to-End Imaging Management'>",
    "reasoning_chain": "<Full Chain-of-Thought analysis>"
}}"""


class MockAnalystAgent(BaseAgent):
    """Mock Analyst Agent for UI testing without API calls."""
    
    def execute(
        self,
        leads: List[Lead],
        icp_definition: str = "",
        **kwargs
    ) -> List[ScoredLead]:
        """Return mock scored leads for testing."""
        self.report_progress(f"Scoring {len(leads)} leads...")
        
        mock_scores = [
            {
                "icp_score": 92,
                "is_qualified": True,
                "disqualification_reason": None,
                "buying_signal": "Phase 2 initiated Q4 2025 with PET dosimetry as primary endpoint. Series B closed ($85M) to fund pivotal imaging studies.",
                "recommended_offer": "Imaging Readiness Sprint",
                "score_breakdown": {
                    "base_company_fit": 38,
                    "phase_match": 20,
                    "imaging_materiality": 19,
                    "why_now_trigger": 12,
                    "complexity_bonus": 3
                },
                "score_explanation": "Base fit: 38/40 - Strong biopharma in radiopharma. Phase: 20/20 - Active Phase 2. Imaging: 19/20 - PET dosimetry is primary endpoint. Trigger: 12/15 - Recent funding + phase initiation. Complexity: 3/5 - Multi-region.",
                "scoring_timestamp": datetime.now(),
                "reasoning_chain": """ANALYSIS CHAIN:

1. COMPANY TYPE: ✓ Biopharma (radiopharma therapeutics)
   - Verified specialty pharma focused on targeted radiotherapeutics
   - Not med device or diagnostics-only

2. TRIAL PHASE: ✓ Phase 2 (meets criteria)
   - Active Phase 2 trial registered on ClinicalTrials.gov
   - First patient dosed November 2025

3. IMAGING MATERIALITY: ✓ High
   - PET dosimetry is PRIMARY endpoint (not exploratory)
   - RECIST 1.1 for tumor response assessment
   - Central read required per protocol

4. COMPLEXITY SIGNALS: ✓ Multiple
   - 35 sites across US and EU
   - Multi-region execution
   - Oncology indication (solid tumors)

5. WHY NOW TRIGGER: ✓ Strong
   - Series B funding closed ($85M) Q3 2025
   - Phase 2 just initiated (optimal timing for imaging support)
   - New VP Clinical Ops hired August 2025

SCORE CALCULATION:
- Base ICP fit: 38 points (strong biopharma match)
- Phase match: 20 points (Phase 2 = full points)
- Imaging materiality: 19 points (primary endpoint)
- Why now trigger: 12 points (funding + phase transition + new hire)
- Complexity bonus: 3 points (multi-region)
- TOTAL: 92/100

RECOMMENDATION: Imaging Readiness Sprint is ideal—they need protocol validation before scaling to all 35 sites."""
            },
            {
                "icp_score": 85,
                "is_qualified": True,
                "disqualification_reason": None,
                "buying_signal": "Protocol amendment filed adding MRI volumetrics as secondary endpoint. New Head of Imaging hired January 2025.",
                "recommended_offer": "Imaging Charter Fast-Track",
                "score_breakdown": {
                    "base_company_fit": 35,
                    "phase_match": 20,
                    "imaging_materiality": 16,
                    "why_now_trigger": 10,
                    "complexity_bonus": 4
                },
                "score_explanation": "Base fit: 35/40 - CNS biopharma. Phase: 20/20 - Active Phase 2. Imaging: 16/20 - MRI as secondary endpoint. Trigger: 10/15 - Protocol amendment + new hire. Complexity: 4/5 - CNS specialty.",
                "scoring_timestamp": datetime.now(),
                "reasoning_chain": """ANALYSIS CHAIN:

1. COMPANY TYPE: ✓ Biopharma (CNS-focused)
   - Specialty pharma in neurodegeneration space
   - Venture-backed (Series C)

2. TRIAL PHASE: ✓ Phase 2 (meets criteria)
   - Ongoing Phase 2 for Alzheimer's disease
   - Approximately 18 months into enrollment

3. IMAGING MATERIALITY: ✓ High
   - MRI volumetrics for hippocampal atrophy
   - Central read mandated by protocol
   - FDA feedback requiring standardized imaging charter

4. COMPLEXITY SIGNALS: ✓ Present
   - 28 sites (US + Canada)
   - CNS indication with complex imaging requirements

5. WHY NOW TRIGGER: ✓ Moderate-Strong
   - Protocol amendment adding imaging endpoints (regulatory pressure)
   - New Head of Imaging suggests capability gap
   - No "hot" funding trigger but clear operational need

SCORE CALCULATION:
- Base ICP fit: 35 points (CNS biopharma match)
- Phase match: 20 points (Phase 2 = full points)
- Imaging materiality: 16 points (secondary endpoint but mandated)
- Why now trigger: 10 points (org change + protocol amendment)
- Complexity bonus: 4 points (CNS specialty imaging)
- TOTAL: 85/100

RECOMMENDATION: Imaging Charter Fast-Track—they have defined endpoints but need formal charter development."""
            },
            {
                "icp_score": 78,
                "is_qualified": True,
                "disqualification_reason": None,
                "buying_signal": "First-in-human PET imaging study. Novel tracer requiring specialized dosimetry expertise.",
                "recommended_offer": "Imaging Readiness Sprint",
                "score_breakdown": {
                    "base_company_fit": 32,
                    "phase_match": 15,
                    "imaging_materiality": 20,
                    "why_now_trigger": 8,
                    "complexity_bonus": 3
                },
                "score_explanation": "Base fit: 32/40 - Early-stage immunotherapy biotech. Phase: 15/20 - Phase 1/2 (partial). Imaging: 20/20 - PET IS the therapy. Trigger: 8/15 - FIH timing. Complexity: 3/5 - Novel tracer.",
                "scoring_timestamp": datetime.now(),
                "reasoning_chain": """ANALYSIS CHAIN:

1. COMPANY TYPE: ✓ Biopharma (immunotherapy/imaging)
   - Early-stage biotech combining immunotherapy with PET imaging
   - Series A+ funding

2. TRIAL PHASE: ✓ Phase 1/2 (meets criteria as "late Phase 1")
   - First-in-human PET imaging study
   - Dose escalation with imaging-based response assessment

3. IMAGING MATERIALITY: ✓ Critical
   - PET imaging IS the therapeutic approach
   - Dosimetry is primary safety/efficacy measure
   - Novel tracer = regulatory scrutiny

4. COMPLEXITY SIGNALS: ⚠️ Partial
   - Only 8 sites currently (below 20 threshold)
   - US-only (single region)
   - BUT: Oncology indication, high imaging complexity

5. WHY NOW TRIGGER: ✓ Present
   - First-in-human = maximum need for imaging expertise
   - No existing imaging infrastructure
   - Likely planning Phase 2 expansion

SCORE CALCULATION:
- Base ICP fit: 32 points (early-stage biotech)
- Phase match: 15 points (Phase 1/2 partial points)
- Imaging materiality: 20 points (imaging IS the therapy)
- Why now trigger: 8 points (FIH timing)
- Complexity bonus: 3 points (novel tracer complexity)
- TOTAL: 78/100

RECOMMENDATION: Imaging Readiness Sprint—foundational imaging strategy needed before scale-up."""
            },
        ]
        
        scored_leads = []
        for i, lead in enumerate(leads):
            self.report_progress(f"Scoring lead {i+1}/{len(leads)}: {lead.company_name}")
            
            if i < len(mock_scores):
                score_data = mock_scores[i]
            else:
                # Generate variation for additional leads
                score_data = mock_scores[i % len(mock_scores)].copy()
                score_data = dict(score_data)  # Make a proper copy
                score_data["icp_score"] = max(50, score_data["icp_score"] - (i * 5))
                score_data["is_qualified"] = score_data["icp_score"] >= 75
                score_data["scoring_timestamp"] = datetime.now()
                # Adjust score breakdown
                if score_data["icp_score"] < 75:
                    score_data["score_breakdown"] = {
                        "base_company_fit": 25,
                        "phase_match": 10,
                        "imaging_materiality": 10,
                        "why_now_trigger": 5,
                        "complexity_bonus": 0
                    }
                    score_data["disqualification_reason"] = "Score below 75 threshold - weak trigger signals"
            
            scored_lead = ScoredLead(
                **lead.model_dump(),
                **score_data
            )
            scored_leads.append(scored_lead)
        
        qualified_count = sum(1 for l in scored_leads if l.is_qualified)
        self.report_progress(f"Scoring complete: {qualified_count}/{len(scored_leads)} qualified")
        return scored_leads


class AnalystAgent(BaseAgent):
    """Production Analyst Agent using DeepSeek R1 for reasoning."""
    
    def __init__(
        self,
        deepseek_service,
        on_progress: Optional[Callable[[str], None]] = None
    ):
        super().__init__(on_progress)
        self.deepseek = deepseek_service
    
    def _analyze_single_lead(
        self,
        lead: Lead,
        icp_definition: str
    ) -> ScoredLead:
        """Analyze a single lead and return ScoredLead with detailed breakdown."""
        prompt = ANALYST_SCORING_PROMPT.format(
            company_name=lead.company_name,
            website=lead.website or "N/A",
            therapeutic_area=lead.therapeutic_area,
            clinical_phase=lead.clinical_phase,
            imaging_signal=lead.imaging_signal,
            icp_definition=icp_definition
        )
        
        user_prompt = f"Analyze {lead.company_name} for ICP fit. Return JSON only."
        
        # Call with JSON parsing and retry
        score_data = self.deepseek.call_r1_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_retries=2
        )
        
        # Extract and validate score
        icp_score = int(score_data.get("icp_score", 0))
        is_qualified = score_data.get("is_qualified", icp_score >= 75)
        
        # Parse score breakdown with defaults
        raw_breakdown = score_data.get("score_breakdown", {})
        score_breakdown = {
            "base_company_fit": int(raw_breakdown.get("base_company_fit", 0)),
            "phase_match": int(raw_breakdown.get("phase_match", 0)),
            "imaging_materiality": int(raw_breakdown.get("imaging_materiality", 0)),
            "why_now_trigger": int(raw_breakdown.get("why_now_trigger", 0)),
            "complexity_bonus": int(raw_breakdown.get("complexity_bonus", 0)),
        }
        
        return ScoredLead(
            **lead.model_dump(),
            icp_score=icp_score,
            is_qualified=is_qualified,
            disqualification_reason=score_data.get("disqualification_reason"),
            buying_signal=score_data.get("buying_signal", "No specific trigger identified"),
            recommended_offer=score_data.get("recommended_offer", "Imaging Readiness Sprint"),
            reasoning_chain=score_data.get("reasoning_chain", ""),
            score_breakdown=score_breakdown,
            score_explanation=score_data.get("score_explanation", ""),
            scoring_timestamp=datetime.now()
        )
    
    def execute(
        self,
        leads: List[Lead],
        icp_definition: str = "",
        **kwargs
    ) -> List[ScoredLead]:
        """Score each lead against ICP criteria using DeepSeek R1."""
        if not leads:
            self.report_progress("No leads to analyze")
            return []
        
        self.report_progress(f"Analyzing {len(leads)} leads with reasoning model...")
        
        scored_leads = []
        
        for i, lead in enumerate(leads):
            self.report_progress(f"Analyzing {i+1}/{len(leads)}: {lead.company_name}")
            
            try:
                scored_lead = self._analyze_single_lead(lead, icp_definition)
                scored_leads.append(scored_lead)
                
                # Brief delay to avoid rate limiting
                if i < len(leads) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                self.report_progress(f"Error analyzing {lead.company_name}: {e}")
                # Create a failed lead with score 0
                scored_lead = ScoredLead(
                    **lead.model_dump(),
                    icp_score=0,
                    is_qualified=False,
                    disqualification_reason=f"Analysis error: {str(e)}",
                    buying_signal="",
                    recommended_offer="",
                    reasoning_chain=f"Analysis failed: {str(e)}",
                    score_breakdown={
                        "base_company_fit": 0,
                        "phase_match": 0,
                        "imaging_materiality": 0,
                        "why_now_trigger": 0,
                        "complexity_bonus": 0
                    },
                    score_explanation=f"Analysis failed: {str(e)}",
                    scoring_timestamp=datetime.now()
                )
                scored_leads.append(scored_lead)
        
        qualified_count = sum(1 for l in scored_leads if l.is_qualified)
        self.report_progress(f"Analysis complete: {qualified_count}/{len(scored_leads)} qualified")
        return scored_leads
