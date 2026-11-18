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
    assert compressed.original_estimated_tokens == 35
    assert compressed.token_reduction_percent == 0.0
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

    compressed = compressor.compress_and_format("Como funciona?", scored, max_tokens=1000)
    assert compressed.original_estimated_tokens == 60
    assert compressed.token_reduction_percent == pytest.approx(33.33, abs=0.1)


def test_query_cache_key_isolates_flags():
    from src.application.use_cases.query_books_use_case import (
        QueryBooksUseCase,
        invalidate_query_cache,
        _QUERY_CACHE,
    )

    uc = QueryBooksUseCase.__new__(QueryBooksUseCase)
    k1 = uc._get_cache_key("concorrencia", None, 2500, True, False, True, True)
    k2 = uc._get_cache_key("concorrencia", None, 2500, True, False, False, True)
    k3 = uc._get_cache_key("concorrencia", None, 2500, True, False, True, False)
    assert len({k1, k2, k3}) == 3

    _QUERY_CACHE[k1] = {"response": "stale"}
    new_epoch = invalidate_query_cache()
    assert len(_QUERY_CACHE) == 0
    assert new_epoch >= 2
    k1_after = uc._get_cache_key("concorrencia", None, 2500, True, False, True, True)
    assert k1_after != k1


def test_pdf_normalize_preserving_structure():
    from src.adapters.outbound.loaders.document_loaders import normalize_preserving_structure

    raw = "def allocate(line, batches):   \r\n    return next(b for b in batches)\r\n\r\n\r\n\r\nCol1  |  Col2\n"
    cleaned = normalize_preserving_structure(raw)
    assert "\ndef allocate(line, batches):" not in cleaned
    assert "def allocate(line, batches):\n    return next(b for b in batches)\n\nCol1  |  Col2" == cleaned


def test_deep_prompt_includes_short_refusal_rule():
    compressor = PromptCompressorService()
    c1 = BookChunk("c1", "b1", "Book 1", 1, "Texto qualquer", 10, 1, "Cap 1")
    ctx = compressor.compress_and_format("Pergunta", [ScoredChunk(chunk=c1, score=0.8)], max_tokens=500)
    sys_inst, _ = compressor.build_qa_prompt("Pergunta", ctx, deep_reasoning=True)
    assert "REGRA DE RECUSA ECONÔMICA" in sys_inst
    assert "Não encontrei evidências suficientes" in sys_inst


def test_conservative_strategy_respects_max_cut_percent():
    compressor = PromptCompressorService()
    chunks = [
        ScoredChunk(BookChunk(f"c{i}", "b1", "Book 1", i, f"Texto {i}", 100, i, "Cap 1"), 0.9 - i * 0.05)
        for i in range(5)
    ]
    res = compressor.compress_and_format(
        "Como funciona?", chunks, max_tokens=2000, strategy="conservative", max_cut_percent=10.0
    )
    assert res.token_reduction_percent <= 10.0


def test_resolve_book_filter_and_lexical_boost():
    from src.application.use_cases.query_books_use_case import (
        resolve_book_filter,
        apply_lexical_identifier_boost,
    )

    titles = ["Architecturepatternswithpython", "Introducingpython3Rdedition", "Pythonpolars Thedefinitiveguide"]
    f1, amb1 = resolve_book_filter("Show SqlAlchemyRepository from Architecture Patterns with Python", None, titles)
    assert f1 == "Architecturepatternswithpython" and amb1 == []

    f2, amb2 = resolve_book_filter("Explain Python", "Python", titles)
    assert f2 is None and len(amb2) == 3

    c_generic = ScoredChunk(BookChunk("c1", "b2", "Introducingpython3Rdedition", 1, "Generic Python class", 10, 1, "P1"), 0.90)
    c_exact = ScoredChunk(BookChunk("c2", "b1", "Architecturepatternswithpython", 1, "class SqlAlchemyRepository: pass", 10, 1, "P1"), 0.80)
    ranked = apply_lexical_identifier_boost("Show SqlAlchemyRepository", [c_generic, c_exact])
    assert ranked[0].chunk.id == "c2"


def test_extract_technical_identifiers():
    from src.application.use_cases.query_books_use_case import extract_technical_identifiers

    ids = extract_technical_identifiers("Show SqlAlchemyRepository and can_allocate methods")
    assert ids == ["SqlAlchemyRepository", "can_allocate"]


def test_citation_grounding_and_span_traceability():
    compressor = PromptCompressorService()
    c1 = BookChunk("c1", "b1", "Book 1", 1, "Repository decouples domain.", 10, 49, "Cap 2")
    ctx = compressor.compress_and_format("Repository?", [ScoredChunk(c1, 0.9)], max_tokens=500)
    src = ctx.sources[0]
    assert src["chunk_id"] == "c1"
    assert src["page_start"] == 49 and src["page_end"] == 49
    assert src["char_start"] == 0 and src["char_end"] == len(c1.content)

    g_ok = compressor.verify_citation_grounding("Conforme Book 1 (Pág 49).", ctx.sources)
    assert g_ok["grounding_ratio"] == 1.0 and g_ok["ungrounded_pages"] == []

    g_bad = compressor.verify_citation_grounding("Conforme Book 1 (Pág 999).", ctx.sources)
    assert g_bad["grounding_ratio"] == 0.0 and g_bad["ungrounded_pages"] == [999]


def test_bm25_sqlite_index_search(tmp_path):
    from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex

    idx = BM25SqliteIndex(db_path=str(tmp_path / "bm25_test.db"))
    with idx._connect() as conn:
        conn.execute(
            "INSERT INTO chunks_fts(chunk_id, book_id, book_title, chapter, page_number, token_count, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("c1", "b1", "Architecturepatternswithpython", "Cap 2", 54, 20, "class SqlAlchemyRepository: def add(self, batch): pass"),
        )
        conn.execute(
            "INSERT INTO chunks_fts(chunk_id, book_id, book_title, chapter, page_number, token_count, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("c2", "b2", "Introducingpython3Rdedition", "Cap 1", 10, 15, "Python lists and dictionaries tutorial"),
        )
        conn.commit()
    hits = idx.search("SqlAlchemyRepository add", top_k=5)
    assert len(hits) >= 1
    assert hits[0].chunk.id == "c1"
    assert hits[0].chunk.page_number == 54

    idx.upsert_chunks("b1", "Architecturepatternswithpython", [
        BookChunk("c3", "b1", "Architecturepatternswithpython", 0, "def allocate(line, batches): pass", 12, 46, "Cap 1")
    ])
    assert idx.count() == 2
    idx.delete_book("b1")
    assert idx.count() == 1
    assert idx.verify_consistency(1)["in_sync"] is True


def test_hybrid_bm25_query_use_case_profiles(tmp_path):
    from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
    from src.application.use_cases.query_books_use_case import QueryBooksUseCase, invalidate_query_cache
    from tests.test_episodic_memory import MockEmbeddingPort, MockVectorStorePort, MockLLMPort

    idx = BM25SqliteIndex(db_path=str(tmp_path / "bm25_uc.db"))
    idx.upsert_chunks("b1", "Book 1", [
        BookChunk("c_bm25", "b1", "Book 1", 0, "SqlAlchemyRepository uses session.add and session.query", 15, 54, "Cap 2")
    ])
    uc = QueryBooksUseCase(
        embedding_port=MockEmbeddingPort(),
        vector_store=MockVectorStorePort(),
        llm_port=MockLLMPort(),
        bm25_index=idx,
    )
    invalidate_query_cache()
    res_fid = uc.execute("SqlAlchemyRepository", use_brain=False, auto_learn=False, profile="fidelity")
    assert any(s.get("chunk_id") == "c_bm25" for s in res_fid["sources"])

    res_eco = uc.execute("SqlAlchemyRepository", use_brain=False, auto_learn=False, profile="economy")
    assert any(s.get("chunk_id") == "c_bm25" for s in res_eco["sources"])

    res_leg = uc.execute("SqlAlchemyRepository", use_brain=False, auto_learn=False, profile="legacy")
    assert not any(s.get("chunk_id") == "c_bm25" for s in res_leg["sources"])


def test_url_sanitization_and_default_economy_profile():
    from src.application.dtos.query_dtos import QueryRequestDTO

    assert QueryRequestDTO(query="test").profile == "economy"

    ctx = "Veja a doc oficial em https://redis.io/docs/latest/develop/data-types/sorted-sets/."
    resp = (
        "Use [Redis Docs](https://redis.io/docs/latest/develop/data-types/sorted-sets/) "
        "e evite [Fake](https://example.com/redis#hincrby) ou https://fake-url.local/test."
    )
    cleaned, blocked = PromptCompressorService.validate_and_sanitize_urls(resp, ctx)
    assert "https://redis.io/docs/latest/develop/data-types/sorted-sets/" in cleaned
    assert "https://example.com/redis#hincrby" not in cleaned
    assert "https://fake-url.local/test" not in cleaned
    assert len(blocked) == 2


def test_generation_queue_limits_and_saturation():
    import threading
    import time
    import pytest
    from src.adapters.outbound.llm.generation_queue import GenerationQueue, QueueSaturatedError

    q = GenerationQueue(max_concurrent=1, max_pending=1, acquire_timeout_s=2.0)
    entered = threading.Event()
    release = threading.Event()

    def worker():
        with q.slot():
            entered.set()
            release.wait(timeout=2.0)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    entered.wait(timeout=1.0)
    t2.start()
    time.sleep(0.05)

    with pytest.raises(QueueSaturatedError):
        with q.slot():
            pass

    release.set()
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)
    m = q.get_metrics()
    assert m["total_acquired"] == 2
    assert m["generation_rejected_total"] == 1
    assert m["generation_active"] == 0


def test_generation_queue_cooperative_cancellation():
    import threading
    import time
    import pytest
    from src.adapters.outbound.llm.generation_queue import GenerationQueue, QueueCancelledError

    q = GenerationQueue(max_concurrent=1, max_pending=4, acquire_timeout_s=5.0)
    entered = threading.Event()
    release = threading.Event()
    cancel_flag = threading.Event()

    def active_worker():
        with q.slot():
            entered.set()
            release.wait(timeout=2.0)

    t_active = threading.Thread(target=active_worker)
    t_active.start()
    entered.wait(timeout=1.0)

    # Dispara cancelamento enquanto a segunda requisição aguarda na fila
    threading.Timer(0.15, cancel_flag.set).start()
    with pytest.raises(QueueCancelledError):
        with q.slot(is_cancelled=cancel_flag.is_set):
            pass

    # Garante que a geração ativa manteve o slot até liberar
    assert q.get_metrics()["generation_active"] == 1
    release.set()
    t_active.join(timeout=2.0)

    m = q.get_metrics()
    assert m["generation_cancelled_total"] == 1
    assert m["generation_active"] == 0
    assert m["generation_pending"] == 0


def test_lexical_port_contract_and_prometheus_metrics():
    from fastapi.testclient import TestClient
    from src.adapters.inbound.api.fastapi_app import app
    from src.adapters.outbound.vector_store.bm25_sqlite_index import BM25SqliteIndex
    from src.domain.ports.outbound import ILexicalIndexPort

    assert issubclass(BM25SqliteIndex, ILexicalIndexPort)
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "reductor_generation_active" in resp.text
    assert "reductor_process_rss_bytes" in resp.text

