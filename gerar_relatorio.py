#!/usr/bin/env python3
"""
Script de Geração Contínua do Relatório de Auditoria de Segurança
Executado diretamente ou gerenciado via PM2.
"""
import sys
import time
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_GEN_SCRIPT = SCRIPT_DIR / "docs" / "security-audit" / "generate_audit_report.py"


def run_generator() -> bool:
    """Executa a compilação do relatório PDF."""
    if not REPORT_GEN_SCRIPT.exists():
        print(f"❌ Script não encontrado: {REPORT_GEN_SCRIPT}", file=sys.stderr)
        return False
    try:
        print("📄 [gerar_relatorio] Iniciando compilação do relatório de segurança...")
        result = subprocess.run(
            [sys.executable, str(REPORT_GEN_SCRIPT)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ [gerar_relatorio] {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"❌ [gerar_relatorio] Erro ao gerar relatório:\n{exc.stderr}", file=sys.stderr)
        return False


def main():
    """Ponto de entrada principal."""
    # Gera na inicialização
    run_generator()

    # Modo contínuo se executado via PM2 ou com flag --watch / --daemon
    is_daemon = "--daemon" in sys.argv or "--watch" in sys.argv or "PM2_HOME" in sys.modules or True
    if is_daemon:
        print("⏱️ [gerar_relatorio] Serviço em execução no PM2 (atualização periódica a cada 60 min)...")
        while True:
            try:
                time.sleep(3600)
                run_generator()
            except KeyboardInterrupt:
                print("🛑 Encerrando serviço gerar_relatorio...")
                break


if __name__ == "__main__":
    main()
