#!/usr/bin/env python3
"""
One-time migration script to move local company history to Supabase.

Usage:
    python migrate_to_supabase.py

This will:
1. Load company_history.json from ~/.pharmhunter/
2. Upload all companies to Supabase
3. Upload all hunt summaries to Supabase
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.company_history_service import CompanyHistoryService
from src.models.company_history import CompanyHistory


def main():
    """Main migration function."""
    print("=" * 60)
    print("PharmHunter - Migrate Local History to Supabase")
    print("=" * 60)
    
    # Check for local history file
    local_path = Path.home() / ".pharmhunter" / "company_history.json"
    
    if not local_path.exists():
        print(f"\nNo local history found at: {local_path}")
        print("Nothing to migrate.")
        return
    
    print(f"\nFound local history at: {local_path}")
    
    # Load local file
    try:
        with open(local_path, 'r') as f:
            data = json.load(f)
        
        history = CompanyHistory.model_validate(data)
        print(f"\nLoaded local history:")
        print(f"  - {len(history.companies)} companies")
        print(f"  - {len(history.hunt_summary)} hunts")
        
    except Exception as e:
        print(f"\nError loading local history: {e}")
        return
    
    # Initialize Supabase service
    try:
        service = CompanyHistoryService()
        print(f"\nConnected to Supabase")
    except Exception as e:
        print(f"\nError connecting to Supabase: {e}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")
        return
    
    # Migrate companies
    print(f"\nMigrating companies...")
    success_count = 0
    error_count = 0
    
    for i, company in enumerate(history.companies, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(history.companies)}...")
        
        if service._upsert_company(company):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\nCompanies migration complete:")
    print(f"  - Success: {success_count}")
    print(f"  - Errors: {error_count}")
    
    # Migrate hunt summaries
    print(f"\nMigrating hunt summaries...")
    hunt_success = 0
    hunt_error = 0
    
    for hunt_id, hunt in history.hunt_summary.items():
        try:
            hunt_data = {
                "hunt_id": hunt.hunt_id,
                "timestamp": hunt.timestamp.isoformat(),
                "companies_found": hunt.companies_found,
                "new_companies": hunt.new_companies,
                "duplicates_filtered": hunt.duplicates_filtered,
                "qualified_count": hunt.qualified_count,
                "params": hunt.params,
            }
            
            service.supabase.table("hunts").upsert(
                hunt_data,
                on_conflict="hunt_id"
            ).execute()
            
            hunt_success += 1
        except Exception as e:
            print(f"  Error migrating hunt {hunt_id}: {e}")
            hunt_error += 1
    
    print(f"\nHunt summaries migration complete:")
    print(f"  - Success: {hunt_success}")
    print(f"  - Errors: {hunt_error}")
    
    # Verify migration
    print(f"\nVerifying migration...")
    service.clear_cache()  # Force reload from Supabase
    migrated_history = service.load_history()
    
    print(f"Supabase now contains:")
    print(f"  - {migrated_history.total_companies} companies")
    print(f"  - {migrated_history.total_hunts} hunts")
    
    if migrated_history.total_companies == len(history.companies):
        print(f"\n✅ Migration successful!")
        print(f"\nYou can safely delete the local file if desired:")
        print(f"  rm {local_path}")
    else:
        print(f"\n⚠️  Migration may be incomplete. Please verify in Supabase dashboard.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
