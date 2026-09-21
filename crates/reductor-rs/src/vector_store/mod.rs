use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use crate::domain::{Book, BookChunk, ConfidentialityLevel, DocumentFormat, ScoredChunk};

#[derive(Clone, Serialize, Deserialize)]
pub struct VectorIndexData {
    pub books: Vec<Book>,
    pub chunks: Vec<BookChunk>,
}

pub struct EmbeddedVectorStore {
    persist_path: PathBuf,
    data: Arc<RwLock<VectorIndexData>>,
}

impl EmbeddedVectorStore {
    pub fn new<P: AsRef<Path>>(storage_dir: P) -> Self {
        let persist_path = storage_dir.as_ref().join("reductor_index.json");
        let mut initial_data = if persist_path.exists() {
            if let Ok(file) = fs::File::open(&persist_path) {
                let reader = std::io::BufReader::new(file);
                serde_json::from_reader(reader).unwrap_or_else(|_| VectorIndexData {
                    books: Vec::new(),
                    chunks: Vec::new(),
                })
            } else {
                VectorIndexData { books: Vec::new(), chunks: Vec::new() }
            }
        } else {
            VectorIndexData { books: Vec::new(), chunks: Vec::new() }
        };

        // Fallback seguro: se a lista de livros estiver vazia, carrega de indexed_books.json
        if initial_data.books.is_empty() {
            let indexed_books_path = storage_dir.as_ref().join("indexed_books.json");
            if let Ok(content) = fs::read_to_string(&indexed_books_path) {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(books_map) = val.get("books").and_then(|b| b.as_object()) {
                        for (_, b) in books_map {
                            let title = b["title"].as_str().unwrap_or("unknown").to_string();
                            let format_str = b["file_format"].as_str().unwrap_or("pdf");
                            initial_data.books.push(Book {
                                id: b["id"].as_str().unwrap_or("").to_string(),
                                title,
                                file_path: b["file_path"].as_str().unwrap_or("").to_string(),
                                file_hash: b["file_hash"].as_str().unwrap_or("").to_string(),
                                format: DocumentFormat::from_extension(format_str),
                                confidentiality: ConfidentialityLevel::Public,
                                total_chunks: b["total_chunks"].as_u64().unwrap_or(0) as usize,
                                total_tokens: b["total_tokens"].as_u64().unwrap_or(0) as usize,
                            });
                        }
                    }
                }
            }
        }

        Self {
            persist_path,
            data: Arc::new(RwLock::new(initial_data)),
        }
    }

    /// Salva o estado do índice no disco de forma atômica
    pub async fn persist(&self) -> Result<(), String> {
        let data = self.data.read().await;
        if let Some(parent) = self.persist_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let serialized = serde_json::to_string_pretty(&*data)
            .map_err(|e| format!("Erro ao serializar índice vetorial: {}", e))?;
        fs::write(&self.persist_path, serialized)
            .map_err(|e| format!("Erro ao gravar índice em {}: {}", self.persist_path.display(), e))?;
        Ok(())
    }

    /// Adiciona um livro e seus respectivos chunks vetoriais
    pub async fn add_book_with_chunks(&self, book: Book, chunks: Vec<BookChunk>) -> Result<(), String> {
        let mut data = self.data.write().await;
        // Remove versão anterior se já existia (reindexação)
        data.books.retain(|b| b.id != book.id);
        data.chunks.retain(|c| c.book_id != book.id);

        data.books.push(book);
        data.chunks.extend(chunks);
        drop(data);

        self.persist().await
    }

    /// Lista todos os livros indexados de forma síncrona/imediata
    pub fn list_books_sync(&self) -> Vec<Book> {
        self.data.try_read().map(|d| d.books.clone()).unwrap_or_default()
    }

    /// Lista todos os livros indexados
    pub async fn list_books(&self) -> Vec<Book> {
        let data = self.data.read().await;
        data.books.clone()
    }

    /// Obtém um livro pelo hash para evitar reindexação duplicada
    pub async fn find_book_by_hash(&self, hash: &str) -> Option<Book> {
        let data = self.data.read().await;
        data.books.iter().find(|b| b.file_hash == hash).cloned()
    }

    /// Realiza busca por similaridade de cosseno nos vetores
    pub async fn search_similar(
        &self,
        query_vector: &[f32],
        top_k: usize,
        threshold: f32,
        book_filter: Option<&str>,
    ) -> Vec<ScoredChunk> {
        let data = self.data.read().await;
        let mut scored_chunks: Vec<ScoredChunk> = Vec::new();

        for chunk in &data.chunks {
            if let Some(filter) = book_filter {
                if !chunk.book_title.to_lowercase().contains(&filter.to_lowercase()) {
                    continue;
                }
            }

            if let Some(emb) = &chunk.embedding {
                let similarity = cosine_similarity(query_vector, emb);
                if similarity >= threshold {
                    scored_chunks.push(ScoredChunk {
                        chunk: chunk.clone(),
                        similarity_score: similarity,
                        rank_position: 0,
                    });
                }
            }
        }

        // Ordena por maior similaridade
        scored_chunks.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap_or(std::cmp::Ordering::Equal));

        // Atribui posições de rank e limita pelo Top-K
        scored_chunks.truncate(top_k);
        for (idx, sc) in scored_chunks.iter_mut().enumerate() {
            sc.rank_position = idx + 1;
        }

        scored_chunks
    }
}

/// Cálculo otimizado de Similaridade de Cosseno entre dois vetores
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let mut dot_product = 0.0;
    let mut norm_a = 0.0;
    let mut norm_b = 0.0;

    for i in 0..a.len() {
        dot_product += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denominator = norm_a.sqrt() * norm_b.sqrt();
    if denominator == 0.0 {
        0.0
    } else {
        (dot_product / denominator).clamp(-1.0, 1.0)
    }
}
