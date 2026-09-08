from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.application.dtos.query_dtos import (
    QueryRequestDTO, 
    QueryResponseDTO, 
    AnalyzeProjectRequestDTO, 
    AnalyzeProjectResponseDTO
)
from src.adapters.outbound.loaders.document_loaders import CompositeDocumentLoader
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase
from src.config.settings import settings

app = FastAPI(
    title="ReductorPrompt API",
    description="API para Otimização Extrema de Tokens e RAG sobre Livros Técnicos",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ReductorPrompt"}


@app.get("/api/v1/books")
def list_books():
    """Lista todos os livros atualmente indexados no sistema."""
    vector_store = ChromaVectorStoreAdapter()
    return {"books": vector_store.list_indexed_books()}


@app.post("/api/v1/ingest")
def trigger_ingest(force: bool = False):
    """Executa varredura e indexação de novos livros na pasta database."""
    loader = CompositeDocumentLoader()
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    book_repo = FileBookRepositoryAdapter()
    
    use_case = IngestBooksUseCase(
        loader=loader,
        embedding_port=embedding_port,
        vector_store=vector_store,
        book_repo=book_repo
    )
    
    books = use_case.execute(force_reindex=force)
    return {
        "message": f"{len(books)} novos livros foram indexados com sucesso.",
        "indexed_books": [{"title": b.title, "chunks": b.total_chunks, "tokens": b.total_tokens} for b in books]
    }


@app.post("/api/v1/query", response_model=QueryResponseDTO)
def query_knowledge(req: QueryRequestDTO):
    """Realiza uma consulta recuperando apenas o extrato enxuto dos livros para a LLM."""
    try:
        embedding_port = ResilientEmbeddingAdapter()
        vector_store = ChromaVectorStoreAdapter()
        llm_port = LLMFactory.create(req.llm_provider)
        
        use_case = QueryBooksUseCase(
            embedding_port=embedding_port,
            vector_store=vector_store,
            llm_port=llm_port
        )
        
        res = use_case.execute(
            query=req.query,
            book_filter=req.book_filter,
            max_tokens=req.max_tokens,
            only_context=req.only_context
        )
        
        return QueryResponseDTO(
            query=req.query,
            response=res["response"],
            sources=res["sources"],
            tokens_used=res["tokens_used"],
            tokens_saved=res["tokens_saved"],
            reduction_percentage=res["reduction_percentage"],
            llm_provider=req.llm_provider or settings.LLM_PROVIDER
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/analyze", response_model=AnalyzeProjectResponseDTO)
def analyze_project(req: AnalyzeProjectRequestDTO):
    """Cruza a arquitetura de um projeto com as melhores práticas de um livro."""
    try:
        embedding_port = ResilientEmbeddingAdapter()
        vector_store = ChromaVectorStoreAdapter()
        llm_port = LLMFactory.create(req.llm_provider)
        
        use_case = AnalyzeProjectUseCase(
            embedding_port=embedding_port,
            vector_store=vector_store,
            llm_port=llm_port
        )
        
        insight = use_case.execute(
            project_description=req.project_description,
            book_filter=req.book_filter,
            focus_topic=req.focus_topic,
            max_tokens=req.max_tokens
        )
        
        stats = insight.token_stats
        return AnalyzeProjectResponseDTO(
            project_summary=insight.project_summary,
            book_title=insight.book_title,
            analysis=insight.raw_response,
            sources=stats.get("sources", []),
            tokens_used=stats.get("tokens_used", 0),
            tokens_saved=stats.get("tokens_saved", 0),
            reduction_percentage=stats.get("reduction_percent", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
