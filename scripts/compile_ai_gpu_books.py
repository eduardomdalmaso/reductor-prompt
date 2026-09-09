#!/usr/bin/env python3
"""
Compilador de Documentações de IA & GPU para o ReductorPrompt Database:
1. Triton GPU Programming Language (OpenAI)
2. Ultralytics YOLO Computer Vision & Real-time Tracking (Ultralytics)
3. PyTorch Core & GPU Architecture (PyTorch Team)
"""

import os
import re
import html
import requests
import markdown_it
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas


DB_DIR = "/home/hades/Documents/ReductorPrompt/database"
TMP_DIR = "/tmp/ai_gpu_docs"


class NumberedCanvas(canvas.Canvas):
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

        doc_title = getattr(self, 'doc_title', 'AI & GPU Engineering Guide')
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, doc_title)

        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "ReductorPrompt Database — AI & GPU Collection")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_text)
        self.restoreState()


def get_styles():
    return {
        'CoverTitle': ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=26, leading=32, textColor=colors.HexColor("#1A365D"), alignment=1, spaceAfter=12),
        'CoverSubtitle': ParagraphStyle('CoverSubtitle', fontName='Helvetica', fontSize=13, leading=18, textColor=colors.HexColor("#4A5568"), alignment=1, spaceAfter=20),
        'CoverMeta': ParagraphStyle('CoverMeta', fontName='Helvetica', fontSize=10, leading=15, textColor=colors.HexColor("#718096"), alignment=1),
        'ChapterBanner': ParagraphStyle('ChapterBanner', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor("#2B6CB0"), spaceBefore=14, spaceAfter=8, keepWithNext=True),
        'PageTitle': ParagraphStyle('PageTitle', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=colors.HexColor("#1A202C"), spaceBefore=2, spaceAfter=6, keepWithNext=True),
        'Heading2': ParagraphStyle('Heading2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor("#2D3748"), spaceBefore=8, spaceAfter=3, keepWithNext=True),
        'Heading3': ParagraphStyle('Heading3', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=colors.HexColor("#4A5568"), spaceBefore=6, spaceAfter=2, keepWithNext=True),
        'Heading4': ParagraphStyle('Heading4', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=colors.HexColor("#718096"), spaceBefore=5, spaceAfter=2, keepWithNext=True),
        'Body': ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor("#2D3748")),
        'IndentedBody': ParagraphStyle('IndentedBody', fontName='Helvetica', fontSize=9.5, leading=14, leftIndent=16, textColor=colors.HexColor("#2D3748")),
        'ListItem': ParagraphStyle('ListItem', fontName='Helvetica', fontSize=9.5, leading=14, leftIndent=14, textColor=colors.HexColor("#2D3748")),
        'CodeBox': ParagraphStyle('CodeBox', fontName='Courier', fontSize=7.5, leading=10, textColor=colors.HexColor("#1A202C")),
        'TableHeader': ParagraphStyle('TableHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor("#1A202C")),
        'TableCell': ParagraphStyle('TableCell', fontName='Helvetica', fontSize=8, leading=10.5, textColor=colors.HexColor("#2D3748")),
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
                href = child.get('href', '')
                if href.startswith('http'):
                    parts.append(f"<font color='#2B6CB0'><u>{inner}</u></font>")
                else:
                    parts.append(f"<font color='#2B6CB0'>{inner}</font>")
            elif t == 'br':
                parts.append("<br/>")
            else:
                parts.append(inner)
    return "".join(parts)


def create_code_flowable(raw_code: str, styles, width=490):
    lines = raw_code.rstrip('\n').split('\n')
    max_chars = 78
    wrapped_lines = []
    for line in lines:
        if len(line) <= max_chars:
            wrapped_lines.append(html.escape(line).replace(' ', '&nbsp;'))
        else:
            while len(line) > max_chars:
                wrapped_lines.append(html.escape(line[:max_chars]).replace(' ', '&nbsp;'))
                line = "    " + line[max_chars:]
            if line:
                wrapped_lines.append(html.escape(line).replace(' ', '&nbsp;'))
    
    flowables = []
    chunk_size = 10  # Max 10 lines per chunk ensures height < 120 points (safe for any page)
    for i in range(0, len(wrapped_lines), chunk_size):
        chunk = wrapped_lines[i:i + chunk_size]
        formatted_code = "<br/>".join(chunk)
        code_p = Paragraph(f"<font face='Courier' size='7.5' color='#1A202C'>{formatted_code}</font>", styles['CodeBox'])

        table = Table([[code_p]], colWidths=[width])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        flowables.append(table)
        flowables.append(Spacer(1, 1))
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
    story.append(Paragraph(f"<b>Autor/Projeto:</b> {html.escape(author)}", styles['CoverSubtitle']))
    story.append(Spacer(1, 80))
    story.append(Paragraph(f"<b>Origem:</b> {html.escape(meta_origin)}", styles['CoverMeta']))
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt AI &amp; GPU Collection", styles['CoverMeta']))
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
# 1. TRITON GPU PROGRAMMING (OpenAI / Triton Team)
# ==============================================================================
def compile_triton():
    print("\n[1/3] Compilando: Triton GPU Programming Documentation...")
    triton_dir = os.path.join(TMP_DIR, "triton", "docs")
    sections = []
    full_md_lines = [
        "# OpenAI Triton: GPU Programming Language & Compiler",
        "\n> **Autor:** OpenAI & Triton Community\n> **Fonte:** github.com/triton-lang/triton/tree/main/docs\n\n---\n"
    ]

    for root, dirs, files in sorted(os.walk(triton_dir)):
        for f in sorted(files):
            if f.endswith('.md') or f.endswith('.rst'):
                fpath = os.path.join(root, f)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                
                rel = os.path.relpath(fpath, triton_dir)
                title = rel.replace('.md', '').replace('.rst', '').replace('/', ' > ')
                sections.append({'title': title, 'markdown': content})
                full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "triton_gpu_programming_guide.md")
    out_pdf = os.path.join(DB_DIR, "triton_gpu_programming_guide.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo MD: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "OpenAI Triton",
        "GPU Programming Language, Compiler Architecture & Kernel Optimization",
        "OpenAI & Triton Community",
        "https://github.com/triton-lang/triton/tree/main/docs",
        sections,
        out_pdf
    )
    print(f"Salvo PDF: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 2. ULTRALYTICS YOLO & COMPUTER VISION (Ultralytics)
# ==============================================================================
def compile_ultralytics():
    print("\n[2/3] Compilando: Ultralytics YOLO & Vision Documentation...")
    en_dir = os.path.join(TMP_DIR, "ultralytics", "docs", "en")
    sections = []
    full_md_lines = [
        "# Ultralytics YOLO: Computer Vision & Real-time Tracking Guide",
        "\n> **Autor:** Ultralytics Team\n> **Fonte:** github.com/ultralytics/ultralytics/tree/main/docs\n\n---\n"
    ]

    # Prioriza seções fundamentais de modelos, modos, guias e integrações
    subdirs = ['models', 'modes', 'tasks', 'guides', 'integrations', 'usage']
    for sub in subdirs:
        sub_path = os.path.join(en_dir, sub)
        if os.path.exists(sub_path):
            for root, dirs, files in sorted(os.walk(sub_path)):
                for f in sorted(files):
                    if f.endswith('.md'):
                        fpath = os.path.join(root, f)
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                            content = fp.read()
                        rel = os.path.relpath(fpath, en_dir)
                        title = rel.replace('.md', '').replace('/', ' > ')
                        sections.append({'title': title, 'markdown': content})
                        full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "ultralytics_yolo_vision_guide.md")
    out_pdf = os.path.join(DB_DIR, "ultralytics_yolo_vision_guide.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo MD: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "Ultralytics YOLO Vision Guide",
        "Object Detection, Segmentation, Pose, Multi-Object Tracking & TensorRT Deployment",
        "Ultralytics Team",
        "https://github.com/ultralytics/ultralytics/tree/main/docs",
        sections,
        out_pdf
    )
    print(f"Salvo PDF: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# 3. PYTORCH CORE & GPU ARCHITECTURE (PyTorch)
# ==============================================================================
def compile_pytorch():
    print("\n[3/3] Compilando: PyTorch Core & GPU Architecture Manual...")
    
    pytorch_docs_dir = os.path.join(TMP_DIR, "pytorch", "docs")
    notes_dir = os.path.join(pytorch_docs_dir, "source", "notes")
    cpp_api_dir = os.path.join(pytorch_docs_dir, "cpp", "source", "api")

    sections = []
    full_md_lines = [
        "# PyTorch Core: GPU Architecture, CUDA Semantics & LibTorch C++ Engine",
        "\n> **Autor:** PyTorch Core Team\n> **Fonte:** github.com/pytorch/pytorch/tree/main/docs\n\n---\n"
    ]

    # 1. PyTorch Architecture Notes
    if os.path.exists(notes_dir):
        for f in sorted(os.listdir(notes_dir)):
            if f.endswith('.md') or f.endswith('.rst'):
                fpath = os.path.join(notes_dir, f)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                title = f"Architecture Notes > {f.replace('.md', '').replace('.rst', '').replace('_', ' ').title()}"
                sections.append({'title': title, 'markdown': content})
                full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    # 2. PyTorch C++ / CUDA LibTorch APIs
    if os.path.exists(cpp_api_dir):
        for root, dirs, files in sorted(os.walk(cpp_api_dir)):
            for f in sorted(files):
                if f.endswith('.md') or f.endswith('.rst'):
                    fpath = os.path.join(root, f)
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                    rel = os.path.relpath(fpath, cpp_api_dir)
                    title = f"C++ LibTorch API > {rel.replace('.md', '').replace('.rst', '').replace('/', ' > ')}"
                    sections.append({'title': title, 'markdown': content})
                    full_md_lines.append(f"# {title}\n\n{content}\n\n---\n")

    out_md = os.path.join(DB_DIR, "pytorch_gpu_core_guide.md")
    out_pdf = os.path.join(DB_DIR, "pytorch_gpu_core_guide.pdf")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md_lines))
    print(f"Salvo MD: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "PyTorch Core & GPU Architecture",
        "CUDA Semantics, Memory Management, Autograd Engine & C++ LibTorch FFI",
        "The PyTorch Core Team",
        "https://github.com/pytorch/pytorch/tree/main/docs",
        sections,
        out_pdf
    )
    print(f"Salvo PDF: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    compile_triton()
    compile_ultralytics()
    compile_pytorch()
    print("\nTodas as compilações de Triton, Ultralytics e PyTorch foram concluídas com sucesso!")


if __name__ == "__main__":
    main()
