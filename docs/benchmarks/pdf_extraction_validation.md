# Validação de Preservação Estrutural na Extração de PDF

**Arquivo alterado:** [document_loaders.py](file:///c:/Users/hades/Documents/reductor-prompt/src/adapters/outbound/loaders/document_loaders.py#L33-L115)  
**Função adicionada:** `normalize_preserving_structure(text)`  
**PDF real testado:** `database/architecturepatternswithpython.pdf` (Página física `39`)

---

## 1. O que mudou

- **Antes**: `re.sub(r'\s+', ' ', cleaned).strip()` colapsava todas as quebras de linha (`\n`), espaços de indentação e linhas em branco em um único espaço `' '`.
- **Depois**: `normalize_preserving_structure(text)` normaliza `\r\n`/`\r` para `\n`, remove apenas espaços à direita no fim de cada linha (`[ \t]+$`) e colapsa 3+ linhas em branco consecutivas para `\n\n`, preservando quebras de linha, indentação de código, separação de parágrafos e colunas alinhadas.

---

## 2. Comparação Real (Página 39 de `architecturepatternswithpython.pdf`)

- **Quantidade de linhas extraídas (antes):** `1` linha (tudo achatado)
- **Quantidade de linhas extraídas (depois):** `34` linhas preservadas

### Antes (achatado)
```text
This test is going to require a smarter model (test_batches.py) def test_can_only_deallocate_allocated_lines(): batch, unallocated_line = make_batch_and_line("DECORATIVE-TRINKET", 20, 2) batch.deallocate(unallocated_line) assert batch.available_quantity == 20 In this test, we’re asserting that deallocating a line from a batch has no effect unless the batch previously allocated the line.
```

### Depois (estrutura preservada)
```text
This test is going to require a smarter model (test_batches.py)
def test_can_only_deallocate_allocated_lines():
    batch, unallocated_line = make_batch_and_line("DECORATIVE-TRINKET", 20, 2)
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == 20
In this test, we’re asserting that deallocating a line from a batch has no effect unless
the batch previously allocated the line.
```

---

## 3. Limitações Observadas

1. O ambiente atual não possui `pymupdf` nem `fontTools` instalados, portanto o `PDFDocumentLoader` utilizou o fallback `pypdf`.
2. Hífens de quebra de linha tipográfica no PDF (ex.: `under‐\nstan`) são preservados literalmente como estão na camada de texto do PDF; diagramas em imagem continuam sem OCR.
3. `EPUBDocumentLoader` não foi alterado nesta etapa (mantém `re.sub(r'\s+', ' ', text)`).
