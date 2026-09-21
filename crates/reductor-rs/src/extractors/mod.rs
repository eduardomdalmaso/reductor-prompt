use std::fs;
use std::path::Path;
use sha2::{Digest, Sha256};
use crate::domain::{Book, BookChunk};

pub struct DocumentExtractor;

impl DocumentExtractor {
    /// Calcula o hash SHA-256 do arquivo para deduplicação instantânea
    pub fn compute_sha256(path: &Path) -> Result<String, String> {
        let bytes = fs::read(path).map_err(|e| format!("Erro ao ler arquivo {}: {}", path.display(), e))?;
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        Ok(format!("{:x}", hasher.finalize()))
    }

    /// Extrai o texto completo de um documento com base na extensão
    pub fn extract_text(path: &Path) -> Result<Vec<(Option<usize>, String)>, String> {
        let ext = path.extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        match ext.as_str() {
            "pdf" => Self::extract_pdf(path),
            "md" | "txt" | "markdown" => Self::extract_plain(path),
            _ => Err(format!("Formato não suportado: {}", ext)),
        }
    }

    fn extract_pdf(path: &Path) -> Result<Vec<(Option<usize>, String)>, String> {
        let doc = lopdf::Document::load(path)
            .map_err(|e| format!("Erro ao carregar PDF {}: {}", path.display(), e))?;

        let mut pages_text = Vec::new();
        for (page_num, _) in doc.get_pages() {
            if let Ok(text) = doc.extract_text(&[page_num]) {
                let trimmed = text.trim().to_string();
                if !trimmed.is_empty() {
                    pages_text.push((Some(page_num as usize), trimmed));
                }
            }
        }

        if pages_text.is_empty() {
            // Fallback se extract_text por página falhar
            let full_text = doc.extract_text(&[1, 2, 3]).unwrap_or_default();
            pages_text.push((Some(1), full_text));
        }

        Ok(pages_text)
    }

    fn extract_plain(path: &Path) -> Result<Vec<(Option<usize>, String)>, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| format!("Erro ao ler arquivo {}: {}", path.display(), e))?;
        Ok(vec![(Some(1), content)])
    }

    /// Divide as páginas de um livro em chunks semânticos com overlap
    pub fn chunk_document(
        book: &Book,
        pages: &[(Option<usize>, String)],
        chunk_size: usize,
        chunk_overlap: usize,
    ) -> Vec<BookChunk> {
        let mut chunks = Vec::new();
        let mut chunk_idx = 0;

        for (page_num, text) in pages {
            let words: Vec<&str> = text.split_whitespace().collect();
            if words.is_empty() {
                continue;
            }

            // Estimativa de tokens: ~1.3 tokens por palavra
            let step = if chunk_size > chunk_overlap { chunk_size - chunk_overlap } else { chunk_size };
            let mut i = 0;

            while i < words.len() {
                let end = (i + chunk_size).min(words.len());
                let slice = &words[i..end];
                let chunk_content = slice.join(" ");
                let approx_tokens = (slice.len() as f32 * 1.3) as usize;

                chunks.push(BookChunk {
                    id: format!("{}_c{}", book.id, chunk_idx),
                    book_id: book.id.clone(),
                    book_title: book.title.clone(),
                    content: chunk_content,
                    page_number: *page_num,
                    chapter: None,
                    token_count: approx_tokens,
                    confidentiality: book.confidentiality.clone(),
                    embedding: None,
                });

                chunk_idx += 1;
                i += step;
                if end == words.len() {
                    break;
                }
            }
        }

        chunks
    }
}
