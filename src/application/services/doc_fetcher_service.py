import os
import re
import json
import time
import socket
import ipaddress
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.settings import settings
from src.application.services.doc_compiler_service import DocCompilerService

SUPPORTED_EXTENSIONS = {'.pdf', '.epub', '.ipynb', '.txt', '.md', '.markdown'}
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReductorPrompt-Fetcher/2.0"


def is_safe_public_url(url: str) -> Tuple[bool, str]:
    """Valida se a URL é pública e segura contra SSRF."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False, f"Esquema de URL não permitido: '{parsed.scheme}'."
        hostname = parsed.hostname
        if not hostname or hostname.lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            return False, "Acesso a endereços de loopback/localhost é proibido por segurança."
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), proto=socket.IPPROTO_TCP)
        for entry in addr_info:
            ip = ipaddress.ip_address(entry[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Acesso a IP privado ({ip}) bloqueado (prevenção a SSRF)."
        return True, "OK"
    except Exception as e:
        return False, f"Erro ao validar URL: {e}"


class DocFetcherService:
    """Serviço Universal de Download e Compilação Dinâmica de Documentações e Livros."""

    def __init__(self, database_dir: Optional[Path] = None):
        self.database_dir = database_dir or Path(settings.DATABASE_DIR)
        self.database_dir.mkdir(parents=True, exist_ok=True)

    def resolve_source(self, url: str) -> Tuple[str, List[Dict]]:
        """Resolve uma URL em tipo de fonte ('github_tree', 'github_blob', 'direct_url') e lista de itens."""
        url = url.strip().strip("'").strip('"')
        if not url:
            return "empty", []

        # 1. GitHub Tree
        tree_match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.*))?$', url, re.IGNORECASE)
        if tree_match:
            owner, repo, branch, path = tree_match.group(1), tree_match.group(2), tree_match.group(3), (tree_match.group(4) or "").rstrip('/')
            return "github_tree", self._fetch_gh_tree(owner, repo, branch, path)

        # 2. GitHub Blob
        blob_match = re.match(r'^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)$', url, re.IGNORECASE)
        if blob_match:
            owner, repo, branch, path = blob_match.group(1), blob_match.group(2), blob_match.group(3), blob_match.group(4)
            filename = Path(path).name
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{urllib.parse.quote(path)}"
            return "github_blob", [{"filename": filename, "download_url": raw_url, "category": f"{owner}/{repo}"}]

        # 3. Direct URL
        parsed = urllib.parse.urlparse(url)
        raw_name = Path(parsed.path).name or "document.pdf"
        if not any(raw_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            raw_name += ".pdf"
        return "direct_url", [{"filename": raw_name, "download_url": url, "category": parsed.netloc or "web"}]

    def _fetch_gh_tree(self, owner: str, repo: str, branch: str, target_path: str) -> List[Dict]:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": DEFAULT_USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tree = data.get("tree", [])
        except Exception:
            return []

        items = []
        for node in tree:
            if node.get("type") == "blob":
                path = node.get("path", "")
                if not target_path or path.startswith(target_path + "/") or path == target_path:
                    if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{urllib.parse.quote(path)}"
                        items.append({
                            "filename": path,
                            "download_url": raw_url,
                            "category": f"{owner}/{repo}",
                            "size": node.get("size", 0)
                        })
        return items

    def process_url(self, url: str, compile_tree: bool = True, max_workers: int = 8) -> List[Tuple[str, str, str]]:
        """Processa a URL: baixa arquivos individuais ou compila uma árvore de docs em manual único."""
        safe, reason = is_safe_public_url(url)
        if not safe:
            return [("ERROR", url, f"Bloqueio SSRF: {reason}")]

        src_type, items = self.resolve_source(url)
        if not items:
            return [("EMPTY", url, "Nenhum documento encontrado na fonte")]

        results = []
        # Se for uma árvore do GitHub com múltiplos arquivos e compile_tree=True, compila em manual estruturado
        if src_type == "github_tree" and compile_tree and len(items) > 1:
            first_cat = items[0]["category"].replace("/", "_")
            parsed_title = Path(url).name or first_cat
            clean_title = f"{first_cat}_{parsed_title}".replace("-", "_")
            out_file = self.database_dir / f"{clean_title}_Manual.md"
            ok, bytes_count, msg = DocCompilerService.compile_markdown_tree(
                title=clean_title.replace("_", " ").title(),
                output_path=out_file,
                items=items,
                max_workers=max_workers
            )
            status = "COMPILED" if ok else "ERROR"
            results.append((status, out_file.name, msg))
        else:
            # Download arquivo por arquivo
            for it in items:
                dest = self.database_dir / Path(it["filename"]).name
                if dest.exists():
                    results.append(("SKIPPED_EXISTING", dest.name, "Já existe localmente"))
                    continue
                try:
                    req = urllib.request.Request(it["download_url"], headers={"User-Agent": DEFAULT_USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
                        f.write(resp.read())
                    results.append(("DOWNLOADED", dest.name, f"{dest.stat().st_size / 1024:.1f} KB"))
                except Exception as e:
                    results.append(("ERROR", dest.name, str(e)))
        return results
