from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.domain.entities.book import Book, BookChunk, ScoredChunk


class IDocumentLoaderPort(ABC):
    """Porta para carregar e extrair texto de diferentes formatos de livros."""
    
    @abstractmethod
    def can_load(self, file_path: str) -> bool:
        """Verifica se o loader suporta a extensão do arquivo."""
        pass
    
    @abstractmethod
    def load(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extrai o conteúdo do arquivo.
        Retorna uma lista de blocos brutos com metadados (texto, página/seção).
        """
        pass


class IEmbeddingPort(ABC):
    """Porta para geração de vetores de embedding."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um único texto."""
        pass
        
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings em lote para otimizar velocidade."""
        pass


class IVectorStorePort(ABC):
    """Porta para armazenamento e recuperação vetorial."""
    
    @abstractmethod
    def upsert_chunks(self, book: Book, chunks: List[BookChunk], embeddings: List[List[float]]) -> None:
        """Salva ou atualiza chunks com seus respectivos vetores."""
        pass
        
    @abstractmethod
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 4, 
        book_title_filter: Optional[str] = None
    ) -> List[ScoredChunk]:
        """Realiza busca semântica por proximidade vetorial."""
        pass

    @abstractmethod
    def delete_book(self, book_id: str) -> None:
        """Remove todos os chunks associados a um livro."""
        pass

    @abstractmethod
    def list_indexed_books(self) -> List[Dict[str, Any]]:
        """Lista todos os livros atualmente indexados no banco vetorial."""
        pass


class ILLMPort(ABC):
    """Porta para comunicação com o LLM (Gemini / Ollama)."""
    
    @abstractmethod
    def generate_response(
        self, 
        system_instruction: str, 
        prompt: str, 
        temperature: float = 0.2
    ) -> str:
        """Gera uma resposta baseada no prompt enxuto."""
        pass


class IBookRepositoryPort(ABC):
    """Porta para gerenciamento de metadados e estado dos livros no disco."""
    
    @abstractmethod
    def get_indexed_hashes(self) -> Dict[str, str]:
        """Retorna mapeamento de {file_path: sha256_hash} dos livros já processados."""
        pass
        
    @abstractmethod
    def save_book_metadata(self, book: Book) -> None:
        """Persiste metadados do livro após ingestão."""
        pass
