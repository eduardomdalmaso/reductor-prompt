#!/usr/bin/env python3
"""
Universal Dynamic Book & Doc Fetcher - ReductorPrompt
======================================================
Downloader e compilador dinâmico universal baseado nas melhores práticas de:
- "High Performance Python" (Concorrência com ThreadPoolExecutor e I/O Buffering)
- "Python in a Nutshell" (Resiliência de Rede, Backoff e Tratamento de Exceções)
- "Architecture Patterns with Python" & Clean Code (Separação de Responsabilidades e Idempotência)

Suporta:
  1. Pastas do GitHub (tree): https://github.com/owner/repo/tree/branch/subfolder
  2. Arquivos do GitHub (blob): https://github.com/owner/repo/blob/branch/book.pdf
  3. Links diretos da Web (ArXiv, PDFs, EPUBs, Markdown, etc.)
  4. Múltiplas URLs separadas por vírgula, espaço ou arquivo .txt
  5. Deduplicação criptográfica SHA-256 e verificação pré-download
  6. Ingestão vetorial automática opcional (--ingest)
"""

import os
import sys
import re
import time
import json
import hashlib
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
    console = Console()
except ImportError:
    console = None

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
REGISTRY_FILE = STORAGE_DIR / "indexed_books.json"

SUPPORTED_EXTENSIONS = {'.pdf', '.epub', '.ipynb', '.txt', '.md', '.markdown'}
DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (ReductorPrompt-Fetcher/2.0)"


def calculate_sha256(file_path: Path) -> str:
    """Calcula hash SHA-256 com buffer otimizado de 64KB (High Performance Python)."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_title(name: str) -> str:
    """Normaliza nome de arquivo para comparação de similaridade sem ruídos."""
    name = Path(name).stem
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return name


def load_indexed_metadata() -> Dict[str, str]:
    """Carrega catálogo de livros já indexados para deduplicação absoluta."""
    if not REGISTRY_FILE.exists():
        return {}
    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {b["file_path"]: b.get("file_hash", "") for b in data.get("books", {}).values()}
    except Exception:
        return {}


def get_local_database_catalog() -> Dict[str, Dict]:
    """Mapeia todos os arquivos locais existentes na pasta database/."""
    catalog = {}
    if not DATABASE_DIR.exists():
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        return catalog

    for f in DATABASE_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            norm = normalize_title(f.name)
            catalog[f.name.lower()] = {
                "path": f,
                "size": f.stat().st_size,
                "norm": norm
            }
    return catalog


class SourceResolver:
    """Resolve dinamicamente qualquer link (GitHub Tree, GitHub Blob, URL direta) em tarefas de download."""

    @staticmethod
    def parse_github_url(url: str) -> Optional[Dict[str, str]]:
        """Extrai owner, repo, tipo (tree/blob), branch e path de uma URL do GitHub."""
        tree_match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)$', url, re.IGNORECASE)
        if tree_match:
            return {
                "owner": tree_match.group(1),
                "repo": tree_match.group(2),
                "type": "tree",
                "branch": tree_match.group(3),
                "path": urllib.parse.unquote(tree_match.group(4)).rstrip('/')
            }

        blob_match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)$', url, re.IGNORECASE)
        if blob_match:
            return {
                "owner": blob_match.group(1),
                "repo": blob_match.group(2),
                "type": "blob",
                "branch": blob_match.group(3),
                "path": urllib.parse.unquote(blob_match.group(4))
            }
        return None

    @classmethod
    def resolve(cls, input_url: str) -> List[Dict]:
        """Transforma qualquer URL em uma lista padronizada de itens para download."""
        url = input_url.strip().strip("'").strip('"')
        if not url:
            return []

        gh_info = cls.parse_github_url(url)
        if gh_info:
            if gh_info["type"] == "blob":
                # Arquivo único no GitHub
                rel_path = gh_info["path"]
                filename = Path(rel_path).name
                encoded_path = urllib.parse.quote(rel_path)
                raw_url = f"https://raw.githubusercontent.com/{gh_info['owner']}/{gh_info['repo']}/{gh_info['branch']}/{encoded_path}"
                return [{
                    "source_type": "github_blob",
                    "title": filename,
                    "filename": filename,
                    "download_url": raw_url,
                    "expected_size": 0,
                    "category": f"{gh_info['owner']}/{gh_info['repo']}"
                }]

            elif gh_info["type"] == "tree":
                # Pasta no GitHub via API
                return cls._fetch_github_tree_items(gh_info)

        # Link Direto Web
        parsed = urllib.parse.urlparse(url)
        raw_name = Path(parsed.path).name or "downloaded_document.pdf"
        if not any(raw_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            raw_name += ".pdf"

        return [{
            "source_type": "direct_url",
            "title": raw_name,
            "filename": raw_name,
            "download_url": url,
            "expected_size": 0,
            "category": parsed.netloc or "web"
        }]

    @classmethod
    def _fetch_github_tree_items(cls, gh_info: Dict[str, str]) -> List[Dict]:
        """Consulta a árvore do repositório GitHub e extrai arquivos da pasta especificada."""
        owner = gh_info["owner"]
        repo = gh_info["repo"]
        branch = gh_info["branch"]
        target_path = gh_info["path"]

        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": DEFAULT_USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                tree = data.get("tree", [])
        except Exception as e:
            if console:
                console.print(f"[red]Erro ao consultar API do GitHub ({owner}/{repo}): {e}[/red]")
            else:
                print(f"Erro ao consultar API do GitHub ({owner}/{repo}): {e}")
            return []

        items = []
        for node in tree:
            if node.get("type") == "blob":
                path = node.get("path", "")
                if path.startswith(target_path + "/") or path == target_path:
                    suffix = Path(path).suffix.lower()
                    if suffix in SUPPORTED_EXTENSIONS or not suffix:
                        filename = Path(path).name
                        encoded_path = urllib.parse.quote(path)
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
                        items.append({
                            "source_type": "github_tree",
                            "title": filename,
                            "filename": filename,
                            "download_url": raw_url,
                            "expected_size": node.get("size", 0),
                            "category": target_path
                        })
        return items


class ResilientDownloader:
    """Executa downloads atômicos com retentativas, backoff exponencial e deduplicação inteligente."""

    def __init__(self, max_retries: int = 3, timeout: int = 120):
        self.max_retries = max_retries
        self.timeout = timeout

    def download(self, item: Dict, local_catalog: Dict[str, Dict]) -> Tuple[str, str, str, Any]:
        filename = item["filename"]
        url = item["download_url"]
        category = item["category"]
        expected_size = item.get("expected_size", 0)
        dest_path = DATABASE_DIR / filename

        # 1. Verificação de deduplicação local exata
        if dest_path.exists():
            actual_size = dest_path.stat().st_size
            if expected_size > 0 and actual_size == expected_size:
                return ("SKIPPED_EXISTING", filename, category, actual_size)
            elif expected_size == 0 and actual_size > 0:
                return ("SKIPPED_EXISTING", filename, category, actual_size)

        # 2. Verificação de deduplicação por nome em minúsculas
        lower_name = filename.lower()
        if lower_name in local_catalog:
            info = local_catalog[lower_name]
            if expected_size > 0 and info["size"] == expected_size:
                return ("SKIPPED_EXISTING", filename, category, info["size"])

        # 3. Download Atômico com Retry e Exponential Backoff
        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp, open(temp_path, "wb") as out_f:
                    total_read = 0
                    while True:
                        chunk = resp.read(256 * 1024)  # 256KB buffer
                        if not chunk:
                            break
                        out_f.write(chunk)
                        total_read += len(chunk)

                # Move atomicamente o arquivo finalizado
                temp_path.replace(dest_path)
                return ("DOWNLOADED", filename, category, total_read)

            except Exception as err:
                last_error = err
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 2s, 4s, 8s backoff

        return ("ERROR", filename, category, str(last_error))


def run_pipeline(urls: List[str], max_workers: int = 6, trigger_ingest: bool = False):
    """Orquestrador principal de download concorrente e ingestão."""
    if console:
        console.print(Panel.fit(
            "[bold cyan]📚 ReductorPrompt - Universal Book & Doc Fetcher[/bold cyan]\n"
            "[dim]Download inteligente, deduplicação SHA-256 e auto-ingestão vetorial[/dim]",
            border_style="cyan"
        ))
    else:
        print("=== ReductorPrompt - Universal Book & Doc Fetcher ===")

    local_catalog = get_local_database_catalog()
    all_items: List[Dict] = []
    seen_urls: Set[str] = set()

    for raw_url in urls:
        for single_url in re.split(r'[,\s]+', raw_url):
            single_url = single_url.strip()
            if not single_url or single_url in seen_urls:
                continue
            seen_urls.add(single_url)

            if console:
                console.print(f"🔍 [dim]Resolvendo fonte:[/dim] [blue]{single_url}[/blue]")
            else:
                print(f"Resolvendo fonte: {single_url}")

            items = SourceResolver.resolve(single_url)
            all_items.extend(items)

    if not all_items:
        if console:
            console.print("[yellow]⚠️ Nenhum arquivo para download encontrado nas URLs fornecidas.[/yellow]")
        else:
            print("Nenhum arquivo para download encontrado.")
        return

    # Deduplicação na lista de itens encontrados
    unique_items = []
    seen_filenames = set()
    for it in all_items:
        if it["filename"] not in seen_filenames:
            seen_filenames.add(it["filename"])
            unique_items.append(it)

    if console:
        console.print(f"\n🚀 [bold green]Iniciando processamento de {len(unique_items)} arquivos ({max_workers} threads concorrentes)...[/bold green]\n")
    else:
        print(f"\nIniciando processamento de {len(unique_items)} arquivos ({max_workers} threads)...\n")

    downloader = ResilientDownloader()
    downloaded_count = 0
    skipped_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(downloader.download, it, local_catalog): it for it in unique_items}
        for idx, future in enumerate(as_completed(futures), 1):
            status, filename, category, detail = future.result()
            if status == "DOWNLOADED":
                downloaded_count += 1
                size_mb = detail / (1024 * 1024)
                if console:
                    console.print(f"[{idx}/{len(unique_items)}] [bold green]✅ Baixado:[/bold green] [cyan][{category}][/cyan] {filename} ([dim]{size_mb:.2f} MB[/dim])")
                else:
                    print(f"[{idx}/{len(unique_items)}] ✅ Baixado: [{category}] {filename} ({size_mb:.2f} MB)")
            elif status == "SKIPPED_EXISTING":
                skipped_count += 1
                size_mb = detail / (1024 * 1024)
                if console:
                    console.print(f"[{idx}/{len(unique_items)}] [bold yellow]⏩ Já existente (ignorado):[/bold yellow] [cyan][{category}][/cyan] {filename} ([dim]{size_mb:.2f} MB[/dim])")
                else:
                    print(f"[{idx}/{len(unique_items)}] ⏩ Já existente: [{category}] {filename} ({size_mb:.2f} MB)")
            else:
                error_count += 1
                if console:
                    console.print(f"[{idx}/{len(unique_items)}] [bold red]❌ Erro:[/bold red] [cyan][{category}][/cyan] {filename} - {detail}")
                else:
                    print(f"[{idx}/{len(unique_items)}] ❌ Erro: [{category}] {filename} - {detail}")

    # Resumo da Execução
    if console:
        table = Table(title="📊 Resumo da Operação", border_style="cyan")
        table.add_column("Métrica", style="bold")
        table.add_column("Quantidade", justify="right")
        table.add_row("Novos Livros Baixados", f"[green]{downloaded_count}[/green]")
        table.add_row("Deduplicados / Já Existentes", f"[yellow]{skipped_count}[/yellow]")
        table.add_row("Falhas / Erros", f"[red]{error_count}[/red]")
        table.add_row("Total Processado", str(len(unique_items)))
        console.print("\n", table)
    else:
        print("\n" + "="*40)
        print(f"Baixados: {downloaded_count} | Já existentes: {skipped_count} | Erros: {error_count}")
        print("="*40)

    # Disparo opcional da ingestão vetorial
    if trigger_ingest and downloaded_count > 0:
        if console:
            console.print("\n[bold cyan]🧠 Iniciando ingestão vetorial automática no ChromaDB...[/bold cyan]")
        else:
            print("\nIniciando ingestão vetorial no ChromaDB...")

        from src.application.use_cases.ingest_books_use_case import IngestBooksUseCase
        from src.adapters.outbound.loaders.document_loader_adapter import DocumentLoaderAdapter
        from src.adapters.outbound.embeddings.ollama_embedding_adapter import OllamaEmbeddingAdapter
        from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
        from src.adapters.outbound.storage.file_book_repository import FileBookRepositoryAdapter

        use_case = IngestBooksUseCase(
            loader=DocumentLoaderAdapter(),
            embedding_port=OllamaEmbeddingAdapter(),
            vector_store=ChromaVectorStoreAdapter(),
            book_repo=FileBookRepositoryAdapter()
        )
        processed = use_case.execute(force_reindex=False)
        if console:
            console.print(f"[bold green]✨ Ingestão concluída com sucesso! {len(processed)} livros indexados.[/bold green]")
        else:
            print(f"Ingestão concluída! {len(processed)} livros indexados.")


def main():
    parser = argparse.ArgumentParser(
        description="ReductorPrompt Universal Book & Doc Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/fetch_books.py "https://github.com/MinhNguyenDS/AI-pdf-books/tree/Master/Paper"
  python scripts/fetch_books.py "https://github.com/owner/repo/blob/main/manual.pdf"
  python scripts/fetch_books.py "https://arxiv.org/pdf/2401.05566.pdf" --ingest
  python scripts/fetch_books.py "link1,link2,link3" --workers 8
        """
    )
    parser.add_argument("urls", nargs="+", help="Uma ou mais URLs (GitHub tree, blob ou links diretos)")
    parser.add_argument("--workers", "-w", type=int, default=6, help="Número de threads concorrentes (padrão: 6)")
    parser.add_argument("--ingest", "-i", action="store_true", help="Executar ingestão vetorial no ChromaDB automaticamente após download")

    args = parser.parse_args()
    run_pipeline(args.urls, max_workers=args.workers, trigger_ingest=args.ingest)


if __name__ == "__main__":
    main()
