import hashlib
import os
from typing import Any, Dict, List, Optional

from src.config.settings import settings
from src.domain.entities.memory import EvidenceStatus, MemoryEpisode, ProvenanceType


def load_consistent_bm25_index(vector_store, cached_idx: Any, logger):
    """Carrega BM25SqliteIndex apenas se estiver sincronizado com o ChromaDB."""
    if cached_idx is not None:
        return cached_idx
    try:
        db_path = os.path.join(settings.STORAGE_DIR, "bm25_fts5.db")
        if os.path.exists(db_path):
            from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
            idx = BM25SqliteIndex(db_path=db_path)
            bm25_cnt = idx.count()
            if bm25_cnt > 0:
                if hasattr(vector_store, "collection"):
                    chroma_cnt = vector_store.collection.count()
                    if chroma_cnt > 0 and bm25_cnt != chroma_cnt:
                        logger.warning(f"BM25 FTS5 dessincronizado ({bm25_cnt} != {chroma_cnt}); usando Dense-only.")
                        return None
                return idx
    except Exception as e:
        logger.warning(f"BM25 FTS5 indisponível (fallback para Dense-only): {e}")
    return None


def build_query_cache_key(
    query: str, book_filter: Optional[str], max_tokens: int, only_ctx: bool,
    deep: bool, enable_rewriting: bool, use_brain: bool, profile: str,
    cache_epoch: int, algo_ver: str, prompt_ver: str,
) -> str:
    active_llm_model = settings.OLLAMA_LLM_MODEL if settings.LLM_PROVIDER.lower() == "ollama" else settings.GEMINI_MODEL
    raw_key = "|".join([
        query.strip().lower(), book_filter or "", str(max_tokens), str(only_ctx),
        str(deep), str(enable_rewriting), str(use_brain), profile,
        settings.LLM_PROVIDER, active_llm_model, settings.EMBEDDING_PROVIDER,
        settings.OLLAMA_EMBED_MODEL, str(settings.DEFAULT_TOP_K),
        str(settings.SIMILARITY_THRESHOLD), str(cache_epoch), algo_ver, prompt_ver,
    ])
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def search_empirical_episodes(query: str, embedding_port, memory_port, logger) -> List[MemoryEpisode]:
    try:
        base_q_vector = embedding_port.embed_text(query)
        return memory_port.search_episodes(
            query_embedding=base_q_vector, min_similarity=0.75, top_k=2,
            provenance=ProvenanceType.EMPIRICAL, status=EvidenceStatus.VALID,
        )
    except Exception as e:
        logger.warning(f"Busca empírica falhou: {e}")
        return []


def persist_auto_learn(query: str, llm_response: str, all_sources: List[Dict[str, Any]], result: Dict[str, Any], embedding_port, memory_port, logger) -> None:
    try:
        episode_id = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        q_vec = embedding_port.embed_text(query)
        memory_port.save_episode(
            MemoryEpisode(
                id=episode_id, query=query.strip(), response=llm_response,
                sources=all_sources, topic="Theoretical Synthesis",
                tokens_used=result["tokens_used"], tokens_saved=result["tokens_saved"],
                reduction_percentage=result["reduction_percentage"],
                provenance=ProvenanceType.THEORETICAL,
            ),
            q_vec,
        )
    except Exception as e:
        logger.warning(f"Falha ao persistir auto-learn: {e}")
