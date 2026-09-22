import re
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.parse


class DocCompilerService:
    """Compila dinamicamente conjuntos de arquivos markdown de uma árvore em manuais canônicos."""

    @staticmethod
    def compile_markdown_tree(
        title: str,
        output_path: Path,
        items: List[Dict],
        max_workers: int = 10,
        user_agent: str = "Mozilla/5.0 (ReductorPrompt-Compiler/2.0)"
    ) -> Tuple[bool, int, str]:
        """Baixa em paralelo e compila uma lista de arquivos Markdown em um único manual estruturado."""
        if not items:
            return False, 0, "Nenhum arquivo para compilar."

        contents = {}
        
        def _fetch(item):
            url = item["download_url"]
            path = item["filename"]
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    text = resp.read().decode("utf-8", errors="ignore")
                    return path, text
            except Exception as e:
                return path, f"<!-- Erro ao baixar {path}: {e} -->"

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch, it): it for it in items}
            for future in as_completed(futures):
                p, text = future.result()
                contents[p] = text

        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(f"# {title}\n\n")
            out.write(f"> Manual Técnico Consolidado Dinamicamente pelo ReductorPrompt.\n")
            out.write(f"> Total de seções compiladas: {len(items)} arquivos de documentação.\n\n")

            for item in items:
                p = item["filename"]
                text = contents.get(p, "")
                if not text.strip():
                    continue
                section_title = Path(p).stem.replace("-", " ").replace("_", " ").title()
                out.write(f"\n\n---\n\n## Seção: {section_title}\n")
                out.write(f"*Fonte: `{p}`*\n\n")
                out.write(text.strip())
                out.write("\n")

        total_bytes = output_path.stat().st_size
        return True, total_bytes, f"Compilado com sucesso: {output_path.name} ({total_bytes / 1024:.1f} KB)"
