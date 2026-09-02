# Proveedor LLM y mapeo — ChatHCE

**Última actualización**: 2 de septiembre de 2026 (Fase 1, ADR 0080)

## Un solo proveedor tras un port

Todo el uso de modelos pasa por el port `LLMProvider` (`chathce/ports/llm_provider.py`). La única implementación real es `AnthropicLLMProvider` (`chathce/adapters/anthropic/provider.py`); para tests existe `FakeLLMProvider` (`chathce/adapters/memory/fake_llm_provider.py`).

| Consumidor | Modelo(s) | Cómo |
|---|---|---|
| `ModelGateway` (chat) | `settings.llm.model_chain` = `claude-haiku-4-5-20251001` → `claude-sonnet-4-5` → `claude-opus-4-0` | Cadena por petición; un reintento por modelo ante errores `retryable`; deadline total 120 s |
| `QueryAugmenter` (RAG, multi-query / HyDE) | `settings.rag.query_augmentation_model` (por defecto Haiku 4.5) | Mismo `LLMProvider` inyectado; degrada a la consulta original si falla |
| `/ready` | primer modelo de la cadena | `health(model)` con `models.retrieve` (no gasta tokens), cacheado `API_READY_CACHE_S` |

Embeddings (`sentence-transformers/all-MiniLM-L6-v2`) y reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) son modelos locales, no LLM.

## Tipos neutrales del port

```
LLMMessage(role, parts)         parts: TextPart | ToolUsePart(id, name, input) | ToolResultPart(tool_use_id, content, is_error)
LLMToolSpec(name, description, input_schema)
generate(messages, tools, system, model, max_tokens, temperature, timeout_s, stream) -> AsyncIterator[LLMEvent]
LLMEvent: text_delta | tool_use_start | tool_use_end | message_end(stop_reason, usage, model, assistant_parts)
```

Errores (`chathce/ports/llm_provider.py`): `LLMRateLimited`, `LLMOverloaded`, `LLMTimeout`, `LLMUnavailable` (retryable) y `LLMAuthError`, `LLMBadRequest` (no retryable).

## Mapeo Anthropic (`chathce/adapters/anthropic/mapping.py`)

| Función | Traduce |
|---|---|
| `to_anthropic_messages` | `LLMMessage` → bloques `text` / `tool_use` / `tool_result` |
| `to_anthropic_tools` | `LLMToolSpec` → `{"name","description","input_schema"}` |
| `from_anthropic_content` | bloques de la respuesta final → `LLMPart` |
| `map_stop_reason` | `end_turn` / `tool_use` / `max_tokens` / `stop_sequence` |
| `translate_exception` | `RateLimitError` → `LLMRateLimited` (con `retry-after`), `APIStatusError 529` → `LLMOverloaded`, `APITimeoutError`/`APIConnectionError` → `LLMTimeout`/`LLMUnavailable`, `AuthenticationError` → `LLMAuthError`, `BadRequestError` → `LLMBadRequest` |

`AnthropicLLMProvider` usa `AsyncAnthropic(max_retries=0)` (los reintentos los decide el gateway) y `messages.stream(...)`: acumula `input_json_delta` por índice de bloque y hace `json.loads` en `content_block_stop`; `get_final_message()` aporta `usage` y `stop_reason`.

Versión: `anthropic>=0.77,<1` (`requirements.txt`, `environment.yml`).

## Configuración

```env
LLM_PROVIDER=anthropic            # anthropic | fake
LLM_MODEL_CHAIN=["claude-haiku-4-5-20251001","claude-sonnet-4-5","claude-opus-4-0"]
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.1
LLM_REQUEST_TIMEOUT_S=60
LLM_TOTAL_TIMEOUT_S=120
LLM_MAX_RETRIES_PER_MODEL=1
LLM_MAX_ITERATIONS=6
```

`ANTHROPIC_API_KEY` es la única credencial; se exige con `Settings.require_anthropic()` en el composition root, no al importar.

## Añadir otro proveedor

1. Implementar `LLMProvider` en `chathce/adapters/<proveedor>/provider.py` con su `mapping.py` (mismos tipos neutrales y misma jerarquía de errores).
2. Añadir el perfil en `build_container()` (`settings.llm.provider`).
3. Tests de contrato análogos a `tests/contract/test_anthropic_mapping.py` y live opcional en `tests/integration/`.

El core (`ModelGateway`, `ChatService`, tools) no cambia.
