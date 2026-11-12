import logging
import hashlib
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from datetime import datetime, timezone

from src.domain.ports.inbound import IQueryBooksUseCase
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort, IEpisodicMemoryPort
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.application.services.query_rewriter_service import QueryRewriterService
from src.config.settings import settings

logger = logging.getLogger(__name__)

_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX_SIZE = 128


class QueryBooksUseCase(IQueryBooksUseCase):
    """Caso de uso de RAG Cognitivo Bilateral (Teoria dos Livros + Evidências Empíricas)."""

    def __init__(
        self,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        llm_port: ILLMPort,
        memory_port: Optional[IEpisodicMemoryPort] = None,
        compressor_service: Optional[PromptCompressorService] = None,
        rewriter_service: Optional[QueryRewriterService] = None
    ):
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.llm_port = llm_port
        self.memory_port = memory_port
        self.compressor = compressor_service or PromptCompressorService()
        self.rewriter = rewriter_service or QueryRewriterService()

    def _get_cache_key(self, query: str, book_filter: Optional[str], max_tokens: int, only_ctx: bool, deep: bool) -> str:
        raw_key = f"{query.strip().lower()}_{book_filter or ''}_{max_tokens}_{only_ctx}_{deep}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    def execute(
        self,
        query: str,
        book_filter: Optional[str] = None,
        max_tokens: int = 2500,
        only_context: bool = False,
        deep_reasoning: bool = False,
        enable_rewriting: bool = True,
        use_brain: bool = True,
        auto_learn: bool = True
    ) -> Dict[str, Any]:
        cache_key = self._get_cache_key(query, book_filter, max_tokens, only_context, deep_reasoning)

        if cache_key in _QUERY_CACHE:
            _QUERY_CACHE.move_to_end(cache_key)
            return _QUERY_CACHE[cache_key]

        # 1. Expansão de Query
        variations = self.rewriter.expand_query(query, max_variations=3) if enable_rewriting else [query]

        # 2. Busca de Evidências Empíricas no Cérebro (HydraStream)
        empirical_episodes: List[MemoryEpisode] = []
        if use_brain and self.memory_port and not book_filter:
            try:
                base_q_vector = self.embedding_port.embed_text(query)
                empirical_episodes = self.memory_port.search_episodes(
                    query_embedding=base_q_vector,
                    min_similarity=0.75,
                    top_k=2,
                    provenance=ProvenanceType.EMPIRICAL,
                    status=EvidenceStatus.VALID
                )
            except Exception as e:
                logger.warning(f"Busca empírica falhou: {e}")

        # 3. Busca Vetorial nos Livros
        top_k = settings.DEFAULT_TOP_K * 2
        batch_results: List[List] = []
        for q_var in variations:
            q_vec = self.embedding_port.embed_text(q_var)
            scored = self.vector_store.search(query_embedding=q_vec, top_k=top_k, book_title_filter=book_filter)
            if scored:
                batch_results.append(scored)

        scored_chunks = self.compressor.fuse_chunks_rrf(batch_results) if batch_results else []

        if not scored_chunks and not empirical_episodes:
            return {
                "query": query, "response": "Nenhum conteúdo técnico relevante foi localizado.",
                "sources": [], "tokens_used": 0, "tokens_saved": 0, "reduction_percentage": 0.0,
                "context_text": "", "query_variations": variations, "from_brain": False
            }

        # 4. Formata contexto teórico e empírico bilateral
        compressed_ctx = self.compressor.compress_and_format(query=query, scored_chunks=scored_chunks, max_tokens=max_tokens)
        empirical_text = self.compressor.format_empirical_evidence(empirical_episodes)

        all_sources = list(compressed_ctx.sources)
        for ep in empirical_episodes:
            hw = ep.environment_context.get("hardware") or ep.environment_context.get("gpu") or "N/A"
            commit = f"#{ep.commit_hash[:7]}" if ep.commit_hash else "N/A"
            all_sources.append({
                "book_title": f"Empirical: {ep.project_source or 'HydraStream'}",
                "chapter": f"Exp: {ep.experiment_id or ep.id} ({commit} | {hw})",
                "score": ep.confidence_score,
                "provenance": "empirical"
            })

        full_context_text = compressed_ctx.raw_context_text
        if empirical_text:
            full_context_text = f"{full_context_text}\n\n{empirical_text}"

        # 5. Entrega de Contexto Direto (Bypass)
        if only_context:
            result = {
                "query": query,
                "response": full_context_text,
                "sources": all_sources,
                "tokens_used": compressed_ctx.total_tokens + len(empirical_text.split()),
                "tokens_saved": compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text,
                "query_variations": variations,
                "from_brain": bool(empirical_episodes)
            }
        else:
            # 6. Síntese Bilateral com LLM
            sys_inst, user_prompt = self.compressor.build_qa_prompt(
                query=query, compressed_context=compressed_ctx,
                deep_reasoning=deep_reasoning, empirical_context=empirical_text
            )
            llm_response = self.llm_port.generate_response(system_instruction=sys_inst, prompt=user_prompt)

            result = {
                "query": query,
                "response": llm_response,
                "sources": all_sources,
                "tokens_used": compressed_ctx.total_tokens + len(empirical_text.split()),
                "tokens_saved": compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text,
                "query_variations": variations,
                "from_brain": bool(empirical_episodes)
            }

            if auto_learn and self.memory_port and not book_filter:
                try:
                    episode_id = hashlib.sha256(query.strip().lower().encode('utf-8')).hexdigest()[:16]
                    q_vec = self.embedding_port.embed_text(query)
                    self.memory_port.save_episode(
                        MemoryEpisode(
                            id=episode_id, query=query.strip(), response=llm_response,
                            sources=all_sources, topic="Theoretical Synthesis",
                            tokens_used=result["tokens_used"], tokens_saved=result["tokens_saved"],
                            reduction_percentage=result["reduction_percentage"],
                            provenance=ProvenanceType.THEORETICAL
                        ),
                        q_vec
                    )
                except Exception as e:
                    logger.warning(f"Falha ao persistir auto-learn: {e}")

        if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)
        _QUERY_CACHE[cache_key] = result
        return result
