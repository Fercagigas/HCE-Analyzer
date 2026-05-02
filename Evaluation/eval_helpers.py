"""
Shared helper module for the ChatHCE Evaluation Framework.

Provides utilities for retry logic, TXT report formatting, filename generation,
MD5 computation, and agent instantiation used across all evaluation scripts.
"""

import hashlib
import logging
import sys
import time
from datetime import datetime
from importlib.metadata import version as pkg_version
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

def retry_on_rate_limit(
    func: Callable,
    *args: Any,
    max_retries: int = 3,
    wait_seconds: int = 60,
    **kwargs: Any,
) -> Any:
    """Retry a callable on rate-limit errors (HTTP 429 or RateLimitError).

    Args:
        func: The callable to invoke.
        *args: Positional arguments forwarded to func.
        max_retries: Maximum number of retry attempts after the first failure.
        wait_seconds: Seconds to wait between retries.
        **kwargs: Keyword arguments forwarded to func.

    Returns:
        The return value of func on success.

    Raises:
        The original exception after max_retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            exc_str = str(exc).lower()
            is_rate_limit = "429" in exc_str or "rate" in exc_str or "ratelimit" in type(exc).__name__.lower()
            if is_rate_limit and attempt < max_retries:
                logger.warning(
                    "Rate limit hit, waiting %ds (attempt %d/%d)",
                    wait_seconds,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_seconds)
                last_exc = exc
                continue
            raise
    # Should not reach here, but satisfy type checker
    raise RuntimeError(f"Max retries ({max_retries}) exceeded") from last_exc


def retry_on_connection_error(
    func: Callable,
    *args: Any,
    max_retries: int = 3,
    base_wait: int = 2,
    **kwargs: Any,
) -> Any:
    """Retry a callable on ConnectionError with exponential backoff.

    Args:
        func: The callable to invoke.
        *args: Positional arguments forwarded to func.
        max_retries: Maximum number of retry attempts after the first failure.
        base_wait: Base wait time in seconds; actual wait = base_wait * 2^attempt.
        **kwargs: Keyword arguments forwarded to func.

    Returns:
        The return value of func on success.

    Raises:
        ConnectionError after max_retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except ConnectionError as exc:
            if attempt < max_retries:
                wait = base_wait * (2 ** attempt)
                logger.warning(
                    "Connection error, retrying in %ds (attempt %d/%d): %s",
                    wait,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                time.sleep(wait)
                last_exc = exc
                continue
            raise
    raise RuntimeError(f"Max retries ({max_retries}) exceeded") from last_exc


# ---------------------------------------------------------------------------
# Library version helpers
# ---------------------------------------------------------------------------

def _get_lib_version(lib_name: str) -> str:
    """Return the installed version of a library, or 'N/A' if not found.

    Args:
        lib_name: The distribution package name (e.g. 'ragas', 'anthropic').

    Returns:
        Version string or 'N/A'.
    """
    try:
        return pkg_version(lib_name)
    except Exception:
        return "N/A"


def _get_model_name() -> str:
    """Return the primary model name from config.settings.

    Returns:
        Model name string, or 'N/A' if settings cannot be loaded.
    """
    try:
        from config.settings import settings  # type: ignore
        return settings.claude_agent.primary_model
    except Exception:
        return "N/A"


# ---------------------------------------------------------------------------
# TXT report formatting helpers
# ---------------------------------------------------------------------------

SEP_MAJOR = "=" * 80
SEP_MINOR = "-" * 80


def write_txt_header(
    f: Any,
    module_name: str,
    golden_set_path: Optional[str] = None,
) -> datetime:
    """Write the environment section header to an open file handle.

    Writes Python version, key library versions, model name, optional golden
    set filename with MD5 hash, and start timestamp.

    Args:
        f: An open writable file handle.
        module_name: Human-readable module name (e.g. 'RAGAS EVALUATION').
        golden_set_path: Optional path to the golden set file for MD5 hashing.

    Returns:
        The start_time datetime object (UTC-local).
    """
    start_time = datetime.now()
    timestamp_str = start_time.strftime("%Y%m%d %H:%M:%S")

    f.write(f"{SEP_MAJOR}\n")
    f.write(f"  EVALUATION FRAMEWORK - {module_name} RESULTS\n")
    f.write(f"  {timestamp_str}\n")
    f.write(f"{SEP_MAJOR}\n\n")

    f.write("ENVIRONMENT\n")
    f.write(f"  Python:               {sys.version.split()[0]}\n")
    f.write(f"  RAGAS:                {_get_lib_version('ragas')}\n")
    f.write(f"  LangChain:            {_get_lib_version('langchain')}\n")
    f.write(f"  LangChain-Anthropic:  {_get_lib_version('langchain-anthropic')}\n")
    f.write(f"  Anthropic SDK:        {_get_lib_version('anthropic')}\n")
    f.write(f"  Sentence-Transformers:{_get_lib_version('sentence-transformers')}\n")
    f.write(f"  Model:                {_get_model_name()}\n")

    if golden_set_path:
        try:
            md5 = compute_md5(golden_set_path)
            import os
            gs_filename = os.path.basename(golden_set_path)
            f.write(f"  Golden Set:           {gs_filename} (MD5: {md5})\n")
        except Exception as exc:
            logger.warning("Could not compute MD5 for %s: %s", golden_set_path, exc)
            f.write(f"  Golden Set:           {golden_set_path} (MD5: N/A)\n")

    f.write(f"  Start Time:           {timestamp_str}\n")
    f.write("\n")

    return start_time


def write_txt_summary(
    f: Any,
    summary_data: List[Dict[str, Any]],
) -> None:
    """Write a formatted summary table section to an open file handle.

    Args:
        f: An open writable file handle.
        summary_data: List of dicts with keys: name, score, threshold, status.
            - name (str): Metric or test name.
            - score (float): Achieved score.
            - threshold (float): Required threshold.
            - status (str): 'PASS' or 'FAIL'.
    """
    f.write(f"{SEP_MINOR}\n")
    f.write("SUMMARY\n")
    f.write(f"{SEP_MINOR}\n\n")

    # Column widths
    col_name = max((len(str(row.get("name", ""))) for row in summary_data), default=20)
    col_name = max(col_name, 20)

    header = f"  {'Metric':<{col_name}} | {'Score':>7} | {'Threshold':>9} | Status"
    divider = f"  {'-' * col_name}-+-{'-' * 7}-+-{'-' * 9}-+-------"
    f.write(header + "\n")
    f.write(divider + "\n")

    pass_count = 0
    for row in summary_data:
        name = str(row.get("name", ""))
        score = row.get("score", 0.0)
        threshold = row.get("threshold", 0.0)
        status = str(row.get("status", "FAIL"))
        if status == "PASS":
            pass_count += 1
        score_str = f"{score:.4f}" if isinstance(score, float) else str(score)
        threshold_str = f"{threshold:.4f}" if isinstance(threshold, float) else str(threshold)
        f.write(f"  {name:<{col_name}} | {score_str:>7} | {threshold_str:>9} | {status}\n")

    total = len(summary_data)
    overall = "PASS" if pass_count == total else "FAIL"
    f.write(f"\n  Overall: {overall} ({pass_count}/{total} metrics above threshold)\n\n")


def write_txt_conclusions(
    f: Any,
    conclusions_text: str,
    duration_seconds: float,
    total_items: int,
    error_count: int,
) -> None:
    """Write the conclusions section and footer to an open file handle.

    Args:
        f: An open writable file handle.
        conclusions_text: Human-readable analysis / conclusions paragraph.
        duration_seconds: Total execution time in seconds.
        total_items: Total number of questions/tests processed.
        error_count: Number of items that resulted in errors.
    """
    f.write(f"{SEP_MINOR}\n")
    f.write("CONCLUSIONS\n")
    f.write(f"{SEP_MINOR}\n\n")
    f.write(f"  {conclusions_text}\n\n")

    f.write(f"{SEP_MAJOR}\n")
    f.write(
        f"  Execution time: {duration_seconds:.1f}s"
        f" | Items: {total_items}"
        f" | Errors: {error_count}\n"
    )
    f.write(f"{SEP_MAJOR}\n")


# ---------------------------------------------------------------------------
# Filename generation
# ---------------------------------------------------------------------------

def generate_result_filename(module_name: str) -> str:
    """Return a result filename following the standard naming convention.

    Args:
        module_name: Module identifier (e.g. 'ragas', 'latency', 'security').

    Returns:
        Filename string in the form ``{module_name}_results_{YYYYMMDD_HHMMSS}.txt``.

    Example:
        >>> generate_result_filename("ragas")
        'ragas_results_20251115_143022.txt'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{module_name}_results_{timestamp}.txt"


# ---------------------------------------------------------------------------
# MD5 computation
# ---------------------------------------------------------------------------

def compute_md5(filepath: str) -> str:
    """Compute and return the MD5 hex digest of a file.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Lowercase hexadecimal MD5 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    hasher = hashlib.md5()
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Agent instantiation
# ---------------------------------------------------------------------------

def instantiate_agent() -> Any:
    """Import and return a new UnifiedChatAgent instance.

    Returns:
        A fresh ``UnifiedChatAgent`` instance from
        ``services.unified_chat.unified_agent``.

    Raises:
        ImportError: If the module cannot be imported.
        Exception: If the agent cannot be instantiated.
    """
    from services.unified_chat.unified_agent import UnifiedChatAgent  # type: ignore
    logger.info("Instantiating UnifiedChatAgent for evaluation")
    return UnifiedChatAgent()
