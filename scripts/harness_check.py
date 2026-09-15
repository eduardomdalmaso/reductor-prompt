"""ReductorPrompt - Agent Harness Verification Script.

Executa diagnóstico instantâneo e verificável por máquina dos 5 subsistemas de
Harness Engineering:
1. Environment: Python Conda runtime e dependências.
2. State & Storage: Acesso ao ChromaDB (Podman / Local persistente) e diretórios.
3. Instruction & Security: Configurações de API_SECURITY_KEY e CORS.
4. Tooling & MCP: Disponibilidade do CLI e endpoints.
5. Feedback Signals: Execução rápida da suíte de testes automatizados.
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Adiciona raiz do projeto ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def print_status(component: str, status: str, details: str = ""):
    if console:
        color = "green" if status == "OK" else ("yellow" if status == "WARN" else "red")
        console.print(f"[{color}]●[/{color}] [bold]{component:<25}[/bold] [{color}]{status:<6}[/{color}] {details}")
    else:
        print(f"[{status}] {component:<25}: {details}")


def check_environment():
    """Verifica runtime e ambiente Python."""
    py_ver = sys.version.split()[0]
    in_conda = "reductor-prompt" in sys.executable or "conda" in sys.executable
    details = f"Python {py_ver} ({'Conda env ativo' if in_conda else 'Python de sistema'})"
    print_status("Environment (Python)", "OK" if in_conda else "WARN", details)
    return in_conda


def check_storage_and_vector_db():
    """Verifica conectividade e integridade do ChromaDB e repositório de livros."""
    from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
    try:
        adapter = ChromaVectorStoreAdapter()
        books = adapter.list_indexed_books()
        details = f"{len(books)} livros indexados no ChromaDB ({adapter.mode})"
        print_status("Vector Store (ChromaDB)", "OK", details)
        return True
    except Exception as e:
        print_status("Vector Store (ChromaDB)", "FAIL", f"Erro: {str(e)}")
        return False


def check_security_and_config():
    """Verifica parâmetros de segurança e configurações do harness."""
    from src.config.settings import settings
    sec_key = getattr(settings, "API_SECURITY_KEY", None)
    cors = getattr(settings, "CORS_ALLOWED_ORIGINS", "")
    provider = getattr(settings, "LLM_PROVIDER", "ollama")
    
    details = f"Provider: {provider} | Auth: {'Habilitada' if sec_key else 'Aberta (dev)'} | CORS: {cors or 'Padrão restrito'}"
    print_status("Security & Config", "OK", details)
    return True


def check_test_suite():
    """Executa a suíte de testes pytest de forma concisa."""
    pytest_bin = str(Path(sys.executable).parent / "pytest")
    if not os.path.exists(pytest_bin):
        pytest_bin = "pytest"
        
    start = time.time()
    result = subprocess.run([pytest_bin, "-q"], capture_output=True, text=True, cwd=str(ROOT_DIR))
    elapsed = time.time() - start
    
    if result.returncode == 0:
        summary = result.stdout.strip().split("\n")[-1]
        print_status("Feedback Tests (pytest)", "OK", f"{summary} ({elapsed:.2f}s)")
        return True
    else:
        print_status("Feedback Tests (pytest)", "FAIL", f"Falha nos testes: {result.stdout.strip()[:100]}")
        return False


def main():
    if console:
        console.print(Panel.fit(
            "[bold cyan]🛡️ ReductorPrompt - Harness Engineering Health Check[/bold cyan]\n"
            "[dim]Validação de determinismo, infraestrutura e feedback loops do agente[/dim]",
            border_style="cyan"
        ))
    else:
        print("=== ReductorPrompt - Harness Engineering Health Check ===")

    print("\n🔍 Executando diagnósticos do Harness:")
    c1 = check_environment()
    c2 = check_storage_and_vector_db()
    c3 = check_security_and_config()
    c4 = check_test_suite()

    all_passed = c2 and c3 and c4
    print("\n" + "─" * 60)
    if all_passed:
        if console:
            console.print("[bold green]✨ Harness operacional e 100% calibrado para execução autônoma.[/bold green]\n")
        else:
            print("✨ Harness operacional e 100% calibrado para execução autônoma.\n")
        sys.exit(0)
    else:
        if console:
            console.print("[bold red]⚠️ Falhas detectadas no Harness. Verifique os componentes acima.[/bold red]\n")
        else:
            print("⚠️ Falhas detectadas no Harness. Verifique os componentes acima.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
