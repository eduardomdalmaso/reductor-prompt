import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from src.adapters.inbound.api.dependencies import (
    LLMConfigDTO,
    LLMToggleDTO,
    TeachBrainDTO,
    UnloadVRAMDTO,
    verify_auth,
)
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.application.services.hardware_budget_advisor_service import hardware_advisor_service
from src.application.services.llm_manager_service import llm_manager_service
from src.application.services.system_telemetry_service import telemetry_service
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase

router = APIRouter()


@router.get("/api/v1/llm/status")
async def get_llm_status():
    return await asyncio.to_thread(llm_manager_service.get_status)


@router.post("/api/v1/llm/toggle", dependencies=[Depends(verify_auth)])
async def toggle_llm(req: LLMToggleDTO):
    return await asyncio.to_thread(llm_manager_service.toggle_llm_state, req.enabled)


@router.post("/api/v1/llm/config", dependencies=[Depends(verify_auth)])
async def update_llm_config(req: LLMConfigDTO):
    return await asyncio.to_thread(
        llm_manager_service.set_config,
        provider=req.provider,
        model=req.model,
        temperature=req.temperature,
        enabled=req.enabled,
    )


@router.post("/api/v1/llm/unload", dependencies=[Depends(verify_auth)])
async def unload_llm_vram(req: UnloadVRAMDTO):
    return await asyncio.to_thread(llm_manager_service.unload_vram, req.model_name)


@router.get("/api/v1/hardware/budget-advice")
async def get_hardware_budget_advice(provider: Optional[str] = None):
    return await asyncio.to_thread(hardware_advisor_service.get_runtime_advice, provider_override=provider)


@router.get("/api/v1/brain/episodes")
async def list_brain_episodes(limit: int = 50, filter: Optional[str] = None):
    def _fetch():
        uc = ManageBrainUseCase(memory_port=ChromaEpisodicMemoryAdapter(), embedding_port=ResilientEmbeddingAdapter())
        return uc.list_knowledge(limit=limit, query_filter=filter)

    episodes = await asyncio.to_thread(_fetch)
    return {"episodes": episodes, "count": len(episodes)}


@router.post("/api/v1/brain/teach", dependencies=[Depends(verify_auth)])
async def teach_brain_endpoint(req: TeachBrainDTO):
    def _teach():
        uc = ManageBrainUseCase(memory_port=ChromaEpisodicMemoryAdapter(), embedding_port=ResilientEmbeddingAdapter())
        return uc.teach_brain(query=req.query, insight=req.insight, topic=req.topic)

    episode = await asyncio.to_thread(_teach)
    telemetry_service.log("INFO", "Brain", f"Novo conhecimento ensinado ao cérebro: [ID: {episode.id}]")
    return {"message": "Conhecimento gravado com sucesso no cérebro.", "episode": episode.to_dict()}


@router.delete("/api/v1/brain/episodes/{episode_id}", dependencies=[Depends(verify_auth)])
async def delete_brain_episode(episode_id: str):
    def _del():
        uc = ManageBrainUseCase(memory_port=ChromaEpisodicMemoryAdapter(), embedding_port=ResilientEmbeddingAdapter())
        return uc.delete_knowledge(episode_id)

    deleted = await asyncio.to_thread(_del)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memória '{episode_id}' não encontrada.")
    return {"message": f"Memória '{episode_id}' removida com sucesso."}


@router.delete("/api/v1/brain/clear", dependencies=[Depends(verify_auth)])
async def clear_brain_endpoint():
    def _clear():
        uc = ManageBrainUseCase(memory_port=ChromaEpisodicMemoryAdapter(), embedding_port=ResilientEmbeddingAdapter())
        uc.clear_brain()

    await asyncio.to_thread(_clear)
    telemetry_service.log("WARNING", "Brain", "Cérebro episódico resetado.")
    return {"message": "Cérebro episódico resetado com sucesso."}
