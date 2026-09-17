from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MemoryEpisode:
    """Entidade que representa uma memória episódica ou aprendizado indexado no Cérebro."""
    id: str
    query: str
    response: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    topic: Optional[str] = None
    tokens_used: int = 0
    tokens_saved: int = 0
    reduction_percentage: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence_score: float = 1.0
    hit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "response": self.response,
            "sources": self.sources,
            "topic": self.topic,
            "tokens_used": self.tokens_used,
            "tokens_saved": self.tokens_saved,
            "reduction_percentage": self.reduction_percentage,
            "created_at": self.created_at,
            "confidence_score": self.confidence_score,
            "hit_count": self.hit_count
        }
