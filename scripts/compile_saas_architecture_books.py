#!/usr/bin/env python3
"""
Compilador de Livros de Arquitetura de Software para ReductorPrompt Database:
1. SaaS Multi-Tenant Architecture & Tenant Isolation Patterns
2. PostgreSQL Multi-Tenancy & Row-Level Security (RLS) Handbook
3. Hierarchical Data & Tree Structures in SQL: The Clean Tree Patterns
4. Domain-Driven Design & Clean Architecture for High-Performance Backends
5. Modular Monolith & Pragmatic Backend Scalability Patterns
"""

import os
import re
import html
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

        doc_title = getattr(self, 'doc_title', 'Software Architecture Guide')
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 36, 8.5 * 72 - 54, 11 * 72 - 36)
        self.drawString(54, 11 * 72 - 30, doc_title)

        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "ReductorPrompt Database — Software Architecture & SaaS Collection")
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
    story.append(Paragraph("<b>Projeto:</b> ReductorPrompt Software Architecture &amp; SaaS Collection", styles['CoverMeta']))
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
# DEFINIÇÃO DOS 5 LIVROS / GUIAS
# ==============================================================================

BOOKS = [
    {
        "filename_base": "saas_multitenant_architecture_guide",
        "title": "SaaS Multi-Tenant Architecture & Tenant Isolation Patterns",
        "subtitle": "Runtime Context Propagation, Pooled Storage, Tenant Caching & Noisy Neighbor Mitigation",
        "author": "AWS SaaS Architecture Team & Tod Golding (Open Blueprint)",
        "origin": "Open SaaS Architecture Patterns & Multi-Tenant Reference Designs",
        "sections": [
            {
                "title": "1. Multi-Tenant Architecture Models: Silo vs. Pool vs. Hybrid",
                "markdown": """## Multi-Tenancy Fundamentals in High-Performance Systems

Building modern Software-as-a-Service (SaaS) applications requires a definitive strategy for managing tenant isolation, resource sharing, and operational complexity.

### The Three Core Tenancy Models:

1. **Silo Model (Dedicated Resources):**
   - Each tenant receives completely isolated compute, database instances, or network namespaces.
   - **Pros:** Total physical isolation, simple compliance guarantees.
   - **Cons:** Astronomical infrastructure costs, operational nightmare when managing thousands of tenants, inefficient resource utilization (cold cameras/idle instances).

2. **Pooled Model (Shared Everything - Recommended):**
   - Tenants share the same application runtime, memory pools, and database tables.
   - Data separation is enforced logically via a mandatory `tenant_id` foreign key and execution-level filters.
   - **Pros:** Maximum cost efficiency, instant onboarding of new tenants, seamless scaling of shared compute nodes (e.g. Go backend, Rust decoders, GPU clusters).
   - **Cons:** Requires rigorous, zero-leak runtime enforcement and noisy neighbor mitigation.

3. **Hybrid / Bridge Model:**
   - Shared compute layer (APIs, WebRTC gateways) with pooled relational data, but dedicated high-throughput storage (e.g., dedicated S3 bucket or MinIO prefix per tenant for video recordings).

```
+-------------------------------------------------------------+
|                      API Gateway / Ingress                  |
|          (Extracts Tenant ID from JWT / API Key)            |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|               Shared Application Services (Go / Rust)       |
|    - Request Context: context.WithValue(ctx, "tenant_id")   |
|    - Zero-Copy Buffer Pools                                 |
+-------------------------------------------------------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
+-----------------------------+   +---------------------------+
|    Pooled Relational DB     |   |    Tenant-Isolated Storage|
| (PostgreSQL with RLS & IDs) |   | (MinIO / S3 Record Buckets|
+-----------------------------+   +---------------------------+
```
"""
            },
            {
                "title": "2. Runtime Tenant Context Propagation & Middleware Enforcement",
                "markdown": """## Zero-Trust Runtime Context Injection

The golden rule of multi-tenant isolation: **Never trust the client to declare its tenant in query parameters or request bodies.** The tenant identity must always be extracted from cryptographic tokens at the boundary and bound to the thread/goroutine context.

### Golang Tenant Context Middleware Pattern:

```go
package middleware

import (
	"context"
	"net/http"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type contextKey string
const TenantContextKey contextKey = "tenant_id"

func TenantIsolationMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tokenStr := r.Header.Get("Authorization")
		if tokenStr == "" {
			http.Error(w, "Missing Authorization Header", http.StatusUnauthorized)
			return
		}

		claims := &CustomClaims{}
		token, err := jwt.ParseWithClaims(tokenStr, claims, keyFunc)
		if err != nil || !token.Valid {
			http.Error(w, "Invalid Token", http.StatusUnauthorized)
			return
		}

		tenantID, err := uuid.Parse(claims.TenantID)
		if err != nil {
			http.Error(w, "Malformed Tenant ID in Token", http.StatusForbidden)
			return
		}

		// Inject strictly into request context
		ctx := context.WithValue(r.Context(), TenantContextKey, tenantID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func GetTenantID(ctx context.Context) (uuid.UUID, error) {
	val, ok := ctx.Value(TenantContextKey).(uuid.UUID)
	if !ok || val == uuid.Nil {
		return uuid.Nil, ErrMissingTenantContext
	}
	return val, nil
}
```

### Key Principles for Business Logic:
- Repository methods **must receive `ctx context.Context` as the first argument**.
- SQL queries must unpack `tenantID` from `ctx` rather than accepting it as an unchecked method parameter.
"""
            },
            {
                "title": "3. Tenant-Aware Caching & Preventing Cross-Tenant Data Leaks",
                "markdown": """## Safe Multi-Tenant Redis & In-Memory Caching

A frequent source of catastrophic security bugs in SaaS architectures is **cache pollution across tenants**.

### 1. Mandatory Cache Key Namespacing
Every cache key stored in Redis or memory **must follow a strict hierarchical namespace containing the tenant UUID**:

```
tenant:{tenant_id}:{module}:{resource_id}
```

Examples:
- `tenant:d3b07384-d113:cameras:cam_front_gate`
- `tenant:d3b07384-d113:layouts:mosaico_principal`
- `tenant:d3b07384-d113:folders:arvore_geral`

### 2. Tenant Cache Eviction Wrapper (Go Example):

```go
type TenantCache struct {
	redisClient *redis.Client
}

func (c *TenantCache) FormatKey(ctx context.Context, module string, resourceID string) (string, error) {
	tenantID, err := GetTenantID(ctx)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("tenant:%s:%s:%s", tenantID.String(), module, resourceID), nil
}

func (c *TenantCache) GetCamera(ctx context.Context, cameraID string) (*Camera, error) {
	key, err := c.FormatKey(ctx, "cameras", cameraID)
	if err != nil {
		return nil, err
	}
	val, err := c.redisClient.Get(ctx, key).Result()
	if err != nil {
		return nil, err
	}
	var cam Camera
	return &cam, json.Unmarshal([]byte(val), &cam)
}
```
"""
            },
            {
                "title": "4. Noisy Neighbor Mitigation & Fair Resource Scheduling",
                "markdown": """## Preventing Single-Tenant Resource Starvation

In video surveillance and real-time streaming systems, a single active tenant with 100 4K cameras can exhaust network bandwidth, decode threads, or database connection pools, degrading service for all other tenants.

### Architectural Remedies:

1. **Per-Tenant Token Bucket Rate Limiting:**
   - Enforce limits per tenant on API requests per second (RPS) and concurrent active WebRTC stream channels.

2. **Fair-Queueing in Background Workers:**
   - In queue systems (e.g. Asynq, RabbitMQ, Redis Streams), do not process tasks in a single global FIFO queue.
   - Use partitioned queues: `queue:video_processing:{tenant_id}` and round-robin across active tenant queues.

3. **Worker Thread Pooling & GPU Quotas:**
   - Dedicate a maximum percentage of NVDEC / GPU memory allocation per tenant context.
"""
            }
        ]
    },
    {
        "filename_base": "postgresql_multitenancy_and_rls_handbook",
        "title": "PostgreSQL Multi-Tenancy & Row-Level Security (RLS) Handbook",
        "subtitle": "Database-Engine Isolation, SET LOCAL Session Variables, PgBouncer & Index Optimization",
        "author": "PostgreSQL Architecture Community & Open Database Guides",
        "origin": "PostgreSQL Core Security & High-Performance Schema Modeling",
        "sections": [
            {
                "title": "1. Row-Level Security (RLS) Mechanics & Architecture",
                "markdown": """## Enforcing Multi-Tenancy at the Kernel Level

Application-level filtering (`WHERE tenant_id = ?`) is prone to developer oversight. PostgreSQL **Row-Level Security (RLS)** moves tenant isolation into the database engine itself, guaranteeing zero data leakage even in complex joins or subqueries.

### Step-by-Step RLS Implementation:

```sql
-- 1. Enable RLS on the target table
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE cameras FORCE ROW LEVEL SECURITY; -- Also applies to table owners!

-- 2. Create the tenant isolation policy using session settings
CREATE POLICY tenant_isolation_policy ON cameras
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);
```

### How Queries Work:
When the application executes `SELECT * FROM cameras;`, PostgreSQL internally rewrites the query execution plan to:
```sql
SELECT * FROM cameras WHERE tenant_id = current_setting('app.current_tenant')::uuid;
```
"""
            },
            {
                "title": "2. Session Context Injection with Connection Poolers (PgBouncer)",
                "markdown": """## Transaction-Scoped Session Variables (`SET LOCAL`)

In high-concurrency backends using connection poolers (such as PgBouncer in transaction pooling mode), `SET app.current_tenant` must be scoped strictly to the current transaction to prevent context leaking to subsequent requests reusing the connection.

### The `SET LOCAL` Pattern in Transactions:

```sql
BEGIN;
-- Scoped strictly to this transaction; automatically cleared upon COMMIT/ROLLBACK
SET LOCAL app.current_tenant = 'd3b07384-d113-4674-8b64-55be654162e2';

SELECT id, name, rtsp_url FROM cameras;
COMMIT;
```

### Go Database Wrapper Example:

```go
func (r *CameraRepository) WithTenantTx(ctx context.Context, fn func(tx *sql.Tx) error) error {
	tenantID, err := GetTenantID(ctx)
	if err != nil {
		return err
	}

	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Set tenant context for this transaction
	_, err = tx.ExecContext(ctx, "SET LOCAL app.current_tenant = $1", tenantID.String())
	if err != nil {
		return fmt.Errorf("failed to set tenant context: %w", err)
	}

	if err := fn(tx); err != nil {
		return err
	}
	return tx.Commit()
}
```
"""
            },
            {
                "title": "3. Indexing Strategies for Multi-Tenant Tables",
                "markdown": """## Composite B-Trees & Query Optimization

In a pooled multi-tenant database, every single index must take `tenant_id` into account.

### Golden Indexing Rules:

1. **Lead with `tenant_id` in Composite Indexes:**
   - **Correct:** `CREATE INDEX idx_cameras_tenant_folder ON cameras (tenant_id, folder_id);`
   - **Correct:** `CREATE INDEX idx_cameras_tenant_status ON cameras (tenant_id, status);`
   - **Incorrect:** `CREATE INDEX idx_cameras_folder ON cameras (folder_id);` (Causes full-table index scans across all tenants).

2. **Multi-Tenant Unique Constraints:**
   - Camera names should be unique *per tenant*, not globally across the entire database:
   ```sql
   CREATE UNIQUE INDEX uq_cameras_tenant_name ON cameras (tenant_id, LOWER(name));
   ```

3. **Table Partitioning for Hyper-Scale Tenants:**
   - For tenants with millions of daily event records, use PostgreSQL Declarative Partitioning by List (`PARTITION BY LIST (tenant_id)`).
"""
            }
        ]
    },
    {
        "filename_base": "hierarchical_data_and_tree_patterns_in_sql",
        "title": "Hierarchical Data & Tree Structures in SQL: The Clean Tree Patterns",
        "subtitle": "Universal Folder Hierarchy, Recursive CTEs (WITH RECURSIVE), Adjacency Lists & LTree",
        "author": "Relational Database Architecture Patterns & Bill Karwin",
        "origin": "Open Database Modeling Patterns & Tree Representation Systems",
        "sections": [
            {
                "title": "1. The Universal Folder Pattern: Avoiding Over-Engineering",
                "markdown": """## One Folder Table to Rule Them All

A common anti-pattern in VMS and administrative systems is creating separate folder tables for every entity type (`camera_folders`, `layout_folders`, `user_folders`, `map_folders`). This causes schema bloat, duplicated maintenance logic, and complex frontend adapters.

### The Clean Solution: Universal `folders` Table

```sql
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES folders(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    module VARCHAR(50) NOT NULL, -- Discriminator: 'cameras', 'layouts', 'analytics', 'devices'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_folder_name UNIQUE (tenant_id, module, parent_id, name)
);

CREATE INDEX idx_folders_tenant_module_parent ON folders (tenant_id, module, parent_id);
```

### Referencing Entities:
The `cameras` table simply has an optional reference:
```sql
ALTER TABLE cameras ADD COLUMN folder_id UUID REFERENCES folders(id) ON DELETE SET NULL;
```
"""
            },
            {
                "title": "2. Recursive CTEs (`WITH RECURSIVE`) for Sub-Millisecond Tree Traversal",
                "markdown": """## Fetching Entire Folder Trees in 1 Query

Using `WITH RECURSIVE`, the database resolves arbitrarily nested parent-child hierarchies in a single round-trip, returning depth, full breadcrumbs, and hierarchy ordering.

### Complete Tree Query with Breadcrumb Path:

```sql
WITH RECURSIVE folder_tree AS (
    -- Anchor member: Root folders (parent_id IS NULL) for the tenant and module
    SELECT 
        id, 
        parent_id, 
        name, 
        module,
        ARRAY[name::text] AS path,
        1 AS depth
    FROM folders
    WHERE tenant_id = $1 AND module = $2 AND parent_id IS NULL

    UNION ALL

    -- Recursive member: Fetch all children
    SELECT 
        f.id, 
        f.parent_id, 
        f.name, 
        f.module,
        ft.path || f.name::text,
        ft.depth + 1
    FROM folders f
    JOIN folder_tree ft ON f.parent_id = ft.id
    WHERE f.tenant_id = $1 AND f.module = $2
)
SELECT 
    id, 
    parent_id, 
    name, 
    depth, 
    array_to_string(path, ' / ') AS breadcrumb
FROM folder_tree
ORDER BY path;
```

### Advantages:
- **No N+1 Queries:** Front-ends receive the entire hierarchy structured with zero round-trip overhead.
- **Cycle-Proof:** PostgreSQL handles recursion limits safely.
"""
            },
            {
                "title": "3. Moving, Renaming, and Deleting Folder Subtrees",
                "markdown": """## Clean Hierarchy Operations

### 1. Moving a Folder (and its entire subtree)
In an Adjacency List model, moving an entire branch containing 1,000 subfolders and 5,000 cameras takes **1 single atomic UPDATE query**:
```sql
UPDATE folders 
SET parent_id = $1, updated_at = NOW() 
WHERE id = $2 AND tenant_id = $3;
```
All children automatically remain attached because they reference the moved folder's `id`.

### 2. Deleting a Folder (Choice of Behavior):
- **Cascade Delete (Delete folder and all children):** Enabled via `ON DELETE CASCADE`.
- **Orphan Preservation (Unlink cameras to root):** Handled via `ON DELETE SET NULL` on the `cameras.folder_id` foreign key.
"""
            }
        ]
    },
    {
        "filename_base": "domain_driven_design_and_clean_architecture_guide",
        "title": "Domain-Driven Design & Clean Architecture for High-Performance Backends",
        "subtitle": "Strategic Bounded Contexts, Tactical Aggregates, Hexagonal Ports/Adapters & Type Invariants",
        "author": "Open DDD & Clean Architecture Community",
        "origin": "Modern Backend Architecture & DDD Modeling Principles",
        "sections": [
            {
                "title": "1. Strategic DDD: Bounded Contexts in Video & Streaming Systems",
                "markdown": """## Separating Business Concerns

In a high-throughput Video Management System (VMS) or IoT pipeline, domain confusion causes monolithic deadlock.

### Key Bounded Contexts:

1. **Media Ingestion & Streaming Context (Low-Latency / Real-Time):**
   - **Concepts:** `StreamSession`, `RTSPConnection`, `WebRTCPeer`, `NALUnit`, `FrameBuffer`.
   - **Requirements:** Zero allocations, lock-free queues, Cgo/FFI decoders, GPU memory handles.
   - **Does NOT care about:** User permissions, folder trees, UI layouts.

2. **System Management & Organization Context (Administrative):**
   - **Concepts:** `Tenant`, `User`, `Folder`, `DeviceRegistry`, `AuditLog`.
   - **Requirements:** Relational consistency, transactional integrity, ACL policies.

3. **Analytics & AI Processing Context (Batch / Inference):**
   - **Concepts:** `DetectionModel`, `InferenceJob`, `BoundingBox`, `TrackedObject`.
"""
            },
            {
                "title": "2. Tactical DDD: Aggregates, Value Objects & Entities",
                "markdown": """## Defining Clear Invariants

### 1. The `Folder` Aggregate:
- `Folder` is an Aggregate Root responsible for holding its own name, parent pointer, and tenant invariant.
- It does **not** manage the internal state or streaming buffers of cameras.

### 2. Strongly Typed Value Objects in Go:

```go
package domain

import (
	"errors"
	"github.com/google/uuid"
)

type TenantID struct {
	value uuid.UUID
}

func NewTenantID(id string) (TenantID, error) {
	u, err := uuid.Parse(id)
	if err != nil || u == uuid.Nil {
		return TenantID{}, errors.New("invalid tenant ID")
	}
	return TenantID{value: u}, nil
}

func (t TenantID) UUID() uuid.UUID {
	return t.value
}

func (t TenantID) String() string {
	return t.value.String()
}
```
"""
            },
            {
                "title": "3. Ports & Adapters (Hexagonal Architecture) Implementation",
                "markdown": """## Decoupling Core Domain from Frameworks & Drivers

```
+-------------------------------------------------------------+
|                     Inbound Adapters                        |
|        (HTTP REST / WebSockets / gRPC / WebRTC)             |
+-------------------------------------------------------------+
                               | (Calls)
                               v
+-------------------------------------------------------------+
|                 Application Layer (Use Cases)               |
|      - CreateFolderUseCase                                  |
|      - StreamCameraUseCase                                  |
+-------------------------------------------------------------+
                               | (Uses Interfaces / Ports)
                               v
+-------------------------------------------------------------+
|                   Domain Layer (Entities)                   |
|      - Camera, Folder, Tenant                               |
+-------------------------------------------------------------+
                               ^ (Implements)
                               |
+-------------------------------------------------------------+
|                    Outbound Adapters                        |
|   (PostgreSQL / Redis / MediaMTX FFI / Nvidia TensorRT)     |
+-------------------------------------------------------------+
```
"""
            }
        ]
    },
    {
        "filename_base": "modular_monolith_and_backend_scalability_patterns",
        "title": "Modular Monolith & Pragmatic Backend Scalability Patterns",
        "subtitle": "Module Boundaries in Go/Rust, Lock-Free Concurrency, Channel Pipelines & Slicing Strategy",
        "author": "Backend Architecture & Distributed Systems Open Guides",
        "origin": "High-Performance Systems Design & Pragmatic Scalability Patterns",
        "sections": [
            {
                "title": "1. The Modular Monolith: Zero-Latency Internal Communications",
                "markdown": """## High Performance Without Microservice Overhead

For streaming and media backends, premature microservice decomposition introduces devastating network serialization latency (gRPC/HTTP), network serialization overhead, and distributed transaction headaches.

### Principles of a Clean Modular Monolith:
- **Strict Package Isolation:** Package `streaming` cannot directly import internal types from `billing` or `admin_ui`.
- **Public Module Interfaces:** Communication between modules occurs through explicit Go/Rust interfaces or typed in-process event buses.
- **Zero-Copy Data Transfer:** Pointers to camera frame buffers can be passed directly across module boundaries in nanoseconds without JSON/Protobuf encoding.
"""
            },
            {
                "title": "2. Lock-Free Concurrency & Worker Ring Buffers",
                "markdown": """## High-Throughput Ingestion Pipelines

```go
package pipeline

import (
	"sync/atomic"
	"unsafe"
)

type RingBuffer struct {
	buffer []unsafe.Pointer
	mask   uint64
	head   uint64
	tail   uint64
}

func NewRingBuffer(size uint64) *RingBuffer {
	// Size must be power of 2
	return &RingBuffer{
		buffer: make([]unsafe.Pointer, size),
		mask:   size - 1,
	}
}

func (rb *RingBuffer) Push(item unsafe.Pointer) bool {
	head := atomic.LoadUint64(&rb.head)
	tail := atomic.LoadUint64(&rb.tail)
	if head-tail >= uint64(len(rb.buffer)) {
		return false // Buffer full, zero allocation drop or backpressure
	}
	rb.buffer[head&rb.mask] = item
	atomic.AddUint64(&rb.head, 1)
	return true
}
```
"""
            },
            {
                "title": "3. The Pragmatic Evolution Path: When to Extract Microservices",
                "markdown": """## Extracting Services Based on Hardware Profiles

In a video/AI platform, do not extract services by domain entities (e.g. `camera-service`, `user-service`). **Extract services by hardware profile**:

1. **CPU/Network-Bound Services (Go):**
   - API Gateway, WebRTC Signalling, Multi-Tenant Authentication, Database CRUD.
   - Low CPU per connection, high I/O concurrency.

2. **GPU/Compute-Bound Services (Rust / C++ / CUDA / Triton):**
   - Bitstream decoding, TensorRT inference, Optical Flow, Object Tracking.
   - Dedicated GPU instances, high power draw.
"""
            }
        ]
    }
]


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    print("Iniciando compilação dos 5 Livros de Arquitetura de Software...\n")

    for idx, b in enumerate(BOOKS, 1):
        print(f"[{idx}/5] Compilando: {b['title']}...")
        out_md = os.path.join(DB_DIR, f"{b['filename_base']}.md")
        out_pdf = os.path.join(DB_DIR, f"{b['filename_base']}.pdf")

        # Gerar MD
        full_md = [
            f"# {b['title']}",
            f"\n> **Subtítulo:** {b['subtitle']}",
            f"> **Autor:** {b['author']}",
            f"> **Origem:** {b['origin']}\n",
            "---\n"
        ]
        for sec in b['sections']:
            full_md.append(f"# {sec['title']}\n\n{sec['markdown']}\n\n---\n")

        with open(out_md, 'w', encoding='utf-8') as fp:
            fp.write("\n".join(full_md))
        print(f"  ✔ MD salvo: {out_md} ({os.path.getsize(out_md)/1024:.1f} KB)")

        # Gerar PDF
        render_book_pdf(
            b['title'],
            b['subtitle'],
            b['author'],
            b['origin'],
            b['sections'],
            out_pdf
        )
        print(f"  ✔ PDF salvo: {out_pdf} ({os.path.getsize(out_pdf)/1024:.1f} KB)")

    print("\nTodos os 5 livros foram compilados com sucesso!")


if __name__ == "__main__":
    main()
