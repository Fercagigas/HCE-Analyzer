"""
Latency Benchmarks Script for ChatHCE.

Measures response times of the UnifiedChatAgent by tool category (DB, RAG, VIZ,
Complex). Executes each query n_runs times (plus 1 warmup) and computes per-category
statistics (mean, median, p95, p99, min, max). Results are written to a human-readable
TXT file in the output directory.

Usage:
    python evaluation/run_latency_benchmarks.py \\
        --n-runs 3 \\
        --output evaluation/results/
"""

import argparse
import logging
import os
import statistics
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from Evaluation.eval_helpers import (
    generate_result_filename,
    instantiate_agent,
    write_txt_conclusions,
    write_txt_header,
    write_txt_summary,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DELAY_BETWEEN_RUNS_SECONDS: int = 2

# p95 thresholds in milliseconds per category
THRESHOLDS_MS: Dict[str, float] = {
    "DB": 60000.0,
    "RAG": 90000.0,
    "VIZ": 120000.0,
    "Complex": 150000.0,
}

# ---------------------------------------------------------------------------
# Predefined queries (17 total)
# ---------------------------------------------------------------------------
QUERIES: List[Dict[str, str]] = [
    # DB queries (5)
    {
        "category": "DB",
        "query": "¿Cuáles son los diagnósticos del paciente 10014729?",
    },
    {
        "category": "DB",
        "query": "¿Cuáles son los signos vitales del paciente 10018328 en su estancia 34176810?",
    },
    {
        "category": "DB",
        "query": "¿Qué medicamentos se administraron al paciente 10026255?",
    },
    {
        "category": "DB",
        "query": "¿Cuál es la disposición final del paciente 10015272?",
    },
    {
        "category": "DB",
        "query": "¿Cuántas visitas tiene el paciente 10014354 en urgencias?",
    },
    # RAG queries (5)
    {
        "category": "RAG",
        "query": "¿Cuál es el protocolo de manejo de sepsis en urgencias?",
    },
    {
        "category": "RAG",
        "query": "¿Cuáles son las indicaciones de vancomicina en urgencias?",
    },
    {
        "category": "RAG",
        "query": "¿Cuál es el protocolo de triaje de Manchester?",
    },
    {
        "category": "RAG",
        "query": "¿Cómo se maneja la fibrilación auricular en urgencias?",
    },
    {
        "category": "RAG",
        "query": "¿Cuáles son los criterios de ingreso hospitalario desde urgencias?",
    },
    # VIZ queries (5)
    {
        "category": "VIZ",
        "query": "Genera una gráfica de la evolución de la frecuencia cardíaca del paciente 10014729",
    },
    {
        "category": "VIZ",
        "query": "Muestra un gráfico de barras de los diagnósticos más frecuentes en urgencias",
    },
    {
        "category": "VIZ",
        "query": "Crea una visualización de la distribución de acuidad de triaje",
    },
    {
        "category": "VIZ",
        "query": "Genera un gráfico de la presión arterial del paciente 10026255 en su estancia 34236274",
    },
    {
        "category": "VIZ",
        "query": "Muestra la distribución de medicamentos administrados en urgencias",
    },
    # Complex queries (2)
    {
        "category": "Complex",
        "query": (
            "Analiza los signos vitales del paciente 10014729, "
            "busca protocolos de sepsis y genera una gráfica de evolución"
        ),
    },
    {
        "category": "Complex",
        "query": (
            "Compara los diagnósticos del paciente 10026255 con las guías clínicas "
            "de fibrilación auricular y visualiza los signos vitales"
        ),
    },
]


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def compute_percentile(values: List[float], p: float) -> float:
    """Compute the p-th percentile of a list of values.

    Uses numpy if available; falls back to a manual linear-interpolation
    implementation otherwise.

    Args:
        values: List of numeric values (must be non-empty).
        p: Percentile to compute (0–100).

    Returns:
        The p-th percentile as a float. Returns 0.0 for empty input.
    """
    if not values:
        return 0.0

    try:
        import numpy as np  # type: ignore
        return float(np.percentile(values, p))
    except ImportError:
        pass

    # Manual fallback: linear interpolation
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = (p / 100) * (n - 1)
    lower = int(idx)
    upper = min(lower + 1, n - 1)
    frac = idx - lower
    return sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower])


def compute_category_stats(latencies_ms: List[float]) -> Dict[str, float]:
    """Compute descriptive statistics for a list of latency measurements.

    Args:
        latencies_ms: List of latency values in milliseconds (successful runs only).

    Returns:
        Dict with keys: mean, median, p95, p99, min, max.
        All values are 0.0 if the input list is empty.
    """
    if not latencies_ms:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}

    return {
        "mean": statistics.mean(latencies_ms),
        "median": statistics.median(latencies_ms),
        "p95": compute_percentile(latencies_ms, 95),
        "p99": compute_percentile(latencies_ms, 99),
        "min": min(latencies_ms),
        "max": max(latencies_ms),
    }


# ---------------------------------------------------------------------------
# Core benchmark logic
# ---------------------------------------------------------------------------

def run_single_query(
    agent: Any,
    query: str,
    run_number: int,
    category: str,
) -> Dict[str, Any]:
    """Execute a single query against the agent and measure latency.

    Args:
        agent: An instantiated ``UnifiedChatAgent``.
        query: The query string to send.
        run_number: The run index (for logging).
        category: The query category (for logging).

    Returns:
        Dict with keys: query, category, run_number, latency_ms (float or None),
        success (bool), error (str or None).
    """
    result: Dict[str, Any] = {
        "query": query,
        "category": category,
        "run_number": run_number,
        "latency_ms": None,
        "success": False,
        "error": None,
        "cache_bypass_active": True,
    }

    try:
        start = time.perf_counter()
        # Pass UUID as context to bypass cache (cache key includes context)
        cache_bypass_context = {"_eval_run_id": str(uuid.uuid4())}
        agent.process_message(query, context=cache_bypass_context, session_id=f"eval-latency-{category}-{run_number}")
        end = time.perf_counter()
        result["latency_ms"] = (end - start) * 1000
        result["success"] = True
    except Exception as exc:
        logger.error(
            "Error on run %d for category=%s query='%s...': %s",
            run_number,
            category,
            query[:60],
            exc,
        )
        result["error"] = str(exc)

    return result


def benchmark_query(
    agent: Any,
    query_def: Dict[str, str],
    n_runs: int,
) -> Tuple[List[Dict[str, Any]], List[float]]:
    """Run warmup + n_runs measured executions for a single query.

    Args:
        agent: An instantiated ``UnifiedChatAgent``.
        query_def: Dict with 'category' and 'query' keys.
        n_runs: Number of measured runs (warmup excluded).

    Returns:
        Tuple of (all_run_results, successful_latencies_ms).
        all_run_results includes the warmup (run_number=0) and measured runs.
        successful_latencies_ms contains only the latency_ms values from
        successful measured runs (warmup excluded).
    """
    category = query_def["category"]
    query = query_def["query"]
    all_results: List[Dict[str, Any]] = []

    # Warmup run (run_number=0, excluded from stats)
    logger.info("  Warmup run for: %s...", query[:60])
    warmup = run_single_query(agent, query, run_number=0, category=category)
    all_results.append(warmup)
    time.sleep(DELAY_BETWEEN_RUNS_SECONDS)

    # Measured runs
    successful_latencies: List[float] = []
    for i in range(1, n_runs + 1):
        logger.info("  Run %d/%d for: %s...", i, n_runs, query[:60])
        run_result = run_single_query(agent, query, run_number=i, category=category)
        all_results.append(run_result)

        if run_result["success"] and run_result["latency_ms"] is not None:
            successful_latencies.append(run_result["latency_ms"])

        if i < n_runs:
            time.sleep(DELAY_BETWEEN_RUNS_SECONDS)

    return all_results, successful_latencies


# ---------------------------------------------------------------------------
# TXT output
# ---------------------------------------------------------------------------

def write_results_txt(
    output_path: str,
    all_run_results: List[Dict[str, Any]],
    category_stats: Dict[str, Dict[str, float]],
    start_time: datetime,
    duration_seconds: float,
    n_runs: int,
) -> None:
    """Write the full latency benchmark results to a TXT file.

    Args:
        output_path: Full path to the output TXT file.
        all_run_results: Flat list of all run result dicts (warmup + measured).
        category_stats: Dict mapping category -> stats dict (mean, median, p95, ...).
        start_time: Benchmark start datetime.
        duration_seconds: Total elapsed seconds.
        n_runs: Number of measured runs per query.
    """
    error_count = sum(1 for r in all_run_results if not r["success"] and r["run_number"] > 0)
    total_measured = sum(1 for r in all_run_results if r["run_number"] > 0)

    with open(output_path, "w", encoding="utf-8") as f:
        write_txt_header(f, "LATENCY BENCHMARKS", golden_set_path=None)

        f.write(f"  Cache Bypass: ACTIVE (UUID session_id per run)\n\n")

        # ---- Per-query results section ----
        f.write("-" * 80 + "\n")
        f.write("RESULTS — PER QUERY RUNS\n")
        f.write("-" * 80 + "\n\n")

        # Group by category for display
        categories_order = ["DB", "RAG", "VIZ", "Complex"]
        for cat in categories_order:
            cat_runs = [r for r in all_run_results if r["category"] == cat and r["run_number"] > 0]
            if not cat_runs:
                continue

            f.write(f"  Category: {cat}\n")
            f.write(f"  {'Run':<5} | {'Latency (ms)':>14} | {'Status':<8} | Query (truncated)\n")
            f.write(f"  {'-' * 5}-+-{'-' * 14}-+-{'-' * 8}-+-{'-' * 40}\n")

            for r in cat_runs:
                lat_str = f"{r['latency_ms']:.1f}" if r["latency_ms"] is not None else "N/A"
                status = "OK" if r["success"] else "FAIL"
                q_short = r["query"][:50].replace("\n", " ")
                f.write(f"  {r['run_number']:<5} | {lat_str:>14} | {status:<8} | {q_short}\n")
                if r.get("error"):
                    f.write(f"  {'':>5}   {'':>14}   {'':>8}   Error: {r['error'][:70]}\n")
            f.write("\n")

        # ---- Per-category statistics section ----
        f.write("-" * 80 + "\n")
        f.write("RESULTS — PER CATEGORY STATISTICS\n")
        f.write("-" * 80 + "\n\n")

        f.write(
            f"  {'Category':<10} | {'Mean':>8} | {'Median':>8} | {'P95':>8} | "
            f"{'P99':>8} | {'Min':>8} | {'Max':>8} | {'Threshold':>10} | Status\n"
        )
        f.write(
            f"  {'-' * 10}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 8}-+"
            f"-{'-' * 8}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 10}-+-------\n"
        )

        for cat in categories_order:
            stats = category_stats.get(cat)
            if stats is None:
                continue
            threshold = THRESHOLDS_MS.get(cat, 0.0)
            p95 = stats["p95"]
            status = "PASS" if p95 < threshold else "FAIL"
            f.write(
                f"  {cat:<10} | {stats['mean']:>8.1f} | {stats['median']:>8.1f} | "
                f"{p95:>8.1f} | {stats['p99']:>8.1f} | {stats['min']:>8.1f} | "
                f"{stats['max']:>8.1f} | {threshold:>10.0f} | {status}\n"
            )
        f.write("\n")

        # ---- Summary section ----
        summary_data = []
        for cat in categories_order:
            stats = category_stats.get(cat)
            if stats is None:
                continue
            threshold = THRESHOLDS_MS.get(cat, 0.0)
            p95 = stats["p95"]
            summary_data.append({
                "name": cat,
                "score": p95,
                "threshold": threshold,
                "status": "PASS" if p95 < threshold else "FAIL",
            })

        write_txt_summary(f, summary_data)

        # ---- Conclusions section ----
        pass_cats = [d["name"] for d in summary_data if d["status"] == "PASS"]
        fail_cats = [d["name"] for d in summary_data if d["status"] == "FAIL"]
        overall = "PASS" if not fail_cats else "FAIL"

        conclusions_parts = [
            f"Overall result: {overall} ({len(pass_cats)}/{len(summary_data)} categories below p95 threshold).",
            f"Measured {n_runs} runs per query (plus 1 warmup) across {len(QUERIES)} queries.",
        ]
        if fail_cats:
            conclusions_parts.append(
                f"Categories exceeding p95 threshold: {', '.join(fail_cats)}."
            )
        if pass_cats:
            conclusions_parts.append(
                f"Categories within p95 threshold: {', '.join(pass_cats)}."
            )
        conclusions_parts.append(
            f"Total measured runs: {total_measured} | Failed runs: {error_count}."
        )

        write_txt_conclusions(
            f,
            conclusions_text=" ".join(conclusions_parts),
            duration_seconds=duration_seconds,
            total_items=total_measured,
            error_count=error_count,
        )

    logger.info("Results written to: %s", output_path)


# ---------------------------------------------------------------------------
# Summary to stdout
# ---------------------------------------------------------------------------

def print_summary_table(
    category_stats: Dict[str, Dict[str, float]],
    all_run_results: List[Dict[str, Any]],
) -> None:
    """Print a summary table of latency results to stdout.

    Args:
        category_stats: Dict mapping category -> stats dict.
        all_run_results: Flat list of all run result dicts.
    """
    sep = "-" * 70
    print(sep)
    print("  LATENCY BENCHMARKS SUMMARY")
    print(sep)
    print(
        f"  {'Category':<10} | {'P95 (ms)':>10} | {'Threshold':>10} | {'Mean (ms)':>10} | Status"
    )
    print(f"  {'-' * 10}-+-{'-' * 10}-+-{'-' * 10}-+-{'-' * 10}-+-------")

    categories_order = ["DB", "RAG", "VIZ", "Complex"]
    pass_count = 0
    for cat in categories_order:
        stats = category_stats.get(cat)
        if stats is None:
            continue
        threshold = THRESHOLDS_MS.get(cat, 0.0)
        p95 = stats["p95"]
        status = "PASS" if p95 < threshold else "FAIL"
        if status == "PASS":
            pass_count += 1
        print(
            f"  {cat:<10} | {p95:>10.1f} | {threshold:>10.0f} | {stats['mean']:>10.1f} | {status}"
        )

    total_cats = len([c for c in categories_order if c in category_stats])
    overall = "PASS" if pass_count == total_cats else "FAIL"
    print(f"\n  Overall: {overall} ({pass_count}/{total_cats} categories within p95 threshold)")

    error_count = sum(1 for r in all_run_results if not r["success"] and r["run_number"] > 0)
    total_measured = sum(1 for r in all_run_results if r["run_number"] > 0)
    print(f"\n  Measured runs: {total_measured} | Failed runs: {error_count}")
    print(sep)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional list of argument strings (defaults to sys.argv).

    Returns:
        Parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        description="Run latency benchmarks on ChatHCE UnifiedChatAgent.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--n-runs",
        type=int,
        default=3,
        help="Number of measured runs per query (warmup excluded).",
    )
    parser.add_argument(
        "--output",
        default="evaluation/results/",
        help="Output directory for the results TXT file.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the latency benchmarks script.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Exit code: 0 on success, 1 on fatal error.
    """
    args = parse_args(argv)
    n_runs: int = args.n_runs

    logger.info(
        "Starting latency benchmarks: %d queries, %d runs each (+1 warmup)",
        len(QUERIES),
        n_runs,
    )

    # ---- Ensure output directory exists ----
    os.makedirs(args.output, exist_ok=True)

    # ---- Instantiate agent ----
    try:
        agent = instantiate_agent()
    except Exception as exc:
        logger.error("Failed to instantiate UnifiedChatAgent: %s", exc)
        return 1

    # ---- Run benchmarks ----
    all_run_results: List[Dict[str, Any]] = []
    # Collect latencies per category for stats computation
    category_latencies: Dict[str, List[float]] = {cat: [] for cat in THRESHOLDS_MS}

    start_time = datetime.now()

    for idx, query_def in enumerate(QUERIES, start=1):
        cat = query_def["category"]
        logger.info(
            "Benchmarking query %d/%d [%s]: %s...",
            idx,
            len(QUERIES),
            cat,
            query_def["query"][:60],
        )

        run_results, successful_latencies = benchmark_query(agent, query_def, n_runs)
        all_run_results.extend(run_results)
        category_latencies.setdefault(cat, []).extend(successful_latencies)

    end_time = datetime.now()
    duration_seconds = (end_time - start_time).total_seconds()

    # ---- Compute per-category statistics ----
    category_stats: Dict[str, Dict[str, float]] = {}
    for cat, latencies in category_latencies.items():
        if latencies:
            category_stats[cat] = compute_category_stats(latencies)
            logger.info(
                "Category %s stats: mean=%.1fms p95=%.1fms (threshold=%.0fms) — %s",
                cat,
                category_stats[cat]["mean"],
                category_stats[cat]["p95"],
                THRESHOLDS_MS.get(cat, 0),
                "PASS" if category_stats[cat]["p95"] < THRESHOLDS_MS.get(cat, float("inf")) else "FAIL",
            )
        else:
            logger.warning("No successful runs for category: %s", cat)

    # ---- Write results TXT ----
    filename = generate_result_filename("latency")
    output_path = os.path.join(args.output, filename)

    try:
        write_results_txt(
            output_path=output_path,
            all_run_results=all_run_results,
            category_stats=category_stats,
            start_time=start_time,
            duration_seconds=duration_seconds,
            n_runs=n_runs,
        )
    except Exception as exc:
        logger.error("Failed to write results TXT: %s", exc)

    # ---- Print summary to stdout ----
    print_summary_table(category_stats, all_run_results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
