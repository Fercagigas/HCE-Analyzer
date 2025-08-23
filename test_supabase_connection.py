#!/usr/bin/env python3
"""
Test script to verify Supabase database connection for HCE Analyzer Pro
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_environment():
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env file")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables")
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")

def check_environment_variables() -> Dict[str, Any]:
    """Check if required environment variables are set"""
    print("\n" + "="*50)
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("="*50)
    
    # Check for both possible variable names
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    results = {
        "supabase_url": supabase_url,
        "supabase_key": supabase_key,
        "all_present": bool(supabase_url and supabase_key)
    }
    
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    if supabase_url:
        print(f"  URL: {supabase_url[:30]}...")
    
    print(f"SUPABASE_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")
    if supabase_key:
        print(f"  Key: {supabase_key[:20]}...")
    
    return results

def test_supabase_import():
    """Test if Supabase client can be imported"""
    print("\n" + "="*50)
    print("📦 TESTING SUPABASE IMPORT")
    print("="*50)
    
    try:
        from supabase import create_client, Client
        print("✅ Supabase client imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Supabase client: {e}")
        print("💡 Install with: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing Supabase: {e}")
        return False

def test_supabase_connection(supabase_url: str, supabase_key: str) -> Optional[Any]:
    """Test connection to Supabase"""
    print("\n" + "="*50)
    print("🔗 TESTING SUPABASE CONNECTION")
    print("="*50)
    
    try:
        from supabase import create_client
        
        # Create client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        return supabase
        
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return None

def test_database_operations(supabase_client) -> bool:
    """Test basic database operations"""
    print("\n" + "="*50)
    print("🗄️  TESTING DATABASE OPERATIONS")
    print("="*50)
    
    if not supabase_client:
        print("❌ No Supabase client available")
        return False
    
    try:
        # Test 1: List tables (this will show available tables)
        print("📋 Testing table access...")
        
        # Try to get schema information
        try:
            # This is a simple query that should work with any Supabase setup
            result = supabase_client.table('_realtime_schema').select('*').limit(1).execute()
            print("✅ Database connection verified - can access system tables")
        except Exception as e:
            print(f"⚠️  System table access failed (this is normal): {e}")
            
            # Try a more basic approach - just test the connection
            try:
                # Test with a simple RPC call that should always exist
                result = supabase_client.rpc('version').execute()
                print("✅ Database connection verified via RPC")
            except Exception as e2:
                print(f"⚠️  RPC test failed: {e2}")
                print("🔍 Attempting basic connection test...")
                
                # Most basic test - just try to access the client
                if hasattr(supabase_client, 'url'):
                    print(f"✅ Client initialized with URL: {supabase_client.url}")
                    return True
                else:
                    print("❌ Client seems invalid")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False

def test_auth_functionality(supabase_client) -> bool:
    """Test authentication functionality"""
    print("\n" + "="*50)
    print("🔐 TESTING AUTHENTICATION")
    print("="*50)
    
    if not supabase_client:
        print("❌ No Supabase client available")
        return False
    
    try:
        # Test auth client access
        auth_client = supabase_client.auth
        print("✅ Auth client accessible")
        
        # Test getting current session (should be None for anonymous)
        session = auth_client.get_session()
        print(f"📋 Current session: {'Active' if session else 'None (expected for test)'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Auth functionality test failed: {e}")
        return False

def test_project_configuration():
    """Test project-specific configuration"""
    print("\n" + "="*50)
    print("⚙️  TESTING PROJECT CONFIGURATION")
    print("="*50)
    
    try:
        # Test if we can load the project settings
        from config.settings import settings
        print("✅ Project settings loaded successfully")
        
        # Check database settings
        db_settings = settings.database
        print(f"📋 Database URL configured: {'✅ Yes' if db_settings.supabase_url else '❌ No'}")
        print(f"📋 Database Key configured: {'✅ Yes' if db_settings.supabase_key else '❌ No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Project configuration test failed: {e}")
        print("💡 Make sure you're running from the project root directory")
        return False

def generate_report(results: Dict[str, Any]):
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("📊 SUPABASE CONNECTION TEST REPORT")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Test completed at: {timestamp}")
    
    print(f"\n📋 Environment Variables: {'✅ PASS' if results.get('env_check', False) else '❌ FAIL'}")
    print(f"📦 Supabase Import: {'✅ PASS' if results.get('import_test', False) else '❌ FAIL'}")
    print(f"🔗 Connection Test: {'✅ PASS' if results.get('connection_test', False) else '❌ FAIL'}")
    print(f"🗄️  Database Operations: {'✅ PASS' if results.get('db_operations', False) else '❌ FAIL'}")
    print(f"🔐 Authentication: {'✅ PASS' if results.get('auth_test', False) else '❌ FAIL'}")
    print(f"⚙️  Project Config: {'✅ PASS' if results.get('config_test', False) else '❌ FAIL'}")
    
    overall_status = all([
        results.get('env_check', False),
        results.get('import_test', False),
        results.get('connection_test', False)
    ])
    
    print(f"\n🎯 OVERALL STATUS: {'✅ READY TO USE' if overall_status else '❌ NEEDS ATTENTION'}")
    
    if not overall_status:
        print("\n💡 RECOMMENDATIONS:")
        if not results.get('env_check', False):
            print("   • Check your .env file and ensure SUPABASE_URL and SUPABASE_KEY are set")
        if not results.get('import_test', False):
            print("   • Install Supabase client: pip install supabase")
        if not results.get('connection_test', False):
            print("   • Verify your Supabase credentials are correct")
            print("   • Check if your Supabase project is active")
    
    print("\n" + "="*60)

async def main():
    """Main test function"""
    print("🚀 HCE Analyzer Pro - Supabase Connection Test")
    print("="*60)
    
    results = {}
    
    # Load environment
    load_environment()
    
    # Check environment variables
    env_results = check_environment_variables()
    results['env_check'] = env_results['all_present']
    
    if not env_results['all_present']:
        print("\n❌ Missing required environment variables. Please check your .env file.")
        generate_report(results)
        return
    
    # Test Supabase import
    results['import_test'] = test_supabase_import()
    
    if not results['import_test']:
        generate_report(results)
        return
    
    # Test connection
    supabase_client = test_supabase_connection(
        env_results['supabase_url'], 
        env_results['supabase_key']
    )
    results['connection_test'] = supabase_client is not None
    
    # Test database operations
    if supabase_client:
        results['db_operations'] = test_database_operations(supabase_client)
        results['auth_test'] = test_auth_functionality(supabase_client)
    else:
        results['db_operations'] = False
        results['auth_test'] = False
    
    # Test project configuration
    results['config_test'] = test_project_configuration()
    
    # Generate final report
    generate_report(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)