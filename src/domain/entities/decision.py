from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DecisionVerdict(str, Enum):
    """Veredicto técnico emitido pelo motor de decisão de engenharia."""
    FAVORABLE = "FAVORABLE"          # Teoria e experimentos empíricos convergem
    CONTROVERSIAL = "CONTROVERSIAL"  # Experimentos empíricos divergem ou impõem trade-offs severos
    INSUFFICIENT = "INSUFFICIENT"    # Evidências empíricas ou teóricas insuficientes para bater o martelo
    REFUTED = "REFUTED"              # A medição prática refutou a hipótese/recomendação teórica


class DecisionReport(BaseModel):
    """Relatório estruturado de decisão de engenharia com rastreabilidade total."""
    decision_id: str = Field(default="", description="Identificador único e determinístico da decisão")
    query: str = Field(..., description="Dúvida ou decisão técnica avaliada")
    recommendation: str = Field(..., description="Recomendação técnica fundamentada")
    verdict: DecisionVerdict = Field(default=DecisionVerdict.FAVORABLE, description="Veredicto formal determinístico")
    policy_version: str = Field(default="1.0", description="Versão da política analítica utilizada")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp ISO da decisão")
    
    # Rastreabilidade de Origem
    theoretical_basis: List[Dict[str, Any]] = Field(default_factory=list, description="Chunks canônicos dos livros")
    empirical_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Benchmarks reais medidos")
    used_episode_ids: List[str] = Field(default_factory=list, description="IDs dos episódios de evidência consultados")
    used_commit_hashes: List[str] = Field(default_factory=list, description="Commits dos experimentos participantes")
    used_source_books: List[str] = Field(default_factory=list, description="Títulos dos livros utilizados como fundamentação")

    # Índices e Diagnósticos Analíticos
    completeness_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Score de completude dos metadados experimentais")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Similaridade semântica da busca")
    staleness_analysis: Dict[str, Any] = Field(default_factory=dict, description="Diagnóstico de obsolescência e compatibilidade")
    comparative_summary: Optional[str] = Field(default=None, description="Resumo comparativo entre múltiplos experimentos")
    limitations: List[str] = Field(default_factory=list, description="Restrições de hardware, carga e runtime")
    next_validation_steps: List[str] = Field(default_factory=list, description="Próximas ações e validações empíricas recomendadas")
