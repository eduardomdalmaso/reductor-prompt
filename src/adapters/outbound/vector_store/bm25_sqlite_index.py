import os
import re
import sqlite3
from typing import List, Optional

from src.domain.entities.book import BookChunk, ScoredChunk


class BM25SqliteIndex:
    """Índice lexical BM25 experimental sobre os mesmos chunks do ChromaDB via SQLite FTS5."""

    def __init__(self, db_path: str = "./storage/bm25_fts5.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    book_id UNINDEXED,
                    book_title,
                    chapter,
                    page_number UNINDEXED,
                    token_count UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                )
                """
            )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()
            return int(row[0]) if row else 0

    def rebuild_from_chroma(self, collection, batch_size: int = 2000) -> int:
        """Constrói o índice FTS5 lendo diretamente os chunks canônicos do ChromaDB."""
        total = collection.count()
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks_fts")
            offset = 0
            inserted = 0
            while offset < total:
                batch = collection.get(limit=batch_size, offset=offset, include=["documents", "metadatas"])
                ids = batch.get("ids") or []
                docs = batch.get("documents") or []
                metas = batch.get("metadatas") or []
                if not ids:
                    break
                rows = [
                    (
                        cid,
                        m.get("book_id", ""),
                        m.get("book_title", "Desconhecido"),
                        m.get("chapter", ""),
                        int(m.get("page_number", -1)),
                        int(m.get("token_count", len(doc.split()))),
                        doc,
                    )
                    for cid, doc, m in zip(ids, docs, metas)
                    if doc
                ]
                conn.executemany(
                    "INSERT INTO chunks_fts(chunk_id, book_id, book_title, chapter, page_number, token_count, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                inserted += len(rows)
                offset += batch_size
            conn.commit()
        return inserted

    @staticmethod
    def _build_fts_query(query: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9_]{2,}", query)
        if not tokens:
            return ""
        # Limita a 16 termos para consultas FTS5 rápidas e seguras
        unique = list(dict.fromkeys(tokens))[:16]
        return " OR ".join(f'"{t}"' for t in unique)

    def search(
        self,
        query: str,
        top_k: int = 16,
        book_title_filter: Optional[str] = None,
    ) -> List[ScoredChunk]:
        fts_query = self._build_fts_query(query)
        if not fts_query:
            return []

        sql = (
            "SELECT chunk_id, book_id, book_title, chapter, page_number, token_count, content, "
            "bm25(chunks_fts) AS rank_score "
            "FROM chunks_fts WHERE chunks_fts MATCH ? "
        )
        params: list = [fts_query]
        if book_title_filter:
            sql += "AND book_title = ? "
            params.append(book_title_filter)
        sql += "ORDER BY rank_score ASC LIMIT ?"
        params.append(top_k)

        with self._connect() as conn:
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []

        results: List[ScoredChunk] = []
        for cid, bid, btitle, chap, page, tcount, doc, raw_bm25 in rows:
            # bm25() no FTS5 é negativo (quanto menor/mais negativo, melhor)
            score = 1.0 / (1.0 + max(0.0, 10.0 + float(raw_bm25)))
            chunk = BookChunk(
                id=cid,
                book_id=bid,
                book_title=btitle,
                chunk_index=0,
                content=doc,
                token_count=int(tcount) if tcount else len(doc.split()),
                page_number=int(page) if page is not None and int(page) != -1 else None,
                chapter=chap or None,
            )
            results.append(ScoredChunk(chunk=chunk, score=min(1.0, max(0.0, score))))
        return results
