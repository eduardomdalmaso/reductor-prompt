from typing import Optional
import typer
from rich.panel import Panel

from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.adapters.inbound.cli.formatters import print_brain_table, console

brain_app = typer.Typer(help="Gerenciamento da Memória Episódica & Cérebro Coletivo")


def register_brain_commands(brain_typer: typer.Typer, get_deps_fn):
    @brain_typer.command(name="list")
    def brain_list(
        limit: int = typer.Option(30, "--limit", "-l"),
        query: Optional[str] = typer.Option(None, "--filter", "-f")
    ):
        """Lista memórias do Cérebro Episódico."""
        _, embedding_port, _, memory_port, _, _ = get_deps_fn()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        print_brain_table(use_case.list_knowledge(limit=limit, query_filter=query))

    @brain_typer.command(name="teach")
    def brain_teach(
        query: str = typer.Argument(...),
        insight: str = typer.Argument(...),
        topic: Optional[str] = typer.Option(None, "--topic", "-t")
    ):
        """Ensina conhecimento diretamente ao Cérebro."""
        _, embedding_port, _, memory_port, _, _ = get_deps_fn()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        episode = use_case.teach_brain(query=query, insight=insight, topic=topic)
        console.print(f"[bold green]✔ Conhecimento registrado no cérebro! [ID: {episode.id}][/bold green]")

    @brain_typer.command(name="clear")
    def brain_clear():
        """Limpa a memória do Cérebro Coletivo."""
        _, embedding_port, _, memory_port, _, _ = get_deps_fn()
        use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
        use_case.clear_brain()
        console.print("[bold red]✔ Cérebro resetado com sucesso.[/bold red]")
