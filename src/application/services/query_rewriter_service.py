import re
import logging
from typing import List, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Cache LRU para expansões de query (<0.1ms de latência)
_EXPANSION_CACHE: OrderedDict[str, List[str]] = OrderedDict()
_CACHE_MAX_SIZE = 256


class QueryRewriterService:
    """
    Serviço de Expansão e Reescrita de Consultas (Query Expansion / Multi-Query).
    Baseado no padrão 'Query Transformation & Hybrid Retrieval' (Generative AI Design Patterns).
    
    Transforma perguntas curtas ou genéricas em variações técnicas ricas
    no vocabulário dos livros (Postgres, Go, Rust, IA, LLMs, Concorrência, etc.).
    """

    TECHNICAL_SYNONYMS = {
        "concorrencia": ["threads", "async await", "goroutines", "channels", "locks", "atomic operations", "mutex"],
        "concurrency": ["multithreading", "async io", "worker pools", "race conditions", "memory barrier"],
        "banco de dados": ["indexes", "wal write ahead log", "query optimization", "connection pool", "partitioning"],
        "database": ["btree", "mvcc", "acid transactions", "vacuum", "replication", "cache invalidation"],
        "performance": ["latency", "throughput", "profiling", "zero copy", "memory allocation", "cpu cache"],
        "ia": ["transformers", "embeddings", "rag", "fine tuning", "prompt engineering", "context window"],
        "llm": ["tokenization", "self attention", "few shot learning", "hallucination mitigation", "llmops"],
        "arquitetura": ["domain driven design", "clean architecture", "microservices", "event driven", "hexagonal"],
        "architecture": ["separation of concerns", "idempotency", "fault tolerance", "event sourcing"]
    }

    def __init__(self, enable_expansion: bool = True):
        self.enable_expansion = enable_expansion

    def expand_query(self, query: str, max_variations: int = 3) -> List[str]:
        """
        Gera variações semânticas da consulta para busca multi-vetorial.
        Retorna a query original + expansões técnicas.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return [query]

        if not self.enable_expansion:
            return [cleaned_query]

        cache_key = cleaned_query.lower()
        if cache_key in _EXPANSION_CACHE:
            _EXPANSION_CACHE.move_to_end(cache_key)
            return _EXPANSION_CACHE[cache_key]

        variations = [cleaned_query]
        query_lower = cleaned_query.lower()

        # Extrai palavras-chave e encontra termos técnicos correlatos
        discovered_terms = []
        for term, synonyms in self.TECHNICAL_SYNONYMS.items():
            if term in query_lower:
                discovered_terms.extend(synonyms[:3])

        if discovered_terms:
            # Cria variação 1: Query original enriquecida com termos técnicos
            enriched_v1 = f"{cleaned_query} ({', '.join(discovered_terms[:4])})"
            variations.append(enriched_v1)

            # Cria variação 2: Foco em padrões e boas práticas
            enriched_v2 = f"Best practices, design patterns and internals of {cleaned_query}"
            variations.append(enriched_v2)

        # Limita ao número de variações desejadas
        final_variations = variations[:max_variations]

        # Salva no cache LRU
        if len(_EXPANSION_CACHE) >= _CACHE_MAX_SIZE:
            _EXPANSION_CACHE.popitem(last=False)
        _EXPANSION_CACHE[cache_key] = final_variations

        return final_variations
