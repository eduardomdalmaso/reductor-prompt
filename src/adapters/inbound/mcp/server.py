import sys
import logging
from typing import Optional, List, Dict, Any
from mcp.server.mcpserver import MCPServer

from src.config.settings import settings
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase

# Desativa logs verbosos no stdout para não corromper o canal stdio do MCP
logging.basicConfig(level=logging.ERROR)

mcp = MCPServer("ReductorPrompt-KnowledgeServer")


@mcp.tool()
def search_books(
    query: str, 
    book_filter: Optional[str] = None, 
    max_tokens: int = 2000
) -> str:
    """
    Busca cirurgicamente nos livros técnicos indexados retornando apenas o contexto
    comprimido e relevante para responder à pergunta com economia máxima de tokens (>95%).
    
    :param query: A pergunta ou conceito a pesquisar nos livros.
    :param book_filter: (Opcional) Filtrar por título de livro específico.
    :param max_tokens: Limite máximo de tokens do contexto retornado (default: 2000).
    """
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    llm_port = LLMFactory.create("ollama")
    
    use_case = QueryBooksUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port
    )
    
    result = use_case.execute(
        query=query,
        book_filter=book_filter,
        max_tokens=max_tokens,
        only_context=True
    )
    
    sources_summary = "\n".join([
        f"• {s['book_title']} ({s.get('chapter', '')}) - Similaridade: {s['score']}"
        for s in result.get("sources", [])
    ])
    
    return (
        f"=== CONTEXTO EXTRAÍDO DOS LIVROS (Tokens: {result['tokens_used']} | Economia: {result['reduction_percentage']}%) ===\n\n"
        f"{result['response']}\n\n"
        f"=== FONTES CONSULTADAS ===\n"
        f"{sources_summary}"
    )


@mcp.tool()
def analyze_project_with_books(
    project_description: str,
    topic: Optional[str] = None,
    book_filter: Optional[str] = None,
    max_tokens: int = 2500
) -> str:
    """
    Realiza uma Análise Cruzada entre a arquitetura/código do seu projeto e os conceitos
    e melhores práticas extraídos dos livros técnicos de referência.
    
    :param project_description: Descrição da arquitetura, pipeline ou problema do projeto.
    :param topic: (Opcional) Foco específico (ex: latência, escalabilidade, concorrência, modelagem).
    :param book_filter: (Opcional) Nome do livro de referência.
    :param max_tokens: Limite de tokens do contexto de livros analisado.
    """
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    llm_port = LLMFactory.create("ollama")
    
    use_case = AnalyzeProjectUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port
    )
    
    insight = use_case.execute(
        project_description=project_description,
        book_filter=book_filter,
        focus_topic=topic,
        max_tokens=max_tokens
    )
    
    return insight.raw_response


@mcp.tool()
def list_indexed_books() -> List[Dict[str, Any]]:
    """
    Lista todos os livros técnicos atualmente indexados e disponíveis no banco vetorial.
    """
    vector_store = ChromaVectorStoreAdapter()
    return vector_store.list_indexed_books()


if __name__ == "__main__":
    mcp.run(transport="stdio")
