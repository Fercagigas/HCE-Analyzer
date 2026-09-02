"""Caracterizacion del formato de respuesta de `UnifiedChatAgent._format_response`.

Fija el contrato del dict legacy que consumen `ui/unified_chat_interface.py` y los
runners de `Evaluation/` (`success, content, tools_used, tool_results,
visualizations, sources, tokens_used, model_used`) y el comportamiento de los
parsers de texto que WP8 sustituye por contratos tipados.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

OBSERVATIONS = Path(__file__).resolve().parents[1] / "fixtures" / "tool_observations"
LEGACY_KEYS = {"success", "content", "tools_used", "tool_results", "visualizations", "sources", "tokens_used", "model_used"}


@pytest.fixture
def agent():
    from services.medical_agent.prompt_manager import PromptManager
    from services.unified_chat.unified_agent import UnifiedChatAgent

    instance = UnifiedChatAgent.__new__(UnifiedChatAgent)
    instance.prompt_manager = PromptManager(max_tokens=8000, anthropic_api_key=None, enable_caching=False)
    instance.llm_manager = SimpleNamespace(get_current_model_name=lambda: "claude-test-model")
    return instance


def _step(tool: str, tool_input: dict, observation):
    return (SimpleNamespace(tool=tool, tool_input=tool_input), observation)


def test_plain_answer_without_tools(agent):
    result = agent._format_response({"output": "Hola, ¿en qué puedo ayudarte?", "intermediate_steps": []})

    assert set(result) == LEGACY_KEYS
    assert result["success"] is True
    assert result["content"] == "Hola, ¿en qué puedo ayudarte?"
    assert result["tools_used"] == []
    assert result["tool_results"] == []
    assert result["visualizations"] == []
    assert result["sources"] == []
    assert result["model_used"] == "claude-test-model"
    assert isinstance(result["tokens_used"], int)


def test_output_as_content_blocks_is_flattened(agent):
    output = [{"type": "text", "text": "Primera parte."}, {"type": "text", "text": "Segunda parte."}, "Tercera."]
    result = agent._format_response({"output": output, "intermediate_steps": []})
    assert result["content"] == "Primera parte.\nSegunda parte.\nTercera."


def test_database_tool_result_is_preserved_as_structured_context(agent):
    observation = json.loads((OBSERVATIONS / "db_observation.json").read_text(encoding="utf-8"))
    tool_input = {"query_type": "patient_summary", "subject_id": 10014729}

    result = agent._format_response({
        "output": "El paciente 10014729 tiene una admisión.",
        "intermediate_steps": [_step("query_mimic_database", tool_input, observation)],
    })

    assert result["tools_used"] == ["query_mimic_database"]
    assert len(result["tool_results"]) == 1
    tool_result = result["tool_results"][0]
    assert tool_result["tool"] == "query_mimic_database"
    assert tool_result["input"] == tool_input
    assert tool_result["raw_output"] == observation
    assert isinstance(tool_result["summary"], str) and tool_result["summary"]
    assert result["sources"] == []


def test_rag_sources_are_parsed_from_formatted_text(agent):
    observation = (OBSERVATIONS / "rag_observation.txt").read_text(encoding="utf-8")

    result = agent._format_response({
        "output": "Según la guía de sepsis [1]...",
        "intermediate_steps": [_step("search_clinical_documents", {"query": "sepsis"}, observation)],
    })

    assert result["tools_used"] == ["search_clinical_documents"]
    assert len(result["sources"]) == 2
    first, second = result["sources"]
    assert first["tool"] == "search_clinical_documents"
    assert first["filename"] == "guia_sepsis.pdf"
    assert first["page"] == "12"
    assert first["specialty"] == "Urgencias"
    assert first["doc_type"] == "guia_clinica"
    assert first["retrieved_content"].startswith("La sepsis se define")
    assert second["filename"] == "protocolo_hta.pdf"
    assert second["page"] == "4"
    assert second["specialty"] == "Cardiología"
    # raw_observation se conserva para que extract_contexts (RAGAS) pueda re-parsear
    assert result["tool_results"][0]["raw_observation"] == observation


def test_rag_without_citation_marker_falls_back_to_truncated_content(agent):
    observation = "📚 Búsqueda en Documentos Clínicos\n\nNo se encontraron documentos."
    result = agent._format_response({
        "output": "No hay documentos.",
        "intermediate_steps": [_step("search_clinical_documents", {"query": "x"}, observation)],
    })
    assert result["sources"] == [{"tool": "search_clinical_documents", "content": observation}]


def test_visualization_ids_are_extracted_without_base64(agent):
    observation = (OBSERVATIONS / "viz_observation.txt").read_text(encoding="utf-8")

    result = agent._format_response({
        "output": "Aquí tienes la evolución.",
        "intermediate_steps": [_step("request_visualization", {"visualization_type": "timeline"}, observation)],
    })

    assert result["tools_used"] == ["request_visualization"]
    assert len(result["visualizations"]) == 1
    viz = result["visualizations"][0]
    assert viz["type"] == "visualization_ids"
    assert viz["ids"] == ["viz_a1b2c3", "viz_d4e5f6"]
    assert viz["count"] == 2
    assert viz["tool"] == "request_visualization"
    assert "data:image" not in json.dumps(result, default=str)
    assert result["tool_results"][0]["raw_output"] == "visualization_generated"


def test_tools_used_is_deduplicated(agent):
    observation = json.loads((OBSERVATIONS / "db_observation.json").read_text(encoding="utf-8"))
    result = agent._format_response({
        "output": "ok",
        "intermediate_steps": [
            _step("query_mimic_database", {"query_type": "patient_summary", "subject_id": 1}, observation),
            _step("query_mimic_database", {"query_type": "labs", "subject_id": 1}, observation),
        ],
    })
    assert result["tools_used"] == ["query_mimic_database"]
    assert len(result["tool_results"]) == 2
