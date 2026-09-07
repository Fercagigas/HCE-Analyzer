"""
Query Augmenter for RAG System

Uses an LLM to augment user queries before retrieval, improving recall and
relevance through two complementary techniques:

1. Multi-Query Generation: alternative queries from different perspectives.
2. HyDE (Hypothetical Document Embeddings): a hypothetical snippet that would
   answer the query, improving semantic match with indexed documents.

WP6 (ADR 0080): la generacion pasa por el port ``LLMProvider`` del core (un unico
cliente Anthropic en ``chathce.adapters.anthropic``). Si no hay proveedor o
credenciales, el augmenter se degrada a la consulta original.

References:
- DMQR-RAG (https://openreview.net/forum?id=lz936bYmb3)
- HyDE (https://arxiv.org/abs/2212.10496)
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


MULTI_QUERY_SYSTEM_PROMPT = """Eres un especialista en recuperación de información médica.
Tu tarea es generar consultas alternativas para mejorar la búsqueda en documentos clínicos.

Reglas:
- Genera exactamente {num_queries} consultas alternativas
- Usa terminología médica variada (sinónimos, términos técnicos, abreviaturas)
- Aborda la consulta desde diferentes ángulos (diagnóstico, tratamiento, fisiopatología)
- Cada consulta debe ser independiente y autocontenida
- Responde SOLO con las consultas, una por línea, sin numeración ni prefijos"""

HYDE_SYSTEM_PROMPT = """Eres un experto médico redactando un fragmento de guía clínica.
Genera un párrafo breve (3-5 oraciones) que responda directamente a la consulta del usuario,
como si fuera un extracto de un protocolo clínico o guía de práctica.

Reglas:
- Usa lenguaje técnico médico apropiado
- Incluye datos específicos cuando sea posible (dosis, rangos, clasificaciones)
- No inventes referencias bibliográficas
- Responde SOLO con el párrafo, sin preámbulos"""


def _default_provider() -> Optional[Any]:
    """Construye el proveedor Anthropic del core si hay credenciales; None en caso contrario."""
    try:
        from config.settings import get_settings
        from chathce.adapters.anthropic.provider import AnthropicLLMProvider

        api_key = get_settings().require_anthropic()
        return AnthropicLLMProvider(api_key)
    except Exception as exc:  # noqa: BLE001 - degradacion silenciosa
        logger.warning(f"QueryAugmenter sin proveedor LLM ({exc.__class__.__name__}); se usara la consulta original")
        return None


class QueryAugmenter:
    """Augments user queries via the core LLMProvider to improve RAG retrieval."""

    def __init__(self, llm: Optional[Any] = None, *, model: Optional[str] = None,
                 max_queries: Optional[int] = None, enabled: Optional[bool] = None):
        from config.settings import get_settings

        settings = get_settings()
        self.model = model or settings.rag.query_augmentation_model
        self.max_queries = max_queries or settings.rag.query_augmentation_max_queries
        flag = settings.rag.query_augmentation_enabled and settings.llm.query_augmentation_enabled
        self.enabled = flag if enabled is None else enabled
        self._llm = llm
        self._llm_resolved = llm is not None
        logger.info(f"QueryAugmenter initialized (enabled={self.enabled}, model={self.model}, max_queries={self.max_queries})")

    @property
    def llm(self) -> Optional[Any]:
        if not self._llm_resolved:
            self._llm = _default_provider()
            self._llm_resolved = True
        return self._llm

    # ------------------------------------------------------------------
    def _complete(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        """Generacion sin streaming a traves del port; texto concatenado."""
        provider = self.llm
        if provider is None:
            raise RuntimeError("LLMProvider no disponible")
        from chathce.composition.async_runner import run_sync
        from chathce.ports.llm_provider import LLMMessage, LLMTextDelta

        async def _collect() -> str:
            chunks: List[str] = []
            async for event in provider.generate(
                [LLMMessage.user_text(user)], tools=[], system=system, model=self.model,
                max_tokens=max_tokens, temperature=temperature, timeout_s=30.0, stream=False,
            ):
                if isinstance(event, LLMTextDelta):
                    chunks.append(event.text)
            return "".join(chunks)

        return run_sync(_collect(), timeout=45.0)

    def augment(self, query: str, use_multi_query: bool = True, use_hyde: bool = True) -> List[str]:
        """Original query first, then augmented ones. Falls back to [original] on any error."""
        if not self.enabled or not query.strip() or self.llm is None:
            return [query]

        queries = [query]
        try:
            if use_multi_query:
                queries.extend(self._generate_multi_queries(query))
            if use_hyde:
                hyde_doc = self._generate_hypothetical_document(query)
                if hyde_doc:
                    queries.append(hyde_doc)
            logger.info(f"Query augmented: 1 original + {len(queries) - 1} generated queries")
            return queries
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Query augmentation failed, using original: {e}")
            return [query]

    def _generate_multi_queries(self, query: str) -> List[str]:
        try:
            raw_text = self._complete(
                MULTI_QUERY_SYSTEM_PROMPT.format(num_queries=self.max_queries), query, max_tokens=300, temperature=0.4,
            ).strip()
            alt_queries = [line.strip() for line in raw_text.split("\n") if line.strip() and len(line.strip()) > 10]
            return alt_queries[: self.max_queries]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Multi-query generation failed: {e}")
            return []

    def _generate_hypothetical_document(self, query: str) -> Optional[str]:
        try:
            hyde_text = self._complete(HYDE_SYSTEM_PROMPT, query, max_tokens=250, temperature=0.2).strip()
            if len(hyde_text) < 20:
                return None
            return hyde_text
        except Exception as e:  # noqa: BLE001
            logger.warning(f"HyDE generation failed: {e}")
            return None
