from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequestDTO(BaseModel):
    query: str = Field(..., description="Pergunta do usuário a ser respondida com base nos livros")
    book_filter: Optional[str] = Field(None, description="Nome ou parte do nome do livro para filtrar")
    max_tokens: int = Field(default=1500, description="Limite máximo de tokens de contexto")
    only_context: bool = Field(default=False, description="Se True, retorna apenas o contexto sem chamar o LLM")
    llm_provider: Optional[str] = Field(None, description="Provedor de LLM ('gemini' ou 'ollama')")


class QueryResponseDTO(BaseModel):
    query: str
    response: str
    sources: List[Dict[str, Any]]
    tokens_used: int
    tokens_saved: int
    reduction_percentage: float
    llm_provider: str


class AnalyzeProjectRequestDTO(BaseModel):
    project_description: str = Field(..., description="Descrição detalhada da arquitetura ou código do seu projeto")
    book_filter: Optional[str] = Field(None, description="Nome do livro ou tema de referência")
    focus_topic: Optional[str] = Field(None, description="Foco específico (ex: 'latência', 'modelagem', 'gargalos')")
    max_tokens: int = Field(default=2000, description="Limite de tokens para o contexto recuperado")
    llm_provider: Optional[str] = Field(None, description="Provedor de LLM ('gemini' ou 'ollama')")


class AnalyzeProjectResponseDTO(BaseModel):
    project_summary: str
    book_title: str
    analysis: str
    sources: List[Dict[str, Any]]
    tokens_used: int
    tokens_saved: int
    reduction_percentage: float
