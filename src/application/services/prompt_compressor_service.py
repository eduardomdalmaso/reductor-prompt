from typing import List, Dict, Any, Tuple
from src.domain.entities.book import ScoredChunk, CompressedContext
from src.application.services.chunking_service import ChunkingService
from src.config.settings import settings


class PromptCompressorService:
    """Serviço responsável por comprimir, filtrar e formatar o contexto para economia máxima de tokens."""

    def __init__(self, chunking_service: ChunkingService = None):
        self.chunking_service = chunking_service or ChunkingService()

    def compress_and_format(
        self,
        query: str,
        scored_chunks: List[ScoredChunk],
        max_tokens: int = None,
        similarity_threshold: float = None
    ) -> CompressedContext:
        limit_tokens = max_tokens or settings.DEFAULT_MAX_CONTEXT_TOKENS
        min_score = similarity_threshold or settings.SIMILARITY_THRESHOLD

        # 1. Filtra por limiar mínimo de relevância
        relevant_chunks = [sc for sc in scored_chunks if sc.score >= min_score]
        
        # Se nenhum atingir o threshold mas houver resultados, pega o melhor
        if not relevant_chunks and scored_chunks:
            relevant_chunks = [scored_chunks[0]]

        # 2. Ordena decrescente por score de relevância
        relevant_chunks.sort(key=lambda x: x.score, reverse=True)

        selected_chunks: List[ScoredChunk] = []
        current_tokens = 0
        sources_list: List[Dict[str, Any]] = []
        formatted_blocks: List[str] = []

        for sc in relevant_chunks:
            chunk = sc.chunk
            
            # Formata o bloco de forma limpa e contextualizada
            loc_info = []
            if chunk.chapter:
                loc_info.append(chunk.chapter)
            if chunk.page_number and chunk.page_number > 0:
                loc_info.append(f"Pág {chunk.page_number}")
            loc_str = f" ({', '.join(loc_info)})" if loc_info else ""

            block_text = f"--- [Livro: {chunk.book_title}{loc_str} | Relevância: {sc.score:.2f}] ---\n{chunk.content.strip()}"
            block_tokens = self.chunking_service.count_tokens(block_text)

            if current_tokens + block_tokens > limit_tokens and selected_chunks:
                # Atingiu o limite do TokenBudget
                break

            selected_chunks.append(sc)
            current_tokens += block_tokens
            formatted_blocks.append(block_text)

            sources_list.append({
                "book_title": chunk.book_title,
                "chapter": chunk.chapter,
                "page": chunk.page_number,
                "score": round(sc.score, 3),
                "tokens": chunk.token_count
            })

        final_context_str = "\n\n".join(formatted_blocks)
        total_compressed_tokens = self.chunking_service.count_tokens(final_context_str)

        # Estimativa de tokens do livro completo original (média de 75.000 tokens por livro)
        estimated_original_tokens = max(75000, total_compressed_tokens * 40)
        saved_tokens = max(0, estimated_original_tokens - total_compressed_tokens)
        reduction_percentage = round((saved_tokens / estimated_original_tokens) * 100, 2)

        return CompressedContext(
            query=query,
            chunks=selected_chunks,
            raw_context_text=final_context_str,
            total_tokens=total_compressed_tokens,
            original_estimated_tokens=estimated_original_tokens,
            token_reduction_percent=reduction_percentage,
            sources=sources_list
        )

    @staticmethod
    def fuse_chunks_rrf(chunk_batches: List[List[ScoredChunk]], rrf_k: int = 60) -> List[ScoredChunk]:
        """
        Funde múltiplos conjuntos de resultados de busca vetorial usando Reciprocal Rank Fusion (RRF).
        Padrão ouro de Information Retrieval (IR) para combinar consultas multi-query.
        """
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, ScoredChunk] = {}

        for batch in chunk_batches:
            for rank, sc in enumerate(batch, 1):
                chunk_id = sc.chunk.id
                chunk_map[chunk_id] = sc
                # Fórmula RRF: score = sum(1 / (k + rank))
                score_increment = 1.0 / (rrf_k + rank)
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score_increment

        # Normaliza e atualiza os scores finais
        if not rrf_scores:
            return []

        max_rrf = max(rrf_scores.values())
        fused_chunks = []
        for chunk_id, total_rrf in sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True):
            orig_sc = chunk_map[chunk_id]
            normalized_score = min(1.0, max(orig_sc.score, total_rrf / max_rrf))
            fused_chunks.append(ScoredChunk(chunk=orig_sc.chunk, score=normalized_score))

        return fused_chunks

    def build_qa_prompt(
        self, 
        query: str, 
        compressed_context: CompressedContext,
        deep_reasoning: bool = False
    ) -> Tuple[str, str]:
        """Gera o System Instruction e o User Prompt com suporte a Chain-of-Thought e Self-Reflection."""
        if deep_reasoning:
            system_instruction = (
                "Você é um Arquiteto Principal de Software e Pesquisador de IA especialista. "
                "Sua missão é responder à dúvida do usuário com profundidade analítica, utilizando a metodologia "
                "de Chain-of-Thought (Cadeia de Raciocínio) e Auto-Reflexão baseada EXCLUSIVAMENTE nos livros fornecidos.\n\n"
                "Estrutura da Resposta:\n"
                "1. 🧠 Análise dos Fundamentos e Conceitos-Chave (Explicação teórica com base nas fontes)\n"
                "2. ⚙️ Aplicação Prática, Padrões e Arquitetura (Exemplos de código e trade-offs)\n"
                "3. 🔍 Auto-Validação e Integridade (Garantir que cada afirmação decorre estritamente dos trechos)\n"
                "4. 📖 Citações Exatas (Nome do Livro, Capítulo e Página)"
            )
        else:
            system_instruction = (
                "Você é um consultor especialista em engenharia de software, arquitetura e análise técnica. "
                "Responda à pergunta do usuário de forma precisa, concisa e altamente embasada no CONTEXTO DOS LIVROS fornecido. "
                "Diretrizes:\n"
                "1. Cite os livros e capítulos/páginas de onde as conclusões foram extraídas sempre que relevante.\n"
                "2. Seja direto e evite enrolação para economizar tokens.\n"
                "3. Se o contexto não contiver a resposta, informe educadamente o que foi possível encontrar nos livros indexados."
            )

        user_prompt = (
            f"CONTEXTO EXTRAÍDO DOS LIVROS:\n"
            f"{compressed_context.raw_context_text}\n\n"
            f"PERGUNTA DO USUÁRIO:\n"
            f"{query}\n\n"
            f"RESPOSTA ESTRUTURADA:"
        )

        return system_instruction, user_prompt

    def build_cross_analysis_prompt(
        self, 
        project_description: str, 
        compressed_context: CompressedContext,
        focus_topic: str = None
    ) -> Tuple[str, str]:
        """Gera o prompt especializado para Análise Cruzada de Projeto vs. Conceitos do Livro."""
        system_instruction = (
            "Você é um Arquiteto Principal de Software e Engenharia de Dados. "
            "Sua missão é realizar uma Análise Cruzada Estratégica entre o PROJETO informado pelo usuário "
            "e os CONCEITOS/MELHORES PRÁTICAS extraídos dos livros técnicos de referência.\n\n"
            "Estruture sua resposta estritamente nas seguintes seções:\n"
            "1. 🎯 Diagnóstico e Alinhamento Teórico (O que o livro diz sobre essa abordagem)\n"
            "2. 🚀 Oportunidades Concretas de Otimização (O que e como melhorar no projeto)\n"
            "3. ⚠️ Riscos Arquiteturais, Gargalos e Trade-offs (Alertas apontados na literatura)\n"
            "4. 📋 Plano de Ação Recomendado (Passos prioritários)\n"
            "5. 📖 Referências Citadas (Livros e capítulos referenciados)"
        )

        topic_instruction = f"Foco principal da análise: {focus_topic}\n" if focus_topic else ""

        user_prompt = (
            f"DESCRIÇÃO DO MEU PROJETO:\n"
            f"{project_description}\n\n"
            f"{topic_instruction}"
            f"CONCEITOS E PRÁTICAS EXTRAÍDAS DOS LIVROS DE REFERÊNCIA:\n"
            f"{compressed_context.raw_context_text}\n\n"
            f"ANÁLISE ESTRATÉGICA CRUZADA:"
        )

        return system_instruction, user_prompt
