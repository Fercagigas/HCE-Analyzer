"""
Evaluation Orchestrator for ChatHCE.

Executes all four evaluation modules sequentially:
  1. RAGAS evaluation (faithfulness, relevancy, precision, recall)
  2. Latency benchmarks (p95 per tool category)
  3. Security tests (SQL injection, prompt injection, anti-hallucination)
  4. Functional test cases (TC-DB, TC-RAG, TC-VIZ, TC-AGENT)

Generates a consolidated TXT report and saves execution logs to file.

Usage:
    python evaluation/run_all_evaluations.py [options]

    --skip-ragas          Skip RAGAS evaluation module
    --skip-latency        Skip latency benchmarks module
    --skip-security       Skip security tests module
    --skip-test-cases     Skip functional test cases module
    --output-dir DIR      Results directory (default: evaluation/results/)
    --dry-run             Pre-flight checks and cost estimate only, no API calls
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Cargar variables de entorno desde .env antes de cualquier otra importación
from dotenv import load_dotenv
load_dotenv()

from Evaluation.eval_helpers import (
    compute_md5,
    write_txt_conclusions,
    write_txt_header,
    write_txt_summary,
)

# ---------------------------------------------------------------------------
# Module name constant
# ---------------------------------------------------------------------------
MODULE_NAME = "EVALUATION ORCHESTRATOR"

# ---------------------------------------------------------------------------
# Cost estimates (USD) per module
# ---------------------------------------------------------------------------
_COST_ESTIMATES: Dict[str, Dict[str, Any]] = {
    "ragas_db": {
        "description": "RAGAS DB: ~40 questions * $0.001",
        "cost": 0.04,
    },
    "ragas_rag": {
        "description": "RAGAS RAG: ~30 questions * $0.001",
        "cost": 0.03,
    },
    "latency": {
        "description": "Latency: ~17 queries * 4 runs * $0.001",
        "cost": 0.07,
    },
    "security": {
        "description": "Security: ~11 tests * $0.001",
        "cost": 0.01,
    },
    "test_cases": {
        "description": "Functional: ~28 tests * $0.001",
        "cost": 0.03,
    },
}
_TOTAL_COST_ESTIMATE: float = sum(v["cost"] for v in _COST_ESTIMATES.values())

# Golden set file paths
_GOLDEN_SET_DB = "evaluation/golden_set_ragas.json"
_GOLDEN_SET_RAG = "evaluation/golden_set_ragas_rag.json"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_path: str) -> logging.Logger:
    """Configure root logger to write to stdout and a log file.

    Args:
        log_path: Full path to the log file.

    Returns:
        Configured logger for this module.
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: List[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers, force=True)
    return logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def check_golden_set_files() -> List[str]:
    """Verify that required golden set files exist.

    Returns:
        List of error strings; empty list means all files are present.
    """
    errors: List[str] = []
    for path in [_GOLDEN_SET_DB, _GOLDEN_SET_RAG]:
        if not os.path.isfile(path):
            errors.append(f"Golden set file not found: {path}")
    return errors


def check_api_key() -> List[str]:
    """Verify that ANTHROPIC_API_KEY environment variable is set.

    Returns:
        List of error strings; empty list means the key is present.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ["ANTHROPIC_API_KEY environment variable is not set."]
    return []


def check_supabase_connection() -> List[str]:
    """Verify that Supabase connection is available.

    Uses a lightweight REST ping instead of querying mimic_ed directly,
    since the anon key may not have schema-level permissions via REST.

    Returns:
        List of error strings; empty list means connection is available.
    """
    try:
        from config.settings import settings  # type: ignore
        import httpx

        # Ping the REST root — any 2xx/404 means Supabase is reachable
        resp = httpx.get(
            settings.database.supabase_url.rstrip("/") + "/rest/v1/",
            headers={"apikey": settings.database.supabase_key},
            timeout=8.0,
        )
        if resp.status_code in (200, 404):
            return []
        return [f"Supabase HTTP {resp.status_code}: {resp.text[:120]}"]
    except ImportError as exc:
        return [f"Supabase import error: {exc}"]
    except Exception as exc:
        return [f"Supabase connection error: {exc}"]



def ensure_results_directory(output_dir: str) -> List[str]:
    """Create the results directory if it does not exist.

    Args:
        output_dir: Path to the results directory.

    Returns:
        List of error strings; empty list means directory is ready.
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        return []
    except OSError as exc:
        return [f"Cannot create results directory '{output_dir}': {exc}"]


def run_preflight_checks(output_dir: str) -> Dict[str, Any]:
    """Run all pre-flight checks and return a summary dict.

    Args:
        output_dir: Path to the results directory.

    Returns:
        Dict with keys:
            - passed (bool): True if all checks passed.
            - errors (List[str]): All error messages collected.
            - checks (Dict[str, bool]): Per-check pass/fail status.
    """
    checks: Dict[str, bool] = {}
    all_errors: List[str] = []

    # 1. Golden set files
    errs = check_golden_set_files()
    checks["golden_set_files"] = len(errs) == 0
    all_errors.extend(errs)

    # 2. API key
    errs = check_api_key()
    checks["anthropic_api_key"] = len(errs) == 0
    all_errors.extend(errs)

    # 3. Supabase connection
    errs = check_supabase_connection()
    checks["supabase_connection"] = len(errs) == 0
    all_errors.extend(errs)

    # 4. Results directory
    errs = ensure_results_directory(output_dir)
    checks["results_directory"] = len(errs) == 0
    all_errors.extend(errs)

    return {
        "passed": len(all_errors) == 0,
        "errors": all_errors,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Module execution
# ---------------------------------------------------------------------------

def _run_module(
    module_key: str,
    module_label: str,
    main_func: Any,
    argv: List[str],
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Execute a single evaluation module and return a result summary.

    Args:
        module_key: Short key for the module (e.g. 'ragas').
        module_label: Human-readable label (e.g. 'RAGAS Evaluation').
        main_func: The module's main() callable.
        argv: CLI arguments to pass to the module's main().
        logger: Logger instance.

    Returns:
        Dict with keys: module_key, module_label, status ('passed'/'failed'/'skipped'),
        exit_code (int or None), error (str or None), start_time, end_time,
        duration_seconds.
    """
    result: Dict[str, Any] = {
        "module_key": module_key,
        "module_label": module_label,
        "status": "failed",
        "exit_code": None,
        "error": None,
        "start_time": None,
        "end_time": None,
        "duration_seconds": 0.0,
    }

    logger.info("=" * 60)
    logger.info("Starting module: %s", module_label)
    logger.info("=" * 60)

    start = datetime.now()
    result["start_time"] = start.strftime("%Y%m%d %H:%M:%S")

    try:
        exit_code = main_func(argv)
        result["exit_code"] = exit_code
        result["status"] = "passed" if exit_code == 0 else "failed"
        logger.info("Module %s completed with exit code %d", module_label, exit_code)
    except Exception as exc:
        result["error"] = str(exc)
        result["status"] = "failed"
        logger.error("Module %s raised an unrecoverable error: %s", module_label, exc)

    end = datetime.now()
    result["end_time"] = end.strftime("%Y%m%d %H:%M:%S")
    result["duration_seconds"] = (end - start).total_seconds()

    return result


# ---------------------------------------------------------------------------
# Consolidated TXT report
# ---------------------------------------------------------------------------

def write_consolidated_report(
    output_path: str,
    module_results: List[Dict[str, Any]],
    preflight: Dict[str, Any],
    start_time: datetime,
    duration_seconds: float,
) -> None:
    """Write the consolidated evaluation report to a TXT file.

    Args:
        output_path: Full path to the consolidated report TXT file.
        module_results: List of module result dicts from _run_module().
        preflight: Pre-flight check result dict from run_preflight_checks().
        start_time: Overall orchestration start datetime.
        duration_seconds: Total elapsed seconds for the full run.
    """
    error_count = sum(1 for r in module_results if r["status"] == "failed")
    total_modules = len(module_results)

    with open(output_path, "w", encoding="utf-8") as f:
        write_txt_header(f, MODULE_NAME, golden_set_path=_GOLDEN_SET_DB)

        # ---- Pre-flight checks section ----
        f.write("-" * 80 + "\n")
        f.write("PRE-FLIGHT CHECKS\n")
        f.write("-" * 80 + "\n\n")

        check_labels = {
            "golden_set_files": "Golden set files exist",
            "anthropic_api_key": "ANTHROPIC_API_KEY set",
            "supabase_connection": "Supabase connection available",
            "results_directory": "Results directory ready",
        }
        for check_key, check_label in check_labels.items():
            status = "OK" if preflight["checks"].get(check_key, False) else "FAIL"
            f.write(f"  [{status}] {check_label}\n")

        if preflight["errors"]:
            f.write("\n  Errors:\n")
            for err in preflight["errors"]:
                f.write(f"    - {err}\n")
        f.write("\n")

        # ---- Module results section ----
        f.write("-" * 80 + "\n")
        f.write("MODULE RESULTS\n")
        f.write("-" * 80 + "\n\n")

        f.write(
            f"  {'Module':<30} | {'Status':<8} | {'Duration':>10} | "
            f"{'Start':<19} | {'End':<19}\n"
        )
        f.write(
            f"  {'-' * 30}-+-{'-' * 8}-+-{'-' * 10}-+-{'-' * 19}-+-{'-' * 19}\n"
        )

        for r in module_results:
            status_str = r["status"].upper()
            dur_str = f"{r['duration_seconds']:.1f}s"
            start_str = r.get("start_time", "N/A")
            end_str = r.get("end_time", "N/A")
            f.write(
                f"  {r['module_label']:<30} | {status_str:<8} | {dur_str:>10} | "
                f"{start_str:<19} | {end_str:<19}\n"
            )
            if r.get("error"):
                f.write(f"  {'':30}   Error: {r['error'][:70]}\n")

        f.write("\n")

        # ---- Summary section ----
        summary_data = [
            {
                "name": r["module_label"],
                "score": 1.0 if r["status"] == "passed" else 0.0,
                "threshold": 1.0,
                "status": "PASS" if r["status"] == "passed" else "FAIL",
            }
            for r in module_results
        ]
        write_txt_summary(f, summary_data)

        # ---- Conclusions section ----
        passed_modules = [r["module_label"] for r in module_results if r["status"] == "passed"]
        failed_modules = [r["module_label"] for r in module_results if r["status"] == "failed"]
        skipped_modules = [r["module_label"] for r in module_results if r["status"] == "skipped"]
        overall = "PASS" if not failed_modules else "FAIL"

        conclusions_parts = [
            f"Overall result: {overall} "
            f"({len(passed_modules)}/{total_modules} modules completed successfully).",
        ]
        if passed_modules:
            conclusions_parts.append(
                f"Modules passed: {', '.join(passed_modules)}."
            )
        if failed_modules:
            conclusions_parts.append(
                f"Modules failed: {', '.join(failed_modules)}. "
                "Review individual module logs for details."
            )
        if skipped_modules:
            conclusions_parts.append(
                f"Modules skipped: {', '.join(skipped_modules)}."
            )

        write_txt_conclusions(
            f,
            conclusions_text=" ".join(conclusions_parts),
            duration_seconds=duration_seconds,
            total_items=total_modules,
            error_count=error_count,
        )


# ---------------------------------------------------------------------------
# Dry-run cost estimate
# ---------------------------------------------------------------------------

def print_cost_estimate(skip_ragas: bool, skip_latency: bool, skip_security: bool, skip_test_cases: bool) -> None:
    """Print API cost estimates for the planned evaluation run.

    Args:
        skip_ragas: Whether RAGAS module is skipped.
        skip_latency: Whether latency module is skipped.
        skip_security: Whether security module is skipped.
        skip_test_cases: Whether test cases module is skipped.
    """
    sep = "=" * 60
    print(sep)
    print("  API COST ESTIMATE (DRY-RUN)")
    print(sep)

    skip_map = {
        "ragas_db": skip_ragas,
        "ragas_rag": skip_ragas,
        "latency": skip_latency,
        "security": skip_security,
        "test_cases": skip_test_cases,
    }

    total = 0.0
    for key, info in _COST_ESTIMATES.items():
        if skip_map.get(key, False):
            print(f"  [SKIP] {info['description']:<45} $0.00")
        else:
            print(f"  [RUN]  {info['description']:<45} ~${info['cost']:.2f}")
            total += info["cost"]

    print(f"  {'-' * 55}")
    print(f"  {'Total estimated cost':<45} ~${total:.2f}")
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
        description="Run all ChatHCE evaluation modules and generate a consolidated report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Skip the RAGAS evaluation module.",
    )
    parser.add_argument(
        "--skip-latency",
        action="store_true",
        help="Skip the latency benchmarks module.",
    )
    parser.add_argument(
        "--skip-security",
        action="store_true",
        help="Skip the security tests module.",
    )
    parser.add_argument(
        "--skip-test-cases",
        action="store_true",
        help="Skip the functional test cases module.",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/results/",
        help="Directory where all result files and logs are written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform pre-flight checks and estimate costs only. No API calls are made.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the evaluation orchestrator.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Exit code: 0 on success, 1 if any module failed or pre-flight failed.
    """
    args = parse_args(argv)
    output_dir: str = args.output_dir

    # ---- Set up log file (create output dir first if needed) ----
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"evaluation_{timestamp}.log"
    log_path = os.path.join(output_dir, log_filename)
    logger = setup_logging(log_path)

    logger.info("Evaluation Orchestrator starting — timestamp: %s", timestamp)
    logger.info("Output directory: %s", output_dir)
    logger.info("Log file: %s", log_path)

    # ---- Pre-flight checks ----
    logger.info("Running pre-flight checks...")
    preflight = run_preflight_checks(output_dir)

    for check_name, passed in preflight["checks"].items():
        status = "OK" if passed else "FAIL"
        logger.info("  Pre-flight [%s]: %s", status, check_name)

    if preflight["errors"]:
        for err in preflight["errors"]:
            logger.error("  Pre-flight error: %s", err)

    # ---- Dry-run: print checks + cost estimate and exit ----
    if args.dry_run:
        print("\n" + "=" * 60)
        print("  DRY-RUN MODE — no API calls will be made")
        print("=" * 60)

        print("\n  PRE-FLIGHT CHECKS:")
        check_labels = {
            "golden_set_files": "Golden set files exist",
            "anthropic_api_key": "ANTHROPIC_API_KEY set",
            "supabase_connection": "Supabase connection available",
            "results_directory": "Results directory ready",
        }
        all_ok = True
        for key, label in check_labels.items():
            status = "OK  " if preflight["checks"].get(key, False) else "FAIL"
            if status == "FAIL":
                all_ok = False
            print(f"    [{status}] {label}")

        if preflight["errors"]:
            print("\n  Errors:")
            for err in preflight["errors"]:
                print(f"    - {err}")

        print()
        print_cost_estimate(
            skip_ragas=args.skip_ragas,
            skip_latency=args.skip_latency,
            skip_security=args.skip_security,
            skip_test_cases=args.skip_test_cases,
        )

        overall_status = "READY" if all_ok else "NOT READY (fix errors above)"
        print(f"\n  System status: {overall_status}")
        print(f"  Log file: {log_path}\n")

        return 0 if all_ok else 1

    # ---- Abort if critical pre-flight checks failed ----
    if not preflight["passed"]:
        logger.error(
            "Pre-flight checks failed. Aborting evaluation. Fix the errors above and retry."
        )
        return 1

    # ---- Import module main() functions ----
    try:
        from Evaluation.run_ragas_eval import main as ragas_main  # type: ignore
        from Evaluation.run_latency_benchmarks import main as latency_main  # type: ignore
        from Evaluation.run_security_tests import main as security_main  # type: ignore
        from Evaluation.run_test_cases import main as test_cases_main  # type: ignore
    except ImportError as exc:
        logger.error("Failed to import evaluation modules: %s", exc)
        return 1

    # ---- Build module execution plan ----
    # RAGAS runs twice: once per golden set (DB queries and RAG documents)
    modules_to_run: List[Dict[str, Any]] = [
        {
            "key": "ragas_db",
            "label": "RAGAS Evaluation (DB)",
            "main": ragas_main,
            "skip": args.skip_ragas,
            "argv": [
                "--output", output_dir,
                "--golden-set", _GOLDEN_SET_DB,
                "--subset", "db",
            ],
        },
        {
            "key": "ragas_rag",
            "label": "RAGAS Evaluation (RAG)",
            "main": ragas_main,
            "skip": args.skip_ragas,
            "argv": [
                "--output", output_dir,
                "--golden-set", _GOLDEN_SET_RAG,
                "--subset", "rag",
            ],
        },
        {
            "key": "latency",
            "label": "Latency Benchmarks",
            "main": latency_main,
            "skip": args.skip_latency,
            "argv": ["--output", output_dir],
        },
        {
            "key": "security",
            "label": "Security Tests",
            "main": security_main,
            "skip": args.skip_security,
            "argv": ["--output", output_dir],
        },
        {
            "key": "test_cases",
            "label": "Functional Test Cases",
            "main": test_cases_main,
            "skip": args.skip_test_cases,
            "argv": ["--output", output_dir],
        },
    ]

    # ---- Execute modules sequentially ----
    overall_start = datetime.now()
    module_results: List[Dict[str, Any]] = []

    for module_def in modules_to_run:
        if module_def["skip"]:
            logger.info("Skipping module: %s (--skip flag set)", module_def["label"])
            module_results.append({
                "module_key": module_def["key"],
                "module_label": module_def["label"],
                "status": "skipped",
                "exit_code": None,
                "error": None,
                "start_time": datetime.now().strftime("%Y%m%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y%m%d %H:%M:%S"),
                "duration_seconds": 0.0,
            })
            continue

        result = _run_module(
            module_key=module_def["key"],
            module_label=module_def["label"],
            main_func=module_def["main"],
            argv=module_def["argv"],
            logger=logger,
        )
        module_results.append(result)

    overall_end = datetime.now()
    total_duration = (overall_end - overall_start).total_seconds()

    # ---- Generate consolidated report ----
    report_filename = f"consolidated_report_{timestamp}.txt"
    report_path = os.path.join(output_dir, report_filename)

    try:
        write_consolidated_report(
            output_path=report_path,
            module_results=module_results,
            preflight=preflight,
            start_time=overall_start,
            duration_seconds=total_duration,
        )
        logger.info("Consolidated report written to: %s", report_path)
    except Exception as exc:
        logger.error("Failed to write consolidated report: %s", exc)

    # ---- Print final summary to stdout ----
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  EVALUATION ORCHESTRATOR — FINAL SUMMARY")
    print(sep)
    passed_count = sum(1 for r in module_results if r["status"] == "passed")
    failed_count = sum(1 for r in module_results if r["status"] == "failed")
    skipped_count = sum(1 for r in module_results if r["status"] == "skipped")
    total_count = len(module_results)

    for r in module_results:
        status_str = r["status"].upper()
        dur_str = f"{r['duration_seconds']:.1f}s"
        print(f"  [{status_str:<8}] {r['module_label']:<30} ({dur_str})")

    overall_label = "PASS" if failed_count == 0 else "FAIL"
    print(f"\n  Overall: {overall_label} — {passed_count} passed, {failed_count} failed, {skipped_count} skipped")
    print(f"  Total duration: {total_duration:.1f}s")
    print(f"  Consolidated report: {report_path}")
    print(f"  Log file: {log_path}")
    print(sep)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
