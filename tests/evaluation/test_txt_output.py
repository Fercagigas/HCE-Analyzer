"""
Property-Based Tests for TXT Output Format.

Property 17: TXT output contains required metadata
Validates: Requirements 10.6, 12.1, 12.2, 12.3

Property 18: Result filename matches required pattern
Validates: Requirements 10.4
"""

import io
import re
import sys
from datetime import datetime
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from Evaluation.eval_helpers import generate_result_filename, write_txt_header

# ---------------------------------------------------------------------------
# Property 17: TXT output contains required metadata
# Validates: Requirements 10.6, 12.1, 12.2, 12.3
# ---------------------------------------------------------------------------

VALID_MODULES = ["RAGAS EVALUATION", "LATENCY BENCHMARKS", "SECURITY TESTS", "TEST CASES"]


@given(
    module_name=st.sampled_from(VALID_MODULES),
)
@settings(max_examples=50)
def test_property_17_txt_contains_required_metadata(module_name):
    """**Validates: Requirements 10.6, 12.1, 12.2, 12.3**

    Property 17: TXT output contains required metadata.

    For any evaluation results TXT file produced by write_txt_header(), the
    output must contain: Python version, key library versions (ragas, anthropic),
    the model name, and execution timestamps.
    """
    buf = io.StringIO()

    # Patch library version lookups and model name to avoid real imports
    with patch("Evaluation.eval_helpers._get_lib_version", return_value="1.2.3"), \
         patch("Evaluation.eval_helpers._get_model_name", return_value="claude-haiku-4-5-20251001"):
        start_time = write_txt_header(buf, module_name)

    content = buf.getvalue()

    # Must contain Python version
    python_version = sys.version.split()[0]
    assert python_version in content, (
        f"Python version '{python_version}' not found in TXT output"
    )

    # Must contain library version entries
    assert "RAGAS:" in content, "RAGAS version entry missing from TXT output"
    assert "Anthropic SDK:" in content, "Anthropic SDK version entry missing from TXT output"

    # Must contain model name
    assert "claude-haiku-4-5-20251001" in content, (
        "Model name 'claude-haiku-4-5-20251001' not found in TXT output"
    )

    # Must contain module name in header
    assert module_name in content, f"Module name '{module_name}' not found in TXT output"

    # Must contain start timestamp
    timestamp_str = start_time.strftime("%Y%m%d")
    assert timestamp_str in content, (
        f"Start timestamp date '{timestamp_str}' not found in TXT output"
    )

    # Must contain the ENVIRONMENT section
    assert "ENVIRONMENT" in content, "ENVIRONMENT section missing from TXT output"


def test_property_17_txt_contains_golden_set_md5():
    """**Validates: Requirements 10.6, 12.1**

    Property 17 (golden set): When a golden_set_path is provided,
    write_txt_header() must include the filename and MD5 hash in the output.
    """
    import tempfile
    import os

    buf = io.StringIO()

    # Create a temporary file to compute a real MD5
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp.write(b'{"test": "data"}')
        tmp_path = tmp.name

    try:
        with patch("Evaluation.eval_helpers._get_lib_version", return_value="1.0.0"), \
             patch("Evaluation.eval_helpers._get_model_name", return_value="claude-haiku-4-5-20251001"):
            write_txt_header(buf, "RAGAS EVALUATION", golden_set_path=tmp_path)

        content = buf.getvalue()
        filename = os.path.basename(tmp_path)

        assert "Golden Set:" in content, "Golden Set entry missing from TXT output"
        assert filename in content, f"Golden set filename '{filename}' not in TXT output"
        assert "MD5:" in content, "MD5 hash entry missing from TXT output"
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Property 18: Result filename matches required pattern
# Validates: Requirements 10.4
# ---------------------------------------------------------------------------

VALID_MODULE_NAMES = ["ragas", "latency", "security", "test_cases"]
FILENAME_PATTERN = re.compile(
    r"^(ragas|latency|security|test_cases)_results_\d{8}_\d{6}\.txt$"
)


@given(
    module=st.sampled_from(VALID_MODULE_NAMES),
)
@settings(max_examples=100)
def test_property_18_result_filename_pattern(module):
    """**Validates: Requirements 10.4**

    Property 18: Result filename matches required pattern.

    For any module name, generate_result_filename() must produce a filename
    matching the pattern {module}_results_{YYYYMMDD_HHMMSS}.txt.
    """
    filename = generate_result_filename(module)

    assert FILENAME_PATTERN.match(filename), (
        f"Filename '{filename}' does not match pattern "
        f"'{module}_results_YYYYMMDD_HHMMSS.txt'"
    )


@given(
    module=st.sampled_from(VALID_MODULE_NAMES),
)
@settings(max_examples=100)
def test_property_18_filename_starts_with_module(module):
    """**Validates: Requirements 10.4**

    Property 18 (prefix): The generated filename must start with the module name.
    """
    filename = generate_result_filename(module)
    assert filename.startswith(f"{module}_results_"), (
        f"Filename '{filename}' does not start with '{module}_results_'"
    )


@given(
    module=st.sampled_from(VALID_MODULE_NAMES),
)
@settings(max_examples=100)
def test_property_18_filename_ends_with_txt(module):
    """**Validates: Requirements 10.4**

    Property 18 (extension): The generated filename must end with '.txt'.
    """
    filename = generate_result_filename(module)
    assert filename.endswith(".txt"), (
        f"Filename '{filename}' does not end with '.txt'"
    )


@given(
    module=st.sampled_from(VALID_MODULE_NAMES),
)
@settings(max_examples=50)
def test_property_18_filename_timestamp_is_valid_datetime(module):
    """**Validates: Requirements 10.4**

    Property 18 (timestamp validity): The timestamp embedded in the filename
    must represent a valid date and time.
    """
    filename = generate_result_filename(module)
    # Extract timestamp: {module}_results_{YYYYMMDD_HHMMSS}.txt
    match = re.match(
        r"^[a-z_]+_results_(\d{8})_(\d{6})\.txt$", filename
    )
    assert match is not None, f"Could not extract timestamp from '{filename}'"

    date_str, time_str = match.group(1), match.group(2)
    try:
        datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    except ValueError as exc:
        assert False, f"Timestamp in '{filename}' is not a valid datetime: {exc}"
