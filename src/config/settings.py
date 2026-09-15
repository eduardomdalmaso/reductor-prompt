import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configurações centralizadas da aplicação."""
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # LLM Settings
    LLM_PROVIDER: str = Field(default="gemini", description="'gemini' ou 'ollama'")
    GEMINI_API_KEY: str = Field(default="", description="Chave de API do Google Gemini")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Nome do modelo Gemini")
    
    # Ollama Settings
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="URL base do Ollama")
    OLLAMA_LLM_MODEL: str = Field(default="qwen2.5-coder:32b", description="Modelo LLM no Ollama")
    OLLAMA_EMBED_MODEL: str = Field(default="nomic-embed-text", description="Modelo de embeddings no Ollama")
    
    # Embeddings & Vector Store
    EMBEDDING_PROVIDER: str = Field(default="ollama", description="'ollama' ou 'chroma_default'")
    CHROMA_MODE: str = Field(default="http", description="'http' (via Podman/Docker) ou 'local' (embutido)")
    CHROMA_HOST: str = Field(default="127.0.0.1", description="Host do ChromaDB no Podman")
    CHROMA_PORT: int = Field(default=8001, description="Porta do ChromaDB no Podman")

    
    # Diretórios
    DATABASE_DIR: str = Field(default="./database", description="Diretório onde ficam os livros")
    STORAGE_DIR: str = Field(default="./storage", description="Diretório de armazenamento persistente")
    CHROMA_PERSIST_DIR: str = Field(default="./storage/chroma", description="Diretório do banco vetorial ChromaDB local")
    
    # Chunking & Token Optimization
    CHUNK_SIZE: int = Field(default=600, description="Tamanho médio do chunk em caracteres/palavras")
    CHUNK_OVERLAP: int = Field(default=100, description="Overlap entre chunks consecutivos")
    DEFAULT_TOP_K: int = Field(default=4, description="Quantidade de trechos mais relevantes recuperados")
    DEFAULT_MAX_CONTEXT_TOKENS: int = Field(default=1500, description="Limite máximo de tokens de contexto")
    SIMILARITY_THRESHOLD: float = Field(default=0.25, description="Score mínimo de corte semântico")

    # Segurança & API
    API_SECURITY_KEY: Optional[str] = Field(default=None, description="Chave de segurança opcional para proteger a API REST. Se vazia, opera em modo local aberto.")
    CORS_ALLOWED_ORIGINS: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000", description="Origens permitidas no CORS separadas por vírgula")

    def resolve_paths(self):
        """Garante que os diretórios necessários existam no disco."""
        Path(self.DATABASE_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)


# Instância global de configurações
settings = Settings()
settings.resolve_paths()
