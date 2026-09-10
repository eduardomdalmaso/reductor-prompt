import os
import re
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.domain.entities.book import Book, BookChunk, ScoredChunk
from src.domain.ports.outbound import IVectorStorePort
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ChromaVectorStoreAdapter(IVectorStorePort):
    """Adaptador de banco vetorial com suporte a Podman/Container (HttpClient) e Local (PersistentClient)."""

    def __init__(
        self, 
        persist_directory: Optional[str] = None, 
        embedding_model_name: Optional[str] = None,
        mode: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        self.persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        self.mode = (mode or settings.CHROMA_MODE).lower()
        self.host = host or settings.CHROMA_HOST
        self.port = port or settings.CHROMA_PORT

        # Cria um nome de coleção limpo associado ao modelo de embedding
        model_tag = re.sub(r'[^a-zA-Z0-9_]', '_', embedding_model_name or settings.OLLAMA_EMBED_MODEL or "default")
        self.collection_name = f"books_kb_{model_tag}"

        self.client = self._init_client()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _init_client(self):
        """Inicializa HttpClient (Podman) ou PersistentClient (Local)."""
        if self.mode == "http":
            try:
                client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                # Testa se o container está respondendo
                client.heartbeat()
                logger.info(f"Conectado ao ChromaDB via Podman em http://{self.host}:{self.port}")
                return client
            except Exception as e:
                logger.warning(
                    f"Não foi possível conectar ao ChromaDB no Podman (http://{self.host}:{self.port}): {e}. "
                    f"Alternando para modo local persistente em '{self.persist_dir}'."
                )
        
        os.makedirs(self.persist_dir, exist_ok=True)
        return chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    def upsert_chunks(self, book: Book, chunks: List[BookChunk], embeddings: List[List[float]]) -> None:
        if not chunks:
            return

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "book_id": book.id,
                "book_title": book.title,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "page_number": chunk.page_number if chunk.page_number is not None else -1,
                "chapter": chunk.chapter or ""
            }
            for chunk in chunks
        ]

        # Chroma upsert em lotes
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end]
            )

    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 4, 
        book_title_filter: Optional[str] = None
    ) -> List[ScoredChunk]:
        where_filter = None
        if book_title_filter:
            where_filter = {"book_title": {"$eq": book_title_filter}}

        # Consulta no Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(1, self.collection.count())),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        scored_chunks: List[ScoredChunk] = []
        
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
            similarity = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
            
            chunk = BookChunk(
                id=chunk_id,
                book_id=meta.get("book_id", ""),
                book_title=meta.get("book_title", "Desconhecido"),
                chunk_index=meta.get("chunk_index", 0),
                content=doc,
                token_count=meta.get("token_count", len(doc.split())),
                page_number=meta.get("page_number") if meta.get("page_number", -1) != -1 else None,
                chapter=meta.get("chapter") or None
            )
            scored_chunks.append(ScoredChunk(chunk=chunk, score=similarity))

        return scored_chunks

    def delete_book(self, book_id: str) -> None:
        self.collection.delete(where={"book_id": {"$eq": book_id}})

    def list_indexed_books(self) -> List[Dict[str, Any]]:
        # 1. Tenta carregar do catálogo persistente de metadados se existir
        catalog_path = os.path.join(settings.STORAGE_DIR, "indexed_books.json")
        if os.path.exists(catalog_path):
            try:
                import json
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    books = data.get("books", {})
                    if books:
                        return [
                            {
                                "book_id": b.get("id", b_id),
                                "title": b.get("title", "Desconhecido"),
                                "chunks_count": b.get("total_chunks", 0)
                            }
                            for b_id, b in books.items()
                        ]
            except Exception:
                pass

        # 2. Paginação segura em lotes no ChromaDB para não estourar variáveis do SQLite
        books_map = {}
        batch_size = 500
        offset = 0
        total_count = self.collection.count()

        while offset < total_count:
            try:
                batch = self.collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["metadatas"]
                )
                metas = batch.get("metadatas", [])
                if not metas:
                    break

                for m in metas:
                    b_id = m.get("book_id")
                    if b_id and b_id not in books_map:
                        books_map[b_id] = {
                            "book_id": b_id,
                            "title": m.get("book_title", "Desconhecido"),
                            "chunks_count": 0
                        }
                    if b_id:
                        books_map[b_id]["chunks_count"] += 1

                offset += batch_size
            except Exception:
                break

        return list(books_map.values())
