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
    
    Exemplos de uso:
    - query="Como funciona o RRF no RAG híbrido?", max_tokens=1500
    - query="Otimização de loop em PyTorch", book_filter="Modern Computer Vision"
    
    :param query: A pergunta técnica ou conceito a pesquisar.
    :param book_filter: (Opcional) Filtrar por título de livro específico ou palavra-chave no título.
    :param max_tokens: Limite máximo de tokens do contexto retornado (default: 2000).
    """
    try:
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
    except Exception as e:
        return f"⚠️ Erro ao consultar base de livros: {str(e)}. Verifique se a base ChromaDB está acessível."


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
    
    Exemplos de uso:
    - project_description="API FastAPI com fila Celery e Redis", topic="escalabilidade e resiliência"
    - project_description="Pipeline de ingestão de dados em Rust", topic="gerenciamento de memória e concorrência"
    
    :param project_description: Descrição da arquitetura, pipeline ou problema do projeto.
    :param topic: (Opcional) Foco específico (ex: latência, escalabilidade, concorrência, modelagem).
    :param book_filter: (Opcional) Nome do livro de referência.
    :param max_tokens: Limite de tokens do contexto de livros analisado.
    """
    try:
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
    except Exception as e:
        return f"⚠️ Erro na análise cruzada: {str(e)}."


@mcp.tool()
def list_indexed_books(
    query_filter: Optional[str] = None,
    limit: int = 30
) -> Dict[str, Any]:
    """
    Lista os livros técnicos atualmente indexados e disponíveis no banco vetorial.
    Suporta filtragem por palavra-chave no título/tópico e limite para economizar tokens.
    
    :param query_filter: (Opcional) Filtrar por palavra-chave (ex: 'python', 'rag', 'vision', 'llm', 'rust').
    :param limit: (Opcional) Limite máximo de livros retornados (default: 30).
    """
    try:
        vector_store = ChromaVectorStoreAdapter()
        all_books = vector_store.list_indexed_books()
        
        if query_filter:
            q = query_filter.lower()
            filtered = [
                b for b in all_books 
                if q in b.get("title", "").lower() or q in b.get("filename", "").lower()
            ]
        else:
            filtered = all_books
            
        sliced = filtered[:limit]
        
        # Formata de forma enxuta para o agente
        books_summary = [
            {
                "title": b.get("title"),
                "format": b.get("format"),
                "chunks": b.get("total_chunks", 0),
                "tokens": b.get("total_tokens", 0)
            }
            for b in sliced
        ]
        
        return {
            "total_indexed": len(all_books),
            "matched": len(filtered),
            "returned": len(books_summary),
            "books": books_summary
        }
    except Exception as e:
        return {"error": f"Erro ao listar livros: {str(e)}", "books": []}


if __name__ == "__main__":
    mcp.run(transport="stdio")
