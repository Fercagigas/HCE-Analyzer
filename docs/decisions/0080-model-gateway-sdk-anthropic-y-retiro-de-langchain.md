# ADR 0080 — Model Gateway sobre SDK anthropic y retiro de LangChain del bucle agéntico

Estado: Aceptada

Fecha: 2026-09-02

## Contexto

El bucle agéntico dependía de `langchain_classic.AgentExecutor` (paquete no declarado en
`requirements.txt`) y de `ChatAnthropic` a través de `ClaudeLLMManager`. Consecuencias
observadas en Fase 0: cada inicialización probaba el modelo gastando tokens, el fallback entre
modelos se decidía en la construcción y no por petición, los reintentos usaban `time.sleep`,
no existía timeout total, los resultados de tools se reinyectaban completos entre turnos
(fuga si cambia el paciente en la sesión) y la caché de respuestas no incluía usuario ni
paciente. El roadmap (doc 03 Model Gateway) pide un gateway propio con selección de modelo,
timeouts, reintentos, política de tools, trazas y degradación, y el ADR 0010 exige que el core
no importe SDKs concretos.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Mantener LangChain y envolverlo en un port.** Descartada: el `AgentExecutor` controla el
   bucle, los reintentos y la forma de los mensajes; el port quedaría reducido a un adaptador
   de la abstracción de LangChain, sin control de timeout total ni de eventos de streaming.
2. **Usar el `tool_runner` del SDK anthropic.** Descartada: es una API beta acoplada al SDK;
   la política de tools, el scope y la auditoría deben vivir en el core, no en el cliente.
3. **Bucle propio sobre un port `LLMProvider` y adapter `anthropic` nativo** (elegida).
   El core define tipos neutrales de mensajes, partes y eventos; el adapter traduce a
   `AsyncAnthropic.messages.stream`.
4. **Proveedor multi-LLM desde el inicio (OpenAI, Bedrock).** Descartada para Fase 1: sin
   consumidor; el port lo permite sin rediseño.

## Decision

- Port `LLMProvider` (`chathce/ports/llm_provider.py`) con `generate(...) -> AsyncIterator[LLMEvent]`
  y jerarquía de errores con `retryable` (`LLMRateLimited`, `LLMOverloaded`, `LLMTimeout`,
  `LLMUnavailable` frente a `LLMAuthError`, `LLMBadRequest`).
- `AnthropicLLMProvider` (`chathce/adapters/anthropic/provider.py`, `mapping.py`) con
  `AsyncAnthropic(max_retries=0)`, streaming de texto y acumulación de `input_json` por bloque,
  y `health(model)` mediante `models.retrieve` (sin gastar tokens). Pin `anthropic>=0.77,<1`.
- `ModelGateway` (`chathce/gateway/model_gateway.py`): cadena de modelos por petición desde
  `settings.llm.model_chain`, un reintento por modelo con `asyncio.sleep`, deadline total,
  máximo de iteraciones y síntesis final sin tools; emite eventos de alto nivel
  `status`, `tool_call`, `tool_result_summary`, `text_delta`, `error` y nunca razonamiento
  interno.
- `ToolRegistry.dispatch` (`chathce/gateway/tool_registry.py`) nunca lanza: valida entrada
  (Pydantic, `extra=forbid`), aplica `ToolPolicy` (scope, propósito), `asyncio.wait_for`,
  valida la salida, recorta filas y renderiza para el modelo con
  `<tool_data ... trust="untrusted_data">` (`rendering.py`).
- Historial entre turnos: replay resumido (texto más lista de tools usadas); nunca se reinyectan
  datos de tools de turnos anteriores. Se elimina la caché de respuestas de chat.
- `QueryAugmenter` del RAG recibe el mismo `LLMProvider` inyectado; `langchain-classic` y
  `langchain-anthropic` salen de las dependencias. LangChain permanece solo para embeddings y
  splitters del RAG.
- `FakeLLMProvider` (`chathce/adapters/memory/fake_llm_provider.py`) guioniza turnos para
  tests deterministas.

## Motivo

Control completo del bucle es requisito para aplicar política de tools, deadlines y
auditoría por petición; el SDK oficial ya provee streaming y tipado; retirar LangChain del
bucle elimina una dependencia no declarada y reduce la superficie de prompt implícita.

## Consecuencias

- Positivas: comportamiento verificable con guiones (`tests/unit/gateway/`), fallback y
  reintentos observables en auditoría (`llm_call`, `llm_fallback`), SSE de eventos en la API.
- Negativas: el proyecto mantiene su propio bucle (más código propio que mantener);
  cualquier proveedor nuevo requiere un adapter.
- El prompt del sistema se construye desde los contratos de tools
  (`chathce/application/prompts/system_prompt.py`, plantilla `chat_system.es.md`) y lleva
  versión `chat-system/<ver>+<sha8>` en metadatos y auditoría.

## Pendientes

- Circuit breaker por modelo y métricas de latencia agregadas (P1).
- Prompt caching y `max_tokens` adaptativo.
- Streaming en la interfaz Streamlit (hoy solo en `/api/v1/chat/stream`).
