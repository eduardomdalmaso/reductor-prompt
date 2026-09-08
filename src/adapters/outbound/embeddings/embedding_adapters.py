import logging
from typing import List
import httpx
import chromadb.utils.embedding_functions as ef

from src.domain.ports.outbound import IEmbeddingPort
from src.domain.exceptions.exceptions import EmbeddingException
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Connection pool para chamadas de embeddings locais
_EMBED_HTTP_CLIENT = httpx.Client(
    timeout=httpx.Timeout(120.0, connect=5.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
)


class OllamaEmbeddingAdapter(IEmbeddingPort):
    """Gera embeddings ultrarrápidos usando o serviço local do Ollama com connection pooling."""
    
    def __init__(self, base_url: str = None, model: str = None, keep_alive: str = "60m"):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_EMBED_MODEL
        self.keep_alive = keep_alive

    def embed_text(self, text: str) -> List[float]:
        # Tenta endpoint novo v2 do Ollama /api/embed
        url_v2 = f"{self.base_url}/api/embed"
        payload_v2 = {"model": self.model, "input": text, "keep_alive": self.keep_alive}
        try:
            resp_v2 = _EMBED_HTTP_CLIENT.post(url_v2, json=payload_v2)
            if resp_v2.status_code == 200:
                embeddings = resp_v2.json().get("embeddings", [])
                if embeddings:
                    return embeddings[0]
        except Exception:
            pass

        # Fallback para endpoint v1
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text, "keep_alive": self.keep_alive}
        try:
            resp = _EMBED_HTTP_CLIENT.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()["embedding"]
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            raise EmbeddingException("Ollama", f"Erro ao gerar embedding: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        url_v2 = f"{self.base_url}/api/embed"
        payload = {"model": self.model, "input": texts, "keep_alive": self.keep_alive}
        try:
            resp = _EMBED_HTTP_CLIENT.post(url_v2, json=payload)
            if resp.status_code == 200:
                embeddings = resp.json().get("embeddings", [])
                if len(embeddings) == len(texts):
                    return embeddings
        except Exception:
            pass

        return [self.embed_text(t) for t in texts]


class ChromaDefaultEmbeddingAdapter(IEmbeddingPort):
    """Gera embeddings localmente usando a função default do ChromaDB (ONNX all-MiniLM-L6-v2)."""
    
    def __init__(self):
        self._fn = ef.DefaultEmbeddingFunction()

    def embed_text(self, text: str) -> List[float]:
        try:
            embeddings = self._fn([text])
            return [float(x) for x in embeddings[0]]
        except Exception as e:
            raise EmbeddingException("ChromaDefault", str(e))

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            embeddings = self._fn(texts)
            return [[float(x) for x in emb] for emb in embeddings]
        except Exception as e:
            raise EmbeddingException("ChromaDefault", str(e))


class ResilientEmbeddingAdapter(IEmbeddingPort):
    """Adaptador inteligente com fallback automático (Ollama -> Chroma Default)."""
    
    def __init__(self):
        self.ollama_adapter = OllamaEmbeddingAdapter()
        self.default_adapter = ChromaDefaultEmbeddingAdapter()
        self._active_provider = "ollama" if settings.EMBEDDING_PROVIDER == "ollama" else "default"

    def embed_text(self, text: str) -> List[float]:
        if self._active_provider == "ollama":
            try:
                return self.ollama_adapter.embed_text(text)
            except Exception as e:
                logger.warning(f"Ollama embedding indisponível ({e}). Alternando para Chroma Default.")
                self._active_provider = "default"
                return self.default_adapter.embed_text(text)
        return self.default_adapter.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._active_provider == "ollama":
            try:
                return self.ollama_adapter.embed_batch(texts)
            except Exception as e:
                logger.warning(f"Ollama embedding batch falhou ({e}). Alternando para Chroma Default.")
                self._active_provider = "default"
                return self.default_adapter.embed_batch(texts)
        return self.default_adapter.embed_batch(texts)
