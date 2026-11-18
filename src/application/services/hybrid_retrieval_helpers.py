import re
from typing import List, Optional, Tuple
from src.domain.entities.book import ScoredChunk


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


def fuse_hybrid_dense_bm25(
    dense: List[ScoredChunk],
    bm25: List[ScoredChunk],
    w_dense: float = 0.4,
    w_bm25: float = 0.6,
) -> List[ScoredChunk]:
    """Fusão calibrada Dense + BM25 com deduplicação por chunk_id."""
    scores = {}
    chunks = {}
    if dense:
        max_d = max(sc.score for sc in dense) or 1.0
        for rank, sc in enumerate(dense, 1):
            cid = sc.chunk.id
            chunks[cid] = sc
            scores[cid] = scores.get(cid, 0.0) + w_dense * ((sc.score / max_d) * 0.5 + 0.5 / rank)
    if bm25:
        for rank, sc in enumerate(bm25, 1):
            cid = sc.chunk.id
            if cid not in chunks:
                chunks[cid] = sc
            scores[cid] = scores.get(cid, 0.0) + w_bm25 * (1.0 / rank)
    merged = [ScoredChunk(chunk=chunks[cid].chunk, score=s) for cid, s in scores.items()]
    return sorted(merged, key=lambda x: x.score, reverse=True)


def retrieve_hybrid_candidates(
    query: str,
    variations: List[str],
    effective_filter: Optional[str],
    embedding_port,
    vector_store,
    compressor,
    bm25,
    default_top_k: int,
    logger,
) -> List[ScoredChunk]:
    """Executa recuperação híbrida (Dense + BM25) ou fallback RRF legado."""
    if bm25 is not None:
        q_vec = embedding_port.embed_text(query)
        dense_hits = vector_store.search(query_embedding=q_vec, top_k=16, book_title_filter=effective_filter)
        try:
            bm25_hits = bm25.search(query=query, top_k=16, book_title_filter=effective_filter)
        except Exception as e:
            logger.warning(f"Busca BM25 falhou (usando Dense): {e}")
            bm25_hits = []
        scored_chunks = fuse_hybrid_dense_bm25(dense_hits, bm25_hits, w_dense=0.4, w_bm25=0.6)
        if hasattr(vector_store, "search_by_identifier"):
            extra_ids = {sc.chunk.id for sc in scored_chunks}
            for ident in extract_technical_identifiers(query)[:2]:
                for lh in vector_store.search_by_identifier(ident, top_k=4, book_title_filter=effective_filter):
                    if lh.chunk.id not in extra_ids:
                        scored_chunks.append(lh)
                        extra_ids.add(lh.chunk.id)
        return apply_lexical_identifier_boost(query, scored_chunks)

    top_k = max(16, default_top_k * 2)
    batch_results: List[List] = []
    if len(variations) > 1 and hasattr(embedding_port, "embed_batch"):
        q_vecs = embedding_port.embed_batch(variations)
    else:
        q_vecs = [embedding_port.embed_text(q_var) for q_var in variations]
    for q_vec in q_vecs:
        scored = vector_store.search(query_embedding=q_vec, top_k=top_k, book_title_filter=effective_filter)
        if scored:
            batch_results.append(scored)

    if hasattr(vector_store, "search_by_identifier"):
        for ident in extract_technical_identifiers(query)[:2]:
            lex_hits = vector_store.search_by_identifier(
                identifier=ident, top_k=4, book_title_filter=effective_filter
            )
            if lex_hits:
                batch_results.append(lex_hits)

    scored_chunks = compressor.fuse_chunks_rrf(batch_results) if batch_results else []
    return apply_lexical_identifier_boost(query, scored_chunks)
