#!/usr/bin/env python3
"""
Compilador de Guias Especializados em Go + Rust de Alta Performance para o ReductorPrompt.

Gera em PDF e Markdown de alta fidelidade:
1. Go + Rust High-Performance Video Pipeline & GPU Acceleration (NVDEC, Zero-Copy, CGo/FFI, Shm, Lock-Free Ring Buffers)
2. Pion WebRTC & Real-Time Media Streaming Guide (RTP/RTCP, H.264/H.265, Jitter Buffers, Payloaders)
3. Low-Latency Go Systems & Zero-Allocation Engineering (GC Optimization, sync.Pool, Atomic Lock-Free, Cache Lines)
"""

import os
import html
import markdown_it
from bs4 import BeautifulSoup, NavigableString, Tag

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas


DB_DIR = "/home/hades/Documents/ReductorPrompt/database"


class NumberedCanvas(canvas.Canvas):
    """Canvas com cabeçalho elegante e paginação dinâmica."""
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

        doc_title = getattr(self, 'doc_title', 'Go & Rust Video Performance Guide')
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, doc_title)

        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "ReductorPrompt Database — High Performance Engineering")
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


def build_manual(title, subtitle, author, sections, out_base):
    out_md = f"{out_base}.md"
    out_pdf = f"{out_base}.pdf"

    md_lines = [f"# {title}", f"\n**{subtitle}**\n\n> **Autor/Curadoria:** {author}\n> **Projeto:** ReductorPrompt Technical Collection\n\n---\n"]
    for s in sections:
        md_lines.append(f"# {s['title']}\n\n{s['content']}\n\n---\n")

    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
    print(f"Salvo MD: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    doc = SimpleDocTemplate(out_pdf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = get_styles()
    md = markdown_it.MarkdownIt('commonmark').enable('table')
    story = []

    # Capa
    story.append(Spacer(1, 120))
    story.append(Paragraph(html.escape(title), styles['CoverTitle']))
    story.append(Paragraph(html.escape(subtitle), styles['CoverSubtitle']))
    story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#3182CE"), spaceBefore=10, spaceAfter=20))
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"<b>Autor/Curadoria:</b> {html.escape(author)}", styles['CoverSubtitle']))
    story.append(Spacer(1, 80))
    story.append(Paragraph("<b>Origem:</b> High-Performance Video & Systems Engineering Reference", styles['CoverMeta']))
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt Database", styles['CoverMeta']))
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

        soup = BeautifulSoup(md.render(sec['content']), 'html.parser')
        dom_f = process_dom(soup.children, styles)
        story.extend(dom_f)
        story.append(Spacer(1, 10))
        story.append(PageBreak())

    class CustomCanvas(NumberedCanvas):
        pass
    CustomCanvas.doc_title = f"{title} — {subtitle}"

    doc.build(story, canvasmaker=CustomCanvas)
    print(f"Salvo PDF: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


# ==============================================================================
# MANUAIS TÉCNICOS ESPECÍFICOS
# ==============================================================================

def create_video_pipeline_manual():
    print("\n[1/3] Gerando Guia: Go + Rust High-Performance Video Pipeline & GPU Acceleration...")
    sections = [
        {
            'title': '1. Arquitetura Geral do Pipeline Híbrido Go + Rust',
            'content': """
O processamento de dezenas de câmeras de alta resolução (1080p/4K) exige divisão estrita de responsabilidades:

- **Go (Orquestração, Rede e I/O):** Gerencia conexões RTSP/WebRTC/HLS com milhares de clientes, multiplexação de streams, autenticação, métricas Prometheus e despacho de mensagens assíncronas.
- **Rust (Decodificação de Baixo Nível e GPU):** Parsing de bitstreams (H.264/H.265/AV1), aceleração por hardware via NVDEC (NVIDIA), VA-API (Intel/AMD) ou Vulkan Video, conversão de cores SIMD (YUV420 ➔ RGB/BGR) e repasse para pipelines de inferência (TensorRT/ONNX).

### Diagrama de Fluxo de Dados:
```
[ Câmera RTSP / WebRTC ] 
          │ (H.264 NAL Units via TCP/UDP)
          ▼
┌──────────────────────────────────────┐
│       GO NETWORKING LAYER            │
│   (Zero-Copy I/O com epoll/netpoll)  │
└──────────────────┬───────────────────┘
                   │ (Ponteiro de Pacote / Ring Buffer)
                   ▼
┌──────────────────────────────────────┐
│       RUST DECODER CORE (FFI)        │
│   - NVDEC / VA-API Hardware Decoder  │
│   - YUV420p to BGR (SIMD / CUDA)     │
│   - Frame Memory Pool (DMA-BUF / Shm)│
└──────────────────┬───────────────────┘
                   │ (Ponteiro de Frame Decodificado)
                   ▼
┌──────────────────────────────────────┐
│       GO ROUTER / CONSUMIDORES       │
│   (Broadcast WebRTC / IA Inference)  │
└──────────────────────────────────────┘
```
"""
        },
        {
            'title': '2. Zero-Copy e Compartilhamento de Memória entre Rust e Go',
            'content': """
Ao decodificar vídeo 1080p a 30fps, cada câmera gera aproximadamente **93.3 MB/s** em formato bruto YUV420 (ou 186 MB/s em RGB24). Copiar esses bytes entre linguagens destrói o throughput da memória RAM.

### Estratégias de Zero-Copy:

1. **Memória Compartilhada POSIX (`/dev/shm` / `mmap`):**
   - Utilizada quando Go e Rust rodam em processos isolados para tolerância a falhas.
   - O processo Rust cria um descritor de arquivo `shm_open("video_feed_cam1", ...)` e mapeia a memória com `mmap`.
   - O processo Go mapeia o mesmo arquivo em modo somente leitura (`PROT_READ`).

2. **Fixação de Ponteiros em Go com `runtime.Pinner` (Go 1.21+):**
   - Se o Go alocar o buffer, use `runtime.Pinner` para garantir que o Garbage Collector não mova ou desaloque o buffer durante a operação no Rust:

```go
package main

import (
    "runtime"
    "unsafe"
)

type FrameBuffer struct {
    Data   []byte
    pinner runtime.Pinner
}

func NewFrameBuffer(size int) *FrameBuffer {
    fb := &FrameBuffer{
        Data: make([]byte, size),
    }
    fb.pinner.Pin(&fb.Data[0])
    return fb
}

func (fb *FrameBuffer) Ptr() unsafe.Pointer {
    return unsafe.Pointer(&fb.Data[0])
}

func (fb *FrameBuffer) Release() {
    fb.pinner.Unpin()
}
```
"""
        },
        {
            'title': '3. Otimização de CGo e FFI (Eliminando Overhead de Chamadas)',
            'content': """
Cada chamada de função através da fronteira CGo custa entre **40 a 60 nanosegundos** porque o runtime do Go precisa trocar a pilha da Goroutine para a pilha de threads do sistema operacional (`pthread`) e registrar sinais.

### Regras para FFI de Alta Performance:

1. **Nunca chame CGo por pacote ou por linha de pixels.**
2. **Use o Padrão de Callback ou Processamento em Lote (Batching):**
   Em vez do Go chamar o Rust frame a frame, inicie um worker em Rust em uma thread dedicada que consome de um ring buffer compartilhado e emite notificações apenas quando blocos de frames estão disponíveis.
3. **Assinatura FFI em Rust com `#[repr(C)]` e `extern "C"`:**

```rust
#[repr(C)]
pub struct VideoFrameHeader {
    pub width: u32,
    pub height: u32,
    pub format: u32, // 0 = YUV420p, 1 = RGB24, 2 = NV12
    pub timestamp_us: u64,
    pub data_ptr: *const u8,
    pub data_len: usize,
}

#[no_mangle]
pub unsafe extern "C" fn decode_nal_unit(
    decoder_ctx: *mut std::ffi::c_void,
    nal_data: *const u8,
    nal_len: usize,
    out_frame: *mut VideoFrameHeader,
) -> i32 {
    // Decodificação via NVDEC / FFmpeg
    // Preenche out_frame sem cópia adicional de memória
    0 // Sucesso
}
```
"""
        },
        {
            'title': '4. Ring Buffers Lock-Free e Descarte Inteligente de Frames (Backpressure)',
            'content': """
Em pipelines de vídeo em tempo real, canais tradicionais (`chan []byte`) sofrem com contenção de Mutex interno. Para concorrência máxima entre Goroutines de ingestão e envio para o Rust, utiliza-se o padrão **LMAX Disruptor Lock-Free**:

### Ring Buffer Circular com Operações Atômicas em Go:

```go
package ringbuffer

import (
    "sync/atomic"
    "unsafe"
)

type FrameSlot struct {
    Seq  uint64
    Data unsafe.Pointer
    Len  int
}

type LockFreeFrameRing struct {
    buffer []FrameSlot
    mask   uint64
    head   atomic.Uint64
    tail   atomic.Uint64
}

func NewRing(sizePowerOfTwo uint64) *LockFreeFrameRing {
    return &LockFreeFrameRing{
        buffer: make([]FrameSlot, sizePowerOfTwo),
        mask:   sizePowerOfTwo - 1,
    }
}

func (r *LockFreeFrameRing) Push(data unsafe.Pointer, length int) bool {
    head := r.head.Load()
    tail := r.tail.Load()
    if head-tail >= uint64(len(r.buffer)) {
        // Buffer cheio: Política de descarte automático para tempo real
        return false
    }
    slot := &r.buffer[head&r.mask]
    slot.Data = data
    slot.Len = length
    slot.Seq = head
    r.head.Add(1)
    return true
}
```

### Política de Keyframe Drop:
Se a fila de decodificação atingir 80% da capacidade, o Go deve imediatamente descartar frames intermediários (B-Frames e P-Frames) e aguardar o próximo **IDR Keyframe (I-Frame)** para restabelecer a sincronia sem travar o processamento.
"""
        }
    ]
    build_manual(
        "Go + Rust High-Performance Video Pipeline",
        "Zero-Copy Architecture, GPU Acceleration & Lock-Free Systems",
        "Engenharia de Baixa Latência & Vídeo",
        sections,
        os.path.join(DB_DIR, "go_rust_video_pipeline_architecture")
    )


def create_low_latency_manual():
    print("\n[2/3] Gerando Guia: Low-Latency Go Systems & Zero-Allocation Engineering...")
    sections = [
        {
            'title': '1. Engenharia de Zero-Alocação (Zero-Allocation Go)',
            'content': """
Em sistemas de tempo real com alto volume de frames e pacotes de rede, alocações de heap acionam pausas de Stop-The-World (STW) e ciclos de varredura concorrente do Garbage Collector.

### Técnicas Fundamentais:

1. **Slab Allocators e Pools com `sync.Pool`:**
   Mantenha fatias de memória com tamanhos pré-determinados (ex: 4KB para pacotes de rede, 2MB para frames de vídeo):

```go
var packetPool = sync.Pool{
    New: func() any {
        b := make([]byte, 4096)
        return &b
    },
}

func ProcessPacket(data []byte) {
    bufPtr := packetPool.Get().(*[]byte)
    buf := *bufPtr
    defer packetPool.Put(bufPtr)

    // Utiliza buf sem alocar nova memória
    copy(buf, data)
}
```

2. **Evitar Escapada para a Heap (Escape Analysis):**
   - Execute `go build -gcflags="-m -m"` para inspecionar todas as variáveis que escapam para a Heap.
   - Evite passar interfaces `any` ou closures em loops críticos de processamento de vídeo.
"""
        },
        {
            'title': '2. Ajustes Finos do Runtime e Garbage Collector (GOGC & GOMEMLIMIT)',
            'content': """
A partir do Go 1.19+, a variável `GOMEMLIMIT` revolucionou o comportamento do GC em serviços de alto consumo de memória:

- **Configuração de Alta Performance:**
  - `GOMEMLIMIT=8GiB`: Define o teto máximo de memória antes do GC agir agressivamente.
  - `GOGC=off` ou `GOGC=300`: Desativa o GC por percentual e deixa a coleta ocorrer apenas quando o consumo se aproxima do limite real do sistema, eliminando coletas desnecessárias a cada microssegundo.
- **Fixação de Thread do Sistema Operacional (`runtime.LockOSThread`):**
  Para Goroutines que interagem com drivers de GPU ou contextos de hardware FFI, fixe a goroutine na thread do SO para evitar migrações de contexto pelo scheduler do Go:

```go
func DedicatedDecoderWorker() {
    runtime.LockOSThread()
    defer runtime.UnlockOSThread()

    // Loop de chamada ao driver / FFI
    for {
        // Executa decodificação em thread nativa isolada
    }
}
```
"""
        },
        {
            'title': '3. Alinhamento de Memória, Linhas de Cache e Prevenção de False Sharing',
            'content': """
Em processadores modernos (x86_64 e ARM64), a memória é transferida para o cache da CPU em blocos de **64 bytes (Cache Lines)**.

Se duas Goroutines em núcleos diferentes modificarem variáveis adjacentes que residem na mesma linha de cache de 64 bytes, ocorre o fenômeno de **False Sharing**, reduzindo o throughput em até 10x.

### Prevenção de False Sharing em Go via Padding:

```go
package cache

import "sync/atomic"

// CacheLinePad garante que cada contador ocupe sua própria linha de cache de 64 bytes
type CacheLinePad struct {
    _ [56]byte
}

type IndependentCounters struct {
    Cam1Frames atomic.Uint64
    _          CacheLinePad
    Cam2Frames atomic.Uint64
    _          CacheLinePad
}
```
"""
        }
    ]
    build_manual(
        "Low-Latency Go Systems & Zero-Allocation",
        "GC Optimization, Memory Alignment & Microsecond Determinism",
        "High Performance Go Systems Group",
        sections,
        os.path.join(DB_DIR, "go_low_latency_zero_allocation_guide")
    )


def create_pion_media_manual():
    print("\n[3/3] Gerando Guia: Pion WebRTC & Real-Time Media Streaming in Go...")
    sections = [
        {
            'title': '1. Fundamentos do Ecossistema Pion (Pion WebRTC & Media)',
            'content': """
O ecossistema **Pion** é a implementação 100% nativa em Go para protocolos de mídia em tempo real (WebRTC, RTP, RTCP, DTLS, SCTP, SDP).

### Pacotes Principais para Arquitetura de Mídia:
- **`pion/webrtc/v4`:** Gerenciamento de PeerConnections, DataChannels e Tracks de vídeo/áudio em tempo real com sub-segundo de latência.
- **`pion/rtp`:** Empacotamento e desempacotamento de pacotes RTP (Payloading H.264, H.265, VP8, VP9, Opus).
- **`pion/interceptor`:** Pipeline de filtros para NACK (retransmissão de pacotes perdidos), PLI/FIR (solicitação de I-Frames para decodificadores) e controle de banda TWCC.
- **`pion/mediadevices`:** Captura e conversão direta de codecs de vídeo/áudio sem dependências C.
"""
        },
        {
            'title': '2. Pipeline de Payloading H.264 / H.265 e Extração de NAL Units',
            'content': """
Ao receber pacotes de câmeras para envio a decodificadores GPU em Rust ou repasse via WebRTC, é necessário descompactar pacotes RTP em **NAL Units contínuas**:

```go
package media

import (
    "github.com/pion/rtp"
    "github.com/pion/rtp/codecs"
)

type H264PacketExtractor struct {
    depacketizer codecs.H264Packet
}

func (e *H264PacketExtractor) ExtractNAL(pkt *rtp.Packet) ([][]byte, error) {
    payload, err := e.depacketizer.Unmarshal(pkt.Payload)
    if err != nil {
        return nil, err
    }
    
    // Identifica início de NAL Unit (0x00000001)
    // Encaminha NAL para o decodificador Rust/NVDEC
    return [][]byte{payload}, nil
}
```
"""
        },
        {
            'title': '3. Sincronização de Jitter Buffer e Solicitação de Keyframes (PLI)',
            'content': """
Quando a conexão de rede oscila, pacotes RTP chegam fora de ordem. O receptor em Go precisa:

1. **Jitter Buffer:** Reordenar pacotes por número de sequência RTP (`SequenceNumber`) antes de alimentar o decodificador.
2. **Picture Loss Indication (PLI / FIR):** Se um pacote do meio de um frame for perdido e o NACK falhar, envie um pacote RTCP PLI imediatamente para a câmera gerar um novo I-Frame completo:

```go
import (
    "github.com/pion/rtcp"
    "github.com/pion/webrtc/v4"
)

func RequestKeyframe(pc *webrtc.PeerConnection, ssrc uint32) error {
    return pc.WriteRTCP([]rtcp.Packet{
        &rtcp.PictureLossIndication{
            MediaSSRC: ssrc,
        },
    })
}
```
"""
        }
    ]
    build_manual(
        "Pion WebRTC & Real-Time Media Streaming",
        "RTP/RTCP Engineering, Payloading, Jitter Buffers & WebRTC Pipelines",
        "Pion Open Source Community & Media Engineers",
        sections,
        os.path.join(DB_DIR, "pion_webrtc_media_streaming_guide")
    )


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    create_video_pipeline_manual()
    create_low_latency_manual()
    create_pion_media_manual()
    print("\nTodos os 3 guias especializados foram compilados com sucesso em PDF e MD!")


if __name__ == "__main__":
    main()
