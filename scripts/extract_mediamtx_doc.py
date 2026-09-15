from pathlib import Path
#!/usr/bin/env python3
"""
MediaMTX Documentation Scraper & High-Quality PDF Generator.

Extrai todas as páginas da documentação oficial do MediaMTX diretamente dos fontes Markdown
originais do GitHub (bluenviron/mediamtx), utilizando markdown-it-py (CommonMark) e ReportLab Platypus.
Garante 100% de fidelidade ao texto original, blocos de código aninhados em listas, tabelas,
links formatados e diagramas de arquitetura SVG.
"""

import os
import io
import sys
import html
import subprocess
import requests
import markdown_it
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any, Tuple, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether,
    Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg


DOCS_TMP_DIR = "/tmp/mediamtx_repo"
OUTPUT_PDF_PATH = str(Path(__file__).resolve().parent.parent / "database" / "mediamtx_documentation.pdf")


class NumberedCanvas(canvas.Canvas):
    """Canvas com cabeçalhos profissionais e contagem de páginas (Página X de Y)."""
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
            # Não exibe cabeçalho/rodapé na capa
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Cabeçalho elegante
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, "MediaMTX Documentation — Complete Reference Guide")

        # Rodapé com numeração
        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "https://mediamtx.org/docs")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_text)
        self.restoreState()


def ensure_docs_repository() -> str:
    """Garante que a documentação oficial esteja clonada localmente em Markdown."""
    docs_path = os.path.join(DOCS_TMP_DIR, "docs")
    if not os.path.exists(docs_path):
        print("Clonando documentação do repositório oficial bluenviron/mediamtx...")
        os.makedirs(DOCS_TMP_DIR, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth=1", "--filter=blob:none", "--sparse",
             "https://github.com/bluenviron/mediamtx.git", "."],
            cwd=DOCS_TMP_DIR,
            check=True
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", "docs"],
            cwd=DOCS_TMP_DIR,
            check=True
        )
    else:
        print(f"Repositório local de documentação encontrado em: {docs_path}")
    return docs_path


def load_doc_structure(docs_path: str) -> List[Dict[str, Any]]:
    """Carrega as categorias e arquivos Markdown ordenados."""
    category_order = [
        ("1-kickoff", "Kickoff"),
        ("2-features", "Features"),
        ("3-publish", "Publish with"),
        ("4-read", "Read with"),
        ("5-references", "References"),
        ("6-misc", "Misc"),
    ]

    structured_categories = []
    for dir_name, cat_title in category_order:
        cat_dir = os.path.join(docs_path, dir_name)
        if not os.path.exists(cat_dir):
            continue

        files = sorted(os.listdir(cat_dir))
        doc_files = []
        for f in files:
            if f.endswith('.md') and f != 'index.md':
                doc_files.append(os.path.join(cat_dir, f))

        pages = []
        for file_path in doc_files:
            with open(file_path, 'r', encoding='utf-8') as fp:
                content = fp.read()
            
            # Extrai o título do H1
            title = os.path.splitext(os.path.basename(file_path))[0]
            lines = content.strip().split('\n')
            for line in lines:
                if line.startswith('# '):
                    title = line.replace('# ', '').strip()
                    break

            pages.append({
                'title': title,
                'file_path': file_path,
                'content': content,
                'dir_path': cat_dir,
                'category': cat_title
            })

        structured_categories.append({
            'category': cat_title,
            'pages': pages
        })

    total_pages = sum(len(c['pages']) for c in structured_categories)
    print(f"Estrutura carregada: {len(structured_categories)} categorias, {total_pages} páginas de documentação.")
    return structured_categories


def sanitize_inline_node(node: Tag) -> str:
    """Converte nós inline de HTML para tags XML seguras do ReportLab, preservando espaços e texto completo."""
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(html.escape(str(child)))
        elif isinstance(child, Tag):
            tag_name = child.name.lower()
            inner = sanitize_inline_node(child)
            if tag_name in ['strong', 'b']:
                parts.append(f"<b>{inner}</b>")
            elif tag_name in ['em', 'i']:
                parts.append(f"<i>{inner}</i>")
            elif tag_name == 'code':
                parts.append(f"<font face='Courier' color='#9B2C2C'><b>{inner}</b></font>")
            elif tag_name == 'a':
                parts.append(f"<font color='#2B6CB0'><u>{inner}</u></font>")
            elif tag_name == 'br':
                parts.append("<br/>")
            else:
                parts.append(inner)
    return "".join(parts)


def format_code_chunk(code_text: str, max_chars_per_line: int = 80) -> str:
    """Formata linhas de código com escape seguro e quebra suave se linha for muito longa."""
    lines = code_text.split('\n')
    wrapped_lines = []
    for line in lines:
        if len(line) <= max_chars_per_line:
            wrapped_lines.append(html.escape(line).replace(' ', '&nbsp;'))
        else:
            while len(line) > max_chars_per_line:
                wrapped_lines.append(html.escape(line[:max_chars_per_line]).replace(' ', '&nbsp;'))
                line = "    " + line[max_chars_per_line:]
            if line:
                wrapped_lines.append(html.escape(line).replace(' ', '&nbsp;'))
    return "<br/>".join(wrapped_lines)


def create_code_flowable(raw_code: str, styles: Dict[str, ParagraphStyle], width: int = 490) -> List[Any]:
    """Gera blocos de código com fundo cinza, borda e quebra multi-páginas suave."""
    lines = raw_code.rstrip('\n').split('\n')
    flowables = []
    chunk_size = 20
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i:i + chunk_size]
        chunk_text = "\n".join(chunk_lines)
        formatted_code = format_code_chunk(chunk_text, max_chars_per_line=80)
        code_p = Paragraph(f"<font face='Courier' size='7.5' color='#1A202C'>{formatted_code}</font>", styles['CodeBox'])

        table = Table([[code_p]], colWidths=[width])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        flowables.append(table)
        flowables.append(Spacer(1, 2))
    flowables.append(Spacer(1, 4))
    return flowables


def process_dom_elements(elements, styles: Dict[str, ParagraphStyle], dir_path: str, indent_level: int = 0) -> List[Any]:
    """Processa recursivamente elementos DOM gerados a partir do CommonMark."""
    flowables = []
    content_width = 490 - (indent_level * 16)

    for elem in elements:
        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text:
                flowables.append(Paragraph(html.escape(text), styles['Body']))
                flowables.append(Spacer(1, 4))
            continue

        if not isinstance(elem, Tag):
            continue

        tag_name = elem.name.lower()

        if tag_name == 'h1':
            continue

        elif tag_name == 'h2':
            h2_text = elem.get_text(strip=True)
            flowables.append(Spacer(1, 8))
            flowables.append(Paragraph(html.escape(h2_text), styles['Heading2']))
            flowables.append(Spacer(1, 4))

        elif tag_name == 'h3':
            h3_text = elem.get_text(strip=True)
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(html.escape(h3_text), styles['Heading3']))
            flowables.append(Spacer(1, 3))

        elif tag_name == 'h4':
            h4_text = elem.get_text(strip=True)
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(html.escape(h4_text), styles['Heading4']))
            flowables.append(Spacer(1, 2))

        elif tag_name == 'p':
            img_tag = elem.find('img')
            if img_tag:
                src = img_tag.get('src', '')
                if src.endswith('.svg'):
                    svg_file = os.path.join(dir_path, src)
                    if os.path.exists(svg_file):
                        try:
                            drawing = svg2rlg(svg_file)
                            if drawing:
                                max_w = content_width - 10
                                if drawing.width > max_w:
                                    scale = max_w / drawing.width
                                    drawing.width *= scale
                                    drawing.height *= scale
                                    drawing.scale(scale, scale)
                                flowables.append(Spacer(1, 6))
                                flowables.append(drawing)
                                flowables.append(Spacer(1, 8))
                        except Exception as e:
                            print(f"Aviso ao renderizar SVG {svg_file}: {e}")
                continue

            p_xml = sanitize_inline_node(elem)
            if p_xml.strip():
                p_style = styles['IndentedBody'] if indent_level > 0 else styles['Body']
                flowables.append(Paragraph(p_xml, p_style))
                flowables.append(Spacer(1, 5))

        elif tag_name in ['ul', 'ol']:
            is_ordered = (tag_name == 'ol')
            list_items = elem.find_all('li', recursive=False)
            for idx, li in enumerate(list_items, 1):
                bullet = f"{idx}." if is_ordered else "&bull;"
                
                # Verifica se li contém blocos estruturados como <pre>, <ul>, <ol>, <table>
                block_tags = ['pre', 'ul', 'ol', 'table']
                has_sub_blocks = any(c.name in block_tags for c in li.children if isinstance(c, Tag))

                if not has_sub_blocks:
                    # Item puramente inline (pode conter texto, links, code, em, etc.)
                    p_tag = li.find('p', recursive=False)
                    target = p_tag if p_tag else li
                    li_xml = sanitize_inline_node(target)
                    bullet_p = Paragraph(f"<b>{bullet}</b>&nbsp;&nbsp;{li_xml}", styles['ListItem'])
                    flowables.append(bullet_p)
                    flowables.append(Spacer(1, 3))
                else:
                    # Item composto (com parágrafos e blocos de código internos)
                    first = True
                    for c in li.children:
                        if isinstance(c, NavigableString):
                            t = str(c).strip()
                            if t:
                                p_prefix = f"<b>{bullet}</b>&nbsp;&nbsp;" if first else ""
                                p_style = styles['ListItem'] if first else styles['IndentedBody']
                                flowables.append(Paragraph(f"{p_prefix}{html.escape(t)}", p_style))
                                flowables.append(Spacer(1, 3))
                                first = False
                        elif isinstance(c, Tag):
                            if c.name == 'p':
                                p_xml = sanitize_inline_node(c)
                                p_prefix = f"<b>{bullet}</b>&nbsp;&nbsp;" if first else ""
                                p_style = styles['ListItem'] if first else styles['IndentedBody']
                                flowables.append(Paragraph(f"{p_prefix}{p_xml}", p_style))
                                flowables.append(Spacer(1, 3))
                                first = False
                            elif c.name == 'pre':
                                code_elem = c.find('code') or c
                                raw_code = code_elem.get_text()
                                code_flowables = create_code_flowable(raw_code, styles, width=content_width - 16)
                                flowables.extend(code_flowables)
                            elif c.name in ['ul', 'ol']:
                                sub_flowables = process_dom_elements([c], styles, dir_path, indent_level=indent_level + 1)
                                flowables.extend(sub_flowables)

            flowables.append(Spacer(1, 4))

        elif tag_name == 'pre':
            code_elem = elem.find('code') or elem
            raw_code = code_elem.get_text()
            code_flowables = create_code_flowable(raw_code, styles, width=content_width)
            flowables.extend(code_flowables)

        elif tag_name == 'table':
            rows_data = []
            for tr in elem.find_all('tr'):
                row = []
                for cell in tr.find_all(['th', 'td']):
                    is_th = (cell.name.lower() == 'th')
                    cell_text = sanitize_inline_node(cell)
                    style = styles['TableHeader'] if is_th else styles['TableCell']
                    row.append(Paragraph(cell_text, style))
                if row:
                    rows_data.append(row)

            if rows_data:
                num_cols = max(len(r) for r in rows_data)
                for r in rows_data:
                    while len(r) < num_cols:
                        r.append(Paragraph("", styles['TableCell']))

                col_w = content_width / num_cols
                t = Table(rows_data, colWidths=[col_w] * num_cols)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                flowables.append(Spacer(1, 5))
                flowables.append(t)
                flowables.append(Spacer(1, 6))

    return flowables


def render_markdown_page(page_info: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    """Renderiza uma página Markdown com cabeçalho, breadcrumb e elementos DOM."""
    raw_md = page_info['content']
    dir_path = page_info['dir_path']
    category = page_info['category']
    page_title = page_info['title']

    md = markdown_it.MarkdownIt('commonmark').enable('table')
    html_str = md.render(raw_md)
    soup = BeautifulSoup(html_str, 'html.parser')

    flowables = []

    # Breadcrumb e Título
    breadcrumb = f"Documentation &gt; {html.escape(category)} &gt; {html.escape(page_title)}"
    flowables.append(Paragraph(breadcrumb, styles['Breadcrumb']))
    flowables.append(Spacer(1, 2))
    flowables.append(Paragraph(html.escape(page_title), styles['PageTitle']))
    flowables.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=10))

    # Processa o conteúdo DOM
    dom_flowables = process_dom_elements(soup.children, styles, dir_path, indent_level=0)
    flowables.extend(dom_flowables)

    return flowables


def build_pdf_document(categories: List[Dict[str, Any]], output_path: str):
    """Constrói o documento PDF final de alta fidelidade técnica."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = {
        'CoverTitle': ParagraphStyle(
            'CoverTitle',
            fontName='Helvetica-Bold',
            fontSize=30,
            leading=36,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,
            spaceAfter=12
        ),
        'CoverSubtitle': ParagraphStyle(
            'CoverSubtitle',
            fontName='Helvetica',
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=24
        ),
        'CoverMeta': ParagraphStyle(
            'CoverMeta',
            fontName='Helvetica',
            fontSize=10,
            leading=16,
            textColor=colors.HexColor("#718096"),
            alignment=1,
        ),
        'Breadcrumb': ParagraphStyle(
            'Breadcrumb',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#718096"),
            spaceBefore=0,
            spaceAfter=2
        ),
        'CategoryBanner': ParagraphStyle(
            'CategoryBanner',
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=14,
            spaceAfter=10,
            keepWithNext=True
        ),
        'PageTitle': ParagraphStyle(
            'PageTitle',
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1A202C"),
            spaceBefore=2,
            spaceAfter=6,
            keepWithNext=True
        ),
        'Heading2': ParagraphStyle(
            'Heading2',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2D3748"),
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True
        ),
        'Heading3': ParagraphStyle(
            'Heading3',
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
            spaceBefore=6,
            spaceAfter=2,
            keepWithNext=True
        ),
        'Heading4': ParagraphStyle(
            'Heading4',
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#718096"),
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True
        ),
        'Body': ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#2D3748"),
        ),
        'IndentedBody': ParagraphStyle(
            'IndentedBody',
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            leftIndent=16,
            textColor=colors.HexColor("#2D3748"),
        ),
        'ListItem': ParagraphStyle(
            'ListItem',
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            leftIndent=14,
            textColor=colors.HexColor("#2D3748"),
        ),
        'CodeBox': ParagraphStyle(
            'CodeBox',
            fontName='Courier',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#1A202C"),
        ),
        'TableHeader': ParagraphStyle(
            'TableHeader',
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1A202C"),
        ),
        'TableCell': ParagraphStyle(
            'TableCell',
            fontName='Helvetica',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#2D3748"),
        ),
        'TocCategory': ParagraphStyle(
            'TocCategory',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=6,
            spaceAfter=2
        ),
        'TocItem': ParagraphStyle(
            'TocItem',
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            leftIndent=12,
            textColor=colors.HexColor("#4A5568"),
        )
    }

    story = []

    # ==================== CAPA ====================
    story.append(Spacer(1, 120))
    story.append(Paragraph("MediaMTX", styles['CoverTitle']))
    story.append(Paragraph("Official Documentation &amp; Comprehensive Reference", styles['CoverSubtitle']))
    story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#3182CE"), spaceBefore=10, spaceAfter=20))
    story.append(Spacer(1, 30))
    story.append(Paragraph("Ready-to-use live media server and media proxy", styles['CoverSubtitle']))
    story.append(Paragraph("Publish, Read, Proxy, Record and Playback Real-time Streams", styles['CoverSubtitle']))
    story.append(Spacer(1, 100))
    story.append(Paragraph("<b>Origem:</b> https://mediamtx.org/docs", styles['CoverMeta']))
    story.append(Paragraph("<b>Repositório:</b> github.com/bluenviron/mediamtx", styles['CoverMeta']))
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt Technical Collection", styles['CoverMeta']))
    story.append(PageBreak())

    # ==================== ÍNDICE ====================
    story.append(Paragraph("Table of Contents", styles['CategoryBanner']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=12))

    for cat in categories:
        story.append(Paragraph(html.escape(cat['category']), styles['TocCategory']))
        for p in cat['pages']:
            story.append(Paragraph(f"&bull; {html.escape(p['title'])}", styles['TocItem']))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ==================== CONTEÚDO ====================
    total_pages = sum(len(c['pages']) for c in categories)
    current_page_idx = 0

    for cat in categories:
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"Chapter: {html.escape(cat['category'])}", styles['CategoryBanner']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2B6CB0"), spaceAfter=14))
        story.append(Spacer(1, 6))

        for page in cat['pages']:
            current_page_idx += 1
            print(f"[{current_page_idx}/{total_pages}] Renderizando: {cat['category']} -> {page['title']}")

            page_flowables = render_markdown_page(page, styles)
            if page_flowables:
                story.extend(page_flowables)
                story.append(Spacer(1, 12))
                story.append(PageBreak())

    print(f"\nConstruindo PDF em: {output_path}...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF compilado com sucesso! Tamanho final: {os.path.getsize(output_path) / 1024:.1f} KB")


def main():
    print("Iniciando geração de alta fidelidade da documentação do MediaMTX...")
    docs_path = ensure_docs_repository()
    categories = load_doc_structure(docs_path)
    build_pdf_document(categories, OUTPUT_PDF_PATH)
    print(f"\nProcesso finalizado com sucesso! Arquivo: {OUTPUT_PDF_PATH}")


if __name__ == "__main__":
    main()
