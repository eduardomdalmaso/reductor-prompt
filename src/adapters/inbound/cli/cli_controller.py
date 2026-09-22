import os
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
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
from src.adapters.inbound.cli.formatters import (
    print_ask_result, print_analyze_result, print_books_table, print_brain_table, console
)
from src.adapters.inbound.cli.chat_handler import run_interactive_chat

app = typer.Typer(help="ReductorPrompt - Otimizador de Prompts, RAG e CLI para Livros Técnicos")
brain_app = typer.Typer(help="Gerenciamento da Memória Episódica & Cérebro Coletivo")
app.add_typer(brain_app, name="brain")


def get_dependencies(llm_provider: Optional[str] = None):
    loader = CompositeDocumentLoader()
    embedding_port = ResilientEmbeddingAdapter()
    vector_store = ChromaVectorStoreAdapter()
    memory_port = ChromaEpisodicMemoryAdapter()
    book_repo = FileBookRepositoryAdapter()
    llm_port = LLMFactory.create(llm_provider)
    return loader, embedding_port, vector_store, memory_port, book_repo, llm_port


@app.command(name="ask")
def ask(
    query: str = typer.Argument(..., help="Pergunta técnica a ser respondida com base nos livros"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Filtrar busca por título de livro"),
    max_tokens: int = typer.Option(1500, "--max-tokens", "-m", help="Limite máximo de tokens do contexto"),
    only_context: bool = typer.Option(False, "--only-context", "-c", help="Retorna apenas o contexto enxuto"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Ativa modo de raciocínio profundo com Chain-of-Thought"),
    fast: bool = typer.Option(False, "--fast", help="Desativa expansão de query para resposta direta"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Retorna o resultado formatado em JSON"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM: 'gemini' ou 'ollama'")
):
    """Consulta os livros e o cérebro consumindo o mínimo de tokens com máxima precisão."""
    if not json_output:
        console.print(Panel.fit(f"[bold cyan]🔍 Pergunta:[/bold cyan] {query}"))
    
    _, embedding_port, vector_store, memory_port, _, llm_port = get_dependencies(provider)
    use_case = QueryBooksUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        llm_port=llm_port,
        memory_port=memory_port
    )

    if not json_output:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
            p.add_task(description="Consultando cérebro e livros técnicos...", total=None)
            result = use_case.execute(
                query=query, book_filter=book, max_tokens=max_tokens, only_context=only_context,
                deep_reasoning=deep, enable_rewriting=not fast, use_brain=True, auto_learn=True
            )
    else:
        result = use_case.execute(
            query=query, book_filter=book, max_tokens=max_tokens, only_context=only_context,
            deep_reasoning=deep, enable_rewriting=not fast, use_brain=True, auto_learn=True
        )

    print_ask_result(result, json_output=json_output)


@app.command(name="chat")
def chat(
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Filtrar contexto por título de livro"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Raciocínio profundo ativado"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM")
):
    """Inicia sessão interativa de perguntas e respostas no terminal (REPL)."""
    _, embedding_port, vector_store, memory_port, _, llm_port = get_dependencies(provider)
    use_case = QueryBooksUseCase(
        embedding_port=embedding_port, vector_store=vector_store, llm_port=llm_port, memory_port=memory_port
    )
    run_interactive_chat(use_case, book_filter=book, deep_reasoning=deep)


@app.command(name="analyze")
def analyze(
    project: str = typer.Option(..., "--project", "-p", help="Descrição da arquitetura ou código"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Tópico específico a cruzar"),
    book: Optional[str] = typer.Option(None, "--book", "-b", help="Filtrar por livro específico"),
    max_tokens: int = typer.Option(2500, "--max-tokens", "-m", help="Limite de tokens do contexto"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Retorna resultado em JSON"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM")
):
    """Executa Análise Cruzada: o que a literatura técnica recomenda para otimizar o projeto."""
    if not json_output:
        console.print(Panel.fit("[bold magenta]🚀 ReductorPrompt - Análise Cruzada de Projeto vs. Livros[/bold magenta]"))
    
    _, embedding_port, vector_store, _, _, llm_port = get_dependencies(provider)
    use_case = AnalyzeProjectUseCase(embedding_port=embedding_port, vector_store=vector_store, llm_port=llm_port)
    insight = use_case.execute(project_description=project, book_filter=book, focus_topic=topic, max_tokens=max_tokens)
    print_analyze_result(insight, json_output=json_output)


@app.command(name="ingest")
def ingest(
    force: bool = typer.Option(False, "--force", "-f", help="Força reindexação total"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Diretório customizado de documentos")
):
    """Indexa documentos e livros novos da pasta database/ no ChromaDB."""
    console.print(Panel.fit("[bold cyan]📚 ReductorPrompt - Ingestão de Documentos Técnicos[/bold cyan]"))
    loader, embedding_port, vector_store, _, book_repo, _ = get_dependencies()
    use_case = IngestBooksUseCase(
        loader=loader, embedding_port=embedding_port, vector_store=vector_store,
        book_repo=book_repo, database_dir=path or settings.DATABASE_DIR
    )
    books = use_case.execute(force_reindex=force)
    console.print(f"[bold green]✔ Ingestão concluída! {len(books)} documentos processados.[/bold green]")


@app.command(name="list")
def list_books():
    """Lista todos os livros e manuais indexados no banco vetorial."""
    _, _, vector_store, _, _, _ = get_dependencies()
    print_books_table(vector_store.list_indexed_books())


@app.command(name="serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host de binding da API"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta TCP da API REST"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Ativar auto-reload em desenvolvimento")
):
    """Inicia a API REST FastAPI de alta performance."""
    import uvicorn
    console.print(Panel.fit(f"[bold green]🚀 Iniciando ReductorPrompt REST API em http://{host}:{port}[/bold green]"))
    uvicorn.run("src.adapters.inbound.api.fastapi_app:app", host=host, port=port, reload=reload)


@app.command(name="advisor")
def advisor(provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Simular provedor")):
    """Exibe telemetria de hardware e parâmetros ideais de consulta."""
    advice = hardware_advisor_service.get_runtime_advice(provider_override=provider)
    console.print(Panel.fit(f"[bold cyan]🔮 Oráculo de Recursos:[/bold cyan] {advice.get('strategy_name', '')}"))
    console.print(f"[bold]Hardware:[/bold] {advice.get('hardware_detected')} | [bold]Provedor:[/bold] {advice.get('active_provider')}")


@app.command(name="fetch")
def fetch(
    urls: str = typer.Argument(..., help="URLs separadas por vírgula para download"),
    workers: int = typer.Option(6, "--workers", "-w", help="Threads concorrentes"),
    ingest_after: bool = typer.Option(False, "--ingest", "-i", help="Auto-ingestão após download")
):
    """Baixa dinamicamente livros/docs do GitHub com deduplicação SHA-256."""
    from scripts.fetch_books import run_pipeline
    run_pipeline([u.strip() for u in urls.split(",") if u.strip()], max_workers=workers, trigger_ingest=ingest_after)


@brain_app.command(name="list")
def brain_list(limit: int = typer.Option(30, "--limit", "-l"), query: Optional[str] = typer.Option(None, "--filter", "-f")):
    """Lista memórias do Cérebro Episódico."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    print_brain_table(use_case.list_knowledge(limit=limit, query_filter=query))


@brain_app.command(name="teach")
def brain_teach(query: str = typer.Argument(...), insight: str = typer.Argument(...), topic: Optional[str] = typer.Option(None, "--topic", "-t")):
    """Ensina conhecimento diretamente ao Cérebro."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    episode = use_case.teach_brain(query=query, insight=insight, topic=topic)
    console.print(f"[bold green]✔ Conhecimento registrado no cérebro! [ID: {episode.id}][/bold green]")


@brain_app.command(name="clear")
def brain_clear():
    """Limpa a memória do Cérebro Coletivo."""
    _, embedding_port, _, memory_port, _, _ = get_dependencies()
    use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
    use_case.clear_brain()
    console.print("[bold red]✔ Cérebro resetado com sucesso.[/bold red]")
