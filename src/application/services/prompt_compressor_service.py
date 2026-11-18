from typing import List, Dict, Any, Tuple, Optional
from src.domain.entities.book import ScoredChunk, CompressedContext
from src.application.services.chunking_service import ChunkingService
from src.application.services.citation_guard import (
    validate_and_sanitize_urls as _validate_and_sanitize_urls,
    verify_citation_grounding as _verify_citation_grounding,
)
from src.application.services.elbow_budget_service import (
    apply_elbow_cutoff as _apply_elbow_cutoff,
    classify_query_complexity as _classify_query_complexity,
    determine_dynamic_budget as _determine_dynamic_budget,
    fuse_chunks_rrf as _fuse_chunks_rrf,
)
from src.application.services.prompt_templates import (
    build_cross_analysis_prompt as _build_cross_analysis_prompt,
    build_qa_prompt as _build_qa_prompt,
    format_empirical_evidence as _format_empirical_evidence,
)
from src.config.settings import settings


class PromptCompressorService:
    """Serviço responsável por comprimir, filtrar e formatar o contexto com orçamento dinâmico."""

    def __init__(self, chunking_service: ChunkingService = None):
        self.chunking_service = chunking_service or ChunkingService()

    def classify_query_complexity(self, query: str) -> str:
        return _classify_query_complexity(query)

    def determine_dynamic_budget(self, query: str, max_tokens_override: Optional[int] = None) -> int:
        return _determine_dynamic_budget(query, max_tokens_override)

    def apply_elbow_cutoff(
        self,
        sorted_chunks: List[ScoredChunk],
        min_score: float,
        max_relative_drop: float = None,
        max_step_drop: float = None,
    ) -> List[ScoredChunk]:
        return _apply_elbow_cutoff(sorted_chunks, min_score, max_relative_drop, max_step_drop)

    _STRATEGY_PARAMS = {
        "conservative": (0.55, 0.35),
        "balanced": (0.45, 0.30),
        "aggressive": (0.35, 0.22),
    }

    def compress_and_format(
        self,
        query: str,
        scored_chunks: List[ScoredChunk],
        max_tokens: int = None,
        similarity_threshold: float = None,
        strategy: str = "balanced",
        max_cut_percent: Optional[float] = None
    ) -> CompressedContext:
        """Comprime e formata o contexto com orçamento adaptativo e estratégia configurável."""
        limit_tokens = self.determine_dynamic_budget(query, max_tokens)
        min_score = similarity_threshold or settings.SIMILARITY_THRESHOLD

        # 1. Ordena decrescente por score de relevância
        sorted_chunks = sorted(scored_chunks, key=lambda x: x.score, reverse=True)
        raw_retrieved_tokens = sum(
            sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)
            for sc in sorted_chunks
        )

        # 2. Aplica corte dinâmico por curva de relevância conforme estratégia
        rel_drop, step_drop = self._STRATEGY_PARAMS.get(strategy, self._STRATEGY_PARAMS["balanced"])
        if strategy == "aggressive" and max_cut_percent is None:
            relevant_chunks = self.apply_elbow_cutoff(sorted_chunks, min_score)
        else:
            relevant_chunks = self.apply_elbow_cutoff(
                sorted_chunks, min_score, max_relative_drop=rel_drop, max_step_drop=step_drop
            )

        # No modo conservative com limite explícito, garante que o corte não ultrapasse max_cut_percent
        if strategy == "conservative" and max_cut_percent is not None and sorted_chunks:
            min_keep_tokens = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
            kept_ids = {sc.chunk.id for sc in relevant_chunks}
            kept_raw = sum(
                sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)
                for sc in relevant_chunks
            )
            for sc in sorted_chunks:
                if kept_raw >= min_keep_tokens:
                    break
                if sc.chunk.id not in kept_ids:
                    relevant_chunks.append(sc)
                    kept_ids.add(sc.chunk.id)
                    kept_raw += sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)

        selected_chunks: List[ScoredChunk] = []
        current_tokens = 0
        selected_raw_tokens = 0
        sources_list: List[Dict[str, Any]] = []
        formatted_blocks: List[str] = []

        for sc in relevant_chunks:
            chunk = sc.chunk
            chunk_raw_tokens = chunk.token_count if chunk.token_count > 0 else self.chunking_service.count_tokens(chunk.content)

            # Formata o bloco de forma limpa e contextualizada
            loc_info = []
            if chunk.chapter:
                loc_info.append(chunk.chapter)
            if chunk.page_number and chunk.page_number > 0:
                loc_info.append(f"Pág {chunk.page_number}")
            loc_str = f" ({', '.join(loc_info)})" if loc_info else ""

            block_text = f"--- [Livro: {chunk.book_title}{loc_str} | Relevância: {sc.score:.2f}] ---\n{chunk.content.strip()}"
            block_tokens = self.chunking_service.count_tokens(block_text)

            if strategy == "conservative" and max_cut_percent is not None:
                min_keep_tokens = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
                if selected_chunks and selected_raw_tokens >= min_keep_tokens and current_tokens + block_tokens > limit_tokens:
                    break
            elif max_cut_percent is not None:
                target_keep = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
                if selected_chunks and (selected_raw_tokens + chunk_raw_tokens > target_keep or current_tokens + block_tokens > limit_tokens):
                    break
            elif current_tokens + block_tokens > limit_tokens and selected_chunks:
                # Protege a única evidência de um livro distinto antes de truncar no modo balanced
                seen_books = {s.chunk.book_title for s in selected_chunks}
                if strategy != "aggressive" and chunk.book_title not in seen_books:
                    pass
                else:
                    break

            selected_chunks.append(sc)
            current_tokens += block_tokens
            selected_raw_tokens += chunk_raw_tokens
            formatted_blocks.append(block_text)

            sources_list.append({
                "chunk_id": chunk.id,
                "book_id": chunk.book_id,
                "book_title": chunk.book_title,
                "chapter": chunk.chapter,
                "page": chunk.page_number,
                "page_start": chunk.page_number,
                "page_end": chunk.page_number,
                "char_start": 0,
                "char_end": len(chunk.content),
                "excerpt_preview": chunk.content.strip()[:200],
                "score": round(sc.score, 3),
                "tokens": chunk.token_count
            })

        final_context_str = "\n\n".join(formatted_blocks)
        total_compressed_tokens = self.chunking_service.count_tokens(final_context_str)

        saved_tokens = max(0, raw_retrieved_tokens - selected_raw_tokens)
        reduction_percentage = round((saved_tokens / raw_retrieved_tokens) * 100, 2) if raw_retrieved_tokens > 0 else 0.0

        return CompressedContext(
            query=query,
            chunks=selected_chunks,
            raw_context_text=final_context_str,
            total_tokens=total_compressed_tokens,
            original_estimated_tokens=raw_retrieved_tokens,
            token_reduction_percent=reduction_percentage,
            sources=sources_list
        )

    @staticmethod
    def verify_citation_grounding(response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        return _verify_citation_grounding(response, sources)

    @staticmethod
    def validate_and_sanitize_urls(response: str, context_text: str) -> Tuple[str, List[str]]:
        return _validate_and_sanitize_urls(response, context_text)

    @staticmethod
    def fuse_chunks_rrf(chunk_batches: List[List[ScoredChunk]], rrf_k: int = 60) -> List[ScoredChunk]:
        return _fuse_chunks_rrf(chunk_batches, rrf_k)

    def format_empirical_evidence(self, episodes: List[Any]) -> str:
        return _format_empirical_evidence(episodes)

    def build_qa_prompt(
        self,
        query: str,
        compressed_context: CompressedContext,
        deep_reasoning: bool = False,
        empirical_context: Optional[str] = None,
    ) -> Tuple[str, str]:
        return _build_qa_prompt(query, compressed_context, deep_reasoning, empirical_context)

    def build_cross_analysis_prompt(
        self,
        project_description: str,
        compressed_context: CompressedContext,
        focus_topic: str = None,
    ) -> Tuple[str, str]:
        return _build_cross_analysis_prompt(project_description, compressed_context, focus_topic)
