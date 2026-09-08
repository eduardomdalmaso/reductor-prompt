from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TokenBudget:
    """Value Object para controle estrito de limites de tokens."""
    max_context_tokens: int = 1500
    max_response_tokens: int = 2000
    estimated_cost_per_million_input: float = 0.075  # Custo padrão de referência em USD (Gemini 2.5 Flash / Flash-lite)
    
    def calculate_savings(self, original_tokens: int, actual_tokens: int) -> float:
        """Calcula o percentual de tokens economizados."""
        if original_tokens <= 0:
            return 0.0
        saved = max(0, original_tokens - actual_tokens)
        return (saved / original_tokens) * 100.0


@dataclass(frozen=True)
class SourceReference:
    """Value Object representando uma citação rastreável de um livro."""
    book_title: str
    chunk_index: int
    score: float
    page: Optional[int] = None
    chapter: Optional[str] = None
    snippet: str = ""
