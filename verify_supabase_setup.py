#!/usr/bin/env python3
"""
Verificar la configuración completa de Supabase después de los comandos SQL
"""

import os
from dotenv import load_dotenv

def main():
    print("🔍 Verificando configuración completa de Supabase...")
    print("=" * 60)
    
    load_dotenv()
    
    try:
        from supabase import create_client
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        
        # Verificar todas las tablas
        all_tables = [
            "users", "chat_messages", "chat_sessions", 
            "clinical_documents", "analyses", "user_preferences", "user_sessions"
        ]
        
        print("📊 VERIFICANDO TABLAS:")
        accessible_count = 0
        for table in all_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                print(f"✅ {table}")
                accessible_count += 1
            except Exception as e:
                print(f"❌ {table} - {str(e)[:50]}...")
        
        print(f"\n📋 Tablas accesibles: {accessible_count}/{len(all_tables)}")
        
        # Verificar funciones
        print("\n🔧 VERIFICANDO FUNCIONES:")
        try:
            result = supabase.rpc('version').execute()
            print("✅ Función version() disponible")
        except:
            print("❌ Función version() no disponible")
        
        # Verificar storage
        print("\n📁 VERIFICANDO STORAGE:")
        try:
            buckets = supabase.storage.list_buckets()
            print(f"✅ Buckets encontrados: {len(buckets)}")
            for bucket in buckets:
                print(f"   📦 {bucket.name}")
        except Exception as e:
            print(f"❌ Error en storage: {e}")
        
        print(f"\n🎯 CONFIGURACIÓN COMPLETA: {'✅ EXITOSA' if accessible_count >= 6 else '⚠️ PARCIAL'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()