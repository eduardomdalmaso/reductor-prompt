import pytest
from src.application.services.chunking_service import ChunkingService
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.domain.entities.book import BookChunk, ScoredChunk


def test_chunking_service_split():
    service = ChunkingService(chunk_size=100, chunk_overlap=20)
    raw_docs = [
        {"text": "Este é o primeiro parágrafo de teste sobre bancos de dados.\n\nEste é o segundo parágrafo sobre LSM-Trees e otimização.", "page_number": 1, "chapter": "Cap 1"}
    ]
    chunks = service.split_raw_documents(raw_docs, "b1", "Test Book")
    assert len(chunks) >= 1
    assert chunks[0].book_title == "Test Book"
    assert chunks[0].page_number == 1
    assert chunks[0].token_count > 0


def test_prompt_compressor_reduction():
    compressor = PromptCompressorService()
    
    c1 = BookChunk("c1", "b1", "Book 1", 1, "LSM-Tree é uma estrutura de dados de escrita sequencial rápida.", 20, 1, "Cap 1")
    c2 = BookChunk("c2", "b1", "Book 1", 2, "Bloom filter previne leituras desnecessárias de disco.", 15, 2, "Cap 1")
    
    scored_chunks = [
        ScoredChunk(chunk=c1, score=0.85),
        ScoredChunk(chunk=c2, score=0.78)
    ]
    
    compressed = compressor.compress_and_format(
        query="Como otimizar escrita?",
        scored_chunks=scored_chunks,
        max_tokens=1000
    )
    
    assert compressed.total_tokens > 0
    assert compressed.token_reduction_percent > 90.0
    assert len(compressed.sources) == 2
    assert "Book 1" in compressed.raw_context_text
