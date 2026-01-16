# PharmHunter

Automated biopharma lead discovery, qualification, and outreach drafting powered by AI agents.

## Overview

PharmHunter automates the manual lead generation and qualification workflow for biopharma business development. The system uses a chain of AI agents to:

1. **Discover** - Find biopharma companies matching your criteria using Tavily search
2. **Qualify** - Score leads against your ICP using DeepSeek R1 reasoning model
3. **Draft** - Generate personalized outreach using DeepSeek V3

## Features

- **Mission Control** - Configure ICP definition, value proposition, and search parameters
- **War Room** - Review scored leads with detailed reasoning and edit draft outreach
- **Mock Mode** - Test the UI flow without API calls
- **CSV Export** - Download all leads and drafts for CRM import

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

1. Clone the repository:
```bash
cd /path/to/PharmHunter
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure API keys (optional - can also enter in UI):
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

## API Keys

You'll need two API keys to use live mode:

### DeepSeek API Key
- Sign up at [DeepSeek](https://platform.deepseek.com/)
- Used for lead scoring (R1 reasoner) and outreach drafting (V3 chat)

### Tavily API Key
- Sign up at [Tavily](https://tavily.com/)
- Used for company discovery search

## Usage

### Running the Application

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`

### Quick Start

1. **Configure API Keys** - Enter your DeepSeek and Tavily API keys in the sidebar (or enable Mock Mode for testing)

2. **Set Context** (Mission Control tab)
   - Review/edit the **ICP Definition** - criteria for qualifying leads
   - Review/edit the **Value Proposition** - your consulting offers

3. **Configure Hunt Parameters**
   - Set the number of leads to find (5-50)
   - Specify therapeutic focus (e.g., "Radiopharma, Oncology")
   - Select preferred clinical phases
   - Set geographic focus and exclusions

4. **Start Hunting** - Click the "START HUNTING" button

5. **Review Results** (War Room tab)
   - View scored leads in the summary table
   - Expand each lead to see:
     - The **Math** - reasoning chain explaining the score
     - The **Draft** - editable email templates and LinkedIn message
   - Download all data as CSV

### Mock Mode

Enable "Use Mock Data" in the sidebar to test the UI without making API calls. This returns sample leads with realistic scoring and draft outreach.

## Architecture

```
PharmHunter/
├── main.py                 # Streamlit entry point
├── requirements.txt        # Dependencies
├── src/
│   ├── models/
│   │   └── leads.py       # Pydantic models (Lead, ScoredLead, DraftedLead)
│   ├── services/
│   │   ├── tavily_service.py    # Search API wrapper
│   │   └── deepseek_service.py  # LLM inference
│   ├── agents/
│   │   ├── scout_agent.py       # Discovery agent
│   │   ├── analyst_agent.py     # Scoring agent (DeepSeek R1)
│   │   └── scribe_agent.py      # Drafting agent (DeepSeek V3)
│   ├── prompts/
│   │   └── templates.py         # Prompt templates
│   └── ui/
│       ├── sidebar.py           # Config panel
│       ├── mission_control.py   # Context & parameters
│       └── war_room.py          # Results & review
```

## Agent Pipeline

```
Scout Agent (Tavily Search)
       ↓
  List[Lead]
       ↓
Analyst Agent (DeepSeek R1)
       ↓
 List[ScoredLead]
       ↓
Scribe Agent (DeepSeek V3)
       ↓
List[DraftedLead]
```

### Scout Agent
- Searches for biopharma companies using Tavily
- Looks for imaging signals: RECIST, PET, MRI volumetrics
- Filters by therapeutic area, phase, and geography

### Analyst Agent
- Evaluates each lead against ICP criteria
- Uses DeepSeek R1 (reasoning model) for analysis
- Produces ICP score (0-100) with detailed reasoning
- Identifies "Why Now" triggers for outreach timing
- Qualifies leads with score >= 75

### Scribe Agent
- Drafts personalized outreach for qualified leads
- Uses DeepSeek V3 (chat model) for copywriting
- Generates:
  - 6 subject line options
  - Primary email (120-180 words)
  - 2 email variants (different angles)
  - LinkedIn message (max 350 chars)
  - Follow-up email

## Customization

### ICP Definition
Edit the default ICP criteria in `src/prompts/templates.py`:
- `ICP_DEFINITION` - Must-have criteria, exclusions, and triggers

### Value Proposition
Edit the default offers in `src/prompts/templates.py`:
- `DEFAULT_VALUE_PROP` - Consulting offers and positioning

### Prompt Templates
Modify agent behavior by editing:
- `SCOUT_SYSTEM_PROMPT` - Discovery criteria and output format
- `ANALYST_SYSTEM_PROMPT` - Scoring logic and reasoning structure
- `SCRIBE_SYSTEM_PROMPT` - Outreach tone and email structure

## Troubleshooting

### "No leads found"
- Broaden your therapeutic focus or phase preferences
- Check if your exclusions are too restrictive
- Verify your Tavily API key is valid

### "Analysis error"
- Check your DeepSeek API key
- The model may have timed out - try again with fewer leads

### "Draft generation failed"
- This usually indicates a JSON parsing issue
- Check the console for detailed error messages

### Rate Limiting
- The system includes automatic delays between API calls
- For large lead counts (30+), processing may take several minutes

## License

MIT

## Credits

Built for Marigold consulting outreach automation.
