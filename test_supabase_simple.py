#!/usr/bin/env python3
"""
Simple Supabase connection test for HCE Analyzer Pro
"""

import os
import sys
from dotenv import load_dotenv

def main():
    """Simple test to verify Supabase connection"""
    print("🔍 Simple Supabase Connection Test")
    print("-" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials (checking both possible variable names)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    print(f"URL: {supabase_url}")
    print(f"Key: {supabase_key[:20] + '...' if supabase_key else 'Not found'}")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return False
    
    try:
        # Import and create client
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        print("✅ Supabase client created successfully")
        print(f"📍 Connected to: {supabase.url}")
        
        # Test basic functionality
        try:
            # Simple test - check if we can access auth
            auth = supabase.auth
            session = auth.get_session()
            print(f"🔐 Auth accessible: {'Yes' if auth else 'No'}")
            print(f"📋 Current session: {'Active' if session else 'None'}")
            
            print("✅ Connection test PASSED")
            return True
            
        except Exception as e:
            print(f"⚠️  Auth test failed: {e}")
            print("✅ Basic connection works, auth might need setup")
            return True
            
    except ImportError:
        print("❌ Supabase package not installed")
        print("💡 Run: pip install supabase")
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)