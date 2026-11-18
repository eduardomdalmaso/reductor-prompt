import re
from typing import List, Optional
from src.config.settings import settings
from src.domain.entities.book import ScoredChunk


def classify_query_complexity(query: str) -> str:
    """Classifica a complexidade da consulta em 'factual', 'conceptual' ou 'architectural'."""
    q = query.lower().strip()
    word_count = len(q.split())

    arch_patterns = [
        r"\banalys[e|is]\b", r"\barquitetura\b", r"\bcompar[e|ar|ando]\b", r"\btrade-?offs?\b",
        r"\bbenchmark\b", r"\bscalab\w+\b", r"\bescalabil\w+\b", r"\bmigra\w+\b",
        r"\bdistribu\w+\b", r"\bconcorr\w+\b", r"\bdiagn[oó]stico\b", r"\bpipeline\b",
    ]
    if any(re.search(pat, q) for pat in arch_patterns):
        return "architectural"

    conceptual_patterns = [
        r"^como funciona\b", r"^como implementar\b", r"^como usar\b", r"^por que\b",
        r"^explique\b", r"^tutorial\b", r"^descreva\b", r"\bmecanismo\b", r"\balgoritmo\b",
    ]
    if any(re.search(pat, q) for pat in conceptual_patterns):
        return "conceptual"

    factual_patterns = [
        r"^o que [eé]\b", r"^qual [eé]\b", r"^quais s[aã]o\b", r"\bcomando\b", r"\bsintaxe\b",
        r"\bflag\b", r"\bdefina\b", r"\bsignificado\b", r"\bvers[aã]o\b", r"\batalho\b",
    ]
    if any(re.search(pat, q) for pat in factual_patterns) or word_count <= 3:
        return "factual"

    return "conceptual"


def determine_dynamic_budget(query: str, max_tokens_override: Optional[int] = None) -> int:
    """Calcula o orçamento dinâmico de tokens conforme complexidade da query."""
    if max_tokens_override is not None and max_tokens_override != settings.DEFAULT_MAX_CONTEXT_TOKENS:
        return max_tokens_override

    if not getattr(settings, "DYNAMIC_TOKEN_BUDGET_ENABLED", True):
        return max_tokens_override or settings.DEFAULT_MAX_CONTEXT_TOKENS

    complexity = classify_query_complexity(query)
    if complexity == "factual":
        return getattr(settings, "DYNAMIC_MIN_FACTUAL_TOKENS", 800)
    if complexity == "architectural":
        return getattr(settings, "DYNAMIC_MAX_ARCHITECTURAL_TOKENS", 4000)
    return getattr(settings, "DYNAMIC_MAX_CONCEPTUAL_TOKENS", 1800)


def apply_elbow_cutoff(
    sorted_chunks: List[ScoredChunk],
    min_score: float,
    max_relative_drop: float = None,
    max_step_drop: float = None,
) -> List[ScoredChunk]:
    """Aplica o método Elbow para descartar a cauda de ruído preservando evidências principais."""
    if not sorted_chunks:
        return []

    rel_drop_threshold = (
        max_relative_drop
        if max_relative_drop is not None
        else getattr(settings, "DYNAMIC_ELBOW_MAX_RELATIVE_DROP", 0.35)
    )
    step_drop_threshold = (
        max_step_drop
        if max_step_drop is not None
        else getattr(settings, "DYNAMIC_ELBOW_MAX_STEP_DROP", 0.22)
    )

    top_score = sorted_chunks[0].score
    if top_score < min_score:
        return [sorted_chunks[0]]

    selected: List[ScoredChunk] = []
    prev_score = top_score

    for sc in sorted_chunks:
        if sc.score < min_score:
            break
        relative_drop = (top_score - sc.score) / max(0.01, top_score)
        if relative_drop > rel_drop_threshold and len(selected) >= 1:
            break
        if (prev_score - sc.score) > step_drop_threshold and len(selected) >= 1:
            break
        selected.append(sc)
        prev_score = sc.score

    return selected or [sorted_chunks[0]]


def fuse_chunks_rrf(chunk_batches: List[List[ScoredChunk]], rrf_k: int = 60) -> List[ScoredChunk]:
    """Funde múltiplos conjuntos de busca vetorial usando Reciprocal Rank Fusion (RRF)."""
    rrf_scores = {}
    chunk_map = {}
    for batch in chunk_batches:
        for rank, sc in enumerate(batch, 1):
            cid = sc.chunk.id
            chunk_map[cid] = sc
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
    if not rrf_scores:
        return []
    max_rrf = max(rrf_scores.values())
    return [
        ScoredChunk(chunk=chunk_map[cid].chunk, score=min(1.0, max(chunk_map[cid].score, total / max_rrf)))
        for cid, total in sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
    ]
