use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DocumentFormat {
    Pdf,
    Epub,
    Markdown,
    PlainText,
    Unknown,
}

impl DocumentFormat {
    pub fn from_extension(ext: &str) -> Self {
        match ext.to_lowercase().as_str() {
            "pdf" => DocumentFormat::Pdf,
            "epub" => DocumentFormat::Epub,
            "md" | "markdown" => DocumentFormat::Markdown,
            "txt" => DocumentFormat::PlainText,
            _ => DocumentFormat::Unknown,
        }
    }

    pub fn badge_label(&self) -> &'static str {
        match self {
            DocumentFormat::Pdf => ".PDF",
            DocumentFormat::Epub => ".EPUB",
            DocumentFormat::Markdown => ".MD",
            DocumentFormat::PlainText => ".TXT",
            DocumentFormat::Unknown => ".DOC",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConfidentialityLevel {
    Public,       // Livros técnicos e documentação pública (pode ir para Gemini/Cloud)
    Internal,     // Documentos internos da empresa (apenas Ollama local)
    Confidential, // Segredos estritos / PII (Ollama local + Sanitização forçada)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub id: String,
    pub title: String,
    pub file_path: String,
    pub file_hash: String,
    pub format: DocumentFormat,
    pub confidentiality: ConfidentialityLevel,
    pub total_chunks: usize,
    pub total_tokens: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookChunk {
    pub id: String,
    pub book_id: String,
    pub book_title: String,
    pub content: String,
    pub page_number: Option<usize>,
    pub chapter: Option<String>,
    pub token_count: usize,
    pub confidentiality: ConfidentialityLevel,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding: Option<Vec<f32>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredChunk {
    pub chunk: BookChunk,
    pub similarity_score: f32,
    pub rank_position: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenBudgetResult {
    pub selected_chunks: Vec<ScoredChunk>,
    pub total_tokens_used: usize,
    pub total_tokens_saved: usize,
    pub reduction_percentage: f32,
}
