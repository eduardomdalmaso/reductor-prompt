import asyncio
import time
import secrets
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status, Query, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from src.application.dtos.query_dtos import (
    QueryRequestDTO, 
    QueryResponseDTO, 
    AnalyzeProjectRequestDTO, 
    AnalyzeProjectResponseDTO
)
from src.adapters.outbound.loaders.document_loaders import CompositeDocumentLoader
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.application.services.hardware_budget_advisor_service import hardware_advisor_service
from src.application.services.system_telemetry_service import telemetry_service
from src.application.services.llm_manager_service import llm_manager_service
from src.config.settings import settings

app = FastAPI(
    title="ReductorPrompt API",
    description="API REST & Tool Server para Otimização Extrema de Tokens (>98%), RAG Cognitivo e MCP Hub",
    version="2.0.0"
)

# Configuração de CORS Seguro com Origens Explícitas
_raw_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] if _raw_origins else [
    "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Provedores de Autenticação Segura (X-API-Key ou Bearer Token)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


async def verify_auth(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth)
):
    """Verifica autenticação se API_SECURITY_KEY estiver configurada no .env."""
    required_key = settings.API_SECURITY_KEY
    if not required_key:
        return True

    token = api_key or (bearer.credentials if bearer else None)
    if not token or not secrets.compare_digest(token, required_key):
        telemetry_service.log("WARNING", "SecurityGuard", "Tentativa de acesso não autorizada a endpoint protegido.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado. Forneça um X-API-Key ou Bearer Token válido.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True


# ==========================================
# DTOs Adicionais
# ==========================================
class LLMConfigDTO(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    enabled: Optional[bool] = None


class LLMToggleDTO(BaseModel):
    enabled: bool


class UnloadVRAMDTO(BaseModel):
    model_name: Optional[str] = None


class MCPCallDTO(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class FetchBooksRequestDTO(BaseModel):
    urls: str = Field(..., description="URLs separadas por vírgula ou repositórios GitHub")
    ingest_after: bool = Field(default=False, description="Executar indexação vetorial imediatamente após download")


class TeachBrainDTO(BaseModel):
    query: str = Field(..., description="Pergunta ou problema chave")
    insight: str = Field(..., description="Resposta lapidada ou código canônico")
    topic: Optional[str] = Field(default=None, description="Tópico ou categoria do conhecimento")



# ==========================================
# Rotas de Saúde & Livros (Não Bloqueantes)
# ==========================================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ReductorPrompt",
        "version": "2.0.0",
        "llm_enabled": llm_manager_service.llm_enabled,
        "active_provider": llm_manager_service.active_provider
    }


@app.get("/api/v1/books")
async def list_books():
    """Lista todos os livros atualmente indexados no sistema (execução em worker thread)."""
    try:
        def _fetch():
            vector_store = ChromaVectorStoreAdapter()
            return vector_store.list_indexed_books()

        books = await asyncio.to_thread(_fetch)
        return {"books": books, "count": len(books)}
    except Exception as e:
        telemetry_service.log("ERROR", "VectorStore", f"Erro ao listar livros: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest", dependencies=[Depends(verify_auth)])
async def trigger_ingest(force: bool = False):
    """Executa varredura e indexação de novos livros sem bloquear o event loop."""
    telemetry_service.log("INFO", "Ingestor", f"Disparando ingestão (force={force})...")
    
    def _run_ingest():
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
        return use_case.execute(force_reindex=force)

    books = await asyncio.to_thread(_run_ingest)
    telemetry_service.log("INFO", "Ingestor", f"Ingestão concluída: {len(books)} livros processados.")
    return {
        "message": f"{len(books)} novos livros foram processados com sucesso.",
        "indexed_books": [{"title": b.title, "chunks": b.total_chunks, "tokens": b.total_tokens} for b in books]
    }


@app.delete("/api/v1/books/{book_id}", dependencies=[Depends(verify_auth)])
async def delete_book_endpoint(book_id: str):
    """Deleta um livro específico do banco vetorial pelo ID."""
    try:
        def _delete():
            vector_store = ChromaVectorStoreAdapter()
            vector_store.delete_book(book_id)
            return True
        await asyncio.to_thread(_delete)
        telemetry_service.log("INFO", "VectorStore", f"Livro {book_id} removido com sucesso.")
        return {"status": "ok", "message": f"Livro '{book_id}' removido do banco vetorial."}
    except Exception as e:
        telemetry_service.log("ERROR", "VectorStore", f"Erro ao deletar livro {book_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/fetch", dependencies=[Depends(verify_auth)])
async def fetch_materials(req: FetchBooksRequestDTO):
    """Baixa livros ou papers dinamicamente da web/GitHub em segundo plano com proteção anti-SSRF."""
    from scripts.fetch_books import run_pipeline, is_safe_public_url
    telemetry_service.log("INFO", "Fetcher", f"Iniciando download dinâmico para: {req.urls}")
    try:
        urls_list = [u.strip() for u in req.urls.split(",") if u.strip()]
        if not urls_list:
            raise HTTPException(status_code=400, detail="Nenhuma URL informada.")

        # Validação de Segurança contra SSRF
        for u in urls_list:
            is_safe, reason = is_safe_public_url(u)
            if not is_safe:
                telemetry_service.log("WARNING", "SecurityGuard", f"Bloqueio de SSRF na URL: {u} ({reason})")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"URL bloqueada por segurança (SSRF): {reason}"
                )

        result = await asyncio.to_thread(
            run_pipeline,
            sources=urls_list,
            auto_ingest=req.ingest_after,
            workers=4
        )
        telemetry_service.log("INFO", "Fetcher", f"Download concluído: {result.get('downloaded', 0)} arquivos baixados.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        telemetry_service.log("ERROR", "Fetcher", f"Erro no download dinâmico: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Rotas de Consulta & RAG com Telemetria (Assíncrona)
# ==========================================
@app.post("/api/v1/query", response_model=QueryResponseDTO)
async def query_knowledge(req: QueryRequestDTO):
    """Realiza consulta semântica cirúrgica aplicando compressão de tokens e inferência sem travar o loop."""
    start_time = time.time()
    telemetry_service.log("INFO", "QueryEngine", f"Recebida consulta: '{req.query[:60]}...'")

    try:
        effective_provider = req.llm_provider or llm_manager_service.active_provider
        effective_only_context = req.only_context or not llm_manager_service.llm_enabled

        def _execute():
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            memory_port = ChromaEpisodicMemoryAdapter()
            llm_port = LLMFactory.create(effective_provider)
            
            use_case = QueryBooksUseCase(
                embedding_port=embedding_port,
                vector_store=vector_store,
                llm_port=llm_port,
                memory_port=memory_port
            )
            
            return use_case.execute(
                query=req.query,
                book_filter=req.book_filter,
                max_tokens=req.max_tokens,
                only_context=effective_only_context,
                use_brain=True,
                auto_learn=True
            )

        res = await asyncio.to_thread(_execute)
        
        duration_ms = (time.time() - start_time) * 1000
        telemetry_service.record_query_metric(
            query=req.query,
            tokens_used=res["tokens_used"],
            tokens_saved=res["tokens_saved"],
            reduction_percentage=res["reduction_percentage"],
            sources_count=len(res.get("sources", [])),
            llm_provider="context-only (bypass)" if effective_only_context else effective_provider,
            duration_ms=duration_ms
        )

        return QueryResponseDTO(
            query=req.query,
            response=res["response"],
            sources=res["sources"],
            tokens_used=res["tokens_used"],
            tokens_saved=res["tokens_saved"],
            reduction_percentage=res["reduction_percentage"],
            llm_provider="context-only" if effective_only_context else effective_provider
        )
    except Exception as e:
        telemetry_service.log("ERROR", "QueryEngine", f"Erro ao processar consulta: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/analyze", response_model=AnalyzeProjectResponseDTO)
async def analyze_project(req: AnalyzeProjectRequestDTO):
    """Cruza a arquitetura de um projeto com as melhores práticas dos livros."""
    start_time = time.time()
    telemetry_service.log("INFO", "AnalyzeEngine", f"Iniciando análise de projeto: tópico='{req.focus_topic}'")

    try:
        effective_provider = req.llm_provider or llm_manager_service.active_provider

        def _run_analysis():
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            llm_port = LLMFactory.create(effective_provider)
            
            use_case = AnalyzeProjectUseCase(
                embedding_port=embedding_port,
                vector_store=vector_store,
                llm_port=llm_port
            )
            
            return use_case.execute(
                project_description=req.project_description,
                book_filter=req.book_filter,
                focus_topic=req.focus_topic,
                max_tokens=req.max_tokens
            )

        insight = await asyncio.to_thread(_run_analysis)
        
        stats = insight.token_stats
        duration_ms = (time.time() - start_time) * 1000
        telemetry_service.record_query_metric(
            query=f"Análise de Projeto: {req.focus_topic or 'Geral'}",
            tokens_used=stats.get("tokens_used", 0),
            tokens_saved=stats.get("tokens_saved", 0),
            reduction_percentage=stats.get("reduction_percent", 0.0),
            sources_count=len(stats.get("sources", [])),
            llm_provider=effective_provider,
            duration_ms=duration_ms
        )

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
        telemetry_service.log("ERROR", "AnalyzeEngine", f"Erro na análise do projeto: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# Rotas de Telemetria, Logs e Métricas
# ==========================================
@app.get("/api/v1/metrics")
async def get_metrics():
    """Retorna métricas consolidadas de economia de tokens, economia em USD e latência."""
    return telemetry_service.get_metrics()


@app.get("/api/v1/queries/export", dependencies=[Depends(verify_auth)])
async def export_queries(format: str = Query(default="json", pattern="^(json|csv)$")):
    """Exporta o histórico de consultas persistido no SQLite para download em CSV ou JSON."""
    content = await asyncio.to_thread(telemetry_service.export_queries, format)
    media_type = "text/csv" if format == "csv" else "application/json"
    filename = f"reductor_queries_{int(time.time())}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/v1/logs", dependencies=[Depends(verify_auth)])
async def get_logs(limit: int = Query(default=100, le=500), level: Optional[str] = None):
    """Retorna o histórico de logs recentes do sistema."""
    return {"logs": telemetry_service.get_logs(limit=limit, level_filter=level)}


# ==========================================
# Rotas de Controle de LLM & VRAM do Ollama
# ==========================================
@app.get("/api/v1/llm/status")
async def get_llm_status():
    """Verifica estado do LLM, status do Ollama e modelos na VRAM."""
    return await asyncio.to_thread(llm_manager_service.get_status)


@app.post("/api/v1/llm/toggle", dependencies=[Depends(verify_auth)])
async def toggle_llm(req: LLMToggleDTO):
    """Liga ou desliga o LLM (ativando/desativando o bypass de contexto)."""
    return await asyncio.to_thread(llm_manager_service.toggle_llm_state, req.enabled)


@app.post("/api/v1/llm/config", dependencies=[Depends(verify_auth)])
async def update_llm_config(req: LLMConfigDTO):
    """Atualiza configurações ativas de LLM."""
    return await asyncio.to_thread(
        llm_manager_service.set_config,
        provider=req.provider,
        model=req.model,
        temperature=req.temperature,
        enabled=req.enabled
    )


@app.post("/api/v1/llm/unload", dependencies=[Depends(verify_auth)])
async def unload_llm_vram(req: UnloadVRAMDTO):
    """Descarrega modelo da GPU liberando VRAM no Ollama."""
    return await asyncio.to_thread(llm_manager_service.unload_vram, req.model_name)


@app.get("/api/v1/hardware/budget-advice")
async def get_hardware_budget_advice(provider: Optional[str] = None):
    """Retorna o diagnóstico de hardware (GPU/VRAM/CPU) e orientações de orçamento de tokens."""
    return await asyncio.to_thread(hardware_advisor_service.get_runtime_advice, provider_override=provider)


# ==========================================
# Rotas do Cérebro Episódico (Knowledge Distillation)
# ==========================================
@app.get("/api/v1/brain/episodes")
async def list_brain_episodes(limit: int = 50, filter: Optional[str] = None):
    """Lista conhecimentos e memórias destiladas no Cérebro Coletivo."""
    def _fetch():
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        return use_case.list_knowledge(limit=limit, query_filter=filter)

    episodes = await asyncio.to_thread(_fetch)
    return {"episodes": episodes, "count": len(episodes)}


@app.post("/api/v1/brain/teach", dependencies=[Depends(verify_auth)])
async def teach_brain_endpoint(req: TeachBrainDTO):
    """Ensina diretamente um novo conhecimento ao Cérebro Coletivo."""
    def _teach():
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        return use_case.teach_brain(query=req.query, insight=req.insight, topic=req.topic)

    episode = await asyncio.to_thread(_teach)
    telemetry_service.log("INFO", "Brain", f"Novo conhecimento ensinado ao cérebro: [ID: {episode.id}]")
    return {"message": "Conhecimento gravado com sucesso no cérebro.", "episode": episode.to_dict()}


@app.delete("/api/v1/brain/episodes/{episode_id}", dependencies=[Depends(verify_auth)])
async def delete_brain_episode(episode_id: str):
    """Deleta um episódio específico do cérebro."""
    def _del():
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        return use_case.delete_knowledge(episode_id)

    deleted = await asyncio.to_thread(_del)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memória '{episode_id}' não encontrada.")
    return {"message": f"Memória '{episode_id}' removida com sucesso."}


@app.delete("/api/v1/brain/clear", dependencies=[Depends(verify_auth)])
async def clear_brain_endpoint():
    """Limpa toda a memória episódica do cérebro."""
    def _clear():
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        use_case.clear_brain()

    await asyncio.to_thread(_clear)
    telemetry_service.log("WARNING", "Brain", "Cérebro episódico resetado.")
    return {"message": "Cérebro episódico resetado com sucesso."}


# ==========================================
# Hub MCP (Model Context Protocol) para Agentes
# ==========================================
@app.get("/api/v1/mcp/tools")
async def get_mcp_tools():
    """Lista as ferramentas registradas no Servidor MCP do ReductorPrompt."""
    return {
        "server_name": "reductor-books",
        "protocol_version": "2024-11-05",
        "tools": [
            {
                "name": "search_books",
                "description": "Busca cirurgicamente nos livros técnicos indexados e no cérebro episódico (>95% economia de tokens).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Pergunta ou conceito a pesquisar"},
                        "book_filter": {"type": "string", "description": "Filtro por título de livro específico (opcional)"},
                        "max_tokens": {"type": "integer", "default": 2000, "description": "Limite máximo de tokens do contexto"},
                        "use_local_llm": {"type": "boolean", "default": False, "description": "Se True, sintetiza resposta com LLM"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "teach_brain",
                "description": "Ensina e grava um aprendizado/solução diretamente no Cérebro Coletivo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Pergunta ou problema chave"},
                        "insight": {"type": "string", "description": "Resposta lapidada ou código canônico"},
                        "topic": {"type": "string", "description": "Tópico/Categoria (opcional)"}
                    },
                    "required": ["query", "insight"]
                }
            },
            {
                "name": "consult_brain",
                "description": "Consulta exclusivamente a Memória Episódica do Cérebro Coletivo (<2ms se já resolvida).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Dúvida a pesquisar na memória"},
                        "min_similarity": {"type": "number", "default": 0.85, "description": "Limiar de similaridade"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "validate_reasoning",
                "description": "Validação Cruzada de Raciocínio (Peer Review Cognitivo entre Hipótese do Agente e Livros).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hypothesis_or_plan": {"type": "string", "description": "Hipótese ou plano do agente"},
                        "topic": {"type": "string", "description": "Tópico de foco (opcional)"}
                    },
                    "required": ["hypothesis_or_plan"]
                }
            },
            {
                "name": "analyze_project_with_books",
                "description": "Realiza uma Análise Cruzada entre a arquitetura/código do seu projeto e as melhores práticas dos livros.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_description": {"type": "string", "description": "Descrição da arquitetura ou código do projeto"},
                        "topic": {"type": "string", "description": "Foco específico da análise (opcional)"},
                        "book_filter": {"type": "string", "description": "Nome do livro de referência (opcional)"},
                        "max_tokens": {"type": "integer", "default": 2500, "description": "Limite de tokens de contexto"}
                    },
                    "required": ["project_description"]
                }
            },
            {
                "name": "list_indexed_books",
                "description": "Lista livros técnicos indexados com suporte a filtro por tópico/palavra-chave e paginação enxuta para IA.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_filter": {"type": "string", "description": "Filtro por palavra-chave no título (opcional)"},
                        "limit": {"type": "integer", "default": 30, "description": "Limite máximo de livros retornados"}
                    }
                }
            },
            {
                "name": "get_runtime_budget_advice",
                "description": "Oráculo de Recursos & Telemetria Adaptativa. Inspeciona hardware local (GPU/VRAM) ou cota de API cloud e orienta parâmetros ótimos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "Provedor para simular ('ollama' ou 'gemini')"}
                    }
                }
            }
        ]
    }


@app.post("/api/v1/mcp/call", dependencies=[Depends(verify_auth)])
async def call_mcp_tool(req: MCPCallDTO):
    """Executa diretamente uma ferramenta MCP e retorna o resultado estruturado."""
    telemetry_service.log("INFO", "MCPHub", f"Executando ferramenta MCP: '{req.tool_name}'")
    
    if req.tool_name == "list_indexed_books":
        from src.adapters.inbound.mcp.server import list_indexed_books
        q_filter = req.arguments.get("query_filter")
        limit = int(req.arguments.get("limit", 30))
        result = await asyncio.to_thread(list_indexed_books, query_filter=q_filter, limit=limit)
        return {"tool": req.tool_name, "result": result}
        
    elif req.tool_name == "get_runtime_budget_advice":
        from src.adapters.inbound.mcp.server import get_runtime_budget_advice
        provider = req.arguments.get("provider")
        result = await asyncio.to_thread(get_runtime_budget_advice, provider=provider)
        return {"tool": req.tool_name, "result": result}

    elif req.tool_name == "search_books":
        from src.adapters.inbound.mcp.server import search_books
        query = req.arguments.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Argument 'query' is required.")
        book_filter = req.arguments.get("book_filter")
        max_tokens = int(req.arguments.get("max_tokens", 2000))
        use_llm = bool(req.arguments.get("use_local_llm", False))
        output = await asyncio.to_thread(
            search_books, 
            query=query, 
            book_filter=book_filter, 
            max_tokens=max_tokens,
            use_local_llm=use_llm
        )
        return {"tool": req.tool_name, "result": output}

    elif req.tool_name == "teach_brain":
        from src.adapters.inbound.mcp.server import teach_brain
        query = req.arguments.get("query", "")
        insight = req.arguments.get("insight", "")
        topic = req.arguments.get("topic")
        if not query or not insight:
            raise HTTPException(status_code=400, detail="Arguments 'query' and 'insight' are required.")
        output = await asyncio.to_thread(teach_brain, query=query, insight=insight, topic=topic)
        return {"tool": req.tool_name, "result": output}

    elif req.tool_name == "consult_brain":
        from src.adapters.inbound.mcp.server import consult_brain
        query = req.arguments.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Argument 'query' is required.")
        sim = float(req.arguments.get("min_similarity", 0.85))
        output = await asyncio.to_thread(consult_brain, query=query, min_similarity=sim)
        return {"tool": req.tool_name, "result": output}

    elif req.tool_name == "validate_reasoning":
        from src.adapters.inbound.mcp.server import validate_reasoning
        hypo = req.arguments.get("hypothesis_or_plan", "")
        if not hypo:
            raise HTTPException(status_code=400, detail="Argument 'hypothesis_or_plan' is required.")
        topic = req.arguments.get("topic")
        output = await asyncio.to_thread(validate_reasoning, hypothesis_or_plan=hypo, topic=topic)
        return {"tool": req.tool_name, "result": output}

    elif req.tool_name == "analyze_project_with_books":
        from src.adapters.inbound.mcp.server import analyze_project_with_books
        desc = req.arguments.get("project_description", "")
        if not desc:
            raise HTTPException(status_code=400, detail="Argument 'project_description' is required.")
        topic = req.arguments.get("topic")
        book_filter = req.arguments.get("book_filter")
        max_tokens = int(req.arguments.get("max_tokens", 2500))
        output = await asyncio.to_thread(
            analyze_project_with_books,
            project_description=desc,
            topic=topic,
            book_filter=book_filter,
            max_tokens=max_tokens
        )
        return {"tool": req.tool_name, "result": output}

    else:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found.")


