import pytest
from src.domain.entities.book import Book, BookChunk, ScoredChunk, CompressedContext, OptimizationInsight
from src.domain.value_objects.token_budget import TokenBudget
from src.domain.exceptions.exceptions import BookNotFoundException, EmptyDatabaseException


def test_token_budget_savings():
    budget = TokenBudget(max_context_tokens=1500)
    original = 100000
    actual = 1200
    savings = budget.calculate_savings(original, actual)
    assert savings == 98.8


def test_book_entity_creation():
    book = Book(
        id="book-123",
        title="Test Book",
        file_path="/path/test.md",
        file_name="test.md",
        file_hash="abc123hash",
        file_format="md",
        total_chunks=5,
        total_tokens=2500
    )
    assert book.title == "Test Book"
    assert book.total_chunks == 5
    assert book.total_tokens == 2500


def test_domain_exceptions():
    with pytest.raises(BookNotFoundException) as exc:
        raise BookNotFoundException("NonExistentBook")
    assert "NonExistentBook" in str(exc.value)

    with pytest.raises(EmptyDatabaseException) as exc:
        raise EmptyDatabaseException("/path/database")
    assert "/path/database" in str(exc.value)
