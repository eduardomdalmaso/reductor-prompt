use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use crate::config::Settings;
use crate::domain::ScoredChunk;
use crate::security::{ConfidentialityGuard, SecuritySanitizer};

#[derive(Clone)]
pub struct LLMService {
    settings: Settings,
    http_client: Client,
}

#[derive(Serialize)]
struct OllamaGenerateRequest<'a> {
    model: &'a str,
    prompt: &'a str,
    stream: bool,
}

#[derive(Deserialize)]
struct OllamaGenerateResponse {
    response: String,
}

#[derive(Serialize)]
struct GeminiPart<'a> {
    text: &'a str,
}

#[derive(Serialize)]
struct GeminiContent<'a> {
    parts: Vec<GeminiPart<'a>>,
}

#[derive(Serialize)]
struct GeminiRequest<'a> {
    contents: Vec<GeminiContent<'a>>,
}

#[derive(Deserialize)]
struct GeminiCandidate {
    content: GeminiCandidateContent,
}

#[derive(Deserialize)]
struct GeminiCandidateContent {
    parts: Vec<GeminiCandidatePart>,
}

#[derive(Deserialize)]
struct GeminiCandidatePart {
    text: Option<String>,
}

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Option<Vec<GeminiCandidate>>,
}

impl LLMService {
    pub fn new(settings: Settings) -> Self {
        let http_client = Client::builder()
            .timeout(Duration::from_secs(180))
            .build()
            .unwrap_or_default();

        Self {
            settings,
            http_client,
        }
    }

    /// Gera resposta através de RAG seguro, com roteamento automático de confidencialidade
    pub async fn generate_rag_response(
        &self,
        query: &str,
        chunks: &[ScoredChunk],
        deep_mode: bool,
    ) -> Result<String, String> {
        if chunks.is_empty() {
            return Ok("Nenhum trecho relevante foi encontrado na base de livros para responder a esta consulta.".to_string());
        }

        // 1. Determina nível de confidencialidade dos dados recuperados
        let effective_level = ConfidentialityGuard::determine_effective_level(chunks);
        let cloud_allowed = ConfidentialityGuard::is_cloud_allowed(&effective_level);

        // 2. Monta o contexto dos livros
        let mut raw_context = String::new();
        for (i, sc) in chunks.iter().enumerate() {
            raw_context.push_str(&format!(
                "--- Trecho {} [Livro: {} | Pág: {} | Relevância: {:.2}] ---\n{}\n\n",
                i + 1,
                sc.chunk.book_title,
                sc.chunk.page_number.map(|p| p.to_string()).unwrap_or_else(|| "N/A".to_string()),
                sc.similarity_score,
                sc.chunk.content
            ));
        }

        // 3. Monta o Prompt Estruturado
        let system_instructions = if deep_mode {
            "Você é o ReductorPrompt, um arquiteto sênior de software e especialista técnico. \
            Analise profundamente os trechos dos livros abaixo e elabore uma resposta rica, detalhada, \
            com raciocínio lógico (Chain-of-Thought), citando os livros, capítulos e páginas correspondentes."
        } else {
            "Você é o ReductorPrompt, um assistente técnico cirúrgico. Responda diretamente à pergunta \
            com base estrita nos trechos dos livros fornecidos, citando os livros e autores correspondentes."
        };

        let prompt = format!(
            "{}\n\nContexto dos Livros:\n{}\nPergunta: {}\n\nResposta Técnica e Fundamentada:",
            system_instructions, raw_context, query
        );

        // 4. Roteamento de Provedor com Guardrails
        if self.settings.llm_provider == "gemini" && cloud_allowed && !self.settings.gemini_api_key.is_empty() {
            // Sanitiza antes de enviar para nuvem
            let sanitized_prompt = SecuritySanitizer::sanitize(&prompt);
            self.call_gemini(&sanitized_prompt).await
        } else {
            // Roda local no Ollama (RTX 5090)
            self.call_ollama(&prompt).await
        }
    }

    async fn call_ollama(&self, prompt: &str) -> Result<String, String> {
        let url = format!("{}/api/generate", self.settings.ollama_base_url.trim_end_matches('/'));
        let req = OllamaGenerateRequest {
            model: &self.settings.ollama_llm_model,
            prompt,
            stream: false,
        };

        let resp = self.http_client.post(&url)
            .json(&req)
            .send()
            .await
            .map_err(|e| format!("Falha de conexão com Ollama LLM ({}): {}", url, e))?;

        if !resp.status().is_success() {
            return Err(format!("Erro HTTP do Ollama: {}", resp.status()));
        }

        let body = resp.json::<OllamaGenerateResponse>()
            .await
            .map_err(|e| format!("Erro ao ler resposta do Ollama: {}", e))?;

        Ok(body.response)
    }

    async fn call_gemini(&self, prompt: &str) -> Result<String, String> {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.settings.gemini_model, self.settings.gemini_api_key
        );

        let req = GeminiRequest {
            contents: vec![GeminiContent {
                parts: vec![GeminiPart { text: prompt }],
            }],
        };

        let resp = self.http_client.post(&url)
            .json(&req)
            .send()
            .await
            .map_err(|e| format!("Falha ao conectar com Gemini API: {}", e))?;

        if !resp.status().is_success() {
            let error_text = resp.text().await.unwrap_or_default();
            return Err(format!("Erro da API Gemini: {}", error_text));
        }

        let body = resp.json::<GeminiResponse>()
            .await
            .map_err(|e| format!("Erro ao decodificar retorno do Gemini: {}", e))?;

        if let Some(candidates) = body.candidates {
            if let Some(first) = candidates.first() {
                if let Some(part) = first.content.parts.first() {
                    if let Some(text) = &part.text {
                        return Ok(text.clone());
                    }
                }
            }
        }

        Err("Resposta vazia da API Gemini".to_string())
    }
}
