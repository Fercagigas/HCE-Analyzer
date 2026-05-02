"""
Query Augmenter for RAG System

Uses Claude Haiku to augment user queries before retrieval, improving
recall and relevance through two complementary techniques:

1. Multi-Query Generation: Creates alternative queries from different
   perspectives using medical terminology and synonyms.
2. HyDE (Hypothetical Document Embeddings): Generates a hypothetical
   document snippet that would answer the query, providing better
   semantic match with actual indexed documents.

References:
- DMQR-RAG (https://openreview.net/forum?id=lz936bYmb3)
- HyDE (https://arxiv.org/abs/2212.10496)
"""

import logging
from typing import List, Optional

from anthropic import Anthropic

from config.settings import settings

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


class QueryAugmenter:
    """
    Augments user queries using Claude Haiku to improve RAG retrieval.

    Combines multi-query generation and HyDE to produce a set of
    semantically diverse queries that maximize document recall.
    """

    def __init__(self):
        """Initialize with Anthropic client and RAG settings."""
        self.client = Anthropic(api_key=settings.rag.anthropic_api_key)
        self.model = settings.rag.query_augmentation_model
        self.max_queries = settings.rag.query_augmentation_max_queries
        self.enabled = settings.rag.query_augmentation_enabled
        logger.info(
            f"QueryAugmenter initialized (enabled={self.enabled}, "
            f"model={self.model}, max_queries={self.max_queries})"
        )

    def augment(
        self,
        query: str,
        use_multi_query: bool = True,
        use_hyde: bool = True
    ) -> List[str]:
        """
        Augment a query using LLM-based techniques.

        Always includes the original query as the first element.
        Additional queries are generated via multi-query and/or HyDE.

        Args:
            query: Original user query
            use_multi_query: Generate alternative queries
            use_hyde: Generate hypothetical document snippet

        Returns:
            List of queries (original + augmented). Falls back to
            [original] on any error.
        """
        if not self.enabled or not query.strip():
            return [query]

        queries = [query]

        try:
            if use_multi_query:
                alt_queries = self._generate_multi_queries(query)
                queries.extend(alt_queries)

            if use_hyde:
                hyde_doc = self._generate_hypothetical_document(query)
                if hyde_doc:
                    queries.append(hyde_doc)

            logger.info(
                f"Query augmented: 1 original + "
                f"{len(queries) - 1} generated queries"
            )
            return queries

        except Exception as e:
            logger.warning(f"Query augmentation failed, using original: {e}")
            return [query]

    def _generate_multi_queries(self, query: str) -> List[str]:
        """
        Generate alternative queries using Claude Haiku.

        Args:
            query: Original user query

        Returns:
            List of alternative query strings
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.4,
                system=MULTI_QUERY_SYSTEM_PROMPT.format(
                    num_queries=self.max_queries
                ),
                messages=[{"role": "user", "content": query}]
            )

            raw_text = response.content[0].text.strip()
            alt_queries = [
                line.strip()
                for line in raw_text.split("\n")
                if line.strip() and len(line.strip()) > 10
            ]

            # Limit to configured max
            alt_queries = alt_queries[:self.max_queries]

            logger.debug(
                f"Generated {len(alt_queries)} alternative queries "
                f"for: {query[:50]}..."
            )
            return alt_queries

        except Exception as e:
            logger.warning(f"Multi-query generation failed: {e}")
            return []

    def _generate_hypothetical_document(self, query: str) -> Optional[str]:
        """
        Generate a hypothetical document snippet (HyDE technique).

        The generated text acts as a semantic bridge between the user's
        natural language query and the technical language in indexed documents.

        Args:
            query: Original user query

        Returns:
            Hypothetical document snippet, or None on failure
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=250,
                temperature=0.2,
                system=HYDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": query}]
            )

            hyde_text = response.content[0].text.strip()

            if len(hyde_text) < 20:
                logger.debug("HyDE response too short, discarding")
                return None

            logger.debug(
                f"Generated HyDE document ({len(hyde_text)} chars) "
                f"for: {query[:50]}..."
            )
            return hyde_text

        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}")
            return None
