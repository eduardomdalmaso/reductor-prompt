import os
import logging
from typing import Optional
import httpx

from src.domain.ports.outbound import ILLMPort
from src.domain.exceptions.exceptions import LLMProviderException
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Shared HTTP connection pool for high-throughput persistent keep-alive
_HTTP_CLIENT = httpx.Client(
    timeout=httpx.Timeout(180.0, connect=10.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
)


class GeminiLLMAdapter(ILLMPort):
    """Adaptador para Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or settings.GEMINI_MODEL

    def generate_response(
        self, 
        system_instruction: str, 
        prompt: str, 
        temperature: float = 0.2
    ) -> str:
        if not self.api_key or self.api_key == "sua_chave_gemini_aqui":
            raise LLMProviderException(
                "Gemini", 
                "Chave GEMINI_API_KEY não configurada no arquivo .env. "
                "Adicione sua chave ou alterne para LLM_PROVIDER=ollama."
            )

        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except ImportError:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": temperature}
            }
            resp = _HTTP_CLIENT.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            raise LLMProviderException("Gemini", f"Erro na API REST do Gemini: {resp.text}")
        except Exception as e:
            raise LLMProviderException("Gemini", str(e))


class OllamaLLMAdapter(ILLMPort):
    """Adaptador de alta performance para modelos locais rodando no Ollama (RTX 5090)."""
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        model: Optional[str] = None,
        num_ctx: int = 4096,
        keep_alive: str = "60m"
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive

    def generate_response(
        self, 
        system_instruction: str, 
        prompt: str, 
        temperature: float = 0.1
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,  # Otimiza alocação de KV-Cache na VRAM
                "num_thread": 8,
            },
            "keep_alive": self.keep_alive,  # Mantém os pesos residentes na GPU RTX 5090
            "stream": False
        }
        
        try:
            resp = _HTTP_CLIENT.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
            else:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            raise LLMProviderException("Ollama", f"Erro na comunicação com Ollama: {str(e)}")


class MockLLMAdapter(ILLMPort):
    """Adaptador Mock para testes e benchmarks de Information Retrieval."""
    def generate_response(self, system_instruction: str, prompt: str, temperature: float = 0.1) -> str:
        return "[MOCK RESPONSE] Resposta baseada no contexto com sucesso."


class LLMFactory:
    """Factory para instanciar o provedor LLM configurado."""
    
    @staticmethod
    def create(provider: Optional[str] = None) -> ILLMPort:
        prov = (provider or settings.LLM_PROVIDER).lower()
        if prov == "ollama":
            return OllamaLLMAdapter()
        elif prov == "gemini":
            return GeminiLLMAdapter()
        elif prov == "mock":
            return MockLLMAdapter()
        else:
            logger.warning(f"Provedor desconhecido '{prov}'. Usando Gemini.")
            return GeminiLLMAdapter()
