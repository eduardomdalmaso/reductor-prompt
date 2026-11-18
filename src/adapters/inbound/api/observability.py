import asyncio
import os
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

from src.adapters.inbound.api.dependencies import generation_queue, verify_auth
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.application.services.llm_manager_service import llm_manager_service
from src.application.services.system_telemetry_service import telemetry_service

router = APIRouter()


def check_and_reconcile_indexes() -> dict:
    try:
        from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
        vs = ChromaVectorStoreAdapter()
        chroma_cnt = vs.collection.count()
        bm25 = BM25SqliteIndex()
        sync_status = bm25.verify_consistency(chroma_cnt)
        if not sync_status["in_sync"] and chroma_cnt > 0:
            telemetry_service.log("WARNING", "IndexSync", f"Desvio detectado ({sync_status}); iniciando rebuild FTS5.")
            bm25.rebuild_from_chroma(vs.collection)
            sync_status = bm25.verify_consistency(chroma_cnt)
        return sync_status
    except Exception as e:
        return {"in_sync": False, "error": str(e)}


def get_process_memory_mb() -> Dict[str, float]:
    rss_mb = 0.0
    try:
        import psutil
        rss_mb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass
    cur_heap, peak_heap = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
    return {
        "pid": os.getpid(),
        "rss_mb": rss_mb,
        "heap_current_mb": round(cur_heap / (1024 * 1024), 2),
        "heap_peak_mb": round(peak_heap / (1024 * 1024), 2),
    }


@router.get("/health")
async def health():
    def _sync_status():
        try:
            from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
            vs = ChromaVectorStoreAdapter()
            return BM25SqliteIndex().verify_consistency(vs.collection.count())
        except Exception as e:
            return {"in_sync": False, "error": str(e)}

    idx_sync = await asyncio.to_thread(_sync_status)
    return {
        "status": "ok" if idx_sync.get("in_sync", False) else "degraded",
        "service": "ReductorPrompt",
        "version": "2.0.0",
        "llm_enabled": llm_manager_service.llm_enabled,
        "active_provider": llm_manager_service.active_provider,
        "index_sync": idx_sync,
        "generation_queue": generation_queue.get_metrics(),
        "process_memory": get_process_memory_mb(),
    }


@router.get("/api/v1/metrics")
async def get_metrics():
    return telemetry_service.get_metrics()


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    q = generation_queue.get_metrics()
    mem = get_process_memory_mb()
    try:
        from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
        in_sync = 1 if BM25SqliteIndex().verify_consistency(ChromaVectorStoreAdapter().collection.count()).get("in_sync") else 0
    except Exception:
        in_sync = 0
    lines = [
        f"reductor_generation_active {q['generation_active']}",
        f"reductor_generation_pending {q['generation_pending']}",
        f"reductor_generation_rejected_total {q['generation_rejected_total']}",
        f"reductor_generation_timeout_total {q['generation_timeout_total']}",
        f"reductor_generation_cancelled_total {q['generation_cancelled_total']}",
        f"reductor_generation_queue_wait_seconds_avg {q['generation_queue_wait_seconds']['avg']}",
        f"reductor_generation_duration_seconds_avg {q['generation_duration_seconds']['avg']}",
        f"reductor_index_in_sync {in_sync}",
        f"reductor_process_rss_bytes {int(mem['rss_mb'] * 1024 * 1024)}",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@router.get("/api/v1/queries/export", dependencies=[Depends(verify_auth)])
async def export_queries(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=1000, ge=1, le=5000),
    since: Optional[float] = Query(default=None),
):
    content = await asyncio.to_thread(telemetry_service.export_queries, format, limit, since)
    media_type = "text/csv" if format == "csv" else "application/json"
    filename = f"reductor_queries_{int(time.time())}.{format}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/api/v1/logs", dependencies=[Depends(verify_auth)])
async def get_logs(limit: int = Query(default=100, le=500), level: Optional[str] = None):
    return {"logs": telemetry_service.get_logs(limit=limit, level_filter=level)}


@router.get("/api/v1/report/pdf", summary="Obtém o relatório de auditoria de segurança compilado em PDF")
async def get_security_audit_report():
    pdf_path = Path(__file__).resolve().parents[4] / "docs" / "security-audit" / "relatorio-auditoria-seguranca.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Relatório em PDF não encontrado.")
    return FileResponse(path=str(pdf_path), media_type="application/pdf", filename="relatorio-auditoria-seguranca.pdf")
