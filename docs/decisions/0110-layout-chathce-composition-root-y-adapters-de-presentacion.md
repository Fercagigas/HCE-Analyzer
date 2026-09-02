# ADR 0110 — Layout del paquete chathce, composition root y adapters de presentación

Estado: Aceptada

Fecha: 2026-09-02

## Contexto

ADR 0010 fijó ports and adapters y migración strangler con Streamlit como adapter temporal,
pero no el layout concreto ni cómo convivirían el core asíncrono, Streamlit (síncrono) y
FastAPI. El RAG carga modelos locales (embeddings y reranker, con CUDA si está disponible) en
un singleton de proceso.

## Opciones consideradas (incluidas las descartadas y por que)

1. **Refactorizar `services/` en el sitio, añadiendo interfaces.** Descartada: mezcla código
   legacy y nuevo en los mismos paquetes, impide un test de fronteras por AST y prolonga los
   imports de Streamlit/Supabase en el core.
2. **Paquete nuevo `chathce/` con capas explícitas y test de fronteras** (elegida).
3. **Un proceso por canal (Streamlit y API separados) desde el inicio.** Se mantiene la opción
   pero no se impone: ambos canales comparten `build_container()` y pueden ejecutarse en el
   mismo proceso o en procesos distintos.
4. **Varios workers uvicorn.** Descartada en Fase 1: cada worker cargaría los modelos del RAG
   y competiría por la GPU; sin un servicio de embeddings separado no hay ganancia.

## Decision

- Layout: `chathce/domain`, `ports`, `application`, `gateway` (sin dependencias de
  frameworks), `adapters/{anthropic,supabase,memory,logging,visualization}`, `composition`,
  `api`, `streamlit_adapter`, `legacy`. `tests/unit/test_architecture_boundaries.py` prohíbe
  por AST importar `streamlit`, `supabase`, `postgrest`, `anthropic` o `langchain*` fuera de
  `adapters/**` y comprueba `sys.modules` en un subproceso.
- `build_container(settings)` (`chathce/composition/container.py`) es el único lugar que
  instancia adapters; perfiles `llm` (anthropic|fake), `clinical` (supabase_mimic|memory) y
  persistencia (supabase|memory). `AsyncRunner` ejecuta el core desde código síncrono.
- Streamlit es adapter de presentación: `bootstrap.get_container()` con `st.cache_resource`,
  `StreamlitChatClient` y `LegacyAuthServiceAdapter`; `SessionManager` queda como fachada
  estática con los mismos métodos. Sin persistencia ni composición en la UI.
- Compatibilidad: `LegacyAgentFacade.process_message()` y `to_legacy_dict()` mantienen el
  contrato que consumen la UI y los runners de `Evaluation/` mientras dura el strangler.
- FastAPI se arranca con `python -m uvicorn chathce.api.app:app --host 127.0.0.1 --port 8000 --workers 1`;
  el RAG se carga en el `lifespan` en un hilo; `/ready` devuelve 503 hasta entonces.
- Configuración única en `config/settings.py` con `get_settings()` perezoso; `config/config.py`
  eliminado; constantes de dominio en `config/constants.py`.

## Motivo

Un paquete nuevo con fronteras verificables permite migrar por partes sin que el legacy
contamine el core, y un composition root único hace explícito qué adapter usa cada canal.
Un solo worker es la configuración honesta para un proceso que aloja modelos locales.

## Consecuencias

- Positivas: el core se prueba sin red ni credenciales; los mismos casos de uso sirven a
  API, Streamlit y evaluación; imports de SDK confinados.
- Negativas: duplicidad temporal (`services/rag` sigue siendo legacy envuelto por
  `KnowledgeRepository`; `ui/` mantiene lógica de presentación extensa); un solo worker limita
  el paralelismo de la API.

## Pendientes

- Migrar `services/rag/*` a `chathce/adapters/rag` y `src/processors` a un port de documentos.
- Servicio de embeddings separado para permitir varios workers.
- Retirar `chathce/legacy` cuando la UI consuma `ChatResponse` directamente y la evaluación use
  el core.
