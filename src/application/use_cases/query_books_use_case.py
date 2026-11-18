import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from src.application.services.hybrid_retrieval_helpers import (
    apply_lexical_identifier_boost,
    extract_technical_identifiers,
    fuse_hybrid_dense_bm25,
    resolve_book_filter,
    retrieve_hybrid_candidates,
)
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.application.services.query_execution_helpers import (
    build_query_cache_key,
    load_consistent_bm25_index,
    persist_auto_learn,
    search_empirical_episodes,
)
from src.application.services.query_rewriter_service import QueryRewriterService
from src.config.settings import settings
from src.domain.entities.memory import MemoryEpisode
from src.domain.ports.inbound import IQueryBooksUseCase
from src.domain.ports.outbound import IEmbeddingPort, IEpisodicMemoryPort, ILLMPort, IVectorStorePort

logger = logging.getLogger(__name__)

_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX_SIZE = 128
_CACHE_EPOCH = 1
RETRIEVAL_ALGO_VERSION = "hybrid-bm25-v4"
PROMPT_TEMPLATE_VERSION = "qa-v4-strict-urls"


def invalidate_query_cache() -> int:
    """Limpa o cache de consultas e incrementa a época de corpus."""
    global _CACHE_EPOCH
    _QUERY_CACHE.clear()
    _CACHE_EPOCH += 1
    return _CACHE_EPOCH


class QueryBooksUseCase(IQueryBooksUseCase):
    """Caso de uso de RAG Cognitivo Bilateral (Teoria dos Livros + Evidências Empíricas)."""

    def __init__(
        self,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        llm_port: ILLMPort,
        memory_port: Optional[IEpisodicMemoryPort] = None,
        compressor_service: Optional[PromptCompressorService] = None,
        rewriter_service: Optional[QueryRewriterService] = None,
        bm25_index: Optional[Any] = None,
    ):
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.llm_port = llm_port
        self.memory_port = memory_port
        self.compressor = compressor_service or PromptCompressorService()
        self.rewriter = rewriter_service or QueryRewriterService()
        self.bm25_index = bm25_index

    def _get_bm25_index(self):
        idx = load_consistent_bm25_index(self.vector_store, self.bm25_index, logger)
        if idx is not None:
            self.bm25_index = idx
        return idx

    def _get_cache_key(
        self, query: str, book_filter: Optional[str], max_tokens: int,
        only_ctx: bool, deep: bool, enable_rewriting: bool, use_brain: bool, profile: str = "economy",
    ) -> str:
        return build_query_cache_key(
            query, book_filter, max_tokens, only_ctx, deep, enable_rewriting,
            use_brain, profile, _CACHE_EPOCH, RETRIEVAL_ALGO_VERSION, PROMPT_TEMPLATE_VERSION,
        )

    def execute(
        self, query: str, book_filter: Optional[str] = None, max_tokens: int = 2500,
        only_context: bool = False, deep_reasoning: bool = False, enable_rewriting: bool = True,
        use_brain: bool = True, auto_learn: bool = True, profile: str = "economy",
    ) -> Dict[str, Any]:
        cache_key = self._get_cache_key(
            query, book_filter, max_tokens, only_context, deep_reasoning, enable_rewriting, use_brain, profile
        )
        if cache_key in _QUERY_CACHE:
            _QUERY_CACHE.move_to_end(cache_key)
            return {**_QUERY_CACHE[cache_key], "cache_hit": True}

        available_titles = []
        try:
            available_titles = [b.get("title", "") for b in self.vector_store.list_indexed_books() if b.get("title")]
        except Exception:
            pass
        effective_filter, ambiguous_titles = resolve_book_filter(query, book_filter, available_titles)
        if ambiguous_titles:
            return {
                "query": query,
                "response": f"Título ambíguo detectado. Especifique qual livro deseja consultar: {', '.join(ambiguous_titles[:5])}.",
                "sources": [], "tokens_used": 0, "tokens_saved": 0, "reduction_percentage": 0.0,
                "context_text": "", "query_variations": [query], "from_brain": False, "cache_hit": False,
                "ambiguous_books": ambiguous_titles,
            }

        variations = self.rewriter.expand_query(query, max_variations=3) if enable_rewriting else [query]
        empirical_episodes: List[MemoryEpisode] = (
            search_empirical_episodes(query, self.embedding_port, self.memory_port, logger)
            if (use_brain and self.memory_port and not book_filter) else []
        )

        bm25 = None if profile == "legacy" else self._get_bm25_index()
        scored_chunks = retrieve_hybrid_candidates(
            query, variations, effective_filter, self.embedding_port,
            self.vector_store, self.compressor, bm25, settings.DEFAULT_TOP_K, logger,
        )
        if not scored_chunks and not empirical_episodes:
            return {
                "query": query, "response": "Nenhum conteúdo técnico relevante foi localizado.",
                "sources": [], "tokens_used": 0, "tokens_saved": 0, "reduction_percentage": 0.0,
                "context_text": "", "query_variations": variations, "from_brain": False, "cache_hit": False,
            }

        if profile == "economy":
            compressed_ctx = self.compressor.compress_and_format(query, scored_chunks[:12], max_tokens=min(max_tokens, 2500), strategy="balanced")
        elif profile == "fidelity":
            compressed_ctx = self.compressor.compress_and_format(query, scored_chunks[:10], max_tokens=max(max_tokens, 10000), strategy="conservative", max_cut_percent=5.0)
        else:
            compressed_ctx = self.compressor.compress_and_format(query, scored_chunks, max_tokens=max_tokens)

        empirical_text = self.compressor.format_empirical_evidence(empirical_episodes)
        all_sources = list(compressed_ctx.sources) + [
            {
                "book_title": f"Empirical: {ep.project_source or 'HydraStream'}",
                "chapter": f"Exp: {ep.experiment_id or ep.id} ({f'#{ep.commit_hash[:7]}' if ep.commit_hash else 'N/A'} | {ep.environment_context.get('hardware') or ep.environment_context.get('gpu') or 'N/A'})",
                "score": ep.confidence_score, "provenance": "empirical",
            }
            for ep in empirical_episodes
        ]
        full_context_text = f"{compressed_ctx.raw_context_text}\n\n{empirical_text}" if empirical_text else compressed_ctx.raw_context_text
        tokens_used = compressed_ctx.total_tokens + len(empirical_text.split())
        tokens_saved = max(0, compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens)

        if only_context:
            result = {
                "query": query, "response": full_context_text, "sources": all_sources,
                "tokens_used": tokens_used, "tokens_saved": tokens_saved,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text, "query_variations": variations,
                "from_brain": bool(empirical_episodes), "cache_hit": False,
            }
        else:
            sys_inst, user_prompt = self.compressor.build_qa_prompt(query, compressed_ctx, deep_reasoning=deep_reasoning, empirical_context=empirical_text)
            llm_response = self.llm_port.generate_response(system_instruction=sys_inst, prompt=user_prompt)
            llm_response, fabricated_urls = self.compressor.validate_and_sanitize_urls(llm_response, full_context_text)
            grounding = self.compressor.verify_citation_grounding(llm_response, all_sources)
            grounding["fabricated_urls_blocked"] = fabricated_urls
            result = {
                "query": query, "response": llm_response, "sources": all_sources,
                "tokens_used": tokens_used, "tokens_saved": tokens_saved,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text, "query_variations": variations,
                "from_brain": bool(empirical_episodes), "cache_hit": False, "citation_grounding": grounding,
            }
            if auto_learn and self.memory_port and not book_filter:
                persist_auto_learn(query, llm_response, all_sources, result, self.embedding_port, self.memory_port, logger)

        if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)
        _QUERY_CACHE[cache_key] = result
        return result
