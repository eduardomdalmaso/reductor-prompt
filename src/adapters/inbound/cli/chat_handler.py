import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.application.use_cases.query_books_use_case import QueryBooksUseCase

console = Console()


def run_interactive_chat(
    use_case: QueryBooksUseCase,
    book_filter: Optional[str] = None,
    deep_reasoning: bool = False
):
    """Executa loop interativo de conversação técnica no terminal (REPL)."""
    console.print(Panel.fit(
        "[bold cyan]💬 ReductorPrompt - Terminal Interativo (REPL)[/bold cyan]\n"
        "[dim]Digite sua dúvida técnica ou 'sair' / 'exit' para encerrar. Digite ':clear' para limpar.[/dim]",
        border_style="cyan"
    ))
    
    if book_filter:
        console.print(f"[bold yellow]Filtro de Livro Ativo:[/bold yellow] [cyan]{book_filter}[/cyan]\n")

    while True:
        try:
            console.print("[bold green]reductor>[/bold green] ", end="")
            user_input = input().strip()
            
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "sair", ":q"]:
                console.print("[bold yellow]Encerrando sessão interativa. Até mais![/bold yellow]")
                break

            if user_input.lower() == ":clear":
                console.clear()
                continue

            # Processa a pergunta
            with console.status("[bold cyan]Consultando cérebro e livros técnicos...[/bold cyan]", spinner="dots"):
                result = use_case.execute(
                    query=user_input,
                    book_filter=book_filter,
                    deep_reasoning=deep_reasoning,
                    use_brain=True,
                    auto_learn=True
                )

            console.print("\n[bold cyan]─── Resposta ───[/bold cyan]")
            console.print(Markdown(result["response"]))
            
            origin = "🧠 Cérebro (<2ms)" if result.get("from_brain") else "📚 RAG 194+ Livros"
            console.print(
                f"\n[dim]Tokens: {result['tokens_used']} | Economia: {result['reduction_percentage']}% | Origem: {origin}[/dim]\n"
            )

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Sessão encerrada.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro ao processar consulta:[/bold red] {e}\n")
