use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Clone)]
pub struct OllamaEmbeddingClient {
    base_url: String,
    model: String,
    client: Client,
}

#[derive(Serialize)]
struct EmbedRequestV2<'a> {
    model: &'a str,
    input: Vec<&'a str>,
    keep_alive: &'a str,
}

#[derive(Deserialize)]
struct EmbedResponseV2 {
    embeddings: Vec<Vec<f32>>,
}

#[derive(Serialize)]
struct EmbedRequestV1<'a> {
    model: &'a str,
    prompt: &'a str,
    keep_alive: &'a str,
}

#[derive(Deserialize)]
struct EmbedResponseV1 {
    embedding: Vec<f32>,
}

impl OllamaEmbeddingClient {
    pub fn new(base_url: String, model: String) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(120))
            .pool_max_idle_per_host(20)
            .build()
            .unwrap_or_default();

        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            model,
            client,
        }
    }

    /// Gera embeddings em batch para uma lista de textos
    pub async fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>, String> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }

        // 1. Tenta endpoint moderno /api/embed (Batch nativo do Ollama)
        let url_v2 = format!("{}/api/embed", self.base_url);
        let req_v2 = EmbedRequestV2 {
            model: &self.model,
            input: texts.to_vec(),
            keep_alive: "60m",
        };

        if let Ok(resp) = self.client.post(&url_v2).json(&req_v2).send().await {
            if resp.status().is_success() {
                if let Ok(parsed) = resp.json::<EmbedResponseV2>().await {
                    if parsed.embeddings.len() == texts.len() {
                        return Ok(parsed.embeddings);
                    }
                }
            }
        }

        // 2. Fallback para chamadas unitárias /api/embeddings se batch falhar
        let mut results = Vec::with_capacity(texts.len());
        for &text in texts {
            let emb = self.embed_single(text).await?;
            results.push(emb);
        }

        Ok(results)
    }

    /// Gera embedding para um único texto
    pub async fn embed_single(&self, text: &str) -> Result<Vec<f32>, String> {
        let url_v1 = format!("{}/api/embeddings", self.base_url);
        let req_v1 = EmbedRequestV1 {
            model: &self.model,
            prompt: text,
            keep_alive: "60m",
        };

        let resp = self.client.post(&url_v1)
            .json(&req_v1)
            .send()
            .await
            .map_err(|e| format!("Falha de conexão com Ollama embeddings: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Erro HTTP do Ollama: {}", resp.status()));
        }

        let data = resp.json::<EmbedResponseV1>()
            .await
            .map_err(|e| format!("Erro ao decodificar embedding do Ollama: {}", e))?;

        Ok(data.embedding)
    }
}
