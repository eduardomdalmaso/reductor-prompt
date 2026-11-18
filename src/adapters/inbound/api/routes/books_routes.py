import asyncio
from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.inbound.api.dependencies import FetchBooksRequestDTO, verify_auth
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.loaders.document_loaders import CompositeDocumentLoader
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.application.services.system_telemetry_service import telemetry_service
from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase

router = APIRouter()


@router.get("/api/v1/books")
async def list_books():
    """Lista todos os livros atualmente indexados no sistema (execução em worker thread)."""
    try:
        books = await asyncio.to_thread(lambda: ChromaVectorStoreAdapter().list_indexed_books())
        return {"books": books, "count": len(books)}
    except Exception as e:
        telemetry_service.log("ERROR", "VectorStore", f"Erro ao listar livros: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/ingest", dependencies=[Depends(verify_auth)])
async def trigger_ingest(force: bool = False):
    """Executa varredura e indexação de novos livros sem bloquear o event loop."""
    telemetry_service.log("INFO", "Ingestor", f"Disparando ingestão (force={force})...")

    def _run_ingest():
        use_case = IngestBooksUseCase(
            loader=CompositeDocumentLoader(),
            embedding_port=ResilientEmbeddingAdapter(),
            vector_store=ChromaVectorStoreAdapter(),
            book_repo=FileBookRepositoryAdapter(),
        )
        return use_case.execute(force_reindex=force)

    books = await asyncio.to_thread(_run_ingest)
    telemetry_service.log("INFO", "Ingestor", f"Ingestão concluída: {len(books)} livros processados.")
    return {
        "message": f"{len(books)} novos livros foram processados com sucesso.",
        "indexed_books": [{"title": b.title, "chunks": b.total_chunks, "tokens": b.total_tokens} for b in books],
    }


@router.delete("/api/v1/books/{book_id}", dependencies=[Depends(verify_auth)])
async def delete_book_endpoint(book_id: str):
    """Deleta um livro específico do banco vetorial pelo ID."""
    try:
        def _delete():
            from src.application.use_cases.query_books_use_case import invalidate_query_cache
            ChromaVectorStoreAdapter().delete_book(book_id)
            try:
                from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
                BM25SqliteIndex().delete_book(book_id)
            except Exception as e:
                telemetry_service.log("WARNING", "BM25Index", f"Falha ao remover {book_id} do FTS5: {e}")
            invalidate_query_cache()
            return True

        await asyncio.to_thread(_delete)
        telemetry_service.log("INFO", "VectorStore", f"Livro {book_id} removido com sucesso.")
        return {"status": "ok", "message": f"Livro '{book_id}' removido do banco vetorial."}
    except Exception as e:
        telemetry_service.log("ERROR", "VectorStore", f"Erro ao deletar livro {book_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/fetch", dependencies=[Depends(verify_auth)])
async def fetch_materials(req: FetchBooksRequestDTO):
    """Baixa livros ou papers dinamicamente da web/GitHub em segundo plano com proteção anti-SSRF."""
    from scripts.fetch_books import is_safe_public_url, run_pipeline
    telemetry_service.log("INFO", "Fetcher", f"Iniciando download dinâmico para: {req.urls}")
    try:
        urls_list = [u.strip() for u in req.urls.split(",") if u.strip()]
        if not urls_list:
            raise HTTPException(status_code=400, detail="Nenhuma URL informada.")

        for u in urls_list:
            is_safe, reason = is_safe_public_url(u)
            if not is_safe:
                telemetry_service.log("WARNING", "SecurityGuard", f"Bloqueio de SSRF na URL: {u} ({reason})")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"URL bloqueada por segurança (SSRF): {reason}")

        result = await asyncio.to_thread(run_pipeline, sources=urls_list, auto_ingest=req.ingest_after, workers=4)
        telemetry_service.log("INFO", "Fetcher", f"Download concluído: {result.get('downloaded', 0)} arquivos baixados.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        telemetry_service.log("ERROR", "Fetcher", f"Erro no download dinâmico: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
