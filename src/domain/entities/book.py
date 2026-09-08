from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional



@dataclass
class BookChunk:
    """Representa um bloco semântico extraído de um livro."""
    id: str
    book_id: str
    book_title: str
    chunk_index: int
    content: str
    token_count: int
    page_number: Optional[int] = None
    chapter: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Book:
    """Entidade que representa um livro registrado no sistema."""
    id: str
    title: str
    file_path: str
    file_name: str
    file_hash: str
    file_format: str  # 'pdf', 'epub', 'txt', 'md'
    total_chunks: int = 0
    total_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredChunk:
    """Chunk recuperado com pontuação de relevância semântica."""
    chunk: BookChunk
    score: float  # Similaridade semântica (0 a 1)


@dataclass
class CompressedContext:
    """Contexto comprimido e otimizado para envio ao LLM."""
    query: str
    chunks: List[ScoredChunk]
    raw_context_text: str
    total_tokens: int
    original_estimated_tokens: int
    token_reduction_percent: float
    sources: List[Dict[str, Any]]


@dataclass
class OptimizationInsight:
    """Estrutura para análise cruzada entre o projeto do usuário e o livro."""
    project_summary: str
    book_title: str
    key_findings: List[str]
    optimization_opportunities: List[str]
    architectural_risks: List[str]
    action_items: List[str]
    references: List[str]
    raw_response: str
    token_stats: Dict[str, Any]
