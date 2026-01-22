# Supabase Setup Instructions

This application uses Supabase for persistent company history storage. Follow these steps to set up your database.

## Step 1: Create Database Tables

Go to your Supabase SQL Editor:
https://ptehtflcnskwwhfmksoc.supabase.co/project/default/sql

Copy and paste the contents of `supabase_schema.sql` and run it. This will create:

- **`companies`** table - Stores basic company information and discovery metadata
- **`hunts`** table - Stores metadata about each hunt execution
- **`encounters`** table - Stores detailed records of each company encounter (messages, scores, provenance)
- **`metadata`** table - System configuration and versioning

## Step 2: Verify Tables Created

After running the schema, verify the tables exist:
1. Go to Table Editor in Supabase
2. You should see: `companies`, `hunts`, `encounters`, `metadata`

## Step 3: Configure Credentials

### For Local Development:

Your credentials are already in `.env`:
```
SUPABASE_URL=https://ptehtflcnskwwhfmksoc.supabase.co
SUPABASE_KEY=sb_publishable_hO_YGYBND2ighlLaLcEu9Q_GZjo9PSO
```

### For Streamlit Cloud:

1. Go to your Streamlit Cloud app settings
2. Navigate to **Secrets**
3. Add these values:

```toml
DEEPSEEK_API_KEY = "sk-a0ac094f977c465bb78255e8d6b2c1a2"
TAVILY_API_KEY = "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"
SUPABASE_URL = "https://ptehtflcnskwwhfmksoc.supabase.co"
SUPABASE_KEY = "sb_publishable_hO_YGYBND2ighlLaLcEu9Q_GZjo9PSO"
```

## Step 4: Test Locally

```bash
# Install dependencies (if not done)
pip install -r requirements.txt

# Run the app
streamlit run main.py
```

Run a test hunt to verify data is being saved to Supabase. Check the Company History tab to see if companies appear.

## Step 5: Deploy to Streamlit Cloud

Once local testing works:

1. Push code to GitHub (already done)
2. Update Streamlit Cloud secrets (Step 3)
3. Redeploy the app

## Data Model

### Companies Table
Stores aggregate information about each unique company:
- Basic info (name, website)
- Discovery timestamps
- All therapeutic areas and phases seen
- Score history and best score
- Hunt IDs where appeared

### Encounters Table
Stores detailed records for each hunt encounter:
- **Scoring details**: ICP score, breakdown, explanation
- **Drafted messages**: Email subject, body, personalization notes
- **Provenance**: Discovery source, priority tier, search round
- **Clinical info**: Therapeutic area, clinical phase for this hunt

This allows you to see exactly how a company was scored and messaged in each specific hunt.

## Migration from Local Files

If you have existing local company history (`~/.pharmhunter/company_history.json`), run:

```bash
python migrate_to_supabase.py
```

This will upload your existing data to Supabase.

## Security Notes

- The `sb_publishable_*` key is safe for client-side use
- Row Level Security (RLS) is enabled with permissive policies
- Never commit `sb_secret_*` keys to code
