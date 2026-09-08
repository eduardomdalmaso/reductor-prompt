import os
import tempfile
import pytest
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.domain.entities.book import Book


def test_file_book_repository_hash_and_metadata():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = FileBookRepositoryAdapter(storage_dir=tmp_dir)
        
        # Cria arquivo temporário
        test_file = os.path.join(tmp_dir, "sample.txt")
        with open(test_file, "w") as f:
            f.write("Conteúdo de teste para hashing.")
            
        file_hash = repo.calculate_file_hash(test_file)
        assert len(file_hash) == 64  # SHA-256
        
        book = Book(
            id="book-test",
            title="Sample Book",
            file_path=test_file,
            file_name="sample.txt",
            file_hash=file_hash,
            file_format="txt",
            total_chunks=1,
            total_tokens=10
        )
        repo.save_book_metadata(book)
        
        indexed_hashes = repo.get_indexed_hashes()
        assert test_file in indexed_hashes
        assert indexed_hashes[test_file] == file_hash
