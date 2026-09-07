import pytest

from chathce.application.prompts.system_prompt import build_system_prompt, render_tools_section
from chathce.domain.chat import ChatOptions
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.tools import LLM_VISIBLE_FORBIDDEN_PATTERN

pytestmark = pytest.mark.unit


def test_prompt_contains_no_sql_or_table_names(registry):
    ctx = RequestContext(user_id="u", channel=Channel.api, patient_id="10001217")
    prompt, version = build_system_prompt(registry.contracts(), ctx, ChatOptions())
    assert LLM_VISIBLE_FORBIDDEN_PATTERN.search(prompt) is None
    assert "CREATE TABLE" not in prompt
    assert version.startswith("chat-system/1+") and len(version.split("+")[1]) == 8


def test_prompt_version_is_stable_across_contexts(registry):
    a = build_system_prompt(registry.contracts(), RequestContext(user_id="a", channel=Channel.api, patient_id="1"))[1]
    b = build_system_prompt(registry.contracts(), RequestContext(user_id="b", channel=Channel.streamlit, patient_id="2"))[1]
    assert a == b
    c = build_system_prompt(registry.contracts(enabled=["get_labs"]), RequestContext(user_id="a", channel=Channel.api))[1]
    assert c != a  # distinta lista de herramientas -> distinta version


def test_context_block_reflects_scope_and_purpose(registry):
    ctx = RequestContext(user_id="u", channel=Channel.api, patient_id="10001217", encounter_id="555")
    prompt, _ = build_system_prompt(registry.contracts(), ctx)
    assert "Paciente activo: 10001217" in prompt and "Episodio activo: 555" in prompt
    assert "NO están disponibles en este modo" in prompt
    research = RequestContext(user_id="u", channel=Channel.api, purpose=Purpose.research, roles=frozenset({"researcher"}))
    prompt_r, _ = build_system_prompt(registry.contracts(), research)
    assert "NO están disponibles" not in prompt_r
    no_patient, _ = build_system_prompt(registry.contracts(), RequestContext(user_id="u", channel=Channel.api))
    assert "seleccione un paciente" in no_patient


def test_tools_section_is_generated_from_contracts(registry):
    section = render_tools_section(registry.contracts(enabled=["get_labs", "get_dataset_statistics"]))
    assert "**get_labs**" in section and "subject_id (integer, obligatorio)" in section
    assert "Requiere paciente activo" in section
    assert "Solo disponible con propósito 'research'" in section
    assert "untrusted" not in section.lower()
