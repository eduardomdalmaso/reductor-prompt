import re
import uuid
from typing import List, Dict, Any, Optional
try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODER = None

from src.domain.entities.book import BookChunk
from src.config.settings import settings


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace('\x00', '')
    cleaned = re.sub(r'[\ud800-\udfff]', '', cleaned)
    return cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')



class ChunkingService:
    """Serviço de divisão semântica inteligente de textos em blocos com metadados."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    @staticmethod
    def count_tokens(text: str) -> int:
        """Conta ou estima com precisão o número de tokens do texto."""
        if _ENCODER:
            try:
                return len(_ENCODER.encode(text, disallowed_special=()))
            except Exception:
                pass
        # Estimativa aproximada (1 token ~= 4 caracteres ou 0.75 palavras)
        return int(len(text.split()) * 1.3)

    def split_raw_documents(
        self, 
        raw_docs: List[Dict[str, Any]], 
        book_id: str, 
        book_title: str
    ) -> List[BookChunk]:
        """Divide uma lista de seções/páginas brutas em chunks semânticos."""
        chunks: List[BookChunk] = []
        global_chunk_idx = 0

        for doc in raw_docs:
            text = sanitize_text(doc.get("text", "")).strip()
            page_num = doc.get("page_number")
            chapter = doc.get("chapter")


            if not text:
                continue

            # Se o texto da página/seção for menor ou igual ao chunk_size, cria um chunk direto
            tokens = self.count_tokens(text)
            if tokens <= self.chunk_size:
                global_chunk_idx += 1
                chunk = BookChunk(
                    id=f"{book_id}_{global_chunk_idx}_{uuid.uuid4().hex[:6]}",
                    book_id=book_id,
                    book_title=book_title,
                    chunk_index=global_chunk_idx,
                    content=text,
                    token_count=tokens,
                    page_number=page_num,
                    chapter=chapter,
                    metadata={"page": page_num, "chapter": chapter}
                )
                chunks.append(chunk)
            else:
                # Divide em parágrafos preservando coerência
                paragraphs = re.split(r'\n\s*\n', text)
                current_chunk_text = []
                current_tokens = 0

                for para in paragraphs:
                    p_clean = para.strip()
                    if not p_clean:
                        continue
                    p_tokens = self.count_tokens(p_clean)

                    if current_tokens + p_tokens > self.chunk_size and current_chunk_text:
                        # Salva o bloco acumulado
                        full_chunk_str = "\n\n".join(current_chunk_text)
                        global_chunk_idx += 1
                        chunks.append(BookChunk(
                            id=f"{book_id}_{global_chunk_idx}_{uuid.uuid4().hex[:6]}",
                            book_id=book_id,
                            book_title=book_title,
                            chunk_index=global_chunk_idx,
                            content=full_chunk_str,
                            token_count=self.count_tokens(full_chunk_str),
                            page_number=page_num,
                            chapter=chapter,
                            metadata={"page": page_num, "chapter": chapter}
                        ))
                        # Mantém pequeno overlap se houver múltiplos parágrafos
                        current_chunk_text = [current_chunk_text[-1]] if len(current_chunk_text) > 1 else []
                        current_tokens = self.count_tokens(current_chunk_text[0]) if current_chunk_text else 0

                    current_chunk_text.append(p_clean)
                    current_tokens += p_tokens

                if current_chunk_text:
                    full_chunk_str = "\n\n".join(current_chunk_text)
                    global_chunk_idx += 1
                    chunks.append(BookChunk(
                        id=f"{book_id}_{global_chunk_idx}_{uuid.uuid4().hex[:6]}",
                        book_id=book_id,
                        book_title=book_title,
                        chunk_index=global_chunk_idx,
                        content=full_chunk_str,
                        token_count=self.count_tokens(full_chunk_str),
                        page_number=page_num,
                        chapter=chapter,
                        metadata={"page": page_num, "chapter": chapter}
                    ))

        return chunks
