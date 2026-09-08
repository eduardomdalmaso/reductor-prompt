from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.domain.entities.book import Book, CompressedContext, OptimizationInsight


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
