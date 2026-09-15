from pathlib import Path
#!/usr/bin/env python3
"""
Compilador do Manual Completo de PostgreSQL (Core, Architecture, SQL & High Performance)
para o ReductorPrompt Database
"""

import os
import re
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

DB_DIR = str(Path(__file__).resolve().parent.parent / "database")


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

        doc_title = getattr(self, 'doc_title', 'PostgreSQL Core & Performance Manual')
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, doc_title)

        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "ReductorPrompt Database — Database Engineering Collection")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_text)
        self.restoreState()


def get_styles():
    return {
        'CoverTitle': ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=24, leading=30, textColor=colors.HexColor("#1A365D"), alignment=1, spaceAfter=12),
        'CoverSubtitle': ParagraphStyle('CoverSubtitle', fontName='Helvetica', fontSize=12, leading=17, textColor=colors.HexColor("#4A5568"), alignment=1, spaceAfter=18),
        'CoverMeta': ParagraphStyle('CoverMeta', fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor("#718096"), alignment=1),
        'ChapterBanner': ParagraphStyle('ChapterBanner', fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=8, keepWithNext=True),
        'PageTitle': ParagraphStyle('PageTitle', fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor("#1A202C"), spaceBefore=2, spaceAfter=6, keepWithNext=True),
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
    chunk_size = 10
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
    story.append(Paragraph(f"<b>Autor / Referência:</b> {html.escape(author)}", styles['CoverSubtitle']))
    story.append(Spacer(1, 80))
    story.append(Paragraph(f"<b>Origem / Escopo:</b> {html.escape(meta_origin)}", styles['CoverMeta']))
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt Database Engineering Collection", styles['CoverMeta']))
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


SECTIONS = [
    {
        "title": "1. Data Modeling & Modern Types: UUIDv7, JSONB & Timezones",
        "markdown": """## Modern PostgreSQL Data Types & Schema Design

PostgreSQL offers rich data types that eliminate the need for schema bloat or external key-value stores.

### 1. Primary Keys: UUIDv7 vs UUIDv4
Traditional random UUIDv4 causes index fragmentation and random page splits in B-Tree indexes as tables grow past millions of rows.
**UUIDv7** embeds a millisecond-precision Unix timestamp in the most significant 48 bits, making keys naturally sequential:

```sql
-- In PostgreSQL 17 or via pg_uuidv7 extension / application generation
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Or uuidv7()
    tenant_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2. Deep JSONB Manipulation & Containment
JSONB stores parsed binary JSON, enabling indexed lookups, key manipulation and containment queries:

```sql
-- Check if JSONB contains specific key/value pair (Indexable via GIN)
SELECT * FROM cameras WHERE config @> '{"ai_analytics": {"ppe_detection": true}}';

-- Extract scalar values with type coercion
SELECT id, config->'stream_settings'->>'resolution' AS res FROM cameras;

-- Atomic JSONB update (modifying a nested key without rewriting entire object)
UPDATE cameras 
SET config = jsonb_set(config, '{stream_settings,fps}', '30'::jsonb, true)
WHERE id = $1;
```
"""
    },
    {
        "title": "2. Advanced SQL: Recursive CTEs, Window Functions & Upserts",
        "markdown": """## High-Performance Query Design

### 1. Recursive Common Table Expressions (`WITH RECURSIVE`)
Used for resolving arbitrarily deep folder structures, category hierarchies, and DAG graphs in a single round-trip:

```sql
WITH RECURSIVE folder_hierarchy AS (
    -- Anchor: Root folders for a given tenant
    SELECT id, parent_id, name, ARRAY[name::text] AS breadcrumbs, 1 AS level
    FROM folders
    WHERE tenant_id = $1 AND parent_id IS NULL

    UNION ALL

    -- Recursive Step: Join child folders
    SELECT f.id, f.parent_id, f.name, fh.breadcrumbs || f.name::text, fh.level + 1
    FROM folders f
    JOIN folder_hierarchy fh ON f.parent_id = fh.id
    WHERE f.tenant_id = $1
)
SELECT id, parent_id, name, level, array_to_string(breadcrumbs, ' > ') AS full_path
FROM folder_hierarchy
ORDER BY breadcrumbs;
```

### 2. Window Functions (`ROW_NUMBER`, `LEAD`, `LAG`)
Calculate partition-level analytics without slow self-joins:

```sql
-- Fetch the latest 3 detections per camera in 1 query
WITH ranked_detections AS (
    SELECT 
        id, camera_id, detection_type, confidence, created_at,
        ROW_NUMBER() OVER (PARTITION BY camera_id ORDER BY created_at DESC) AS rank_num
    FROM detections
    WHERE tenant_id = $1
)
SELECT * FROM ranked_detections WHERE rank_num <= 3;
```

### 3. Atomic Upserts (`INSERT ON CONFLICT`)
```sql
INSERT INTO camera_statuses (camera_id, status, last_ping, fps)
VALUES ($1, $2, NOW(), $3)
ON CONFLICT (camera_id) 
DO UPDATE SET 
    status = EXCLUDED.status,
    last_ping = EXCLUDED.last_ping,
    fps = EXCLUDED.fps;
```
"""
    },
    {
        "title": "3. Indexing Internals: B-Tree, GIN, GiST, BRIN & Covering Indexes",
        "markdown": """## Selecting the Right Index for the Right Workload

Choosing the optimal index type determines whether queries execute in 0.2ms or trigger full table scans.

```
+----------------+-----------------------------+-------------------------------------+
| Index Type     | Internal Structure          | Best Used For                       |
+----------------+-----------------------------+-------------------------------------+
| B-Tree         | Balanced Multi-way Tree     | Equality, Range (<, >, BETWEEN),    |
|                |                             | ORDER BY, Unique Constraints        |
+----------------+-----------------------------+-------------------------------------+
| GIN            | Generalized Inverted Index  | JSONB (@>, ?), Full-Text, Arrays    |
+----------------+-----------------------------+-------------------------------------+
| GiST           | Generalized Search Tree     | LTree hierarchies, PostGIS spatial  |
+----------------+-----------------------------+-------------------------------------+
| BRIN           | Block Range Index           | Massive append-only time-series     |
|                | (Stores min/max per page)   | logs (100x smaller memory footprint)|
+----------------+-----------------------------+-------------------------------------+
```

### 1. Covering Index with `INCLUDE` (Index-Only Scans)
Eliminates table heap page lookups by appending payload columns into leaf nodes:
```sql
-- Queries selecting id, name, status by tenant_id can execute 100% in RAM index
CREATE INDEX idx_cameras_tenant_covering 
ON cameras (tenant_id, folder_id) 
INCLUDE (name, status);
```

### 2. Partial Indexes (Zero-Overhead Indexing)
Index only relevant rows:
```sql
-- Indexes only active recording cameras, ignoring 95% of idle records
CREATE INDEX idx_active_recordings 
ON cameras (tenant_id, id) 
WHERE is_recording = TRUE AND status = 'ONLINE';
```

### 3. GIN Index on JSONB Columns
```sql
CREATE INDEX idx_cameras_config_gin ON cameras USING GIN (config jsonb_path_ops);
```

### 4. BRIN Index for Big Data / Camera Detection Logs
```sql
-- Indexes millions of detections in ~100 KB RAM
CREATE INDEX idx_detections_brin_time ON detections USING BRIN (created_at);
```
"""
    },
    {
        "title": "4. Concurrency, MVCC & Lock-Free Job Queues (`SKIP LOCKED`)",
        "markdown": """## Multi-Version Concurrency Control & Queue Processing

PostgreSQL uses Multi-Version Concurrency Control (MVCC) where readers never block writers, and writers never block readers.

### Building Ultra-Fast Distributed Task Queues in PostgreSQL
Instead of deploying separate Redis/RabbitMQ brokers for backend workers, PostgreSQL provides native, transactional, lock-free queue processing via `FOR UPDATE SKIP LOCKED`:

```sql
-- 100 Go/Rust workers can execute this concurrently with ZERO lock contention:
WITH next_task AS (
    SELECT id
    FROM video_processing_tasks
    WHERE status = 'PENDING'
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
UPDATE video_processing_tasks
SET status = 'PROCESSING', started_at = NOW(), worker_id = $1
FROM next_task
WHERE video_processing_tasks.id = next_task.id
RETURNING video_processing_tasks.*;
```

### Advantages:
- **Zero Deadlocks:** Each worker atomically claims a separate row without waiting on locks.
- **ACID Integrity:** If a worker crashes or panics, the transaction automatically rolls back and the task returns to `PENDING` state.
"""
    },
    {
        "title": "5. Table Partitioning & Time-Series Scaling",
        "markdown": """## Declarative Partitioning for Billions of Records

When tables grow past tens of millions of rows (e.g., camera motion events, telemetry, access logs), single-table B-Trees become too large to fit in buffer cache RAM.

### Range Partitioning Pattern (By Month):

```sql
-- Parent Table
CREATE TABLE camera_events (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    camera_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

-- Monthly Partitions
CREATE TABLE camera_events_2026_09 PARTITION OF camera_events
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE camera_events_2026_10 PARTITION OF camera_events
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

-- Indexes are automatically built on each individual partition:
CREATE INDEX idx_events_tenant_created ON camera_events (tenant_id, created_at);
```

### Partition Pruning:
Queries with `WHERE created_at >= '2026-09-10'` will automatically scan **only** the `camera_events_2026_09` table partition and completely skip older/newer partitions.
"""
    },
    {
        "title": "6. Performance Tuning, Query Analysis (`EXPLAIN ANALYZE`) & Memory",
        "markdown": """## PostgreSQL Diagnostic & Server Calibration

### 1. Reading `EXPLAIN (ANALYZE, BUFFERS)`
Always analyze query execution plans to identify bottlenecks:

```sql
EXPLAIN (ANALYZE, BUFFERS, COSTS)
SELECT c.name, COUNT(d.id)
FROM cameras c
JOIN detections d ON c.id = d.camera_id
WHERE c.tenant_id = 'd3b07384-d113-4674-8b64-55be654162e2'
GROUP BY c.name;
```

**What to look for:**
- `Seq Scan`: Table scan on large table (indicates missing index).
- `Index Scan` / `Bitmap Index Scan`: Good, using index.
- `Index Only Scan`: Best possible, data answered directly from RAM cache.
- `Buffers: shared hit=428 read=0`: 100% of data fetched from RAM buffer cache.

### 2. Core Server Tuning Parameters (`postgresql.conf`):

```ini
# Memory Configuration for 32GB RAM Dedicated Server
shared_buffers = 8GB                  # 25% of total RAM
effective_cache_size = 24GB           # 75% of total RAM
work_mem = 64MB                       # Memory per sort/hash operation
maintenance_work_mem = 2GB            # Memory for VACUUM, CREATE INDEX

# WAL & Checkpoints
checkpoint_completion_target = 0.9    # Smooth I/O spikes
max_wal_size = 16GB
min_wal_size = 2GB

# Autovacuum Optimization
autovacuum_vacuum_scale_factor = 0.05 # Trigger vacuum at 5% table update/delete
autovacuum_vacuum_cost_limit = 2000   # Prevent I/O throttling during vacuum
```
"""
    }
]


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    out_md = os.path.join(DB_DIR, "postgresql_core_and_performance_guide.md")
    out_pdf = os.path.join(DB_DIR, "postgresql_core_and_performance_guide.pdf")

    print("Compilando PostgreSQL Core & High-Performance Manual...")

    full_md = [
        "# PostgreSQL Core Architecture, SQL Engine & High-Performance Manual",
        "\n> **Subtítulo:** Advanced SQL, Indexing (B-Tree, GIN, BRIN), MVCC, Queue Processing & Server Tuning",
        "> **Autor:** PostgreSQL Global Development Group & Database Architecture Community",
        "> **Origem:** Official PostgreSQL Architecture Standards & Production Engineering Guides\n",
        "---\n"
    ]
    for sec in SECTIONS:
        full_md.append(f"# {sec['title']}\n\n{sec['markdown']}\n\n---\n")

    with open(out_md, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(full_md))
    print(f"  ✔ MD salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

    render_book_pdf(
        "PostgreSQL Core & Performance Manual",
        "Advanced SQL, Indexing (B-Tree, GIN, GiST, BRIN), MVCC, SKIP LOCKED Queues & Partitioning",
        "PostgreSQL Global Development Group",
        "Official PostgreSQL Documentation & Architecture Reference",
        SECTIONS,
        out_pdf
    )
    print(f"  ✔ PDF salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
