"""
RAGAS Evaluation Script for ChatHCE.

Runs RAGAS metrics (faithfulness, answer_relevancy, context_precision,
context_recall) against the UnifiedChatAgent using a golden set JSON file.
Results are written to a human-readable TXT file in the output directory.

Usage:
    python evaluation/run_ragas_eval.py \\
        --golden-set evaluation/golden_set_ragas.json \\
        --output evaluation/results/ \\
        --subset db \\
        --max-samples 10 \\
        --dry-run
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Cargar variables de entorno ANTES de cualquier import que las necesite
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Optional RAGAS imports — legacy ragas.metrics API with LangchainLLMWrapper
# Works with RAGAS 0.4 + instructor 1.x (avoids instructor schema conflicts)
# ---------------------------------------------------------------------------
try:
    from langchain_anthropic import ChatAnthropic
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.metrics import (  # noqa: deprecated but functional in 0.4
        faithfulness as _faithfulness_metric,
        answer_relevancy as _answer_relevancy_metric,
        context_precision as _context_precision_metric,
        context_recall as _context_recall_metric,
    )
    from ragas import evaluate as ragas_evaluate
    from datasets import Dataset as HFDataset

    _lc_llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        temperature=0,
    )
    evaluator_llm = LangchainLLMWrapper(_lc_llm)
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )

    _faithfulness_metric.llm = evaluator_llm
    _answer_relevancy_metric.llm = evaluator_llm
    _answer_relevancy_metric.embeddings = evaluator_embeddings
    _context_precision_metric.llm = evaluator_llm
    _context_recall_metric.llm = evaluator_llm

    RAGAS_METRICS = [
        _faithfulness_metric,
        _answer_relevancy_metric,
        _context_precision_metric,
        _context_recall_metric,
    ]
    RAGAS_AVAILABLE = True
except (ImportError, ValueError, Exception):
    RAGAS_AVAILABLE = False
    RAGAS_METRICS = []

from Evaluation.eval_helpers import (
    compute_md5,
    generate_result_filename,
    instantiate_agent,
    retry_on_rate_limit,
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
THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.70,
}

REQUIRED_QUESTION_FIELDS = [
    "id",
    "question",
    "ground_truth",
    "contexts",
]

# Fields only present in the DB golden set (optional for RAG golden set)
OPTIONAL_QUESTION_FIELDS = [
    "ground_truth_sql",
    "category",
]


# ---------------------------------------------------------------------------
# Golden set helpers
# ---------------------------------------------------------------------------

def _normalize_question(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a question entry to the canonical internal format.

    Supports two source formats:
    - DB golden set: uses ``question``, ``ground_truth``, ``contexts``, ``category``
    - RAG golden set: uses ``pregunta``, ``respuesta_referencia``, ``contextos``

    Args:
        raw: Raw question dict as loaded from JSON.

    Returns:
        Normalized dict with canonical field names.
    """
    normalized = dict(raw)

    # Map RAG golden set field names to canonical names
    if "question" not in normalized and "pregunta" in normalized:
        normalized["question"] = normalized["pregunta"]
    if "ground_truth" not in normalized and "respuesta_referencia" in normalized:
        normalized["ground_truth"] = normalized["respuesta_referencia"]
    if "contexts" not in normalized and "contextos" in normalized:
        normalized["contexts"] = normalized["contextos"]
    if "category" not in normalized and "tipo" in normalized:
        normalized["category"] = normalized["tipo"]

    return normalized


def load_golden_set(path: str) -> Dict[str, Any]:
    """Load and return the golden set JSON from *path*.

    Supports two top-level formats:
    - DB golden set: ``{"questions": [...], "metadata": {...}}``
    - RAG golden set: ``{"golden_set": [...], "metadata": {...}}``

    All question entries are normalized to the canonical internal format
    via :func:`_normalize_question`.

    Args:
        path: Filesystem path to the golden set JSON file.

    Returns:
        Parsed JSON as a dict with ``metadata`` and ``questions`` keys,
        where ``questions`` contains normalized question dicts.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is missing both ``questions`` and ``golden_set`` keys.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Golden set file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Support both key names
    if "questions" in data:
        raw_questions = data["questions"]
    elif "golden_set" in data:
        raw_questions = data["golden_set"]
        # Expose under the canonical key so callers always use "questions"
        data["questions"] = raw_questions
    else:
        raise ValueError(
            "Golden set JSON is missing both 'questions' and 'golden_set' keys."
        )

    # Normalize all entries in-place
    data["questions"] = [_normalize_question(q) for q in raw_questions]

    return data


def validate_question(question: Dict[str, Any]) -> List[str]:
    """Return a list of validation errors for a single question dict.

    Only the fields in REQUIRED_QUESTION_FIELDS are mandatory.
    Fields in OPTIONAL_QUESTION_FIELDS are allowed to be absent.

    Args:
        question: A normalized question dict from the golden set.

    Returns:
        List of error strings; empty list means the question is valid.
    """
    errors: List[str] = []
    for field in REQUIRED_QUESTION_FIELDS:
        if field not in question:
            errors.append(f"Missing field: '{field}'")
        elif not question[field]:
            errors.append(f"Empty field: '{field}'")

    contexts = question.get("contexts")
    if isinstance(contexts, list) and len(contexts) == 0:
        errors.append("'contexts' must be a non-empty list")

    return errors


def filter_questions(
    questions: List[Dict[str, Any]],
    subset: str,
    max_samples: Optional[int],
) -> List[Dict[str, Any]]:
    """Filter and limit the question list.

    Args:
        questions: Full list of normalized question dicts.
        subset: One of ``'db'``, ``'rag'``, or ``'all'``.
            - ``'db'``: keeps questions whose id starts with ``DB-``
            - ``'rag'``: keeps questions whose id starts with ``RAG-`` or ``GS-RAG-``
            - ``'all'``: no id-based filtering
        max_samples: Optional upper limit on the number of questions returned.

    Returns:
        Filtered (and optionally truncated) list of question dicts.
    """
    if subset == "db":
        questions = [q for q in questions if q.get("id", "").startswith("DB-")]
    elif subset == "rag":
        questions = [
            q for q in questions
            if q.get("id", "").startswith("RAG-") or q.get("id", "").startswith("GS-RAG-")
        ]
    # subset == "all" → no filtering

    if max_samples is not None and max_samples > 0:
        questions = questions[:max_samples]

    return questions


# ---------------------------------------------------------------------------
# Context extraction
# ---------------------------------------------------------------------------

def extract_contexts(response: Dict[str, Any]) -> List[str]:
    """Extract context strings from an agent response dict.

    Combines ``sources`` (RAG) and ``tool_results`` (DB) into a flat list
    of strings suitable for RAGAS.

    For RAG sources, prefers ``retrieved_content`` (actual document text).
    For DB tool results, uses the structured data.

    Args:
        response: The dict returned by ``UnifiedChatAgent.process_message()``.

    Returns:
        List of context strings (may be empty).
    """
    contexts: List[str] = []

    # RAG sources — prefer retrieved_content (actual document text) over content (citation string)
    for src in response.get("sources", []) or []:
        if isinstance(src, dict):
            text = (
                src.get("retrieved_content")   # actual text from the document
                or src.get("content")           # fallback: citation string
                or src.get("text")
                or src.get("page_content")
                or str(src)
            )
        else:
            text = str(src)
        if text and len(text) > 20:  # skip trivially short strings
            contexts.append(text)

    # Tool results (DB / VIZ / RAG raw output)
    for tr in response.get("tool_results", []) or []:
        if isinstance(tr, dict):
            # For RAG tool results, extract document content directly
            tool_name = tr.get("tool", "")
            if "search_clinical_documents" in str(tool_name):
                # Extract from raw observation if available
                raw = tr.get("raw_observation") or tr.get("result") or tr.get("content") or tr.get("output")
                if isinstance(raw, str) and "--- Documento" in raw:
                    # Parse document sections directly from formatted output
                    import re as _re
                    doc_pattern = _re.compile(
                        r'--- Documento \d+: .+? ---\n(.*?)(?=\n--- Documento \d+:|=== FUENTES CITADAS ===|\Z)',
                        _re.DOTALL
                    )
                    for match in doc_pattern.finditer(raw):
                        doc_text = match.group(1).strip()
                        if doc_text and len(doc_text) > 20:
                            contexts.append(doc_text)
                    continue

            text = (
                tr.get("result")
                or tr.get("content")
                or tr.get("output")
                or tr.get("data")
            )
            if isinstance(text, (dict, list)):
                text = json.dumps(text, ensure_ascii=False)
            elif text is None:
                text = str(tr)
        else:
            text = str(tr)
        if text and len(str(text)) > 20:
            contexts.append(str(text))

    # Fallback: if no contexts found, use the answer itself so RAGAS doesn't crash
    if not contexts:
        answer = response.get("content", "")
        if answer:
            contexts.append(answer)

    return contexts


# ---------------------------------------------------------------------------
# Per-question evaluation
# ---------------------------------------------------------------------------

def process_question(
    agent: Any,
    question: Dict[str, Any],
) -> Dict[str, Any]:
    """Call the agent for a single question and return a result dict.

    Args:
        agent: An instantiated ``UnifiedChatAgent``.
        question: A question dict from the golden set.

    Returns:
        Dict with keys: ``question_id``, ``question``, ``answer``,
        ``contexts``, ``ground_truth``, ``error``.
    """
    q_id = question["id"]
    q_text = question["question"]
    ground_truth = question["ground_truth"]

    result: Dict[str, Any] = {
        "question_id": q_id,
        "question": q_text,
        "answer": "ERROR",
        "contexts": [],
        "ground_truth": ground_truth,
        "error": None,
    }

    try:
        def _call() -> Dict[str, Any]:
            return agent.process_message(
                q_text,
                context=None,
                session_id=f"eval-ragas-{q_id}",
            )

        response = retry_on_rate_limit(_call, max_retries=3, wait_seconds=60)
        result["answer"] = response.get("content", "")
        result["contexts"] = extract_contexts(response)
    except Exception as exc:
        logger.error("Error processing question %s: %s", q_id, exc)
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Per-sample RAGAS scoring with single_turn_ascore
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-sample RAGAS scoring using ragas.evaluate (legacy Dataset API)
# ---------------------------------------------------------------------------

def score_sample(
    pregunta: str,
    respuesta: str,
    contextos: List[str],
    referencia: str,
) -> Dict[str, float]:
    """Score a single sample using ragas.evaluate with the legacy Dataset API.

    Builds a one-row HuggingFace Dataset and calls ragas_evaluate() which
    works reliably with LangchainLLMWrapper in RAGAS 0.4.

    Args:
        pregunta: The user question.
        respuesta: The agent answer.
        contextos: Retrieved context strings.
        referencia: Ground truth reference string.

    Returns:
        Dict with faithfulness, answer_relevancy, context_precision,
        context_recall scores (float, NaN on failure).
    """
    data = {
        "question": [pregunta],
        "answer": [respuesta],
        "contexts": [contextos],
        "ground_truth": [referencia],
    }
    ds = HFDataset.from_dict(data)
    result = ragas_evaluate(
        ds,
        metrics=RAGAS_METRICS,
        raise_exceptions=False,
    )
    row = result.scores[0] if result.scores else {}
    return {
        "faithfulness": float(row.get("faithfulness", float("nan"))),
        "answer_relevancy": float(row.get("answer_relevancy", float("nan"))),
        "context_precision": float(row.get("context_precision", float("nan"))),
        "context_recall": float(row.get("context_recall", float("nan"))),
    }


# ---------------------------------------------------------------------------
# TXT output
# ---------------------------------------------------------------------------

def write_results_txt(
    output_path: str,
    golden_set_path: str,
    results: List[Dict[str, Any]],
    scores: Optional[Dict[str, float]],
    start_time: datetime,
    duration_seconds: float,
) -> None:
    """Write the full evaluation results to a TXT file.

    Args:
        output_path: Full path to the output TXT file.
        golden_set_path: Path to the golden set file (for MD5).
        results: Per-question result dicts.
        scores: Aggregate RAGAS scores (may be None on failure).
        start_time: Evaluation start datetime.
        duration_seconds: Total elapsed seconds.
    """
    error_count = sum(1 for r in results if r.get("error"))

    with open(output_path, "w", encoding="utf-8") as f:
        write_txt_header(f, "RAGAS EVALUATION", golden_set_path)

        # ---- RESULTS section ----
        f.write("-" * 80 + "\n")
        f.write("RESULTS\n")
        f.write("-" * 80 + "\n\n")

        col_id = max((len(r["question_id"]) for r in results), default=10)
        col_id = max(col_id, 10)
        header = f"  {'ID':<{col_id}} | {'Status':<8} | Question (truncated)"
        f.write(header + "\n")
        f.write(f"  {'-' * col_id}-+-{'-' * 8}-+-{'-' * 40}\n")

        for r in results:
            status = "ERROR" if r.get("error") else "OK"
            q_short = r["question"][:60].replace("\n", " ")
            f.write(f"  {r['question_id']:<{col_id}} | {status:<8} | {q_short}\n")
            if r.get("error"):
                f.write(f"  {'':>{col_id}}   {'':>8}   Error: {r['error'][:80]}\n")

        f.write("\n")

        # ---- SUMMARY section ----
        if scores:
            summary_data = [
                {
                    "name": "Faithfulness",
                    "score": scores.get("faithfulness", 0.0),
                    "threshold": THRESHOLDS["faithfulness"],
                    "status": "PASS" if scores.get("faithfulness", 0.0) >= THRESHOLDS["faithfulness"] else "FAIL",
                },
                {
                    "name": "Answer Relevancy",
                    "score": scores.get("answer_relevancy", 0.0),
                    "threshold": THRESHOLDS["answer_relevancy"],
                    "status": "PASS" if scores.get("answer_relevancy", 0.0) >= THRESHOLDS["answer_relevancy"] else "FAIL",
                },
                {
                    "name": "Context Precision",
                    "score": scores.get("context_precision", 0.0),
                    "threshold": THRESHOLDS["context_precision"],
                    "status": "PASS" if scores.get("context_precision", 0.0) >= THRESHOLDS["context_precision"] else "FAIL",
                },
                {
                    "name": "Context Recall",
                    "score": scores.get("context_recall", 0.0),
                    "threshold": THRESHOLDS["context_recall"],
                    "status": "PASS" if scores.get("context_recall", 0.0) >= THRESHOLDS["context_recall"] else "FAIL",
                },
            ]
            write_txt_summary(f, summary_data)
        else:
            f.write("-" * 80 + "\n")
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n\n")
            f.write("  RAGAS evaluation did not complete — no aggregate scores available.\n\n")

        # ---- CONCLUSIONS section ----
        if scores:
            passed_metrics = [
                name for name, threshold in THRESHOLDS.items()
                if scores.get(name, 0.0) >= threshold
            ]
            n_pass = len(passed_metrics)
            n_total = len(THRESHOLDS)
            overall = "PASS" if n_pass == n_total else "FAIL"
            conclusions = (
                f"Overall result: {overall} ({n_pass}/{n_total} metrics above threshold). "
                f"Processed {len(results)} questions with {error_count} errors. "
                f"Faithfulness={scores.get('faithfulness', 0.0):.4f} "
                f"(threshold {THRESHOLDS['faithfulness']}), "
                f"Answer Relevancy={scores.get('answer_relevancy', 0.0):.4f} "
                f"(threshold {THRESHOLDS['answer_relevancy']}), "
                f"Context Precision={scores.get('context_precision', 0.0):.4f} "
                f"(threshold {THRESHOLDS['context_precision']}), "
                f"Context Recall={scores.get('context_recall', 0.0):.4f} "
                f"(threshold {THRESHOLDS['context_recall']})."
            )
        else:
            conclusions = (
                f"RAGAS evaluation failed to produce scores. "
                f"Processed {len(results)} questions with {error_count} errors."
            )

        write_txt_conclusions(
            f,
            conclusions_text=conclusions,
            duration_seconds=duration_seconds,
            total_items=len(results),
            error_count=error_count,
        )

    logger.info("Results written to: %s", output_path)


# ---------------------------------------------------------------------------
# Summary table to stdout
# ---------------------------------------------------------------------------

def print_summary_table(scores: Optional[Dict[str, float]], results: List[Dict[str, Any]]) -> None:
    """Print a summary table to stdout.

    Args:
        scores: Aggregate RAGAS scores (may be None).
        results: Per-question result dicts.
    """
    sep = "-" * 60
    print(sep)
    print("  RAGAS EVALUATION SUMMARY")
    print(sep)

    if scores:
        print(f"  {'Metric':<22} | {'Score':>7} | {'Threshold':>9} | Status")
        print(f"  {'-' * 22}-+-{'-' * 7}-+-{'-' * 9}-+-------")
        metric_display = {
            "faithfulness": "Faithfulness",
            "answer_relevancy": "Answer Relevancy",
            "context_precision": "Context Precision",
            "context_recall": "Context Recall",
        }
        pass_count = 0
        for key, display in metric_display.items():
            score = scores.get(key, 0.0)
            threshold = THRESHOLDS[key]
            status = "PASS" if score >= threshold else "FAIL"
            if status == "PASS":
                pass_count += 1
            print(f"  {display:<22} | {score:>7.4f} | {threshold:>9.4f} | {status}")
        overall = "PASS" if pass_count == len(THRESHOLDS) else "FAIL"
        print(f"\n  Overall: {overall} ({pass_count}/{len(THRESHOLDS)} metrics above threshold)")
    else:
        print("  No RAGAS scores available (evaluation failed or RAGAS not installed).")

    error_count = sum(1 for r in results if r.get("error"))
    print(f"\n  Questions processed: {len(results)} | Errors: {error_count}")
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
        description="Run RAGAS evaluation on ChatHCE UnifiedChatAgent.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--golden-set",
        default="evaluation/golden_set_ragas.json",
        help="Path to the golden set JSON file.",
    )
    parser.add_argument(
        "--output",
        default="evaluation/results/",
        help="Output directory for the results TXT file.",
    )
    parser.add_argument(
        "--subset",
        choices=["db", "rag", "all"],
        default="all",
        help="Filter questions by subset: db (DB-* ids), rag (RAG-* ids), or all.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limit the number of questions to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without calling the agent.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the RAGAS evaluation script.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Exit code: 0 on success, 1 on fatal error.
    """
    args = parse_args(argv)

    # ---- Pre-flight: RAGAS availability ----
    if not RAGAS_AVAILABLE and not args.dry_run:
        logger.error(
            "RAGAS library is not installed. Install with: pip install ragas datasets"
        )
        return 1

    # ---- Load golden set ----
    try:
        golden_data = load_golden_set(args.golden_set)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load golden set: %s", exc)
        return 1

    all_questions: List[Dict[str, Any]] = golden_data.get("questions", [])

    # ---- Validate questions ----
    invalid_count = 0
    for q in all_questions:
        errors = validate_question(q)
        if errors:
            logger.warning("Question %s has validation errors: %s", q.get("id", "?"), errors)
            invalid_count += 1

    # ---- Filter ----
    questions = filter_questions(all_questions, args.subset, args.max_samples)
    logger.info(
        "Golden set loaded: %d total questions, %d after filtering (subset=%s, max_samples=%s)",
        len(all_questions),
        len(questions),
        args.subset,
        args.max_samples,
    )

    # ---- Dry-run: print info and exit ----
    if args.dry_run:
        try:
            md5 = compute_md5(args.golden_set)
        except Exception:
            md5 = "N/A"
        print("=" * 60)
        print("  DRY-RUN MODE — no agent calls will be made")
        print("=" * 60)
        print(f"  Golden set:    {args.golden_set}")
        print(f"  MD5:           {md5}")
        print(f"  Total Qs:      {len(all_questions)}")
        print(f"  Filtered Qs:   {len(questions)}")
        print(f"  Subset:        {args.subset}")
        print(f"  Max samples:   {args.max_samples}")
        print(f"  Output dir:    {args.output}")
        print(f"  RAGAS avail:   {RAGAS_AVAILABLE}")
        print(f"  Invalid Qs:    {invalid_count}")
        print("=" * 60)
        print("  Setup validated. Ready to run evaluation.")
        return 0

    # ---- Ensure output directory exists ----
    os.makedirs(args.output, exist_ok=True)

    # ---- Instantiate agent ----
    try:
        agent = instantiate_agent()
    except Exception as exc:
        logger.error("Failed to instantiate UnifiedChatAgent: %s", exc)
        return 1

    # ---- Process questions and score per-sample ----
    results: List[Dict[str, Any]] = []
    start_time = datetime.now()

    all_metric_scores: Dict[str, List[float]] = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_precision": [],
        "context_recall": [],
    }

    for i, question in enumerate(questions, start=1):
        q_id = question.get("id", f"Q{i}")
        logger.info("Processing question %d/%d: %s", i, len(questions), q_id)
        result = process_question(agent, question)
        results.append(result)

        # Score this sample if no error and RAGAS is available
        if RAGAS_AVAILABLE and not result.get("error"):
            try:
                sample_scores = score_sample(
                    pregunta=result["question"],
                    respuesta=result["answer"],
                    contextos=result["contexts"],
                    referencia=result["ground_truth"],
                )
                result["ragas_scores"] = sample_scores
                for metric, val in sample_scores.items():
                    all_metric_scores[metric].append(val)
                logger.info("Scores for %s: %s", q_id, sample_scores)
            except Exception as exc:
                logger.error("RAGAS scoring failed for %s: %s", q_id, exc)
                result["ragas_scores"] = None

    end_time = datetime.now()
    duration_seconds = (end_time - start_time).total_seconds()

    # ---- Aggregate scores (mean across all scored samples) ----
    scores: Optional[Dict[str, float]] = None
    if RAGAS_AVAILABLE and any(all_metric_scores[m] for m in all_metric_scores):
        scores = {}
        for metric, vals in all_metric_scores.items():
            scores[metric] = sum(vals) / len(vals) if vals else 0.0
        logger.info("Aggregated RAGAS scores: %s", scores)

    # ---- Write results TXT ----
    filename = generate_result_filename("ragas")
    output_path = os.path.join(args.output, filename)

    try:
        write_results_txt(
            output_path=output_path,
            golden_set_path=args.golden_set,
            results=results,
            scores=scores,
            start_time=start_time,
            duration_seconds=duration_seconds,
        )
    except Exception as exc:
        logger.error("Failed to write results TXT: %s", exc)

    # ---- Print summary to stdout ----
    print_summary_table(scores, results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
