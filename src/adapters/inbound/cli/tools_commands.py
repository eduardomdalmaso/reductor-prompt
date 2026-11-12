from typing import Optional
import typer
from rich.panel import Panel

from src.application.services.hardware_budget_advisor_service import hardware_advisor_service
from src.adapters.inbound.cli.formatters import console


def register_tools_commands(app: typer.Typer):
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
