from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer

from src.config.settings import settings
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory
from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase


def register_knowledge_tools(mcp: MCPServer):
    @mcp.tool()
    def search_books(
        query: str, 
        book_filter: Optional[str] = None, 
        max_tokens: int = 2000,
        use_local_llm: bool = False,
        provider: Optional[str] = None,
        deep_reasoning: bool = False,
        use_brain: bool = True
    ) -> str:
        """
        Busca cirurgicamente nos livros técnicos indexados com suporte ao Cérebro Episódico.
        Por padrão (use_local_llm=False), retorna o contexto comprimido literal dos livros (>95% economia).
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            memory_port = ChromaEpisodicMemoryAdapter()
            selected_provider = provider or settings.LLM_PROVIDER
            llm_port = LLMFactory.create(selected_provider)
            
            use_case = QueryBooksUseCase(
                embedding_port=embedding_port, vector_store=vector_store,
                llm_port=llm_port, memory_port=memory_port
            )
            result = use_case.execute(
                query=query, book_filter=book_filter, max_tokens=max_tokens,
                only_context=not use_local_llm, deep_reasoning=deep_reasoning,
                use_brain=use_brain, auto_learn=True
            )
            sources_summary = "\n".join([
                f"• {s['book_title']} ({s.get('chapter', '')}) - Similaridade: {s['score']}"
                for s in result.get("sources", [])
            ])
            origin_label = "MEMÓRIA DO CÉREBRO EPISÓDICO" if result.get("from_brain") else (
                f"RESPOSTA SINTETIZADA PELA LLM ({selected_provider.upper()})" if use_local_llm else "CONTEXTO EXTRAÍDO DOS LIVROS"
            )
            header = f"=== {origin_label} (Tokens: {result['tokens_used']} | Economia: {result['reduction_percentage']}%) ===\n\n"
            sources_section = f"\n\n=== FONTES CONSULTADAS ===\n{sources_summary}" if sources_summary else ""
            return f"{header}{result['response']}{sources_section}"
        except Exception as e:
            return f"⚠️ Erro ao consultar base de livros: {str(e)}."

    @mcp.tool()
    def validate_reasoning(
        hypothesis_or_plan: str,
        topic: Optional[str] = None,
        book_filter: Optional[str] = None,
        provider: Optional[str] = None,
        max_tokens: int = 2500
    ) -> str:
        """
        Validação Cruzada de Raciocínio (Peer Review Cognitivo).
        Confronta a hipótese do agente contra os livros técnicos com parecer da LLM.
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            selected_provider = provider or settings.LLM_PROVIDER
            llm_port = LLMFactory.create(selected_provider)
            use_case = AnalyzeProjectUseCase(embedding_port=embedding_port, vector_store=vector_store, llm_port=llm_port)
            
            prompt = (
                f"[HIPÓTESE / RACIOCÍNIO DO AGENTE PARA VALIDAÇÃO]:\n{hypothesis_or_plan}\n\n"
                f"Por favor, compare criticamente este raciocínio com os livros técnicos. "
                f"Avalie se a proposta é sólida, se há falhas conceituais e aponte trade-offs."
            )
            insight = use_case.execute(
                project_description=prompt, book_filter=book_filter,
                focus_topic=topic or "Validação Crítica de Hipótese e Alinhamento com a Literatura",
                max_tokens=max_tokens
            )
            return f"=== RESULTADO DA VALIDAÇÃO CRUZADA ({selected_provider.upper()} + LIVROS) ===\n\n{insight.raw_response}"
        except Exception as e:
            return f"⚠️ Erro ao validar raciocínio: {str(e)}."

    @mcp.tool()
    def analyze_project_with_books(
        project_description: str,
        topic: Optional[str] = None,
        book_filter: Optional[str] = None,
        max_tokens: int = 2500
    ) -> str:
        """
        Realiza uma Análise Cruzada entre a arquitetura/código do projeto e os conceitos dos livros.
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            llm_port = LLMFactory.create("ollama")
            use_case = AnalyzeProjectUseCase(embedding_port=embedding_port, vector_store=vector_store, llm_port=llm_port)
            insight = use_case.execute(project_description=project_description, book_filter=book_filter, focus_topic=topic, max_tokens=max_tokens)
            return insight.raw_response
        except Exception as e:
            return f"⚠️ Erro na análise cruzada: {str(e)}."

    @mcp.tool()
    def list_indexed_books(query_filter: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
        """Lista os livros técnicos atualmente indexados no banco vetorial."""
        try:
            vector_store = ChromaVectorStoreAdapter()
            all_books = vector_store.list_indexed_books()
            filtered = [b for b in all_books if query_filter.lower() in b.get("title", "").lower()] if query_filter else all_books
            sliced = filtered[:limit]
            summary = [{"title": b.get("title"), "format": b.get("format"), "chunks": b.get("total_chunks", 0)} for b in sliced]
            return {"total_indexed": len(all_books), "matched": len(filtered), "returned": len(summary), "books": summary}
        except Exception as e:
            return {"error": f"Erro ao listar livros: {str(e)}", "books": []}
