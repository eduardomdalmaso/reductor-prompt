from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from src.domain.entities.book import Book, OptimizationInsight
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.entities.decision import DecisionReport, DecisionVerdict


@dataclass
class IngestEvidenceCommand:
    """Comando de entrada para ingestão de evidências empíricas ou decisões técnicas."""
    query: str
    response: str
    project_source: str
    experiment_id: str
    commit_hash: str
    provenance: ProvenanceType = ProvenanceType.EMPIRICAL
    status: EvidenceStatus = EvidenceStatus.VALID
    measured_at: Optional[str] = None
    environment_context: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    topic: Optional[str] = None
    source_hashes: List[str] = field(default_factory=list)


class IIngestBooksUseCase(ABC):
    """Porta de entrada para ingestão de livros da pasta database."""
    
    @abstractmethod
    def execute(self, force_reindex: bool = False) -> List[Book]:
        """Processa novos livros e retorna os livros indexados."""
        pass


class IQueryBooksUseCase(ABC):
    """Porta de entrada para consultas com contexto reduzido."""
    
    @abstractmethod
    def execute(
        self, 
        query: str, 
        book_filter: Optional[str] = None, 
        max_tokens: int = 1500,
        only_context: bool = False
    ) -> Dict[str, Any]:
        """Executa a busca, enxuga o contexto e opcionalmente gera a resposta via LLM."""
        pass


class IAnalyzeProjectUseCase(ABC):
    """Porta de entrada para análise cruzada (Projeto vs. Conhecimento dos Livros)."""
    
    @abstractmethod
    def execute(
        self, 
        project_description: str, 
        book_filter: Optional[str] = None,
        focus_topic: Optional[str] = None,
        max_tokens: int = 2000
    ) -> OptimizationInsight:
        """Cruza o cenário do projeto com os conceitos do livro e extrai melhorias."""
        pass


class IIngestEvidenceUseCase(ABC):
    """Porta de entrada para ingestão de evidências empíricas e benchmarks operacionais."""
    
    @abstractmethod
    def execute(self, command: IngestEvidenceCommand) -> Tuple[MemoryEpisode, bool]:
        """
        Valida, deduplica idempotentemente e persiste a evidência.
        Retorna (MemoryEpisode, is_created: bool).
        """
        pass


@dataclass
class MakeDecisionCommand:
    """Comando para requisição de decisão técnica fundamentada."""
    query: str
    target_hardware: Optional[str] = None
    target_commit: Optional[str] = None
    book_filter: Optional[str] = None
    max_tokens: int = 2500
    llm_synthesis: bool = True


class IMakeDecisionUseCase(ABC):
    """Porta de entrada para orquestração de decisões de engenharia fundamentadas."""

    @abstractmethod
    def execute(self, command: MakeDecisionCommand) -> DecisionReport:
        """
        Orquestra recuperação bilateral, avaliação de completude, detecção de
        obsolescência e política determinística, emitindo o DecisionReport.
        """
        pass
