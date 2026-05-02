"""
Script para indexar los PDFs de guías clínicas en Supabase pgvector.

Uso:
    python -m scripts.index_guias
"""
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

GUIAS_DIR = Path("guias")

PDF_METADATA = {
    "GUÍA-FORMATIVA-MEDICINA-INTENSIVA-1.pdf": {
        "title": "Manual del Residente de Medicina Intensiva - Hospital Universitario Virgen del Rocío",
        "specialty": "medicina_intensiva",
        "doc_type": "guia_formativa",
        "language": "es",
    },
    "UCI.pdf": {
        "title": "Estándares y Recomendaciones para Unidades de Cuidados Intensivos - Ministerio de Sanidad",
        "specialty": "medicina_intensiva",
        "doc_type": "protocolo",
        "language": "es",
    },
    "El Libro de la UCI Paul Marino 3a ed.pdf": {
        "title": "El Libro de la UCI - Paul L. Marino, 3ª Edición",
        "specialty": "medicina_intensiva",
        "doc_type": "manual",
        "language": "es",
    },
}


def main() -> int:
    from services.rag_service import RAGService

    # Verify PDFs exist
    pdf_paths = []
    for filename in PDF_METADATA:
        path = GUIAS_DIR / filename
        if not path.exists():
            logger.error("PDF not found: %s", path)
            return 1
        pdf_paths.append(str(path))
        logger.info("Found: %s", path)

    logger.info("Initializing RAG service...")
    rag = RAGService()

    # Check current state
    stats = rag.get_collection_stats()
    logger.info("Current collection stats: %s", stats)

    # Index each PDF with its metadata
    logger.info("Starting indexing of %d PDFs...", len(pdf_paths))
    for pdf_path in pdf_paths:
        filename = Path(pdf_path).name
        meta = PDF_METADATA.get(filename, {})
        logger.info("Indexing: %s", filename)
        result = rag.add_documents([pdf_path], metadata=meta)
        if result.get("success"):
            processed = result.get("processed_files", [])
            for p in processed:
                logger.info(
                    "  ✅ %s — %d parent chunks, %d child chunks",
                    p["file"],
                    p["parent_chunks"],
                    p["child_chunks"],
                )
        else:
            failed = result.get("failed_files", [])
            for f in failed:
                logger.error("  ❌ %s — %s", f["file"], f["error"])

    # Final stats
    stats_after = rag.get_collection_stats()
    logger.info("Collection stats after indexing: %s", stats_after)
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
