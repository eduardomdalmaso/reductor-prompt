import logging
from typing import Optional
from src.domain.entities.book import OptimizationInsight
from src.domain.ports.inbound import IAnalyzeProjectUseCase
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class AnalyzeProjectUseCase(IAnalyzeProjectUseCase):
    """Caso de uso para Análise Cruzada entre o Projeto do Usuário e Conceitos de Livros."""
    
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

    def execute(
        self, 
        project_description: str, 
        book_filter: Optional[str] = None,
        focus_topic: Optional[str] = None,
        max_tokens: int = 2000
    ) -> OptimizationInsight:
        # 1. Constrói query de busca com base no projeto e no foco
        search_query = f"{project_description} {focus_topic or 'arquitetura otimização melhores práticas gargalos'}"
        
        # 2. Embedding local (Custo zero)
        query_vector = self.embedding_port.embed_text(search_query)

        # 3. Busca os trechos mais pertinentes no banco vetorial
        top_k = settings.DEFAULT_TOP_K * 3
        scored_chunks = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            book_title_filter=book_filter
        )

        if not scored_chunks:
            return OptimizationInsight(
                project_summary=project_description[:100] + "...",
                book_title=book_filter or "Todos os livros",
                key_findings=[],
                optimization_opportunities=[],
                architectural_risks=[],
                action_items=[],
                references=[],
                raw_response="Nenhum conceito relevante foi localizado nos livros para este cenário de projeto.",
                token_stats={"tokens_used": 0, "tokens_saved": 0, "reduction_percent": 0.0}
            )

        # 4. Comprime os conceitos encontrados
        compressed_ctx = self.compressor.compress_and_format(
            query=search_query,
            scored_chunks=scored_chunks,
            max_tokens=max_tokens
        )

        # 5. Monta o prompt especializado de Análise Cruzada
        sys_inst, user_prompt = self.compressor.build_cross_analysis_prompt(
            project_description=project_description,
            compressed_context=compressed_ctx,
            focus_topic=focus_topic
        )

        # 6. Chama o LLM para síntese de alto nível
        llm_response = self.llm_port.generate_response(
            system_instruction=sys_inst,
            prompt=user_prompt
        )

        saved_tokens = compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens

        return OptimizationInsight(
            project_summary=project_description[:120] + ("..." if len(project_description) > 120 else ""),
            book_title=book_filter or "Livros da Base",
            key_findings=[],
            optimization_opportunities=[],
            architectural_risks=[],
            action_items=[],
            references=[s.get("book_title", "") for s in compressed_ctx.sources],
            raw_response=llm_response,
            token_stats={
                "tokens_used": compressed_ctx.total_tokens,
                "tokens_saved": saved_tokens,
                "reduction_percent": compressed_ctx.token_reduction_percent,
                "sources": compressed_ctx.sources
            }
        )
