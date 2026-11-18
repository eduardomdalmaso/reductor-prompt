import re
from typing import List, Dict, Any, Tuple, Optional
from src.domain.entities.book import ScoredChunk, CompressedContext
from src.application.services.chunking_service import ChunkingService
from src.config.settings import settings


class PromptCompressorService:
    """Serviço responsável por comprimir, filtrar e formatar o contexto para economia máxima de tokens com orçamento dinâmico e corte por curva de relevância (Elbow Method)."""

    def __init__(self, chunking_service: ChunkingService = None):
        self.chunking_service = chunking_service or ChunkingService()

    def classify_query_complexity(self, query: str) -> str:
        """
        Classifica a complexidade e escopo da consulta para orçamentação dinâmica de tokens:
        - 'factual': Dúvidas pontuais, comandos, sintaxe, definições diretas (400-800 tokens).
        - 'architectural': Análise cruzada, comparações estruturais, diagnósticos e trade-offs (3000-4500 tokens).
        - 'conceptual': Explicações de mecanismos, tutoriais, algoritmos e boas práticas (1200-2000 tokens).
        """
        q = query.lower().strip()
        word_count = len(q.split())

        # Padrões Arquiteturais / Análise Cruzada
        arch_patterns = [
            r"\banalys[e|is]\b", r"\barquitetura\b", r"\bcompar[e|ar|ando]\b", r"\btrade-?offs?\b",
            r"\bbenchmark\b", r"\bscalab\w+\b", r"\bescalabil\w+\b", r"\bmigra\w+\b",
            r"\bdistribu\w+\b", r"\bconcorr\w+\b", r"\bdiagn[oó]stico\b", r"\bpipeline\b"
        ]
        if any(re.search(pat, q) for pat in arch_patterns):
            return "architectural"

        # Padrões Conceituais / Explicativos Explícitos
        conceptual_patterns = [
            r"^como funciona\b", r"^como implementar\b", r"^como usar\b", r"^por que\b",
            r"^explique\b", r"^tutorial\b", r"^descreva\b", r"\bmecanismo\b", r"\balgoritmo\b"
        ]
        if any(re.search(pat, q) for pat in conceptual_patterns):
            return "conceptual"

        # Padrões Factuais / Pontuais
        factual_patterns = [
            r"^o que [eé]\b", r"^qual [eé]\b", r"^quais s[aã]o\b", r"\bcomando\b", r"\bsintaxe\b",
            r"\bflag\b", r"\bdefina\b", r"\bsignificado\b", r"\bvers[aã]o\b", r"\batalho\b"
        ]
        if any(re.search(pat, q) for pat in factual_patterns) or word_count <= 3:
            return "factual"

        return "conceptual"

    def determine_dynamic_budget(self, query: str, max_tokens_override: Optional[int] = None) -> int:
        """
        Calcula o orçamento de tokens dinamicamente para evitar ruído excessivo (Lost in the Middle)
        ou corte prematuro de respostas profundas.
        """
        if max_tokens_override is not None and max_tokens_override != settings.DEFAULT_MAX_CONTEXT_TOKENS:
            return max_tokens_override

        if not getattr(settings, "DYNAMIC_TOKEN_BUDGET_ENABLED", True):
            return max_tokens_override or settings.DEFAULT_MAX_CONTEXT_TOKENS

        complexity = self.classify_query_complexity(query)
        if complexity == "factual":
            return getattr(settings, "DYNAMIC_MIN_FACTUAL_TOKENS", 800)
        elif complexity == "architectural":
            return getattr(settings, "DYNAMIC_MAX_ARCHITECTURAL_TOKENS", 4000)
        else:
            return getattr(settings, "DYNAMIC_MAX_CONCEPTUAL_TOKENS", 1800)

    def apply_elbow_cutoff(
        self,
        sorted_chunks: List[ScoredChunk],
        min_score: float,
        max_relative_drop: float = None,
        max_step_drop: float = None
    ) -> List[ScoredChunk]:
        """
        Aplica o método Elbow (curva de declínio de relevância) para descartar a cauda de ruído.
        Se um chunk tiver queda abrupta em relação ao pico ou ao anterior, corta os subsequentes.
        """
        if not sorted_chunks:
            return []

        rel_drop_threshold = max_relative_drop if max_relative_drop is not None else getattr(settings, "DYNAMIC_ELBOW_MAX_RELATIVE_DROP", 0.35)
        step_drop_threshold = max_step_drop if max_step_drop is not None else getattr(settings, "DYNAMIC_ELBOW_MAX_STEP_DROP", 0.22)

        top_score = sorted_chunks[0].score
        if top_score < min_score:
            return [sorted_chunks[0]]

        selected: List[ScoredChunk] = []
        prev_score = top_score

        for sc in sorted_chunks:
            # 1. Filtro absoluto mínimo
            if sc.score < min_score:
                break

            # 2. Queda relativa máxima em relação ao melhor chunk (ex: 35% de tolerância)
            relative_drop = (top_score - sc.score) / max(0.01, top_score)
            if relative_drop > rel_drop_threshold and len(selected) >= 1:
                break

            # 3. Queda brusca de degrau em relação ao chunk imediatamente anterior
            step_drop = prev_score - sc.score
            if step_drop > step_drop_threshold and len(selected) >= 1:
                break

            selected.append(sc)
            prev_score = sc.score

        return selected or [sorted_chunks[0]]

    _STRATEGY_PARAMS = {
        "conservative": (0.55, 0.35),
        "balanced": (0.45, 0.30),
        "aggressive": (0.35, 0.22),
    }

    def compress_and_format(
        self,
        query: str,
        scored_chunks: List[ScoredChunk],
        max_tokens: int = None,
        similarity_threshold: float = None,
        strategy: str = "balanced",
        max_cut_percent: Optional[float] = None
    ) -> CompressedContext:
        """Comprime e formata o contexto com orçamento adaptativo e estratégia configurável."""
        limit_tokens = self.determine_dynamic_budget(query, max_tokens)
        min_score = similarity_threshold or settings.SIMILARITY_THRESHOLD

        # 1. Ordena decrescente por score de relevância
        sorted_chunks = sorted(scored_chunks, key=lambda x: x.score, reverse=True)
        raw_retrieved_tokens = sum(
            sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)
            for sc in sorted_chunks
        )

        # 2. Aplica corte dinâmico por curva de relevância conforme estratégia
        rel_drop, step_drop = self._STRATEGY_PARAMS.get(strategy, self._STRATEGY_PARAMS["balanced"])
        if strategy == "aggressive" and max_cut_percent is None:
            relevant_chunks = self.apply_elbow_cutoff(sorted_chunks, min_score)
        else:
            relevant_chunks = self.apply_elbow_cutoff(
                sorted_chunks, min_score, max_relative_drop=rel_drop, max_step_drop=step_drop
            )

        # No modo conservative com limite explícito, garante que o corte não ultrapasse max_cut_percent
        if strategy == "conservative" and max_cut_percent is not None and sorted_chunks:
            min_keep_tokens = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
            kept_ids = {sc.chunk.id for sc in relevant_chunks}
            kept_raw = sum(
                sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)
                for sc in relevant_chunks
            )
            for sc in sorted_chunks:
                if kept_raw >= min_keep_tokens:
                    break
                if sc.chunk.id not in kept_ids:
                    relevant_chunks.append(sc)
                    kept_ids.add(sc.chunk.id)
                    kept_raw += sc.chunk.token_count if sc.chunk.token_count > 0 else self.chunking_service.count_tokens(sc.chunk.content)

        selected_chunks: List[ScoredChunk] = []
        current_tokens = 0
        selected_raw_tokens = 0
        sources_list: List[Dict[str, Any]] = []
        formatted_blocks: List[str] = []

        for sc in relevant_chunks:
            chunk = sc.chunk
            chunk_raw_tokens = chunk.token_count if chunk.token_count > 0 else self.chunking_service.count_tokens(chunk.content)

            # Formata o bloco de forma limpa e contextualizada
            loc_info = []
            if chunk.chapter:
                loc_info.append(chunk.chapter)
            if chunk.page_number and chunk.page_number > 0:
                loc_info.append(f"Pág {chunk.page_number}")
            loc_str = f" ({', '.join(loc_info)})" if loc_info else ""

            block_text = f"--- [Livro: {chunk.book_title}{loc_str} | Relevância: {sc.score:.2f}] ---\n{chunk.content.strip()}"
            block_tokens = self.chunking_service.count_tokens(block_text)

            if strategy == "conservative" and max_cut_percent is not None:
                min_keep_tokens = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
                if selected_chunks and selected_raw_tokens >= min_keep_tokens and current_tokens + block_tokens > limit_tokens:
                    break
            elif max_cut_percent is not None:
                target_keep = raw_retrieved_tokens * (1.0 - max_cut_percent / 100.0)
                if selected_chunks and (selected_raw_tokens + chunk_raw_tokens > target_keep or current_tokens + block_tokens > limit_tokens):
                    break
            elif current_tokens + block_tokens > limit_tokens and selected_chunks:
                # Protege a única evidência de um livro distinto antes de truncar no modo balanced
                seen_books = {s.chunk.book_title for s in selected_chunks}
                if strategy != "aggressive" and chunk.book_title not in seen_books:
                    pass
                else:
                    break

            selected_chunks.append(sc)
            current_tokens += block_tokens
            selected_raw_tokens += chunk_raw_tokens
            formatted_blocks.append(block_text)

            sources_list.append({
                "chunk_id": chunk.id,
                "book_id": chunk.book_id,
                "book_title": chunk.book_title,
                "chapter": chunk.chapter,
                "page": chunk.page_number,
                "page_start": chunk.page_number,
                "page_end": chunk.page_number,
                "char_start": 0,
                "char_end": len(chunk.content),
                "excerpt_preview": chunk.content.strip()[:200],
                "score": round(sc.score, 3),
                "tokens": chunk.token_count
            })

        final_context_str = "\n\n".join(formatted_blocks)
        total_compressed_tokens = self.chunking_service.count_tokens(final_context_str)

        saved_tokens = max(0, raw_retrieved_tokens - selected_raw_tokens)
        reduction_percentage = round((saved_tokens / raw_retrieved_tokens) * 100, 2) if raw_retrieved_tokens > 0 else 0.0

        return CompressedContext(
            query=query,
            chunks=selected_chunks,
            raw_context_text=final_context_str,
            total_tokens=total_compressed_tokens,
            original_estimated_tokens=raw_retrieved_tokens,
            token_reduction_percent=reduction_percentage,
            sources=sources_list
        )

    @staticmethod
    def verify_citation_grounding(
        response: str,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verifica se livros e páginas citados na resposta existem nas fontes recuperadas."""
        import re as _re

        if not response or not sources:
            return {"grounded_pages": 0, "cited_pages": 0, "ungrounded_pages": [], "grounding_ratio": 1.0}

        retrieved_pages = {s.get("page") for s in sources if s.get("page") is not None}
        cited_pages = [int(p) for p in _re.findall(r"(?:P[áa]g\.?|Page|p\.)\s*(\d+)", response, flags=_re.IGNORECASE)]
        if not cited_pages:
            return {"grounded_pages": 0, "cited_pages": 0, "ungrounded_pages": [], "grounding_ratio": 1.0}

        grounded = [p for p in cited_pages if p in retrieved_pages]
        ungrounded = [p for p in cited_pages if p not in retrieved_pages]
        return {
            "grounded_pages": len(grounded),
            "cited_pages": len(cited_pages),
            "ungrounded_pages": sorted(set(ungrounded)),
            "grounding_ratio": round(len(grounded) / len(cited_pages), 4),
        }

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

    def format_empirical_evidence(self, episodes: List[Any]) -> str:
        """Formata evidências empíricas preservando commit, hardware e experimento."""
        if not episodes:
            return ""
        blocks = ["=== EVIDÊNCIAS EMPÍRICAS & BENCHMARKS DE EXECUÇÃO ==="]
        for ep in episodes:
            hw = ep.environment_context.get("hardware") or ep.environment_context.get("gpu") or "N/A"
            commit = f"#{ep.commit_hash[:7]}" if ep.commit_hash else "N/A"
            exp = ep.experiment_id or ep.id
            proj = ep.project_source or "Empirical"
            blocks.append(
                f"--- [Projeto: {proj} | Experimento: {exp} | Commit: {commit} | Hardware: {hw}] ---\n"
                f"{ep.response.strip()}"
            )
        return "\n\n".join(blocks)

    def build_qa_prompt(
        self, 
        query: str, 
        compressed_context: CompressedContext,
        deep_reasoning: bool = False,
        empirical_context: Optional[str] = None
    ) -> Tuple[str, str]:
        """Gera o System Instruction e o User Prompt com suporte a Chain-of-Thought e Síntese Bilateral."""
        if deep_reasoning:
            system_instruction = (
                "Você é um Arquiteto Principal de Software e Pesquisador de IA especialista. "
                "Sua missão é responder à dúvida do usuário com profundidade analítica, utilizando a metodologia "
                "de Chain-of-Thought (Cadeia de Raciocínio) e Auto-Reflexão baseada nas fontes fornecidas.\n\n"
                "REGRA DE RECUSA ECONÔMICA: Antes de escrever qualquer seção, verifique se o CONTEXTO TÉCNICO "
                "contém evidências suficientes para responder à pergunta. Se NÃO houver evidências suficientes, "
                "NÃO gere as 4 seções nem justificativas longas: responda apenas em 1 ou 2 frases curtas: "
                "'Não encontrei evidências suficientes nos documentos indexados para responder a esta pergunta.' "
                "(mencionando brevemente o tema dos trechos recuperados apenas se útil).\n\n"
                "Estrutura da Resposta (somente quando houver evidências suficientes):\n"
                "1. 🧠 Análise dos Fundamentos e Conceitos-Chave (Explicação teórica com base nas fontes)\n"
                "2. ⚙️ Aplicação Prática, Padrões e Arquitetura (Exemplos de código e trade-offs)\n"
                "3. 🔍 Auto-Validação e Integridade (Garantir que cada afirmação decorre estritamente dos trechos)\n"
                "4. 📖 Citações Exatas (Nome do Livro, Capítulo e Página)"
            )
        else:
            system_instruction = (
                "Você é um consultor especialista em engenharia de software. "
                "Responda de forma precisa e concisa estritamente com base no CONTEXTO fornecido. "
                "Cite os livros e páginas utilizados. Se o contexto não contiver a resposta, recuse em 1 ou 2 frases curtas."
            )

        context_blocks = [
            f"=== FUNDAMENTAÇÃO TEÓRICA (Livros & Manuais) ===\n{compressed_context.raw_context_text}"
        ]
        if empirical_context:
            context_blocks.append(empirical_context)
            system_instruction += (
                "\n\nATENÇÃO - SÍNTESE BILATERAL DE ENGENHARIA:\n"
                "O contexto contém tanto FUNDAMENTAÇÃO TEÓRICA (livros) quanto EVIDÊNCIAS EMPÍRICAS (benchmarks reais medidos em projetos como HydraStream). "
                "Confronte explicitamente a teoria com a prática: aponte se as medições confirmam, refutam ou impõem limites às recomendações dos livros."
            )

        full_context = "\n\n".join(context_blocks)
        user_prompt = (
            f"CONTEXTO TÉCNICO DISPONÍVEL:\n"
            f"{full_context}\n\n"
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
