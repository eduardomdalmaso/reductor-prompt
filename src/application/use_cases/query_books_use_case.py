import logging
import hashlib
import re
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from datetime import datetime, timezone

from src.domain.ports.inbound import IQueryBooksUseCase
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort, IEpisodicMemoryPort
from src.domain.entities.book import ScoredChunk
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.application.services.query_rewriter_service import QueryRewriterService
from src.config.settings import settings

logger = logging.getLogger(__name__)

_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX_SIZE = 128
_CACHE_EPOCH = 1
RETRIEVAL_ALGO_VERSION = "rrf-elbow-v3-grounded"
PROMPT_TEMPLATE_VERSION = "qa-v2"


def _norm_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def resolve_book_filter(
    query: str,
    explicit_filter: Optional[str],
    available_titles: List[str],
) -> Tuple[Optional[str], List[str]]:
    """Resolve filtro de livro por normalização tolerante ou detecção na pergunta."""
    if not available_titles:
        return explicit_filter, []

    unique_titles = sorted(set(available_titles))
    norm_map = {_norm_title(t): t for t in unique_titles if _norm_title(t)}

    if explicit_filter:
        norm_exp = _norm_title(explicit_filter)
        if norm_exp in norm_map:
            return norm_map[norm_exp], []
        matches = [t for nt, t in norm_map.items() if norm_exp and (norm_exp in nt or nt in norm_exp)]
        if len(matches) == 1:
            return matches[0], []
        if len(matches) > 1:
            return None, matches
        return explicit_filter, []

    norm_q = _norm_title(query)
    if not norm_q:
        return None, []

    detected = [t for nt, t in norm_map.items() if len(nt) >= 12 and nt in norm_q]
    # Remove títulos que são apenas substring de outro título mais específico já detectado
    filtered = [
        t for t in detected
        if not any(t != other and _norm_title(t) in _norm_title(other) for other in detected)
    ]
    if len(filtered) == 1:
        return filtered[0], []
    if len(filtered) > 1:
        return None, filtered
    return None, []


def extract_technical_identifiers(query: str) -> List[str]:
    """Extrai identificadores técnicos (CamelCase / snake_case) da query."""
    camel_ids = re.findall(r"\b[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b", query)
    snake_ids = re.findall(r"\b[a-z]+_[a-z0-9_]+\b", query)
    return list(dict.fromkeys(camel_ids + snake_ids))


def apply_lexical_identifier_boost(
    query: str,
    chunks: List[ScoredChunk],
    boost_per_match: float = 0.15,
) -> List[ScoredChunk]:
    """Reforça chunks que contêm identificadores técnicos ou termos compostos exatos da query."""
    identifiers = extract_technical_identifiers(query)
    phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", query)
    terms = list(dict.fromkeys(identifiers + phrases))
    if not terms or not chunks:
        return chunks

    boosted = []
    for sc in chunks:
        hits = sum(1 for t in terms if t in sc.chunk.content)
        new_score = sc.score + (hits * boost_per_match) if hits else sc.score
        boosted.append(ScoredChunk(chunk=sc.chunk, score=new_score))
    return sorted(boosted, key=lambda x: x.score, reverse=True)


def invalidate_query_cache() -> int:
    """Limpa o cache de consultas e incrementa a época de corpus."""
    global _CACHE_EPOCH
    _QUERY_CACHE.clear()
    _CACHE_EPOCH += 1
    return _CACHE_EPOCH


class QueryBooksUseCase(IQueryBooksUseCase):
    """Caso de uso de RAG Cognitivo Bilateral (Teoria dos Livros + Evidências Empíricas)."""

    def __init__(
        self,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        llm_port: ILLMPort,
        memory_port: Optional[IEpisodicMemoryPort] = None,
        compressor_service: Optional[PromptCompressorService] = None,
        rewriter_service: Optional[QueryRewriterService] = None
    ):
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.llm_port = llm_port
        self.memory_port = memory_port
        self.compressor = compressor_service or PromptCompressorService()
        self.rewriter = rewriter_service or QueryRewriterService()

    def _get_cache_key(
        self,
        query: str,
        book_filter: Optional[str],
        max_tokens: int,
        only_ctx: bool,
        deep: bool,
        enable_rewriting: bool,
        use_brain: bool
    ) -> str:
        active_llm_model = (
            settings.OLLAMA_LLM_MODEL
            if settings.LLM_PROVIDER.lower() == "ollama"
            else settings.GEMINI_MODEL
        )
        raw_key = "|".join([
            query.strip().lower(),
            book_filter or "",
            str(max_tokens),
            str(only_ctx),
            str(deep),
            str(enable_rewriting),
            str(use_brain),
            settings.LLM_PROVIDER,
            active_llm_model,
            settings.EMBEDDING_PROVIDER,
            settings.OLLAMA_EMBED_MODEL,
            str(settings.DEFAULT_TOP_K),
            str(settings.SIMILARITY_THRESHOLD),
            str(_CACHE_EPOCH),
            RETRIEVAL_ALGO_VERSION,
            PROMPT_TEMPLATE_VERSION,
        ])
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    def execute(
        self,
        query: str,
        book_filter: Optional[str] = None,
        max_tokens: int = 2500,
        only_context: bool = False,
        deep_reasoning: bool = False,
        enable_rewriting: bool = True,
        use_brain: bool = True,
        auto_learn: bool = True
    ) -> Dict[str, Any]:
        cache_key = self._get_cache_key(
            query, book_filter, max_tokens, only_context, deep_reasoning, enable_rewriting, use_brain
        )

        if cache_key in _QUERY_CACHE:
            _QUERY_CACHE.move_to_end(cache_key)
            return {**_QUERY_CACHE[cache_key], "cache_hit": True}

        # 0. Resolução tolerante e detecção automática de filtro de livro
        available_titles: List[str] = []
        try:
            available_titles = [b.get("title", "") for b in self.vector_store.list_indexed_books() if b.get("title")]
        except Exception:
            pass
        resolved_filter, ambiguous_titles = resolve_book_filter(query, book_filter, available_titles)
        if ambiguous_titles:
            opts = ", ".join(ambiguous_titles[:5])
            return {
                "query": query,
                "response": f"Título ambíguo detectado. Especifique qual livro deseja consultar: {opts}.",
                "sources": [],
                "tokens_used": 0,
                "tokens_saved": 0,
                "reduction_percentage": 0.0,
                "context_text": "",
                "query_variations": [query],
                "from_brain": False,
                "cache_hit": False,
                "ambiguous_books": ambiguous_titles,
            }
        effective_filter = resolved_filter

        # 1. Expansão de Query
        variations = self.rewriter.expand_query(query, max_variations=3) if enable_rewriting else [query]

        # 2. Busca de Evidências Empíricas no Cérebro (HydraStream)
        empirical_episodes: List[MemoryEpisode] = []
        if use_brain and self.memory_port and not book_filter:
            try:
                base_q_vector = self.embedding_port.embed_text(query)
                empirical_episodes = self.memory_port.search_episodes(
                    query_embedding=base_q_vector,
                    min_similarity=0.75,
                    top_k=2,
                    provenance=ProvenanceType.EMPIRICAL,
                    status=EvidenceStatus.VALID
                )
            except Exception as e:
                logger.warning(f"Busca empírica falhou: {e}")

        # 3. Busca Vetorial nos Livros (batch embedding) + Fallback Lexical para Identificadores
        top_k = max(16, settings.DEFAULT_TOP_K * 2)
        batch_results: List[List] = []
        if len(variations) > 1 and hasattr(self.embedding_port, "embed_batch"):
            q_vecs = self.embedding_port.embed_batch(variations)
        else:
            q_vecs = [self.embedding_port.embed_text(q_var) for q_var in variations]
        for q_vec in q_vecs:
            scored = self.vector_store.search(query_embedding=q_vec, top_k=top_k, book_title_filter=effective_filter)
            if scored:
                batch_results.append(scored)

        if hasattr(self.vector_store, "search_by_identifier"):
            for ident in extract_technical_identifiers(query)[:2]:
                lex_hits = self.vector_store.search_by_identifier(
                    identifier=ident, top_k=4, book_title_filter=effective_filter
                )
                if lex_hits:
                    batch_results.append(lex_hits)

        scored_chunks = self.compressor.fuse_chunks_rrf(batch_results) if batch_results else []
        scored_chunks = apply_lexical_identifier_boost(query, scored_chunks)

        if not scored_chunks and not empirical_episodes:
            return {
                "query": query, "response": "Nenhum conteúdo técnico relevante foi localizado.",
                "sources": [], "tokens_used": 0, "tokens_saved": 0, "reduction_percentage": 0.0,
                "context_text": "", "query_variations": variations, "from_brain": False
            }

        # 4. Formata contexto teórico e empírico bilateral
        compressed_ctx = self.compressor.compress_and_format(query=query, scored_chunks=scored_chunks, max_tokens=max_tokens)
        empirical_text = self.compressor.format_empirical_evidence(empirical_episodes)

        all_sources = list(compressed_ctx.sources)
        for ep in empirical_episodes:
            hw = ep.environment_context.get("hardware") or ep.environment_context.get("gpu") or "N/A"
            commit = f"#{ep.commit_hash[:7]}" if ep.commit_hash else "N/A"
            all_sources.append({
                "book_title": f"Empirical: {ep.project_source or 'HydraStream'}",
                "chapter": f"Exp: {ep.experiment_id or ep.id} ({commit} | {hw})",
                "score": ep.confidence_score,
                "provenance": "empirical"
            })

        full_context_text = compressed_ctx.raw_context_text
        if empirical_text:
            full_context_text = f"{full_context_text}\n\n{empirical_text}"

        # 5. Entrega de Contexto Direto (Bypass)
        if only_context:
            result = {
                "query": query,
                "response": full_context_text,
                "sources": all_sources,
                "tokens_used": compressed_ctx.total_tokens + len(empirical_text.split()),
                "tokens_saved": max(0, compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens),
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text,
                "query_variations": variations,
                "from_brain": bool(empirical_episodes),
                "cache_hit": False
            }
        else:
            # 6. Síntese Bilateral com LLM
            sys_inst, user_prompt = self.compressor.build_qa_prompt(
                query=query, compressed_context=compressed_ctx,
                deep_reasoning=deep_reasoning, empirical_context=empirical_text
            )
            llm_response = self.llm_port.generate_response(system_instruction=sys_inst, prompt=user_prompt)
            grounding = self.compressor.verify_citation_grounding(llm_response, all_sources)

            result = {
                "query": query,
                "response": llm_response,
                "sources": all_sources,
                "tokens_used": compressed_ctx.total_tokens + len(empirical_text.split()),
                "tokens_saved": max(0, compressed_ctx.original_estimated_tokens - compressed_ctx.total_tokens),
                "reduction_percentage": compressed_ctx.token_reduction_percent,
                "context_text": full_context_text,
                "query_variations": variations,
                "from_brain": bool(empirical_episodes),
                "cache_hit": False,
                "citation_grounding": grounding,
            }

            if auto_learn and self.memory_port and not book_filter:
                try:
                    episode_id = hashlib.sha256(query.strip().lower().encode('utf-8')).hexdigest()[:16]
                    q_vec = self.embedding_port.embed_text(query)
                    self.memory_port.save_episode(
                        MemoryEpisode(
                            id=episode_id, query=query.strip(), response=llm_response,
                            sources=all_sources, topic="Theoretical Synthesis",
                            tokens_used=result["tokens_used"], tokens_saved=result["tokens_saved"],
                            reduction_percentage=result["reduction_percentage"],
                            provenance=ProvenanceType.THEORETICAL
                        ),
                        q_vec
                    )
                except Exception as e:
                    logger.warning(f"Falha ao persistir auto-learn: {e}")

        if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)
        _QUERY_CACHE[cache_key] = result
        return result
