#!/usr/bin/env python3
"""
Test to discover actual tables in the Supabase database
"""

import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing credentials")
        return
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        # Based on the hints from error messages, let's test these tables:
        potential_tables = [
            "users",
            "chat_messages", 
            "chat_sessions",
            "clinical_documents",
            "user_sessions",
            "profiles",
            "documents",
            "analyses"
        ]
        
        print("🔍 Discovering actual database tables...")
        print("-" * 50)
        
        accessible_tables = []
        
        for table in potential_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                accessible_tables.append(table)
                print(f"✅ {table} - accessible")
                
                # Show column info if possible
                if result.data:
                    columns = list(result.data[0].keys()) if result.data else []
                    print(f"   Columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
                else:
                    print(f"   (empty table)")
                    
            except Exception as e:
                print(f"❌ {table} - not accessible")
        
        print(f"\n📊 Summary:")
        print(f"✅ Accessible tables: {len(accessible_tables)}")
        print(f"📋 Tables: {', '.join(accessible_tables)}")
        
        return accessible_tables
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    main()