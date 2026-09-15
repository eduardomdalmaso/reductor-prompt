import os
import uuid
import logging
from pathlib import Path
from typing import List, Optional

from src.domain.entities.book import Book
from src.domain.ports.inbound import IIngestBooksUseCase
from src.domain.ports.outbound import (
    IDocumentLoaderPort,
    IEmbeddingPort,
    IVectorStorePort,
    IBookRepositoryPort
)
from src.application.services.chunking_service import ChunkingService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class IngestBooksUseCase(IIngestBooksUseCase):
    """Caso de uso para escanear a pasta database, processar e indexar livros com deduplicação."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.epub', '.ipynb', '.txt', '.md', '.markdown'}

    def __init__(
        self,
        loader: IDocumentLoaderPort,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        book_repo: IBookRepositoryPort,
        chunking_service: Optional[ChunkingService] = None,
        database_dir: Optional[str] = None
    ):
        self.loader = loader
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.book_repo = book_repo
        self.chunking_service = chunking_service or ChunkingService()
        self.database_dir = database_dir or settings.DATABASE_DIR

    def execute(self, force_reindex: bool = False) -> List[Book]:
        db_path = Path(self.database_dir)
        if not db_path.exists():
            db_path.mkdir(parents=True, exist_ok=True)
            return []

        indexed_hashes = self.book_repo.get_indexed_hashes() if not force_reindex else {}
        processed_books: List[Book] = []

        files_to_process = [
            f for f in db_path.iterdir() 
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

        for file_path in files_to_process:
            str_path = str(file_path.resolve())
            current_hash = self.book_repo.calculate_file_hash(str_path)

            # Verifica se já foi indexado e não mudou
            if str_path in indexed_hashes and indexed_hashes[str_path] == current_hash and not force_reindex:
                logger.info(f"Livro já indexado sem alterações: {file_path.name}")
                continue

            book_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{str_path}_{current_hash}"))
            book_title = file_path.stem.replace('_', ' ').replace('-', ' ').title()

            logger.info(f"Extraindo conteúdo de: {file_path.name}")
            raw_docs = self.loader.load(str_path)
            if not raw_docs:
                logger.warning(f"Nenhum texto pôde ser extraído de {file_path.name}")
                continue

            # Divisão semântica em chunks
            chunks = self.chunking_service.split_raw_documents(raw_docs, book_id, book_title)
            if not chunks:
                continue

            # Geração de embeddings locais (Custo zero de API)
            logger.info(f"Gerando embeddings para {len(chunks)} blocos de '{book_title}'...")
            chunk_texts = [c.content for c in chunks]
            embeddings = self.embedding_port.embed_batch(chunk_texts)

            # Armazena no banco vetorial
            self.vector_store.upsert_chunks(
                book=Book(
                    id=book_id,
                    title=book_title,
                    file_path=str_path,
                    file_name=file_path.name,
                    file_hash=current_hash,
                    file_format=file_path.suffix.lower().lstrip('.'),
                    total_chunks=len(chunks),
                    total_tokens=sum(c.token_count for c in chunks)
                ),
                chunks=chunks,
                embeddings=embeddings
            )

            book = Book(
                id=book_id,
                title=book_title,
                file_path=str_path,
                file_name=file_path.name,
                file_hash=current_hash,
                file_format=file_path.suffix.lower().lstrip('.'),
                total_chunks=len(chunks),
                total_tokens=sum(c.token_count for c in chunks)
            )

            self.book_repo.save_book_metadata(book)
            processed_books.append(book)

        return processed_books
