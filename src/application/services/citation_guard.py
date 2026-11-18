import re
from typing import Any, Dict, List, Tuple


def verify_citation_grounding(response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verifica se páginas citadas na resposta existem nas fontes recuperadas."""
    if not response or not sources:
        return {"grounded_pages": 0, "cited_pages": 0, "ungrounded_pages": [], "grounding_ratio": 1.0}

    retrieved_pages = {s.get("page") for s in sources if s.get("page") is not None}
    cited_pages = [int(p) for p in re.findall(r"(?:P[áa]g\.?|Page|p\.)\s*(\d+)", response, flags=re.IGNORECASE)]
    if not cited_pages:
        return {"grounded_pages": 0, "cited_pages": 0, "ungrounded_pages": [], "grounding_ratio": 1.0}

    grounded = [p for p in cited_pages if p in retrieved_pages]
    ungrounded = [p for p in cited_pages if p not in retrieved_pages]
    return {
        "grounded_pages": len(grounded),
        "cited_pages": len(cited_pages),
        "ungrounded_pages": sorted(set(ungrounded)),
        "grounding_ratio": round(len(grounded) / len(cited_pages), 4),
    }


def validate_and_sanitize_urls(response: str, context_text: str) -> Tuple[str, List[str]]:
    """Remove URLs fabricadas que não constam literalmente no contexto recuperado."""
    if not response:
        return response, []

    ctx_lower = (context_text or "").lower()
    found_urls = re.findall(r"https?://[^\s\)\]>\"']+", response)
    fabricated: List[str] = []
    sanitized = response
    for raw_url in dict.fromkeys(found_urls):
        clean_url = raw_url.rstrip(".,;:")
        if clean_url.lower() not in ctx_lower:
            fabricated.append(clean_url)
            sanitized = re.sub(
                r"\[([^\]]+)\]\(" + re.escape(clean_url) + r"[^\)]*\)",
                r"\1",
                sanitized,
            )
            sanitized = sanitized.replace(clean_url, "[link removido: não consta nas fontes]")
    return sanitized, fabricated
