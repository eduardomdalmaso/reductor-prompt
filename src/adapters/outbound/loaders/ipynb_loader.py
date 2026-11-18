import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from src.domain.exceptions.exceptions import IngestionException
from src.domain.ports.outbound import IDocumentLoaderPort


def _sanitize_ipynb_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\ud800-\udfff]", "", cleaned)
    return cleaned.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


class IPYNBDocumentLoader(IDocumentLoaderPort):
    """Carregador para Jupyter Notebooks (.ipynb) com extração de código, markdown e saídas."""

    def can_load(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == ".ipynb"

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            cells = data.get("cells", [])
            sections: List[Dict[str, Any]] = []
            current_section_title = "Introdução"
            current_buffer: List[str] = []
            section_idx = 1

            for cell_num, cell in enumerate(cells, 1):
                cell_type = cell.get("cell_type", "")
                raw_source = cell.get("source", [])
                source_text = "".join(raw_source) if isinstance(raw_source, list) else str(raw_source)
                source_text = _sanitize_ipynb_text(source_text).strip()
                if not source_text:
                    continue

                if cell_type == "markdown":
                    header_match = re.match(r"^(#{1,3})\s+(.*)", source_text)
                    if header_match and current_buffer:
                        sections.append({
                            "text": "\n\n".join(current_buffer),
                            "page_number": section_idx,
                            "chapter": current_section_title,
                        })
                        section_idx += 1
                        current_buffer = []
                        current_section_title = header_match.group(2).strip()
                    current_buffer.append(source_text)

                elif cell_type == "code":
                    code_block = f"```python\n# Célula {cell_num} (Código):\n{source_text}\n```"
                    out_texts = []
                    for out in cell.get("outputs", []):
                        if out.get("output_type") == "stream":
                            st_text = "".join(out.get("text", []))
                            if st_text.strip():
                                out_texts.append(st_text.strip())
                        elif out.get("output_type") in ("execute_result", "display_data"):
                            data_dict = out.get("data", {})
                            if "text/plain" in data_dict:
                                res_text = "".join(data_dict["text/plain"])
                                if res_text.strip():
                                    out_texts.append(res_text.strip())
                    if out_texts:
                        code_block += f"\n```\n# Resultado / Cálculos da Execução:\n{chr(10).join(out_texts)}\n```"
                    current_buffer.append(code_block)

            if current_buffer:
                sections.append({
                    "text": "\n\n".join(current_buffer),
                    "page_number": section_idx,
                    "chapter": current_section_title,
                })
            return sections
        except Exception as e:
            raise IngestionException(os.path.basename(file_path), str(e))
