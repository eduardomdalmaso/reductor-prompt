import logging
import hashlib
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from datetime import datetime

from src.domain.ports.inbound import IQueryBooksUseCase
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort, IEpisodicMemoryPort
from src.domain.entities.memory import MemoryEpisode
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.application.services.query_rewriter_service import QueryRewriterService
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Cache LRU em memória RAM para consultas quentes (<0.1ms de resposta)
_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX_SIZE = 128


class QueryBooksUseCase(IQueryBooksUseCase):
    """Caso de uso de RAG Cognitivo com Memória Episódica (Cérebro Coletivo) e Destilação Contínua."""
    
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

    def _get_cache_key(self, query: str, book_filter: Optional[str], max_tokens: int, only_context: bool, deep_reasoning: bool) -> str:
        raw_key = f"{query.strip().lower()}_{book_filter or ''}_{max_tokens}_{only_context}_{deep_reasoning}"
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
        
        # 1. Verifica se o resultado já está no cache quente em RAM (<0.1ms)
        if cache_key in _QUERY_CACHE:
            logger.info("Retornando resultado instantâneo do cache semântico em RAM (<0.1ms)")
            _QUERY_CACHE.move_to_end(cache_key)
            return _QUERY_CACHE[cache_key]

        # 2. Verifica se a dúvida já foi respondida e indexada no CÉREBRO EPISÓDICO (Semantic Memory Hit)
        if use_brain and self.memory_port and not only_context and not book_filter:
            try:
                q_vector = self.embedding_port.embed_text(query)
                episodes = self.memory_port.search_episodes(
                    query_embedding=q_vector,
                    min_similarity=0.88,
                    top_k=1
                )
                if episodes:
                    hit = episodes[0]
                    logger.info(f"⚡ Semantic Brain Hit! Similaridade: {hit.confidence_score:.2f} - ID: {hit.id}")
                    result = {
                        "query": query,
                        "response": f"🧠 **[Memória Recuperada do Cérebro Coletivo - Confiança: {hit.confidence_score:.0%}]**\n\n{hit.response}",
                        "sources": hit.sources,
                        "tokens_used": hit.tokens_used,
                        "tokens_saved": hit.tokens_saved,
                        "reduction_percentage": hit.reduction_percentage,
                        "context_text": "",
                        "query_variations": [query],
                        "from_brain": True,
                        "brain_episode_id": hit.id
                    }
                    _QUERY_CACHE[cache_key] = result
                    return result
            except Exception as e:
                logger.warning(f"Erro ao verificar memória episódica: {e}. Seguindo com busca nos livros.")

        # 3. Expansão de Query (Multi-Query Expansion)
        if enable_rewriting:
            query_variations = self.rewriter.expand_query(query, max_variations=3)
        else:
            query_variations = [query]

        # 4. Busca Vetorial Multi-Query paralela/em lote nos 194 Livros
        top_k = settings.DEFAULT_TOP_K * 2
        batch_results: List[List] = []

        for q_var in query_variations:
            q_vector = self.embedding_port.embed_text(q_var)
            scored = self.vector_store.search(
                query_embedding=q_vector,
                top_k=top_k,
                book_title_filter=book_filter
            )
            if scored:
                batch_results.append(scored)

        # 5. Fusão de Resultados via Reciprocal Rank Fusion (RRF)
        if batch_results:
            scored_chunks = self.compressor.fuse_chunks_rrf(batch_results)
        else:
            scored_chunks = []

        if not scored_chunks:
            return {
                "query": query,
                "response": "Nenhum conteúdo relevante foi encontrado nos livros indexados para a sua pergunta.",
                "sources": [],
                "tokens_used": 0,
                "tokens_saved": 0,
                "reduction_percentage": 0.0,
                "context_text": "",
                "query_variations": query_variations,
                "from_brain": False
            }

        # 6. Comprime e enxuga o contexto respeitando o orçamento de tokens (Adaptive Budgeting)
        compressed_ctx = self.compressor.compress_and_format(
            query=query,
            scored_chunks=scored_chunks,
            max_tokens=max_tokens
        )

        # Se o usuário pediu apenas o contexto extraído (bypass)
        if only_context:
            result = {
                "query": query,
                "response": compressed_ctx.raw_context_text,
                "sources": compressed_ctx.sources,
                "tokens_used": compressed_ctx.total_tokens,
                "tokens_saved": compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": compressed_ctx.raw_context_text,
                "query_variations": query_variations,
                "from_brain": False
            }
        else:
            # 7. Monta o prompt otimizado (com CoT se deep_reasoning=True)
            sys_inst, user_prompt = self.compressor.build_qa_prompt(
                query=query, 
                compressed_context=compressed_ctx,
                deep_reasoning=deep_reasoning
            )
            
            llm_response = self.llm_port.generate_response(
                system_instruction=sys_inst,
                prompt=user_prompt
            )

            result = {
                "query": query,
                "response": llm_response,
                "sources": compressed_ctx.sources,
                "tokens_used": compressed_ctx.total_tokens,
                "tokens_saved": compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": compressed_ctx.raw_context_text,
                "query_variations": query_variations,
                "from_brain": False
            }

            # 8. Auto-Destilação no Cérebro Coletivo (Salva aprendizado na memória episódica)
            if auto_learn and self.memory_port and not book_filter:
                try:
                    episode_id = hashlib.sha256(query.strip().lower().encode('utf-8')).hexdigest()[:16]
                    q_vector = self.embedding_port.embed_text(query)
                    episode = MemoryEpisode(
                        id=episode_id,
                        query=query.strip(),
                        response=llm_response,
                        sources=compressed_ctx.sources,
                        topic="Auto-Learned RAG Episode",
                        tokens_used=compressed_ctx.total_tokens,
                        tokens_saved=compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                        reduction_percentage=compressed_ctx.token_reduction_percent,
                        created_at=datetime.utcnow().isoformat(),
                        confidence_score=1.0,
                        hit_count=0
                    )
                    self.memory_port.save_episode(episode, q_vector)
                    logger.info(f"✨ Novo conhecimento destilado no cérebro com sucesso: {episode_id}")
                except Exception as e:
                    logger.warning(f"Não foi possível persistir no cérebro episódico: {e}")

        # Armazena no cache LRU em RAM
        if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)
        _QUERY_CACHE[cache_key] = result

        return result
