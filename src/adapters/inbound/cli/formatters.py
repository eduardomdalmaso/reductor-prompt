import json
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def print_ask_result(result: Dict[str, Any], json_output: bool = False):
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    console.print("\n[bold green]💡 Resposta:[/bold green]")
    console.print(Markdown(result["response"]))
    console.print("\n" + "─" * 60)

    metric_table = Table(
        title="📊 Métricas de Otimização de Tokens",
        show_header=True,
        header_style="bold blue"
    )
    metric_table.add_column("Tokens Utilizados", justify="center", style="green")
    metric_table.add_column("Tokens Economizados", justify="center", style="cyan")
    metric_table.add_column("Taxa de Redução", justify="center", style="bold magenta")
    metric_table.add_column("Origem", justify="center", style="bold yellow")
    
    origin = "🧠 Cérebro (<2ms)" if result.get("from_brain") else "📚 RAG 194+ Livros"
    
    metric_table.add_row(
        f"{result['tokens_used']:,}",
        f"{result['tokens_saved']:,}",
        f"{result['reduction_percentage']}%",
        origin
    )
    console.print(metric_table)

    if result.get("sources"):
        console.print("\n[bold yellow]📖 Fontes Consultadas:[/bold yellow]")
        for s in result["sources"]:
            loc = []
            if s.get("chapter"): loc.append(s["chapter"])
            if s.get("page"): loc.append(f"Pág {s['page']}")
            loc_str = f" ({', '.join(loc)})" if loc else ""
            console.print(f" • [cyan]{s['book_title']}[/cyan]{loc_str} [dim]Similaridade: {s['score']}[/dim]")
    console.print("")


def print_analyze_result(insight, json_output: bool = False):
    if json_output:
        print(json.dumps(insight.to_dict(), ensure_ascii=False, indent=2))
        return

    console.print("\n[bold green]📋 Relatório de Otimização Estratégica:[/bold green]")
    console.print(Markdown(insight.raw_response))
    console.print("\n" + "─" * 60)

    stats = insight.token_stats
    console.print(
        f"[bold]Tokens de Contexto Enviados:[/bold] [green]{stats.get('tokens_used', 0):,}[/green] | "
        f"[bold]Economizados:[/bold] [cyan]{stats.get('tokens_saved', 0):,}[/cyan] | "
        f"[bold]Redução:[/bold] [magenta]{stats.get('reduction_percent', 0)}%[/magenta]\n"
    )


def print_books_table(books: List[Dict[str, Any]]):
    if not books:
        console.print("[yellow]Nenhum livro indexado ainda. Use 'ingest' após colocar arquivos em database/.[/yellow]")
        return

    table = Table(title="📚 Livros e Manuais no Banco Vetorial", show_header=True, header_style="bold cyan")
    table.add_column("ID do Livro", style="dim")
    table.add_column("Título", style="bold green")
    table.add_column("Total de Chunks", justify="right", style="magenta")

    for b in books:
        table.add_row(b["book_id"][:12] + "...", b["title"], str(b["chunks_count"]))

    console.print(table)


def print_brain_table(episodes: List[Dict[str, Any]]):
    if not episodes:
        console.print("[yellow]Nenhum conhecimento registrado no Cérebro ainda.[/yellow]")
        return

    table = Table(
        title="🧠 Memórias do Cérebro Coletivo (agent_episodic_brain)",
        show_header=True,
        header_style="bold magenta"
    )
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
