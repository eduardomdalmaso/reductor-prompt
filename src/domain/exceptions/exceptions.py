class DomainException(Exception):
    """Exceção base do domínio."""
    pass


class BookNotFoundException(DomainException):
    """Lançada quando um livro específico não é encontrado."""
    def __init__(self, book_identifier: str):
        super().__init__(f"Livro não encontrado no sistema: '{book_identifier}'")


class EmptyDatabaseException(DomainException):
    """Lançada quando a pasta database está vazia ou nenhum livro foi indexado."""
    def __init__(self, path: str):
        super().__init__(f"Nenhum livro encontrado na pasta '{path}'. Por favor, adicione arquivos PDF, EPUB, TXT ou MD.")


class IngestionException(DomainException):
    """Lançada quando ocorre um erro na leitura ou extração do livro."""
    def __init__(self, filename: str, reason: str):
        super().__init__(f"Falha ao processar o arquivo '{filename}': {reason}")


class EmbeddingException(DomainException):
    """Lançada quando a geração de embeddings falha."""
    def __init__(self, provider: str, reason: str):
        super().__init__(f"Falha no provedor de embeddings '{provider}': {reason}")


class LLMProviderException(DomainException):
    """Lançada quando a chamada ao modelo LLM falha."""
    def __init__(self, provider: str, reason: str):
        super().__init__(f"Falha na comunicação com o provedor LLM '{provider}': {reason}")
