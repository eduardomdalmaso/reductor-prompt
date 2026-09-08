import os
import json
import hashlib
from typing import Dict, Any, Optional
from src.domain.entities.book import Book
from src.domain.ports.outbound import IBookRepositoryPort
from src.config.settings import settings


class FileBookRepositoryAdapter(IBookRepositoryPort):
    """Gerencia o registro e estado dos livros indexados em JSON persistente."""
    
    REGISTRY_FILE = "indexed_books.json"

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        os.makedirs(self.storage_dir, exist_ok=True)
        self.registry_path = os.path.join(self.storage_dir, self.REGISTRY_FILE)
        self._init_registry()

    def _init_registry(self):
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump({"books": {}}, f, indent=2)

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"books": {}}

    def _save_data(self, data: Dict[str, Any]):
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_indexed_hashes(self) -> Dict[str, str]:
        data = self._load_data()
        return {b_info["file_path"]: b_info["file_hash"] for b_info in data.get("books", {}).values()}

    def save_book_metadata(self, book: Book) -> None:
        data = self._load_data()
        data["books"][book.id] = {
            "id": book.id,
            "title": book.title,
            "file_path": book.file_path,
            "file_name": book.file_name,
            "file_hash": book.file_hash,
            "file_format": book.file_format,
            "total_chunks": book.total_chunks,
            "total_tokens": book.total_tokens,
            "created_at": book.created_at.isoformat(),
            "metadata": book.metadata
        }
        self._save_data(data)

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calcula o hash SHA-256 do arquivo para controle de modificações."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
