import logging
import hashlib
from typing import Dict, Any, Optional
from collections import OrderedDict

from src.domain.ports.inbound import IQueryBooksUseCase
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Cache LRU em memória para consultas idênticas ou muito frequentes (<1ms de resposta)
_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX_SIZE = 128


class QueryBooksUseCase(IQueryBooksUseCase):
    """Caso de uso para responder perguntas usando trechos cirúrgicos dos livros com cache em memória."""
    
    def __init__(
        self,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        llm_port: ILLMPort,
        compressor_service: Optional[PromptCompressorService] = None
    ):
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.llm_port = llm_port
        self.compressor = compressor_service or PromptCompressorService()

    def _get_cache_key(self, query: str, book_filter: Optional[str], max_tokens: int, only_context: bool) -> str:
        raw_key = f"{query.strip().lower()}_{book_filter or ''}_{max_tokens}_{only_context}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    def execute(
        self, 
        query: str, 
        book_filter: Optional[str] = None, 
        max_tokens: int = 2500,
        only_context: bool = False
    ) -> Dict[str, Any]:
        cache_key = self._get_cache_key(query, book_filter, max_tokens, only_context)
        
        # 1. Verifica se o resultado já está no cache quente
        if cache_key in _QUERY_CACHE:
            logger.info("Retornando resultado instantâneo do cache semântico em memória (<1ms)")
            _QUERY_CACHE.move_to_end(cache_key)
            return _QUERY_CACHE[cache_key]

        # 2. Gera embedding da pergunta localmente (Custo zero)
        query_vector = self.embedding_port.embed_text(query)

        # 3. Busca os trechos mais relevantes no banco vetorial
        top_k = settings.DEFAULT_TOP_K * 2
        scored_chunks = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            book_title_filter=book_filter
        )

        if not scored_chunks:
            return {
                "query": query,
                "response": "Nenhum conteúdo relevante foi encontrado nos livros indexados para a sua pergunta.",
                "sources": [],
                "tokens_used": 0,
                "tokens_saved": 0,
                "reduction_percentage": 0.0,
                "context_text": ""
            }

        # 4. Comprime e enxuga o contexto respeitando o orçamento de tokens
        compressed_ctx = self.compressor.compress_and_format(
            query=query,
            scored_chunks=scored_chunks,
            max_tokens=max_tokens
        )

        # Se o usuário pediu apenas o contexto extraído
        if only_context:
            result = {
                "query": query,
                "response": compressed_ctx.raw_context_text,
                "sources": compressed_ctx.sources,
                "tokens_used": compressed_ctx.total_tokens,
                "tokens_saved": compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens,
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": compressed_ctx.raw_context_text
            }
        else:
            # 5. Monta o prompt otimizado e chama o LLM (Ollama na 5090 ou Gemini)
            sys_inst, user_prompt = self.compressor.build_qa_prompt(query, compressed_ctx)
            
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
                "context_text": compressed_ctx.raw_context_text
            }

        # Armazena no cache LRU
        if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)
        _QUERY_CACHE[cache_key] = result

        return result
