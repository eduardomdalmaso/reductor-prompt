import json
import os
from typing import Any, Dict, List

from src.config.settings import settings


def list_indexed_books_from_storage(collection) -> List[Dict[str, Any]]:
    """Lista livros indexados via catálogo JSON ou paginação segura no ChromaDB."""
    catalog_path = os.path.join(settings.STORAGE_DIR, "indexed_books.json")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                books = json.load(f).get("books", {})
                if books:
                    return [
                        {
                            "book_id": b.get("id", b_id),
                            "title": b.get("title", "Desconhecido"),
                            "chunks_count": b.get("total_chunks", 0),
                        }
                        for b_id, b in books.items()
                    ]
        except Exception:
            pass

    books_map: Dict[str, Dict[str, Any]] = {}
    batch_size = 500
    offset = 0
    total_count = collection.count()

    while offset < total_count:
        try:
            batch = collection.get(limit=batch_size, offset=offset, include=["metadatas"])
            metas = batch.get("metadatas", [])
            if not metas:
                break
            for m in metas:
                b_id = m.get("book_id")
                if b_id and b_id not in books_map:
                    books_map[b_id] = {
                        "book_id": b_id,
                        "title": m.get("book_title", "Desconhecido"),
                        "chunks_count": 0,
                    }
                if b_id:
                    books_map[b_id]["chunks_count"] += 1
            offset += batch_size
        except Exception:
            break

    return list(books_map.values())
