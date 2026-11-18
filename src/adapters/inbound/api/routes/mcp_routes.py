import asyncio
from fastapi import APIRouter, Depends, HTTPException

from src.adapters.inbound.api.dependencies import MCPCallDTO, verify_auth
from src.application.services.system_telemetry_service import telemetry_service

router = APIRouter()

_MCP_TOOLS_CATALOG = [
    {"name": "search_books", "description": "Busca cirurgicamente nos livros técnicos indexados e no cérebro episódico.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "book_filter": {"type": "string"}, "max_tokens": {"type": "integer", "default": 2000}, "use_local_llm": {"type": "boolean", "default": False}}, "required": ["query"]}},
    {"name": "teach_brain", "description": "Ensina e grava um aprendizado/solução diretamente no Cérebro Coletivo.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "insight": {"type": "string"}, "topic": {"type": "string"}}, "required": ["query", "insight"]}},
    {"name": "consult_brain", "description": "Consulta exclusivamente a Memória Episódica do Cérebro Coletivo.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "min_similarity": {"type": "number", "default": 0.85}}, "required": ["query"]}},
    {"name": "validate_reasoning", "description": "Validação Cruzada de Raciocínio entre Hipótese do Agente e Livros.", "parameters": {"type": "object", "properties": {"hypothesis_or_plan": {"type": "string"}, "topic": {"type": "string"}}, "required": ["hypothesis_or_plan"]}},
    {"name": "analyze_project_with_books", "description": "Realiza Análise Cruzada entre a arquitetura/código do projeto e os livros.", "parameters": {"type": "object", "properties": {"project_description": {"type": "string"}, "topic": {"type": "string"}, "book_filter": {"type": "string"}, "max_tokens": {"type": "integer", "default": 2500}}, "required": ["project_description"]}},
    {"name": "list_indexed_books", "description": "Lista livros técnicos indexados com filtro por palavra-chave e paginação.", "parameters": {"type": "object", "properties": {"query_filter": {"type": "string"}, "limit": {"type": "integer", "default": 30}}}},
    {"name": "get_runtime_budget_advice", "description": "Oráculo de Recursos & Telemetria Adaptativa.", "parameters": {"type": "object", "properties": {"provider": {"type": "string"}}}},
]


@router.get("/api/v1/mcp/tools")
async def get_mcp_tools():
    return {"server_name": "reductor-books", "protocol_version": "2024-11-05", "tools": _MCP_TOOLS_CATALOG}


@router.post("/api/v1/mcp/call", dependencies=[Depends(verify_auth)])
async def call_mcp_tool(req: MCPCallDTO):
    telemetry_service.log("INFO", "MCPHub", f"Executando ferramenta MCP: '{req.tool_name}'")
    from src.adapters.inbound.mcp import server as mcp_srv

    if req.tool_name == "list_indexed_books":
        res = await asyncio.to_thread(mcp_srv.list_indexed_books, query_filter=req.arguments.get("query_filter"), limit=int(req.arguments.get("limit", 30)))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "get_runtime_budget_advice":
        res = await asyncio.to_thread(mcp_srv.get_runtime_budget_advice, provider=req.arguments.get("provider"))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "search_books":
        query = req.arguments.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Argument 'query' is required.")
        res = await asyncio.to_thread(mcp_srv.search_books, query=query, book_filter=req.arguments.get("book_filter"), max_tokens=int(req.arguments.get("max_tokens", 2000)), use_local_llm=bool(req.arguments.get("use_local_llm", False)))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "teach_brain":
        query, insight = req.arguments.get("query", ""), req.arguments.get("insight", "")
        if not query or not insight:
            raise HTTPException(status_code=400, detail="Arguments 'query' and 'insight' are required.")
        res = await asyncio.to_thread(mcp_srv.teach_brain, query=query, insight=insight, topic=req.arguments.get("topic"))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "consult_brain":
        query = req.arguments.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Argument 'query' is required.")
        res = await asyncio.to_thread(mcp_srv.consult_brain, query=query, min_similarity=float(req.arguments.get("min_similarity", 0.85)))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "validate_reasoning":
        hypo = req.arguments.get("hypothesis_or_plan", "")
        if not hypo:
            raise HTTPException(status_code=400, detail="Argument 'hypothesis_or_plan' is required.")
        res = await asyncio.to_thread(mcp_srv.validate_reasoning, hypothesis_or_plan=hypo, topic=req.arguments.get("topic"))
        return {"tool": req.tool_name, "result": res}
    if req.tool_name == "analyze_project_with_books":
        desc = req.arguments.get("project_description", "")
        if not desc:
            raise HTTPException(status_code=400, detail="Argument 'project_description' is required.")
        res = await asyncio.to_thread(mcp_srv.analyze_project_with_books, project_description=desc, topic=req.arguments.get("topic"), book_filter=req.arguments.get("book_filter"), max_tokens=int(req.arguments.get("max_tokens", 2500)))
        return {"tool": req.tool_name, "result": res}
    raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found.")
