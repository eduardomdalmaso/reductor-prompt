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
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.application.services.hardware_budget_advisor_service import hardware_advisor_service

app = typer.Typer(help="ReductorPrompt - Otimizador de Prompts e RAG para Livros Técnicos")
brain_app = typer.Typer(help="Gerenciamento da Memória Episódica & Cérebro Coletivo")
app.add_typer(brain_app, name="brain")

console = Console()


def get_dependencies(llm_provider: Optional[str] = None):
    loader = CompositeDocumentLoader()
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    memory_port = ChromaEpisodicMemoryAdapter()
    book_repo = FileBookRepositoryAdapter()
    llm_port = LLMFactory.create(llm_provider)
    return loader, embedding_port, vector_store, memory_port, book_repo, llm_port


@app.command(name="ingest")
def ingest(
    force: bool = typer.Option(False, "--force", "-f", help="Força a reindexação de todos os livros"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Diretório customizado de livros")
):
    """Escaneia a pasta database/ e indexa livros novos ou modificados."""
    console.print(Panel.fit("[bold cyan]📚 ReductorPrompt - Ingestão Inteligente de Livros[/bold cyan]"))
    
    loader, embedding_port, vector_store, _, book_repo, _ = get_dependencies()
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
    deep: bool = typer.Option(False, "--deep", "-d", help="Ativa modo de raciocínio profundo com Chain-of-Thought e Self-Reflection"),
    fast: bool = typer.Option(False, "--fast", help="Desativa expansão de query para resposta ultrarrápida direta"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM: 'gemini' ou 'ollama'")
):
    """Faz uma pergunta ao agente consumindo o mínimo de tokens e máxima precisão semântica."""
    console.print(Panel.fit(f"[bold cyan]🔍 Pergunta:[/bold cyan] {query}"))
    
    loader, embedding_port, vector_store, memory_port, book_repo, llm_port = get_dependencies(provider)
    use_case = QueryBooksUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port,
        memory_port=memory_port
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description="Consultando cérebro e livros técnicos...", total=None)
        result = use_case.execute(
            query=query,
            book_filter=book,
            max_tokens=max_tokens,
            only_context=only_context,
            deep_reasoning=deep,
            enable_rewriting=not fast,
            use_brain=True,
            auto_learn=True
        )

    # Exibe Resposta
    console.print("\n[bold green]💡 Resposta:[/bold green]")
    console.print(Markdown(result["response"]))
    console.print("\n" + "─" * 60)

    # Exibe Métricas de Economia de Tokens
    metric_table = Table(title="📊 Métricas de Otimização de Tokens", show_header=True, header_style="bold blue")
    metric_table.add_column("Tokens Utilizados", justify="center", style="green")
    metric_table.add_column("Tokens Economizados", justify="center", style="cyan")
    metric_table.add_column("Taxa de Redução", justify="center", style="bold magenta")
    metric_table.add_column("Origem", justify="center", style="bold yellow")
    
    origin = "🧠 Cérebro (<2ms)" if result.get("from_brain") else "📚 RAG 194 Livros"
    
    metric_table.add_row(
        f"{result['tokens_used']:,}",
        f"{result['tokens_saved']:,}",
        f"{result['reduction_percentage']}%",
        origin
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
    project: str = typer.Option(..., "--project", "-p", help="Descrição da arquitetura, pipeline ou problema do seu projeto"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Tópico específico a cruzar com a teoria dos livros"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Filtrar por título de livro específico"),
    max_tokens: int = typer.Option(2500, "--max-tokens", "-m", help="Limite máximo de tokens do contexto do livro"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM: 'gemini' ou 'ollama'")
):
    """Executa Análise Cruzada: o que do livro pode otimizar o seu projeto."""
    console.print(Panel.fit("[bold magenta]🚀 ReductorPrompt - Análise Cruzada de Projeto vs. Livro[/bold magenta]"))
    console.print(f"[bold cyan]Projeto:[/bold cyan] {project[:150]}...")
    if topic:
        console.print(f"[bold yellow]Foco:[/bold yellow] {topic}")

    loader, embedding_port, vector_store, _, book_repo, llm_port = get_dependencies(provider)
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
    _, _, vector_store, _, _, _ = get_dependencies()
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


# ==========================================
# Subcomandos do Cérebro Episódico (brain)
# ==========================================

@brain_app.command(name="list")
def brain_list(
    limit: int = typer.Option(30, "--limit", "-l", help="Limite de memórias"),
    query: Optional[str] = typer.Option(None, "--filter", "-f", help="Filtro de busca")
):
    """Lista os aprendizados e memórias indexados no Cérebro Coletivo."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    episodes = use_case.list_knowledge(limit=limit, query_filter=query)

    if not episodes:
        console.print("[yellow]Nenhum conhecimento registrado no Cérebro ainda.[/yellow]")
        return

    table = Table(title="🧠 Memórias do Cérebro Coletivo (agent_episodic_brain)", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Pergunta / Conceito", style="cyan")
    table.add_column("Tópico", style="green")
    table.add_column("Hits", justify="right", style="yellow")
    table.add_column("Data", style="dim")

    for ep in episodes:
        table.add_row(
            ep["id"][:8],
            ep["query"][:60] + ("..." if len(ep["query"]) > 60 else ""),
            ep.get("topic") or "Geral",
            str(ep.get("hit_count", 0)),
            ep.get("created_at", "")[:10]
        )

    console.print(table)


@brain_app.command(name="teach")
def brain_teach(
    query: str = typer.Argument(..., help="Pergunta ou problema chave"),
    insight: str = typer.Argument(..., help="Resposta lapidada ou código canônico"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Tópico/Categoria")
):
    """Ensina diretamente um novo conhecimento ao Cérebro Coletivo."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    episode = use_case.teach_brain(query=query, insight=insight, topic=topic)
    console.print(f"[bold green]✔ Conhecimento gravado no cérebro com sucesso! [ID: {episode.id}][/bold green]")


@brain_app.command(name="clear")
def brain_clear():
    """Limpa todas as memórias do Cérebro Coletivo."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    use_case.clear_brain()
    console.print("[bold red]✔ Cérebro episódico resetado com sucesso.[/bold red]")


@app.command(name="advisor")
def budget_advisor(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Simular provedor ('ollama' ou 'gemini')")
):
    """Oráculo de Recursos: Exibe telemetria de hardware e parâmetros ideais de consulta."""
    console.print(Panel.fit("[bold cyan]🔮 Oráculo de Recursos & Telemetria Adaptativa[/bold cyan]"))
    advice = hardware_advisor_service.get_runtime_advice(provider_override=provider)

    table = Table(title="📊 Diagnóstico de Hardware & Orçamento", show_header=True, header_style="bold green")
    table.add_column("Propriedade", style="cyan")
    table.add_column("Status / Valor", style="bold yellow")

    table.add_row("Ambiente de Execução", advice.get("runtime_environment", ""))
    table.add_row("Hardware Detectado", advice.get("hardware_detected", ""))
    table.add_row("Custo Financeiro", advice.get("financial_cost", ""))
    table.add_row("Provedor Ativo", advice.get("active_provider", "").upper())
    table.add_row("Estratégia Recomendada", advice.get("strategy_name", ""))
    
    if "recommended_model" in advice:
        table.add_row("Modelo Recomendado", advice.get("recommended_model", ""))

    console.print(table)

    # Parâmetros ideais
    params = advice.get("optimal_parameters", {})
    param_table = Table(title="⚙️ Parâmetros Ótimos Recomendados para o Agente", show_header=True, header_style="bold magenta")
    param_table.add_column("Parâmetro", style="bold white")
    param_table.add_column("Valor Recomendado", style="bold green")

    for k, v in params.items():
        param_table.add_row(k, str(v))

    console.print(param_table)
    console.print(Panel(f"[bold green]💡 Orientação para o Agente:[/bold green]\n{advice.get('guidance_for_agent', '')}"))


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
