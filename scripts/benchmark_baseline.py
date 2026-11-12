#!/usr/bin/env python3
"""Benchmark Baseline V1 do ReductorPrompt.

Mede e discrimina com precisão estatística cada etapa do pipeline atual:
1. Expansão Heurística de Query (t_expand)
2. Geração de Embeddings (t_embed)
3. Busca Vetorial no ChromaDB (t_search)
4. Fusão RRF e Compressão Elbow (t_compress)
5. Tokens Recuperados, Tokens Reduzidos e Preservação Canônica
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config.settings import settings
from src.application.services.query_rewriter_service import QueryRewriterService
from src.application.services.prompt_compressor_service import PromptCompressorService

BENCHMARK_QUERIES = [
    {
        "id": "q1_factual",
        "category": "factual",
        "query": "Qual a diferença de performance entre B-Tree e LSM-Tree?",
    },
    {
        "id": "q2_conceptual",
        "category": "conceptual",
        "query": "Como funciona o mecanismo de replicação líder-seguidor e consistência eventual?",
    },
    {
        "id": "q3_architectural",
        "category": "architectural",
        "query": "Como estruturar um pipeline de streaming WebRTC com WHEP e baixa latência?",
    }
]


def benchmark_single_query(
    query_item: Dict[str, str],
    rewriter: QueryRewriterService,
    embedder: ResilientEmbeddingAdapter,
    vector_store: ChromaVectorStoreAdapter,
    compressor: PromptCompressorService,
    iterations: int = 3
) -> Dict[str, Any]:
    query_text = query_item["query"]
    t_expands, t_embeds, t_searches, t_compresses = [], [], [], []
    last_context = None

    for _ in range(iterations):
        # 1. Medição da Expansão
        t0 = time.perf_counter()
        variations = rewriter.expand_query(query_text, max_variations=3)
        t_expand = (time.perf_counter() - t0) * 1000
        t_expands.append(t_expand)

        # 2. Medição do Embedding + 3. Busca Vetorial
        t_embed_total = 0.0
        t_search_total = 0.0
        batch_results: List[List] = []
        top_k = settings.DEFAULT_TOP_K * 2

        for q_var in variations:
            t_emb_start = time.perf_counter()
            q_vector = embedder.embed_text(q_var)
            t_embed_total += (time.perf_counter() - t_emb_start) * 1000

            t_search_start = time.perf_counter()
            scored = vector_store.search(query_embedding=q_vector, top_k=top_k)
            t_search_total += (time.perf_counter() - t_search_start) * 1000

            if scored:
                batch_results.append(scored)

        t_embeds.append(t_embed_total)
        t_searches.append(t_search_total)

        # 4. Fusão RRF e Compressão Adaptativa (Elbow Cutoff)
        t_comp_start = time.perf_counter()
        scored_chunks = compressor.fuse_chunks_rrf(batch_results) if batch_results else []
        compressed_ctx = compressor.compress_and_format(query=query_text, scored_chunks=scored_chunks)
        t_compress = (time.perf_counter() - t_comp_start) * 1000
        t_compresses.append(t_compress)
        last_context = compressed_ctx

    def _avg(lst: List[float]) -> float:
        return round(sum(lst) / len(lst), 3) if lst else 0.0

    return {
        "id": query_item["id"],
        "category": query_item["category"],
        "query": query_text,
        "timings_ms": {
            "query_expansion": _avg(t_expands),
            "embeddings": _avg(t_embeds),
            "vector_search": _avg(t_searches),
            "fusion_and_compression": _avg(t_compresses),
            "total_retrieval": round(_avg(t_expands) + _avg(t_embeds) + _avg(t_searches) + _avg(t_compresses), 3)
        },
        "metrics": {
            "tokens_used": last_context.total_tokens if last_context else 0,
            "tokens_original": last_context.original_estimated_tokens if last_context else 0,
            "reduction_percent": round(last_context.token_reduction_percent, 2) if last_context else 0.0,
            "sources_count": len(last_context.sources) if last_context else 0,
            "canonical_fidelity": all("book_title" in s for s in last_context.sources) if last_context else True
        }
    }


def main():
    print("=" * 65)
    print("⚡ ReductorPrompt - Benchmark Instrumentado Baseline V1")
    print("=" * 65)

    from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
    from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter

    rewriter = QueryRewriterService(enable_expansion=True)
    embedder = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    compressor = PromptCompressorService()

    # Warmup
    print("Iniciando warmup de modelos e conexões...")
    try:
        _ = embedder.embed_text("warmup")
    except Exception as e:
        print(f"[Aviso] Warmup de embedding com fallback: {e}")

    results = []
    for item in BENCHMARK_QUERIES:
        print(f"\n▶ Executando benchmark: [{item['category']}] '{item['query'][:50]}...'")
        metrics = benchmark_single_query(item, rewriter, embedder, vector_store, compressor, iterations=3)
        results.append(metrics)
        t = metrics["timings_ms"]
        m = metrics["metrics"]
        print(f"  ├─ Expansão: {t['query_expansion']}ms | Embed: {t['embeddings']}ms | Busca: {t['vector_search']}ms | Compressão: {t['fusion_and_compression']}ms")
        print(f"  ├─ Tempo Total de Recuperação: {t['total_retrieval']}ms")
        print(f"  └─ Tokens: {m['tokens_used']} usados de {m['tokens_original']} ({m['reduction_percent']}% reduzido) | Fontes: {m['sources_count']}")

    output_path = ROOT_DIR / "docs" / "benchmarks" / "baseline_v1.json"
    output_path.write_text(json.dumps({"benchmark": "Baseline V1", "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 65)
    print(f"✔ Benchmark concluído! Resultados persistidos em: {output_path.relative_to(ROOT_DIR)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
