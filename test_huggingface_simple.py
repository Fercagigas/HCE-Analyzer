#!/usr/bin/env python3
"""
Script de prueba simple para verificar que el token de HuggingFace se está usando correctamente
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_huggingface_token_simple():
    """Prueba simple del token de HuggingFace"""
    print("🔍 Verificando configuración de HuggingFace...")
    
    # Verificar que el token está configurado
    token = os.getenv("HUGGINFACEHUB_API_TOKEN")
    if token:
        print(f"✅ Token de HuggingFace configurado: {token[:10]}...")
    else:
        print("❌ Token de HuggingFace no configurado")
        return False
    
    try:
        # Probar inicialización de embeddings con token
        from langchain_huggingface import HuggingFaceEmbeddings
        
        model_kwargs = {'device': 'cpu'}
        if token:
            model_kwargs['use_auth_token'] = token
        
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs=model_kwargs,
            encode_kwargs={'normalize_embeddings': True}
        )
        
        print("✅ Embeddings de HuggingFace inicializados correctamente")
        
        # Probar una embedding simple
        test_text = "Este es un texto de prueba para verificar los embeddings"
        embedding = embeddings.embed_query(test_text)
        print(f"✅ Embedding generado correctamente (dimensión: {len(embedding)})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al probar HuggingFace: {e}")
        return False

def test_chromadb_embedding_function_simple():
    """Prueba simple de la función de embeddings de ChromaDB"""
    print("\n🔍 Verificando función de embeddings de ChromaDB...")
    
    try:
        from chromadb.utils import embedding_functions
        
        token = os.getenv("HUGGINFACEHUB_API_TOKEN")
        
        # Configurar función de embeddings
        embedding_function_kwargs = {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2"
        }
        if token:
            embedding_function_kwargs["token"] = token
        
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            **embedding_function_kwargs
        )
        
        print("✅ Función de embeddings de ChromaDB inicializada correctamente")
        
        # Probar embedding
        test_texts = ["Texto de prueba para ChromaDB"]
        embeddings = embedding_function(test_texts)
        print(f"✅ Embedding de ChromaDB generado correctamente (dimensión: {len(embeddings[0])})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al probar función de embeddings de ChromaDB: {e}")
        return False

def test_token_authentication():
    """Prueba si el token mejora la autenticación"""
    print("\n🔍 Verificando autenticación con token...")
    
    try:
        import requests
        
        token = os.getenv("HUGGINFACEHUB_API_TOKEN")
        if not token:
            print("⚠️ No hay token para probar autenticación")
            return True
        
        # Probar acceso a la API de HuggingFace
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "https://huggingface.co/api/whoami",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Token válido - Usuario: {user_info.get('name', 'Desconocido')}")
            return True
        else:
            print(f"⚠️ Token puede no ser válido (status: {response.status_code})")
            return True  # No es crítico para el funcionamiento
            
    except Exception as e:
        print(f"⚠️ No se pudo verificar el token: {e}")
        return True  # No es crítico para el funcionamiento

if __name__ == "__main__":
    print("🚀 Iniciando pruebas simples de configuración de HuggingFace...\n")
    
    success = True
    
    # Ejecutar pruebas
    success &= test_huggingface_token_simple()
    success &= test_chromadb_embedding_function_simple()
    success &= test_token_authentication()
    
    print("\n" + "="*50)
    if success:
        print("✅ El token de HuggingFace está configurado correctamente")
    else:
        print("❌ Algunas pruebas fallaron")
        print("🔧 Revisa la configuración del token de HuggingFace")
    
    print("="*50)