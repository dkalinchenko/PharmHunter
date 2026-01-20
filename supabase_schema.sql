-- PharmHunter Supabase Database Schema
-- Run this in your Supabase SQL Editor: https://ptehtflcnskwwhfmksoc.supabase.co/project/default/sql

-- Table 1: Companies
-- Stores all discovered companies with their history
CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL UNIQUE,
  website TEXT,
  first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  times_discovered INTEGER NOT NULL DEFAULT 1,
  hunt_ids TEXT[] NOT NULL DEFAULT '{}',
  therapeutic_areas TEXT[] NOT NULL DEFAULT '{}',
  clinical_phases TEXT[] NOT NULL DEFAULT '{}',
  icp_scores INTEGER[] NOT NULL DEFAULT '{}',
  best_score INTEGER,
  was_qualified BOOLEAN NOT NULL DEFAULT false,
  source_urls TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON companies(normalized_name);
CREATE INDEX IF NOT EXISTS idx_companies_was_qualified ON companies(was_qualified);
CREATE INDEX IF NOT EXISTS idx_companies_last_seen ON companies(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_companies_best_score ON companies(best_score DESC);

-- Table 2: Hunts
-- Stores metadata for each hunt execution
CREATE TABLE IF NOT EXISTS hunts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hunt_id TEXT NOT NULL UNIQUE,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  companies_found INTEGER NOT NULL DEFAULT 0,
  new_companies INTEGER NOT NULL DEFAULT 0,
  duplicates_filtered INTEGER NOT NULL DEFAULT 0,
  qualified_count INTEGER NOT NULL DEFAULT 0,
  params JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for hunt queries
CREATE INDEX IF NOT EXISTS idx_hunts_timestamp ON hunts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hunts_hunt_id ON hunts(hunt_id);

-- Table 3: Metadata (optional)
-- For version tracking and system configuration
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Insert initial metadata
INSERT INTO metadata (key, value) VALUES ('version', '1.0')
ON CONFLICT (key) DO NOTHING;

-- Enable Row Level Security (RLS)
-- For now, allow all operations (can be restricted later for multi-tenancy)
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE hunts ENABLE ROW LEVEL SECURITY;
ALTER TABLE metadata ENABLE ROW LEVEL SECURITY;

-- Create permissive policies (allows all authenticated operations)
CREATE POLICY "Allow all operations on companies" ON companies
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on hunts" ON hunts
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on metadata" ON metadata
  FOR ALL USING (true) WITH CHECK (true);

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on companies table
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'PharmHunter database schema created successfully!';
END $$;
