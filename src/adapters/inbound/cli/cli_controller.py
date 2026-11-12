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
from src.application.use_cases.make_decision_use_case import MakeDecisionUseCase
from src.domain.ports.inbound import MakeDecisionCommand
from src.adapters.inbound.cli.formatters import (
    print_ask_result, print_analyze_result, print_books_table, print_decision_result, console
)
from src.adapters.inbound.cli.chat_handler import run_interactive_chat
from src.adapters.inbound.cli.brain_commands import register_brain_commands
from src.adapters.inbound.cli.tools_commands import register_tools_commands

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


@app.command(name="decide")
def decide(
    query: str = typer.Argument(..., help="Dúvida técnica ou proposta arquitetural para decisão"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Nome do projeto (ex: HydraStream)"),
    hardware: Optional[str] = typer.Option(None, "--hardware", "-hw", help="Hardware alvo (ex: RTX 5090)"),
    commit: Optional[str] = typer.Option(None, "--commit", "-c", help="Commit hash de referência"),
    policy_version: str = typer.Option("1.0.0", "--policy", help="Versão da política determinística"),
    max_tokens: int = typer.Option(2500, "--max-tokens", "-m", help="Limite de tokens do contexto"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Retorna relatório em JSON"),
    provider: Optional[str] = typer.Option(None, "--provider", "-P", help="Provedor LLM")
):
    """Executa decisão bilateral confrontando teoria e benchmarks com política determinística."""
    _, embedding_port, vector_store, memory_port, _, llm_port = get_dependencies(provider)
    use_case = MakeDecisionUseCase(
        embedding_port=embedding_port,
        vector_store=vector_store,
        memory_port=memory_port,
        llm_port=llm_port
    )
    cmd = MakeDecisionCommand(
        query=query, project_source=project, target_hardware=hardware,
        target_commit=commit, policy_version=policy_version, max_tokens=max_tokens
    )
    report = use_case.execute(cmd)
    print_decision_result(report, json_output=json_output)


register_brain_commands(brain_app, get_dependencies)
register_tools_commands(app)
