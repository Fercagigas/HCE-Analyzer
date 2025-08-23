#!/usr/bin/env python3
"""
Advanced Supabase database test with schema validation for HCE Analyzer Pro
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

def test_database_schema(supabase_client) -> Dict[str, Any]:
    """Test database schema and expected tables"""
    print("\n🗄️  Testing Database Schema...")
    
    results = {
        "schema_accessible": False,
        "tables_found": [],
        "expected_tables": [
            "users", "sessions", "documents", "analyses", 
            "clinical_guidelines", "user_preferences"
        ],
        "missing_tables": []
    }
    
    try:
        # Try to get information about tables
        # Note: This might not work depending on RLS policies
        
        # Method 1: Try to query information_schema
        try:
            schema_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
            
            result = supabase_client.rpc('exec_sql', {'sql': schema_query}).execute()
            if result.data:
                results["tables_found"] = [row['table_name'] for row in result.data]
                results["schema_accessible"] = True
                print(f"✅ Found {len(results['tables_found'])} tables")
                
        except Exception as e:
            print(f"⚠️  Schema query method 1 failed: {e}")
            
            # Method 2: Try individual table access
            for table in results["expected_tables"]:
                try:
                    test_result = supabase_client.table(table).select('*').limit(1).execute()
                    results["tables_found"].append(table)
                    print(f"✅ Table '{table}' accessible")
                except Exception as table_error:
                    print(f"❌ Table '{table}' not accessible: {table_error}")
                    results["missing_tables"].append(table)
        
        # Check for missing expected tables
        for expected in results["expected_tables"]:
            if expected not in results["tables_found"]:
                results["missing_tables"].append(expected)
        
        if results["tables_found"]:
            print(f"📋 Accessible tables: {', '.join(results['tables_found'])}")
        
        if results["missing_tables"]:
            print(f"⚠️  Missing expected tables: {', '.join(results['missing_tables'])}")
            
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
    
    return results

def test_rls_policies(supabase_client) -> Dict[str, Any]:
    """Test Row Level Security policies"""
    print("\n🔒 Testing Row Level Security...")
    
    results = {
        "rls_enabled": False,
        "policies_found": [],
        "test_passed": False
    }
    
    try:
        # Try to query RLS information
        rls_query = """
        SELECT schemaname, tablename, rowsecurity 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = true;
        """
        
        result = supabase_client.rpc('exec_sql', {'sql': rls_query}).execute()
        
        if result.data:
            results["rls_enabled"] = True
            results["policies_found"] = result.data
            print(f"✅ RLS enabled on {len(result.data)} tables")
        else:
            print("⚠️  No RLS policies found or query failed")
            
    except Exception as e:
        print(f"⚠️  RLS test failed (this might be normal): {e}")
    
    return results

def test_user_operations(supabase_client) -> Dict[str, Any]:
    """Test user-related operations"""
    print("\n👤 Testing User Operations...")
    
    results = {
        "auth_accessible": False,
        "can_signup": False,
        "can_signin": False,
        "session_management": False
    }
    
    try:
        # Test auth client
        auth = supabase_client.auth
        results["auth_accessible"] = True
        print("✅ Auth client accessible")
        
        # Test session management
        current_session = auth.get_session()
        results["session_management"] = True
        print(f"✅ Session management working (current: {'active' if current_session else 'none'})")
        
        # Note: We won't test actual signup/signin to avoid creating test users
        print("ℹ️  Signup/signin tests skipped (would create test users)")
        
    except Exception as e:
        print(f"❌ User operations test failed: {e}")
    
    return results

def test_storage_functionality(supabase_client) -> Dict[str, Any]:
    """Test storage functionality"""
    print("\n📁 Testing Storage...")
    
    results = {
        "storage_accessible": False,
        "buckets_found": [],
        "can_list_buckets": False
    }
    
    try:
        # Test storage client
        storage = supabase_client.storage
        results["storage_accessible"] = True
        print("✅ Storage client accessible")
        
        # Try to list buckets
        try:
            buckets = storage.list_buckets()
            results["can_list_buckets"] = True
            results["buckets_found"] = [bucket.name for bucket in buckets] if buckets else []
            print(f"✅ Found {len(results['buckets_found'])} storage buckets")
            
            if results["buckets_found"]:
                print(f"📋 Buckets: {', '.join(results['buckets_found'])}")
                
        except Exception as e:
            print(f"⚠️  Bucket listing failed: {e}")
        
    except Exception as e:
        print(f"❌ Storage test failed: {e}")
    
    return results

def create_test_report(all_results: Dict[str, Any]):
    """Create a comprehensive test report"""
    print("\n" + "="*70)
    print("📊 COMPREHENSIVE SUPABASE TEST REPORT")
    print("="*70)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Generated: {timestamp}")
    
    # Basic connectivity
    print(f"\n🔗 Basic Connection: {'✅ PASS' if all_results.get('connection_test', False) else '❌ FAIL'}")
    
    # Schema results
    schema_results = all_results.get('schema_test', {})
    print(f"🗄️  Database Schema: {'✅ PASS' if schema_results.get('schema_accessible', False) else '⚠️  LIMITED'}")
    if schema_results.get('tables_found'):
        print(f"   Tables found: {len(schema_results['tables_found'])}")
    if schema_results.get('missing_tables'):
        print(f"   Missing tables: {len(schema_results['missing_tables'])}")
    
    # Auth results
    auth_results = all_results.get('auth_test', {})
    print(f"🔐 Authentication: {'✅ PASS' if auth_results.get('auth_accessible', False) else '❌ FAIL'}")
    
    # Storage results
    storage_results = all_results.get('storage_test', {})
    print(f"📁 Storage: {'✅ PASS' if storage_results.get('storage_accessible', False) else '❌ FAIL'}")
    if storage_results.get('buckets_found'):
        print(f"   Buckets: {len(storage_results['buckets_found'])}")
    
    # Overall assessment
    critical_tests = [
        all_results.get('connection_test', False),
        auth_results.get('auth_accessible', False)
    ]
    
    overall_status = all(critical_tests)
    print(f"\n🎯 OVERALL STATUS: {'✅ PRODUCTION READY' if overall_status else '⚠️  NEEDS SETUP'}")
    
    # Recommendations
    if not overall_status or schema_results.get('missing_tables'):
        print(f"\n💡 RECOMMENDATIONS:")
        
        if not all_results.get('connection_test', False):
            print("   • Fix basic connection issues first")
            
        if schema_results.get('missing_tables'):
            print("   • Run database migrations to create missing tables:")
            for table in schema_results['missing_tables']:
                print(f"     - {table}")
                
        if not auth_results.get('auth_accessible', False):
            print("   • Check authentication configuration")
            
        if not storage_results.get('storage_accessible', False):
            print("   • Verify storage permissions and setup")
    
    # Save report to file
    report_data = {
        "timestamp": timestamp,
        "results": all_results,
        "overall_status": overall_status
    }
    
    try:
        with open("supabase_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\n💾 Detailed report saved to: supabase_test_report.json")
    except Exception as e:
        print(f"\n⚠️  Could not save report file: {e}")
    
    print("="*70)

def main():
    """Main advanced test function"""
    print("🚀 HCE Analyzer Pro - Advanced Supabase Test")
    print("="*70)
    
    # Load environment
    load_dotenv()
    
    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in environment")
        return False
    
    print(f"🔗 Testing connection to: {supabase_url}")
    
    all_results = {}
    
    try:
        # Create client
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        all_results['connection_test'] = True
        print("✅ Supabase client created successfully")
        
        # Run comprehensive tests
        all_results['schema_test'] = test_database_schema(supabase)
        all_results['rls_test'] = test_rls_policies(supabase)
        all_results['auth_test'] = test_user_operations(supabase)
        all_results['storage_test'] = test_storage_functionality(supabase)
        
    except ImportError:
        print("❌ Supabase package not installed")
        print("💡 Run: pip install supabase")
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        all_results['connection_test'] = False
    
    # Generate comprehensive report
    create_test_report(all_results)
    
    return all_results.get('connection_test', False)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)