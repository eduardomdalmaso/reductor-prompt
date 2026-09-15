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


def test_dynamic_budget_and_query_complexity():
    compressor = PromptCompressorService()

    # Factual query -> Orçamento enxuto
    assert compressor.classify_query_complexity("O que é RRF?") == "factual"
    assert compressor.determine_dynamic_budget("O que é RRF?") <= 800

    # Conceptual query -> Orçamento padrão
    assert compressor.classify_query_complexity("Como funciona a atenção em Transformers?") == "conceptual"
    assert compressor.determine_dynamic_budget("Como funciona a atenção em Transformers?") <= 1800

    # Architectural query -> Orçamento expandido
    assert compressor.classify_query_complexity("Análise de arquitetura e escalabilidade do pipeline") == "architectural"
    assert compressor.determine_dynamic_budget("Análise de arquitetura e escalabilidade do pipeline") >= 2500


def test_elbow_cutoff_filters_noise_tail():
    compressor = PromptCompressorService()
    
    c1 = BookChunk("c1", "b1", "Book 1", 1, "Trecho altamente relevante", 20, 1, "Cap 1")
    c2 = BookChunk("c2", "b1", "Book 1", 2, "Outro trecho muito bom", 20, 2, "Cap 1")
    c3 = BookChunk("c3", "b1", "Book 1", 3, "Trecho marginal de ruído", 20, 3, "Cap 1")

    # c3 cai de 0.90 para 0.40 (> 35% de queda relativa e > 0.22 de degrau)
    scored = [
        ScoredChunk(chunk=c1, score=0.92),
        ScoredChunk(chunk=c2, score=0.88),
        ScoredChunk(chunk=c3, score=0.38)
    ]

    filtered = compressor.apply_elbow_cutoff(scored, min_score=0.25)
    assert len(filtered) == 2
    assert filtered[0].chunk.id == "c1"
    assert filtered[1].chunk.id == "c2"

