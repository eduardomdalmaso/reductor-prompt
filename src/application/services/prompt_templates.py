from typing import Any, List, Optional, Tuple
from src.domain.entities.book import CompressedContext


def format_empirical_evidence(episodes: List[Any]) -> str:
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
    query: str,
    compressed_context: CompressedContext,
    deep_reasoning: bool = False,
    empirical_context: Optional[str] = None,
) -> Tuple[str, str]:
    """Gera o System Instruction e o User Prompt com suporte a recusa econômica e síntese bilateral."""
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
            "Cite os livros e páginas utilizados. Nunca invente, complete ou presuma URLs/links; "
            "só inclua links presentes literalmente no CONTEXTO. "
            "Se o contexto não contiver a resposta, recuse em 1 ou 2 frases curtas."
        )

    context_blocks = [f"=== FUNDAMENTAÇÃO TEÓRICA (Livros & Manuais) ===\n{compressed_context.raw_context_text}"]
    if empirical_context:
        context_blocks.append(empirical_context)
        system_instruction += (
            "\n\nATENÇÃO - SÍNTESE BILATERAL DE ENGENHARIA:\n"
            "O contexto contém tanto FUNDAMENTAÇÃO TEÓRICA (livros) quanto EVIDÊNCIAS EMPÍRICAS (benchmarks reais medidos em projetos como HydraStream). "
            "Confronte explicitamente a teoria com a prática: aponte se as medições confirmam, refutam ou impõem limites às recomendações dos livros."
        )

    full_context = "\n\n".join(context_blocks)
    user_prompt = (
        f"CONTEXTO TÉCNICO DISPONÍVEL:\n{full_context}\n\n"
        f"PERGUNTA DO USUÁRIO:\n{query}\n\nRESPOSTA ESTRUTURADA:"
    )
    return system_instruction, user_prompt


def build_cross_analysis_prompt(
    project_description: str,
    compressed_context: CompressedContext,
    focus_topic: str = None,
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
        f"DESCRIÇÃO DO MEU PROJETO:\n{project_description}\n\n{topic_instruction}"
        f"CONCEITOS E PRÁTICAS EXTRAÍDAS DOS LIVROS DE REFERÊNCIA:\n{compressed_context.raw_context_text}\n\n"
        f"ANÁLISE ESTRATÉGICA CRUZADA:"
    )
    return system_instruction, user_prompt
