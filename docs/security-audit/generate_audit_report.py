#!/usr/bin/env python3
"""
Script Gerador do Relatório de Auditoria de Segurança - ReductorPrompt
======================================================================
Gera um relatório profissional em PDF (A4) com gráficos vetoriais nativos,
tabelas detalhadas, resumo executivo e issues do GitHub prontas para uso.
"""

import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Group, Line, Wedge

# Paleta Oficial da Auditoria
COLOR_CRITICA = colors.HexColor("#B91C1C")
COLOR_ALTA = colors.HexColor("#EA580C")
COLOR_MEDIA = colors.HexColor("#D97706")
COLOR_BAIXA = colors.HexColor("#2563EB")
COLOR_FORTE = colors.HexColor("#059669")
COLOR_SLATE_900 = colors.HexColor("#0F172A")
COLOR_SLATE_700 = colors.HexColor("#334155")
COLOR_SLATE_100 = colors.HexColor("#F1F5F9")
COLOR_SLATE_50 = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#CBD5E1")

OUTPUT_PDF = Path(__file__).resolve().parent / "relatorio-auditoria-seguranca.pdf"


class NumberedCanvas(canvas.Canvas):
    """Adiciona cabeçalhos e rodapés elegantes com contagem total de páginas."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Não desenha cabeçalho/rodapé na capa
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_SLATE_700)
        
        # Cabeçalho
        self.drawString(54, 800, "RELATÓRIO DE AUDITORIA DE SEGURANÇA — REDUCTORPROMPT")
        self.setFont("Helvetica", 8)
        self.drawRightString(541, 800, "CONFIDENCIAL / DEFENSIVO")
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(54, 792, 541, 792)

        # Rodapé
        self.line(54, 45, 541, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_SLATE_700)
        self.drawString(54, 32, "ReductorPrompt v2.0 • Análise Estática de Segurança e Conformidade")
        self.drawRightString(541, 32, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def create_donut_chart():
    """Gera gráfico de rosca vetorial com contagem por severidade."""
    d = Drawing(220, 140)
    
    # Centro e raio
    cx, cy, r_out, r_in = 70, 70, 55, 32
    
    # Dados: Crítica: 0, Alta: 1 (20%), Média: 3 (60%), Baixa: 1 (20%)
    # Total = 5 achados
    # Angulos:
    # Alta (1/5 = 72 deg): 0 to 72
    # Média (3/5 = 216 deg): 72 to 288
    # Baixa (1/5 = 72 deg): 288 to 360
    
    # Alta
    d.add(Wedge(cx, cy, r_out, 0, 72, fillColor=COLOR_ALTA, strokeColor=colors.white, strokeWidth=1.5))
    # Média
    d.add(Wedge(cx, cy, r_out, 72, 288, fillColor=COLOR_MEDIA, strokeColor=colors.white, strokeWidth=1.5))
    # Baixa
    d.add(Wedge(cx, cy, r_out, 288, 360, fillColor=COLOR_BAIXA, strokeColor=colors.white, strokeWidth=1.5))
    
    # Círculo interno (efeito rosca)
    d.add(Circle(cx, cy, r_in, fillColor=colors.white, strokeColor=colors.white))
    
    # Texto Central
    d.add(String(cx - 8, cy + 3, "5", fontName="Helvetica-Bold", fontSize=16, fillColor=COLOR_SLATE_900))
    d.add(String(cx - 19, cy - 10, "Achados", fontName="Helvetica", fontSize=7, fillColor=COLOR_SLATE_700))
    
    # Legenda
    items = [
        ("Crítica (0)", COLOR_CRITICA),
        ("Alta (1)", COLOR_ALTA),
        ("Média (3)", COLOR_MEDIA),
        ("Baixa (1)", COLOR_BAIXA)
    ]
    
    ly = 105
    for label, col in items:
        d.add(Rect(140, ly, 10, 10, rx=2, ry=2, fillColor=col, strokeColor=None))
        d.add(String(155, ly + 2, label, fontName="Helvetica-Bold", fontSize=8, fillColor=COLOR_SLATE_900))
        ly -= 22
        
    return d


def create_bar_chart():
    """Gera gráfico de barras horizontal vetorial por categoria."""
    d = Drawing(260, 140)
    
    categories = [
        ("1. Banco / Isolamento", 1, COLOR_ALTA),
        ("2. Permissões Backend", 1, COLOR_MEDIA),
        ("3. IDOR / Exfiltração", 1, COLOR_MEDIA),
        ("4. Chaves / Defaults", 1, COLOR_BAIXA),
        ("5. SSRF / Inputs", 1, COLOR_MEDIA)
    ]
    
    by = 110
    max_w = 90
    for label, count, col in categories:
        # Label
        d.add(String(5, by + 3, label, fontName="Helvetica", fontSize=7.5, fillColor=COLOR_SLATE_900))
        # Fundo da barra
        d.add(Rect(130, by, max_w, 11, rx=3, ry=3, fillColor=COLOR_SLATE_100, strokeColor=None))
        # Barra de valor
        bar_w = (count / 1.0) * max_w
        d.add(Rect(130, by, bar_w, 11, rx=3, ry=3, fillColor=col, strokeColor=None))
        # Valor
        d.add(String(130 + bar_w + 6, by + 2, f"{count}", fontName="Helvetica-Bold", fontSize=7.5, fillColor=COLOR_SLATE_900))
        by -= 23
        
    return d


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_cover_title = ParagraphStyle(
        "CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=COLOR_SLATE_900,
        alignment=0
    )
    style_cover_subtitle = ParagraphStyle(
        "CoverSubtitle",
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=COLOR_SLATE_700,
        alignment=0
    )
    style_h1 = ParagraphStyle(
        "SectionH1",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=COLOR_SLATE_900,
        spaceAfter=10
    )
    style_h2 = ParagraphStyle(
        "SectionH2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=COLOR_SLATE_700,
        spaceBefore=8,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_SLATE_900,
        spaceAfter=6
    )
    style_body_bold = ParagraphStyle(
        "BodyBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=COLOR_SLATE_900
    )
    style_code = ParagraphStyle(
        "CodeBlock",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0284C7")
    )
    style_table_cell = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_SLATE_900
    )
    style_table_header = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # CAPA (Page 1)
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("🛡️ RELATÓRIO DE AUDITORIA DE SEGURANÇA", style_cover_title))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Projeto: <b>ReductorPrompt</b> — Análise de Vulnerabilidades, Isolamento e Conformidade", style_cover_subtitle))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=3, color=COLOR_ALTA, spaceAfter=20, spaceBefore=0))

    metadata_data = [
        [Paragraph("<b>Data da Auditoria:</b>", style_body), Paragraph("15 de Setembro de 2026", style_body)],
        [Paragraph("<b>Escopo Auditado:</b>", style_body), Paragraph("API REST (FastAPI), MCP Hub (FastMCP), Vector Store (ChromaDB), SQLite Telemetry, Frontend React & Scripts", style_body)],
        [Paragraph("<b>Versão do Sistema:</b>", style_body), Paragraph("ReductorPrompt v2.0.0", style_body)],
        [Paragraph("<b>Classificação:</b>", style_body), Paragraph("<font color='#B91C1C'><b>DOCUMENTO TÉCNICO DEFENSIVO</b></font>", style_body)],
    ]
    t_meta = Table(metadata_data, colWidths=[120, 360])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_SLATE_50),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Nota Metodológica & Mapeamento de Stack</b>", style_h2))
    methodology_text = (
        "Esta auditoria analisou estaticamente 100% dos manipuladores de rota, adaptadores de persistência, "
        "comunicação cliente-servidor e rotinas de download do <b>ReductorPrompt</b>. A stack detectada e as "
        "categorias mapeadas foram:<br/><br/>"
        "• <b>Stack Detectada:</b> Python 3.11+, FastAPI, ChromaDB (Vector Store), SQLite (Telemetry), FastMCP, React 18 / TypeScript / Vite.<br/>"
        "• <b>1. Banco Sem Tranca:</b> Mapeado para isolamento no ChromaDB e endpoints de busca/agregação sem filtro de tenant.<br/>"
        "• <b>2. Permissão no Navegador:</b> Mapeado para operações de controle de VRAM/hardware e ingestão sem verificação de privilégio no backend.<br/>"
        "• <b>3. IDOR:</b> Mapeado para deleção e exportação de logs e histórico SQLite sem autenticação de posse.<br/>"
        "• <b>4. Chaves Expostas:</b> Mapeado para passagem de API keys em URLs e CORS wildcard permissivo.<br/>"
        "• <b>5. Inputs Sem Tratamento / SSRF / XSS:</b> Mapeado para renderização de Markdown no React e downloads dinâmicos de URLs arbitrárias."
    )
    story.append(Paragraph(methodology_text, style_body))
    story.append(PageBreak())

    # =========================================================================
    # RESUMO EXECUTIVO (Page 2)
    # =========================================================================
    story.append(Paragraph("1. Resumo Executivo", style_h1))
    story.append(Paragraph(
        "A auditoria identificou um total de <b>5 achados acionáveis</b> e <b>4 pontos fortes arquiteturais</b>. "
        "O ReductorPrompt apresenta excelente higiene de código contra ataques comuns como <b>XSS</b> e <b>SQL Injection</b>. "
        "No entanto, por ter sido concebido inicialmente como uma ferramenta monousuário de uso local (desktop/localhost), "
        "o sistema opera com <b>ausência total de camadas de autenticação e autorização</b> em seus endpoints REST, "
        "o que representa risco significativo se exposto em rede local compartilhada, Docker bridge ou ambiente em nuvem.",
        style_body
    ))
    story.append(Spacer(1, 10))

    # Gráficos em Tabela Lado a Lado
    donut = create_donut_chart()
    bars = create_bar_chart()
    t_charts = Table([[donut, bars]], colWidths=[240, 245])
    t_charts.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), COLOR_SLATE_50),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_charts)
    story.append(Spacer(1, 15))

    # Tabela Resumo
    summary_table_data = [
        [Paragraph("<b>Severidade</b>", style_table_header), Paragraph("<b>Qtd</b>", style_table_header), Paragraph("<b>Impacto Principal</b>", style_table_header)],
        [Paragraph("<font color='#B91C1C'><b>CRÍTICA</b></font>", style_table_cell), Paragraph("<b>0</b>", style_table_cell), Paragraph("Nenhuma vulnerabilidade com exploração remota imediata de RCE sem autenticação.", style_table_cell)],
        [Paragraph("<font color='#EA580C'><b>ALTA</b></font>", style_table_cell), Paragraph("<b>1</b>", style_table_cell), Paragraph("Ausência de isolamento e autenticação na API REST & ChromaDB em rede aberta.", style_table_cell)],
        [Paragraph("<font color='#D97706'><b>MÉDIA</b></font>", style_table_cell), Paragraph("<b>3</b>", style_table_cell), Paragraph("SSRF no download de URLs; Ações de escrita/VRAM abertas; Exportação irrestrita de dados.", style_table_cell)],
        [Paragraph("<font color='#2563EB'><b>BAIXA</b></font>", style_table_cell), Paragraph("<b>1</b>", style_table_cell), Paragraph("API Key do Gemini transitando em query string no fallback HTTP; CORS wildcard.", style_table_cell)],
    ]
    t_sum = Table(summary_table_data, colWidths=[80, 40, 365])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SLATE_900),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_sum)
    story.append(PageBreak())

    # =========================================================================
    # PONTOS FORTES E PONTOS FRACOS (Page 3)
    # =========================================================================
    story.append(Paragraph("2. Pontos Fortes e Pontos Fracos", style_h1))
    
    story.append(Paragraph("<b>✅ Pontos Fortes Verificados (Proteções Ativas)</b>", style_h2))
    fortes_data = [
        [
            Paragraph("<font color='#059669'><b>Ponto Forte</b></font>", style_table_header),
            Paragraph("<font color='#059669'><b>Arquivo e Linhas</b></font>", style_table_header),
            Paragraph("<font color='#059669'><b>Evidência de Proteção</b></font>", style_table_header)
        ],
        [
            Paragraph("<b>Prevenção a XSS no Frontend</b>", style_table_cell),
            Paragraph("<code>web/src/.../MarkdownRenderer.tsx:20-80</code>", style_table_cell),
            Paragraph("Renderizador customizado que converte Markdown em nós nativos React (JSX). Não utiliza <code>dangerouslySetInnerHTML</code>, <code>innerHTML</code> nem <code>eval()</code>.", style_table_cell)
        ],
        [
            Paragraph("<b>Prevenção a SQL Injection</b>", style_table_cell),
            Paragraph("<code>src/.../system_telemetry_service.py:157,212</code>", style_table_cell),
            Paragraph("Todas as operações no banco relacional SQLite utilizam queries parametrizadas (<code>?</code>). Nenhuma concatenação direta de string com input do usuário.", style_table_cell)
        ],
        [
            Paragraph("<b>Higiene de Segredos em Git</b>", style_table_cell),
            Paragraph("<code>.gitignore:1-10</code><br/><code>src/config/settings.py:17</code>", style_table_cell),
            Paragraph("Arquivos <code>.env</code> são estritamente ignorados pelo Git. Chaves padrão utilizam strings vazias e bloqueiam execução se não preenchidas.", style_table_cell)
        ],
        [
            Paragraph("<b>Resiliência do Vector Store</b>", style_table_cell),
            Paragraph("<code>src/.../chroma_vector_store.py:28-39</code>", style_table_cell),
            Paragraph("Fallback automático e transparente do Podman HTTP para SQLite local persistente em caso de falha de conexão de rede.", style_table_cell)
        ]
    ]
    t_fortes = Table(fortes_data, colWidths=[110, 140, 235])
    t_fortes.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_FORTE),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_fortes)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>⚠️ Pontos Fracos e Riscos Centrais</b>", style_h2))
    fracos_text = (
        "• <b>Ausência de Autenticação/Autorização (Zero Trust):</b> A API REST não possui nenhum mecanismo de autenticação "
        "(como API Keys, JWT ou mTLS). Qualquer cliente na rede local tem acesso a comandos administrativos e aos dados do banco vetorial.<br/>"
        "• <b>Risco de SSRF em Downloads Dinâmicos:</b> A rota <code>/api/v1/fetch</code> aceita URLs arbitrárias e realiza requisições "
        "sem validação de destino (permitindo sondar endereços locais <code>127.0.0.1</code> e metadados de nuvem).<br/>"
        "• <b>CORS Wildcard com Credentials:</b> A configuração de CORS libera <code>*</code> com <code>allow_credentials=True</code>."
    )
    story.append(Paragraph(fracos_text, style_body))
    story.append(PageBreak())

    # =========================================================================
    # TABELA DE ACHADOS DETALHADOS (Page 4)
    # =========================================================================
    story.append(Paragraph("3. Tabela Detalhada de Achados de Segurança", style_h1))
    story.append(Paragraph("Relação completa de achados verificados diretamente no código-fonte, linha a linha:", style_body))
    story.append(Spacer(1, 8))

    findings_table_data = [
        [
            Paragraph("<b>Sev.</b>", style_table_header),
            Paragraph("<b>Categoria & Arquivo:Linha</b>", style_table_header),
            Paragraph("<b>Descrição da Falha & Impacto</b>", style_table_header)
        ],
        [
            Paragraph("<font color='#EA580C'><b>ALTA</b></font>", style_table_cell),
            Paragraph("<b>1. Banco Sem Tranca / Falta de Auth</b><br/><code>src/.../fastapi_app.py:85-125</code><br/><code>podman-compose.yml:1-13</code>", style_table_cell),
            Paragraph("Todos os endpoints REST e a porta 8001 do ChromaDB estão expostos sem autenticação nem particionamento por usuário/inquilino. Qualquer chamador de rede pode ler o acervo e disparar ingestão massiva.", style_table_cell)
        ],
        [
            Paragraph("<font color='#D97706'><b>MÉDIA</b></font>", style_table_cell),
            Paragraph("<b>2. Permissão Sem Validação Backend</b><br/><code>src/.../fastapi_app.py:298-320</code><br/><code>web/.../LLMControllerView.tsx:1-120</code>", style_table_cell),
            Paragraph("Ações privilegiadas de controle de GPU/VRAM (<code>/api/v1/llm/toggle</code>, <code>/api/v1/llm/unload</code>) e reconfiguração de provedor são executadas pelo backend sem checagem de privilégio de administrador.", style_table_cell)
        ],
        [
            Paragraph("<font color='#D97706'><b>MÉDIA</b></font>", style_table_cell),
            Paragraph("<b>3. IDOR / Exfiltração de Histórico</b><br/><code>src/.../fastapi_app.py:270-286</code><br/><code>src/.../chroma_vector_store.py:138</code>", style_table_cell),
            Paragraph("Endpoints <code>/api/v1/queries/export</code> e <code>/api/v1/logs</code> entregam todo o histórico de consultas e logs do SQLite a qualquer requisitante sem verificação de posse ou identificação.", style_table_cell)
        ],
        [
            Paragraph("<font color='#D97706'><b>MÉDIA</b></font>", style_table_cell),
            Paragraph("<b>4. SSRF em Fetch de Livros</b><br/><code>src/.../fastapi_app.py:128-145</code><br/><code>scripts/fetch_books.py:153-165,245</code>", style_table_cell),
            Paragraph("O endpoint <code>/api/v1/fetch</code> aceita URLs externas arbitrárias e dispara requisições HTTP GET sem validar endereços de rede privada (RFC 1918), permitindo varredura de portas internas e metadados de nuvem.", style_table_cell)
        ],
        [
            Paragraph("<font color='#2563EB'><b>BAIXA</b></font>", style_table_cell),
            Paragraph("<b>5. API Key em Query String & CORS</b><br/><code>src/.../llm_adapters.py:55</code><br/><code>src/.../fastapi_app.py:36</code>", style_table_cell),
            Paragraph("No fallback REST da API do Gemini, a <code>GEMINI_API_KEY</code> é transmitida como parâmetro de URL (<code>?key=...</code>) em vez de header HTTP (<code>x-goog-api-key</code>), podendo vazar em logs intermediários.", style_table_cell)
        ]
    ]

    t_findings = Table(findings_table_data, colWidths=[55, 175, 255])
    t_findings.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SLATE_900),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_findings)
    story.append(Spacer(1, 15))

    # =========================================================================
    # RECOMENDAÇÕES PRIORIZADAS (Page 5)
    # =========================================================================
    story.append(Paragraph("4. Plano de Recomendações Priorizadas", style_h1))
    
    recomms = [
        ("P1 (Imediato - Alta Prioridade)", "Implementação de Autenticação via API Key / Bearer Token", 
         "Adicionar middleware de segurança no FastAPI (<code>HTTPBearer</code> ou <code>APIKeyHeader</code>) protegendo todos os endpoints <code>/api/v1/*</code>. Em modo desktop/local, vincular o servidor estritamente a <code>127.0.0.1</code> e não a <code>0.0.0.0</code>."),
        
        ("P2 (Curto Prazo - Média Prioridade)", "Mitigação de SSRF no Download Dinâmico (/api/v1/fetch)", 
         "Validar URLs recebidas no <code>fetch_books.py</code>: permitir apenas esquemas <code>https://</code> e aplicar resolução de DNS para bloquear endereços IP privados (<code>127.0.0.1</code>, <code>10.0.0.0/8</code>, <code>192.168.0.0/16</code>, <code>169.254.169.254</code>)."),
        
        ("P3 (Curto Prazo - Média Prioridade)", "Restrição de Operações Administrativas & IDOR", 
         "Separar rotas de consulta (leitura) de rotas administrativas (escrita/GPU/exportação). Exigir chave de administração para endpoints como <code>/api/v1/llm/*</code> e <code>/api/v1/queries/export</code>."),
        
        ("P4 (Médio Prazo - Baixa Prioridade)", "Ajuste de Headers de API e CORS", 
         "Substituir o parâmetro de query string da API Gemini por cabeçalho <code>x-goog-api-key</code> e restringir o <code>allow_origins</code> do CORS para a URL específica do frontend.")
    ]
    
    for p_level, title, desc in recomms:
        story.append(Paragraph(f"<b>{p_level}: {title}</b>", style_h2))
        story.append(Paragraph(desc, style_body))
        story.append(Spacer(1, 4))
        
    story.append(PageBreak())

    # =========================================================================
    # ISSUES PARA O GITHUB (Page 6-8)
    # =========================================================================
    story.append(Paragraph("5. Issues Acionáveis para o GitHub", style_h1))
    story.append(Paragraph(
        "Copie e cole os blocos abaixo diretamente nas <b>Issues do repositório GitHub</b> para acompanhamento e correção:",
        style_body
    ))
    story.append(Spacer(1, 10))

    issues_text = [
        """--- ISSUE 1 ---
**Título:** [Segurança] Ausência de Autenticação e Isolamento nas Rotas da API REST e ChromaDB
**Labels:** security, priority-high, severity-high

### Descrição do Problema
A API FastAPI (`src/adapters/inbound/api/fastapi_app.py`) e a instância do ChromaDB (`podman-compose.yml`) operam sem nenhuma camada de autenticação (API Key, Bearer Token) ou isolamento de inquilino. Qualquer cliente com acesso à porta 8000/8001 pode consultar a base vetorial completa, listar livros e disparar processos pesados de ingestão.

### Evidência
- `src/adapters/inbound/api/fastapi_app.py:34-40` (CORS wildcard `allow_origins=["*"]`)
- `src/adapters/inbound/api/fastapi_app.py:85-125` (Rotas `/api/v1/books` e `/api/v1/ingest` sem dependência de segurança)
- `podman-compose.yml:1-13` (Porta 8001 exposta sem `CHROMA_SERVER_AUTH_CREDENTIALS`)

### Impacto
Exposição total de dados vetoriais, histórico de buscas e possibilidade de negação de serviço (DoS) por sobrecarga de ingestão em ambientes compartilhados.

### Sugestão de Correção
1. Adicionar middleware de autenticação baseado em `API_KEY` configurável via `.env`.
2. Vincular o FastAPI e o ChromaDB ao `127.0.0.1` por padrão no `podman-compose.yml` e no `uvicorn.run`.
3. Ativar autenticação básica por token no ChromaDB.

### Critérios de Aceite
- [ ] Todas as rotas `/api/v1/*` retornam HTTP 401 caso o cabeçalho `X-API-Key` não seja fornecido.
- [ ] O arquivo `podman-compose.yml` vincula a porta a `127.0.0.1:8001:8000`.
- [ ] A suíte de testes valida a rejeição de requisições não autorizadas.
--- FIM ISSUE 1 ---""",

        """--- ISSUE 2 ---
**Título:** [Segurança] Vulnerabilidade de Server-Side Request Forgery (SSRF) no Endpoint /api/v1/fetch
**Labels:** security, priority-medium, severity-medium

### Descrição do Problema
O endpoint `/api/v1/fetch` e a função `scripts/fetch_books.py:ResilientDownloader` recebem URLs fornecidas pelo usuário e realizam downloads HTTP GET usando `urllib.request.urlopen` sem validar o protocolo ou verificar se o IP de destino pertence a redes privadas/locais.

### Evidência
- `src/adapters/inbound/api/fastapi_app.py:128-145`
- `scripts/fetch_books.py:153-165, 245-250`
```python
req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
with urllib.request.urlopen(req, timeout=self.timeout) as resp:
```

### Impacto
Um atacante pode submeter URLs como `http://127.0.0.1:11434/api/tags` ou `http://169.254.169.254/latest/meta-data/` para mapear serviços internos locais, manipular o Ollama ou extrair credenciais de instâncias cloud.

### Sugestão de Correção
1. Validar que a URL utiliza estritamente o esquema `https://`.
2. Resolver o DNS do hostname antes da requisição e rejeitar endereços IP pertencentes a:
   - Loopback (`127.0.0.0/8`)
   - Redes Privadas (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   - Link-local / Cloud Metadata (`169.254.0.0/16`)

### Critérios de Aceite
- [ ] URLs com `http://` não seguro são rejeitadas com HTTP 400.
- [ ] URLs apontando para localhost ou IPs privados são bloqueadas antes de abrir conexão.
--- FIM ISSUE 2 ---""",

        """--- ISSUE 3 ---
**Título:** [Segurança] Exfiltração de Histórico de Consultas e Logs sem Controle de Acesso (IDOR/Privilege)
**Labels:** security, priority-medium, severity-medium

### Descrição do Problema
Os endpoints de exportação de telemetria (`/api/v1/queries/export`) e logs (`/api/v1/logs`) retornam o banco de dados completo de consultas e mensagens operacionais a qualquer cliente HTTP, sem segregação de usuário ou chave de administrador.

### Evidência
- `src/adapters/inbound/api/fastapi_app.py:270-286`
```python
@app.get("/api/v1/queries/export")
async def export_queries(format: str = Query(default="json", pattern="^(json|csv)$")):
    content = await asyncio.to_thread(telemetry_service.export_queries, format)
```

### Impacto
Vazamento de todas as perguntas realizadas por usuários ou outros agentes no sistema, expondo código-fonte, tópicos confidenciais de projetos e logs de telemetria interna.

### Sugestão de Correção
1. Proteger os endpoints `/api/v1/queries/*`, `/api/v1/logs` e `/api/v1/llm/*` exigindo perfil/chave administrativa.
2. Limitar o histórico retornado apenas a consultas autorizadas.

### Critérios de Aceite
- [ ] Exportação de queries exige autenticação administrativa.
- [ ] Logs operacionais só podem ser lidos localmente ou por administradores.
--- FIM ISSUE 3 ---""",

        """--- ISSUE 4 ---
**Título:** [Segurança] Envio de Chave de API Gemini em Query String na Requisição HTTP Fallback
**Labels:** security, priority-low, severity-low

### Descrição do Problema
No adaptador `GeminiLLMAdapter`, caso a biblioteca oficial `google-genai` não esteja instalada e o fallback HTTP seja acionado, a `GEMINI_API_KEY` é enviada diretamente na URL como parâmetro de consulta (`?key=...`).

### Evidência
- `src/adapters/outbound/llm/llm_adapters.py:55`
```python
url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
```

### Impacto
Chaves de API em query strings são gravadas em logs de proxies, gateways corporativos, históricos de navegadores e logs de rede, aumentando o risco de comprometimento da credencial.

### Sugestão de Correção
Alterar o envio da chave para o cabeçalho HTTP padrão da Google Cloud: `x-goog-api-key: <chave>`.

### Critérios de Aceite
- [ ] A URL da requisição de fallback não contém o parâmetro `?key=`.
- [ ] A chave é passada via header `headers={"x-goog-api-key": self.api_key}`.
--- FIM ISSUE 4 ---"""
    ]

    for iss in issues_text:
        # Formata o bloco de issue
        lines = iss.split("\n")
        issue_story = []
        for l in lines:
            if l.startswith("**Título:**"):
                issue_story.append(Paragraph(f"<b>{l}</b>", style_h2))
            elif l.startswith("--- ISSUE") or l.startswith("--- FIM"):
                issue_story.append(Paragraph(f"<font color='#2563EB'><b>{l}</b></font>", style_body_bold))
            elif l.startswith("```"):
                continue
            elif l.strip().startswith("- [ ]") or l.strip().startswith("- `"):
                issue_story.append(Paragraph(f"&nbsp;&nbsp;• {l.replace('- [ ]', '[ ]')}", style_body))
            elif l.startswith("###"):
                issue_story.append(Paragraph(f"<b>{l.replace('###', '').strip()}</b>", style_h2))
            else:
                if l.strip():
                    issue_story.append(Paragraph(l, style_body))
        
        t_box = Table([[issue_story]], colWidths=[485])
        t_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_SLATE_50),
            ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_box)
        story.append(Spacer(1, 10))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Relatório gerado com sucesso: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
