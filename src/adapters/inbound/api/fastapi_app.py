import asyncio
import tracemalloc
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.inbound.api.dependencies import (
    generation_queue,
    get_decision_use_case,
    get_evidence_use_case,
    verify_auth,
)
from src.adapters.inbound.api.observability import (
    check_and_reconcile_indexes,
    router as observability_router,
)
from src.adapters.inbound.api.routes.books_routes import router as books_router
from src.adapters.inbound.api.routes.decision_routes import router as decision_router
from src.adapters.inbound.api.routes.llm_brain_routes import router as llm_brain_router
from src.adapters.inbound.api.routes.mcp_routes import router as mcp_router
from src.adapters.inbound.api.routes.query_routes import router as query_router
from src.config.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    asyncio.create_task(asyncio.to_thread(check_and_reconcile_indexes))
    yield


app = FastAPI(
    title="ReductorPrompt API",
    description="API REST & Tool Server para RAG Híbrido, Governança de Inferência e MCP Hub",
    version="2.0.0",
    lifespan=lifespan,
)

_raw_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", "")
_default_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:8002", "http://127.0.0.1:8002",
    "http://localhost:3001", "http://127.0.0.1:3001",
]
_parsed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip() and o.strip() != "*"] if _raw_origins else []
_allowed_origins = list(set(_default_origins + _parsed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept", "Origin"],
)

app.include_router(observability_router)
app.include_router(books_router)
app.include_router(query_router)
app.include_router(decision_router)
app.include_router(llm_brain_router)
app.include_router(mcp_router)

__all__ = [
    "app",
    "verify_auth",
    "get_evidence_use_case",
    "get_decision_use_case",
    "generation_queue",
]
