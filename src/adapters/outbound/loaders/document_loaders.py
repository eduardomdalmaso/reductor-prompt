import os
import re
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from src.domain.ports.outbound import IDocumentLoaderPort
from src.domain.exceptions.exceptions import IngestionException


def sanitize_text(text: str) -> str:
    """Remove caracteres inválidos UTF-8, substitutos (surrogates) e caracteres de controle nulos."""
    if not text:
        return ""
    # Remove caracteres nulos e normaliza UTF-8 ignorando surrogates
    cleaned = text.replace('\x00', '')
    cleaned = re.sub(r'[\ud800-\udfff]', '', cleaned)
    return cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')


class TextAndMarkdownLoader(IDocumentLoaderPort):
    """Carregador para arquivos .txt e .md."""
    
    def can_load(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in ['.txt', '.md', '.markdown']

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Divide arquivos longos por seções/cabeçalhos se existirem
            sections = re.split(r'\n(?=#{1,3}\s+)', content)
            
            docs = []
            for idx, sec in enumerate(sections):
                cleaned = sec.strip()
                if cleaned:
                    docs.append({
                        "text": cleaned,
                        "page_number": idx + 1,
                        "chapter": f"Seção {idx + 1}"
                    })
            return docs
        except Exception as e:
            raise IngestionException(os.path.basename(file_path), str(e))


class PDFDocumentLoader(IDocumentLoaderPort):
    """Carregador de alta performance para arquivos PDF com PyMuPDF e fallback para pypdf."""
    
    def can_load(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == '.pdf'

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        # 1. Tenta extração de alta velocidade via PyMuPDF
        try:
            import pymupdf
            doc = pymupdf.open(file_path)
            docs = []
            for idx, page in enumerate(doc):
                text = page.get_text() or ""
                cleaned = sanitize_text(text)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if len(cleaned) > 20:
                    docs.append({
                        "text": cleaned,
                        "page_number": idx + 1,
                        "chapter": f"Página {idx + 1}"
                    })
            if docs:
                return docs
        except Exception:
            pass

        # 2. Fallback resiliente via pypdf
        try:
            reader = PdfReader(file_path)
            docs = []
            for idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    continue
                if text:
                    cleaned = sanitize_text(text)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    if len(cleaned) > 20:
                        docs.append({
                            "text": cleaned,
                            "page_number": idx + 1,
                            "chapter": f"Página {idx + 1}"
                        })
            return docs
        except Exception as e:
            raise IngestionException(os.path.basename(file_path), str(e))



class EPUBDocumentLoader(IDocumentLoaderPort):
    """Carregador para livros no formato EPUB."""
    
    def can_load(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == '.epub'

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
            docs = []
            chapter_count = 0
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text = soup.get_text()
                    cleaned = re.sub(r'\s+', ' ', text).strip()
                    
                    if len(cleaned) > 50:
                        chapter_count += 1
                        # Tenta extrair o primeiro título como nome do capítulo
                        title_tag = soup.find(['h1', 'h2', 'h3', 'title'])
                        chapter_title = title_tag.get_text().strip() if title_tag else f"Capítulo {chapter_count}"
                        
                        docs.append({
                            "text": cleaned,
                            "page_number": chapter_count,
                            "chapter": chapter_title
                        })
            return docs
        except Exception as e:
            raise IngestionException(os.path.basename(file_path), str(e))


class IPYNBDocumentLoader(IDocumentLoaderPort):
    """Carregador para Jupyter Notebooks (.ipynb) com extração de código, markdown, cálculos e saídas."""

    def can_load(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == '.ipynb'

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        import json
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)

            cells = data.get("cells", [])
            sections: List[Dict[str, Any]] = []
            current_section_title = "Introdução"
            current_buffer = []
            section_idx = 1

            for cell_num, cell in enumerate(cells, 1):
                cell_type = cell.get("cell_type", "")
                raw_source = cell.get("source", [])
                source_text = "".join(raw_source) if isinstance(raw_source, list) else str(raw_source)
                source_text = sanitize_text(source_text).strip()

                if not source_text:
                    continue

                if cell_type == "markdown":
                    # Detecta se é um título de seção
                    header_match = re.match(r'^(#{1,3})\s+(.*)', source_text)
                    if header_match and current_buffer:
                        # Despeja buffer anterior
                        sections.append({
                            "text": "\n\n".join(current_buffer),
                            "page_number": section_idx,
                            "chapter": current_section_title
                        })
                        section_idx += 1
                        current_buffer = []
                        current_section_title = header_match.group(2).strip()
                    current_buffer.append(source_text)

                elif cell_type == "code":
                    code_block = f"```python\n# Célula {cell_num} (Código):\n{source_text}\n```"
                    
                    # Captura saídas de texto/cálculos da célula se existirem
                    outputs = cell.get("outputs", [])
                    out_texts = []
                    for out in outputs:
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
                        formatted_out = "\n".join(out_texts)
                        code_block += f"\n```\n# Resultado / Cálculos da Execução:\n{formatted_out}\n```"

                    current_buffer.append(code_block)

            # Despeja o último buffer
            if current_buffer:
                sections.append({
                    "text": "\n\n".join(current_buffer),
                    "page_number": section_idx,
                    "chapter": current_section_title
                })

            return sections
        except Exception as e:
            raise IngestionException(os.path.basename(file_path), str(e))


class CompositeDocumentLoader(IDocumentLoaderPort):
    """Orquestrador que seleciona o loader apropriado com base no formato."""
    
    def __init__(self):
        self.loaders: List[IDocumentLoaderPort] = [
            PDFDocumentLoader(),
            EPUBDocumentLoader(),
            IPYNBDocumentLoader(),
            TextAndMarkdownLoader()
        ]

    def can_load(self, file_path: str) -> bool:
        return any(loader.can_load(file_path) for loader in self.loaders)

    def load(self, file_path: str) -> List[Dict[str, Any]]:
        for loader in self.loaders:
            if loader.can_load(file_path):
                return loader.load(file_path)
        raise IngestionException(
            os.path.basename(file_path), 
            f"Formato não suportado. Suporta: .pdf, .epub, .ipynb, .txt, .md"
        )
