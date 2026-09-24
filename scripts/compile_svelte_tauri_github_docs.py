#!/usr/bin/env python3
"""
Compilador Oficial de Documentação GitHub para Svelte, SvelteKit e Tauri v2.
Baixa e compila árvores completas do GitHub em manuais unificados em database/.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_DIR = Path(__file__).resolve().parent.parent / "database"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReductorPrompt-Compiler/2.0"

SOURCES = [
    {
        "title": "Svelte Official GitHub Documentation",
        "output_file": "Svelte_Official_GitHub_Documentation.md",
        "owner": "sveltejs",
        "repo": "svelte",
        "branch": "main",
        "path_prefix": "documentation/docs",
        "allowed_exts": (".md", ".mdx"),
    },
    {
        "title": "SvelteKit Official GitHub Documentation",
        "output_file": "SvelteKit_Official_GitHub_Documentation.md",
        "owner": "sveltejs",
        "repo": "kit",
        "branch": "main",
        "path_prefix": "documentation/docs",
        "allowed_exts": (".md", ".mdx"),
    },
    {
        "title": "Tauri v2 Official GitHub Documentation",
        "output_file": "Tauri_v2_Official_GitHub_Documentation.md",
        "owner": "tauri-apps",
        "repo": "tauri-docs",
        "branch": "v2",
        "path_prefix": "src/content/docs",
        "allowed_exts": (".md", ".mdx"),
    },
]


def clean_markdown_content(raw_text: str) -> str:
    """Remove frontmatter YAML do cabeçalho e normaliza quebras de linha."""
    if not raw_text:
        return ""
    # Remove frontmatter YAML --- ... ---
    cleaned = re.sub(r"^---\s*\n.*?\n---\s*\n", "", raw_text, flags=re.DOTALL)
    # Remove imports MDX comuns
    cleaned = re.sub(r"^import\s+.*?;\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def fetch_repo_tree(owner: str, repo: str, branch: str, prefix: str, exts: tuple) -> List[Dict]:
    """Obtém lista de arquivos markdown na árvore do GitHub."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Erro ao buscar árvore de {owner}/{repo}: {e}")
        return []

    files = []
    for item in data.get("tree", []):
        if item.get("type") == "blob":
            p = item.get("path", "")
            if p.startswith(prefix) and any(p.endswith(ext) for ext in exts):
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{urllib.parse.quote(p)}"
                files.append({"path": p, "download_url": raw_url, "size": item.get("size", 0)})

    # Ordena caminhos numericamente e alfabeticamente
    files.sort(key=lambda x: x["path"])
    return files


def download_single_file(item: Dict) -> tuple:
    """Baixa um arquivo individual e limpa formatação."""
    path = item["path"]
    url = item["download_url"]
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            cleaned = clean_markdown_content(raw)
            return path, cleaned
    except Exception as e:
        return path, f"<!-- Falha ao baixar {path}: {e} -->"


def compile_source(source: Dict, max_workers: int = 12):
    """Executa o download e compilação de uma fonte completa."""
    title = source["title"]
    out_file = DB_DIR / source["output_file"]
    owner = source["owner"]
    repo = source["repo"]
    branch = source["branch"]
    prefix = source["path_prefix"]
    exts = source["allowed_exts"]

    print(f"\n🔍 Buscando árvore de arquivos para '{title}' ({owner}/{repo})...")
    items = fetch_repo_tree(owner, repo, branch, prefix, exts)
    print(f"📄 Encontrados {len(items)} arquivos de documentação.")

    if not items:
        print(f"⚠️ Nenhum arquivo encontrado para {title}.")
        return

    print(f"🚀 Baixando {len(items)} arquivos em paralelo ({max_workers} threads)...")
    contents = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_single_file, it): it for it in items}
        for fut in as_completed(futures):
            p, text = fut.result()
            contents[p] = text

    DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out:
        out.write(f"# {title}\n\n")
        out.write(f"> Documentação Oficial consolidada diretamente do repositório `{owner}/{repo}` (branch `{branch}`).\n")
        out.write(f"> Total de seções compiladas: {len(items)} documentos.\n\n")

        for item in items:
            p = item["path"]
            text = contents.get(p, "")
            if not text.strip():
                continue
            section_name = p.replace(prefix, "").lstrip("/").replace(".mdx", "").replace(".md", "")
            readable_title = section_name.replace("/", " > ").replace("-", " ").replace("_", " ").title()
            out.write(f"\n\n---\n\n## Seção: {readable_title}\n")
            out.write(f"*Origem no GitHub: `{p}`*\n\n")
            out.write(text.strip())
            out.write("\n")

    size_mb = out_file.stat().st_size / (1024 * 1024)
    print(f"✅ Manual compilado com sucesso: {out_file.name} ({size_mb:.2f} MB)")


def main():
    print("📚 Iniciando Compilação Oficial de Documentações GitHub (Svelte + Tauri)...")
    for src in SOURCES:
        compile_source(src)
    print("\n🎉 Todas as documentações oficiais foram compiladas em database/!")


if __name__ == "__main__":
    main()
