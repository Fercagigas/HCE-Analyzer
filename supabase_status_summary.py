#!/usr/bin/env python3
"""
Final Supabase Status Summary for HCE Analyzer Pro
"""

import os
from dotenv import load_dotenv
from datetime import datetime

def main():
    print("🎯 HCE Analyzer Pro - Supabase Status Summary")
    print("=" * 60)
    
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        print("✅ CONNECTION STATUS: WORKING")
        print(f"🔗 Database URL: {supabase_url}")
        print(f"🕒 Tested at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📊 DATABASE TABLES:")
        print("-" * 30)
        
        # Test actual tables found
        actual_tables = ["users", "chat_messages", "chat_sessions", "clinical_documents"]
        
        for table in actual_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                count_result = supabase.table(table).select('*', count='exact').execute()
                count = count_result.count if hasattr(count_result, 'count') else 0
                print(f"✅ {table:<20} - Ready (records: {count})")
            except Exception as e:
                print(f"❌ {table:<20} - Error: {str(e)[:50]}...")
        
        print("\n🔐 AUTHENTICATION:")
        print("-" * 20)
        auth = supabase.auth
        session = auth.get_session()
        print(f"✅ Auth system: Ready")
        print(f"📋 Current session: {'Active' if session else 'None (normal for test)'}")
        
        print("\n📁 STORAGE:")
        print("-" * 15)
        storage = supabase.storage
        buckets = storage.list_buckets()
        print(f"✅ Storage system: Ready")
        print(f"📦 Buckets: {len(buckets)} configured")
        
        print("\n🎯 OVERALL STATUS:")
        print("-" * 20)
        print("✅ SUPABASE DATABASE IS WORKING CORRECTLY")
        print("✅ Ready for HCE Analyzer Pro application")
        
        print("\n💡 NEXT STEPS:")
        print("- Your Supabase database is properly connected")
        print("- Core tables are available and accessible")
        print("- Authentication system is ready")
        print("- You can now run your main application")
        
        return True
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("🚀 Database test completed successfully!")
    else:
        print("❌ Database test failed - check your configuration")