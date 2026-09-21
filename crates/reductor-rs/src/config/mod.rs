use std::env;
use std::path::PathBuf;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct Settings {
    pub llm_provider: String,
    pub gemini_api_key: String,
    pub gemini_model: String,
    pub ollama_base_url: String,
    pub ollama_llm_model: String,
    pub ollama_embed_model: String,
    pub database_dir: PathBuf,
    pub storage_dir: PathBuf,
    pub chunk_size: usize,
    pub chunk_overlap: usize,
    pub default_top_k: usize,
    pub default_max_context_tokens: usize,
    pub similarity_threshold: f32,
    pub api_security_key: Option<String>,
}

impl Default for Settings {
    fn default() -> Self {
        Self::load()
    }
}

impl Settings {
    pub fn load() -> Self {
        // Tenta carregar .env da raiz do projeto ou diretório atual
        let _ = dotenvy::dotenv();

        Self {
            llm_provider: env::var("LLM_PROVIDER").unwrap_or_else(|_| "ollama".to_string()),
            gemini_api_key: env::var("GEMINI_API_KEY").unwrap_or_default(),
            gemini_model: env::var("GEMINI_MODEL").unwrap_or_else(|_| "gemini-2.5-flash".to_string()),
            ollama_base_url: env::var("OLLAMA_BASE_URL").unwrap_or_else(|_| "http://localhost:11434".to_string()),
            ollama_llm_model: env::var("OLLAMA_LLM_MODEL").unwrap_or_else(|_| "qwen2.5:14b".to_string()),
            ollama_embed_model: env::var("OLLAMA_EMBED_MODEL").unwrap_or_else(|_| "nomic-embed-text".to_string()),
            database_dir: PathBuf::from(env::var("DATABASE_DIR").unwrap_or_else(|_| "./database".to_string())),
            storage_dir: PathBuf::from(env::var("STORAGE_DIR").unwrap_or_else(|_| "./storage".to_string())),
            chunk_size: env::var("CHUNK_SIZE").ok().and_then(|v| v.parse().ok()).unwrap_or(800),
            chunk_overlap: env::var("CHUNK_OVERLAP").ok().and_then(|v| v.parse().ok()).unwrap_or(150),
            default_top_k: env::var("DEFAULT_TOP_K").ok().and_then(|v| v.parse().ok()).unwrap_or(6),
            default_max_context_tokens: env::var("DEFAULT_MAX_CONTEXT_TOKENS").ok().and_then(|v| v.parse().ok()).unwrap_or(2500),
            similarity_threshold: env::var("SIMILARITY_THRESHOLD").ok().and_then(|v| v.parse().ok()).unwrap_or(0.25),
            api_security_key: env::var("API_SECURITY_KEY").ok().filter(|s| !s.trim().is_empty()),
        }
    }
}
