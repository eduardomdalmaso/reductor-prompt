import asyncio
import threading
import time
import uuid
from fastapi import APIRouter, HTTPException, Request, status

from src.adapters.inbound.api.dependencies import generation_queue
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.llm.generation_queue import (
    QueueCancelledError,
    QueueSaturatedError,
    QueueTimeoutError,
)
from src.adapters.outbound.llm.llm_adapters import LLMFactory
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.application.dtos.query_dtos import (
    AnalyzeProjectRequestDTO,
    AnalyzeProjectResponseDTO,
    QueryRequestDTO,
    QueryResponseDTO,
)
from src.application.services.llm_manager_service import llm_manager_service
from src.application.services.system_telemetry_service import telemetry_service
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase

router = APIRouter()


@router.post("/api/v1/query", response_model=QueryResponseDTO)
async def query_knowledge(req: QueryRequestDTO, raw_request: Request):
    """Realiza consulta semântica cirúrgica aplicando compressão de tokens e inferência sem travar o loop."""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    telemetry_service.log("INFO", "QueryEngine", f"[{request_id}] Consulta: '{req.query[:60]}...'")

    try:
        effective_provider = req.llm_provider or llm_manager_service.active_provider
        effective_only_context = req.only_context or not llm_manager_service.llm_enabled
        cancel_event = threading.Event()

        def _execute():
            use_case = QueryBooksUseCase(
                embedding_port=ResilientEmbeddingAdapter(),
                vector_store=ChromaVectorStoreAdapter(),
                llm_port=LLMFactory.create(effective_provider),
                memory_port=ChromaEpisodicMemoryAdapter(),
            )

            def _run_uc():
                return use_case.execute(
                    query=req.query,
                    book_filter=req.book_filter,
                    max_tokens=req.max_tokens,
                    only_context=effective_only_context,
                    use_brain=True,
                    auto_learn=True,
                    profile=req.profile,
                )

            if effective_only_context:
                return _run_uc()
            with generation_queue.slot(is_cancelled=cancel_event.is_set):
                return _run_uc()

        async def _watch_disconnect():
            while not cancel_event.is_set():
                if await raw_request.is_disconnected():
                    cancel_event.set()
                    break
                await asyncio.sleep(0.1)

        watcher = asyncio.create_task(_watch_disconnect())
        try:
            res = await asyncio.to_thread(_execute)
        finally:
            cancel_event.set()
            watcher.cancel()

        duration_ms = (time.time() - start_time) * 1000
        telemetry_service.record_query_metric(
            query=req.query,
            tokens_used=res["tokens_used"],
            tokens_saved=res["tokens_saved"],
            reduction_percentage=res["reduction_percentage"],
            sources_count=len(res.get("sources", [])),
            llm_provider="context-only (bypass)" if effective_only_context else effective_provider,
            duration_ms=duration_ms,
        )
        return QueryResponseDTO(
            query=req.query,
            response=res["response"],
            sources=res["sources"],
            tokens_used=res["tokens_used"],
            tokens_saved=res["tokens_saved"],
            reduction_percentage=res["reduction_percentage"],
            llm_provider="context-only" if effective_only_context else effective_provider,
        )
    except QueueCancelledError as e:
        telemetry_service.log("INFO", "GenerationQueue", f"[{request_id}] {e}")
        raise HTTPException(status_code=499, detail=str(e))
    except QueueSaturatedError as e:
        telemetry_service.log("WARNING", "GenerationQueue", str(e))
        raise HTTPException(status_code=429, detail=str(e))
    except QueueTimeoutError as e:
        telemetry_service.log("WARNING", "GenerationQueue", str(e))
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        telemetry_service.log("ERROR", "QueryEngine", f"Erro ao processar consulta: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/analyze", response_model=AnalyzeProjectResponseDTO)
async def analyze_project(req: AnalyzeProjectRequestDTO):
    """Cruza a arquitetura de um projeto com as melhores práticas dos livros."""
    start_time = time.time()
    telemetry_service.log("INFO", "AnalyzeEngine", f"Iniciando análise de projeto: tópico='{req.focus_topic}'")

    try:
        effective_provider = req.llm_provider or llm_manager_service.active_provider

        def _execute():
            use_case = AnalyzeProjectUseCase(
                embedding_port=ResilientEmbeddingAdapter(),
                vector_store=ChromaVectorStoreAdapter(),
                llm_port=LLMFactory.create(effective_provider),
            )
            return use_case.execute(
                project_description=req.project_description,
                book_filter=req.book_filter,
                focus_topic=req.focus_topic,
                max_tokens=req.max_tokens,
            )

        res = await asyncio.to_thread(_execute)
        stats = res.get("token_stats", {})
        duration_ms = (time.time() - start_time) * 1000
        telemetry_service.record_query_metric(
            query=f"[Analyze] {req.focus_topic or req.project_description[:40]}",
            tokens_used=stats.get("tokens_used", 0),
            tokens_saved=stats.get("tokens_saved", 0),
            reduction_percentage=stats.get("reduction_percent", 0.0),
            sources_count=len(res.get("sources", [])),
            llm_provider=effective_provider,
            duration_ms=duration_ms,
        )
        return AnalyzeProjectResponseDTO(
            project_summary=res["project_summary"],
            book_title=res["book_title"],
            analysis=res["analysis"],
            sources=res["sources"],
            tokens_used=stats.get("tokens_used", 0),
            tokens_saved=stats.get("tokens_saved", 0),
            reduction_percentage=stats.get("reduction_percent", 0.0),
        )
    except Exception as e:
        telemetry_service.log("ERROR", "AnalyzeEngine", f"Erro ao analisar projeto: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
