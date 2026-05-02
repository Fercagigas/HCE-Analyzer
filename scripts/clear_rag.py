"""
Script para limpiar la base de datos vectorial RAG en Supabase.

Elimina todos los chunks de la tabla rag_chunks.
Útil para empezar de cero con documentos limpios.
"""
import logging
import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_rag_chunks() -> int:
    """
    Elimina todos los chunks de la tabla rag_chunks en Supabase.

    Returns:
        Número de registros eliminados

    Raises:
        Exception: Si no se puede conectar a Supabase
    """
    try:
        from supabase import create_client

        client = create_client(
            settings.database.supabase_url,
            settings.database.supabase_key,
        )

        logger.info("🗑️ Eliminando todos los chunks de rag_chunks...")

        result = (
            client.table("rag_chunks")
            .delete()
            .neq("id", "00000000-0000-0000-0000-000000000000")
            .execute()
        )

        deleted = len(result.data) if result.data else 0
        logger.info(f"✅ {deleted} chunks eliminados de Supabase")
        return deleted

    except Exception as e:
        logger.error(f"❌ Error eliminando chunks: {e}")
        raise


def main():
    """Función principal."""
    print("=" * 70)
    print("🗑️  LIMPIEZA DE BASE DE DATOS VECTORIAL RAG")
    print("=" * 70)
    print()
    print("⚠️  ADVERTENCIA: Esta operación eliminará TODOS los documentos")
    print("    indexados en el sistema RAG (Supabase pgvector).")
    print("    Esta acción es IRREVERSIBLE.")
    print()

    response = input("¿Está seguro de que desea continuar? (escriba 'SI' para confirmar): ")

    if response.strip().upper() != "SI":
        print()
        print("❌ Operación cancelada por el usuario")
        return

    print()
    print("🔄 Iniciando limpieza...")
    print()

    try:
        deleted = clear_rag_chunks()
    except Exception:
        deleted = 0

    print()
    print("=" * 70)
    if deleted > 0:
        print("✅ LIMPIEZA COMPLETADA")
        print()
        print("Próximos pasos:")
        print("1. Reinicie la aplicación: streamlit run main.py")
        print("2. Suba sus documentos nuevamente desde la interfaz")
        print("3. Los documentos se indexarán en Supabase pgvector")
    else:
        print("ℹ️  No se encontraron datos para eliminar")
    print("=" * 70)


if __name__ == "__main__":
    main()
