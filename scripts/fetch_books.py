#!/usr/bin/env python3
"""
Ponto de entrada para download e compilação dinâmica universal de livros e documentações.
Uso:
  python scripts/fetch_books.py "https://github.com/laravel/docs/tree/12.x" --compile --ingest
  python scripts/fetch_books.py "https://arxiv.org/pdf/2401.05566.pdf" --ingest
"""

import sys
import argparse
from pathlib import Path
from typing import List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.application.services.doc_fetcher_service import DocFetcherService, is_safe_public_url

console = Console()


def run_pipeline(urls: List[str], max_workers: int = 8, compile_tree: bool = True, trigger_ingest: bool = False):
    console.print(Panel.fit(
        "[bold cyan]📚 ReductorPrompt - Universal Book & Doc Fetcher[/bold cyan]\n"
        "[dim]Download inteligente, compilação semântica e auto-ingestão vetorial[/dim]",
        border_style="cyan"
    ))

    service = DocFetcherService()
    all_results = []

    for u in urls:
        console.print(f"🔍 [dim]Processando fonte:[/dim] [blue]{u}[/blue]")
        results = service.process_url(u, compile_tree=compile_tree, max_workers=max_workers)
        all_results.extend(results)

    table = Table(title="📊 Resumo da Extração Dinâmica", border_style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Arquivo / Manual", style="cyan")
    table.add_column("Detalhes", style="dim")

    for status, name, detail in all_results:
        st_color = "green" if status in ["DOWNLOADED", "COMPILED"] else ("yellow" if status == "SKIPPED_EXISTING" else "red")
        table.add_row(f"[{st_color}]{status}[/{st_color}]", name, detail)

    console.print("\n", table)

    if trigger_ingest and any(st in ["DOWNLOADED", "COMPILED"] for st, _, _ in all_results):
        console.print("\n[bold cyan]🧠 Disparando ingestão vetorial automática no ChromaDB...[/bold cyan]")
        from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
        from src.adapters.outbound.loaders.document_loaders import CompositeDocumentLoader
        from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
        from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
        from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter

        use_case = IngestBooksUseCase(
            loader=CompositeDocumentLoader(),
            embedding_port=ResilientEmbeddingAdapter(),
            vector_store=ChromaVectorStoreAdapter(),
            book_repo=FileBookRepositoryAdapter()
        )
        books = use_case.execute(force_reindex=False)
        console.print(f"[bold green]✨ Ingestão concluída com sucesso! {len(books)} livros/manuais indexados.[/bold green]")


def main():
    parser = argparse.ArgumentParser(description="ReductorPrompt Universal Book & Doc Fetcher")
    parser.add_argument("urls", nargs="+", help="Uma ou mais URLs (GitHub tree, blob ou links diretos)")
    parser.add_argument("--workers", "-w", type=int, default=8, help="Número de threads concorrentes")
    parser.add_argument("--compile", "-c", action="store_true", default=True, help="Compila árvores de markdown em manuais únicos")
    parser.add_argument("--ingest", "-i", action="store_true", help="Auto-ingestão no ChromaDB após download")

    args = parser.parse_args()
    run_pipeline(args.urls, max_workers=args.workers, compile_tree=args.compile, trigger_ingest=args.ingest)


if __name__ == "__main__":
    main()
