import os
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.settings import settings
from src.adapters.outbound.loaders.document_loaders import CompositeDocumentLoader
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase

app = typer.Typer(help="ReductorPrompt - Otimizador de Prompts e RAG para Livros Técnicos")
console = Console()


def get_dependencies(llm_provider: Optional[str] = None):
    loader = CompositeDocumentLoader()
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    book_repo = FileBookRepositoryAdapter()
    llm_port = LLMFactory.create(llm_provider)
    return loader, embedding_port, vector_store, book_repo, llm_port


@app.command(name="ingest")
def ingest(
    force: bool = typer.Option(False, "--force", "-f", help="Força a reindexação de todos os livros"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Diretório customizado de livros")
):
    """Escaneia a pasta database/ e indexa livros novos ou modificados."""
    console.print(Panel.fit("[bold cyan]📚 ReductorPrompt - Ingestão Inteligente de Livros[/bold cyan]"))
    
    loader, embedding_port, vector_store, book_repo, _ = get_dependencies()
    use_case = IngestBooksUseCase(
        loader=loader,
        embedding_port=embedding_port,
        vector_store=vector_store,
        book_repo=book_repo,
        database_dir=path or settings.DATABASE_DIR
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description="Processando e indexando livros...", total=None)
        books = use_case.execute(force_reindex=force)

    if not books:
        console.print("[yellow]Nenhum livro novo encontrado para indexar.[/yellow]")
        console.print(f"Coloque seus arquivos (.pdf, .epub, .txt, .md) em: [bold]{settings.DATABASE_DIR}[/bold]")
        return

    table = Table(title="✨ Livros Indexados com Sucesso", show_header=True, header_style="bold green")
    table.add_column("Título", style="cyan")
    table.add_column("Formato", style="magenta")
    table.add_column("Total Chunks", justify="right")
    table.add_column("Tokens Indexados", justify="right")

    for b in books:
        table.add_row(b.title, b.file_format.upper(), str(b.total_chunks), f"{b.total_tokens:,}")

    console.print(table)
    console.print("[bold green]✔ Ingestão concluída com custo zero de API![/bold green]\n")


@app.command(name="ask")
def ask(
    query: str = typer.Argument(..., help="Pergunta a ser respondida com base nos livros"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Filtrar busca por título de livro específico"),
    max_tokens: int = typer.Option(1500, "--max-tokens", "-m", help="Limite máximo de tokens do contexto"),
    only_context: bool = typer.Option(False, "--only-context", "-c", help="Retorna apenas o contexto enxuto"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM: 'gemini' ou 'ollama'")
):
    """Faz uma pergunta ao agente consumindo o mínimo de tokens."""
    console.print(Panel.fit(f"[bold cyan]🔍 Pergunta:[/bold cyan] {query}"))
    
    loader, embedding_port, vector_store, book_repo, llm_port = get_dependencies(provider)
    use_case = QueryBooksUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description="Buscando trechos cirúrgicos e gerando resposta...", total=None)
        result = use_case.execute(
            query=query,
            book_filter=book,
            max_tokens=max_tokens,
            only_context=only_context
        )

    # Exibe Resposta
    console.print("\n[bold green]💡 Resposta do Agente:[/bold green]")
    console.print(Markdown(result["response"]))
    console.print("\n" + "─" * 60)

    # Exibe Métricas de Economia de Tokens
    metric_table = Table(title="📊 Métricas de Otimização de Tokens", show_header=True, header_style="bold blue")
    metric_table.add_column("Tokens Utilizados", justify="center", style="green")
    metric_table.add_column("Tokens Economizados", justify="center", style="cyan")
    metric_table.add_column("Taxa de Redução", justify="center", style="bold magenta")
    
    metric_table.add_row(
        f"{result['tokens_used']:,}",
        f"{result['tokens_saved']:,}",
        f"{result['reduction_percentage']}%"
    )
    console.print(metric_table)

    # Exibe Fontes Citadas
    if result.get("sources"):
        console.print("\n[bold yellow]📖 Fontes Consultadas:[/bold yellow]")
        for s in result["sources"]:
            loc = []
            if s.get("chapter"): loc.append(s["chapter"])
            if s.get("page"): loc.append(f"Pág {s['page']}")
            loc_str = f" ({', '.join(loc)})" if loc else ""
            console.print(f" • [cyan]{s['book_title']}[/cyan]{loc_str} [dim]Similaridade: {s['score']}[/dim]")
    console.print("")


@app.command(name="analyze")
def analyze(
    project: str = typer.Option(..., "--project", "-p", help="Descrição detalhada do seu projeto ou código"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Livro de referência específico para a análise"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Foco (ex: latência, escalabilidade, modelagem)"),
    max_tokens: int = typer.Option(2000, "--max-tokens", "-m", help="Limite de tokens para o contexto"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM: 'gemini' ou 'ollama'")
):
    """Executa Análise Cruzada: o que do livro pode otimizar o seu projeto."""
    console.print(Panel.fit("[bold magenta]🚀 ReductorPrompt - Análise Cruzada de Projeto vs. Livro[/bold magenta]"))
    console.print(f"[bold cyan]Projeto:[/bold cyan] {project[:150]}...")
    if topic:
        console.print(f"[bold yellow]Foco:[/bold yellow] {topic}")

    loader, embedding_port, vector_store, book_repo, llm_port = get_dependencies(provider)
    use_case = AnalyzeProjectUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description="Cruzando arquitetura do projeto com a literatura...", total=None)
        insight = use_case.execute(
            project_description=project,
            book_filter=book,
            focus_topic=topic,
            max_tokens=max_tokens
        )

    console.print("\n[bold green]📋 Relatório de Otimização Estratégica:[/bold green]")
    console.print(Markdown(insight.raw_response))
    console.print("\n" + "─" * 60)

    # Métricas
    stats = insight.token_stats
    console.print(f"[bold]Tokens de Contexto Enviados:[/bold] [green]{stats.get('tokens_used', 0):,}[/green] | "
                  f"[bold]Economizados:[/bold] [cyan]{stats.get('tokens_saved', 0):,}[/cyan] | "
                  f"[bold]Redução:[/bold] [magenta]{stats.get('reduction_percent', 0)}%[/magenta]\n")


@app.command(name="list")
def list_books():
    """Lista todos os livros atualmente indexados no banco vetorial."""
    _, _, vector_store, _, _ = get_dependencies()
    books = vector_store.list_indexed_books()

    if not books:
        console.print("[yellow]Nenhum livro indexado ainda. Use o comando 'ingest' após colocar arquivos na pasta database/.[/yellow]")
        return

    table = Table(title="📚 Livros Disponíveis no Banco Vetorial", show_header=True, header_style="bold cyan")
    table.add_column("ID do Livro", style="dim")
    table.add_column("Título", style="bold green")
    table.add_column("Total de Chunks", justify="right", style="magenta")

    for b in books:
        table.add_row(b["book_id"][:12] + "...", b["title"], str(b["chunks_count"]))

    console.print(table)


@app.command(name="fetch")
def fetch(
    urls: str = typer.Argument(..., help="Uma ou mais URLs separadas por vírgula (GitHub tree, blob ou links diretos)"),
    workers: int = typer.Option(6, "--workers", "-w", help="Número de threads concorrentes para download"),
    ingest_after: bool = typer.Option(False, "--ingest", "-i", help="Dispara a ingestão vetorial automaticamente após o download")
):
    """Baixa dinamicamente livros de repositórios GitHub ou links diretos com deduplicação."""
    from scripts.fetch_books import run_pipeline
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    run_pipeline(url_list, max_workers=workers, trigger_ingest=ingest_after)
