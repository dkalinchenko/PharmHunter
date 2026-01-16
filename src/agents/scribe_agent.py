"""Scribe Agent - Drafts personalized outreach for qualified leads."""

import json
from typing import List, Optional, Callable

from ..models.leads import ScoredLead, DraftedLead
from ..prompts.templates import SCRIBE_SYSTEM_PROMPT
from .base_agent import BaseAgent


class MockScribeAgent(BaseAgent):
    """Mock Scribe Agent for UI testing without API calls."""
    
    def execute(
        self,
        scored_leads: List[ScoredLead],
        value_prop: str = "",
        **kwargs
    ) -> List[DraftedLead]:
        """Return mock drafted outreach for testing."""
        qualified_leads = [l for l in scored_leads if l.is_qualified]
        self.report_progress(f"Drafting outreach for {len(qualified_leads)} qualified leads...")
        
        mock_drafts = [
            {
                "contact_persona": "VP of Clinical Operations",
                "contact_name": "Sarah Chen",
                "contact_title": "VP, Clinical Operations",
                "contact_linkedin": "https://linkedin.com/in/sarah-chen-example",
                "email_subject_options": [
                    "Quick question on your Phase 2 imaging protocol",
                    "PET dosimetry for your Lu-177 program",
                    "Imaging execution before your 35-site rollout",
                    "Re: Your recent Series B and Phase 2 imaging",
                    "Avoiding the #1 cause of Phase 2 delays",
                    "Your imaging charter—before site activation"
                ],
                "email_body_primary": """Sarah,

Saw you recently closed your Series B and initiated Phase 2 for your Lu-177 program across 35 sites. PET dosimetry at that scale is where imaging programs typically hit turbulence—site variability, central read discordance, and protocol deviations that surface at the worst possible moment.

We run 2-3 week Imaging Readiness Sprints specifically for radiopharma sponsors at this stage. The output: a risk-prioritized action list and imaging protocol validation before you're locked into site contracts.

Worth a 15-minute call to see if this applies to your timeline? I can also send over a pre-trial imaging checklist we use with similar programs.

Best,
[Your Name]""",
                "email_variant_1": """Sarah,

Phase 2 PET dosimetry trials have a specific failure mode: endpoint integrity issues that only surface at database lock. By then, you're choosing between protocol amendments and compromised data.

We help radiopharma sponsors lock down their imaging execution before enrollment scales. For your Lu-177 program, that means validating dosimetry protocols and central read workflows now—while changes are still cheap.

15 minutes to discuss? Happy to share how similar programs have de-risked this stage.

[Your Name]""",
                "email_variant_2": """Sarah,

35 sites across US and EU for PET dosimetry—that's where imaging consistency becomes a full-time problem. Site training gaps, equipment variability, and protocol drift compound fast.

We specialize in pre-activation imaging readiness: getting sites aligned on acquisition parameters and read procedures before the first scan. Prevents the "site 23 didn't follow the protocol" conversation later.

Quick call to see if timing makes sense?

[Your Name]""",
                "linkedin_message": "Sarah—congrats on the Phase 2 initiation. PET dosimetry across 35 sites is exactly where imaging execution gets complex. We help radiopharma sponsors de-risk this stage. Worth a quick chat?",
                "follow_up_email": """Sarah,

Following up on my note about imaging readiness for your Phase 2 rollout.

Given your 35-site footprint and PET dosimetry requirements, the window to validate imaging protocols is narrow. Happy to share a quick checklist we use with similar programs—no commitment required.

Let me know if 15 minutes works this week.

[Your Name]"""
            },
            {
                "contact_persona": "Head of Translational Medicine",
                "contact_name": "Michael Torres",
                "contact_title": "Head of Translational Medicine",
                "contact_linkedin": "https://linkedin.com/in/michael-torres-example",
                "email_subject_options": [
                    "Your MRI volumetrics protocol amendment",
                    "CNS imaging charter—before FDA asks",
                    "Hippocampal atrophy measurement standardization",
                    "Re: Your new Head of Imaging hire",
                    "MRI endpoints in Alzheimer's trials",
                    "Imaging charter development for CNS"
                ],
                "email_body_primary": """Michael,

Noticed your recent protocol amendment adding MRI volumetrics as a secondary endpoint, plus the new Head of Imaging hire. Both signal you're strengthening imaging rigor—which FDA increasingly expects for CNS programs.

We do 10-day Imaging Charter Fast-Tracks for exactly this situation: defined endpoints that need formal charter documentation and central read specifications before the next FDA touchpoint.

Would a 15-minute call make sense to see if this fits your timeline? I can also share a CNS imaging charter template we've used with similar programs.

Best,
[Your Name]""",
                "email_variant_1": """Michael,

MRI volumetrics in Alzheimer's trials carry a specific risk: measurement variability that undermines your endpoint integrity. Hippocampal atrophy is a small signal—site-to-site differences in acquisition and analysis can swamp it.

We help CNS sponsors lock down imaging charters before this becomes a regulatory conversation. For your program, that means standardized protocols and central read specs that hold up to FDA scrutiny.

15 minutes to explore fit?

[Your Name]""",
                "email_variant_2": """Michael,

28 sites for CNS MRI volumetrics—consistency across that footprint is non-trivial. Scanner differences, acquisition parameters, and analysis pipelines all introduce variability that shows up in your data.

We specialize in imaging charter development: getting the technical specifications documented before site activation. Prevents the retrospective "why do these measurements not match" analysis.

Quick call to discuss timing?

[Your Name]""",
                "linkedin_message": "Michael—saw your protocol amendment adding MRI volumetrics. CNS imaging charters are where FDA scrutiny often intensifies. We help sponsors get ahead of this. Brief chat?",
                "follow_up_email": """Michael,

Circling back on imaging charter development for your CNS program.

With the protocol amendment filed, timing matters for getting imaging specifications documented before your next FDA interaction. Happy to share a CNS imaging charter template—no strings attached.

15 minutes this week?

[Your Name]"""
            },
            {
                "contact_persona": "VP of Clinical Development",
                "contact_name": None,
                "contact_title": None,
                "contact_linkedin": None,
                "email_subject_options": [
                    "PET imaging for your first-in-human study",
                    "Dosimetry expertise for novel tracers",
                    "Your CD8+ imaging program—regulatory pathway",
                    "First-in-human PET: imaging considerations",
                    "Scaling from Phase 1 to Phase 2 imaging",
                    "Novel tracer dosimetry requirements"
                ],
                "email_body_primary": """Hi,

Your first-in-human PET imaging study for CD8+ T-cell visualization caught my attention. Novel tracers in immunotherapy trials face unique imaging challenges—dosimetry requirements, regulatory scrutiny, and the need for imaging protocols that scale to Phase 2.

We run Imaging Readiness Sprints for exactly this stage: establishing imaging infrastructure and protocols before you're committed to a larger footprint. For novel tracers, getting this right early prevents costly retrofits later.

Worth a 15-minute conversation to see if timing aligns? I can also send over a first-in-human imaging checklist we use with similar programs.

Best,
[Your Name]""",
                "email_variant_1": """Hi,

First-in-human PET imaging with a novel tracer—that's where regulatory scrutiny on imaging methodology is highest. Dosimetry protocols, acquisition standardization, and analysis pipelines all need to be bulletproof before Phase 2 discussions.

We help sponsors at this stage establish imaging foundations that hold up to IND amendments and FDA feedback. For your CD8+ program, that means getting ahead of the imaging questions before they're asked.

15 minutes to explore?

[Your Name]""",
                "email_variant_2": """Hi,

Scaling PET imaging from 8 sites to a Phase 2 footprint exposes every inconsistency in your imaging protocols. For novel tracers especially, site variability in acquisition and dosimetry can compromise your data integrity.

We specialize in imaging readiness for Phase 1→2 transitions: documenting protocols, training specifications, and central read workflows before scale-up. Prevents the "different sites, different results" problem.

Quick call to discuss fit?

[Your Name]""",
                "linkedin_message": "Your FIH PET imaging program is at a critical stage—novel tracer dosimetry needs imaging infrastructure that scales to Phase 2. We help sponsors get this right early. Quick chat?",
                "follow_up_email": """Hi,

Following up on imaging readiness for your first-in-human PET study.

Novel tracers face heightened regulatory scrutiny on imaging methodology. Getting protocols and dosimetry specifications documented now saves significant rework when Phase 2 planning begins.

Happy to share a FIH imaging checklist—let me know if 15 minutes works.

[Your Name]"""
            },
        ]
        
        drafted_leads = []
        for i, lead in enumerate(qualified_leads):
            self.report_progress(f"Drafting outreach {i+1}/{len(qualified_leads)}: {lead.company_name}")
            
            if i < len(mock_drafts):
                draft_data = mock_drafts[i]
            else:
                draft_data = mock_drafts[i % len(mock_drafts)]
            
            drafted_lead = DraftedLead(
                **lead.model_dump(),
                **draft_data
            )
            drafted_leads.append(drafted_lead)
        
        self.report_progress(f"Drafting complete: {len(drafted_leads)} outreach packages ready")
        return drafted_leads


class ScribeAgent(BaseAgent):
    """Production Scribe Agent using DeepSeek V3 for copywriting."""
    
    def __init__(
        self,
        deepseek_service,
        on_progress: Optional[Callable[[str], None]] = None
    ):
        super().__init__(on_progress)
        self.deepseek = deepseek_service
    
    def _draft_single_lead(
        self,
        lead: ScoredLead,
        value_prop: str
    ) -> DraftedLead:
        """Draft outreach for a single lead."""
        prompt = SCRIBE_SYSTEM_PROMPT.format(
            company_name=lead.company_name,
            therapeutic_area=lead.therapeutic_area,
            clinical_phase=lead.clinical_phase,
            buying_signal=lead.buying_signal,
            recommended_offer=lead.recommended_offer,
            value_prop=value_prop
        )
        
        user_prompt = f"Create outreach for {lead.company_name}. Their buying signal: {lead.buying_signal}"
        
        # Call with JSON parsing and retry
        draft_data = self.deepseek.call_v3_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_retries=2
        )
        
        # Ensure email_subject_options is a list
        subject_options = draft_data.get("email_subject_options", [])
        if isinstance(subject_options, str):
            subject_options = [subject_options]
        
        return DraftedLead(
            **lead.model_dump(),
            contact_persona=draft_data.get("contact_persona", "VP of Clinical Operations"),
            contact_name=draft_data.get("contact_name"),
            contact_title=draft_data.get("contact_title"),
            contact_linkedin=draft_data.get("contact_linkedin"),
            email_subject_options=subject_options,
            email_body_primary=draft_data.get("email_body_primary", ""),
            email_variant_1=draft_data.get("email_variant_1", ""),
            email_variant_2=draft_data.get("email_variant_2", ""),
            linkedin_message=draft_data.get("linkedin_message", ""),
            follow_up_email=draft_data.get("follow_up_email", "")
        )
    
    def execute(
        self,
        scored_leads: List[ScoredLead],
        value_prop: str = "",
        **kwargs
    ) -> List[DraftedLead]:
        """Draft personalized outreach for qualified leads using DeepSeek V3."""
        qualified_leads = [l for l in scored_leads if l.is_qualified]
        
        if not qualified_leads:
            self.report_progress("No qualified leads to draft outreach for")
            return []
        
        self.report_progress(f"Drafting outreach for {len(qualified_leads)} qualified leads...")
        
        drafted_leads = []
        
        for i, lead in enumerate(qualified_leads):
            self.report_progress(f"Drafting {i+1}/{len(qualified_leads)}: {lead.company_name}")
            
            try:
                drafted_lead = self._draft_single_lead(lead, value_prop)
                drafted_leads.append(drafted_lead)
                
                # Brief delay to avoid rate limiting
                if i < len(qualified_leads) - 1:
                    import time
                    time.sleep(0.5)
                    
            except Exception as e:
                self.report_progress(f"Error drafting for {lead.company_name}: {e}")
                # Create lead with placeholder drafts
                drafted_lead = DraftedLead(
                    **lead.model_dump(),
                    contact_persona="VP of Clinical Operations",
                    contact_name=None,
                    contact_title=None,
                    contact_linkedin=None,
                    email_subject_options=["Follow up on imaging partnership"],
                    email_body_primary=f"[Draft generation failed: {str(e)}. Please manually compose outreach.]",
                    email_variant_1="",
                    email_variant_2="",
                    linkedin_message="",
                    follow_up_email=""
                )
                drafted_leads.append(drafted_lead)
        
        self.report_progress(f"Drafting complete: {len(drafted_leads)} outreach packages ready")
        return drafted_leads
