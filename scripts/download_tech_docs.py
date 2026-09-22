#!/usr/bin/env python3
"""
Baixa e compila documentações Markdown de Elasticsearch, Redis e Triton
para o banco de dados do ReductorPrompt.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReductorPrompt/1.0"
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"


def fetch_github_tree(owner: str, repo: str, branch: str) -> List[Dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("tree", [])


def fetch_file_content(owner: str, repo: str, branch: str, path: str) -> Tuple[str, str]:
    encoded = urllib.parse.quote(path)
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            return path, content
    except Exception as e:
        return path, f"<!-- Erro ao baixar {path}: {e} -->"


def compile_topic_manual(
    title: str,
    output_filename: str,
    owner: str,
    repo: str,
    branch: str,
    path_filter_fn,
    max_files: int = 150
) -> Path:
    print(f"📦 Compilando: {title} ({owner}/{repo})...")
    tree = fetch_github_tree(owner, repo, branch)
    
    selected_paths = [
        item["path"] for item in tree
        if item.get("type") == "blob"
        and item["path"].endswith((".md", ".markdown"))
        and path_filter_fn(item["path"])
    ]
    
    # Ordena para consistência e limita para evitar sobrecarga excessiva
    selected_paths = sorted(selected_paths)[:max_files]
    print(f"  -> {len(selected_paths)} arquivos markdown selecionados.")
    
    contents = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_file_content, owner, repo, branch, p): p
            for p in selected_paths
        }
        for future in as_completed(futures):
            p, text = future.result()
            contents[p] = text
            
    out_path = DATABASE_DIR / output_filename
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"# {title}\n\n")
        out.write(f"> Compilação oficial de documentação extraída de `{owner}/{repo}` (branch `{branch}`).\n\n")
        
        for p in selected_paths:
            text = contents.get(p, "")
            if not text.strip():
                continue
            section_name = Path(p).stem.replace("-", " ").replace("_", " ").title()
            out.write(f"\n\n---\n\n## Seção: {section_name}\n")
            out.write(f"*Fonte: `{p}`*\n\n")
            out.write(text.strip())
            out.write("\n")
            
    print(f"✅ Salvo: {out_path.name} ({out_path.stat().st_size / 1024:.1f} KB)")
    return out_path


def main():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    
    topics = [
        # Elasticsearch
        (
            "Elasticsearch Core Architecture and Engine",
            "Elasticsearch_Core_Architecture_and_Engine.md",
            "elastic", "elasticsearch", "main",
            lambda p: p.startswith("docs/reference/elasticsearch") or p in ["docs/README.md", "docs/AGENTS.md"]
        ),
        (
            "Elasticsearch Query DSL and Search Guide",
            "Elasticsearch_Query_DSL_and_Search_Guide.md",
            "elastic", "elasticsearch", "main",
            lambda p: p.startswith("docs/reference/query-languages") or p.startswith("docs/reference/aggregations")
        ),
        (
            "Elasticsearch Text Analysis Mapping and Plugins",
            "Elasticsearch_Text_Analysis_Mapping_and_Plugins.md",
            "elastic", "elasticsearch", "main",
            lambda p: p.startswith("docs/reference/text-analysis") or p.startswith("docs/extend") or p.startswith("docs/reference/ingest-processor")
        ),
        # Redis
        (
            "Redis Core Architecture and Data Types",
            "Redis_Core_Architecture_and_Data_Types.md",
            "redis", "docs", "main",
            lambda p: p.startswith("content/develop/data-types") or p.startswith("content/develop/use-cases") or p.startswith("content/develop/reference")
        ),
        (
            "Redis AI Vector Search and Semantic Caching",
            "Redis_AI_Vector_Search_and_Semantic_Caching.md",
            "redis", "docs", "main",
            lambda p: p.startswith("content/develop/ai")
        ),
        (
            "Redis Operations Clustering and Kubernetes",
            "Redis_Operations_Clustering_and_Kubernetes.md",
            "redis", "docs", "main",
            lambda p: p.startswith("content/operate/oss_and_stack") or p.startswith("content/operate/rc") or p.startswith("content/operate/kubernetes")
        ),
        # Triton
        (
            "Triton Inference Server Architecture and User Guide",
            "Triton_Inference_Server_Architecture_and_Guide.md",
            "triton-inference-server", "server", "main",
            lambda p: p.startswith("docs/")
        ),
        (
            "Triton Conceptual Guides and Optimization Tutorials",
            "Triton_Conceptual_Guides_and_Optimization_Tutorials.md",
            "triton-inference-server", "tutorials", "main",
            lambda p: p.startswith("Conceptual_Guide/") or p.startswith("Deployment/")
        ),
        (
            "Triton GPU Language Compiler and Kernel Programming",
            "Triton_GPU_Language_Compiler_and_Programming.md",
            "triton-lang", "triton", "main",
            lambda p: p.startswith("docs/") or p.startswith("examples/")
        ),
    ]

    print("🚀 Iniciando download e compilação das documentações técnicas...")
    for title, filename, owner, repo, branch, fn in topics:
        try:
            compile_topic_manual(title, filename, owner, repo, branch, fn)
        except Exception as e:
            print(f"❌ Falha ao processar {title}: {e}")

    print("\n✨ Todos os manuais markdown foram gerados em database/!")


if __name__ == "__main__":
    main()
