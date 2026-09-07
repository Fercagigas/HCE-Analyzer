"""ChatService con todos los ports en fakes: sin tools, con tool clinica, RAG, visualizacion, errores y persistencia."""

import pytest

from chathce.adapters.memory import InMemoryKnowledgeRepository, ScriptedTurn
from chathce.domain.chat import ChatRequest, CompleteEvent, ErrorEvent, TextDeltaEvent, ToolCallEvent
from chathce.domain.context import Channel, Purpose, RequestContext
from chathce.domain.evidence import ClaimType
from chathce.domain.knowledge import KnowledgeHit
from chathce.ports.llm_provider import LLMAuthError
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest

pytestmark = [pytest.mark.unit, pytest.mark.skipif(not fixtures_available(), reason="fixtures MIMIC no grabadas")]

SUBJECT = load_manifest()["subject_ids"][0] if fixtures_available() else 0


def _ctx(**kw) -> RequestContext:
    base = dict(user_id="clinician-1", channel=Channel.api, patient_id=str(SUBJECT))
    base.update(kw)
    return RequestContext(**base)


async def test_plain_answer_without_tools_is_persisted():
    container = build_test_container([ScriptedTurn(text="Hola, ¿en qué puedo ayudarte?")])
    ctx = _ctx()
    response = await container.chat_service.handle_chat(ChatRequest(message="hola"), ctx)

    assert response.success and response.content == "Hola, ¿en qué puedo ayudarte?"
    assert response.tool_calls == [] and response.facts == [] and len(response.inferences) == 1
    assert response.uncertainty.level == "medium"  # sin hechos verificados
    assert response.metadata.session_id and response.metadata.model_used == "fake-primary"
    sessions = await container.conversation_service.list_sessions(ctx)
    assert len(sessions) == 1 and sessions[0].title == "hola"
    stored = await container.conversations.list_messages(ctx.model_copy(update={"session_id": sessions[0].session_id}), session_id=sessions[0].session_id)
    assert [m.role for m in stored] == ["user", "assistant"]
    assert container.analyses.records[0].analysis_type == "general"
    assert "chat_completed" in container.audit.actions() and container.audit.phi_findings() == []


async def test_clinical_tool_produces_facts_evidence_and_persists_metadata():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": SUBJECT, "limit": 5})]),
        ScriptedTurn(text="Estos son los últimos 5 laboratorios."),
    ])
    ctx = _ctx()
    response = await container.chat_service.handle_chat(ChatRequest(message="¿Últimos laboratorios?"), ctx)

    assert response.success and len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.tool_name == "get_labs" and call.success and call.count == 5 and len(call.evidence_ids) == 5
    assert len(response.facts) == 1 and response.facts[0].type == ClaimType.OBSERVED_FACT
    assert response.facts[0].evidence_ids == call.evidence_ids
    assert {e.evidence_id for e in response.evidence} == set(call.evidence_ids)
    assert all(e.patient_id == str(SUBJECT) and e.provenance.tool_use_id == call.tool_use_id for e in response.evidence)
    assert response.inferences[0].type == ClaimType.AI_INFERENCE and response.uncertainty.level == "low"
    session_id = response.metadata.session_id
    stored = await container.conversations.list_messages(ctx.model_copy(update={"session_id": session_id}), session_id=session_id)
    assert stored[1].metadata.tools_used == ["get_labs"] and stored[1].metadata.trace_id == ctx.trace_id
    assert container.analyses.records[0].analysis_type == "database_query"
    # el modelo recibio los datos delimitados como no confiables
    sent = container.llm_provider.calls[1].messages[-1].parts[0].content
    assert 'trust="untrusted_data"' in sent and "labevent" in sent


async def test_scope_refusal_surfaces_in_uncertainty():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_labs", {"subject_id": 99999999})]),
        ScriptedTurn(text="No puedo consultar otro paciente."),
    ])
    response = await container.chat_service.handle_chat(ChatRequest(message="labs del 99999999"), _ctx())
    assert response.success
    assert response.tool_calls[0].error_code == "scope_refused"
    assert response.uncertainty.scope_refusals and response.uncertainty.level == "medium"
    assert "tool_refused" in container.audit.actions()


async def test_rag_tool_adds_sources_and_guideline_claims():
    knowledge = InMemoryKnowledgeRepository([
        KnowledgeHit(chunk_id="c1", filename="guia_sepsis.pdf", page=12, specialty="Urgencias", doc_type="guia_clinica",
                     content="La sepsis se define como disfunción orgánica...", score=0.9),
    ])
    container = build_test_container([
        ScriptedTurn(tool_calls=[("search_clinical_documents", {"query": "sepsis", "top_k": 3})]),
        ScriptedTurn(text="Según la guía [1]..."),
    ], knowledge=knowledge)
    response = await container.chat_service.handle_chat(ChatRequest(message="¿protocolo de sepsis?"), _ctx(patient_id=None))
    assert response.sources[0].filename == "guia_sepsis.pdf" and response.sources[0].page == 12
    assert response.facts[0].type == ClaimType.GUIDELINE_STATEMENT
    assert response.evidence[0].type.value == "guideline_document"
    assert container.analyses.records[0].analysis_type == "rag_search"


async def test_visualization_tool_registers_artifact():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("create_visualization", {"visualization_type": "timeline", "source": "labs", "subject_id": SUBJECT})]),
        ScriptedTurn(text="Aquí tienes la evolución."),
    ])
    ctx = _ctx()
    response = await container.chat_service.handle_chat(ChatRequest(message="grafica de labs"), ctx)
    assert response.success and len(response.visualizations) == 1
    ref = response.visualizations[0]
    artifact = await container.visualizations.get(ctx, ref.viz_id)
    assert artifact is not None and artifact.viz_type == "timeline" and artifact.figure_json.startswith("{")
    assert response.tool_calls[0].success


async def test_visualizations_can_be_disabled_per_request():
    container = build_test_container([ScriptedTurn(text="ok")])
    request = ChatRequest(message="hola", options={"enable_visualizations": False})
    await container.chat_service.handle_chat(request, _ctx())
    assert "create_visualization" not in [t.name for t in container.llm_provider.calls[0].tools]


async def test_provider_failure_yields_error_and_failed_response():
    container = build_test_container([LLMAuthError("clave invalida")])
    events = [e async for e in container.chat_service.stream_chat(ChatRequest(message="hola"), _ctx())]
    assert any(isinstance(e, ErrorEvent) for e in events)
    final = events[-1]
    assert isinstance(final, CompleteEvent) and final.response.success is False
    assert final.response.error.code == "LLM_AUTH_ERROR" and "chat_failed" in container.audit.actions()


async def test_stream_emits_text_deltas_and_tool_calls_before_complete():
    container = build_test_container([
        ScriptedTurn(text="Consulto", tool_calls=[("get_diagnoses", {"subject_id": SUBJECT})]),
        ScriptedTurn(text="Listo."),
    ])
    events = [e async for e in container.chat_service.stream_chat(ChatRequest(message="dx"), _ctx())]
    types = [type(e).__name__ for e in events]
    assert types[0] == "StatusEvent" and types[-1] == "CompleteEvent"
    assert any(isinstance(e, TextDeltaEvent) for e in events) and any(isinstance(e, ToolCallEvent) for e in events)
    assert types.index("ToolCallEvent") < types.index("CompleteEvent")


async def test_history_is_replayed_without_old_tool_data():
    container = build_test_container([ScriptedTurn(text="primera"), ScriptedTurn(text="segunda")])
    ctx = _ctx()
    first = await container.chat_service.handle_chat(ChatRequest(message="pregunta 1"), ctx)
    ctx2 = ctx.model_copy(update={"session_id": first.metadata.session_id})
    await container.chat_service.handle_chat(ChatRequest(message="pregunta 2", session_id=first.metadata.session_id), ctx2)
    replayed = container.llm_provider.calls[1].messages
    assert [m.role for m in replayed] == ["user", "assistant", "user"]
    assert replayed[0].text() == "pregunta 1" and replayed[1].text().startswith("primera")


async def test_rate_limit_blocks_after_burst():
    container = build_test_container([ScriptedTurn(text="ok")] * 5, rate_limit=True)
    ctx = _ctx()
    await container.chat_service.handle_chat(ChatRequest(message="1"), ctx)
    await container.chat_service.handle_chat(ChatRequest(message="2"), ctx)
    third = await container.chat_service.handle_chat(ChatRequest(message="3"), ctx)
    assert third.success is False and third.error.code == "RATE_LIMITED"
    other = await container.chat_service.handle_chat(ChatRequest(message="1"), _ctx(user_id="other"))
    assert other.success is True


async def test_research_purpose_enables_dataset_statistics():
    container = build_test_container([
        ScriptedTurn(tool_calls=[("get_dataset_statistics", {"statistic": "top_drugs", "limit": 3})]),
        ScriptedTurn(text="Los fármacos más prescritos son..."),
    ])
    ctx = RequestContext(user_id="r", channel=Channel.api, purpose=Purpose.research, roles=frozenset({"researcher"}))
    response = await container.chat_service.handle_chat(ChatRequest(message="top farmacos", purpose=Purpose.research), ctx)
    assert response.tool_calls[0].success and response.facts[0].type == ClaimType.CALCULATION
