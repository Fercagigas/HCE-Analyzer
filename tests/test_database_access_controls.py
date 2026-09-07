"""Regression tests for the model-facing MIMIC access boundary."""

import json
import os
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture(scope="module")
def access_control_checks() -> dict[str, bool]:
    """Run application imports once without polluting the baseline test process."""
    env = os.environ.copy()
    env.update(
        {
            "SUPABASE_URL": "https://example.invalid",
            "SUPABASE_KEY": "test-only",
            "ANTHROPIC_API_KEY": "test-only",
            "SECRET_KEY": "test-only-secret-key",
        }
    )
    source = """
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock

        import pandas as pd
        from pydantic import ValidationError as PydanticValidationError

        from services.medical_agent.services.database_service import (
            DatabaseService,
            ValidationError,
        )
        from services.unified_chat.tools.database_tool import (
            DatabaseTool,
            DatabaseToolInput,
        )

        checks = {}

        schema = DatabaseToolInput.model_json_schema()
        properties = schema["properties"]
        assert not {"custom_query", "params", "table_name", "filters", "sql"} & set(properties)
        try:
            DatabaseToolInput(
                query_type="custom",
                custom_query="SELECT * FROM mimic_ed.edstays",
            )
        except PydanticValidationError:
            pass
        else:
            raise AssertionError("The model schema accepted arbitrary SQL")
        checks["schema"] = True

        tool = DatabaseTool.__new__(DatabaseTool)
        tool.db_service = Mock()
        for query_type in ("diagnoses", "medications", "triage"):
            result = tool.execute(query_type=query_type)
            assert result["success"] is False
            assert "subject_id o stay_id" in result["error"]
        assert not tool.db_service.method_calls
        checks["scope"] = True

        result = tool.execute(query_type="custom")
        assert result["success"] is False
        assert "no permitida" in result["error"]
        try:
            tool.execute(
                query_type="patient_summary",
                subject_id=10014729,
                custom_query="SELECT * FROM mimic_ed.edstays",
            )
        except TypeError:
            pass
        else:
            raise AssertionError("execute accepted a custom_query argument")
        assert not tool.db_service.method_calls
        checks["custom"] = True

        tool.db_service.get_diagnosis_frequency.return_value = {
            "groups": [{"name": str(i), "count": 1} for i in range(250)],
            "source_rows": 1000,
            "scan_limit": 1000,
            "source_truncated": True,
        }
        result = tool.execute(query_type="diagnosis_frequency", limit=200)
        assert result["success"] is True
        assert result["permissions"] == "read_only"
        assert result["scope"]["scope_type"] == "dataset_aggregate"
        assert len(result["data"]["groups"]) == 200
        assert result["count"] == 200
        assert result["truncated"] is True
        assert result["timeout_seconds"] == 30
        rejected = tool.execute(query_type="diagnosis_frequency", limit=201)
        assert rejected["success"] is False
        assert tool.db_service.get_diagnosis_frequency.call_count == 1
        checks["limit"] = True

        assert not hasattr(DatabaseService, "execute_custom_query")
        service = DatabaseService.__new__(DatabaseService)
        session = SimpleNamespace(timeout=None)
        connection = SimpleNamespace(postgrest=SimpleNamespace(session=session))
        service._configure_query_timeout(connection)
        assert session.timeout.connect == 30
        assert session.timeout.read == 30

        service.get_table_data = Mock(return_value=pd.DataFrame())
        try:
            service.get_scoped_diagnoses(icd_title="sepsis")
        except ValidationError:
            pass
        else:
            raise AssertionError("Service accepted an unscoped diagnosis query")
        service.get_table_data.assert_not_called()
        checks["service"] = True

        print(json.dumps(checks))
    """
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_model_schema_has_no_arbitrary_sql_input(access_control_checks) -> None:
    assert access_control_checks["schema"]


def test_unscoped_clinical_queries_are_blocked_before_database_access(
    access_control_checks,
) -> None:
    assert access_control_checks["scope"]


def test_custom_operation_and_sql_keyword_arguments_are_rejected(
    access_control_checks,
) -> None:
    assert access_control_checks["custom"]


def test_row_limit_and_dataset_aggregate_contract_are_enforced(
    access_control_checks,
) -> None:
    assert access_control_checks["limit"]


def test_service_has_no_raw_sql_route_and_enforces_provider_timeout(
    access_control_checks,
) -> None:
    assert access_control_checks["service"]
