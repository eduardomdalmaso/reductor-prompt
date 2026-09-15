from pathlib import Path
#!/usr/bin/env python3
"""
Compilador de Livros e Manuais Open Source de Go para o ReductorPrompt Database.

Processa e compila em PDF e Markdown de alta fidelidade:
1. Learn Go with Tests (Chris James)
2. Build Web Application with Golang (Asta Xie)
3. Uber Go Style Guide (Uber Engineering)
4. Go Design Patterns (Timur Tasci)
5. Effective Go (The Go Core Team)
"""

import os
import re
import html
import subprocess
import requests
import markdown_it
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas


DB_DIR = str(Path(__file__).resolve().parent.parent / "database")
TMP_DIR = "/tmp/go_books"


class NumberedCanvas(canvas.Canvas):
    """Canvas com cabeçalho e contagem dinâmica de páginas."""
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
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        doc_title = getattr(self, 'doc_title', 'Go Engineering Collection')
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, doc_title)

        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "ReductorPrompt Database — Go Collection")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_text)
        self.restoreState()


def get_styles():
    return {
        'CoverTitle': ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=28, leading=34, textColor=colors.HexColor("#1A365D"), alignment=1, spaceAfter=12),
        'CoverSubtitle': ParagraphStyle('CoverSubtitle', fontName='Helvetica', fontSize=13, leading=18, textColor=colors.HexColor("#4A5568"), alignment=1, spaceAfter=20),
        'CoverMeta': ParagraphStyle('CoverMeta', fontName='Helvetica', fontSize=10, leading=15, textColor=colors.HexColor("#718096"), alignment=1),
        'Breadcrumb': ParagraphStyle('Breadcrumb', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#718096"), spaceBefore=0, spaceAfter=2),
        'ChapterBanner': ParagraphStyle('ChapterBanner', fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor("#2B6CB0"), spaceBefore=14, spaceAfter=10, keepWithNext=True),
        'PageTitle': ParagraphStyle('PageTitle', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor("#1A202C"), spaceBefore=2, spaceAfter=6, keepWithNext=True),
        'Heading2': ParagraphStyle('Heading2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor("#2D3748"), spaceBefore=8, spaceAfter=3, keepWithNext=True),
        'Heading3': ParagraphStyle('Heading3', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=colors.HexColor("#4A5568"), spaceBefore=6, spaceAfter=2, keepWithNext=True),
        'Heading4': ParagraphStyle('Heading4', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=colors.HexColor("#718096"), spaceBefore=5, spaceAfter=2, keepWithNext=True),
        'Body': ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor("#2D3748")),
        'IndentedBody': ParagraphStyle('IndentedBody', fontName='Helvetica', fontSize=9.5, leading=14, leftIndent=16, textColor=colors.HexColor("#2D3748")),
        'ListItem': ParagraphStyle('ListItem', fontName='Helvetica', fontSize=9.5, leading=14, leftIndent=14, textColor=colors.HexColor("#2D3748")),
        'CodeBox': ParagraphStyle('CodeBox', fontName='Courier', fontSize=7.5, leading=10, textColor=colors.HexColor("#1A202C")),
        'TableHeader': ParagraphStyle('TableHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor("#1A202C")),
        'TableCell': ParagraphStyle('TableCell', fontName='Helvetica', fontSize=8, leading=10.5, textColor=colors.HexColor("#2D3748")),
        'TocCategory': ParagraphStyle('TocCategory', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=2),
        'TocItem': ParagraphStyle('TocItem', fontName='Helvetica', fontSize=9, leading=13, leftIndent=12, textColor=colors.HexColor("#4A5568")),
    }


def sanitize_inline_node(node: Tag) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(html.escape(str(child)))
        elif isinstance(child, Tag):
            t = child.name.lower()
            inner = sanitize_inline_node(child)
            if t in ['strong', 'b']:
                parts.append(f"<b>{inner}</b>")
            elif t in ['em', 'i']:
                parts.append(f"<i>{inner}</i>")
            elif t == 'code':
                parts.append(f"<font face='Courier' color='#9B2C2C'><b>{inner}</b></font>")
            elif t == 'a':
                parts.append(f"<font color='#2B6CB0'><u>{inner}</u></font>")
            elif t == 'br':
                parts.append("<br/>")
            else:
                parts.append(inner)
    return "".join(parts)


def format_code_chunk(code_text: str, max_chars_per_line: int = 80) -> str:
    lines = code_text.split('\n')
    wrapped = []
    for line in lines:
        if len(line) <= max_chars_per_line:
            wrapped.append(html.escape(line).replace(' ', '&nbsp;'))
        else:
            while len(line) > max_chars_per_line:
                wrapped.append(html.escape(line[:max_chars_per_line]).replace(' ', '&nbsp;'))
                line = "    " + line[max_chars_per_line:]
            if line:
                wrapped.append(html.escape(line).replace(' ', '&nbsp;'))
    return "<br/>".join(wrapped)


def create_code_flowable(raw_code: str, styles, width=490):
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


def process_dom(elements, styles, indent=0):
    flowables = []
    width = 490 - (indent * 16)
    for elem in elements:
        if isinstance(elem, NavigableString):
            t = str(elem).strip()
            if t:
                flowables.append(Paragraph(html.escape(t), styles['Body']))
                flowables.append(Spacer(1, 4))
            continue
        if not isinstance(elem, Tag):
            continue
        
        name = elem.name.lower()
        if name == 'h1':
            continue
        elif name == 'h2':
            flowables.append(Spacer(1, 8))
            flowables.append(Paragraph(html.escape(elem.get_text(strip=True)), styles['Heading2']))
            flowables.append(Spacer(1, 4))
        elif name == 'h3':
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(html.escape(elem.get_text(strip=True)), styles['Heading3']))
            flowables.append(Spacer(1, 3))
        elif name == 'h4':
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(html.escape(elem.get_text(strip=True)), styles['Heading4']))
            flowables.append(Spacer(1, 2))
        elif name == 'p':
            p_xml = sanitize_inline_node(elem)
            if p_xml.strip():
                st = styles['IndentedBody'] if indent > 0 else styles['Body']
                flowables.append(Paragraph(p_xml, st))
                flowables.append(Spacer(1, 4))
        elif name in ['ul', 'ol']:
            is_ol = (name == 'ol')
            for idx, li in enumerate(elem.find_all('li', recursive=False), 1):
                bullet = f"{idx}." if is_ol else "&bull;"
                block_tags = ['pre', 'ul', 'ol', 'table']
                has_blocks = any(c.name in block_tags for c in li.children if isinstance(c, Tag))

                if not has_blocks:
                    p_tag = li.find('p', recursive=False)
                    target = p_tag if p_tag else li
                    li_xml = sanitize_inline_node(target)
                    flowables.append(Paragraph(f"<b>{bullet}</b>&nbsp;&nbsp;{li_xml}", styles['ListItem']))
                    flowables.append(Spacer(1, 3))
                else:
                    first = True
                    for c in li.children:
                        if isinstance(c, NavigableString):
                            t = str(c).strip()
                            if t:
                                pfx = f"<b>{bullet}</b>&nbsp;&nbsp;" if first else ""
                                st = styles['ListItem'] if first else styles['IndentedBody']
                                flowables.append(Paragraph(f"{pfx}{html.escape(t)}", st))
                                flowables.append(Spacer(1, 3))
                                first = False
                        elif isinstance(c, Tag):
                            if c.name == 'p':
                                p_xml = sanitize_inline_node(c)
                                pfx = f"<b>{bullet}</b>&nbsp;&nbsp;" if first else ""
                                st = styles['ListItem'] if first else styles['IndentedBody']
                                flowables.append(Paragraph(f"{pfx}{p_xml}", st))
                                flowables.append(Spacer(1, 3))
                                first = False
                            elif c.name == 'pre':
                                code = (c.find('code') or c).get_text()
                                flowables.extend(create_code_flowable(code, styles, width=width - 16))
                            elif c.name in ['ul', 'ol']:
                                flowables.extend(process_dom([c], styles, indent=indent + 1))
            flowables.append(Spacer(1, 4))
        elif name == 'pre':
            code = (elem.find('code') or elem).get_text()
            flowables.extend(create_code_flowable(code, styles, width=width))
        elif name == 'table':
            rows = []
            for tr in elem.find_all('tr'):
                r = []
                for cell in tr.find_all(['th', 'td']):
                    is_th = (cell.name.lower() == 'th')
                    st = styles['TableHeader'] if is_th else styles['TableCell']
                    r.append(Paragraph(sanitize_inline_node(cell), st))
                if r:
                    rows.append(r)
            if rows:
                ncols = max(len(r) for r in rows)
                for r in rows:
                    while len(r) < ncols:
                        r.append(Paragraph("", styles['TableCell']))
                cw = width / ncols
                t = Table(rows, colWidths=[cw] * ncols)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                flowables.append(Spacer(1, 4))
                flowables.append(t)
                flowables.append(Spacer(1, 6))
    return flowables


def render_book_pdf(book_title, subtitle, author, meta_origin, sections, output_pdf):
    """Renderiza um livro completo com seções estruturadas para PDF."""
    doc = SimpleDocTemplate(output_pdf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = get_styles()
    md = markdown_it.MarkdownIt('commonmark').enable('table')
    story = []

    # Capa
    story.append(Spacer(1, 120))
    story.append(Paragraph(html.escape(book_title), styles['CoverTitle']))
    story.append(Paragraph(html.escape(subtitle), styles['CoverSubtitle']))
    story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#3182CE"), spaceBefore=10, spaceAfter=20))
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"<b>Autor/Mantenedor:</b> {html.escape(author)}", styles['CoverSubtitle']))
    story.append(Spacer(1, 80))
    story.append(Paragraph(f"<b>Origem:</b> {html.escape(meta_origin)}", styles['CoverMeta']))
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt Technical Collection", styles['CoverMeta']))
    story.append(PageBreak())

    # Índice
    story.append(Paragraph("Table of Contents", styles['ChapterBanner']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=12))
    for sec in sections:
        story.append(Paragraph(f"&bull; {html.escape(sec['title'])}", styles['TocItem']))
    story.append(PageBreak())

    # Conteúdo
    for sec in sections:
        story.append(Paragraph(html.escape(sec['title']), styles['PageTitle']))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=10))

        soup = BeautifulSoup(md.render(sec['markdown']), 'html.parser')
        dom_f = process_dom(soup.children, styles)
        story.extend(dom_f)
        story.append(Spacer(1, 10))
        story.append(PageBreak())

    class CustomCanvas(NumberedCanvas):
        pass
    CustomCanvas.doc_title = f"{book_title} — {subtitle}"

    doc.build(story, canvasmaker=CustomCanvas)


# ==============================================================================
# 1. BUILD WEB APPLICATION WITH GOLANG (Asta Xie)
# ==============================================================================
def compile_build_web_app():
    print("\n[1/5] Compilando: Build Web Application with Golang (astaxie)...")
    en_dir = os.path.join(TMP_DIR, "build-web-app-go", "en")
    if not os.path.exists(en_dir):
        print("Diretório não encontrado, pulando...")
        return

    md_files = sorted([f for f in os.listdir(en_dir) if re.match(r'^\d{2}\.\d+\.md$', f)])
    sections = []
    full_md_lines = ["# Build Web Application with Golang", "\n> **Autor:** Asta Xie\n> **Fonte:** github.com/astaxie/build-web-application-with-golang\n\n---\n"]

    for f in md_files:
        path = os.path.join(en_dir, f)
        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read()
        
        # Pega título do H1 ou H2
        title = f
        for l in content.split('\n'):
            if l.startswith('# ') or l.startswith('## '):
                title = l.lstrip('#').strip()
                break
        
        sections.append({'title': title, 'markdown': content})
        full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "build_web_application_with_golang.md")
    out_pdf = os.path.join(DB_DIR, "build_web_application_with_golang.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Build Web Application with Golang",
        "A Complete Guide to Web Architecture & Systems in Go",
        "Asta Xie (astaxie)",
        "https://github.com/astaxie/build-web-application-with-golang",
        sections,
        out_pdf
    )
    print(f"Salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 2. LEARN GO WITH TESTS (Chris James)
# ==============================================================================
def compile_learn_go_with_tests():
    print("\n[2/5] Compilando: Learn Go with Tests (Chris James)...")
    repo_dir = os.path.join(TMP_DIR, "learn-go-with-tests")
    if not os.path.exists(repo_dir):
        return

    summary_file = os.path.join(repo_dir, "SUMMARY.md")
    order = []
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as fp:
            for line in fp:
                m = re.search(r'\[(.*?)\]\((.*?\.md)\)', line)
                if m:
                    order.append((m.group(1), m.group(2)))

    sections = []
    full_md_lines = ["# Learn Go with Tests", "\n> **Autor:** Chris James\n> **Fonte:** github.com/quii/learn-go-with-tests\n\n---\n"]

    for title, fname in order:
        fpath = os.path.join(repo_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as fp:
                content = fp.read()
            sections.append({'title': title, 'markdown': content})
            full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "learn_go_with_tests.md")
    out_pdf = os.path.join(DB_DIR, "learn_go_with_tests.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Learn Go with Tests",
        "Test-Driven Development, Concurrency & Backend Architecture",
        "Chris James (quii)",
        "https://github.com/quii/learn-go-with-tests",
        sections,
        out_pdf
    )
    print(f"Salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 3. UBER GO STYLE GUIDE (Uber Engineering)
# ==============================================================================
def compile_uber_guide():
    print("\n[3/5] Compilando: Uber Go Style Guide...")
    style_file = os.path.join(TMP_DIR, "uber-go-guide", "style.md")
    if not os.path.exists(style_file):
        return

    with open(style_file, 'r', encoding='utf-8') as fp:
        content = fp.read()

    out_md = os.path.join(DB_DIR, "uber_go_style_guide.md")
    out_pdf = os.path.join(DB_DIR, "uber_go_style_guide.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("# Uber Go Style Guide\n\n> **Autor:** Uber Engineering\n> **Fonte:** github.com/uber-go/guide\n\n---\n\n" + content)
    print(f"Salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Uber Go Style Guide",
        "Production Engineering Patterns, Concurrency & Performance",
        "Uber Engineering",
        "https://github.com/uber-go/guide",
        [{'title': 'Uber Go Style Guide', 'markdown': content}],
        out_pdf
    )
    print(f"Salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 4. GO DESIGN PATTERNS (Timur Tasci)
# ==============================================================================
def compile_go_patterns():
    print("\n[4/5] Compilando: Go Design Patterns...")
    repo_dir = os.path.join(TMP_DIR, "go-patterns")
    if not os.path.exists(repo_dir):
        return

    sections = []
    full_md_lines = ["# Go Design Patterns & Idioms", "\n> **Autor:** Timur Tasci (tmrts)\n> **Fonte:** github.com/tmrts/go-patterns\n\n---\n"]

    categories = ['creational', 'structural', 'behavioral', 'concurrency', 'synchronization', 'messaging', 'stability', 'profiling', 'idiom']
    for cat in categories:
        cat_path = os.path.join(repo_dir, cat)
        if os.path.exists(cat_path) and os.path.isdir(cat_path):
            files = sorted(os.listdir(cat_path))
            for f in files:
                if f.endswith('.md'):
                    fpath = os.path.join(cat_path, f)
                    with open(fpath, 'r', encoding='utf-8') as fp:
                        content = fp.read()
                    title = f"{cat.capitalize()}: {f.replace('.md', '').replace('-', ' ').title()}"
                    sections.append({'title': title, 'markdown': content})
                    full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "go_design_patterns.md")
    out_pdf = os.path.join(DB_DIR, "go_design_patterns.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Go Design Patterns",
        "Idiomatic Design Patterns, Concurrency & Resilience in Go",
        "Timur Tasci (tmrts)",
        "https://github.com/tmrts/go-patterns",
        sections,
        out_pdf
    )
    print(f"Salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 5. EFFECTIVE GO (Rob Pike & Go Core Team)
# ==============================================================================
def compile_effective_go():
    print("\n[5/5] Compilando: Effective Go (The Go Core Team)...")
    url = "https://raw.githubusercontent.com/golang/go/master/doc/effective_go.md"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            content = r.text
        else:
            # Fallback para html
            r_html = requests.get("https://go.dev/doc/effective_go", timeout=15)
            soup = BeautifulSoup(r_html.text, 'html.parser')
            article = soup.find('article', class_='Article') or soup.find('main')
            content = article.get_text() if article else "Effective Go"
    except Exception as e:
        print(f"Erro ao baixar Effective Go: {e}")
        return

    out_md = os.path.join(DB_DIR, "effective_go.md")
    out_pdf = os.path.join(DB_DIR, "effective_go.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("# Effective Go\n\n> **Autor:** The Go Core Team (Rob Pike et al.)\n> **Fonte:** go.dev/doc/effective_go\n\n---\n\n" + content)
    print(f"Salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Effective Go",
        "Official Guide to Writing Idiomatic, Clean and Concurrent Go",
        "The Go Core Team",
        "https://go.dev/doc/effective_go",
        [{'title': 'Effective Go', 'markdown': content}],
        out_pdf
    )
    print(f"Salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    compile_build_web_app()
    compile_learn_go_with_tests()
    compile_uber_guide()
    compile_go_patterns()
    compile_effective_go()
    print("\nTodas as compilações de livros e manuais Go foram concluídas com sucesso!")


if __name__ == "__main__":
    main()
