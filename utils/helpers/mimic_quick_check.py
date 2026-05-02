"""
MIMIC quick connectivity check utilities.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def check_mimic_connectivity() -> Dict[str, Any]:
    """
    Quick check to verify connectivity to the MIMIC-IV-ED dataset in Supabase.

    Returns:
        Dict with keys: connected (bool), tables_accessible (list), error (str or None)
    """
    result: Dict[str, Any] = {
        "connected": False,
        "tables_accessible": [],
        "error": None,
    }

    try:
        from supabase import create_client
        from config.settings import settings

        client = create_client(
            settings.database.supabase_url,
            settings.database.supabase_key,
        )

        mimic_tables = ["edstays", "triage", "vitalsign", "diagnosis", "medrecon", "pyxis"]
        accessible = []

        for table in mimic_tables:
            try:
                client.schema("mimic_ed").table(table).select("*").limit(1).execute()
                accessible.append(table)
            except Exception:
                # Try without schema prefix (public schema fallback)
                try:
                    client.table(table).select("*").limit(1).execute()
                    accessible.append(table)
                except Exception:
                    pass

        result["connected"] = len(accessible) > 0
        result["tables_accessible"] = accessible

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"MIMIC connectivity check failed: {e}")

    return result


def quick_mimic_check() -> bool:
    """
    Simplified boolean check for MIMIC-IV-ED connectivity.

    Returns:
        True if at least one MIMIC table is accessible, False otherwise.
    """
    result = check_mimic_connectivity()
    return result["connected"]


__all__ = ["quick_mimic_check", "check_mimic_connectivity"]
